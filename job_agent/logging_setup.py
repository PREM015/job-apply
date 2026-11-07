"""Structured JSON logging with conservative redaction."""
from __future__ import annotations

import json
import logging
import logging.handlers
import re
from pathlib import Path
from typing import Any

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
TOKEN_RE = re.compile(r"(?i)\b(?:api[_-]?key|token|secret|password|authorization)\b\s*[:=]\s*\S+")
WINDOWS_PATH_RE = re.compile(r"[A-Za-z]:\\[^\s\"']+")


def redact(value: Any) -> Any:
    if isinstance(value, str):
        value = EMAIL_RE.sub("<email>", value)
        value = PHONE_RE.sub("<phone>", value)
        value = TOKEN_RE.sub("<redacted>", value)
        value = WINDOWS_PATH_RE.sub("<path>", value)
        return value
    if isinstance(value, dict):
        return {k: ("<redacted>" if "secret" in str(k).lower() or "token" in str(k).lower() or "password" in str(k).lower() else redact(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return value


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.msg)
        record.args = tuple(redact(a) for a in record.args) if record.args else record.args
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
        }
        for key in ("run_id", "stage", "source", "company_master_id", "job_id", "event", "duration_ms", "error_type"):
            if hasattr(record, key):
                payload[key] = redact(getattr(record, key))
        if record.exc_info:
            payload["error_type"] = record.exc_info[0].__name__ if record.exc_info[0] else "Exception"
        return json.dumps(payload, ensure_ascii=True)


def setup_logging(logs_dir: str | Path = "logs") -> logging.Logger:
    directory = Path(logs_dir)
    directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("job_agent")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = logging.handlers.RotatingFileHandler(directory / "job_agent.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RedactionFilter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger
