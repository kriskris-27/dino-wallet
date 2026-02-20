from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, Account, Balance, AssetType

router = APIRouter()

@router.get("/users/{user_id}/balances")
def get_user_balances(user_id: int, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Query balances for the user
    results = (
        db.query(AssetType.code, Balance.balance)
        .join(Account, Account.asset_type_id == AssetType.id)
        .join(Balance, Balance.account_id == Account.id)
        .filter(Account.user_id == user_id)
        .all()
    )
    
    balances = [{"asset": row.code, "balance": row.balance} for row in results]
    
    return {
        "userId": user_id,
        "balances": balances
    }
