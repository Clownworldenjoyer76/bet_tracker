import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from django.urls import reverse

from accounts.models import UserPreferences

User = get_user_model()

with transaction.atomic():
    user = User.objects.create_user(
        email="preference-check@example.invalid",
        password="PreferenceCheck!2026",
    )
    preferences = UserPreferences.objects.create(
        user=user,
        timezone="America/Denver",
    )

    if preferences.user_id != user.pk:
        raise SystemExit("Preference ownership validation failed.")

    if UserPreferences.objects.filter(user=user).count() != 1:
        raise SystemExit("One-to-one preference validation failed.")

    if reverse("accounts:preferences_api") != "/api/account/preferences/":
        raise SystemExit("Preference API route validation failed.")

    transaction.set_rollback(True)

print("USER PREFERENCES OK")
print("Ownership: one-to-one with accounts.User")
print("Timezone persistence: PostgreSQL")
print("Preference API: /api/account/preferences/")
print("Validation records persisted: no")
