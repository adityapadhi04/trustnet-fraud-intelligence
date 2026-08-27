import React from 'react';
import SystemStatus from './SystemStatus';

function Header() {
  return (
    <header className="header">
      <div className="header-title-group">
        <h1>TRUSTNET</h1>
        <p>Fraud Intelligence & Decision-Support Workbench</p>
      </div>
      <SystemStatus />
    </header>
  );
}

export default Header;
