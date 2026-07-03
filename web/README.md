# Vercettia Store Web

Laravel 12 application for the Vercettia Store marketplace API and premium web experience.

## Requirements

- PHP 8.4
- Composer
- Node.js 20+
- MySQL
- Redis

## Install

```bash
cd web
composer install
npm install
cp .env.example .env
php artisan key:generate
php artisan migrate
```

## Development

```bash
composer run dev
```

Or run processes separately:

```bash
php artisan serve
php artisan queue:listen
npm run dev
```

## Build

```bash
npm run build
php artisan optimize
```

## API

- `GET /api/v1/products`
- `GET /api/v1/products/{slug}`
- `GET /api/v1/statistics`

## Architecture

Controllers stay thin. Business logic belongs in services. Data access belongs in repositories when queries become shared or complex.

```text
Controller -> Service -> Repository -> Model
```

## Design Notes

The frontend intentionally avoids generic dashboard or marketplace styling. It uses a dark layered visual system, large product showcases, restrained accent color, and motion that supports navigation rather than distracting from it.

## Bot Migration

The Discord bot should gradually move from local JSON/SQLite reads to this API:

1. Read catalog from `GET /api/v1/products`.
2. Create orders through Laravel.
3. Let Laravel own payment status and supplier stock state.
4. Keep Discord responsible for interaction, tickets, and admin communication.
