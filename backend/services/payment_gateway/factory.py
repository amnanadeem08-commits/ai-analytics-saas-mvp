from __future__ import annotations

from backend.services.payment_gateway.config import (
    get_payment_gateway_config,
    reset_payment_gateway_config,
)
from backend.services.payment_gateway.interfaces import PaymentGateway
from backend.services.payment_gateway.internal_gateway import InternalPaymentGateway
from backend.services.payment_gateway.stripe_gateway import StripePaymentGateway

_GATEWAY: PaymentGateway | None = None


class PaymentGatewayConfigError(Exception):
    def __init__(self, message: str, *, status_code: int = 503):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def get_payment_gateway() -> PaymentGateway:
    global _GATEWAY
    if _GATEWAY is not None:
        return _GATEWAY

    config = get_payment_gateway_config()
    provider = (config.provider or "internal").strip().lower()

    if provider in {"internal", "local", "dev", "test"}:
        _GATEWAY = InternalPaymentGateway()
        return _GATEWAY

    if provider == "stripe":
        if not config.stripe_secret_key:
            raise PaymentGatewayConfigError(
                "BILLING_GATEWAY=stripe requires STRIPE_SECRET_KEY",
                status_code=503,
            )
        _GATEWAY = StripePaymentGateway(config)
        return _GATEWAY

    raise PaymentGatewayConfigError(
        f"Unsupported BILLING_GATEWAY provider: {provider}",
        status_code=503,
    )


def reset_payment_gateway() -> None:
    global _GATEWAY
    _GATEWAY = None
    reset_payment_gateway_config()


def gateway_status() -> dict:
    config = get_payment_gateway_config()
    try:
        gateway = get_payment_gateway()
        return {
            "configured_provider": config.provider,
            "active_provider": gateway.name,
            "is_live": gateway.is_live(),
            "stripe_publishable_key_present": bool(config.stripe_publishable_key),
            "stripe_secret_configured": bool(config.stripe_secret_key),
            "stripe_webhook_secret_configured": bool(config.stripe_webhook_secret),
            "ready": True,
        }
    except PaymentGatewayConfigError as exc:
        return {
            "configured_provider": config.provider,
            "active_provider": None,
            "is_live": False,
            "stripe_publishable_key_present": bool(config.stripe_publishable_key),
            "stripe_secret_configured": bool(config.stripe_secret_key),
            "stripe_webhook_secret_configured": bool(config.stripe_webhook_secret),
            "ready": False,
            "error": exc.message,
        }
