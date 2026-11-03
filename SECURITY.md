# Security

Treat this plugin as trusted gateway code. Run one tenant per isolated gateway with its own credentials, authenticated origin and private state. The request URL grants no authority. Only the configured, verified native dashboard identity can inspect and answer requests.

The decision-path review (request binding, replay, expiry, CSRF, approver identity, card URL) is in [docs/security-review.md](docs/security-review.md). One approver per tenant: the configured verified dashboard identity, not anyone who can text the gateway.

Report suspected vulnerabilities through this repository's private vulnerability reporting when available. Do not include credentials, private commands, phone numbers or customer data in public issues.

Changes to authentication, request binding, approval scope, expiry or state transitions require focused regression tests and independent review. A preview update or recorded decision is not proof that Hermes authorized or executed a command. No automatic retry follows uncertain delivery.
