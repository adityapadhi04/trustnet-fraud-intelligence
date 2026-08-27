import React from 'react';

function RiskScore({ score, level }) {
  // Safe default formatting
  const formattedScore = score !== undefined && score !== null ? score.toFixed(1) : '0.0';
  const riskClass = level ? `risk-level-${level}` : 'risk-level-LOW';

  return (
    <div className="risk-score-card">
      <span className="risk-score-label">TRUSTNET Risk Score</span>
      <div className={`risk-circle ${riskClass}`}>
        <span className="risk-value">{formattedScore}</span>
        <span className="risk-max">/ 100</span>
      </div>
      <div className={`risk-level-badge ${riskClass}`}>
        {level || 'LOW'}
      </div>
    </div>
  );
}

export default RiskScore;
