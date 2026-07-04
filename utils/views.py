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


def _rules_channel_reference(guild: discord.Guild, settings: dict[str, Any]) -> tuple[str, str | None]:
    channel_id = int(settings.get("rules_channel_id", 0))
    channel = guild.get_channel(channel_id) if channel_id else None
    if isinstance(channel, discord.TextChannel):
        return channel.mention, f"https://discord.com/channels/{guild.id}/{channel.id}"
    return "channel rules server", None


async def _grant_member_role(interaction: discord.Interaction) -> tuple[bool, str]:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        return False, "Verify hanya bisa digunakan di server."

    settings = getattr(interaction.client, "settings", {})
    role_id = int(settings.get("member_role_id", 0))
    role = interaction.guild.get_role(role_id) if role_id else None
    if role is None:
        return False, "Role member belum diset. Minta admin menjalankan /verify_panel terlebih dahulu."

    if role in interaction.user.roles:
        return True, f"Akun kamu sudah terverifikasi dengan role {role.mention}."

    try:
        await interaction.user.add_roles(role, reason="Vercettia member verification")
    except discord.Forbidden:
        return False, "Bot belum punya izin untuk memberi role ini. Naikkan role bot di atas role member."

    return True, f"Verifikasi berhasil. Role {role.mention} sudah ditambahkan."


async def _send_rules_step(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Verify hanya bisa digunakan di server.", ephemeral=True)
        return

    settings = getattr(interaction.client, "settings", {})
    rules_reference, rules_url = _rules_channel_reference(interaction.guild, settings)
    await interaction.response.send_message(
        view=RulesReadView(interaction.user.id, rules_reference, rules_url),
        ephemeral=True,
    )


class VerifyPanelView(discord.ui.LayoutView):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.render()

    def render(self) -> None:
        container = discord.ui.Container(accent_color=0x8B5CF6)
        container.add_item(discord.ui.TextDisplay("**Vercettia Verification**"))
        container.add_item(discord.ui.Separator())
        container.add_item(
            discord.ui.TextDisplay(
                "Sebelum mendapatkan role member, baca rules server terlebih dahulu. "
                "Setelah itu lanjutkan verifikasi untuk membuka akses server."
            )
        )
        container.add_item(discord.ui.Separator())
        container.add_item(
            discord.ui.TextDisplay(
                "**Alur Join:**\n"
                "- Baca rules server\n"
                "- Konfirmasi sudah membaca rules\n"
                "- Verify member\n"
                "- Role member otomatis diberikan"
            )
        )
        self.add_item(container)

        button = discord.ui.Button(
            label="Baca Rules",
            style=discord.ButtonStyle.primary,
            custom_id="vercettia_read_rules",
        )
        button.callback = self.read_rules

        actions = discord.ui.Container()
        actions.add_item(discord.ui.ActionRow(button))
        self.add_item(actions)

    async def read_rules(self, interaction: discord.Interaction) -> None:
        await _send_rules_step(interaction)


class LegacyVerifyMemberView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verify Member",
        style=discord.ButtonStyle.primary,
        custom_id="vercettia_verify_member",
    )
    async def legacy_verify(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await _send_rules_step(interaction)


class RulesReadView(discord.ui.LayoutView):
    def __init__(self, user_id: int, rules_reference: str, rules_url: str | None) -> None:
        super().__init__(timeout=300)
        self.user_id = user_id
        self.rules_reference = rules_reference
        self.rules_url = rules_url
        self.render()

    def render(self) -> None:
        container = discord.ui.Container(accent_color=0x8B5CF6)
        container.add_item(discord.ui.TextDisplay("**Baca Rules Terlebih Dahulu**"))
        container.add_item(discord.ui.Separator())
        container.add_item(
            discord.ui.TextDisplay(
                f"Buka dan baca rules di {self.rules_reference}. "
                "Pastikan kamu paham aturan server sebelum lanjut verify member."
            )
        )
        self.add_item(container)

        confirm_button = discord.ui.Button(
            label="Saya Sudah Baca Rules",
            style=discord.ButtonStyle.primary,
        )
        confirm_button.callback = self.confirm_rules

        row_items: list[discord.ui.Item] = []
        if self.rules_url:
            row_items.append(
                discord.ui.Button(
                    label="Open Rules",
                    style=discord.ButtonStyle.link,
                    url=self.rules_url,
                )
            )
        row_items.append(confirm_button)

        actions = discord.ui.Container()
        actions.add_item(discord.ui.ActionRow(*row_items))
        self.add_item(actions)

    async def confirm_rules(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Flow verify ini hanya untuk akun yang membuka panel.", ephemeral=True)
            return
        await interaction.response.edit_message(view=RulesVerifyView(self.user_id))


class RulesVerifyView(discord.ui.LayoutView):
    def __init__(self, user_id: int) -> None:
        super().__init__(timeout=300)
        self.user_id = user_id
        self.render()

    def render(self) -> None:
        container = discord.ui.Container(accent_color=0x8B5CF6)
        container.add_item(discord.ui.TextDisplay("**Verify Member**"))
        container.add_item(discord.ui.Separator())
        container.add_item(
            discord.ui.TextDisplay(
                "Rules sudah dikonfirmasi. Klik tombol verify untuk mendapatkan role member."
            )
        )
        self.add_item(container)

        button = discord.ui.Button(
            label="Verify Member",
            style=discord.ButtonStyle.primary,
        )
        button.callback = self.verify

        actions = discord.ui.Container()
        actions.add_item(discord.ui.ActionRow(button))
        self.add_item(actions)

    async def verify(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Flow verify ini hanya untuk akun yang membuka panel.", ephemeral=True)
            return

        success, message = await _grant_member_role(interaction)
        await interaction.response.edit_message(view=VerificationResultView(success, message))


class VerificationResultView(discord.ui.LayoutView):
    def __init__(self, success: bool, message: str) -> None:
        super().__init__(timeout=300)
        container = discord.ui.Container(accent_color=0x22C55E if success else 0xEF4444)
        container.add_item(discord.ui.TextDisplay("**Verification Complete**" if success else "**Verification Failed**"))
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(message))
        self.add_item(container)


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
