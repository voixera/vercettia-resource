from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import discord

from utils.checkout import CheckoutView
from utils.embeds import invoice_embed, money
from utils.files import configured_files
from utils.pakasir import PakasirConfigError, PakasirGateway
from utils.qris import make_qris_file


class BuyModal(discord.ui.Modal):
    def __init__(self, product: dict[str, Any]) -> None:
        super().__init__(title=f"Checkout - {product['name']}")
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
            await bot.db.update_product_field(self.product["name"], "stock", stock - quantity)
            self.product["stock"] = stock - quantity
            await bot.save_products_config()

        embed = invoice_embed(settings, order, self.product)
        if payment_url:
            embed.add_field(name="Payment Gateway", value="Pakasir Checkout", inline=False)
            if qris_text:
                embed.add_field(name="QRIS", value="Scan QRIS yang terlampir pada invoice ini.", inline=False)
                embed.set_image(url=f"attachment://qris-{order['invoice']}.png")
            if pakasir_total:
                embed.add_field(name="Pakasir Total", value=money(int(pakasir_total), settings), inline=True)
            if pakasir_expired:
                embed.add_field(name="Expired At", value=str(pakasir_expired), inline=True)
            if checkout_note:
                embed.add_field(name="Payment Instruction", value=checkout_note, inline=False)
        else:
            embed.add_field(
                name="Payment Instruction",
                value="Payment gateway belum aktif. Silakan hubungi staff untuk instruksi pembayaran.",
                inline=False,
            )
        base_dir = Path(__file__).resolve().parent.parent
        files = configured_files(settings, base_dir)
        checkout_view = CheckoutView(order["invoice"], total, payment_url)

        await interaction.followup.send(
            "Invoice berhasil dibuat. Detail checkout sudah dikirim ke DM Anda.",
            ephemeral=True,
        )

        try:
            dm_files = configured_files(settings, base_dir)
            if qris_text:
                dm_files.append(make_qris_file(qris_text, order["invoice"]))
            await interaction.user.send(
                embed=embed,
                view=checkout_view,
                files=dm_files,
            )
        except discord.Forbidden:
            if qris_text:
                files.append(make_qris_file(qris_text, order["invoice"]))
            await interaction.followup.send(
                "DM Anda tertutup, invoice dikirim di sini.",
                embed=embed,
                view=checkout_view,
                files=files,
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

        embed = discord.Embed(
            title="New Checkout",
            color=discord.Color(int(str(settings.get("embed_color", "#8B5CF6")).lstrip("#"), 16)),
        )
        embed.add_field(name="Customer", value=interaction.user.mention, inline=False)
        embed.add_field(name="Invoice ID", value=order["invoice"], inline=True)
        embed.add_field(name="Product", value=self.product["name"], inline=True)
        embed.add_field(name="Quantity", value=str(order["quantity"]), inline=True)
        embed.add_field(name="Unit Price", value=money(int(self.product["price"]), settings), inline=True)
        embed.add_field(name="Grand Total", value=f"**{money(total, settings)}**", inline=True)
        embed.add_field(name="Status", value=order["status"], inline=True)
        embed.add_field(name="Created At", value=order["date"], inline=False)
        if order.get("payment_url"):
            embed.add_field(name="Pakasir Checkout", value=order["payment_url"], inline=False)
        if order.get("note"):
            embed.add_field(name="Catatan", value=order["note"], inline=False)
        await channel.send(embed=embed)
