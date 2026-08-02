# Deploying to lifu.doslan.com

Cloudflare has no first-party way to run a Django app (no Python runtime, and
`repos/sqlite.py` needs a real local file with `BEGIN IMMEDIATE` transactions,
which doesn't map onto Workers or D1 without a rewrite). So the architecture
is split:

| Piece | Where | Why |
|---|---|---|
| Frontend (static build) | Cloudflare Pages, `lifu.doslan.com` | Cloudflare's actual job: a CDN for the built SPA |
| Backend (Django) | This machine, `api.lifu.doslan.com` via Cloudflare Tunnel | Keeps the local-SQLite latency win (§6, ARCHITECTURE.md) that was the whole reason to move off Firestore |

The frontend calls the API cross-origin (`VITE_API_BASE_URL`), which is
already accounted for: `CORS_ALLOWED_ORIGINS` and `django-cors-headers` were
wired up when `FRIEND_LINK_BASE_URL` was added. `lifu.doslan.com` and
`api.lifu.doslan.com` share `doslan.com` as their registrable domain, so the
`SESSION_COOKIE_SAMESITE = "Lax"` cookie already in use works across the two
subdomains without change.

Trade-off worth knowing: the game is only reachable while this machine and
the tunnel are running. Friend links break if the PC is off. Fine for a
single-owner project; revisit if that stops being true.

## 1. Backend: production settings

In the real `backend/.env` (never committed):

```
DJANGO_SECRET_KEY=<run: python -c "import secrets; print(secrets.token_urlsafe(50))">
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=api.lifu.doslan.com
CORS_ALLOWED_ORIGINS=https://lifu.doslan.com
OWNER_PASSWORD=<pick a real one>
REPO_BACKEND=sqlite
FRIEND_LINK_BASE_URL=https://lifu.doslan.com
```

`DEBUG=false` flips `SESSION_COOKIE_SECURE` on (settings.py:62), so the
backend must only ever be reached over HTTPS — true here since Cloudflare
Tunnel terminates TLS at Cloudflare's edge and speaks plain HTTP only inside
the tunnel to `localhost`, never on the open internet.

## 2. Backend: run it with a real WSGI server

`manage.py runserver` is dev-only. Install the `prod` extra and run
[waitress](https://github.com/Pylons/waitress) — pure-Python, no `fork()`
needed, so it works on Windows unlike gunicorn:

```bash
cd backend
./.venv/Scripts/python.exe -m pip install -e ".[prod]"
./run_prod.ps1
```

`run_prod.ps1` sets `DEBUG=false`/`ALLOWED_HOSTS`/`CORS_ALLOWED_ORIGINS` for
that process only (never the persistent environment, so a normal dev
`manage.py runserver` elsewhere is unaffected) and reads
`DJANGO_SECRET_KEY_PROD` from a persistent User environment variable — set it
once:

```powershell
[Environment]::SetEnvironmentVariable("DJANGO_SECRET_KEY_PROD", "<run: python -c 'import secrets; print(secrets.token_urlsafe(50))'>", "User")
```

It serves on **port 8001**, not 8000 — 8000 is this machine's usual
`manage.py runserver` dev port, kept free so dev and prod can run side by
side. Bound to `127.0.0.1` on purpose: reachable only via the tunnel or this
machine, never the LAN.

To survive reboots/logouts, wrap that command in a Windows Scheduled Task
("run at log on", `waitress-serve.exe` as the action) or install it as a
service with [NSSM](https://nssm.cc/) if you want proper start/stop control.

## 3. Cloudflare Tunnel: expose the backend as api.lifu.doslan.com

```bash
winget install --id Cloudflare.cloudflared
cloudflared tunnel login          # opens your browser, pick the doslan.com zone
cloudflared tunnel create lifu-backend
cloudflared tunnel route dns lifu-backend api.lifu.doslan.com
```

Then `%USERPROFILE%\.cloudflared\config.yml`:

```yaml
tunnel: <TUNNEL_ID from `tunnel create`>
credentials-file: C:\Users\<you>\.cloudflared\<TUNNEL_ID>.json
ingress:
  - hostname: api.lifu.doslan.com
    service: http://localhost:8001
  - service: http_status:404
```

Run it in the foreground first to confirm it works:

```bash
cloudflared tunnel run lifu-backend
```

Once confirmed, install it as a Windows service so it starts on boot:

```bash
cloudflared service install
```

Verify: `curl https://api.lifu.doslan.com/api/health` from any machine
should return the health check — with waitress running locally in another
window.

## 4. Cloudflare Pages: the frontend

Git-connected (recommended — every push to `main` redeploys automatically):

1. Cloudflare dashboard → Workers & Pages → Create → Pages → Connect to Git →
   the `LifU-backend` repo (it's a monorepo; the name predates the frontend).
2. Build settings:
   - Root directory: `frontend`
   - Build command: `npm run build`
   - Output directory: `dist`
3. Custom domains → add `lifu.doslan.com`.
4. Settings → Environment variables (Production) → add
   `VITE_API_BASE_URL` = `https://api.lifu.doslan.com`.

`frontend/.env.production` sets the same thing for local `npm run build`
runs, but it's covered by `.gitignore`'s `.env.*` rule like the rest of the
env files, so it never reaches Pages' build — the dashboard variable in step
4 is the one that actually takes effect there.

Manual alternative (no git push needed, e.g. for a one-off test deploy):

```bash
cd frontend
npm run build
npx wrangler pages deploy dist --project-name=lifu
```

(`npx wrangler login` first, if not already authenticated.)

## 5. Verify

- `https://api.lifu.doslan.com/api/health` — backend reachable through the tunnel.
- `https://lifu.doslan.com` — frontend loads, login gate appears.
- Log in, complete a task, check the session cookie persists (owner login
  should survive a reload — that's the Lax-cross-subdomain cookie working).
- A friend link (`https://lifu.doslan.com/<name>`) opens the trial sandbox.

## Rollback

Pages keeps every previous deployment — "Rollback to this deployment" in the
dashboard. The backend has no equivalent; it's one SQLite file
(`SQLITE_PATH`), so back it up before risky changes.
