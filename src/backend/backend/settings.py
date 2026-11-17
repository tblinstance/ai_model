"""Django settings for AI-Model backend control plane."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parents[2] / ".env")

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-ai-model-fallback-secret",
)
BILLING_SECRET_KEY = os.getenv("BILLING_SECRET_KEY", SECRET_KEY)
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if h.strip()
]
if "testserver" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("testserver")
if "*" not in ALLOWED_HOSTS and DEBUG:
    ALLOWED_HOSTS.append("*")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "djoser",
    # Domain apps
    "billing",
    "transactions",
    "api",
    "Agent",
    "quota",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"
ASGI_APPLICATION = "backend.asgi.application"

def _build_databases() -> dict[str, dict[str, object]]:
    """Build Django database settings from DATABASE_URL or POSTGRES_* env vars."""
    db_engine = os.getenv("DB_ENGINE", "").strip().lower()
    database_url = os.getenv("DATABASE_URL", "").strip()
    conn_max_age = int(os.getenv("DB_CONN_MAX_AGE", "60"))

    if db_engine in ("sqlite", "sqlite3"):
        return {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": BASE_DIR / "db.sqlite3",
            }
        }

    run_socket_dir = BASE_DIR.parent / "base" / ".run"
    if database_url.startswith(("postgres://", "postgresql://")):
        parsed = urlparse(database_url)
        query_params = parse_qs(parsed.query)
        options = {k: v[0] for k, v in query_params.items() if v}
        default_host = os.getenv("POSTGRES_HOST") or parsed.hostname or "127.0.0.1"
        if default_host in ("127.0.0.1", "localhost") and (run_socket_dir / ".s.PGSQL.5433").exists():
            default_host = str(run_socket_dir)
        config: dict[str, object] = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(parsed.path.lstrip("/")) or os.getenv("POSTGRES_DB", "ai_model"),
            "USER": unquote(parsed.username or "") or os.getenv("POSTGRES_USER", "ai_model"),
            "PASSWORD": unquote(parsed.password or "") or os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": default_host,
            "PORT": str(parsed.port or os.getenv("POSTGRES_PORT", "5433")),
            "CONN_MAX_AGE": conn_max_age,
            "CONN_HEALTH_CHECKS": True,
        }
        if options:
            config["OPTIONS"] = options
        return {"default": config}

    if db_engine in ("postgres", "postgresql") or os.getenv("POSTGRES_DB"):
        default_host = os.getenv("POSTGRES_HOST", "127.0.0.1")
        if default_host in ("127.0.0.1", "localhost") and (run_socket_dir / ".s.PGSQL.5433").exists():
            default_host = str(run_socket_dir)
        return {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": os.getenv("POSTGRES_DB", "ai_model"),
                "USER": os.getenv("POSTGRES_USER", "ai_model"),
                "PASSWORD": os.getenv("POSTGRES_PASSWORD", "ai_model_dev_pass"),
                "HOST": default_host,
                "PORT": os.getenv("POSTGRES_PORT", "5433"),
                "CONN_MAX_AGE": conn_max_age,
                "CONN_HEALTH_CHECKS": True,
            }
        }

    return {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


DATABASES = _build_databases()

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/generated/"
MEDIA_ROOT = BASE_DIR.parent / "ai_engine" / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "DJANGO_CORS_ALLOWED_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8000,http://localhost:8000,http://127.0.0.1:5000,http://localhost:5000",
    ).split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "api.auth.SecretKeyAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

SIMPLE_JWT = {
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

DJOSER = {
    "LOGIN_FIELD": "username",
    "USER_CREATE_PASSWORD_RETYPE": False,
    "SEND_ACTIVATION_EMAIL": False,
    "SERIALIZERS": {},
}

FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://127.0.0.1:8001")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "ai-model-internal-dev-key")

DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024

