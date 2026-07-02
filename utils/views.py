from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import discord

from utils.embeds import base_embed, category_embed, product_embed
from utils.files import configured_files
from utils.modals import BuyModal


class BuyView(discord.ui.View):
    def __init__(self, product: dict[str, Any]) -> None:
        super().__init__(timeout=300)
        self.product = product

    @discord.ui.button(label="Buy Now", style=discord.ButtonStyle.primary)
    async def buy(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(BuyModal(self.product))




class ProductSelect(discord.ui.Select):
    def __init__(self, products: list[dict[str, Any]]) -> None:
        options = [
            discord.SelectOption(
                label=product["name"][:100],
                description=f"{product['duration']} | {product['type']} | Rp {int(product['price']):,}".replace(",", ".")[:100],
                value=product["name"],
            )
            for product in products[:25]
        ]
        if not options:
            options = [discord.SelectOption(label="Belum ada produk", value="empty")]
        super().__init__(placeholder="Pilih produk", min_values=1, max_values=1, options=options)
        self.products = {product["name"]: product for product in products}

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.values[0] == "empty":
            await interaction.response.send_message("Belum ada produk yang tersedia.", ephemeral=True)
            return
        product = self.products[self.values[0]]
        settings = getattr(interaction.client, "settings", {})
        base_dir = Path(__file__).resolve().parent.parent
        await interaction.response.send_message(
            embed=product_embed(settings, product),
            view=BuyView(product),
            files=configured_files(settings, base_dir),
            ephemeral=True,
        )


class StoreView(discord.ui.View):
    def __init__(
        self,
        settings: dict[str, Any],
        categories: dict[str, Any],
        products: list[dict[str, Any]],
    ) -> None:
        super().__init__(timeout=300)
        self.settings = settings
        self.categories = categories
        self.products = products
        self.grouped = self._group_products()
        self.add_item(ProductSelect(products))

    def build_embed(self) -> discord.Embed:
        return self.build_embeds()[0]

    def build_embeds(self) -> list[discord.Embed]:
        embed = base_embed(
            self.settings,
            "Vercettia Store",
            None,
        )
        embeds = [embed]

        for category_key, products in self.grouped.items():
            category = self.categories.get(category_key, {"name": category_key})
            embeds.append(
                category_embed(
                    self.settings,
                    category["name"],
                    category.get("description", ""),
                    products,
                )
            )

        return embeds[:10]

    def _group_products(self) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for product in self.products:
            grouped.setdefault(product.get("category", "products"), []).append(product)
        return grouped


class TicketPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Help Ticket", style=discord.ButtonStyle.primary, custom_id="ticket_open")
    async def open_ticket(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        settings = getattr(interaction.client, "settings", {})
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Ticket hanya bisa dibuat di server.", ephemeral=True)
            return

        category_id = int(settings.get("ticket_category_id", 0))
        category = guild.get_channel(category_id) if category_id else None
        staff_role = guild.get_role(int(settings.get("staff_role_id", 0)))
        admin_role = guild.get_role(int(settings.get("admin_role_id", 0)))
        safe_name = "".join(
            character.lower() if character.isalnum() else "-"
            for character in interaction.user.name
        ).strip("-")
        unique_suffix = str(interaction.user.id)[-6:]
        time_suffix = discord.utils.utcnow().strftime("%H%M%S")
        channel_name = f"help-{safe_name or 'user'}-{unique_suffix}-{time_suffix}"[:90]

        overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        for role in (staff_role, admin_role):
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True,
                )

        channel = await guild.create_text_channel(
            name=channel_name,
            category=category if isinstance(category, discord.CategoryChannel) else None,
            overwrites=overwrites,
            reason="Vercettia Store help ticket",
        )

        mention = staff_role.mention if staff_role else ""
        await channel.send(
            f"{interaction.user.mention} {mention}",
            embed=base_embed(
                settings,
                "Help Ticket Opened",
                "Silakan jelaskan kendala Anda dengan jelas. Tim Vercettia Store akan membantu melalui channel ini.",
            ),
            view=CloseTicketView(interaction.user.id),
        )
        await interaction.response.send_message(f"Help ticket dibuat: {channel.mention}", ephemeral=True)


class CloseTicketModal(discord.ui.Modal):
    def __init__(self, opener_id: int) -> None:
        super().__init__(title="Close Ticket")
        self.opener_id = opener_id
        self.reason = discord.ui.TextInput(
            label="Alasan Close",
            placeholder="Contoh: kendala sudah selesai, salah buka ticket, refund diproses",
            style=discord.TextStyle.paragraph,
            min_length=3,
            max_length=500,
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.channel, discord.TextChannel) or interaction.guild is None:
            await interaction.response.send_message("Ticket hanya bisa ditutup di channel server.", ephemeral=True)
            return

        settings = getattr(interaction.client, "settings", {})
        reason = str(self.reason.value)
        await interaction.response.send_message(
            embed=base_embed(
                settings,
                "Ticket Closed",
                "Ticket ini sudah ditutup. Channel akan dihapus otomatis.",
            ).add_field(name="Closed By", value=interaction.user.mention, inline=True)
            .add_field(name="Reason", value=reason, inline=False),
        )

        await asyncio.sleep(5)
        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}: {reason[:120]}")


class CloseTicketView(discord.ui.View):
    def __init__(self, opener_id: int) -> None:
        super().__init__(timeout=None)
        self.opener_id = opener_id

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger)
    async def close_ticket(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        settings = getattr(interaction.client, "settings", {})
        member = interaction.user
        is_opener = member.id == self.opener_id
        is_admin = isinstance(member, discord.Member) and (
            member.guild_permissions.administrator
            or any(role.id == int(settings.get("admin_role_id", 0)) for role in member.roles)
            or member.id in {int(user_id) for user_id in settings.get("admin_user_ids", [])}
        )
        if not is_opener and not is_admin:
            await interaction.response.send_message(
                "Ticket hanya bisa ditutup oleh pembuka ticket atau admin.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(CloseTicketModal(self.opener_id))
