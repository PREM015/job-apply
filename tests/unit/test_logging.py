from __future__ import annotations

import json
import logging
from pathlib import Path

from job_agent.logging_setup import JsonFormatter, RedactionFilter, redact, setup_logging


def test_redact_email_phone_token_and_path():
    text = "mail a@b.com phone +91 98765 43210 token=abc123 path D:\\secret\\file.txt"
    cleaned = redact(text)
    assert "a@b.com" not in cleaned
    assert "98765" not in cleaned
    assert "abc123" not in cleaned
    assert "D:\\secret" not in cleaned


def test_redact_nested_values():
    value = {"password": "hunter2", "items": [{"token": "x"}]}
    cleaned = redact(value)
    assert cleaned["password"] == "<redacted>"
    assert cleaned["items"][0]["token"] == "<redacted>"


def test_setup_logging_writes_json(tmp_path: Path):
    logger = setup_logging(tmp_path)
    record = logger.makeRecord("job_agent", logging.INFO, __file__, 1, "hello a@b.com", (), None)
    formatted = JsonFormatter().format(record)
    payload = json.loads(formatted)
    assert payload["level"] == "INFO"
    assert "<email>" in payload["message"]
    logger.info("write test")
    assert (tmp_path / "job_agent.log").exists()


def test_redaction_filter_mutates_record():
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "token=abc", (), None)
    assert RedactionFilter().filter(record) is True
    assert "abc" not in record.msg
