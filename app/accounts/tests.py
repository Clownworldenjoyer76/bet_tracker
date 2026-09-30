from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.test import SimpleTestCase


class CustomUserConfigurationTests(SimpleTestCase):
    def test_email_is_login_identifier(self):
        user_model = get_user_model()
        self.assertEqual(user_model.USERNAME_FIELD, "email")
        self.assertEqual(user_model.REQUIRED_FIELDS, [])

    def test_username_field_is_removed(self):
        user_model = get_user_model()
        with self.assertRaises(FieldDoesNotExist):
            user_model._meta.get_field("username")

    def test_email_field_is_unique(self):
        user_model = get_user_model()
        self.assertTrue(user_model._meta.get_field("email").unique)


from django.urls import reverse

from .forms import EmailAuthenticationForm, RegistrationForm


class AccountRouteConfigurationTests(SimpleTestCase):
    def test_account_routes_are_root_html_routes(self):
        self.assertEqual(reverse("accounts:register"), "/register.html")
        self.assertEqual(reverse("accounts:login"), "/login.html")
        self.assertEqual(reverse("accounts:account"), "/account.html")
        self.assertEqual(
            reverse("accounts:password_reset"),
            "/password_reset.html",
        )

    def test_login_form_uses_email_input(self):
        form = EmailAuthenticationForm()
        self.assertEqual(form.fields["username"].label, "Email")
        self.assertEqual(form.fields["username"].widget.input_type, "email")

    def test_registration_form_targets_custom_user(self):
        self.assertEqual(RegistrationForm._meta.model, get_user_model())



from django.test import Client, TestCase

from .models import UserPreferences


class UserPreferencesTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="one@example.com",
            password="StrongPass!2026",
        )
        self.other_user = user_model.objects.create_user(
            email="two@example.com",
            password="StrongPass!2026",
        )

    def test_preferences_api_requires_authentication(self):
        response = self.client.get(reverse("accounts:preferences_api"))
        self.assertEqual(response.status_code, 401)

    def test_preferences_default_to_eastern(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:preferences_api"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["timezone"], "America/New_York")
        self.assertIsNone(payload["bankroll"])
        self.assertEqual(payload["kelly_fraction"], 1.0)

    def test_preferences_update_is_user_owned(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:preferences_api"),
            data='{"timezone":"America/Los_Angeles"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            UserPreferences.objects.get(user=self.user).timezone,
            "America/Los_Angeles",
        )

        self.client.force_login(self.other_user)
        other_response = self.client.get(reverse("accounts:preferences_api"))
        self.assertEqual(other_response.json()["timezone"], "America/New_York")

    def test_invalid_timezone_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:preferences_api"),
            data='{"timezone":"Invalid/Timezone"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_account_page_updates_preferences(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:account"),
            data={"timezone": "America/Chicago"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            UserPreferences.objects.get(user=self.user).timezone,
            "America/Chicago",
        )



class PrivateKellyPreferenceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="kelly@example.com",
            password="StrongPass!2026",
        )
        self.other_user = user_model.objects.create_user(
            email="other-kelly@example.com",
            password="StrongPass!2026",
        )

    def test_partial_api_update_preserves_other_preferences(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:preferences_api"),
            data='{"bankroll":"12500.50","kelly_fraction":0.5}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        prefs = UserPreferences.objects.get(user=self.user)
        self.assertEqual(str(prefs.bankroll), "12500.50")
        self.assertEqual(str(prefs.kelly_fraction), "0.50")
        self.assertEqual(prefs.timezone, "America/New_York")

        response = self.client.post(
            reverse("accounts:preferences_api"),
            data='{"timezone":"America/Denver"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        prefs.refresh_from_db()
        self.assertEqual(str(prefs.bankroll), "12500.50")
        self.assertEqual(str(prefs.kelly_fraction), "0.50")
        self.assertEqual(prefs.timezone, "America/Denver")

    def test_private_kelly_preferences_are_user_owned(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse("accounts:preferences_api"),
            data='{"bankroll":"5000.00","kelly_fraction":0.25}',
            content_type="application/json",
        )

        self.client.force_login(self.other_user)
        response = self.client.get(reverse("accounts:preferences_api"))
        payload = response.json()

        self.assertIsNone(payload["bankroll"])
        self.assertEqual(payload["kelly_fraction"], 1.0)

    def test_negative_bankroll_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:preferences_api"),
            data='{"bankroll":"-1.00"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_kelly_fraction_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:preferences_api"),
            data='{"kelly_fraction":0.75}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_unknown_preference_field_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:preferences_api"),
            data='{"user_id":999}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_account_page_saves_bankroll_and_fraction(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:account"),
            data={
                "timezone": "America/New_York",
                "bankroll": "8800.25",
                "kelly_fraction": "0.25",
            },
        )
        self.assertEqual(response.status_code, 200)

        prefs = UserPreferences.objects.get(user=self.user)
        self.assertEqual(str(prefs.bankroll), "8800.25")
        self.assertEqual(str(prefs.kelly_fraction), "0.25")



class PreferenceBackwardCompatibilityTests(TestCase):
    def test_timezone_only_account_post_keeps_new_private_defaults(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            email="backward-compatible@example.com",
            password="StrongPass!2026",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("accounts:account"),
            data={"timezone": "America/Chicago"},
        )
        self.assertEqual(response.status_code, 200)

        prefs = UserPreferences.objects.get(user=user)
        self.assertEqual(prefs.timezone, "America/Chicago")
        self.assertIsNone(prefs.bankroll)
        self.assertEqual(str(prefs.kelly_fraction), "1.00")



from datetime import timedelta

from django.utils import timezone

from .entitlements import (
    FEATURE_KELLY_PRIVATE_SETTINGS,
    FEATURE_PREMIUM_ANALYTICS,
    ensure_user_subscription,
    has_entitlement,
)
from .models import EntitlementOverride, SubscriptionPlan, UserSubscription


class EntitlementFoundationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="free-plan@example.com",
            password="StrongPass!2026",
        )
        self.pro_user = user_model.objects.create_user(
            email="pro-plan@example.com",
            password="StrongPass!2026",
        )

    def test_seeded_plans_exist(self):
        free_plan = SubscriptionPlan.objects.get(slug="free")
        pro_plan = SubscriptionPlan.objects.get(slug="pro")

        self.assertIn(FEATURE_KELLY_PRIVATE_SETTINGS, free_plan.features)
        self.assertIn(FEATURE_PREMIUM_ANALYTICS, pro_plan.features)

    def test_new_user_defaults_to_free_subscription(self):
        subscription = ensure_user_subscription(self.user)

        self.assertEqual(subscription.plan.slug, "free")
        self.assertEqual(subscription.status, UserSubscription.Status.ACTIVE)
        self.assertFalse(
            has_entitlement(self.user, FEATURE_PREMIUM_ANALYTICS)
        )

    def test_active_pro_subscription_grants_premium_feature(self):
        pro_plan = SubscriptionPlan.objects.get(slug="pro")
        subscription = ensure_user_subscription(self.pro_user)
        subscription.plan = pro_plan
        subscription.status = UserSubscription.Status.ACTIVE
        subscription.save(update_fields=("plan", "status", "updated_at"))

        self.assertTrue(
            has_entitlement(self.pro_user, FEATURE_PREMIUM_ANALYTICS)
        )

    def test_canceled_pro_subscription_falls_back_to_free_features(self):
        pro_plan = SubscriptionPlan.objects.get(slug="pro")
        subscription = ensure_user_subscription(self.pro_user)
        subscription.plan = pro_plan
        subscription.status = UserSubscription.Status.CANCELED
        subscription.save(update_fields=("plan", "status", "updated_at"))

        self.assertFalse(
            has_entitlement(self.pro_user, FEATURE_PREMIUM_ANALYTICS)
        )
        self.assertTrue(
            has_entitlement(self.pro_user, FEATURE_KELLY_PRIVATE_SETTINGS)
        )

    def test_admin_override_can_grant_premium_feature(self):
        ensure_user_subscription(self.user)
        EntitlementOverride.objects.create(
            user=self.user,
            feature=FEATURE_PREMIUM_ANALYTICS,
            enabled=True,
            reason="Internal access test",
        )

        self.assertTrue(
            has_entitlement(self.user, FEATURE_PREMIUM_ANALYTICS)
        )

    def test_admin_override_can_remove_plan_feature(self):
        pro_plan = SubscriptionPlan.objects.get(slug="pro")
        subscription = ensure_user_subscription(self.pro_user)
        subscription.plan = pro_plan
        subscription.status = UserSubscription.Status.ACTIVE
        subscription.save(update_fields=("plan", "status", "updated_at"))

        EntitlementOverride.objects.create(
            user=self.pro_user,
            feature=FEATURE_PREMIUM_ANALYTICS,
            enabled=False,
            reason="Temporary restriction",
        )

        self.assertFalse(
            has_entitlement(self.pro_user, FEATURE_PREMIUM_ANALYTICS)
        )

    def test_expired_override_is_ignored(self):
        ensure_user_subscription(self.user)
        EntitlementOverride.objects.create(
            user=self.user,
            feature=FEATURE_PREMIUM_ANALYTICS,
            enabled=True,
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        self.assertFalse(
            has_entitlement(self.user, FEATURE_PREMIUM_ANALYTICS)
        )

    def test_entitlements_api_is_private_to_authenticated_user(self):
        anonymous = self.client.get(reverse("accounts:entitlements_api"))
        self.assertEqual(anonymous.status_code, 401)

        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:entitlements_api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["plan"]["slug"], "free")
        self.assertEqual(payload["status"], "active")
        self.assertNotIn(FEATURE_PREMIUM_ANALYTICS, payload["features"])

    def test_premium_api_is_server_side_gated(self):
        self.client.force_login(self.user)
        denied = self.client.get(
            reverse("accounts:premium_analytics_access_api")
        )
        self.assertEqual(denied.status_code, 403)

        pro_plan = SubscriptionPlan.objects.get(slug="pro")
        subscription = ensure_user_subscription(self.user)
        subscription.plan = pro_plan
        subscription.status = UserSubscription.Status.ACTIVE
        subscription.save(update_fields=("plan", "status", "updated_at"))

        allowed = self.client.get(
            reverse("accounts:premium_analytics_access_api")
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertTrue(allowed.json()["access"])

    def test_registration_creates_free_subscription(self):
        response = self.client.post(
            reverse("accounts:register"),
            data={
                "email": "registered-plan@example.com",
                "password1": "StrongPass!2026",
                "password2": "StrongPass!2026",
            },
        )
        self.assertEqual(response.status_code, 302)

        user = get_user_model().objects.get(
            email="registered-plan@example.com"
        )
        self.assertEqual(user.subscription.plan.slug, "free")
        self.assertEqual(user.subscription.status, "active")



from types import SimpleNamespace
from unittest.mock import patch

from django.test import override_settings

from .billing import (
    process_stripe_event,
    sync_subscription_object,
)
from .models import (
    BillingCustomer,
    BillingEvent,
    BillingSubscription,
)


class BillingIntegrationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="billing@example.com",
            password="StrongPass!2026",
        )
        self.subscription = ensure_user_subscription(self.user)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_example",
        STRIPE_PRO_PRICE_ID="price_pro",
    )
    @patch("accounts.billing.stripe.checkout.Session.create")
    @patch("accounts.billing.stripe.Customer.create")
    def test_checkout_creates_customer_and_redirects(
        self,
        customer_create,
        session_create,
    ):
        customer_create.return_value = SimpleNamespace(id="cus_test_1")
        session_create.return_value = SimpleNamespace(
            url="https://checkout.stripe.test/session"
        )

        self.client.force_login(self.user)
        response = self.client.post(reverse("accounts:billing_checkout"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            "https://checkout.stripe.test/session",
        )
        self.assertTrue(
            BillingCustomer.objects.filter(
                user=self.user,
                external_customer_id="cus_test_1",
            ).exists()
        )

        kwargs = session_create.call_args.kwargs
        self.assertEqual(kwargs["mode"], "subscription")
        self.assertEqual(
            kwargs["line_items"][0]["price"],
            "price_pro",
        )
        self.assertEqual(kwargs["client_reference_id"], str(self.user.pk))

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_example",
        STRIPE_PRO_PRICE_ID="price_pro",
        STRIPE_PORTAL_CONFIGURATION_ID="",
    )
    @patch("accounts.billing.stripe.billing_portal.Session.create")
    def test_portal_redirects_linked_customer(self, portal_create):
        BillingCustomer.objects.create(
            user=self.user,
            provider="stripe",
            external_customer_id="cus_test_2",
        )
        portal_create.return_value = SimpleNamespace(
            url="https://billing.stripe.test/portal"
        )

        self.client.force_login(self.user)
        response = self.client.post(reverse("accounts:billing_portal"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            "https://billing.stripe.test/portal",
        )

    @override_settings(
        STRIPE_PRO_PRICE_ID="price_pro",
    )
    def test_subscription_event_grants_pro(self):
        BillingCustomer.objects.create(
            user=self.user,
            provider="stripe",
            external_customer_id="cus_sub_1",
        )

        sync_subscription_object(
            {
                "id": "sub_pro_1",
                "customer": "cus_sub_1",
                "status": "active",
                "cancel_at_period_end": False,
                "items": {
                    "data": [
                        {
                            "price": {"id": "price_pro"},
                            "current_period_end": 1893456000,
                        }
                    ]
                },
                "metadata": {
                    "user_id": str(self.user.pk),
                },
            }
        )

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.plan.slug, "pro")
        self.assertEqual(
            self.subscription.status,
            UserSubscription.Status.ACTIVE,
        )
        self.assertTrue(
            BillingSubscription.objects.filter(
                external_subscription_id="sub_pro_1",
                is_current=True,
            ).exists()
        )

    @override_settings(
        STRIPE_PRO_PRICE_ID="price_pro",
    )
    def test_failed_invoice_marks_subscription_past_due(self):
        BillingCustomer.objects.create(
            user=self.user,
            provider="stripe",
            external_customer_id="cus_sub_2",
        )

        sync_subscription_object(
            {
                "id": "sub_pro_2",
                "customer": "cus_sub_2",
                "status": "active",
                "items": {
                    "data": [
                        {"price": {"id": "price_pro"}}
                    ]
                },
                "metadata": {
                    "user_id": str(self.user.pk),
                },
            }
        )

        process_stripe_event(
            {
                "id": "evt_failed_invoice_1",
                "type": "invoice.payment_failed",
                "livemode": False,
                "data": {
                    "object": {
                        "subscription": "sub_pro_2",
                    }
                },
            }
        )

        self.subscription.refresh_from_db()
        self.assertEqual(
            self.subscription.status,
            UserSubscription.Status.PAST_DUE,
        )

    def test_billing_event_processing_is_idempotent(self):
        event = {
            "id": "evt_idempotent_1",
            "type": "unhandled.example",
            "livemode": False,
            "data": {"object": {}},
        }

        process_stripe_event(event)
        process_stripe_event(event)

        self.assertEqual(
            BillingEvent.objects.filter(
                external_event_id="evt_idempotent_1"
            ).count(),
            1,
        )
        self.assertIsNotNone(
            BillingEvent.objects.get(
                external_event_id="evt_idempotent_1"
            ).processed_at
        )

    @override_settings(
        STRIPE_WEBHOOK_SECRET="whsec_test",
    )
    @patch("accounts.billing_views.process_stripe_event")
    @patch("accounts.billing_views.stripe.Webhook.construct_event")
    def test_webhook_verifies_signature_and_processes_event(
        self,
        construct_event,
        process_event,
    ):
        construct_event.return_value = {
            "id": "evt_webhook_1",
            "type": "unhandled.example",
            "data": {"object": {}},
        }

        response = self.client.post(
            reverse("accounts:billing_webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test-signature",
        )

        self.assertEqual(response.status_code, 200)
        construct_event.assert_called_once()
        process_event.assert_called_once()

    def test_checkout_requires_configuration(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("accounts:billing_checkout"))
        self.assertEqual(response.status_code, 503)

    def test_portal_requires_existing_customer(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("accounts:billing_portal"))
        self.assertEqual(response.status_code, 409)

from django.test import SimpleTestCase as _PasswordResetRouteTestCase

class PasswordResetRouteTests(_PasswordResetRouteTestCase):
    def test_reset_token_with_hyphen_resolves_without_corruption(self):
        from django.urls import resolve, reverse
        url = reverse("accounts:password_reset_confirm", kwargs={"uidb64": "Mg", "token": "d12345-abcdef"})
        self.assertEqual(resolve(url).kwargs, {"uidb64": "Mg", "token": "d12345-abcdef"})