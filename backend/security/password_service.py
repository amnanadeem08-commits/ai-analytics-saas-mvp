from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass

from backend.security.security_config import get_security_config

# Stored hash format: pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
_ALGO_TAG = "pbkdf2_sha256"


@dataclass
class PasswordPolicyResult:
    valid: bool
    issues: list[str]

    def as_dict(self) -> dict[str, object]:
        return {"valid": self.valid, "issues": list(self.issues)}


def hash_password(password: str, *, iterations: int | None = None) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256 and a random salt."""
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string")
    config = get_security_config()
    iters = int(iterations or config.pbkdf2_iterations)
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters)
    return f"{_ALGO_TAG}${iters}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Constant-time verification of a password against a stored hash."""
    if not password or not stored_hash:
        return False
    try:
        algo, iters_raw, salt_hex, hash_hex = stored_hash.split("$")
    except ValueError:
        return False
    if algo != _ALGO_TAG:
        return False
    try:
        iters = int(iters_raw)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, TypeError):
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters)
    return hmac.compare_digest(candidate, expected)


def needs_rehash(stored_hash: str) -> bool:
    """Return True when the stored hash uses fewer iterations than configured."""
    try:
        _, iters_raw, _, _ = stored_hash.split("$")
        return int(iters_raw) < get_security_config().pbkdf2_iterations
    except (ValueError, TypeError):
        return True


def validate_password_policy(password: str) -> PasswordPolicyResult:
    """Validate a password against the configured policy."""
    config = get_security_config()
    issues: list[str] = []
    if not isinstance(password, str):
        return PasswordPolicyResult(False, ["Password must be a string"])
    if len(password) < config.password_min_length:
        issues.append(f"Password must be at least {config.password_min_length} characters")
    if config.password_require_upper and not any(c.isupper() for c in password):
        issues.append("Password must contain an uppercase letter")
    if config.password_require_lower and not any(c.islower() for c in password):
        issues.append("Password must contain a lowercase letter")
    if config.password_require_digit and not any(c.isdigit() for c in password):
        issues.append("Password must contain a digit")
    if config.password_require_symbol and password.isalnum():
        issues.append("Password must contain a symbol")
    return PasswordPolicyResult(not issues, issues)


def generate_token(nbytes: int = 32) -> str:
    """Generate a cryptographically secure URL-safe token."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """One-way hash for opaque tokens stored at rest (refresh/reset/verify)."""
    secret = get_security_config().jwt_secret.encode("utf-8")
    return hmac.new(secret, token.encode("utf-8"), hashlib.sha256).hexdigest()
