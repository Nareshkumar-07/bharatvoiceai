from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ai_engine.registry import build_adapters
from app.api.deps import get_current_user
from app.database.session import get_db
from app.models import User
from app.schemas.ai import (
    EvaluationResponse,
    RouterMetrics,
    RouterPolicyIn,
    StatusResponse,
)
from app.services import ai_service
from app.services.speech_service import get_router

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/models")
async def models(_: User = Depends(get_current_user)) -> dict:
    payload = await ai_service.status_payload()
    return {"models": payload["models"], "primary_engine": payload["primary_engine"]}


@router.get("/status", response_model=StatusResponse)
async def status_endpoint(_: User = Depends(get_current_user)) -> dict:
    return await ai_service.status_payload()


@router.get("/router/metrics", response_model=RouterMetrics)
def router_metrics(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return ai_service.router_metrics(db, user.id)


@router.put("/router/policy", response_model=dict)
def update_policy(payload: RouterPolicyIn, _: User = Depends(get_current_user)) -> dict:
    router = get_router()
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if value is not None:
            setattr(router.policy, field, value)
    return {"policy": router.policy.to_dict()}


@router.get("/evaluation", response_model=EvaluationResponse)
def evaluation(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return ai_service.evaluation_summary(db, user.id)
