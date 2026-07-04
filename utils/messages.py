from __future__ import annotations

from typing import Any

from utils.embeds import compact_datetime, display_product_name, money, product_status, stock_text

DIVIDER = "────────────────────────────"

TEXT = {
    "id": {
        "catalog_intro": "Pilih produk dari menu di bawah. Harga yang tampil adalah harga aktif Vercettia Store.",
        "product_intro": "Detail produk, harga, status, dan stok aktif tersedia di bawah.",
        "invoice_intro": "Invoice berhasil dibuat. Selesaikan pembayaran di ticket ini. Admin akan mengirim data akun premium setelah pembayaran terkonfirmasi.",
        "payment_intro": "Metode pembayaran resmi Vercettia Store.",
        "offer_intro": "Promo aktif dan penawaran khusus akan tampil di sini.",
        "Product Data": "Data Produk",
        "Order Data": "Data Order",
        "Payment": "Pembayaran",
        "Description": "Deskripsi",
        "Stats": "Statistik",
        "Voucher Data": "Data Voucher",
        "Offer Data": "Data Promo",
        "Ticket Data": "Data Ticket",
        "Close Data": "Data Close",
        "Member Data": "Data Member",
        "Product": "Produk",
        "Price": "Harga",
        "Harga": "Harga",
        "Access": "Akses",
        "Akses": "Akses",
        "Status": "Status",
        "Stock": "Stok",
        "Stok": "Stok",
        "Quantity": "Jumlah",
        "Total": "Total",
        "Method": "Metode",
        "Delivery": "Pengiriman",
        "QRIS": "QRIS",
        "Total Bayar": "Total Bayar",
        "Expired": "Expired",
        "Holder": "Nama Rekening",
        "Destination": "Tujuan",
        "Invoice": "Invoice",
        "Plan": "Plan",
        "Customer": "Customer",
        "Customer ID": "Customer ID",
        "Item": "Item",
        "Gross Sales": "Gross Sales",
        "Invoices": "Invoices",
        "Kode": "Kode",
        "Diskon": "Diskon",
        "Total Akhir": "Total Akhir",
        "Type": "Tipe",
        "User": "User",
        "Closed By": "Closed By",
        "Reason": "Alasan",
        "Channel": "Channel",
        "Created At": "Created At",
        "Members": "Members",
        "Invoice ID": "Invoice ID",
        "Pakasir Checkout": "Pakasir Checkout",
    },
    "en": {
        "catalog_intro": "Choose a product from the menu below. Listed prices are the current Vercettia Store prices.",
        "product_intro": "Product details, price, status, and active stock are listed below.",
        "invoice_intro": "Invoice created. Complete payment in this ticket. Admin will send the premium account data after payment is confirmed.",
        "payment_intro": "Official payment methods for Vercettia Store.",
        "offer_intro": "Active promotions and special offers will appear here.",
        "Product Data": "Product Data",
        "Order Data": "Order Data",
        "Payment": "Payment",
        "Description": "Description",
        "Stats": "Stats",
        "Voucher Data": "Voucher Data",
        "Offer Data": "Offer Data",
        "Ticket Data": "Ticket Data",
        "Close Data": "Close Data",
        "Member Data": "Member Data",
        "Product": "Product",
        "Price": "Price",
        "Harga": "Price",
        "Access": "Access",
        "Akses": "Access",
        "Status": "Status",
        "Stock": "Stock",
        "Stok": "Stock",
        "Quantity": "Quantity",
        "Total": "Total",
        "Method": "Method",
        "Delivery": "Delivery",
        "QRIS": "QRIS",
        "Total Bayar": "Amount Due",
        "Expired": "Expires",
        "Holder": "Account Name",
        "Destination": "Destination",
        "Invoice": "Invoice",
        "Plan": "Plan",
        "Customer": "Customer",
        "Customer ID": "Customer ID",
        "Item": "Item",
        "Gross Sales": "Gross Sales",
        "Invoices": "Invoices",
        "Kode": "Code",
        "Diskon": "Discount",
        "Total Akhir": "Final Total",
        "Type": "Type",
        "User": "User",
        "Closed By": "Closed By",
        "Reason": "Reason",
        "Channel": "Channel",
        "Created At": "Created At",
        "Members": "Members",
        "Invoice ID": "Invoice ID",
        "Pakasir Checkout": "Pakasir Checkout",
    },
}


