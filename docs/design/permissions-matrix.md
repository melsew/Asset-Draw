# Permission matrix (least privilege; enforced server-side on every endpoint)

✓ = allowed · o = own resources only · r = read-only · — = never. There is **no** permission to choose, edit or
override a winner or any draw input, for any role including SUPER_ADMIN.

| Capability | SUPER_ADMIN | ADMIN | CAMPAIGN_MANAGER | FINANCE | AUDITOR | VENDOR | CUSTOMER_SUPPORT | PARTICIPANT |
|---|---|---|---|---|---|---|---|---|
| Manage staff accounts, roles, system config | ✓ | — | — | — | — | — | — | — |
| Approve/reject/suspend vendors | — | ✓ | — | — | — | — | — | — |
| Verify assets (custody evidence) | — | ✓ | — | — | — | — | — | — |
| Create/edit own vendor, assets, draft campaigns | — | — | — | — | — | o | — | — |
| Review campaigns (start review) | — | ✓ | ✓ | — | — | — | — | — |
| Approve/reject campaigns | — | ✓ | — | — | — | — | — | — |
| Schedule, close early, lock pool | — | — | ✓ | — | — | — | — | — |
| Suspend/resume/cancel campaigns | — | ✓ | — | — | — | — | — | — |
| Retry a draw (must differ from locker) | — | ✓ | — | — | — | — | — | — |
| Record winner verification | — | ✓ | — | — | ✓ | — | — | — |
| Record prize fulfillment | — | — | ✓ | — | — | r (own) | — | — |
| View payments, reconcile, request refunds | — | r | — | ✓ | r | r (own campaign totals) | — | o |
| Approve refunds | — | — | — | ✓ (≠ requester) | — | — | — | — |
| View participants' phone/email | — | — | — | — | — | — | r (masked, audited) | o |
| View audit logs, verify chain | r | r | — | — | ✓ | — | — | — |
| Participate, view own entries/results | — | — | — | — | — | — | — | ✓ |
| Vendor analytics (anonymised aggregates) | — | r | r | — | r | o | — | — |
| Public verification pages | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (no login needed) |
Rules: staff roles require MFA (A-14); a user cannot approve their own vendor/campaign; entry-mode approvals
(A-16) require ADMIN + a legal reference; every use of CUSTOMER_SUPPORT PII access is audited.
