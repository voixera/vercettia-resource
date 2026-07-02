from __future__ import annotations

from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import base_embed, product_embed
from utils.files import configured_files
from utils.views import BuyView, StoreView


class Store(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="store", description="Tampilkan katalog Vercettia Store.")
    @app_commands.checks.cooldown(1, 10)
    async def store(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        settings = self.bot.settings
        products = self.bot.products_config.get("products", [])
        categories = self.bot.products_config.get("categories", {})
        view = StoreView(settings, categories, products)
        await interaction.followup.send(
            embeds=view.build_embeds(),
            view=view,
            files=configured_files(settings, self.bot.db.path.parent.parent),
        )

    async def product_autocomplete(
        self,
        _: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        products = self.bot.products_config.get("products", [])
        matches = [
            product["name"]
            for product in products
            if current.lower() in product["name"].lower()
        ][:25]
        return [app_commands.Choice(name=name, value=name) for name in matches]

    @app_commands.command(name="product", description="Lihat detail produk.")
    @app_commands.autocomplete(name=product_autocomplete)
    @app_commands.checks.cooldown(1, 5)
    async def product(self, interaction: discord.Interaction, name: str | None = None) -> None:
        await interaction.response.defer(thinking=True)
        settings = self.bot.settings
        products = self.bot.products_config.get("products", [])
        if name is None:
            categories = self.bot.products_config.get("categories", {})
            view = StoreView(settings, categories, products)
            await interaction.followup.send(
                embeds=view.build_embeds(),
                view=view,
                files=configured_files(settings, self.bot.db.path.parent.parent),
            )
            return

        product = self._find_product(name)
        if product is None:
            await interaction.followup.send("Produk tidak ditemukan.", ephemeral=True)
            return

        await interaction.followup.send(
            embed=product_embed(settings, product),
            view=BuyView(product),
            files=configured_files(settings, self.bot.db.path.parent.parent),
        )

    @app_commands.command(name="promo", description="Tampilkan promo Vercettia Store.")
    async def promo(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        settings = self.bot.settings
        embed = base_embed(
            settings,
            "Vercettia Offers",
            "Limited deals, curated upgrades, and fresh premium slots from Vercettia Store.",
        )
        embed.add_field(
            name="How to Claim",
            value="Buka `/product`, pilih aplikasi yang tersedia, lalu checkout melalui invoice resmi.",
            inline=False,
        )
        await interaction.followup.send(
            embed=embed,
            files=configured_files(settings, self.bot.db.path.parent.parent),
        )

    def _find_product(self, name: str) -> dict[str, Any] | None:
        for product in self.bot.products_config.get("products", []):
            if product["name"].lower() == name.lower():
                return product
        return None

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Store(bot))
