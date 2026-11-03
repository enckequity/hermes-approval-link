import json
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from hermes_photon_approvals.photon import PhotonSender

class PhotonTests(unittest.TestCase):
    def sender(self):
        return PhotonSender('project-id','project-secret','+15555550123','/installed/grpcurl','/official/proto')
    def test_token_exchange_identifies_the_connector(self):
        with patch('hermes_photon_approvals.photon.build_opener') as build:
            response=build.return_value.open.return_value.__enter__.return_value
            response.read.return_value=b'{"succeed":true,"data":{"type":"shared","token":"synthetic-token"}}'
            self.assertEqual(self.sender()._token(3),'synthetic-token')
            request=build.return_value.open.call_args.args[0]
            self.assertEqual(request.get_header('User-agent'),'HermesPhotonApprovals/0.1.3')
    def test_fixed_existing_dm_and_no_secret_argv(self):
        sender=self.sender(); calls=[]
        def run(args,**kwargs):
            calls.append((args,kwargs))
            body=json.loads(kwargs['input'])
            if args[-1].endswith('/GetChat'):
                self.assertEqual(body,{'chatGuid':'any;-;+15555550123'})
                return SimpleNamespace(returncode=0,stdout=json.dumps({'chat':{'guid':'any;-;+15555550123'}}))
            self.assertEqual(body['chatGuid'],'any;-;+15555550123')
            self.assertTrue(body['live'])
            return SimpleNamespace(returncode=0,stdout=json.dumps({'miniAppCardSession':{'messageGuid':'msg','chatGuid':'any;-;+15555550123','sessionId':'s','targetMessageGuid':'msg'}}))
        with patch.object(sender,'_token',return_value='access-secret'), patch('subprocess.run',side_effect=run):
            result=sender.send('https://agent.example.test/photon-approvals?request=r1','uuid',3)
        self.assertEqual(len(calls),2)
        self.assertEqual(result['session']['messageGuid'],'msg')
        for args,kwargs in calls:
            self.assertNotIn('access-secret',' '.join(args))
            self.assertNotIn('project-secret',' '.join(args))
            self.assertEqual(kwargs['env']['PHOTON_ACCESS_TOKEN'],'access-secret')
    def test_wrong_chat_or_ambiguous_failure_never_retries(self):
        sender=self.sender()
        with patch.object(sender,'_token',return_value='secret'), patch('subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='{"chat":{"guid":"group-chat"}}')) as run:
            with self.assertRaises(RuntimeError): sender.send('https://agent.example.test','uuid',3)
            self.assertEqual(run.call_count,1)
        with patch.object(sender,'_token',return_value='secret'), patch('subprocess.run',side_effect=TimeoutError('secret')) as run:
            with self.assertRaisesRegex(RuntimeError,'Photon request failed'): sender.send('https://agent.example.test','uuid',3)
            self.assertEqual(run.call_count,1)
