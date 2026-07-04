import Lenis from 'lenis'

type Product = {
  access_type: string
  category: string
  description: string
  duration: string
  name: string
  price: number
  slug: string
  stock: number
}

type CatalogGroup = {
  products: Product[]
}

type ProductResponse = {
  data: Record<string, CatalogGroup>
}

const appRoot = document.querySelector<HTMLElement>('#vercettia-app')

const lenis = new Lenis({
  lerp: 0.1,
  wheelMultiplier: 0.9,
})

function raf(time: number) {
  lenis.raf(time)
  requestAnimationFrame(raf)
}

requestAnimationFrame(raf)

function escapeHtml(value: string) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}

function formatRupiah(value: number) {
  return new Intl.NumberFormat('id-ID', {
    currency: 'IDR',
    maximumFractionDigits: 0,
    style: 'currency',
  }).format(value)
}

function sortProducts(products: Product[]) {
  return [...products].sort((first, second) => first.name.localeCompare(second.name, 'id-ID'))
}

function productSearchText(product: Product) {
  return `${product.name} ${product.description} ${product.category} ${product.duration} ${product.access_type}`.toLowerCase()
}

function productLogoFile(product: Product) {
  const name = product.name.toLowerCase()

  if (name.includes('alight')) return 'Alight Motion Icon.png'
  if (name.includes('canva')) return 'Canva.png'
  if (name.includes('capcut')) return 'CapCut.png'
  if (name.includes('disney')) return 'Disney+.png'
  if (name.includes('hbo')) return 'HBO Max.png'
  if (name.includes('iqiyi')) return 'iQIYI.png'
  if (name.includes('loklok')) return 'LokLok.png'
  if (name.includes('netflix')) return 'Netflix.png'
  if (name.includes('picsart')) return 'PicsArt.png'
  if (name.includes('prime')) return 'Prime Video.png'
  if (name.includes('spotify')) return 'Spotify.png'
  if (name.includes('viu')) return 'VIU.png'
  if (name.includes('wetv')) return 'WeTV.png'
  if (name.includes('youku')) return 'Youku.png'
  if (name.includes('youtube')) return 'YouTube.png'

  return `${product.slug}.png`
}

function productLogoUrl(product: Product) {
  return `/assets/app-logos/${encodeURIComponent(productLogoFile(product))}`
}

function brandMarkSvg() {
  return `
    <svg class="brand-mark" viewBox="0 0 28 28" aria-hidden="true">
      <rect x="3.5" y="3.5" width="21" height="21" rx="3.5"></rect>
      <path d="M9 8.5v11M19 8.5v11M9 14h10"></path>
      <circle cx="14" cy="14" r="2.5"></circle>
    </svg>
  `
}

function arrowSvg() {
  return `
    <svg class="chip-arrow" viewBox="0 0 16 16" aria-hidden="true">
      <circle cx="8" cy="8" r="6"></circle>
      <path d="M6.4 5.8 9 8l-2.6 2.2"></path>
    </svg>
  `
}

function heroBlueprintSvg() {
  return `
    <svg class="hero-blueprint wire-animate" viewBox="0 0 900 520" aria-hidden="true">
      <defs>
        <pattern id="blueprint-grid" width="36" height="36" patternUnits="userSpaceOnUse">
          <path d="M36 0H0V36" class="grid-line"></path>
        </pattern>
      </defs>
      <rect width="900" height="520" fill="url(#blueprint-grid)"></rect>
      <g class="blueprint-device">
        <path class="draw-line" d="M220 132h350l98 92v150H318l-98-92z"></path>
        <path class="draw-line" d="M220 132l98 92h350M318 224v150"></path>
        <path class="draw-line" d="M390 176h124M362 260h226M362 306h166"></path>
        <circle class="node-dot" cx="606" cy="182" r="5"></circle>
        <circle class="node-dot node-two" cx="618" cy="308" r="5"></circle>
        <circle class="node-dot node-three" cx="268" cy="182" r="5"></circle>
      </g>
      <g class="blueprint-orbit">
        <path class="draw-line slow-line" d="M160 410c90-62 198-92 326-90 92 1 178 20 258 58"></path>
        <path class="draw-line slow-line" d="M170 92c84 48 172 68 264 60 116-10 200-46 254-108"></path>
      </g>
    </svg>
  `
}

