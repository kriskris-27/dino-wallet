from pydantic import BaseModel
from typing import List

class BalanceResponse(BaseModel):
    asset: str
    balance: int

class UserBalancesResponse(BaseModel):
    userId: int
    balances: List[BalanceResponse]

class TransactionDetail(BaseModel):
    id: str
    type: str
    assetCode: str
    amount: int
    status: str
    createdAt: str

class TransactionHistoryResponse(BaseModel):
    userId: int
    transactions: List[TransactionDetail]
