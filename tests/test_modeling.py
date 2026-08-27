"""
TRUSTNET - Model Verification and Integrity Test Suite
Verifies feature lists, temporal splits, and prediction correctness.
"""

import os
import json
import pytest
import pandas as pd
import numpy as np
import xgboost as xgb
import joblib

from machine_learning.src.models.xgboost_model import (
    load_and_split_data,
    FEATURES as XGB_FEATURES,
    TARGET as XGB_TARGET
)
from machine_learning.src.models.isolation_forest import (
    FEATURES as IF_FEATURES
)

# Root directory check
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DATA_PATH = os.path.join(BASE_DIR, "datasets", "processed_features.csv")
MODELS_DIR = os.path.join(BASE_DIR, "models")


@pytest.fixture
def load_dataset():
    """Fixture to load sorted processed features."""
    if not os.path.exists(PROCESSED_DATA_PATH):
        pytest.skip(f"Processed features file not found: {PROCESSED_DATA_PATH}")
    df = pd.read_csv(PROCESSED_DATA_PATH)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp").reset_index(drop=True)


def test_feature_target_separation():
    """
    Assert that the ML feature list is completely separate from targets and identifiers.
    """
    excluded_fields = ["transaction_id", "sender_id", "receiver_id", "timestamp", "payment_method", "is_fraud_labeled", "data_type"]
    
    for feature in XGB_FEATURES:
        assert feature not in excluded_fields, f"Feature '{feature}' should be excluded from model training."
    
    assert XGB_TARGET == "is_fraud_labeled"


def test_temporal_split_ordering(load_dataset):
    """
    Verify that train, validation, and test splits are strictly chronological
    and have no overlap.
    """
    df = load_dataset
    
    train_df, val_df, test_df = load_and_split_data(PROCESSED_DATA_PATH)
    
    # Assert row counts sum up to total rows
    assert len(train_df) + len(val_df) + len(test_df) == len(df)
    
    # Assert strict chronological boundary
    train_max_time = train_df["timestamp"].max()
    val_min_time = val_df["timestamp"].min()
    val_max_time = val_df["timestamp"].max()
    test_min_time = test_df["timestamp"].min()
    
    assert train_max_time < val_min_time, "Validation data occurs before training data ends."
    assert val_max_time < test_min_time, "Test data occurs before validation data ends."


def test_xgboost_output_probabilities():
    """
    Verify that the saved XGBoost baseline model outputs valid probabilities in [0, 1].
    """
    model_json_path = os.path.join(MODELS_DIR, "xgboost_baseline.json")
    if not os.path.exists(model_json_path):
        pytest.skip(f"Model file not found: {model_json_path}")
        
    # Load model and run inference on mock data
    clf = xgb.XGBClassifier()
    clf.load_model(model_json_path)
    
    # Create random mock features matching shape
    mock_input = pd.DataFrame(
        np.random.randn(5, len(XGB_FEATURES)),
        columns=XGB_FEATURES
    )
    
    probs = clf.predict_proba(mock_input)[:, 1]
    
    assert len(probs) == 5
    for p in probs:
        assert 0.0 <= p <= 1.0, f"Probability {p} is outside boundary [0, 1]."


def test_isolation_forest_label_exclusion():
    """
    Confirm that the saved Isolation Forest model has the correct features
    and does not utilize ground-truth fraud labels.
    """
    model_pkl_path = os.path.join(MODELS_DIR, "isolation_forest_baseline.pkl")
    metadata_json_path = os.path.join(MODELS_DIR, "isolation_forest_metadata.json")
    
    if not os.path.exists(model_pkl_path) or not os.path.exists(metadata_json_path):
        pytest.skip("Isolation Forest baseline model/metadata files not found.")
        
    with open(metadata_json_path, "r") as f:
        meta = json.load(f)
        
    # Verify features list does not contain TARGET
    assert "is_fraud_labeled" not in meta["features"]
    assert "sender_id" not in meta["features"]
    assert "transaction_id" not in meta["features"]
    
    # Load model binary
    clf = joblib.load(model_pkl_path)
    assert clf.n_features_in_ == len(IF_FEATURES)


def test_missing_values_imputation():
    """
    Verify that missing values (due to user cold starts) are present in the raw data
    and handled correctly (XGBoost runs natively, and mock data for Isolation Forest handles fillna).
    """
    df = pd.read_csv(PROCESSED_DATA_PATH)
    
    # Assert cold starts are present as NaN in raw features
    assert df["amount_deviation"].isna().sum() > 0, "Expected cold start NaNs in amount_deviation."
    assert df["location_deviation_km"].isna().sum() > 0, "Expected cold start NaNs in location_deviation_km."
    
    # Assert Isolation Forest features can be filled using defaults
    impute_defaults = {"amount_deviation": 1.0, "location_deviation_km": 0.0}
    df_imputed = df[IF_FEATURES].fillna(impute_defaults)
    assert df_imputed.isna().sum().sum() == 0, "NaN values remained after applying default fillna."
