from __future__ import annotations

"""Security foundation package (Sprint 8.0).

Dependency-free JWT + password hashing built on the Python standard library so
tests remain deterministic and no external services are required.
"""

from backend.security.security_config import SecurityConfig, get_security_config

__all__ = ["SecurityConfig", "get_security_config"]
