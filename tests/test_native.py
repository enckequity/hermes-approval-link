"""Run inside a supported Hermes environment, without starting a service."""
import hashlib
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

from hermes_cli.plugin_validate import validate_plugin_dir
from hermes_cli.plugins import PluginManager
from hermes_constants import set_hermes_home_override, reset_hermes_home_override

ROOT = Path(__file__).resolve().parents[1]

def copy_runtime(target):
    """Copy only the shipped files (MANIFEST.sha256), as an install would."""
    for line in (ROOT/'MANIFEST.sha256').read_text().splitlines():
        name = line.split(None, 1)[1].strip()
        (target/name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/name, target/name)


class NativeTests(unittest.TestCase):
    def test_native_manifest_validator_and_real_manager_registration(self):
        with tempfile.TemporaryDirectory() as home:
            plugins = Path(home)/'plugins'
            copy_runtime(plugins/'photon-approvals')
            report = validate_plugin_dir(str(plugins/'photon-approvals'))
            self.assertTrue(report.ok, report.failures)
            (Path(home)/'config.yaml').write_text('plugins:\n  enabled: [photon-approvals]\n  isolation: in_process\n')
            manager = PluginManager(scope_key=home)
            try:
                manager.discover_and_load()
                token = set_hermes_home_override(home)
                try:
                    entry = manager.get_approval_transport('photon-cards')
                finally:
                    reset_hermes_home_override(token)
                self.assertIsNone(manager.get_approval_transport('photon-cards'))
                self.assertIsNotNone(entry, {k: {"error": v.error, "enabled": v.enabled} for k,v in manager._plugins.items() if k == "photon-approvals"})
                self.assertEqual(entry.plugin_id,'photon-approvals')
                self.assertEqual(entry.profile_home,str(Path(home).resolve()))
            finally:
                manager.unload()

    def test_dashboard_backend_exports_native_router(self):
        spec=importlib.util.spec_from_file_location('approval_dashboard_test',ROOT/'dashboard/plugin_api.py')
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        paths={route.path for route in module.router.routes}
        self.assertEqual(paths,{'/requests/{request_id}','/requests/{request_id}/decision'})

    def test_native_dashboard_mount_preserves_plugin_paths(self):
        import json
        from fastapi import FastAPI
        from hermes_cli.web_server_dashboard import _dashboard_plugin_entry, _mount_plugin_api_routes
        from unittest.mock import patch
        raw=json.loads((ROOT/'dashboard/manifest.json').read_text())
        plugin=_dashboard_plugin_entry(raw,'photon-approvals',ROOT/'dashboard','user')
        app=FastAPI()
        with patch('hermes_cli.web_server.app',app), \
                patch('hermes_cli.web_server._get_dashboard_plugins',return_value=[plugin]), \
                patch('hermes_cli.plugins_cmd._get_enabled_set',return_value={'photon-approvals'}), \
                patch('hermes_cli.plugins_cmd._get_disabled_set',return_value=set()):
            _mount_plugin_api_routes()
        paths={route.path for route in app.routes}
        self.assertIn('/api/plugins/photon-approvals/requests/{request_id}',paths)
        self.assertIn('/api/plugins/photon-approvals/requests/{request_id}/decision',paths)

    def test_copied_plugin_directory_loads_without_installing_the_package(self):
        import subprocess, sys
        with tempfile.TemporaryDirectory() as home:
            target = Path(home)/'photon-approvals'
            copy_runtime(target)
            code = (
                "import importlib.util as u, sys\n"
                "def load(name, path, **kw):\n"
                "    spec = u.spec_from_file_location(name, path, **kw); m = u.module_from_spec(spec)\n"
                "    sys.modules[name] = m; spec.loader.exec_module(m); return m\n"
                f"plugin = load('copied_plugin', {str(target/'__init__.py')!r}, submodule_search_locations=[{str(target)!r}])\n"
                "names = []\n"
                "class Ctx:\n"
                "    def register_approval_transport(self, name, fn): names.append(name)\n"
                "plugin.register(Ctx())\n"
                f"api = load('copied_api', {str(target/'dashboard/plugin_api.py')!r})\n"
                "assert names == ['photon-cards'] and api.router.routes\n")
            result = subprocess.run([sys.executable, '-I', '-c', code], capture_output=True, text=True, cwd=home)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_manifest_matches_every_runtime_file(self):
        listed = {}
        for line in (ROOT / 'MANIFEST.sha256').read_text().splitlines():
            digest, name = line.split(None, 1)
            listed[name.strip()] = digest
        actual = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                  [ROOT / 'plugin.yaml', ROOT / '__init__.py', ROOT / 'dashboard/manifest.json',
                   ROOT / 'dashboard/plugin_api.py', *(ROOT / 'hermes_photon_approvals').glob('*.py'),
                   *(ROOT / 'dashboard/dist').glob('*')]}
        self.assertEqual(listed, actual, 'Regenerate MANIFEST.sha256: see the README.')
