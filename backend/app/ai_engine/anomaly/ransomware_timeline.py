import structlog
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.base_models import LogEvent, Anomaly
from app.ai_engine.explainability.shap_explainer import explain_ransomware_detection

logger = structlog.get_logger()

MODEL_NAME = "ransomware_detector"
MODEL_VERSION = "ransomware_detector_v1"

RANSOMWARE_INDICATORS = {
    "process_start": ["encrypt", "cipher", "lock", "decrypt", "bitcoin", "wallet"],
    "file_write": [".locked", ".encrypted", ".crypto", ".crypt", ".enc"],
    "network_connection": ["tor", "onion", "bitcoin", "wallet", "ransom"],
    "file_delete": ["shadow", "backup", "volume"],
    "ransom_note_created": ["readme", "decrypt", "ransom", "bitcoin", "restore"],
}

SEVERITY_WEIGHTS = {
    "ransom_note_created": 1.0,
    "encryption_activity": 0.95,
    "suspicious_process": 0.85,
    "network_c2": 0.8,
    "shadow_copy_deletion": 0.9,
    "suspicious_file_write": 0.7,
}


async def detect_ransomware_timeline(case_id: str, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(LogEvent).where(LogEvent.case_id == case_id).order_by(LogEvent.timestamp)
    )
    events = result.scalars().all()

    if not events:
        return []

    timeline_events = []
    anomalies_found = []

    for event in events:
        indicators = _check_ransomware_indicators(event)
        if indicators:
            timeline_events.append({
                "event_id": str(event.id),
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                "action": event.action,
                "object": event.object,
                "indicators": indicators,
                "severity_weight": max(SEVERITY_WEIGHTS.get(ind, 0.5) for ind in indicators),
            })

    if not timeline_events:
        return []

    # Group by time windows (30 seconds)
    chains = _build_event_chains(timeline_events)

    for chain in chains:
        if len(chain) >= 2:
            severity = _chain_severity(chain)
            explanation = explain_ransomware_detection(
                chain_events=chain,
                total_suspicious=len(timeline_events),
                total_events=len(events),
            )

            event_ids = [e["event_id"] for e in chain]

            anomaly_data = {
                "event_ids": event_ids,
                "score": chain[-1]["severity_weight"],
                "severity": severity,
                "category": "ransomware",
                "model_name": MODEL_NAME,
                "model_version": MODEL_VERSION,
                "explanation": explanation,
            }
            anomalies_found.append(anomaly_data)

    # Persist
    for a_data in anomalies_found:
        anomaly = Anomaly(
            case_id=case_id,
            event_ids=a_data["event_ids"],
            score=a_data["score"],
            severity=a_data["severity"],
            category=a_data["category"],
            model_name=a_data["model_name"],
            model_version=a_data["model_version"],
            explanation_json=a_data["explanation"],
        )
        db.add(anomaly)

    await db.flush()

    logger.info(
        "ransomware_detection_complete",
        case_id=case_id,
        suspicious_events=len(timeline_events),
        chains_detected=len(chains),
        anomalies_created=len(anomalies_found),
    )

    return anomalies_found


def _check_ransomware_indicators(event: LogEvent) -> list[str]:
    indicators = []
    lower_action = (event.action or "").lower()
    lower_object = (event.object or "").lower()
    lower_detail = (event.detail or "").lower()
    combined = f"{lower_action} {lower_object} {lower_detail}"

    if "ransom" in combined or "decrypt" in combined or "readme" in combined:
        indicators.append("ransom_note_created")

    if any(ext in combined for ext in [".locked", ".encrypted", ".crypto", ".crypt", ".enc"]):
        indicators.append("encryption_activity")

    if "encrypt" in combined or "cipher" in combined or "lock" in combined:
        indicators.append("suspicious_process")

    if "shadow" in combined or "backup" in combined and "delet" in combined:
        indicators.append("shadow_copy_deletion")

    if "tor" in combined or "onion" in combined or "bitcoin" in combined:
        indicators.append("network_c2")

    if "process" in lower_action and any(word in combined for word in ["encrypt", "cipher", "lock"]):
        indicators.append("suspicious_file_write")

    return indicators


def _build_event_chains(timeline_events: list[dict]) -> list[list[dict]]:
    if not timeline_events:
        return []

    chains = []
    current_chain = [timeline_events[0]]

    for i in range(1, len(timeline_events)):
        prev_ts = datetime.fromisoformat(timeline_events[i - 1]["timestamp"].replace("Z", "+00:00"))
        curr_ts = datetime.fromisoformat(timeline_events[i]["timestamp"].replace("Z", "+00:00"))
        diff = (curr_ts - prev_ts).total_seconds()

        if diff <= 120:
            current_chain.append(timeline_events[i])
        else:
            if len(current_chain) >= 2:
                chains.append(current_chain)
            current_chain = [timeline_events[i]]

    if len(current_chain) >= 2:
        chains.append(current_chain)

    return chains


def _chain_severity(chain: list[dict]) -> str:
    max_weight = max(e["severity_weight"] for e in chain)
    indicator_types = set()
    for e in chain:
        indicator_types.update(e["indicators"])

    if "ransom_note_created" in indicator_types and max_weight > 0.9:
        return "critical"
    if "encryption_activity" in indicator_types:
        return "critical"
    if max_weight > 0.85 and len(chain) >= 3:
        return "high"
    if max_weight > 0.7:
        return "medium"
    return "low"
