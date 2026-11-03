# Photon approval cards

Approved scope: a standalone open-source connector for unchanged Hermes. Issue #1. This is custom integration code, not a Hermes fork.

## Contract

Register the supported approval transport. Render only the host-redacted command and description, with Approve once and Deny. Return request.respond(choice); never execute commands or change approval policy. A SQLite compare-and-set accepts one decision for the exact request ID/digest before its deadline. Host timeout remains authoritative. Failure denies. Restart never transfers a decision to another request.

A plain JavaScript native dashboard plugin uses Hermes’s existing session authentication. The API independently requires auth_required, a verified unexpired interactive session matching configured provider/user/org, and the deployment’s configured tenant. POST additionally requires the exact configured Origin, JSON and a custom header. Request URLs contain an opaque non-authorizing ID, no credentials. GET is read-only. DOM text is escaped by React. Wrong identities cannot inspect or resolve requests.

Use a fixed operator-configured existing E.164 DM, never a model-selected recipient or group. The maintained grpcurl binary and official Advanced iMessage schemas send/update the Spectrum launcher card using the existing project token exchange. Store a private send intent before transmission. Never automatically retry uncertain sends. Tokens stay in memory/child environment and never enter argv, logs or SQLite. A failed card update does not reverse a recorded decision. UI state says the decision was recorded, not that execution succeeded.

Each tenant needs its own gateway/container, home, DB, Photon project and authenticated origin. Profiles are not a customer boundary. The in-process approval transport requires a trusted plugin; do not weaken a shared host-isolation policy to load it. No customer activation while the architecture session owns those resources.

## Limits

First release uses the existing Spectrum API/schema contract, not the unrelated Photon 2 beta API. No new polling messenger, native iMessage extension, dashboard replacement, permanent/session grants, task engine, external auth service or execution provider dependency. The native dashboard page may open in a sheet; inline rendering depends on Spectrum/device support and must be tested separately.

## Success criteria

Tests prove valid decision through the host contract; wrong identity/tenant/digest and malformed choice rejection; concurrent approve/deny accepts one; expiry, process restart and failed sends cannot authorize; cross-origin and missing auth rejected; no sensitive URL/argv/logs. Qualify native discovery, mounting and frontend against pinned Hermes v0.22.2 source. Review before release. Live phone/card rendering and real authenticated device actions are separate evidence, never inferred from API acceptance.

## Resource ownership

Development uses an isolated task branch and worktree. Tests run offline from `scripts/test-offline.sh` with temporary databases and no gateway configuration changes. The operator keeps the exact machine/session/resource ledger on the tracking issue. Public artifacts contain no credentials, account identities or runtime receipts.
