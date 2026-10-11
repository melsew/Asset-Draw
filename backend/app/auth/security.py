"""Authentication cryptography. Secrets are supplied only through environment settings."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

PASSWORD_HASHER = PasswordHasher()
ACCESS_TOKEN_SECONDS = 15 * 60
TOKEN_ISSUER = "asset-draw"
TOKEN_AUDIENCE = "asset-draw-api"


class InvalidTokenError(ValueError):
    """Raised when an access token cannot be trusted."""


def _required_key(name: str) -> bytes:
    settings = get_settings()
    value = getattr(settings, name)
    if value is None or not value.get_secret_value():
        raise RuntimeError(f"{name.upper()} must be configured before using authentication")
    encoded = value.get_secret_value().encode("utf-8")
    if len(encoded) < 32:
        raise RuntimeError(f"{name.upper()} must contain at least 32 bytes")
    return encoded


def hash_password(password: str) -> str:
    return PASSWORD_HASHER.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return PASSWORD_HASHER.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def new_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def hash_otp(challenge_id: uuid.UUID, phone: str, code: str) -> str:
    key = _required_key("auth_secret_key")
    message = f"asset-draw/otp/v1\n{challenge_id}\n{phone}\n{code}".encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def verify_otp_hash(expected_hash: str, challenge_id: uuid.UUID, phone: str, code: str) -> bool:
    return hmac.compare_digest(expected_hash, hash_otp(challenge_id, phone, code))


def create_access_token(user_id: uuid.UUID, roles: list[str]) -> str:
    return create_scoped_token(
        user_id,
        token_type="access",
        lifetime=timedelta(seconds=ACCESS_TOKEN_SECONDS),
        roles=sorted(set(roles)),
    )


def create_scoped_token(
    user_id: uuid.UUID,
    *,
    token_type: str,
    lifetime: timedelta,
    roles: list[str] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "iss": TOKEN_ISSUER,
        "aud": TOKEN_AUDIENCE,
        "sub": str(user_id),
        "iat": now,
        "exp": now + lifetime,
        "typ": token_type,
        "jti": str(uuid.uuid4()),
    }
    if roles is not None:
        payload["roles"] = roles
    return jwt.encode(payload, _required_key("auth_secret_key"), algorithm="HS256")


def decode_access_token(token: str) -> dict[str, object]:
    payload = decode_scoped_token(token, expected_type="access")
    if not isinstance(payload.get("roles", []), list):
        raise InvalidTokenError("invalid roles")
    return payload


def decode_scoped_token(token: str, *, expected_type: str) -> dict[str, object]:
    try:
        payload = jwt.decode(
            token,
            _required_key("auth_secret_key"),
            algorithms=["HS256"],
            audience=TOKEN_AUDIENCE,
            issuer=TOKEN_ISSUER,
            options={"require": ["exp", "iat", "iss", "aud", "sub", "typ", "jti"]},
        )
    except (jwt.InvalidTokenError, RuntimeError, ValueError) as exc:
        raise InvalidTokenError("invalid access token") from exc
    if payload.get("typ") != expected_type:
        raise InvalidTokenError("wrong token type")
    try:
        uuid.UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise InvalidTokenError("invalid subject") from exc
    return payload


def encrypt_totp_secret(secret: str) -> bytes:
    key_material = b"asset-draw/totp-encryption/v1\n" + _required_key("auth_encryption_key")
    key = hashlib.sha256(key_material).digest()
    return Fernet(base64.urlsafe_b64encode(key)).encrypt(secret.encode("ascii"))


def decrypt_totp_secret(ciphertext: bytes) -> str:
    key_material = b"asset-draw/totp-encryption/v1\n" + _required_key("auth_encryption_key")
    key = hashlib.sha256(key_material).digest()
    try:
        return Fernet(base64.urlsafe_b64encode(key)).decrypt(ciphertext).decode("ascii")
    except (InvalidToken, UnicodeDecodeError) as exc:
        raise ValueError("unable to decrypt staff MFA secret") from exc