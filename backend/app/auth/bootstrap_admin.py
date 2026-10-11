"""One-time operator command for creating the first MFA-protected SUPER_ADMIN."""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import timedelta

import pyotp
from fastapi import Request
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.auth.models import StaffMFA
from app.auth.security import create_scoped_token, encrypt_totp_secret, hash_password
from app.auth.services import assign_role, write_audit
from app.core.config import get_settings
from app.core.db import get_sessionmaker
from app.users.models import Role, User, UserRole

BOOTSTRAP_LOCK_NAMESPACE = 684391
BOOTSTRAP_LOCK_ID = 1


class BootstrapError(ValueError):
    """Raised when the first owner account cannot be safely bootstrapped."""


@dataclass(frozen=True)
class BootstrapResult:
    user_id: uuid.UUID
    setup_token: str
    otpauth_url: str


def _bootstrap_request() -> Request:
    return Request({"type": "http", "headers": [], "client": None})


def bootstrap_first_super_admin(session: Session, email: str, password: str) -> BootstrapResult:
    normalized_email = email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized_email):
        raise BootstrapError("BOOTSTRAP_ADMIN_EMAIL must be a valid email address")
    if not 12 <= len(password) <= 256:
        raise BootstrapError("BOOTSTRAP_ADMIN_PASSWORD must be 12 to 256 characters")

    session.execute(
        text("SELECT pg_advisory_xact_lock(:namespace, :lock_id)"),
        {"namespace": BOOTSTRAP_LOCK_NAMESPACE, "lock_id": BOOTSTRAP_LOCK_ID},
    )
    existing_super_admin = session.scalar(
        select(UserRole.user_id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.name == "SUPER_ADMIN")
        .limit(1)
    )
    if existing_super_admin is not None:
        raise BootstrapError("SUPER_ADMIN already exists; bootstrap is one-time only")

    existing_user = session.scalar(select(User.id).where(User.email.ilike(normalized_email)))
    if existing_user is not None:
        raise BootstrapError("That email already belongs to a user; bootstrap will not promote it")

    user = User(email=normalized_email, password_hash=hash_password(password))
    session.add(user)
    session.flush()
    assign_role(session, user.id, "SUPER_ADMIN", None)

    totp_secret = pyotp.random_base32()
    session.add(
        StaffMFA(
            user_id=user.id,
            totp_secret_encrypted=encrypt_totp_secret(totp_secret),
            enabled_at=None,
        )
    )
    setup_token = create_scoped_token(
        user.id, token_type="mfa_setup", lifetime=timedelta(minutes=10)
    )
    write_audit(
        session,
        _bootstrap_request(),
        action="INITIAL_SUPER_ADMIN_BOOTSTRAPPED",
        entity_type="User",
        entity_id=user.id,
        actor_user_id=None,
        actor_type="SYSTEM",
    )
    session.flush()

    return BootstrapResult(
        user_id=user.id,
        setup_token=setup_token,
        otpauth_url=pyotp.TOTP(totp_secret).provisioning_uri(
            name=normalized_email,
            issuer_name="Asset-Draw",
        ),
    )


def main() -> None:
    settings = get_settings()
    email = settings.bootstrap_admin_email
    password = (
        settings.bootstrap_admin_password.get_secret_value()
        if settings.bootstrap_admin_password is not None
        else ""
    )
    if not email or not password:
        raise SystemExit("Set BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD first")

    try:
        with get_sessionmaker().begin() as session:
            result = bootstrap_first_super_admin(session, email, password)
    except BootstrapError as exc:
        raise SystemExit(str(exc)) from None

    print("Initial SUPER_ADMIN created with MFA pending.")
    print("Use these one-time MFA enrollment values within 10 minutes:")
    print(f"Setup token: {result.setup_token}")
    print(f"Authenticator URI: {result.otpauth_url}")
    print("Confirm enrollment at POST /api/v1/auth/staff/mfa/confirm.")


if __name__ == "__main__":
    main()