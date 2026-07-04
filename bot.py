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
from utils.views import LegacyVerifyMemberView, TicketPanelView, VerifyPanelView


BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR / "config"
COGS = (
    "cogs.store",
    "cogs.admin",
    "cogs.community",
    "cogs.ticket",
    "cogs.payment",
    "cogs.voucher",
    "cogs.invoice",
)


class VercettiaBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = self._env_bool("DISCORD_MEMBERS_INTENT", True)
        intents.voice_states = self._env_bool("DISCORD_VOICE_STATES_INTENT", True)
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.base_dir = BASE_DIR
        self.configs: dict[str, Any] = {}
        database_path = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "database" / "database.db")))
        self.db = Database(database_path)
        self._fulfillment_running = False

    async def setup_hook(self) -> None:
        await self.reload_configs()
        await self.db.connect()
        await self.db.init()
        await self.sync_products_to_database()

        for cog in COGS:
            await self.load_extension(cog)

        self.add_view(TicketPanelView())
        self.add_view(VerifyPanelView())
        self.add_view(LegacyVerifyMemberView())

        self.fulfillment_worker.change_interval(
            seconds=int(self.delivery_config.get("poll_interval_seconds", 45))
        )
        self.fulfillment_worker.start()

        if self._env_bool("DISCORD_SYNC_COMMANDS", False):
            await self.sync_application_commands()
        else:
            logging.info("Skipping application command sync. Set DISCORD_SYNC_COMMANDS=true to sync slash commands.")

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
            "payment": self._payment_config_from_env(
                self._load_json(CONFIG_DIR / "payment.json", required=False)
            ),
            "delivery": self._load_json(CONFIG_DIR / "delivery.json"),
            "supplier": self._supplier_config_from_env(
                self._load_json(CONFIG_DIR / "supplier.json", required=False)
            ),
        }

    async def sync_products_to_database(self) -> None:
        products = self.products_config.get("products", [])
        await self.db.prune_products([product["name"] for product in products])
        for product in products:
            await self.db.upsert_product(product)

    async def save_products_config(self) -> None:
        self._write_json(CONFIG_DIR / "products.json", self.products_config)
        await self.sync_products_to_database()
        self.dispatch("products_updated")

    async def save_settings_config(self) -> None:
        self._write_json(CONFIG_DIR / "settings.json", self.settings)

    async def save_supplier_config(self) -> None:
        self._write_json(CONFIG_DIR / "supplier.json", self.supplier_config)

    async def sync_application_commands(self) -> None:
        guild_id = os.getenv("GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logging.info("Synced %s slash commands to guild %s.", len(synced), guild_id)
            return

        synced = await self.tree.sync()
        logging.info("Synced %s global slash commands.", len(synced))

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

    @property
    def supplier_config(self) -> dict[str, Any]:
        return self.configs.get("supplier", {})

    @tasks.loop(seconds=45)
    async def fulfillment_worker(self) -> None:
        if self._fulfillment_running or not self.delivery_config.get("enabled", True):
            return

        gateway = PakasirGateway(self.payment_config)
        if not gateway.is_ready_for_status_check:
            return

        self._fulfillment_running = True
        try:
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
                    logging.info(
                        "Payment confirmed for %s. Manual delivery will be handled in the ticket.",
                        order["invoice"],
                    )
                except Exception:
                    logging.exception("Failed to process fulfillment for %s.", order["invoice"])
        except Exception:
            logging.exception("Fulfillment worker failed.")
        finally:
            self._fulfillment_running = False

    @fulfillment_worker.before_loop
    async def before_fulfillment_worker(self) -> None:
        await self.wait_until_ready()

    @staticmethod
    def _load_json(path: Path, *, required: bool = True) -> dict[str, Any]:
        if not path.exists():
            if required:
                raise FileNotFoundError(path)
            return {}
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def _env_bool(name: str, default: bool = False) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    @classmethod
    def _payment_config_from_env(cls, config: dict[str, Any]) -> dict[str, Any]:
        gateway = dict(config.get("payment_gateway", {}))
        if os.getenv("PAKASIR_PROJECT_SLUG") or os.getenv("PAKASIR_API_KEY"):
            gateway.update(
                {
                    "enabled": cls._env_bool("PAKASIR_ENABLED", True),
                    "provider": "pakasir",
                    "base_url": os.getenv("PAKASIR_BASE_URL", gateway.get("base_url", "https://app.pakasir.com")),
                    "project_slug": os.getenv("PAKASIR_PROJECT_SLUG", gateway.get("project_slug", "")),
                    "api_key": os.getenv("PAKASIR_API_KEY", gateway.get("api_key", "")),
                    "qris_only": cls._env_bool("PAKASIR_QRIS_ONLY", bool(gateway.get("qris_only", True))),
                    "redirect_url": os.getenv("PAKASIR_REDIRECT_URL", gateway.get("redirect_url", "")),
                    "default_method": os.getenv("PAKASIR_DEFAULT_METHOD", gateway.get("default_method", "qris")),
                    "checkout_note": os.getenv(
                        "PAKASIR_CHECKOUT_NOTE",
                        gateway.get(
                            "checkout_note",
                            "Admin akan mengirim data akun premium di ticket setelah pembayaran terkonfirmasi.",
                        ),
                    ),
                }
            )
        config["payment_gateway"] = gateway
        config.setdefault("methods", [])
        return config

    @classmethod
    def _supplier_config_from_env(cls, config: dict[str, Any]) -> dict[str, Any]:
        if os.getenv("TELEGRAM_API_ID") or os.getenv("TELEGRAM_SESSION_STRING"):
            config.update(
                {
                    "enabled": cls._env_bool("SUPPLIER_ENABLED", True),
                    "provider": "telegram_bot",
                    "bot_username": os.getenv("SUPPLIER_BOT_USERNAME", config.get("bot_username", "MeowtensOrder_bot")),
                    "api_id": int(os.getenv("TELEGRAM_API_ID", str(config.get("api_id", 0) or 0))),
                    "api_hash": os.getenv("TELEGRAM_API_HASH", config.get("api_hash", "")),
                    "session_name": os.getenv("TELEGRAM_SESSION_NAME", config.get("session_name", "meowtens_supplier")),
                    "session_string": os.getenv("TELEGRAM_SESSION_STRING", config.get("session_string", "")),
                    "stock_command": os.getenv("SUPPLIER_STOCK_COMMAND", config.get("stock_command", "/stock")),
                    "response_wait_seconds": int(
                        os.getenv("SUPPLIER_RESPONSE_WAIT_SECONDS", str(config.get("response_wait_seconds", 8)))
                    ),
                }
            )
        config.setdefault("product_map", [])
        return config

    @staticmethod
    def _write_json(path: Path, data: dict[str, Any]) -> None:
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
            file.write("\n")


async def main() -> None:
    load_dotenv(BASE_DIR / ".env")
    load_dotenv(BASE_DIR.parent / ".env")
    setup_logging(BASE_DIR / "logs")
    token = os.getenv("DISCORD_TOKEN")
    if not token or token == "put_your_bot_token_here":
        raise RuntimeError("Set DISCORD_TOKEN di file .env terlebih dahulu.")

    async with VercettiaBot() as bot:
        try:
            await bot.start(token)
        except discord.PrivilegedIntentsRequired as exc:
            raise RuntimeError(
                "Aktifkan Server Members Intent di Discord Developer Portal untuk bot ini, "
                "atau set DISCORD_MEMBERS_INTENT=false jika fitur welcome/leave/verify role ingin dimatikan sementara."
            ) from exc


if __name__ == "__main__":
    asyncio.run(main())
