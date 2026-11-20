from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models import User, UserPreference

router = APIRouter(prefix="/api/settings", tags=["settings"])


class PreferencesOut(BaseModel):
    preferred_languages: list[str]
    default_output_mode: str
    default_context: str
    audio_quality: str
    noise_reduction: bool
    vad_enabled: bool
    offline_mode: bool
    auto_punctuation: bool
    audio_retention: str
    theme: str
    reduced_motion: bool
    keyboard_shortcuts: dict

    model_config = {"from_attributes": True}


class PreferencesUpdate(BaseModel):
    preferred_languages: list[str] | None = Field(default=None, max_length=13)
    default_output_mode: str | None = Field(
        default=None, pattern="^(transcribe|codemix|translit|translate|verbatim)$"
    )
    default_context: str | None = None
    audio_quality: str | None = Field(default=None, pattern="^(low|medium|high)$")
    noise_reduction: bool | None = None
    vad_enabled: bool | None = None
    offline_mode: bool | None = None
    auto_punctuation: bool | None = None
    audio_retention: str | None = Field(default=None, pattern="^(discard|30d|90d|keep)$")
    theme: str | None = Field(default=None, pattern="^(dark|light)$")
    reduced_motion: bool | None = None
    keyboard_shortcuts: dict | None = None


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)


def _get_or_create(db: Session, user: User) -> UserPreference:
    pref = db.query(UserPreference).filter(UserPreference.user_id == user.id).first()
    if pref is None:
        pref = UserPreference(user_id=user.id)
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref


@router.get("", response_model=PreferencesOut)
def get_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> UserPreference:
    return _get_or_create(db, user)


@router.put("", response_model=PreferencesOut)
def update_settings(
    payload: PreferencesUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserPreference:
    pref = _get_or_create(db, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(pref, field, value)
    db.commit()
    db.refresh(pref)
    return pref


@router.put("/profile", response_model=dict)
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    db.commit()
    return {"id": user.id, "email": user.email, "full_name": user.full_name}


@router.delete("/data", response_model=dict)
def delete_all_data(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Right-to-erasure: removes transcriptions, vocabulary and events."""
    from app.models import AnalyticsEvent, RoutingDecision, Transcription, UserCorrection, UserVocabulary

    counts = {}
    for model, field in (
        (Transcription, Transcription.user_id),
        (UserVocabulary, UserVocabulary.user_id),
        (UserCorrection, UserCorrection.user_id),
        (RoutingDecision, RoutingDecision.user_id),
        (AnalyticsEvent, AnalyticsEvent.user_id),
    ):
        counts[model.__tablename__] = db.query(model).filter(field == user.id).delete()
    db.commit()
    return {"deleted": counts}
