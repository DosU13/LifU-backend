/**
 * "a minute ago" for recent things, a plain date once that stops being useful.
 *
 * The cutover is deliberate: "13 days ago" makes you do arithmetic, while a
 * date does not. Anything inside a week reads better as elapsed time.
 */
export function relativeTime(iso: string, now: Date = new Date()): string {
  const then = new Date(iso)
  if (Number.isNaN(then.getTime())) return ''

  const seconds = Math.floor((now.getTime() - then.getTime()) / 1000)

  // Clock skew, or a task logged a moment ago on a slightly fast server.
  if (seconds < 45) return 'just now'
  if (seconds < 90) return 'a minute ago'

  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} minutes ago`

  const hours = Math.round(minutes / 60)
  if (hours === 1) return 'an hour ago'
  if (hours < 24) return `${hours} hours ago`

  const days = Math.round(hours / 24)
  if (days === 1) return 'yesterday'
  if (days < 7) return `${days} days ago`

  return then.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}
