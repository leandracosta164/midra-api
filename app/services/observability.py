"""Secret-safe request observability for the MIDRA API."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import re
import threading
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse

_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
_START_MONOTONIC = time.monotonic()
_lock = threading.Lock()
_state = {"total_requests": 0, "active_requests": 0, "responses_4xx": 0, "responses_5xx": 0, "latest_5xx_at": None}


class JsonLogFormatter(logging.Formatter):
    """Compact JSON formatter containing only explicitly selected fields."""
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        for key in ("request_id", "method", "path", "status_code", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def configure_structured_logging(settings: object) -> None:
    level_name = str(getattr(settings, "MIDRA_LOG_LEVEL", "INFO") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logger = logging.getLogger("midra.requests")
    logger.setLevel(level)
    logger.propagate = False
    if not any(getattr(handler, "_midra_json", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonLogFormatter())
        handler._midra_json = True  # type: ignore[attr-defined]
        logger.addHandler(handler)


def _request_id(request: Request, header_name: str) -> str:
    supplied = str(request.headers.get(header_name, "") or "").strip()
    if supplied and _REQUEST_ID.fullmatch(supplied):
        return supplied
    return uuid.uuid4().hex


def operational_snapshot() -> dict[str, object]:
    with _lock:
        snapshot = dict(_state)
    snapshot["uptime_seconds"] = max(0, int(time.monotonic() - _START_MONOTONIC))
    return snapshot


async def observe_request(request: Request, call_next, settings: object):
    """Add request correlation, request-size protection, and secret-safe request logs."""
    header_name = str(getattr(settings, "MIDRA_REQUEST_ID_HEADER", "X-Request-ID") or "X-Request-ID")
    request_id = _request_id(request, header_name)
    request.state.request_id = request_id
    started = time.monotonic()
    logger = logging.getLogger("midra.requests")

    with _lock:
        _state["total_requests"] += 1
        _state["active_requests"] += 1

    status_code = 500
    try:
        # Engineering document uploads are base64 JSON, so reject implausibly large bodies
        # before Pydantic/base64 decoding allocates them in memory. No request body is logged.
        path = request.url.path
        if request.method == "POST" and "/engineering/jobs/" in path and "/documents" in path:
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    maximum = int(getattr(settings, "MIDRA_ENGINEERING_MAX_REQUEST_MB", 40)) * 1024 * 1024
                    if int(content_length) > maximum:
                        status_code = 413
                        response = JSONResponse(status_code=413, content={"detail": "request body exceeds Engineering upload limit"})
                        response.headers[header_name] = request_id
                        return response
                except ValueError:
                    pass

        response = await call_next(request)
        status_code = int(response.status_code)
        response.headers[header_name] = request_id
        return response
    except Exception:
        logger.exception(
            "request_exception",
            extra={"request_id": request_id, "method": request.method, "path": request.url.path},
        )
        raise
    finally:
        duration_ms = round((time.monotonic() - started) * 1000, 2)
        now = datetime.now(timezone.utc).isoformat()
        with _lock:
            _state["active_requests"] = max(0, int(_state["active_requests"]) - 1)
            if 400 <= status_code < 500:
                _state["responses_4xx"] += 1
            elif status_code >= 500:
                _state["responses_5xx"] += 1
                _state["latest_5xx_at"] = now
        logger.info(
            "request_complete",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )
