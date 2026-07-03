from __future__ import annotations

from dataclasses import dataclass, field

from discord.ext import commands

from utils.supplier import SupplierConfigError, TelegramSupplierStockClient


@dataclass(slots=True)
class SupplierSyncResult:
    updated: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    error: str | None = None


async def refresh_supplier_products(
    bot: commands.Bot,
    *,
    add_new_products: bool = True,
    save: bool = True,
) -> SupplierSyncResult:
    result = SupplierSyncResult()
    client = TelegramSupplierStockClient(bot.supplier_config, bot.base_dir)
    try:
        snapshot = await client.fetch_snapshot()
    except SupplierConfigError as exc:
        result.error = str(exc)
        return result

    products = bot.products_config.setdefault("products", [])
    product_by_name = {str(product["name"]).casefold(): product for product in products}

    map_items = bot.supplier_config.setdefault("product_map", [])
    mapped_supplier_names = {str(item.get("supplier_name", "")).casefold() for item in map_items}
    apply_changes = save

    supplier_items: dict[str, object] = {item.local_name.casefold(): item for item in snapshot.mapped}
    for item in snapshot.catalog:
        supplier_items.setdefault(item.local_name.casefold(), item)

    for item in supplier_items.values():
        product = product_by_name.get(item.local_name.casefold())
        if product is None:
            continue

        old_stock = int(product.get("stock", 0))
        old_status = str(product.get("status", ""))
        new_status = "Kosong" if item.stock == 0 else "Ready"
        if apply_changes:
            product["stock"] = item.stock
            if old_status.casefold() != "need price":
                product["status"] = new_status
        result.updated.append(f"{item.local_name}: {old_stock} -> {item.stock}")

    if add_new_products:
        for item in snapshot.catalog:
            if item.supplier_name.casefold() in mapped_supplier_names:
                continue
            if item.local_name.casefold() in product_by_name:
                continue

            product = _new_product_from_supplier(item.local_name, item.stock)
            if apply_changes:
                products.append(product)
                product_by_name[product["name"].casefold()] = product
                map_items.append({"local_name": item.local_name, "supplier_name": item.supplier_name})
                mapped_supplier_names.add(item.supplier_name.casefold())
            result.added.append(item.local_name)

    if save and (result.updated or result.added):
        await bot.save_products_config()
        if hasattr(bot, "save_supplier_config") and result.added:
            await bot.save_supplier_config()

    return result


def _new_product_from_supplier(name: str, stock: int) -> dict:
    upper_name = name.upper()
    category = "editing" if any(word in upper_name for word in ("ALIGHT", "CANVA", "PICSART", "CAPCUT")) else "streaming"
    product_type = "Private" if any(word in upper_name for word in ("PRIVATE", "PRIV")) else "Shared"
    duration = "1 Tahun" if "TAHUN" in upper_name else "1 Bulan" if ("BULAN" in upper_name or " 1B" in upper_name) else "-"
    return {
        "name": name,
        "duration": duration,
        "type": product_type,
        "price": 0,
        "stock": stock,
        "status": "Need Price",
        "description": "Produk baru dari supplier. Set harga sebelum dijual.",
        "category": category,
    }
