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
                if gateway.is_ready_for_status_check and gateway.default_method == "qris":
                    payment_data = await gateway.create_transaction(order["invoice"], total, method="qris")
                    payment = payment_data.get("payment") or {}
                    qris_text = payment.get("payment_number")
                    pakasir_total = payment.get("total_payment")
                    pakasir_expired = payment.get("expired_at")
                await bot.db.update_order_payment(
                    order["invoice"],
                    provider="pakasir",
                    method="qris" if qris_text else "checkout_url",
                    payment_url=payment_url,
                )
                order["payment_provider"] = "pakasir"
                order["payment_method"] = "qris" if qris_text else "checkout_url"
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
        checkout_view = CheckoutView(order["invoice"], total, payment_url, content_builder)

        channel = await create_private_ticket_channel(
            guild,
            interaction.user,
            settings,
            prefix="order",
            reason=f"Vercettia Store checkout {order['invoice']}",
        )
        mention = staff_mention(guild, settings)
        qris_files: list[discord.File] = []
        if qris_text:
            qris_files.append(make_qris_file(qris_text, order["invoice"]))

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
