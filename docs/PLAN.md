# LifU — Implementation plan

One phase per session, in order. Every phase ends with: app runnable (`runserver` works), `python -m pytest` green, `ruff check` clean. Read [ARCHITECTURE.md](ARCHITECTURE.md) sections referenced in each phase before coding — all formulas live there, not here. Phases marked **★ HARD** need extra care; write the tests first there.

## Phase 1 — Backend scaffold
**Goal:** empty but running Django project with tooling.
**Create:** `backend/` — Django project `lifu`, app `api`, `pyproject.toml` (django, djangorestframework, drf-spectacular, firebase-admin, requests, pytest, pytest-django, ruff), `core/`, `repos/`, `services/`, `aiclients/`, `providers/` packages (empty `__init__`s), `.env.example`, settings reading env per ARCHITECTURE §11.
**Accept:** `GET /api/health` → `{"ok": true}`; swagger UI loads at `/api/docs`; pytest runs 1 trivial test; ruff clean.

## Phase 2 — Domain core (§2, §3, §4)
**Goal:** all enums, mappings, constants, entities, errors, Rng.
**Create:** `core/enums.py`, `core/mappings.py`, `core/constants.py`, `core/entities.py`, `core/errors.py`, `core/rng.py`, tests.
**Accept:** tests verify: 16 elements/6+6 rarities/5+10 virtues exact; every mapping table matches ARCHITECTURE §3 exactly (test the full tables, not samples); sell-price function reproduces the §4 table (12 cells); `core/` imports no Django/Firebase.

## Phase 3 — Repository interfaces + memory implementations (§6)
**Goal:** all 7 interfaces + full in-memory implementations + factory returning memory bundle.
**Create:** `repos/interfaces.py`, `repos/memory.py`, `repos/factory.py`, tests.
**Accept:** contract test class per interface run against memory impls: atomicity of `CollectableRepository.adjust` (all-or-nothing on insufficient stock), `WalletRepository.adjust` floor at 0, receptacle state filtering.

## Phase 4 — Firebase implementations (§6)
**Goal:** Firestore versions of all repositories behind the same contract tests.
**Create:** `repos/firebase.py`; factory gains `firebase` branch; Firestore layout per §6.
**Accept:** the Phase-3 contract tests are parametrized to also run against Firebase **when** `FIREBASE_CREDENTIALS` is set (skipped otherwise — CI/test default stays offline); `adjust` uses Firestore transactions; manual smoke: `REPO_BACKEND=firebase runserver` boots.

## Phase 5 — AI clients + validation pipeline (§8)
**Goal:** Groq client, Random client, Fake client, and the parse/clamp/retry pipeline.
**Create:** `aiclients/base.py`, `groq_client.py`, `random_client.py`, `fake.py`, `validation.py`, `prompts.py` (copy prompts from [AI_PROMPTS.md](AI_PROMPTS.md)), tests.
**Accept:** validation tests cover: valid response passes; out-of-range clamped (not retried); missing key / bad type / unparseable → retried with corrective message then `AIResponseInvalid`; Class filtered+deduped+truncated to 3, empty-after-filter retried; secret value ≤50 forced to 51. All with `FakeAIClient`; no network.

## Phase 6 — Task flow (§7.1, §7.7 stats)
**Goal:** complete a task end-to-end through the API.
**Create:** `services/task_service.py`, `services/stats_service.py`, `services/container.py` (memory-only wiring for now), `api` views/serializers/urls for POST `/api/tasks`, GET `/api/tasks`, GET `/api/stats`.
**Accept:** unit tests pin the fragment formula (incl. rounding-to-0 case and the Value-10/50% ≈2–3 example from §7.1); streak logic tested across TIMEZONE day boundary; API tests: happy path + 502 on AI failure.

## Phase 7 — Collectables: merge, harmony, combine, sell (§7.2, §7.3, §7.7)
**Goal:** full collectable economy.
**Create:** `services/merger_service.py`, `services/economy_service.py`, endpoints merge/harmony/combine/sell.
**Accept:** tests: 3→1 up-merge for base/harmony/combined, CORE rejected; harmony with `SeededRng` pins exact `extras` sequence and cap; combine consumes 1+1+1 and produces correct combined element for all 10 pairs; sell credits exact FE prices; insufficient stock → error, nothing mutated.

