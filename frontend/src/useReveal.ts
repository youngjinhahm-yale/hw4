import { useEffect } from 'react'

const SAFETY_MS = 2500 // content must never stay hidden, whatever the browser does

/**
 * Fade/slide elements with class "reveal" into view as they scroll on screen.
 * Re-scans when `deps` change (new page or new data). Fail-safe: anything already
 * on screen shows at once, and everything shows after SAFETY_MS even if the
 * observer never fires (old browsers, background tabs). Reduced-motion users see
 * everything immediately (handled in CSS).
 */
export function useReveal(deps: unknown[] = []) {
  useEffect(() => {
    const els = [...document.querySelectorAll<HTMLElement>('.reveal:not(.is-visible)')]
    const show = (el: Element) => el.classList.add('is-visible')
    const onScreen = (el: Element) => el.getBoundingClientRect().top < window.innerHeight * 0.95

    els.filter(onScreen).forEach(show)
    const safety = setTimeout(() => els.forEach(show), SAFETY_MS)
    if (!('IntersectionObserver' in window)) {
      els.forEach(show)
      return () => clearTimeout(safety)
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            show(e.target)
            io.unobserve(e.target)
          }
        }
      },
      { rootMargin: '0px 0px -8% 0px', threshold: 0.08 },
    )
    els.forEach((el) => io.observe(el))
    return () => {
      io.disconnect()
      clearTimeout(safety)
    }
  }, deps)
}
