from __future__ import annotations

"""HTTP API clients for the Sprint 7.9 Streamlit workspace.

All clients talk to FastAPI over HTTP. They must never import backend services.
"""

from frontend.api.base import ApiClient, ApiError, friendly_api_error
from frontend.api.admin_client import AdminClient
from frontend.api.analyst_client import AnalystClient
from frontend.api.apikey_client import ApiKeyClient
from frontend.api.billing_client import BillingClient
from frontend.api.auth_client import AuthClient
from frontend.api.evaluation_client import EvaluationClient
from frontend.api.job_client import JobClient
from frontend.api.monitoring_client import MonitoringClient
from frontend.api.storage_client import StorageClient
from frontend.api.knowledge_client import KnowledgeClient
from frontend.api.organization_client import OrganizationClient
from frontend.api.rbac_client import RBACClient
from frontend.api.system_client import SystemClient
from frontend.api.workflow_client import WorkflowClient
from frontend.api.workspace_client import WorkspaceClient

__all__ = [
    "ApiClient",
    "ApiError",
    "friendly_api_error",
    "AnalystClient",
    "AuthClient",
    "WorkflowClient",
    "EvaluationClient",
    "KnowledgeClient",
    "SystemClient",
    "OrganizationClient",
    "WorkspaceClient",
    "RBACClient",
    "JobClient",
    "StorageClient",
    "MonitoringClient",
    "BillingClient",
    "ApiKeyClient",
    "AdminClient",
]
