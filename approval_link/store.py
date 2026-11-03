"""Private, request-bound state shared by the gateway and dashboard processes."""

import json
import os
import re
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path


# A waiter touches its row; a pending row nobody is waiting on (gateway restart) stops being answerable.
STALE = 15


class Rejected(ValueError):
    """The request is missing, expired, already answered or not authorized."""


class Store:
    def __init__(self, directory, tenant, identity):
        self.directory = Path(directory)
        self.tenant, self.identity = tenant, tuple(identity)
        if not tenant or len(self.identity) != 3 or not all(self.identity[:2]):
            raise ValueError("Configure the tenant and approver identity.")
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = self.directory.lstat()
        if self.directory.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("Approval state needs a private directory owned by this user.")
        self.path = self.directory / "approvals.sqlite3"
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            if info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ValueError("Approval state needs a private database owned by this user.")
        finally:
            os.close(fd)
        with self.connection() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS requests (
                id TEXT PRIMARY KEY, digest TEXT NOT NULL, tenant TEXT NOT NULL,
                identity TEXT NOT NULL, command TEXT NOT NULL, description TEXT NOT NULL,
                expires REAL NOT NULL, status TEXT NOT NULL, choice TEXT, beat REAL NOT NULL)""")

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def _scope(self):
        return self.tenant, json.dumps(self.identity)

    def create(self, request_id, digest, command, description, expires):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id) or not digest:
            raise Rejected("Invalid request identifier.")
        try:
            with self.connection() as db:
                db.execute("INSERT INTO requests VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', NULL, ?)",
                           (request_id, digest, *self._scope(), command, description, expires, time.time()))
        except sqlite3.IntegrityError:
            raise Rejected("This request already exists.") from None

    def read(self, request_id):
        with self.connection() as db:
            row = db.execute("SELECT * FROM requests WHERE id=? AND tenant=? AND identity=?",
                             (request_id, *self._scope())).fetchone()
        if row is None:
            raise Rejected("This approval is unavailable.")
        result = dict(row)
        if result['status'] == 'pending' and (result['expires'] <= time.time() or result['beat'] < time.time() - STALE):
            result['status'] = 'expired'
        return result

    def resolve(self, request_id, digest, choice):
        if choice not in ('once', 'deny'):
            raise Rejected("Choose Approve once or Deny.")
        with self.connection() as db:
            result = db.execute("""UPDATE requests SET status=?, choice=?
                WHERE id=? AND digest=? AND tenant=? AND identity=?
                AND status='pending' AND expires>? AND beat>?""",
                (choice, choice, request_id, digest, *self._scope(), time.time(), time.time() - STALE))
            if result.rowcount != 1:
                raise Rejected("This approval is expired, answered or unavailable.")

    def close(self, request_id, status):
        if status not in ('recorded', 'expired', 'send_failed'):
            raise ValueError("Invalid closing state.")
        # A decision is never overwritten by expiry or failure; only a decision becomes 'recorded'.
        guard = "status IN ('once','deny')" if status == 'recorded' else "status='pending'"
        with self.connection() as db:
            db.execute("UPDATE requests SET status=? WHERE id=? AND tenant=? AND identity=? AND " + guard,
                       (status, request_id, *self._scope()))

    def touch(self, request_id):
        with self.connection() as db:
            db.execute("UPDATE requests SET beat=? WHERE id=? AND status='pending'", (time.time(), request_id))
