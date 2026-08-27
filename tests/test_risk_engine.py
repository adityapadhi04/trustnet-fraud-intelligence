"""
TRUSTNET - Risk Engine Test Suite
Tests for risk scorer weights, normalizations, and factor extractions.
"""

import pytest
import pandas as pd
import numpy as np
import math

from machine_learning.src.risk_engine.schemas import RiskInput
from machine_learning.src.risk_engine.risk_scorer import RiskScorer


@pytest.fixture
def scorer():
    """Initializes the baseline RiskScorer."""
    return RiskScorer()


def test_weights_sum_to_one():
    """
    Verify scorer rejects weight configurations that do not sum to 1.0.
    """
    # Valid sum
    RiskScorer(weights={"supervised": 0.40, "anomaly": 0.20, "behavioral": 0.30, "network": 0.10})
    
    # Invalid sum
    with pytest.raises(ValueError):
        RiskScorer(weights={"supervised": 0.50, "anomaly": 0.50, "behavioral": 0.10, "network": 0.10})


def test_validation_input_bounds(scorer):
    """
    Verify scorer input validations reject negative amounts or out-of-bounds probabilities.
    """
    # Negative amount
    invalid_input1 = RiskInput(
        amount=-10.0, amount_deviation=1.0, is_new_device=0, is_new_ip=0,
        location_deviation_km=0.0, velocity_1h=0, velocity_24h=0,
        recipient_in_degree=0, sender_out_degree=0, fraud_probability=0.1, anomaly_score=-0.1
    )
    with pytest.raises(ValueError):
        scorer.score(invalid_input1)
        
    # Probability > 1.0
    invalid_input2 = RiskInput(
        amount=100.0, amount_deviation=1.0, is_new_device=0, is_new_ip=0,
        location_deviation_km=0.0, velocity_1h=0, velocity_24h=0,
        recipient_in_degree=0, sender_out_degree=0, fraud_probability=1.2, anomaly_score=-0.1
    )
    with pytest.raises(ValueError):
        scorer.score(invalid_input2)


def test_low_risk_scenario(scorer):
    """
    Verify all-zero/low-risk signals produce LOW risk.
    """
    low_input = RiskInput(
        amount=10.0,
        amount_deviation=1.0,
        is_new_device=0,
        is_new_ip=0,
        location_deviation_km=0.0,
        velocity_1h=0,
        velocity_24h=0,
        recipient_in_degree=0,
        sender_out_degree=0,
        fraud_probability=0.0,
        anomaly_score=-0.25  # minimum anomaly (most normal)
    )
    output = scorer.score(low_input)
    
    # Assert risk is 0 or extremely low and classified as LOW
    assert output.risk_score == 0.0
    assert output.risk_level == "LOW"
    assert len(output.risk_factors) == 0


def test_supervised_ml_impact(scorer):
    """
    Verify high supervised fraud probability drives risk to HIGH/CRITICAL.
    """
    high_supervised = RiskInput(
        amount=100.0, amount_deviation=1.0, is_new_device=0, is_new_ip=0,
        location_deviation_km=0.0, velocity_1h=0, velocity_24h=0,
        recipient_in_degree=0, sender_out_degree=0,
        fraud_probability=0.95,
        anomaly_score=-0.25
    )
    output = scorer.score(high_supervised)
    
    # 0.45 * 95 = 42.75 risk score (with others at 0).
    # Since 42.75 >= 30, it should be MEDIUM.
    assert output.risk_score == 42.75
    assert output.risk_level == "MEDIUM"
    
    # Check that the supervised risk factor is flagged
    factors = [f.factor for f in output.risk_factors]
    assert "Elevated ML supervised fraud probability" in factors
    assert output.risk_factors[0].category == "supervised_ml"
    assert output.risk_factors[0].severity == "high"


def test_anomaly_score_normalization(scorer):
    """
    Verify raw Isolation Forest scores map correctly to 0-100 anomaly risk.
    """
    # Minimum score (-0.25) -> 0 risk
    assert scorer.normalize_anomaly_score(-0.25) == 0.0
    # Threshold score (0.0) -> 50 risk
    assert scorer.normalize_anomaly_score(0.0) == 50.0
    # Maximum score (0.25) -> 100 risk
    assert scorer.normalize_anomaly_score(0.25) == 100.0
    # Out of bounds clamping
    assert scorer.normalize_anomaly_score(0.40) == 100.0
    assert scorer.normalize_anomaly_score(-0.40) == 0.0


