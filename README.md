# Hermes Photon approval cards

Approve a specific Hermes command once, or deny it, from an authenticated workspace opened inside Messages. This standalone plugin uses Hermes's approval transport and dashboard plugin APIs. Hermes source stays unchanged and Hermes keeps final authority over execution.

**Status: being revived as a TeamShift feature (teamshift#416).** Offline contract tests run against the pinned Hermes v0.22.2 source (`scripts/test-offline.sh`). Inline button rendering was confirmed on a device using the harmless demo. Live authenticated phone approval is not yet qualified. The earlier multi-select poll is not used by this connector. Cards go through Spectrum's existing shared-line API, not the Photon 2 beta line. See [what native Hermes already does](docs/native-gap.md) for why the plugin is still needed.

## What happens

1. Hermes determines that a command needs approval and gives this plugin a redacted, request-bound prompt.
2. The plugin sends one Spectrum card to the operator-configured existing DM. Its URL contains a request ID, not a credential.
3. Opening the card loads the native Hermes dashboard plugin and its existing login. The API checks the configured provider, user and organization.
4. Approve once or Deny records one atomic decision. Hermes validates its request ID, digest, allowed scope and timeout before continuing.

An old card cannot approve a later request. Multiple clicks have one winner. Missing identity, expiry, invalid choices and delivery failures deny. A recorded decision is not proof that a command executed. A host interruption or timeout can discard a late response. Reopen the card to refresh state; consult the original conversation for execution results.

## Requirements

- Unmodified Hermes with `register_approval_transport` and native dashboard plugins. Tested revision: `d923a5eb487a17c0a68801bba9ef0f56c81040a8` (v0.22.2). Other versions need qualification.
- One isolated gateway/container and private home per tenant. Profiles alone are not tenant isolation. Gateway and dashboard must share this tenant's private state directory.
- Existing authenticated HTTPS dashboard reachable from the recipient's device (a path prefix such as `/native` is fine). The plugin refuses an ungated dashboard. It does not expose a private dashboard or create an authentication service.
- Trusted in-process plugin execution. Do not loosen a shared host's isolation policy to install it.
- An existing Spectrum shared-line project and designated E.164 DM, plus the Spectrum Messages extension for in-Messages rendering. Groups and dedicated lines are not supported in this release.
- Maintained `grpcurl` 1.9.4 and official `@photon-ai/advanced-imessage` 2.3.0 proto schemas. These are runtime prerequisites, not vendored code. Verify publisher checksums/integrity before installation.

## Install on the gateway

Use a reviewed release or full commit SHA, run in the runtime's own environment. The plugin directory is self-contained: copying the files listed in `MANIFEST.sha256` into `$HERMES_HOME/plugins/photon-approvals` is the whole install, with no `pip install` into Hermes's environment. Check each file against the manifest, then validate with Hermes:

```sh
# APPROVAL_REVISION is the reviewed full commit SHA.
git clone https://github.com/enckequity/hermes-photon-approvals /tmp/approvals-src
git -C /tmp/approvals-src checkout --detach "$APPROVAL_REVISION"
DEST="$HERMES_HOME/plugins/photon-approvals"
(cd /tmp/approvals-src && for f in $(awk '{print $2}' MANIFEST.sha256) MANIFEST.sha256; do
  mkdir -p "$DEST/$(dirname "$f")" && cp "$f" "$DEST/$f"; done)
(cd "$DEST" && shasum -a 256 -c MANIFEST.sha256)   # sha256sum -c on Linux
hermes plugins validate "$DEST"
```

TeamShift ships it from `deploy/photon-approvals` instead; see [the install and fold-in plan](docs/teamshift-install.md).

Installation and enabling are distinct. Keep the transport set to `builtin` until configuration and authenticated access pass. Do not install arbitrary latest code into production.

Set these variables through your existing runtime secret/config manager for both gateway and dashboard:

```dotenv
PHOTON_APPROVAL_TENANT_ID=your-isolated-tenant-id
PHOTON_APPROVAL_PUBLIC_URL=https://your-authenticated-agent.example   # add a path prefix if the dashboard has one
PHOTON_APPROVAL_PROVIDER=your-native-auth-provider-id
PHOTON_APPROVAL_USER_ID=your-verified-stable-user-id
PHOTON_APPROVAL_ORG_ID=your-verified-org-id
PHOTON_APPROVAL_DM=+15555550123
PHOTON_APPROVAL_STATE_DIR=/private/hermes-home/photon-approvals
PHOTON_APPROVAL_GRPCURL=/absolute/path/to/grpcurl
PHOTON_APPROVAL_PROTO_DIR=/absolute/path/to/advanced-imessage/2.3.0/proto
# Existing runtime credentials, supplied by your secret manager:
PHOTON_PROJECT_ID=your-existing-spectrum-project-id
PHOTON_PROJECT_SECRET=your-existing-spectrum-project-secret
```

The public URL must be the HTTPS URL of the authenticated dashboard, with no query or credentials. A plain path prefix (for example `/native`) is allowed and is used only in the card link. Origin checks use scheme and host. The org ID may be empty only when the verified provider has no organization. Obtain the identity from verified native session evidence, never a guessed email address. Do not copy an owner's Photon credentials into customer gateways. The DM and identity are operator configuration, never model arguments.

After native discovery, authenticated route checks and device qualification, explicitly enable and select the transport:

```yaml
plugins:
  enabled: [photon-approvals] # retain your other enabled entries
security:
  approval:
    transport: photon-cards
    transport_fallback: deny
```

The transport does not change `approvals.mode`. Hermes still decides which actions need approval. Restart gateway/dashboard using your normal supervisor after configuration changes. Verify the plugin's native `/photon-approvals` page and a harmless approval request before production use.

## Recovery and operations

Restore `security.approval.transport: builtin` to use stock controls. Do not remove or replace state while a request is pending. No session or permanent grant is offered. Timeouts are capped at 300 seconds and remain bounded by Hermes's own timeout.

The state directory must be owned by the runtime user with mode 0700; the SQLite database is 0600. It stores redacted display text, identity scope, decision and non-credential card receipts. Keep it inside the tenant's trusted gateway boundary, away from untrusted execution environments. It is not a separate protection against code that can already edit that user's database or Hermes configuration. It never stores Photon tokens or project secrets.

A private intent is written before sending. Do not automatically retry an uncertain send: inspect its receipt and provider state first. Bubble updates are best effort and may be skipped near the deadline; the authenticated page reads canonical state. Retain the private state only as long as your audit policy requires. Remove it only after all pending requests have ended and the plugin is disabled.

## Tests

```sh
scripts/test-offline.sh
```

This clones Hermes v0.22.2 (checked against commit `d923a5eb487a17c0a68801bba9ef0f56c81040a8`) and builds a Python 3.14 virtualenv under `.work/`, then runs the Python and Node suites. It needs `git`, `uv` and `node`, and sends no message and calls no provider. To also run the official proto-schema regression, set `PHOTON_APPROVAL_GRPCURL` (grpcurl 1.9.4) and `PHOTON_APPROVAL_PROTO_DIR` (the `proto` directory of `@photon-ai/advanced-imessage` 2.3.0) first; that test is skipped otherwise.

After changing a runtime file, run `scripts/make-manifest.sh` and commit `MANIFEST.sha256`; a test fails when it is stale.

Tests use synthetic identities and temporary databases. See [native gap](docs/native-gap.md), [security review](docs/security-review.md), [install and fold-in](docs/teamshift-install.md), [live acceptance](docs/live-acceptance.md), [design](docs/design.md), [plan](docs/plan.md) and [verification](docs/verification.md).

MIT licensed. This connector is maintained independently of Nous Research and Photon.
