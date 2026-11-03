"""Return correlated human decisions; Hermes owns authorization and execution."""

import json
import logging
import math
import time

from .store import Store

log = logging.getLogger(__name__)


def send_text(target, text):
    """Text the link through Hermes' own send path, so relay egress rules and the live adapter apply."""
    from tools.send_message_tool import send_message_tool
    result = json.loads(send_message_tool({'action': 'send', 'target': target, 'message': text}))
    if not result.get('success'):
        raise RuntimeError('The approval text was not sent.')


def present(request, settings, send=send_text):
    seconds = min(float(request.timeout_seconds), 300)
    if not math.isfinite(seconds) or seconds <= 0 or not {'once','deny'} <= set(request.allowed_choices):
        return request.respond('deny')
    expires = time.time()+seconds  # taken before the deadline so no answer is accepted after the final read
    deadline = time.monotonic()+seconds
    store = Store(settings.state_dir, settings.tenant, settings.identity)
    store.create(request.request_id,request.digest,request.command,request.description,expires)
    url = settings.origin+settings.prefix+'/approval-link?request='+request.request_id
    text = ('Hermes needs your OK to run a command. Review it and approve once or deny: '
            + url + ' (expires in ' + str(int(seconds//60) or 1) + ' min)')
    try:
        send(settings.target, text)  # never retried: an uncertain send is a denial
    except Exception:
        store.close(request.request_id,'send_failed')
        log.warning('Approval text delivery failed; the request was denied. Do not resend automatically.')
        return request.respond('deny')
    choice, status = 'deny', 'expired'
    try:
        while True:
            row = store.read(request.request_id)
            if row['status'] in ('once','deny'):
                choice, status = row['status'], 'recorded'
                break
            if row['status'] != 'pending' or time.monotonic() >= deadline:
                break
            store.touch(request.request_id)
            time.sleep(min(.25,max(0,deadline-time.monotonic())))
    finally:
        store.close(request.request_id,status)
    return request.respond(choice)
