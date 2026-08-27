"""
TRUSTNET - Transactions Retrieval Endpoints
Exposes existing synthetic records and processed features from the dataset
for prototype visualization and local API verification.
"""

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, status
from backend.app.schemas.transactions import SampleTransactionsResponse
from backend.app.models_loader import get_transactions_df, get_models_status

router = APIRouter(prefix="/api/v1/transactions", tags=["Transactions Database"])


def _clean_nans(record_dict: dict) -> dict:
    """Helper to convert float NaNs and infs into serializable None values."""
    cleaned = {}
    for k, v in record_dict.items():
        if pd.isna(v):
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned


@router.get(
    "/sample",
    response_model=SampleTransactionsResponse,
    summary="Get sample synthetic transactions",
    description="Returns a configurable number of processed transactions from the synthetic dataset."
)
async def get_sample_transactions(
    limit: int = Query(10, description="Number of records to return (1-100).", ge=1, le=100)
):
    status_check = get_models_status()
    if not status_check["dataset_available"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Synthetic transaction dataset not found on the server. Please run preprocessing."
        )

    try:
        df = get_transactions_df()
        # Get head rows up to limit
        sub_df = df.head(limit)
        
        records = []
        for idx, row in sub_df.iterrows():
            records.append(_clean_nans(row.to_dict()))
            
        return {
            "source": "TRUSTNET_SYNTHETIC_SIMULATION",
            "records_returned": len(records),
            "transactions": records
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query synthetic database: {str(e)}"
        )


@router.get(
    "/{transaction_id}",
    summary="Retrieve transaction by ID",
    description="Lookup a specific synthetic transaction and return its processed feature records."
)
async def get_transaction_by_id(transaction_id: str):
    status_check = get_models_status()
    if not status_check["dataset_available"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Synthetic transaction dataset not found on the server. Please run preprocessing."
        )

    try:
        df = get_transactions_df()
        # Find matching transaction_id string
        match = df[df["transaction_id"] == transaction_id]
        if match.empty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction with ID '{transaction_id}' not found in the database."
            )
            
        record = match.iloc[0].to_dict()
        return _clean_nans(record)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error querying transaction '{transaction_id}': {str(e)}"
        )
