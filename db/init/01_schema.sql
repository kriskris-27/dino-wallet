-- 01_schema.sql

-- Types
CREATE TYPE owner_type AS ENUM ('USER', 'SYSTEM');
CREATE TYPE transaction_type AS ENUM ('TOPUP', 'BONUS', 'SPEND');

-- Asset Types Table
CREATE TABLE asset_types (
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Users Table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Accounts Table
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    owner_type owner_type NOT NULL,
    user_id INTEGER NULL REFERENCES users(id),
    system_name VARCHAR(64) NULL,
    asset_type_id INTEGER NOT NULL REFERENCES asset_types(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT owner_check CHECK (
        (owner_type = 'USER' AND user_id IS NOT NULL AND system_name IS NULL) OR
        (owner_type = 'SYSTEM' AND system_name IS NOT NULL AND user_id IS NULL)
    ),
    UNIQUE (owner_type, COALESCE(user_id, 0), COALESCE(system_name, ''), asset_type_id)
);

-- Balances Cache Table
CREATE TABLE balances (
    account_id INTEGER PRIMARY KEY REFERENCES accounts(id),
    balance BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT balance_positive CHECK (balance >= 0)
);

-- Ledger Transactions Table
CREATE TABLE ledger_transactions (
    id UUID PRIMARY KEY,
    type transaction_type NOT NULL,
    idempotency_key VARCHAR(64) NOT NULL UNIQUE,
    asset_type_id INTEGER NOT NULL REFERENCES asset_types(id),
    amount BIGINT NOT NULL CHECK (amount > 0),
    from_account_id INTEGER NULL REFERENCES accounts(id),
    to_account_id INTEGER NULL REFERENCES accounts(id),
    metadata JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Ledger Entries Table
CREATE TABLE ledger_entries (
    id BIGSERIAL PRIMARY KEY,
    transaction_id UUID NOT NULL REFERENCES ledger_transactions(id) ON DELETE CASCADE,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    amount BIGINT NOT NULL, -- positive = credit, negative = debit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_ledger_entries_account_id ON ledger_entries(account_id);
CREATE INDEX idx_ledger_entries_transaction_id ON ledger_entries(transaction_id);
