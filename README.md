# Hermes approval links

When Hermes needs approval for a command, this plugin texts the owner one short message with a link bound to that request. The link opens the Hermes dashboard, where the owner taps Approve once or Deny. The guarantees (binding, replay, expiry, identity, CSRF) are in [docs/security-review.md](docs/security-review.md).

It sends through Hermes' own `send_message` path, so it works wherever the gateway can already text the owner, including a workspace on the Linq iMessage front door (`GATEWAY_RELAY_URL`). It has no messaging provider code of its own.

Why this is needed on top of native approvals: [docs/native-gap.md](docs/native-gap.md). The phone test: [docs/live-acceptance.md](docs/live-acceptance.md). Status: offline-tested against Hermes v0.22.2; the live phone flow is not yet proven.

## Install

Copy the files listed in `MANIFEST.sha256` into `$HERMES_HOME/plugins/approval-link`, check them with `shasum -a 256 -c MANIFEST.sha256` (`sha256sum -c` on Linux), and run `hermes plugins validate` on the directory. No `pip install`. Set these for both the gateway and the dashboard:

| Variable | Meaning |
| --- | --- |
| `APPROVAL_LINK_TENANT_ID` | fixed label for this runtime |
| `APPROVAL_LINK_PUBLIC_URL` | HTTPS URL of the authenticated dashboard, path prefix allowed (for example `https://hermes.example.com/native`) |
| `APPROVAL_LINK_PROVIDER`, `APPROVAL_LINK_USER_ID`, `APPROVAL_LINK_ORG_ID` | the one verified dashboard identity who may answer; org may be empty only if the provider has none |
| `APPROVAL_LINK_TARGET` | the one chat to text, as `platform:chat_id` (for example `relay:<chat id>`); never model-chosen |
| `APPROVAL_LINK_STATE_DIR` | absolute private directory (0700) shared by gateway and dashboard |

Then enable it, switching the transport only after the checks in the acceptance doc pass:

```yaml
plugins:
  enabled: [approval-link]   # keep your other entries
security:
  approval:
    transport: approval-link
    transport_fallback: deny
```

Set `transport: builtin` to go back to stock approvals at any time.

## Test

```sh
scripts/test-offline.sh
```

Clones Hermes v0.22.2 (checked against commit `d923a5eb487a17c0a68801bba9ef0f56c81040a8`) into `.work/`, builds a Python 3.14 virtualenv and runs the Python and Node suites. Needs `git`, `uv` and `node`. No message is sent. After changing a runtime file, regenerate the manifest: `ls plugin.yaml __init__.py approval_link/*.py dashboard/manifest.json dashboard/plugin_api.py dashboard/dist/* | LC_ALL=C sort | xargs shasum -a 256 > MANIFEST.sha256`.

MIT licensed. Maintained independently of Nous Research.
