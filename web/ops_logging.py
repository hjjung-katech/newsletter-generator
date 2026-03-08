"""Small helpers for stable, field-oriented operational logging."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Any


def _serialize_log_value(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (dict, list, tuple, set)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def build_log_message(event: str, **fields: Any) -> str:
    parts = [event]
    for key in sorted(fields):
        value = fields[key]
        if value is None:
            continue
        parts.append(f"{key}={_serialize_log_value(value)}")
    return " ".join(parts)


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    logger.log(level, build_log_message(event, **fields))


def log_debug(logger: logging.Logger, event: str, **fields: Any) -> None:
    log_event(logger, logging.DEBUG, event, **fields)


def log_info(logger: logging.Logger, event: str, **fields: Any) -> None:
    log_event(logger, logging.INFO, event, **fields)


def log_warning(logger: logging.Logger, event: str, **fields: Any) -> None:
    log_event(logger, logging.WARNING, event, **fields)


def log_error(logger: logging.Logger, event: str, **fields: Any) -> None:
    log_event(logger, logging.ERROR, event, **fields)


def log_exception(
    logger: logging.Logger, event: str, error: Exception, **fields: Any
) -> None:
    log_error(
        logger,
        event,
        error=str(error),
        error_type=type(error).__name__,
        **fields,
    )
