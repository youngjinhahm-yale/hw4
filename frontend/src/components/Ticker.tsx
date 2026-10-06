const ITEMS = [
  'Beat Harvard',
  'Officially licensed Yale apparel',
  'Bulldogs! Bulldogs! Bow wow wow!',
  'Made to order in New Haven',
  'Returns on unworn items within 30 days',
  'Boola boola',
]

/** Scrolling stadium-style ticker under the nav (pauses on hover, static with reduced motion). */
export default function Ticker() {
  const row = ITEMS.map((t, i) => (
    <span key={i} className="ticker-item">
      {t}
      <span className="ticker-dot" aria-hidden="true">
        ◆
      </span>
    </span>
  ))
  return (
    <div className="ticker" aria-label={ITEMS.join('. ')}>
      <div className="ticker-track" aria-hidden="true">
        {row}
        {row}
      </div>
    </div>
  )
}
