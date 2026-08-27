"""
TRUSTNET - Network Intelligence Endpoints
Exposes graph metrics, mule patterns, and ego-network visualization data
for interactive forensic network investigation.
"""

from fastapi import APIRouter, HTTPException, status
from backend.app.models_loader import get_network_engine, get_models_status
from typing import Dict, Any, List, Optional
import pandas as pd

router = APIRouter(prefix="/api/v1/network", tags=["Network Intelligence"])


@router.get(
    "/{account_id}",
    summary="Retrieve account network profile",
    description="Loads the 1-hop ego network graph and computes connectivity, concentration, and mule indicators."
)
async def get_account_network_profile(account_id: str, before_timestamp: Optional[str] = None):
    # 1. Verify dataset / models status
    status_check = get_models_status()
    if not status_check["dataset_available"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Synthetic dataset not available. Please run preprocessing."
        )

    try:
        net_engine = get_network_engine()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load Network Intelligence Engine: {str(e)}"
        )

    # 2. Check if the account exists in the global transaction graph
    account_str = str(account_id)
    if not net_engine.G.has_node(account_str):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with ID '{account_id}' not found in the transaction graph."
        )

    try:
        # Parse before_timestamp
        before_ts = None
        if before_timestamp:
            try:
                before_ts = pd.to_datetime(before_timestamp)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid before_timestamp format: '{before_timestamp}'"
                )

        # 3. Calculate all indicators
        metrics = net_engine.get_account_metrics(account_str, before_timestamp=before_ts)
        patterns = net_engine.check_mule_patterns(account_str, before_timestamp=before_ts)
        net_risk = net_engine.calculate_account_network_risk(account_str, before_timestamp=before_ts)
        indicators = net_engine.generate_explanations(account_str, before_timestamp=before_ts)
        ego = net_engine.get_ego_network(account_str, before_timestamp=before_ts)
        
        # Calculate mule risk percentage
        mule_risk = 0.0
        active_patterns = [k for k, v in patterns.items() if v]
        if active_patterns:
            mule_risk = min(100.0, len(active_patterns) * 20.0 + (net_risk * 0.4))

        # Extract predecessor/successor unique counterparties list
        incoming_conns = []
        for u, v, data in net_engine.G.in_edges(account_str, data=True):
            if before_ts is None or data["timestamp"] <= before_ts:
                incoming_conns.append(u)
        incoming_conns = list(set(incoming_conns))

        outgoing_conns = []
        for u, v, data in net_engine.G.out_edges(account_str, data=True):
            if before_ts is None or data["timestamp"] <= before_ts:
                outgoing_conns.append(v)
        outgoing_conns = list(set(outgoing_conns))

        connected_accounts = list(set(incoming_conns + outgoing_conns))

        # Build response payload, ensuring absolute data safety (excluding is_fraud_labeled)
        return {
            "account_id": account_str,
            "network_risk": net_risk,
            "mule_risk": round(mule_risk, 2),
            "incoming_connections": len(incoming_conns),
            "outgoing_connections": len(outgoing_conns),
            "indicators": indicators,
            "network_metrics": {
                "incoming_amount": metrics["incoming_amount"],
                "outgoing_amount": metrics["outgoing_amount"],
                "incoming_tx_count": metrics["incoming_tx_count"],
                "outgoing_tx_count": metrics["outgoing_tx_count"],
                "total_network_tx_count": metrics["total_network_tx_count"],
                "rapid_pass_through_count": len(net_engine.detect_rapid_pass_through_events(account_str))
            },
            "connected_accounts": connected_accounts,
            "relevant_transaction_relationships": {
                "nodes": ego["nodes"],
                "edges": ego["edges"]
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forensic network analysis execution failed for account '{account_id}': {str(e)}"
        )
