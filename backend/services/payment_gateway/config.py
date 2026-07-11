from __future__ import annotations

"""Payment gateway configuration (Post-1.0 billing gateway)."""

import os
from dataclasses import dataclass, field


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class PaymentGatewayConfig:
    """Env-driven payment gateway settings. Secrets never hardcoded."""

    provider: str = field(
        default_factory=lambda: os.getenv("BILLING_GATEWAY", "internal").strip().lower() or "internal"
    )
    stripe_secret_key: str = field(default_factory=lambda: os.getenv("STRIPE_SECRET_KEY", "").strip())
    stripe_webhook_secret: str = field(default_factory=lambda: os.getenv("STRIPE_WEBHOOK_SECRET", "").strip())
    stripe_publishable_key: str = field(default_factory=lambda: os.getenv("STRIPE_PUBLISHABLE_KEY", "").strip())
    stripe_api_base: str = field(
        default_factory=lambda: os.getenv("STRIPE_API_BASE", "https://api.stripe.com").strip().rstrip("/")
    )
    default_success_url: str = field(
        default_factory=lambda: os.getenv(
            "BILLING_CHECKOUT_SUCCESS_URL",
            "http://127.0.0.1:8501/?billing=success",
        ).strip()
    )
    default_cancel_url: str = field(
        default_factory=lambda: os.getenv(
            "BILLING_CHECKOUT_CANCEL_URL",
            "http://127.0.0.1:8501/?billing=cancel",
        ).strip()
    )
    allow_internal_in_production: bool = field(
        default_factory=lambda: _env_bool("BILLING_ALLOW_INTERNAL_GATEWAY", True)
    )


_CONFIG: PaymentGatewayConfig | None = None


def get_payment_gateway_config() -> PaymentGatewayConfig:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = PaymentGatewayConfig()
    return _CONFIG


def reset_payment_gateway_config() -> None:
    global _CONFIG
    _CONFIG = None
