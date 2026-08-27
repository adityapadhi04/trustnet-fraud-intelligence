"""
TRUSTNET - Model Status Endpoints
Returns status availability and metadata for XGBoost, Isolation Forest,
and SHAP modules.
"""

from fastapi import APIRouter
from backend.app.models_loader import get_models_status

router = APIRouter(prefix="/api/v1/model", tags=["Model Analytics"])

MODEL_FEATURES = [
    "amount", "amount_deviation", "is_new_device", "is_new_ip", "location_deviation_km",
    "hour_of_day", "day_of_week", "velocity_1h", "velocity_24h", "recipient_in_degree",
    "sender_out_degree"
]


@router.get(
    "/status",
    summary="Retrieve model pipeline status",
    description="Returns platform availability status of trained AI models and feature schemas."
)
async def get_model_pipeline_status():
    status_info = get_models_status()
    
    return {
        "xgboost_loaded": status_info["xgboost_available"],
        "isolation_forest_loaded": status_info["isolation_forest_available"],
        "shap_loaded": status_info["shap_available"],
        "features_count": len(MODEL_FEATURES),
        "features": MODEL_FEATURES,
        "prototype_version": "0.1.0"
    }
