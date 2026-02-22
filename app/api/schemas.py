from pydantic import BaseModel, Field
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
    amount: int = Field(gt=0)
    idempotencyKey: str

class SpendRequest(BaseModel):
    userId: int
    assetCode: str
    amount: int = Field(gt=0)
    idempotencyKey: str

class TransferRequest(BaseModel):
    fromUserId: int
    toUserId: int
    assetCode: str
    amount: int = Field(gt=0)
    idempotencyKey: str

class TransactionResponse(BaseModel):
    transactionId: str
    status: str

class SystemBalancesResponse(BaseModel):
    systemName: str
    balances: List[BalanceResponse]

class TransactionDetail(BaseModel):
    id: str
    type: str
    assetCode: str
    amount: int
    status: str
    createdAt: str
    # otherParty: str # We Can add this later if needed

class TransactionHistoryResponse(BaseModel):
    userId: int
    transactions: List[TransactionDetail]
