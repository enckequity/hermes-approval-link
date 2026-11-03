import unittest
from approval_link.config import Settings

class ConfigTests(unittest.TestCase):
    def test_https_origin_and_fixed_dm_required(self):
        env = dict(APPROVAL_LINK_TENANT_ID='tenant-a', APPROVAL_LINK_PUBLIC_URL='https://agent.example.test',
                   APPROVAL_LINK_PROVIDER='oidc', APPROVAL_LINK_USER_ID='alice', APPROVAL_LINK_ORG_ID='org-a',
                   APPROVAL_LINK_TARGET='relay:chat-1', APPROVAL_LINK_STATE_DIR='/tmp/approval-test-state')
        self.assertEqual(Settings.from_env(env).identity, ('oidc','alice','org-a'))
        for url in ['http://agent.example.test','https://user:pass@agent.example.test','https://agent.example.test/?token=bad',
                    'https://agent.example.test/a/../b','https://agent.example.test//x','https://agent.example.test/a b','https://agent.example.test/#token', 'https://agent.example.test\\@evil.test']:
            with self.assertRaises(ValueError):
                Settings.from_env({**env, 'APPROVAL_LINK_PUBLIC_URL':url})
        for target in ['chat-1', 'relay:', 'relay:a b', ':chat', 'relay:a:b']:
            with self.assertRaises(ValueError):
                Settings.from_env({**env, 'APPROVAL_LINK_TARGET':target})

    def test_dashboard_path_prefix_is_kept_out_of_the_origin(self):
        env = dict(APPROVAL_LINK_TENANT_ID='t', APPROVAL_LINK_PUBLIC_URL='https://agent.example.test/native/',
                   APPROVAL_LINK_PROVIDER='oidc', APPROVAL_LINK_USER_ID='alice', APPROVAL_LINK_ORG_ID='',
                   APPROVAL_LINK_TARGET='relay:chat-1', APPROVAL_LINK_STATE_DIR='/tmp/approval-test-state')
        settings = Settings.from_env(env)
        self.assertEqual((settings.origin, settings.prefix), ('https://agent.example.test', '/native'))

    def test_origin_matches_what_browsers_send(self):
        env = dict(APPROVAL_LINK_TENANT_ID='t', APPROVAL_LINK_PROVIDER='oidc', APPROVAL_LINK_USER_ID='alice',
                   APPROVAL_LINK_TARGET='relay:chat-1', APPROVAL_LINK_STATE_DIR='/tmp/approval-test-state')
        for url, origin in [('HTTPS://A.Example.test:443/native', 'https://a.example.test'),
                            ('https://a.example.test:8443', 'https://a.example.test:8443')]:
            self.assertEqual(Settings.from_env({**env, 'APPROVAL_LINK_PUBLIC_URL': url}).origin, origin)
        with self.assertRaises(ValueError):
            Settings.from_env({**env, 'APPROVAL_LINK_PUBLIC_URL': 'https://a.example.test./x'})
