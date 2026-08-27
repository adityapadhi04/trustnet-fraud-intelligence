import React, { useState, useEffect } from 'react';
import { fetchAlerts, updateAlertStatus, fetchTransaction } from '../services/api';

function Alerts({ onNavigate, setSelectedTx, setAnalysisResult }) {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters state
  const [filterSeverity, setFilterSeverity] = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  // Selection state
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [updatingStatus, setUpdatingStatus] = useState(false);

  // Load alerts when filters change
  const loadAlerts = async () => {
    try {
      setLoading(true);
      const data = await fetchAlerts({
        severity: filterSeverity,
        status: filterStatus
      });
      setAlerts(data);
      setError(null);
      
      // Keep selected alert reference updated if it exists in the new list
      if (selectedAlert) {
        const updatedSelected = data.find(a => a.alert_id === selectedAlert.alert_id);
        if (updatedSelected) {
          setSelectedAlert(updatedSelected);
        }
      }
    } catch (err) {
      console.error('Failed to load alerts:', err);
      setError('Unable to fetch alerts from the server.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, [filterSeverity, filterStatus]);

  // Handle status update
  const handleUpdateStatus = async (statusVal) => {
    if (!selectedAlert) return;
    try {
      setUpdatingStatus(true);
      const updated = await updateAlertStatus(selectedAlert.alert_id, statusVal);
      setSelectedAlert(updated);
      // Reload list to update status in the table
      await loadAlerts();
    } catch (err) {
      alert(`Failed to update status: ${err.message}`);
    } finally {
      setUpdatingStatus(false);
    }
  };

  // Navigate to Transaction Analysis page and auto-trigger
  const handleViewTransaction = async (txId) => {
    try {
      setLoading(true);
      const tx = await fetchTransaction(txId);
      setSelectedTx(tx);
      setAnalysisResult(null); // Clear previous result to trigger auto-analysis
      onNavigate('analysis');
    } catch (err) {
      alert(`Failed to retrieve transaction details: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Compute summary stats
  const criticalCount = alerts.filter(a => a.severity === 'CRITICAL').length;
  const highCount = alerts.filter(a => a.severity === 'HIGH').length;
  const mediumCount = alerts.filter(a => a.severity === 'MEDIUM').length;
  const openCount = alerts.filter(a => a.status === 'OPEN' || a.status === 'INVESTIGATING').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', height: '100%' }}>
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '24px', fontWeight: '800', color: 'var(--text-primary)' }}>🚨 Alerts Management</h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Review, investigate, and resolve payment security triggers.</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="overview-grid">
        <div className="card" style={{ gap: '8px', padding: '16px 20px' }}>
          <div className="card-title">Critical Severity</div>
          <div className="card-value" style={{ color: 'var(--color-critical)' }}>{criticalCount}</div>
        </div>
        <div className="card" style={{ gap: '8px', padding: '16px 20px' }}>
          <div className="card-title">High Severity</div>
          <div className="card-value" style={{ color: 'var(--color-danger)' }}>{highCount}</div>
        </div>
        <div className="card" style={{ gap: '8px', padding: '16px 20px' }}>
          <div className="card-title">Medium Severity</div>
          <div className="card-value" style={{ color: 'var(--color-warning)' }}>{mediumCount}</div>
        </div>
        <div className="card" style={{ gap: '8px', padding: '16px 20px' }}>
          <div className="card-title">Active Investigations</div>
          <div className="card-value" style={{ color: 'var(--color-primary)' }}>{openCount}</div>
        </div>
      </div>

      {/* Workspace Grid */}
      <div className="workspace-grid">
        {/* Left Pane: Alert List */}
        <div className="transaction-list-pane">
          <div className="pane-header">
            <span className="pane-title">Security Alert Logs</span>
            <div className="filters-row">
              <select
                className="filter-select"
                value={filterSeverity}
                onChange={(e) => setFilterSeverity(e.target.value)}
              >
                <option value="">All Severities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>

              <select
                className="filter-select"
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
              >
                <option value="">All Statuses</option>
                <option value="OPEN">Open</option>
                <option value="INVESTIGATING">Investigating</option>
                <option value="RESOLVED">Resolved</option>
                <option value="FALSE_POSITIVE">False Positive</option>
              </select>
            </div>
          </div>

          <div className="table-container">
            {loading && alerts.length === 0 ? (
              <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                <div className="spinner" style={{ margin: '20px auto', width: '30px', height: '30px' }}></div>
                <p style={{ fontSize: '13px' }}>Loading alerts...</p>
              </div>
            ) : error ? (
              <div style={{ padding: '20px', color: '#FDA4AF', fontSize: '13px' }}>
                {error}
              </div>
            ) : alerts.length === 0 ? (
              <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                No alerts found matching the current filters.
              </div>
            ) : (
              <table className="tx-table">
                <thead>
                  <tr>
                    <th>Severity</th>
                    <th>Alert Info</th>
                    <th style={{ textAlign: 'right' }}>Score</th>
                  </tr>
                </thead>
                <tbody>
                  {alerts.map((alert) => (
                    <tr
                      key={alert.alert_id}
                      className={`tx-row ${selectedAlert?.alert_id === alert.alert_id ? 'selected' : ''}`}
                      onClick={() => setSelectedAlert(alert)}
                    >
                      <td style={{ verticalAlign: 'middle' }}>
                        <span className={`badge severity-${alert.severity}`}>{alert.severity}</span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                          <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                            {alert.transaction_id}
                          </span>
                          <span className={`badge status-${alert.status}`} style={{ fontSize: '9px', padding: '1px 4px' }}>
                            {alert.status}
                          </span>
                        </div>
                        <div style={{ fontSize: '13px', fontWeight: '500', color: 'var(--text-primary)', marginTop: '2px' }}>
                          {alert.alert_type.replace('_', ' ')}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px', maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {alert.primary_reason}
                        </div>
                      </td>
                      <td className="tx-amount" style={{ verticalAlign: 'middle' }}>
                        {alert.risk_score.toFixed(1)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Right Pane: Alert Details Workbench */}
        <div className="analysis-workbench-pane">
          {!selectedAlert ? (
            <div className="empty-state">
              <div style={{ fontSize: '48px' }}>🚨</div>
              <h3>No Alert Selected</h3>
              <p>Select an alert from the log panel on the left to begin checking transaction variables, network logs, and investigation status.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              
              {/* Alert Header Summary */}
              <div className="tx-details-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                      {selectedAlert.alert_id}
                    </span>
                    <h3 style={{ fontSize: '18px', fontWeight: '700', marginTop: '2px' }}>
                      {selectedAlert.alert_type.replace('_', ' ')}
                    </h3>
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <span className={`badge severity-${selectedAlert.severity}`} style={{ fontSize: '12px', padding: '4px 10px' }}>
                      {selectedAlert.severity}
                    </span>
                    <span className={`badge status-${selectedAlert.status}`} style={{ fontSize: '12px', padding: '4px 10px' }}>
                      {selectedAlert.status}
                    </span>
                  </div>
                </div>

                <div className="details-grid" style={{ marginTop: '8px' }}>
                  <div className="detail-field">
                    <span className="detail-label">Associated Transaction</span>
                    <span className="detail-value mono">{selectedAlert.transaction_id}</span>
                  </div>
                  <div className="detail-field">
                    <span className="detail-label">Consolidated Risk Score</span>
                    <span className="detail-value" style={{ color: selectedAlert.severity === 'CRITICAL' ? 'var(--color-critical)' : 'var(--text-primary)', fontWeight: '700' }}>
                      {selectedAlert.risk_score} / 100 ({selectedAlert.risk_level})
                    </span>
                  </div>
                  <div className="detail-field">
                    <span className="detail-label">Trigger Timestamp</span>
                    <span className="detail-value">{selectedAlert.created_at}</span>
                  </div>
                  <div className="detail-field">
                    <span className="detail-label">Investigator Status</span>
                    <span className="detail-value">{selectedAlert.status.replace('_', ' ')}</span>
                  </div>
                </div>
              </div>

              {/* Primary Trigger Reason */}
              <div className="risk-factors-card">
                <div className="section-heading">Alert Diagnostic Reason</div>
                <div className="factor-item" style={{ borderLeftColor: selectedAlert.severity === 'CRITICAL' ? 'var(--color-critical)' : 'var(--color-primary)' }}>
                  <span className="factor-text" style={{ fontSize: '14px', lineHeight: '1.4' }}>
                    {selectedAlert.primary_reason}
                  </span>
                </div>
              </div>

              {/* Status Investigation Actions */}
              <div className="tx-details-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div className="section-heading" style={{ marginBottom: '4px' }}>Investigation Workflow Actions</div>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  Transition the life-cycle of this security event. All actions are logged under the current Analyst role session.
                </p>
                <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                  <button
                    className="btn btn-warning"
                    disabled={selectedAlert.status === 'INVESTIGATING' || updatingStatus}
                    onClick={() => handleUpdateStatus('INVESTIGATING')}
                  >
                    🔍 Start Investigation
                  </button>
                  <button
                    className="btn btn-success"
                    disabled={selectedAlert.status === 'RESOLVED' || updatingStatus}
                    onClick={() => handleUpdateStatus('RESOLVED')}
                  >
                    ✅ Resolve Alert
                  </button>
                  <button
                    className="btn btn-danger"
                    disabled={selectedAlert.status === 'FALSE_POSITIVE' || updatingStatus}
                    onClick={() => handleUpdateStatus('FALSE_POSITIVE')}
                  >
                    ❌ Mark False Positive
                  </button>
                </div>
              </div>

              {/* Navigation Action */}
              <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                <button
                  className="btn btn-primary"
                  style={{ padding: '12px 24px', fontSize: '14px', width: '100%' }}
                  onClick={() => handleViewTransaction(selectedAlert.transaction_id)}
                >
                  🔍 View Diagnostics in Transaction Analysis
                </button>
              </div>

            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Alerts;
