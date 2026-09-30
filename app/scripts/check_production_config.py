import argparse
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.production",
)

import django

django.setup()

from django.conf import settings
from django.urls import reverse

from config.production import production_configuration_errors


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Validate the host-independent Django production foundation."
        )
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Fail when deployment-specific environment variables "
            "are not production-ready."
        ),
    )
    args = parser.parse_args()

    structural_errors = []

    if settings.DEBUG:
        structural_errors.append("DEBUG must be False.")

    if "whitenoise.middleware.WhiteNoiseMiddleware" not in settings.MIDDLEWARE:
        structural_errors.append(
            "WhiteNoise middleware is not installed."
        )

    if not getattr(settings, "STATIC_ROOT", None):
        structural_errors.append("STATIC_ROOT is not configured.")

    if not settings.SESSION_COOKIE_SECURE:
        structural_errors.append(
            "SESSION_COOKIE_SECURE must be enabled."
        )

    if not settings.CSRF_COOKIE_SECURE:
        structural_errors.append(
            "CSRF_COOKIE_SECURE must be enabled."
        )

    if not settings.SECURE_CONTENT_TYPE_NOSNIFF:
        structural_errors.append(
            "SECURE_CONTENT_TYPE_NOSNIFF must be enabled."
        )

    frontend_index = (
        Path(settings.FRONTEND_DIST_DIR) / "index.html"
    )
    if not frontend_index.is_file():
        structural_errors.append(
            f"Built frontend is missing: {frontend_index}"
        )

    if reverse("healthz") != "/healthz":
        structural_errors.append("healthz route is not registered.")

    if reverse("readyz") != "/readyz":
        structural_errors.append("readyz route is not registered.")

    deployment_errors = production_configuration_errors()

    if structural_errors:
        print("PRODUCTION FOUNDATION INVALID")
        for error in structural_errors:
            print(f"ERROR: {error}")
        return 1

    if args.strict and deployment_errors:
        print("PRODUCTION CONFIGURATION NOT READY")
        for error in deployment_errors:
            print(f"ERROR: {error}")
        return 1

    print("PRODUCTION FOUNDATION OK")
    print("Settings module: config.production")
    print("DEBUG: false")
    print("Application server: Gunicorn")
    print("Django static files: WhiteNoise")
    print("Health endpoint: /healthz")
    print("Readiness endpoint: /readyz")
    print("Secure session cookie: enabled")
    print("Secure CSRF cookie: enabled")
    print(
        "HSTS: staged / environment-controlled "
        f"({settings.SECURE_HSTS_SECONDS}s)"
    )

    if deployment_errors:
        print("Deployment-specific configuration: pending")
        for error in deployment_errors:
            print(f"PENDING: {error}")
    else:
        print("Deployment-specific configuration: ready")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
