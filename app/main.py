from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from .db import get_db
from .api.v1.api import api_router

app = FastAPI(title="Wallet Service")

@app.get("/")
def welcome():
    return {
        "message": "Welcome to the Dino Wallet Service API!",
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "/": "Overview of all available routes.",
            "/health": "Check API and Database status.",
            "/v1/users/{id}/balances": "Get current balances for a user.",
            "/v1/users/{id}/transactions": "Get transaction history for a user.",
            "/v1/topup": "Add funds to a user wallet.",
            "/v1/spend": "Deduct funds from a user wallet.",
            "/v1/bonus": "Issue bonus funds to a user.",
            "/v1/treasury/balances": "Check system treasury status."
        },
        "rationale": "Built with a double-entry ledger and pessimistic locking for high-concurrency safety."
    }

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "details": str(e)}

app.include_router(api_router, prefix="/v1")
