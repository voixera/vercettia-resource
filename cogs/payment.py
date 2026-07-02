from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import is_admin_member
from utils.embeds import base_embed
from utils.files import configured_files
from utils.pakasir import PakasirConfigError, PakasirGateway


class Payment(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="payment", description="Tampilkan metode pembayaran.")
    async def payment(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        settings = self.bot.settings
        embed = base_embed(
            settings,
            "Vercettia Checkout",
            "Pembayaran diproses melalui channel resmi. Pastikan nominal sesuai invoice sebelum konfirmasi.",
        )
        methods = self.bot.payment_config.get("methods", [])
        gateway = PakasirGateway(self.bot.payment_config)
        if gateway.is_ready_for_checkout:
            embed.add_field(
                name="Pakasir QRIS Checkout",
                value=(
                    "Setiap invoice memiliki tombol **Pay Now** dengan mode QRIS. "
                    "Jika API key sudah diisi, bot juga melampirkan gambar QRIS langsung di DM invoice."
                ),
                inline=False,
            )
        for method in methods:
            if not method.get("enabled", True):
                continue
            embed.add_field(
                name=method["name"],
                value=f"Holder: **{method['account_name']}**\nDestination: `{method['account_number']}`",
                inline=False,
            )
        await interaction.followup.send(
            embed=embed,
            files=configured_files(settings, self.bot.db.path.parent.parent),
        )

    @app_commands.command(name="paymentstatus", description="Cek status pembayaran invoice Pakasir.")
    async def paymentstatus(self, interaction: discord.Interaction, invoice_id: str) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        order = await self.bot.db.get_order_for_user(invoice_id, interaction.user.id)
        if order is None:
            can_check_all = isinstance(interaction.user, discord.Member) and is_admin_member(
                interaction.user,
                self.bot.settings,
            )
            if can_check_all:
                order = await self.bot.db.get_order(invoice_id)
            if order is None:
                await interaction.followup.send("Invoice tidak ditemukan.", ephemeral=True)
                return

        if order["status"].lower() == "done":
            await interaction.followup.send("Transaksi sudah selesai dan produk sudah dikirim.", ephemeral=True)
            return

        if order["status"].lower() == "paid":
            await self.bot.deliver_order(order)
            await interaction.followup.send("Produk sudah dikirim ke DM dan transaksi selesai.", ephemeral=True)
            return

        gateway = PakasirGateway(self.bot.payment_config)
        if not gateway.is_ready_for_status_check:
            await interaction.followup.send(
                "Cek status Pakasir belum aktif. Isi `api_key` di `config/payment.json`, lalu jalankan `/reload`.",
                ephemeral=True,
            )
            return

        try:
            detail = await gateway.transaction_detail(order["invoice"], int(order["total"]))
        except PakasirConfigError as error:
            await interaction.followup.send(str(error), ephemeral=True)
            return
        except Exception:
            await interaction.followup.send("Gagal menghubungi Pakasir. Coba lagi nanti.", ephemeral=True)
            return

        transaction = detail.get("transaction") or {}
        status = str(transaction.get("status", "pending"))
        if status == "completed":
            await self.bot.db.mark_order_paid(
                order["invoice"],
                str(transaction.get("completed_at", "")),
                str(transaction.get("payment_method", order["payment_method"] or "")),
            )
            updated_order = await self.bot.db.get_order(order["invoice"])
            if updated_order:
                await self.bot.deliver_order(updated_order)
            await interaction.followup.send(
                "Payment terkonfirmasi. Produk sudah dikirim ke DM dan transaksi selesai.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(f"Payment belum selesai. Status Pakasir: `{status}`.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Payment(bot))
