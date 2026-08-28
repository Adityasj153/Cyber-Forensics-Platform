"""Regression tests for the five pipeline bugs found during Scenario 1 E2E.

Covered, matching each bug fixed in the session:

  Bug #1 - The Celery worker must actually register tasks.parse_log_file and
           tasks.run_ai_correlation (previously registered zero tasks because
           autodiscover_tasks found no modules to import).
  Bug #2 - runner.run_async() must run the coroutine AND dispose the loop-bound
           engine, so a stale asyncpg pool is never reused across Celery
           prefork loops ("Future attached to a different loop").
  Bug #3 - parse_log_file must persist LogEvent rows to Postgres (previously
           they were only ES-indexed, so the AI engine saw nothing).
  Bug #4 - Re-running run_ai_pipeline for the same case must be idempotent
           (advisory lock + delete-rebuild) and not accumulate duplicate
           Entity/CorrelationEdge/Anomaly rows.
  Bug #5 - The search endpoint's size cap must stay >= what the frontend
           timeline requests (500); a cap of 200 previously caused HTTP 422
           and an empty timeline.

Notes on the DB-backed tests: pytest-asyncio (this version) runs each async
test in its own event loop. The global SQLAlchemy engine is loop-bound, so
each test disposes the engine when finished to force a fresh pool in the next
test's loop, avoiding "Future attached to a different loop".
"""
import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, func, select

import app.main
import app.tasks.ingestion_tasks
import app.tasks.ai_tasks
from app.tasks.celery_app import celery_app
from app.tasks.runner import run_async
from app.tasks.ingestion_tasks import persist_log_events
from app.tasks.ai_tasks import run_ai_pipeline
from app.db.session import async_session_factory, engine
from app.db.models.base_models import (
    User,
    UserRole,
    Case,
    Device,
    RawArtifact,
    ArtifactStatus,
    LogEvent,
    Entity,
    CorrelationEdge,
    Anomaly,
)

pytestmark = pytest.mark.asyncio

PC = "windows_evtx"


# --------------------------------------------------------------------------- #
# Bug #1 - Celery task registration
# --------------------------------------------------------------------------- #
async def test_celery_registers_parse_and_ai_tasks():
    names = set(celery_app.tasks.keys())
    assert "tasks.parse_log_file" in names, "tasks.parse_log_file not registered"
    assert "tasks.run_ai_correlation" in names, "tasks.run_ai_correlation not registered"


# --------------------------------------------------------------------------- #
# Bug #2 - runner disposes the engine after each run (fresh loop reuse)
# --------------------------------------------------------------------------- #
async def test_run_async_runs_coro_and_disposes_engine():
    import app.tasks.runner as runner_mod

    class FakeEngine:
        def __init__(self):
            self.disposed = []

        async def dispose(self):
            self.disposed.append(True)

    fake_engine = FakeEngine()
    ran = []

    async def coro():
        ran.append(True)

    original_engine = runner_mod.engine
    runner_mod.engine = fake_engine
    try:
        # run_async uses asyncio.run() which needs a fresh event loop; invoke it
        # from a worker thread since we are already inside the pytest loop.
        await asyncio.to_thread(run_async, coro)
    finally:
        runner_mod.engine = original_engine

    assert ran == [True], "coroutine should have been executed"
    assert fake_engine.disposed == [True], "engine must be disposed after the run"


# --------------------------------------------------------------------------- #
# Helpers for the DB-backed tests
# --------------------------------------------------------------------------- #
async def _seed_case() -> dict:
    """Create a User + Case + 2 Devices + a RawArtifact; return their ids."""
    async with async_session_factory() as db:
        user = User(
            username=f"reg_{uuid.uuid4().hex[:10]}",
            email=f"reg_{uuid.uuid4().hex[:10]}@example.com",
            hashed_password="not-a-real-hash",
            role=UserRole.INVESTIGATOR,
        )
        db.add(user)
        await db.flush()

        case = Case(name="regression-case", created_by=user.id)
        db.add(case)
        await db.flush()

        dev1 = Device(case_id=case.id, device_type="pc", name="PC-A")
        dev2 = Device(case_id=case.id, device_type="mobile", name="MOB-B")
        db.add_all([dev1, dev2])
        await db.flush()

        artifact = RawArtifact(
            case_id=case.id,
            device_id=dev1.id,
            filename="scenario_pc.txt",
            sha256="a" * 64,
            storage_path="regression/pc.txt",
            uploaded_by=user.id,
            status=ArtifactStatus.PARSED,
        )
        db.add(artifact)
        await db.commit()

        return {
            "user_id": user.id,
            "case_id": case.id,
            "dev1": dev1.id,
            "dev2": dev2.id,
            "artifact_id": artifact.id,
        }


async def _cleanup(ids: dict):
    async with async_session_factory() as db:
        await db.execute(delete(Case).where(Case.id == ids["case_id"]))
        await db.execute(delete(User).where(User.id == ids["user_id"]))
        await db.commit()


async def _count(db, model, case_id) -> int:
    result = await db.execute(
        select(func.count()).select_from(model).where(model.case_id == case_id)
    )
    return result.scalar_one()


