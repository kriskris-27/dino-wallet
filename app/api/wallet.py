from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import logging
from ..db import get_db
from ..models import User, Account, Balance, AssetType, LedgerTransaction, LedgerEntry, TransactionType
from . import schemas

# Initialize logger
logger = logging.getLogger(__name__)

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
    # 0. Check idempotency (Problem #2) - Scoped per user
    scoped_key = f"user_{request.userId}:{request.idempotencyKey}"
    existing_tx = db.query(LedgerTransaction).filter(
        LedgerTransaction.idempotency_key == scoped_key
    ).first()
    if existing_tx:
        return {
            "transactionId": str(existing_tx.id),
            "status": "completed"
        }

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
    
    # 3. Update balances with pessimistic local locking (Problem #1)
    # We lock rows in a consistent order (by ID) to prevent deadlocks
    account_ids = sorted([user_account.id, treasury_account.id])
    
    # Executing the query with with_for_update() locks the selected rows in the DB
    # Postgres locks these in the order they appear in the index (account_id)
    balances = (
        db.query(Balance)
        .filter(Balance.account_id.in_(account_ids))
        .with_for_update()
        .all()
    )
    
    if len(balances) != 2:
        raise HTTPException(status_code=404, detail="Balance record not found")
        
    # Map them back for easy update
    balance_map = {b.account_id: b for b in balances}
    user_balance = balance_map[user_account.id]
    treasury_balance = balance_map[treasury_account.id]
    
    # 4. Validate treasury funds (Problem #4)
    if treasury_balance.balance < request.amount:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient treasury funds. Required: {request.amount}, Available: {treasury_balance.balance}"
        )
    
    # Update balances
    user_balance.balance += request.amount
    treasury_balance.balance -= request.amount
    
    # 4. Insert a ledger_transactions row
    import uuid
    transaction_id = uuid.uuid4()
    
    new_tx = LedgerTransaction(
        id=transaction_id,
        type=TransactionType.TOPUP,
        idempotency_key=scoped_key,
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
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError in top_up_wallet: {str(e)}")
        raise HTTPException(status_code=409, detail="Transaction conflict or duplicate detected at database level")
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("Database error occurred during top-up")
        raise HTTPException(status_code=500, detail="A database error occurred while processing the transaction")
    except Exception as e:
        db.rollback()
        logger.exception("Unexpected error during top-up")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
    
    return {
        "transactionId": str(transaction_id),
        "status": "completed"
    }

@router.post("/spend", response_model=schemas.TransactionResponse)
def spend_credits(request: schemas.SpendRequest, db: Session = Depends(get_db)):
    # 0. Check idempotency - Scoped per user
    scoped_key = f"user_{request.userId}:{request.idempotencyKey}"
    existing_tx = db.query(LedgerTransaction).filter(
        LedgerTransaction.idempotency_key == scoped_key
    ).first()
    if existing_tx:
        return {"transactionId": str(existing_tx.id), "status": "completed"}

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
    
    # 3. Update balances with pessimistic local locking
    account_ids = sorted([user_account.id, treasury_account.id])
    balances = (
        db.query(Balance)
        .filter(Balance.account_id.in_(account_ids))
        .with_for_update()
        .all()
    )
    
    if len(balances) != 2:
        raise HTTPException(status_code=404, detail="Balance record not found")
        
    balance_map = {b.account_id: b for b in balances}
    user_balance = balance_map[user_account.id]
    treasury_balance = balance_map[treasury_account.id]
    
    # 4. Validate user funds
    if user_balance.balance < request.amount:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient user funds. Required: {request.amount}, Available: {user_balance.balance}"
        )
    
    # Update balances
    user_balance.balance -= request.amount
    treasury_balance.balance += request.amount
    
    # 5. Insert transaction & entries
    import uuid
    transaction_id = uuid.uuid4()
    
    new_tx = LedgerTransaction(
        id=transaction_id,
        type=TransactionType.SPEND,
        idempotency_key=scoped_key,
        asset_type_id=asset.id,
        amount=request.amount,
        from_account_id=user_account.id,
        to_account_id=treasury_account.id
    )
    
    new_tx.entries.append(LedgerEntry(account_id=user_account.id, amount=-request.amount))
    new_tx.entries.append(LedgerEntry(account_id=treasury_account.id, amount=request.amount))
    
    db.add(new_tx)
    
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError in spend_credits: {str(e)}")
        raise HTTPException(status_code=409, detail="Transaction conflict at database level")
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("Database error during spend")
        raise HTTPException(status_code=500, detail="Database failure")
    
    return {"transactionId": str(transaction_id), "status": "completed"}

