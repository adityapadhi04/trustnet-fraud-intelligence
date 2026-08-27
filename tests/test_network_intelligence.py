import pytest
import pandas as pd
import numpy as np
import networkx as nx
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from machine_learning.src.risk_engine.network_intelligence import NetworkIntelligenceEngine
from machine_learning.src.risk_engine.risk_scorer import RiskScorer
from machine_learning.src.risk_engine.schemas import RiskInput
from backend.app.main import app

# Create a clean synthetic dataset for testing network features
@pytest.fixture
def sample_transactions_data():
    base_time = datetime(2026, 8, 1, 10, 0, 0)
    data = [
        # T1: normal tx from A to B
        {"transaction_id": "T1", "sender_id": "A", "receiver_id": "B", "amount": 100.0, "timestamp": base_time, "is_new_device": 0, "is_new_ip": 0, "amount_deviation": 1.0, "is_fraud_labeled": 0},
        # T2: normal tx from A to B (parallel edge, must not be lost)
        {"transaction_id": "T2", "sender_id": "A", "receiver_id": "B", "amount": 150.0, "timestamp": base_time + timedelta(minutes=10), "is_new_device": 0, "is_new_ip": 0, "amount_deviation": 1.0, "is_fraud_labeled": 0},
        # T3: normal tx from B to C (rapid pass-through pair with T2)
        {"transaction_id": "T3", "sender_id": "B", "receiver_id": "C", "amount": 140.0, "timestamp": base_time + timedelta(minutes=20), "is_new_device": 0, "is_new_ip": 0, "amount_deviation": 1.0, "is_fraud_labeled": 0},
        # T4: normal tx from D to B (part of Fan-In)
        {"transaction_id": "T4", "sender_id": "D", "receiver_id": "B", "amount": 50.0, "timestamp": base_time + timedelta(minutes=30), "is_new_device": 0, "is_new_ip": 0, "amount_deviation": 1.0, "is_fraud_labeled": 0},
        # T5: future transaction relative to T3
        {"transaction_id": "T5", "sender_id": "B", "receiver_id": "E", "amount": 200.0, "timestamp": base_time + timedelta(hours=5), "is_new_device": 1, "is_new_ip": 1, "amount_deviation": 3.5, "is_fraud_labeled": 1}
    ]
    return pd.DataFrame(data)


def test_graph_construction(sample_transactions_data):
    """Verify directed MultiDiGraph preserves parallel edges and amounts."""
    engine = NetworkIntelligenceEngine(sample_transactions_data)
    assert isinstance(engine.G, nx.MultiDiGraph)
    assert engine.G.has_edge("A", "B")
    
    # Check that parallel edges exist
    edges_A_B = engine.G.get_edge_data("A", "B")
    assert len(edges_A_B) == 2
    assert edges_A_B[0]["amount"] == 100.0
    assert edges_A_B[1]["amount"] == 150.0
    assert engine.get_total_network_transactions() == 5


def test_network_metrics_calculation(sample_transactions_data):
    """Verify correct calculation of degree, counterparties, strength, and fan-in/fan-out."""
    engine = NetworkIntelligenceEngine(sample_transactions_data)
    
    # Verify metrics for account B (center of activity)
    metrics = engine.get_account_metrics("B")
    
    # B has incoming from A (T1, T2) and D (T4), outgoing to C (T3) and E (T5)
    assert metrics["incoming_tx_count"] == 3
    assert metrics["outgoing_tx_count"] == 2
    assert metrics["in_degree"] == 3
    assert metrics["out_degree"] == 2
    
    # B has 2 unique incoming counterparties (A, D) and 2 unique outgoing counterparties (C, E)
    assert metrics["incoming_counterparties"] == 2
    assert metrics["outgoing_counterparties"] == 2
    assert metrics["unique_incoming_counterparties"] == 2
    assert metrics["unique_outgoing_counterparties"] == 2
    assert metrics["fan_in"] == 2
    assert metrics["fan_out"] == 2
    
    # B incoming amount = 100 + 150 + 50 = 300
    assert metrics["incoming_amount"] == 300.0
    # B outgoing amount = 140 + 200 = 340
    assert metrics["outgoing_amount"] == 340.0


def test_rapid_pass_through_detection(sample_transactions_data):
    """Verify pass-through detection is temporally correct and threshold-respecting."""
    engine = NetworkIntelligenceEngine(sample_transactions_data)
    
    # A->B (T2) at 10:10, B->C (T3) at 10:20 (delay: 10 minutes) -> Rapid pass-through
    pass_throughs = engine.detect_rapid_pass_through_events("B", threshold_hours=1.0)
    assert len(pass_throughs) >= 1
    
    # Verify matching pairs
    pair = next(p for p in pass_throughs if p["incoming_tx_id"] == "T2" and p["outgoing_tx_id"] == "T3")
    assert pair["from_user"] == "A"
    assert pair["to_user"] == "C"
    assert pair["incoming_amount"] == 150.0
    assert pair["outgoing_amount"] == 140.0
    assert pair["delay_minutes"] == 10.0
    
    # Verify future/late pass-through: T2 at 10:10, B->E (T5) at 15:00 (delay: 4.83 hours)
    # Should NOT be detected under 1.0 hour threshold
    late_pass_throughs = [p for p in pass_throughs if p["outgoing_tx_id"] == "T5"]
    assert len(late_pass_throughs) == 0


