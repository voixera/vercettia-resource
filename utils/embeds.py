from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import discord


def color_from_settings(settings: dict[str, Any]) -> discord.Color:
    raw = str(settings.get("embed_color", "#8B5CF6")).lstrip("#")
    return discord.Color(int(raw, 16))


def money(value: int, settings: dict[str, Any]) -> str:
    currency = settings.get("currency", "Rp")
    return f"{currency} {value:,.0f}".replace(",", ".")


def stock_text(stock: int) -> str:
    return "Unlimited" if stock == -1 else str(stock)


def status_badge(status: str) -> str:
    normalized = status.strip().lower()
    if normalized == "ready":
        return "Ready"
    if normalized == "maintenance":
        return "Maintenance"
    if normalized in {"out of stock", "sold out"}:
        return "Sold Out"
    return status


def display_product_name(product: dict[str, Any]) -> str:
    name = str(product["name"])
    duration = str(product.get("duration", "")).strip()
    if duration and duration.lower() not in name.lower():
        return f"{name} {duration}"
    return name


def base_embed(
    settings: dict[str, Any],
    title: str,
    description: str | None = None,
    include_assets: bool = True,
) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color_from_settings(settings),
        timestamp=datetime.now(UTC),
    )
    if settings.get("footer"):
        embed.set_footer(text=settings["footer"])
    if include_assets and settings.get("logo") and (Path(__file__).resolve().parent.parent / settings["logo"]).exists():
        embed.set_thumbnail(url=f"attachment://{settings['logo'].split('/')[-1]}")
    if include_assets and settings.get("banner") and (Path(__file__).resolve().parent.parent / settings["banner"]).exists():
        embed.set_image(url=f"attachment://{settings['banner'].split('/')[-1]}")
    return embed


def category_embed(
    settings: dict[str, Any],
    name: str,
    description: str,
    products: list[dict[str, Any]],
) -> discord.Embed:
    embed = base_embed(settings, name, None, include_assets=False)
    for product in products:
        detail_lines = [
            f"**Harga:** {money(int(product['price']), settings)}",
            f"{product['type']} | {status_badge(product['status'])} | Stok {stock_text(int(product['stock']))}",
        ]
        embed.add_field(
            name=display_product_name(product),
            value="\n".join(detail_lines),
            inline=False,
        )
    return embed


def product_embed(settings: dict[str, Any], product: dict[str, Any]) -> discord.Embed:
    embed = base_embed(
        settings,
        display_product_name(product),
        None,
    )
    embed.add_field(name="Plan", value=f"**{product['duration']}**", inline=True)
    embed.add_field(name="Access", value=f"**{product['type']}**", inline=True)
    embed.add_field(name="Harga", value=f"**{money(int(product['price']), settings)}**", inline=True)
    embed.add_field(name="Status", value=f"**{status_badge(product['status'])}**", inline=True)
    embed.add_field(name="Stock", value=f"**{stock_text(int(product['stock']))}**", inline=True)
    return embed


def invoice_embed(
    settings: dict[str, Any],
    order: dict[str, Any],
    product: dict[str, Any],
) -> discord.Embed:
    embed = base_embed(settings, f"Invoice {order['invoice']}")
    embed.description = (
        "Order berhasil dibuat. Selesaikan pembayaran melalui checkout resmi, "
        "lalu gunakan **Check Payment** untuk verifikasi."
    )
    embed.add_field(name="Product", value=f"**{display_product_name(product)}**", inline=False)
    embed.add_field(name="Plan", value=product["duration"], inline=True)
    embed.add_field(name="Access", value=product["type"], inline=True)
    embed.add_field(name="Quantity", value=str(order["quantity"]), inline=True)
    embed.add_field(name="Harga", value=money(int(product["price"]), settings), inline=True)
    embed.add_field(name="Grand Total", value=f"**{money(int(order['total']), settings)}**", inline=True)
    embed.add_field(name="Status", value=f"**{order['status']}**", inline=True)
    return embed
