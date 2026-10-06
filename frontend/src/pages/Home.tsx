import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CATEGORIES, fetchProducts, type Product } from '../api'
import GameCountdown from '../components/GameCountdown'
import ProductCard from '../components/ProductCard'
import { useReveal } from '../useReveal'

// Rivalry-ready pieces from the catalogue, shown as a curated "kit".
const GAME_DAY_KIT = [
  '2025-yale-vs-harvard-t-shirt',
  'ua-gameday-double-knit-hood',
  'district-vit-crewneck-vintage-standing-bulldog',
  'district-vit-hoodie-vintage-bulldog',
]
const FAN_FAVORITES = [
  'basic-hoodie-big-yale',
  'champion-reverse-weave-crewneck',
  'brooks-brothers-bomber-jacket-yale',
  'boola-boola-t-shirt',
]
const COLLEGES = [
  'Benjamin Franklin', 'Berkeley', 'Branford', 'Davenport', 'Ezra Stiles', 'Grace Hopper',
  'Jonathan Edwards', 'Morse', 'Pauli Murray', 'Pierson', 'Saybrook', 'Silliman',
  'Timothy Dwight', 'Trumbull',
]

export default function Home() {
  const [products, setProducts] = useState<Product[]>([])

  useEffect(() => {
    fetchProducts().then(setProducts).catch(() => setProducts([]))
  }, [])
  useReveal([products.length])

  const pick = (ids: string[]) =>
    ids.map((id) => products.find((p) => p.product_id === id)).filter((p): p is Product => Boolean(p))
  const categoryImage = (match: (t: string) => boolean) =>
    products.find((p) => match(p.garment_type))?.image_url
  // Only show colleges we actually carry, with live item counts.
  const colleges = COLLEGES.map((name) => ({
    name,
    count: products.filter((p) => p.name.toLowerCase().includes(name.toLowerCase())).length,
  })).filter((c) => c.count > 0)

  return (
    <>
      <section className="hero">
        <div className="hero-field" aria-hidden="true" />
        <div className="hero-text">
          <p className="eyebrow">
            <span className="eyebrow-dot" /> The Game · Yale vs Harvard
          </p>
          <h1 className="hero-title">
            <span className="hero-line">Beat</span>
            <span className="hero-line hero-line-rival">Harvard.</span>
          </h1>
          <p className="hero-sub">
            Dress the part in Bulldog blue: officially licensed Yale gear, made to order a few
            blocks from Old Campus.
          </p>
          <div className="hero-actions">
            <Link to="/products?q=Harvard" className="btn btn-light btn-lg">
              Shop The Game
            </Link>
            <Link to="/products" className="btn btn-outline-light btn-lg">
              Shop all Yale
            </Link>
          </div>
          <p className="hero-motto">Lux et veritas · New Haven, CT</p>
        </div>
        <div className="hero-visual">
          <GameCountdown />
          <Link to="/products/2025-yale-vs-harvard-t-shirt" className="hero-jersey" aria-label="2025 Yale vs Harvard T-shirt">
            <img src="/images/2025-yale-vs-harvard-t-shirt.jpg" alt="" />
            <span className="hero-jersey-tag">The 2025 Game tee · $32</span>
          </Link>
        </div>
      </section>

      <section className="section reveal">
        <div className="section-head">
          <div>
            <p className="kicker">Kickoff ready</p>
            <h2 className="section-title">The Game Day Kit</h2>
          </div>
          <Link to="/products?q=Harvard" className="link-arrow">
            Shop rivalry gear
          </Link>
        </div>
        <div className="grid grid-feature">
          {pick(GAME_DAY_KIT).map((p) => (
            <ProductCard key={p.product_id} product={p} />
          ))}
        </div>
      </section>

      <section className="section reveal">
        <p className="kicker">Find your fit</p>
        <h2 className="section-title">Shop by category</h2>
        <div className="categories">
          {CATEGORIES.filter((c) => c.key !== 'other').map((c, i) => (
            <Link
              key={c.key}
              to={`/products?category=${c.key}`}
              className="category"
              style={{ animationDelay: `${i * 70}ms` }}
            >
              {categoryImage(c.match) && <img src={categoryImage(c.match)} alt="" />}
              <span>{c.label}</span>
            </Link>
          ))}
        </div>
      </section>

      {colleges.length > 0 && (
        <section className="colleges reveal">
          <div className="colleges-inner">
            <div>
              <p className="kicker kicker-light">Residential colleges</p>
              <h2 className="section-title section-title-light">Rep your college</h2>
              <p className="colleges-sub">Crests, quarter-zips and crewnecks for the house you call home.</p>
            </div>
            <div className="pennants">
              {colleges.map((c) => (
                <Link key={c.name} to={`/products?q=${encodeURIComponent(c.name)}`} className="pennant">
                  <span className="pennant-name">{c.name}</span>
                  <span className="pennant-count">{c.count}</span>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="section reveal">
        <div className="section-head">
          <div>
            <p className="kicker">Bulldog staples</p>
            <h2 className="section-title">Fan favorites</h2>
          </div>
          <Link to="/products" className="link-arrow">
            View all
          </Link>
        </div>
        <div className="grid">
          {pick(FAN_FAVORITES).map((p) => (
            <ProductCard key={p.product_id} product={p} />
          ))}
        </div>
      </section>

      <section className="perks reveal">
        <div>
          <span className="perk-icon" aria-hidden="true">🛡️</span>
          <h3>Officially licensed</h3>
          <p>Real Yale marks, approved by the university. No knockoffs here.</p>
        </div>
        <div>
          <span className="perk-icon" aria-hidden="true">🧵</span>
          <h3>Made to order</h3>
          <p>Most pieces are produced within 5–8 business days and ship by UPS.</p>
        </div>
        <div>
          <span className="perk-icon" aria-hidden="true">↩️</span>
          <h3>Easy returns</h3>
          <p>Changed your mind? Send unworn items back with tags within 30 days.</p>
        </div>
        <div>
          <span className="perk-icon" aria-hidden="true">🐶</span>
          <h3>Ask Dan</h3>
          <p>Our chat bulldog checks live sizes and stock for you, any time.</p>
        </div>
      </section>
    </>
  )
}
