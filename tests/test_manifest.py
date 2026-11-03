"""MANIFEST.sha256 pins the installed plugin files; regenerate with scripts/make-manifest.sh."""
import hashlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ManifestTests(unittest.TestCase):
    def test_manifest_matches_every_runtime_file(self):
        listed = {}
        for line in (ROOT / 'MANIFEST.sha256').read_text().splitlines():
            digest, name = line.split(None, 1)
            listed[name.strip()] = digest
        actual = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                  [ROOT / 'plugin.yaml', ROOT / '__init__.py', ROOT / 'dashboard/manifest.json',
                   ROOT / 'dashboard/plugin_api.py', *(ROOT / 'hermes_photon_approvals').glob('*.py'),
                   *(ROOT / 'dashboard/dist').glob('*')]}
        self.assertEqual(listed, actual, 'Run scripts/make-manifest.sh and commit MANIFEST.sha256.')
