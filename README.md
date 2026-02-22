# Dino Wallet Service

This is a high-performance virtual wallet backend. I built it with a double-entry ledger system to make sure every cent/coin is accounted for, and it handles heavy concurrent traffic without breaking.

## Tech Stack & Why

*   **FastAPI (Python 3.11)**: It's the fastest way to get a robust API up. It handles async out of the box and the Pydantic integration means I don't have to write manual validation for every request.
*   **PostgreSQL**: For a wallet, you need ACID. Postgres is the industry standard for financial data, and its row-level locking is exactly what we need for concurrency.
*   **SQLAlchemy 2.0**: The new typed syntax makes the DB layer clean and hard to screw up with type errors.
*   **Docker**: To make sure "it works on my machine" means "it works on yours, too."

## Getting Started (Local & Cloud)

Everything is containerized. You can spin up the whole stack (API + DB) with:

```bash
docker-compose up --build
```

### Automatic Database Setup
I've automated the DB initialization. When the container starts, an entrypoint script (`scripts/entrypoint.sh`) runs a Python utility I wrote (`scripts/init_db.py`). 
*   It detects if the database is already set up.
*   If it's empty (like a fresh Neon DB), it automatically runs the `01_schema.sql` and `02_seed.sql` scripts.
*   This seeds asset types (`GOLD`, `DIAMOND`, `POINT`) and initial users (`alice`, `bob`) so you can start testing immediately.

## Concurrency & Safety

Handling simultaneous transactions (like two people spending at the exact same millisecond) is the core problem. Here's my strategy:

1.  **Row-Level Locking**: I use `SELECT ... FOR UPDATE` when reading balances. This locks the specific rows so no other process can touch them until the transaction commits.
2.  **Deadlock Prevention**: To avoid circular waits, I always sort the account IDs and lock them in strict ascending order. If you're moving funds between two accounts, Account 1 always gets locked before Account 2, no matter what.
3.  **Idempotency**: Every write request (`/topup`, `/spend`, etc.) takes an `idempotencyKey`. It's scoped to the user (`user_{id}:{key}`), so retrying a failed network request won't result in charging the user twice.

## Key Endpoints

*   `GET /v1/users/{id}/balances`: Current balances across all assets.
*   `POST /v1/topup`: Buy credits (funded by Treasury).
*   `POST /v1/spend`: Spend credits on in-game items (sent back to Treasury).
*   `POST /v1/bonus`: Loyalty/incentive credits.
*   `GET /v1/users/{id}/transactions`: Full audit log of the user's history.
