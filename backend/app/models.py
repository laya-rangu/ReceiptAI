import time
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def uid():
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(20), default="customer")


class LoginSession(Base):
    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[int] = mapped_column(Integer)


class Sale(Base):
    __tablename__ = "sales"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    merchant_name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    receipt_data: Mapped[dict] = mapped_column(JSON)


class ReceiptClaim(Base):
    __tablename__ = "receipt_claims"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    sale_id: Mapped[str] = mapped_column(ForeignKey("sales.id"), unique=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[int] = mapped_column(Integer)
    claimed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    claimed_at: Mapped[int | None] = mapped_column(Integer)


class Receipt(Base):
    __tablename__ = "receipts"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    sale_id: Mapped[str | None] = mapped_column(ForeignKey("sales.id"), unique=True)
    source_type: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(24), index=True)
    merchant_name: Mapped[str] = mapped_column(String(200), default="Untitled receipt")
    purchased_at: Mapped[date | None] = mapped_column(Date, index=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    subtotal_cents: Mapped[int] = mapped_column(Integer, default=0)
    discount_cents: Mapped[int] = mapped_column(Integer, default=0)
    tax_cents: Mapped[int] = mapped_column(Integer, default=0)
    fees_cents: Mapped[int] = mapped_column(Integer, default=0)
    total_cents: Mapped[int] = mapped_column(Integer, default=0)
    tax_included: Mapped[bool] = mapped_column(Boolean, default=False)
    category: Mapped[str] = mapped_column(String(40), default="Other")
    notes: Mapped[str] = mapped_column(Text, default="")
    validation_errors: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[int] = mapped_column(Integer, default=lambda: int(time.time()))
    items: Mapped[list["ReceiptItem"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    files: Mapped[list["ReceiptFile"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    runs: Mapped[list["ExtractionRun"]] = relationship(cascade="all, delete-orphan")


class ReceiptItem(Base):
    __tablename__ = "receipt_items"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    receipt_id: Mapped[str] = mapped_column(
        ForeignKey("receipts.id", ondelete="CASCADE"), index=True
    )
    raw_name: Mapped[str] = mapped_column(String(300))
    normalized_name: Mapped[str] = mapped_column(String(300))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    line_total_cents: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(40), default="Other")


class ReceiptFile(Base):
    __tablename__ = "receipt_files"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    receipt_id: Mapped[str] = mapped_column(
        ForeignKey("receipts.id", ondelete="CASCADE"), index=True
    )
    object_key: Mapped[str] = mapped_column(String(100))
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    content_type: Mapped[str] = mapped_column(String(60))


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    receipt_id: Mapped[str] = mapped_column(
        ForeignKey("receipts.id", ondelete="CASCADE"), index=True
    )
    model_version: Mapped[str] = mapped_column(String(100))
    outcome: Mapped[str] = mapped_column(String(30))
    raw_output: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[int] = mapped_column(Integer, default=lambda: int(time.time()))


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(15))
    content: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[int] = mapped_column(Integer, default=lambda: int(time.time()))
