import { describe, expect, it } from 'vitest'

import { routeFromPath } from '../routing'

describe('routeFromPath', () => {
  it('sends the root at the game', () => {
    expect(routeFromPath('/')).toEqual({ kind: 'game' })
    expect(routeFromPath('')).toEqual({ kind: 'game' })
  })

  it('recognises the admin page', () => {
    expect(routeFromPath('/admin')).toEqual({ kind: 'admin' })
    expect(routeFromPath('/admin/')).toEqual({ kind: 'admin' })
  })

  it('reads a friend name', () => {
    expect(routeFromPath('/alex')).toEqual({ kind: 'friend', name: 'alex' })
    expect(routeFromPath('/sam-2')).toEqual({ kind: 'friend', name: 'sam-2' })
  })

  it('never treats a reserved word as a friend', () => {
    // "admin" is the one that would actually bite: it is a real path.
    for (const reserved of ['api', 'static', 'assets', 'icons']) {
      expect(routeFromPath(`/${reserved}`)).toEqual({ kind: 'game' })
    }
  })

  it('falls back to the game for anything malformed', () => {
    expect(routeFromPath('/Not A Name')).toEqual({ kind: 'game' })
    expect(routeFromPath('/-leading-dash')).toEqual({ kind: 'game' })
    expect(routeFromPath('/a'.repeat(80))).toEqual({ kind: 'game' })
  })
})
