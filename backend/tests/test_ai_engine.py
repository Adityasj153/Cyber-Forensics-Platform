"""Test the AI engine components against synthetic scenario data."""
import pytest
import numpy as np
from app.ai_engine.explainability.shap_explainer import (
    explain_anomaly,
    explain_correlation,
    explain_ransomware_detection,
)


def test_explain_anomaly():
    explanation = explain_anomaly(
        model_name="isolation_forest",
        feature_names=["hour_of_day", "is_weekend", "action_risk_score", "has_ip", "has_file_hash"],
        feature_values=[0.8, 0.0, 0.9, 1.0, 1.0],
        score=0.85,
        threshold=0.6,
    )
    assert explanation["type"] in ("shap_explanation", "rule_based_explanation")
    assert "reasons" in explanation
    assert len(explanation["reasons"]) > 0
    assert "feature_importance" in explanation


def test_explain_cross_device_correlation():
    explanation = explain_correlation(
        relation_type="cross_device_file",
        entities={
            "hash": "hash:abc123",
            "devices": ["device:pc1", "device:mobile1"],
            "files": ["file:Q3_financials.xlsx"],
        },
        evidence_count=4,
    )
    assert explanation["type"] == "correlation_explanation"
    assert explanation["relation_type"] == "cross_device_file"
    assert len(explanation["reasons"]) > 0
    assert explanation["evidence_count"] == 4


def test_explain_ransomware_detection():
    chain = [
        {
            "timestamp": "2026-08-21T14:07:00Z",
            "action": "process_start",
            "indicators": ["suspicious_process"],
        },
        {
            "timestamp": "2026-08-21T14:08:00Z",
            "action": "file_write",
            "indicators": ["encryption_activity"],
        },
        {
            "timestamp": "2026-08-21T14:09:00Z",
            "action": "ransom_note_created",
            "indicators": ["ransom_note_created"],
        },
    ]
    explanation = explain_ransomware_detection(
        chain_events=chain,
        total_suspicious=6,
        total_events=15,
    )
    assert explanation["type"] == "ransomware_explanation"
    assert len(explanation["reasons"]) >= 2
    assert "encryption_activity" in explanation["statistics"]["indicator_counts"]
    assert "ransom_note_created" in explanation["statistics"]["indicator_counts"]
    assert explanation["statistics"]["chain_length"] == 3
