from __future__ import annotations

import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models import User, UserVocabulary
from app.schemas.vocabulary import (
    VocabularyBulkImport,
    VocabularyCreate,
    VocabularyOut,
    VocabularyUpdate,
)

router = APIRouter(prefix="/api/vocabulary", tags=["vocabulary"])


@router.get("", response_model=list[VocabularyOut])
def list_entries(
    search: str | None = None,
    category: str | None = None,
    language_code: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[UserVocabulary]:
    q = db.query(UserVocabulary).filter(UserVocabulary.user_id == user.id)
    if search:
        like = f"%{search.lower()}%"
        q = q.filter(
            (UserVocabulary.word.ilike(like)) | (UserVocabulary.preferred_spelling.ilike(like))
        )
    if category:
        q = q.filter(UserVocabulary.category == category)
    if language_code:
        q = q.filter(UserVocabulary.language_code == language_code)
    return q.order_by(UserVocabulary.created_at.desc()).limit(limit).all()


@router.post("", response_model=VocabularyOut, status_code=status.HTTP_201_CREATED)
def create_entry(
    payload: VocabularyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserVocabulary:
    existing = (
        db.query(UserVocabulary)
        .filter(
            UserVocabulary.user_id == user.id,
            UserVocabulary.word == payload.word.strip(),
            UserVocabulary.language_code == payload.language_code,
        )
        .first()
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "This word already exists for that language")
    entry = UserVocabulary(user_id=user.id, **payload.model_dump())
    entry.word = entry.word.strip()
    entry.preferred_spelling = entry.preferred_spelling.strip()
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.put("/{entry_id}", response_model=VocabularyOut)
def update_entry(
    entry_id: str,
    payload: VocabularyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserVocabulary:
    entry = (
        db.query(UserVocabulary)
        .filter(UserVocabulary.id == entry_id, UserVocabulary.user_id == user.id)
        .first()
    )
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vocabulary entry not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_entry(
    entry_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    entry = (
        db.query(UserVocabulary)
        .filter(UserVocabulary.id == entry_id, UserVocabulary.user_id == user.id)
        .first()
    )
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vocabulary entry not found")
    db.delete(entry)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/import", response_model=dict)
def import_entries(
    payload: VocabularyBulkImport,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    existing = {
        (w, l)
        for w, l in db.query(UserVocabulary.word, UserVocabulary.language_code)
        .filter(UserVocabulary.user_id == user.id)
        .all()
    }
    created = skipped = 0
    for item in payload.entries:
        key = (item.word.strip(), item.language_code)
        if key in existing:
            skipped += 1
            continue
        db.add(UserVocabulary(user_id=user.id, **item.model_dump()))
        existing.add(key)
        created += 1
    db.commit()
    return {"created": created, "skipped": skipped}


@router.get("/export", response_class=PlainTextResponse)
def export_entries(
    fmt: str = Query("json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PlainTextResponse:
    rows = db.query(UserVocabulary).filter(UserVocabulary.user_id == user.id).all()
    data = [
        {
            "word": r.word,
            "preferred_spelling": r.preferred_spelling,
            "category": r.category,
            "language_code": r.language_code,
            "pronunciation_hint": r.pronunciation_hint,
            "weight": r.weight,
        }
        for r in rows
    ]
    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(data[0].keys()) if data else ["word"])
        writer.writeheader()
        writer.writerows(data)
        return PlainTextResponse(buf.getvalue(), media_type="text/csv",
                                 headers={"Content-Disposition": "attachment; filename=vocabulary.csv"})
    return PlainTextResponse(json.dumps(data, ensure_ascii=False, indent=2),
                             media_type="application/json",
                             headers={"Content-Disposition": "attachment; filename=vocabulary.json"})
