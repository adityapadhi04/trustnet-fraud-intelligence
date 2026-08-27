import React from 'react';

function Sidebar({ currentPage, onPageChange }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          TRUST<span>NET</span>
        </div>
      </div>
      
      <nav className="sidebar-nav">
        <button 
          className={`nav-item ${currentPage === 'overview' ? 'active' : ''}`}
          onClick={() => onPageChange('overview')}
        >
          <span>📊</span> Overview
        </button>
        
        <button 
          className={`nav-item ${currentPage === 'analysis' ? 'active' : ''}`}
          onClick={() => onPageChange('analysis')}
        >
          <span>🔍</span> Transaction Analysis
        </button>
        
        <button 
          className={`nav-item ${currentPage === 'risk' ? 'active' : ''}`}
          onClick={() => onPageChange('risk')}
        >
          <span>🛡️</span> Risk Intelligence
        </button>
        
        <button 
          className={`nav-item ${currentPage === 'explainability' ? 'active' : ''}`}
          onClick={() => onPageChange('explainability')}
        >
          <span>💡</span> Explainability
        </button>
        
        <button 
          className={`nav-item ${currentPage === 'network' ? 'active' : ''}`}
          onClick={() => onPageChange('network')}
        >
          <span>🕸️</span> Network Investigation
        </button>

        <button className="nav-item disabled" disabled>
          <span>🚨</span> Alerts <span className="nav-item-badge">Soon</span>
        </button>

        <button className="nav-item disabled" disabled>
          <span>📄</span> Reports <span className="nav-item-badge">Soon</span>
        </button>
      </nav>
      
      <div className="sidebar-footer">
        <p>TRUSTNET Platform v0.1.0</p>
        <p style={{ marginTop: '4px' }}>Role: Fraud Analyst</p>
      </div>
    </aside>
  );
}

export default Sidebar;
