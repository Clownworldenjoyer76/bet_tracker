# React V2 — all user-facing pages migration (work in progress)

Status: **DRAFT — DO NOT DEPLOY**

Architecture agreed October 13, 2026:
- One native React/TSX maintained page per actual user-facing page.
- Django remains the backend and is responsible for authentication, CSRF protection, secure sessions, database operations, billing, entitlements, contact rate limiting, and password-reset tokens.
- **Django Admin remains Django-managed.**
- CFL placeholder is excluded.

## Implemented on this draft branch
- React `FootballMaster.tsx` with NFL and CFB links; CFL intentionally omitted.
- React `PropsMaster.tsx` with links to existing prop tools.
- `/ncaab_dashboard.html` mapped to the already-existing native NCAAM React component.
- Native `MatDashboard.tsx` shortcuts.
- Draft native React pages: About, Accessibility, Disclaimer, FAQ, Methodology, Privacy, Responsible Gambling, Terms.
- Corresponding React Router entries, Vite shell inputs, and shared navigation route recognition.
- Draft React home view, **not functionally equivalent** to the currently signed-in/signed-out Django homepage.

## CRITICAL: not completed
- The eight information pages contain **new draft wording** (historical HTML files had largely blank info content). Privacy and Terms deliberately carry a draft label and must not replace approved legal documents without operator/legal review. Other informational wording also requires editorial approval.
- Home page parity: preserve announcements, membership, sponsored panel, league tiles, games, history, signed-in/signed-out behavior, and accessibility.
- Account page parity: member details, entitlements, private message inbox, preferences, billing checkout and portal, and logout.
- Authentication pages: login, registration, logout, password reset request/sent/confirm/complete.
- Contact form: retain Django validation, spam honeypot, rate limiting, authenticated message linkage and error states. Current `/contact.html` is Django-owned.
- Backend integration: create appropriate session/bootstrap endpoints or safe Django-rendered React shell, preserving CSRF, redirects, session cookies and POST actions.
- Django URL dispatcher: account/auth/home/contact routes currently intercept paths before the frontend-file fallback. Do not rewrite these until backend + UI parity and tests pass.
- The existing `react/scripts/deploy-react-to-production.ps1` intentionally denies most of the new page shells. Do NOT relax its allowlist or denylist before approved staging/cutover.
- Existing `app/frontend/src/pages` HTML sources have NOT been removed and `app/frontend/dist` has NOT been changed.
- No Vite build, TypeScript compilation, Django tests, or live browser testing has been executed from the assistant environment.

## Required release gates
1. Complete account, login, registration, password reset, billing and contact screens, and home parity.
2. Exercise security tests: CSRF rejection, login/session, password-reset token safety, redirects, rate limit, permissions and private inbox leakage.
3. Test React and Django paths on both the `api.sportsmodelhub.com` and `bt.sportsmodelhub.com` hostnames; GitHub Pages is static and **cannot** directly serve Django-backed authenticated routes, so cross-origin/cookie issues must be handled deliberately.
4. Verify content approval, keyboard support, and layout/feature parity.
5. Run `npm ci`, `npx tsc --noEmit`, `npm run build` with careful review of any snapshot-sync side effects.
6. Stage controlled backup/deploy/rollback and update allowlist only after all required tests pass, operator approves, and original Django route behavior can be restored quickly.
