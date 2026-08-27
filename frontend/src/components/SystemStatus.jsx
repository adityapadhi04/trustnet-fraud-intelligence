import React, { useState, useEffect } from 'react';
import { fetchHealth } from '../services/api';

function SystemStatus({ demoMode, handleToggleDemo }) {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    async function checkHealth() {
      try {
        const data = await fetchHealth();
        setHealth(data);
        setError(false);
      } catch (err) {
        console.error('SystemStatus check failed:', err);
        setHealth(null);
        setError(true);
      }
    }

    checkHealth();
    const interval = setInterval(checkHealth, 10000); // Poll health every 10s
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div className="status-badge error" id="system-status-indicator">
          <span className="status-dot"></span>
          <span>Offline</span>
        </div>
      </div>
    );
  }

  if (!health) {
    return (
      <div className="status-badge" style={{ backgroundColor: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)' }}>
        <span>Checking...</span>
      </div>
    );
  }

  const isHealthy = health.status === 'healthy';
  const modelsLoaded = health.models_loaded;

  return (
    <div className="system-status-container" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
      {/* Dynamic Demo Mode Toggle Badge */}
      <button 
        onClick={handleToggleDemo}
        className={`status-badge ${demoMode ? 'demo-active' : ''}`}
        style={{
          cursor: 'pointer',
          pointerEvents: 'auto',
          zIndex: 9999,
          border: '1px solid var(--border-color)',
          background: demoMode ? 'rgba(245, 158, 11, 0.12)' : 'rgba(255, 255, 255, 0.02)',
          borderColor: demoMode ? '#F59E0B' : 'var(--border-color)',
          color: demoMode ? '#F59E0B' : 'var(--text-secondary)',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontWeight: '700',
          transition: 'all 0.25s ease',
          fontSize: '11px',
          borderRadius: 'var(--radius-sm)',
          padding: '4px 10px'
        }}
        title="Toggle Demo Mode: When enabled, every 5th transaction is forced to be a CRITICAL risk incident for presentation purposes."
      >
        <span style={{ 
          width: '6px', 
          height: '6px', 
          borderRadius: '50%', 
          backgroundColor: demoMode ? '#F59E0B' : 'var(--text-muted)',
          boxShadow: demoMode ? '0 0 6px #F59E0B' : 'none'
        }}/>
        DEMO MODE: {demoMode ? 'ON' : 'OFF'}
      </button>

      <div className={`status-badge ${isHealthy ? '' : 'error'}`} id="system-status-indicator">
        <span className="status-dot"></span>
        <span>{isHealthy ? 'API Active' : 'API Degraded'}</span>
      </div>
      <div className={`status-badge ${modelsLoaded ? '' : 'error'}`} id="models-status-indicator">
        <span className="status-dot"></span>
        <span>{modelsLoaded ? 'ML Models Loaded' : 'ML Models Missing'}</span>
      </div>
    </div>
  );
}

export default SystemStatus;
