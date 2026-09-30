from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_entitlement_foundation"),
    ]

    operations = [
        migrations.CreateModel(
            name="BillingCustomer",
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
                ("provider", models.CharField(default="stripe", max_length=32)),
                (
                    "external_customer_id",
                    models.CharField(max_length=255, unique=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="billing_customers",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("user_id", "provider"),
            },
        ),
        migrations.CreateModel(
            name="BillingEvent",
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
                ("provider", models.CharField(default="stripe", max_length=32)),
                (
                    "external_event_id",
                    models.CharField(max_length=255),
                ),
                ("event_type", models.CharField(max_length=255)),
                ("livemode", models.BooleanField(default=False)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ("-received_at",),
            },
        ),
        migrations.CreateModel(
            name="BillingSubscription",
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
                ("provider", models.CharField(default="stripe", max_length=32)),
                (
                    "external_subscription_id",
                    models.CharField(max_length=255, unique=True),
                ),
                ("external_price_id", models.CharField(blank=True, max_length=255)),
                ("external_status", models.CharField(blank=True, max_length=64)),
                ("current_period_end", models.DateTimeField(blank=True, null=True)),
                ("cancel_at_period_end", models.BooleanField(default=False)),
                ("is_current", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user_subscription",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="billing_subscriptions",
                        to="accounts.usersubscription",
                    ),
                ),
            ],
            options={
                "ordering": ("-is_current", "-updated_at"),
            },
        ),
        migrations.AddConstraint(
            model_name="billingcustomer",
            constraint=models.UniqueConstraint(
                fields=("user", "provider"),
                name="accounts_billing_customer_user_provider_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="billingevent",
            constraint=models.UniqueConstraint(
                fields=("provider", "external_event_id"),
                name="accounts_billing_event_provider_event_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="billingsubscription",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_current", True)),
                fields=("user_subscription", "provider"),
                name="accounts_billing_subscription_current_unique",
            ),
        ),
    ]