@router.post("/transfer", response_model=schemas.TransactionResponse)
def transfer_credits(request: schemas.TransferRequest, db: Session = Depends(get_db)):
    # 0. Check idempotency - Scoped per sender
    scoped_key = f"user_{request.fromUserId}:{request.idempotencyKey}"
    existing_tx = db.query(LedgerTransaction).filter(
        LedgerTransaction.idempotency_key == scoped_key
    ).first()
    if existing_tx:
        return {"transactionId": str(existing_tx.id), "status": "completed"}

    # 1. Resolve asset_type_id
    asset = db.query(AssetType).filter(AssetType.code == request.assetCode).first()
    if not asset:
        raise HTTPException(status_code=400, detail="Invalid asset code")
    
    # 2. Resolve both user accounts
    from_account = db.query(Account).filter(
        Account.user_id == request.fromUserId,
        Account.asset_type_id == asset.id
    ).first()
    
    to_account = db.query(Account).filter(
        Account.user_id == request.toUserId,
        Account.asset_type_id == asset.id
    ).first()
    
    if not from_account or not to_account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Prevent transferring to self
    if from_account.id == to_account.id:
        raise HTTPException(status_code=400, detail="Cannot transfer to the same account")

    # 3. Update balances with pessimistic local locking (Problem #1)
    # Lock rows in a consistent order (by ID) to prevent deadlocks
    account_ids = sorted([from_account.id, to_account.id])
    balances = (
        db.query(Balance)
        .filter(Balance.account_id.in_(account_ids))
        .with_for_update()
        .all()
    )
    
    if len(balances) != 2:
        raise HTTPException(status_code=404, detail="Balance record not found for one or both accounts")
        
    balance_map = {b.account_id: b for b in balances}
    from_balance = balance_map[from_account.id]
    to_balance = balance_map[to_account.id]
    
    # 4. Validate sender funds
    if from_balance.balance < request.amount:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient funds. Required: {request.amount}, Available: {from_balance.balance}"
        )
    
    # Update balances
    from_balance.balance -= request.amount
    to_balance.balance += request.amount
    
    # 5. Insert transaction & entries
    import uuid
    transaction_id = uuid.uuid4()
    
    new_tx = LedgerTransaction(
        id=transaction_id,
        type=TransactionType.TRANSFER, # Use TRANSFER type for user-to-user transfers
        idempotency_key=scoped_key,
        asset_type_id=asset.id,
        amount=request.amount,
        from_account_id=from_account.id,
        to_account_id=to_account.id
    )
    
    new_tx.entries.append(LedgerEntry(account_id=from_account.id, amount=-request.amount))
    new_tx.entries.append(LedgerEntry(account_id=to_account.id, amount=request.amount))
    
    db.add(new_tx)
    
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError in transfer_credits: {str(e)}")
        raise HTTPException(status_code=409, detail="Transaction conflict or duplicate detected at database level")
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("Database error during transfer")
        raise HTTPException(status_code=500, detail="A database error occurred while processing the transaction")
    except Exception as e:
        db.rollback()
        logger.exception("Unexpected error during transfer")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
    
    return {"transactionId": str(transaction_id), "status": "completed"}

@router.get("/users/{user_id}/transactions", response_model=schemas.TransactionHistoryResponse)
def get_user_transaction_history(user_id: int, db: Session = Depends(get_db)):
    # 1. Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 2. Get all accounts for this user to filter transactions
    user_account_ids = [acc.id for acc in db.query(Account.id).filter(Account.user_id == user_id).all()]
    
    if not user_account_ids:
        return {"userId": user_id, "transactions": []}
    
    # 3. Query LedgerTransaction
    # A transaction involves the user if they are the sender or receiver
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
    
    history = []
    for tx in transactions:
        # Determine if it's an inflow or outflow for the user
        # This is a simplification for history display
        history.append({
            "id": str(tx.id),
            "type": tx.type,
            "assetCode": tx.asset_type.code,
            "amount": tx.amount,
            "status": "completed",
            "createdAt": tx.created_at.isoformat()
        })
        
    return {
        "userId": user_id,
        "transactions": history
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
