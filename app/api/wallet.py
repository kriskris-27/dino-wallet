from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, Account, Balance, AssetType
from .schemas import UserBalancesResponse

router = APIRouter()

@router.get("/users/{user_id}/balances", response_model=UserBalancesResponse)

def get_user_balances(user_id: int, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all available asset types
    all_assets = db.query(AssetType).all()
    
    # Query actual balances for the user
    user_balances = (
        db.query(AssetType.code, Balance.balance)
        .join(Account, Account.asset_type_id == AssetType.id)
        .join(Balance, Balance.account_id == Account.id)
        .filter(Account.user_id == user_id)
        .all()
    )
    
    # Create a lookup map for faster merging
    balance_map = {row.code: row.balance for row in user_balances}
    
    # Construct final balances list ensuring all assets are present
    final_balances = []
    for asset in all_assets:
        final_balances.append({
            "asset": asset.code,
            "balance": balance_map.get(asset.code, 0)
        })
    
    return {
        "userId": user_id,
        "balances": final_balances
    }
