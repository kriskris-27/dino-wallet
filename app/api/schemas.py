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
    idempotencyKey: str

class SpendRequest(BaseModel):
    userId: int
    assetCode: str
    amount: int
    idempotencyKey: str

class TransferRequest(BaseModel):
    fromUserId: int
    toUserId: int
    assetCode: str
    amount: int
    idempotencyKey: str

class TransactionResponse(BaseModel):
    transactionId: str
    status: str

class SystemBalancesResponse(BaseModel):
    systemName: str
    balances: List[BalanceResponse]
