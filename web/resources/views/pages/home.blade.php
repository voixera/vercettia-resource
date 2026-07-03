@php
    use Illuminate\Support\Str;

    $products = collect($catalog)->flatMap(fn ($group) => $group['products'])->values();
    $popular = $products->sortByDesc('stock')->take(8);
    $productLogo = function (array $product) {
        $slug = $product['slug'] ?? Str::slug($product['name']);
        $path = public_path("assets/product-logos/{$slug}.png");

        return file_exists($path) ? asset("assets/product-logos/{$slug}.png") : null;
    };
@endphp

<x-layouts.app title="Vercettia Store">
    <header class="site-header">
        <div class="header-inner">
            <a class="brand" href="/" aria-label="Vercettia Store">
                <img src="{{ asset('assets/logos.png') }}" alt="Vercettia Store">
                <strong>Vercettia Store</strong>
            </a>

            <nav class="main-nav" aria-label="Navigasi utama">
                <a href="#home">Home</a>
                <a href="#catalog">Produk</a>
                <a href="#order">Cara Order</a>
                <a href="#transaction">Cek Transaksi</a>
                <a href="#help">Bantuan</a>
            </nav>

            <div class="header-actions">
                <a href="#transaction">Cek Invoice</a>
                <a class="button-fill" href="#catalog">Lihat Produk</a>
            </div>
        </div>
    </header>

    <main class="page-wrap">
        <section id="home" class="landing-hero">
            <div class="landing-copy">
                <span class="eyebrow">Digital account marketplace</span>
                <h1>APK premium dengan proses order yang rapi.</h1>
                <p>Pilih paket, cek harga, lalu lanjutkan pembelian lewat ticket agar data akun diproses langsung oleh admin Vercettia.</p>
                <div class="landing-actions">
                    <a class="button-fill" href="#catalog">Explore Products</a>
                    <a class="button-line" href="#order">Cara Order</a>
                </div>
            </div>

            <aside class="hero-panel" aria-label="Ringkasan Vercettia Store">
                <div class="hero-panel-head">
                    <img src="{{ asset('assets/logos.png') }}" alt="">
                    <div>
                        <strong>Vercettia Store</strong>
                        <span>Premium apps ready to order</span>
                    </div>
                </div>
                <div class="hero-metrics">
                    <div>
                        <strong>{{ $products->count() }}</strong>
                        <span>Produk aktif</span>
                    </div>
                    <div>
                        <strong>{{ $products->sum('stock') }}</strong>
                        <span>Total stok</span>
                    </div>
                    <div>
                        <strong>QRIS</strong>
                        <span>Payment</span>
                    </div>
                </div>
                <div class="hero-preview">
                    @foreach ($popular->take(3) as $product)
                        @php($logoUrl = $productLogo($product))
                        <a href="#catalog">
                            <span class="app-logo">
                                @if ($logoUrl)
                                    <img src="{{ $logoUrl }}" alt="{{ $product['name'] }} logo">
                                @else
                                    {{ Str::of($product['name'])->substr(0, 1) }}
                                @endif
                            </span>
                            <div>
                                <strong @class(['is-empty' => $product['stock'] === 0])>{{ $product['name'] }}</strong>
                                <small>Rp {{ number_format($product['price'], 0, ',', '.') }}</small>
                            </div>
                            <b>{{ $product['stock'] === 0 ? 'Kosong' : 'Ready' }}</b>
                        </a>
                    @endforeach
                </div>
            </aside>
        </section>

        <section class="feature-row" aria-label="Keunggulan layanan">
            <article>
                <span>01</span>
                <h2>Produk terkurasi</h2>
                <p>Katalog fokus ke aplikasi premium yang sering dipakai, jadi pelanggan tidak perlu memilah daftar yang berantakan.</p>
            </article>
            <article>
                <span>02</span>
                <h2>Checkout jelas</h2>
                <p>Harga, stok, dan akses tampil ringkas sebelum customer lanjut ke ticket pembelian.</p>
            </article>
            <article>
                <span>03</span>
                <h2>Support via ticket</h2>
                <p>Admin memberi data akun dan membantu kendala langsung di channel ticket order.</p>
            </article>
        </section>

        <section class="quick-panel">
            <div class="search-box">
                <span>Cari produk</span>
                <input type="search" placeholder="Canva, VIU, WeTV, Prime Video..." data-product-search>
            </div>
            <div class="category-tabs" data-category-filter>
                <button class="is-active" type="button" data-category="all">Semua</button>
                @foreach ($catalog as $categoryName => $group)
                    <button type="button" data-category="{{ $categoryName }}">{{ $categoryName }}</button>
                @endforeach
            </div>
        </section>

        <section id="popular" class="section-block">
            <div class="section-head">
                <div>
                    <h2>Populer Sekarang</h2>
                    <p>Pilihan paling sering dibuka pelanggan.</p>
                </div>
                <a href="#catalog">Lihat semua</a>
            </div>

            <div class="popular-grid">
                @foreach ($popular as $product)
                    @php($logoUrl = $productLogo($product))
                    <a class="popular-card" href="#catalog" data-product-card data-category="{{ $product['category'] }}" data-name="{{ Str::lower($product['name'].' '.$product['description']) }}">
                        <span class="app-logo">
                            @if ($logoUrl)
                                <img src="{{ $logoUrl }}" alt="{{ $product['name'] }} logo">
                            @else
                                {{ Str::of($product['name'])->substr(0, 1) }}
                            @endif
                        </span>
                        <div>
                            <strong @class(['is-empty' => $product['stock'] === 0])>{{ $product['name'] }}</strong>
                            <small>{{ $product['duration'] }} · {{ $product['access_type'] }}</small>
                        </div>
                        <b>Rp {{ number_format($product['price'], 0, ',', '.') }}</b>
                    </a>
                @endforeach
            </div>
        </section>

        <section id="catalog" class="section-block">
            <div class="section-head">
                <div>
                    <h2>Daftar Produk</h2>
                    <p>Harga final tampil sebelum lanjut order.</p>
                </div>
            </div>

            @foreach ($catalog as $categoryName => $group)
                <div class="category-group" data-category-group="{{ $categoryName }}">
                    <h3>{{ $categoryName }}</h3>
                    <div class="product-list">
                        @foreach ($group['products'] as $product)
                            @php($logoUrl = $productLogo($product))
                            <article class="product-item" data-product-card data-category="{{ $categoryName }}" data-name="{{ Str::lower($product['name'].' '.$product['description']) }}">
                                <div class="product-main">
                                    <span class="app-logo">
                                        @if ($logoUrl)
                                            <img src="{{ $logoUrl }}" alt="{{ $product['name'] }} logo">
                                        @else
                                            {{ Str::of($product['name'])->substr(0, 1) }}
                                        @endif
                                    </span>
                                    <div>
                                        <h4 @class(['is-empty' => $product['stock'] === 0])>{{ $product['name'] }}</h4>
                                        <p>{{ $product['duration'] }} · {{ $product['access_type'] }}</p>
                                    </div>
                                </div>
                                <div class="product-info">
                                    <span @class(['stock-empty' => $product['stock'] === 0])>
                                        {{ $product['stock'] === -1 ? 'Stok unlimited' : 'Stok '.$product['stock'] }}
                                    </span>
                                    <strong>Rp {{ number_format($product['price'], 0, ',', '.') }}</strong>
                                </div>
                                <a class="buy-button" href="#help">Beli</a>
                            </article>
                        @endforeach
                    </div>
                </div>
            @endforeach
        </section>

        <section id="order" class="info-grid">
            <article>
                <h2>Cara Order</h2>
                <ol>
                    <li>Pilih produk dari katalog.</li>
                    <li>Checkout dan bayar via QRIS.</li>
                    <li>Lanjutkan proses di ticket.</li>
                </ol>
            </article>
            <article id="transaction">
                <h2>Cek Transaksi</h2>
                <p>Simpan nomor invoice setelah checkout. Status pembayaran dan bantuan order diproses melalui ticket.</p>
                <a class="button-line" href="#help">Butuh bantuan?</a>
            </article>
        </section>

        <section id="help" class="help-card">
            <div>
                <h2>Bantuan order</h2>
                <p>Untuk pembelian, kendala pembayaran, atau pertanyaan produk, lanjutkan melalui ticket Discord Vercettia Store.</p>
            </div>
            <a class="button-fill" href="#catalog">Pilih Produk</a>
        </section>
    </main>

    <footer class="site-footer">
        <strong>Vercettia Store</strong>
        <span>APK premium · QRIS checkout · Ticket support</span>
    </footer>
</x-layouts.app>
