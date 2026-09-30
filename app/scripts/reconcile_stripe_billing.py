import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.conf import settings

from accounts.billing import (
    BillingConfigurationError,
    reconcile_user_from_stripe,
)
from accounts.models import BillingCustomer


if not settings.STRIPE_SECRET_KEY:
    raise SystemExit(
        "STRIPE_SECRET_KEY is not configured. Reconciliation did not run."
    )

customers = BillingCustomer.objects.filter(provider="stripe").select_related(
    "user"
)

processed_customers = 0
processed_subscriptions = 0

for customer in customers.iterator():
    try:
        count = reconcile_user_from_stripe(customer.user)
    except BillingConfigurationError as exc:
        raise SystemExit(str(exc)) from exc

    processed_customers += 1
    processed_subscriptions += count

print("STRIPE RECONCILIATION COMPLETE")
print(f"Customers checked: {processed_customers}")
print(f"Subscriptions synchronized: {processed_subscriptions}")
