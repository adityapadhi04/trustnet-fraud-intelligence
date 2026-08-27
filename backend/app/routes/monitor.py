"""
TRUSTNET - Live Transaction Stream Simulator
Traverses the synthetic dataset sequentially to simulate a real-time stream of incoming bank transactions.
"""

import threading
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
import pandas as pd

from backend.app.models_loader import get_transactions_df, get_models_status
from backend.app.routes.risk import analyze_transaction
from backend.app.schemas.risk import TransactionAnalysisRequest
from backend.app.routes.alerts import AlertsStore, _db_lock

router = APIRouter(prefix="/api/v1/monitor", tags=["Live Monitor"])


class LiveMonitorState:
    """Thread-safe state manager for live simulator cursor and metrics."""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.cursor = 0
        self.transactions_processed = 0
        self.last_transaction_time = None
        self.high_risk_count = 0
        self.demo_mode = False

    def reset(self):
        with self.lock:
            self.cursor = 0
            self.transactions_processed = 0
            self.last_transaction_time = None
            self.high_risk_count = 0
            self.demo_mode = False


# Singleton global simulator state
monitor_state = LiveMonitorState()


def _clean_nans(record_dict: dict) -> dict:
    """Helper to convert float NaNs into serializable None values."""
    cleaned = {}
    for k, v in record_dict.items():
        if pd.isna(v):
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned


@router.get(
    "/next",
    summary="Get next transaction in the stream",
    description="Fetches the next row sequentially from the synthetic dataset, executes the risk engine pipeline, and creates alerts."
)
async def get_next_transaction():
    status_check = get_models_status()
    if not status_check["dataset_available"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Synthetic dataset not available on the server. Please verify setup."
        )

    try:
        df = get_transactions_df()
        total_txs = len(df)
        if total_txs == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction dataset is empty."
            )

        is_demo_tx = False
        with monitor_state.lock:
            current_cursor = monitor_state.cursor
            # Advance cursor index sequentially, looping back to 0 at the end
            monitor_state.cursor = (current_cursor + 1) % total_txs
            
            # Retrieve transaction row
            row = df.iloc[current_cursor]
            tx_dict = _clean_nans(row.to_dict())
            
            # Map parameters into request schema to pass to the risk scorer
            req_obj = TransactionAnalysisRequest(**tx_dict)
            
            if monitor_state.demo_mode and (monitor_state.transactions_processed + 1) % 5 == 0:
                is_demo_tx = True
                req_obj.demo_event = True

        # Call existing risk analysis pipeline (XGBoost, Isolation Forest, Network Risk, SHAP)
        # This will also automatically trigger add_alert_for_transaction if risk_score >= 40
        analysis_result = await analyze_transaction(req_obj)

        # Update metrics after successful analysis
        wall_clock_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with monitor_state.lock:
            monitor_state.transactions_processed += 1
            monitor_state.last_transaction_time = wall_clock_time
            if analysis_result.get("risk_level") in ("HIGH", "CRITICAL") or analysis_result.get("risk_score", 0.0) >= 60.0:
                monitor_state.high_risk_count += 1

        return {
            "transaction": tx_dict,
            "analysis": analysis_result,
            "sequence_number": current_cursor + 1,
            "total_transactions": total_txs,
            "timestamp": wall_clock_time,
            "demo_event": is_demo_tx
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process live transaction: {str(e)}"
        )


@router.get(
    "/status",
    summary="Get simulator dashboard status",
    description="Returns aggregate simulation metrics and system online state."
)
async def get_monitor_status():
    status_check = get_models_status()
    # System is online if models are loaded and dataset is available
    online = (
        status_check["dataset_available"] 
        and status_check["xgboost_available"] 
        and status_check["isolation_forest_available"]
    )

    with _db_lock:
        alerts_db = AlertsStore.load_all()
    alert_count = len(alerts_db)

    with monitor_state.lock:
        processed = monitor_state.transactions_processed
        last_time = monitor_state.last_transaction_time
        high_risk = monitor_state.high_risk_count
        demo_mode = monitor_state.demo_mode

    return {
        "online": online,
        "transactions_processed": processed,
        "last_transaction_time": last_time,
        "high_risk_count": high_risk,
        "alert_count": alert_count,
        "demo_mode": demo_mode
    }


@router.get("/demo_mode", summary="Get current demo mode state")
async def get_demo_mode():
    with monitor_state.lock:
        return {"demo_mode": monitor_state.demo_mode}


@router.post("/demo_mode", summary="Toggle demo mode state")
async def set_demo_mode(payload: dict):
    val = payload.get("demo_mode", False)
    with monitor_state.lock:
        monitor_state.demo_mode = val
        return {"demo_mode": monitor_state.demo_mode}
