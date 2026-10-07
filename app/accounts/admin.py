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


# SMH_CONTACT_ADMIN_START
from django import forms as contact_admin_forms
from django.contrib import messages as contact_admin_messages
from django.contrib.admin.utils import unquote as contact_admin_unquote
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from django.utils import timezone as contact_admin_timezone

from .models import ContactMessage

admin.site.site_header = "ADMIN"


class ContactMessageAdminForm(contact_admin_forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ("reply",)

    def clean_reply(self):
        reply = (self.cleaned_data.get("reply") or "").strip()
        if not reply:
            raise contact_admin_forms.ValidationError(
                "Write a reply before sending."
            )
        return reply


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    form = ContactMessageAdminForm
    list_display = (
        "created_at",
        "status",
        "read_state",
        "name",
        "email",
        "subject",
    )
    list_filter = ("status", "is_read")
    search_fields = ("name", "email", "subject", "message")
    ordering = ("-created_at",)
    fields = (
        "created_at",
        "name",
        "email",
        "account",
        "subject",
        "message",
        "status",
        "reply",
        "replied_at",
        "email_delivery",
    )
    readonly_fields = (
        "created_at",
        "name",
        "email",
        "account",
        "subject",
        "message",
        "status",
        "replied_at",
        "email_delivery",
    )

    @admin.display(description="Read / unread", ordering="is_read")
    def read_state(self, obj):
        return "Read" if obj.is_read else "Unread"

    @admin.display(description="Account")
    def account(self, obj):
        acct = obj.user or User.objects.filter(email__iexact=obj.email).first()
        return acct.email if acct else "- (no account with this email)"

    @admin.display(description="Email")
    def email_delivery(self, obj):
        if not obj.replied_at:
            return "-"
        return "Sent" if obj.email_sent else "NOT sent (email failed)"

    def has_add_permission(self, request):
        return False

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None and obj.replied_at:
            readonly.append("reply")
        return readonly

    def change_view(self, request, object_id, form_url="", extra_context=None):
        response = super().change_view(
            request, object_id, form_url, extra_context
        )
        if request.method == "GET" and response.status_code == 200:
            try:
                ContactMessage.objects.filter(
                    pk=contact_admin_unquote(object_id), is_read=False
                ).update(is_read=True)
            except (TypeError, ValueError):
                pass
        return response

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)
        data = getattr(response, "context_data", None)
        if data is not None and "cl" in data:
            cols = list(data["cl"].list_display)
            idx = {name: cols.index(name) for name in cols}
            current = request.GET.get("o", "")
            choices = [
                ("Newest first", "-%d" % idx["created_at"]),
                ("Oldest first", "%d" % idx["created_at"]),
                ("Unread first", "%d" % idx["read_state"]),
                ("Read first", "-%d" % idx["read_state"]),
                ("Status: New first", "%d" % idx["status"]),
                ("Status: Replied first", "-%d" % idx["status"]),
                ("Name A-Z", "%d" % idx["name"]),
                ("Name Z-A", "-%d" % idx["name"]),
                ("Email A-Z", "%d" % idx["email"]),
                ("Email Z-A", "-%d" % idx["email"]),
            ]
            data["sort_options"] = [
                {"label": label, "o": o, "selected": o == current}
                for label, o in choices
            ]
            data["sort_default_o"] = "-%d" % idx["created_at"]
        return response

    def save_model(self, request, obj, form, change):
        reply = (obj.reply or "").strip()
        obj.reply = reply

        if change and reply and not obj.replied_at:
            obj.replied_at = contact_admin_timezone.now()
            obj.status = ContactMessage.Status.REPLIED
            obj.is_read = True

            subject = obj.subject.strip()
            if not subject.lower().startswith("re:"):
                subject = f"Re: {subject}"
            body = (
                f"{reply}\n\n"
                "--\n"
                "Your original message:\n"
                f"{obj.message}\n"
            )
            try:
                send_mail(subject, body, None, [obj.email], fail_silently=False)
            except Exception as exc:
                obj.email_sent = False
                obj.replied_at = None
                obj.status = ContactMessage.Status.NEW
                contact_admin_messages.error(
                    request,
                    f"Reply NOT sent. Your text is kept as a draft; press Send reply to try again. Email to "
                    f"{obj.email} FAILED: {exc}",
                )
            else:
                obj.email_sent = True
                if obj.user_id or User.objects.filter(email__iexact=obj.email).exists():
                    contact_admin_messages.success(
                        request,
                        f"Reply sent: emailed to {obj.email} and delivered "
                        "to their account inbox.",
                    )
                else:
                    contact_admin_messages.success(
                        request,
                        f"Reply emailed to {obj.email}. No account uses "
                        "that email, so there is no inbox copy.",
                    )

        super().save_model(request, obj, form, change)

    def response_change(self, request, obj):
        if "_send" in request.POST:
            return HttpResponseRedirect(request.get_full_path())
        return super().response_change(request, obj)
# SMH_CONTACT_ADMIN_END