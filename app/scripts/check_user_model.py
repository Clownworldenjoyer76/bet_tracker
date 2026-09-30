import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

if User.USERNAME_FIELD != "email":
    raise SystemExit("Custom user validation failed: USERNAME_FIELD is not email.")

if User.REQUIRED_FIELDS != []:
    raise SystemExit("Custom user validation failed: REQUIRED_FIELDS is not empty.")

if any(field.name == "username" for field in User._meta.get_fields()):
    raise SystemExit("Custom user validation failed: username field still exists.")

check_email = "auth-foundation-check@example.invalid"
check_password = "FoundationCheck!2026"

with transaction.atomic():
    user = User.objects.create_user(
        email=check_email.upper(),
        password=check_password,
    )

    if user.email != check_email:
        raise SystemExit("Custom user validation failed: email normalization failed.")

    if not user.check_password(check_password):
        raise SystemExit("Custom user validation failed: password hashing failed.")

    if User.objects.get_by_natural_key(check_email) != user:
        raise SystemExit("Custom user validation failed: natural-key lookup failed.")

    transaction.set_rollback(True)

print("CUSTOM USER MODEL OK")
print("Login identifier: email")
print("Username field: removed")
print("Validation record persisted: no")
