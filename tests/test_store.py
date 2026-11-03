import concurrent.futures
import tempfile
import time
import unittest
from pathlib import Path

from hermes_photon_approvals.store import Store, Rejected


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / "state", "tenant-a", ("oidc", "alice", "org-a"))
        self.store.create("r1", "digest-1", "echo test", "Test request", time.time() + 30)

    def test_bound_decision_survives_process_connection(self):
        self.store.resolve("r1", "digest-1", "once")
        other = Store(self.store.directory, "tenant-a", ("oidc", "alice", "org-a"))
        self.assertEqual(other.read("r1")["status"], "once")
        self.store.close("r1", "recorded")
        with self.assertRaises(Rejected):
            other.resolve("r1", "digest-1", "deny")

    def test_closing_never_overwrites_a_recorded_decision(self):
        self.store.resolve("r1", "digest-1", "once")
        self.store.close("r1", "expired")
        self.assertEqual(self.store.read("r1")["status"], "once")
        self.store.create("r2", "digest-2", "echo", "Test", time.time() + 30)
        self.store.close("r2", "recorded")
        self.assertEqual(self.store.read("r2")["status"], "pending")

    def test_wrong_tenant_identity_or_digest_cannot_read_or_decide(self):
        for tenant, identity in [("tenant-b", ("oidc", "alice", "org-a")),
                                 ("tenant-a", ("oidc", "mallory", "org-a")),
                                 ("tenant-a", ("oidc", "alice", "org-b"))]:
            other = Store(self.store.directory, tenant, identity)
            with self.assertRaises(Rejected):
                other.read("r1")
            with self.assertRaises(Rejected):
                other.resolve("r1", "digest-1", "once")
        with self.assertRaises(Rejected):
            self.store.resolve("r1", "wrong", "once")
        self.assertEqual(self.store.read("r1")["status"], "pending")

    def test_expired_denied_and_unoffered_choices(self):
        self.store.create("expired", "d", "x", "x", time.time() - 1)
        self.assertEqual(self.store.read("expired")["status"], "expired")
        for choice in ["once", "deny", "always", "session", "Approve demo", ""]:
            with self.assertRaises(Rejected):
                self.store.resolve("expired", "d", choice)
        for choice in ["always", "session", "yes"]:
            with self.assertRaises(Rejected):
                self.store.resolve("r1", "digest-1", choice)

    def test_simultaneous_decisions_have_one_winner(self):
        def decide(choice):
            try:
                self.store.resolve("r1", "digest-1", choice)
                return True
            except Rejected:
                return False
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            self.assertEqual(sum(pool.map(decide, ["once", "deny"])), 1)

    def test_old_card_cannot_decide_new_request(self):
        self.store.close("r1", "expired")
        self.store.create("r2", "digest-2", "new command", "new", time.time() + 30)
        with self.assertRaises(Rejected):
            self.store.resolve("r1", "digest-1", "once")
        with self.assertRaises(Rejected):
            self.store.resolve("r2", "digest-1", "once")
        self.assertEqual(self.store.read("r2")["status"], "pending")

    def test_private_files_and_duplicate_id(self):
        self.assertEqual(self.store.directory.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(Rejected):
            self.store.create("r1", "d2", "changed", "x", time.time() + 30)

    def test_symlink_or_shared_database_is_rejected(self):
        import os
        target = Path(self.tmp.name)/'target'
        target.mkdir(mode=0o700)
        link = Path(self.tmp.name)/'link'
        link.symlink_to(target, target_is_directory=True)
        with self.assertRaises(ValueError): Store(link,'a',('p','u',''))
        other = Path(self.tmp.name)/'other'
        other.mkdir(mode=0o700)
        (other/'approvals.sqlite3').symlink_to(self.store.path)
        with self.assertRaises(OSError): Store(other,'a',('p','u',''))
        os.chmod(self.store.path,0o644)
        try:
            with self.assertRaises(ValueError): Store(self.store.directory,'a',('p','u',''))
        finally:
            os.chmod(self.store.path,0o600)
