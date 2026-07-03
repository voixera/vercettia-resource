# Vercettia Store Architecture

Vercettia Store is designed as a premium digital marketplace with one source of truth: the Laravel API.

## System Shape

```text
project/
├── bot/              # Target location for the Discord client
├── web/              # Laravel 12 API and Blade/Vite web experience
├── docs/             # Architecture, operation, and product notes
├── database/         # Shared database notes and exports
└── storage/          # Runtime storage and backups
```

The current repository still keeps the production Discord bot at the root for stability. The migration path is to move it into `bot/` after the Laravel API is running and the bot has been switched from JSON/SQLite reads to REST API reads.

## Request Flow

1. Customer opens the web catalog or Discord `/product`.
2. Web and bot request product data from Laravel.
3. Laravel reads MySQL product data and cached supplier stock state.
4. Customer starts checkout.
5. Payment is created through Pakasir.
6. Discord ticket is opened for manual fulfillment.
7. Admin sends account data inside the ticket after payment confirmation.

## API Flow

```text
Discord Bot/Web UI
        |
        v
Laravel REST API
        |
        +--> MySQL: products, orders, vouchers, tickets
        +--> Redis: cache, queue, sessions
        +--> Scheduler: stock sync, payment status polling
```

## Database Core

- `categories`: visual and operational product grouping.
- `products`: catalog, price, supplier code, stock, and status.
- `orders`: invoice and payment lifecycle.

Future tables:

- `vouchers`
- `payments`
- `tickets`
- `supplier_sync_logs`
- `admin_api_keys`
- `audit_logs`

## Bot Integration

The bot should become a client:

- `GET /api/v1/products`
- `GET /api/v1/products/{slug}`
- `POST /api/v1/orders`
- `POST /api/v1/payments/pakasir`
- `GET /api/v1/statistics`

Bot-side JSON files are useful during transition, but Laravel should own permanent product, order, voucher, and payment state.

## Frontend Direction

The web experience uses Blade, Vite, TailwindCSS v4, AlpineJS, GSAP, Lenis, Motion One, and Three.js.

The visual system should feel quiet, premium, and product-led:

- deep layered black backgrounds
- restrained violet/cyan accents
- generous spacing
- smooth scroll and reveal
- glass with meaningful hierarchy
- large product showcases instead of dense marketplace cards

## Security

- Never commit `.env`, API keys, Telegram sessions, or payment config.
- Use Sanctum for admin and bot API authentication.
- Use signed webhook routes for payment callbacks.
- Log admin actions to `audit_logs`.
- Rate-limit public API and checkout endpoints.

## Performance

- Cache catalog responses in Redis.
- Queue supplier sync and payment polling.
- Use optimized Vite builds.
- Avoid heavy Three.js scenes on low-power devices.
- Keep motion transform/opacity based for smooth frames.
