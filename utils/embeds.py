from __future__ import annotations

from datetime import datetime
from typing import Any

import discord


def color_from_settings(settings: dict[str, Any]) -> discord.Color:
    raw = str(settings.get("embed_color", "#8B5CF6")).lstrip("#")
    return discord.Color(int(raw, 16))


def money(value: int, settings: dict[str, Any]) -> str:
    currency = settings.get("currency", "Rp")
    return f"{currency} {value:,.0f}".replace(",", ".")


def line(label: str, value: Any) -> str:
    return f"• **{label}:** {value}"


def section(*items: tuple[str, Any]) -> str:
    return "\n".join(line(label, value) for label, value in items)


def stock_text(stock: int) -> str:
    return "Unlimited" if stock == -1 else str(stock)


def compact_datetime(value: str) -> str:
    if not value:
        return "-"
    cleaned = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return value.split(".")[0].replace("T", " ")
    return parsed.strftime("%d %b %Y, %H:%M")


def status_badge(status: str) -> str:
    normalized = status.strip().lower()
    if normalized == "ready":
        return "Ready"
    if normalized in {"kosong", "empty"}:
        return "Kosong"
    if normalized == "maintenance":
        return "Maintenance"
    if normalized in {"out of stock", "sold out"}:
        return "Kosong"
    return status


def product_status(product: dict[str, Any]) -> str:
    stock = int(product.get("stock", 0))
    if stock == 0:
        return "Kosong"
    return status_badge(str(product.get("status", "Ready")))


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
    include_assets: bool = False,
) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color_from_settings(settings),
    )
    if settings.get("footer"):
        embed.set_footer(text=settings["footer"])
    return embed


def category_embed(
    settings: dict[str, Any],
    name: str,
    description: str,
    products: list[dict[str, Any]],
) -> discord.Embed:
    embed = base_embed(settings, name, None, include_assets=False)
    for product in products:
        embed.add_field(
            name=display_product_name(product),
            value=section(
                ("Harga", money(int(product["price"]), settings)),
                ("Akses", product["type"]),
                ("Status", product_status(product)),
                ("Stok", stock_text(int(product["stock"]))),
            ),
            inline=False,
        )
    return embed


def product_embed(settings: dict[str, Any], product: dict[str, Any]) -> discord.Embed:
    embed = base_embed(
        settings,
        display_product_name(product),
        None,
    )
    embed.add_field(
        name="Product Data:",
        value=section(
            ("Plan", product["duration"]),
            ("Akses", product["type"]),
            ("Harga", money(int(product["price"]), settings)),
            ("Status", product_status(product)),
            ("Stok", stock_text(int(product["stock"]))),
        ),
        inline=False,
    )
    description = str(product.get("description", "")).strip()
    if description:
        embed.add_field(name="Description:", value=description[:1024], inline=False)
    return embed


def invoice_embed(
    settings: dict[str, Any],
    order: dict[str, Any],
    product: dict[str, Any],
) -> discord.Embed:
    embed = base_embed(settings, f"Invoice {order['invoice']}")
    embed.add_field(
        name="Order Data:",
        value=section(
            ("Product", display_product_name(product)),
            ("Plan", product["duration"]),
            ("Akses", product["type"]),
            ("Quantity", order["quantity"]),
            ("Harga", money(int(product["price"]), settings)),
            ("Total", money(int(order["total"]), settings)),
            ("Status", order["status"]),
        ),
        inline=False,
    )
    return embed
