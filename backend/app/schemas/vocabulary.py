from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

CATEGORIES = ("general", "personal_name", "place", "technical", "brand", "acronym")


class VocabularyBase(BaseModel):
    word: str = Field(min_length=1, max_length=160)
    preferred_spelling: str = Field(min_length=1, max_length=160)
    category: str = "general"
    language_code: str = "en-IN"
    pronunciation_hint: Optional[str] = Field(default=None, max_length=160)
    weight: float = Field(default=1.0, ge=0.0, le=5.0)


class VocabularyCreate(VocabularyBase):
    pass


class VocabularyUpdate(BaseModel):
    word: Optional[str] = Field(default=None, min_length=1, max_length=160)
    preferred_spelling: Optional[str] = Field(default=None, min_length=1, max_length=160)
    category: Optional[str] = None
    language_code: Optional[str] = None
    pronunciation_hint: Optional[str] = None
    weight: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    is_active: Optional[bool] = None


class VocabularyOut(VocabularyBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    is_active: bool
    source: str
    usage_count: int
    created_at: Optional[datetime] = None


class VocabularyBulkImport(BaseModel):
    entries: List[VocabularyCreate] = Field(max_length=500)
