from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from backend.security.security_config import get_security_config


class JWTError(Exception):
    """Raised when a JWT cannot be decoded or fails validation."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(signing_input: bytes, secret: str, algorithm: str) -> bytes:
    if algorithm != "HS256":
        raise JWTError(f"Unsupported JWT algorithm: {algorithm}")
    return hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()


def encode_token(
    payload: dict[str, Any],
    *,
    ttl_seconds: int,
    token_type: str = "access",
    secret: str | None = None,
) -> str:
    """Encode a signed JWT with standard claims (iat/exp/iss/aud/type)."""
    config = get_security_config()
    now = int(time.time())
    claims = {
        "iat": now,
        "nbf": now,
        "exp": now + int(ttl_seconds),
        "iss": config.jwt_issuer,
        "aud": config.jwt_audience,
        "type": token_type,
        **payload,
    }
    header = {"alg": config.jwt_algorithm, "typ": "JWT"}
    segments = [
        _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")),
        _b64url_encode(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode("utf-8")),
    ]
    signing_input = ".".join(segments).encode("ascii")
    signature = _sign(signing_input, secret or config.jwt_secret, config.jwt_algorithm)
    segments.append(_b64url_encode(signature))
    return ".".join(segments)


def decode_token(
    token: str,
    *,
    expected_type: str | None = None,
    verify_exp: bool = True,
    secret: str | None = None,
) -> dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on any failure."""
    config = get_security_config()
    if not token or token.count(".") != 2:
        raise JWTError("Malformed token")
    header_b64, payload_b64, signature_b64 = token.split(".")
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    try:
        header = json.loads(_b64url_decode(header_b64))
    except Exception as exc:  # noqa: BLE001
        raise JWTError("Invalid token header") from exc

    algorithm = header.get("alg", config.jwt_algorithm)
    expected_sig = _sign(signing_input, secret or config.jwt_secret, algorithm)
    try:
        actual_sig = _b64url_decode(signature_b64)
    except Exception as exc:  # noqa: BLE001
        raise JWTError("Invalid token signature encoding") from exc
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise JWTError("Signature verification failed")

    try:
        claims = json.loads(_b64url_decode(payload_b64))
    except Exception as exc:  # noqa: BLE001
        raise JWTError("Invalid token payload") from exc

    now = int(time.time())
    if verify_exp and int(claims.get("exp", 0)) < now:
        raise JWTError("Token has expired")
    if int(claims.get("nbf", 0)) > now + 1:
        raise JWTError("Token not yet valid")
    if claims.get("iss") != config.jwt_issuer:
        raise JWTError("Invalid token issuer")
    if claims.get("aud") != config.jwt_audience:
        raise JWTError("Invalid token audience")
    if expected_type is not None and claims.get("type") != expected_type:
        raise JWTError(f"Expected {expected_type} token, got {claims.get('type')}")
    return claims


def create_access_token(subject: str, *, extra_claims: dict[str, Any] | None = None) -> str:
    config = get_security_config()
    payload = {"sub": subject, **(extra_claims or {})}
    return encode_token(payload, ttl_seconds=config.access_token_ttl_seconds, token_type="access")


def create_refresh_token(subject: str, *, session_id: str, extra_claims: dict[str, Any] | None = None) -> str:
    config = get_security_config()
    payload = {"sub": subject, "sid": session_id, **(extra_claims or {})}
    return encode_token(payload, ttl_seconds=config.refresh_token_ttl_seconds, token_type="refresh")


def token_expiry_seconds(token_type: str = "access") -> int:
    config = get_security_config()
    return (
        config.refresh_token_ttl_seconds
        if token_type == "refresh"
        else config.access_token_ttl_seconds
    )
