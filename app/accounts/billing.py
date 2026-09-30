from datetime import datetime, timezone as datetime_timezone

import stripe
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .entitlements import ensure_user_subscription
from .models import (
    BillingCustomer,
    BillingEvent,
    BillingSubscription,
    SubscriptionPlan,
    User,
    UserSubscription,
)


class BillingConfigurationError(RuntimeError):
    pass


class BillingStateError(RuntimeError):
    pass


STRIPE_PROVIDER = BillingCustomer.PROVIDER_STRIPE


def _get(obj, key, default=None):
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(key, default)

    getter = getattr(obj, "get", None)
    if callable(getter):
        try:
            return getter(key, default)
        except TypeError:
            pass

    return getattr(obj, key, default)


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return list(value)


def _metadata_value(obj, key):
    metadata = _get(obj, "metadata", {}) or {}
    return _get(metadata, key)


def _timestamp_to_datetime(value):
    if value in (None, ""):
        return None

    try:
        value = int(value)
    except (TypeError, ValueError):
        return None

    return datetime.fromtimestamp(value, tz=datetime_timezone.utc)


def stripe_checkout_configured():
    return bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_PRO_PRICE_ID)


def stripe_webhook_configured():
    return bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_WEBHOOK_SECRET)


def _configure_stripe():
    if not settings.STRIPE_SECRET_KEY:
        raise BillingConfigurationError("Stripe secret key is not configured.")
    stripe.api_key = settings.STRIPE_SECRET_KEY


def get_stripe_customer(user):
    return BillingCustomer.objects.filter(
        user=user,
        provider=STRIPE_PROVIDER,
    ).first()


@transaction.atomic
def ensure_stripe_customer(user):
    existing = get_stripe_customer(user)
    if existing:
        return existing

    _configure_stripe()

    customer = stripe.Customer.create(
        email=user.email,
        metadata={
            "user_id": str(user.pk),
        },
    )

    return BillingCustomer.objects.create(
        user=user,
        provider=STRIPE_PROVIDER,
        external_customer_id=customer.id,
    )


def create_checkout_session(user, success_url, cancel_url):
    if not stripe_checkout_configured():
        raise BillingConfigurationError(
            "Stripe Checkout is not configured."
        )

    customer = ensure_stripe_customer(user)
    _configure_stripe()

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer.external_customer_id,
        line_items=[
            {
                "price": settings.STRIPE_PRO_PRICE_ID,
                "quantity": 1,
            }
        ],
        client_reference_id=str(user.pk),
        metadata={
            "user_id": str(user.pk),
            "plan_slug": "pro",
        },
        subscription_data={
            "metadata": {
                "user_id": str(user.pk),
                "plan_slug": "pro",
            }
        },
        success_url=success_url,
        cancel_url=cancel_url,
    )

    if not getattr(session, "url", None):
        raise BillingStateError(
            "Stripe Checkout did not return a redirect URL."
        )

    return session


def create_portal_session(user, return_url):
    customer = get_stripe_customer(user)
    if not customer:
        raise BillingStateError(
            "No Stripe billing customer is linked to this account."
        )

    _configure_stripe()

    params = {
        "customer": customer.external_customer_id,
        "return_url": return_url,
    }

    if settings.STRIPE_PORTAL_CONFIGURATION_ID:
        params["configuration"] = settings.STRIPE_PORTAL_CONFIGURATION_ID

    session = stripe.billing_portal.Session.create(**params)

    if not getattr(session, "url", None):
        raise BillingStateError(
            "Stripe customer portal did not return a redirect URL."
        )

    return session


def _subscription_price_id(subscription):
    items = _get(subscription, "items")
    data = _get(items, "data", []) or []

    for item in _as_list(data):
        price = _get(item, "price")
        price_id = _get(price, "id")
        if price_id:
            return str(price_id)

    return ""


