import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useChatResults } from '../chatResults'
import ProductCard from './ProductCard'

/**
 * Renders the chat agent's product matches on the page as regular product cards.
 * Cards use the same <ProductCard> as the Products page, so clicking one opens the
 * single-item page. The panel collapses (but stays available) after navigating.
 */
export default function ChatResultsPanel() {
  const { results, clear } = useChatResults()
  const [collapsed, setCollapsed] = useState(false)
  const panelRef = useRef<HTMLElement>(null)
  const location = useLocation()
  const shownAt = useRef(location.key)

  // New results: open the panel and bring it into view.
  useEffect(() => {
    if (!results) return
    setCollapsed(false)
    shownAt.current = location.key
    // Wait a tick: inserting the panel above the viewport makes the browser's scroll
    // anchoring shift the page, which would cancel a scroll started right away.
    // Smooth scrolling needs a visible tab, so fall back to an instant jump otherwise.
    const timer = setTimeout(() => {
      panelRef.current?.scrollIntoView({
        behavior: document.hidden ? 'auto' : 'smooth',
        block: 'start',
      })
    }, 50)
    return () => clearTimeout(timer)
  }, [results?.id])

  // Navigated somewhere else (e.g. clicked a card): fold the panel so the page is visible.
  useEffect(() => {
    if (results && location.key !== shownAt.current) setCollapsed(true)
  }, [location.key])

  if (!results) return null
  const count = results.products.length

  return (
    <section ref={panelRef} className="chat-results" aria-label="Products from chat" data-results-id={results.id}>
      <div className="chat-results-head">
        <div>
          <p className="chat-results-eyebrow">💬 Found by our chat assistant</p>
          <h2 className="chat-results-title">
            {results.title} <span>{count} {count === 1 ? 'item' : 'items'}</span>
          </h2>
        </div>
        <div className="chat-results-actions">
          <button className="btn btn-small btn-outline" onClick={() => setCollapsed((c) => !c)}>
            {collapsed ? 'Show' : 'Hide'}
          </button>
          <button className="btn btn-small btn-outline" onClick={clear} aria-label="Clear chat results">
            Clear
          </button>
        </div>
      </div>
      {!collapsed && (
        <div className="grid chat-results-grid">
          {results.products.map((p) => (
            <ProductCard key={p.product_id} product={p} />
          ))}
        </div>
      )}
    </section>
  )
}
