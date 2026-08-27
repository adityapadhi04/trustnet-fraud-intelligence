"""
TRUSTNET - Risk Analysis Pydantic Schemas
Defines request validation and response models for the risk analysis endpoint.
"""

from pydantic import BaseModel, Field
from typing import List, Optional

class TransactionAnalysisRequest(BaseModel):
    amount: float = Field(..., description="Transaction transfer amount in currency units.", ge=0.0)
    amount_deviation: Optional[float] = Field(None, description="Ratio of transaction amount to historical average.", ge=0.0)
    is_new_device: int = Field(..., description="Flag indicating if the device fingerprint is new for the user (0 or 1).", ge=0, le=1)
    is_new_ip: int = Field(..., description="Flag indicating if the IP address is new for the user (0 or 1).", ge=0, le=1)
    location_deviation_km: Optional[float] = Field(None, description="Distance deviation in kilometers from typical user coordinates.", ge=0.0)
    hour_of_day: int = Field(..., description="Hour of transaction execution (0 to 23).", ge=0, le=23)
    day_of_week: int = Field(..., description="Day of the week of transaction execution (0 to 6).", ge=0, le=6)
    velocity_1h: int = Field(..., description="Number of user transactions in the last hour.", ge=0)
    velocity_24h: int = Field(..., description="Number of user transactions in the last 24 hours.", ge=0)
    recipient_in_degree: int = Field(..., description="Number of unique sending accounts to this receiver in 24h.", ge=0)
    sender_out_degree: int = Field(..., description="Number of unique receiving accounts from this sender in 24h.", ge=0)
    sender_id: Optional[str] = Field(None, description="Sender account ID.")
    receiver_id: Optional[str] = Field(None, description="Receiver account ID.")
    timestamp: Optional[str] = Field(None, description="Transaction timestamp.")


class RiskFactorSchema(BaseModel):
    factor: str = Field(..., description="Brief description of the risk alert trigger.")
    category: str = Field(..., description="Core risk classification category.")
    severity: str = Field(..., description="Alert severity level.")
    contribution: float = Field(..., description="Exact score contribution out of 100.")


class SHAPContributionSchema(BaseModel):
    feature: str = Field(..., description="Model feature name.")
    value: Optional[float] = Field(..., description="Actual feature value passed in.")
    shap_value: float = Field(..., description="Log-odds contribution value computed by SHAP.")
    direction: str = Field(..., description="Direction of contribution ('increases_risk' or 'decreases_risk').")
    human_readable: str = Field(..., description="User-friendly diagnostic text explanation.")


class SHAPExplanationSchema(BaseModel):
    base_value: float = Field(..., description="Model expected base prediction value in log-odds.")
    contributions: List[SHAPContributionSchema] = Field(..., description="Feature contribution lists.")


class NetworkIntelligenceSchema(BaseModel):
    network_risk: float = Field(..., description="Network risk score from 0 to 100.")
    mule_risk: float = Field(..., description="Mule risk score from 0 to 100.")
    indicators: List[str] = Field(..., description="List of detected network risk factors.")
    metrics: dict = Field(..., description="Key-value dictionary of network metrics.")
    suspicious_connections: List[dict] = Field(..., description="List of suspicious counterparties.")


class TransactionAnalysisResponse(BaseModel):
    fraud_probability: float = Field(..., description="Supervised XGBoost fraud probability prediction (0.0 to 1.0).")
    anomaly_score: float = Field(..., description="Unsupervised Isolation Forest anomaly score (-decision_function()).")
    supervised_risk: float = Field(..., description="Normalized supervised risk contribution score (0 to 100).")
    anomaly_risk: float = Field(..., description="Normalized unsupervised anomaly risk score (0 to 100).")
    behavioral_risk: float = Field(..., description="Consolidated user behavioral deviation risk score (0 to 100).")
    network_risk: float = Field(..., description="Consolidated network flow path risk score (0 to 100).")
    risk_score: float = Field(..., description="Consolidated final decision prioritization score (0 to 100).")
    risk_level: str = Field(..., description="Risk category level: LOW, MEDIUM, HIGH, or CRITICAL.")
    risk_factors: List[RiskFactorSchema] = Field(..., description="Diagnosed triggering risk alerts.")
    shap_explanation: SHAPExplanationSchema = Field(..., description="SHAP feature attribution explanations.")
    network_intelligence: Optional[NetworkIntelligenceSchema] = Field(None, description="Detailed network graph intelligence metrics.")
