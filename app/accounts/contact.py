import hashlib

from django import forms
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .models import ContactMessage

CONTACT_RATE_LIMIT = 5
CONTACT_RATE_WINDOW_SECONDS = 3600


class ContactForm(forms.Form):
    name = forms.CharField(
        label="Name",
        max_length=100,
        widget=forms.TextInput(
            attrs={"autocomplete": "name", "placeholder": "Your name"}
        ),
    )
    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(
            attrs={"autocomplete": "email", "placeholder": "you@example.com"}
        ),
    )
    subject = forms.CharField(
        label="Subject",
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Subject"}),
    )
    message = forms.CharField(
        label="Message",
        min_length=10,
        max_length=5000,
        widget=forms.Textarea(
            attrs={"rows": 7, "placeholder": "How can we help?"}
        ),
    )
    website = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(
            attrs={"tabindex": "-1", "autocomplete": "off"}
        ),
    )


def _rate_key(request):
    ip = (
        request.META.get("HTTP_CF_CONNECTING_IP")
        or request.META.get("REMOTE_ADDR")
        or ""
    )
    return "contact-rate:" + hashlib.sha256(ip.encode("utf-8")).hexdigest()[:32]


@never_cache
@require_http_methods(["GET", "POST"])
def contact_view(request):
    sent_url = reverse("accounts:contact") + "?sent=1"
    sent = request.method == "GET" and request.GET.get("sent") == "1"

    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            if form.cleaned_data["website"]:
                return redirect(sent_url)

            key = _rate_key(request)
            count = cache.get(key, 0)
            if count >= CONTACT_RATE_LIMIT:
                form.add_error(
                    None,
                    "Too many messages from your connection. "
                    "Please try again later.",
                )
            else:
                ContactMessage.objects.create(
                    name=form.cleaned_data["name"].strip(),
                    email=form.cleaned_data["email"].strip().lower(),
                    subject=form.cleaned_data["subject"].strip(),
                    message=form.cleaned_data["message"].strip(),
                    user=(
                        request.user
                        if request.user.is_authenticated
                        else None
                    ),
                )
                cache.set(key, count + 1, CONTACT_RATE_WINDOW_SECONDS)
                return redirect(sent_url)
    else:
        form = ContactForm()

    return render(request, "accounts/contact.html", {"form": form, "sent": sent})
