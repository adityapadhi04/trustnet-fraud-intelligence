import React from 'react';

function ShapExplanation({ shapExplanation }) {
  if (!shapExplanation || !shapExplanation.contributions) {
    return (
      <div className="shap-card">
        <h3 className="section-heading">Local Model Interpretability</h3>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          No local interpretability data available.
        </p>
      </div>
    );
  }

  const { base_value, contributions } = shapExplanation;

  // Render feature value helper
  const formatFeatureValue = (feature, val) => {
    if (val === null || val === undefined) return 'N/A';
    if (feature === 'amount') return `₹${val.toLocaleString('en-IN')}`;
    if (feature === 'amount_deviation') return `${val.toFixed(1)}x`;
    if (feature === 'location_deviation_km') return `${val.toFixed(1)} km`;
    if (feature === 'is_new_device' || feature === 'is_new_ip') return val === 1 ? 'Yes' : 'No';
    return String(val);
  };

  return (
    <div className="shap-card">
      <h3 className="section-heading">Local Model Interpretability (SHAP)</h3>
      <div className="shap-intro">
        <p><strong>Methodology Note:</strong> SHAP explains how individual features influenced the XGBoost fraud prediction model relative to the base expected value (base log-odds: {base_value?.toFixed(4)}).</p>
        <p style={{ marginTop: '4px', fontSize: '11px', color: 'var(--text-muted)' }}>
          *SHAP values explain model feature weights; they indicate model decision path attribution, not definitive real-world guilt.
        </p>
      </div>

      <table className="shap-table">
        <thead>
          <tr>
            <th>Feature</th>
            <th>Observed Value</th>
            <th style={{ textAlign: 'right' }}>SHAP Attribution</th>
            <th style={{ textAlign: 'right' }}>Direction</th>
          </tr>
        </thead>
        <tbody>
          {contributions.map((c) => {
            const isIncrease = c.direction === 'increases_risk';
            const valueStr = formatFeatureValue(c.feature, c.value);
            return (
              <tr key={c.feature}>
                <td style={{ fontWeight: '500' }}>{c.feature}</td>
                <td style={{ fontFamily: 'var(--font-mono)' }}>{valueStr}</td>
                <td 
                  style={{ textAlign: 'right' }} 
                  className={`shap-val-col ${isIncrease ? 'increases' : 'decreases'}`}
                >
                  {isIncrease ? '+' : ''}{c.shap_value.toFixed(4)}
                </td>
                <td 
                  style={{ textAlign: 'right', fontSize: '11px', fontWeight: '600' }} 
                  className={`shap-val-col ${isIncrease ? 'increases' : 'decreases'}`}
                >
                  {isIncrease ? 'INCREASES RISK' : 'DECREASES RISK'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default ShapExplanation;
