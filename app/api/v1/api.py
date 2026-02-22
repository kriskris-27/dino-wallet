from fastapi import APIRouter
from .endpoints import users, transactions, treasury

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(transactions.router, tags=["transactions"])
api_router.include_router(treasury.router, prefix="/treasury", tags=["treasury"])
