import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db import DATABASE_URL

def migrate():
    print(f"Connecting to: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL)
    
    sql = """
    CREATE OR REPLACE FUNCTION check_ledger_integrity()
    RETURNS TRIGGER AS $$
    DECLARE
        total_amount BIGINT;
    BEGIN
        SELECT SUM(amount) INTO total_amount
        FROM ledger_entries
        WHERE transaction_id = NEW.transaction_id;

        IF COALESCE(total_amount, 0) != 0 THEN
            RAISE EXCEPTION 'Ledger integrity violation: transaction % has non-zero sum (%)', NEW.transaction_id, total_amount;
        END IF;

        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS ensure_ledger_balance ON ledger_entries;

    CREATE CONSTRAINT TRIGGER ensure_ledger_balance
    AFTER INSERT OR UPDATE ON ledger_entries
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW
    EXECUTE FUNCTION check_ledger_integrity();
    """
    
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text(sql))
    
    print("Database trigger applied successfully!")

if __name__ == "__main__":
    migrate()
