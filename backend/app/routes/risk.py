"""
TRUSTNET - Risk Analysis Endpoints
Wires transaction input parameters to the active AI baseline models, Risk Engine,
and SHAP Explainability systems.
"""

import pandas as pd
from fastapi import APIRouter, HTTPException, status
from backend.app.schemas.risk import TransactionAnalysisRequest, TransactionAnalysisResponse
from backend.app.models_loader import (
    get_xgboost_model,
    get_isolation_forest,
    get_risk_scorer,
    get_shap_explainer,
    get_models_status,
    get_network_engine
)
from machine_learning.src.risk_engine.schemas import RiskInput

router = APIRouter(prefix="/api/v1/risk", tags=["Risk Intelligence"])


@router.post(
    "/analyze",
    response_model=TransactionAnalysisResponse,
    summary="Analyze transaction risk",
    description=(
        "Ingests raw transaction features, executes XGBoost and Isolation Forest models, "
        "evaluates combined decision prioritization scoring policies, and calculates local SHAP attributions."
    )
)
async def analyze_transaction(request: TransactionAnalysisRequest):
    # 1. Verify model files are loaded
    status_check = get_models_status()
    if not (status_check["xgboost_available"] and status_check["isolation_forest_available"]):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Models are not loaded or initialized on the server. Please run baseline training."
        )

    # 2. Extract inputs into raw Dict and project in correct feature order
    features_order = [
        "amount", "amount_deviation", "is_new_device", "is_new_ip", "location_deviation_km",
        "hour_of_day", "day_of_week", "velocity_1h", "velocity_24h", "recipient_in_degree",
        "sender_out_degree"
    ]
    req_dict = request.model_dump()
    df = pd.DataFrame([req_dict])[features_order]
    
    # Impute missing values for models that don't handle NaNs natively in Playbook constraints
    df_imputed = df.fillna({"amount_deviation": 1.0, "location_deviation_km": 0.0})
    
    # Cast fields explicitly to numeric types to avoid pandas object dtype errors with XGBoost/SKLearn
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

    # 3. Model Predictions execution
    try:
        clf = get_xgboost_model()
        fraud_prob = float(clf.predict_proba(df_imputed)[0, 1])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"XGBoost classification execution failed: {str(e)}"
        )

    try:
        iforest = get_isolation_forest()
        anomaly_score = float(-iforest.decision_function(df_imputed)[0])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Isolation Forest anomaly execution failed: {str(e)}"
        )

    # 4. Calculate Network Intelligence first (if sender_id is provided)
    network_intel = None
    net_risk_val = None
    before_ts = None
    if request.timestamp:
        try:
            before_ts = pd.to_datetime(request.timestamp)
        except Exception:
            pass

    if request.sender_id:
        try:
            net_engine = get_network_engine()
            net_risk_val = net_engine.calculate_account_network_risk(request.sender_id, before_timestamp=before_ts)
            metrics = net_engine.get_account_metrics(request.sender_id, before_timestamp=before_ts)
            patterns = net_engine.check_mule_patterns(request.sender_id, before_timestamp=before_ts)
            indicators = net_engine.generate_explanations(request.sender_id, before_timestamp=before_ts)
            
            # Find suspicious connections (nodes in ego network with risk >= 30)
            suspicious_connections = []
            ego = net_engine.get_ego_network(request.sender_id, before_timestamp=before_ts)
            for node in ego["nodes"]:
                if node["id"] != request.sender_id and node["risk"] >= 30:
                    suspicious_connections.append({
                        "account_id": node["id"],
                        "risk_score": node["risk"]
                    })
                    
            mule_risk = 0.0
            active_patterns = [k for k, v in patterns.items() if v]
            if active_patterns:
                mule_risk = min(100.0, len(active_patterns) * 20.0 + (net_risk_val * 0.4))
                
            network_intel = {
                "network_risk": net_risk_val,
                "mule_risk": round(mule_risk, 2),
                "indicators": indicators,
                "metrics": {
                    "incoming_amount": metrics["incoming_amount"],
                    "outgoing_amount": metrics["outgoing_amount"],
                    "incoming_tx_count": metrics["incoming_tx_count"],
                    "outgoing_tx_count": metrics["outgoing_tx_count"],
                    "total_network_tx_count": metrics["total_network_tx_count"],
                    "rapid_pass_through_count": len(net_engine.detect_rapid_pass_through_events(request.sender_id, before_timestamp=before_ts))
                },
                "suspicious_connections": suspicious_connections
            }
        except Exception as e:
            print(f"Network intelligence calculation failed: {str(e)}")

    if network_intel is None:
        network_intel = {
            "network_risk": 0.0,
            "mule_risk": 0.0,
            "indicators": [],
            "metrics": {},
            "suspicious_connections": []
        }

    # 5. Consolidate combined Risk Score
    try:
        scorer = get_risk_scorer()
        risk_input = RiskInput(
            amount=request.amount,
            amount_deviation=request.amount_deviation,
            is_new_device=request.is_new_device,
            is_new_ip=request.is_new_ip,
            location_deviation_km=request.location_deviation_km,
            velocity_1h=request.velocity_1h,
            velocity_24h=request.velocity_24h,
            recipient_in_degree=request.recipient_in_degree,
            sender_out_degree=request.sender_out_degree,
            fraud_probability=fraud_prob,
            anomaly_score=anomaly_score,
            network_risk_override=net_risk_val
        )
        risk_out = scorer.score(risk_input)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TRUSTNET Risk Engine scoring failed: {str(e)}"
        )

    # 6. Calculate Local SHAP Explanations
    try:
        explainer = get_shap_explainer()
        shap_out = explainer.explain_local(req_dict)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SHAP explanation attribution extraction failed: {str(e)}"
        )

    # 7. Format response JSON matching response Pydantic schema
    response_payload = {
        "fraud_probability": round(fraud_prob, 4),
        "anomaly_score": round(anomaly_score, 4),
        "supervised_risk": risk_out.supervised_risk,
        "anomaly_risk": risk_out.anomaly_risk,
        "behavioral_risk": risk_out.behavioral_risk,
        "network_risk": risk_out.network_risk,
        "risk_score": risk_out.risk_score,
        "risk_level": risk_out.risk_level,
        "risk_factors": [
            {
                "factor": f.factor,
                "category": f.category,
                "severity": f.severity,
                "contribution": f.contribution
            } for f in risk_out.risk_factors
        ],
        "shap_explanation": {
            "base_value": shap_out["base_value"],
            "contributions": [
                {
                    "feature": c["feature"],
                    "value": c["value"],
                    "shap_value": c["shap_value"],
                    "direction": c["direction"],
                    "human_readable": c["human_readable"]
                } for c in shap_out["contributions"]
            ]
        },
        "network_intelligence": network_intel
    }

    return response_payload
