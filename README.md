# LifU

A single-player game where the currency is things you actually did.

You describe something you finished. It gets valued, and pays out fragments of
the five elements it called on. Rewards you want are sealed into receptacles
whose rarity depends on how they compare to your other rewards — and each one
opens with exactly one collectable you have to craft. A Safe of Serenity wants
an Ocean Essence, and nothing else will do.

Built for one owner, with shareable sandbox links for friends.

## The loop

| Step | What happens |
|---|---|
| Log a task | An AI rates how hard and valuable it was, and which of the five virtues it needed |
| Earn fragments | Each virtue pays its element — willpower pays fire, awareness pays space |
| Merge | Three of a kind become one of the next rarity, up through Fragment → Shard → Crystal → Essence → Soul → Core |
| Harmony | One of each base element becomes five Harmony, then a build-up rolls for extras |
| Combine | Two base elements plus a Harmony become one of the ten combined elements — the keys |
| Hide a reward | It is sealed into a receptacle; rarity comes from a 27:9:3:1 ratio across everything you own |
| Buy a treasure | Coins buy a pull; rarer receptacles are rarer drops, with pity counters at 27 and 81 |
| Open | Spend the matching key. The reward is revealed and pays out its value in coins |

## Running it

Requires Python 3.10+ and Node 20+.

### Backend

```bash
cd backend
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -e ".[dev]"   # Windows
# python -m venv .venv && .venv/bin/pip install -e ".[dev]"   # macOS/Linux
cp .env.example .env
```

Set `OWNER_PASSWORD` in `.env` — that is how you sign in. Everything else is
optional: with `REPO_BACKEND=memory` (the default) the game runs entirely in
memory, and with no `GROQ_API_KEY` it uses a random stand-in for the AI. That
is enough to play with immediately.

```bash
./.venv/Scripts/python.exe manage.py runserver
```

API docs at http://localhost:8000/api/docs.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server proxies `/api` to the backend, so
the session cookie is same-origin and there is no CORS to configure locally.

### Going further

| Variable | What it turns on |
|---|---|
| `GROQ_API_KEY` | Real task valuation and reward classification (free tier at console.groq.com) |
| `REPO_BACKEND=firebase` + `FIREBASE_CREDENTIALS` | Persistent storage in Firestore |
| `DEVIANTART_*`, `JAMENDO_CLIENT_ID` | Extra sources for the surprises inside generated Pouches and Sacks |
| `TIMEZONE` | Day boundary for streaks and the once-a-day discard. Must be an IANA name like `Asia/Almaty`, not `UTC+6` |
| `CORS_ALLOWED_ORIGINS` | Only needed when the frontend is served from a different origin than the API |

## Friend links

Create one in the app; it produces `https://lifu.doslan.com/{name}`. That page
explains the game and opens a sandbox: its own in-memory world with a random
AI and some starting coins. Nothing a friend does reaches the real save, and
reloading starts them over.

## Tests

```bash
cd backend && ./.venv/Scripts/python.exe -m pytest && ./.venv/Scripts/python.exe -m ruff check .
cd frontend && npm test && npm run lint && npm run build
```

The backend suite runs offline by default. Tests that need credentials — live
Firestore contract tests, and prompt-calibration tests marked `groq` — skip
themselves unless `FIREBASE_CREDENTIALS` / `GROQ_API_KEY` are set.

## Layout

```
backend/
  core/        pure domain: enums, mapping tables, constants, entities
  repos/       repository interfaces + memory and Firestore implementations
  services/    game rules: valuation, merging, rarity, treasures, rewards
  aiclients/   Groq client, random client, and the validation pipeline
  providers/   live content for generated Pouches and Sacks
  api/         thin DRF views over the services
frontend/
  src/scene/   the three.js canvas
  src/state/   Zustand store and session
  src/         typed API client and the HUD panels
docs/          SPEC, ARCHITECTURE, PLAN, AI_PROMPTS, ICON_PROMPTS
```

[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) is the source of truth for the
rules and formulas; [CLAUDE.md](CLAUDE.md) has the repo conventions.