## Phase 8 — ★ HARD — Rewards + rarity recalculator (§7.4, §7.5 submit)
**Goal:** submit rewards (own + secret), recalculation engine.
**Create:** `services/rarity_service.py`, `services/reward_service.py` (submit only; open comes in Phase 9), endpoints POST `/api/rewards`, GET `/api/receptacles`.
**Why hard:** Hamilton apportionment edge cases, frozen-opened-slot interaction, deterministic ordering.
**Accept:** unit tests pin: N=1→1C, N=4→3C+1S, N=14→10C+3S+1V, N=40→27/9/3/1; tie-break (equal values → older wins rarer slot); opened receptacle at rank 1 consumes the Sanctum slot while keeping its frozen rarity; recalc idempotent; secret receptacle never leaks `reward_text` via any endpoint (explicit test).

## Phase 9 — ★ HARD — Treasures: generate, price, buy, pity, discard (§7.6, §7.5 open)
**Goal:** the whole treasure loop, including opening dropped receptacles.
**Create:** `services/treasure_service.py`, reward_service.open_receptacle, endpoints GET `/api/treasures`, buy, discard, POST `/api/receptacles/{id}/open`, GET `/api/state`.
**Why hard:** most intertwined logic — roll fall-through, per-treasure pity with fulfillability, regeneration, once-a-day discard, key consumption, recalc triggers. Use `SeededRng` to script exact roll sequences; use a `FakeProviders` stub for generated content (real providers are Phase 10).
**Accept:** tests pin: rarest-first roll order; tier hit with rarity absent falls through; Pouch fallback; pity fires at exact thresholds, Sanctum before Vault, unfulfillable pity keeps counting then fires; counters reset only on their rarity; price = max(1, ceil(avg)) recomputed after each drop; treasure empty → deleted + regenerated; discard blocked twice same day (TIMEZONE), contents back to IN_POOL; open consumes correct key (Safe of Serenity ⇒ Ocean Essence), missing key → `MISSING_KEY`, coins += value, recalc ran.

## Phase 10 — Content providers (§7.6 generated content)
**Goal:** live quote/fact/music/art fetching with fallback chain.
**Create:** `providers/base.py`, `quotes.py`, `art.py` (DeviantArt API), `music.py` (Jamendo), `fallback.py` (small local lists), wiring into treasure buys.
**Accept:** provider protocol tests with mocked HTTP (no live calls in tests); chain falls back on any exception/timeout and ultimately to local lists; generated receptacle stores `{kind,title,url,author,text}`; buy flow never crashes on provider failure.

## Phase 11 — Auth, friend links, trial mode (§6 factory, §9 trial)
**Goal:** owner password login; friend links; full trial sandbox.
**Create:** `api/auth.py` (login/logout, session), `api/trial.py` (token issue + resolution), friend endpoints, container wiring: owner session → firebase+Groq, trial token → per-token memory bundle (TTL 24 h) + RandomAIClient + seeded starter state (100 coins, 5 of each base fragment, 6 pool receptacles with varied values).
**Accept:** tests: wrong password 401; all game endpoints 401 without session or trial token; trial token plays a full loop (task→sell→buy→open) hitting zero Firebase/Groq (assert via fakes); two tokens are isolated; expired/unknown token 401; POST `/api/friends` returns `https://lifu.doslan.com/{name}`.

## Phase 12 — Frontend scaffold + state + API client
**Goal:** running SPA with login and live state snapshot.
**Create:** `frontend/` Vite+React+TS, `src/api.ts` (typed client, error envelope, trial header), `src/state/store.ts` (Zustand, `GET /api/state` hydrate + delta patching), LoginGate, WalletBadge, raw JSON debug view of state.
**Accept:** `npm run build` clean, strict TS; vitest covers store patching and api error mapping; manual: login → state renders.

