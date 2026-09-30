from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


FREE_FEATURES = [
    "account_preferences",
    "kelly_private_settings",
]

PRO_FEATURES = [
    "account_preferences",
    "kelly_private_settings",
    "premium_analytics",
]


def seed_entitlement_foundation(apps, schema_editor):
    SubscriptionPlan = apps.get_model("accounts", "SubscriptionPlan")
    UserSubscription = apps.get_model("accounts", "UserSubscription")
    User = apps.get_model("accounts", "User")

    free_plan, _ = SubscriptionPlan.objects.update_or_create(
        slug="free",
        defaults={
            "name": "Free",
            "features": FREE_FEATURES,
            "is_active": True,
            "sort_order": 0,
        },
    )

    SubscriptionPlan.objects.update_or_create(
        slug="pro",
        defaults={
            "name": "Pro",
            "features": PRO_FEATURES,
            "is_active": True,
            "sort_order": 10,
        },
    )

    for user_id in User.objects.values_list("pk", flat=True).iterator():
        UserSubscription.objects.get_or_create(
            user_id=user_id,
            defaults={
                "plan_id": free_plan.pk,
                "status": "active",
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_userpreferences_bankroll_kelly_fraction"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubscriptionPlan",
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
                ("slug", models.SlugField(max_length=50, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("features", models.JSONField(blank=True, default=list)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ("sort_order", "name"),
            },
        ),
        migrations.CreateModel(
            name="UserSubscription",
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
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("trialing", "Trialing"),
                            ("past_due", "Past due"),
                            ("canceled", "Canceled"),
                            ("inactive", "Inactive"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("starts_at", models.DateTimeField(auto_now_add=True)),
                ("ends_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="subscriptions",
                        to="accounts.subscriptionplan",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscription",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="EntitlementOverride",
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
                ("feature", models.CharField(max_length=100)),
                ("enabled", models.BooleanField(default=True)),
                ("reason", models.CharField(blank=True, max_length=255)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entitlement_overrides",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("user_id", "feature"),
            },
        ),
        migrations.AddConstraint(
            model_name="entitlementoverride",
            constraint=models.UniqueConstraint(
                fields=("user", "feature"),
                name="accounts_entitlement_override_user_feature_unique",
            ),
        ),
        migrations.RunPython(
            seed_entitlement_foundation,
            migrations.RunPython.noop,
        ),
    ]