def tr(label: str, language: str) -> str:
    return TEXT.get(language, TEXT["id"]).get(label, label)


def sorted_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(products, key=lambda product: display_product_name(product).casefold())


def is_product_sold_out(product: dict[str, Any]) -> bool:
    status = str(product.get("status", "")).strip().casefold()
    stock = int(product.get("stock", 0))
    return stock == 0 or status in {"kosong", "empty", "out of stock", "sold out", "habis"}


def is_product_orderable(product: dict[str, Any]) -> bool:
    status = str(product.get("status", "Ready")).strip().casefold()
    return not is_product_sold_out(product) and status == "ready" and int(product.get("price", 0)) > 0


def display_product_name_markdown(product: dict[str, Any]) -> str:
    name = display_product_name(product)
    if is_product_sold_out(product):
        return f"~~{name}~~"
    return name


def row(label: str, value: Any, language: str = "id") -> str:
    return f"- **{tr(label, language)}:** {value}"


def panel(
    title: str,
    *sections: tuple[str, list[tuple[str, Any]] | str],
    intro: str | None = None,
    language: str = "id",
) -> str:
    parts = [f"**{title}**", DIVIDER]
    if intro:
        parts.extend([intro, DIVIDER])
    for heading, content in sections:
        parts.append(f"**{tr(heading, language)}:**")
        if isinstance(content, str):
            parts.append(content)
        else:
            parts.extend(row(label, value, language) for label, value in content)
        parts.append(DIVIDER)
    if parts[-1] == DIVIDER:
        parts.pop()
    return "\n".join(parts)


def catalog_message(
    settings: dict[str, Any],
    categories: dict[str, Any],
    products: list[dict[str, Any]],
    language: str = "id",
    limit: int | None = None,
) -> str:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for product in products:
        grouped.setdefault(product.get("category", "products"), []).append(product)

    lines = [
        "**Vercettia Store**",
        DIVIDER,
        tr("catalog_intro", language),
        DIVIDER,
    ]

    for category_key, items in grouped.items():
        category = categories.get(category_key, {"name": category_key})
        lines.extend([f"**{category['name']}**"])
        for product in sorted_products(items):
            item = (
                f"- **{display_product_name_markdown(product)}**\n"
                f"  {tr('Harga', language)}: {money(int(product['price']), settings)} | "
                f"{tr('Akses', language)}: {product['type']} | "
                f"{tr('Status', language)}: {product_status(product)} | "
                f"{tr('Stok', language)}: {stock_text(int(product['stock']))}"
            )
            next_content = "\n".join([*lines, item])
            if limit is not None and len(next_content) > limit:
                lines.append("- Produk lain tersedia di menu pilihan." if language == "id" else "- More products are available in the selection menu.")
                return "\n".join(lines)
            lines.append(item)
        lines.append(DIVIDER)

    return "\n".join(lines)


def product_message(settings: dict[str, Any], product: dict[str, Any], language: str = "id") -> str:
    sections: list[tuple[str, list[tuple[str, Any]] | str]] = [
        (
            "Product Data",
            [
                ("Plan", product["duration"]),
                ("Akses", product["type"]),
                ("Harga", money(int(product["price"]), settings)),
                ("Status", product_status(product)),
                ("Stok", stock_text(int(product["stock"]))),
            ],
        )
    ]
    description = str(product.get("description", "")).strip()
    if description:
        sections.append(("Description", description[:900]))
    return panel(
        f"{display_product_name_markdown(product)} | {tr('Price', language)}",
        *sections,
        intro=tr("product_intro", language),
        language=language,
    )


def invoice_message(
    settings: dict[str, Any],
    order: dict[str, Any],
    product: dict[str, Any],
    payment_items: list[tuple[str, Any]] | None = None,
    language: str = "id",
) -> str:
    sections: list[tuple[str, list[tuple[str, Any]] | str]] = [
        (
            "Order Data",
            [
                ("Product", display_product_name(product)),
                ("Plan", product["duration"]),
                ("Akses", product["type"]),
                ("Quantity", order["quantity"]),
                ("Harga", money(int(product["price"]), settings)),
                ("Total", money(int(order["total"]), settings)),
                ("Status", order["status"]),
            ],
        )
    ]
    if payment_items:
        sections.append(("Payment", payment_items))
    return panel(f"Invoice {order['invoice']}", *sections, intro=tr("invoice_intro", language), language=language)


