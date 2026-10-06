import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { CATEGORIES, SIZES, fetchProducts, type Product } from '../api'
import ProductCard from '../components/ProductCard'

const SORTS = {
  featured: { label: 'Featured (A–Z)', compare: (a: Product, b: Product) => a.name.localeCompare(b.name) },
  'price-asc': { label: 'Price: low → high', compare: (a: Product, b: Product) => a.price - b.price || a.name.localeCompare(b.name) },
  'price-desc': { label: 'Price: high → low', compare: (a: Product, b: Product) => b.price - a.price || a.name.localeCompare(b.name) },
} as const
type SortKey = keyof typeof SORTS

export default function Products() {
  const [params, setParams] = useSearchParams()
  const category = params.get('category') ?? 'all'
  const q = params.get('q') ?? ''
  const size = params.get('size') ?? ''
  const sort = (params.get('sort') ?? 'featured') as SortKey
  const [search, setSearch] = useState(q)
  const [products, setProducts] = useState<Product[] | null>(null)
  const [error, setError] = useState(false)

  // Keyword and size filtering happen on the server (size uses live inventory).
  useEffect(() => {
    setError(false)
    fetchProducts(q || undefined, size || undefined)
      .then(setProducts)
      .catch(() => setError(true))
  }, [q, size])

  const visible = useMemo(() => {
    const cat = CATEGORIES.find((c) => c.key === category)
    const compare = (SORTS[sort] ?? SORTS.featured).compare
    return (products ?? []).filter((p) => !cat || cat.match(p.garment_type)).sort(compare)
  }, [products, category, sort])

  function update(next: Record<string, string>) {
    const p = new URLSearchParams(params)
    for (const [k, v] of Object.entries(next)) {
      if (v && v !== 'all' && !(k === 'sort' && v === 'featured')) p.set(k, v)
      else p.delete(k)
    }
    setParams(p)
  }

  return (
    <section className="section">
      <h1 className="page-title">Shop Yale apparel</h1>
      <form
        className="search"
        onSubmit={(e) => {
          e.preventDefault()
          update({ q: search.trim() })
        }}
      >
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search hoodies, colleges, colors…"
          aria-label="Search products"
        />
        <button className="btn" type="submit">
          Search
        </button>
      </form>
      <div className="chips">
        {[{ key: 'all', label: 'All' }, ...CATEGORIES].map((c) => (
          <button
            key={c.key}
            className={`chip ${category === c.key ? 'chip-active' : ''}`}
            onClick={() => update({ category: c.key })}
          >
            {c.label}
          </button>
        ))}
      </div>

      <div className="toolbar">
        <div className="size-filter" role="group" aria-label="In stock in size">
          <span className="toolbar-label">In stock in size</span>
          <button className={`chip chip-small ${!size ? 'chip-active' : ''}`} onClick={() => update({ size: '' })}>
            Any
          </button>
          {SIZES.map((s) => (
            <button
              key={s}
              className={`chip chip-small ${size === s ? 'chip-active' : ''}`}
              onClick={() => update({ size: size === s ? '' : s })}
              aria-pressed={size === s}
            >
              {s}
            </button>
          ))}
        </div>
        <label className="sort">
          <span className="toolbar-label">Sort</span>
          <select value={sort} onChange={(e) => update({ sort: e.target.value })} aria-label="Sort products">
            {Object.entries(SORTS).map(([key, s]) => (
              <option key={key} value={key}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && <p className="notice">We couldn't load products. Is the backend running?</p>}
      {!error && products === null && <p className="notice">Loading products…</p>}
      {products !== null && (
        <p className="result-count">
          {visible.length} {visible.length === 1 ? 'item' : 'items'}
          {q && <> for “{q}”</>}
          {size && <> in stock in size {size}</>}
        </p>
      )}
      <div className="grid">
        {visible.map((p) => (
          <ProductCard key={p.product_id} product={p} size={size || undefined} />
        ))}
      </div>
    </section>
  )
}
