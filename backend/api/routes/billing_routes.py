from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

from backend.api.auth_dependencies import current_organization, get_current_user_dependency
from backend.api.error_handlers import map_service_exception, raise_api_error
from backend.models.user_models import User
from backend.services import billing_service, subscription_service, usage_service
from backend.services.billing_service import BillingError
from backend.services.subscription_service import SubscriptionError
from backend.services.usage_service import UsageError

router = APIRouter(prefix="/api/v1/billing", tags=["Billing"])


class AssignPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str
    start_trial: bool = False


class AddCreditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount_cents: int = Field(..., ge=1)


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success_url: str | None = None
    cancel_url: str | None = None


def _handle(exc: Exception):
    if isinstance(exc, (BillingError, SubscriptionError, UsageError)):
        raise_api_error(exc.status_code, exc.message)
    raise map_service_exception(exc) from exc


def _org_id(request, organization_id: str | None) -> str:
    org = organization_id or current_organization(request)
    if not org:
        raise_api_error(400, "organization_id is required")
    return org


@router.get("/plans", summary="List subscription plans")
def list_plans(current_user: User = Depends(get_current_user_dependency)) -> dict[str, Any]:
    _ = current_user
    plans = subscription_service.list_plans()
    return {"success": True, "count": len(plans), "plans": [p.model_dump() for p in plans]}


@router.get("/plans/{plan_id}", summary="Get a subscription plan")
def get_plan(plan_id: str, current_user: User = Depends(get_current_user_dependency)) -> dict[str, Any]:
    _ = current_user
    plan = subscription_service.get_plan(plan_id)
    if plan is None:
        raise_api_error(404, f"Plan not found: {plan_id}")
    return {"success": True, "plan": plan.model_dump()}


