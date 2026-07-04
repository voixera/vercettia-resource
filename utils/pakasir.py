from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import aiohttp


class PakasirConfigError(RuntimeError):
    pass


class PakasirGateway:
    def __init__(self, config: dict[str, Any]) -> None:
        gateway = config.get("payment_gateway", {})
        self.enabled = bool(gateway.get("enabled", False))
        self.provider = str(gateway.get("provider", "")).lower()
        self.base_url = str(gateway.get("base_url", "https://app.pakasir.com")).rstrip("/")
        self.project_slug = str(gateway.get("project_slug", "")).strip()
        self.api_key = str(gateway.get("api_key", "")).strip()
        self.qris_only = bool(gateway.get("qris_only", False))
        self.direct_qris_enabled = bool(gateway.get("direct_qris_enabled", False))
        self.redirect_url = str(gateway.get("redirect_url", "")).strip()
        self.default_method = str(gateway.get("default_method", "qris")).strip().lower()
        self.checkout_note = str(gateway.get("checkout_note", "")).strip()

    @property
    def is_ready_for_checkout(self) -> bool:
        return (
            self.enabled
            and self.provider == "pakasir"
            and bool(self.project_slug)
            and self.project_slug != "isi-slug-project-pakasir"
        )

    @property
    def is_ready_for_status_check(self) -> bool:
        return (
            self.is_ready_for_checkout
            and bool(self.api_key)
            and self.api_key != "isi-api-key-pakasir"
        )

    def build_payment_url(self, order_id: str, amount: int) -> str:
        if not self.is_ready_for_checkout:
            raise PakasirConfigError("Pakasir project_slug belum dikonfigurasi.")

        query: dict[str, str | int] = {"order_id": order_id}
        if self.redirect_url:
            query["redirect"] = self.redirect_url
        if self.qris_only:
            query["qris_only"] = 1

        return f"{self.base_url}/pay/{self.project_slug}/{amount}?{urlencode(query)}"

    async def create_transaction(self, order_id: str, amount: int, method: str | None = None) -> dict[str, Any]:
        if not self.is_ready_for_status_check:
            raise PakasirConfigError("Pakasir api_key belum dikonfigurasi.")

        payment_method = method or self.default_method
        payload = {
            "project": self.project_slug,
            "order_id": order_id,
            "amount": amount,
            "api_key": self.api_key,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/transactioncreate/{payment_method}",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=8),
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def transaction_detail(self, order_id: str, amount: int) -> dict[str, Any]:
        if not self.is_ready_for_status_check:
            raise PakasirConfigError("Pakasir api_key belum dikonfigurasi.")

        params = {
            "project": self.project_slug,
            "amount": amount,
            "order_id": order_id,
            "api_key": self.api_key,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/api/transactiondetail",
                params=params,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as response:
                response.raise_for_status()
                return await response.json()
