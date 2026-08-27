# TRUSTNET - Database Layer

This directory holds the database schemas, seed scripts, and migration files.

## Planned Technology
- **Database**: PostgreSQL (relational storage for transactions, behavior metrics, and alerts).
- **ORM**: SQLAlchemy (Python Object Relational Mapper).
- **Migrations**: Alembic (for database versioning and tables maintenance).

## Planned Entities
- **Users / Accounts**: Unique identifiers, creation date, risk profile state.
- **Transactions**: Financial record of transfer, amount, source, destination, device fingerprint, and computed fraud probability.
- **BehaviorProfiles**: Real-time aggregated statistics per user (e.g. daily transaction velocity).
- **Alerts**: Highlighted incidents containing high risk-scores, SHAP explanations metadata, and status (e.g., Open, Under Investigation, Closed).