function stepIconSvg(kind: 'catalog' | 'checkout' | 'ticket') {
  if (kind === 'catalog') {
    return `
      <svg class="step-svg wire-animate" viewBox="0 0 48 48" aria-hidden="true">
        <rect class="draw-line" x="10" y="9" width="28" height="30" rx="4"></rect>
        <path class="draw-line" d="M16 17h16M16 24h16M16 31h10"></path>
        <circle class="node-dot" cx="34" cy="31" r="2"></circle>
      </svg>
    `
  }

  if (kind === 'checkout') {
    return `
      <svg class="step-svg wire-animate" viewBox="0 0 48 48" aria-hidden="true">
        <path class="draw-line" d="M9 16h30v20H9zM9 22h30"></path>
        <path class="draw-line" d="M16 30h6M28 30h4"></path>
        <circle class="node-dot" cx="36" cy="12" r="3"></circle>
      </svg>
    `
  }

  return `
    <svg class="step-svg wire-animate" viewBox="0 0 48 48" aria-hidden="true">
      <path class="draw-line" d="M10 12h28v20H21l-7 6v-6h-4z"></path>
      <path class="draw-line" d="M17 20h14M17 26h9"></path>
      <circle class="node-dot" cx="35" cy="35" r="3"></circle>
    </svg>
  `
}

function featureIllustrationSvg(kind: 'box' | 'pipeline') {
  if (kind === 'box') {
    return `
      <svg class="feature-svg wire-animate" viewBox="0 0 420 420" aria-hidden="true">
        <g class="cad-box">
          <path class="draw-line" d="M112 150 210 94l98 56-98 57z"></path>
          <path class="draw-line" d="M112 150v120l98 56 98-56V150"></path>
          <path class="draw-line" d="M210 207v119"></path>
          <path class="draw-line slow-line" d="M150 170l98-56M170 286l98-56"></path>
        </g>
        <g class="stipple">
          <circle cx="82" cy="104" r="2"></circle>
          <circle cx="326" cy="98" r="2"></circle>
          <circle cx="340" cy="296" r="2"></circle>
          <circle cx="88" cy="304" r="2"></circle>
          <circle cx="218" cy="58" r="2"></circle>
          <circle cx="250" cy="352" r="2"></circle>
        </g>
      </svg>
    `
  }

  return `
    <svg class="feature-svg wire-animate" viewBox="0 0 420 420" aria-hidden="true">
      <path class="draw-line" d="M76 146h92c28 0 42 14 42 42v44c0 28 14 42 42 42h92"></path>
      <path class="draw-line slow-line" d="M76 274h68c28 0 42-14 42-42v-44c0-28 14-42 42-42h116"></path>
      <rect class="draw-line" x="70" y="118" width="72" height="56" rx="18"></rect>
      <rect class="draw-line" x="278" y="118" width="72" height="56" rx="18"></rect>
      <rect class="draw-line" x="278" y="246" width="72" height="56" rx="18"></rect>
      <circle class="node-dot" cx="210" cy="210" r="5"></circle>
      <circle class="node-dot node-two" cx="106" cy="146" r="4"></circle>
      <circle class="node-dot node-three" cx="314" cy="274" r="4"></circle>
    </svg>
  `
}

function checkIconSvg() {
  return `
    <svg class="check-svg" viewBox="0 0 14 14" aria-hidden="true">
      <path d="m3 7 2.5 2.5L11 4"></path>
    </svg>
  `
}

function productLogo(product: Product) {
  return `
    <span class="app-logo">
      <img src="${productLogoUrl(product)}" alt="" loading="lazy" data-logo-image>
      <span>${escapeHtml(product.name.trim().slice(0, 1).toUpperCase())}</span>
    </span>
  `
}

function orbitApp(product: Product, index: number) {
  return `
    <a class="orbit-app orbit-app-${index + 1}" href="#catalog" aria-label="${escapeHtml(product.name)}" data-reveal>
      <img src="${productLogoUrl(product)}" alt="" loading="lazy" data-logo-image>
      <span>${escapeHtml(product.name.split(' ')[0])}</span>
    </a>
  `
}

