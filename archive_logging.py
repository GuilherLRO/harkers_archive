"""Shared logging setup for the archive runner and Telegram bot."""

from __future__ import annotations

import logging
import os
from pathlib import Path

HTTP_LOGGER_NAMES = ("httpx", "httpcore")
DEFAULT_HTTP_LOG_NAME = "helsings_round_http.log"


def http_log_path(repo_root: Path) -> Path:
    override = os.environ.get("HELSINGS_HTTP_LOG", "").strip()
    if override:
        return Path(override).expanduser()
    return repo_root / DEFAULT_HTTP_LOG_NAME


def configure_logging(repo_root: Path) -> None:
    """App logs go to stderr; Telegram HTTP traffic goes to a separate file."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        force=True,
    )

    path = http_log_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)

    http_handler = logging.FileHandler(path, encoding="utf-8")
    http_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )

    for name in HTTP_LOGGER_NAMES:
        http_logger = logging.getLogger(name)
        http_logger.handlers.clear()
        http_logger.setLevel(logging.INFO)
        http_logger.addHandler(http_handler)
        http_logger.propagate = False
