from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.checkout import CheckoutView
from utils.messages import order_lookup_message


class Invoice(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="invoice", description="Cari invoice berdasarkan ID.")
    async def invoice(self, interaction: discord.Interaction, invoice_id: str) -> None:
        order = await self.bot.db.get_order_for_user(invoice_id, interaction.user.id)
        if order is None:
            await interaction.response.send_message("Invoice tidak ditemukan.", ephemeral=True)
            return

        payment_url = order["payment_url"] if "payment_url" in order.keys() else ""
        content_builder = lambda language: order_lookup_message(self.bot.settings, order, language)
        await interaction.response.send_message(
            view=CheckoutView(order["invoice"], int(order["total"]), payment_url, content_builder),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Invoice(bot))
