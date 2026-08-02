# Deploying to lifu.doslan.com

Cloudflare has no first-party way to run a Django app (no Python runtime, and
`repos/sqlite.py` needs a real local file with `BEGIN IMMEDIATE` transactions,
which doesn't map onto Workers or D1 without a rewrite). So the architecture
is split:

| Piece | Where | Why |
|---|---|---|
| Frontend (static build) | Cloudflare Worker (static assets), `lifu.doslan.com` | Cloudflare's actual job: a CDN for the built SPA |
| Backend (Django) | This machine, `lifu-api.doslan.com` via Cloudflare Tunnel | Keeps the local-SQLite latency win (§6, ARCHITECTURE.md) that was the whole reason to move off Firestore |

Both processes — the tunnel and the backend — run as **Scheduled Tasks**
under this Windows account, triggered **at system startup** (see §3). Not a
Windows service: `cloudflared service install` runs as `LocalSystem`, whose
default config path (`%USERPROFILE%\.cloudflared\`) resolves to a different,
nonexistent profile than the one the tunnel was created under, and there's no
`--config` flag on `service install` to point it elsewhere. Not an "at logon"
trigger either, even though that's where this started: it only fires for a
real interactive desktop logon, and remote/automation access to this machine
doesn't count as one — after the process died once, nothing brought it back
because Windows never considered anyone "logged on." An `AtStartup` trigger
combined with an `S4U` logon (runs as this user, without storing the account
password anywhere) fires at boot regardless, and still has this user's
profile and environment variables. `backend/setup-autostart.ps1` sets this
up in one shot (§3) — it needs to run elevated, which isn't something this
assistant can reliably do unattended (Windows' UAC prompt has no one to click
"Yes" when nobody's watching), so it's written to be run by hand once.

The API hostname is `lifu-api.doslan.com` — a first-level subdomain of
`doslan.com` — not `api.lifu.doslan.com`. Cloudflare's automatic Universal
SSL certificate only covers the zone apex and one level of wildcard
(`doslan.com` + `*.doslan.com`); a second-level name like
`api.lifu.doslan.com` gets no certificate and the TLS handshake fails outright
(confirmed while setting this up — `openssl s_client` returned "handshake
failure" for the two-level name and a valid cert for the one-level name).
Total TLS (Cloudflare's paid-tier-adjacent feature for arbitrary subdomain
depth) would also fix it, but the flat name needs nothing extra.

The frontend calls the API cross-origin (`VITE_API_BASE_URL`), which is
already accounted for: `CORS_ALLOWED_ORIGINS` and `django-cors-headers` were
wired up when `FRIEND_LINK_BASE_URL` was added. `lifu.doslan.com` and
`lifu-api.doslan.com` share `doslan.com` as their registrable domain, so the
`SESSION_COOKIE_SAMESITE = "Lax"` cookie already in use works across the two
subdomains without change. It will **not** work from the Worker's raw
`*.workers.dev` URL, deliberately — that's a different origin entirely, not
in `CORS_ALLOWED_ORIGINS`, so the browser blocks the request outright. Always
test against `lifu.doslan.com`.

Trade-off worth knowing: the game is only reachable while this machine is on.
Friend links break otherwise. Fine for a single-owner project; revisit if
that stops being true.

## 1. Backend: production settings

In the real `backend/.env` (never committed):

```
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=lifu-api.doslan.com
CORS_ALLOWED_ORIGINS=https://lifu.doslan.com
OWNER_PASSWORD=<pick a real one>
REPO_BACKEND=sqlite
FRIEND_LINK_BASE_URL=https://lifu.doslan.com
```

`run_prod.ps1` (below) sets `DEBUG`/`ALLOWED_HOSTS`/`CORS_ALLOWED_ORIGINS` for
its own process only, overriding whatever `.env` says, so the `.env` values
above are mostly documentation of intent — the actual production values live
in the script. `DEBUG=false` flips `SESSION_COOKIE_SECURE` on (settings.py:62),
so the backend must only ever be reached over HTTPS — true here since
Cloudflare Tunnel terminates TLS at Cloudflare's edge and speaks plain HTTP
only inside the tunnel to `localhost`, never on the open internet.

## 2. Backend: run it with a real WSGI server

`manage.py runserver` is dev-only. Install the `prod` extra and run
[waitress](https://github.com/Pylons/waitress) — pure-Python, no `fork()`
needed, so it works on Windows unlike gunicorn:

```bash
cd backend
./.venv/Scripts/python.exe -m pip install -e ".[prod]"
./run_prod.ps1
```

`run_prod.ps1` reads `DJANGO_SECRET_KEY_PROD` from a persistent User
environment variable — set it once:

```powershell
[Environment]::SetEnvironmentVariable("DJANGO_SECRET_KEY_PROD", "<run: python -c 'import secrets; print(secrets.token_urlsafe(50))'>", "User")
```

Note this only takes effect in *new* processes started after you set it — a
shell (or Scheduled Task) that was already running won't see it until
restarted.

It serves on **port 8001**, not 8000 — 8000 is this machine's usual
`manage.py runserver` dev port, kept free so dev and prod can run side by
side. Bound to `127.0.0.1` on purpose: reachable only via the tunnel or this
machine, never the LAN.

## 3. Auto-start: Scheduled Tasks for both processes

One-time setup, from an **Administrator** PowerShell (registering an
`AtStartup` trigger needs elevation; a plain `AtLogOn` one doesn't, which is
how this went sideways the first time — see above):

```powershell
cd D:\Doslan\Desktop\LifU\backend
.\setup-autostart.ps1
```

This registers both `LifU-Backend` and `LifU-Tunnel` as Scheduled Tasks
(`AtStartup` trigger, `S4U` logon as this user, auto-restart up to 5 times on
crash), then starts them immediately and runs a health check so you don't
have to reboot to find out if it worked. Safe to re-run any time — `-Force`
overwrites the existing registration.

To start both right now without a reboot: `Start-ScheduledTask -TaskName
"LifU-Backend"` and `... "LifU-Tunnel"`. To check they're actually up:
`Get-NetTCPConnection -LocalPort 8001` should show waitress listening, and
`curl https://lifu-api.doslan.com/api/health` should return `{"ok":true}`.

If you ever start the backend manually while the Scheduled Task is also
running, you'll get a silent port-8001 conflict — one instance wins the bind,
the other exits. Stop one before starting the other by hand.

If both tasks are `Running` but the health check still fails, check
`Microsoft-Windows-TaskScheduler/Operational` in Event Viewer (enable it
first if needed: `wevtutil sl Microsoft-Windows-TaskScheduler/Operational
/e:true`, elevated) — it'll show whether the task actually launched the
process or was blocked.

Give the tunnel's DNS record a few minutes after first creating a hostname
before concluding something's wrong — edge certificate issuance for a brand
new hostname isn't instant.

## 4. Cloudflare Tunnel setup (one-time)

```bash
winget install --id Cloudflare.cloudflared
cloudflared tunnel login          # opens your browser, pick the doslan.com zone
cloudflared tunnel create lifu-backend
cloudflared tunnel route dns lifu-backend lifu-api.doslan.com
```

Then `%USERPROFILE%\.cloudflared\config.yml`:

```yaml
tunnel: <TUNNEL_ID from `tunnel create`>
credentials-file: C:\Users\<you>\.cloudflared\<TUNNEL_ID>.json
ingress:
  - hostname: lifu-api.doslan.com
    service: http://localhost:8001
  - service: http_status:404
```

## 5. Frontend: deploy to the Worker

The Cloudflare dashboard's "Workers & Pages → Create" defaults to a plain
Worker with a "Hello World" template, not a Pages project connected to git —
easy to hit by accident. Once that happens, the simplest fix is to just
deploy the actual build to that Worker via Workers Static Assets, rather than
re-do it as Pages:

```bash
cd frontend
npm run build          # picks up frontend/.env.production (VITE_API_BASE_URL)
npx wrangler@3 deploy  # wrangler 4 needs Node 22+; this machine has Node 20
```

`frontend/wrangler.jsonc` (committed) points `assets.directory` at `dist`,
sets SPA fallback so client-side routes survive a hard refresh, and declares
`lifu.doslan.com` as a custom domain — `wrangler deploy` provisions the DNS
record and certificate for that automatically. First-time auth: `npx
wrangler@3 login`.

This uploads a locally-built artifact rather than having Cloudflare build
from git, so there's no separate dashboard build step or Pages-style
environment variable to configure — `VITE_API_BASE_URL` is already baked into
the build from `frontend/.env.production` before it's ever uploaded.

Redeploying after a change is just `npm run build && npx wrangler@3 deploy`
again.

## 6. Verify

- `https://lifu-api.doslan.com/api/health` — backend reachable through the tunnel.
- `https://lifu.doslan.com` — frontend loads, login gate appears.
- Log in with the real `OWNER_PASSWORD`, confirm the session cookie survives
  a reload (that's the Lax-cross-subdomain cookie working) — **must** be
  tested on `lifu.doslan.com`, not the `*.workers.dev` URL (see above).
- A friend link (`https://lifu.doslan.com/<name>`) opens the trial sandbox.
- After a fresh reboot: log in to Windows, wait ~10s, re-run the health
  check above to confirm both Scheduled Tasks actually started.

## Rollback

`npx wrangler@3 deployments list` (from `frontend/`) shows prior Worker
versions; `wrangler rollback <version-id>` reverts. The backend has no
equivalent; it's one SQLite file (`SQLITE_PATH`), so back it up before risky
changes.
