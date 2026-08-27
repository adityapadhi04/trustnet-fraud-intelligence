"""
TRUSTNET - Alerts Pydantic Schemas
Defines request validation and response models for the alert management endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class AlertStatus(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class AlertType(str, Enum):
    FRAUD_RISK = "FRAUD_RISK"
    ANOMALY = "ANOMALY"
    NETWORK_RISK = "NETWORK_RISK"
    POTENTIAL_MULE = "POTENTIAL_MULE"


class AlertResponse(BaseModel):
    alert_id: str = Field(..., description="Unique alert identifier.")
    transaction_id: str = Field(..., description="Associated transaction identifier.")
    severity: str = Field(..., description="Alert severity (LOW, MEDIUM, HIGH, CRITICAL).")
    risk_score: float = Field(..., description="Consolidated risk score (0 to 100).")
    risk_level: str = Field(..., description="Categorical risk level.")
    alert_type: AlertType = Field(..., description="Type of alert triggered.")
    primary_reason: str = Field(..., description="Primary reason or factor for triggering the alert.")
    status: AlertStatus = Field(..., description="Current lifecycle status of the alert.")
    created_at: str = Field(..., description="Alert creation timestamp.")


class AlertPatchRequest(BaseModel):
    status: AlertStatus = Field(..., description="Updated lifecycle status for the alert.")
