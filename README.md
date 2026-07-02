# Vercettia Store

Discord Marketplace Bot untuk penjualan akun premium digital menggunakan Python 3.12+, discord.py 2.x, dan SQLite async.

## Setup

1. Install dependency:

```bash
pip install -r requirements.txt
```

2. Isi token bot di `.env`:

```env
DISCORD_TOKEN=your_token
GUILD_ID=optional_test_guild_id
```

Gunakan `.env.example` sebagai template.

3. Edit konfigurasi:

- `config/settings.json` untuk role, channel, warna embed, logo, banner, dan branding.
- `config/products.json` untuk kategori dan produk.
- Copy `config/payment.example.json` menjadi `config/payment.json`, lalu isi metode pembayaran dan kredensial Pakasir.

4. Jalankan bot:

```bash
python bot.py
```

## Slash Commands

- `/store` menampilkan katalog dengan pagination dan select menu.
- `/product` menampilkan detail produk dengan autocomplete dan tombol Buy Now.
- `/payment` menampilkan metode pembayaran dari JSON.
- `/paymentstatus` mengecek status invoice Pakasir.
- `/ticket` mengirim panel ticket.
- `/promo` mengirim embed promo.
- `/voucher create`, `/voucher redeem`, `/voucher delete`.
- `/invoice` mencari invoice milik customer.
- `/addproduct`, `/removeproduct`, `/editproduct`, `/setprice`, `/setstock`, `/setstatus`.
- `/orders`, `/statistic`, `/reload`, `/backup`.

## Catatan Konfigurasi

Nilai `stock` `-1` berarti unlimited. Status produk yang siap dibeli harus bernilai `Ready`.

Role dan channel wajib diisi dengan ID Discord asli:

- `admin_role_id`
- `staff_role_id`
- `ticket_category_id`
- `order_log_channel_id`

Letakkan file gambar branding di:

- `assets/logo.png`
- `assets/banner.png`

## Pakasir Checkout

Setelah akun/proyek Pakasir siap, isi bagian `payment_gateway` di `config/payment.json`:

```json
{
  "payment_gateway": {
    "enabled": true,
    "provider": "pakasir",
    "base_url": "https://app.pakasir.com",
    "project_slug": "slug-project-pakasir",
    "api_key": "api-key-project-pakasir",
    "qris_only": false,
    "redirect_url": "",
    "default_method": "qris"
  }
}
```

Alur checkout:

1. Customer klik `Buy Now`.
2. Bot membuat invoice lokal.
3. Bot membuat link checkout Pakasir dengan invoice seperti `Vercettia-000001`.
4. Customer menerima DM invoice dengan tombol `Pay Now`.
5. Customer membayar melalui Pakasir.
6. Customer atau admin menjalankan `/paymentstatus invoice_id`.
7. Jika status Pakasir `completed`, invoice lokal berubah menjadi `Paid`.

`project_slug` cukup untuk membuat link checkout. `api_key` diperlukan untuk cek status transaksi melalui API Pakasir.
