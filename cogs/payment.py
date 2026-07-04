from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import admin_only
from utils.messages import panel, payment_message
from utils.pakasir import PakasirGateway
from utils.translate import StaticPanelView, TranslatableView


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

    @app_commands.command(name="pakasir_status", description="Cek config Pakasir yang sedang dipakai bot.")
    @app_commands.default_permissions(administrator=True)
    @admin_only()
    async def pakasir_status(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        gateway = PakasirGateway(self.bot.payment_config)
        test_url = "-"
        if gateway.is_ready_for_checkout:
            test_url = gateway.build_payment_url("VERCETTIA-CHECK", 1000)

        content = panel(
            "Pakasir Runtime Status",
            (
                "Payment",
                [
                    ("Status", "Ready" if gateway.is_ready_for_checkout else "Not Ready"),
                    ("Method", gateway.default_method.upper()),
                    ("Destination", gateway.base_url),
                    ("Project", gateway.project_slug or "-"),
                    ("QRIS", "Hosted Checkout" if not gateway.direct_qris_enabled else "Direct QRIS API"),
                    ("Invoice", test_url),
                    ("Type", gateway.masked_api_key()),
                ],
            ),
            (
                "Note",
                gateway.production_hint(),
            ),
        )
        await interaction.followup.send(
            view=StaticPanelView(content, accent_color=0x8B5CF6),
            ephemeral=True,
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Payment(bot))
