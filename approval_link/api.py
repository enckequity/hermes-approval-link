"""Native dashboard routes; the host verifies sessions, then we pin the approver."""

import time
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .config import Settings
from .store import Rejected, Store


class Decision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    digest: str = Field(min_length=1, max_length=256, strict=True)
    choice: Literal['once', 'deny']


def make_router(settings=None):
    router = APIRouter()

    def authorized(request):
        try:
            config = settings or Settings.from_env()
        except ValueError:
            raise HTTPException(503, 'Approval cards are not configured.') from None
        if not getattr(request.app.state, 'auth_required', False):
            raise HTTPException(503, 'Approval cards require authenticated dashboard access.')
        session = getattr(request.state, 'session', None)
        if session is None:
            raise HTTPException(401, 'Sign in to review this request.')
        identity = tuple(getattr(session, key, None) for key in ('provider', 'user_id', 'org_id'))
        if identity != config.identity or getattr(session, 'expires_at', 0) <= time.time():
            raise HTTPException(403, 'This account cannot review this request.')
        return config, Store(config.state_dir, config.tenant, config.identity)

    def response(row):
        fields = ('id', 'digest', 'command', 'description', 'expires', 'status', 'choice')
        return JSONResponse({key: row[key] for key in fields}, headers={
            'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer',
            'X-Content-Type-Options': 'nosniff'})

    @router.get('/requests/{request_id}')
    def read(request_id: str, request: Request):
        _, store = authorized(request)
        try:
            return response(store.read(request_id))
        except Rejected:
            raise HTTPException(404, 'This approval is unavailable.') from None

    @router.post('/requests/{request_id}/decision')
    async def decide(request_id: str, request: Request):
        config, store = authorized(request)
        if (request.headers.get('origin') != config.origin
                or request.headers.get('x-approval-link') != '1'):
            raise HTTPException(403, 'Open this approval from its original workspace.')
        if request.headers.get('content-type', '').split(';')[0].strip() != 'application/json':
            raise HTTPException(415, 'Send a JSON decision.')
        raw = await request.body()
        if len(raw) > 2048:
            raise HTTPException(413, 'The decision is too large.')
        try:
            decision = Decision.model_validate_json(raw)
        except ValueError:
            raise HTTPException(422, 'Choose Approve once or Deny for this request.') from None
        try:
            store.resolve(request_id, decision.digest, decision.choice)
            return response(store.read(request_id))
        except Rejected:
            raise HTTPException(409, 'This approval is expired, answered or unavailable.') from None

    return router
