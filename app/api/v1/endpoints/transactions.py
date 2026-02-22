from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import logging
import uuid
from ....db import get_db
from ....models import User, Account, Balance, AssetType, LedgerTransaction, LedgerEntry, TransactionType
from ....schemas import transaction_schemas

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/topup", response_model=transaction_schemas.TransactionResponse)
def top_up_wallet(request: transaction_schemas.TopUpRequest, db: Session = Depends(get_db)):
    scoped_key = f"user_{request.userId}:{request.idempotencyKey}"
    existing_tx = db.query(LedgerTransaction).filter(LedgerTransaction.idempotency_key == scoped_key).first()
    if existing_tx:
        return {"transactionId": str(existing_tx.id), "status": "completed"}

    asset = db.query(AssetType).filter(AssetType.code == request.assetCode).first()
    if not asset:
        raise HTTPException(status_code=400, detail="Invalid asset code")
    
    user_account = db.query(Account).filter(Account.user_id == request.userId, Account.asset_type_id == asset.id).first()
    treasury_account = db.query(Account).filter(Account.system_name == "TREASURY", Account.asset_type_id == asset.id).first()
    
    if not user_account or not treasury_account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account_ids = sorted([user_account.id, treasury_account.id])
    balances = db.query(Balance).filter(Balance.account_id.in_(account_ids)).with_for_update().all()
    if len(balances) != 2:
        raise HTTPException(status_code=404, detail="Balance record not found")
        
    balance_map = {b.account_id: b for b in balances}
    user_balance = balance_map[user_account.id]
    treasury_balance = balance_map[treasury_account.id]
    
    if treasury_balance.balance < request.amount:
        raise HTTPException(status_code=400, detail=f"Insufficient treasury funds")
    
    user_balance.balance += request.amount
    treasury_balance.balance -= request.amount
    
    transaction_id = uuid.uuid4()
    new_tx = LedgerTransaction(
        id=transaction_id, type=TransactionType.TOPUP, idempotency_key=scoped_key,
        asset_type_id=asset.id, amount=request.amount, from_account_id=treasury_account.id, to_account_id=user_account.id
    )
    new_tx.entries.extend([LedgerEntry(account_id=treasury_account.id, amount=-request.amount), LedgerEntry(account_id=user_account.id, amount=request.amount)])
    
    db.add(new_tx)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("Error during top-up")
        raise HTTPException(status_code=500, detail="Transaction failed")
    
    return {"transactionId": str(transaction_id), "status": "completed"}

@router.post("/spend", response_model=transaction_schemas.TransactionResponse)
def spend_credits(request: transaction_schemas.SpendRequest, db: Session = Depends(get_db)):
    scoped_key = f"user_{request.userId}:{request.idempotencyKey}"
    existing_tx = db.query(LedgerTransaction).filter(LedgerTransaction.idempotency_key == scoped_key).first()
    if existing_tx:
        return {"transactionId": str(existing_tx.id), "status": "completed"}

    asset = db.query(AssetType).filter(AssetType.code == request.assetCode).first()
    if not asset:
        raise HTTPException(status_code=400, detail="Invalid asset code")
    
    user_account = db.query(Account).filter(Account.user_id == request.userId, Account.asset_type_id == asset.id).first()
    treasury_account = db.query(Account).filter(Account.system_name == "TREASURY", Account.asset_type_id == asset.id).first()
    
    if not user_account or not treasury_account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account_ids = sorted([user_account.id, treasury_account.id])
    balances = db.query(Balance).filter(Balance.account_id.in_(account_ids)).with_for_update().all()
    if len(balances) != 2:
        raise HTTPException(status_code=404, detail="Balance record not found")
        
    balance_map = {b.account_id: b for b in balances}
    user_balance = balance_map[user_account.id]
    treasury_balance = balance_map[treasury_account.id]
    
    if user_balance.balance < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    user_balance.balance -= request.amount
    treasury_balance.balance += request.amount
    
    transaction_id = uuid.uuid4()
    new_tx = LedgerTransaction(
        id=transaction_id, type=TransactionType.SPEND, idempotency_key=scoped_key,
        asset_type_id=asset.id, amount=request.amount, from_account_id=user_account.id, to_account_id=treasury_account.id
    )
    new_tx.entries.extend([LedgerEntry(account_id=user_account.id, amount=-request.amount), LedgerEntry(account_id=treasury_account.id, amount=request.amount)])
    
    db.add(new_tx)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("Error during spend")
        raise HTTPException(status_code=500, detail="Transaction failed")
    
    return {"transactionId": str(transaction_id), "status": "completed"}

@router.post("/transfer", response_model=transaction_schemas.TransactionResponse)
def transfer_credits(request: transaction_schemas.TransferRequest, db: Session = Depends(get_db)):
    scoped_key = f"user_{request.fromUserId}:{request.idempotencyKey}"
    existing_tx = db.query(LedgerTransaction).filter(LedgerTransaction.idempotency_key == scoped_key).first()
    if existing_tx:
        return {"transactionId": str(existing_tx.id), "status": "completed"}

    asset = db.query(AssetType).filter(AssetType.code == request.assetCode).first()
    if not asset:
        raise HTTPException(status_code=400, detail="Invalid asset code")
    
    from_account = db.query(Account).filter(Account.user_id == request.fromUserId, Account.asset_type_id == asset.id).first()
    to_account = db.query(Account).filter(Account.user_id == request.toUserId, Account.asset_type_id == asset.id).first()
    
    if not from_account or not to_account:
        raise HTTPException(status_code=404, detail="Account not found")
    if from_account.id == to_account.id:
        raise HTTPException(status_code=400, detail="Cannot transfer to self")

    account_ids = sorted([from_account.id, to_account.id])
    balances = db.query(Balance).filter(Balance.account_id.in_(account_ids)).with_for_update().all()
    if len(balances) != 2:
        raise HTTPException(status_code=404, detail="Balance record not found")
        
    balance_map = {b.account_id: b for b in balances}
    from_balance = balance_map[from_account.id]
    to_balance = balance_map[to_account.id]
    
    if from_balance.balance < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    from_balance.balance -= request.amount
    to_balance.balance += request.amount
    
    transaction_id = uuid.uuid4()
    new_tx = LedgerTransaction(
        id=transaction_id, type=TransactionType.TRANSFER, idempotency_key=scoped_key,
        asset_type_id=asset.id, amount=request.amount, from_account_id=from_account.id, to_account_id=to_account.id
    )
    new_tx.entries.extend([LedgerEntry(account_id=from_account.id, amount=-request.amount), LedgerEntry(account_id=to_account.id, amount=request.amount)])
    
    db.add(new_tx)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("Error during transfer")
        raise HTTPException(status_code=500, detail="Transaction failed")
    
    return {"transactionId": str(transaction_id), "status": "completed"}
