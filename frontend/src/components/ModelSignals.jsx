import React from 'react';

function ModelSignals({ fraudProbability, anomalyScore, behavioralRisk, networkRisk }) {
  const formatProb = (p) => (p !== undefined && p !== null ? `${(p * 100).toFixed(1)}%` : '0.0%');
  const formatScore = (s) => (s !== undefined && s !== null ? s.toFixed(4) : '0.0000');
  const formatRisk = (r) => (r !== undefined && r !== null ? `${r.toFixed(1)}/100` : '0.0/100');

  return (
    <div className="signals-grid">
      <div className="signal-card">
        <span className="signal-header">Supervised Classification</span>
        <span className="signal-value">{formatProb(fraudProbability)}</span>
        <span className="signal-label">Model Signal (XGBoost)</span>
      </div>

      <div className="signal-card">
        <span className="signal-header">Anomaly Dev Score</span>
        <span className="signal-value">{formatScore(anomalyScore)}</span>
        <span className="signal-label">Model Signal (IForest)</span>
      </div>

      <div className="signal-card">
        <span className="signal-header">Behavioral Risk</span>
        <span className="signal-value">{formatRisk(behavioralRisk)}</span>
        <span className="signal-label">Aggregated User Deviation</span>
      </div>

      <div className="signal-card">
        <span className="signal-header">Network Risk</span>
        <span className="signal-value">{formatRisk(networkRisk)}</span>
        <span className="signal-label">Graph Flow Topology</span>
      </div>
    </div>
  );
}

export default ModelSignals;
