import calendar
import re
from datetime import date, timedelta

from sqlalchemy import func, or_, select

from .models import Receipt, ReceiptItem

CATEGORIES = ["Groceries", "Food & drink", "Shopping", "Transport", "Health", "Other"]


def receipt_query(user_id, search="", category=None, source=None, start=None, end=None):
    query = select(Receipt).where(Receipt.user_id == user_id)
    if search:
        pattern = "%" + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        query = query.where(
            or_(
                Receipt.merchant_name.ilike(pattern, escape="\\"),
                Receipt.items.any(
                    or_(
                        ReceiptItem.normalized_name.ilike(pattern, escape="\\"),
                        ReceiptItem.raw_name.ilike(pattern, escape="\\"),
                    )
                ),
            )
        )
    if category:
        query = query.where(Receipt.category == category)
    if source:
        query = query.where(Receipt.source_type == source)
    if start:
        query = query.where(Receipt.purchased_at >= start)
    if end:
        query = query.where(Receipt.purchased_at <= end)
    return query


def spending(db, user_id, start=None, end=None):
    query = receipt_query(user_id, start=start, end=end).where(Receipt.status == "READY")
    ids = query.with_only_columns(Receipt.id)
    total, count = db.execute(
        select(func.coalesce(func.sum(Receipt.total_cents), 0), func.count()).where(
            Receipt.id.in_(ids)
        )
    ).one()
    categories = db.execute(
        select(Receipt.category, func.sum(Receipt.total_cents))
        .where(Receipt.id.in_(ids))
        .group_by(Receipt.category)
        .order_by(func.sum(Receipt.total_cents).desc())
    ).all()
    daily = db.execute(
        select(Receipt.purchased_at, func.sum(Receipt.total_cents))
        .where(Receipt.id.in_(ids))
        .group_by(Receipt.purchased_at)
        .order_by(Receipt.purchased_at)
    ).all()
    merchants = db.scalar(
        select(func.count(func.distinct(Receipt.merchant_name))).where(Receipt.id.in_(ids))
    )
    pending = db.scalar(
        select(func.count())
        .select_from(Receipt)
        .where(Receipt.user_id == user_id, Receipt.status != "READY")
    )
    return {
        "total_cents": total,
        "receipt_count": count,
        "merchant_count": merchants,
        "pending_count": pending,
        "currency": "USD",
        "categories": [{"name": name, "total_cents": value} for name, value in categories],
        "daily": [{"date": day.isoformat(), "total_cents": value} for day, value in daily],
    }


def answer_question(db, user_id, question):
    q = question.lower().strip()
    today = date.today()
    start = end = None
    period = "across all your saved receipts"
    if "last month" in q:
        end = today.replace(day=1) - timedelta(days=1)
        start = end.replace(day=1)
        period = f"in {calendar.month_name[start.month]} {start.year}"
    elif "this month" in q:
        start, end = today.replace(day=1), today
        period = "this month"
    elif "last 30 days" in q:
        start, end = today - timedelta(days=29), today
        period = "in the last 30 days"
    elif "yesterday" in q:
        start = end = today - timedelta(days=1)
        period = "yesterday"
    elif "today" in q:
        start = end = today
        period = "today"
    category = next((cat for cat in CATEGORIES if cat.lower() in q), None)
    if "grocery" in q:
        category = "Groceries"
    if "return" in q or "warranty" in q:
        return (
            "Your receipts do not include return or warranty policies. I can find a purchase date, but I cannot verify eligibility without the retailer’s terms.",
            [],
            "limitation",
        )
    if any(term in q for term in ["spend", "spent", "total", "how much"]):
        if not any(
            term in q
            for term in [
                "this month",
                "last month",
                "last 30 days",
                "today",
                "yesterday",
                "all time",
                "overall",
                "everything",
                "total",
                "all my",
            ]
        ):
            return (
                "Which period should I use: this month, last month, last 30 days, or all time? You can also name a receipt category, such as groceries.",
                [],
                "clarification",
            )
        if any(
            term in q for term in ["week", "year", "between", "more", "less", "compare"]
        ) or re.search(r"\b\d{4}\b", q):
            return (
                "I can calculate this month, last month, last 30 days, or all-time spending, optionally by receipt category. Custom periods and price comparisons are not available yet.",
                [],
                "limitation",
            )
        # Recognize only the documented aggregate templates. Never silently ignore merchant/product filters.
        allowed = {
            "how",
            "much",
            "did",
            "i",
            "have",
            "do",
            "we",
            "spend",
            "spent",
            "spending",
            "total",
            "what",
            "is",
            "my",
            "the",
            "show",
            "me",
            "in",
            "on",
            "at",
            "for",
            "this",
            "last",
            "month",
            "30",
            "days",
            "all",
            "time",
            "overall",
            "everything",
            "today",
            "yesterday",
            "and",
            "by",
            "category",
            "receipt",
            "receipts",
        }
        words = (
            set(re.findall(r"\w+", q))
            - set(re.findall(r"\w+", (category or "").lower()))
            - {"grocery"}
        )
        if words - allowed:
            return (
                "I can calculate spending by period and receipt category. Try “How much did I spend this month?” or “Total groceries spending last month”. Merchant and product spending filters are not supported yet.",
                [],
                "clarification",
            )
        query = receipt_query(user_id, category=category, start=start, end=end).where(
            Receipt.status == "READY"
        )
        rows = db.scalars(query.order_by(Receipt.purchased_at.desc(), Receipt.id)).all()
        total = db.scalar(
            select(func.coalesce(func.sum(Receipt.total_cents), 0)).where(
                Receipt.id.in_(query.with_only_columns(Receipt.id))
            )
        )
        text = (
            f"You spent ${total / 100:,.2f} USD {period}"
            + (f" on receipts categorized as {category.lower()}" if category else "")
            + f", across {len(rows)} saved receipt{'s' if len(rows) != 1 else ''}."
        )
        if not rows:
            text += " There are no matching saved receipts. Unconfirmed uploads are excluded."
        text += " Category totals include the full receipt, including taxes and discounts."
        return text, rows[:20], "sql_analytics"
    if any(term in q for term in ["find", "bought", "buy", "receipt", "search"]):
        ignored = {
            "find",
            "the",
            "my",
            "receipt",
            "receipts",
            "for",
            "where",
            "is",
            "are",
            "i",
            "bought",
            "buy",
            "when",
            "did",
            "last",
            "please",
            "search",
            "a",
            "an",
            "show",
            "me",
        }
        terms = [word for word in re.findall(r"[\w'-]+", q) if word not in ignored]
        search = " ".join(terms)
        rows = db.scalars(
            receipt_query(user_id, search=search)
            .where(Receipt.status == "READY")
            .order_by(Receipt.purchased_at.desc(), Receipt.id)
            .limit(10)
        ).all()
        if not rows:
            return (
                "I could not find a saved receipt matching that search. Try an exact product or merchant name, such as “Find oat milk”. Semantic search is not connected yet.",
                [],
                "keyword_search",
            )
        latest = rows[0]
        return (
            f"I found {len(rows)} matching receipt{'s' if len(rows) != 1 else ''}. The most recent is from {latest.merchant_name} on {latest.purchased_at:%b %d, %Y}, totaling ${latest.total_cents / 100:,.2f}. Open the sources below to see the items.",
            rows,
            "keyword_search",
        )
    return (
        "I can calculate spending or find saved receipts using exact names. Try “How much did I spend this month?”, “Total groceries spending last month”, or “Find headphones”. AI semantic search is planned for the next milestone.",
        [],
        "help",
    )
