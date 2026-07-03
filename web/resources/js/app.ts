import Alpine from 'alpinejs'
import Lenis from 'lenis'

declare global {
  interface Window {
    Alpine: typeof Alpine
  }
}

window.Alpine = Alpine
Alpine.start()

const lenis = new Lenis({
  lerp: 0.1,
  wheelMultiplier: 0.9,
})

function raf(time: number) {
  lenis.raf(time)
  requestAnimationFrame(raf)
}

requestAnimationFrame(raf)

const searchInput = document.querySelector<HTMLInputElement>('[data-product-search]')
const categoryButtons = document.querySelectorAll<HTMLButtonElement>('[data-category-filter] button')
const productCards = document.querySelectorAll<HTMLElement>('[data-product-card]')
const categoryGroups = document.querySelectorAll<HTMLElement>('[data-category-group]')
let activeCategory = 'all'

function applyCatalogFilter() {
  const query = searchInput?.value.trim().toLowerCase() ?? ''

  productCards.forEach((card) => {
    const name = card.dataset.name ?? ''
    const category = card.dataset.category ?? ''
    const categoryMatch = activeCategory === 'all' || category === activeCategory
    const queryMatch = !query || name.includes(query)
    card.classList.toggle('is-hidden', !(categoryMatch && queryMatch))
  })

  categoryGroups.forEach((group) => {
    const visibleCards = group.querySelectorAll('[data-product-card]:not(.is-hidden)')
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
