from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.audit import log_audit_event
from app.db.models.base_models import Case, CaseInvestigator, CaseStatus, User, UserRole
from app.db.session import get_db

router = APIRouter(prefix="/api/cases", tags=["cases"])


class CaseCreateRequest(BaseModel):
    name: str
    description: str | None = None


class CaseUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    status: CaseStatus | None = None


class CaseResponse(BaseModel):
    id: str
    name: str
    description: str | None
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    body: CaseCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.INVESTIGATOR)),
):
    case = Case(
        name=body.name,
        description=body.description,
        created_by=current_user.id,
    )
    db.add(case)
    await db.flush()

    investigator = CaseInvestigator(case_id=case.id, user_id=current_user.id)
    db.add(investigator)
    await db.flush()

    await log_audit_event(
        db,
        case_id=str(case.id),
        user_id=str(current_user.id),
        action="case_created",
        target_type="case",
        target_id=str(case.id),
        detail=f"Case '{body.name}' created",
    )

    return CaseResponse(
        id=str(case.id),
        name=case.name,
        description=case.description,
        status=case.status.value,
        created_by=str(case.created_by),
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.get("", response_model=list[CaseResponse])
async def list_cases(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.ADMIN:
        result = await db.execute(select(Case).order_by(Case.created_at.desc()))
    else:
        result = await db.execute(
            select(Case)
            .join(CaseInvestigator, CaseInvestigator.case_id == Case.id)
            .where(CaseInvestigator.user_id == current_user.id)
            .order_by(Case.created_at.desc())
        )
    cases = result.scalars().all()
    return [
        CaseResponse(
            id=str(c.id),
            name=c.name,
            description=c.description,
            status=c.status.value,
            created_by=str(c.created_by),
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in cases
    ]


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if current_user.role != UserRole.ADMIN:
        inv_result = await db.execute(
            select(CaseInvestigator).where(
                CaseInvestigator.case_id == case.id,
                CaseInvestigator.user_id == current_user.id,
            )
        )
        if not inv_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not assigned to this case")

    return CaseResponse(
        id=str(case.id),
        name=case.name,
        description=case.description,
        status=case.status.value,
        created_by=str(case.created_by),
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: str,
    body: CaseUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.INVESTIGATOR)),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if current_user.role != UserRole.ADMIN:
        inv_result = await db.execute(
            select(CaseInvestigator).where(
                CaseInvestigator.case_id == case.id,
                CaseInvestigator.user_id == current_user.id,
            )
        )
        if not inv_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not assigned to this case")

    if body.name is not None:
        case.name = body.name
    if body.description is not None:
        case.description = body.description
    if body.status is not None:
        case.status = body.status

    await db.flush()

    await log_audit_event(
        db,
        case_id=str(case.id),
        user_id=str(current_user.id),
        action="case_updated",
        target_type="case",
        target_id=str(case.id),
    )

    return CaseResponse(
        id=str(case.id),
        name=case.name,
        description=case.description,
        status=case.status.value,
        created_by=str(case.created_by),
        created_at=case.created_at,
        updated_at=case.updated_at,
    )
