"""
TRUSTNET - Reports Endpoints
Computes analytical platform statistics and serves downloadable alert reports.
"""

import io
import csv
import pandas as pd
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from backend.app.routes.alerts import AlertsStore, _db_lock
from backend.app.models_loader import get_transactions_df, get_models_status

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


@router.get(
    "/summary",
    summary="Get platform reports summary",
    description="Calculates overview metrics, risk level distributions, and network indicator summaries."
)
async def get_reports_summary() -> Dict[str, Any]:
    status_check = get_models_status()
    if not status_check["dataset_available"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Synthetic transaction dataset not found. Cannot compute reports."
        )

    try:
        # Load transactions dataframe (cached)
        df = get_transactions_df()
        total_tx = len(df)
        fraud_lbl_count = int(df["is_fraud_labeled"].sum())

        # Load alerts from AlertsStore
        with _db_lock:
            alerts_db = AlertsStore.load_all()
        alerts = list(alerts_db.values())

        # Compute metrics based on alerts
        high_risk_alerts = [a for a in alerts if a["severity"] in ("HIGH", "CRITICAL")]
        open_alerts = [a for a in alerts if a["status"] in ("OPEN", "INVESTIGATING")]
        anomalies = [a for a in alerts if a["alert_type"] == "ANOMALY"]
        mules = [a for a in alerts if a["alert_type"] == "POTENTIAL_MULE"]
        net_risks = [a for a in alerts if a["alert_type"] == "NETWORK_RISK"]

        # Risk distribution counts
        risk_dist = {
            "low": len([a for a in alerts if a["severity"] == "LOW"]),
            "medium": len([a for a in alerts if a["severity"] == "MEDIUM"]),
            "high": len([a for a in alerts if a["severity"] == "HIGH"]),
            "critical": len([a for a in alerts if a["severity"] == "CRITICAL"])
        }

        # Recent alerts (top 5 newest)
        sorted_alerts = sorted(alerts, key=lambda x: x["created_at"], reverse=True)
        recent_alerts = sorted_alerts[:5]

        # Top risk factors aggregation
        factor_counts = {}
        for a in alerts:
            reason = a["primary_reason"]
            factor_counts[reason] = factor_counts.get(reason, 0) + 1
            
        sorted_factors = sorted(factor_counts.items(), key=lambda x: x[1], reverse=True)
        top_risk_factors = [{"factor": k, "count": v} for k, v in sorted_factors[:5]]

        # Network intelligence summary stats
        # Collect unique transaction IDs from alerts to map back to their sender_ids
        suspicious_senders = set()
        alert_tx_ids = {a["transaction_id"] for a in alerts}
        if not df.empty and alert_tx_ids:
            matching_txs = df[df["transaction_id"].isin(alert_tx_ids)]
            suspicious_senders = set(matching_txs["sender_id"].dropna().unique())

        # Calculate transaction volume timeline (group by date)
        transaction_timeline = []
        try:
            if not df.empty and "timestamp" in df.columns:
                df_temp = df.copy()
                df_temp["date"] = pd.to_datetime(df_temp["timestamp"]).dt.strftime("%Y-%m-%d")
                tx_counts = df_temp.groupby("date").size().reset_index(name="count")
                tx_counts = tx_counts.sort_values("date")
                transaction_timeline = tx_counts.to_dict(orient="records")
        except Exception as e:
            print(f"Failed to calculate transaction timeline: {str(e)}")

        # Calculate alert volume timeline (group by date)
        alert_timeline = []
        try:
            from collections import Counter
            alert_dates = []
            for a in alerts:
                created_at_str = a.get("created_at")
                if created_at_str:
                    date_part = created_at_str.split(" ")[0]
                    alert_dates.append(date_part)
            date_counts = Counter(alert_dates)
            alert_timeline = [{"date": d, "count": c} for d, c in sorted(date_counts.items())]
        except Exception as e:
            print(f"Failed to calculate alert timeline: {str(e)}")

        return {
            "overview_stats": {
                "total_transactions": total_tx,
                "high_risk_transactions": len(high_risk_alerts),
                "fraud_predictions": fraud_lbl_count,
                "anomalies_detected": len(anomalies),
                "open_alerts": len(open_alerts),
                "potential_mule_findings": len(mules)
            },
            "risk_distribution": risk_dist,
            "recent_alerts": recent_alerts,
            "top_risk_factors": top_risk_factors,
            "network_summary": {
                "suspicious_accounts_count": len(suspicious_senders),
                "potential_mule_indicators_count": len(mules),
                "high_risk_network_activity_count": len(net_risks)
            },
            "transaction_timeline": transaction_timeline,
            "alert_timeline": alert_timeline
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate reports summary: {str(e)}"
        )


@router.get(
    "/download",
    summary="Download alerts report as CSV",
    description="Generates and streams a CSV report containing the details of all alerts in the system."
)
async def download_alerts_csv():
    try:
        with _db_lock:
            alerts_db = AlertsStore.load_all()
        alerts = list(alerts_db.values())
        
        # Sort by creation time newest first
        alerts = sorted(alerts, key=lambda x: x["created_at"], reverse=True)

        output = io.StringIO()
        writer = csv.writer(output)
        
        # CSV Headers
        writer.writerow([
            "Alert ID", 
            "Transaction ID", 
            "Severity", 
            "Risk Score", 
            "Risk Level", 
            "Alert Type", 
            "Primary Reason", 
            "Status", 
            "Created At"
        ])
        
        # Write rows
        for a in alerts:
            writer.writerow([
                a["alert_id"],
                a["transaction_id"],
                a["severity"],
                a["risk_score"],
                a["risk_level"],
                a["alert_type"],
                a["primary_reason"],
                a["status"],
                a["created_at"]
            ])
            
        csv_data = output.getvalue()
        output.close()

        headers = {
            "Content-Disposition": "attachment; filename=trustnet_alerts_report.csv",
            "Content-Type": "text/csv"
        }
        return Response(content=csv_data, headers=headers, media_type="text/csv")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download report: {str(e)}"
        )
