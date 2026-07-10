from __future__ import annotations

import json
import logging

from backend.logging.formatters import JSONFormatter, TextFormatter
from backend.logging.logger import bind_context, clear_context, get_context, get_logger, setup_logging


def test_json_formatter_includes_context_fields():
    formatter = JSONFormatter()
    record = logging.LogRecord("x", logging.INFO, "", 0, "hello", (), None)
    record.request_id = "req_1"
    record.workflow_id = "wf_1"
    payload = json.loads(formatter.format(record))
    assert payload["request_id"] == "req_1"
    assert payload["workflow_id"] == "wf_1"


def test_bind_and_clear_context():
    bind_context(request_id="req_a", user_id="usr_1")
    assert get_context()["request_id"] == "req_a"
    clear_context()
    assert get_context() == {}


def test_context_adapter_logger():
    logger = get_logger("test.logger", job_id="job_1")
    assert isinstance(logger, logging.LoggerAdapter)


def test_setup_logging_does_not_raise():
    setup_logging(level="INFO", fmt="text")
