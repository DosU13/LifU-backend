# LifU — Architecture

Single-user gamified productivity app. Owner logs in with a password and plays for real; friends get shareable trial links. Django + DRF backend, Firebase (Firestore) behind repository interfaces, Groq for AI, React + three.js single-page frontend.

This document is the source of truth for domain rules. Where SPEC.md is ambiguous, the rules here win (they were confirmed with the owner).

---

## 1. Repository layout

```
LifU/
├── CLAUDE.md
├── docs/                  # SPEC.md, ARCHITECTURE.md, PLAN.md, AI_PROMPTS.md
├── backend/
│   ├── manage.py
│   ├── pyproject.toml     # deps, ruff, pytest config
│   ├── lifu/              # Django project: settings.py, urls.py, wsgi.py
│   ├── core/              # PURE PYTHON domain layer — no Django, no Firebase, no HTTP
│   │   ├── enums.py       # Element, CollectableRarity, TaskVirtue, Virtue,
│   │   │                  # ReceptacleRarity, ReceptacleState
│   │   ├── mappings.py    # all lookup tables (§3)
│   │   ├── entities.py    # dataclasses: Task, Receptacle, Treasure, FriendLink
│   │   ├── constants.py   # every tunable number (§4)
│   │   ├── errors.py      # DomainError subclasses (§9)
│   │   └── rng.py         # Rng protocol + SystemRng + SeededRng (tests)
│   ├── repos/
│   │   ├── interfaces.py  # abstract repositories (§6)
│   │   ├── memory.py      # in-memory implementations (trial mode + tests)
│   │   ├── firebase.py    # Firestore implementations
│   │   └── factory.py     # builds a RepoBundle: firebase (real) or memory (trial)
│   ├── aiclients/
│   │   ├── base.py        # AIClient protocol: complete_json(system, user) -> dict
│   │   ├── groq_client.py # real Groq HTTP client
│   │   ├── random_client.py  # trial mode: returns random valid values
│   │   ├── fake.py        # tests: returns pre-programmed responses
│   │   ├── prompts.py     # system prompts (kept in sync with docs/AI_PROMPTS.md)
│   │   └── validation.py  # parse/clamp/retry pipeline (§8)
│   ├── providers/         # content for generated receptacles (§7.6)
│   │   ├── base.py        # QuoteProvider / DiscoveryProvider protocols
│   │   ├── quotes.py      # live quote/fact APIs + local fallback
│   │   ├── art.py         # DeviantArt API provider
│   │   ├── music.py       # Jamendo/iTunes provider
│   │   └── fallback.py    # local curated lists, used only when live fetch fails
│   ├── services/          # game logic, constructor-injected repos/ai/rng (§7)
│   │   ├── container.py   # wires services per request context (real vs trial)
│   │   ├── task_service.py
│   │   ├── reward_service.py
│   │   ├── merger_service.py
│   │   ├── rarity_service.py
│   │   ├── treasure_service.py
│   │   ├── economy_service.py   # sell, wallet
│   │   └── stats_service.py
│   ├── api/               # the only Django app
│   │   ├── views/         # thin: parse request → call service → serialize
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── auth.py        # owner password login, session auth
│   │   └── trial.py       # trial-token resolution middleware/permission
│   └── tests/             # mirrors package structure
└── frontend/              # Vite + React + TypeScript + three.js (§10)
```

**Dependency direction (enforced by review, this is the SOLID core):**
`api → services → (repos.interfaces, aiclients.base, providers.base, core)`.
Concrete adapters (`repos.firebase`, `repos.memory`, `groq_client`, live providers) are only referenced in `repos/factory.py` and `services/container.py`. **No Firebase / Groq / HTTP call anywhere outside `repos/firebase.py`, `aiclients/groq_client.py`, `providers/*`.**

---

## 2. Domain model

### Enums

