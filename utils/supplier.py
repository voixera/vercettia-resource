from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class SupplierConfigError(RuntimeError):
    pass


@dataclass(slots=True)
class SupplierStock:
    local_name: str
    supplier_name: str
    stock: int
    raw_line: str


@dataclass(slots=True)
class SupplierSnapshot:
    mapped: list[SupplierStock]
    catalog: list[SupplierStock]


class TelegramSupplierStockClient:
    def __init__(self, config: dict[str, Any], base_dir: Path) -> None:
        self.config = config
        self.base_dir = base_dir

    @property
    def enabled(self) -> bool:
        return bool(self.config.get("enabled", False))

    async def fetch_stock(self) -> list[SupplierStock]:
        snapshot = await self.fetch_snapshot()
        return snapshot.mapped

    async def fetch_snapshot(self) -> SupplierSnapshot:
        if not self.enabled:
            raise SupplierConfigError("Supplier stock sync belum aktif di config/supplier.json.")

        api_id = int(self.config.get("api_id", 0))
        api_hash = str(self.config.get("api_hash", "")).strip()
        bot_username = str(self.config.get("bot_username", "")).strip().lstrip("@")
        stock_command = str(self.config.get("stock_command", "/stock")).strip()
        product_map = list(self.config.get("product_map", []))
        if not api_id or not api_hash or not bot_username or not stock_command:
            raise SupplierConfigError("Lengkapi api_id, api_hash, bot_username, dan stock_command supplier.")

        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
        except ImportError as exc:
            raise SupplierConfigError("Install dependency dulu: pip install -r requirements.txt") from exc

        session_name = str(self.config.get("session_name", "meowtens_supplier")).strip()
        session_string = str(self.config.get("session_string", "") or os.getenv("TELEGRAM_SESSION_STRING", "")).strip()
        session = StringSession(session_string) if session_string else str(self.base_dir / session_name)
        wait_seconds = max(3, int(self.config.get("response_wait_seconds", 8)))

        async with TelegramClient(session, api_id, api_hash) as client:
            if not await client.is_user_authorized():
                raise SupplierConfigError(
                    "Session Telegram belum login. Jalankan script login supplier dulu sebelum sync stok."
                )

            entity = await client.get_entity(bot_username)
            before_id = 0
            async for message in client.iter_messages(entity, limit=1):
                before_id = int(message.id)
                break

            await client.send_message(entity, stock_command)
            await asyncio.sleep(wait_seconds)

            chunks: list[str] = []
            async for message in client.iter_messages(entity, limit=12):
                if int(message.id) <= before_id:
                    break
                if message.raw_text:
                    chunks.append(str(message.raw_text))

        if not chunks:
            raise SupplierConfigError("Bot supplier tidak mengirim balasan stok.")

        response_text = "\n".join(reversed(chunks))
        catalog = parse_supplier_catalog(response_text)
        mapped = parse_supplier_stock(response_text, product_map)
        return SupplierSnapshot(mapped=mapped, catalog=catalog)


def parse_supplier_catalog(response_text: str) -> list[SupplierStock]:
    results: list[SupplierStock] = []
    for line in response_text.splitlines():
        cleaned = line.strip()
        if not cleaned.startswith("-"):
            continue

        stock = _extract_stock(cleaned)
        if stock is None:
            continue

        name_part = cleaned.lstrip("-").strip()
        name = re.split(r"\s[:=]\s|\s:\s|:", name_part, maxsplit=1)[0].strip()
        if not name:
            continue

        results.append(
            SupplierStock(
                local_name=name,
                supplier_name=name,
                stock=stock,
                raw_line=cleaned,
            )
        )
    return results


def parse_supplier_stock(response_text: str, product_map: list[dict[str, Any]]) -> list[SupplierStock]:
    lines = [line.strip() for line in response_text.splitlines() if line.strip()]
    results: list[SupplierStock] = []
    for mapping in product_map:
        local_name = str(mapping.get("local_name", "")).strip()
        supplier_name = str(mapping.get("supplier_name", "")).strip()
        if not local_name or not supplier_name:
            continue

        matched_line = next((line for line in lines if supplier_name.casefold() in line.casefold()), "")
        if not matched_line:
            continue

        stock = _extract_stock(matched_line)
        if stock is None:
            continue

        results.append(
            SupplierStock(
                local_name=local_name,
                supplier_name=supplier_name,
                stock=stock,
                raw_line=matched_line,
            )
        )
    return results


def _extract_stock(line: str) -> int | None:
    normalized = line.casefold()
    if any(word in normalized for word in ("kosong", "habis", "sold out", "out of stock")):
        return 0
    if any(word in normalized for word in ("unlimited", "unlimit", "ready terus")):
        return -1

    patterns = (
        r"(?:stok|stock|sisa|qty|quantity)\s*[:=\-]?\s*(-?\d+)",
        r"(-?\d+)\s*(?:stok|stock|pcs|slot|akun)",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            return int(match.group(1))

    numbers = re.findall(r"-?\d+", normalized)
    if numbers:
        return int(numbers[-1])
    if "ready" in normalized:
        return 1
    return None
