from __future__ import annotations

import asyncio
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "supplier.json"


async def main() -> None:
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
    except ImportError as exc:
        raise RuntimeError("Install dependency dulu: pip install -r requirements.txt") from exc

    if not CONFIG_PATH.exists():
        raise RuntimeError("Buat dan login config/supplier.json dulu.")

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = json.load(file)

    api_id = int(config.get("api_id", 0))
    api_hash = str(config.get("api_hash", "")).strip()
    session_name = str(config.get("session_name", "meowtens_supplier")).strip()
    if not api_id or not api_hash:
        raise RuntimeError("Isi api_id dan api_hash di config/supplier.json.")

    async with TelegramClient(str(BASE_DIR / session_name), api_id, api_hash) as client:
        if not await client.is_user_authorized():
            raise RuntimeError("Session belum login. Jalankan python tools/supplier_login.py dulu.")
        string_session = StringSession.save(client.session)

    print(string_session)


if __name__ == "__main__":
    asyncio.run(main())
