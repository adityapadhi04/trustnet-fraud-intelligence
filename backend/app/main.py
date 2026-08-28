"""
TRUSTNET - FastAPI Backend Entrypoint
Registers modular routers, configures restricted CORS policies, and serves
the baseline health and metadata endpoints.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routes import risk, transactions, model, network, alerts, reports, monitor
from backend.app.models_loader import get_models_status

app = FastAPI(
    title="TRUSTNET - Fraud Intelligence Platform",
    description="Prototype decision-support API for payment risk, behavior anomaly, and fraud network analysis.",
    version="0.1.0",
)

# Configure CORS restricted origins to support React client development
# http://localhost:3000 (React default), http://localhost:5173 (Vite default)
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://trustnet-fraud-intelligence.vercel.app",
    "https://trustnet-fraud-intelligence.vercel.app/"
]

# Read optional deployed Vercel frontend URL from environment configuration
frontend_url_env = os.getenv("FRONTEND_URL")
if frontend_url_env:
    # Allow multiple origins separated by commas
    origins_from_env = [origin.strip() for origin in frontend_url_env.split(",") if origin.strip()]
    ALLOWED_ORIGINS.extend(origins_from_env)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex="https://trustnet-.*\\.vercel\\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register modular routers
app.include_router(risk.router)
app.include_router(transactions.router)
app.include_router(model.router)
app.include_router(network.router)
app.include_router(alerts.router)
app.include_router(reports.router)
app.include_router(monitor.router)


@app.get("/")
async def root():
    """
    Root endpoint showing API metadata.
    """
    return {
        "project": "TRUSTNET",
        "status": "initialized",
        "description": "AI-powered financial fraud intelligence decision-support API",
        "scope": "prototype-only",
    }


@app.get("/health")
async def health_check():
    """
    Dynamic health status reporting engine and model loading status.
    """
    status_info = get_models_status()
    
    # Platform models are fully loaded if both XGBoost and Isolation Forest are available
    models_loaded = status_info["xgboost_available"] and status_info["isolation_forest_available"]
    
    return {
        "status": "healthy",
        "api_version": "0.1.0",
        "database_connected": status_info["dataset_available"],
        "models_loaded": models_loaded
    }
