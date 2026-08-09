import type { ReactNode } from 'react'

import { DOSHA_INFO } from '../domain'
import type { Dosha } from '../domain'
import { collectableIcon } from '../ui/Icon'
import type { Element } from '../types'

/**
 * The book's content, kept separate from the machinery that turns its pages
 * (Codex.tsx). Each entry is one spread — a left page and a right page — and
 * adding lore later (the ten combined elements, Harmony, the virtues) is
 * exactly one more entry here, nothing in Codex.tsx has to change.
 *
 * `left`/`right` are content only: no outer `.page` div, no folio number, no
 * edge-click hitbox. Codex.tsx supplies that furniture uniformly so every
 * spread looks like it belongs to the same book.
 */
export interface Spread {
  left: ReactNode
  right: ReactNode
}

/**
 * One row, reused for both the five classical elements and the ten combined
 * ones — only what goes in the italic gloss differs. A base element gets its
 * Sanskrit name; Harmony and the combined elements are not part of the
 * classical five, so they get what they are made from instead (still in the
 * same slot, same styling — the book does not flag the difference, it just
 * quietly stops pretending to a Sanskrit word that does not exist).
 */
function ElementEntry({ element, gloss, body }: { element: Element; gloss: string; body: string }) {
  return (
    <div className="element-row">
      <img src={collectableIcon(element, 'FRAGMENT')} alt="" width={40} height={40} />
      <div>
        <span className="name">
          {ELEMENT_NAME[element]} <span className="sanskrit">— {gloss}</span>
        </span>
        <p>{body}</p>
      </div>
    </div>
  )
}

const ELEMENT_NAME: Record<Element, string> = {
  SPACE: 'Space',
  AIR: 'Air',
  FIRE: 'Fire',
  WATER: 'Water',
  EARTH: 'Earth',
  HARMONY: 'Harmony',
  GROWTH: 'Growth',
  FORGE: 'Forge',
  DUST: 'Dust',
  MOUNTAIN: 'Mountain',
  STEAM: 'Steam',
  MIST: 'Mist',
  OCEAN: 'Ocean',
  LIGHTNING: 'Lightning',
  SUN: 'Sun',
  WIND: 'Wind',
}

function DoshaEntry({ dosha, tagline, body }: { dosha: Dosha; tagline: string; body: string }) {
  const info = DOSHA_INFO[dosha]
  return (
    <div className="dosha-entry">
      <div className="name">
        <span className="swatch" style={{ background: info.color }} aria-hidden="true" />
        {info.name} <span className="sanskrit">— {info.sanskrit}</span>
        <span style={{ color: '#8a7156', fontWeight: 400 }}> · {tagline}</span>
      </div>
      <p>{body}</p>
    </div>
  )
}

/**
 * @param constitutionCharts The two dosha pie charts, rendered by Codex.tsx
 *   (it owns the fetched task history the charts are built from) and slotted
 *   in here rather than fetched again — the book's content stays pure data
 *   everywhere except this one live figure.
 */
