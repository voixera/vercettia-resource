from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.checkout import CheckoutView
from utils.embeds import base_embed, money


class Invoice(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="invoice", description="Cari invoice berdasarkan ID.")
    async def invoice(self, interaction: discord.Interaction, invoice_id: str) -> None:
        order = await self.bot.db.get_order_for_user(invoice_id, interaction.user.id)
        if order is None:
            await interaction.response.send_message("Invoice tidak ditemukan.", ephemeral=True)
            return

        settings = self.bot.settings
        embed = base_embed(
            settings,
            f"Invoice {order['invoice']}",
            None,
        )
        embed.add_field(name="Product", value=f"**{order['product']}**", inline=False)
        embed.add_field(name="Quantity", value=str(order["quantity"]), inline=True)
        embed.add_field(name="Total", value=f"**{money(int(order['total']), settings)}**", inline=True)
        embed.add_field(name="Status", value=f"**{order['status']}**", inline=True)
        payment_url = order["payment_url"] if "payment_url" in order.keys() else ""
        if payment_url:
            embed.add_field(name="Payment", value="QRIS", inline=False)
        await interaction.response.send_message(
            embed=embed,
            view=CheckoutView(order["invoice"], int(order["total"]), payment_url or None),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Invoice(bot))
