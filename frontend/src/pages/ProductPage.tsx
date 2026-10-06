import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError, fetchProduct, formatPrice, type ProductDetail } from '../api'

export default function ProductPage() {
  const { productId = '' } = useParams()
  const [product, setProduct] = useState<ProductDetail | null>(null)
  const [status, setStatus] = useState<'loading' | 'ok' | 'missing' | 'error'>('loading')
  const [size, setSize] = useState<string | null>(null)

  useEffect(() => {
    setStatus('loading')
    setSize(null)
    fetchProduct(productId)
      .then((p) => {
        setProduct(p)
        setStatus('ok')
      })
      .catch((e) => setStatus(e instanceof ApiError && e.status === 404 ? 'missing' : 'error'))
  }, [productId])

  if (status === 'loading') return <p className="section notice">Loading…</p>
  if (status !== 'ok' || !product)
    return (
      <section className="section">
        <p className="notice">
          {status === 'missing' ? "We couldn't find that product." : "We couldn't load this product."}
        </p>
        <Link to="/products">← Back to all products</Link>
      </section>
    )

  const selected = product.sizes.find((s) => s.size === size)

  return (
    <section className="section">
      <Link to="/products" className="back-link">
        ← All products
      </Link>
      <div className="detail">
        {/* Hover to zoom: the image scales toward the cursor so shoppers can inspect prints and stitching. */}
        <div
          className="detail-image"
          onMouseMove={(e) => {
            const r = e.currentTarget.getBoundingClientRect()
            e.currentTarget.style.setProperty('--zx', `${((e.clientX - r.left) / r.width) * 100}%`)
            e.currentTarget.style.setProperty('--zy', `${((e.clientY - r.top) / r.height) * 100}%`)
          }}
        >
          <img src={product.image_url} alt={product.name} />
          <span className="zoom-hint" aria-hidden="true">
            Hover to zoom
          </span>
        </div>
        <div className="detail-info">
          <p className="card-type">
            {product.garment_type}
            {/harvard|the game/i.test(product.name + ' ' + product.description) && (
              <span className="badge-inline">The Game</span>
            )}
          </p>
          <h1>{product.name}</h1>
          <p className="detail-price">{formatPrice(product.price)}</p>
          <p className="detail-desc">{product.description}</p>

          <h3>Colors</h3>
          <p className="colors">{product.colors.join(', ')}</p>

          <h3>Size & stock</h3>
          <div className="sizes">
            {product.sizes.map((s) => (
              <button
                key={s.size}
                className={`size ${size === s.size ? 'size-active' : ''}`}
                disabled={s.quantity === 0}
                onClick={() => setSize(s.size)}
                title={s.quantity === 0 ? 'Sold out' : `${s.quantity} in stock`}
              >
                {s.size}
              </button>
            ))}
          </div>
          <p className="stock-note">
            {selected
              ? `${selected.quantity} in stock in size ${selected.size}.`
              : product.total_stock > 0
                ? 'Pick a size to see how many are left. Crossed-out sizes are sold out.'
                : 'This item is currently sold out in every size.'}
          </p>
          <table className="stock-table">
            <tbody>
              {product.sizes.map((s) => (
                <tr key={s.size}>
                  <td>{s.size}</td>
                  <td className={s.quantity === 0 ? 'sold-out' : ''}>
                    {s.quantity === 0 ? 'Sold out' : `${s.quantity} in stock`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="tags">
            {product.search_tags.map((t) => (
              <span key={t} className="tag">
                {t}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
