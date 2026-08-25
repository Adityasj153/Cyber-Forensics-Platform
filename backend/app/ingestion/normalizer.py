from datetime import datetime, timezone
from uuid import uuid4

from app.ingestion.parsers.base import ParsedEvent


def normalize_events(
    case_id: str,
    device_id: str | None,
    artifact_id: str,
    events: list[ParsedEvent],
) -> list[dict]:
    normalized = []
    for event in events:
        normalized.append({
            "id": str(uuid4()),
            "case_id": case_id,
            "device_id": device_id,
            "artifact_id": artifact_id,
            "timestamp": event.timestamp or datetime.now(timezone.utc),
            "source_type": event.source_type,
            "actor": event.actor,
            "action": event.action,
            "object": event.object,
            "ip_address": event.ip_address,
            "file_hash": event.file_hash,
            "detail": event.detail,
            "raw_line": event.raw_line,
        })
    return normalized
