import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-secret-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    "api",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]

ROOT_URLCONF = "lifu.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
            ],
        },
    },
]

WSGI_APPLICATION = "lifu.wsgi.application"
ASGI_APPLICATION = "lifu.asgi.application"

# No relational database is used at all: game data lives behind the repository
# abstraction (ARCHITECTURE.md §6) and the owner session is a signed cookie,
# so there is nothing to migrate and nothing to back up here.
DATABASES = {}

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 days — this is a single-user game

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("TIMEZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "api.authentication.GameAuthentication",
    ],
    # Game endpoints are owner-or-trial by default; public ones opt out with
    # permission_classes = [].
    "DEFAULT_PERMISSION_CLASSES": [
        "api.permissions.GamePermission",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "api.errors.exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "LifU API",
    "DESCRIPTION": "Gamified productivity app — task valuation, rewards, treasures.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

CORS_ALLOWED_ORIGINS = [
    o for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o
]

# --- LifU domain configuration (ARCHITECTURE.md §11) ---
OWNER_PASSWORD = os.environ.get("OWNER_PASSWORD", "")
REPO_BACKEND = os.environ.get("REPO_BACKEND", "memory")  # "firebase" | "memory"
FIREBASE_CREDENTIALS = os.environ.get("FIREBASE_CREDENTIALS", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
DEVIANTART_CLIENT_ID = os.environ.get("DEVIANTART_CLIENT_ID", "")
DEVIANTART_CLIENT_SECRET = os.environ.get("DEVIANTART_CLIENT_SECRET", "")
JAMENDO_CLIENT_ID = os.environ.get("JAMENDO_CLIENT_ID", "")
FRIEND_LINK_BASE_URL = os.environ.get("FRIEND_LINK_BASE_URL", "https://lifu.doslan.com").rstrip(
    "/"
)