def order_lookup_message(settings: dict[str, Any], order: dict[str, Any], language: str = "id") -> str:
    sections: list[tuple[str, list[tuple[str, Any]] | str]] = [
        (
            "Order Data",
            [
                ("Product", order["product"]),
                ("Quantity", order["quantity"]),
                ("Total", money(int(order["total"]), settings)),
                ("Status", order["status"]),
            ],
        )
    ]
    if "payment_url" in order.keys() and order["payment_url"]:
        sections.append(("Payment", [("Method", "QRIS")]))
    return panel(f"Invoice {order['invoice']}", *sections, intro=tr("invoice_intro", language), language=language)


def payment_message(settings: dict[str, Any], methods: list[dict[str, Any]], gateway_ready: bool, language: str = "id") -> str:
    sections: list[tuple[str, list[tuple[str, Any]] | str]] = []
    if gateway_ready:
        sections.append(
            (
                "Pakasir QRIS Checkout",
                [
                    ("Method", "QRIS"),
                    ("Status", "Active"),
                    ("Invoice", "Pay Now tersedia di setiap checkout"),
                ],
            )
        )
    for method in methods:
        if not method.get("enabled", True):
            continue
        sections.append(
            (
                method["name"],
                [
                    ("Holder", method["account_name"]),
                    ("Destination", f"`{method['account_number']}`"),
                ],
            )
        )
    return panel("Vercettia Checkout", *sections, intro=tr("payment_intro", language), language=language)


def orders_message(settings: dict[str, Any], orders: list[Any], language: str = "id") -> str:
    if not orders:
        return panel("Order Desk", ("Order Data", "Belum ada order masuk." if language == "id" else "No orders yet."), language=language)

    sections: list[tuple[str, list[tuple[str, Any]] | str]] = []
    for order in orders:
        sections.append(
            (
                order["invoice"],
                [
                    ("Customer ID", f"`{order['user_id']}`"),
                    ("Item", f"{order['product']} x{order['quantity']}"),
                    ("Total", money(int(order["total"]), settings)),
                    ("Status", order["status"]),
                ],
            )
        )
    return panel("Order Desk", *sections, language=language)


def statistic_message(settings: dict[str, Any], stats: dict[str, int], language: str = "id") -> str:
    return panel(
        "Store Performance",
        (
            "Stats",
            [
                ("Invoices", stats["orders_count"]),
                ("Gross Sales", money(stats["revenue"], settings)),
            ],
        ),
        language=language,
    )


def order_log_message(
    settings: dict[str, Any],
    user_mention: str,
    order: dict[str, Any],
    product: dict[str, Any],
    total: int,
    language: str = "id",
) -> str:
    sections: list[tuple[str, list[tuple[str, Any]] | str]] = [
        (
            "Order Data",
            [
                ("Customer", user_mention),
                ("Invoice ID", order["invoice"]),
                ("Product", product["name"]),
                ("Quantity", order["quantity"]),
                ("Harga", money(int(product["price"]), settings)),
                ("Total", money(total, settings)),
                ("Status", order["status"]),
                ("Created At", compact_datetime(str(order["date"]))),
            ],
        )
    ]
    if order.get("payment_url"):
        sections.append(("Payment", [("Pakasir Checkout", order["payment_url"])]))
    if order.get("note"):
        sections.append(("Note", str(order["note"])[:900]))
    return panel("New Checkout", *sections, language=language)


def ticket_panel_message(language: str = "id") -> str:
    return panel(
        "Help Ticket",
        (
            "Ticket Data",
            [
                ("Type", "Help Ticket"),
                ("Status", "Available"),
            ],
        ),
        intro=(
            "Buka ticket untuk kendala order, payment, produk, atau bantuan store."
            if language == "id"
            else "Open a ticket for order, payment, product, or store support."
        ),
        language=language,
    )
