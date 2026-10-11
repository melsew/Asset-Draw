# Security baseline (decisions, not options)

**Sessions.** Access token: JWT, 15 minutes, held in memory only (never localStorage). Refresh token: opaque
256-bit random, stored only as SHA-256 in `refresh_sessions`, sent as an `HttpOnly; Secure; SameSite=Strict`
cookie scoped to `/api/v1/auth`; rotated on every use; reuse of an old token revokes its whole `family_id`.
`refresh`/`logout` also require an `Origin` check and a custom header (CSRF defence in depth).
**Auth.** Participants: phone + OTP (6 digits, hashed, 5-minute TTL, ≤5 attempts). Staff: email + Argon2id
password + TOTP (A-14). Generic errors; no account enumeration.
**Rate limiting** (Redis): per IP and per phone/account on login, OTP request/verify, participate, payment,
public endpoints. **Headers:** HSTS, CSP (no inline scripts), `X-Content-Type-Options`, `Referrer-Policy`,
frame denial; strict CORS allow-list.
**Payments.** Provider secrets backend-only; verify webhook signature *and* re-query provider status; check
amount, currency, campaign and merchant reference; idempotent on `(provider, provider_event_id)` else payload
hash; the mock provider cannot start in production (A-15).
**Draw.** protocol §6; seed encrypted at rest, unreadable by the API DB role before reveal.
**Uploads.** Size and content-type limits, hash stored, object storage private, signed URLs.
**Data.** No PII in audit metadata, logs, verification packages, or URLs; encrypted, restore-tested backups.
**Secrets** only from the environment/secret manager; `.env` never committed; CI secret scanning.
**Operations.** Structured JSON logs with request IDs; Sentry (PII scrubbing on); dependency and image
vulnerability scanning in CI; least-privilege DB roles (`database-design.md` §7).
