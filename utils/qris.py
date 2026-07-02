from __future__ import annotations

from io import BytesIO

import discord
import qrcode


def make_qris_file(qris_text: str, invoice: str) -> discord.File:
    image = qrcode.make(qris_text)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    filename = f"qris-{invoice}.png"
    return discord.File(buffer, filename=filename)
