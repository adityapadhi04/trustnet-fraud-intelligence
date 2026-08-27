import React from 'react';
import TransactionDetails from '../components/TransactionDetails';
import RiskScore from '../components/RiskScore';
import ModelSignals from '../components/ModelSignals';
import RiskFactors from '../components/RiskFactors';

function RiskIntelligence({ selectedTx, analysisResult, onNavigate }) {
  if (!selectedTx || !analysisResult) {
    return (
      <div className="empty-state-container" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60vh', textAlign: 'center' }}>
        <div style={{ fontSize: '48px', marginBottom: '16px' }}>🛡️</div>
        <h3>No Transaction Selected</h3>
        <p style={{ color: 'var(--text-secondary)', maxWidth: '400px', margin: '0 auto 24px auto', fontSize: '14px' }}>
          Select a transaction record in the database and run risk analysis to populate the diagnostic workspace.
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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', padding: '24px 0' }}>
      <div className="pane-header">
        <h2 style={{ fontSize: '20px', fontWeight: '600', color: 'var(--text-primary)' }}>Risk Intelligence Hub</h2>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
          Consolidated risk assessment across machine learning classification, anomaly detection, behavioral analytics, and network topology.
        </p>
      </div>

      <TransactionDetails transaction={selectedTx} />

      <div className="risk-summary-section">
        <RiskScore 
          score={analysisResult.risk_score} 
          level={analysisResult.risk_level} 
        />
        <ModelSignals 
          fraudProbability={analysisResult.fraud_probability}
          anomalyScore={analysisResult.anomaly_score}
          behavioralRisk={analysisResult.behavioral_risk}
          networkRisk={analysisResult.network_risk}
        />
      </div>

      <RiskFactors factors={analysisResult.risk_factors} />
    </div>
  );
}

export default RiskIntelligence;
