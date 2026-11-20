from __future__ import annotations

import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models import Transcription, User
from app.schemas.history import HistoryPage, TranscriptionOut, TranscriptionUpdate
from app.services.speech_service import regenerate_output

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=HistoryPage)
def list_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = None,
    language: str | None = None,
    sort: str = Query("desc", pattern="^(asc|desc)$"),
    model: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HistoryPage:
    q = (
        db.query(Transcription)
        .options(selectinload(Transcription.segments))
        .filter(Transcription.user_id == user.id, Transcription.deleted_at.is_(None))
    )
    if search:
        like = f"%{search}%"
        q = q.filter(
            or_(
                Transcription.title.ilike(like),
                Transcription.original_text.ilike(like),
                Transcription.english_text.ilike(like),
            )
        )
    if language:
        # JSON column: compare via cast to text to stay portable across SQLite/PG
        q = q.filter(Transcription.detected_languages.cast(__import__("sqlalchemy").String).ilike(f"%{language}%"))
    if model:
        q = q.filter(Transcription.model_used == model)

    total = q.count()
    order = Transcription.created_at.desc() if sort == "desc" else Transcription.created_at.asc()
    items = q.order_by(order).offset((page - 1) * page_size).limit(page_size).all()
    return HistoryPage(
        items=[TranscriptionOut.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/{transcription_id}", response_model=TranscriptionOut)
def get_transcription(
    transcription_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Transcription:
    row = (
        db.query(Transcription)
        .options(selectinload(Transcription.segments))
        .filter(Transcription.id == transcription_id, Transcription.user_id == user.id)
        .first()
    )
    if row is None or row.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transcription not found")
    return row


@router.patch("/{transcription_id}", response_model=TranscriptionOut)
def update_transcription(
    transcription_id: str,
    payload: TranscriptionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Transcription:
    row = (
        db.query(Transcription)
        .options(selectinload(Transcription.segments))
        .filter(Transcription.id == transcription_id, Transcription.user_id == user.id)
        .first()
    )
    if row is None or row.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transcription not found")
    changes = payload.model_dump(exclude_unset=True)
    if "original_text" in changes and changes["original_text"] != row.original_text:
        row.edit_count = (row.edit_count or 0) + 1
    for field, value in changes.items():
        setattr(row, field, value)
    if "original_text" in changes:
        row.word_count = len((changes["original_text"] or "").split())
    db.commit()
    db.refresh(row)
    return row


@router.post("/{transcription_id}/outputs/{kind}", response_model=dict)
async def generate_output(
    transcription_id: str,
    kind: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    if kind not in ("native", "romanized", "english"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "kind must be native|romanized|english")
    row = (
        db.query(Transcription)
        .filter(Transcription.id == transcription_id, Transcription.user_id == user.id)
        .first()
    )
    if row is None or row.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transcription not found")
    return await regenerate_output(db, user, row, kind)


@router.delete("/{transcription_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_transcription(
    transcription_id: str,
    hard: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    row = (
        db.query(Transcription)
        .filter(Transcription.id == transcription_id, Transcription.user_id == user.id)
        .first()
    )
    if row is None or row.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transcription not found")
    if hard:
        db.delete(row)
    else:
        row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{transcription_id}/rewrite", response_model=dict)
def smart_rewrite_endpoint(
    transcription_id: str,
    profile: str = Query("email"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Context-aware rewrite of a stored transcript.

    Rule-based by default (labelled ``method="rule_based"``); an LLM rewriter can
    be plugged into the engine via ``set_llm_rewriter``.
    """
    from ai_engine.intelligence.contextual_correction import smart_rewrite

    row = (
        db.query(Transcription)
        .filter(Transcription.id == transcription_id, Transcription.user_id == user.id)
        .first()
    )
    if row is None or row.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transcription not found")

    from app.services.speech_service import load_vocabulary

    preserve = [e.target for e in load_vocabulary(db, user.id)]
    result = smart_rewrite(row.original_text, profile, preserve)
    row.professional_text = result.text
    row.context_profile = profile
    db.commit()
    return {"text": result.text, "method": result.method, "changes": result.changes, "profile": profile}
