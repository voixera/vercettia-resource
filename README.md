# Vercettia Store Discord Bot

Vercettia Store sekarang difokuskan sebagai Discord marketplace bot untuk produk digital premium. Runtime utama hanya bot Python, tanpa website.

## Struktur

- `bot.py`: entrypoint bot.
- `cogs/`: slash commands dan fitur modular.
- `utils/`: helper checkout, ticket, supplier sync, message UI, payment gateway, dan checks.
- `config/`: konfigurasi produk, settings, payment, supplier, dan delivery.
- `database/`: SQLite runtime bot.
- `tools/`: helper login/export session supplier Telegram.
- `assets/`: logo dan asset produk.

## Setup Lokal

```bash
pip install -r requirements.txt
```

Isi token bot di `.env`:

```env
DISCORD_TOKEN=your_token
GUILD_ID=optional_test_guild_id
```

Jalankan bot:

```bash
python bot.py
```

## Deploy Railway

Project siap berjalan di Railway sebagai bot service dengan public domain untuk OAuth verify.

1. Push repository ke GitHub.
2. Buat project Railway dari repository GitHub.
3. Tambahkan Railway Volume dan mount ke `/data`.
4. Generate Railway public domain, lalu pakai domain itu untuk `PUBLIC_BASE_URL`.
5. Isi Variables:

```env
DISCORD_TOKEN=token_bot_discord
GUILD_ID=id_server_discord
DATABASE_PATH=/data/database.db
DISCORD_MEMBERS_INTENT=true
DISCORD_VOICE_STATES_INTENT=true
DISCORD_SYNC_COMMANDS=false
VERIFY_OAUTH_ENABLED=true
DISCORD_CLIENT_ID=client_id_aplikasi_discord
DISCORD_CLIENT_SECRET=client_secret_aplikasi_discord
PUBLIC_BASE_URL=https://domain-railway-kamu.up.railway.app
DISCORD_OAUTH_REDIRECT_URI=https://domain-railway-kamu.up.railway.app/verify/callback

PAKASIR_ENABLED=true
PAKASIR_PROJECT_SLUG=slug_project_pakasir
PAKASIR_API_KEY=api_key_pakasir
PAKASIR_QRIS_ONLY=true
PAKASIR_DIRECT_QRIS=true
PAKASIR_DEFAULT_METHOD=qris

SUPPLIER_ENABLED=true
SUPPLIER_BOT_USERNAME=MeowtensOrder_bot
SUPPLIER_STOCK_COMMAND=/stock
TELEGRAM_API_ID=api_id_telegram
TELEGRAM_API_HASH=api_hash_telegram
TELEGRAM_SESSION_STRING=session_string_telegram
```

Railway akan menjalankan:

```bash
python bot.py
```

Di Discord Developer Portal, buka aplikasi bot lalu aktifkan:

- Server Members Intent

Intent ini wajib untuk welcome/leave dan verify role. Jika belum aktif, Discord akan menolak koneksi dengan error `PrivilegedIntentsRequired`.

Untuk OAuth verify, buka Discord Developer Portal lalu tambahkan redirect URL:

```text
https://domain-railway-kamu.up.railway.app/verify/callback
```

URL itu harus sama dengan `DISCORD_OAUTH_REDIRECT_URI` di Railway.

Untuk update slash command, set `DISCORD_SYNC_COMMANDS=true` sementara lalu deploy sekali. Setelah command muncul di server, kembalikan ke `false` agar Railway restart tidak kena rate limit Discord `429`.

Untuk mendapatkan `TELEGRAM_SESSION_STRING`, login Telegram lokal dulu lalu export:

```bash
python tools/supplier_login.py
python tools/export_telegram_session.py
```

Copy output `export_telegram_session.py` ke variable Railway `TELEGRAM_SESSION_STRING`.

## Config

- `config/products.json`: kategori dan produk.
- `config/settings.json`: role, channel, whitelist admin, status bot, dan pesan.
- `config/delivery.json`: interval monitoring payment.
- `config/payment.json`: Pakasir/payment gateway, tidak di-commit.
- `config/supplier.json`: supplier Telegram, tidak di-commit.

## Commands

- `/store`
- `/product`
- `/payment`, `/pakasir_status`
- `/ticket`
- `/promo`
- `/voucher create`, `/voucher redeem`, `/voucher delete`
- `/invoice`
- `/addproduct`, `/removeproduct`, `/editproduct`
- `/setprice`, `/setstock`, `/setstatus`
- `/syncsupplierstock`
- `/orders`, `/statistic`, `/reload`, `/backup`
- `/welcome_setup`, `/leave_setup`, `/rules_setup`, `/verify_panel`, `/verify_lockdown`
- `/gift_role`, `/give_role`, `/remove_role`
- `/join_voice`, `/leave_voice`

## Join Flow

Alur member baru:

1. Klik `Verify Member`.
2. Authorize Vercettia melalui Discord OAuth.
3. Rules tampil di halaman verifikasi.
4. Setujui rules.
5. Bot otomatis memberi role member.

Setup:

```text
/rules_setup channel:#rules
/verify_panel role:@Member channel:#verify rules_channel:#rules lockdown:true
```

`/verify_panel` dengan `lockdown:true` akan membuat member yang belum verify hanya bisa melihat channel verify dan rules. Channel lain disembunyikan dari `@everyone`, lalu role member diberi akses ke channel publik yang sebelumnya memang terbuka.

Jika panel sudah pernah dibuat dan hanya ingin mengatur permission:

```text
/verify_lockdown role:@Member verify_channel:#verify rules_channel:#rules
```

## Supplier Telegram

Bot bisa sync stok dari supplier Telegram melalui session akun Telegram reseller.

1. Isi `api_id` dan `api_hash` di `config/supplier.json` atau Railway Variables.
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
- `config/supplier.json`
- `database/database.db`
- `logs/`
- `*.session`
