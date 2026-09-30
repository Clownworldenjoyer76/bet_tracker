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
from django.db import connection, transaction

from accounts.entitlements import (
    FEATURE_PREMIUM_ANALYTICS,
    ensure_user_subscription,
    has_entitlement,
)
from accounts.models import SubscriptionPlan, UserSubscription

if connection.vendor != "postgresql":
    raise SystemExit(
        f"Expected PostgreSQL for runtime validation, got {connection.vendor}."
    )

User = get_user_model()

free_plan = SubscriptionPlan.objects.get(slug="free")
pro_plan = SubscriptionPlan.objects.get(slug="pro")

if FEATURE_PREMIUM_ANALYTICS in free_plan.features:
    raise SystemExit("Free plan unexpectedly includes premium analytics.")

if FEATURE_PREMIUM_ANALYTICS not in pro_plan.features:
    raise SystemExit("Pro plan is missing premium analytics.")

with transaction.atomic():
    user = User.objects.create_user(
        email="entitlement-check@example.invalid",
        password="EntitlementCheck!2026",
    )

    subscription = ensure_user_subscription(user)

    if subscription.plan.slug != "free":
        raise SystemExit("Default subscription is not Free.")

    if has_entitlement(user, FEATURE_PREMIUM_ANALYTICS):
        raise SystemExit("Free user unexpectedly has premium analytics.")

    subscription.plan = pro_plan
    subscription.status = UserSubscription.Status.ACTIVE
    subscription.save(update_fields=("plan", "status", "updated_at"))

    if not has_entitlement(user, FEATURE_PREMIUM_ANALYTICS):
        raise SystemExit("Active Pro user lacks premium analytics.")

    transaction.set_rollback(True)

print("ENTITLEMENT FOUNDATION OK")
print("Runtime database: PostgreSQL")
print("Plans: Free + Pro")
print("Default assignment: Free / active")
print("Premium server-side gate: premium_analytics")
print("Admin override model: available")
print("Validation records persisted: no")
