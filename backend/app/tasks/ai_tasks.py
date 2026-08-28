import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.tasks.celery_app import celery_app

settings = structlog.get_logger()


async def run_ai_pipeline(case_id: str):
    """Run the full AI pipeline — entity graph, correlation, anomaly detection.

    Extracted from the Celery task so the idempotency fix (advisory lock +
    delete-and-rebuild) has a direct regression test: running this twice for
    the same case must not accumulate duplicate Entity/Edge/Anomaly rows.
    """
    from app.ai_engine.correlation.cross_device import run_cross_device_correlation
    from app.ai_engine.anomaly.isolation_forest import detect_anomalies
    from app.ai_engine.anomaly.ransomware_timeline import detect_ransomware_timeline

    logger = structlog.get_logger()
    logger.info("ai_pipeline_started", case_id=case_id)

    async with async_session_factory() as db:
        try:
            # Serialize AI runs per case (multiple file uploads each trigger
            # their own AI task). A Postgres advisory lock held for this
            # transaction ensures concurrent runs for the same case do not
            # race on the idempotent rebuild below.
            from sqlalchemy import delete, text
            from app.db.models.base_models import Entity, CorrelationEdge, Anomaly
            await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": f"ai:{case_id}"})

            # Reset prior AI outputs for this case (idempotent rebuild). The
            # pipeline recomputes everything from current LogEvents, so
            # re-running must replace old Entity/Edge/Anomaly rows instead of
            # accumulating duplicates.
            await db.execute(delete(Entity).where(Entity.case_id == case_id))
            await db.execute(delete(CorrelationEdge).where(CorrelationEdge.case_id == case_id))
            await db.execute(delete(Anomaly).where(Anomaly.case_id == case_id))
            await db.flush()

            # Run cross-device correlation
            correlation_edges = await run_cross_device_correlation(case_id, db)
            logger.info(
                "correlation_complete",
                case_id=case_id,
                edges=len(correlation_edges),
            )

            # Run general anomaly detection
            general_anomalies = await detect_anomalies(case_id, db)
            logger.info(
                "anomaly_detection_complete",
                case_id=case_id,
                anomalies=len(general_anomalies),
            )

            # Run ransomware-specific detection
            ransomware_anomalies = await detect_ransomware_timeline(case_id, db)
            logger.info(
                "ransomware_detection_complete",
                case_id=case_id,
                ransomware_anomalies=len(ransomware_anomalies),
            )

            await db.commit()

            logger.info(
                "ai_pipeline_complete",
                case_id=case_id,
                total_correlations=len(correlation_edges),
                total_anomalies=len(general_anomalies) + len(ransomware_anomalies),
            )

        except Exception as e:
            await db.rollback()
            logger.error(
                "ai_pipeline_failed",
                case_id=case_id,
                error=str(e),
                exc_info=True,
            )
            # AI failure must not crash — raw data remains viewable
            raise


@celery_app.task(name="tasks.run_ai_correlation", bind=True, max_retries=2)
def run_ai_correlation(self, case_id: str):
    """Async task: run full AI pipeline — entity graph, correlation, anomaly detection."""
    async def _run():
        await run_ai_pipeline(case_id)

    from app.tasks.runner import run_async
    run_async(_run)
