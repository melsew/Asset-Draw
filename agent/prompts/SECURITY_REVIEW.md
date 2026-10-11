# Security review prompt
Act as an application-security reviewer. Inspect the actual source and migrations. For each finding give severity,
file/function, attack scenario, fix and required test. Cover auth, RBAC/IDOR, injection, XSS/CSRF/CORS, SSRF, uploads,
secrets, sessions, rate limits, payment webhooks and replay, races, draw integrity, audit-chain integrity, PII leakage,
logging and backups. Do not invent vulnerabilities without evidence.
