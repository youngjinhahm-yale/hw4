import { Link } from 'react-router-dom'
import { LOW_STOCK, SIZES, formatPrice, shortDescription, type Product } from '../api'

const FEW_SIZES = 3 // badge items with this many sizes or fewer still in stock
const LOW_TOTAL = 20 // ...or this many units or fewer across all sizes

/**
 * Live-inventory badge, shown only when it matters (about 1 in 4 items), so it stays a
 * real signal. With a size filter on, it speaks about the shopper's own size.
 */
function stockBadge(product: Product, size?: string): { text: string; tone: 'out' | 'low' } | null {
  if (product.total_stock === 0) return { text: 'Sold out', tone: 'out' }
  if (size) {
    const qty = product.stock[size] ?? 0
    if (qty === 0) return { text: `Sold out in ${size}`, tone: 'out' }
    return qty <= LOW_STOCK ? { text: `Only ${qty} left in ${size}`, tone: 'low' } : null
  }
  const inStock = SIZES.filter((s) => (product.stock[s] ?? 0) > 0)
  if (inStock.length <= FEW_SIZES) return { text: `Only ${inStock.join(', ')} left`, tone: 'low' }
  if (product.total_stock <= LOW_TOTAL) return { text: 'Low stock', tone: 'low' }
  return null
}

export default function ProductCard({ product, size }: { product: Product; size?: string }) {
  const badge = stockBadge(product, size)
  const isRivalry = /harvard|the game/i.test(product.name + ' ' + product.description)
  return (
    <Link to={`/products/${product.product_id}`} className="card">
      <div className="card-image">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        {badge && <span className={`badge badge-${badge.tone}`}>{badge.text}</span>}
        {isRivalry && <span className="badge badge-rival">The Game</span>}
        <span className="card-cta" aria-hidden="true">
          View details →
        </span>
      </div>
      <div className="card-body">
        <p className="card-type">{product.garment_type}</p>
        <h3 className="card-name">{product.name}</h3>
        <p className="card-desc">{shortDescription(product.description)}</p>
        <div className="card-foot">
          <p className="card-price">{formatPrice(product.price)}</p>
          {/* Size availability at a glance: filled = in stock, struck = sold out */}
          <ul className="size-dots" aria-label="Sizes in stock">
            {SIZES.map((s) => {
              const qty = product.stock[s] ?? 0
              return (
                <li
                  key={s}
                  className={qty === 0 ? 'dot-out' : qty <= LOW_STOCK ? 'dot-low' : 'dot-in'}
                  title={qty === 0 ? `${s}: sold out` : `${s}: ${qty} in stock`}
                >
                  {s}
                </li>
              )
            })}
          </ul>
        </div>
      </div>
    </Link>
  )
}