## Phase 13 — Frontend game HUD (tasks, rewards, collectables)
**Goal:** playable via HTML panels (no 3D yet): TaskComposer, RewardComposer (incl. spoiler-safe masked paste + friend select), MergePanel (merge/harmony/combine/sell), StatsPanel.
**Accept:** full task→fragments→merge→sell loop playable in browser against memory backend; vitest on panel logic (key derivation display, disabled states); secret textarea visually masked.

## Phase 14 — ★ HARD — three.js scene + treasures + opening
**Goal:** SceneCanvas per ARCHITECTURE §10: TreasureShelf, CollectableWall, FxLayer; TreasurePanel + VaultPanel; buy/drop reveal animation; harmony build-up replaying exactly `extras` bursts from the server response.
**Why hard:** first three.js work (owner is learning it — keep it simple, orthographic 2.5D), animation sequencing driven by server results, sync between canvas and Zustand.
**Accept:** buy a treasure → drop animates then panel shows result; harmony merge animates `extras+1` pulses; discard + pity bars visible; runs 60 fps with full inventory; no game logic in canvas components (they read the store only).

## Phase 15 — Friend page, polish, deploy prep
**Goal:** `/{friend_name}` route: explanation page + "try it" → trial session → same GameScreen in trialMode (banner, no friend-links panel); CORS for lifu.doslan.com; swagger pass (every endpoint documented with request/response schemas); README with setup steps.
**Accept:** unknown friend name → friendly "ask Doslan for a link" page; trial reload = fresh game; `python -m pytest` + `npm test` + both linters green; fresh-clone setup following README works with `REPO_BACKEND=memory` and no secrets.

---

# Part II — Frontend rebuild

Phases 1–15 are complete. The HUD they produced was functional but not designed;
Part II replaces it with the three-layout scroll-snap design agreed in
`frontend/public/mockup.html` (delete that file at the end of Phase 22 — it is
scaffolding, not a deliverable).

Same rules as Part I: one phase per session, app runnable at the end of each,
`pytest` + `ruff` + `npm test` + `npm run lint` + `npm run build` all green
before a phase counts as finished.

**The shape:** one root page that scroll-snaps between three full-height layouts
— *Ledger* (log a task, see recent ones), *Vault* (everything you own, merge
bench), *Treasury* (three treasures, buy, elimination) — plus a separate
`/admin` page for rewards.

## Phase 16 — ★ HARD — Seal the reward↔receptacle link (§2 privacy)
**Goal:** make the surprise actually hold. Today `serialize_receptacle` returns
`virtue`, `rarity` and `reward_text` in one object and only withholds the text
when `is_secret`, so a reward you wrote yourself is readable *before* you open
its receptacle — and the admin list would tell you which receptacle each reward
landed in. Hiding it on one endpoint is not enough; the link leaks from
whichever side is left open.
**Create:** `serialize_receptacle` withholds `reward_text` for **any** unopened
receptacle, not just secret ones; new `GET /api/rewards` for the admin page
returning `{text, is_secret, friend_name, created_at}` and deliberately **no**
`virtue`, `rarity`, `value` or receptacle id; update hard rule 6 in
[CLAUDE.md](../CLAUDE.md) and the privacy rule in [ARCHITECTURE.md](ARCHITECTURE.md) §2.
**Accept:** tests assert an own, non-secret, unopened receptacle returns
`reward_text: null` from `/api/receptacles` *and* from `/api/state`; opened ones
still return it; `/api/rewards` response contains no rarity/virtue/value key at
all (assert on the key set, not on values); every existing secret-leak test
still passes.

## Phase 17 — Design system + app shell
**Goal:** the tokens, the icon layer, and the snapping deck — no game content yet.
**Create:** `src/ui/tokens.css` (palette, radii, the serif/sans pairing — lift
from the mockup), `src/ui/Icon.tsx` mapping a stock key to
`/icons/{collectables|receptacles}/{name}.png`, `src/ui/Deck.tsx` (scroll-snap
container + section rail), `src/ui/Overlay.tsx` (the shared veil: staged prize
queue and modal), restyled `WalletBadge`, `App.tsx` routing root / `/admin` /
`/{friend}`.
**Accept:** three empty sections snap and the rail tracks them; a test walks all
16 elements × 6 rarities and 10 virtues × 6 tiers and asserts every one of the
156 resolved icon paths exists on disk; strict TS, build clean.

