import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .billing import (
    BillingConfigurationError,
    BillingStateError,
    create_checkout_session,
    create_portal_session,
    process_stripe_event,
)


@login_required
@require_POST
def checkout_view(request):
    try:
        session = create_checkout_session(
            request.user,
            success_url=request.build_absolute_uri(
                "/account.html?billing=success"
            ),
            cancel_url=request.build_absolute_uri(
                "/account.html?billing=canceled"
            ),
        )
    except BillingConfigurationError as exc:
        return JsonResponse({"detail": str(exc)}, status=503)
    except BillingStateError as exc:
        return JsonResponse({"detail": str(exc)}, status=409)
    except stripe.StripeError:
        return JsonResponse(
            {"detail": "Stripe Checkout could not be created."},
            status=502,
        )

    return redirect(session.url)


@login_required
@require_POST
def portal_view(request):
    try:
        session = create_portal_session(
            request.user,
            return_url=request.build_absolute_uri("/account.html"),
        )
    except BillingConfigurationError as exc:
        return JsonResponse({"detail": str(exc)}, status=503)
    except BillingStateError as exc:
        return JsonResponse({"detail": str(exc)}, status=409)
    except stripe.StripeError:
        return JsonResponse(
            {"detail": "Stripe customer portal could not be created."},
            status=502,
        )

    return redirect(session.url)


@csrf_exempt
@require_POST
def stripe_webhook_view(request):
    if not settings.STRIPE_WEBHOOK_SECRET:
        return JsonResponse(
            {"detail": "Stripe webhook secret is not configured."},
            status=503,
        )

    signature = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(
            request.body,
            signature,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except (ValueError, stripe.SignatureVerificationError):
        return HttpResponse(status=400)

    try:
        process_stripe_event(event)
    except Exception:
        # A 5xx response tells Stripe to retry the event.
        return HttpResponse(status=500)

    return HttpResponse(status=200)
