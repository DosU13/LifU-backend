import { useEffect, useState } from 'react'

import { api } from '../api'
import { useSessionStore } from '../state/session'

type Status = 'checking' | 'valid' | 'unknown'

/**
 * What a friend sees at lifu.doslan.com/{their-name}: an explanation of the
 * game and a way into a sandbox. Nothing here can reach the real save.
 */
export function FriendGate({ friendName }: { friendName: string }) {
  const [status, setStatus] = useState<Status>('checking')
  const [busy, setBusy] = useState(false)
  const startTrial = useSessionStore((s) => s.startTrial)
  const error = useSessionStore((s) => s.error)

  useEffect(() => {
    let cancelled = false
    void api
      .checkFriend(friendName)
      .then(({ valid }) => {
        if (!cancelled) setStatus(valid ? 'valid' : 'unknown')
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
      <main className="gate wide">
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
    <main className="gate wide">
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

      <button type="button" onClick={() => void onTry()} disabled={busy}>
        {busy ? 'Setting it up…' : 'Try it'}
      </button>
      {error && <p role="alert" className="error">{error}</p>}
    </main>
  )
}
