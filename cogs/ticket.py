from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import admin_only
from utils.embeds import base_embed
from utils.files import configured_files
from utils.views import TicketPanelView


class Ticket(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ticket", description="Kirim panel ticket Vercettia Store.")
    @app_commands.default_permissions(administrator=True)
    @admin_only()
    async def ticket(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        settings = self.bot.settings
        await interaction.followup.send(
            embed=base_embed(
                settings,
                "Help Ticket",
                "Gunakan ticket ini untuk kendala pembayaran, kendala produk, klaim order, atau bantuan lainnya.",
            ),
            view=TicketPanelView(),
            files=configured_files(settings, self.bot.db.path.parent.parent),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Ticket(bot))
