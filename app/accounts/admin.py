from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import (
    BillingCustomer,
    BillingEvent,
    BillingSubscription,
    EntitlementOverride,
    SubscriptionPlan,
    User,
    UserPreferences,
    UserSubscription,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("email",)
    list_display = ("email", "is_staff", "is_active", "date_joined")
    search_fields = ("email", "first_name", "last_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )



@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ("user", "timezone", "bankroll", "kelly_fraction", "updated_at")
    search_fields = ("user__email",)
    list_filter = ("timezone",)
    readonly_fields = ("updated_at",)



@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "sort_order", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    ordering = ("sort_order", "name")


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "starts_at", "ends_at", "updated_at")
    list_filter = ("plan", "status")
    search_fields = ("user__email", "plan__name", "plan__slug")
    autocomplete_fields = ("user", "plan")


@admin.register(EntitlementOverride)
class EntitlementOverrideAdmin(admin.ModelAdmin):
    list_display = ("user", "feature", "enabled", "expires_at", "updated_at")
    list_filter = ("enabled", "feature")
    search_fields = ("user__email", "feature", "reason")
    autocomplete_fields = ("user",)



@admin.register(BillingCustomer)
class BillingCustomerAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "provider",
        "external_customer_id",
        "updated_at",
    )
    search_fields = ("user__email", "external_customer_id")
    list_filter = ("provider",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(BillingSubscription)
class BillingSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user_subscription",
        "provider",
        "external_status",
        "external_price_id",
        "is_current",
        "cancel_at_period_end",
        "current_period_end",
    )
    search_fields = (
        "user_subscription__user__email",
        "external_subscription_id",
        "external_price_id",
    )
    list_filter = (
        "provider",
        "external_status",
        "is_current",
        "cancel_at_period_end",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(BillingEvent)
class BillingEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_type",
        "external_event_id",
        "provider",
        "livemode",
        "processed_at",
        "received_at",
    )
    search_fields = ("event_type", "external_event_id", "last_error")
    list_filter = ("provider", "livemode", "event_type")
    readonly_fields = (
        "provider",
        "external_event_id",
        "event_type",
        "livemode",
        "processed_at",
        "last_error",
        "received_at",
    )

    def has_add_permission(self, request):
        return False
