import { useEffect, useState } from 'react'

/** The Game is traditionally played the Saturday before Thanksgiving (4th Thursday of Nov). */
function nextGameDay(now: Date): Date {
  for (const year of [now.getFullYear(), now.getFullYear() + 1]) {
    const nov1 = new Date(year, 10, 1)
    const firstThursday = 1 + ((4 - nov1.getDay() + 7) % 7)
    const kickoff = new Date(year, 10, firstThursday + 21 - 5, 12) // Thanksgiving - 5 days, noon
    if (kickoff.getTime() + 6 * 3600_000 > now.getTime()) return kickoff
  }
  return now
}

const pad = (n: number) => String(n).padStart(2, '0')

/** Scoreboard-style countdown: YALE vs HARVARD with days / hours / minutes to The Game. */
export default function GameCountdown() {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 30_000)
    return () => clearInterval(id)
  }, [])

  const game = nextGameDay(now)
  const ms = Math.max(0, game.getTime() - now.getTime())
  const days = Math.floor(ms / 86_400_000)
  const hours = Math.floor((ms % 86_400_000) / 3_600_000)
  const mins = Math.floor((ms % 3_600_000) / 60_000)
  const dateLabel = game.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })

  return (
    <div className="scoreboard" role="timer" aria-label={`${days} days until The Game, ${dateLabel}`}>
      <div className="scoreboard-teams">
        <span className="team team-yale">YALE</span>
        <span className="team-vs">vs</span>
        <span className="team team-harvard">HARVARD</span>
      </div>
      <div className="scoreboard-clock">
        <div>
          <strong>{days}</strong>
          <span>days</span>
        </div>
        <i>:</i>
        <div>
          <strong>{pad(hours)}</strong>
          <span>hrs</span>
        </div>
        <i>:</i>
        <div>
          <strong>{pad(mins)}</strong>
          <span>min</span>
        </div>
      </div>
      <p className="scoreboard-foot">Until The Game · {dateLabel}</p>
    </div>
  )
}
