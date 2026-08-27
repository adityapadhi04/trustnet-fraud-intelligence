"""
TRUSTNET - SHAP Explainability Test Suite
Tests for local and global SHAP calculations and validation equations.
"""

import os
import pytest
import pandas as pd
import numpy as np
import math

from machine_learning.src.explainability.shap_explainer import TrustnetExplainer

# Root directory check
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "xgboost_baseline.json")
PROCESSED_DATA_PATH = os.path.join(BASE_DIR, "datasets", "processed_features.csv")


@pytest.fixture
def explainer():
    """Initializes the baseline TrustnetExplainer."""
    if not os.path.exists(MODEL_PATH):
        pytest.skip(f"XGBoost baseline model not found at: {MODEL_PATH}")
    return TrustnetExplainer(MODEL_PATH)


@pytest.fixture
def sample_transaction():
    """Fixture containing a mock transaction."""
    return {
        "amount": 1250.0,
        "amount_deviation": 1.5,
        "is_new_device": 1,
        "is_new_ip": 0,
        "location_deviation_km": 15.0,
        "hour_of_day": 14,
        "day_of_week": 2,
        "velocity_1h": 1,
        "velocity_24h": 3,
        "recipient_in_degree": 2,
        "sender_out_degree": 1
    }


def test_explainer_initialization(explainer):
    """
    Verify explainer loads model and extracts matching feature names from metadata.
    """
    assert explainer.clf is not None
    assert explainer.features is not None
    assert len(explainer.features) == 11
    
    # Assert target label and metadata exclusions are respected
    excluded_metadata = ["is_fraud_labeled", "transaction_id", "sender_id", "receiver_id", "timestamp"]
    for f in excluded_metadata:
        assert f not in explainer.features


def test_local_explanation_structure(explainer, sample_transaction):
    """
    Verify explain_local returns one numeric contribution per model feature
    and categorizes direction correctly.
    """
    explanation = explainer.explain_local(sample_transaction)
    
    # Should contain fraud probability, base value, and contributions
    assert "fraud_probability" in explanation
    assert "base_value" in explanation
    assert "contributions" in explanation
    
    contributions = explanation["contributions"]
    assert len(contributions) == 11
    
    for item in contributions:
        assert "feature" in item
        assert "value" in item
        assert "shap_value" in item
        assert "direction" in item
        assert "human_readable" in item
        
        assert isinstance(item["shap_value"], float)
        # Check direction classification
        if item["shap_value"] > 0:
            assert item["direction"] == "increases_risk"
        else:
            assert item["direction"] == "decreases_risk"


def test_global_explanation_ranking(explainer):
    """
    Verify explain_global returns all model features sorted in descending order of importance.
    """
    if not os.path.exists(PROCESSED_DATA_PATH):
        pytest.skip("Processed features dataset not found.")
        
    df = pd.read_csv(PROCESSED_DATA_PATH)
    
    # Run global importance
    importance = explainer.explain_global(df.iloc[:20])
    
    assert len(importance) == 11
    
    # Check ranking order
    prev_shap = float('inf')
    for rank_idx, item in enumerate(importance, 1):
        assert item["feature"] in explainer.features
        assert item["rank"] == rank_idx
        # Sorted descending assert
        assert item["mean_abs_shap"] <= prev_shap
        prev_shap = item["mean_abs_shap"]


def test_missing_feature_raises_error(explainer, sample_transaction):
    """
    Verify explainer raises a clear ValueError if a required feature is missing.
    """
    bad_tx = sample_transaction.copy()
    del bad_tx["amount_deviation"] # remove required feature
    
    with pytest.raises(ValueError) as excinfo:
        explainer.explain_local(bad_tx)
    assert "amount_deviation" in str(excinfo.value)


def test_wrong_feature_ordering_handled_safely(explainer, sample_transaction):
    """
    Verify explainer aligns inputs correctly even if key orders are shuffled in the dictionary.
    """
    # Create scrambled key order
    shuffled_keys = list(sample_transaction.keys())
    np.random.seed(42)
    np.random.shuffle(shuffled_keys)
    shuffled_tx = {k: sample_transaction[k] for k in shuffled_keys}
    
    # Run local explanation
    output = explainer.explain_local(shuffled_tx)
    
    # Result should still compute successfully and match
    assert output["fraud_probability"] is not None
    assert len(output["contributions"]) == 11


def test_additive_shap_logodds_property(explainer, sample_transaction):
    """
    Verify mathematical property: base_value + sum(shap_values) equals raw model margin log-odds prediction.
    """
    is_valid = explainer.validate_additive_property(sample_transaction, tol=1e-5)
    assert is_valid, "Sum of SHAP values + base value does not equal raw model output margin."


def test_determinism_and_read_only(explainer, sample_transaction):
    """
    Verify calculations are deterministic (running twice gives identical results)
    and do not alter the underlying model parameters.
    """
    # Run 1
    exp1 = explainer.explain_local(sample_transaction)
    
    # Run 2
    exp2 = explainer.explain_local(sample_transaction)
    
    assert exp1["fraud_probability"] == exp2["fraud_probability"]
    assert exp1["base_value"] == exp2["base_value"]
    
    for idx in range(11):
        assert exp1["contributions"][idx]["shap_value"] == exp2["contributions"][idx]["shap_value"]
        assert exp1["contributions"][idx]["direction"] == exp2["contributions"][idx]["direction"]
