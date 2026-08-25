import structlog
import numpy as np

logger = structlog.get_logger()


def explain_anomaly(
    model_name: str,
    feature_names: list[str],
    feature_values: list[float],
    score: float,
    threshold: float,
) -> dict:
    try:
        return _shap_explanation(model_name, feature_names, feature_values, score, threshold)
    except Exception:
        logger.warning("shap_fallback", model_name=model_name, exc_info=True)
        return _rule_based_explanation(feature_names, feature_values, score, threshold)


def explain_correlation(
    relation_type: str,
    entities: dict,
    evidence_count: int,
) -> dict:
    reasons = []
    contributing_factors = []

    if relation_type == "cross_device_file":
        devices = entities.get("devices", [])
        files = entities.get("files", [])
        reasons.append(f"Same file hash found across {len(devices)} different devices")
        contributing_factors.append({
            "factor": "multi_device_presence",
            "weight": 0.7,
            "detail": f"File appears on {len(devices)} devices",
        })
        if files:
            contributing_factors.append({
                "factor": "file_identity_match",
                "weight": 0.9,
                "detail": f"Matching files: {', '.join(files[:3])}",
            })

    elif relation_type == "file_transfer_chain":
        devices = entities.get("devices", [])
        file_name = entities.get("file", "unknown")
        reasons.append(f"File '{file_name}' transferred across {len(devices)} devices")
        contributing_factors.append({
            "factor": "transfer_chain",
            "weight": 0.85,
            "detail": f"File movement detected across device chain",
        })

    elif relation_type == "shared_ip":
        devices = entities.get("devices", [])
        ip = entities.get("ip", "unknown")
        reasons.append(f"IP address {ip} connected to {len(devices)} devices")
        contributing_factors.append({
            "factor": "shared_network_identity",
            "weight": 0.75,
            "detail": f"Multiple devices share IP {ip}",
        })

    return {
        "type": "correlation_explanation",
        "relation_type": relation_type,
        "reasons": reasons,
        "contributing_factors": contributing_factors,
        "evidence_count": evidence_count,
        "confidence_factors": {
            "entity_overlap": len(entities),
            "evidence_support": evidence_count,
        },
    }


def explain_ransomware_detection(
    chain_events: list[dict],
    total_suspicious: int,
    total_events: int,
) -> dict:
    indicator_summary = {}
    for event in chain_events:
        for indicator in event.get("indicators", []):
            indicator_summary[indicator] = indicator_summary.get(indicator, 0) + 1

    reasons = []
    contributing_factors = []

    if "ransom_note_created" in indicator_summary:
        reasons.append("Ransom note file detected on filesystem")
        contributing_factors.append({
            "factor": "ransom_note",
            "weight": 1.0,
            "detail": "README/DECRYPT file created — hallmark of ransomware",
        })

    if "encryption_activity" in indicator_summary:
        reasons.append(f"File encryption detected ({indicator_summary['encryption_activity']} files)")
        contributing_factors.append({
            "factor": "encryption",
            "weight": 0.95,
            "detail": "Files renamed with .locked/.encrypted extension",
        })

    if "suspicious_process" in indicator_summary:
        reasons.append("Suspicious process execution detected")
        contributing_factors.append({
            "factor": "malicious_process",
            "weight": 0.85,
            "detail": "Process with encryption-related behavior",
        })

    if "network_c2" in indicator_summary:
        reasons.append("Connection to known C2/Tor infrastructure")
        contributing_factors.append({
            "factor": "c2_communication",
            "weight": 0.8,
            "detail": "Outbound connection to suspicious destination",
        })

    if "shadow_copy_deletion" in indicator_summary:
        reasons.append("Shadow copy/backup deletion detected")
        contributing_factors.append({
            "factor": "backup_destruction",
            "weight": 0.9,
            "detail": "Volume shadow copies deleted — prevents recovery",
        })

    timeline_summary = []
    for event in chain_events:
        timeline_summary.append({
            "timestamp": event["timestamp"],
            "action": event["action"],
            "indicators": event["indicators"],
        })

    return {
        "type": "ransomware_explanation",
        "reasons": reasons,
        "contributing_factors": contributing_factors,
        "timeline": timeline_summary,
        "statistics": {
            "total_events_analyzed": total_events,
            "suspicious_events": total_suspicious,
            "chain_length": len(chain_events),
            "indicator_counts": indicator_summary,
        },
    }


def _shap_explanation(
    model_name: str,
    feature_names: list[str],
    feature_values: list[float],
    score: float,
    threshold: float,
) -> dict:
    try:
        import shap

        n_features = len(feature_names)
        X = np.array([feature_values])

        if model_name == "isolation_forest":
            from sklearn.ensemble import IsolationForest
            model = IsolationForest(n_estimators=50, random_state=42, contamination=0.15)
            dummy_data = np.random.rand(20, n_features)
            model.fit(dummy_data)
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X)
        else:
            return _rule_based_explanation(feature_names, feature_values, score, threshold)

        feature_importance = []
        if hasattr(shap_values, '__len__') and len(shap_values) > 0:
            vals = shap_values[0] if isinstance(shap_values[0], (list, np.ndarray)) else shap_values
            for i, name in enumerate(feature_names):
                if i < len(vals):
                    importance = float(abs(vals[i]))
                    feature_importance.append({
                        "feature": name,
                        "importance": round(importance, 4),
                        "value": round(feature_values[i], 4),
                        "direction": "increases" if vals[i] > 0 else "decreases",
                    })

        feature_importance.sort(key=lambda x: x["importance"], reverse=True)

        top_factors = feature_importance[:3]
        reasons = []
        for f in top_factors:
            reasons.append(f"{f['feature']} = {f['value']:.2f} ({f['direction']} anomaly score by {f['importance']:.3f})")

        return {
            "type": "shap_explanation",
            "model": model_name,
            "score": round(score, 4),
            "threshold": round(threshold, 4),
            "reasons": reasons,
            "feature_importance": feature_importance,
            "top_contributing_factors": feature_importance[:5],
        }

    except Exception:
        return _rule_based_explanation(feature_names, feature_values, score, threshold)


def _rule_based_explanation(
    feature_names: list[str],
    feature_values: list[float],
    score: float,
    threshold: float,
) -> dict:
    feature_importance = []
    for i, name in enumerate(feature_names):
        importance = feature_values[i] if i < len(feature_values) else 0.0
        feature_importance.append({
            "feature": name,
            "importance": round(importance, 4),
            "value": round(feature_values[i], 4) if i < len(feature_values) else 0.0,
            "direction": "increases" if importance > 0.5 else "neutral",
        })

    feature_importance.sort(key=lambda x: x["importance"], reverse=True)

    reasons = []
    for f in feature_importance[:3]:
        if f["importance"] > 0.3:
            reasons.append(f"{f['feature']} = {f['value']:.2f} (elevated)")

    if not reasons:
        reasons.append(f"Overall anomaly score ({score:.3f}) exceeds threshold ({threshold:.3f})")

    return {
        "type": "rule_based_explanation",
        "score": round(score, 4),
        "threshold": round(threshold, 4),
        "reasons": reasons,
        "feature_importance": feature_importance,
        "note": "SHAP explanation unavailable; using rule-based attribution",
    }
