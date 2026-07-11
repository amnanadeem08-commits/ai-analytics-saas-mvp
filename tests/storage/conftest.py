"""Storage test defaults: in-memory metadata unless marked durable."""

import pytest

from backend.storage.config import reset_storage_config
from backend.storage.factory import reset_storage_backends

pytestmark = pytest.mark.filterwarnings("ignore::pytest.PytestUnknownMarkWarning")


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "durable_storage: exercise file/SQL storage metadata backends (KI-009)",
    )


@pytest.fixture(autouse=True)
def _storage_metadata_memory_default(request, monkeypatch):
    if "durable_storage" in request.keywords:
        yield
        return
    monkeypatch.setenv("STORAGE_METADATA_BACKEND", "memory")
    reset_storage_config()
    reset_storage_backends()
    yield
    reset_storage_backends()
