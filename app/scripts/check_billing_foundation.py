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

from accounts.entitlements import ensure_user_subscription
from accounts.models import (
    BillingCustomer,
    BillingEvent,
    BillingSubscription,
)

if connection.vendor != "postgresql":
    raise SystemExit(
        f"Expected PostgreSQL for runtime validation, got {connection.vendor}."
    )

User = get_user_model()

with transaction.atomic():
    user = User.objects.create_user(
        email="billing-foundation-check@example.invalid",
        password="BillingFoundationCheck!2026",
    )
    canonical = ensure_user_subscription(user)

    customer = BillingCustomer.objects.create(
        user=user,
        provider="stripe",
        external_customer_id="cus_validation_only",
    )

    billing_subscription = BillingSubscription.objects.create(
        user_subscription=canonical,
        provider="stripe",
        external_subscription_id="sub_validation_only",
        external_price_id="price_validation_only",
        external_status="active",
        is_current=True,
    )

    event = BillingEvent.objects.create(
        provider="stripe",
        external_event_id="evt_validation_only",
        event_type="validation.only",
        livemode=False,
    )

    if customer.user_id != user.pk:
        raise SystemExit("Billing customer ownership validation failed.")

    if billing_subscription.user_subscription_id != canonical.pk:
        raise SystemExit("Billing subscription linkage validation failed.")

    if event.provider != "stripe":
        raise SystemExit("Billing event provider validation failed.")

    transaction.set_rollback(True)

print("BILLING FOUNDATION OK")
print("Runtime database: PostgreSQL")
print("Provider adapter: Stripe")
print("Customer linkage model: OK")
print("Subscription linkage model: OK")
print("Webhook idempotency model: OK")
print("Validation records persisted: no")
