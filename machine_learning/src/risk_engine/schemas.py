"""
TRUSTNET - Risk Engine Data Schemas
Defines input and output structures for the Risk Scorer.
"""

from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class RiskInput:
    """
    Input parameters representing transaction signals and ML model outputs.
    """
    amount: float
    amount_deviation: Optional[float]
    is_new_device: int
    is_new_ip: int
    location_deviation_km: Optional[float]
    velocity_1h: int
    velocity_24h: int
    recipient_in_degree: int
    sender_out_degree: int
    fraud_probability: float
    anomaly_score: float
    network_risk_override: Optional[float] = None

    def validate(self):
        """
        Ensures input signals are within mathematically and physically correct bounds.
        """
        if self.amount < 0:
            raise ValueError(f"Amount must be non-negative: {self.amount}")
        
        if not (0.0 <= self.fraud_probability <= 1.0):
            raise ValueError(f"Fraud probability must be in [0, 1]: {self.fraud_probability}")
            
        # Velocity and degree inputs must be non-negative
        for name, val in [
            ("is_new_device", self.is_new_device),
            ("is_new_ip", self.is_new_ip),
            ("velocity_1h", self.velocity_1h),
            ("velocity_24h", self.velocity_24h),
            ("recipient_in_degree", self.recipient_in_degree),
            ("sender_out_degree", self.sender_out_degree)
        ]:
            if val < 0:
                raise ValueError(f"{name} must be non-negative: {val}")


@dataclass
class RiskFactor:
    """
    Represents an individual risk factor contributing to the overall threat score.
    """
    factor: str
    category: str      # e.g., 'supervised_ml', 'unsupervised_ml', 'behavioral', 'network'
    severity: str      # e.g., 'low', 'medium', 'high'
    contribution: float  # Weighted points contributed (out of 100)


@dataclass
class RiskOutput:
    """
    Unified TRUSTNET risk assessment containing consolidated scores, levels,
    and diagnostic factors.
    """
    risk_score: float
    risk_level: str
    fraud_probability: float
    anomaly_score: float
    supervised_risk: float
    anomaly_risk: float
    behavioral_risk: float
    network_risk: float
    risk_factors: List[RiskFactor] = field(default_factory=list)
