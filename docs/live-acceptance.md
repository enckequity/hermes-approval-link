# Rollout and live acceptance

Not run. Nothing here has been done in `enckequity/teamshift`, and nothing is live.

## Fold-in plan (enckequity/teamshift)

1. Add `deploy/approval-link/`: `plugin/` (verbatim files from `MANIFEST.sha256`), the manifest, this repo's tests and a README. Add drift tests: plugin vs manifest, and the Hermes pin in `upstream-context.json` still being `d923a5e`.
2. Record the bounded exception (Dakota, 2026-11-03) in `docs/native-deployment-policy.md`, citing [native-gap.md](native-gap.md), and update the approval row in `docs/custom-code-current.md`.
3. Add the framing header to `deploy/owner-web/Caddyfile` ([security-review.md](security-review.md)).
4. No front-door change is needed. The plugin texts through Hermes' `send_message` to the owner's existing front-door chat.
5. The owner workspace sets `GATEWAY_RELAY_URL` only when all its messaging moves to the front door. Until then, set `APPROVAL_LINK_TARGET` to a platform the gateway can already send to. After the move, use `relay:<chat id>`; list known targets with the native `send_message` `list` action.

Owner values: public URL `https://owner.teamshift.io/native` (`deploy/owner-web/native-dashboard.yaml`), provider `self-hosted`, empty org, user ID Dakota's Dex subject read from a verified native session (never from an email address), state directory a 0700 directory in the runtime's private home. Customers stay out until a per-member approver design exists.

Install as the README says, with `transport: builtin` first. Rollback: set `builtin`, reload; remove the plugin from `plugins.enabled`. Restart through the supervisor's drain-aware path.

## Owner phone checklist

Use only harmless flagged commands, for example removing an empty directory the test made. Record results and dates on teamshift#416; never paste phone numbers, tokens or the Dex subject.

Setup, before enabling the transport:
1. `hermes plugins validate` passes and every file matches `MANIFEST.sha256`.
2. Anonymous `GET /native/api/plugins/approval-link/requests/x` returns 401 or a login redirect, never data. Signed in as the owner, `/native/approval-link` renders "unavailable". A non-owner account gets 403 for a known request.
3. Native texting still works and native `/approve` still resolves a harmless request (the rollback baseline).

Enable `approval-link` with `transport_fallback: deny`, restart, then:
1. **Text arrives.** One flagged command produces one short text in the owner's existing chat within seconds, with a link and no command text.
2. **Link opens signed in.** Tap it. Record whether Pomerium and the Hermes sign-in complete, and in which browser. If sign-in cannot complete from Messages, stop: that is the open risk.
3. **Approve once.** The page shows the redacted command and reason. Approve once. The command runs once. A second tap does nothing.
4. **Deny.** The command does not run and the agent reports the denial.
5. **Replay.** Reopen the first link: buttons disabled. A new request cannot be answered from the old link.
6. **Concurrent.** Two requests close together each answer only their own.
7. **Expiry.** Do nothing until the timeout: the command does not run and the page shows expired.
8. **Wrong identity.** The link opened under another account shows nothing and accepts nothing.
9. **Logout and restart.** After sign-out the page asks for sign-in. Restart the gateway with a request pending: it ends denied, its old link reads expired within about 15 seconds, and a new request works.
10. **Send failure.** On a test copy, set an unreachable target: the command is denied and nothing is resent. Also confirm a brand-new Linq chat (no prior text from the owner) denies rather than hanging.
11. **Rollback.** `builtin` restores native `/approve`.

Pass: all eleven, no secret in logs or the text, one decision per request in the state database. Failure in 2, 3, 5 or 8 blocks wider use.
