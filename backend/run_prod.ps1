# Runs the backend in production mode: DEBUG off, hosts locked to
# api.lifu.doslan.com, served by waitress instead of manage.py runserver.
#
# These overrides are scoped to this process only — they never touch the
# persistent environment, so a normal dev `manage.py runserver` elsewhere on
# this machine keeps using backend/.env (DEBUG=true) unaffected.
#
# DJANGO_SECRET_KEY_PROD must already exist as a persistent User environment
# variable (set once via [Environment]::SetEnvironmentVariable(...), not
# stored in this file or in git) — see docs/DEPLOY.md.

$ErrorActionPreference = "Stop"

if (-not $env:DJANGO_SECRET_KEY_PROD) {
    Write-Error "DJANGO_SECRET_KEY_PROD is not set. See docs/DEPLOY.md section 1."
    exit 1
}

$env:DJANGO_SECRET_KEY = $env:DJANGO_SECRET_KEY_PROD
$env:DJANGO_DEBUG = "false"
$env:DJANGO_ALLOWED_HOSTS = "api.lifu.doslan.com"
$env:CORS_ALLOWED_ORIGINS = "https://lifu.doslan.com"

Set-Location $PSScriptRoot
# Port 8001, not 8000 — 8000 is this machine's usual `manage.py runserver`
# dev port; keeping them apart means dev and prod can run side by side.
& "$PSScriptRoot\.venv\Scripts\waitress-serve.exe" --host=127.0.0.1 --port=8001 lifu.wsgi:application
