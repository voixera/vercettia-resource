from __future__ import annotations

from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from utils.messages import panel, product_message, sorted_products
from utils.supplier_sync import refresh_supplier_products
from utils.translate import TranslatableView
from utils.views import BuyView, StoreView


class Store(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="store", description="Tampilkan katalog Vercettia Store.")
    @app_commands.checks.cooldown(1, 10)
    async def store(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        await self._refresh_supplier_stock()
        settings = self.bot.settings
        products = self.bot.products_config.get("products", [])
        categories = self.bot.products_config.get("categories", {})
        view = StoreView(settings, categories, products)
        await interaction.followup.send(
            view=view,
        )

    async def product_autocomplete(
        self,
        _: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        products = self.bot.products_config.get("products", [])
        matches = [
            product["name"]
            for product in sorted_products(products)
            if current.lower() in product["name"].lower()
        ][:25]
        return [app_commands.Choice(name=name, value=name) for name in matches]

    @app_commands.command(name="product", description="Lihat detail produk.")
    @app_commands.autocomplete(name=product_autocomplete)
    @app_commands.checks.cooldown(1, 5)
    async def product(self, interaction: discord.Interaction, name: str | None = None) -> None:
        await interaction.response.defer(thinking=True)
        await self._refresh_supplier_stock()
        settings = self.bot.settings
        products = self.bot.products_config.get("products", [])
        if name is None:
            categories = self.bot.products_config.get("categories", {})
            view = StoreView(settings, categories, products)
            await interaction.followup.send(
                view=view,
            )
            return

        product = self._find_product(name)
        if product is None:
            await interaction.followup.send("Produk tidak ditemukan.", ephemeral=True)
            return

        await interaction.followup.send(
            view=BuyView(product, settings),
        )

    @app_commands.command(name="promo", description="Tampilkan promo Vercettia Store.")
    async def promo(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        content_builder = lambda language: panel(
            "Vercettia Offers",
            ("Offer Data", [("Status", "Belum ada promo aktif." if language == "id" else "No active promotions.")]),
            intro="Promo aktif dan penawaran khusus akan tampil di sini." if language == "id" else "Active promotions and special offers will appear here.",
            language=language,
        )
        await interaction.followup.send(view=TranslatableView(content_builder))

    def _find_product(self, name: str) -> dict[str, Any] | None:
        for product in self.bot.products_config.get("products", []):
            if product["name"].lower() == name.lower():
                return product
        return None

    async def _refresh_supplier_stock(self) -> None:
        if not self.bot.supplier_config.get("enabled", False):
            return
        await refresh_supplier_products(self.bot, add_new_products=True, save=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Store(bot))