@router.get("/subscriptions/{organization_id}", summary="Get organization subscription")
def get_subscription(
    organization_id: str,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    sub = subscription_service.get_subscription(organization_id)
    if sub is None:
        raise_api_error(404, "No subscription found")
    return {"success": True, "subscription": sub.model_dump()}


@router.post(
    "/subscriptions/{organization_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Assign subscription plan",
)
def assign_subscription(
    organization_id: str,
    request: AssignPlanRequest,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    try:
        sub = subscription_service.assign_plan(
            organization_id,
            request.plan_id,
            start_trial=request.start_trial,
        )
        return {"success": True, "subscription": sub.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.post("/subscriptions/{organization_id}/upgrade", summary="Upgrade plan")
def upgrade_subscription(
    organization_id: str,
    request: AssignPlanRequest,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    try:
        sub = subscription_service.upgrade_plan(organization_id, request.plan_id, start_trial=request.start_trial)
        return {"success": True, "subscription": sub.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.post("/subscriptions/{organization_id}/downgrade", summary="Downgrade plan")
def downgrade_subscription(
    organization_id: str,
    request: AssignPlanRequest,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    try:
        sub = subscription_service.downgrade_plan(organization_id, request.plan_id)
        return {"success": True, "subscription": sub.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.post("/subscriptions/{organization_id}/suspend", summary="Suspend subscription")
def suspend_subscription(
    organization_id: str,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    try:
        sub = subscription_service.suspend_subscription(organization_id)
        return {"success": True, "subscription": sub.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.post("/subscriptions/{organization_id}/reactivate", summary="Reactivate subscription")
def reactivate_subscription(
    organization_id: str,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    try:
        sub = subscription_service.reactivate_subscription(organization_id)
        return {"success": True, "subscription": sub.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.get("/usage/{organization_id}", summary="Usage summary")
def usage_summary(
    organization_id: str,
    workspace_id: str = Query(default=""),
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    return {"success": True, **usage_service.usage_summary(organization_id, workspace_id=workspace_id)}


@router.get("/usage/{organization_id}/records", summary="List usage records")
def usage_records(
    organization_id: str,
    metric: str | None = Query(default=None),
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    records = usage_service.list_usage(organization_id=organization_id, metric=metric)
    return {"success": True, "count": len(records), "records": [r.model_dump() for r in records]}


@router.get("/limits/{organization_id}", summary="Feature limits for organization")
def feature_limits(
    organization_id: str,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    limits = subscription_service.get_limits(organization_id)
    return {"success": True, "limits": [l.model_dump() for l in limits]}


@router.get("/estimate/{organization_id}", summary="Estimated charges")
def estimate(
    organization_id: str,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    return {"success": True, "estimate": billing_service.estimated_charges(organization_id)}


@router.post(
    "/invoices/{organization_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Generate invoice",
)
def generate_invoice(
    organization_id: str,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    try:
        invoice = billing_service.generate_invoice(organization_id)
        return {"success": True, "invoice": invoice.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.get("/invoices/{organization_id}", summary="List invoices")
def list_invoices(
    organization_id: str,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    invoices = billing_service.list_invoices(organization_id=organization_id)
    return {"success": True, "count": len(invoices), "invoices": [i.model_dump() for i in invoices]}


@router.get("/invoices/detail/{invoice_id}", summary="Get invoice")
def get_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    invoice = billing_service.get_invoice(invoice_id)
    if invoice is None:
        raise_api_error(404, f"Invoice not found: {invoice_id}")
    return {"success": True, "invoice": invoice.model_dump()}


@router.get("/credits/{organization_id}", summary="Credit balance")
def credit_balance(
    organization_id: str,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    bal = billing_service.get_credit_balance(organization_id)
    return {"success": True, "credit": bal.model_dump()}


@router.post("/credits/{organization_id}", summary="Add account credit")
def add_credit(
    organization_id: str,
    request: AddCreditRequest,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    bal = billing_service.add_credit(organization_id, request.amount_cents)
    return {"success": True, "credit": bal.model_dump()}


@router.get("/gateway/status", summary="Payment gateway status")
def payment_gateway_status(
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    return {"success": True, "gateway": billing_service.get_gateway_status()}


@router.post(
    "/payments/{invoice_id}/checkout",
    status_code=status.HTTP_201_CREATED,
    summary="Start payment checkout for an invoice",
)
def start_invoice_checkout(
    invoice_id: str,
    request: CheckoutRequest | None = None,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    body = request or CheckoutRequest()
    try:
        session = billing_service.start_checkout(
            invoice_id,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
        )
        return {
            "success": True,
            "checkout": {
                "session_id": session.session_id,
                "provider": session.provider,
                "invoice_id": session.invoice_id,
                "organization_id": session.organization_id,
                "amount_cents": session.amount_cents,
                "currency": session.currency,
                "status": session.status,
                "checkout_url": session.checkout_url,
                "provider_reference": session.provider_reference,
                "metadata": session.metadata,
            },
        }
    except Exception as exc:
        _handle(exc)


@router.post(
    "/payments/{invoice_id}/pay",
    summary="Record / settle payment attempt (gateway-aware)",
)
def pay_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    try:
        attempt = billing_service.record_payment_attempt(invoice_id)
        invoice = billing_service.get_invoice(invoice_id)
        return {
            "success": True,
            "payment": attempt.model_dump(),
            "invoice": invoice.model_dump() if invoice else None,
        }
    except Exception as exc:
        _handle(exc)


@router.post("/webhooks/{provider}", summary="Payment provider webhook", include_in_schema=True)
async def payment_webhook(provider: str, request: Request) -> dict[str, Any]:
    body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}
    # Preserve Stripe-Signature casing lookup helpers inside gateway
    if "stripe-signature" in headers:
        headers["Stripe-Signature"] = headers["stripe-signature"]
    try:
        result = billing_service.handle_payment_webhook(
            provider=provider,
            headers=headers,
            body=body,
        )
        return result
    except Exception as exc:
        _handle(exc)
