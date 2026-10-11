# Phase 2 — Authentication and RBAC
Read first: AGENTS.md, docs/decisions.md, docs/design/security.md, docs/design/permissions-matrix.md.
Implement: phone+OTP for participants (SMS behind an adapter; console adapter in dev only), staff email+Argon2id+TOTP,
JWT access + rotating opaque refresh cookies with reuse detection, logout/revocation, Redis rate limiting, role
assignment by SUPER_ADMIN only, `/users/me`, an authorization dependency driven by the permission matrix.
Tests: every matrix cell for a representative endpoint set; revoked/rotated/reused refresh tokens; OTP brute force and
expiry; rate limits; no user enumeration; passwords never logged. Do not invent permissions absent from the matrix.
