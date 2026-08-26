from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.audit import log_audit_event
from app.db.models.base_models import Anomaly, CorrelationEdge, Entity, User, UserRole
from app.db.session import get_db

router = APIRouter(prefix="/api/cases", tags=["anomalies"])


class AnomalyResponse(BaseModel):
    id: str
    event_ids: list[str]
    score: float
    severity: str
    category: str
    model_name: str
    model_version: str | None
    explanation: dict | None
    review_status: str
    created_at: str

    model_config = {"from_attributes": True}


class CorrelationEdgeResponse(BaseModel):
    id: str
    entity_a_id: str
    entity_b_id: str
    relation_type: str
    confidence: float
    evidence_event_ids: list[str]
    explanation: dict | None
    model_version: str | None
    created_at: str

    model_config = {"from_attributes": True}


class EntityResponse(BaseModel):
    id: str
    entity_type: str
    value: str
    metadata: dict | None

    model_config = {"from_attributes": True}


class ReviewRequest(BaseModel):
    review_status: str  # confirmed or dismissed


@router.get("/{case_id}/anomalies", response_model=list[AnomalyResponse])
async def list_anomalies(
    case_id: str,
    severity: str | None = Query(None),
    category: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Anomaly).where(Anomaly.case_id == case_id).order_by(Anomaly.score.desc())
    if severity:
        stmt = stmt.where(Anomaly.severity == severity)
    if category:
        stmt = stmt.where(Anomaly.category == category)

    result = await db.execute(stmt)
    anomalies = result.scalars().all()

    return [
        AnomalyResponse(
            id=str(a.id),
            event_ids=a.event_ids or [],
            score=a.score,
            severity=a.severity,
            category=a.category,
            model_name=a.model_name,
            model_version=a.model_version,
            explanation=a.explanation_json,
            review_status=a.review_status,
            created_at=a.created_at.isoformat(),
        )
        for a in anomalies
    ]


@router.patch("/{case_id}/anomalies/{anomaly_id}/review")
async def review_anomaly(
    case_id: str,
    anomaly_id: str,
    body: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.INVESTIGATOR)),
):
    result = await db.execute(
        select(Anomaly).where(Anomaly.id == anomaly_id, Anomaly.case_id == case_id)
    )
    anomaly = result.scalar_one_or_none()
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    if body.review_status not in ("pending", "confirmed", "dismissed"):
        raise HTTPException(status_code=400, detail="Invalid review_status")

    anomaly.review_status = body.review_status
    anomaly.reviewed_by = current_user.id
    await db.flush()

    await log_audit_event(
        db,
        case_id=case_id,
        user_id=str(current_user.id),
        action="anomaly_reviewed",
        target_type="anomaly",
        target_id=str(anomaly.id),
        detail=f"Review status: {body.review_status}",
    )

    return {"status": anomaly.review_status, "reviewed_by": str(current_user.id)}


@router.get("/{case_id}/correlations", response_model=list[CorrelationEdgeResponse])
async def list_correlations(
    case_id: str,
    relation_type: str | None = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(CorrelationEdge)
        .where(CorrelationEdge.case_id == case_id)
        .where(CorrelationEdge.confidence >= min_confidence)
        .order_by(CorrelationEdge.confidence.desc())
    )
    if relation_type:
        stmt = stmt.where(CorrelationEdge.relation_type == relation_type)

    result = await db.execute(stmt)
    edges = result.scalars().all()

    return [
        CorrelationEdgeResponse(
            id=str(e.id),
            entity_a_id=str(e.entity_a_id),
            entity_b_id=str(e.entity_b_id),
            relation_type=e.relation_type,
            confidence=e.confidence,
            evidence_event_ids=e.evidence_event_ids or [],
            explanation=e.explanation_json,
            model_version=e.model_version,
            created_at=e.created_at.isoformat(),
        )
        for e in edges
    ]


@router.get("/{case_id}/entities", response_model=list[EntityResponse])
async def list_entities(
    case_id: str,
    entity_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Entity).where(Entity.case_id == case_id)
    if entity_type:
        stmt = stmt.where(Entity.entity_type == entity_type)

    result = await db.execute(stmt)
    entities = result.scalars().all()

    return [
        EntityResponse(
            id=str(e.id),
            entity_type=e.entity_type,
            value=e.value,
            metadata=e.entity_metadata,
        )
        for e in entities
    ]
