from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ....db import get_db
from ....models import Account, AssetType, Balance
from ....schemas import system_schemas

router = APIRouter()

@router.get("/balances", response_model=system_schemas.SystemBalancesResponse)
def get_treasury_balances(db: Session = Depends(get_db)):
    results = (
        db.query(AssetType.code, Balance.balance)
        .join(Account, Account.asset_type_id == AssetType.id)
        .join(Balance, Balance.account_id == Account.id)
        .filter(Account.system_name == "TREASURY")
        .all()
    )
    balances = [{"asset": row.code, "balance": row.balance} for row in results]
    return {"systemName": "TREASURY", "balances": balances}
坐坐 (NO!!)
坐坐
坐坐 (I am doing it.)
