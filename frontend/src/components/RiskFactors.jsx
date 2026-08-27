import React from 'react';

function RiskFactors({ factors }) {
  if (!factors || factors.length === 0) {
    return (
      <div className="risk-factors-card">
        <h3 className="section-heading">Risk Indicators</h3>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          No risk indicators triggered for this transaction.
        </p>
      </div>
    );
  }

  return (
    <div className="risk-factors-card">
      <h3 className="section-heading">Triggered Risk Indicators</h3>
      <div className="factors-list">
        {factors.map((f, index) => (
          <div 
            key={`${f.factor}-${index}`} 
            className={`factor-item severity-${f.severity?.toLowerCase() || 'low'}`}
          >
            <span className="factor-text">{f.factor}</span>
            <span className="factor-contrib">+{f.contribution?.toFixed(1)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default RiskFactors;
