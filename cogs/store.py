from __future__ import annotations

import json
import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.messages import panel, product_message, sorted_products
from utils.supplier_sync import refresh_supplier_products
from utils.translate import TranslatableView
from utils.views import BuyView, StoreView


class Store(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.active_catalog_messages: set[tuple[int, int]] = set()
        self._last_products_snapshot = self._products_snapshot()
        self._refresh_interval_seconds = 60
        self.product_refresh_worker.start()

    def cog_unload(self) -> None:
        self.product_refresh_worker.cancel()

    @app_commands.command(name="store", description="Tampilkan katalog Vercettia Store.")
    @app_commands.checks.cooldown(1, 10)
    async def store(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        await self._refresh_supplier_stock()
        settings = self.bot.settings
        products = self.bot.products_config.get("products", [])
        categories = self.bot.products_config.get("categories", {})
        view = StoreView(settings, categories, products)
        message = await interaction.followup.send(view=view, wait=True)
        self._register_catalog_message(message)

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
            message = await interaction.followup.send(view=view, wait=True)
            self._register_catalog_message(message)
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
        try:
            result = await refresh_supplier_products(self.bot, add_new_products=True, save=True)
        except Exception:
            logging.exception("Failed to refresh supplier products.")
            return
        if result.error:
            logging.warning("Supplier refresh skipped: %s", result.error)

    @commands.Cog.listener("on_products_updated")
    async def on_products_updated(self) -> None:
        self._last_products_snapshot = self._products_snapshot()
        await self._edit_active_catalog_messages()

    @tasks.loop(seconds=60)
    async def product_refresh_worker(self) -> None:
        settings = getattr(self.bot, "settings", {})
        refresh_config = settings.get("product_auto_refresh", {})
        if isinstance(refresh_config, dict) and not refresh_config.get("enabled", True):
            return

        interval = int(refresh_config.get("interval_seconds", 60)) if isinstance(refresh_config, dict) else 60
        interval = max(30, interval)
        if self._refresh_interval_seconds != interval:
            self._refresh_interval_seconds = interval
            self.product_refresh_worker.change_interval(seconds=interval)

        await self._refresh_supplier_stock()

    @product_refresh_worker.before_loop
    async def before_product_refresh_worker(self) -> None:
        await self.bot.wait_until_ready()

    def _products_snapshot(self) -> str:
        payload = {
            "categories": self.bot.products_config.get("categories", {}),
            "products": self.bot.products_config.get("products", []),
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)

    def _register_catalog_message(self, message: discord.Message) -> None:
        channel = getattr(message, "channel", None)
        channel_id = getattr(channel, "id", None) or getattr(message, "channel_id", None)
        message_id = getattr(message, "id", None)
        if channel_id and message_id:
            self.active_catalog_messages.add((int(channel_id), int(message_id)))

    async def _edit_active_catalog_messages(self) -> None:
        if not self.active_catalog_messages:
            return

        settings = self.bot.settings
        products = self.bot.products_config.get("products", [])
        categories = self.bot.products_config.get("categories", {})
        stale_messages: set[tuple[int, int]] = set()

        for channel_id, message_id in list(self.active_catalog_messages):
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except discord.HTTPException:
                    stale_messages.add((channel_id, message_id))
                    continue

            if not hasattr(channel, "fetch_message"):
                stale_messages.add((channel_id, message_id))
                continue

            try:
                message = await channel.fetch_message(message_id)
                await message.edit(view=StoreView(settings, categories, products))
            except (discord.NotFound, discord.Forbidden):
                stale_messages.add((channel_id, message_id))
            except discord.HTTPException:
                logging.exception("Failed to edit product catalog message %s.", message_id)

        self.active_catalog_messages.difference_update(stale_messages)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Store(bot))
