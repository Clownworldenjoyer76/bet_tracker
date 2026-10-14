"""Opt-in Django transport for native React account pages.

Off by default. No data is sent to the static GitHub Pages origin; these
pages must be served from the authenticated Django origin.
"""
import json
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.utils.cache import patch_vary_headers

ACCOUNT_SHELLS = frozenset({
    "login.html", "register.html", "account.html", "contact.html",
    "password_reset.html", "password_reset_done.html",
    "password_reset_complete.html", "index.html",
})


def react_enabled():
    return getattr(settings, "REACT_ACCOUNT_PAGES_ENABLED", False) is True


def form_bootstrap(request, form=None, *, page, extra=None):
    bootstrap = {
        "page": page,
        "authenticated": bool(request.user.is_authenticated),
        "csrfToken": get_token(request),
        "values": {},
        "errors": {},
        "nonFieldErrors": [],
    }
    if form is not None:
        fields = getattr(form, "fields", {})
        for name in fields:
            if "password" in name.lower() or "token" in name.lower():
                continue
            value = form[name].value()
            if value is not None and isinstance(value, (str, int, float)):
                bootstrap["values"][name] = str(value)
        for name, details in form.errors.get_json_data().items():
            messages = [str(part["message"]) for part in details]
            if name == "__all__":
                bootstrap["nonFieldErrors"] = messages
            else:
                bootstrap["errors"][name] = messages
    if extra:
        bootstrap.update(extra)
    return bootstrap


def account_bootstrap(request, *, context, form):
    data = form_bootstrap(request, form, page="account")
    user = request.user
    prefs = form.instance
    plan = context.get("access_plan")
    features = context.get("access_features") or []
    inbox = context.get("inbox_messages") or []
    data["profile"] = {
        "email": user.email,
        "joined": user.date_joined.strftime("%b %d, %Y"),
        "plan": (plan.get("name", "") if isinstance(plan, dict) else getattr(plan, "name", "")) or "",
        "status": str(context.get("access_status_label") or ""),
        "features": [str(f) for f in features],
        "messages": [
            {
                "subject": m.subject, "message": m.message,
                "created": m.created_at.isoformat(),
                "replied": bool(m.replied_at),
                "reply": m.reply if m.replied_at else "",
                "repliedAt": m.replied_at.isoformat() if m.replied_at else "",
            }
            for m in inbox
        ],
        "timezone": prefs.timezone,
        "bankroll": str(prefs.bankroll) if prefs.bankroll is not None else "",
        "kellyFraction": str(prefs.kelly_fraction),
        "timezoneOptions": [
            {"value": str(value), "label": str(label)}
            for value, label in form.fields["timezone"].choices
        ],
        "billingCheckoutConfigured": bool(context.get("billing_checkout_configured")),
        "billingCustomerLinked": bool(context.get("billing_customer_linked")),
        "billingExternalStatus": str(context.get("billing_external_status") or ""),
        "billingNotice": str(context.get("billing_notice") or ""),
    }
    return data


def render_react(request, shell_name, bootstrap):
    if shell_name not in ACCOUNT_SHELLS:
        raise ValueError("Unapproved React account shell")
    path = Path(settings.FRONTEND_DIST_DIR).resolve() / shell_name
    if not path.is_file():
        raise FileNotFoundError("React account shell not deployed: " + shell_name)
    html = path.read_text(encoding="utf-8")
    if html.count('<div id="root"></div>') != 1 or html.count('</body>') != 1:
        raise ValueError("Invalid or unbuilt React account shell: " + shell_name)
    if './assets/' not in html:
        raise ValueError("Account shell has no built asset references")
    # Vite shells use relative ./assets. Nested /reset/UID/TOKEN.html
    # requires a base URL for those paths to resolve to /assets/.
    if '</head>' not in html:
        raise ValueError("React account shell missing head")
    html = html.replace('</head>', '<base href="/">\n</head>', 1)
    # JSON-in-script escaped against HTML/script termination and entity mixing.
    payload = json.dumps(bootstrap, ensure_ascii=False, separators=(",", ":"))
    payload = (payload.replace("&", "\\u0026")
                      .replace("<", "\\u003c")
                      .replace(">", "\\u003e")
                      .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))
    tag = '<script id="smh-account-bootstrap" type="application/json">' + payload + '</script>'
    html = html.replace('</body>', tag + '\n</body>', 1)
    response = HttpResponse(html, content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "private, no-store"
    patch_vary_headers(response, ["Cookie"])
    return response
