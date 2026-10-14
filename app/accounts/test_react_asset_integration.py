"""Django-to-Vite built asset checks on an isolated test runner.

All tests use Django's temporary in-memory SQLite database and locally-built
React files. No production origin, credentials or live customers are contacted.
"""
import re
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings


DIST = Path(__file__).resolve().parents[2] / "react" / "react-dist"
ASSET_LINK = re.compile(r'(?:src|href)="\./(assets/[A-Za-z0-9_-]+\.(?:js|css))"')


@override_settings(
    REACT_ACCOUNT_PAGES_ENABLED=True,
    REACT_HOME_PAGE_ENABLED=True,
    FRONTEND_DIST_DIR=DIST,
)
class ReactV2BuiltAssetIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            email="review-asset-ci@example.com", password="StrongPass!2026"
        )

    def _assert_assets(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, path)
        self.assertIn(b'<div id="root"></div>', response.content)
        self.assertIn(b'id="smh-account-bootstrap"', response.content)
        html = response.content.decode("utf-8")
        self.assertIn('<base href="/">', html)
        assets = sorted(set(ASSET_LINK.findall(html)))
        self.assertTrue(any(asset.endswith(".js") for asset in assets), path)
        self.assertTrue(any(asset.endswith(".css") for asset in assets), path)
        for asset in assets:
            with self.subTest(path=path, asset=asset):
                self.assertTrue((DIST / asset).is_file(), asset)
                delivered = self.client.get("/" + asset)
                self.assertEqual(delivered.status_code, 200, asset)
                mime = delivered["Content-Type"].lower()
                if asset.endswith(".js"):
                    self.assertIn("javascript", mime, mime)
                else:
                    self.assertIn("css", mime, mime)

    def test_anonymous_react_shells_serve_build_assets(self):
        for url in (
            "/", "/index.html", "/login.html", "/register.html",
            "/contact.html", "/password_reset.html",
            "/password_reset_done.html", "/password_reset_complete.html",
        ):
            with self.subTest(url=url):
                self._assert_assets(url)

    def test_authenticated_react_account_shell_serves_build_assets(self):
        self.client.force_login(self.user)
        self._assert_assets("/account.html")
        self._assert_assets("/")

    def test_admin_login_remains_django(self):
        page = self.client.get("/admin/login/")
        self.assertEqual(page.status_code, 200)
        self.assertNotIn(b'id="smh-account-bootstrap"', page.content)

    @override_settings(REACT_ACCOUNT_PAGES_ENABLED=False, REACT_HOME_PAGE_ENABLED=False)
    def test_both_feature_flags_off_preserve_legacy_django(self):
        for url in ("/", "/login.html", "/contact.html"):
            with self.subTest(url=url):
                page = self.client.get(url)
                self.assertEqual(page.status_code, 200)
                self.assertNotIn(b'id="smh-account-bootstrap"', page.content)