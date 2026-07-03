from __future__ import annotations

from collections.abc import Callable

import discord

from utils.messages import DIVIDER


ContentBuilder = Callable[[str], str]


class PanelView(discord.ui.LayoutView):
    def __init__(
        self,
        content_builder: ContentBuilder,
        timeout: float | None = 300,
        accent_color: int | None = None,
    ) -> None:
        super().__init__(timeout=timeout)
        self.content_builder = content_builder
        self.accent_color = accent_color
        self.language = "id"
        self.render()

    def extra_items(self) -> list[discord.ui.Item]:
        return []

    def add_content_container(self, content: str) -> None:
        content_container = discord.ui.Container(accent_color=self.accent_color)
        parts = [part.strip() for part in content.split(DIVIDER)]
        for index, part in enumerate(part for part in parts if part):
            if index:
                content_container.add_item(discord.ui.Separator())
            content_container.add_item(discord.ui.TextDisplay(part))
        self.add_item(content_container)

    def render(self) -> None:
        self.clear_items()
        self.add_content_container(self.content_builder(self.language))

        action_items = self.extra_items()
        if action_items:
            action_container = discord.ui.Container()
            for item in action_items:
                action_container.add_item(discord.ui.ActionRow(item))
            self.add_item(action_container)

        id_button = discord.ui.Button(
            label="Translate Indonesia",
            style=discord.ButtonStyle.secondary,
            emoji="🇮🇩",
            custom_id=None if self.timeout else "translate_id",
        )
        en_button = discord.ui.Button(
            label="Translate English",
            style=discord.ButtonStyle.secondary,
            emoji="🇺🇸",
            custom_id=None if self.timeout else "translate_en",
        )
        id_button.callback = self.translate_indonesia
        en_button.callback = self.translate_english

        translate_container = discord.ui.Container()
        translate_container.add_item(discord.ui.ActionRow(id_button, en_button))
        self.add_item(translate_container)

    async def set_language(self, interaction: discord.Interaction, language: str) -> None:
        await interaction.response.send_message(
            view=StaticPanelView(self.content_builder(language), self.accent_color),
            ephemeral=True,
        )

    async def translate_indonesia(self, interaction: discord.Interaction) -> None:
        await self.set_language(interaction, "id")

    async def translate_english(self, interaction: discord.Interaction) -> None:
        await self.set_language(interaction, "en")


TranslatableView = PanelView


class StaticPanelView(discord.ui.LayoutView):
    def __init__(self, content: str, accent_color: int | None = None) -> None:
        super().__init__(timeout=None)
        content_container = discord.ui.Container(accent_color=accent_color)
        parts = [part.strip() for part in content.split(DIVIDER)]
        for index, part in enumerate(part for part in parts if part):
            if index:
                content_container.add_item(discord.ui.Separator())
            content_container.add_item(discord.ui.TextDisplay(part))
        self.add_item(content_container)
