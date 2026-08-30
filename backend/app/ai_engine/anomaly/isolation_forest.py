import numpy as np
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_engine.explainability.shap_explainer import explain_anomaly
from app.db.models.base_models import Anomaly, LogEvent

logger = structlog.get_logger()

MODEL_NAME = "isolation_forest"
MODEL_VERSION = "isolation_forest_v1"


async def detect_anomalies(case_id: str, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(LogEvent).where(LogEvent.case_id == case_id).order_by(LogEvent.timestamp)
    )
    events = result.scalars().all()

    if len(events) < 5:
        logger.info(
            "insufficient_events_for_anomaly_detection",
            case_id=case_id,
            count=len(events),
        )
        return []

    features, event_ids, feature_names = _extract_features(events)
    if features.shape[0] < 5:
        return []

    scores = _run_isolation_forest(features)

    anomalies_found = []
    threshold = np.percentile(scores, 85)

    for i, (score, event_id) in enumerate(zip(scores, event_ids)):
        if score > threshold:
            event = events[i] if i < len(events) else None
            severity = _score_to_severity(score, threshold)
            category = _categorize_anomaly(event, features[i], feature_names)

            explanation = explain_anomaly(
                model_name=MODEL_NAME,
                feature_names=feature_names,
                feature_values=features[i].tolist(),
                score=float(score),
                threshold=float(threshold),
            )

            anomaly_data = {
                "event_ids": [str(event_id)],
                "score": float(score),
                "severity": severity,
                "category": category,
                "model_name": MODEL_NAME,
                "model_version": MODEL_VERSION,
                "explanation": explanation,
            }
            anomalies_found.append(anomaly_data)

    # Persist anomalies
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
        "anomaly_detection_complete",
        case_id=case_id,
        total_events=len(events),
        anomalies_found=len(anomalies_found),
    )

    return anomalies_found


def _extract_features(events: list) -> tuple[np.ndarray, list, list[str]]:
    feature_names = [
        "hour_of_day",
        "is_weekend",
        "action_risk_score",
        "has_ip",
        "has_file_hash",
        "event_count_same_hour",
        "bytes_numeric",
    ]

    # Compute per-event features
    hourly_counts = {}
    for event in events:
        if event.timestamp:
            h = event.timestamp.hour
            hourly_counts[h] = hourly_counts.get(h, 0) + 1

    features = []
    event_ids = []

    action_risk = {
        "file_transfer": 0.8,
        "usb_transfer": 0.9,
        "bluetooth_transfer": 0.85,
        "email_sent": 0.6,
        "process_start": 0.5,
        "network_connection": 0.4,
        "privilege_escalation": 0.95,
        "software_install": 0.7,
        "download_complete": 0.6,
        "file_write": 0.3,
        "file_delete": 0.5,
        "error": 0.4,
        "warning": 0.3,
    }

    for event in events:
        hour = event.timestamp.hour if event.timestamp else 12
        is_weekend = 1.0 if event.timestamp and event.timestamp.weekday() >= 5 else 0.0
        action_score = action_risk.get(event.action, 0.2)
        has_ip = 1.0 if event.ip_address else 0.0
        has_hash = 1.0 if event.file_hash else 0.0
        same_hour_count = hourly_counts.get(hour, 0) / max(len(events), 1)

        features.append(
            [
                hour / 23.0,
                is_weekend,
                action_score,
                has_ip,
                has_hash,
                same_hour_count,
                0.0,
            ]
        )
        event_ids.append(event.id)

    return np.array(features), event_ids, feature_names


def _run_isolation_forest(features: np.ndarray) -> np.ndarray:
    try:
        from sklearn.ensemble import IsolationForest  # noqa: PLC0415

        model = IsolationForest(
            n_estimators=100,
            contamination=0.15,
            random_state=42,
            n_jobs=-1,
        )
        raw_scores = model.fit(features).score_samples(features)
        # Normalize: more negative = more anomalous → higher score
        normalized = -raw_scores
        normalized = (normalized - normalized.min()) / (normalized.max() - normalized.min() + 1e-10)
        return normalized
    except Exception:
        # Fallback: simple statistical anomaly detection
        means = features.mean(axis=0)
        stds = features.std(axis=0) + 1e-10
        z_scores = np.abs((features - means) / stds)
        return z_scores.mean(axis=1)


def _score_to_severity(score: float, threshold: float) -> str:
    if score > threshold * 2.0:
        return "critical"
    elif score > threshold * 1.5:
        return "high"
    elif score > threshold * 1.2:
        return "medium"
    return "low"


def _categorize_anomaly(event, features, feature_names: list[str]) -> str:
    if event:
        lower_action = event.action.lower() if event.action else ""
        if "usb" in lower_action or "bluetooth" in lower_action:
            return "suspicious_transfer"
        elif "process" in lower_action:
            return "suspicious_process"
        elif "network" in lower_action or "connection" in lower_action:
            return "unusual_network"
        elif "install" in lower_action:
            return "unauthorized_install"
        elif "privilege" in lower_action:
            return "privilege_escalation"
        elif "email" in lower_action:
            return "suspicious_email"

    if features[1] > 0.5:
        return "off_hours_activity"
    if features[3] > 0.5:
        return "network_anomaly"
    return "general_anomaly"
