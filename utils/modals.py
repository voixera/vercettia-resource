from __future__ import annotations

import logging
from typing import Any

import discord

from utils.checkout import CheckoutView
from utils.embeds import compact_datetime, money
from utils.messages import invoice_message, order_log_message, panel
from utils.pakasir import PakasirConfigError, PakasirGateway
from utils.qris import make_qris_file
from utils.tickets import create_private_ticket_channel, staff_mention
from utils.translate import TranslatableView


QRIS_KEYS = {
    "payment_number",
    "qris",
    "qr_string",
    "qr_code",
    "qr_content",
    "qris_string",
    "qris_content",
    "qris_payload",
}
TOTAL_KEYS = {"total_payment", "total", "amount", "gross_amount"}
EXPIRED_KEYS = {"expired_at", "expires_at", "expired", "expiry_time"}


def _find_nested_value(data: Any, keys: set[str]) -> Any | None:
    if isinstance(data, dict):
        for key, value in data.items():
            if str(key).casefold() in keys and value not in (None, ""):
                return value
        for value in data.values():
            found = _find_nested_value(value, keys)
            if found not in (None, ""):
                return found
    elif isinstance(data, list):
        for item in data:
            found = _find_nested_value(item, keys)
            if found not in (None, ""):
                return found
    return None


def _as_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip().replace("Rp", "").replace("IDR", "").replace(" ", "")
    try:
        if "," in text and "." in text:
            text = text.replace(".", "").replace(",", ".")
        elif "," in text:
            head, tail = text.rsplit(",", 1)
            text = f"{head}.{tail}" if len(tail) <= 2 else text.replace(",", "")
        elif "." in text:
            head, tail = text.rsplit(".", 1)
            text = text.replace(".", "") if len(tail) == 3 else f"{head}.{tail}"
        return int(float(text))
    except ValueError:
        return None


