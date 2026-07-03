from __future__ import annotations

from pathlib import Path
from typing import Any

import discord


def configured_files(settings: dict[str, Any], base_dir: Path) -> list[discord.File]:
    if not settings.get("embed_assets_enabled", False):
        return []

    files: list[discord.File] = []
    for key in ("logo", "banner"):
        raw = settings.get(key)
        if not raw:
            continue
        path = base_dir / raw
        if path.exists():
            files.append(discord.File(path, filename=path.name))
    return files
