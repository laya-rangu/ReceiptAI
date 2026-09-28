from datetime import date

from fastapi import HTTPException
from sqlalchemy import select

from .models import Receipt, ReceiptItem
from .schemas import ReceiptDraft


def validate_finances(draft: ReceiptDraft):
    errors = []
    item_sum = sum(item.line_total_cents for item in draft.items)
    if item_sum != draft.subtotal_cents:
        errors.append(
            f"Items add up to {item_sum / 100:.2f}, but subtotal is {draft.subtotal_cents / 100:.2f}."
        )
    expected = draft.subtotal_cents - draft.discount_cents + draft.fees_cents
    if not draft.tax_included:
        expected += draft.tax_cents
    if expected != draft.total_cents:
        errors.append(
            f"Expected total {expected / 100:.2f}; receipt total is {draft.total_cents / 100:.2f}."
        )
    if draft.discount_cents > draft.subtotal_cents:
        errors.append("Discount cannot exceed subtotal.")
    if draft.purchased_at > date.today():
        errors.append("Purchase date is in the future.")
    return errors


def apply_draft(receipt: Receipt, draft: ReceiptDraft):
    for field, value in draft.model_dump(exclude={"items"}).items():
        setattr(receipt, field, value)
    receipt.items = [ReceiptItem(**item.model_dump()) for item in draft.items]
    receipt.validation_errors = validate_finances(draft)


def owned_receipt(db, user_id, receipt_id):
    receipt = db.scalar(select(Receipt).where(Receipt.id == receipt_id, Receipt.user_id == user_id))
    if not receipt:
        raise HTTPException(404, "Receipt not found")
    return receipt


def possible_duplicates(db, receipt):
    if not receipt.purchased_at or not receipt.total_cents:
        return []
    rows = db.scalars(
        select(Receipt).where(
            Receipt.user_id == receipt.user_id,
            Receipt.id != receipt.id,
            Receipt.purchased_at == receipt.purchased_at,
            Receipt.total_cents == receipt.total_cents,
            Receipt.status == "READY",
        )
    ).all()
    return [
        {"id": row.id, "merchant_name": row.merchant_name}
        for row in rows
        if row.merchant_name.casefold().strip() == receipt.merchant_name.casefold().strip()
    ]


def serialize(receipt: Receipt):
    return {
        "id": receipt.id,
        "source_type": receipt.source_type,
        "status": receipt.status,
        "merchant_name": receipt.merchant_name,
        "purchased_at": receipt.purchased_at.isoformat() if receipt.purchased_at else None,
        "currency": receipt.currency,
        "subtotal_cents": receipt.subtotal_cents,
        "discount_cents": receipt.discount_cents,
        "tax_cents": receipt.tax_cents,
        "fees_cents": receipt.fees_cents,
        "total_cents": receipt.total_cents,
        "tax_included": receipt.tax_included,
        "category": receipt.category,
        "notes": receipt.notes,
        "validation_errors": receipt.validation_errors,
        "created_at": receipt.created_at,
        "has_file": bool(receipt.files),
        "items": [
            {
                "raw_name": i.raw_name,
                "normalized_name": i.normalized_name,
                "quantity": str(i.quantity),
                "line_total_cents": i.line_total_cents,
                "category": i.category,
            }
            for i in receipt.items
        ],
    }
