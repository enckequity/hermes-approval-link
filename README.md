# Hermes Photon approval cards

When Hermes needs approval for a command, this plugin sends one card to the owner's existing Messages DM. Opening it loads the Hermes dashboard (existing login) where the owner taps Approve once or Deny. The decision is bound to that exact request, accepted once, and Hermes still validates it (request ID, digest, scope, timeout). Failure, expiry or a missing identity always denies. Hermes source is unchanged.

Why this is needed on top of native approvals: [docs/native-gap.md](docs/native-gap.md). Decision-path review: [docs/security-review.md](docs/security-review.md). Status: offline-tested against Hermes v0.22.2; live phone approval not yet proven.

## Install

Copy the files listed in `MANIFEST.sha256` to `$HERMES_HOME/plugins/photon-approvals`, check them with `shasum -a 256 -c MANIFEST.sha256`, run `hermes plugins validate` on the directory, then configure and enable it. No `pip install` is needed. Needs grpcurl 1.9.4 and the official `@photon-ai/advanced-imessage` 2.3.0 proto schemas on the runtime. Configuration, TeamShift bundle layout, rollback and the owner phone checklist are in [docs/install.md](docs/install.md).

## Test

```sh
scripts/test-offline.sh
```

Clones Hermes v0.22.2 (verified against commit `d923a5eb487a17c0a68801bba9ef0f56c81040a8`) into `.work/`, builds a Python 3.14 virtualenv, and runs the Python and Node suites. Needs `git`, `uv` and `node`. No message is sent and no provider is called. Set `PHOTON_APPROVAL_GRPCURL` and `PHOTON_APPROVAL_PROTO_DIR` to also run the official proto-schema test. After changing a runtime file, regenerate the manifest: `ls plugin.yaml __init__.py hermes_photon_approvals/*.py dashboard/manifest.json dashboard/plugin_api.py dashboard/dist/* | LC_ALL=C sort | xargs shasum -a 256 > MANIFEST.sha256`.

MIT licensed. Maintained independently of Nous Research and Photon.
