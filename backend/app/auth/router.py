from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.auth.dependencies import Principal, require_roles
from app.auth.models import OTPChallenge, RefreshSession, StaffInvitation, StaffMFA
from app.auth.security import (
    InvalidTokenError,
    create_access_token,
    create_scoped_token,
    decode_scoped_token,
    decrypt_totp_secret,
    encrypt_totp_secret,
    hash_opaque_token,
    hash_otp,
    hash_password,
    new_opaque_token,
    verify_otp_hash,
    verify_password,
)
from app.core.demo_store import demo_request_otp, demo_verify_otp, is_demo_mode
from app.auth.services import (
    REFRESH_COOKIE,
    REFRESH_TOKEN_TTL,
    assign_role,
    auth_response,
    clear_refresh_cookie,
    ensure_role,
    make_refresh_session,
    roles_for_user,
    write_audit,
)
from app.core.config import get_settings
from app.core.db import get_db
from app.core.rate_limit import RateLimitExceeded, enforce_rate_limit
from app.core.redis_client import get_redis
from app.users.models import ROLE_NAMES, User, UserRole

router = APIRouter(prefix="/auth", tags=["auth"])
admin_router = APIRouter(prefix="/admin/users", tags=["admin-users"])


class OTPRequest(BaseModel):
    phone: str = Field(pattern=r"^\+[1-9][0-9]{6,14}$")


class OTPVerify(BaseModel):
    challenge_id: uuid.UUID
    code: str = Field(pattern=r"^[0-9]{6}$")


