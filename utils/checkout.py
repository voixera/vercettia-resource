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
    ) -> None:
        self.invoice = invoice
        self.amount = amount
        self.payment_url = payment_url
        super().__init__(content_builder, timeout=900)

    def extra_items(self) -> list[discord.ui.Item]:
        if not self.payment_url:
            return []
        return [
            discord.ui.Button(
                label="Pay Now",
                style=discord.ButtonStyle.link,
                url=self.payment_url,
            )
        ]
