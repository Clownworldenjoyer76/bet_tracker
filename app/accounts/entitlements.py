from functools import wraps

from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone

from .models import EntitlementOverride, SubscriptionPlan, UserSubscription


FREE_PLAN_SLUG = "free"
PRO_PLAN_SLUG = "pro"

FEATURE_ACCOUNT_PREFERENCES = "account_preferences"
FEATURE_KELLY_PRIVATE_SETTINGS = "kelly_private_settings"
FEATURE_PREMIUM_ANALYTICS = "premium_analytics"

KNOWN_FEATURES = (
    FEATURE_ACCOUNT_PREFERENCES,
    FEATURE_KELLY_PRIVATE_SETTINGS,
    FEATURE_PREMIUM_ANALYTICS,
)

ACTIVE_PAID_STATUSES = {
    UserSubscription.Status.ACTIVE,
    UserSubscription.Status.TRIALING,
}


def get_free_plan():
    return SubscriptionPlan.objects.get(slug=FREE_PLAN_SLUG)


@transaction.atomic
def ensure_user_subscription(user):
    if not user or not user.is_authenticated:
        raise ValueError("An authenticated user is required.")

    free_plan = get_free_plan()
    subscription, _ = UserSubscription.objects.get_or_create(
        user=user,
        defaults={
            "plan": free_plan,
            "status": UserSubscription.Status.ACTIVE,
        },
    )
    return subscription


def _active_overrides(user):
    now = timezone.now()
    return EntitlementOverride.objects.filter(user=user).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    )


def effective_features(user):
    if not user or not user.is_authenticated:
        return set()

    if user.is_superuser:
        return set(KNOWN_FEATURES)

    free_plan = get_free_plan()
    features = set(free_plan.features or [])

    subscription = ensure_user_subscription(user)

    if (
        subscription.status in ACTIVE_PAID_STATUSES
        and subscription.plan.is_active
    ):
        features.update(subscription.plan.features or [])

    for override in _active_overrides(user):
        if override.enabled:
            features.add(override.feature)
        else:
            features.discard(override.feature)

    return features


def has_entitlement(user, feature):
    return feature in effective_features(user)


def entitlement_summary(user):
    subscription = ensure_user_subscription(user)
    features = sorted(effective_features(user))

    return {
        "plan": {
            "slug": subscription.plan.slug,
            "name": subscription.plan.name,
        },
        "status": subscription.status,
        "status_label": subscription.get_status_display(),
        "features": features,
    }


def entitlement_api_required(feature):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse(
                    {
                        "detail": "Authentication required.",
                        "feature": feature,
                    },
                    status=401,
                )

            if not has_entitlement(request.user, feature):
                return JsonResponse(
                    {
                        "detail": "Entitlement required.",
                        "feature": feature,
                    },
                    status=403,
                )

            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