class StaffLogin(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class MFAChallengeVerify(BaseModel):
    challenge_token: str
    code: str = Field(pattern=r"^[0-9]{6}$")


class StaffInvitationRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class StaffInvitationAccept(BaseModel):
    invitation_token: str = Field(min_length=20, max_length=256)
    password: str = Field(min_length=12, max_length=256)


class StaffMFAConfirm(BaseModel):
    setup_token: str
    code: str = Field(pattern=r"^[0-9]{6}$")


class RoleAssignment(BaseModel):
    roles: list[str] = Field(min_length=1, max_length=len(ROLE_NAMES))


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _rate_limit(
    request: Request,
    *,
    scope: str,
    identity: str,
    limit: int,
    window_seconds: int,
) -> None:
    try:
        enforce_rate_limit(
            get_redis(),
            scope=scope,
            identity=identity,
            limit=limit,
            window_seconds=window_seconds,
        )
    except RateLimitExceeded:
        raise HTTPException(status_code=429, detail="Too many requests") from None
    except Exception:
        raise HTTPException(status_code=503, detail="Authentication service unavailable") from None


def _require_csrf_headers(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin not in get_settings().cors_origins or request.headers.get("x-csrf-protection") != "1":
        raise HTTPException(status_code=403, detail="Request origin rejected")


def _generic_auth_failure() -> HTTPException:
    return HTTPException(status_code=401, detail="Invalid credentials")


def _new_session_response(
    session: Session,
    user: User,
    response: Response,
    request: Request,
) -> dict[str, object]:
    payload = auth_response(session, user, response)
    write_audit(
        session,
        request,
        action="SESSION_CREATED",
        entity_type="User",
        entity_id=user.id,
        actor_user_id=user.id,
        actor_type="USER",
    )
    session.commit()
    return payload


@router.post("/otp/request", status_code=202)
def request_otp(
    body: OTPRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    if is_demo_mode():
        return demo_request_otp(body.phone)

    settings = get_settings()
    if settings.is_production or settings.sms_provider != "console":
        raise HTTPException(status_code=503, detail="SMS delivery is not configured")

    phone = body.phone.strip()
    _rate_limit(request, scope="otp-ip", identity=_client_ip(request), limit=10, window_seconds=3600)
    _rate_limit(request, scope="otp-phone", identity=phone, limit=3, window_seconds=3600)

    challenge_id = uuid.uuid4()
    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = OTPChallenge(
        id=challenge_id,
        phone=phone,
        code_hash=hash_otp(challenge_id, phone, code),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        attempts=0,
        ip_address=_client_ip(request),
    )
    session.add(challenge)
    write_audit(
        session,
        request,
        action="OTP_REQUESTED",
        entity_type="OTPChallenge",
        entity_id=challenge_id,
        actor_user_id=None,
    )
    session.commit()

    result: dict[str, object] = {
        "challenge_id": str(challenge_id),
        "detail": "If the number is eligible, a verification code has been sent.",
    }
    if settings.environment == "development":
        result["development_code"] = code
    return result


@router.post("/otp/verify")
def verify_otp(
    body: OTPVerify,
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    if is_demo_mode():
        return demo_verify_otp(str(body.challenge_id), body.code)

    _rate_limit(request, scope="otp-verify-ip", identity=_client_ip(request), limit=20, window_seconds=3600)
    _rate_limit(
        request,
        scope="otp-challenge",
        identity=str(body.challenge_id),
        limit=6,
        window_seconds=600,
    )
    challenge = session.scalar(
        select(OTPChallenge).where(OTPChallenge.id == body.challenge_id).with_for_update()
    )
    now = datetime.now(UTC)
    if (
        challenge is None
        or challenge.consumed_at is not None
        or challenge.expires_at <= now
        or challenge.attempts >= 5
    ):
        raise _generic_auth_failure()

    challenge.attempts += 1
    if not verify_otp_hash(challenge.code_hash, challenge.id, challenge.phone, body.code):
        session.commit()
        raise _generic_auth_failure()

    challenge.consumed_at = now
    user = session.scalar(select(User).where(User.phone == challenge.phone).with_for_update())
    is_new_user = user is None
    if user is None:
        user = User(phone=challenge.phone, phone_verified_at=now)
        session.add(user)
        session.flush()
        assign_role(session, user.id, "PARTICIPANT", None)
    elif user.status != "ACTIVE":
        session.commit()
        raise _generic_auth_failure()

    roles = roles_for_user(session, user.id)
    if any(role != "PARTICIPANT" for role in roles):
        session.commit()
        raise _generic_auth_failure()
    if "PARTICIPANT" not in roles:
        assign_role(session, user.id, "PARTICIPANT", None)

    if is_new_user:
        write_audit(
            session,
            request,
            action="PARTICIPANT_REGISTERED",
            entity_type="User",
            entity_id=user.id,
            actor_user_id=user.id,
            actor_type="USER",
        )
    return _new_session_response(session, user, response, request)


@router.post("/login")
def staff_login(
    body: StaffLogin,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    _rate_limit(request, scope="staff-login-ip", identity=_client_ip(request), limit=10, window_seconds=900)
    email = body.email.strip().lower()
    _rate_limit(request, scope="staff-login-account", identity=email, limit=8, window_seconds=900)
    user = session.scalar(select(User).where(func.lower(User.email) == email))

    if user is None or user.password_hash is None:
        # Match the expensive password verification path without revealing account existence.
        hash_password(body.password[:128])
        raise _generic_auth_failure()
    if user.status != "ACTIVE" or not verify_password(user.password_hash, body.password):
        raise _generic_auth_failure()

    roles = roles_for_user(session, user.id)
    staff_mfa = session.get(StaffMFA, user.id)
    if not any(role != "PARTICIPANT" for role in roles) or staff_mfa is None or staff_mfa.enabled_at is None:
        raise _generic_auth_failure()

    challenge_token = create_scoped_token(
        user.id, token_type="mfa_challenge", lifetime=timedelta(minutes=5)
    )
    write_audit(
        session,
        request,
        action="STAFF_PASSWORD_ACCEPTED",
        entity_type="User",
        entity_id=user.id,
        actor_user_id=user.id,
        actor_type="USER",
    )
    session.commit()
    return {"mfa_required": True, "challenge_token": challenge_token, "expires_in": 300}


@router.post("/mfa/verify")
def verify_staff_mfa(
    body: MFAChallengeVerify,
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    _rate_limit(request, scope="staff-mfa-ip", identity=_client_ip(request), limit=10, window_seconds=900)
    try:
        payload = decode_scoped_token(body.challenge_token, expected_type="mfa_challenge")
        user_id = uuid.UUID(str(payload["sub"]))
    except (InvalidTokenError, KeyError, ValueError):
        raise _generic_auth_failure() from None

    user = session.scalar(select(User).where(User.id == user_id).with_for_update())
    staff_mfa = session.get(StaffMFA, user_id)
    if user is None or user.status != "ACTIVE" or staff_mfa is None or staff_mfa.enabled_at is None:
        raise _generic_auth_failure()
    try:
        secret = decrypt_totp_secret(staff_mfa.totp_secret_encrypted)
    except ValueError:
        raise HTTPException(status_code=503, detail="MFA service unavailable") from None
    if not pyotp.TOTP(secret).verify(body.code, valid_window=1):
        raise _generic_auth_failure()
    return _new_session_response(session, user, response, request)


@router.post("/refresh")
def refresh_session(
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    _require_csrf_headers(request)
    _rate_limit(request, scope="refresh-ip", identity=_client_ip(request), limit=60, window_seconds=3600)
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        clear_refresh_cookie(response)
        raise _generic_auth_failure()
    token_hash = hash_opaque_token(token)
    row = session.scalar(
        select(RefreshSession).where(RefreshSession.token_hash == token_hash).with_for_update()
    )
    if row is None:
        clear_refresh_cookie(response)
        raise _generic_auth_failure()
    now = datetime.now(UTC)
    if row.revoked_at is not None or row.replaced_by is not None:
        session.execute(
            update(RefreshSession)
            .where(RefreshSession.family_id == row.family_id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        write_audit(
            session,
            request,
            action="REFRESH_REUSE_DETECTED",
            entity_type="RefreshSession",
            entity_id=row.id,
            actor_user_id=row.user_id,
            actor_type="USER",
        )
        session.commit()
        clear_refresh_cookie(response)
        raise _generic_auth_failure()
    if row.expires_at <= now:
        row.revoked_at = now
        session.commit()
        clear_refresh_cookie(response)
        raise _generic_auth_failure()

    user = session.scalar(select(User).where(User.id == row.user_id).with_for_update())
    if user is None or user.status != "ACTIVE":
        row.revoked_at = now
        session.commit()
        clear_refresh_cookie(response)
        raise _generic_auth_failure()

    new_token, replacement = make_refresh_session(session, user.id, row.family_id)
    row.revoked_at = now
    row.replaced_by = replacement.id
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=new_token,
        max_age=int(REFRESH_TOKEN_TTL.total_seconds()),
        path="/api/v1/auth",
        secure=get_settings().is_production,
        httponly=True,
        samesite="strict",
    )
    write_audit(
        session,
        request,
        action="REFRESH_ROTATED",
        entity_type="RefreshSession",
        entity_id=row.id,
        actor_user_id=user.id,
        actor_type="USER",
    )
    access_token = create_access_token(user.id, roles_for_user(session, user.id))
    session.commit()
    return {"access_token": access_token, "token_type": "bearer", "expires_in": 900}


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    _require_csrf_headers(request)
    token = request.cookies.get(REFRESH_COOKIE)
    if token:
        row = session.scalar(
            select(RefreshSession).where(
                RefreshSession.token_hash == hash_opaque_token(token)
            )
        )
        if row is not None:
            now = datetime.now(UTC)
            session.execute(
                update(RefreshSession)
                .where(RefreshSession.family_id == row.family_id, RefreshSession.revoked_at.is_(None))
                .values(revoked_at=now)
            )
            write_audit(
                session,
                request,
                action="SESSION_REVOKED",
                entity_type="RefreshSession",
                entity_id=row.id,
                actor_user_id=row.user_id,
                actor_type="USER",
            )
            session.commit()
    clear_refresh_cookie(response)
    response.status_code = 204
    return response


@router.post("/staff/invitations", status_code=201)
def invite_staff(
    body: StaffInvitationRequest,
    request: Request,
    principal: Annotated[Principal, Depends(require_roles("SUPER_ADMIN"))],
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    email = body.email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(status_code=422, detail="Invalid email address")
    _rate_limit(request, scope="staff-invite-ip", identity=_client_ip(request), limit=20, window_seconds=3600)
    if session.scalar(select(User.id).where(func.lower(User.email) == email)) is not None:
        raise HTTPException(status_code=409, detail="Invitation cannot be created")
    now = datetime.now(UTC)
    session.execute(
        update(StaffInvitation)
        .where(
            func.lower(StaffInvitation.email) == email,
            StaffInvitation.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )
    invitation_token = new_opaque_token()
    invitation = StaffInvitation(
        email=email,
        token_hash=hash_opaque_token(invitation_token),
        invited_by=principal.user.id,
        expires_at=now + timedelta(hours=1),
    )
    session.add(invitation)
    session.flush()
    write_audit(
        session,
        request,
        action="STAFF_INVITATION_CREATED",
        entity_type="StaffInvitation",
        entity_id=invitation.id,
        actor_user_id=principal.user.id,
        actor_type="USER",
    )
    session.commit()
    return {"invitation_id": str(invitation.id), "invitation_token": invitation_token, "expires_in": 3600}


@router.post("/staff/accept", status_code=201)
def accept_staff_invitation(
    body: StaffInvitationAccept,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    _rate_limit(
        request,
        scope="staff-invite-accept-ip",
        identity=_client_ip(request),
        limit=10,
        window_seconds=3600,
    )
    token_hash = hash_opaque_token(body.invitation_token)
    invitation = session.scalar(
        select(StaffInvitation)
        .where(StaffInvitation.token_hash == token_hash)
        .with_for_update()
    )
    now = datetime.now(UTC)
    if (
        invitation is None
        or invitation.consumed_at is not None
        or invitation.expires_at <= now
        or session.scalar(select(User.id).where(func.lower(User.email) == invitation.email)) is not None
    ):
        raise HTTPException(status_code=400, detail="Invitation is invalid or expired")

    user = User(email=invitation.email, password_hash=hash_password(body.password))
    secret = pyotp.random_base32()
    session.add(user)
    session.flush()
    session.add(
        StaffMFA(
            user_id=user.id,
            totp_secret_encrypted=encrypt_totp_secret(secret),
            recovery_code_hashes=[],
        )
    )
    invitation.consumed_at = now
    setup_token = create_scoped_token(
        user.id, token_type="mfa_setup", lifetime=timedelta(minutes=10)
    )
    write_audit(
        session,
        request,
        action="STAFF_INVITATION_ACCEPTED",
        entity_type="User",
        entity_id=user.id,
        actor_user_id=user.id,
        actor_type="USER",
    )
    session.commit()
    return {
        "user_id": str(user.id),
        "mfa_setup_required": True,
        "setup_token": setup_token,
        "totp_secret": secret,
        "otpauth_url": pyotp.TOTP(secret).provisioning_uri(
            name=invitation.email, issuer_name="Asset-Draw"
        ),
    }


@router.post("/staff/mfa/confirm")
def confirm_staff_mfa(
    body: StaffMFAConfirm,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    _rate_limit(
        request,
        scope="mfa-setup-ip",
        identity=_client_ip(request),
        limit=10,
        window_seconds=900,
    )
    try:
        payload = decode_scoped_token(body.setup_token, expected_type="mfa_setup")
        user_id = uuid.UUID(str(payload["sub"]))
    except (InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=400, detail="MFA setup is invalid or expired") from None
    mfa = session.scalar(select(StaffMFA).where(StaffMFA.user_id == user_id).with_for_update())
    if mfa is None or mfa.enabled_at is not None:
        raise HTTPException(status_code=400, detail="MFA setup is invalid or expired")
    secret = decrypt_totp_secret(mfa.totp_secret_encrypted)
    if not pyotp.TOTP(secret).verify(body.code, valid_window=1):
        raise HTTPException(status_code=400, detail="MFA setup is invalid or expired")
    mfa.enabled_at = datetime.now(UTC)
    write_audit(
        session,
        request,
        action="STAFF_MFA_ENABLED",
        entity_type="User",
        entity_id=user_id,
        actor_user_id=user_id,
        actor_type="USER",
    )
    session.commit()
    return {"mfa_enabled": True, "detail": "MFA enabled. A SUPER_ADMIN must assign your staff role."}


@admin_router.put("/{user_id}/roles")
def set_user_roles(
    user_id: uuid.UUID,
    body: RoleAssignment,
    request: Request,
    principal: Annotated[Principal, Depends(require_roles("SUPER_ADMIN"))],
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    desired_roles = set(body.roles)
    if not desired_roles or not desired_roles.issubset(ROLE_NAMES):
        raise HTTPException(status_code=422, detail="Invalid role assignment")
    target = session.scalar(select(User).where(User.id == user_id).with_for_update())
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    current_roles = set(roles_for_user(session, user_id))
    if "SUPER_ADMIN" in current_roles and "SUPER_ADMIN" not in desired_roles:
        other_super_admin = session.scalar(
            select(UserRole.user_id)
            .join_from(UserRole, __import__("app.users.models", fromlist=["Role"]).Role)
            .where(
                __import__("app.users.models", fromlist=["Role"]).Role.name == "SUPER_ADMIN",
                UserRole.user_id != user_id,
            )
            .limit(1)
        )
        if other_super_admin is None:
            raise HTTPException(status_code=409, detail="At least one SUPER_ADMIN must remain")

    session.query(UserRole).filter(UserRole.user_id == user_id).delete(synchronize_session=False)
    for role_name in sorted(desired_roles):
        assign_role(session, user_id, role_name, principal.user.id)
    write_audit(
        session,
        request,
        action="USER_ROLES_REPLACED",
        entity_type="User",
        entity_id=user_id,
        actor_user_id=principal.user.id,
        actor_type="USER",
    )
    session.commit()
    return {"user_id": str(user_id), "roles": sorted(desired_roles)}