def _subscription_period_end(subscription):
    direct = _get(subscription, "current_period_end")
    if direct:
        return _timestamp_to_datetime(direct)

    items = _get(subscription, "items")
    data = _get(items, "data", []) or []

    for item in _as_list(data):
        value = _get(item, "current_period_end")
        if value:
            return _timestamp_to_datetime(value)

    return None


def _internal_status(external_status):
    mapping = {
        "active": UserSubscription.Status.ACTIVE,
        "trialing": UserSubscription.Status.TRIALING,
        "past_due": UserSubscription.Status.PAST_DUE,
        "canceled": UserSubscription.Status.CANCELED,
        "unpaid": UserSubscription.Status.INACTIVE,
        "incomplete": UserSubscription.Status.INACTIVE,
        "incomplete_expired": UserSubscription.Status.INACTIVE,
        "paused": UserSubscription.Status.INACTIVE,
    }
    return mapping.get(
        str(external_status or "").lower(),
        UserSubscription.Status.INACTIVE,
    )


def _user_from_subscription(subscription):
    customer_id = _get(subscription, "customer")
    if hasattr(customer_id, "id"):
        customer_id = customer_id.id

    customer = None
    if customer_id:
        customer = BillingCustomer.objects.filter(
            provider=STRIPE_PROVIDER,
            external_customer_id=str(customer_id),
        ).select_related("user").first()

    if customer:
        return customer.user

    user_id = _metadata_value(subscription, "user_id")
    if not user_id:
        return None

    try:
        user = User.objects.get(pk=int(user_id))
    except (TypeError, ValueError, User.DoesNotExist):
        return None

    if customer_id:
        BillingCustomer.objects.update_or_create(
            user=user,
            provider=STRIPE_PROVIDER,
            defaults={
                "external_customer_id": str(customer_id),
            },
        )

    return user


@transaction.atomic
def sync_subscription_object(subscription):
    external_subscription_id = _get(subscription, "id")
    if not external_subscription_id:
        raise BillingStateError(
            "Subscription event has no external subscription ID."
        )

    user = _user_from_subscription(subscription)
    if not user:
        raise BillingStateError(
            "Could not map Stripe subscription to a local user."
        )

    canonical = ensure_user_subscription(user)
    pro_plan = SubscriptionPlan.objects.get(slug="pro")

    external_status = str(_get(subscription, "status", "") or "")
    external_price_id = _subscription_price_id(subscription)
    internal_status = _internal_status(external_status)

    canonical.plan = (
        pro_plan
        if external_price_id == settings.STRIPE_PRO_PRICE_ID
        else SubscriptionPlan.objects.get(slug="free")
    )
    canonical.status = internal_status
    canonical.ends_at = _subscription_period_end(subscription)
    canonical.save(
        update_fields=(
            "plan",
            "status",
            "ends_at",
            "updated_at",
        )
    )

    BillingSubscription.objects.filter(
        user_subscription=canonical,
        provider=STRIPE_PROVIDER,
        is_current=True,
    ).exclude(
        external_subscription_id=str(external_subscription_id)
    ).update(is_current=False)

    billing_subscription, _ = BillingSubscription.objects.update_or_create(
        external_subscription_id=str(external_subscription_id),
        defaults={
            "user_subscription": canonical,
            "provider": STRIPE_PROVIDER,
            "external_price_id": external_price_id,
            "external_status": external_status,
            "current_period_end": _subscription_period_end(subscription),
            "cancel_at_period_end": bool(
                _get(subscription, "cancel_at_period_end", False)
            ),
            "is_current": True,
        },
    )

    return billing_subscription


@transaction.atomic
def link_checkout_session(session):
    user_id = _get(session, "client_reference_id") or _metadata_value(
        session,
        "user_id",
    )
    customer_id = _get(session, "customer")

    if hasattr(customer_id, "id"):
        customer_id = customer_id.id

    if not user_id or not customer_id:
        raise BillingStateError(
            "Checkout completion is missing user or customer linkage."
        )

    try:
        user = User.objects.get(pk=int(user_id))
    except (TypeError, ValueError, User.DoesNotExist) as exc:
        raise BillingStateError(
            "Checkout completion references an unknown user."
        ) from exc

    BillingCustomer.objects.update_or_create(
        user=user,
        provider=STRIPE_PROVIDER,
        defaults={
            "external_customer_id": str(customer_id),
        },
    )

    return user


