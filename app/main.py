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
            "/": "You are here! Overview of the API.",
            "/health": "Check if the API and Database are breathing.",
            "/v1/users/{id}/balances": "Check how much gold/diamonds a user has.",
            "/v1/users/{id}/transactions": "Full audit trail of everything a user has done.",
            "/v1/topup": "Add credits to a wallet (usually from a real-money purchase).",
            "/v1/spend": "Spend credits on in-game items or skins.",
            "/v1/bonus": "Free loyalty points or system-issued rewards.",
            "/v1/treasury/balances": "Internal view of the system's total funds."
        },
        "rationale": "Built for high-concurrency gaming environments using a double-entry ledger for zero-error accounting."
    }

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "details": str(e)}

app.include_router(api_router, prefix="/v1")
