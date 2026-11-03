import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from pathlib import Path

from hermes_cli.approval_transport import ApprovalRequest, invoke_approval_transport
from approval_link.config import Settings
from approval_link.store import Store, Rejected
from approval_link.transport import present


class Sender:
    def __init__(self, callback=None, fail=False):
        self.callback, self.fail, self.calls = callback, fail, []
    def __call__(self, target, text):
        self.calls.append((target,text))
        if self.fail:
            raise RuntimeError('secret-that-must-not-be-logged')
        if self.callback:
            self.callback()


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.settings = Settings('tenant-a','https://agent.example.test','oidc','alice','org-a',
                                 'relay:chat-1',Path(self.tmp.name)/'state')
        self.store = Store(self.settings.state_dir,self.settings.tenant,self.settings.identity)
    def request(self, timeout=2):
        return ApprovalRequest.create(command='echo test',description='Test',pattern_key='test',pattern_keys=('test',),
                                      session_key='test:synthetic',surface='gateway',allow_session=True,
                                      allow_permanent=True,timeout_seconds=timeout)
    def test_real_host_accepts_request_bound_once_and_deny(self):
        for choice in ['once','deny']:
            req=self.request()
            sender=Sender(lambda:self.store.resolve(req.request_id,req.digest,choice))
            result=invoke_approval_transport(lambda r:present(r,self.settings,sender),req,timeout_seconds=2,poll_interval=.01)
            self.assertEqual(result.choice,choice)
            self.assertIsNone(result.failure)
            target,text=sender.calls[0]
            self.assertEqual(target,'relay:chat-1')
            self.assertIn(self.settings.origin+'/approval-link?request='+req.request_id+' ',text)
            self.assertNotIn(req.digest,text)
            self.assertNotIn('echo test',text)
            self.assertEqual(self.store.read(req.request_id)['status'],'recorded')
    def test_timeout_or_send_failure_denies_without_retry(self):
        req=self.request(.05); sender=Sender()
        decision=present(req,self.settings,sender)
        self.assertEqual(decision.choice,'deny')
        self.assertEqual(len(sender.calls),1)
        with self.assertRaises(Rejected): self.store.resolve(req.request_id,req.digest,'once')
        req=self.request(); sender=Sender(fail=True)
        with self.assertLogs('approval_link.transport',level='WARNING') as logs:
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

    def test_slow_send_does_not_abandon_the_request(self):
        req=self.request(3)
        sender=Sender(lambda:time.sleep(.8))
        out=[]
        thread=threading.Thread(target=lambda:out.append(present(req,self.settings,sender)))
        with patch('approval_link.store.STALE',.6):
            thread.start(); time.sleep(1)
            self.store.resolve(req.request_id,req.digest,'once')
            thread.join(3)
        self.assertEqual(out[0].choice,'once')

    def test_plugin_gives_up_before_the_host_deadline(self):
        req=self.request(2); start=time.monotonic()
        self.assertEqual(present(req,self.settings,Sender()).choice,'deny')
        self.assertLess(time.monotonic()-start,1.3)
        with self.assertRaises(Rejected): self.store.resolve(req.request_id,req.digest,'once')

    def test_pending_row_nobody_is_waiting_on_cannot_be_answered(self):
        self.store.create('orphan','d','echo','x',time.time()+60)
        with patch('approval_link.store.time.time', return_value=time.time()+30):
            self.assertEqual(self.store.read('orphan')['status'],'expired')
            with self.assertRaises(Rejected): self.store.resolve('orphan','d','once')

    def test_send_text_goes_through_hermes_send_message(self):
        from approval_link.transport import send_text
        with patch('tools.send_message_tool.send_message_tool', return_value='{"success": true}') as tool:
            send_text('relay:chat-1','hi')
        tool.assert_called_once_with({'action':'send','target':'relay:chat-1','message':'hi'})
        for reply in ['{"error": "no"}', '{"success": true, "skipped": true}']:
            with patch('tools.send_message_tool.send_message_tool', return_value=reply):
                with self.assertRaises(RuntimeError): send_text('relay:chat-1','hi')
