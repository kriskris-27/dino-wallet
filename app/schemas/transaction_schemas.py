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

class TransferRequest(BaseModel):
    fromUserId: int
    toUserId: int
    assetCode: str
    amount: int = Field(gt=0)
    idempotencyKey: str

class TransactionResponse(BaseModel):
    transactionId: str
    status: str
