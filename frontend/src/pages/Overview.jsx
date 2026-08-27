import React, { useState, useEffect } from 'react';
import { fetchHealth, fetchModelStatus, fetchSampleTransactions } from '../services/api';

function Overview() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [health, setHealth] = useState(null);
  const [modelStatus, setModelStatus] = useState(null);
  const [sampleCount, setSampleCount] = useState(0);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [healthData, modelData, sampleData] = await Promise.all([
          fetchHealth(),
          fetchModelStatus(),
          fetchSampleTransactions(100) // Request larger limit to see count
        ]);

        setHealth(healthData);
        setModelStatus(modelData);
        setSampleCount(sampleData.transactions ? sampleData.transactions.length : 0);
        setError(null);
      } catch (err) {
        console.error('Failed to load Overview data:', err);
        setError(err.message || 'Unable to connect to TRUSTNET API.');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  if (loading) {
    return (
      <div className="loading-state">
        <div className="spinner"></div>
        <p>Retrieving TRUSTNET status...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-alert-box" style={{ marginTop: '20px' }}>
        <strong>System Error:</strong> {error}
        <p style={{ marginTop: '8px', fontSize: '12px' }}>
          Ensure the FastAPI backend is running at http://127.0.0.1:8000 and try again.
        </p>
      </div>
    );
  }

  return (
    <div className="overview-page">
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '4px' }}>Platform Overview</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
          Diagnostic view of loaded AI models, database states, and prototype parameters.
        </p>
      </div>

      <div className="overview-grid">
        {/* API Health Card */}
        <div className="card">
          <div className="card-title">System Connectivity</div>
          <div className="card-value" style={{ color: health?.status === 'healthy' ? 'var(--color-success)' : 'var(--color-danger)' }}>
            {health?.status === 'healthy' ? 'ACTIVE' : 'DEGRADED'}
          </div>
          <div className="card-detail-list">
            <div className="card-detail-item">
              <span className="card-detail-label">API Version</span>
              <span className="card-detail-value">{health?.api_version}</span>
            </div>
            <div className="card-detail-item">
              <span className="card-detail-label">Database Connected</span>
              <span className="card-detail-value">
                <span className={`badge ${health?.database_connected ? 'success' : 'danger'}`}>
                  {health?.database_connected ? 'CONNECTED' : 'DISCONNECTED'}
                </span>
              </span>
            </div>
          </div>
        </div>

        {/* AI Pipelines Card */}
        <div className="card">
          <div className="card-title">AI Pipelines Status</div>
          <div className="card-value">
            {modelStatus?.features_count} <span style={{ fontSize: '16px', color: 'var(--text-muted)' }}>features</span>
          </div>
          <div className="card-detail-list">
            <div className="card-detail-item">
              <span className="card-detail-label">XGBoost Classifier</span>
              <span className="card-detail-value">
                <span className={`badge ${modelStatus?.xgboost_loaded ? 'success' : 'danger'}`}>
                  {modelStatus?.xgboost_loaded ? 'LOADED' : 'MISSING'}
                </span>
              </span>
            </div>
            <div className="card-detail-item">
              <span className="card-detail-label">Isolation Forest</span>
              <span className="card-detail-value">
                <span className={`badge ${modelStatus?.isolation_forest_loaded ? 'success' : 'danger'}`}>
                  {modelStatus?.isolation_forest_loaded ? 'LOADED' : 'MISSING'}
                </span>
              </span>
            </div>
            <div className="card-detail-item">
              <span className="card-detail-label">SHAP Explainer</span>
              <span className="card-detail-value">
                <span className={`badge ${modelStatus?.shap_loaded ? 'success' : 'danger'}`}>
                  {modelStatus?.shap_loaded ? 'ACTIVE' : 'INACTIVE'}
                </span>
              </span>
            </div>
          </div>
        </div>

        {/* Datasets Card */}
        <div className="card">
          <div className="card-title">Dataset Metrics</div>
          <div className="card-value">{sampleCount}</div>
          <div className="card-detail-list">
            <div className="card-detail-item">
              <span className="card-detail-label">Dataset Source</span>
              <span className="card-detail-value" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                TRUSTNET_SYNTHETIC_SIMULATION
              </span>
            </div>
            <div className="card-detail-item">
              <span className="card-detail-label">Dataset State</span>
              <span className="card-detail-value">
                <span className="badge success">AVAILABLE</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="card" style={{ gap: '8px' }}>
        <div className="card-title">Model Features Order</div>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '10px' }}>
          The following features are extracted and engineered in the exact sequence expected by the classifier:
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {modelStatus?.features.map((feat, i) => (
            <span key={feat} className="badge" style={{ fontFamily: 'var(--font-mono)', padding: '4px 8px' }}>
              {i + 1}. {feat}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export default Overview;
