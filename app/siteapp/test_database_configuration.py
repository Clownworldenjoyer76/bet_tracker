from django.conf import settings
from django.test import SimpleTestCase


class DatabaseConfigurationTests(SimpleTestCase):
    def test_database_engine_is_supported(self):
        engine = settings.DATABASES["default"]["ENGINE"]
        self.assertIn(
            engine,
            {
                "django.db.backends.sqlite3",
                "django.db.backends.postgresql",
            },
        )
