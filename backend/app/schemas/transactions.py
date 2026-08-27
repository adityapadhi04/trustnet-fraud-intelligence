"""
TRUSTNET - Transactions Retrieval Pydantic Schemas
Defines request and response schemas for transaction data lookup.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any

class SampleTransactionsResponse(BaseModel):
    source: str = Field("TRUSTNET_SYNTHETIC_SIMULATION", description="Data generation engine classification.")
    records_returned: int = Field(..., description="Number of transaction records in the payload.")
    transactions: List[Dict[str, Any]] = Field(..., description="List of transaction records containing features and ground-truth values.")
