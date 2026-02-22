import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import DATABASE_URL

def run_sql_file(engine, file_path):
    print(f"Executing {file_path}...")
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    with open(file_path, 'r') as f:
        content = f.read()
        # Simple split by semicolon (not perfect for all cases but works for our scripts)
        statements = content.split(';')
        
    with engine.connect() as conn:
        with conn.begin():
            for statement in statements:
                stmt_stripped = statement.strip()
                if stmt_stripped:
                    try:
                        conn.execute(text(stmt_stripped))
                    except Exception as e:
                        print(f"Error executing statement: {stmt_stripped[:50]}...")
                        print(f"Error detail: {e}")
                        # Depending on the error, we might want to continue or abort.
                        # For initialization, we usually want to know.

def init_db():
    print(f"Connecting to: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Check if tables already exist
            result = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'asset_types')"
            ))
            exists = result.scalar()
            
            if not exists:
                print("Database not initialized. Running schema and seed scripts...")
                # Run schema
                run_sql_file(engine, "db/init/01_schema.sql")
                # Run seed
                run_sql_file(engine, "db/init/02_seed.sql")
                print("Database initialization complete.")
            else:
                print("Database already initialized. Skipping setup.")
                
    except SQLAlchemyError as e:
        print(f"Error during database initialization: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_db()
