from __future__ import annotations

from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import admin_only
from utils.embeds import base_embed, money


class VoucherGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(name="voucher", description="Kelola voucher Vercettia Store.")
        self.bot = bot

    @app_commands.command(name="create", description="Buat voucher baru.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(
        voucher_type=[
            app_commands.Choice(name="Persentase", value="percent"),
            app_commands.Choice(name="Nominal", value="nominal"),
        ]
    )
    @admin_only()
    async def create(
        self,
        interaction: discord.Interaction,
        code: str,
        voucher_type: app_commands.Choice[str],
        value: int,
        expired: str,
    ) -> None:
        await self.bot.db.create_voucher(code, voucher_type.value, value, expired)
        await interaction.response.send_message(f"Voucher `{code.upper()}` berhasil dibuat.", ephemeral=True)

    @app_commands.command(name="redeem", description="Cek dan hitung voucher.")
    async def redeem(self, interaction: discord.Interaction, code: str, total: int) -> None:
        voucher = await self.bot.db.get_voucher(code)
        if voucher is None:
            await interaction.response.send_message("Voucher tidak ditemukan.", ephemeral=True)
            return

        try:
            expired = datetime.fromisoformat(voucher["expired"])
            if expired.tzinfo is None:
                expired = expired.replace(tzinfo=UTC)
        except ValueError:
            await interaction.response.send_message("Format expired voucher tidak valid.", ephemeral=True)
            return

        if expired < datetime.now(UTC):
            await interaction.response.send_message("Voucher sudah expired.", ephemeral=True)
            return

        discount = int(voucher["value"])
        if voucher["type"] == "percent":
            discount_amount = total * discount // 100
        else:
            discount_amount = discount
        final_total = max(0, total - discount_amount)

        settings = self.bot.settings
        embed = base_embed(settings, "Voucher Applied")
        embed.add_field(name="Kode", value=voucher["code"], inline=True)
        embed.add_field(name="Diskon", value=money(discount_amount, settings), inline=True)
        embed.add_field(name="Total Akhir", value=money(final_total, settings), inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="delete", description="Hapus voucher.")
    @app_commands.default_permissions(administrator=True)
    @admin_only()
    async def delete(self, interaction: discord.Interaction, code: str) -> None:
        await self.bot.db.delete_voucher(code)
        await interaction.response.send_message(f"Voucher `{code.upper()}` dihapus.", ephemeral=True)


class Voucher(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.bot.tree.add_command(VoucherGroup(bot))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Voucher(bot))