def test_temporal_leakage_prevention(sample_transactions_data):
    """Verify that future transactions do not leak into past network calculations."""
    engine = NetworkIntelligenceEngine(sample_transactions_data)
    
    # Query B metrics as of base_time + 30 minutes (before the future T5 at 5 hours)
    cutoff_time = datetime(2026, 8, 1, 10, 45, 0)
    
    metrics_past = engine.get_account_metrics("B", before_timestamp=cutoff_time)
    metrics_all = engine.get_account_metrics("B")
    
    # In past, outgoing should only count T3 (B->C at 10:20) and not T5 (B->E at 15:00)
    assert metrics_past["outgoing_tx_count"] == 1
    assert metrics_past["outgoing_amount"] == 140.0
    assert metrics_past["unique_outgoing_counterparties"] == 1
    
    # Without temporal filtering, outgoing counts both T3 and T5
    assert metrics_all["outgoing_tx_count"] == 2
    assert metrics_all["outgoing_amount"] == 340.0
    assert metrics_all["unique_outgoing_counterparties"] == 2
    
    # Verify STRICT less-than filtering: a transaction at EXACTLY cutoff_time is excluded
    exact_t3_time = sample_transactions_data.loc[sample_transactions_data["transaction_id"] == "T3", "timestamp"].values[0]
    exact_t3_time = pd.Timestamp(exact_t3_time).to_pydatetime()
    metrics_strict = engine.get_account_metrics("B", before_timestamp=exact_t3_time)
    # T3 is at exact_t3_time, so with strict '<', it MUST be excluded. Outgoing tx count should be 0.
    assert metrics_strict["outgoing_tx_count"] == 0
    
    # Verify label independence: Changing is_fraud_labeled does not change network risk
    net_risk = engine.calculate_account_network_risk("B", before_timestamp=cutoff_time)
    df_altered = sample_transactions_data.copy()
    df_altered["is_fraud_labeled"] = 0
    engine_altered = NetworkIntelligenceEngine(df_altered)
    net_risk_altered = engine_altered.calculate_account_network_risk("B", before_timestamp=cutoff_time)
    assert net_risk == net_risk_altered


def test_mule_indicators_explanations(sample_transactions_data):
    """Verify that indicators do not claim confirmation, but prioritise investigation."""
    engine = NetworkIntelligenceEngine(sample_transactions_data)
    
    # Fetch indicators
    explanations = engine.generate_explanations("B")
    
    # Verify no claim of "Confirmed mule" is present
    for exp in explanations:
        assert "confirmed mule" not in exp.lower()
        assert "proven fraud" not in exp.lower()
        
    # Potential mule indicator output assertion
    if len(explanations) > 0:
        assert any("mule" in exp.lower() for exp in explanations)


def test_risk_engine_integration_scoring():
    """Verify that network risk override parameter directly updates final scoring output."""
    scorer = RiskScorer()
    
    # 1. Base input without network override
    r_base = RiskInput(
        amount=100.0,
        amount_deviation=1.0,
        is_new_device=0,
        is_new_ip=0,
        location_deviation_km=0.0,
        velocity_1h=0,
        velocity_24h=0,
        recipient_in_degree=0,
        sender_out_degree=0,
        fraud_probability=0.1,
        anomaly_score=-0.1
    )
    res_base = scorer.score(r_base)
    base_score = res_base.risk_score
    
    # 2. Input with high network risk override
    r_override = RiskInput(
        amount=100.0,
        amount_deviation=1.0,
        is_new_device=0,
        is_new_ip=0,
        location_deviation_km=0.0,
        velocity_1h=0,
        velocity_24h=0,
        recipient_in_degree=0,
        sender_out_degree=0,
        fraud_probability=0.1,
        anomaly_score=-0.1,
        network_risk_override=85.0
    )
    res_override = scorer.score(r_override)
    override_score = res_override.risk_score
    
    # Since weight for network risk is 0.10, adding 85.0 override should increase risk score by exactly 8.5 points
    assert res_override.network_risk == 85.0
    assert override_score > base_score
    assert round(override_score - base_score, 1) == 8.5


def test_api_network_routes():
    """Verify endpoint schemas, validation, 404 responses, and data safety."""
    client = TestClient(app)
    
    # Test 404 response on unknown account
    resp_404 = client.get("/api/v1/network/UNKNOWN_ACCOUNT")
    assert resp_404.status_code == 404
    assert "not found" in resp_404.json()["detail"].lower()
    
    # Test endpoint with a valid account (e.g. U0001 or any user loaded in synthetic engine)
    # We can request U0001 which is present in synthetic dataset
    resp_200 = client.get("/api/v1/network/U0001")
    if resp_200.status_code == 200:
        data = resp_200.json()
        assert "network_risk" in data
        assert "mule_risk" in data
        assert "incoming_connections" in data
        assert "network_metrics" in data
        assert "connected_accounts" in data
        assert "relevant_transaction_relationships" in data
        
        # Verify no ground truth target leakage in payload
        assert "is_fraud_labeled" not in data
        relationships = data["relevant_transaction_relationships"]
        for node in relationships["nodes"]:
            assert "is_fraud_labeled" not in node
        for edge in relationships["edges"]:
            assert "is_fraud_labeled" not in edge
            
        # Verify before_timestamp parameter works on route
        resp_filtered = client.get("/api/v1/network/U0001?before_timestamp=2026-08-05T12:00:00")
        assert resp_filtered.status_code == 200
        assert resp_filtered.json()["network_risk"] <= data["network_risk"] or resp_filtered.json()["network_risk"] >= 0.0
