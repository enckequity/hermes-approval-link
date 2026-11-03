"""Spectrum shared-line cards using grpcurl and Photon’s official proto schemas."""

import base64
import json
import os
import subprocess
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PhotonSender:
    def __init__(self, project_id, secret, dm, grpcurl, proto_dir):
        self.project_id, self.secret = project_id, secret
        self.chat = 'any;-;' + dm
        self.grpcurl, self.proto_dir = str(grpcurl), str(proto_dir)

    @classmethod
    def from_env(cls, dm):
        project = os.environ.get('PHOTON_PROJECT_ID', '')
        secret = os.environ.get('PHOTON_PROJECT_SECRET', '')
        if not project or not secret:
            raise ValueError('Configure the existing Spectrum project credentials.')
        grpcurl = Path(os.environ.get('PHOTON_APPROVAL_GRPCURL', str(Path.home()/'.local/bin/grpcurl')))
        protos = Path(os.environ.get('PHOTON_APPROVAL_PROTO_DIR', str(Path.home()/'.local/share/photon/advanced-imessage/2.3.0/proto')))
        if not grpcurl.is_absolute() or not grpcurl.is_file() or not protos.is_dir():
            raise ValueError('Install the pinned grpcurl and official proto schemas first.')
        return cls(project, secret, dm, grpcurl, protos)

    def _token(self, timeout):
        auth = base64.b64encode((self.project_id+':'+self.secret).encode()).decode()
        request = Request('https://spectrum.photon.codes/projects/'+quote(self.project_id, safe='')+'/imessage/tokens',
                          data=b'', headers={'Authorization':'Basic '+auth,
                                             'User-Agent':'HermesPhotonApprovals/0.1.3'}, method='POST')
        try:
            with build_opener(NoRedirect).open(request, timeout=timeout) as response:
                payload = json.loads(response.read(1024*1024))
            data = payload.get('data', {})
            if payload.get('succeed') is not True or data.get('type') != 'shared' or not data.get('token'):
                raise ValueError('Unsupported token response')
            return data['token']
        except Exception:
            raise RuntimeError('Photon token exchange failed or this line type is unsupported.') from None

    def _rpc(self, token, service, method, body, timeout):
        args = [self.grpcurl, '-max-time', str(max(.001, timeout)), '-expand-headers',
                '-H', 'authorization: Bearer ${PHOTON_ACCESS_TOKEN}',
                '-import-path', self.proto_dir, '-proto', 'photon/imessage/v1/'+service+'_service.proto',
                '-d', '@', 'imessage.spectrum.photon.codes:443',
                'photon.imessage.v1.'+service.title()+'Service/'+method]
        try:
            result = subprocess.run(args, input=json.dumps(body), text=True, capture_output=True,
                                    env={'PHOTON_ACCESS_TOKEN':token}, timeout=max(.001,timeout), check=False)
            if result.returncode or len(result.stdout) > 1024*1024:
                raise ValueError('Unsuccessful RPC')
            return json.loads(result.stdout)
        except Exception:
            raise RuntimeError('Photon request failed; delivery may be uncertain.') from None

    @staticmethod
    def _card(url, caption):
        return dict(teamId='P8XT6232SL', extensionBundleId='codes.photon.Spectrum.MessagesExtension',
                    appName='Spectrum', appStoreId='6777616651', url=url, live=True,
                    layout={'caption':caption, 'subcaption':'Open your workspace to review.',
                            'summary':caption})

    def send(self, url, client_id, timeout):
        deadline = time.monotonic()+timeout
        token = self._token(timeout)
        chat = self._rpc(token, 'chat', 'GetChat', {'chatGuid':self.chat}, deadline-time.monotonic())
        if chat.get('chat',{}).get('guid') != self.chat:
            raise RuntimeError('The existing direct-message target did not match.')
        result = self._rpc(token, 'message', 'SendCustomizedMiniAppMessage',
                           {**self._card(url,'Review a command'), 'chatGuid':self.chat,
                            'clientMessageId':client_id}, deadline-time.monotonic())
        session = result.get('miniAppCardSession', {})
        if (session.get('chatGuid') != self.chat
                or not all(session.get(k) for k in ('sessionId','targetMessageGuid','messageGuid'))):
            raise RuntimeError('Photon accepted no usable card receipt; do not resend automatically.')
        return {'session':session}

    def update(self, url, session, status, timeout):
        if session.get('chatGuid') != self.chat:
            raise RuntimeError('The original card target did not match.')
        deadline = time.monotonic()+timeout
        token = self._token(timeout)
        caption = {'once':'Approval recorded', 'deny':'Request denied', 'expired':'Request expired'}[status]
        return self._rpc(token,'message','UpdateCustomizedMiniAppMessage',
                         {**self._card(url,caption), 'session':session}, deadline-time.monotonic())
