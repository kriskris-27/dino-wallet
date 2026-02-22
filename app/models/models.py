from sqlalchemy import Column, Integer, String, ForeignKey, BigInteger, Enum as SQLEnum, CheckConstraint, UniqueConstraint, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from ..db import Base

class OwnerType(str, enum.Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"

class TransactionType(str, enum.Enum):
    TOPUP = "TOPUP"
    BONUS = "BONUS"
    SPEND = "SPEND"
    TRANSFER = "TRANSFER"

class AssetType(Base):
    __tablename__ = "asset_types"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    owner_type = Column(SQLEnum(OwnerType), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    system_name = Column(String(64), nullable=True)
    asset_type_id = Column(Integer, ForeignKey("asset_types.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = (
        CheckConstraint(
            "(owner_type = 'USER' AND user_id IS NOT NULL AND system_name IS NULL) OR "
            "(owner_type = 'SYSTEM' AND system_name IS NOT NULL AND user_id IS NULL)",
            name="owner_check"
        ),
        UniqueConstraint("owner_type", "user_id", "system_name", "asset_type_id", name="uq_owner_asset"),
    )

class Balance(Base):
    __tablename__ = "balances"
    account_id = Column(Integer, ForeignKey("accounts.id"), primary_key=True)
    balance = Column(BigInteger, nullable=False, default=0)

    __table_args__ = (
        CheckConstraint("balance >= 0", name="balance_positive"),
    )

class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"
    id = Column(UUID(as_uuid=True), primary_key=True)
    type = Column(SQLEnum(TransactionType), nullable=False)
    idempotency_key = Column(String(64), unique=True, nullable=False)
    asset_type_id = Column(Integer, ForeignKey("asset_types.id"), nullable=False)
    amount = Column(BigInteger, nullable=False)
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    metadata_json = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    entries = relationship("LedgerEntry", back_populates="transaction", cascade="all, delete-orphan")
    asset_type = relationship("AssetType")

    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
    )

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("ledger_transactions.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    amount = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    transaction = relationship("LedgerTransaction", back_populates="entries")
