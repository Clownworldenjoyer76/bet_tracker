# Bet Tracker — Django Foundation

This is the first Django migration milestone.

## What changed

The application now has a Django foundation, but the frontend itself has not been redesigned or converted.

Django serves the already-verified `frontend/dist` output byte-for-byte. This preserves:

- all 46 existing page filenames and URLs;
- existing HTML, CSS, and JavaScript;
- `nav.html` runtime loading;
- existing data files and JSON paths;
- existing PostHog/frontend behavior;
- the current responsive design and visual baseline.

This compatibility bridge is deliberate. It proves Django can sit behind the site without causing frontend regressions before shared HTML is converted into Django templates or authenticated/private data is introduced.

## Current architecture

```text
Browser
   |
   v
Django
   |
   +-- serves frontend/dist exactly as verified
   |
   +-- Django admin/auth framework installed but not integrated into the UI
   |
   +-- SQLite used only as the temporary local foundation database

frontend/src
   |
   +-- existing source frontend
   |
   +-- build/build.ps1           original Windows build
   +-- scripts/sync_frontend.py  cross-platform equivalent
   |
   v
frontend/dist
```

## Local setup

From PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File ".\setup_local.ps1"
```

Then:

```powershell
powershell -ExecutionPolicy Bypass -File ".\run_local.ps1"
```

Open:

```text
http://127.0.0.1:8000/
```

## Validation

`setup_local.ps1`:

1. creates `.venv`;
2. installs the supported Django 5.2 LTS line;
3. rebuilds and validates the existing frontend;
4. runs `manage.py check`;
5. creates the temporary local SQLite database;
6. runs compatibility tests against every existing frontend page.

## Intentionally not implemented yet

- PostgreSQL
- user registration/login UI
- private user data
- subscriptions
- conversion of the frontend to Django templates
- production deployment

Those are later milestones. This version is a zero-redesign migration boundary.
