import secrets
import time
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .analytics import answer_question, receipt_query, spending
from .auth import (
    COOKIE_NAME,
    create_session,
    current_user,
    find_user,
    hash_password,
    merchant_user,
    public_user,
    token_hash,
    verify_password,
)
from .catalog import CATALOG
from .config import settings
from .db import Base, SessionLocal, engine, get_db
from .ingestion import MAX_UPLOAD_BYTES, enqueue_extraction, file_digest, inspect_file
from .models import ChatMessage, LoginSession, Receipt, ReceiptClaim, ReceiptFile, Sale, User
from .receipts import apply_draft, owned_receipt, possible_duplicates, serialize, validate_finances
from .schemas import (
    ChatInput,
    ClaimInput,
    ConfirmInput,
    LoginInput,
    ReceiptDraft,
    RegisterInput,
    SaleInput,
)
from .seed import seed_demo


@asynccontextmanager
async def lifespan(app):
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    if settings.app_env == "development":
        Base.metadata.create_all(engine)
        if settings.seed_demo:
            with SessionLocal() as db:
                seed_demo(db)
    elif settings.seed_demo:
        raise RuntimeError("SEED_DEMO must be false outside development")
    yield


app = FastAPI(title="ReceiptAI API", version="0.1.0", lifespan=lifespan)
origins = [origin.strip() for origin in settings.allowed_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin not in origins:
            return JSONResponse({"detail": "Request origin is not allowed"}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {
        "status": "ok",
        "extraction_configured": bool(settings.openai_api_key),
        "demo_mode": settings.app_env == "development" and settings.seed_demo,
        "assistant_mode": "deterministic",
        "job_mode": settings.job_mode,
    }


@app.post("/api/auth/register", status_code=201)
def register(body: RegisterInput, response: Response, db: Session = Depends(get_db)):
    if find_user(db, body.email):
        raise HTTPException(409, "This email is already registered")
    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        role="customer",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This email is already registered")
    create_session(db, user, response)
    return public_user(user)


@app.post("/api/auth/login")
def login(body: LoginInput, response: Response, db: Session = Depends(get_db)):
    user = find_user(db, body.email)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Email or password is incorrect")
    create_session(db, user, response)
    return public_user(user)


@app.post("/api/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        db.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash(token)))
        db.commit()
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@app.get("/api/auth/me")
def me(user: User = Depends(current_user)):
    return public_user(user)


@app.get("/api/merchant/products")
def products(user: User = Depends(merchant_user)):
    return CATALOG


@app.post("/api/merchant/sales", status_code=201)
def create_sale(
    body: SaleInput, user: User = Depends(merchant_user), db: Session = Depends(get_db)
):
    catalog = {p["id"]: p for p in CATALOG}
    items = []
    for item in body.items:
        product = catalog.get(item.product_id)
        if not product:
            raise HTTPException(422, "Unknown product")
        items.append(
            {
                "raw_name": product["name"],
                "normalized_name": product["name"],
                "quantity": item.quantity,
                "line_total_cents": product["price_cents"] * item.quantity,
                "category": product["category"],
            }
        )
    subtotal = sum(i["line_total_cents"] for i in items)
    tax = int((Decimal(subtotal) * Decimal("0.08")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    draft = ReceiptDraft(
        merchant_name=user.name,
        purchased_at=date.today(),
        items=items,
        subtotal_cents=subtotal,
        tax_cents=tax,
        total_cents=subtotal + tax,
        category="Food & drink",
    )
    sale = Sale(
        merchant_id=user.id, merchant_name=user.name, receipt_data=draft.model_dump(mode="json")
    )
    db.add(sale)
    db.commit()
    return {"id": sale.id, "status": sale.status, **sale.receipt_data}


@app.post("/api/merchant/sales/{sale_id}/complete")
def complete_sale(sale_id: str, user: User = Depends(merchant_user), db: Session = Depends(get_db)):
    sale = db.scalar(select(Sale).where(Sale.id == sale_id, Sale.merchant_id == user.id))
    if not sale:
        raise HTTPException(404, "Sale not found")
    claim = db.scalar(select(ReceiptClaim).where(ReceiptClaim.sale_id == sale_id))
    if claim and claim.claimed_by:
        raise HTTPException(409, "This sale has already been claimed")
    token = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + 900
    # Reissue only updates an unclaimed row; a concurrent claim cannot be reset.
    if claim:
        result = db.execute(
            update(ReceiptClaim)
            .where(ReceiptClaim.id == claim.id, ReceiptClaim.claimed_by.is_(None))
            .values(token_hash=token_hash(token), expires_at=expires_at)
        )
        if result.rowcount != 1:
            db.rollback()
            raise HTTPException(409, "This sale has already been claimed")
    else:
        db.add(ReceiptClaim(sale_id=sale.id, token_hash=token_hash(token), expires_at=expires_at))
    sale.status = "COMPLETED"
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Sale was completed concurrently. Reissue the QR link.")
    return {
        "sale_id": sale.id,
        "token": token,
        "claim_url": f"{settings.frontend_url}/r/{token}",
        "expires_at": expires_at,
        "total_cents": sale.receipt_data["total_cents"],
    }


def valid_claim(db, token):
    claim = db.scalar(select(ReceiptClaim).where(ReceiptClaim.token_hash == token_hash(token)))
    if not claim:
        raise HTTPException(404, "Receipt link not found")
    if claim.claimed_by:
        raise HTTPException(409, "This receipt has already been claimed")
    if claim.expires_at <= time.time():
        raise HTTPException(
            410, "This receipt link has expired. Ask the merchant for a new QR code."
        )
    return claim


@app.get("/api/public/receipts/{token}")
def preview(token: str, db: Session = Depends(get_db)):
    claim = valid_claim(db, token)
    sale = db.get(Sale, claim.sale_id)
    return {
        "merchant_name": sale.merchant_name,
        "total_cents": sale.receipt_data["total_cents"],
        "currency": "USD",
        "item_count": len(sale.receipt_data["items"]),
        "purchased_at": sale.receipt_data["purchased_at"],
        "expires_at": claim.expires_at,
    }


@app.post("/api/receipts/claim", status_code=201)
def claim_receipt(
    body: ClaimInput, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    now = int(time.time())
    claim = valid_claim(db, body.token)
    result = db.execute(
        update(ReceiptClaim)
        .where(
            ReceiptClaim.id == claim.id,
            ReceiptClaim.token_hash == token_hash(body.token),
            ReceiptClaim.claimed_by.is_(None),
            ReceiptClaim.expires_at > now,
        )
        .values(claimed_by=user.id, claimed_at=now)
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "This receipt link is no longer available")
    sale = db.get(Sale, claim.sale_id)
    receipt = Receipt(user_id=user.id, sale_id=sale.id, source_type="QR", status="READY")
    apply_draft(receipt, ReceiptDraft.model_validate(sale.receipt_data))
    db.add(receipt)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This sale has already been claimed")
    return serialize(receipt)


@app.post("/api/receipts/upload", status_code=202)
async def upload(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    try:
        content_type, extension = inspect_file(data)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    digest = file_digest(data)
    duplicate = db.scalar(
        select(Receipt)
        .join(ReceiptFile)
        .where(Receipt.user_id == user.id, ReceiptFile.file_hash == digest)
    )
    if duplicate:
        raise HTTPException(
            409, {"message": "You already uploaded this file.", "receipt_id": duplicate.id}
        )
    key = secrets.token_hex(24) + extension
    path = settings.storage_path / key
    path.write_bytes(data)
    receipt = Receipt(user_id=user.id, source_type="PHOTO", status="PROCESSING")
    receipt.files = [ReceiptFile(object_key=key, file_hash=digest, content_type=content_type)]
    db.add(receipt)
    try:
        db.commit()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    try:
        enqueue_extraction(receipt.id, background_tasks)
    except Exception:
        receipt.status = "FAILED"
        receipt.validation_errors = [
            "The processing queue is unavailable. Your file is safe. Retry or enter the details manually."
        ]
        db.commit()
    return {"receipt_id": receipt.id, "source_type": "PHOTO", "status": receipt.status}


@app.get("/api/receipts/{receipt_id}/status")
def receipt_status(
    receipt_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    receipt = owned_receipt(db, user.id, receipt_id)
    return {
        "id": receipt.id,
        "status": receipt.status,
        "validation_errors": receipt.validation_errors,
    }


@app.post("/api/receipts/{receipt_id}/retry", status_code=202)
def retry(
    receipt_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    receipt = owned_receipt(db, user.id, receipt_id)
    if receipt.status != "FAILED":
        raise HTTPException(409, "Only failed extractions can be retried")
    receipt.status = "PROCESSING"
    receipt.validation_errors = []
    db.commit()
    try:
        enqueue_extraction(receipt.id, background_tasks)
    except Exception:
        receipt.status = "FAILED"
        receipt.validation_errors = ["The processing queue is unavailable. Try again later."]
        db.commit()
    return {"id": receipt.id, "status": receipt.status}


@app.patch("/api/receipts/{receipt_id}/draft")
def patch_draft(
    receipt_id: str,
    body: ReceiptDraft,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    receipt = owned_receipt(db, user.id, receipt_id)
    if receipt.source_type != "PHOTO" or receipt.status not in {"NEEDS_REVIEW", "FAILED"}:
        raise HTTPException(409, "This receipt cannot be edited")
    apply_draft(receipt, body)
    receipt.status = "NEEDS_REVIEW"
    db.commit()
    return {**serialize(receipt), "possible_duplicates": possible_duplicates(db, receipt)}


@app.post("/api/receipts/{receipt_id}/confirm")
def confirm(
    receipt_id: str,
    body: ConfirmInput,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    receipt = owned_receipt(db, user.id, receipt_id)
    if receipt.status == "READY":
        return serialize(receipt)
    if receipt.status != "NEEDS_REVIEW" or not receipt.items:
        raise HTTPException(409, "Review and save the receipt details first")
    draft_fields = ReceiptDraft.model_fields.keys()
    draft = ReceiptDraft.model_validate(
        {key: value for key, value in serialize(receipt).items() if key in draft_fields}
    )
    errors = validate_finances(draft)
    if errors:
        raise HTTPException(
            422, {"message": "Correct the receipt amounts before confirming.", "errors": errors}
        )
    duplicates = possible_duplicates(db, receipt)
    if duplicates and not body.acknowledge_duplicate:
        raise HTTPException(
            409,
            {
                "message": "This may duplicate a saved purchase. Confirm to keep both.",
                "duplicates": duplicates,
            },
        )
    receipt.status = "READY"
    receipt.validation_errors = []
    db.commit()
    return serialize(receipt)


@app.get("/api/me/receipts")
def history(
    search: str = Query(default="", max_length=200),
    category: str | None = None,
    source: str | None = None,
    start: date | None = None,
    end: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = receipt_query(user.id, search, category, source, start, end)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(
        query.order_by(Receipt.purchased_at.desc(), Receipt.created_at.desc(), Receipt.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [serialize(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.get("/api/me/receipts/{receipt_id}")
def receipt_detail(
    receipt_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    receipt = owned_receipt(db, user.id, receipt_id)
    return {**serialize(receipt), "possible_duplicates": possible_duplicates(db, receipt)}


@app.get("/api/me/receipts/{receipt_id}/file")
def receipt_file(
    receipt_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    receipt = owned_receipt(db, user.id, receipt_id)
    if not receipt.files:
        raise HTTPException(404, "No original file is available for this receipt")
    file = receipt.files[0]
    # PDF downloads are attachments; only decoded images are rendered inline.
    return FileResponse(
        settings.storage_path / file.object_key,
        media_type=file.content_type,
        filename=f"receipt-{receipt.id}"
        + (
            ".pdf"
            if file.content_type == "application/pdf"
            else ".jpg"
            if file.content_type == "image/jpeg"
            else ".png"
        ),
        content_disposition_type="attachment"
        if file.content_type == "application/pdf"
        else "inline",
    )


@app.delete("/api/me/receipts/{receipt_id}", status_code=204)
def delete_receipt(
    receipt_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    receipt = owned_receipt(db, user.id, receipt_id)
    if receipt.status == "PROCESSING":
        raise HTTPException(409, "Wait for processing to finish before deleting this receipt")
    files = [settings.storage_path / f.object_key for f in receipt.files]
    # Removing chat history avoids retaining financial facts about a deleted receipt.
    db.execute(delete(ChatMessage).where(ChatMessage.user_id == user.id))
    db.delete(receipt)
    db.commit()
    for file in files:
        file.unlink(missing_ok=True)
    return Response(status_code=204)


@app.get("/api/me/export")
def export(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Receipt).where(Receipt.user_id == user.id)).all()
    return JSONResponse(
        {"receipts": [serialize(r) for r in rows]},
        headers={"Content-Disposition": 'attachment; filename="receiptai-export.json"'},
    )


@app.get("/api/me/spending")
def spending_summary(
    start: date | None = None,
    end: date | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return spending(db, user.id, start, end)


@app.post("/api/chat")
def chat(body: ChatInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    answer, rows, route = answer_question(db, user.id, body.message)
    # Tool results are scoped to this user; citations are checked again at the output boundary.
    evidence = [
        {
            "id": r.id,
            "merchant_name": r.merchant_name,
            "total_cents": r.total_cents,
            "purchased_at": r.purchased_at.isoformat(),
        }
        for r in rows
        if r.user_id == user.id
    ]
    db.add(ChatMessage(user_id=user.id, role="user", content=body.message))
    reply = ChatMessage(user_id=user.id, role="assistant", content=answer, evidence=evidence)
    db.add(reply)
    db.commit()
    return {
        "id": reply.id,
        "role": "assistant",
        "content": answer,
        "evidence": evidence,
        "route": route,
    }


@app.get("/api/chat/history")
def chat_history(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(100)
    ).all()
    return [
        {"id": row.id, "role": row.role, "content": row.content, "evidence": row.evidence}
        for row in reversed(rows)
    ]
