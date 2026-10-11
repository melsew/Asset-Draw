from __future__ import annotations

import ipaddress
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import Request, Response
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.auth.models import RefreshSession
from app.auth.security import create_access_token, hash_opaque_token, new_opaque_token
from app.audit.models import AuditLog
from app.core.config import get_settings
from app.core.request_id import request_id_ctx
from app.users.models import ROLE_NAMES, Role, User, UserRole

REFRESH_TOKEN_TTL = timedelta(days=30)
REFRESH_COOKIE = "asset_draw_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def ensure_role(session: Session, role_name: str) -> Role:
    if role_name not in ROLE_NAMES:
        raise ValueError("unknown role")
    session.execute(
        insert(Role).values(name=role_name).on_conflict_do_nothing(index_elements=["name"])
    )
    role = session.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        raise RuntimeError("role initialization failed")
    return role


def assign_role(session: Session, user_id: uuid.UUID, role_name: str, granted_by: uuid.UUID | None) -> None:
    role = ensure_role(session, role_name)
    session.execute(
        insert(UserRole)
        .values(user_id=user_id, role_id=role.id, granted_by=granted_by)
        .on_conflict_do_nothing(index_elements=["user_id", "role_id"])
    )


def roles_for_user(session: Session, user_id: uuid.UUID) -> list[str]:
    return list(
        session.scalars(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .order_by(Role.name)
        ).all()
    )


def make_refresh_session(
    session: Session,
    user_id: uuid.UUID,
    family_id: uuid.UUID | None = None,
) -> tuple[str, RefreshSession]:
    token = new_opaque_token()
    row = RefreshSession(
        id=uuid.uuid4(),
        user_id=user_id,
        family_id=family_id or uuid.uuid4(),
        token_hash=hash_opaque_token(token),
        expires_at=datetime.now(UTC) + REFRESH_TOKEN_TTL,
    )
    session.add(row)
    return token, row


def auth_response(session: Session, user: User, response: Response) -> dict[str, object]:
    refresh_token, refresh_row = make_refresh_session(session, user.id)
    access_token = create_access_token(user.id, roles_for_user(session, user.id))
    session.flush()
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        max_age=int(REFRESH_TOKEN_TTL.total_seconds()),
        path=REFRESH_COOKIE_PATH,
        secure=get_settings().is_production,
        httponly=True,
        samesite="strict",
    )
    return {"access_token": access_token, "token_type": "bearer", "expires_in": 900}


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE,
        path=REFRESH_COOKIE_PATH,
        secure=get_settings().is_production,
        httponly=True,
        samesite="strict",
    )


def write_audit(
    session: Session,
    request: Request,
    *,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    actor_user_id: uuid.UUID | None,
    actor_type: str = "SYSTEM",
) -> None:
    remote_address = request.client.host if request.client else None
    try:
        ip_address = str(ipaddress.ip_address(remote_address)) if remote_address else None
    except ValueError:
        ip_address = None
    user_agent = request.headers.get("user-agent")
    session.add(
        AuditLog(
            actor_user_id=actor_user_id,
            actor_type=actor_type,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            request_id=request_id_ctx.get(),
            ip_address=ip_address,
            user_agent=user_agent[:512] if user_agent else None,
            metadata_={},
            row_hash="0" * 64,
        )
    )
