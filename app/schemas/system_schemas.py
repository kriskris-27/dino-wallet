from pydantic import BaseModel
from typing import List
from .user_schemas import BalanceResponse

class SystemBalancesResponse(BaseModel):
    systemName: str
    balances: List[BalanceResponse]
