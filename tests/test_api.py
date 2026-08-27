"""
TRUSTNET - Backend API Routing Test Suite
Verifies status codes, CORS headers, model mappings, and request validations.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models_loader import get_transactions_df

client = TestClient(app)


def test_root_endpoint():
    """Verify GET / returns metadata and successful status."""
    response = client.get("/")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["project"] == "TRUSTNET"
    assert json_data["scope"] == "prototype-only"


def test_health_endpoint():
    """Verify GET /health checks dynamic loading flags."""
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "healthy"
    assert "models_loaded" in json_data
    assert "database_connected" in json_data


def test_model_status_endpoint():
    """Verify GET /api/v1/model/status reports features correctly."""
    response = client.get("/api/v1/model/status")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["features_count"] == 11
    assert "amount" in json_data["features"]
    assert "xgboost_loaded" in json_data


def test_cors_headers():
    """Verify CORS headers are returned when Origin is specified."""
    # Test valid origin
    response = client.get("/", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    # Test invalid origin
    response = client.get("/", headers={"Origin": "http://malicious-site.com"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_get_sample_transactions():
    """Verify sample retrieval endpoint respects limit constraints."""
    # Default limit
    response = client.get("/api/v1/transactions/sample")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["source"] == "TRUSTNET_SYNTHETIC_SIMULATION"
    assert json_data["records_returned"] == 10
    assert len(json_data["transactions"]) == 10

    # Custom limit
    response = client.get("/api/v1/transactions/sample?limit=5")
    assert response.status_code == 200
    assert response.json()["records_returned"] == 5

    # Out of bounds limit check (le=100)
    response = client.get("/api/v1/transactions/sample?limit=150")
    assert response.status_code == 422 # Pydantic validation error


def test_get_transaction_by_id_and_404():
    """Verify lookup returns exact synthetic records and raises 404 for unknown IDs."""
    # Search for an existing transaction ID
    df = get_transactions_df()
    if df.empty:
        pytest.skip("Dataset processed features empty or unavailable.")
    
    first_tx_id = str(df.iloc[0]["transaction_id"])
    response = client.get(f"/api/v1/transactions/{first_tx_id}")
    assert response.status_code == 200
    assert response.json()["transaction_id"] == first_tx_id

    # Test 404 Not Found
    response = client.get("/api/v1/transactions/non-existent-uuid-12345")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_post_risk_analysis_valid():
    """Verify POST /api/v1/risk/analyze computes full scoring parameters."""
    valid_request = {
        "amount": 250.0,
        "amount_deviation": 1.1,
        "is_new_device": 0,
        "is_new_ip": 0,
        "location_deviation_km": 0.0,
        "hour_of_day": 12,
        "day_of_week": 3,
        "velocity_1h": 1,
        "velocity_24h": 2,
        "recipient_in_degree": 0,
        "sender_out_degree": 0
    }
    
    response = client.post("/api/v1/risk/analyze", json=valid_request)
    assert response.status_code == 200
    json_data = response.json()
    
    # Assert output schema elements are present
    assert "fraud_probability" in json_data
    assert "anomaly_score" in json_data
    assert "risk_score" in json_data
    assert "risk_level" in json_data
    assert "risk_factors" in json_data
    assert "shap_explanation" in json_data
    
    # Check probability is valid float bounds
    assert 0.0 <= json_data["fraud_probability"] <= 1.0
    # Check risk level classification
    assert json_data["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def test_post_risk_analysis_invalid():
    """Verify validator catches illegal ranges (e.g. negative amount)."""
    invalid_request = {
        "amount": -50.0,  # invalid negative
        "amount_deviation": 1.1,
        "is_new_device": 2,  # invalid (ge=0, le=1)
        "is_new_ip": 0,
        "location_deviation_km": -1.0, # invalid
        "hour_of_day": 25,  # invalid (le=23)
        "day_of_week": 3,
        "velocity_1h": -1, # invalid
        "velocity_24h": 2,
        "recipient_in_degree": 0,
        "sender_out_degree": 0
    }
    response = client.post("/api/v1/risk/analyze", json=invalid_request)
    assert response.status_code == 422
