from pydantic import BaseModel
from typing import List

class BalanceResponse(BaseModel):
    asset: str
    balance: int

class UserBalancesResponse(BaseModel):
    userId: int
    balances: List[BalanceResponse]
