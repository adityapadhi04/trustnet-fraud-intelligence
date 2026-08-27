"""
TRUSTNET - Alerts Management Endpoints
Handles list retrieval, detail lookup, status transitions, and dynamic trigger generation.
"""

import os
import json
import threading
from datetime import datetime
import pandas as pd
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.schemas.alerts import AlertResponse, AlertPatchRequest, AlertStatus, AlertType
from backend.app.models_loader import (
    get_transactions_df,
    get_xgboost_model,
    get_isolation_forest,
    get_risk_scorer,
    get_network_engine,
    get_models_status
)
from machine_learning.src.risk_engine.schemas import RiskInput

router = APIRouter(prefix="/api/v1/alerts", tags=["Alert Management"])

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALERTS_JSON_PATH = os.path.join(PROJECT_ROOT, "datasets", "alerts.json")

# Thread safety lock for JSON database access
_db_lock = threading.Lock()


# Check for writable temp directory on serverless (Vercel)
is_vercel = os.environ.get("VERCEL") is not None
ALERTS_DB_PATH = "/tmp/alerts.json" if is_vercel else ALERTS_JSON_PATH


class AlertsStore:
    """Thread-safe JSON file based local database for alerts."""
    
    @staticmethod
    def load_all() -> dict:
        # If on Vercel and /tmp/alerts.json doesn't exist yet, copy it from the package
        if is_vercel and not os.path.exists(ALERTS_DB_PATH) and os.path.exists(ALERTS_JSON_PATH):
            try:
                import shutil
                os.makedirs(os.path.dirname(ALERTS_DB_PATH), exist_ok=True)
                shutil.copy2(ALERTS_JSON_PATH, ALERTS_DB_PATH)
            except Exception as e:
                print(f"Could not copy alerts file to tmp: {str(e)}")
        
        if not os.path.exists(ALERTS_DB_PATH):
            return {}
        try:
            with open(ALERTS_DB_PATH, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except Exception as e:
            print(f"Error loading alerts database from {ALERTS_DB_PATH}: {str(e)}")
            return {}

    @staticmethod
    def save_all(alerts_dict: dict):
        try:
            os.makedirs(os.path.dirname(ALERTS_DB_PATH), exist_ok=True)
            with open(ALERTS_DB_PATH, "w", encoding="utf-8") as f:
                json.dump(alerts_dict, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving alerts database to {ALERTS_DB_PATH}: {str(e)}")


def calculate_severity(risk_score: float) -> str:
    """Suggested thresholds for Alert Severity:
    - CRITICAL: >= 80
    - HIGH: >= 60 and < 80
    - MEDIUM: >= 40 and < 60
    - LOW: < 40
    """
    if risk_score >= 80:
        return "CRITICAL"
    elif risk_score >= 60:
        return "HIGH"
    elif risk_score >= 40:
        return "MEDIUM"
    else:
        return "LOW"


def determine_alert_type(risk_score: float, fraud_prob: float, anomaly_score: float, anomaly_risk: float, network_risk: float, mule_risk: float) -> str:
    """Helper to classify alert type based on dominant indicators."""
    if mule_risk >= 40:
        return AlertType.POTENTIAL_MULE.value
    elif network_risk >= 40:
        return AlertType.NETWORK_RISK.value
    elif fraud_prob >= 0.5:
        return AlertType.FRAUD_RISK.value
    elif anomaly_score >= 0.0 or anomaly_risk >= 40:
        return AlertType.ANOMALY.value
    else:
        return AlertType.FRAUD_RISK.value


def determine_primary_reason(alert_type: str, risk_factors: list) -> str:
    """Extracts a meaningful explanation based on the alert type and factors."""
    if alert_type == AlertType.POTENTIAL_MULE.value:
        return "Potential mule behavior detected (e.g. rapid fund pass-through or fan-in/fan-out patterns)"
    
    if risk_factors:
        # Find factor with highest contribution
        sorted_factors = sorted(risk_factors, key=lambda x: getattr(x, "contribution", 0.0), reverse=True)
        if sorted_factors:
            return sorted_factors[0].factor
            
    if alert_type == AlertType.NETWORK_RISK.value:
        return "High risk network node connectivity detected"
    elif alert_type == AlertType.ANOMALY.value:
        return "Anomalous transaction behavioral patterns detected"
    else:
        return "Elevated ML supervised fraud probability"


def add_alert_for_transaction(
    transaction_id: str,
    risk_score: float,
    risk_level: str,
    risk_factors: list,
    network_intel: dict,
    fraud_prob: float = 0.0,
    anomaly_score: float = 0.0,
    anomaly_risk: float = 0.0,
    created_at: str = None
) -> dict:
    """Creates a new alert or updates an existing alert for a transaction."""
    severity = calculate_severity(risk_score)
    mule_risk = network_intel.get("mule_risk", 0.0)
    net_risk = network_intel.get("network_risk", 0.0)
    
    alert_type = determine_alert_type(risk_score, fraud_prob, anomaly_score, anomaly_risk, net_risk, mule_risk)
    primary_reason = determine_primary_reason(alert_type, risk_factors)
    
    if not created_at:
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    alert_id = f"ALT-{transaction_id}"
    
    with _db_lock:
        db = AlertsStore.load_all()
        
        # Check if already exists
        if alert_id in db:
            existing = db[alert_id]
            # Update scores/reasons but preserve lifecycle status
            existing.update({
                "severity": severity,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "alert_type": alert_type,
                "primary_reason": primary_reason
            })
            AlertsStore.save_all(db)
            return existing

        new_alert = {
            "alert_id": alert_id,
            "transaction_id": transaction_id,
            "severity": severity,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "alert_type": alert_type,
            "primary_reason": primary_reason,
            "status": AlertStatus.OPEN.value,
            "created_at": created_at
        }
        
        db[alert_id] = new_alert
        AlertsStore.save_all(db)
        return new_alert


def score_transaction_for_alerts(tx: dict) -> dict:
    """Helper to run the full ML and Risk Scorer pipeline for pre-population."""
    features_order = [
        "amount", "amount_deviation", "is_new_device", "is_new_ip", "location_deviation_km",
        "hour_of_day", "day_of_week", "velocity_1h", "velocity_24h", "recipient_in_degree",
        "sender_out_degree"
    ]
    df = pd.DataFrame([tx])[features_order]
    df_imputed = df.fillna({"amount_deviation": 1.0, "location_deviation_km": 0.0})
    df_imputed = df_imputed.astype({
        "amount": float,
        "amount_deviation": float,
        "is_new_device": int,
        "is_new_ip": int,
        "location_deviation_km": float,
        "hour_of_day": int,
        "day_of_week": int,
        "velocity_1h": int,
        "velocity_24h": int,
        "recipient_in_degree": int,
        "sender_out_degree": int
    })

    clf = get_xgboost_model()
    fraud_prob = float(clf.predict_proba(df_imputed)[0, 1])

    iforest = get_isolation_forest()
    anomaly_score = float(-iforest.decision_function(df_imputed)[0])

    net_risk_val = None
    net_mule_risk = 0.0
    if tx.get("sender_id"):
        try:
            net_engine = get_network_engine()
            before_ts = pd.to_datetime(tx.get("timestamp")) if tx.get("timestamp") else None
            net_risk_val = net_engine.calculate_account_network_risk(tx["sender_id"], before_timestamp=before_ts)
            patterns = net_engine.check_mule_patterns(tx["sender_id"], before_timestamp=before_ts)
            active_patterns = [k for k, v in patterns.items() if v]
            if active_patterns:
                net_mule_risk = min(100.0, len(active_patterns) * 20.0 + (net_risk_val * 0.4))
        except Exception:
            pass

    scorer = get_risk_scorer()
    risk_input = RiskInput(
        amount=tx["amount"],
        amount_deviation=tx.get("amount_deviation"),
        is_new_device=tx["is_new_device"],
        is_new_ip=tx["is_new_ip"],
        location_deviation_km=tx.get("location_deviation_km"),
        velocity_1h=tx["velocity_1h"],
        velocity_24h=tx["velocity_24h"],
        recipient_in_degree=tx["recipient_in_degree"],
        sender_out_degree=tx["sender_out_degree"],
        fraud_probability=fraud_prob,
        anomaly_score=anomaly_score,
        network_risk_override=net_risk_val
    )
    risk_out = scorer.score(risk_input)

    return {
        "risk_score": risk_out.risk_score,
        "risk_level": risk_out.risk_level,
        "fraud_probability": fraud_prob,
        "anomaly_score": anomaly_score,
        "anomaly_risk": risk_out.anomaly_risk,
        "supervised_risk": risk_out.supervised_risk,
        "behavioral_risk": risk_out.behavioral_risk,
        "network_risk": risk_out.network_risk,
        "mule_risk": round(net_mule_risk, 2),
        "risk_factors": risk_out.risk_factors
    }


def pre_populate_alerts_database():
    """Generates initial alerts for transactions with risk_score >= 40."""
    status_check = get_models_status()
    if not (status_check["xgboost_available"] and status_check["isolation_forest_available"] and status_check["dataset_available"]):
        print("Skipping alert database pre-population: models or datasets are not fully loaded/available.")
        return

    # Check if database already has alerts
    with _db_lock:
        db = AlertsStore.load_all()
        if len(db) > 0:
            print(f"Alerts database already populated with {len(db)} records.")
            return

    print("Pre-populating alerts database from synthetic dataset...")
    try:
        df = get_transactions_df()
        # Scan first 300 transactions
        scan_limit = min(300, len(df))
        alerts_added = 0
        
        for idx in range(scan_limit):
            row = df.iloc[idx]
            tx_dict = row.to_dict()
            
            # Run ML scorer
            score_out = score_transaction_for_alerts(tx_dict)
            risk_score = score_out["risk_score"]
            
            # Generate alert only if risk score meets/exceeds Medium threshold (>= 40)
            if risk_score >= 40.0:
                severity = calculate_severity(risk_score)
                mule_risk = score_out["mule_risk"]
                net_risk = score_out["network_risk"]
                
                alert_type = determine_alert_type(
                    risk_score, 
                    score_out["fraud_probability"], 
                    score_out["anomaly_score"], 
                    score_out["anomaly_risk"], 
                    net_risk, 
                    mule_risk
                )
                primary_reason = determine_primary_reason(alert_type, score_out["risk_factors"])
                
                alert_id = f"ALT-{tx_dict['transaction_id']}"
                
                with _db_lock:
                    db = AlertsStore.load_all()
                    db[alert_id] = {
                        "alert_id": alert_id,
                        "transaction_id": tx_dict["transaction_id"],
                        "severity": severity,
                        "risk_score": risk_score,
                        "risk_level": score_out["risk_level"],
                        "alert_type": alert_type,
                        "primary_reason": primary_reason,
                        "status": AlertStatus.OPEN.value,
                        "created_at": tx_dict["timestamp"]
                    }
                    AlertsStore.save_all(db)
                alerts_added += 1

        print(f"Pre-population finished. Added {alerts_added} alerts to local store.")
    except Exception as e:
        print(f"Failed during alert pre-population: {str(e)}")


# Trigger pre-population on file load (FastAPI will import this on start)
try:
    pre_populate_alerts_database()
except Exception as e:
    print(f"Failed to auto pre-populate alerts: {str(e)}")


@router.get(
    "",
    response_model=List[AlertResponse],
    summary="Get all alerts",
    description="Retrieve a list of payment alerts with optional filtering on severity and lifecycle status."
)
async def get_alerts(
    severity: Optional[str] = Query(None, description="Filter alerts by severity level (LOW, MEDIUM, HIGH, CRITICAL)."),
    status: Optional[str] = Query(None, description="Filter alerts by lifecycle status (OPEN, INVESTIGATING, RESOLVED, FALSE_POSITIVE).")
):
    try:
        with _db_lock:
            db = AlertsStore.load_all()
            
        alerts = list(db.values())
        
        # Apply filters
        if severity:
            severity_upper = severity.upper()
            alerts = [a for a in alerts if a["severity"] == severity_upper]
            
        if status:
            status_upper = status.upper()
            alerts = [a for a in alerts if a["status"] == status_upper]
            
        # Sort by creation time (newest first) or highest risk
        alerts = sorted(alerts, key=lambda x: x["created_at"], reverse=True)
        return alerts
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load alerts: {str(e)}"
        )


@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Retrieve alert by ID",
    description="Lookup details for a specific alert record by its unique ID."
)
async def get_alert_by_id(alert_id: str):
    with _db_lock:
        db = AlertsStore.load_all()
        
    if alert_id not in db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID '{alert_id}' not found."
        )
    return db[alert_id]


@router.patch(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Update alert status",
    description="Transitions an alert's investigation lifecycle status."
)
async def update_alert_status(alert_id: str, request: AlertPatchRequest):
    with _db_lock:
        db = AlertsStore.load_all()
        
    if alert_id not in db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID '{alert_id}' not found."
        )
        
    with _db_lock:
        # Load again to be safe within transaction
        db = AlertsStore.load_all()
        alert = db[alert_id]
        alert["status"] = request.status.value
        AlertsStore.save_all(db)
        
    return alert
