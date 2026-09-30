import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.conf import settings
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT 1")
    cursor.fetchone()

engine = settings.DATABASES["default"]["ENGINE"]
name = settings.DATABASES["default"]["NAME"]

print("DATABASE CONNECTION OK")
print(f"Engine: {engine}")
print(f"Name:   {name}")

if engine.endswith("postgresql"):
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_user, version()")
        database, user, version = cursor.fetchone()

    print(f"Database: {database}")
    print(f"User:     {user}")
    print(f"Server:   {version.split(',')[0]}")
