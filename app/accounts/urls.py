from django.urls import path

from . import billing_views, contact, views

app_name = "accounts"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("index.html", views.home_view, name="home_index"),
    path("register.html", views.register_view, name="register"),
    path("login.html", views.EmailLoginView.as_view(), name="login"),
    path("logout.html", views.AccountLogoutView.as_view(), name="logout"),
    path("account.html", views.account_view, name="account"),
    path("contact.html", contact.contact_view, name="contact"),
    path(
        "billing/checkout/",
        billing_views.checkout_view,
        name="billing_checkout",
    ),
    path(
        "billing/portal/",
        billing_views.portal_view,
        name="billing_portal",
    ),
    path(
        "billing/webhook/",
        billing_views.stripe_webhook_view,
        name="billing_webhook",
    ),
    path(
        "api/account/preferences/",
        views.preferences_api,
        name="preferences_api",
    ),
    path(
        "api/account/entitlements/",
        views.entitlements_api,
        name="entitlements_api",
    ),
    path(
        "api/premium/analytics/",
        views.premium_analytics_access_api,
        name="premium_analytics_access_api",
    ),
    path(
        "password_reset.html",
        views.AccountPasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "password_reset_done.html",
        views.AccountPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>.html",
        views.AccountPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password_reset_complete.html",
        views.AccountPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
