import os
import sys
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.contrib.auth import get_user_model
from django.db import connection, transaction

from accounts.models import UserPreferences

User = get_user_model()

if connection.vendor != "postgresql":
    raise SystemExit(
        f"Expected PostgreSQL for runtime validation, got {connection.vendor}."
    )

with transaction.atomic():
    user = User.objects.create_user(
        email="kelly-private-check@example.invalid",
        password="KellyPrivateCheck!2026",
    )
    preferences = UserPreferences.objects.create(
        user=user,
        timezone="America/Chicago",
        bankroll=Decimal("12345.67"),
        kelly_fraction=Decimal("0.50"),
    )

    fetched = UserPreferences.objects.select_related("user").get(user=user)

    if fetched.bankroll != Decimal("12345.67"):
        raise SystemExit("Private bankroll persistence validation failed.")

    if fetched.kelly_fraction != Decimal("0.50"):
        raise SystemExit("Kelly fraction persistence validation failed.")

    if fetched.user_id != user.pk:
        raise SystemExit("User ownership validation failed.")

    transaction.set_rollback(True)

print("PRIVATE KELLY PREFERENCES OK")
print("Runtime database: PostgreSQL")
print("Bankroll ownership: accounts.User -> UserPreferences (1:1)")
print("Kelly fraction ownership: accounts.User -> UserPreferences (1:1)")
print("Validation records persisted: no")
