import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { relativeTime } from '../ui/relativeTime'
import { useReveal } from '../ui/useReveal'
import type { Prize } from '../ui/Overlay'

const prize = (title: string): Prize => ({ image: `/icons/${title}.png`, title })

describe('useReveal', () => {
  it('walks the queue one prize at a time', () => {
    const { result } = renderHook(() => useReveal())

    act(() => result.current.show([prize('a'), prize('b'), prize('c')]))
    expect(result.current.showing).toBe(true)
    expect(result.current.index).toBe(0)

    act(() => result.current.advance())
    expect(result.current.index).toBe(1)

    act(() => result.current.advance())
    expect(result.current.index).toBe(2)

    // Advancing past the last one closes it rather than overflowing.
    act(() => result.current.advance())
    expect(result.current.showing).toBe(false)
  })

  it('preserves the order the server sent', () => {
    const { result } = renderHook(() => useReveal())
    act(() => result.current.show([prize('fire'), prize('earth'), prize('space')]))

    expect(result.current.queue.map((p) => p.title)).toEqual(['fire', 'earth', 'space'])
  })

  it('skips the whole queue at once', () => {
    const { result } = renderHook(() => useReveal())

    act(() => result.current.show([prize('a'), prize('b'), prize('c')]))
    act(() => result.current.skip())

    expect(result.current.showing).toBe(false)
    expect(result.current.index).toBe(0)
  })

  it('does not interrupt for an empty payout', () => {
    // A task can be valued at zero fragments; a full-screen overlay saying
    // "you got nothing" would be worse than saying nothing at all.
    const { result } = renderHook(() => useReveal())

    act(() => result.current.show([]))

    expect(result.current.showing).toBe(false)
  })

  it('reopens cleanly after a previous reveal finished', () => {
    const { result } = renderHook(() => useReveal())

    act(() => result.current.show([prize('a')]))
    act(() => result.current.advance())
    expect(result.current.showing).toBe(false)

    act(() => result.current.show([prize('b'), prize('c')]))
    expect(result.current.index).toBe(0)
    expect(result.current.queue).toHaveLength(2)
  })
})

describe('relativeTime', () => {
  const now = new Date('2026-08-01T12:00:00Z')
  const ago = (ms: number) => new Date(now.getTime() - ms).toISOString()

  const SECOND = 1000
  const MINUTE = 60 * SECOND
  const HOUR = 60 * MINUTE
  const DAY = 24 * HOUR

  it('reads elapsed time while that is still useful', () => {
    expect(relativeTime(ago(5 * SECOND), now)).toBe('just now')
    expect(relativeTime(ago(60 * SECOND), now)).toBe('a minute ago')
    expect(relativeTime(ago(20 * MINUTE), now)).toBe('20 minutes ago')
    expect(relativeTime(ago(1 * HOUR), now)).toBe('an hour ago')
    expect(relativeTime(ago(5 * HOUR), now)).toBe('5 hours ago')
    expect(relativeTime(ago(1 * DAY), now)).toBe('yesterday')
    expect(relativeTime(ago(3 * DAY), now)).toBe('3 days ago')
  })

  it('switches to a date once counting days stops helping', () => {
    // "13 days ago" makes you do arithmetic; a date does not.
    const old = relativeTime(ago(30 * DAY), now)
    expect(old).not.toMatch(/ago/)
    expect(old).toMatch(/\d/)
  })

  it('survives a clock that is slightly ahead', () => {
    const future = new Date(now.getTime() + 5 * SECOND).toISOString()
    expect(relativeTime(future, now)).toBe('just now')
  })

  it('returns nothing for an unparseable timestamp', () => {
    expect(relativeTime('not a date')).toBe('')
  })
})