class BuyModal(discord.ui.Modal):
    def __init__(self, product: dict[str, Any]) -> None:
        super().__init__(title=f"Checkout Ticket - {product['name']}")
        self.product = product
        self.quantity = discord.ui.TextInput(
            label="Quantity",
            placeholder="Jumlah item yang ingin dibeli",
            default="1",
            min_length=1,
            max_length=4,
        )
        self.note = discord.ui.TextInput(
            label="Order Note",
            placeholder="Opsional: email, request akun, atau catatan lain",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=300,
        )
        self.add_item(self.quantity)
        self.add_item(self.note)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        logging.error(
            "Checkout modal failed for %s.",
            self.product.get("name"),
            exc_info=(type(error), error, error.__traceback__),
        )
        message = (
            "Checkout gagal dibuat. Coba jalankan /product ulang lalu klik Buy Now lagi. "
            "Jika masih gagal, hubungi admin untuk cek permission ticket dan konfigurasi pembayaran."
        )
        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except discord.HTTPException:
            logging.exception("Failed to send checkout error response.")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        bot = interaction.client
        settings = getattr(bot, "settings", {})
        guild = interaction.guild
        if guild is None:
            await interaction.followup.send("Checkout hanya bisa dibuat melalui server.", ephemeral=True)
            return

        try:
            quantity = int(str(self.quantity.value).strip())
        except ValueError:
            await interaction.followup.send("Jumlah harus berupa angka.", ephemeral=True)
            return

        if quantity < 1:
            await interaction.followup.send("Jumlah minimal 1.", ephemeral=True)
            return

        stock = int(self.product["stock"])
        status = str(self.product["status"]).lower()
        if stock == 0:
            await interaction.followup.send(
                settings.get("messages", {}).get("out_of_stock", "Stok tidak mencukupi."),
                ephemeral=True,
            )
            return
        if status != "ready":
            await interaction.followup.send(
                settings.get("messages", {}).get("maintenance", "Produk belum ready."),
                ephemeral=True,
            )
            return
        if stock != -1 and quantity > stock:
            await interaction.followup.send(
                settings.get("messages", {}).get("out_of_stock", "Stok tidak mencukupi."),
                ephemeral=True,
            )
            return

        total = int(self.product["price"]) * quantity
        order = await bot.db.create_order(
            user_id=interaction.user.id,
            product=self.product["name"],
            quantity=quantity,
            total=total,
            note=str(self.note.value or ""),
            invoice_prefix=settings.get("invoice_prefix", "VCS"),
        )

        gateway = PakasirGateway(getattr(bot, "payment_config", {}))
        payment_url: str | None = None
        checkout_note = gateway.checkout_note
        qris_text: str | None = None
        pakasir_total: int | None = None
        pakasir_expired: str | None = None
        if gateway.is_ready_for_checkout:
            try:
                payment_url = gateway.build_payment_url(order["invoice"], total)
                if (
                    gateway.direct_qris_enabled
                    and gateway.is_ready_for_status_check
                    and gateway.default_method == "qris"
                ):
                    try:
                        payment_data = await gateway.create_transaction(order["invoice"], total, method="qris")
                        qris_value = _find_nested_value(payment_data, QRIS_KEYS)
                        total_value = _find_nested_value(payment_data, TOTAL_KEYS)
                        expired_value = _find_nested_value(payment_data, EXPIRED_KEYS)
                        qris_text = str(qris_value) if qris_value else None
                        pakasir_total = _as_int(total_value)
                        pakasir_expired = str(expired_value) if expired_value else None
                    except Exception:
                        logging.exception("Failed to create Pakasir QRIS transaction for %s.", order["invoice"])
                await bot.db.update_order_payment(
                    order["invoice"],
                    provider="pakasir",
                    method="qris" if qris_text else "checkout_qr",
                    payment_url=payment_url,
                )
                order["payment_provider"] = "pakasir"
                order["payment_method"] = "qris" if qris_text else "checkout_qr"
                order["payment_url"] = payment_url
            except PakasirConfigError:
                payment_url = None

        if stock != -1:
            new_stock = stock - quantity
            await bot.db.update_product_field(self.product["name"], "stock", new_stock)
            self.product["stock"] = new_stock
            if new_stock == 0:
                await bot.db.update_product_field(self.product["name"], "status", "Kosong")
                self.product["status"] = "Kosong"
            await bot.save_products_config()

        payment_items: list[tuple[str, Any]]
        if payment_url:
            payment_items = [("Method", "Pakasir QRIS")]
            if pakasir_total:
                payment_items.append(("Total Bayar", money(int(pakasir_total), settings)))
            if pakasir_expired:
                payment_items.append(("Expired", compact_datetime(str(pakasir_expired))))
            payment_items.append(("QRIS", "Terlampir di invoice"))
            payment_items.append(("Delivery", "Manual oleh admin di ticket"))
        else:
            payment_items = [("Status", "Hubungi staff untuk instruksi pembayaran")]
        content_builder = lambda language: invoice_message(settings, order, self.product, payment_items, language)

        channel = await create_private_ticket_channel(
            guild,
            interaction.user,
            settings,
            prefix="order",
            reason=f"Vercettia Store checkout {order['invoice']}",
        )
        await bot.db.set_order_ticket_channel(order["invoice"], channel.id)
        order["ticket_channel_id"] = str(channel.id)

        mention = staff_mention(guild, settings)
        qris_files: list[discord.File] = []
        qris_payload = qris_text or payment_url
        if qris_payload:
            qris_files.append(make_qris_file(qris_payload, order["invoice"]))
        qris_filename = qris_files[0].filename if qris_files else None
        checkout_view = CheckoutView(
            order["invoice"],
            total,
            payment_url,
            content_builder,
            qris_filename=qris_filename,
        )

        await channel.send(
            f"{interaction.user.mention} {mention}\n"
            f"Checkout `{order['invoice']}` sudah dibuat. Selesaikan pembayaran di ticket ini, "
            "lalu tunggu admin mengirim data akun premium."
        )
        if qris_files:
            await channel.send(view=checkout_view, files=qris_files)
        else:
            await channel.send(view=checkout_view)

        from utils.views import CloseTicketView

        await channel.send(
            view=CloseTicketView(
                interaction.user.id,
                panel(
                    "Ticket Control",
                    (
                        "Ticket Data",
                        [
                            ("Invoice", order["invoice"]),
                            ("Status", "Open"),
                            ("Delivery", "Admin akan mengirim data akun di sini"),
                        ],
                    ),
                ),
            )
        )

        await interaction.followup.send(
            f"Checkout ticket dibuat: {channel.mention}. Lanjutkan pembayaran di ticket tersebut.",
            ephemeral=True,
        )

        await self._send_order_log(interaction, order, total)

    async def _send_order_log(
        self,
        interaction: discord.Interaction,
        order: dict[str, Any],
        total: int,
    ) -> None:
        bot = interaction.client
        settings = getattr(bot, "settings", {})
        channel_id = int(settings.get("order_log_channel_id", 0))
        channel = bot.get_channel(channel_id) if channel_id else None
        if not isinstance(channel, discord.TextChannel):
            logging.warning("Order log channel is not configured or not found.")
            return

        content_builder = lambda language: order_log_message(
                settings,
                interaction.user.mention,
                order,
                self.product,
                total,
                language,
            )
        await channel.send(view=TranslatableView(content_builder))
