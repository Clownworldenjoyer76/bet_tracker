import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.urls import reverse, resolve

expected = {
    "accounts:register": "/register.html",
    "accounts:login": "/login.html",
    "accounts:logout": "/logout.html",
    "accounts:account": "/account.html",
    "accounts:password_reset": "/password_reset.html",
    "accounts:password_reset_done": "/password_reset_done.html",
    "accounts:password_reset_complete": "/password_reset_complete.html",
}

for name, path in expected.items():
    actual = reverse(name)
    if actual != path:
        raise SystemExit(f"{name}: expected {path}, got {actual}")
    resolve(path)

reset_path = reverse(
    "accounts:password_reset_confirm",
    kwargs={"uidb64": "abc", "token": "def"},
)
if reset_path != "/reset-abc-def.html":
    raise SystemExit(f"Unexpected password reset confirmation route: {reset_path}")

print("AUTH ROUTES OK")
print("Registration: /register.html")
print("Login:        /login.html")
print("Account:      /account.html")
print("Password reset flow: configured")
