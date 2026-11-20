from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models import User
from app.schemas.analytics import AnalyticsOverview, LanguageUsage, PerformanceMetrics
from app.services import analytics_service

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
def overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return analytics_service.overview(db, user.id)


@router.get("/languages", response_model=list[LanguageUsage])
def languages(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    return analytics_service.language_usage(db, user.id)


@router.get("/performance", response_model=PerformanceMetrics)
def performance(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return analytics_service.performance(db, user.id)


@router.get("/activity")
def activity(
    granularity: str = "day",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    if granularity == "week":
        return analytics_service.weekly_activity(db, user.id)
    return analytics_service.daily_activity(db, user.id)
