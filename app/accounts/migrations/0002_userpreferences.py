from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserPreferences",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "timezone",
                    models.CharField(
                        choices=[
                            ("America/New_York", "Eastern"),
                            ("America/Chicago", "Central"),
                            ("America/Denver", "Mountain"),
                            ("America/Los_Angeles", "Pacific"),
                            ("America/Anchorage", "Alaska"),
                            ("Pacific/Honolulu", "Hawaii"),
                        ],
                        default="America/New_York",
                        max_length=64,
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="preferences",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "user preferences",
                "verbose_name_plural": "user preferences",
            },
        ),
    ]
