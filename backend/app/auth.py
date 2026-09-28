import hashlib
import hmac
import secrets
import time

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import LoginSession, User

COOKIE_NAME = "receiptai_session"


def token_hash(value: str):
    return hashlib.sha256(value.encode()).hexdigest()


def hash_password(password: str):
    salt = secrets.token_hex(16)
    result = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
    return f"{salt}:{result.hex()}"


def verify_password(password: str, encoded: str):
    salt, expected = encoded.split(":")
    result = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
    return hmac.compare_digest(result.hex(), expected)


def create_session(db: Session, user: User, response: Response):
    token = secrets.token_urlsafe(32)
    db.add(
        LoginSession(
            token_hash=token_hash(token), user_id=user.id, expires_at=int(time.time()) + 86400
        )
    )
    db.commit()
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="strict",
        max_age=86400,
        secure=settings.app_env != "development",
        path="/",
    )


def current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(401, "Sign in to continue")
    session = db.get(LoginSession, token_hash(token))
    if not session or session.expires_at <= time.time():
        raise HTTPException(401, "Your session has expired. Please sign in again.")
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(401, "Account not found")
    return user


def merchant_user(user: User = Depends(current_user)):
    if user.role != "merchant":
        raise HTTPException(403, "A merchant account is required")
    return user


def public_user(user: User):
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}


def find_user(db: Session, email: str):
    return db.scalar(select(User).where(User.email == email.lower()))
