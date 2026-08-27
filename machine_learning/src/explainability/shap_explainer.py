"""
TRUSTNET - SHAP Explainable AI (XAI) Layer
Loads the trained XGBoost model, computes local/global SHAP values, and
provides human-readable explanations of model predictions.
"""

import os
import json
import math
import numpy as np
import pandas as pd
import xgboost as xgb
import shap
from typing import Dict, List, Any, Union

class TrustnetExplainer:
    """
    Orchestrates local and global SHAP explanations for the XGBoost fraud model.
    """
    
    def __init__(self, model_path: str):
        self.model_path = model_path
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model artifact not found at: {model_path}")
            
        # 1. Load the XGBoost model binary
        self.clf = xgb.XGBClassifier()
        self.clf.load_model(model_path)
        
        # 2. Extract model features from the metadata file
        metadata_path = model_path.replace("xgboost_baseline.json", "xgboost_metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                meta = json.load(f)
            self.features = meta.get("features", [])
        else:
            raise FileNotFoundError(f"Metadata file not found for model: {metadata_path}")
            
        if not self.features:
            raise ValueError("No feature list found in model metadata.")
            
        # 3. Initialize the TreeExplainer
        self.explainer = shap.TreeExplainer(self.clf)

    def _impute_nans(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Fills cold-start NaN deviation features with neutral baseline values
        to prevent TreeExplainer value resolution errors.
        """
        impute_defaults = {
            "amount_deviation": 1.0,
            "location_deviation_km": 0.0
        }
        df_filled = df.fillna(impute_defaults)
        
        # Cast fields explicitly to numeric types to avoid pandas object dtype errors with XGBoost/SKLearn
        type_dict = {f: float if f in ["amount", "amount_deviation", "location_deviation_km"] else int for f in self.features}
        # Only cast features that are actually present in df_filled
        type_dict = {k: v for k, v in type_dict.items() if k in df_filled.columns}
        return df_filled.astype(type_dict)

    def get_human_explanation(self, feature: str, direction: str, value: float) -> str:
        """
        Generates simple, analyst-friendly descriptions of model component weights.
        """
        if feature == "amount_deviation":
            if direction == "increases_risk":
                return f"Transaction amount is significantly higher than the user's historical average ({value:.1f}x baseline)."
            else:
                return "Transaction amount is within normal parameters."
                
        elif feature == "location_deviation_km":
            if direction == "increases_risk":
                return f"The transaction was initiated from a distant location ({value:.1f} km deviation)."
            else:
                return "Transaction coordinates match typical user locations."
                
        elif feature == "is_new_device":
            if direction == "increases_risk" and value == 1:
                return "The current device fingerprint has not been seen before for this user."
                
        elif feature == "is_new_ip":
            if direction == "increases_risk" and value == 1:
                return "The transaction was initiated from a new IP address."
                
        elif feature == "velocity_1h":
            if direction == "increases_risk" and value >= 2:
                return f"Elevated transaction frequency in the last hour ({int(value)} counts)."
                
        elif feature == "velocity_24h":
            if direction == "increases_risk" and value >= 5:
                return f"Elevated transaction frequency in the last 24 hours ({int(value)} counts)."
                
        elif feature == "recipient_in_degree":
            if direction == "increases_risk" and value >= 3:
                return f"Receiver has multiple incoming transfer sources (potential mule in-degree: {int(value)})."
                
        elif feature == "sender_out_degree":
            if direction == "increases_risk" and value >= 3:
                return f"Sender transferring to multiple distinct accounts (out-degree: {int(value)})."
                
        # Fallbacks for low-risk features or temporal factors
        if direction == "increases_risk":
            return f"Feature '{feature}' slightly pushed prediction towards fraud risk."
        else:
            return f"Feature '{feature}' matches normal historical patterns."

    def explain_local(self, transaction_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates local SHAP values and returns structured contribution data.
        """
        # Validate that all required features are present
        missing_features = [f for f in self.features if f not in transaction_features]
        if missing_features:
            raise ValueError(f"Missing required model features: {missing_features}")
            
        # Structure into a DataFrame in the exact training features order
        df = pd.DataFrame([transaction_features])[self.features]
        
        # Capture raw values before imputation for output formatting
        raw_values = df.iloc[0].to_dict()
        
        # Impute NaNs for explainer stability
        df_imputed = self._impute_nans(df)
        
        # 1. Compute SHAP values in log-odds space
        shap_values = self.explainer.shap_values(df_imputed)[0]
        
        # 2. Extract base value (expected value)
        expected_val = self.explainer.expected_value
        if isinstance(expected_val, (list, np.ndarray)):
            base_value = float(expected_val[0])
        else:
            base_value = float(expected_val)
            
        # 3. Compute predicted probability
        prob = float(self.clf.predict_proba(df_imputed)[0, 1])
        
        # 4. Map contributions
        contributions = []
        for idx, f_name in enumerate(self.features):
            shap_val = float(shap_values[idx])
            val = raw_values[f_name]
            direction = "increases_risk" if shap_val > 0.0 else "decreases_risk"
            
            contributions.append({
                "feature": f_name,
                "value": None if pd.isna(val) else float(val),
                "shap_value": round(shap_val, 4),
                "direction": direction,
                "human_readable": self.get_human_explanation(f_name, direction, val)
            })
            
        return {
            "fraud_probability": round(prob, 4),
            "base_value": round(base_value, 4),
            "contributions": contributions
        }

    def explain_global(self, X_test: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Computes global SHAP feature importance ranks across a dataset.
        """
        # Validate columns
        missing_features = [f for f in self.features if f not in X_test.columns]
        if missing_features:
            raise ValueError(f"DataFrame is missing required model features: {missing_features}")
            
        # Project only the required features in the correct order
        X_proj = X_test[self.features].copy()
        X_proj = self._impute_nans(X_proj)
        
        # Calculate SHAP values
        shap_values = self.explainer.shap_values(X_proj)
        
        # Calculate mean absolute SHAP values per feature
        mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
        
        # Build global records list
        global_importance = []
        for idx, f_name in enumerate(self.features):
            global_importance.append({
                "feature": f_name,
                "mean_abs_shap": float(mean_abs_shap[idx])
            })
            
        # Sort by importance descending
        global_importance = sorted(global_importance, key=lambda x: x["mean_abs_shap"], reverse=True)
        
        # Assign rank
        for rank, item in enumerate(global_importance, 1):
            item["rank"] = rank
            
        return global_importance

    def validate_additive_property(self, transaction_features: Dict[str, Any], tol: float = 1e-5) -> bool:
        """
        Validation utility: verifies the sum of SHAP values + base value
        equals the predicted log-odds (margin) output.
        """
        df = pd.DataFrame([transaction_features])[self.features]
        df_imputed = self._impute_nans(df)
        
        # Calculate SHAP summation directly from raw float values
        shap_values = self.explainer.shap_values(df_imputed)[0]
        expected_val = self.explainer.expected_value
        base_value = float(expected_val[0]) if isinstance(expected_val, (list, np.ndarray)) else float(expected_val)
        
        sum_shap = sum(shap_values) + base_value
        
        # Calculate raw model margin predict output
        raw_margin = float(self.clf.predict(df_imputed, output_margin=True)[0])
        
        # Check tolerance closeness
        return math.isclose(sum_shap, raw_margin, abs_tol=tol)
