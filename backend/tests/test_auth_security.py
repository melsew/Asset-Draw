import uuid
from datetime import timedelta

import pytest

from app.auth.security import (
    InvalidTokenError,
    create_access_token,
    create_scoped_token,
    decode_access_token,
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
from app.core.rate_limit import RateLimitExceeded, enforce_rate_limit


@pytest.fixture(autouse=True)
def auth_test_keys(monkeypatch):
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-signing-key-that-is-at-least-32-bytes")
    monkeypatch.setenv("AUTH_ENCRYPTION_KEY", "test-encryption-key-that-is-at-least-32-bytes")
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_argon2_password_hashes_are_not_reversible() -> None:
    encoded = hash_password("Strong-password-0123")
    assert encoded != "Strong-password-0123"
    assert verify_password(encoded, "Strong-password-0123")
    assert not verify_password(encoded, "wrong-password")


def test_access_token_contains_subject_and_rejects_tampering() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id, ["PARTICIPANT"])
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["roles"] == ["PARTICIPANT"]
    with pytest.raises(InvalidTokenError):
        decode_access_token(token + "x")


def test_scoped_tokens_cannot_be_used_as_access_tokens() -> None:
    user_id = uuid.uuid4()
    setup_token = create_scoped_token(
        user_id,
        token_type="mfa_setup",
        lifetime=timedelta(minutes=10),
    )
    assert decode_scoped_token(setup_token, expected_type="mfa_setup")["sub"] == str(user_id)
    with pytest.raises(InvalidTokenError):
        decode_access_token(setup_token)


def test_refresh_and_otp_values_are_only_stored_as_hashes() -> None:
    token = new_opaque_token()
    assert len(token) >= 40
    assert hash_opaque_token(token) != token

    challenge_id = uuid.uuid4()
    phone = "+251911234567"
    code = "004291"
    hashed_code = hash_otp(challenge_id, phone, code)
    assert verify_otp_hash(hashed_code, challenge_id, phone, code)
    assert not verify_otp_hash(hashed_code, challenge_id, phone, "004292")


def test_totp_secret_encryption_roundtrips_and_rejects_wrong_ciphertext() -> None:
    ciphertext = encrypt_totp_secret("JBSWY3DPEHPK3PXP")
    assert b"JBSWY3DPEHPK3PXP" not in ciphertext
    assert decrypt_totp_secret(ciphertext) == "JBSWY3DPEHPK3PXP"
    with pytest.raises(ValueError):
        decrypt_totp_secret(ciphertext[:-2] + b"aa")


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}

    def pipeline(self, transaction: bool = True):
        return FakePipeline(self)


class FakePipeline:
    def __init__(self, client: FakeRedis) -> None:
        self.client = client
        self.key = ""
        self.expiration = 0

    def incr(self, key: str):
        self.key = key
        return self

    def expire(self, key: str, seconds: int, nx: bool = False):
        self.key = key
        self.expiration = seconds
        return self

    def execute(self):
        count = self.client.values.get(self.key, 0) + 1
        self.client.values[self.key] = count
        return count, True


def test_rate_limit_hashes_identity_and_blocks_excess_calls() -> None:
    client = FakeRedis()
    enforce_rate_limit(client, scope="otp", identity="+251911234567", limit=1, window_seconds=60)
    with pytest.raises(RateLimitExceeded):
        enforce_rate_limit(client, scope="otp", identity="+251911234567", limit=1, window_seconds=60)
    assert "+251911234567" not in next(iter(client.values))