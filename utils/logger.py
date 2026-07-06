from __future__ import annotations

import logging
import os
from pathlib import Path
import sys


NOISY_LOGGERS = (
    "telethon",
    "telethon.client",
    "telethon.crypto",
    "telethon.network",
    "telethon.network.mtprotosender",
    "aiohttp.access",
)


def _level_from_env(name: str, default: str) -> int:
    value = os.getenv(name, default).strip().upper()
    return getattr(logging, value, logging.INFO)


def setup_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_level = _level_from_env("LOG_LEVEL", "INFO")
    noisy_level = _level_from_env("TELETHON_LOG_LEVEL", "WARNING")
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "vercettia-store.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )

    for logger_name in NOISY_LOGGERS:
        logging.getLogger(logger_name).setLevel(noisy_level)
