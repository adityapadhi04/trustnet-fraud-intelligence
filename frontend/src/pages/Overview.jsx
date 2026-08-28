import React, { useState, useEffect, useRef } from 'react';
import { fetchHealth, fetchModelStatus, fetchMonitorNext, fetchMonitorStatus } from '../services/api';

function Overview({ setSelectedTx, setAnalysisResult, onNavigate, demoMode, setDemoMode, handleToggleDemo }) {
  // Original overview page states
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [health, setHealth] = useState(null);
  const [modelStatus, setModelStatus] = useState(null);
  const [featuresList, setFeaturesList] = useState([]);

  // Live monitor states
  const [systemOnline, setSystemOnline] = useState(true);
  const [monitorStats, setMonitorStats] = useState({
    transactions_processed: 0,
    high_risk_count: 0,
    alert_count: 0,
    last_transaction_time: null
  });
  const [liveFeed, setLiveFeed] = useState([]);
  
  // Last transaction elapsed time tracking
  const [secondsSinceLast, setSecondsSinceLast] = useState(null);
  const lastTxRef = useRef(null);

  // Initialize and load baseline diagnostics on mount
  useEffect(() => {
    async function loadDiagnostics() {
      try {
        setLoading(true);
        const [healthData, modelData] = await Promise.all([
          fetchHealth(),
          fetchModelStatus()
        ]);
        setHealth(healthData);
        setModelStatus(modelData);
        if (modelData && modelData.features) {
          setFeaturesList(modelData.features);
        }
        setError(null);
      } catch (err) {
        console.error('Failed to load Overview diagnostics:', err);
        setError(err.message || 'Unable to connect to TRUSTNET API.');
      } finally {
        setLoading(false);
      }
    }
    loadDiagnostics();
  }, []);

  // Poll simulator metrics from /monitor/status
  useEffect(() => {
    async function checkMonitorStatus() {
      try {
        const stats = await fetchMonitorStatus();
        setMonitorStats(stats);
        setSystemOnline(stats.online);
        if (stats.demo_mode !== undefined) {
          setDemoMode(stats.demo_mode);
        }
      } catch (err) {
        console.error('Failed to query monitor status:', err);
        setSystemOnline(false);
      }
    }

    checkMonitorStatus();
    const interval = setInterval(checkMonitorStatus, 3000); // Check status every 3s
    return () => clearInterval(interval);
  }, [setDemoMode]);



  // Poll next transaction from /monitor/next
  useEffect(() => {
    async function pollNextTransaction() {
      if (!systemOnline) return;
      try {
        const result = await fetchMonitorNext();
        if (result && result.transaction) {
          // Append new transaction to the top of the feed list
          setLiveFeed(prev => {
            const updated = [result, ...prev];
            return updated.slice(0, 10); // Keep last 10 transactions in feed
          });
          // Update last transaction timestamp and reset elapsed seconds counter
          lastTxRef.current = new Date();
          setSecondsSinceLast(0);
        }
      } catch (err) {
        console.error('Failed to fetch next live transaction:', err);
      }
    }

    const delay = demoMode ? 2500 : 3500;
    const interval = setInterval(pollNextTransaction, delay);
    return () => clearInterval(interval);
  }, [systemOnline, demoMode]);

  // Elapsed seconds timer for last transaction processed
  useEffect(() => {
    const timer = setInterval(() => {
      if (lastTxRef.current) {
        const diffMs = new Date() - lastTxRef.current;
        setSecondsSinceLast(Math.floor(diffMs / 1000));
      }
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Render elapsed seconds label helper
  const renderLastTxTime = () => {
    if (secondsSinceLast === null) return 'No transactions processed';
    if (secondsSinceLast < 2) return 'Just now';
    return `${secondsSinceLast} sec ago`;
  };

  // Navigate analyst to the risk workspace for detailed analysis of the clicked record
  const handleTxRowClick = (item) => {
    setSelectedTx(item.transaction);
    setAnalysisResult(item.analysis);
    onNavigate('risk');
  };

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
          Unable to connect to the TRUSTNET API. Please try again.
        </p>
      </div>
    );
  }

  return (
    <div className="overview-page" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Top Welcome Title */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '4px' }}>Platform Workspace</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
            Decision-support monitoring console for payments flow and anomaly auditing.
          </p>
        </div>
      </div>

      {/* COMPONENT 5 — LIVE STREAM MONITOR PANEL */}
      <div 
        className="card" 
        style={{ 
          borderLeft: `4px solid ${systemOnline ? 'var(--color-success)' : 'var(--color-danger)'}`,
          padding: '24px', 
          display: 'flex', 
          flexDirection: 'column', 
          gap: '20px',
          background: 'radial-gradient(ellipse at top right, rgba(56, 189, 248, 0.04), transparent), var(--bg-card)'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '15px', fontWeight: '700', letterSpacing: '0.5px' }}>
              🛡️ TRUSTNET LIVE MONITOR
            </span>
            {systemOnline && (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--color-success)', fontWeight: '600', backgroundColor: 'rgba(16, 185, 129, 0.1)', padding: '2px 8px', borderRadius: '12px' }}>
                <span style={{ width: '6px', height: '6px', backgroundColor: 'var(--color-success)', borderRadius: '50%', boxShadow: '0 0 8px var(--color-success)' }}></span>
                LIVE STREAMING
              </span>
            )}
            {/* DEMO MODE PRESENTATION TOGGLE BUTTON */}
            <button
              onClick={handleToggleDemo}
              style={{
                cursor: 'pointer',
                border: '1px solid',
                backgroundColor: demoMode ? 'rgba(239, 68, 68, 0.12)' : 'rgba(255, 255, 255, 0.02)',
                borderColor: demoMode ? '#EF4444' : 'var(--border-color)',
                color: demoMode ? '#EF4444' : 'var(--text-secondary)',
                fontSize: '11px',
                fontWeight: '700',
                padding: '4px 10px',
                borderRadius: 'var(--radius-sm)',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                transition: 'all 0.25s ease',
                boxShadow: demoMode ? '0 0 10px rgba(239, 68, 68, 0.25)' : 'none'
              }}
              title="Toggle Demo Mode: When enabled, every 5th transaction is forced to be a CRITICAL risk incident."
            >
              {demoMode ? '⏹ DEMO MODE: ON' : '▶ DEMO MODE: OFF'}
            </button>
          </div>
          <span 
            style={{ 
              fontSize: '12px', 
              fontWeight: '800', 
              letterSpacing: '0.5px',
              color: systemOnline ? 'var(--color-success)' : 'var(--color-danger)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <span style={{ 
              width: '8px', 
              height: '8px', 
              borderRadius: '50%', 
              backgroundColor: systemOnline ? 'var(--color-success)' : 'var(--color-danger)',
              boxShadow: `0 0 8px ${systemOnline ? 'var(--color-success)' : 'var(--color-danger)'}`
            }}></span>
            {systemOnline ? 'SYSTEM ONLINE' : 'SYSTEM OFFLINE'}
          </span>
        </div>

        {demoMode && (
          <div style={{ 
            backgroundColor: 'rgba(239, 68, 68, 0.08)',
            border: '1px solid rgba(239, 68, 68, 0.25)',
            borderRadius: 'var(--radius-sm)',
            padding: '12px 16px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '12px',
            color: '#F87171',
            fontWeight: '700',
            boxShadow: '0 0 10px rgba(239, 68, 68, 0.05)'
          }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <span style={{ textTransform: 'uppercase', letterSpacing: '0.5px' }}>DEMO SIMULATION ACTIVE</span>
              <span style={{ color: 'var(--text-muted)', fontSize: '11px', fontWeight: '500' }}>
                Controlled critical event every 5 transactions
              </span>
            </div>
            <div style={{ 
              fontFamily: 'var(--font-mono)', 
              backgroundColor: 'rgba(239, 68, 68, 0.15)', 
              padding: '4px 10px', 
              borderRadius: 'var(--radius-sm)',
              fontSize: '11px',
              border: '1px solid rgba(239, 68, 68, 0.2)'
            }}>
              {(monitorStats.transactions_processed % 5 === 0 && monitorStats.transactions_processed > 0) ? (
                <span style={{ color: '#EF4444' }}>🚨 CRITICAL EVENT</span>
              ) : (
                <span>Demo cycle: {(monitorStats.transactions_processed % 5)} / 5</span>
              )}
            </div>
          </div>
        )}

        <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginTop: '-8px' }}>
          Monitoring incoming bank transaction stream. Running real-time XGBoost risk scoring and Isolation Forest anomaly profiling.
        </p>

        {/* Live Simulator Metrics Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', marginTop: '4px' }}>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', backgroundColor: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', padding: '12px 16px', borderRadius: 'var(--radius-sm)' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>Transactions Monitored</span>
            <span style={{ fontSize: '24px', fontWeight: '700', fontFamily: 'var(--font-mono)' }}>
              {monitorStats.transactions_processed.toLocaleString()}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', backgroundColor: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', padding: '12px 16px', borderRadius: 'var(--radius-sm)' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>High-Risk Detected</span>
            <span style={{ fontSize: '24px', fontWeight: '700', color: 'var(--color-danger)', fontFamily: 'var(--font-mono)' }}>
              {monitorStats.high_risk_count}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', backgroundColor: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', padding: '12px 16px', borderRadius: 'var(--radius-sm)' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>Alerts Generated</span>
            <span style={{ fontSize: '24px', fontWeight: '700', color: 'var(--color-critical)', fontFamily: 'var(--font-mono)' }}>
              {monitorStats.alert_count}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', backgroundColor: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', padding: '12px 16px', borderRadius: 'var(--radius-sm)' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>Last Transaction</span>
            <span style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-secondary)', marginTop: '8px' }}>
              {renderLastTxTime()}
            </span>
          </div>

        </div>
      </div>

      {/* COMPONENT 6 — LIVE TRANSACTION FEED */}
      <div className="card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            ⚡ LIVE TRANSACTION FEED
          </span>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Showing last 10 transactions • Click row to investigate
          </span>
        </div>

        <div className="table-container" style={{ maxHeight: '400px', overflowY: 'auto' }}>
          <table className="analysis-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)', fontSize: '12px' }}>
                <th style={{ padding: '12px 8px' }}>Time</th>
                <th style={{ padding: '12px 8px' }}>Transaction ID</th>
                <th style={{ padding: '12px 8px' }}>Amount</th>
                <th style={{ padding: '12px 8px' }}>Route</th>
                <th style={{ padding: '12px 8px', textAlign: 'center' }}>Risk Score</th>
                <th style={{ padding: '12px 8px', textAlign: 'center' }}>Risk Level</th>
              </tr>
            </thead>
            <tbody>
              {liveFeed.length === 0 ? (
                <tr>
                  <td colSpan="6" style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                    {systemOnline ? 'Awaiting incoming bank stream transactions...' : 'Live simulation offline. Backend unreachable.'}
                  </td>
                </tr>
              ) : (
                liveFeed.map((item, index) => {
                  const tx = item.transaction;
                  const analysis = item.analysis;
                  
                  // Extract time HH:MM:SS
                  let timeStr = '00:00:00';
                  if (tx.timestamp) {
                    const parts = tx.timestamp.split(' ');
                    timeStr = parts.length > 1 ? parts[1] : parts[0];
                  }

                  const isHighRisk = analysis.risk_level === 'HIGH' || analysis.risk_level === 'CRITICAL';
                  
                  return (
                    <tr 
                      key={tx.transaction_id + '-' + index} 
                      onClick={() => handleTxRowClick(item)}
                      style={{ 
                        borderBottom: '1px solid var(--border-color)', 
                        cursor: 'pointer',
                        transition: 'background var(--transition-fast)',
                        fontSize: '13px'
                      }}
                      className="table-row-hover"
                    >
                      <td style={{ padding: '12px 8px', color: 'var(--text-muted)' }}>{timeStr}</td>
                      <td style={{ padding: '12px 8px', fontFamily: 'var(--font-mono)', fontWeight: '600' }}>{tx.transaction_id}</td>
                      <td style={{ padding: '12px 8px', fontWeight: '500', color: isHighRisk ? 'var(--color-danger)' : 'var(--text-primary)' }}>
                        ₹{parseFloat(tx.amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td style={{ padding: '12px 8px', fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-secondary)' }}>
                        {tx.sender_id} <span style={{ color: 'var(--text-muted)' }}>→</span> {tx.receiver_id}
                      </td>
                      <td style={{ padding: '12px 8px', textAlign: 'center', fontFamily: 'var(--font-mono)', fontWeight: '700' }}>
                        {analysis.risk_score.toFixed(1)}
                      </td>
                      <td style={{ padding: '12px 8px', textAlign: 'center' }}>
                        <span className={`badge severity-${analysis.risk_level}`} style={{ fontSize: '10px', padding: '2px 8px', borderRadius: '4px' }}>
                          {analysis.risk_level}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Diagnostics and Static System Metrics Details */}
      <div className="overview-grid">
        {/* System Connectivity Card */}
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

        {/* Features Card */}
        <div className="card" style={{ gap: '8px' }}>
          <div className="card-title">Model Features Order</div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
            The features order engineered and consumed in real-time scoring:
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {featuresList.map((feat, i) => (
              <span key={feat} className="badge" style={{ fontFamily: 'var(--font-mono)', padding: '2px 6px', fontSize: '10px' }}>
                {i + 1}. {feat}
              </span>
            ))}
          </div>
        </div>
      </div>

    </div>
  );
}

export default Overview;
