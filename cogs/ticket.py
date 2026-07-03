from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import admin_only
from utils.messages import ticket_panel_message
from utils.views import TicketPanelView


class Ticket(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ticket", description="Kirim panel ticket Vercettia Store.")
    @app_commands.default_permissions(administrator=True)
    @admin_only()
    async def ticket(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        await interaction.followup.send(
            view=TicketPanelView(),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Ticket(bot))
