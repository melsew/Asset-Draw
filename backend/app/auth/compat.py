"""Compatibility endpoints matching the frontend API service contracts.

These are thin adapters over the existing auth router's OTP flow.
They provide the /register and /verify-otp paths that the frontend calls.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import create_access_token
from app.auth.services import roles_for_user
from app.core.db import get_db
from app.users.models import User

compat_router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    phone: str = Field(..., min_length=9)
    password: str = Field(..., min_length=4)
    display_name: str = Field(..., min_length=1)


class RegisterOut(BaseModel):
    message: str


class OtpVerifyIn(BaseModel):
    phone: str
    otp: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _phone_e164(phone: str) -> str:
    """Convert 09xxxxxxxx or +251xxxxxxxx to E.164."""
    p = phone.strip()
    if p.startswith("+"):
        return p
    if p.startswith("09"):
        return "+251" + p[1:]
    if p.startswith("9") and len(p) == 9:
        return "+251" + p
    return "+" + p


@compat_router.post("/register", response_model=RegisterOut, status_code=201)
def register(
    body: RegisterIn,
    session: Annotated[Session, Depends(get_db)],
) -> RegisterOut:
    """Register a new consumer account (phone + password).

    In the MVP, OTP verification is simulated — we create the user active.
    Real SMS integration is configured via SMS provider (D-03).
    """
    from app.auth.security import hash_password  # type: ignore[attr-defined]

    phone_e164 = _phone_e164(body.phone)

    # Check for existing user
    existing = session.scalar(select(User).where(User.phone == phone_e164))
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    # Hash password using Argon2id (via the existing security module)
    try:
        pw_hash = hash_password(body.password)
    except Exception:
        # Fallback if hash_password not yet available — use bcrypt or plain argon2
        from passlib.hash import argon2
        pw_hash = argon2.hash(body.password)

    user = User(
        phone=phone_e164,
        password_hash=pw_hash,
        status="ACTIVE",
        phone_verified_at=None,  # set after OTP verify
    )
    session.add(user)
    session.flush()

    # Assign PARTICIPANT role
    from app.users.models import Role, UserRole
    role = session.scalar(select(Role).where(Role.name == "PARTICIPANT"))
    if role:
        ur = UserRole(user_id=user.id, role_id=role.id)
        session.add(ur)

    session.commit()
    return RegisterOut(message="Registration successful. Please verify your phone number.")


@compat_router.post("/verify-otp", response_model=TokenOut)
def verify_otp(
    body: OtpVerifyIn,
    session: Annotated[Session, Depends(get_db)],
) -> TokenOut:
    """Verify OTP and issue access token.

    MVP: accepts any 6-digit code (real SMS integration pending D-03).
    The OTP value '000000' is the sandbox code.
    """
    phone_e164 = _phone_e164(body.phone)

    user = session.scalar(select(User).where(User.phone == phone_e164))
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    # MVP sandbox: any code is accepted
    # TODO (D-03): integrate real OTP challenge verification
    if len(body.otp) != 6 or not body.otp.isdigit():
        raise HTTPException(status_code=400, detail="Invalid OTP format")

    # Mark phone as verified
    if user.phone_verified_at is None:
        user.phone_verified_at = datetime.now(timezone.utc)
        session.commit()

    roles = list(roles_for_user(session, user.id))
    token = create_access_token(user.id, roles)
    return TokenOut(access_token=token, token_type="bearer")


@compat_router.post("/login")
async def participant_login(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> TokenOut:
    """OAuth2 password-grant compatible login for participants (form-encoded)."""
    from urllib.parse import parse_qs
    body_bytes = await request.body()
    try:
        params = parse_qs(body_bytes.decode())
        username = (params.get("username") or params.get("phone") or [""])[0]
        password = (params.get("password") or [""])[0]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid form body")

    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password are required")

    phone_e164 = _phone_e164(username)
    user = session.scalar(select(User).where(User.phone == phone_e164))
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Incorrect phone number or password")
    if user.status != "ACTIVE":
        raise HTTPException(status_code=401, detail="Account suspended")

    from app.auth.security import verify_password
    if not verify_password(user.password_hash, password):
        raise HTTPException(status_code=401, detail="Incorrect phone number or password")

    roles = list(roles_for_user(session, user.id))
    token = create_access_token(user.id, roles)
    return TokenOut(access_token=token, token_type="bearer")
