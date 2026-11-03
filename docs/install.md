# Install and acceptance

Plan for folding this plugin into the product repo (teamshift#416). Nothing here has been done in `enckequity/teamshift`, and nothing is live.

## Bundle layout

```
deploy/photon-approvals/
  README.md            install, enable, verify, recover (this document, adapted)
  MANIFEST.sha256      copied unchanged from this repo at the reviewed commit
  plugin/              the files named in the manifest, same relative paths
  tests/               this repo's tests, run with the pinned Hermes interpreter
```

The manifest lists the 12 runtime files (`plugin.yaml`, `__init__.py`, `hermes_photon_approvals/*.py`, `dashboard/*`). `plugin/` is a verbatim copy, so a PR in teamshift can be checked with `shasum -a 256 -c MANIFEST.sha256` run inside `plugin/`. Record the source commit of this repo in the bundle README. Upstream stays the place to develop; the bundle is updated by copying a new reviewed commit.

The fold-in PR should also:

1. Add a paragraph to `docs/native-deployment-policy.md` recording this as a bounded exception (Dakota, 2026-11-03), with the gap from [native-gap.md](native-gap.md), and the rule that it stays disabled unless the approver, DM and dashboard URL are configured.
2. Update the Photon approval row in `docs/custom-code-current.md` (currently 0 lines) with the real count of the bundled runtime files.
3. Add a test that fails if `plugin/` drifts from `MANIFEST.sha256`, and one that checks `upstream-context.json` still names Hermes commit `d923a5eb487a17c0a68801bba9ef0f56c81040a8`. Any Hermes bump must re-run the bundle tests first.
4. Remove the old "stale package mount" idea for good: this plugin needs no mount and no `pip install`.

## Install on the owner runtime

Owner first. The customer path is blocked by teamshift#56 (own Photon project, DM-only delivery, authenticated page inside Messages).

1. **Prerequisites already in place on the owner runtime** (teamshift#56, PRs #62 and #63): grpcurl 1.9.4 and the official `@photon-ai/advanced-imessage` 2.3.0 proto schemas, plus Spectrum project credentials in the gateway environment. Confirm the two paths below and reuse the same `PHOTON_PROJECT_ID` and `PHOTON_PROJECT_SECRET` the native Photon channel uses. No new account or secret. Do not use the Photon 2 Beta line's key.
2. **Copy** `plugin/` to `$HERMES_HOME/plugins/photon-approvals/` as the runtime user (UID 10000 on native runtimes). Check every file against `MANIFEST.sha256`. Then run `hermes plugins validate` on the directory.
3. **Configure** through the runtime's existing secret and config manager, for both the gateway and the dashboard process:

   | Variable | Owner value |
   | --- | --- |
   | `PHOTON_APPROVAL_TENANT_ID` | a fixed label, for example `owner` |
   | `PHOTON_APPROVAL_PUBLIC_URL` | `https://owner.teamshift.io/native` (from `deploy/owner-web/native-dashboard.yaml`) |
   | `PHOTON_APPROVAL_PROVIDER` | `self-hosted` |
   | `PHOTON_APPROVAL_USER_ID` | Dakota's Dex subject, read from a verified native session, never from an email address |
   | `PHOTON_APPROVAL_ORG_ID` | empty (the self-hosted provider has no organization) |
   | `PHOTON_APPROVAL_DM` | Dakota's E.164 number, from the runtime secret store |
   | `PHOTON_APPROVAL_STATE_DIR` | a 0700 directory inside the runtime's private home, shared by gateway and dashboard |
   | `PHOTON_APPROVAL_GRPCURL`, `PHOTON_APPROVAL_PROTO_DIR` | the installed grpcurl and `.../advanced-imessage/2.3.0/proto` |

   Secrets use 1Password references as in `deploy/photon2-owner`. Resolved values never go in config files, logs or the card.
4. **Enable in two steps.** First `plugins.enabled: [photon-approvals]` with `security.approval.transport: builtin`, and confirm the plugin loads, the `/photon-approvals` page renders after owner login and the API returns 401 anonymously. Only after the [live acceptance checklist](#live-acceptance-checklist-owner-phone-test) setup checks pass, switch to `transport: photon-cards` with `transport_fallback: deny`. Restart through the supervisor's drain-aware path, as done for earlier owner changes.
5. **Do not change** `approvals.mode`, the Photon platform config, `PHOTON_ALLOWED_USERS`, the photon2 transport or the Pomerium route.

Enable with:

```yaml
plugins:
  enabled: [photon-approvals]   # keep your other entries
security:
  approval:
    transport: photon-cards
    transport_fallback: deny
```

Rules for the values: the public URL is HTTPS with no credentials or query (a plain path prefix is fine); the org ID may be empty only when the provider has no organization; the DM is a fixed E.164 number, never a group; the state directory is absolute, owned by the runtime user, mode 0700 (the database is 0600). The state holds redacted command text, the decision and card receipts, never tokens. Photon credentials come from the secret manager as `PHOTON_PROJECT_ID` and `PHOTON_PROJECT_SECRET`. Never retry an uncertain send by hand; inspect the receipt first.

## Rollback

Set `security.approval.transport: builtin` and reload. Native `/approve` and `/deny` work again immediately. Remove the plugin from `plugins.enabled` and delete the plugin directory if desired. Keep the state directory until pending requests end, then keep or remove it per audit policy.

## Constraints to remember

- `GATEWAY_RELAY_URL` set in a workspace (the iMessage front door) disables Hermes' direct Photon platform there, and those workspaces have no Spectrum project for this plugin. Do not enable it there.
- One approver per tenant. Use it only on a runtime whose approvals should all reach that one person.
- Pin: the plugin has been tested only against Hermes v0.22.2. It uses the supported `register_approval_transport` and dashboard plugin APIs, so a Hermes bump needs the bundle tests re-run before rollout.

## Live acceptance checklist: owner phone test

Not run. This is the checklist for a person to run on the owner runtime after the plugin is installed with `transport: builtin`. Use only harmless commands that Hermes will flag, for example removing an empty directory the test created. Record each result and the date on teamshift#416 or the rollout issue. Do not paste phone numbers, tokens or the Dex subject.

## Setup (before enabling the transport)

1. `hermes plugins validate` passes on the installed directory and every file matches `MANIFEST.sha256`.
2. Anonymous `GET https://owner.teamshift.io/native/api/plugins/photon-approvals/requests/x` returns 401 or a login redirect, never data.
3. Signed in as the owner in a normal browser, `/native/photon-approvals` renders with no request and shows "unavailable". With a signed-in non-owner account, a known request ID returns 403.
4. grpcurl 1.9.4 runs, and the proto schema test passes there (`PHOTON_APPROVAL_GRPCURL` and `PHOTON_APPROVAL_PROTO_DIR` set).
5. Native Photon text still works (send a text, get the reply) and native `/approve` still resolves a harmless request. This is the rollback baseline.

## Enable, then test on the phone

Switch to `transport: photon-cards`, `transport_fallback: deny`, and restart through the supervisor.

1. **Card arrives.** Trigger one harmless flagged command. One card appears in the existing owner conversation within about 10 seconds. The bubble says "Review a command", with no command text and no token in the link.
2. **Opens signed in.** Tap the card. The page loads inside Messages. Record whether Pomerium and the Hermes sign-in complete there, or only after a redirect to Safari. If login cannot complete in the webview, stop: that is the known open risk (teamshift#56).
3. **Approve once.** The page shows the redacted command and reason. Tap Approve once. The page says the approval is recorded. The command runs once in the conversation. A second tap does nothing.
4. **Deny.** Trigger another. Tap Deny. The command does not run, and the agent reports the denial.
5. **Replay.** Reopen the first card. It shows approved/expired, buttons disabled. Trigger a third request and confirm the old card cannot answer it.
6. **Concurrent.** Trigger two requests close together. Each card answers only its own.
7. **Expiry.** Trigger one and do nothing until the timeout. The command does not run, the bubble updates to "Request expired" (best effort), and the page shows it expired.
8. **Wrong identity.** Open a request URL in a browser signed in as a different account. Nothing is shown and no decision is accepted.
9. **Logout and restart.** Sign out of the dashboard and confirm the card page asks for sign-in. Restart the gateway while a request is pending: that request ends denied, and a new one works.
10. **Send failure.** Temporarily point `PHOTON_APPROVAL_GRPCURL` at a bad path on a test copy (not production): the command is denied and nothing is resent.
11. **Rollback.** Set `transport: builtin`, reload, and confirm native `/approve` works again.

## Pass criteria

All of 1 to 11 pass, no secret appears in the logs or card, and the audit rows in the state database show one decision per request. Record device model and iOS version. Any failure in 2, 3, 5 or 8 blocks wider use.
