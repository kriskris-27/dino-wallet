import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@db:5432/db")

# In a high concurrency environment, we need a larger connection pool
# default is pool_size=5, max_overflow=10. For locust we use much higher limits.
engine = create_engine(
    DATABASE_URL, 
    pool_size=50, 
    max_overflow=100,
    pool_timeout=30
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
