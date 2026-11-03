# Security

Treat this plugin as trusted gateway code, one tenant per isolated gateway with its own authenticated origin and private state. The link grants no authority; only the configured, verified dashboard identity can inspect and answer a request. The decision-path review is in [docs/security-review.md](docs/security-review.md).

Report suspected vulnerabilities through this repository's private vulnerability reporting. Do not include credentials, private commands, phone numbers or customer data in public issues.

Changes to authentication, request binding, approval scope, expiry or state transitions need focused regression tests and independent review. A recorded decision is not proof that Hermes authorized or executed a command. An uncertain send is never retried.
