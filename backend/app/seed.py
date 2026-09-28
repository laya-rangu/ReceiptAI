from datetime import date, timedelta

from sqlalchemy import select

from .auth import hash_password
from .models import Receipt, User
from .receipts import apply_draft
from .schemas import ReceiptDraft


def seed_demo(db):
    if db.scalar(select(User.id).limit(1)):
        return
    customer = User(
        name="Alex Morgan",
        email="alex@receiptai.demo",
        password_hash=hash_password("ReceiptAI-demo-2026"),
        role="customer",
    )
    other = User(
        name="Jamie Chen",
        email="jamie@receiptai.demo",
        password_hash=hash_password("ReceiptAI-demo-2026"),
        role="customer",
    )
    merchant = User(
        name="Sunday Coffee",
        email="merchant@receiptai.demo",
        password_hash=hash_password("ReceiptAI-demo-2026"),
        role="merchant",
    )
    db.add_all([customer, other, merchant])
    db.flush()
    samples = [
        (
            "Whole Foods Market",
            "Groceries",
            0,
            "PHOTO",
            [
                ("Organic avocados", 2, 598),
                ("Oat milk", 1, 499),
                ("Sourdough bread", 1, 650),
                ("Fresh berries", 2, 1098),
            ],
            0,
        ),
        (
            "Sunday Coffee",
            "Food & drink",
            1,
            "QR",
            [("Oat milk latte", 1, 550), ("Butter croissant", 1, 425)],
            78,
        ),
        (
            "Urban Outfitters",
            "Shopping",
            2,
            "PHOTO",
            [("Everyday cotton tee", 2, 4800), ("Canvas tote bag", 1, 1800)],
            528,
        ),
        (
            "Trader Joe’s",
            "Groceries",
            3,
            "PHOTO",
            [("Greek yogurt", 2, 698), ("Organic bananas", 1, 249), ("Almond butter", 1, 799)],
            0,
        ),
        ("City Transit", "Transport", 4, "QR", [("Weekly transit pass", 1, 3400)], 0),
        (
            "Green Bowl",
            "Food & drink",
            5,
            "QR",
            [("Harvest bowl", 1, 1450), ("Sparkling water", 1, 350)],
            144,
        ),
        ("Tech Corner", "Shopping", 8, "QR", [("Wireless headphones", 1, 8900)], 712),
        (
            "Neighborhood Pharmacy",
            "Health",
            10,
            "PHOTO",
            [("Daily vitamins", 1, 1699), ("Shampoo", 1, 899)],
            208,
        ),
        (
            "Whole Foods Market",
            "Groceries",
            13,
            "PHOTO",
            [("Oat milk", 2, 998), ("Free range eggs", 1, 649)],
            0,
        ),
        ("Sunday Coffee", "Food & drink", 17, "QR", [("Double espresso", 2, 700)], 56),
        ("Trader Joe’s", "Groceries", 32, "PHOTO", [("Oat milk", 1, 449), ("Granola", 1, 599)], 0),
    ]
    for name, category, days, source, items, tax in samples:
        subtotal = sum(item[2] for item in items)
        draft = ReceiptDraft(
            merchant_name=name,
            category=category,
            purchased_at=date.today() - timedelta(days=days),
            items=[
                {
                    "raw_name": n,
                    "normalized_name": n,
                    "quantity": q,
                    "line_total_cents": p,
                    "category": category,
                }
                for n, q, p in items
            ],
            subtotal_cents=subtotal,
            tax_cents=tax,
            total_cents=subtotal + tax,
            notes="Synthetic demo receipt. No real purchase or source image.",
        )
        receipt = Receipt(user_id=customer.id, source_type=source, status="READY")
        apply_draft(receipt, draft)
        db.add(receipt)
    db.commit()
