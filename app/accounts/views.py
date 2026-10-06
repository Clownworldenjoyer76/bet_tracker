import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods

from .billing import billing_account_context
from .entitlements import (
    FEATURE_PREMIUM_ANALYTICS,
    ensure_user_subscription,
    entitlement_api_required,
    entitlement_summary,
)
from .forms import (
    EmailAuthenticationForm,
    RegistrationForm,
    UserPreferencesForm,
)
from .models import UserPreferences




def serialize_preferences(preferences, include_csrf=False, request=None):
    payload = {
        "authenticated": True,
        "timezone": preferences.timezone,
        "bankroll": (
            str(preferences.bankroll)
            if preferences.bankroll is not None
            else None
        ),
        "kelly_fraction": float(preferences.kelly_fraction),
    }

    if include_csrf and request is not None:
        payload["csrfToken"] = get_token(request)

    return payload



def preference_form_data(preferences, updates=None):
    data = {
        "timezone": preferences.timezone,
        "bankroll": (
            str(preferences.bankroll)
            if preferences.bankroll is not None
            else ""
        ),
        "kelly_fraction": f"{preferences.kelly_fraction:.2f}",
    }

    for key, value in (updates or {}).items():
        if key == "bankroll":
            data[key] = "" if value is None else str(value)
            continue

        if key == "kelly_fraction":
            try:
                data[key] = f"{Decimal(str(value)):.2f}"
            except (InvalidOperation, TypeError, ValueError):
                data[key] = str(value)
            continue

        data[key] = value

    return data

class EmailLoginView(LoginView):
    authentication_form = EmailAuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class AccountLogoutView(LogoutView):
    http_method_names = ["post", "options"]
    next_page = reverse_lazy("accounts:login")


class AccountPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/password_reset_email.txt"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class AccountPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class AccountPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class AccountPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


def register_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:account")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            ensure_user_subscription(user)
            login(
                request,
                user,
                backend="django.contrib.auth.backends.ModelBackend",
            )
            return redirect("accounts:account")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def account_view(request, template_name="accounts/account.html"):
    preferences, _ = UserPreferences.objects.get_or_create(user=request.user)
    saved = False

    if request.method == "POST":
        updates = {
            field: request.POST.get(field)
            for field in ("timezone", "bankroll", "kelly_fraction")
            if field in request.POST
        }
        form = UserPreferencesForm(
            preference_form_data(preferences, updates),
            instance=preferences,
        )
        if form.is_valid():
            form.save()
            saved = True
    else:
        form = UserPreferencesForm(instance=preferences)

    access = entitlement_summary(request.user)

    return render(
        request,
        template_name,
        {
            "preferences_form": form,
            "preferences_saved": saved,
            "access_plan": access["plan"],
            "access_status": access["status"],
            "access_status_label": access["status_label"],
            "access_features": access["features"],
            "billing_notice": request.GET.get("billing", ""),
            **billing_account_context(request.user),
        },
    )


@require_http_methods(["GET", "POST"])
def preferences_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False}, status=401)

    preferences, _ = UserPreferences.objects.get_or_create(user=request.user)

    if request.method == "GET":
        return JsonResponse(
            serialize_preferences(
                preferences,
                include_csrf=True,
                request=request,
            )
        )

    try:
        payload = json.loads(request.body or b"{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({"error": "JSON object required."}, status=400)

    allowed_fields = {"timezone", "bankroll", "kelly_fraction"}
    unknown_fields = sorted(set(payload) - allowed_fields)

    if unknown_fields:
        return JsonResponse(
            {
                "error": "Unknown preference fields.",
                "fields": unknown_fields,
            },
            status=400,
        )

    form = UserPreferencesForm(
        preference_form_data(preferences, payload),
        instance=preferences,
    )
    if not form.is_valid():
        return JsonResponse(
            {
                "error": "Invalid preferences.",
                "fields": form.errors.get_json_data(),
            },
            status=400,
        )

    updated = form.save()
    return JsonResponse(serialize_preferences(updated))



@require_http_methods(["GET"])
def entitlements_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False}, status=401)

    return JsonResponse(
        {
            "authenticated": True,
            **entitlement_summary(request.user),
        }
    )


@require_http_methods(["GET"])
@entitlement_api_required(FEATURE_PREMIUM_ANALYTICS)
def premium_analytics_access_api(request):
    return JsonResponse(
        {
            "access": True,
            "feature": FEATURE_PREMIUM_ANALYTICS,
        }
    )

from django.views.decorators.cache import never_cache


class HomeLoginView(EmailLoginView):
    template_name = "accounts/home_login.html"
    redirect_authenticated_user = False

    def get_success_url(self):
        return self.get_redirect_url() or "/"


@never_cache
def home_view(request):
    if request.user.is_authenticated:
        return account_view(request, template_name="accounts/home_account.html")

    return HomeLoginView.as_view()(request)
