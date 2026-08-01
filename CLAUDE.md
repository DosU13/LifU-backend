# LifU — repo conventions

Gamified productivity app, single owner + trial links for friends. Read
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) before touching game logic — it is the source of
truth for all rules and formulas (it overrides docs/SPEC.md where they differ).
[docs/PLAN.md](docs/PLAN.md) tracks implementation phases; work on one phase per session and
keep the app runnable at the end of every phase.

## Commands

Backend (run from `backend/`):
- `python -m pytest` — full test suite (must pass before finishing any phase; no network calls in tests)
- `python -m pytest tests/services/ -k rarity` — focused run example
- `ruff check .` and `ruff format .` — lint + format (both clean before finishing)
- `python manage.py runserver` — dev server; swagger UI at http://localhost:8000/api/docs
- `REPO_BACKEND=memory python manage.py runserver` — run with nothing persisted

Frontend (run from `frontend/`):
- `npm run dev` / `npm run build` / `npm test` (vitest) / `npm run lint` (eslint)

## Hard rules

1. **Repository abstraction**: no Firebase/Firestore import or call outside `backend/repos/firebase.py`. No Groq/HTTP call outside `backend/aiclients/groq_client.py` and `backend/providers/*`. Services receive repositories, AI clients, providers, and `Rng` via constructor — never construct concrete adapters inside a service. Wiring happens only in `repos/factory.py` and `services/container.py`.
2. `backend/core/` is pure Python: no Django, DRF, Firebase, or HTTP imports there.
3. Every tunable number lives in `core/constants.py`. No magic numbers in services.
4. All randomness goes through the injected `Rng` — never call `random` module functions directly in services (tests inject `SeededRng`).
5. API views are thin: deserialize → call one service method → serialize. No game logic in views or serializers.
6. Never return `reward_text` of an unopened secret receptacle from any endpoint.
7. Tests: every service method gets unit tests with memory repos + `FakeAIClient` + `SeededRng`; every endpoint gets at least one happy-path and one error-path API test. New logic without tests is an unfinished phase.
8. AI responses are validated/clamped/retried per ARCHITECTURE §8; on failure return 502 — never fabricate values.
9. Python: type hints everywhere, dataclasses for entities, ruff clean. TypeScript: strict mode, no `any` in `frontend/src/state` or `frontend/src/api.ts`.
10. Don't commit secrets; keep `.env.example` in sync when adding env vars.

## Glossary

- **Element** — one of 16: 5 base (Space, Air, Fire, Water, Earth), Harmony, 10 combined (Growth, Forge, Dust, Mountain, Steam, Mist, Ocean, Lightning, Sun, Wind).
- **Collectable** — element × rarity (Fragment→Shard→Crystal→Essence→Soul→Core). Earned from tasks (base fragments), crafted by merging, sold for coins, spent as keys.
- **Fragment** — lowest collectable rarity; tasks award base-element fragments.
- **Harmony merge** — 1 of each of the 5 base elements (same rarity) → 5 Harmony + repeat-until-fail 50% extras.
- **Combine** — 1 elemA + 1 elemB + 1 Harmony (same rarity) → 1 combined element.
- **FE (fragment-equivalent)** — sell price unit; base/harmony fragment = 1, combined fragment = 3, ×3 per rarity step.
- **Receptacle** — a reward container: virtue × rarity (Pouch, Sack, Chest, Safe, Vault, Sanctum). Non-generated ones hold user/friend reward texts; generated Pouches/Sacks hold quotes/facts/music/art.
- **Virtue** — one of the 10 receptacle classes (Nurturing … Freedom), 1:1 with combined elements.
- **Key** — the collectable that opens a receptacle: element = virtue's combined element, rarity index matches (Safe of Serenity ⇒ Ocean Essence). Consumed on open.
- **Rarity recalculation** — after any non-generated receptacle change: sort by value, apportion Chest:Safe:Vault:Sanctum = 27:9:3:1 (largest remainder); opened receptacles keep frozen rarity but still occupy slots.
- **Treasure** — one of 3 slots holding 5–10 pool receptacles; buying rolls the drop table; price = avg value of contents.
- **Pity** — per-treasure counters (Vault 27, Sanctum 81); guaranteed drop when reached and fulfillable; dies with the treasure.
- **Discard** — "lose the treasure": once per day across all slots, contents return to pool.
- **Pool** — non-generated, unopened receptacles not currently in a treasure (state IN_POOL).
- **Dropped** — owned but locked receptacle awaiting its key.
- **Trial mode** — friend-link sandbox: memory repos + random AI, seeded starter state, lost on token expiry/reload. Real game = owner login only.
- **Spoiler-safe paste** — masked textarea for entering a friend's secret gift without the owner reading it.
