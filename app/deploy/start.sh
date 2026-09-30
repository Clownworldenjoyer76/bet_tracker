#!/usr/bin/env sh
set -eu

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.production}"
export DJANGO_STRICT_PRODUCTION_CONFIG="true"

python scripts/check_production_config.py --strict

PORT="${PORT:-8000}"
WEB_CONCURRENCY="${WEB_CONCURRENCY:-2}"
GUNICORN_THREADS="${GUNICORN_THREADS:-4}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-60}"

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY}" \
  --threads "${GUNICORN_THREADS}" \
  --timeout "${GUNICORN_TIMEOUT}" \
  --access-logfile - \
  --error-logfile - \
  --capture-output