function popularCard(product: Product) {
  return `
    <a class="product-cell popular-card" href="#catalog" data-reveal data-product-card data-category="${escapeHtml(product.category)}" data-name="${escapeHtml(productSearchText(product))}">
      ${productLogo(product)}
      <div>
        <strong class="${product.stock === 0 ? 'is-empty' : ''}">${escapeHtml(product.name)}</strong>
        <small>${escapeHtml(product.duration)} / ${escapeHtml(product.access_type)}</small>
      </div>
      <b>${formatRupiah(product.price)}</b>
    </a>
  `
}

function productItem(product: Product, categoryName: string) {
  const stockLabel = product.stock === -1 ? 'Stok unlimited' : `Stok ${product.stock}`

  return `
    <article class="product-cell product-item" data-reveal data-product-card data-category="${escapeHtml(categoryName)}" data-name="${escapeHtml(productSearchText(product))}">
      <div class="product-main">
        ${productLogo(product)}
        <div>
          <h4 class="${product.stock === 0 ? 'is-empty' : ''}">${escapeHtml(product.name)}</h4>
          <p>${escapeHtml(product.duration)} / ${escapeHtml(product.access_type)}</p>
        </div>
      </div>
      <div class="product-info">
        <span class="${product.stock === 0 ? 'stock-empty' : ''}">${escapeHtml(stockLabel)}</span>
        <strong>${formatRupiah(product.price)}</strong>
      </div>
      <a class="button-pill buy-button" href="#help">Beli</a>
    </article>
  `
}

