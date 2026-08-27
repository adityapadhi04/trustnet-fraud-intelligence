"""
TRUSTNET - Models and Data Loader Utility
Dynamically resolves paths relative to the project root and caches model instances
and datasets in memory to serve FastAPI requests.
"""

import os
import pickle
import json
import xgboost as xgb
import pandas as pd
import joblib
from typing import Any

from machine_learning.src.explainability.shap_explainer import TrustnetExplainer
from machine_learning.src.risk_engine.risk_scorer import RiskScorer
from machine_learning.src.risk_engine.network_intelligence import NetworkIntelligenceEngine

# Resolve the absolute path of the project root
# This file is in backend/app/models_loader.py, so its parent's parent's parent is the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
DATASETS_DIR = os.path.join(PROJECT_ROOT, "datasets")

XGB_MODEL_PATH = os.path.join(MODELS_DIR, "xgboost_baseline.json")
IF_MODEL_PATH = os.path.join(MODELS_DIR, "isolation_forest_baseline.pkl")
DATASET_PATH = os.path.join(DATASETS_DIR, "processed_features.csv")

# Global cached variables
_xgboost_model = None
_isolation_forest = None
_shap_explainer = None
_risk_scorer = None
_transactions_df = None
_network_engine = None


def get_network_engine() -> NetworkIntelligenceEngine:
    """Loads, initializes, and caches the Network Intelligence Engine."""
    global _network_engine
    if _network_engine is None:
        df = get_transactions_df()
        _network_engine = NetworkIntelligenceEngine(df)
    return _network_engine


def get_xgboost_model() -> xgb.XGBClassifier:
    """Loads and caches the XGBoost classifier model."""
    global _xgboost_model
    if _xgboost_model is None:
        if not os.path.exists(XGB_MODEL_PATH):
            raise FileNotFoundError(f"XGBoost model binary not found at: {XGB_MODEL_PATH}")
        clf = xgb.XGBClassifier()
        clf.load_model(XGB_MODEL_PATH)
        _xgboost_model = clf
    return _xgboost_model


def get_isolation_forest() -> Any:
    """Loads and caches the pickled Isolation Forest model."""
    global _isolation_forest
    if _isolation_forest is None:
        if not os.path.exists(IF_MODEL_PATH):
            raise FileNotFoundError(f"Isolation Forest model pickle not found at: {IF_MODEL_PATH}")
        _isolation_forest = joblib.load(IF_MODEL_PATH)
    return _isolation_forest


def get_shap_explainer() -> TrustnetExplainer:
    """Loads and caches the TrustnetExplainer wrapper around SHAP TreeExplainer."""
    global _shap_explainer
    if _shap_explainer is None:
        if not os.path.exists(XGB_MODEL_PATH):
            raise FileNotFoundError(f"XGBoost model binary not found for SHAP explainer: {XGB_MODEL_PATH}")
        _shap_explainer = TrustnetExplainer(XGB_MODEL_PATH)
    return _shap_explainer


def get_risk_scorer() -> RiskScorer:
    """Initializes and caches the RiskScorer."""
    global _risk_scorer
    if _risk_scorer is None:
        _risk_scorer = RiskScorer()
    return _risk_scorer


def get_transactions_df() -> pd.DataFrame:
    """Loads and caches the processed transactions CSV dataset."""
    global _transactions_df
    if _transactions_df is None:
        if not os.path.exists(DATASET_PATH):
            raise FileNotFoundError(f"Processed dataset features not found at: {DATASET_PATH}")
        _transactions_df = pd.read_csv(DATASET_PATH)
    return _transactions_df


def get_models_status() -> dict:
    """Returns availability flags for all platform pipeline models."""
    return {
        "xgboost_available": os.path.exists(XGB_MODEL_PATH),
        "isolation_forest_available": os.path.exists(IF_MODEL_PATH),
        "shap_available": os.path.exists(XGB_MODEL_PATH) and os.path.exists(XGB_MODEL_PATH.replace("xgboost_baseline.json", "xgboost_metadata.json")),
        "dataset_available": os.path.exists(DATASET_PATH)
    }
