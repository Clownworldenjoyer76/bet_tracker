from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower

from .managers import UserManager


class User(AbstractUser):
    username = None
    email = models.EmailField("email address", unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta(AbstractUser.Meta):
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_ci_unique",
            )
        ]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


TIMEZONE_CHOICES = [
    ("America/New_York", "Eastern"),
    ("America/Chicago", "Central"),
    ("America/Denver", "Mountain"),
    ("America/Los_Angeles", "Pacific"),
    ("America/Anchorage", "Alaska"),
    ("Pacific/Honolulu", "Hawaii"),
]


class UserPreferences(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="preferences",
    )
    timezone = models.CharField(
        max_length=64,
        choices=TIMEZONE_CHOICES,
        default="America/New_York",
    )
    bankroll = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    kelly_fraction = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=[
            (Decimal("1.00"), "Full"),
            (Decimal("0.50"), "Half"),
            (Decimal("0.25"), "Quarter"),
        ],
        default=Decimal("1.00"),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "user preferences"
        verbose_name_plural = "user preferences"

    def __str__(self):
        return f"{self.user.email} preferences"



class SubscriptionPlan(models.Model):
    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name


class UserSubscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        TRIALING = "trialing", "Trialing"
        PAST_DUE = "past_due", "Past due"
        CANCELED = "canceled", "Canceled"
        INACTIVE = "inactive", "Inactive"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    starts_at = models.DateTimeField(auto_now_add=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} · {self.plan.name} · {self.status}"


class EntitlementOverride(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="entitlement_overrides",
    )
    feature = models.CharField(max_length=100)
    enabled = models.BooleanField(default=True)
    reason = models.CharField(max_length=255, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "feature"),
                name="accounts_entitlement_override_user_feature_unique",
            )
        ]
        ordering = ("user_id", "feature")

    def __str__(self):
        state = "enabled" if self.enabled else "disabled"
        return f"{self.user.email} · {self.feature} · {state}"



class BillingCustomer(models.Model):
    PROVIDER_STRIPE = "stripe"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="billing_customers",
    )
    provider = models.CharField(max_length=32, default=PROVIDER_STRIPE)
    external_customer_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "provider"),
                name="accounts_billing_customer_user_provider_unique",
            )
        ]
        ordering = ("user_id", "provider")

    def __str__(self):
        return f"{self.user.email} · {self.provider}"


class BillingSubscription(models.Model):
    PROVIDER_STRIPE = "stripe"

    user_subscription = models.ForeignKey(
        UserSubscription,
        on_delete=models.CASCADE,
        related_name="billing_subscriptions",
    )
    provider = models.CharField(max_length=32, default=PROVIDER_STRIPE)
    external_subscription_id = models.CharField(max_length=255, unique=True)
    external_price_id = models.CharField(max_length=255, blank=True)
    external_status = models.CharField(max_length=64, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    is_current = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user_subscription", "provider"),
                condition=models.Q(is_current=True),
                name="accounts_billing_subscription_current_unique",
            )
        ]
        ordering = ("-is_current", "-updated_at")

    def __str__(self):
        return (
            f"{self.user_subscription.user.email} · "
            f"{self.provider} · {self.external_status}"
        )


class BillingEvent(models.Model):
    PROVIDER_STRIPE = "stripe"

    provider = models.CharField(max_length=32, default=PROVIDER_STRIPE)
    external_event_id = models.CharField(max_length=255)
    event_type = models.CharField(max_length=255)
    livemode = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("provider", "external_event_id"),
                name="accounts_billing_event_provider_event_unique",
            )
        ]
        ordering = ("-received_at",)

    def __str__(self):
        return f"{self.provider} · {self.event_type} · {self.external_event_id}"


class ContactMessage(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        REPLIED = "replied", "Replied"

    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=150)
    message = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reply = models.TextField(blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    user = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="contact_messages",
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "contact message"
        verbose_name_plural = "MESSAGES"

    def __str__(self):
        return f"{self.email} - {self.subject}"