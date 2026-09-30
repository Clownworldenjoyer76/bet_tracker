#!/usr/bin/env sh
set -eu

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.production}"
export DJANGO_STRICT_PRODUCTION_CONFIG="true"

python scripts/check_production_config.py --strict
python scripts/sync_frontend.py
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py check --deploy
