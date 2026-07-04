from __future__ import annotations

from io import BytesIO

import discord
import qrcode


def qris_with_amount(qris_text: str, amount: int | None) -> str:
    payload = qris_text.strip()
    if amount is None or amount <= 0 or not _looks_like_qris_payload(payload):
        return payload

    payload = _without_crc(payload)
    payload = _replace_tag(payload, "01", "12")
    payload = _remove_tag(payload, "54")
    payload = _insert_before_tag(payload, "58", _field("54", str(amount)))
    return _append_crc(payload)


def make_qris_file(qris_text: str, invoice: str, amount: int | None = None) -> discord.File:
    image = qrcode.make(qris_with_amount(qris_text, amount))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    filename = f"qris-{invoice}.png"
    return discord.File(buffer, filename=filename)


def _looks_like_qris_payload(payload: str) -> bool:
    return payload.startswith("000201") and "5802ID" in payload and "6304" in payload


def _field(tag: str, value: str) -> str:
    return f"{tag}{len(value):02d}{value}"


def _without_crc(payload: str) -> str:
    crc_index = payload.rfind("6304")
    if crc_index == -1:
        return payload
    return payload[:crc_index]


def _iter_fields(payload: str):
    index = 0
    while index + 4 <= len(payload):
        tag = payload[index : index + 2]
        try:
            length = int(payload[index + 2 : index + 4])
        except ValueError:
            break
        end = index + 4 + length
        if end > len(payload):
            break
        yield tag, index, end
        index = end


def _replace_tag(payload: str, tag: str, value: str) -> str:
    replacement = _field(tag, value)
    for field_tag, start, end in _iter_fields(payload):
        if field_tag == tag:
            return payload[:start] + replacement + payload[end:]
    return replacement + payload


def _remove_tag(payload: str, tag: str) -> str:
    for field_tag, start, end in _iter_fields(payload):
        if field_tag == tag:
            return payload[:start] + payload[end:]
    return payload


def _insert_before_tag(payload: str, tag: str, field: str) -> str:
    for field_tag, start, _ in _iter_fields(payload):
        if field_tag == tag:
            return payload[:start] + field + payload[start:]
    return payload + field


def _append_crc(payload: str) -> str:
    data = f"{payload}6304"
    return f"{data}{_crc16_ccitt(data):04X}"


def _crc16_ccitt(data: str) -> int:
    crc = 0xFFFF
    for byte in data.encode("ascii"):
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc
