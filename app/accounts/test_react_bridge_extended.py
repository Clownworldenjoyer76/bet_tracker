"""Extended end-to-end Django contract tests for the opt-in React account bridge.
Runs ONLY under Django's test command, which uses in-memory SQLite.
"""
import json
import re
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.test import Client, TestCase, SimpleTestCase, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import ContactMessage, UserPreferences

DIST = Path(__file__).resolve().parents[2] / "react" / "react-dist"
REACT_ROOT = Path(__file__).resolve().parents[2] / "react"


def bootstrap(response):
    assert response.status_code == 200, (response.status_code, response.get("Location"))
    html = response.content.decode("utf-8")
    match = re.search(r'<script id="smh-account-bootstrap" type="application/json">([^<]+)</script>', html)
    assert match is not None, "Django React bootstrap script not present"
    return json.loads(match.group(1))


@override_settings(REACT_ACCOUNT_PAGES_ENABLED=True, FRONTEND_DIST_DIR=DIST)
class ReactBridgeBehaviorTests(TestCase):
    def setUp(self):
        cache.clear()

    def make_user(self, email="tester@example.com", password="StrongPass!2026"):
        return get_user_model().objects.create_user(email=email, password=password)

    def test_public_account_routes_deliver_noncacheable_react_shells(self):
        pages = [
            "/login.html", "/register.html", "/contact.html", "/password_reset.html",
            "/password_reset_done.html", "/password_reset_complete.html",
        ]
        for path in pages:
            with self.subTest(path=path):
                response = self.client.get(path)
                state = bootstrap(response)
                self.assertFalse(state["authenticated"])
                self.assertTrue(state["csrfToken"])
                directives = {x.strip().lower() for x in response["Cache-Control"].split(",")}
                self.assertTrue({"private", "no-store"}.issubset(directives))
                self.assertIn("Cookie", response.get("Vary", ""))

    def test_login_success_sets_django_session(self):
        user = self.make_user()
        response = self.client.post("/login.html", data={
            "username": user.email, "password": "StrongPass!2026"
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/account.html")
        state = bootstrap(self.client.get("/account.html"))
        self.assertEqual(state["profile"]["email"], user.email)

    def test_login_invalid_does_not_serialize_password(self):
        response = self.client.post("/login.html", data={
            "username": "tester@example.com", "password": "PRIVATE_FAKE_PASSWORD"
        })
        data = bootstrap(response)
        self.assertEqual(data["values"]["username"], "tester@example.com")
        self.assertTrue(data["nonFieldErrors"])
        self.assertNotIn("PRIVATE_FAKE_PASSWORD", response.content.decode())

    def test_login_csrf_can_succeed_with_token_and_cookie(self):
        user = self.make_user()
        strict = Client(enforce_csrf_checks=True)
        data = bootstrap(strict.get("/login.html"))
        response = strict.post("/login.html", data={
            "username": user.email, "password": "StrongPass!2026",
            "csrfmiddlewaretoken": data["csrfToken"],
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/account.html")

    def test_register_creates_authenticated_user(self):
        email = "new-registrant@example.com"
        response = self.client.post("/register.html", data={
            "email": email, "password1": "StrongPass!2026", "password2": "StrongPass!2026"
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/account.html")
        self.assertTrue(get_user_model().objects.filter(email=email).exists())
        data = bootstrap(self.client.get("/account.html"))
        self.assertTrue(data["authenticated"])
        self.assertEqual(data["profile"]["email"], email)

    def test_logout_stays_post_only(self):
        self.make_user()
        self.client.login(username="tester@example.com", password="StrongPass!2026")
        self.assertEqual(self.client.get("/logout.html").status_code, 405)
        self.assertEqual(self.client.post("/logout.html").status_code, 302)
        self.assertEqual(self.client.get("/account.html").status_code, 302)

    def test_preferences_post_updates_only_logged_in_account(self):
        user = self.make_user()
        self.client.force_login(user)
        response = self.client.post("/account.html", data={
            "timezone": "America/Chicago", "bankroll": "1234.50", "kelly_fraction": "0.50"
        })
        state = bootstrap(response)
        prefs = UserPreferences.objects.get(user=user)
        self.assertEqual(prefs.timezone, "America/Chicago")
        self.assertEqual(str(prefs.bankroll), "1234.50")
        self.assertEqual(str(prefs.kelly_fraction), "0.50")
        self.assertEqual(state["profile"]["timezone"], "America/Chicago")

    def test_account_bootstrap_excludes_another_users_inbox(self):
        user = self.make_user()
        other = self.make_user(email="other@example.com")
        ContactMessage.objects.create(name="Mine", email=user.email, subject="Mine", message="Visible", user=user)
        ContactMessage.objects.create(name="Other", email=other.email, subject="Other", message="SECRET_OTHER", user=other)
        self.client.force_login(user)
        response = self.client.get("/account.html")
        state = bootstrap(response)
        self.assertEqual([m["subject"] for m in state["profile"]["messages"]], ["Mine"])
        self.assertNotIn("SECRET_OTHER", response.content.decode())

    def test_contact_submission_and_success_state(self):
        before = ContactMessage.objects.count()
        response = self.client.post("/contact.html", data={
            "name": "Example", "email": "HELLO@example.com", "subject": "Test question",
            "message": "A complete support message for testing.", "website": "",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContactMessage.objects.count(), before + 1)
        self.assertEqual(ContactMessage.objects.latest("created_at").email, "hello@example.com")
        state = bootstrap(self.client.get("/contact.html?sent=1"))
        self.assertTrue(state["sent"])

    def test_contact_honeypot_rejects_silent_spam(self):
        response = self.client.post("/contact.html", data={
            "name": "Spam", "email": "spam@example.com", "subject": "Test",
            "message": "More than ten characters.", "website": "hidden-bot-value",
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ContactMessage.objects.filter(email="spam@example.com").exists())

    def test_password_reset_confirm_uses_token_and_updates_password(self):
        user = self.make_user()
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        response = self.client.get(f"/reset/{uid}/{token}.html", follow=True)
        state = bootstrap(response)
        self.assertTrue(state["validLink"])
        self.assertEqual(state["page"], "password_reset_confirm")
        end_route = response.request["PATH_INFO"]
        posted = self.client.post(end_route, data={
            "new_password1": "AnotherStrongPass!2026",
            "new_password2": "AnotherStrongPass!2026",
        })
        self.assertEqual(posted.status_code, 302)
        self.assertEqual(posted["Location"], "/password_reset_complete.html")
        user.refresh_from_db()
        self.assertTrue(user.check_password("AnotherStrongPass!2026"))

    def test_invalid_reset_link_does_not_get_valid_form(self):
        response = self.client.get("/reset/aW52YWxpZA/bad-token.html")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(bootstrap(response)["validLink"])

    def test_django_admin_not_replaced_by_react(self):
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"smh-account-bootstrap", response.content)


class ReactSourceContractTests(SimpleTestCase):
    def test_react_account_page_files_have_built_shells(self):
        names = ["account", "login", "register", "contact", "password_reset",
                 "password_reset_done", "password_reset_complete"]
        for name in names:
            with self.subTest(name=name):
                path = DIST / f"{name}.html"
                self.assertTrue(path.is_file(), str(path))
                self.assertIn('<div id="root"></div>', path.read_text(encoding="utf-8"))

    def test_react_router_contains_account_and_reset_routes(self):
        content = (REACT_ROOT / "src" / "App.tsx").read_text(encoding="utf-8")
        for path in ["/account.html", "/login.html", "/register.html", "/contact.html",
                     "/password_reset.html", "/password_reset_done.html", "/reset/*"]:
            with self.subTest(path=path):
                self.assertIn(f'path="{path}"', content)

    def test_navigation_does_not_intercept_sensitive_django_auth_pages(self):
        content = (REACT_ROOT / "src" / "components" / "SiteShell.tsx").read_text(encoding="utf-8")
        captured = re.search(r"const REACT_ROUTES = new Set\(\[([\s\S]*?)\]\);", content)
        self.assertIsNotNone(captured)
        for path in ["/account.html", "/login.html", "/register.html", "/contact.html",
                     "/password_reset.html"]:
            with self.subTest(path=path):
                self.assertNotIn(f'"{path}"', captured.group(1))