# --------------------------------------------------------------------------- #
# Bug #3 - LogEvent persistence to Postgres (AI engine source of truth)
# --------------------------------------------------------------------------- #
async def test_persist_log_events_writes_logevent_rows():
    ids = await _seed_case()
    normalized = [
        {
            "id": str(uuid.uuid4()),
            "case_id": str(ids["case_id"]),
            "device_id": str(ids["dev1"]),
            "artifact_id": str(ids["artifact_id"]),
            "timestamp": datetime(2026, 8, 20, 9, 14, 0, tzinfo=timezone.utc),
            "source_type": PC,
            "actor": None,
            "action": "usb_transfer",
            "object": "Q3_financials.xlsx",
            "ip_address": None,
            "file_hash": None,
            "detail": "copied to USB",
            "raw_line": "raw line",
        },
        {
            "id": str(uuid.uuid4()),
            "case_id": str(ids["case_id"]),
            "device_id": str(ids["dev2"]),
            "artifact_id": str(ids["artifact_id"]),
            "timestamp": datetime(2026, 8, 20, 9, 30, 0, tzinfo=timezone.utc),
            "source_type": "android_logcat",
            "actor": None,
            "action": "email_sent",
            "object": "Q3_financials.xlsx",
            "ip_address": "203.0.113.42",
            "file_hash": None,
            "detail": None,
            "raw_line": "raw line",
        },
    ]

    try:
        case_id = ids["case_id"]
        async with async_session_factory() as db:
            written = await persist_log_events(db, normalized)
            assert written == 2
            await db.commit()

            result = await db.execute(
                select(LogEvent)
                .where(LogEvent.case_id == case_id)
                .order_by(LogEvent.timestamp)
            )
            rows = result.scalars().all()

        assert len(rows) == 2, "LogEvent rows must be persisted to Postgres"
        assert {r.action for r in rows} == {"usb_transfer", "email_sent"}
        assert {r.device_id for r in rows} == {ids["dev1"], ids["dev2"]}
        assert all(r.object == "Q3_financials.xlsx" for r in rows)
        assert any(r.source_type == PC for r in rows)
    finally:
        await _cleanup(ids)
        await engine.dispose()


# --------------------------------------------------------------------------- #
# Bug #4 - AI pipeline idempotency (no duplicate Entity/Edge/Anomaly rows)
# --------------------------------------------------------------------------- #
async def test_ai_pipeline_is_idempotent_across_re_runs():
    ids = await _seed_case()
    case_id = ids["case_id"]

    events = [
        # device 1 (PC)
        ("usb_transfer", "Q3_financials.xlsx", None, ids["dev1"], "2026-08-20 09:14:00"),
        ("email_sent", "Q3_financials.xlsx", "203.0.113.42", ids["dev1"], "2026-08-20 09:30:00"),
        ("network_connection", "edge-router", "203.0.113.42", ids["dev1"], "2026-08-20 09:45:00"),
        # device 2 (mobile)
        ("file_received", "Q3_financials.xlsx", None, ids["dev2"], "2026-08-20 09:17:00"),
        ("bluetooth_transfer", "Q3_financials.xlsx", None, ids["dev2"], "2026-08-20 09:22:00"),
        ("email_sent", "Q3_financials.xlsx", "203.0.113.42", ids["dev2"], "2026-08-20 09:40:00"),
    ]

    try:
        async with async_session_factory() as db:
            for action, obj, ip, device_id, ts in events:
                db.add(
                    LogEvent(
                        id=uuid.uuid4(),
                        case_id=case_id,
                        device_id=device_id,
                        artifact_id=ids["artifact_id"],
                        timestamp=datetime.fromisoformat(ts).replace(tzinfo=timezone.utc),
                        source_type=PC,
                        actor=None,
                        action=action,
                        object=obj,
                        ip_address=ip,
                        file_hash=None,
                        detail=None,
                        raw_line="raw",
                    )
                )
            await db.commit()

        await run_ai_pipeline(case_id)

        async with async_session_factory() as db:
            entities_1 = await _count(db, Entity, case_id)
            edges_1 = await _count(db, CorrelationEdge, case_id)
            anomalies_1 = await _count(db, Anomaly, case_id)

        assert entities_1 > 0, "AI pipeline should have produced entities"

        # Re-run the same pipeline for the same case
        await run_ai_pipeline(case_id)

        async with async_session_factory() as db:
            entities_2 = await _count(db, Entity, case_id)
            edges_2 = await _count(db, CorrelationEdge, case_id)
            anomalies_2 = await _count(db, Anomaly, case_id)

        # The delete-and-rebuild must keep counts identical, not doubled.
        assert entities_2 == entities_1, (
            f"Entities must not duplicate on re-run: {entities_1} -> {entities_2}"
        )
        assert edges_2 == edges_1, f"Edges must not duplicate on re-run: {edges_1} -> {edges_2}"
        assert anomalies_2 == anomalies_1, (
            f"Anomalies must not duplicate on re-run: {anomalies_1} -> {anomalies_2}"
        )

        # Sanity: at least one edge should exist (shared file across two devices)
        assert edges_1 >= 1, "expected a cross-device file_transfer_chain edge"
    finally:
        await _cleanup(ids)
        await engine.dispose()


# --------------------------------------------------------------------------- #
# Bug #5 - search size cap must allow the frontend's 500-event timeline request
# --------------------------------------------------------------------------- #
async def test_search_size_cap_allows_timeline_request():
    schema = app.main.app.openapi()
    path = schema["paths"]["/api/cases/{case_id}/search"]
    get_op = path["get"]
    size_params = [
        p for p in get_op["parameters"] if p.get("name") == "size" and p.get("in") == "query"
    ]
    assert size_params, "search endpoint must expose a size query parameter"

    maximum = size_params[0]["schema"].get("maximum")
    assert maximum is not None and maximum >= 500, (
        f"search size maximum ({maximum}) must be >= 500 (frontend timeline requests 500)"
    )
