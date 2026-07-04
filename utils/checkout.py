from __future__ import annotations

import discord

from utils.translate import ContentBuilder, TranslatableView


class CheckoutView(TranslatableView):
    def __init__(
        self,
        invoice: str,
        amount: int,
        payment_url: str | None,
        content_builder: ContentBuilder,
        qris_filename: str | None = None,
    ) -> None:
        self.invoice = invoice
        self.amount = amount
        self.payment_url = payment_url
        self.qris_filename = qris_filename
        super().__init__(content_builder, timeout=900)

    def add_content_container(self, content: str) -> None:
        super().add_content_container(content)
        if not self.qris_filename:
            return

        qris_container = discord.ui.Container(accent_color=0x8B5CF6)
        qris_container.add_item(
            discord.ui.TextDisplay(
                "**QRIS Payment**\nScan QRIS di bawah ini melalui aplikasi pembayaran kamu."
            )
        )
        qris_container.add_item(
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    f"attachment://{self.qris_filename}",
                    description=f"QRIS invoice {self.invoice}",
                )
            )
        )
        self.add_item(qris_container)

    def extra_items(self) -> list[discord.ui.Item]:
        return []
