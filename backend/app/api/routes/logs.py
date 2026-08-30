from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_case_access, require_role
from app.core.audit import log_audit_event
from app.db.models.base_models import (
    ArtifactStatus,
    Case,
    Device,
    RawArtifact,
    User,
    UserRole,
)
from app.db.session import get_db
from app.storage.object_store import upload_raw_artifact
from app.tasks.ingestion_tasks import parse_log_file

router = APIRouter(prefix="/api/cases", tags=["logs"])

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


class DeviceCreateRequest(BaseModel):
    device_type: str
    os: str | None = None
    owner: str | None = None
    name: str | None = None


class DeviceResponse(BaseModel):
    id: str
    case_id: str
    device_type: str
    os: str | None
    owner: str | None
    name: str | None

    model_config = {"from_attributes": True}


class ArtifactResponse(BaseModel):
    id: str
    filename: str
    sha256: str
    status: str
    status_reason: str | None
    uploaded_at: str

    model_config = {"from_attributes": True}


@router.post(
    "/{case_id}/devices",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_device(
    case_id: str,
    body: DeviceCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.INVESTIGATOR)),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    device = Device(
        case_id=case_id,
        device_type=body.device_type,
        os=body.os,
        owner=body.owner,
        name=body.name,
    )
    db.add(device)
    await db.flush()

    await log_audit_event(
        db,
        case_id=case_id,
        user_id=str(current_user.id),
        action="device_created",
        target_type="device",
        target_id=str(device.id),
    )

    return DeviceResponse(
        id=str(device.id),
        case_id=str(device.case_id),
        device_type=device.device_type,
        os=device.os,
        owner=device.owner,
        name=device.name,
    )


@router.get("/{case_id}/devices", response_model=list[DeviceResponse])
async def list_devices(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_case_access),
):
    result = await db.execute(select(Device).where(Device.case_id == case_id))
    devices = result.scalars().all()
    return [
        DeviceResponse(
            id=str(d.id),
            case_id=str(d.case_id),
            device_type=d.device_type,
            os=d.os,
            owner=d.owner,
            name=d.name,
        )
        for d in devices
    ]


@router.post(
    "/{case_id}/logs",
    response_model=ArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_log(
    case_id: str,
    file: UploadFile = File(...),
    device_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.INVESTIGATOR)),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if device_id:
        dev_result = await db.execute(
            select(Device).where(Device.id == device_id, Device.case_id == case_id)
        )
        if not dev_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Device not found in this case")

    # Read file content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    # Upload to immutable store
    sha256, storage_path = upload_raw_artifact(
        case_id=case_id,
        device_id=device_id,
        filename=file.filename or "unknown",
        data=content,
    )

    # Create DB record
    artifact = RawArtifact(
        case_id=case_id,
        device_id=device_id,
        filename=file.filename or "unknown",
        sha256=sha256,
        storage_path=storage_path,
        status=ArtifactStatus.QUEUED,
        uploaded_by=current_user.id,
    )
    db.add(artifact)
    await db.flush()

    await log_audit_event(
        db,
        case_id=case_id,
        user_id=str(current_user.id),
        action="artifact_uploaded",
        target_type="artifact",
        target_id=str(artifact.id),
        detail=f"Uploaded {file.filename} ({len(content)} bytes, sha256={sha256[:16]}...)",
    )

    # Enqueue async parsing
    parse_log_file.delay(str(artifact.id), case_id, device_id)

    return ArtifactResponse(
        id=str(artifact.id),
        filename=artifact.filename,
        sha256=artifact.sha256,
        status=artifact.status.value,
        status_reason=artifact.status_reason,
        uploaded_at=artifact.uploaded_at.isoformat(),
    )


@router.get("/{case_id}/logs", response_model=list[ArtifactResponse])
async def list_artifacts(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_case_access),
):
    result = await db.execute(
        select(RawArtifact)
        .where(RawArtifact.case_id == case_id)
        .order_by(RawArtifact.uploaded_at.desc())
    )
    artifacts = result.scalars().all()
    return [
        ArtifactResponse(
            id=str(a.id),
            filename=a.filename,
            sha256=a.sha256,
            status=a.status.value,
            status_reason=a.status_reason,
            uploaded_at=a.uploaded_at.isoformat(),
        )
        for a in artifacts
    ]
