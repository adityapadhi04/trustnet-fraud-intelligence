"""
TRUSTNET - Alert and Report API Integration Test Suite
Verifies alert creation, severity rules, status updates, query filtering, and analytics compilation.
"""

import os
import json
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.routes.alerts import (
    calculate_severity,
    add_alert_for_transaction,
    AlertsStore,
    _db_lock
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_test_alerts():
    """Fixture to clean up test alert IDs in the JSON store before and after each test."""
    from backend.app.routes.alerts import AlertsStore, _db_lock
    # Clean up test keys
    def clean():
        with _db_lock:
            db = AlertsStore.load_all()
            keys_to_remove = [k for k in db.keys() if k.startswith("ALT-TEST_TX_")]
            if keys_to_remove:
                for k in keys_to_remove:
                    del db[k]
                AlertsStore.save_all(db)
    clean()
    yield
    clean()


def test_severity_calculation():
    """Verify that severity maps to the correct risk score range."""
    assert calculate_severity(90.0) == "CRITICAL"
    assert calculate_severity(80.0) == "CRITICAL"
    assert calculate_severity(75.5) == "HIGH"
    assert calculate_severity(60.0) == "HIGH"
    assert calculate_severity(55.0) == "MEDIUM"
    assert calculate_severity(40.0) == "MEDIUM"
    assert calculate_severity(30.0) == "LOW"


def test_alert_creation_and_details():
    """Verify alert creation and direct detail queries, including missing key lookups."""
    tx_id = "TEST_TX_9999"
    risk_factors = []
    network_intel = {"mule_risk": 50.0, "network_risk": 20.0}

    alert = add_alert_for_transaction(
        transaction_id=tx_id,
        risk_score=85.0,
        risk_level="CRITICAL",
        risk_factors=risk_factors,
        network_intel=network_intel,
        fraud_prob=0.9,
        anomaly_score=0.1,
        created_at="2026-08-01 12:00:00"
    )

    assert alert["transaction_id"] == tx_id
    assert alert["severity"] == "CRITICAL"
    assert alert["risk_score"] == 85.0
    assert alert["alert_type"] == "POTENTIAL_MULE"

    # Query details via API
    response = client.get(f"/api/v1/alerts/ALT-{tx_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["alert_id"] == f"ALT-{tx_id}"
    assert data["status"] == "OPEN"

    # Test 404 for invalid Alert ID
    response = client.get("/api/v1/alerts/ALT-NON_EXISTENT_ALERT")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_alert_status_updates():
    """Verify state transitions and validation constraints on status updates."""
    tx_id = "TEST_TX_9999"
    alert_id = f"ALT-{tx_id}"

    # Create the test alert first
    add_alert_for_transaction(
        transaction_id=tx_id,
        risk_score=85.0,
        risk_level="CRITICAL",
        risk_factors=[],
        network_intel={"mule_risk": 50.0, "network_risk": 20.0},
        fraud_prob=0.9,
        anomaly_score=0.1,
        created_at="2026-08-01 12:00:00"
    )

    # Update to INVESTIGATING
    response = client.patch(f"/api/v1/alerts/{alert_id}", json={"status": "INVESTIGATING"})
    assert response.status_code == 200
    assert response.json()["status"] == "INVESTIGATING"

    # Update to RESOLVED
    response = client.patch(f"/api/v1/alerts/{alert_id}", json={"status": "RESOLVED"})
    assert response.status_code == 200
    assert response.json()["status"] == "RESOLVED"

    # Validate constraint - Reject invalid enum value
    response = client.patch(f"/api/v1/alerts/{alert_id}", json={"status": "INVALID_STATE"})
    assert response.status_code == 422 # Pydantic enum validation failure

    # Validate constraint - 404 for invalid ID update
    response = client.patch("/api/v1/alerts/ALT-NON_EXISTENT_ALERT", json={"status": "RESOLVED"})
    assert response.status_code == 404


def test_alerts_listing_and_filtering():
    """Verify alerts lists can be loaded and filtered on severity/status."""
    response = client.get("/api/v1/alerts")
    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) >= 1

    # Filter by Status
    response = client.get("/api/v1/alerts?status=RESOLVED")
    assert response.status_code == 200
    for a in response.json():
        assert a["status"] == "RESOLVED"

    # Filter by Severity
    response = client.get("/api/v1/alerts?severity=CRITICAL")
    assert response.status_code == 200
    for a in response.json():
        assert a["severity"] == "CRITICAL"


def test_reports_endpoints():
    """Verify Reports stats summary compiles correctly and CSV file downloading works."""
    # Test summary compilation
    response = client.get("/api/v1/reports/summary")
    assert response.status_code == 200
    data = response.json()
    assert "overview_stats" in data
    assert "risk_distribution" in data
    assert "recent_alerts" in data
    assert "top_risk_factors" in data
    assert "network_summary" in data

    # Test download CSV streaming
    response = client.get("/api/v1/reports/download")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "filename=trustnet_alerts_report.csv" in response.headers["content-disposition"]
    assert len(response.text) > 0
    assert "Alert ID,Transaction ID,Severity" in response.text
