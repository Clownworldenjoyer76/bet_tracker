import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "development-only-change-before-production",
)

DEBUG = os.getenv("DJANGO_DEBUG", "true").strip().lower() in {
    "1", "true", "yes", "on"
}

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "DJANGO_ALLOWED_HOSTS",
        "127.0.0.1,localhost",
    ).split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "accounts",
    "siteapp",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DB_ENGINE = os.getenv("DB_ENGINE", "sqlite").strip().lower()

if DB_ENGINE in {"postgres", "postgresql"}:
    required_db_vars = {
        "DB_NAME": os.getenv("DB_NAME", "").strip(),
        "DB_USER": os.getenv("DB_USER", "").strip(),
        "DB_PASSWORD": os.getenv("DB_PASSWORD", ""),
        "DB_HOST": os.getenv("DB_HOST", "").strip(),
        "DB_PORT": os.getenv("DB_PORT", "5432").strip(),
    }

    missing = [key for key, value in required_db_vars.items() if not value]
    if missing:
        raise RuntimeError(
            "PostgreSQL is selected but required database settings are missing: "
            + ", ".join(missing)
        )

    db_options = {}
    sslmode = os.getenv("DB_SSLMODE", "").strip()
    if sslmode:
        db_options["sslmode"] = sslmode

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": required_db_vars["DB_NAME"],
            "USER": required_db_vars["DB_USER"],
            "PASSWORD": required_db_vars["DB_PASSWORD"],
            "HOST": required_db_vars["DB_HOST"],
            "PORT": required_db_vars["DB_PORT"],
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": db_options,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# The application PostgreSQL role intentionally does not have CREATEDB.
# Django's automated test runner therefore uses an isolated in-memory SQLite
# database. Normal commands, migrations, runtime traffic, and explicit database
# validation continue to use PostgreSQL.
if len(sys.argv) > 1 and sys.argv[1] == "test":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        )
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


LOGIN_URL = "/login.html"
LOGIN_REDIRECT_URL = "/account.html"
LOGOUT_REDIRECT_URL = "/login.html"

# Local development uses the console backend. Production SMTP is configured
# later through environment variables without changing account views.
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    "SportsModelHub <no-reply@localhost>",
)

# Stripe Billing. Hosted Checkout and the customer portal require only
# server-side credentials; no publishable key is needed for this integration.
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
STRIPE_PRO_PRICE_ID = os.getenv("STRIPE_PRO_PRICE_ID", "").strip()
STRIPE_PORTAL_CONFIGURATION_ID = os.getenv(
    "STRIPE_PORTAL_CONFIGURATION_ID",
    "",
).strip()


FRONTEND_SOURCE_DIR = BASE_DIR / "frontend" / "src"
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"



# SMH_EMAIL_SMTP_START
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost").strip()
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "").strip()
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "false").strip().lower() in {"1", "true", "yes", "on"}
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "false").strip().lower() in {"1", "true", "yes", "on"}
SERVER_EMAIL = os.getenv("SERVER_EMAIL", DEFAULT_FROM_EMAIL).strip()
# SMH_EMAIL_SMTP_END

# SMH_STATIC_START
STATIC_ROOT = BASE_DIR / "staticfiles"
if "whitenoise.middleware.WhiteNoiseMiddleware" not in MIDDLEWARE:
    MIDDLEWARE = list(MIDDLEWARE)
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
# SMH_STATIC_END


# SMH_ADMIN_TEMPLATES_START
TEMPLATES[0]["DIRS"] = list(TEMPLATES[0].get("DIRS", [])) + [BASE_DIR / "admin_templates"]
# SMH_ADMIN_TEMPLATES_END
