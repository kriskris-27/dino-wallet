from pydantic import BaseModel, Field

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

class BonusRequest(BaseModel):
    userId: int
    assetCode: str
    amount: int = Field(gt=0)
    idempotencyKey: str

class TransactionResponse(BaseModel):
    transactionId: str
    status: str
