"""Return correlated human decisions; Hermes owns authorization and execution."""

import logging
import math
import time
import uuid

from .store import Store

log = logging.getLogger(__name__)


def present(request, settings, sender):
    seconds = min(float(request.timeout_seconds), 300)
    if not math.isfinite(seconds) or seconds <= 0 or not {'once','deny'} <= set(request.allowed_choices):
        return request.respond('deny')
    deadline = time.monotonic()+seconds
    store = Store(settings.state_dir, settings.tenant, settings.identity)
    store.create(request.request_id,request.digest,request.command,request.description,time.time()+seconds)
    url = settings.origin+settings.prefix+'/photon-approvals?request='+request.request_id
    client_id = str(uuid.uuid4())
    store.record_delivery(request.request_id,'intent',{'clientMessageId':client_id})
    try:
        receipt = sender.send(url,client_id,min(10,seconds))
        store.record_delivery(request.request_id,'accepted',{'clientMessageId':client_id, **receipt})
    except Exception:
        store.close(request.request_id,'send_failed')
        log.warning('Approval card delivery failed; the request was denied. Do not resend automatically.')
        return request.respond('deny')
    choice = 'deny'
    status = 'expired'
    try:
        while time.monotonic() < deadline:
            row = store.read(request.request_id)
            if row['status'] in ('once','deny'):
                choice, status = row['status'], 'recorded'
                break
            if row['status'] != 'pending':
                break
            time.sleep(min(.1,max(0,deadline-time.monotonic())))
    finally:
        store.close(request.request_id,status)
    # The live page reads canonical state even when a bubble update cannot finish in time.
    remaining = deadline-time.monotonic()
    if remaining > 2:
        try:
            sender.update(url,receipt['session'],choice if status=='recorded' else 'expired',min(10,remaining/2))
        except Exception:
            log.warning('Card preview update failed; the decision remains recorded in the workspace.')
    return request.respond(choice)
