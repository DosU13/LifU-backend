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
