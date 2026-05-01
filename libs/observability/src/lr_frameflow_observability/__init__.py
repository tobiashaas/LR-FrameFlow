"""Lightweight logging façade for services and workers."""

from __future__ import annotations

import logging
from typing import Any

__all__ = ["get_logger", "log_kv"]


def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    return logging.getLogger(name)


def log_kv(logger: logging.Logger, level: int, msg: str, **fields: Any) -> None:
    extra = " ".join(f"{k}={v!r}" for k, v in sorted(fields.items()))
    logger.log(level, "%s | %s", msg, extra)
