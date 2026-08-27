"""
TRUSTNET - Risk Scoring Engine
Consolidates supervised and unsupervised model outputs, user behavioral deviations,
and network indicators into a single unified 0-100 decision prioritization score.
"""

import math
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Union
from machine_learning.src.risk_engine.schemas import RiskInput, RiskFactor, RiskOutput

# Prototype scoring weights (Policy configurability)
DEFAULT_WEIGHTS = {
    "supervised": 0.45,
    "anomaly": 0.25,
    "behavioral": 0.20,
    "network": 0.10
}

# Categorical risk level thresholds
DEFAULT_RISK_LIMITS = {
    30: "MEDIUM",
    60: "HIGH",
    80: "CRITICAL"
}


class RiskScorer:
    """
    Risk scoring engine mapping disparate features and prediction probabilities
    into normalized decision-support prioritization outputs.
    """
    
    def __init__(self, weights: Dict[str, float] = None, risk_limits: Dict[int, str] = None):
        self.weights = weights or DEFAULT_WEIGHTS
        self.risk_limits = risk_limits or DEFAULT_RISK_LIMITS
        
        # Verify that weights sum to 1.0 (with floating point tolerance)
        total_weight = sum(self.weights.values())
        if not math.isclose(total_weight, 1.0, rel_tol=1e-5):
            raise ValueError(f"Weights must sum to 1.0. Current sum: {total_weight}")

    def normalize_anomaly_score(self, score: float) -> float:
        """
        Maps raw Isolation Forest anomaly score (-decision_function()) to 0-100.
        By default, the trained model returns scores in range [-0.25, 0.25].
        Linear normalization: (score - min) / (max - min) * 100.
        Scores above 0.0 (anomaly threshold) map to risk scores > 50.0.
        """
        if pd.isna(score) or math.isnan(score):
            # Safe default fallback for missing anomaly score (treated as neutral)
            return 50.0
            
        score_min, score_max = -0.25, 0.25
        normalized = (score - score_min) / (score_max - score_min) * 100.0
        return max(0.0, min(100.0, normalized))

    def calculate_behavioral_risk(self, r: RiskInput) -> tuple:
        """
        Computes behavioral risk out of 100 as a weighted average of active
        (non-null) behavior metrics. Ignores NaN cold start values to prevent false positives.
        Returns (behavioral_risk_score, sub_contributions_dict).
        """
        components = {}
        
        # 1. Amount Deviation Risk (Weight: 30%)
        # Amount deviation <= 1.5: 0 risk. Linear scale up to 10.0 deviation.
        if r.amount_deviation is not None and not pd.isna(r.amount_deviation):
            if r.amount_deviation <= 1.5:
                amount_risk = 0.0
            else:
                amount_risk = min(100.0, (r.amount_deviation - 1.5) / 8.5 * 100.0)
            components["amount"] = (amount_risk, 0.30)
            
        # 2. Location Deviation Risk (Weight: 20%)
        # Location deviation <= 5 km: 0 risk. Linear scale up to 105 km deviation.
        if r.location_deviation_km is not None and not pd.isna(r.location_deviation_km):
            if r.location_deviation_km <= 5.0:
                location_risk = 0.0
            else:
                location_risk = min(100.0, (r.location_deviation_km - 5.0) / 100.0 * 100.0)
            components["location"] = (location_risk, 0.20)
            
        # 3. Device Fingerprint Risk (Weight: 20%)
        components["device"] = (100.0 if r.is_new_device == 1 else 0.0, 0.20)
        
        # 4. IP Address Risk (Weight: 10%)
        components["ip"] = (100.0 if r.is_new_ip == 1 else 0.0, 0.10)
        
        # 5. Transaction Velocity Risk (Weight: 20%)
        # 5 or more transactions in 1 hour -> 100 risk.
        # 15 or more transactions in 24 hours -> 100 risk.
        v1_risk = min(100.0, r.velocity_1h / 5.0 * 100.0)
        v24_risk = min(100.0, r.velocity_24h / 15.0 * 100.0)
        components["velocity"] = (max(v1_risk, v24_risk), 0.20)
        
        # Consolidate using weighted average of non-NaN elements
        weighted_sum = 0.0
        weight_sum = 0.0
        sub_risks = {}
        
        for name, (risk_val, weight) in components.items():
            weighted_sum += risk_val * weight
            weight_sum += weight
            sub_risks[name] = risk_val
            
        final_behavioral = (weighted_sum / weight_sum) if weight_sum > 0 else 0.0
        return round(final_behavioral, 4), sub_risks

    def calculate_network_risk(self, r: RiskInput) -> float:
        """
        Computes network risk out of 100 based on preliminary network indicators.
        If network_risk_override is provided, returns that score.
        Otherwise, falls back to degree-based estimate.
        """
        if getattr(r, "network_risk_override", None) is not None:
            return float(r.network_risk_override)

        # 5 or more incoming unique senders in 24h -> 100 risk
        in_degree_risk = min(100.0, r.recipient_in_degree / 5.0 * 100.0)
        # 5 or more outgoing unique receivers in 24h -> 100 risk
        out_degree_risk = min(100.0, r.sender_out_degree / 5.0 * 100.0)
        
        # Take the maximum indicator flag
        return round(max(in_degree_risk, out_degree_risk), 4)

    def determine_risk_level(self, score: float) -> str:
        """
        Maps a 0-100 risk score to configured categories (LOW, MEDIUM, HIGH, CRITICAL).
        """
        sorted_thresholds = sorted(self.risk_limits.keys())
        current_level = "LOW"
        for threshold in sorted_thresholds:
            if score >= threshold:
                current_level = self.risk_limits[threshold]
        return current_level

    def score(self, r: RiskInput) -> RiskOutput:
        """
        Scores a single transaction. Returns structured outputs, risk level,
        and contributing risk factors list.
        """
        # Validate inputs
        r.validate()
        
        # 1. Component Risk Conversions (each on a 0-100 scale)
        supervised_risk = r.fraud_probability * 100.0
        anomaly_risk = self.normalize_anomaly_score(r.anomaly_score)
        behavioral_risk, sub_behaviors = self.calculate_behavioral_risk(r)
        network_risk = self.calculate_network_risk(r)
        
        # 2. Compute Consolidated Priority Score
        raw_final_score = (
            self.weights["supervised"] * supervised_risk +
            self.weights["anomaly"] * anomaly_risk +
            self.weights["behavioral"] * behavioral_risk +
            self.weights["network"] * network_risk
        )
        
        risk_score = round(max(0.0, min(100.0, raw_final_score)), 2)
        risk_level = self.determine_risk_level(risk_score)
        
        # 3. Generate Structured Risk Factors List
        risk_factors = []
        
        # Supervised check
        if r.fraud_probability > 0.5:
            contrib = round(self.weights["supervised"] * supervised_risk, 2)
            severity = "high" if r.fraud_probability > 0.8 else "medium"
            risk_factors.append(RiskFactor(
                factor="Elevated ML supervised fraud probability",
                category="supervised_ml",
                severity=severity,
                contribution=contrib
            ))
            
        # Unsupervised check
        if anomaly_risk > 50.0:
            contrib = round(self.weights["anomaly"] * anomaly_risk, 2)
            severity = "high" if anomaly_risk > 80.0 else "medium"
            risk_factors.append(RiskFactor(
                factor="Anomalous transaction behavioral patterns detected",
                category="unsupervised_ml",
                severity=severity,
                contribution=contrib
            ))
            
        # Behavioral deviations checks
        if "amount" in sub_behaviors and sub_behaviors["amount"] > 50.0:
            contrib = round(self.weights["behavioral"] * sub_behaviors["amount"] * 0.30, 2)
            risk_factors.append(RiskFactor(
                factor=f"Unusually large transaction amount ({r.amount_deviation:.1f}x average)",
                category="behavioral",
                severity="high" if r.amount_deviation > 5.0 else "medium",
                contribution=contrib
            ))
            
        if r.is_new_device == 1:
            contrib = round(self.weights["behavioral"] * 100.0 * 0.20, 2)
            risk_factors.append(RiskFactor(
                factor="New device fingerprint seen for user",
                category="behavioral",
                severity="medium",
                contribution=contrib
            ))
            
        if r.is_new_ip == 1:
            contrib = round(self.weights["behavioral"] * 100.0 * 0.10, 2)
            risk_factors.append(RiskFactor(
                factor="New IP address seen for user",
                category="behavioral",
                severity="low",
                contribution=contrib
            ))
            
        if "location" in sub_behaviors and sub_behaviors["location"] > 50.0:
            contrib = round(self.weights["behavioral"] * sub_behaviors["location"] * 0.20, 2)
            risk_factors.append(RiskFactor(
                factor=f"Location deviation from home coordinates ({r.location_deviation_km:.1f} km)",
                category="behavioral",
                severity="medium",
                contribution=contrib
            ))
            
        if r.velocity_1h >= 3:
            # Velocity risk component contributes
            contrib = round(self.weights["behavioral"] * sub_behaviors["velocity"] * 0.20, 2)
            risk_factors.append(RiskFactor(
                factor=f"High transaction frequency in the last hour ({r.velocity_1h} count)",
                category="behavioral",
                severity="high",
                contribution=contrib
            ))
            
        # Network indicator checks
        if r.recipient_in_degree >= 3:
            contrib = round(self.weights["network"] * (r.recipient_in_degree / 5.0 * 100.0), 2)
            risk_factors.append(RiskFactor(
                factor=f"Receiver has multiple incoming transfer sources (potential mule in-degree: {r.recipient_in_degree})",
                category="network",
                severity="medium",
                contribution=contrib
            ))
            
        if r.sender_out_degree >= 3:
            contrib = round(self.weights["network"] * (r.sender_out_degree / 5.0 * 100.0), 2)
            risk_factors.append(RiskFactor(
                factor=f"Sender transferring to multiple distinct accounts (out-degree: {r.sender_out_degree})",
                category="network",
                severity="medium",
                contribution=contrib
            ))
            
        return RiskOutput(
            risk_score=risk_score,
            risk_level=risk_level,
            fraud_probability=r.fraud_probability,
            anomaly_score=r.anomaly_score,
            supervised_risk=round(supervised_risk, 2),
            anomaly_risk=round(anomaly_risk, 2),
            behavioral_risk=round(behavioral_risk, 2),
            network_risk=round(network_risk, 2),
            risk_factors=risk_factors
        )

    def score_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies scoring model over a DataFrame of signals and returns new
        scoring output columns.
        """
        required_cols = [
            "amount", "amount_deviation", "is_new_device", "is_new_ip",
            "location_deviation_km", "velocity_1h", "velocity_24h",
            "recipient_in_degree", "sender_out_degree",
            "fraud_probability", "anomaly_score"
        ]
        
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"DataFrame missing required column: {col}")
                
        results = []
        for idx, row in df.iterrows():
            # Build RiskInput
            # Handle float conversions and possible NaNs to None
            amount_dev = row["amount_deviation"]
            amount_dev = None if pd.isna(amount_dev) else float(amount_dev)
            
            loc_dev = row["location_deviation_km"]
            loc_dev = None if pd.isna(loc_dev) else float(loc_dev)
            
            r_input = RiskInput(
                amount=float(row["amount"]),
                amount_deviation=amount_dev,
                is_new_device=int(row["is_new_device"]),
                is_new_ip=int(row["is_new_ip"]),
                location_deviation_km=loc_dev,
                velocity_1h=int(row["velocity_1h"]),
                velocity_24h=int(row["velocity_24h"]),
                recipient_in_degree=int(row["recipient_in_degree"]),
                sender_out_degree=int(row["sender_out_degree"]),
                fraud_probability=float(row["fraud_probability"]),
                anomaly_score=float(row["anomaly_score"])
            )
            
            output = self.score(r_input)
            results.append({
                "risk_score": output.risk_score,
                "risk_level": output.risk_level,
                "supervised_risk": output.supervised_risk,
                "anomaly_risk": output.anomaly_risk,
                "behavioral_risk": output.behavioral_risk,
                "network_risk": output.network_risk
            })
            
        df_scored = df.copy()
        df_results = pd.DataFrame(results, index=df.index)
        
        # Merge scoring outputs back into DataFrame
        for col in df_results.columns:
            df_scored[col] = df_results[col]
            
        return df_scored
