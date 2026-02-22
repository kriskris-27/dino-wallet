from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ....db import get_db
from ....models import User, Account, AssetType, Balance, LedgerTransaction
from ....schemas import user_schemas

router = APIRouter()

@router.get("/{user_id}/balances", response_model=user_schemas.UserBalancesResponse)
def get_user_balances(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    all_assets = db.query(AssetType).all()
    user_balances = (
        db.query(AssetType.code, Balance.balance)
        .join(Account, Account.asset_type_id == AssetType.id)
        .join(Balance, Balance.account_id == Account.id)
        .filter(Account.user_id == user_id)
        .all()
    )
    
    balance_map = {row.code: row.balance for row in user_balances}
    final_balances = [{"asset": a.code, "balance": balance_map.get(a.code, 0)} for a in all_assets]
    
    return {"userId": user_id, "balances": final_balances}

@router.get("/{user_id}/transactions", response_model=user_schemas.TransactionHistoryResponse)
def get_user_transaction_history(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_account_ids = [acc.id for acc in db.query(Account.id).filter(Account.user_id == user_id).all()]
    if not user_account_ids:
        return {"userId": user_id, "transactions": []}
    
    transactions = (
        db.query(LedgerTransaction)
        .join(AssetType, AssetType.id == LedgerTransaction.asset_type_id)
        .filter(
            (LedgerTransaction.from_account_id.in_(user_account_ids)) |
            (LedgerTransaction.to_account_id.in_(user_account_ids))
        )
        .order_by(LedgerTransaction.created_at.desc())
        .all()
    )
    
    history = [{
        "id": str(tx.id),
        "type": tx.type.value if hasattr(tx.type, 'value') else tx.type,
        "assetCode": tx.asset_type.code,
        "amount": tx.amount,
        "status": "completed",
        "createdAt": tx.created_at.isoformat()
    } for tx in transactions]
        
    return {"userId": user_id, "transactions": history}
坐坐 (NO!!)
坐坐
坐坐 (I am doing it.)
