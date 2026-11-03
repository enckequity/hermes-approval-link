# Live acceptance checklist: owner phone test

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
