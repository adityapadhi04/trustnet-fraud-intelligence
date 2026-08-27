import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Overview from './pages/Overview';
import TransactionAnalysis from './pages/TransactionAnalysis';
import NetworkInvestigation from './pages/NetworkInvestigation';
import RiskIntelligence from './pages/RiskIntelligence';
import Explainability from './pages/Explainability';
import Alerts from './pages/Alerts';
import Reports from './pages/Reports';
import { fetchAlerts, fetchTransaction, analyzeRisk, fetchDemoMode, toggleDemoMode } from './services/api';

// Web Audio API Synthesizer for high-tech professional chime
function playAlertChime() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();
    
    const playChime = (time, freq) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, time);
      
      gain.gain.setValueAtTime(0.08, time);
      gain.gain.exponentialRampToValueAtTime(0.0001, time + 0.55);
      
      osc.connect(gain);
      gain.connect(ctx.destination);
      
      osc.start(time);
      osc.stop(time + 0.6);
    };
    
    const now = ctx.currentTime;
    playChime(now, 880); // High chime note
    playChime(now + 0.12, 1046.5); // Second chime note
  } catch (err) {
    console.warn("Audio autoplay restrictions prevented tone play", err);
  }
}

function App() {
  const [currentPage, setCurrentPage] = useState('overview');
  const [selectedTx, setSelectedTx] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [demoMode, setDemoMode] = useState(false);

  useEffect(() => {
    async function getInitialDemoState() {
      try {
        const res = await fetchDemoMode();
        setDemoMode(res.demo_mode);
      } catch (err) {
        // silent fail
      }
    }
    getInitialDemoState();
  }, []);

  const handleToggleDemo = async () => {
    const nextVal = !demoMode;
    try {
      const res = await toggleDemoMode(nextVal);
      setDemoMode(res.demo_mode);
    } catch (err) {
      console.error("Failed to toggle demo mode state:", err);
    }
  };

  // Real-time critical notification state
  const [activeNotification, setActiveNotification] = useState(null);
  const notifiedTxIdsRef = useRef(new Set());
  const isInitializedRef = useRef(false);
  const clearTimerRef = useRef(null);

  // Request browser Notification API permission on first user click interaction
  const requestNotificationPermission = () => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission().then(permission => {
        console.log("Desktop notifications status:", permission);
      });
    }
  };

  // Poll alerts every 3 seconds for new critical events (Read-only, does not call /monitor/next)
  useEffect(() => {
    let active = true;

    async function pollAlerts() {
      try {
        const alertsList = await fetchAlerts();
        if (!active) return;

        // Initialize state on mount with all pre-existing alerts to prevent retro-notification floods
        if (!isInitializedRef.current) {
          alertsList.forEach(alert => {
            notifiedTxIdsRef.current.add(alert.transaction_id);
          });
          isInitializedRef.current = true;
          return;
        }

        // Search for new critical alerts
        const newCritical = alertsList.find(alert => 
          alert.severity === 'CRITICAL' && 
          !notifiedTxIdsRef.current.has(alert.transaction_id)
        );

        if (newCritical) {
          const txId = newCritical.transaction_id;
          notifiedTxIdsRef.current.add(txId);

          // Fetch full transaction details to retrieve sender_id & receiver_id
          const txDetails = await fetchTransaction(txId);
          if (!active) return;

          // Play professional tone
          playAlertChime();

          // Dispatch native browser notification if allowed
          if ('Notification' in window && Notification.permission === 'granted') {
            try {
              new Notification("🚨 CRITICAL FRAUD ALERT", {
                body: `Transaction: ${txId}\nRisk Score: ${newCritical.risk_score}\nSender: ${txDetails.sender_id}\nReceiver: ${txDetails.receiver_id}`,
                tag: txId
              });
            } catch (err) {
              console.error("Native notification failed:", err);
            }
          }

          // Trigger local in-dashboard popup
          setActiveNotification({
            transaction_id: txId,
            risk_score: newCritical.risk_score,
            sender_id: txDetails.sender_id,
            receiver_id: txDetails.receiver_id,
            alert_id: newCritical.alert_id
          });

          // Auto dismiss after 7.5 seconds
          if (clearTimerRef.current) clearTimeout(clearTimerRef.current);
          clearTimerRef.current = setTimeout(() => {
            setActiveNotification(null);
          }, 7500);
        }
      } catch (err) {
        console.error("Critical alert poller check failed:", err);
      }
    }

    const interval = setInterval(pollAlerts, 3000);
    pollAlerts(); // Run immediate first check

    return () => {
      active = false;
      clearInterval(interval);
      if (clearTimerRef.current) clearTimeout(clearTimerRef.current);
    };
  }, []);

  const handleInvestigate = async (txId) => {
    try {
      const txDetails = await fetchTransaction(txId);
      setSelectedTx(txDetails);

      const features = {
        amount: txDetails.amount,
        oldbalanceOrg: txDetails.oldbalanceOrg,
        newbalanceOrig: txDetails.newbalanceOrig,
        oldbalanceDest: txDetails.oldbalanceDest,
        newbalanceDest: txDetails.newbalanceDest,
        is_merchant_org: txDetails.is_merchant_org,
        is_merchant_dest: txDetails.is_merchant_dest,
        transaction_type: txDetails.transaction_type,
        hour_of_day: txDetails.hour_of_day,
        day_of_week: txDetails.day_of_week,
        velocity_last_1h: txDetails.velocity_last_1h,
        network_degree_in: txDetails.network_degree_in,
        network_degree_out: txDetails.network_degree_out,
        risk_score: txDetails.risk_score
      };
      
      const result = await analyzeRisk(features);
      setAnalysisResult(result);
      
      setCurrentPage('analysis');
      setActiveNotification(null);
    } catch (err) {
      console.error("Failed to investigate transaction details:", err);
    }
  };

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  return (
    <div className="app-container" onClick={requestNotificationPermission}>
      {/* Sidebar Navigation */}
      <Sidebar currentPage={currentPage} onPageChange={handlePageChange} />

      {/* Main Workspace Pane */}
      <div className="main-content">
        {/* Top bar with connectivity status */}
        <Header demoMode={demoMode} handleToggleDemo={handleToggleDemo} />

        {/* Dynamic page body */}
        <main className="page-body">
          {currentPage === 'overview' && (
            <Overview 
              setSelectedTx={setSelectedTx} 
              setAnalysisResult={setAnalysisResult} 
              onNavigate={handlePageChange} 
              demoMode={demoMode}
              setDemoMode={setDemoMode}
              handleToggleDemo={handleToggleDemo}
            />
          )}
          {currentPage === 'analysis' && (
            <TransactionAnalysis
              selectedTx={selectedTx}
              setSelectedTx={setSelectedTx}
              analysisResult={analysisResult}
              setAnalysisResult={setAnalysisResult}
            />
          )}
          {currentPage === 'risk' && (
            <RiskIntelligence
              selectedTx={selectedTx}
              analysisResult={analysisResult}
              onNavigate={handlePageChange}
            />
          )}
          {currentPage === 'explainability' && (
            <Explainability
              selectedTx={selectedTx}
              analysisResult={analysisResult}
              onNavigate={handlePageChange}
            />
          )}
          {currentPage === 'network' && (
            <NetworkInvestigation 
              initialAccountId={selectedTx?.sender_id} 
            />
          )}
          {currentPage === 'alerts' && (
            <Alerts 
              onNavigate={handlePageChange} 
              setSelectedTx={setSelectedTx} 
              setAnalysisResult={setAnalysisResult} 
            />
          )}
          {currentPage === 'reports' && <Reports />}
        </main>
      </div>

      {/* Real-time Global Critical Alert Popup */}
      {activeNotification && (
        <div className="critical-popup-container critical-popup-glow">
          <div className="critical-popup-header">
            <span className="critical-popup-title">
              🚨 CRITICAL FRAUD ALERT
            </span>
            <button 
              className="critical-popup-close-btn"
              onClick={() => setActiveNotification(null)}
              title="Dismiss Alert"
            >
              ×
            </button>
          </div>
          <div className="critical-popup-body">
            <strong style={{ color: '#ffffff', fontSize: '12px' }}>
              Critical-risk transaction detected
            </strong>
            <div style={{ marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
              <div><strong>Transaction:</strong> <span style={{ fontFamily: 'var(--font-mono)' }}>{activeNotification.transaction_id}</span></div>
              <div><strong>Risk Score:</strong> <span style={{ color: '#ef4444', fontWeight: '800', fontFamily: 'var(--font-mono)' }}>{activeNotification.risk_score.toFixed(1)}</span></div>
              <div><strong>Sender:</strong> <span style={{ fontFamily: 'var(--font-mono)' }}>{activeNotification.sender_id}</span></div>
              <div><strong>Receiver:</strong> <span style={{ fontFamily: 'var(--font-mono)' }}>{activeNotification.receiver_id}</span></div>
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: '10px', marginTop: '6px', fontStyle: 'italic' }}>
              Detected just now
            </div>
          </div>
          <div className="critical-popup-footer">
            <button 
              className="critical-popup-btn critical-popup-btn-dismiss"
              onClick={() => setActiveNotification(null)}
            >
              Dismiss
            </button>
            <button 
              className="critical-popup-btn critical-popup-btn-action"
              onClick={() => handleInvestigate(activeNotification.transaction_id)}
            >
              Investigate
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
