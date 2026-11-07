"""Centralized logging module for API calls and endpoint interactions.

Logs all incoming and outgoing API requests into rotating log files in the ``logs/`` directory.
"""
from __future__ import annotations

from datetime import datetime
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import time
import traceback
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Root directory of the project
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

API_LOG_FILE = LOGS_DIR / "api.log"

# Setup Dedicated API Logger
api_logger = logging.getLogger("personal_tool.api")
api_logger.setLevel(logging.INFO)
api_logger.propagate = False

# Avoid duplicate handlers on hot reload
if not api_logger.handlers:
    # Rotating handler: max 10MB per file, keeping up to 5 backups
    file_handler = RotatingFileHandler(
        filename=str(API_LOG_FILE),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    api_logger.addHandler(file_handler)

    # Console stream for debugging
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)
    api_logger.addHandler(console_handler)


def _safe_serialize(obj: Any, max_len: int = 1500) -> str:
    """Format and safely truncate payload or response for human-readable logging."""
    if obj is None:
        return "None"
    try:
        if isinstance(obj, (dict, list)):
            text = json.dumps(obj, ensure_ascii=False, indent=2)
        else:
            text = str(obj)
    except Exception:
        text = str(obj)

    if len(text) > max_len:
        return text[:max_len] + f"\n... [truncated, total {len(text)} chars]"
    return text


def log_outgoing_api(
    service: str,
    method: str,
    url: str,
    payload: Any = None,
    status_code: int | None = None,
    duration_ms: float | None = None,
    response_data: Any = None,
    error: Exception | str | None = None,
) -> None:
    """Log outgoing HTTP API calls (e.g., to local Ollama or external services)."""
    sep = "=" * 70
    status_str = f"{status_code}" if status_code is not None else ("FAILED" if error else "UNKNOWN")
    dur_str = f"{duration_ms:.1f}ms" if duration_ms is not None else "N/A"

    msg_lines = [
        "",
        sep,
        f"OUTGOING API CALL -> [{service.upper()}]",
        f"Request : {method.upper()} {url}",
        f"Status  : {status_str} | Duration: {dur_str}",
    ]

    if payload is not None:
        msg_lines.append(f"Payload :\n{_safe_serialize(payload)}")

    if response_data is not None:
        msg_lines.append(f"Response:\n{_safe_serialize(response_data)}")

    if error is not None:
        msg_lines.append(f"Error   : {error}")
        if isinstance(error, Exception):
            tb = traceback.format_exc()
            if tb and tb.strip() != "NoneType: None":
                msg_lines.append(f"Traceback:\n{tb}")

    msg_lines.append(sep)
    log_text = "\n".join(msg_lines)

    if error or (status_code is not None and status_code >= 400):
        api_logger.error(log_text)
    else:
        api_logger.info(log_text)


def log_incoming_request(
    method: str,
    path: str,
    client_ip: str,
    status_code: int,
    duration_ms: float,
    details: str = "",
    error: Exception | str | None = None,
) -> None:
    """Log incoming HTTP request from browser/client to an endpoint."""
    line = f"[INCOMING] {method.upper()} {path} | Client: {client_ip} | Status: {status_code} | Duration: {duration_ms:.1f}ms"
    if details:
        line += f" | {details}"

    if error:
        line += f" | Error: {error}"
        api_logger.error(line)
    elif status_code >= 400:
        api_logger.warning(line)
    else:
        api_logger.info(line)


class ApiLoggingMiddleware(BaseHTTPMiddleware):
    """FastAPI/Starlette middleware to automatically log all API & tool requests."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Ignore static assets to keep logs clean and focused on APIs and actions
        if path.startswith("/static/") or path in ("/favicon.png", "/favicon.ico"):
            return await call_next(request)

        # Log calls to /api/ and /tools/
        is_api_or_tool = path.startswith("/api/") or path.startswith("/tools/")
        start_time = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            if is_api_or_tool:
                log_incoming_request(
                    method=request.method,
                    path=path,
                    client_ip=client_ip,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                )
            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_incoming_request(
                method=request.method,
                path=path,
                client_ip=client_ip,
                status_code=500,
                duration_ms=duration_ms,
                error=exc,
            )
            api_logger.error(f"[EXCEPTION] {request.method} {path} failed:\n{traceback.format_exc()}")
            raise
