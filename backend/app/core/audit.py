import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.base_models import AuditLog

logger = structlog.get_logger()


async def log_audit_event(
    db: AsyncSession,
    *,
    case_id: str | None = None,
    user_id: str | None = None,
    action: str,
    target_type: str,
    target_id: str | None = None,
    detail: str | None = None,
) -> None:
    entry = AuditLog(
        case_id=case_id,
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
    )
    db.add(entry)
    await db.flush()
    logger.info(
        "audit_event",
        action=action,
        target_type=target_type,
        target_id=target_id,
        case_id=case_id,
        user_id=user_id,
    )
