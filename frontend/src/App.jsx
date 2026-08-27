import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Overview from './pages/Overview';
import TransactionAnalysis from './pages/TransactionAnalysis';
import NetworkInvestigation from './pages/NetworkInvestigation';
import RiskIntelligence from './pages/RiskIntelligence';
import Explainability from './pages/Explainability';

function App() {
  const [currentPage, setCurrentPage] = useState('overview');
  const [selectedTx, setSelectedTx] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <Sidebar currentPage={currentPage} onPageChange={handlePageChange} />

      {/* Main Workspace Pane */}
      <div className="main-content">
        {/* Top bar with connectivity status */}
        <Header />

        {/* Dynamic page body */}
        <main className="page-body">
          {currentPage === 'overview' && <Overview />}
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
          {currentPage === 'network' && <NetworkInvestigation />}
        </main>
      </div>
    </div>
  );
}

export default App;
