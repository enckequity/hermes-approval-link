"""Operator configuration; models and request links cannot select identities or recipients."""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    tenant: str
    origin: str
    provider: str
    user_id: str
    org_id: str
    target: str  # where to text the link, e.g. relay:<chat id>; never chosen by a model
    state_dir: Path
    prefix: str = ''  # dashboard path prefix behind a proxy, e.g. /native

    @property
    def identity(self):
        return self.provider, self.user_id, self.org_id

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        def required(name):
            value = env.get('APPROVAL_LINK_' + name, '').strip()
            if not value:
                raise ValueError('Configure APPROVAL_LINK_' + name + '.')
            return value
        public = required('PUBLIC_URL').rstrip('/')
        url = urlsplit(public)
        if (url.scheme != 'https' or not url.hostname or url.username or url.password
                or url.query or url.fragment or '\\' in public or any(c.isspace() for c in public)
                or (url.path and not re.fullmatch(r'(/(?!\.+(?:/|$))[A-Za-z0-9._~-]+)+', url.path))):
            raise ValueError('Use an HTTPS dashboard URL without credentials or query.')
        host = url.hostname
        if host.endswith('.'):
            raise ValueError('Use a valid HTTPS origin.')
        # Match what browsers send in Origin: lowercase host, default port omitted.
        origin = 'https://' + ('[' + host + ']' if ':' in host else host)
        try:
            port = url.port
        except ValueError:
            raise ValueError('Use a valid HTTPS origin.') from None
        if port and port != 443:
            origin += ':' + str(port)
        target = required('TARGET')
        if not re.fullmatch(r'[a-z][a-z0-9_-]*:[^\s:]+', target):
            raise ValueError('Configure the one existing chat to text, as platform:chat_id.')
        directory = Path(required('STATE_DIR'))
        if not directory.is_absolute():
            raise ValueError('Approval state needs an absolute private directory.')
        return cls(required('TENANT_ID'), origin, required('PROVIDER'), required('USER_ID'),
                   env.get('APPROVAL_LINK_ORG_ID', '').strip(), target, directory, url.path)
