from pydantic import BaseModel
from typing import List

class BalanceResponse(BaseModel):
    asset: str
    balance: int

class UserBalancesResponse(BaseModel):
    userId: int
    balances: List[BalanceResponse]

class TopUpRequest(BaseModel):
    userId: int
    assetCode: str
    amount: int

class TransactionResponse(BaseModel):
    transactionId: str
    status: str
