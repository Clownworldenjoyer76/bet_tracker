# PostgreSQL integration

The Django application is now PostgreSQL-aware.

The application defaults to SQLite until `.env` selects:

DB_ENGINE=postgresql

This phase does not change the frontend.

Django reads:

- DB_NAME
- DB_USER
- DB_PASSWORD
- DB_HOST
- DB_PORT
- DB_SSLMODE
- DB_CONN_MAX_AGE

The database driver is Psycopg 3.

The next step after this patch passes is provisioning PostgreSQL and migrating
Django's database schema to it.
