import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from pathlib import Path

from hermes_cli.approval_transport import ApprovalRequest, invoke_approval_transport
from hermes_photon_approvals.config import Settings
from hermes_photon_approvals.store import Store, Rejected
from hermes_photon_approvals.transport import present


class Sender:
    def __init__(self, callback=None, fail=False):
        self.callback, self.fail, self.calls = callback, fail, []
    def send(self, url, client_id, timeout):
        self.calls.append((url,client_id))
        if self.fail:
            raise RuntimeError('secret-that-must-not-be-logged')
        if self.callback:
            self.callback()
        return {'session': {'messageGuid':'msg-1','chatGuid':'any;-;+15555550123'}}
    def update(self, url, session, status, timeout):
        return None


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.settings = Settings('tenant-a','https://agent.example.test','oidc','alice','org-a',
                                 '+15555550123',Path(self.tmp.name)/'state')
        self.store = Store(self.settings.state_dir,self.settings.tenant,self.settings.identity)
    def request(self, timeout=2):
        return ApprovalRequest.create(command='echo test',description='Test',pattern_key='test',pattern_keys=('test',),
                                      session_key='photon:synthetic',surface='gateway',allow_session=True,
                                      allow_permanent=True,timeout_seconds=timeout)
    def test_real_host_accepts_request_bound_once_and_deny(self):
        for choice in ['once','deny']:
            req=self.request()
            sender=Sender(lambda:self.store.resolve(req.request_id,req.digest,choice))
            result=invoke_approval_transport(lambda r:present(r,self.settings,sender),req,timeout_seconds=2,poll_interval=.01)
            self.assertEqual(result.choice,choice)
            self.assertIsNone(result.failure)
            self.assertEqual(sender.calls[0][0],self.settings.origin+self.settings.prefix+'/photon-approvals?request='+req.request_id)
            self.assertNotIn(req.digest,sender.calls[0][0])
            self.assertEqual(self.store.read(req.request_id)['status'],'recorded')
    def test_timeout_or_send_failure_denies_without_retry(self):
        req=self.request(.05); sender=Sender()
        decision=present(req,self.settings,sender)
        self.assertEqual(decision.choice,'deny')
        self.assertEqual(len(sender.calls),1)
        with self.assertRaises(Rejected): self.store.resolve(req.request_id,req.digest,'once')
        req=self.request(); sender=Sender(fail=True)
        with self.assertLogs('hermes_photon_approvals.transport',level='WARNING') as logs:
            decision=present(req,self.settings,sender)
        self.assertEqual(decision.choice,'deny')
        self.assertNotIn('secret-that-must-not-be-logged',''.join(logs.output))
        self.assertEqual(len(sender.calls),1)
        self.assertEqual(self.store.read(req.request_id)['status'],'send_failed')
    def test_old_response_cannot_resume_new_request(self):
        old=self.request(.01); present(old,self.settings,Sender())
        req=self.request()
        def response():
            with self.assertRaises(Rejected): self.store.resolve(old.request_id,old.digest,'once')
            self.store.resolve(req.request_id,req.digest,'deny')
        self.assertEqual(present(req,self.settings,Sender(response)).choice,'deny')

    def test_host_interruption_denies_while_callback_finishes(self):
        req = self.request(.15)
        interrupted, finished = threading.Event(), threading.Event()
        sender = Sender(lambda: interrupted.set())
        def callback(request):
            try:
                return present(request,self.settings,sender)
            finally:
                finished.set()
        result = invoke_approval_transport(callback,req,timeout_seconds=.15,poll_interval=.005,
                                           is_interrupted=interrupted.is_set)
        self.assertEqual((result.choice,result.failure),('deny','interrupted'))
        self.assertTrue(finished.wait(1))
        with self.assertRaises(Rejected): self.store.resolve(req.request_id,req.digest,'once')

    def test_host_discards_a_late_bound_callback(self):
        req = self.request(.2)
        finished = threading.Event()
        def delayed():
            time.sleep(.06)
            self.store.resolve(req.request_id,req.digest,'once')
        def callback(request):
            try:
                return present(request,self.settings,Sender(delayed))
            finally:
                finished.set()
        result = invoke_approval_transport(callback,req,timeout_seconds=.02,poll_interval=.005)
        self.assertEqual((result.choice,result.failure),('deny','timeout'))
        self.assertTrue(finished.wait(1))
        self.assertEqual(result.choice,'deny')
        next_request = self.request()
        self.store.create(next_request.request_id,next_request.digest,'next','next',time.time()+10)
        with self.assertRaises(Rejected): self.store.resolve(next_request.request_id,req.digest,'once')

    def test_preview_update_failure_does_not_reverse_decision(self):
        req = self.request(4)
        sender = Sender(lambda:self.store.resolve(req.request_id,req.digest,'once'))
        def fail(*args): raise RuntimeError('private-provider-error')
        sender.update = fail
        with self.assertLogs('hermes_photon_approvals.transport',level='WARNING') as logs:
            result = invoke_approval_transport(lambda r:present(r,self.settings,sender),req,timeout_seconds=4,poll_interval=.01)
        self.assertEqual(result.choice,'once')
        self.assertIsNone(result.failure)
        self.assertEqual(self.store.read(req.request_id)['choice'],'once')
        self.assertNotIn('private-provider-error',''.join(logs.output))

    def test_preview_update_has_time_for_token_exchange_and_rpc(self):
        for timeout, expected in [(30, 10), (8, 4)]:
            with self.subTest(timeout=timeout):
                req = self.request(timeout)
                sender = Sender(lambda:self.store.resolve(req.request_id,req.digest,'once'))
                budgets = []
                sender.update = lambda url, session, status, budget: budgets.append(budget)
                with patch(
                        'hermes_photon_approvals.transport.time.monotonic', return_value=100):
                    decision = present(req,self.settings,sender)
                self.assertEqual(decision.choice,'once')
                self.assertEqual(budgets,[expected])
