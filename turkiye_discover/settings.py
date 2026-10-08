"""
Django settings for turkiye_discover.

Secrets and machine-specific values come from the .env file (never committed).
See .env.example for the list of variables.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
# In development any host is allowed, so the site can be opened from a phone on the same Wi-Fi.
ALLOWED_HOSTS = [h for h in os.getenv("DJANGO_ALLOWED_HOSTS", "*" if DEBUG else "localhost").split(",") if h]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "sources",
    "events",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "turkiye_discover.urls"

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

WSGI_APPLICATION = "turkiye_discover.wsgi.application"

# SQLite for development. On the server (stage 6) DATABASE_URL-style settings
# for PostgreSQL will be added here.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Persian interface; times are stored in UTC and shown in Istanbul time.
LANGUAGE_CODE = "fa"
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Data collection engine ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
EXTRACTION_MODEL = os.getenv("EXTRACTION_MODEL", "claude-haiku-5-5")
# Records below this confidence go to the manual review queue.
REVIEW_CONFIDENCE_THRESHOLD = float(os.getenv("REVIEW_CONFIDENCE_THRESHOLD", "0.75"))
# Monthly API budget in USD; extraction stops when it is reached.
MONTHLY_API_BUDGET_USD = float(os.getenv("MONTHLY_API_BUDGET_USD", "10"))
CRAWLER_USER_AGENT = os.getenv(
    "CRAWLER_USER_AGENT", "TurkiyeDiscoverBot/0.1 (+contact: PHONE_NUMBER)"
)
# Seconds to wait between two requests to the same site.
CRAWLER_DELAY_SECONDS = float(os.getenv("CRAWLER_DELAY_SECONDS", "3"))

WHATSAPP_NUMBER = os.getenv("WHATSAPP_NUMBER", "PHONE_NUMBER")
