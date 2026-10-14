"""Django homepage opt-in integration checks; test runner uses in-memory SQLite."""
import json
import re
from pathlib import Path
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from .models import ContactMessage

DIST = Path(__file__).resolve().parents[2] / "react" / "react-dist"

def boot(response):
    assert response.status_code == 200, response.status_code
    match = re.search(r'<script id="smh-account-bootstrap" type="application/json">([^<]+)</script>', response.content.decode())
    assert match, "missing React homepage bootstrap"
    return json.loads(match.group(1))

@override_settings(REACT_HOME_PAGE_ENABLED=True, REACT_ACCOUNT_PAGES_ENABLED=False, FRONTEND_DIST_DIR=DIST)
class HomeBridgeTests(TestCase):
    def test_logged_out_home_and_index_render_react(self):
        for path in ["/", "/index.html"]:
            with self.subTest(path=path):
                r = self.client.get(path)
                data = boot(r)
                self.assertEqual(data["page"], "home_login")
                self.assertFalse(data["authenticated"])
                self.assertTrue(data["csrfToken"])
                directives = {x.strip() for x in r["Cache-Control"].split(",")}
                self.assertTrue({"private", "no-store"}.issubset(directives))
                self.assertIn(b'<div id="root"></div>', r.content)

    def test_login_from_home_produces_django_session(self):
        user = get_user_model().objects.create_user(email="home@example.com",password="StrongPass!2026")
        r = self.client.post("/",data={"username": user.email,"password":"StrongPass!2026"})
        self.assertEqual(r.status_code,302)
        self.assertEqual(r["Location"],"/")
        data = boot(self.client.get("/"))
        self.assertTrue(data["authenticated"])
        self.assertEqual(data["profile"]["email"], user.email)
        self.assertEqual(data["page"], "home_account")

    def test_invalid_login_preserves_errors_not_password(self):
        r = self.client.post("/",data={"username":"fail@example.com","password":"NEVER_EXPOSE_SECRET"})
        data = boot(r)
        self.assertTrue(data["nonFieldErrors"])
        self.assertNotIn("NEVER_EXPOSE_SECRET",r.content.decode())

    def test_csrf_enforced_on_home_login(self):
        c = Client(enforce_csrf_checks=True)
        response = c.post("/",data={"username":"fake@example.com","password":"test"})
        self.assertEqual(response.status_code,403)

    def test_private_account_inbox_on_home(self):
        user = get_user_model().objects.create_user(email="private@example.com",password="StrongPass!2026")
        other = get_user_model().objects.create_user(email="other@example.com",password="StrongPass!2026")
        ContactMessage.objects.create(name="Mine",email=user.email,subject="MY_INBOX",message="Visible",user=user)
        ContactMessage.objects.create(name="Other",email=other.email,subject="SECRET_OTHER",message="Invisible",user=other)
        self.client.force_login(user)
        r=self.client.get("/")
        data=boot(r)
        self.assertEqual([m["subject"] for m in data["profile"]["messages"]],["MY_INBOX"])
        self.assertNotIn("SECRET_OTHER",r.content.decode())

    def test_admin_and_account_routes_do_not_switch_with_home_flag(self):
        self.assertNotIn(b"smh-account-bootstrap",self.client.get("/admin/login/").content)
        self.assertNotIn(b"smh-account-bootstrap",self.client.get("/login.html").content)

@override_settings(REACT_HOME_PAGE_ENABLED=False, REACT_ACCOUNT_PAGES_ENABLED=False)
class LegacyHomeTests(TestCase):
    def test_anonymous_home_keeps_legacy_django_markup(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code,200)
        self.assertNotIn(b"smh-account-bootstrap",response.content)
        self.assertIn(b"hl-leagues",response.content)

    def test_authenticated_home_keeps_legacy_django_markup(self):
        user=get_user_model().objects.create_user(email="legacyhome@example.com",password="StrongPass!2026")
        self.client.force_login(user)
        response=self.client.get("/")
        self.assertEqual(response.status_code,200)
        self.assertNotIn(b"smh-account-bootstrap",response.content)
        self.assertIn(b"hl-leagues",response.content)
