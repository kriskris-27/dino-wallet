-- 02_seed.sql

-- Seed Asset Types
INSERT INTO asset_types (code, name) VALUES
('GOLD', 'Gold Coins'),
('DIAMOND', 'Diamonds'),
('POINT', 'Loyalty Points');

-- Seed Users
INSERT INTO users (username) VALUES
('alice'),
('bob');

-- Seed Accounts (System)
INSERT INTO accounts (owner_type, system_name, asset_type_id)
SELECT 'SYSTEM', 'TREASURY', id FROM asset_types WHERE code = 'GOLD';

INSERT INTO accounts (owner_type, system_name, asset_type_id)
SELECT 'SYSTEM', 'REVENUE', id FROM asset_types WHERE code = 'GOLD';

-- Seed Accounts (Users for GOLD)
INSERT INTO accounts (owner_type, user_id, asset_type_id)
SELECT 'USER', u.id, a.id 
FROM users u, asset_types a 
WHERE u.username IN ('alice', 'bob') AND a.code = 'GOLD';

-- Initialize Balances for all accounts
INSERT INTO balances (account_id, balance)
SELECT id, 0 FROM accounts;

-- Set Initial Balances
-- Alice GOLD (500)
UPDATE balances 
SET balance = 500 
WHERE account_id = (
    SELECT acc.id FROM accounts acc 
    JOIN users u ON acc.user_id = u.id 
    JOIN asset_types at ON acc.asset_type_id = at.id 
    WHERE u.username = 'alice' AND at.code = 'GOLD'
);

-- Bob GOLD (200)
UPDATE balances 
SET balance = 200 
WHERE account_id = (
    SELECT acc.id FROM accounts acc 
    JOIN users u ON acc.user_id = u.id 
    JOIN asset_types at ON acc.asset_type_id = at.id 
    WHERE u.username = 'bob' AND at.code = 'GOLD'
);

-- Treasury GOLD (1,000,000)
UPDATE balances 
SET balance = 1000000 
WHERE account_id = (
    SELECT acc.id FROM accounts acc 
    JOIN asset_types at ON acc.asset_type_id = at.id 
    WHERE acc.system_name = 'TREASURY' AND at.code = 'GOLD'
);
