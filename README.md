# Vercettia Store Discord Bot

Vercettia Store adalah premium digital marketplace yang sedang dikembangkan menjadi ekosistem bot Discord dan web Laravel.

Saat ini bot Discord tetap menjadi runtime utama yang stabil. Folder `web/` berisi fondasi Laravel 12 untuk API dan website premium, sedangkan `docs/` berisi arsitektur serta roadmap migrasi.

## Struktur

- `bot.py`, `cogs/`, `utils/`, `config/`: Discord bot produksi saat ini.
- `web/`: Laravel 12 API dan Blade/Vite frontend starter.
- `docs/`: arsitektur, roadmap, dan catatan sistem.
- `database/`: SQLite bot saat ini dan area transisi database.

## Setup

```bash
pip install -r requirements.txt
```

Isi token bot di `.env`:

```env
DISCORD_TOKEN=your_token
GUILD_ID=optional_test_guild_id
```

## Jalankan

```bash
python bot.py
```

## Deploy Railway

Project sudah siap untuk Railway sebagai worker service.

1. Push repository ke GitHub.
2. Buat project baru di Railway dari repository GitHub.
3. Tambahkan Volume Railway dan mount ke `/data`.
4. Isi Variables:

```env
DISCORD_TOKEN=token_bot_discord
GUILD_ID=id_server_discord
DATABASE_PATH=/data/database.db

PAKASIR_ENABLED=true
PAKASIR_PROJECT_SLUG=slug_project_pakasir
PAKASIR_API_KEY=api_key_pakasir
PAKASIR_QRIS_ONLY=true
PAKASIR_DEFAULT_METHOD=qris

SUPPLIER_ENABLED=true
SUPPLIER_BOT_USERNAME=MeowtensOrder_bot
SUPPLIER_STOCK_COMMAND=/stock
TELEGRAM_API_ID=api_id_telegram
TELEGRAM_API_HASH=api_hash_telegram
TELEGRAM_SESSION_STRING=session_string_telegram
```

Untuk mendapatkan `TELEGRAM_SESSION_STRING`, login Telegram lokal dulu lalu export:

```bash
python tools/supplier_login.py
python tools/export_telegram_session.py
```

Copy output `export_telegram_session.py` ke variable Railway `TELEGRAM_SESSION_STRING`.

Railway akan menjalankan:

```bash
python bot.py
```

## Config

- `config/products.json` untuk kategori dan produk.
- `config/payment.json` untuk Pakasir/payment gateway.
- `config/supplier.json` untuk sync stok reseller dari bot Telegram supplier.
- `config/delivery.json` untuk interval monitoring pembayaran. Data akun premium tetap dikirim manual oleh admin di ticket.
- `config/settings.json` untuk role, channel, whitelist admin, status bot, dan pesan.

## Commands

- `/store`
- `/product`
- `/payment`
- `/ticket`
- `/promo`
- `/voucher create`, `/voucher redeem`, `/voucher delete`
- `/invoice`
- `/addproduct`, `/removeproduct`, `/editproduct`
- `/setprice`, `/setstock`, `/setstatus`
- `/syncsupplierstock`
- `/orders`, `/statistic`, `/reload`, `/backup`

## Supplier Telegram

Bot bisa sync stok dari supplier Telegram melalui session akun Telegram reseller.

1. Isi `api_id` dan `api_hash` di `config/supplier.json`.
2. Pastikan `bot_username` berisi `MeowtensOrder_bot`.
3. Ubah `stock_command` sesuai command stok di bot supplier.
4. Sesuaikan `product_map` jika nama produk supplier berbeda.
5. Jalankan login sekali:

```bash
python tools/supplier_login.py
```

6. Aktifkan `"enabled": true`, lalu gunakan `/syncsupplierstock`.

## Catatan

File sensitif tetap di-ignore:

- `.env`
- `config/payment.json`
- `database/database.db`
- `logs/`

## Web Laravel

Lihat [web/README.md](web/README.md) untuk setup Laravel, API, Vite, dan arah migrasi bot ke API.

Dokumentasi arsitektur tersedia di [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
