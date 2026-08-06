import { useEffect, useState } from 'react'

import { api, ApiError } from '../api'
import { useSessionStore } from '../state/session'
import '../ui/composer.css'
import '../ui/gate.css'

type Status = 'checking' | 'valid' | 'unknown'

/**
 * What a friend sees at lifu.doslan.com/{their-name}: an explanation of the
 * game, a way into a sandbox, and a way to seal a gift straight into the
 * owner's real game with nobody in between — see GiftForm below.
 */
export function FriendGate({ friendName }: { friendName: string }) {
  const [status, setStatus] = useState<Status>('checking')
  const [hasGifted, setHasGifted] = useState(false)
  const [busy, setBusy] = useState(false)
  const startTrial = useSessionStore((s) => s.startTrial)
  const error = useSessionStore((s) => s.error)

  useEffect(() => {
    let cancelled = false
    void api
      .checkFriend(friendName)
      .then(({ valid, has_gifted }) => {
        if (cancelled) return
        setStatus(valid ? 'valid' : 'unknown')
        setHasGifted(has_gifted)
      })
      .catch(() => {
        if (!cancelled) setStatus('unknown')
      })
    return () => {
      cancelled = true
    }
  }, [friendName])

  if (status === 'checking') return <p className="muted centered">…</p>

  if (status === 'unknown') {
    return (
      <main className="gate wide panel">
        <h1>LifU</h1>
        <p className="muted">
          This link isn&apos;t one we recognise. Ask Doslan for your own — everyone gets a
          different one.
        </p>
      </main>
    )
  }

  async function onTry() {
    setBusy(true)
    await startTrial(friendName)
    setBusy(false)
  }

  return (
    <main className="gate wide panel">
      <h1>LifU</h1>
      <p className="lead">
        Hi {friendName} — this is a game Doslan built to make finishing things feel like
        something.
      </p>

      <ol className="explainer">
        <li>
          <strong>You describe something you did.</strong> It gets judged on how hard and how
          valuable it was, and on which qualities it called on — awareness, curiosity, willpower,
          compassion, discipline.
        </li>
        <li>
          <strong>You are paid in elements.</strong> A run pays fire and earth; a quiet morning
          pays space. Three of the same merge into something rarer, all the way up to a Core.
        </li>
        <li>
          <strong>Rewards get locked away.</strong> Things you want are sealed into receptacles.
          The better a reward is compared to your others, the rarer the container it lands in.
        </li>
        <li>
          <strong>You have to earn the key.</strong> Every receptacle opens with one exact
          collectable — a Safe of Serenity wants an Ocean Essence, and you have to craft it.
        </li>
      </ol>

      <p className="muted small">
        What you are about to open is a sandbox: your own copy, with some starting coins and
        collectables. Nothing you do touches Doslan&apos;s game, and reloading the page starts you
        over.
      </p>

      <button type="button" className="btn-primary" onClick={() => void onTry()} disabled={busy}>
        {busy ? 'Setting it up…' : 'Try it'}
      </button>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}

      <hr className="gate-divider" />

      <GiftSection
        friendName={friendName}
        hasGifted={hasGifted}
        onSent={() => setHasGifted(true)}
      />
    </main>
  )
}

/**
 * The direct-entry alternative to Doslan pasting a friend's message into the
 * admin composer's masked textarea: here nothing passes through him at all
 * before it's sealed. One gift per link — the backend refuses a second
 * attempt, and `hasGifted` (from the check-friend call) skips straight to
 * the confirmation state for a link that's already been used.
 */
function GiftSection({
  friendName,
  hasGifted,
  onSent,
}: {
  friendName: string
  hasGifted: boolean
  onSent: () => void
}) {
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [giftError, setGiftError] = useState<string | null>(null)

  if (hasGifted) {
    return (
      <div className="gift-section">
        <h2>Leave something to look forward to</h2>
        <p className="muted small">
          Sent — thank you. It stays sealed until Doslan earns the key.
        </p>
      </div>
    )
  }

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    const trimmed = text.trim()
    if (!trimmed || busy) return
    setBusy(true)
    setGiftError(null)
    try {
      await api.submitFriendGift(friendName, trimmed)
      onSent()
    } catch (err) {
      setGiftError(err instanceof ApiError ? err.message : 'Could not send that.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="gift-section">
      <h2>Or, leave something to look forward to</h2>
      <p className="muted small">
        Write a reward for Doslan — sealed away and locked behind a key he has to earn. He&apos;ll
        know it&apos;s from you, but not what it is, until he opens it.
      </p>
      <form className="composer" onSubmit={onSubmit}>
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={3}
          placeholder="Something worth working toward…"
          aria-label="A gift for Doslan"
        />
        <div className="composer-foot">
          <span className="hint">One gift per link — make it count.</span>
          <button type="submit" className="btn-primary" disabled={!text.trim() || busy}>
            {busy ? 'Sealing…' : 'Send it'}
          </button>
        </div>
      </form>
      {giftError && (
        <p role="alert" className="error">
          {giftError}
        </p>
      )}
    </div>
  )
}
