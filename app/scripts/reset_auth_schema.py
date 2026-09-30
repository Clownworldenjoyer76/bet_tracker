from pathlib import Path

import psycopg
from dotenv import dotenv_values
from psycopg import sql

ROOT = Path(__file__).resolve().parent.parent
config = dotenv_values(ROOT / ".env")

engine = (config.get("DB_ENGINE") or "").strip().lower()
if engine not in {"postgres", "postgresql"}:
    raise SystemExit(
        "Refusing schema reset: the active project database is not PostgreSQL."
    )

connection_args = {
    "dbname": config.get("DB_NAME"),
    "user": config.get("DB_USER"),
    "password": config.get("DB_PASSWORD"),
    "host": config.get("DB_HOST") or "127.0.0.1",
    "port": config.get("DB_PORT") or "5432",
}

if not all(connection_args.values()):
    raise SystemExit("Refusing schema reset: PostgreSQL .env settings are incomplete.")

with psycopg.connect(**connection_args, autocommit=True) as connection:
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.auth_user')")
        auth_user_table = cursor.fetchone()[0]

        if auth_user_table:
            cursor.execute("SELECT COUNT(*) FROM public.auth_user")
            user_count = cursor.fetchone()[0]
            if user_count:
                raise SystemExit(
                    "Refusing schema reset: auth_user contains "
                    f"{user_count} user record(s)."
                )

        cursor.execute("SELECT current_user")
        database_owner = cursor.fetchone()[0]

        cursor.execute("DROP SCHEMA public CASCADE")
        cursor.execute(
            sql.SQL("CREATE SCHEMA public AUTHORIZATION {}").format(
                sql.Identifier(database_owner)
            )
        )
        cursor.execute("GRANT USAGE, CREATE ON SCHEMA public TO PUBLIC")

print("EMPTY POSTGRESQL SCHEMA RESET OK")
