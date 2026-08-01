import { useCallback, useState } from 'react'

import type { Prize } from './Overlay'

/**
 * Walks a queue of prizes one at a time.
 *
 * The queue only ever comes from a server response. Nothing here decides how
 * many prizes there are or what they contain — if this invented a count, the
 * animation would stop matching what the player actually received.
 */
export function useReveal() {
  const [queue, setQueue] = useState<Prize[]>([])
  const [index, setIndex] = useState(0)

  const show = useCallback((prizes: Prize[]) => {
    // An empty payout is not worth a full-screen interruption.
    if (prizes.length === 0) return
    setQueue(prizes)
    setIndex(0)
  }, [])

  const advance = useCallback(() => {
    setIndex((current) => {
      const next = current + 1
      if (next >= queue.length) {
        setQueue([])
        return 0
      }
      return next
    })
  }, [queue.length])

  const skip = useCallback(() => {
    setQueue([])
    setIndex(0)
  }, [])

  return { queue, index, showing: queue.length > 0, show, advance, skip }
}
