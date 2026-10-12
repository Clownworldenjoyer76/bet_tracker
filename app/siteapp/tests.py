from pathlib import Path

from django.conf import settings
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase


class FrontendCompatibilityTests(SimpleTestCase):
    # Pages under these names are rendered by Django (accounts.urls), not served from dist.
    DJANGO_OWNED_PAGES = {"index.html", "contact.html"}

    def _body(self, response):
        if getattr(response, "streaming", False):
            return b"".join(response.streaming_content)
        return response.content

    def test_home_is_rendered_by_django(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/home_login.html")

    def test_every_dist_page_is_served_unchanged(self):
        dist = Path(settings.FRONTEND_DIST_DIR)
        pages = sorted(
            p for p in dist.iterdir()
            if p.is_file() and p.suffix == ".html" and p.name not in self.DJANGO_OWNED_PAGES
        )
        self.assertTrue(pages)

        for page in pages:
            with self.subTest(page=page.name):
                response = self.client.get(f"/{page.name}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self._body(response), page.read_bytes())

    def test_news_alias_serves_news_page_as_html(self):
        response = self.client.get("/news")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/html"))
        expected = (Path(settings.FRONTEND_DIST_DIR) / "news.html").read_bytes()
        self.assertEqual(self._body(response), expected)

    def test_runtime_nav_component_is_served(self):
        response = self.client.get("/nav.html")
        self.assertEqual(response.status_code, 200)

    def test_shared_polish_asset_is_served(self):
        response = self.client.get("/assets/css/site-polish.css")
        self.assertEqual(response.status_code, 200)

    def test_other_extensionless_paths_are_404(self):
        response = self.client.get("/pipeline_health")
        self.assertEqual(response.status_code, 404)

    def test_unknown_file_is_404(self):
        response = self.client.get("/definitely-not-a-real-file.xyz")
        self.assertEqual(response.status_code, 404)


class HealthEndpointTests(TestCase):
    def test_healthz_is_application_liveness_only(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["service"], "bet_tracker")

    def test_readyz_checks_database_and_frontend(self):
        response = self.client.get("/readyz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["database"], "ok")
        self.assertEqual(response.json()["frontend"], "ok")

    @patch("siteapp.views.connection.cursor")
    def test_readyz_returns_503_when_database_is_unavailable(
        self,
        cursor,
    ):
        cursor.side_effect = RuntimeError("database unavailable")

        response = self.client.get("/readyz")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "unavailable")
        self.assertEqual(response.json()["database"], "error")
        self.assertNotIn(
            "database unavailable",
            response.content.decode("utf-8"),
        )
