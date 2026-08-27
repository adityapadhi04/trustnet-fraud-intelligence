import React from 'react';
import TransactionDetails from '../components/TransactionDetails';
import ShapExplanation from '../components/ShapExplanation';

function Explainability({ selectedTx, analysisResult, onNavigate }) {
  if (!selectedTx || !analysisResult) {
    return (
      <div className="empty-state-container" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60vh', textAlign: 'center' }}>
        <div style={{ fontSize: '48px', marginBottom: '16px' }}>💡</div>
        <h3>No Transaction Selected</h3>
        <p style={{ color: 'var(--text-secondary)', maxWidth: '400px', margin: '0 auto 24px auto', fontSize: '14px' }}>
          Select a transaction record in the database and run risk analysis to view the machine learning model explanations.
        </p>
        <button 
          className="btn-primary" 
          onClick={() => onNavigate('analysis')}
          style={{ padding: '10px 20px', borderRadius: '4px', cursor: 'pointer', fontWeight: '600' }}
        >
          Go to Transaction Analysis
        </button>
      </div>
    );
  }

  const contributions = [...(analysisResult.shap_explanation?.contributions || [])];
  
  // Sort contributions by absolute SHAP value magnitude descending
  const sortedContributions = contributions.sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value));

  // Helper to determine impact level based on absolute SHAP value
  const getImpactLevel = (val) => {
    const absVal = Math.abs(val);
    if (absVal >= 0.2) return { text: 'HIGH', class: 'impact-high', color: '#EF4444' };
    if (absVal >= 0.05) return { text: 'MEDIUM', class: 'impact-medium', color: '#F59E0B' };
    if (absVal > 0) return { text: 'LOW', class: 'impact-low', color: '#10B981' };
    return { text: 'NEUTRAL', class: 'impact-neutral', color: 'var(--text-muted)' };
  };

  const positiveContributors = contributions.filter(c => c.direction === 'increases_risk' && Math.abs(c.shap_value) > 0);
  const negativeContributors = contributions.filter(c => c.direction === 'decreases_risk' && Math.abs(c.shap_value) > 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', padding: '24px 0' }}>
      <div className="pane-header">
        <h2 style={{ fontSize: '20px', fontWeight: '600', color: 'var(--text-primary)' }}>SHAP Model Explainability (XAI)</h2>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
          Local game-theoretic explanations highlighting which transaction features pushed the risk classification model towards a fraudulent or normal decision.
        </p>
      </div>

      <TransactionDetails transaction={selectedTx} />

      <div className="shap-card" style={{ padding: '24px' }}>
        <h3 className="section-heading" style={{ marginBottom: '16px', color: 'var(--text-primary)' }}>Why Was This Transaction Flagged?</h3>
        
        <table className="shap-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '8px' }}>Feature</th>
              <th style={{ textAlign: 'left', padding: '8px' }}>Impact Level</th>
              <th style={{ textAlign: 'right', padding: '8px' }}>SHAP Value</th>
              <th style={{ textAlign: 'right', padding: '8px' }}>Influence</th>
            </tr>
          </thead>
          <tbody>
            {sortedContributions.slice(0, 5).map((c) => {
              const impact = getImpactLevel(c.shap_value);
              const isIncrease = c.direction === 'increases_risk';
              return (
                <tr key={c.feature} style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <td style={{ padding: '12px 8px', fontWeight: '500' }}>{c.feature}</td>
                  <td style={{ padding: '12px 8px' }}>
                    <span style={{ 
                      backgroundColor: `${impact.color}22`, 
                      color: impact.color, 
                      padding: '2px 8px', 
                      borderRadius: '4px', 
                      fontSize: '11px', 
                      fontWeight: '700' 
                    }}>
                      {impact.text}
                    </span>
                  </td>
                  <td style={{ padding: '12px 8px', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                    {isIncrease ? '+' : ''}{c.shap_value.toFixed(4)}
                  </td>
                  <td style={{ 
                    padding: '12px 8px', 
                    textAlign: 'right', 
                    fontSize: '11px', 
                    fontWeight: '600',
                    color: isIncrease ? '#EF4444' : '#10B981'
                  }}>
                    {isIncrease ? 'INCREASES RISK' : 'DECREASES RISK'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
        {/* Positive Contributors */}
        <div className="shap-card" style={{ padding: '20px' }}>
          <h4 style={{ color: '#EF4444', fontSize: '14px', fontWeight: '600', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>⚠️</span> Top Risk Contributors
          </h4>
          {positiveContributors.length === 0 ? (
            <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>No features contributed positively to the risk score.</p>
          ) : (
            <ul style={{ listStyleType: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {positiveContributors.map((c) => (
                <li key={c.feature} style={{ fontSize: '13px', lineHeight: '1.4', paddingBottom: '8px', borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                  <strong style={{ color: 'var(--text-primary)' }}>{c.feature}</strong>: {c.human_readable}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Negative Contributors */}
        <div className="shap-card" style={{ padding: '20px' }}>
          <h4 style={{ color: '#10B981', fontSize: '14px', fontWeight: '600', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>✅</span> Normal / Mitigating Factors
          </h4>
          {negativeContributors.length === 0 ? (
            <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>No normal mitigating factors detected.</p>
          ) : (
            <ul style={{ listStyleType: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {negativeContributors.map((c) => (
                <li key={c.feature} style={{ fontSize: '13px', lineHeight: '1.4', paddingBottom: '8px', borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                  <strong style={{ color: 'var(--text-primary)' }}>{c.feature}</strong>: {c.human_readable}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <ShapExplanation shapExplanation={analysisResult.shap_explanation} />
    </div>
  );
}

export default Explainability;
