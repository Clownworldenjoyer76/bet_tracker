import os

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F401,F403


def env_bool(name, default=False):
    raw = os.getenv(name)
    if raw is None:
        return bool(default)

    return raw.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def env_csv(name):
    return [
        value.strip()
        for value in os.getenv(name, "").split(",")
        if value.strip()
    ]


# Production is never permitted to inherit local DEBUG=True.
DEBUG = False

# Production values remain environment-controlled. The strict deployment
# validation below prevents startup through the supplied deployment scripts
# when required values are absent.
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    SECRET_KEY,
).strip()

configured_hosts = env_csv("DJANGO_ALLOWED_HOSTS")
if configured_hosts:
    ALLOWED_HOSTS = configured_hosts

CSRF_TRUSTED_ORIGINS = env_csv("DJANGO_CSRF_TRUSTED_ORIGINS")

CORS_ALLOWED_ORIGINS = env_csv("DJANGO_CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = env_bool("DJANGO_CORS_ALLOW_CREDENTIALS", False)

STATIC_ROOT = BASE_DIR / "staticfiles"

MIDDLEWARE = list(MIDDLEWARE)
security_index = MIDDLEWARE.index(
    "django.middleware.security.SecurityMiddleware"
)
whitenoise_middleware = "whitenoise.middleware.WhiteNoiseMiddleware"

if whitenoise_middleware not in MIDDLEWARE:
    MIDDLEWARE.insert(
        security_index + 1,
        whitenoise_middleware,
    )

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

WHITENOISE_MAX_AGE = int(
    os.getenv("WHITENOISE_MAX_AGE", "31536000")
)

SECURE_SSL_REDIRECT = env_bool(
    "DJANGO_SECURE_SSL_REDIRECT",
    True,
)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

SECURE_HSTS_SECONDS = int(
    os.getenv("DJANGO_HSTS_SECONDS", "0")
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "DJANGO_HSTS_INCLUDE_SUBDOMAINS",
    False,
)
SECURE_HSTS_PRELOAD = env_bool(
    "DJANGO_HSTS_PRELOAD",
    False,
)

if env_bool("DJANGO_TRUST_PROXY_SSL_HEADER", False):
    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    EMAIL_BACKEND,
).strip()
EMAIL_HOST = os.getenv("EMAIL_HOST", "").strip()
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "").strip()
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)
SERVER_EMAIL = os.getenv(
    "SERVER_EMAIL",
    DEFAULT_FROM_EMAIL,
).strip()

LOG_LEVEL = os.getenv(
    "DJANGO_LOG_LEVEL",
    "INFO",
).strip().upper()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": (
                "%(asctime)s %(levelname)s "
                "%(name)s %(message)s"
            ),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}


def production_configuration_errors():
    errors = []

    if not SECRET_KEY:
        errors.append("DJANGO_SECRET_KEY is required.")
    elif SECRET_KEY == "development-only-change-before-production":
        errors.append(
            "DJANGO_SECRET_KEY still uses the development fallback."
        )

    if not ALLOWED_HOSTS:
        errors.append("DJANGO_ALLOWED_HOSTS must contain at least one host.")

    if "*" in ALLOWED_HOSTS:
        errors.append(
            "DJANGO_ALLOWED_HOSTS must not use a wildcard in production."
        )

    if not CSRF_TRUSTED_ORIGINS:
        errors.append(
            "DJANGO_CSRF_TRUSTED_ORIGINS must contain the HTTPS site origin."
        )
    else:
        insecure_origins = [
            origin
            for origin in CSRF_TRUSTED_ORIGINS
            if not origin.lower().startswith("https://")
        ]
        if insecure_origins:
            errors.append(
                "DJANGO_CSRF_TRUSTED_ORIGINS must use HTTPS in production."
            )

    if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
        errors.append(
            "Production DATABASES must use PostgreSQL."
        )

    if not SESSION_COOKIE_SECURE:
        errors.append("SESSION_COOKIE_SECURE must be enabled.")

    if not CSRF_COOKIE_SECURE:
        errors.append("CSRF_COOKIE_SECURE must be enabled.")

    if not SECURE_SSL_REDIRECT:
        errors.append("SECURE_SSL_REDIRECT must be enabled.")

    return errors


if env_bool("DJANGO_STRICT_PRODUCTION_CONFIG", False):
    configuration_errors = production_configuration_errors()
    if configuration_errors:
        raise ImproperlyConfigured(
            "Invalid production configuration: "
            + " ".join(configuration_errors)
        )
