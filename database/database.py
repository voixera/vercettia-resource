from __future__ import annotations

import asyncio
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.connection: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = await aiosqlite.connect(self.path)
        self.connection.row_factory = aiosqlite.Row

    async def close(self) -> None:
        if self.connection:
            await self.connection.close()

    async def init(self) -> None:
        db = self._db
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                duration TEXT NOT NULL,
                type TEXT NOT NULL,
                price INTEGER NOT NULL,
                stock INTEGER NOT NULL,
                status TEXT NOT NULL,
                description TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice TEXT NOT NULL UNIQUE,
                user_id INTEGER NOT NULL,
                product TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                total INTEGER NOT NULL,
                status TEXT NOT NULL,
                date TEXT NOT NULL,
                note TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS voucher (
                code TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                value INTEGER NOT NULL,
                expired TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        await self._ensure_order_columns()
        await db.commit()

    async def _ensure_order_columns(self) -> None:
        cursor = await self._db.execute("PRAGMA table_info(orders)")
        columns = {row["name"] for row in await cursor.fetchall()}
        migrations = {
            "payment_provider": "ALTER TABLE orders ADD COLUMN payment_provider TEXT DEFAULT ''",
            "payment_method": "ALTER TABLE orders ADD COLUMN payment_method TEXT DEFAULT ''",
            "payment_url": "ALTER TABLE orders ADD COLUMN payment_url TEXT DEFAULT ''",
            "ticket_channel_id": "ALTER TABLE orders ADD COLUMN ticket_channel_id TEXT DEFAULT ''",
            "paid_at": "ALTER TABLE orders ADD COLUMN paid_at TEXT DEFAULT ''",
            "delivered_at": "ALTER TABLE orders ADD COLUMN delivered_at TEXT DEFAULT ''",
            "payment_notice_sent_at": "ALTER TABLE orders ADD COLUMN payment_notice_sent_at TEXT DEFAULT ''",
        }
        for column, statement in migrations.items():
            if column not in columns:
                await self._db.execute(statement)

    async def upsert_product(self, product: dict[str, Any]) -> None:
        await self._db.execute(
            """
            INSERT INTO products (name, duration, type, price, stock, status, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                duration = excluded.duration,
                type = excluded.type,
                price = excluded.price,
                stock = excluded.stock,
                status = excluded.status,
                description = excluded.description
            """,
            (
                product["name"],
                product["duration"],
                product["type"],
                int(product["price"]),
                int(product["stock"]),
                product["status"],
                product["description"],
            ),
        )
        await self._db.commit()

    async def delete_product(self, name: str) -> None:
        await self._db.execute("DELETE FROM products WHERE lower(name) = lower(?)", (name,))
        await self._db.commit()

    async def prune_products(self, valid_names: list[str]) -> None:
        if not valid_names:
            await self._db.execute("DELETE FROM products")
            await self._db.commit()
            return

        placeholders = ",".join("?" for _ in valid_names)
        await self._db.execute(
            f"DELETE FROM products WHERE lower(name) NOT IN ({placeholders})",
            [name.lower() for name in valid_names],
        )
        await self._db.commit()

    async def list_products(self) -> list[aiosqlite.Row]:
        cursor = await self._db.execute("SELECT * FROM products ORDER BY name")
        return await cursor.fetchall()

    async def get_product(self, name: str) -> aiosqlite.Row | None:
        cursor = await self._db.execute(
            "SELECT * FROM products WHERE lower(name) = lower(?)",
            (name,),
        )
        return await cursor.fetchone()

    async def update_product_field(self, name: str, field: str, value: Any) -> None:
        allowed = {"duration", "type", "price", "stock", "status", "description"}
        if field not in allowed:
            raise ValueError(f"Invalid product field: {field}")
        await self._db.execute(
            f"UPDATE products SET {field} = ? WHERE lower(name) = lower(?)",
            (value, name),
        )
        await self._db.commit()

    async def create_order(
        self,
        user_id: int,
        product: str,
        quantity: int,
        total: int,
        note: str,
        invoice_prefix: str,
    ) -> dict[str, Any]:
        async with self._lock:
            cursor = await self._db.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM orders")
            row = await cursor.fetchone()
            next_id = int(row["next_id"])
            now = datetime.now(UTC)
            date = now.isoformat()
            timestamp = now.strftime("%Y%m%d%H%M%S")
            invoice = f"{invoice_prefix}-{timestamp}-{next_id:06d}"

            await self._db.execute(
                """
                INSERT INTO orders (invoice, user_id, product, quantity, total, status, date, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (invoice, user_id, product, quantity, total, "Waiting Payment", date, note),
            )
            await self._db.commit()

        return {
            "invoice": invoice,
            "user_id": user_id,
            "product": product,
            "quantity": quantity,
            "total": total,
            "status": "Waiting Payment",
            "date": date,
            "note": note,
        }

    async def list_orders(self, limit: int = 10) -> list[aiosqlite.Row]:
        cursor = await self._db.execute(
            "SELECT * FROM orders ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return await cursor.fetchall()

    async def list_orders_by_status(self, status: str, limit: int = 25) -> list[aiosqlite.Row]:
        cursor = await self._db.execute(
            "SELECT * FROM orders WHERE status = ? ORDER BY id ASC LIMIT ?",
            (status, limit),
        )
        return await cursor.fetchall()

    async def list_paid_undelivered_orders(self, limit: int = 25) -> list[aiosqlite.Row]:
        cursor = await self._db.execute(
            """
            SELECT * FROM orders
            WHERE status = ? AND COALESCE(delivered_at, '') = ''
            ORDER BY id ASC
            LIMIT ?
            """,
            ("Paid", limit),
        )
        return await cursor.fetchall()

    async def list_paid_orders_without_notice(self, limit: int = 25) -> list[aiosqlite.Row]:
        cursor = await self._db.execute(
            """
            SELECT * FROM orders
            WHERE status = ?
              AND COALESCE(payment_notice_sent_at, '') = ''
              AND COALESCE(ticket_channel_id, '') != ''
            ORDER BY id ASC
            LIMIT ?
            """,
            ("Paid", limit),
        )
        return await cursor.fetchall()

    async def get_order(self, invoice: str) -> aiosqlite.Row | None:
        cursor = await self._db.execute(
            "SELECT * FROM orders WHERE lower(invoice) = lower(?)",
            (invoice,),
        )
        return await cursor.fetchone()

    async def get_order_for_user(self, invoice: str, user_id: int) -> aiosqlite.Row | None:
        cursor = await self._db.execute(
            "SELECT * FROM orders WHERE lower(invoice) = lower(?) AND user_id = ?",
            (invoice, user_id),
        )
        return await cursor.fetchone()

    async def update_order_payment(
        self,
        invoice: str,
        provider: str,
        method: str,
        payment_url: str,
    ) -> None:
        await self._db.execute(
            """
            UPDATE orders
            SET payment_provider = ?, payment_method = ?, payment_url = ?
            WHERE lower(invoice) = lower(?)
            """,
            (provider, method, payment_url, invoice),
        )
        await self._db.commit()

    async def set_order_ticket_channel(self, invoice: str, channel_id: int) -> None:
        await self._db.execute(
            """
            UPDATE orders
            SET ticket_channel_id = ?
            WHERE lower(invoice) = lower(?)
            """,
            (str(channel_id), invoice),
        )
        await self._db.commit()

    async def mark_order_paid(self, invoice: str, paid_at: str, payment_method: str) -> None:
        await self._db.execute(
            """
            UPDATE orders
            SET status = ?, paid_at = ?, payment_method = ?
            WHERE lower(invoice) = lower(?)
            """,
            ("Paid", paid_at, payment_method, invoice),
        )
        await self._db.commit()

    async def mark_payment_notice_sent(self, invoice: str) -> None:
        sent_at = datetime.now(UTC).isoformat()
        await self._db.execute(
            """
            UPDATE orders
            SET payment_notice_sent_at = ?
            WHERE lower(invoice) = lower(?)
            """,
            (sent_at, invoice),
        )
        await self._db.commit()

    async def mark_order_done(self, invoice: str) -> None:
        delivered_at = datetime.now(UTC).isoformat()
        await self._db.execute(
            """
            UPDATE orders
            SET status = ?, delivered_at = ?
            WHERE lower(invoice) = lower(?)
            """,
            ("Done", delivered_at, invoice),
        )
        await self._db.commit()

    async def statistics(self) -> dict[str, int]:
        cursor = await self._db.execute(
            "SELECT COUNT(*) AS orders_count, COALESCE(SUM(total), 0) AS revenue FROM orders"
        )
        row = await cursor.fetchone()
        return {"orders_count": int(row["orders_count"]), "revenue": int(row["revenue"])}

    async def create_voucher(self, code: str, voucher_type: str, value: int, expired: str) -> None:
        await self._db.execute(
            """
            INSERT INTO voucher (code, type, value, expired)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET type = excluded.type, value = excluded.value, expired = excluded.expired
            """,
            (code.upper(), voucher_type, value, expired),
        )
        await self._db.commit()

    async def get_voucher(self, code: str) -> aiosqlite.Row | None:
        cursor = await self._db.execute("SELECT * FROM voucher WHERE code = ?", (code.upper(),))
        return await cursor.fetchone()

    async def delete_voucher(self, code: str) -> None:
        await self._db.execute("DELETE FROM voucher WHERE code = ?", (code.upper(),))
        await self._db.commit()

    async def backup(self) -> Path:
        backup_dir = self.path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        target = backup_dir / f"database-{timestamp}.db"
        await self._db.commit()
        shutil.copy2(self.path, target)
        return target

    @property
    def _db(self) -> aiosqlite.Connection:
        if self.connection is None:
            raise RuntimeError("Database is not connected.")
        return self.connection
