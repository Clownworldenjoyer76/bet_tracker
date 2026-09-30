from pathlib import Path

from django.conf import settings
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase


class FrontendCompatibilityTests(SimpleTestCase):
    def _body(self, response):
        if getattr(response, "streaming", False):
            return b"".join(response.streaming_content)
        return response.content

    def test_home_is_exact_verified_index(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        expected = (Path(settings.FRONTEND_DIST_DIR) / "index.html").read_bytes()
        self.assertEqual(self._body(response), expected)

    def test_every_existing_page_is_served(self):
        pages = sorted(
            p.name
            for p in Path(settings.FRONTEND_SOURCE_DIR, "pages").iterdir()
            if p.is_file()
        )
        self.assertEqual(len(pages), 46)

        for page in pages:
            with self.subTest(page=page):
                response = self.client.get(f"/{page}")
                self.assertEqual(response.status_code, 200)

    def test_runtime_nav_component_is_served(self):
        response = self.client.get("/nav.html")
        self.assertEqual(response.status_code, 200)

    def test_shared_polish_asset_is_served(self):
        response = self.client.get("/assets/css/site-polish.css")
        self.assertEqual(response.status_code, 200)

    def test_pipeline_data_is_served(self):
        response = self.client.get("/data/pipeline_health/nfl.json")
        self.assertEqual(response.status_code, 200)

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
