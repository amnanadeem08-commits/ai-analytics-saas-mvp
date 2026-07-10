from __future__ import annotations

from backend.security.password_service import (
    hash_password,
    needs_rehash,
    validate_password_policy,
    verify_password,
)
from backend.security.security_config import reset_security_config


def setup_function():
    reset_security_config()


def test_hash_and_verify_password():
    hashed = hash_password("Str0ngPass")
    assert hashed.startswith("pbkdf2_sha256$")
    assert verify_password("Str0ngPass", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_hash_is_salted_and_unique():
    h1 = hash_password("Str0ngPass")
    h2 = hash_password("Str0ngPass")
    assert h1 != h2
    assert verify_password("Str0ngPass", h1)
    assert verify_password("Str0ngPass", h2)


def test_verify_rejects_malformed_hash():
    assert verify_password("x", "not-a-valid-hash") is False
    assert verify_password("x", "") is False


def test_password_policy_enforced():
    assert validate_password_policy("Str0ngPass").valid is True
    weak = validate_password_policy("short")
    assert weak.valid is False
    assert weak.issues

    no_digit = validate_password_policy("NoDigitsHere")
    assert no_digit.valid is False


def test_needs_rehash_for_lower_iterations():
    weak_hash = hash_password("Str0ngPass", iterations=1000)
    assert needs_rehash(weak_hash) is True
