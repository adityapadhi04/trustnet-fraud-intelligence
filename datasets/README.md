# TRUSTNET - Datasets Directory

This directory contains synthetic transaction datasets used for training, evaluating, and testing the TRUSTNET system.

> [!WARNING]
> **SYNTHETIC DATA COMPLIANCE & PRIVACY**
> - **NO REAL BANKING/FINANCIAL DATA**: To respect user privacy and financial regulations, this repository does **NOT** contain or process any real financial, banking, or customer personal data.
> - **SYNTHETIC DATA ONLY**: All datasets present here are generated synthetically using randomized parameters designed to simulate payment velocities, account hierarchies, mule structures, and common fraud patterns (e.g., rapid transfer loops).
> - **GIT IGNORE**: All generated data files (CSV, Parquet, JSON, etc.) are excluded from version control via `.gitignore`. Only this documentation file is committed.

## Planned Synthetic Data Schemas

### Transactions Table
- `transaction_id`: Unique identifier (string).
- `sender_id`: Account ID of the sender (string).
- `receiver_id`: Account ID of the receiver (string).
- `amount`: Transaction value (float).
- `timestamp`: Date and time of transfer (ISO 8601 string).
- `payment_method`: Channel (e.g., UPI, Card, NetBanking).
- `device_id`: Hash of the device initiating the payment (string).
- `ip_address`: IP address of the sender (string).
- `is_fraud_labeled`: Synthetic fraud flag for supervised model training (integer: 0 or 1).

### User Behavioral Profile Table
- `user_id`: Unique identifier (string).
- `average_amount`: Mean transaction amount over 30 days (float).
- `transaction_count_24h`: Number of transactions in the last 24 hours (integer).
- `mule_risk_indicator`: Calculated structural score based on graph properties (float).
