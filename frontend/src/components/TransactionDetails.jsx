import React from 'react';

function TransactionDetails({ transaction }) {
  if (!transaction) return null;

  return (
    <div className="tx-details-card">
      <h3 className="section-heading">Transaction Metadata</h3>
      <div className="details-grid">
        <div className="detail-field">
          <span className="detail-label">Transaction ID</span>
          <span className="detail-value mono">{transaction.transaction_id}</span>
        </div>
        
        <div className="detail-field">
          <span className="detail-label">Timestamp</span>
          <span className="detail-value">{transaction.timestamp}</span>
        </div>

        <div className="detail-field">
          <span className="detail-label">Sender Account</span>
          <span className="detail-value mono">{transaction.sender_id}</span>
        </div>

        <div className="detail-field">
          <span className="detail-label">Receiver Account</span>
          <span className="detail-value mono">{transaction.receiver_id}</span>
        </div>

        <div className="detail-field">
          <span className="detail-label">Amount</span>
          <span className="detail-value">₹{transaction.amount?.toLocaleString('en-IN') || '0.00'}</span>
        </div>

        <div className="detail-field">
          <span className="detail-label">Payment Channel</span>
          <span className="detail-value">{transaction.payment_method}</span>
        </div>
      </div>
    </div>
  );
}

export default TransactionDetails;
