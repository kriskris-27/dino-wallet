from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, Account, Balance, AssetType, LedgerTransaction, LedgerEntry, TransactionType
from . import schemas

router = APIRouter()

@router.get("/users/{user_id}/balances", response_model=schemas.UserBalancesResponse)

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

@router.post("/topup", response_model=schemas.TransactionResponse)
def top_up_wallet(request: schemas.TopUpRequest, db: Session = Depends(get_db)):
    # 1. Resolve asset_type_id
    asset = db.query(AssetType).filter(AssetType.code == request.assetCode).first()
    if not asset:
        raise HTTPException(status_code=400, detail="Invalid asset code")
    
    # 2. Resolve user + treasury accounts
    user_account = db.query(Account).filter(
        Account.user_id == request.userId,
        Account.asset_type_id == asset.id
    ).first()
    
    treasury_account = db.query(Account).filter(
        Account.system_name == "TREASURY",
        Account.asset_type_id == asset.id
    ).first()
    
    if not user_account or not treasury_account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # 3. Update balances
    user_balance = db.query(Balance).filter(Balance.account_id == user_account.id).first()
    treasury_balance = db.query(Balance).filter(Balance.account_id == treasury_account.id).first()
    
    if not user_balance or not treasury_balance:
        raise HTTPException(status_code=404, detail="Balance record not found")
        
    # Naive update: just add/subtract
    user_balance.balance += request.amount
    treasury_balance.balance -= request.amount
    
    # 4. Insert a ledger_transactions row
    import uuid
    transaction_id = uuid.uuid4()
    
    # Using a simple idempotency key for now since it's required by the DB schema
    # although the prompt said "No idempotency yet", the DB constraint requires it.
    idempotency_key = f"topup_{transaction_id}"
    
    new_tx = LedgerTransaction(
        id=transaction_id,
        type=TransactionType.TOPUP,
        idempotency_key=idempotency_key,
        asset_type_id=asset.id,
        amount=request.amount,
        from_account_id=treasury_account.id,
        to_account_id=user_account.id
    )
    
    # 5. Insert ledger entries (Double-entry) using relationship
    debit_entry = LedgerEntry(
        account_id=treasury_account.id,
        amount=-request.amount
    )
    credit_entry = LedgerEntry(
        account_id=user_account.id,
        amount=request.amount
    )
    new_tx.entries.extend([debit_entry, credit_entry])
    
    db.add(new_tx)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")
    
    return {
        "transactionId": str(transaction_id),
        "status": "completed"
    }

@router.get("/treasury/balances", response_model=schemas.SystemBalancesResponse)
def get_treasury_balances(db: Session = Depends(get_db)):
    # Query balances for the treasury system name
    results = (
        db.query(AssetType.code, Balance.balance)
        .join(Account, Account.asset_type_id == AssetType.id)
        .join(Balance, Balance.account_id == Account.id)
        .filter(Account.system_name == "TREASURY")
        .all()
    )
    
    balances = [{"asset": row.code, "balance": row.balance} for row in results]
    
    return {
        "systemName": "TREASURY",
        "balances": balances
    }
