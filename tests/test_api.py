import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from approval_link.api import make_router
from approval_link.config import Settings
from approval_link.store import Store


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings = Settings('tenant-a', 'https://agent.example.test', 'oidc', 'alice', 'org-a',
                                 'relay:chat-1', Path(self.tmp.name) / 'state')
        self.store = Store(self.settings.state_dir, self.settings.tenant, self.settings.identity)
        self.store.create('r1', 'digest-1', '<script>bad()</script>', 'Test', time.time() + 30)
        self.session = SimpleNamespace(provider='oidc', user_id='alice', org_id='org-a', expires_at=time.time()+60)
        self.app = FastAPI()
        self.app.state.auth_required = True
        @self.app.middleware('http')
        async def session(request, next_call):
            if self.session:
                request.state.session = self.session
            return await next_call(request)
        self.app.include_router(make_router(self.settings), prefix='/api/plugins/approval-link')
        self.client = TestClient(self.app)
        self.url = '/api/plugins/approval-link/requests/r1'
        self.headers = {'Origin': self.settings.origin, 'X-Approval-Link': '1'}

    def decide(self, **kw):
        return self.client.post(self.url + '/decision', json={'digest': 'digest-1', 'choice': 'once'}, **kw)

    def test_authenticated_request_and_one_decision(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('identity', response.json())
        self.assertEqual(response.json()['command'], '<script>bad()</script>')
        self.assertEqual(self.decide(headers=self.headers).status_code, 200)
        self.assertEqual(self.decide(headers=self.headers).status_code, 409)

    def test_anonymous_service_identity_wrong_org_and_expiry_fail(self):
        for session in [None, SimpleNamespace(provider='oidc', user_id='bob', org_id='org-a', expires_at=time.time()+60),
                        SimpleNamespace(provider='oidc', user_id='alice', org_id='org-b', expires_at=time.time()+60),
                        SimpleNamespace(provider='other', user_id='alice', org_id='org-a', expires_at=time.time()+60),
                        SimpleNamespace(provider='oidc', user_id='alice', org_id='org-a', expires_at=time.time()-1)]:
            self.session = session
            self.assertIn(self.client.get(self.url).status_code, (401, 403))
            self.assertIn(self.decide(headers=self.headers).status_code, (401, 403))
        self.assertEqual(self.store.read('r1')['status'], 'pending')

    def test_ungated_dashboard_is_rejected_even_with_injected_identity(self):
        self.app.state.auth_required = False
        self.assertEqual(self.client.get(self.url).status_code, 503)

    def test_csrf_origin_content_type_and_header(self):
        for headers in [{}, {'Origin': 'https://evil.example', 'X-Approval-Link': '1'},
                        {'Origin': self.settings.origin},
                        {'Origin': self.settings.origin, 'X-Approval-Link': '0'}]:
            self.assertEqual(self.decide(headers=headers).status_code, 403)
        response = self.client.post(self.url+'/decision', content='choice=once', headers={**self.headers, 'Content-Type':'text/plain'})
        self.assertEqual(response.status_code, 415)
        self.assertEqual(self.store.read('r1')['status'], 'pending')

    def test_unknown_request_bad_digest_or_choice_cannot_approve(self):
        self.assertEqual(self.client.get(self.url+'other').status_code, 404)
        for body in [{'digest':'wrong','choice':'once'}, {'digest':'digest-1','choice':'always'},
                     {'digest':'digest-1','choice':['once','deny']}]:
            self.assertIn(self.client.post(self.url+'/decision', json=body, headers=self.headers).status_code, (409,422))
        self.assertEqual(self.store.read('r1')['status'], 'pending')

    def test_bad_state_directory_mode_is_a_503(self):
        os.chmod(self.settings.state_dir, 0o755)
        self.addCleanup(os.chmod, self.settings.state_dir, 0o700)
        self.assertEqual(self.client.get(self.url).status_code, 503)

    def test_private_response_headers(self):
        response = self.client.get(self.url)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(response.headers['referrer-policy'], 'no-referrer')
