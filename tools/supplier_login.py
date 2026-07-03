from __future__ import annotations

import asyncio
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "supplier.json"


async def main() -> None:
    try:
        from telethon import TelegramClient
        from telethon.errors import (
            ApiIdInvalidError,
            PhoneCodeInvalidError,
            PhoneNumberInvalidError,
            SessionPasswordNeededError,
        )
    except ImportError as exc:
        raise RuntimeError("Install dependency dulu: pip install -r requirements.txt") from exc

    if not CONFIG_PATH.exists():
        raise RuntimeError("Buat config/supplier.json dari config/supplier.example.json dulu.")

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = json.load(file)

    api_id = int(config.get("api_id", 0))
    api_hash = str(config.get("api_hash", "")).strip()
    session_name = str(config.get("session_name", "meowtens_supplier")).strip()
    if not api_id or not api_hash:
        raise RuntimeError("Isi api_id dan api_hash di config/supplier.json.")

    async with TelegramClient(str(BASE_DIR / session_name), api_id, api_hash) as client:
        if not await client.is_user_authorized():
            phone = input("Masukkan nomor Telegram format internasional, contoh +6285183290095: ").strip()
            try:
                await client.send_code_request(phone)
            except PhoneNumberInvalidError as exc:
                raise RuntimeError("Nomor tidak valid. Gunakan format +62, bukan 08.") from exc
            except ApiIdInvalidError as exc:
                raise RuntimeError("api_id atau api_hash salah. Cek lagi dari my.telegram.org.") from exc

            code = input("Masukkan kode OTP Telegram: ").strip().replace(" ", "")
            try:
                await client.sign_in(phone=phone, code=code)
            except PhoneCodeInvalidError as exc:
                raise RuntimeError("Kode OTP salah atau sudah expired. Jalankan ulang script.") from exc
            except SessionPasswordNeededError:
                password = input("Masukkan password 2FA Telegram: ")
                await client.sign_in(password=password)

        me = await client.get_me()
        print(f"Telegram session siap: {getattr(me, 'username', None) or me.id}")


if __name__ == "__main__":
    asyncio.run(main())