## Phase 18 — Layout 1: the Ledger
**Goal:** log a task and watch it pay out.
**Create:** `src/layouts/Ledger.tsx`, rewritten `TaskComposer`, `TaskList`
(drops as `13×[icon]`, relative time, 4 rows then `…more…` → 14), randomised
greeting, and the staged reveal: one drop card at a time with Accept, plus Skip
when more than one is queued.
**Accept:** the reveal replays exactly what the server returned, in server order
— never a client-invented count; `…more…` expands; empty state reads well;
vitest covers queue advance, skip, and the single-item case hiding Skip.

## Phase 19 — ★ HARD — Layout 2: the Vault
**Goal:** everything you own, inspect, and one bench for every merge.
**Create:** `src/layouts/Vault.tsx`, `Hoard` (grouped grid, counts, hover names,
🔒/● key badges), `ItemDetail` (double-click: collectables show element/rarity/
held/next-merge; receptacles show key status and an Open button only when the
key is actually held), `MergeBench` (drag-and-drop + quantity + a button that
names the detected operation), `RecipeInfo` popover with the merge ladder,
harmony recipe and all 10 combine pairs.
**Why hard:** the bench maps an arbitrary set of dropped items onto exactly one
of merge-up / harmony / combine / open, or refuses with a reason. That mirrors
backend rules and must not drift from them — derive from `src/domain.ts`, which
already mirrors `core/mappings.py`.
**Accept:** vitest table-drives detection: 3 identical → merge-up to the right
rarity; 5 distinct base at one rarity → harmony; 2 base + 1 harmony → the
correct combined element for **all 10 pairs**; CORE rejected; invalid sets
disabled with a reason shown. Key availability is computed client-side and
matches `key_for_receptacle`, so a keyless Open is never a 400 round-trip.

## Phase 20 — Layout 3: the Treasury
**Goal:** small selectors, huge contents, a drawn-out elimination.
**Create:** `src/layouts/Treasury.tsx`, `TreasureSelector` (compact cards),
`Contents` (large floating receptacles filling the layout), and the elimination
sequencer: everything shivers, then contents go dark **one at a time in random
order** until the survivor flares and the prize overlay opens.
**Why the order matters:** the survivor is whichever receptacle the server
actually dropped. The client only chooses the *order the losers fade*, never the
winner — same server-authoritative rule as the existing fx queue.
**Accept:** exactly `contents − 1` eliminate; the survivor equals the server's
`drop`; the sequence is skippable; buy is disabled while rolling and when coins
< price; the displayed price is the treasure's fixed `price` field (regression
guard for the bug where price drifted as contents dropped out).

## Phase 21 — Admin page
**Goal:** rewards in, rewards listed, nothing leaked.
**Create:** `src/layouts/Admin.tsx`, restyled `RewardComposer` (keep the
spoiler-safe masked textarea and the friend selector), `RewardList` fed by the
Phase-16 `/api/rewards`, and the friend-link manager moved here.
**Accept:** a test renders the list with fixture data and asserts no virtue or
rarity string appears anywhere in the DOM; a friend's secret gift renders masked
until opened; creating a link shows the shareable URL.

## Phase 22 — Cutover and cleanup
**Goal:** delete the old UI and place the four features that have no home in the
three layouts.
**Placements (decide before starting, these are the proposal):** sell → inside
the collectable `ItemDetail`; once-a-day discard → Treasury, near the selectors;
stats/streak → Ledger header; friend links → Admin (Phase 21).
**Delete:** `src/scene/*`, `StateDebugView`, the Part-I panels superseded by the
new layouts, `frontend/public/mockup.html` and `mockup-admin.html`. Drop `three`
and `@react-three/fiber` from `package.json` **only if** the 3D scene is really
gone — that removes the three.js learning goal from Part I, so confirm first.
**Accept:** no dangling imports; `npm run build` clean and measurably smaller if
three was dropped; every vitest green; the full loop — task → merge → buy →
open — playable end to end against `REPO_BACKEND=memory`; README updated.
