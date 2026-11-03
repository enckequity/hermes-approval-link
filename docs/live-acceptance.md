# Live acceptance

Not run. Nothing is live. Install and rollback steps are in the [README](../README.md).

## Phone checklist


Use only harmless flagged commands, for example removing an empty directory the test made. Record results and dates somewhere private; never paste phone numbers, tokens or the approver's user ID.

Setup, before enabling the transport:
1. `hermes plugins validate` passes and every file matches `MANIFEST.sha256`.
2. Anonymous `GET <dashboard URL>/api/plugins/approval-link/requests/x` returns 401 or a login redirect, never data. Signed in as the owner, `<dashboard URL>/approval-link` renders "unavailable". A non-owner account gets 403 for a known request.
3. Native texting still works and native `/approve` still resolves a harmless request (the rollback baseline).

Enable `approval-link` with `transport_fallback: deny`, restart, then:
1. **Text arrives.** One flagged command produces one short text in the owner's existing chat within seconds, with a link and no command text.
2. **Link opens signed in.** Tap it. Record whether any proxy login and the Hermes sign-in complete, and in which browser. If sign-in cannot complete from Messages, stop: that is the open risk.
3. **Approve once.** The page shows the redacted command and reason. Approve once. The command runs once. A second tap does nothing.
4. **Deny.** The command does not run and the agent reports the denial.
5. **Replay.** Reopen the first link: buttons disabled. A new request cannot be answered from the old link.
6. **Concurrent.** Two requests close together each answer only their own.
7. **Expiry.** Do nothing until the timeout: the command does not run and the page shows expired.
8. **Wrong identity.** The link opened under another account shows nothing and accepts nothing.
9. **Logout and restart.** After sign-out the page asks for sign-in. Restart the gateway with a request pending: it ends denied, its old link reads expired within about 15 seconds, and a new request works.
10. **Send failure.** On a test copy, set an unreachable target: the command is denied and nothing is resent. Also confirm a brand-new chat where the provider bars links in a first message (Linq does; no prior text from the owner) denies rather than hanging.
11. **Rollback.** `builtin` restores native `/approve`.

Pass: all eleven, no secret in logs or the text, one decision per request in the state database. Failure in 2, 3, 5 or 8 blocks wider use.
