from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.messages import payment_message
from utils.pakasir import PakasirGateway
from utils.translate import TranslatableView


class Payment(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="payment", description="Tampilkan metode pembayaran.")
    async def payment(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        settings = self.bot.settings
        methods = self.bot.payment_config.get("methods", [])
        gateway = PakasirGateway(self.bot.payment_config)
        content_builder = lambda language: payment_message(
            settings,
            methods,
            gateway.is_ready_for_checkout,
            language,
        )
        await interaction.followup.send(
            view=TranslatableView(content_builder),
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Payment(bot))
