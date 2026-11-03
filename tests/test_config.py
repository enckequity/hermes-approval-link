import unittest
from hermes_photon_approvals.config import Settings

class ConfigTests(unittest.TestCase):
    def test_https_origin_and_fixed_dm_required(self):
        env = dict(PHOTON_APPROVAL_TENANT_ID='tenant-a', PHOTON_APPROVAL_PUBLIC_URL='https://agent.example.test',
                   PHOTON_APPROVAL_PROVIDER='oidc', PHOTON_APPROVAL_USER_ID='alice', PHOTON_APPROVAL_ORG_ID='org-a',
                   PHOTON_APPROVAL_DM='+15555550123', PHOTON_APPROVAL_STATE_DIR='/tmp/approval-test-state')
        self.assertEqual(Settings.from_env(env).identity, ('oidc','alice','org-a'))
        for url in ['http://agent.example.test','https://user:pass@agent.example.test','https://agent.example.test/?token=bad',
                    'https://agent.example.test/a/../b','https://agent.example.test//x','https://agent.example.test/a b','https://agent.example.test/#token', 'https://agent.example.test\\@evil.test']:
            with self.assertRaises(ValueError):
                Settings.from_env({**env, 'PHOTON_APPROVAL_PUBLIC_URL':url})
        for dm in ['group:abc', 'any;-;group', '+1', 'https://evil.test']:
            with self.assertRaises(ValueError):
                Settings.from_env({**env, 'PHOTON_APPROVAL_DM':dm})

    def test_dashboard_path_prefix_is_kept_out_of_the_origin(self):
        env = dict(PHOTON_APPROVAL_TENANT_ID='t', PHOTON_APPROVAL_PUBLIC_URL='https://agent.example.test/native/',
                   PHOTON_APPROVAL_PROVIDER='oidc', PHOTON_APPROVAL_USER_ID='alice', PHOTON_APPROVAL_ORG_ID='',
                   PHOTON_APPROVAL_DM='+15555550123', PHOTON_APPROVAL_STATE_DIR='/tmp/approval-test-state')
        settings = Settings.from_env(env)
        self.assertEqual((settings.origin, settings.prefix), ('https://agent.example.test', '/native'))

    def test_origin_matches_what_browsers_send(self):
        env = dict(PHOTON_APPROVAL_TENANT_ID='t', PHOTON_APPROVAL_PROVIDER='oidc', PHOTON_APPROVAL_USER_ID='alice',
                   PHOTON_APPROVAL_DM='+15555550123', PHOTON_APPROVAL_STATE_DIR='/tmp/approval-test-state')
        for url, origin in [('HTTPS://A.Example.test:443/native', 'https://a.example.test'),
                            ('https://a.example.test:8443', 'https://a.example.test:8443')]:
            self.assertEqual(Settings.from_env({**env, 'PHOTON_APPROVAL_PUBLIC_URL': url}).origin, origin)
        with self.assertRaises(ValueError):
            Settings.from_env({**env, 'PHOTON_APPROVAL_PUBLIC_URL': 'https://a.example.test./x'})
