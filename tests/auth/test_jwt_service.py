from __future__ import annotations

import time

import pytest

from backend.security.jwt_service import (
    JWTError,
    create_access_token,
    create_refresh_token,
    decode_token,
    encode_token,
)
from backend.security.security_config import reset_security_config


def setup_function():
    reset_security_config()


def test_access_token_roundtrip():
    token = create_access_token("usr_1", extra_claims={"email": "a@b.com"})
    claims = decode_token(token, expected_type="access")
    assert claims["sub"] == "usr_1"
    assert claims["email"] == "a@b.com"
    assert claims["type"] == "access"


def test_refresh_token_type_enforced():
    token = create_refresh_token("usr_1", session_id="ses_1")
    claims = decode_token(token, expected_type="refresh")
    assert claims["sid"] == "ses_1"
    with pytest.raises(JWTError):
        decode_token(token, expected_type="access")


def test_expired_token_rejected():
    token = encode_token({"sub": "usr_1"}, ttl_seconds=-5, token_type="access")
    with pytest.raises(JWTError):
        decode_token(token, expected_type="access")
    # verify_exp=False allows decoding an expired token
    claims = decode_token(token, expected_type="access", verify_exp=False)
    assert claims["sub"] == "usr_1"


def test_tampered_signature_rejected():
    token = create_access_token("usr_1")
    header, payload, _sig = token.split(".")
    forged = f"{header}.{payload}.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    with pytest.raises(JWTError):
        decode_token(forged)


def test_malformed_token_rejected():
    with pytest.raises(JWTError):
        decode_token("not-a-token")
