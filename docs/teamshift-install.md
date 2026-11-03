# Shipping from enckequity/teamshift

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
4. **Enable in two steps.** First `plugins.enabled: [photon-approvals]` with `security.approval.transport: builtin`, and confirm the plugin loads, the `/photon-approvals` page renders after owner login and the API returns 401 anonymously. Only after the [live acceptance checklist](live-acceptance.md) setup checks pass, switch to `transport: photon-cards` with `transport_fallback: deny`. Restart through the supervisor's drain-aware path, as done for earlier owner changes.
5. **Do not change** `approvals.mode`, the Photon platform config, `PHOTON_ALLOWED_USERS`, the photon2 transport or the Pomerium route.

## Rollback

Set `security.approval.transport: builtin` and reload. Native `/approve` and `/deny` work again immediately. Remove the plugin from `plugins.enabled` and delete the plugin directory if desired. Keep the state directory until pending requests end, then keep or remove it per audit policy.

## Constraints to remember

- `GATEWAY_RELAY_URL` set in a workspace (the iMessage front door) disables Hermes' direct Photon platform there, and those workspaces have no Spectrum project for this plugin. Do not enable it there.
- One approver per tenant. Use it only on a runtime whose approvals should all reach that one person.
- Pin: the plugin has been tested only against Hermes v0.22.2. It uses the supported `register_approval_transport` and dashboard plugin APIs, so a Hermes bump needs the bundle tests re-run before rollout.
