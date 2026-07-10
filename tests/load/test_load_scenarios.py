from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi.testclient import TestClient

from backend.main import app
from backend.security.rate_limiter import reset_rate_limiter
from backend.services.auth_service import reset_auth_store
from backend.services.job_service import reset_jobs

client = TestClient(app)
STRONG = "Str0ngPass!234567890"


def setup_function():
    reset_auth_store()
    reset_rate_limiter()
    reset_jobs()


def _register_and_token(email: str) -> str:
    client.post("/api/v1/auth/register", json={"email": email, "password": STRONG})
    return client.post("/api/v1/auth/login", json={"email": email, "password": STRONG}).json()["access_token"]


def test_concurrent_health_checks():
    def hit():
        return client.get("/health").status_code

    with ThreadPoolExecutor(max_workers=20) as pool:
        codes = list(pool.map(lambda _: hit(), range(40)))
    assert all(c == 200 for c in codes)


def test_concurrent_auth_registrations():
    def register(i: int):
        email = f"load{i}@example.com"
        r = client.post("/api/v1/auth/register", json={"email": email, "password": STRONG})
        return r.status_code in (201, 409)

    with ThreadPoolExecutor(max_workers=10) as pool:
        ok = list(pool.map(register, range(25)))
    assert all(ok)


def test_concurrent_job_submissions():
    token = _register_and_token("jobs@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    def submit(_):
        r = client.post(
            "/api/v1/jobs",
            json={"job_type": "generic", "payload": {"n": 1}, "inline": True},
            headers=headers,
        )
        return r.status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(submit, range(16)))
    assert all(c == 201 for c in codes)


def test_concurrent_storage_list():
    token = _register_and_token("storage@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    def list_files(_):
        return client.get("/api/v1/storage/files?page=1&page_size=10", headers=headers).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = [f.result() for f in as_completed(pool.submit(list_files, i) for i in range(12))]
    assert all(c == 200 for c in codes)


def test_api_throughput_smoke():
    start_codes = []
    for _ in range(50):
        start_codes.append(client.get("/api/v1/live").status_code)
    assert all(c == 200 for c in start_codes)
