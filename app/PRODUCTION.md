# Production infrastructure foundation

This phase makes the Django application deployable without choosing a specific
hosting company.

It does not perform DNS cutover, provision a production database, configure
Stripe credentials, or deploy the application.

## Production settings module

Production uses:

`config.production`

Local development continues using:

`config.settings`

The production module forces `DEBUG = False` and adds:

- secure session and CSRF cookies
- HTTPS redirect support
- optional trusted reverse-proxy SSL header handling
- environment-controlled HSTS
- `X-Frame-Options: DENY`
- content-type sniffing protection
- production console logging
- WhiteNoise for Django-collected static files
- a dedicated `STATIC_ROOT`

Deployment-specific settings are validated before startup by the supplied
deployment scripts.

## Required production environment

Start from:

`.env.production.example`

Required deployment-specific values include:

- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- PostgreSQL connection variables

The production secret must not be committed to source control.

`DJANGO_CSRF_TRUSTED_ORIGINS` should contain the complete HTTPS origin, while
`DJANGO_ALLOWED_HOSTS` contains hostnames only.

## Reverse proxies and HTTPS

`DJANGO_TRUST_PROXY_SSL_HEADER` defaults to `false`.

Set it to `true` only when Django is behind a trusted reverse proxy that
correctly overwrites `X-Forwarded-Proto`.

This setting matters because blindly trusting a client-supplied forwarded
protocol header can weaken HTTPS handling.

`DJANGO_SECURE_SSL_REDIRECT` defaults to `true` in production.

## HSTS rollout

HSTS defaults to zero seconds intentionally.

After the deployed domain is confirmed to work exclusively over HTTPS, stage
HSTS deliberately:

1. start with a short value such as 3600 seconds;
2. verify the site and all relevant subdomains;
3. increase the duration gradually;
4. enable `includeSubDomains` only when every subdomain is HTTPS-safe;
5. do not enable preload until the domain is intentionally ready for browser
   preload requirements.

## Application server

Production uses Gunicorn.

Startup script:

`deploy/start.sh`

The script validates production configuration before starting Gunicorn.

Default tuning:

- 2 workers
- 4 threads per worker
- 60 second timeout

These are initial values, not permanent capacity assumptions. Tune them after
observing real CPU, memory, latency, and traffic.

## Pre-deploy procedure

Run:

`deploy/predeploy.sh`

It performs:

1. strict production configuration validation
2. frontend build/synchronization
3. `collectstatic`
4. Django migrations
5. Django deployment checks

Migrations are deliberately kept out of the web-worker startup command so
multiple workers/instances do not race to migrate the database.

## Static-file strategy

There are two existing static surfaces.

### Django static files

Django admin and app static files collected through the staticfiles framework
are served by WhiteNoise from `STATIC_ROOT`.

### Existing frontend distribution

The existing 46-page frontend remains in `frontend/dist` and continues through
the verified compatibility view so routes and runtime behavior do not change in
this infrastructure phase.

A later host-specific reverse proxy or CDN may serve those exact built files
directly if performance measurements justify it, but that optimization should
not silently alter application routes or authentication behavior.

## Health endpoints

Liveness:

`GET /healthz`

This confirms that the Django process can answer requests. It intentionally
does not require PostgreSQL.

Readiness:

`GET /readyz`

This checks:

- PostgreSQL query execution
- existence of the built frontend index

It returns HTTP 503 when either dependency is unavailable.

Neither endpoint exposes exception details or credentials.

## Logging

Production logging writes to stdout/stderr so the eventual hosting platform can
collect logs.

The Django logger does not intentionally log request bodies, database
passwords, Stripe secrets, or environment-variable values.

Gunicorn access and error logs are also written to stdout/stderr.

## Email

The existing password-reset flow requires a real production email provider.

Production environment variables are available for Django's SMTP backend.
Do not leave the local console email backend in place for a real production
launch.

## Stripe

Stripe code remains installed.

Stripe account configuration and end-to-end test-mode validation are
deliberately shelved. Production infrastructure does not require Stripe
credentials to be populated yet.

Keep those variables empty until the separate Stripe handoff is resumed.

## Rollback expectations

This production-foundation phase has no database schema migration.

If the application deployment itself must be rolled back, restore the prior
application release while leaving already-successful database migrations in
place unless a migration has been explicitly reviewed as safe to reverse.

Do not automatically reverse production database migrations as part of a web
code rollback.

Before any production cutover:

- take a database backup/snapshot using the selected host's PostgreSQL tooling;
- record the deployed application revision;
- run the pre-deploy procedure once;
- verify `/healthz` and `/readyz`;
- verify authentication and account pages;
- verify public frontend routes;
- only then change DNS/cut traffic.

## Next infrastructure decision

The next phase after this foundation is to select the actual production host.

That choice should be based on concrete requirements such as:

- PostgreSQL hosting
- persistent/runtime filesystem expectations
- deployment workflow
- custom domain and TLS support
- geographic region
- backup/restore capabilities
- log retention/observability
- expected traffic and budget

The host selection should not require rewriting the application foundation.
