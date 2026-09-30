# Stripe billing integration

This phase connects the existing internal entitlement layer to Stripe Billing.

The application still treats `UserSubscription` as the canonical authorization
record. Stripe is an external billing source that updates that record through
verified webhooks and reconciliation.

## Installed flows

### Hosted Checkout

Authenticated users can start a Pro subscription at:

`POST /billing/checkout/`

The server creates a Stripe-hosted Checkout Session in `subscription` mode
using `STRIPE_PRO_PRICE_ID`.

No premium access is granted from the browser redirect. Access changes only
after a signed Stripe webhook updates the local subscription record.

### Customer portal

Users with a linked Stripe Customer can open:

`POST /billing/portal/`

The Stripe customer portal is used for payment-method management, subscription
changes, and cancellation.

### Webhook

Stripe sends events to:

`POST /billing/webhook/`

The endpoint verifies the raw request body with `Stripe-Signature` and
`STRIPE_WEBHOOK_SECRET`.

Handled events:

- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_failed`

Every event ID is stored in `BillingEvent` so repeated deliveries are
idempotent.

### Reconciliation

`scripts/reconcile_stripe_billing.py` can refresh linked Stripe subscriptions
into PostgreSQL. It is intended for operational repair/reconciliation and
requires a configured Stripe secret key.

## Database models

`BillingCustomer`

Maps one local user to a Stripe Customer ID.

`BillingSubscription`

Stores Stripe subscription linkage and provider status while leaving
`UserSubscription` as the application's canonical entitlement record.

`BillingEvent`

Stores event IDs, types, processing timestamps, and processing errors for
idempotency and operational visibility. Full Stripe event payloads are not
stored.

## Environment variables

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRO_PRICE_ID`
- `STRIPE_PORTAL_CONFIGURATION_ID` — optional

Use Stripe test-mode values until the complete flow has been verified.

## Webhook event selection

Configure the Stripe webhook endpoint for the event types listed above.
The endpoint must be publicly accessible over HTTPS in production.

For local testing, Stripe CLI can forward signed events to the local Django
webhook endpoint.

## Security behavior

- Checkout and customer portal creation require an authenticated Django user.
- Checkout uses the authenticated user's server-side account identity.
- Webhooks are CSRF exempt because authenticity is established with Stripe's
  webhook signature.
- The raw webhook body is used for signature verification.
- Checkout success redirects never grant access by themselves.
- The Stripe secret and webhook signing secret remain environment variables.
