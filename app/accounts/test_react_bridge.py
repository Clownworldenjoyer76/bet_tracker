"""Opt-in React bridge tests; isolated SQLite test DB only."""
import json
from pathlib import Path
import re

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from .models import ContactMessage

DIST = Path(__file__).resolve().parents[2] / "react" / "react-dist"

@override_settings(REACT_ACCOUNT_PAGES_ENABLED=True, FRONTEND_DIST_DIR=DIST)
class ReactAccountBridgeTests(TestCase):
    def _bootstrap(self, response):
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        match = re.search(r'<script id="smh-account-bootstrap" type="application/json">([^<]+)</script>', html)
        self.assertIsNotNone(match)
        self.assertIn('<base href="/">', html)
        directives = {part.strip().lower() for part in response["Cache-Control"].split(",")}
        self.assertTrue({"private", "no-store"}.issubset(directives))
        return json.loads(match.group(1))

    def test_login_and_registration_bootstrap(self):
        for route in ("/login.html", "/register.html", "/password_reset.html", "/contact.html"):
            with self.subTest(route=route):
                data = self._bootstrap(self.client.get(route))
                self.assertFalse(data["authenticated"])
                self.assertTrue(data["csrfToken"])

    def test_form_errors_are_transported_without_passwords(self):
        response = self.client.post("/register.html", data={"email": "invalid-email", "password1": "abc", "password2": "xyz"})
        data = self._bootstrap(response)
        self.assertIn("email", data["errors"])
        self.assertNotIn("password1", data["values"])
        self.assertNotIn("password2", data["values"])

    def test_login_requires_csrf(self):
        strict = Client(enforce_csrf_checks=True)
        response = strict.post("/login.html", data={"username": "someone@example.com", "password": "bad"})
        self.assertEqual(response.status_code, 403)

    def test_account_requires_login_and_only_displays_owned_messages(self):
        self.assertEqual(self.client.get("/account.html").status_code, 302)
        user = get_user_model().objects.create_user(email="owner@example.com",password="StrongPass!2026")
        other = get_user_model().objects.create_user(email="other@example.com",password="StrongPass!2026")
        ContactMessage.objects.create(name="Owner",email=user.email,subject="Owned message",message="My private text",user=user)
        ContactMessage.objects.create(name="Other",email=other.email,subject="Other message",message="Must not leak",user=other)
        self.client.force_login(user)
        result=self.client.get("/account.html")
        data=self._bootstrap(result)
        self.assertTrue(data["authenticated"])
        self.assertEqual(data["profile"]["email"],user.email)
        self.assertEqual([m["subject"] for m in data["profile"]["messages"]],["Owned message"])
        self.assertNotIn("Must not leak",result.content.decode())

    def test_json_escapes_embedded_markup(self):
        user = get_user_model().objects.create_user(email="escape@example.com",password="StrongPass!2026")
        ContactMessage.objects.create(name="Example",email=user.email,subject="</script><script>alert(1)</script>",message="safe test",user=user)
        self.client.force_login(user)
        html=self.client.get("/account.html").content.decode()
        self.assertNotIn('</script><script>alert(1)</script>',html)
        self.assertIn('\\u003c/script\\u003e',html)

@override_settings(REACT_ACCOUNT_PAGES_ENABLED=False)
class LegacyFallbackTests(TestCase):
    def test_login_stays_django_by_default(self):
        response = self.client.get("/login.html")
        self.assertEqual(response.status_code,200)
        self.assertNotIn(b"smh-account-bootstrap",response.content)
