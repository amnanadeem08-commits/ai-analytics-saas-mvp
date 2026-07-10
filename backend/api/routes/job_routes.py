from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field

from backend.api.auth_dependencies import get_current_user_dependency
from backend.api.error_handlers import map_service_exception, raise_api_error
from backend.models.job_models import JobPriority, JobType
from backend.models.user_models import User
from backend.performance.pagination import paginate
from backend.services import job_service
from backend.services.job_service import JobError

router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs"])


class JobSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: str = "normal"
    max_retries: int | None = None
    inline: bool = False


def _handle(exc: Exception):
    if isinstance(exc, JobError):
        raise_api_error(exc.status_code, exc.message)
    raise map_service_exception(exc) from exc


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Submit a job",
    description=(
        "Submits a background job (workflow_execution, analysis, evaluation, "
        "knowledge_ingestion, or generic). Set `inline=true` to run synchronously."
    ),
    responses={201: {"description": "Job submitted"}, 400: {"description": "Invalid job"}},
)
def submit_job(
    request: JobSubmitRequest,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    try:
        job = job_service.submit_job(
            job_type=request.job_type,
            payload=request.payload,
            priority=request.priority,
            max_retries=request.max_retries,
            submitted_by=current_user.user_id,
            inline=request.inline,
        )
        return {"success": True, "job": job.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.get(
    "/statistics",
    summary="Job statistics",
    description="Aggregate counts by status/type plus queue and dead-letter depth.",
)
def statistics(current_user: User = Depends(get_current_user_dependency)) -> dict[str, Any]:
    return {"success": True, "statistics": job_service.job_statistics()}


@router.get(
    "",
    summary="List jobs",
    description="Lists jobs with optional status/type filters.",
)
def list_jobs(
    status_filter: str | None = Query(default=None, alias="status"),
    job_type: str | None = Query(default=None),
    mine: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    jobs = job_service.list_jobs(
        status=status_filter,
        job_type=job_type,
        submitted_by=current_user.user_id if mine else None,
    )
    page_result = paginate(jobs, page=page, page_size=page_size)
    return {
        "success": True,
        "count": page_result.total,
        "page": page_result.page,
        "page_size": page_result.page_size,
        "jobs": [j.model_dump() for j in page_result.items],
    }


@router.get(
    "/{job_id}",
    summary="Get a job",
    description="Returns a job record including status, progress, and result.",
    responses={200: {"description": "Job found"}, 404: {"description": "Not found"}},
)
def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    job = job_service.get_job(job_id)
    if job is None:
        raise_api_error(404, f"Job not found: {job_id}")
    return {"success": True, "job": job.model_dump()}


@router.delete(
    "/{job_id}",
    summary="Cancel a job",
    description="Cancels a pending/queued/running job.",
    responses={200: {"description": "Cancelled"}, 404: {"description": "Not found"}, 409: {"description": "Already terminal"}},
)
def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    try:
        job = job_service.cancel_job(job_id)
        return {"success": True, "job": job.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.post(
    "/{job_id}/retry",
    summary="Retry a job",
    description="Re-queues a failed/cancelled/dead-letter job.",
    responses={200: {"description": "Retried"}, 404: {"description": "Not found"}, 409: {"description": "Not retryable"}},
)
def retry_job(
    job_id: str,
    inline: bool = Query(default=False),
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    try:
        job = job_service.retry_job(job_id, inline=inline)
        return {"success": True, "job": job.model_dump()}
    except Exception as exc:
        _handle(exc)
