from __future__ import annotations

import discord

from utils.pakasir import PakasirConfigError, PakasirGateway


class CheckoutView(discord.ui.View):
    def __init__(self, invoice: str, amount: int, payment_url: str | None) -> None:
        super().__init__(timeout=900)
        self.invoice = invoice
        self.amount = amount
        if payment_url:
            self.add_item(
                discord.ui.Button(
                    label="Pay Now",
                    style=discord.ButtonStyle.link,
                    url=payment_url,
                )
            )

    @discord.ui.button(label="Check Payment", style=discord.ButtonStyle.secondary)
    async def check_payment(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        bot = interaction.client
        order = await bot.db.get_order_for_user(self.invoice, interaction.user.id)
        if order is None:
            await interaction.response.send_message("Invoice tidak ditemukan untuk akun Anda.", ephemeral=True)
            return

        if order["status"].lower() == "done":
            await interaction.response.send_message("Transaksi sudah selesai dan produk sudah dikirim.", ephemeral=True)
            return

        if order["status"].lower() == "paid":
            await bot.deliver_order(order)
            await interaction.response.send_message("Produk sudah dikirim ke DM dan transaksi selesai.", ephemeral=True)
            return

        gateway = PakasirGateway(getattr(bot, "payment_config", {}))
        if not gateway.is_ready_for_status_check:
            await interaction.response.send_message(
                "Payment check belum aktif. Isi `api_key` Pakasir di `config/payment.json`, lalu gunakan `/reload`.",
                ephemeral=True,
            )
            return

        try:
            detail = await gateway.transaction_detail(order["invoice"], int(order["total"]))
        except PakasirConfigError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        except Exception:
            await interaction.response.send_message(
                "Belum bisa menghubungi Pakasir. Coba lagi beberapa saat.",
                ephemeral=True,
            )
            return

        transaction = detail.get("transaction") or {}
        if transaction.get("status") == "completed":
            await bot.db.mark_order_paid(
                order["invoice"],
                str(transaction.get("completed_at", "")),
                str(transaction.get("payment_method", order["payment_method"] or "")),
            )
            updated_order = await bot.db.get_order(order["invoice"])
            if updated_order:
                await bot.deliver_order(updated_order)
            await interaction.response.send_message(
                "Payment terkonfirmasi. Produk sudah dikirim ke DM dan transaksi selesai.",
                ephemeral=True,
            )
            return

        status = transaction.get("status", "pending")
        await interaction.response.send_message(f"Payment belum completed. Status Pakasir: `{status}`.", ephemeral=True)
