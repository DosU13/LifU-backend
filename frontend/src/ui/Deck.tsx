import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'

import './deck.css'

/**
 * The root page: one scroll container that snaps between full-height layouts.
 *
 * `scroll-snap-stop: always` is the part that makes it feel magnetic rather
 * than merely snappy — without it a fast flick sails past a layout entirely.
 */

interface DeckProps {
  sections: { id: string; label: string; node: ReactNode }[]
}

export function Deck({ sections }: DeckProps) {
  const deckRef = useRef<HTMLElement>(null)
  const [active, setActive] = useState(0)

  useEffect(() => {
    const deck = deckRef.current
    if (!deck) return

    // Which layout is showing is read from scroll position rather than tracked
    // separately, so a wheel, a keypress and a rail click cannot disagree.
    function onScroll() {
      if (!deck) return
      setActive(Math.round(deck.scrollTop / deck.clientHeight))
    }

    deck.addEventListener('scroll', onScroll, { passive: true })
    return () => deck.removeEventListener('scroll', onScroll)
  }, [])

  function goTo(index: number) {
    const deck = deckRef.current
    if (!deck) return
    deck.scrollTo({ top: deck.clientHeight * index, behavior: 'smooth' })
  }

  return (
    <>
      <nav className="rail" aria-label="Sections">
        {sections.map((section, index) => (
          <button
            key={section.id}
            type="button"
            className={index === active ? 'on' : undefined}
            aria-label={section.label}
            aria-current={index === active ? 'true' : undefined}
            onClick={() => goTo(index)}
          />
        ))}
      </nav>

      <main className="deck" ref={deckRef}>
        {sections.map((section) => (
          <section key={section.id} id={section.id} className="layout" aria-label={section.label}>
            {section.node}
          </section>
        ))}
      </main>
    </>
  )
}