@transaction.atomic
def mark_invoice_payment_failed(invoice):
    subscription_id = _get(invoice, "subscription")
    if hasattr(subscription_id, "id"):
        subscription_id = subscription_id.id

    if not subscription_id:
        parent = _get(invoice, "parent")
        subscription_details = _get(parent, "subscription_details")
        subscription_id = _get(subscription_details, "subscription")

    if not subscription_id:
        return False

    billing_subscription = BillingSubscription.objects.filter(
        provider=STRIPE_PROVIDER,
        external_subscription_id=str(subscription_id),
        is_current=True,
    ).select_related("user_subscription").first()

    if not billing_subscription:
        return False

    canonical = billing_subscription.user_subscription
    canonical.status = UserSubscription.Status.PAST_DUE
    canonical.save(update_fields=("status", "updated_at"))

    billing_subscription.external_status = "past_due"
    billing_subscription.save(
        update_fields=("external_status", "updated_at")
    )
    return True


def process_stripe_event(event):
    event_id = str(_get(event, "id", "") or "")
    event_type = str(_get(event, "type", "") or "")
    livemode = bool(_get(event, "livemode", False))

    if not event_id or not event_type:
        raise BillingStateError("Stripe event is missing an ID or type.")

    record, _ = BillingEvent.objects.get_or_create(
        provider=STRIPE_PROVIDER,
        external_event_id=event_id,
        defaults={
            "event_type": event_type,
            "livemode": livemode,
        },
    )

    if record.processed_at:
        return record

    data = _get(event, "data", {}) or {}
    obj = _get(data, "object", {}) or {}

    try:
        if event_type == "checkout.session.completed":
            link_checkout_session(obj)

        elif event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        }:
            sync_subscription_object(obj)

        elif event_type == "invoice.payment_failed":
            mark_invoice_payment_failed(obj)

        record.event_type = event_type
        record.livemode = livemode
        record.last_error = ""
        record.processed_at = timezone.now()
        record.save(
            update_fields=(
                "event_type",
                "livemode",
                "last_error",
                "processed_at",
            )
        )
        return record

    except Exception as exc:
        record.event_type = event_type
        record.livemode = livemode
        record.last_error = str(exc)[:4000]
        record.save(
            update_fields=(
                "event_type",
                "livemode",
                "last_error",
            )
        )
        raise


def billing_account_context(user):
    customer = get_stripe_customer(user)
    canonical = ensure_user_subscription(user)
    external = canonical.billing_subscriptions.filter(
        provider=STRIPE_PROVIDER,
        is_current=True,
    ).first()

    return {
        "billing_checkout_configured": stripe_checkout_configured(),
        "billing_webhook_configured": stripe_webhook_configured(),
        "billing_customer_linked": customer is not None,
        "billing_external_status": (
            external.external_status if external else ""
        ),
        "billing_cancel_at_period_end": (
            external.cancel_at_period_end if external else False
        ),
        "billing_current_period_end": (
            external.current_period_end if external else None
        ),
    }


def reconcile_user_from_stripe(user):
    customer = get_stripe_customer(user)
    if not customer:
        return 0

    _configure_stripe()

    subscriptions = stripe.Subscription.list(
        customer=customer.external_customer_id,
        status="all",
        limit=100,
    )

    rows = getattr(subscriptions, "data", None)
    if rows is None and isinstance(subscriptions, dict):
        rows = subscriptions.get("data", [])

    count = 0
    for subscription in rows or []:
        if _metadata_value(subscription, "user_id") in (None, ""):
            try:
                subscription.metadata["user_id"] = str(user.pk)
            except Exception:
                pass
        sync_subscription_object(subscription)
        count += 1

    return count
