from __future__ import annotations

from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import admin_only
from utils.embeds import base_embed, money


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def product_autocomplete(
        self,
        _: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        names = [
            product["name"]
            for product in self.bot.products_config.get("products", [])
            if current.lower() in product["name"].lower()
        ][:25]
        return [app_commands.Choice(name=name, value=name) for name in names]

    @app_commands.command(name="addproduct", description="Tambah produk baru.")
    @app_commands.default_permissions(administrator=True)
    @admin_only()
    async def addproduct(
        self,
        interaction: discord.Interaction,
        name: str,
        duration: str,
        product_type: str,
        price: int,
        stock: int,
        status: str,
        description: str,
        category: str,
    ) -> None:
        await self._safe_defer(interaction)
        categories = self.bot.products_config.get("categories", {})
        if category not in categories:
            await interaction.followup.send(
                f"Kategori tidak ditemukan. Pilihan: {', '.join(categories.keys())}",
                ephemeral=True,
            )
            return

        products = self.bot.products_config.setdefault("products", [])
        if self._find_product(name):
            await interaction.followup.send("Produk sudah ada.", ephemeral=True)
            return

        product = {
            "name": name,
            "duration": duration,
            "type": product_type,
            "price": price,
            "stock": stock,
            "status": status,
            "description": description,
            "category": category,
        }
        products.append(product)
        await self.bot.save_products_config()
        await interaction.followup.send(f"Produk **{name}** berhasil ditambahkan.", ephemeral=True)

    @app_commands.command(name="removeproduct", description="Hapus produk.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(name=product_autocomplete)
    @admin_only()
    async def removeproduct(self, interaction: discord.Interaction, name: str) -> None:
        await self._safe_defer(interaction)
        products = self.bot.products_config.get("products", [])
        self.bot.configs["products"]["products"] = [
            product for product in products if product["name"].lower() != name.lower()
        ]
        await self.bot.db.delete_product(name)
        await self.bot.save_products_config()
        await interaction.followup.send(f"Produk **{name}** dihapus.", ephemeral=True)

    @app_commands.command(name="editproduct", description="Edit deskripsi produk.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(name=product_autocomplete)
    @admin_only()
    async def editproduct(self, interaction: discord.Interaction, name: str, description: str) -> None:
        await self._safe_defer(interaction)
        product = self._find_product(name)
        if product is None:
            await interaction.followup.send("Produk tidak ditemukan.", ephemeral=True)
            return
        product["description"] = description
        await self.bot.save_products_config()
        await interaction.followup.send(f"Produk **{name}** diperbarui.", ephemeral=True)

    @app_commands.command(name="setprice", description="Ubah harga produk.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(name=product_autocomplete)
    @admin_only()
    async def setprice(self, interaction: discord.Interaction, name: str, price: int) -> None:
        await self._safe_defer(interaction)
        await self._set_product_value(interaction, name, "price", price, "Harga")

    @app_commands.command(name="setstock", description="Ubah stok produk. Gunakan -1 untuk unlimited.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(name=product_autocomplete)
    @admin_only()
    async def setstock(self, interaction: discord.Interaction, name: str, stock: int) -> None:
        await self._safe_defer(interaction)
        await self._set_product_value(interaction, name, "stock", stock, "Stok")

    @app_commands.command(name="setstatus", description="Ubah status produk.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(name=product_autocomplete)
    @admin_only()
    async def setstatus(
        self,
        interaction: discord.Interaction,
        name: str,
        status: str,
    ) -> None:
        await self._safe_defer(interaction)
        await self._set_product_value(interaction, name, "status", status, "Status")

    @app_commands.command(name="orders", description="Lihat order terbaru.")
    @app_commands.default_permissions(administrator=True)
    @admin_only()
    async def orders(self, interaction: discord.Interaction, limit: int = 10) -> None:
        await self._safe_defer(interaction)
        rows = await self.bot.db.list_orders(max(1, min(limit, 25)))
        settings = self.bot.settings
        embed = base_embed(settings, "Order Desk", "Ringkasan invoice terbaru dari Vercettia Store.")
        if not rows:
            embed.description = "Belum ada order masuk."
        for order in rows:
            embed.add_field(
                name=order["invoice"],
                value=(
                    f"Customer ID: `{order['user_id']}`\n"
                    f"Item: **{order['product']}** x{order['quantity']}\n"
                    f"Total: **{money(int(order['total']), settings)}**\n"
                    f"Status: **{order['status']}**"
                ),
                inline=False,
            )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="statistic", description="Lihat statistik penjualan.")
    @app_commands.default_permissions(administrator=True)
    @admin_only()
    async def statistic(self, interaction: discord.Interaction) -> None:
        await self._safe_defer(interaction)
        stats = await self.bot.db.statistics()
        settings = self.bot.settings
        embed = base_embed(settings, "Store Performance", "Snapshot penjualan Vercettia Store saat ini.")
        embed.add_field(name="Invoices", value=f"**{stats['orders_count']}**", inline=True)
        embed.add_field(name="Gross Sales", value=f"**{money(stats['revenue'], settings)}**", inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="reload", description="Reload config tanpa restart bot.")
    @app_commands.default_permissions(administrator=True)
    @admin_only()
    async def reload(self, interaction: discord.Interaction) -> None:
        await self._safe_defer(interaction)
        await self.bot.reload_configs()
        await self.bot.sync_products_to_database()
        await interaction.followup.send("Config berhasil direload.", ephemeral=True)

    @app_commands.command(name="backup", description="Backup database.")
    @app_commands.default_permissions(administrator=True)
    @admin_only()
    async def backup(self, interaction: discord.Interaction) -> None:
        await self._safe_defer(interaction)
        target = await self.bot.db.backup()
        await interaction.followup.send(f"Backup dibuat: `{target.name}`", ephemeral=True)

    async def _set_product_value(
        self,
        interaction: discord.Interaction,
        name: str,
        key: str,
        value: Any,
        label: str,
    ) -> None:
        product = self._find_product(name)
        if product is None:
            await interaction.followup.send("Produk tidak ditemukan.", ephemeral=True)
            return
        product[key] = value
        if key == "stock" and int(value) == 0:
            product["status"] = "Kosong"
            await self.bot.db.update_product_field(name, "status", "Kosong")
        elif key == "stock" and int(value) > 0 and str(product.get("status", "")).lower() == "kosong":
            product["status"] = "Ready"
            await self.bot.db.update_product_field(name, "status", "Ready")
        await self.bot.save_products_config()
        await interaction.followup.send(f"{label} **{name}** berhasil diperbarui.", ephemeral=True)

    def _find_product(self, name: str) -> dict[str, Any] | None:
        for product in self.bot.products_config.get("products", []):
            if product["name"].lower() == name.lower():
                return product
        return None

    @staticmethod
    async def _safe_defer(interaction: discord.Interaction) -> None:
        if interaction.response.is_done():
            return
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
        except (discord.HTTPException, discord.NotFound):
            return


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