| Enum | Values |
|---|---|
| `Element` (16) | SPACE, AIR, FIRE, WATER, EARTH, HARMONY, GROWTH, FORGE, DUST, MOUNTAIN, STEAM, MIST, OCEAN, LIGHTNING, SUN, WIND |
| `ElementKind` | BASE (first 5), HARMONY, COMBINED (last 10) |
| `CollectableRarity` (6, ordered) | FRAGMENT=0, SHARD=1, CRYSTAL=2, ESSENCE=3, SOUL=4, CORE=5 |
| `TaskVirtue` (5) | AWARENESS, CURIOSITY, WILLPOWER, COMPASSION, DISCIPLINE |
| `Virtue` (10) | NURTURING, DETERMINATION, ADAPTABILITY, PRESENCE, TRANSFORMATION, REFLECTION, SERENITY, INSPIRATION, VITALITY, FREEDOM |
| `ReceptacleRarity` (6, ordered) | POUCH=0, SACK=1, CHEST=2, SAFE=3, VAULT=4, SANCTUM=5 |
| `ReceptacleState` | IN_POOL, IN_TREASURE, DROPPED, OPENED |
| `GeneratedKind` | QUOTE, FACT, MUSIC, ART (content type of generated Pouches/Sacks) |

### Entities (dataclasses in `core/entities.py`; persistence shape mirrors these)

**Task** — `id, text, created_at, value:int(0-100), virtues: dict[TaskVirtue,int(0-100)], fragments_awarded: dict[Element,int]` (base elements only).

**Receptacle**
```
id, state: ReceptacleState
virtue: Virtue
rarity: ReceptacleRarity        # generated: fixed POUCH/SACK; else recalculated (§7.4)
value: int 0-100                # AI value, or random for generated (§4)
is_generated: bool
is_secret: bool
friend_name: str | None         # attribution for secret gifts
reward_text: str | None         # the promise/reward text; None for generated
content: {kind: GeneratedKind, title, url, author, text} | None   # generated only
treasure_id: str | None         # set while IN_TREASURE
created_at, opened_at
```
Privacy rule: for `is_secret=True` receptacles not yet OPENED, the API never returns `reward_text` (it exists only in DB).

