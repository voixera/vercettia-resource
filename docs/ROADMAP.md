# Vercettia Store Roadmap

## Phase 1: Foundation

- Keep the current Discord bot stable.
- Add Laravel API skeleton.
- Define MySQL schema for products, categories, and orders.
- Build premium Blade/Vite landing and catalog experience.
- Document deployment and security practices.

## Phase 2: API Ownership

- Move products from bot JSON into MySQL.
- Add Sanctum-protected admin API.
- Add bot API token authentication.
- Switch Discord bot catalog reads to Laravel API.
- Add order creation endpoint used by the bot.

## Phase 3: Operations

- Add supplier stock scheduler.
- Add Pakasir payment polling queue.
- Add admin dashboard for products, vouchers, orders, tickets, and payments.
- Add audit logs and backups.

## Phase 4: Premium Experience

- Product detail transitions.
- Search, filter, and sorting.
- Admin charts and analytics.
- Motion QA for desktop and mobile.
- SEO metadata, sitemap, robots, and OpenGraph.

## Phase 5: Hardening

- Tests for API contracts.
- Queue retry policy.
- Webhook signature validation.
- Redis cache invalidation.
- Disaster recovery documentation.
