import React, { useState, useEffect } from 'react';
import { fetchHealth } from '../services/api';

function SystemStatus() {
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
      <div className="status-badge error" id="system-status-indicator">
        <span className="status-dot"></span>
        <span>Offline</span>
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
    <div className="system-status-container">
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