function renderApp(catalog: Record<string, CatalogGroup>) {
  if (!appRoot) {
    return
  }

  const categoryNames = Object.keys(catalog)
  const products = sortProducts(categoryNames.flatMap((categoryName) => catalog[categoryName]?.products ?? []))
  const popular = [...products].sort((first, second) => second.stock - first.stock).slice(0, 8)
  const totalStock = products.reduce((total, product) => total + Math.max(product.stock, 0), 0)

  appRoot.innerHTML = `
    <header class="site-header">
      <div class="header-inner">
        <a class="brand" href="/" aria-label="Vercettia Store">
          ${brandMarkSvg()}
          <strong>Vercettia</strong>
        </a>

        <nav class="main-nav" aria-label="Navigasi utama">
          <a href="#home">Home</a>
          <a href="#steps">Flow</a>
          <a href="#features">System</a>
          <a href="#catalog">Products</a>
          <a href="#help">Support</a>
        </nav>

        <div class="header-actions">
          <a href="#catalog">Login</a>
          <a class="button-pill" href="#catalog">Browse</a>
        </div>
      </div>
    </header>

    <main class="page-wrap">
      <section id="home" class="hero-spotlight section-frame section-frame-carbon">
        <div class="hero-art" data-reveal>${heroBlueprintSvg()}</div>
        <div class="hero-content">
          <span class="eyebrow-chip" data-reveal>NEW · VERCETTIA EARLY PREVIEW ${arrowSvg()}</span>
          <h1 data-reveal>Premium digital accounts, arranged like a clean operating system.</h1>
          <p data-reveal>Vercettia Store menyatukan katalog APK premium, checkout QRIS, dan handoff ticket admin dalam satu alur yang ringkas.</p>
          <div class="hero-actions" data-reveal>
            <a class="button-pill" href="#catalog">Browse products</a>
            <a class="button-ghost" href="#steps">See flow</a>
          </div>
        </div>
        <div class="hero-app-orbit" aria-label="Aplikasi tersedia">
          ${popular.slice(0, 7).map((product, index) => orbitApp(product, index)).join('')}
        </div>
      </section>

      <section id="steps" class="section-frame steps-section">
        <div class="section-title" data-reveal>
          <span class="section-label">ORDER FLOW</span>
          <h2>Get started in 3 simple steps.</h2>
        </div>
        <div class="steps-grid">
          <article class="step-card" data-reveal>
            <div class="icon-shell">${stepIconSvg('catalog')}</div>
            <h3>Pilih Produk</h3>
            <p>Browse katalog, filter kategori, dan cek harga serta stok tanpa daftar yang berantakan.</p>
          </article>
          <article class="step-card" data-reveal>
            <div class="icon-shell">${stepIconSvg('checkout')}</div>
            <h3>Checkout QRIS</h3>
            <p>Customer lanjut ke pembayaran resmi, lalu invoice menjadi referensi order.</p>
          </article>
          <article class="step-card" data-reveal>
            <div class="icon-shell">${stepIconSvg('ticket')}</div>
            <h3>Ticket Admin</h3>
            <p>Admin memberi data akun premium dan membantu kendala langsung di ticket.</p>
          </article>
        </div>
      </section>

      <section id="features" class="feature-panel section-frame">
        <div class="feature-copy" data-reveal>
          <span class="section-label">CONNECT YOUR CATALOG</span>
          <h2>Produk tampil sebagai katalog yang terukur.</h2>
          <p>Semua item tetap bersih: kategori, akses, durasi, harga, dan stok ditampilkan dalam format marketplace yang mudah dipindai.</p>
          <ul>
            <li>${checkIconSvg()} Sinkron dengan endpoint produk</li>
            <li>${checkIconSvg()} Search dan filter realtime</li>
            <li>${checkIconSvg()} Logo produk siap dari folder asset</li>
            <li>${checkIconSvg()} Empty stock tetap terbaca jelas</li>
          </ul>
        </div>
        <div class="feature-illustration" data-reveal>${featureIllustrationSvg('box')}</div>
      </section>

      <section class="feature-panel section-frame">
        <div class="feature-copy" data-reveal>
          <span class="section-label">HANDOFF TO SUPPORT</span>
          <h2>Checkout selesai, proses lanjut ke ticket.</h2>
          <p>Website hanya menjadi storefront. Proses pengiriman data akun tetap dipegang admin supaya order premium tetap rapi.</p>
          <ul>
            <li>${checkIconSvg()} QRIS checkout</li>
            <li>${checkIconSvg()} Invoice sebagai bukti order</li>
            <li>${checkIconSvg()} Ticket support untuk kendala</li>
            <li>${checkIconSvg()} Alur cocok dengan Discord bot</li>
          </ul>
        </div>
        <div class="feature-illustration" data-reveal>${featureIllustrationSvg('pipeline')}</div>
      </section>

      <section class="section-frame metrics-section">
        <div class="metric-card" data-reveal>
          <span>PRODUCTS</span>
          <strong>${products.length}</strong>
        </div>
        <div class="metric-card" data-reveal>
          <span>STOCK</span>
          <strong>${totalStock}</strong>
        </div>
        <div class="metric-card" data-reveal>
          <span>PAYMENT</span>
          <strong>QRIS</strong>
        </div>
        <div class="metric-card" data-reveal>
          <span>SUPPORT</span>
          <strong>TICKET</strong>
        </div>
      </section>

      <section class="section-frame catalog-tools" data-reveal>
        <div class="search-box">
          <span>SEARCH CATALOG</span>
          <input type="search" placeholder="Canva, VIU, WeTV, Prime Video..." data-product-search>
        </div>
        <div class="category-tabs" data-category-filter>
          <button class="is-active" type="button" data-category="all">Semua</button>
          ${categoryNames.map((categoryName) => `<button type="button" data-category="${escapeHtml(categoryName)}">${escapeHtml(categoryName)}</button>`).join('')}
        </div>
      </section>

      <section id="popular" class="section-frame product-section">
        <div class="section-title product-title" data-reveal>
          <span class="section-label">POPULAR NOW</span>
          <h2>Produk paling sering dibuka.</h2>
          <a class="button-ghost" href="#catalog">Lihat semua</a>
        </div>
        <div class="popular-grid">
          ${popular.map((product) => popularCard(product)).join('')}
        </div>
      </section>

      <section id="catalog" class="section-frame product-section">
        <div class="section-title product-title" data-reveal>
          <span class="section-label">PRODUCT DATABASE</span>
          <h2>Daftar Produk</h2>
          <p>Harga final tampil sebelum lanjut order.</p>
        </div>
        ${categoryNames
          .map((categoryName) => {
            const categoryProducts = sortProducts(catalog[categoryName]?.products ?? [])

            return `
              <div class="category-group" data-category-group="${escapeHtml(categoryName)}">
                <h3 data-reveal>${escapeHtml(categoryName)}</h3>
                <div class="product-list">
                  ${categoryProducts.map((product) => productItem(product, categoryName)).join('')}
                </div>
              </div>
            `
          })
          .join('')}
      </section>

      <section id="help" class="section-frame final-panel">
        <div data-reveal>
          <span class="section-label">SUPPORT HANDOFF</span>
          <h2>Bantuan order tetap lewat ticket.</h2>
          <p>Untuk pembelian, kendala pembayaran, atau pertanyaan produk, lanjutkan melalui ticket Discord Vercettia Store.</p>
        </div>
        <a class="button-pill" href="#catalog" data-reveal>Pilih produk</a>
      </section>
    </main>

    <footer class="site-footer">
      <strong>Vercettia Store</strong>
      <span>Blueprint marketplace / QRIS checkout / Ticket support</span>
    </footer>
  `
}

