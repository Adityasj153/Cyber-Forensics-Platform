import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import verify_password, get_user_by_username
from app.db.session import async_session_factory
from app.db.models.base_models import RawArtifact, ArtifactStatus, LogEvent
import app.ingestion.registry as registry
from app.ingestion.parsers.windows_evtx import WindowsEVTXParser
from app.ingestion.parsers.linux_syslog import LinuxSyslogParser
from app.ingestion.parsers.android_logcat import AndroidLogcatParser
from app.ingestion.parsers.android_usb_bt import AndroidUSBBTParser
from app.ingestion.parsers.email_headers import EmailHeadersParser
from app.ingestion.parsers.network_generic import NetworkGenericParser
from app.ingestion.normalizer import normalize_events
from app.storage.object_store import download_raw_artifact, verify_artifact_integrity
from app.storage.search_index import index_log_events_bulk
from app.tasks.celery_app import celery_app

settings = get_settings()
logger = structlog.get_logger()

# Register all parsers on import
registry.register_parser(WindowsEVTXParser())
registry.register_parser(LinuxSyslogParser())
registry.register_parser(AndroidLogcatParser())
registry.register_parser(AndroidUSBBTParser())
registry.register_parser(EmailHeadersParser())
registry.register_parser(NetworkGenericParser())


async def persist_log_events(db: AsyncSession, normalized: list[dict]) -> int:
    """Persist normalized events to Postgres (source of truth for the AI engine).

    Extracted from the parse task so the persistence bug that previously left
    LogEvent rows unpersisted (AI saw nothing) has a direct regression test.
    """
    for ev in normalized:
        db.add(
            LogEvent(
                id=ev["id"],
                case_id=ev["case_id"],
                device_id=ev["device_id"],
                artifact_id=ev["artifact_id"],
                timestamp=ev["timestamp"],
                source_type=ev["source_type"],
                actor=ev["actor"],
                action=ev["action"],
                object=ev["object"],
                ip_address=ev["ip_address"],
                file_hash=ev["file_hash"],
                detail=ev["detail"],
                raw_line=ev["raw_line"],
            )
        )
    return len(normalized)


@celery_app.task(name="tasks.parse_log_file", bind=True, max_retries=3)
def parse_log_file(self, artifact_id: str, case_id: str, device_id: str | None = None):
    """Async task: download artifact, detect format, parse, normalize, index."""
    async def _run():
        async with async_session_factory() as db:
            try:
                result = await db.execute(
                    select(RawArtifact).where(RawArtifact.id == artifact_id)
                )
                artifact = result.scalar_one_or_none()
                if not artifact:
                    logger.error("artifact_not_found", artifact_id=artifact_id)
                    return

                # Update status to parsing
                artifact.status = ArtifactStatus.PARSING
                await db.commit()

                # Verify integrity before processing
                if not verify_artifact_integrity(artifact.storage_path, artifact.sha256):
                    artifact.status = ArtifactStatus.PARSE_FAILED
                    artifact.status_reason = "SHA-256 integrity check failed"
                    await db.commit()
                    logger.error(
                        "integrity_check_failed",
                        artifact_id=artifact_id,
                        case_id=case_id,
                    )
                    return

                # Download and parse
                raw_data = download_raw_artifact(artifact.storage_path)
                parsed_events = registry.parse_file(artifact.filename, raw_data)

                # Normalize
                normalized = normalize_events(
                    case_id=case_id,
                    device_id=device_id,
                    artifact_id=artifact_id,
                    events=parsed_events,
                )

                # Persist normalized events to Postgres (source of truth for the AI engine)
                await persist_log_events(db, normalized)

                # Index into Elasticsearch
                index_log_events_bulk(normalized)

                # Update artifact status
                artifact.status = ArtifactStatus.PARSED
                await db.commit()

                logger.info(
                    "log_parsed_successfully",
                    artifact_id=artifact_id,
                    case_id=case_id,
                    filename=artifact.filename,
                    events_count=len(normalized),
                )

                # Enqueue AI correlation after successful parse
                from app.tasks.ai_tasks import run_ai_correlation
                run_ai_correlation.delay(case_id)

            except ValueError as e:
                # Unsupported format
                async with async_session_factory() as err_db:
                    result = await err_db.execute(
                        select(RawArtifact).where(RawArtifact.id == artifact_id)
                    )
                    artifact = result.scalar_one_or_none()
                    if artifact:
                        artifact.status = ArtifactStatus.PARSE_FAILED
                        artifact.status_reason = str(e)[:500]
                        await err_db.commit()
                logger.error("parse_failed_unsupported", artifact_id=artifact_id, error=str(e))

            except Exception as e:
                # Unexpected error
                async with async_session_factory() as err_db:
                    result = await err_db.execute(
                        select(RawArtifact).where(RawArtifact.id == artifact_id)
                    )
                    artifact = result.scalar_one_or_none()
                    if artifact:
                        artifact.status = ArtifactStatus.PARSE_FAILED
                        artifact.status_reason = f"Unexpected error: {type(e).__name__}: {str(e)[:500]}"
                        await err_db.commit()
                logger.error(
                    "parse_failed_unexpected",
                    artifact_id=artifact_id,
                    case_id=case_id,
                    exc_info=True,
                )
                raise self.retry(exc=e)

    from app.tasks.runner import run_async
    run_async(_run)