**Treasure** — `id, slot:int(0-2), receptacle_ids:[str], pity: {VAULT:int, SANCTUM:int}, created_at`. Pity is **per treasure** and dies with it (owner's explicit choice).

**Wallet** — `coins:int ≥ 0` (single document).

**CollectableStock** — conceptually `dict[(Element, CollectableRarity), int]`; stored as one document with 96 counter fields keyed `"FIRE_SHARD"` etc.

**FriendLink** — `name (slug, unique), created_at`. URL is `https://lifu.doslan.com/{name}`.

**GameMeta** — `last_discard_date: date | None` (in `TIMEZONE`).

### Receptacle lifecycle

```
(reward submitted) ──► IN_POOL ──► IN_TREASURE ──► DROPPED ──► OPENED
                          ▲             │ (discard)
                          └─────────────┘
(generated Pouch/Sack) ────────────────► DROPPED ──► OPENED
```
- Treasures draw only from IN_POOL. A receptacle is in at most one treasure.
- DROPPED = owned by the user but locked; opening needs + consumes the key (§7.5).
- Rarity of a **non-generated** receptacle is mutable in every state except OPENED (literal spec: "after it opened it never changes but attends to calculation"). Yes, a DROPPED receptacle's required key can change after a recalc — accepted.

---

## 3. Lookup tables (`core/mappings.py`)

**Base element ↔ task virtue** (fragment award, §7.1):
SPACE↔AWARENESS, AIR↔CURIOSITY, FIRE↔WILLPOWER, WATER↔COMPASSION, EARTH↔DISCIPLINE.
(Harmony's virtue is "Wisdom" — flavor only, no mechanic.)

**Combined element composition** (harmony merge, §7.3):

| Pair | → | Pair | → |
|---|---|---|---|
| EARTH+WATER | GROWTH | WATER+AIR | MIST |
| EARTH+FIRE | FORGE | WATER+SPACE | OCEAN |
| EARTH+AIR | DUST | FIRE+AIR | LIGHTNING |
| EARTH+SPACE | MOUNTAIN | FIRE+SPACE | SUN |
| WATER+FIRE | STEAM | AIR+SPACE | WIND |

**Virtue ↔ combined element** (key lookup, §7.5): NURTURING↔GROWTH, DETERMINATION↔FORGE, ADAPTABILITY↔DUST, PRESENCE↔MOUNTAIN, TRANSFORMATION↔STEAM, REFLECTION↔MIST, SERENITY↔OCEAN, INSPIRATION↔LIGHTNING, VITALITY↔SUN, FREEDOM↔WIND.

**Receptacle rarity ↔ collectable rarity** (same index): POUCH↔FRAGMENT, SACK↔SHARD, CHEST↔CRYSTAL, SAFE↔ESSENCE, VAULT↔SOUL, SANCTUM↔CORE.
Example: **Safe of Serenity opens with one Ocean Essence.**

---

## 4. Constants (`core/constants.py` — every number tunable here, nowhere else)

| Constant | Value | Meaning |
|---|---|---|
| VIRTUE_TUNER | 1.0 | fragment formula multiplier |
| MERGE_INPUT / MERGE_OUTPUT | 3 / 1 | same-type rarity-up merge |
| HARMONY_BASE_YIELD | 5 | harmony merge guaranteed output |
| HARMONY_EXTRA_CHANCE | 0.5 | repeat-until-fail extra roll |
| HARMONY_EXTRA_CAP | 64 | hard safety cap on extras |
| RARITY_RATIO | CHEST 27 : SAFE 9 : VAULT 3 : SANCTUM 1 | recalculation quotas |
| DROP_CHANCES | SANCTUM 1/243, VAULT 1/81, SAFE 1/27, CHEST 1/9, SACK 1/3, POUCH 1.0 | per-buy, rarest first |
| PITY_THRESHOLDS | VAULT 27, SANCTUM 81 | per-treasure |
| TREASURE_COUNT | 3 | simultaneous treasures |
| TREASURE_SIZE | random 5–10 (fewer if pool short, min 1) | receptacles per treasure |
| POUCH_VALUE_RANGE / SACK_VALUE_RANGE | (1, 15) / (10, 40) | random value for generated |
| SECRET_MIN_VALUE | 51 | floor for secret gifts |
| FE_BASE / FE_HARMONY / FE_COMBINED | 1 / 1 / 3 | fragment-equivalents at FRAGMENT tier |
| DISCARDS_PER_DAY | 1 (global, all slots) | resets at midnight `TIMEZONE` |
| AI_MAX_RETRIES | 2 | validation retry budget |
| TIMEZONE | env, default "UTC" | day boundary for discard + streaks |

**Sell price** (coins) `= FE(elem) * 3^rarity_index`:

| | Fragment | Shard | Crystal | Essence | Soul | Core |
|---|---|---|---|---|---|---|
| base / harmony | 1 | 3 | 9 | 27 | 81 | 243 |
| combined | 3 | 9 | 27 | 81 | 243 | 729 |

---

## 5. Economy loop (confirmed with owner)

Tasks award **fragments only, no coins**. Coins come from (a) opening receptacles — each drops exactly `value` coins — and (b) selling collectables at the table above. Coins buy treasure pulls. Collectables are also the **keys** that open receptacles. Bootstrap: do tasks → sell some fragments for first coins → buy pulls → craft keys → open drops → bigger coins.

---

## 6. Repository interfaces (`repos/interfaces.py`)

All abstract (ABC). Firebase impls in `repos/firebase.py` (Firestore via `firebase-admin`; counters and wallet mutations inside Firestore transactions). Memory impls in `repos/memory.py` (plain dicts; used by trial mode and all unit tests).

```python
class TaskRepository(ABC):
    def add(self, task: Task) -> Task
    def list_since(self, since: datetime) -> list[Task]

class CollectableRepository(ABC):
    def get_all(self) -> dict[tuple[Element, CollectableRarity], int]
    def adjust(self, deltas: dict[tuple[Element, CollectableRarity], int]) -> None
        # atomic; raises InsufficientCollectables if any count would go < 0

class WalletRepository(ABC):
    def get_coins(self) -> int
    def adjust(self, delta: int) -> int   # atomic; raises InsufficientCoins if < 0

class ReceptacleRepository(ABC):
    def add(self, r: Receptacle) -> Receptacle
    def get(self, id: str) -> Receptacle          # raises NotFound
    def update(self, r: Receptacle) -> None
    def list_by_state(self, state: ReceptacleState) -> list[Receptacle]
    def list_non_generated(self) -> list[Receptacle]   # all states, for recalc

class TreasureRepository(ABC):
    def get_all(self) -> list[Treasure]          # ≤ 3
    def save(self, t: Treasure) -> None
    def delete(self, id: str) -> None

class FriendLinkRepository(ABC):
    def add(self, name: str) -> FriendLink       # raises AlreadyExists
    def get(self, name: str) -> FriendLink | None
    def list_all(self) -> list[FriendLink]

class MetaRepository(ABC):
    def get_last_discard_date(self) -> date | None
    def set_last_discard_date(self, d: date) -> None
```

`repos/factory.py` exposes `build_repos(backend: "firebase"|"memory") -> RepoBundle` (a dataclass holding one of each). Trial mode keeps a process-global `dict[trial_token, RepoBundle]` of memory bundles with 24 h TTL — restart or new token = fresh game, which is exactly the intended trial behavior.

**Firestore layout** (single user, no per-user nesting): collections `tasks`, `receptacles`, `treasures`, `friend_links`; singleton docs `wallet/main`, `collectables/main`, `meta/main`.

---

## 7. Services — exact algorithms

Every service takes its dependencies (repos, `AIClient`, `Rng`, providers, clock) via constructor. `Rng` wraps `random.Random`; tests inject `SeededRng`.

### 7.1 TaskService.complete_task(text)

1. `resp = validate_task_valuation(ai.complete_json(TASK_VALUER_SYSTEM, text))` (§8).
2. `avg = mean(resp.virtues.values())` (the 5 virtue ints).
3. For each base element `e` with mapped task virtue `v`:
   `fragments[e] = round((avg / 100) * (resp.virtues[v] / 100) * resp.value * VIRTUE_TUNER)` — can be 0.
   Sanity: Value 10 run at ~50% virtues → ~2–3 per element; Value 100 project at 80% → ~64.
4. `collectables.adjust({(e, FRAGMENT): n for nonzero n})`; save Task with valuation + awards; return both.

### 7.2 MergerService.merge_up(element, rarity)

Requires `rarity != CORE` and stock ≥ 3. Atomically `-3` of `(element, rarity)`, `+1` of `(element, rarity+1)`. Works for all 16 elements including HARMONY and combined.

### 7.3 MergerService.merge_harmony(rarity) and combine(a, b, rarity)

**Harmony:** requires ≥ 1 of each of the 5 base elements at `rarity`. Server rolls the whole outcome (frontend replays the animation `extras` times — server-authoritative):
```
extras = 0
while rng.random() < HARMONY_EXTRA_CHANCE and extras < HARMONY_EXTRA_CAP:
    extras += 1
yield_ = HARMONY_BASE_YIELD + extras        # expected 6
```
Atomically: −1 each base element, +`yield_` HARMONY, all at `rarity`. Return `{yield, extras}`.

**Combine:** `a, b` distinct base elements. Requires 1×a, 1×b, 1×HARMONY, all at `rarity`. Atomically −those, +1 of `COMBINED_MAP[{a,b}]` at `rarity`.

### 7.4 RarityService.recalculate() — the 27:9:3:1 assignment

Runs after **every** mutation of a non-generated receptacle (create, open, drop, discard-return). Idempotent; N is small.

```
rs = repo.list_non_generated()                      # opened AND unopened
sort rs by (value DESC, created_at ASC, id ASC)     # deterministic ties
N = len(rs)
# Hamilton / largest-remainder apportionment over weights 27:9:3:1 (sum 40)
quota[r]  = N * weight[r] / 40          for r in [CHEST, SAFE, VAULT, SANCTUM]
count[r]  = floor(quota[r])
distribute (N - sum(count)) leftover slots one-by-one to largest fractional
    remainder; ties broken toward the more common rarity (CHEST first)
# assign by rank, rarest at top:
ranks 1..count[SANCTUM] → SANCTUM, next count[VAULT] → VAULT,
next count[SAFE] → SAFE, remaining → CHEST
for each receptacle: if state != OPENED and rarity != slot: rarity = slot; update
```
OPENED receptacles keep their frozen rarity but **occupy their rank's slot** — an opened one sitting at rank 1 consumes the Sanctum slot. Live counts may therefore deviate from 27:9:3:1; that is per spec.
Worked examples (must be unit tests): N=1 → 1C. N=4 → 3C,1S. N=14 → 10C,3S,1V. N=40 → 27C,9S,3V,1S(anctum).

### 7.5 RewardService and opening

**submit_reward(text, is_secret, friend_name=None):**
1. `resp = validate_reward(ai.complete_json(REWARD_CLASSIFIER_SYSTEM, wrap(text, is_secret)))` (§8). If `is_secret` and `resp.value ≤ 50` → set to `SECRET_MIN_VALUE`.
2. `virtue = rng.choice(resp.classes)` (1–3 classes).
3. Create Receptacle: IN_POOL, `value=resp.value`, `reward_text=text`, `is_secret`, `friend_name`; rarity placeholder CHEST, then `rarity_service.recalculate()` assigns the real one.
4. `treasure_service.refill_empty_slots()` (a waiting slot may now be fillable).
Secret entry UX: owner pastes the friend's message into a masked textarea ("spoiler-safe paste") — API identical, just `is_secret=true` + `friend_name`.

**open_receptacle(id):** state must be DROPPED. Key: `element = VIRTUE_ELEMENT[virtue]`, `key_rarity = CollectableRarity(receptacle.rarity.value)`. Requires stock ≥ 1 → atomically −1 key, `wallet += receptacle.value` coins, state=OPENED, `opened_at=now`. Then `recalculate()`. Returns full receptacle incl. previously hidden `reward_text` / `content`. Missing key → `MissingKey(element, key_rarity)` error (frontend shows "needs Ocean Essence").

### 7.6 TreasureService

**generate(slot):** draw size `k = rng.randint(5, 10)` clamped to pool size (pool = IN_POOL receptacles; if pool empty, slot stays empty/"waiting" and refills automatically on next reward submission). "Desirably random rarities": group pool by current rarity, shuffle each group, then round-robin across shuffled group order taking one per group until `k` drawn. Set drawn receptacles IN_TREASURE. Pity counters start at 0.

**price(treasure)** = `max(1, ceil(mean(value of its *starting* receptacles)))`, computed once in `generate()` and stored on the Treasure. **Fixed for the treasure's lifetime** — it does not fall as receptacles drop out, so emptying a treasure never makes the remaining pulls cheaper. A new treasure (including one that replaces an emptied or discarded slot) gets its own price from its own starting contents.

**buy(treasure_id):**
```
price = price(t); wallet.adjust(-price)              # raises InsufficientCoins
drop = None
# pity, rarest first, only if fulfillable:
if t.pity[SANCTUM] >= 81 and t has unopened SANCTUM: drop = (SANCTUM, pity=True)
elif t.pity[VAULT] >= 27 and t has VAULT:            drop = (VAULT, pity=True)
if drop is None:                                     # natural roll, rarest first
    for r in [SANCTUM, VAULT, SAFE, CHEST]:
        if rng.random() < DROP_CHANCES[r] and t has receptacle of rarity r:
            drop = r; break                          # tier absent → falls through
    if drop is None:
        drop = SACK if rng.random() < 1/3 else POUCH # always available (generated)
# resolve:
real rarity  → pick uniform among t's receptacles of that rarity,
               remove from treasure, state=DROPPED, recalculate()
SACK/POUCH   → create generated receptacle: state=DROPPED, rarity fixed,
               virtue = rng.choice(all 10), value = rng.randint(*VALUE_RANGE),
               content = providers.fetch(POUCH→quote/fact, SACK→music/art)
# pity update:
for r in [VAULT, SANCTUM]: t.pity[r] = 0 if dropped_rarity == r else t.pity[r] + 1
if t.receptacle_ids empty: delete t; generate(slot)   # regeneration
```
Note: a pity counter past its threshold that can't fire (rarity absent) keeps incrementing and fires on the first fulfillable buy. Counters never migrate to a new treasure.

**discard(treasure_id):** allowed iff `meta.last_discard_date != today(TIMEZONE)` — one discard per day **across all slots**. Contents return to IN_POOL, treasure deleted, `generate(slot)`, record date. Error otherwise: `DiscardAlreadyUsed`.

### 7.7 EconomyService.sell(element, rarity, count) / StatsService

Sell: atomically −count collectables, +`count * sell_price` coins (§4 table).
Stats: tasks per day (last 30 d), mean of each task virtue, current streak = consecutive days ending today with ≥1 task, in `TIMEZONE`.

---

## 8. AI integration (Groq)

- `GroqClient` (in `aiclients/groq_client.py`): POST `https://api.groq.com/openai/v1/chat/completions`, model from env `GROQ_MODEL` (default `llama-3.3-70b-versatile`), `response_format={"type":"json_object"}`, `temperature=0.2`, key from `GROQ_API_KEY`. This is the **only** file that talks to Groq.
- System prompts live in `aiclients/prompts.py`, drafted in [docs/AI_PROMPTS.md](AI_PROMPTS.md).
- **Validation pipeline** (`aiclients/validation.py`), identical for both features:
  1. Parse JSON (already dict from json mode, but guard).
  2. Check exact keys and types (ints for numerics; list[str] for Class).
  3. **Clamp** numerics into [0,100] — out-of-range is fixed, not retried.
  4. Classifier: filter Class against the 10-virtue enum (case-insensitive), dedupe, truncate to 3.
  5. **Retry** (≤ AI_MAX_RETRIES) only for structural failures: unparseable, missing/mistyped keys, or Class empty after filtering. Retry appends a corrective user message naming the violation.
  6. Retries exhausted → raise `AIResponseInvalid` → API returns **502** `{error:{code:"AI_INVALID"}}`; nothing is saved, user retries. Values are never fabricated.
  7. Secret with value ≤ 50 after clamping → forced to 51 (no retry).
- **Trial mode** uses `RandomAIClient` (valid random JSON, no network). **Tests** use `FakeAIClient` (queue of canned responses, including malformed ones to test the pipeline). Zero network in the test suite.

---

## 9. API (DRF, session auth; swagger via drf-spectacular at `/api/docs`)

Errors: consistent `{"error": {"code": str, "message": str}}`; domain errors → 400 (`INSUFFICIENT_COINS`, `INSUFFICIENT_COLLECTABLES`, `MISSING_KEY`, `DISCARD_USED`, `INVALID_MERGE`), 404 `NOT_FOUND`, 502 `AI_INVALID`, 401 unauthenticated.

Trial: `POST /api/trial/session {friend_name}` → `{token}` (name must be a valid FriendLink; memory RepoBundle seeded with a starter state: 100 coins, 5 of each base fragment, 6 pool receptacles). Every game endpoint below accepts **either** the owner session **or** header `X-Trial-Token`; the container picks (firebase repos + GroqClient) or (memory repos + RandomAIClient) accordingly. Same views, same services — the abstraction does the work.

| Method + path | Body → Response (happy path) |
|---|---|
| POST `/api/auth/login` | `{password}` → `{ok}` (sets session; password from env `OWNER_PASSWORD`) |
| POST `/api/auth/logout` | → `{ok}` |
| GET `/api/state` | → full snapshot: wallet, collectables, treasures (with prices+pity), dropped receptacles, stats — one call boots the SPA |
| POST `/api/tasks` | `{text}` → `{task:{value, virtues}, fragments_awarded}` |
| GET `/api/tasks?days=30` | → `{tasks:[...]}` |
| GET `/api/stats` | → `{per_day, virtue_means, streak}` |
| GET `/api/collectables` | → `{stocks:{"FIRE_SHARD":n,...}, coins}` |
| POST `/api/collectables/merge` | `{element, rarity}` → new stocks |
| POST `/api/collectables/harmony` | `{rarity}` → `{yield, extras, stocks}` |
| POST `/api/collectables/combine` | `{element_a, element_b, rarity}` → `{result_element, stocks}` |
| POST `/api/collectables/sell` | `{element, rarity, count}` → `{coins, stocks}` |
| POST `/api/rewards` | `{text, is_secret, friend_name?}` → receptacle summary (no reward_text if secret) |
| GET `/api/receptacles?state=DROPPED` | → list; unopened secrets omit `reward_text`; each includes `key_needed:{element, rarity}` |
| POST `/api/receptacles/{id}/open` | → `{receptacle (full), coins_gained, coins}` |
| GET `/api/treasures` | → 3 slots: `{id, price, pity, contents:[{virtue, rarity, is_secret, friend_name}]}` (no values/texts) |
| POST `/api/treasures/{id}/buy` | → `{drop:{receptacle...}, price_paid, coins, pity, treasure_gone:bool}` |
| POST `/api/treasures/{id}/discard` | → `{new_treasure}` |
| GET `/api/friends` / POST `/api/friends` | `{name}` → `{name, url}` |
| GET `/api/public/friend/{name}` | no auth → `{valid:bool}` (friend-page bootstrap) |

---

## 10. Frontend (`frontend/` — Vite, React 18, TypeScript, three.js via @react-three/fiber + drei, Zustand)

One page, no router except the friend path. three.js is intentionally minimal at first ("fine looking easy 2D game" — owner is learning three.js); the Canvas exists from day one so 3D ideas can grow into it.

```
App
├── (path "/{friend_name}") FriendGate → explanation page + "try it" → trial token → same GameScreen (trialMode)
├── (path "/") LoginGate → GameScreen
└── GameScreen
    ├── SceneCanvas (R3F <Canvas>, orthographic camera — 2.5D)
    │   ├── TreasureShelf → 3 × TreasureMesh (click → BuyPanel; drop/reveal animation)
    │   ├── CollectableWall (instanced meshes per element×rarity, count labels)
    │   └── FxLayer (harmony build-up: replays "+1" burst `extras` times from server response;
    │               merge poof; coin sparkle)
    └── Hud (plain HTML/CSS overlay, all interaction logic)
        ├── TaskComposer        → POST /tasks → award toast + FxLayer trigger
        ├── RewardComposer      → modes: "my reward" | "secret gift" (masked textarea + friend select)
        ├── MergePanel          → merge/harmony/combine/sell actions
        ├── VaultPanel          → DROPPED receptacles, key requirement badges, open button
        ├── TreasurePanel       → price, contents, pity bars, buy/discard
        ├── StatsPanel, WalletBadge, FriendLinksPanel (owner only)
```

**State:** one Zustand store mirroring `GET /api/state`; every mutating call returns the deltas it changed and the store patches them (no refetch-everything). A thin typed `api.ts` client owns fetch + error-envelope handling + the trial-token header. Server is authoritative for all randomness; the frontend only animates results it is told about (harmony `extras`, drop outcome).

**Testing:** Vitest for store reducers and `api.ts`; components smoke-tested with @testing-library/react; no three.js unit tests (visual, verified by hand).

---

## 11. Configuration (env)

`OWNER_PASSWORD`, `DJANGO_SECRET_KEY`, `REPO_BACKEND` (firebase|memory), `FIREBASE_CREDENTIALS` (path to service-account JSON), `GROQ_API_KEY`, `GROQ_MODEL`, `TIMEZONE`, `DEVIANTART_CLIENT_ID/SECRET`, `JAMENDO_CLIENT_ID`, `CORS_ALLOWED_ORIGINS` (lifu.doslan.com). `.env.example` kept current; secrets never committed.
