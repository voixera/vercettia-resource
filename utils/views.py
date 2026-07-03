from __future__ import annotations

import asyncio
from typing import Any

import discord

from utils.messages import catalog_message, product_message, panel, sorted_products, ticket_panel_message
from utils.modals import BuyModal
from utils.tickets import create_private_ticket_channel, staff_mention
from utils.translate import PanelView, TranslatableView


class BuyView(TranslatableView):
    def __init__(self, product: dict[str, Any], settings: dict[str, Any]) -> None:
        self.product = product
        self.settings = settings
        super().__init__(lambda language: product_message(settings, product, language), timeout=300)

    def extra_items(self) -> list[discord.ui.Item]:
        is_available = (
            int(self.product.get("stock", 0)) != 0
            and int(self.product.get("price", 0)) > 0
            and str(self.product.get("status", "Ready")).casefold() == "ready"
        )
        button = discord.ui.Button(
            label="Buy Now" if is_available else "Unavailable",
            style=discord.ButtonStyle.primary if is_available else discord.ButtonStyle.secondary,
            disabled=not is_available,
        )
        button.callback = self.buy
        return [button]

    async def buy(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(BuyModal(self.product))




class ProductSelect(discord.ui.Select):
    def __init__(self, products: list[dict[str, Any]], settings: dict[str, Any]) -> None:
        sorted_items = sorted_products(products)
        options = [
            discord.SelectOption(
                label=product["name"][:100],
                description=f"{product['duration']} | {product['type']} | Rp {int(product['price']):,}".replace(",", ".")[:100],
                value=product["name"],
            )
            for product in sorted_items[:25]
        ]
        if not options:
            options = [discord.SelectOption(label="Belum ada produk", value="empty")]
        super().__init__(placeholder="Pilih produk", min_values=1, max_values=1, options=options)
        self.products = {product["name"]: product for product in sorted_items}
        self.settings = settings

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.values[0] == "empty":
            await interaction.response.send_message("Belum ada produk yang tersedia.", ephemeral=True)
            return
        product = self.products[self.values[0]]
        await interaction.response.send_message(
            view=BuyView(product, self.settings),
            ephemeral=True,
        )


class StoreView(TranslatableView):
    def __init__(
        self,
        settings: dict[str, Any],
        categories: dict[str, Any],
        products: list[dict[str, Any]],
    ) -> None:
        self.settings = settings
        self.categories = categories
        self.products = products
        self.grouped = self._group_products()
        super().__init__(
            lambda language: catalog_message(settings, categories, products, language),
            timeout=300,
        )

    def build_content(self, language: str = "id") -> str:
        return catalog_message(self.settings, self.categories, self.products, language)

    def extra_items(self) -> list[discord.ui.Item]:
        return [ProductSelect(self.products, self.settings)]

    def _group_products(self) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for product in self.products:
            grouped.setdefault(product.get("category", "products"), []).append(product)
        return grouped


class TicketPanelView(PanelView):
    def __init__(self) -> None:
        super().__init__(ticket_panel_message, timeout=None)

    def extra_items(self) -> list[discord.ui.Item]:
        button = discord.ui.Button(
            label="Open Help Ticket",
            style=discord.ButtonStyle.primary,
            custom_id="ticket_open",
        )
        button.callback = self.open_ticket
        return [button]

    async def open_ticket(self, interaction: discord.Interaction) -> None:
        settings = getattr(interaction.client, "settings", {})
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Ticket hanya bisa dibuat di server.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)

        channel = await create_private_ticket_channel(
            guild,
            interaction.user,
            settings,
            prefix="help",
            reason="Vercettia Store help ticket",
        )
        mention = staff_mention(guild, settings)
        ticket_content = panel(
                "Help Ticket Opened",
                (
                    "Ticket Data",
                    [
                        ("User", interaction.user.mention),
                        ("Status", "Open"),
                    ],
                ),
        )
        view = CloseTicketView(interaction.user.id, f"{interaction.user.mention} {mention}\n\n{ticket_content}")
        await channel.send(view=view)
        await interaction.followup.send(f"Help ticket dibuat: {channel.mention}", ephemeral=True)


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

        reason = str(self.reason.value)
        content_builder = lambda language: panel(
            "Ticket Closed",
            (
                "Close Data",
                [
                    ("Closed By", interaction.user.mention),
                    ("Reason", reason),
                    ("Channel", "Auto delete dalam 5 detik"),
                ],
            ),
            language=language,
        )
        await interaction.response.send_message(
            view=TranslatableView(content_builder),
        )

        await asyncio.sleep(5)
        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}: {reason[:120]}")


class CloseTicketView(PanelView):
    def __init__(self, opener_id: int, content: str | None = None) -> None:
        self.opener_id = opener_id
        super().__init__(lambda _: content or ticket_panel_message(), timeout=None)

    def extra_items(self) -> list[discord.ui.Item]:
        button = discord.ui.Button(
            label="Close Ticket",
            style=discord.ButtonStyle.danger,
            custom_id=f"ticket_close_{self.opener_id}",
        )
        button.callback = self.close_ticket
        return [button]

    async def close_ticket(self, interaction: discord.Interaction) -> None:
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
