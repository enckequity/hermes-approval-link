#!/bin/sh
# Regenerate MANIFEST.sha256: the exact files that make up the installed plugin.
set -eu
cd "$(dirname "$0")/.."
{ ls plugin.yaml __init__.py hermes_photon_approvals/*.py dashboard/manifest.json dashboard/plugin_api.py dashboard/dist/*; } \
  | LC_ALL=C sort | xargs shasum -a 256 > MANIFEST.sha256