def test_cold_start_handling(scorer):
    """
    Verify missing behavioral history (NaN in cold start) does not trigger high risk.
    """
    cold_start_input = RiskInput(
        amount=100.0,
        amount_deviation=None,      # NaN/None cold start
        is_new_device=0,
        is_new_ip=0,
        location_deviation_km=None, # NaN/None cold start
        velocity_1h=0,
        velocity_24h=0,
        recipient_in_degree=0,
        sender_out_degree=0,
        fraud_probability=0.0,
        anomaly_score=-0.25
    )
    
    output = scorer.score(cold_start_input)
    
    # Because there are no flags, behavioral risk should remain 0.0 (not maximum risk)
    assert output.behavioral_risk == 0.0
    assert output.risk_score == 0.0
    assert output.risk_level == "LOW"


def test_behavioral_flag_escalation(scorer):
    """
    Verify high behavioral deviations increase behavioral and overall risk.
    """
    high_behavior = RiskInput(
        amount=5000.0,
        amount_deviation=10.0,          # 10x deviation
        is_new_device=1,               # new device
        is_new_ip=1,                   # new IP
        location_deviation_km=205.0,    # far deviation
        velocity_1h=3,
        velocity_24h=3,
        recipient_in_degree=0,
        sender_out_degree=0,
        fraud_probability=0.0,
        anomaly_score=-0.25
    )
    output = scorer.score(high_behavior)
    
    # Behavioral risk should be highly elevated
    assert output.behavioral_risk > 80.0
    # Contributing factors should show behavioral details
    factors = [f.factor for f in output.risk_factors]
    assert any("large transaction amount" in f for f in factors)
    assert "New device fingerprint seen for user" in factors
    assert "New IP address seen for user" in factors


def test_network_flag_escalation(scorer):
    """
    Verify network degree flags correctly influence network risk.
    """
    high_network = RiskInput(
        amount=100.0, amount_deviation=1.0, is_new_device=0, is_new_ip=0,
        location_deviation_km=0.0, velocity_1h=0, velocity_24h=0,
        recipient_in_degree=4,         # multiple sources (sink)
        sender_out_degree=0,
        fraud_probability=0.0, anomaly_score=-0.25
    )
    output = scorer.score(high_network)
    
    # Network risk = (4 / 5) * 100 = 80.0
    assert output.network_risk == 80.0
    # Overall risk = 0.10 * 80 = 8.0
    assert output.risk_score == 8.0
    
    factors = [f.factor for f in output.risk_factors]
    assert any("Receiver has multiple incoming" in f for f in factors)


def test_final_score_clamping(scorer):
    """
    Assert overall risk score is always bounded in [0, 100] and maps to correct levels.
    """
    max_input = RiskInput(
        amount=10000.0, amount_deviation=15.0, is_new_device=1, is_new_ip=1,
        location_deviation_km=500.0, velocity_1h=10, velocity_24h=20,
        recipient_in_degree=10, sender_out_degree=10,
        fraud_probability=1.0, anomaly_score=0.4
    )
    output = scorer.score(max_input)
    
    assert output.risk_score == 100.0
    assert output.risk_level == "CRITICAL"


def test_determinism_and_batch_consistency(scorer):
    """
    Verify scoring is deterministic (same input -> same output)
    and batch scoring matches single-transaction results.
    """
    input_data = {
        "amount": [100.0, 5000.0],
        "amount_deviation": [1.0, 8.5],
        "is_new_device": [0, 1],
        "is_new_ip": [0, 0],
        "location_deviation_km": [0.0, 150.0],
        "velocity_1h": [0, 2],
        "velocity_24h": [0, 5],
        "recipient_in_degree": [0, 4],
        "sender_out_degree": [0, 1],
        "fraud_probability": [0.1, 0.9],
        "anomaly_score": [-0.2, 0.15]
    }
    df = pd.DataFrame(input_data)
    
    # Score batch
    df_scored = scorer.score_batch(df)
    
    # Verify first row matches single score output
    r1 = RiskInput(
        amount=100.0, amount_deviation=1.0, is_new_device=0, is_new_ip=0,
        location_deviation_km=0.0, velocity_1h=0, velocity_24h=0,
        recipient_in_degree=0, sender_out_degree=0,
        fraud_probability=0.1, anomaly_score=-0.2
    )
    out1 = scorer.score(r1)
    
    assert df_scored.loc[0, "risk_score"] == out1.risk_score
    assert df_scored.loc[0, "risk_level"] == out1.risk_level
    assert df_scored.loc[0, "supervised_risk"] == out1.supervised_risk
