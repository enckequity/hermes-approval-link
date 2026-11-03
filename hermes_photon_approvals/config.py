"""Operator configuration; models and card URLs cannot select identities or recipients."""

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
    dm: str
    state_dir: Path
    prefix: str = ''  # dashboard path prefix behind a proxy, e.g. /native

    @property
    def identity(self):
        return self.provider, self.user_id, self.org_id

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        def required(name):
            value = env.get('PHOTON_APPROVAL_' + name, '').strip()
            if not value:
                raise ValueError('Configure PHOTON_APPROVAL_' + name + '.')
            return value
        public = required('PUBLIC_URL').rstrip('/')
        url = urlsplit(public)
        if (url.scheme != 'https' or not url.hostname or url.username or url.password
                or url.query or url.fragment or '\\' in public or any(c.isspace() for c in public)
                or (url.path and not re.fullmatch(r'(/(?!\.+(?:/|$))[A-Za-z0-9._~-]+)+', url.path))):
            raise ValueError('Use an HTTPS dashboard URL without credentials or query.')
        origin = url.scheme + '://' + url.netloc
        try:
            url.port
        except ValueError:
            raise ValueError('Use a valid HTTPS origin.') from None
        dm = required('DM')
        if not re.fullmatch(r'\+[1-9][0-9]{7,14}', dm):
            raise ValueError('Configure an existing E.164 direct-message recipient.')
        directory = Path(required('STATE_DIR'))
        if not directory.is_absolute():
            raise ValueError('Approval state needs an absolute private directory.')
        return cls(required('TENANT_ID'), origin, required('PROVIDER'), required('USER_ID'),
                   env.get('PHOTON_APPROVAL_ORG_ID', '').strip(), dm, directory, url.path)
