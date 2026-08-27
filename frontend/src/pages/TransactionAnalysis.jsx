import React, { useState, useEffect } from 'react';
import { fetchSampleTransactions, analyzeRisk } from '../services/api';
import TransactionDetails from '../components/TransactionDetails';
import RiskScore from '../components/RiskScore';
import ModelSignals from '../components/ModelSignals';
import RiskFactors from '../components/RiskFactors';
import ShapExplanation from '../components/ShapExplanation';

function TransactionAnalysis({ selectedTx, setSelectedTx, analysisResult, setAnalysisResult }) {
  const [transactions, setTransactions] = useState([]);
  const [loadingList, setLoadingList] = useState(true);
  const [errorList, setErrorList] = useState(null);
  
  const [searchQuery, setSearchQuery] = useState('');
  
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [errorAnalysis, setErrorAnalysis] = useState(null);

  // Load sample transactions on mount
  useEffect(() => {
    async function loadTransactions() {
      try {
        setLoadingList(true);
        const data = await fetchSampleTransactions(50); // Fetch up to 50 samples
        setTransactions(data.transactions || []);
        setErrorList(null);
      } catch (err) {
        console.error('Failed to load transactions:', err);
        setErrorList('Unable to retrieve sample transaction list.');
      } finally {
        setLoadingList(false);
      }
    }
    loadTransactions();
  }, []);

  // Run analysis when a transaction is selected
  const handleSelectTransaction = async (tx) => {
    setSelectedTx(tx);
    setAnalysisResult(null);
    setErrorAnalysis(null);
    setLoadingAnalysis(true);

    // Extract exact features expected by POST /api/v1/risk/analyze
    const features = {
      amount: tx.amount,
      amount_deviation: tx.amount_deviation,
      is_new_device: tx.is_new_device,
      is_new_ip: tx.is_new_ip,
      location_deviation_km: tx.location_deviation_km,
      hour_of_day: tx.hour_of_day,
      day_of_week: tx.day_of_week,
      velocity_1h: tx.velocity_1h,
      velocity_24h: tx.velocity_24h,
      recipient_in_degree: tx.recipient_in_degree,
      sender_out_degree: tx.sender_out_degree,
      sender_id: tx.sender_id,
      receiver_id: tx.receiver_id,
      timestamp: tx.timestamp
    };

    try {
      const result = await analyzeRisk(features);
      setAnalysisResult(result);
    } catch (err) {
      console.error('Analysis execution failed:', err);
      setErrorAnalysis(err.message || 'Unable to connect to TRUSTNET API.');
    } finally {
      setLoadingAnalysis(false);
    }
  };

  // Filter transactions based on query
  const filteredTransactions = transactions.filter(tx => 
    tx.transaction_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    tx.sender_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    tx.receiver_id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="workspace-grid">
      {/* Left Pane: Transaction Selector */}
      <div className="transaction-list-pane">
        <div className="pane-header">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="pane-title">Transactions Database</span>
            <span className="dataset-label">Synthetic transaction data</span>
          </div>
          <input 
            type="text" 
            placeholder="Search transaction, sender, or receiver ID..." 
            className="search-input"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="table-container">
          {loadingList ? (
            <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-secondary)' }}>
              <div className="spinner" style={{ margin: '20px auto', width: '30px', height: '30px' }}></div>
              <p style={{ fontSize: '13px' }}>Loading transactions...</p>
            </div>
          ) : errorList ? (
            <div style={{ padding: '20px', color: '#FDA4AF', fontSize: '13px' }}>
              {errorList}
            </div>
          ) : filteredTransactions.length === 0 ? (
            <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
              No matching records found.
            </div>
          ) : (
            <table className="tx-table">
              <thead>
                <tr>
                  <th>TX ID</th>
                  <th>Sender/Receiver</th>
                  <th className="tx-amount-header">Amount</th>
                </tr>
              </thead>
              <tbody>
                {filteredTransactions.map((tx) => (
                  <tr 
                    key={tx.transaction_id}
                    className={`tx-row ${selectedTx?.transaction_id === tx.transaction_id ? 'selected' : ''}`}
                    onClick={() => handleSelectTransaction(tx)}
                  >
                    <td>
                      <div className="tx-id">{tx.transaction_id}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{tx.timestamp.split(' ')[1]}</div>
                    </td>
                    <td>
                      <div style={{ fontSize: '13px' }}>{tx.sender_id} ➔ {tx.receiver_id}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{tx.payment_method}</div>
                    </td>
                    <td className="tx-amount">
                      ₹{tx.amount.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Right Pane: Risk Diagnostic Workspace */}
      <div className="analysis-workbench-pane">
        {loadingAnalysis ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Running ML inference and SHAP explainability calculations...</p>
          </div>
        ) : errorAnalysis ? (
          <div className="error-alert-box" style={{ padding: '24px' }}>
            <strong>Analysis Failed:</strong> {errorAnalysis}
            <p style={{ marginTop: '12px', fontSize: '12px' }}>
              Please check that the FastAPI server is running properly on port 8000.
            </p>
          </div>
        ) : !selectedTx ? (
          <div className="empty-state">
            <div style={{ fontSize: '48px' }}>🔍</div>
            <h3>No Transaction Selected</h3>
            <p>
              Select a transaction record from the left database panel to run the risk analysis models and view local diagnostic explanations.
            </p>
          </div>
        ) : (
          <>
            {/* Metadata Detail */}
            <TransactionDetails transaction={selectedTx} />

            {/* Risk Scoring & Subsystem Output */}
            {analysisResult && (
              <>
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

                {/* Risk Indicators / Alerts list */}
                <RiskFactors factors={analysisResult.risk_factors} />

                {/* SHAP Explanation */}
                <ShapExplanation shapExplanation={analysisResult.shap_explanation} />
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default TransactionAnalysis;
