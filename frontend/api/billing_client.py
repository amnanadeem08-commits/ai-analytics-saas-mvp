from __future__ import annotations

from typing import Any

from frontend.api.base import ApiClient


class BillingClient:
    def __init__(self, client: ApiClient):
        self._client = client

    @staticmethod
    def _auth(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"} if token else {}

    def list_plans(self, token: str) -> dict[str, Any]:
        return self._client.get(self._client.v1("/billing/plans"), headers=self._auth(token))

    def get_subscription(self, token: str, organization_id: str) -> dict[str, Any]:
        return self._client.get(self._client.v1(f"/billing/subscriptions/{organization_id}"), headers=self._auth(token))

    def assign_plan(self, token: str, organization_id: str, *, plan_id: str, start_trial: bool = False) -> dict[str, Any]:
        return self._client.post(
            self._client.v1(f"/billing/subscriptions/{organization_id}"),
            json={"plan_id": plan_id, "start_trial": start_trial},
            headers=self._auth(token),
        )

    def upgrade(self, token: str, organization_id: str, *, plan_id: str) -> dict[str, Any]:
        return self._client.post(
            self._client.v1(f"/billing/subscriptions/{organization_id}/upgrade"),
            json={"plan_id": plan_id, "start_trial": False},
            headers=self._auth(token),
        )

    def usage(self, token: str, organization_id: str) -> dict[str, Any]:
        return self._client.get(self._client.v1(f"/billing/usage/{organization_id}"), headers=self._auth(token))

    def limits(self, token: str, organization_id: str) -> dict[str, Any]:
        return self._client.get(self._client.v1(f"/billing/limits/{organization_id}"), headers=self._auth(token))

    def estimate(self, token: str, organization_id: str) -> dict[str, Any]:
        return self._client.get(self._client.v1(f"/billing/estimate/{organization_id}"), headers=self._auth(token))

    def generate_invoice(self, token: str, organization_id: str) -> dict[str, Any]:
        return self._client.post(self._client.v1(f"/billing/invoices/{organization_id}"), headers=self._auth(token))

    def list_invoices(self, token: str, organization_id: str) -> dict[str, Any]:
        return self._client.get(self._client.v1(f"/billing/invoices/{organization_id}"), headers=self._auth(token))

    def gateway_status(self, token: str) -> dict[str, Any]:
        return self._client.get(self._client.v1("/billing/gateway/status"), headers=self._auth(token))

    def start_checkout(
        self,
        token: str,
        invoice_id: str,
        *,
        success_url: str | None = None,
        cancel_url: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if success_url:
            payload["success_url"] = success_url
        if cancel_url:
            payload["cancel_url"] = cancel_url
        return self._client.post(
            self._client.v1(f"/billing/payments/{invoice_id}/checkout"),
            json=payload,
            headers=self._auth(token),
        )
