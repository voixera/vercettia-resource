from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from database.database import Database
from utils.logger import setup_logging
from utils.pakasir import PakasirGateway
from utils.views import TicketPanelView


BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR / "config"
COGS = (
    "cogs.store",
    "cogs.admin",
    "cogs.ticket",
    "cogs.payment",
    "cogs.voucher",
    "cogs.invoice",
)


class VercettiaBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.configs: dict[str, Any] = {}
        self.db = Database(BASE_DIR / "database" / "database.db")
        self._fulfillment_running = False

    async def setup_hook(self) -> None:
        await self.reload_configs()
        await self.db.connect()
        await self.db.init()
        await self.sync_products_to_database()

        for cog in COGS:
            await self.load_extension(cog)

        self.add_view(TicketPanelView())

        self.fulfillment_worker.change_interval(
            seconds=int(self.delivery_config.get("poll_interval_seconds", 45))
        )
        self.fulfillment_worker.start()

        guild_id = os.getenv("GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def close(self) -> None:
        self.fulfillment_worker.cancel()
        await self.db.close()
        await super().close()

    async def on_ready(self) -> None:
        settings = self.settings
        activity_name = settings.get("activity", "Made With Love by Vercettia Dev")
        await self.change_presence(
            status=discord.Status.dnd,
            activity=discord.CustomActivity(name=activity_name),
        )
        logging.info("Logged in as %s (%s)", self.user, self.user.id if self.user else "unknown")

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError,
    ) -> None:
        logging.exception("Slash command error: %s", error)
        message = self.settings.get("messages", {}).get(
            "generic_error",
            "Terjadi kesalahan. Silakan coba lagi nanti.",
        )
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    async def reload_configs(self) -> None:
        self.configs = {
            "settings": self._load_json(CONFIG_DIR / "settings.json"),
            "products": self._load_json(CONFIG_DIR / "products.json"),
            "payment": self._load_json(CONFIG_DIR / "payment.json"),
            "delivery": self._load_json(CONFIG_DIR / "delivery.json"),
        }

    async def sync_products_to_database(self) -> None:
        products = self.products_config.get("products", [])
        await self.db.prune_products([product["name"] for product in products])
        for product in products:
            await self.db.upsert_product(product)

    async def save_products_config(self) -> None:
        self._write_json(CONFIG_DIR / "products.json", self.products_config)
        await self.sync_products_to_database()

    @property
    def settings(self) -> dict[str, Any]:
        return self.configs.get("settings", {})

    @property
    def products_config(self) -> dict[str, Any]:
        return self.configs.get("products", {})

    @property
    def payment_config(self) -> dict[str, Any]:
        return self.configs.get("payment", {})

    @property
    def delivery_config(self) -> dict[str, Any]:
        return self.configs.get("delivery", {})

    @tasks.loop(seconds=45)
    async def fulfillment_worker(self) -> None:
        if self._fulfillment_running or not self.delivery_config.get("enabled", True):
            return

        gateway = PakasirGateway(self.payment_config)
        if not gateway.is_ready_for_status_check:
            return

        self._fulfillment_running = True
        try:
            paid_orders = await self.db.list_paid_undelivered_orders(limit=25)
            for order in paid_orders:
                try:
                    await self.deliver_order(order)
                except Exception:
                    logging.exception("Failed to deliver paid order %s.", order["invoice"])

            orders = await self.db.list_orders_by_status("Waiting Payment", limit=25)
            for order in orders:
                try:
                    if order["payment_provider"] != "pakasir":
                        continue

                    detail = await gateway.transaction_detail(order["invoice"], int(order["total"]))
                    transaction = detail.get("transaction") or {}
                    if transaction.get("status") != "completed":
                        continue

                    await self.db.mark_order_paid(
                        order["invoice"],
                        str(transaction.get("completed_at", "")),
                        str(transaction.get("payment_method", order["payment_method"] or "qris")),
                    )
                    updated_order = await self.db.get_order(order["invoice"])
                    if updated_order:
                        await self.deliver_order(updated_order)
                except Exception:
                    logging.exception("Failed to process fulfillment for %s.", order["invoice"])
        except Exception:
            logging.exception("Fulfillment worker failed.")
        finally:
            self._fulfillment_running = False

    @fulfillment_worker.before_loop
    async def before_fulfillment_worker(self) -> None:
        await self.wait_until_ready()

    async def deliver_order(self, order: Any) -> None:
        if order["delivered_at"]:
            return

        product_name = order["product"]
        delivery_products = self.delivery_config.get("products", {})
        default_message = self.delivery_config.get(
            "default_message",
            "Pembayaran sudah diterima. Produk sedang diproses oleh tim Vercettia Store.",
        )
        product_message = str(delivery_products.get(product_name, default_message))
        user = self.get_user(int(order["user_id"])) or await self.fetch_user(int(order["user_id"]))

        embed = discord.Embed(
            title=f"Order Done {order['invoice']}",
            description="Pembayaran sudah terkonfirmasi. Detail produk tersedia di bawah ini.",
            color=discord.Color(int(str(self.settings.get("embed_color", "#8B5CF6")).lstrip("#"), 16)),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Product", value=product_name, inline=False)
        embed.add_field(name="Delivery", value=product_message[:1024], inline=False)
        embed.set_footer(text=self.settings.get("footer", "Vercettia Store"))
        await user.send(embed=embed)
        await self.db.mark_order_done(order["invoice"])

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def _write_json(path: Path, data: dict[str, Any]) -> None:
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
            file.write("\n")


async def main() -> None:
    load_dotenv()
    setup_logging(BASE_DIR / "logs")
    token = os.getenv("DISCORD_TOKEN")
    if not token or token == "put_your_bot_token_here":
        raise RuntimeError("Set DISCORD_TOKEN di file .env terlebih dahulu.")

    async with VercettiaBot() as bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
