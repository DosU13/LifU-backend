/**
 * There is no router library here — three routes do not justify one.
 *
 *   /            the game
 *   /admin       rewards management
 *   /{name}      a friend's trial link
 *
 * `/admin` has to be matched before the friend pattern, or it reads as a
 * friend called "admin".
 */

export type Route =
  | { kind: 'game' }
  | { kind: 'admin' }
  | { kind: 'friend'; name: string }

/** Reserved words can never be friend names, whatever the backend allows. */
const RESERVED = new Set(['admin', 'api', 'static', 'assets', 'icons'])

const FRIEND_NAME = /^[a-z0-9][a-z0-9_-]{0,30}$/

export function routeFromPath(pathname: string = window.location.pathname): Route {
  const slug = pathname.replace(/^\/+|\/+$/g, '')

  if (slug === '') return { kind: 'game' }
  if (slug === 'admin') return { kind: 'admin' }
  if (RESERVED.has(slug)) return { kind: 'game' }
  if (FRIEND_NAME.test(slug)) return { kind: 'friend', name: slug }

  return { kind: 'game' }
}