export function buildSpreads(constitutionCharts: ReactNode): Spread[] {
  return [
    // Spread I — frontispiece | the three gunas
    {
      left: (
        <>
          <h2>The Codex of Elements</h2>
          <div className="rule" />
          <p className="dropcap">
            What follows is set down from the oldest teachings on the substance of a mind and the
            substance of a world — five elements, three qualities that color how a mind moves
            through them, and three constitutions a body settles into from the mixing. This game
            borrows their names and, where it can, their honesty.
          </p>
          <p>
            Turn the page by hand, or let the two arrows below do it for you. Nothing here is
            required reading — the tasks and the treasures ask nothing of you that this book does
            not also give freely.
          </p>
        </>
      ),
      right: (
        <>
          <h2>The Three Qualities of Mind</h2>
          <div className="rule" />
          <p className="dropcap">
            <b>Sattva</b> is clarity: the quality of a mind that sees a thing plainly, acts without
            being pushed, and rests without needing to. The old texts call it light, not because it
            is easy, but because it carries no extra weight.
          </p>
          <p>
            <b>Rajas</b> is motion: ambition, restlessness, the itch that gets things done and just
            as easily gets things broken. A mind in Rajas is never quite still, for better and for
            worse — most days log in this book will have been written by it.
          </p>
          <p>
            <b>Tamas</b> is inertia: the pull toward rest, toward staying exactly as you are. Not an
            enemy — a fire needs banked coals as much as it needs sparks — but a mind that stays
            there too long stops being asked anything at all.
          </p>
        </>
      ),
    },

    // Spread II — the five elements
    {
      left: (
        <>
          <h2>The Five Elements</h2>
          <div className="rule" />
          <p style={{ marginBottom: 18 }}>
            Every task logged in this book is weighed and paid out in one of these — the oldest
            reckoning of what a world, and a person, are made from.
          </p>
          <ElementEntry
            element="SPACE"
            gloss="Akasha"
            body="The field everything else happens inside of. Where Awareness is paid: noticing before acting, the pause that makes room for the rest."
          />
          <ElementEntry
            element="AIR"
            gloss="Vayu"
            body="Movement without a fixed shape. Where Curiosity is paid: the reach toward something not yet understood, carried wherever it needs to go."
          />
        </>
      ),
      right: (
        <>
          <div style={{ height: 6 }} />
          <ElementEntry
            element="FIRE"
            gloss="Agni"
            body="Transformation by heat. Where Willpower is paid: the push that turns intention into something actually finished."
          />
          <ElementEntry
            element="WATER"
            gloss="Jala"
            body="Cohesion — what holds separate things together and lets them move as one. Where Compassion is paid, and the one element every dosha on the next page has some claim to."
          />
          <ElementEntry
            element="EARTH"
            gloss="Prithvi"
            body="Structure, mass, what stays. Where Discipline is paid: the ground a streak is actually built on."
          />
        </>
      ),
    },

    // Spread III — the three doshas | your constitution
    {
      left: (
        <>
          <h2>The Three Doshas</h2>
          <div className="rule" />
          <p style={{ marginBottom: 16 }}>
            Where the gunas color a mind, the doshas describe a constitution — the mix of elements
            a body and temperament actually settle into. Everyone carries all three; what varies is
            the proportion, and the proportion is what the page opposite tries to show you.
          </p>
          <DoshaEntry
            dosha="VATA"
            tagline="Space + Air"
            body="Movement and change. Quick to think, quick to tire; the dosha of ideas arriving faster than the body can follow them."
          />
          <DoshaEntry
            dosha="PITTA"
            tagline="Fire + Water"
            body="Transformation with direction. Sharp, driven, a little too willing to burn through something to finish it — heat given a channel to run in."
          />
          <DoshaEntry
            dosha="KAPHA"
            tagline="Earth + Water"
            body="Structure and steadiness. Slow to start and slower to quit; the dosha that shows up as the streak counter at the top of the ledger."
          />
        </>
      ),
      right: (
        <>
          <h2>Your Constitution</h2>
          <div className="rule" />
          <p style={{ marginBottom: 10, fontSize: 13 }}>
            Read from every task logged, not from what is currently in the vault — selling a
            fragment does not change what earned it.
          </p>
          {constitutionCharts}
        </>
      ),
    },

    // Spread IV — Harmony and combining | the first five combined elements
    {
      left: (
        <>
          <h2>Beyond the Five</h2>
          <div className="rule" />
          <p className="dropcap">
            Five elements answer for a day well spent. What follows is what a spent day is
            eventually turned into — the ten forms two elements take once they stop being kept
            separate, and the one substance nothing except patience is ever paid in.
          </p>
          <ElementEntry
            element="HARMONY"
            gloss="all five, at once"
            body="Not one of the five — what happens when they agree. One of each base element, the same rarity, merges into Harmony: a balance nothing pays you in directly, made on purpose, because everything on the next two pages is asking for some."
          />
          <h2 style={{ fontSize: 16, marginTop: 20 }}>On Combining</h2>
          <div className="rule" style={{ marginTop: 8 }} />
          <p style={{ fontSize: 13.5 }}>
            One of an element, one of another, one Harmony, all the same rarity — combined the way a
            recipe is combined, not the way an accident is. What comes out belongs to neither parent
            any more than a child belongs to only one.
          </p>
        </>
      ),
      right: (
        <>
          <div style={{ height: 6 }} />
          <ElementEntry
            element="GROWTH"
            gloss="Earth + Water"
            body="What holds together meets what stays, and something starts growing. A garden, a habit, a friendship kept up past the point it was easy — all of it answers to Growth. Unlocks Nurturing's receptacles, for whatever was kept alive."
          />
          <ElementEntry
            element="FORGE"
            gloss="Earth + Fire"
            body="Heat applied to something that holds its shape does not destroy it, it reshapes it — the particular violence a smith calls patience. Unlocks Determination's receptacles, for whatever got struck at until it stopped being able to break."
          />
          <ElementEntry
            element="DUST"
            gloss="Earth + Air"
            body="Structure worn thin enough to travel: a road, an idea passed hand to hand until nobody remembers who shaped it first. Ground the same way a mountain is, only smaller and willing to move. Unlocks Adaptability's receptacles."
          />
          <ElementEntry
            element="MOUNTAIN"
            gloss="Earth + Space"
            body="Structure given room enough to simply stand and be looked at — not doing, not moving, the oldest thing there is for what staying still can mean. Unlocks Presence's receptacles, for whatever a mind got paid for finally stopping."
          />
          <ElementEntry
            element="STEAM"
            gloss="Water + Fire"
            body="Cohesion undone by heat until it forgets its own shape — water becoming something closer to breath. The change healers refuse to call an ending or a beginning. Unlocks Transformation's receptacles."
          />
        </>
      ),
    },

    // Spread V — the remaining combined elements | receptacles and virtues
    {
      left: (
        <>
          <h2>The Combined Elements, Continued</h2>
          <div className="rule" />
          <ElementEntry
            element="MIST"
            gloss="Water + Air"
            body="Cohesion loosened just enough to travel on air, so a whole body of water can hang over a field without ever leaving it. Fishers would not speak of it — only that it had seen them first. Unlocks Reflection's receptacles."
          />
          <ElementEntry
            element="OCEAN"
            gloss="Water + Space"
            body="Cohesion given the whole of an open field to fill — not a river, not a lake, but the version of water old enough to have never once been troubled by weather above it. Unlocks Serenity's receptacles."
          />
          <ElementEntry
            element="LIGHTNING"
            gloss="Fire + Air"
            body="Heat moving fast enough to stop being fire at all. Struck once, and every later fire is said to have borrowed a little of that first spark. Unlocks Inspiration's receptacles."
          />
          <ElementEntry
            element="SUN"
            gloss="Fire + Space"
            body="Heat given the whole sky to keep — older than any calendar built to track it, and the reason a body still calls a good day warm even when the weather had nothing to do with it. Unlocks Vitality's receptacles."
          />
          <ElementEntry
            element="WIND"
            gloss="Air + Space"
            body="Movement with nowhere in particular it has to be — the wind a traveler is named for, gone again before the story about it finishes. Unlocks Freedom's receptacles, which ask nothing of whoever finally opens them."
          />
        </>
      ),
      right: (
        <>
          <h2>Receptacles &amp; Virtues</h2>
          <div className="rule" />
          <p className="dropcap">
            Every receptacle is a small locked promise — something someone wanted, sealed the moment
            it was written down, and forgotten about on purpose until the right key turns up. Pouch,
            Sack, Chest, Safe, Vault, Sanctum: six sizes of the same idea, each harder to earn than
            the last and harder still to guess the contents of.
          </p>
          <p>
            A key never opens a stranger's receptacle. Determination's answer only to Forge,
            Serenity's only to Ocean — which is the whole of what the last two pages were for:
            naming which combined element stands guard over which kind of wanting.
          </p>
          <p style={{ marginTop: 22, fontStyle: 'italic', color: '#7a5330', fontSize: 13 }}>
            Here the old text ends, for now. What is written above is complete as far as it goes;
            what comes after, should anything come after, will be added to these same pages — not a
            new book.
          </p>
        </>
      ),
    },
  ]
}