function setupLogoFallbacks() {
  document.querySelectorAll<HTMLImageElement>('[data-logo-image]').forEach((image) => {
    image.addEventListener('error', () => {
      image.remove()
    })
  })
}

function setupCatalogFilter() {
  const searchInput = document.querySelector<HTMLInputElement>('[data-product-search]')
  const categoryButtons = document.querySelectorAll<HTMLButtonElement>('[data-category-filter] button')
  const productCards = document.querySelectorAll<HTMLElement>('[data-product-card]')
  const categoryGroups = document.querySelectorAll<HTMLElement>('[data-category-group]')
  const hideTimers = new WeakMap<HTMLElement, number>()
  let activeCategory = 'all'

  function showCard(card: HTMLElement) {
    const timer = hideTimers.get(card)

    if (timer) {
      window.clearTimeout(timer)
    }

    card.classList.remove('is-hidden')
    requestAnimationFrame(() => card.classList.remove('is-filtered-out'))
  }

  function hideCard(card: HTMLElement) {
    card.classList.add('is-filtered-out')
    hideTimers.set(
      card,
      window.setTimeout(() => {
        card.classList.add('is-hidden')
      }, 180),
    )
  }

  function applyCatalogFilter() {
    const query = searchInput?.value.trim().toLowerCase() ?? ''

    productCards.forEach((card) => {
      const name = card.dataset.name ?? ''
      const category = card.dataset.category ?? ''
      const categoryMatch = activeCategory === 'all' || category === activeCategory
      const queryMatch = !query || name.includes(query)
      const isMatch = categoryMatch && queryMatch
      card.dataset.filterMatch = isMatch ? 'true' : 'false'

      if (isMatch) {
        showCard(card)
      } else {
        hideCard(card)
      }
    })

    categoryGroups.forEach((group) => {
      const visibleCards = group.querySelectorAll('[data-product-card][data-filter-match="true"]')
      group.classList.toggle('is-hidden', visibleCards.length === 0)
    })
  }

  searchInput?.addEventListener('input', applyCatalogFilter)

  categoryButtons.forEach((button) => {
    button.addEventListener('click', () => {
      activeCategory = button.dataset.category ?? 'all'
      categoryButtons.forEach((item) => item.classList.toggle('is-active', item === button))
      applyCatalogFilter()
    })
  })
}

function setupRevealAnimations() {
  const revealElements = document.querySelectorAll<HTMLElement>('[data-reveal]')
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        entry.target.classList.toggle('is-visible', entry.isIntersecting)
        entry.target.classList.toggle('is-out', !entry.isIntersecting)
      })
    },
    {
      rootMargin: '-8% 0px -8% 0px',
      threshold: 0.12,
    },
  )

  revealElements.forEach((element, index) => {
    element.style.setProperty('--reveal-delay', `${Math.min(index % 6, 5) * 55}ms`)
    observer.observe(element)
  })
}

async function bootstrap() {
  if (!appRoot) {
    return
  }

  try {
    const response = await fetch('/api/v1/products', {
      headers: {
        Accept: 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error('Catalog request failed')
    }

    const payload = (await response.json()) as ProductResponse
    renderApp(payload.data)
    setupLogoFallbacks()
    setupCatalogFilter()
    setupRevealAnimations()
    document.body.classList.add('app-ready')
  } catch {
    appRoot.innerHTML = `
      <main class="page-wrap">
        <section class="section-frame final-panel is-visible">
          <div>
            <span class="section-label">CATALOG ERROR</span>
            <h2>Katalog belum bisa dimuat.</h2>
            <p>Jalankan server Laravel dan pastikan endpoint API produk aktif.</p>
          </div>
        </section>
      </main>
    `
  }
}

bootstrap()
