"""Private T.* spool: no Q.* retention, immutable parts and crash-safe IO."""

import copy
import errno
import subprocess
import sys
import threading
from types import SimpleNamespace
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

from engine.tick_plane.stream_events import normalize_ws_event
from engine.tick_plane.private_spool import (
    PrivateSpoolBusy, PrivateSpoolRefusal, SpoolLimits, write_private_trade_part,
)

T=1_791_417_600_000
SESSION="2026-10-08:RTH"


def event(ev="T", **kw):
    d = ({"ev":"T","sym":"SPY","t":T,"q":2,"i":"print-12","x":11,
          "s":100,"p":100.5,"c":[0]}
         if ev=="T" else
         {"ev":"Q","sym":"SPY","t":T,"q":1,"bx":1,"bp":100.1,
          "bs":50,"ax":2,"ap":100.2,"as":60})
    d.update(kw)
    return normalize_ws_event(
        json.dumps([d]).encode(),event_index=0,
        frame_received_ns=T*1_000_000+1_000_000,
        source_receipt_id="original-frame-owner",
        session=SESSION,allowed_symbols={"SPY"})


class SpoolTests(unittest.TestCase):
    def setUp(self):
        self.td=tempfile.TemporaryDirectory()
        self.path=Path(self.td.name)
        self.addCleanup(self.td.cleanup)

    def commit(self, events=None, **kw):
        return write_private_trade_part(
            root=self.path,session=SESSION,ticker="SPY",
            events=[event()] if events is None else events, **kw)

    def test_creates_durable_byte_identical_private_part(self):
        a=self.commit()
        p=Path(a["path_private_only"])
        self.assertTrue(p.is_file())
        self.assertEqual(stat.S_IMODE(p.stat().st_mode),0o600)
        self.assertEqual(stat.S_IMODE(p.parent.stat().st_mode),0o700)
        self.assertEqual(a["state"],"PART_CREATED")
        self.assertEqual(a["n"],1)
        raw=json.loads(p.read_text().strip())
        self.assertEqual(raw["correction_status"],"STREAM_PROVISIONAL_UNRECONCILED")
        self.assertEqual(raw["trade_id"],"print-12")

    def test_deterministic_idempotence_with_same_content(self):
        first=self.commit()
        repeat=self.commit()
        self.assertEqual(first["sha256"],repeat["sha256"])
        self.assertEqual(repeat["state"],"ALREADY_PRESENT")

    def test_duplicate_identical_trade_is_deduped(self):
        r=event()
        self.assertEqual(self.commit(events=[r,copy.deepcopy(r)])["n"],1)

    def test_same_native_identity_with_different_payload_rejected(self):
        r=event()
        altered=copy.deepcopy(r)
        altered["price"]="100.6"
        with self.assertRaisesRegex(PrivateSpoolRefusal,"conflicting duplicate"):
            self.commit(events=[r,altered])

    def test_two_distinct_trade_receipts_are_sorted_deterministically(self):
        a=event()
        b=event(i="print-13",q=4,t=T+1)
        one=self.commit(events=[b,a])
        two=self.commit(events=[a,b])
        self.assertEqual(one["sha256"],two["sha256"])
        self.assertEqual(two["state"],"ALREADY_PRESENT")

    def test_quote_payload_cannot_enter_durable_store(self):
        with self.assertRaisesRegex(PrivateSpoolRefusal,"unrecognized or extra source fields"):
            self.commit(events=[event(ev="Q")])

    def test_extra_fields_are_rejected_before_credentials_leak(self):
        r=event()
        r["API_KEY"]="secret-never-write"
        with self.assertRaisesRegex(PrivateSpoolRefusal,"extra source"):
            self.commit(events=[r])
        self.assertEqual(list(self.path.rglob("*.jsonl")),[])

    def test_world_readable_root_refused(self):
        os.chmod(self.path,0o755)
        with self.assertRaisesRegex(PrivateSpoolRefusal,"group/other"):
            self.commit()

    def test_event_with_wrong_symbol_is_rejected(self):
        r=event()
        r["ticker"]="QQQ"
        with self.assertRaisesRegex(PrivateSpoolRefusal,"same-session"):
            self.commit(events=[r])

    def test_future_or_impossible_receive_clock_refused(self):
        r=event()
        r["original_frame_received_ns"]=r["sip_timestamp_ns"]-1
        with self.assertRaisesRegex(PrivateSpoolRefusal,"event/receipt"):
            self.commit(events=[r])

    def test_cannot_write_as_final_vintage_in_stream_spool(self):
        r=event()
        r["correction_status"]="FINAL"
        with self.assertRaisesRegex(PrivateSpoolRefusal,"falsely finalize"):
            self.commit(events=[r])

    def test_zero_or_unbounded_event_batch_refused(self):
        with self.assertRaisesRegex(PrivateSpoolRefusal,"bounded nonempty"):
            self.commit(events=[])
        with self.assertRaisesRegex(PrivateSpoolRefusal,"bounded nonempty"):
            self.commit(events=[event()] * 2001)

    def test_non_absolute_private_root_rejected(self):
        with self.assertRaisesRegex(PrivateSpoolRefusal,"absolute private"):
            write_private_trade_part(root=Path("relative"),session=SESSION,
                                     ticker="SPY",events=[event()])

    def test_symlink_root_refused(self):
        link=self.path.parent / (self.path.name+"-link")
        link.symlink_to(self.path)
        self.addCleanup(lambda:link.unlink(missing_ok=True))
        with self.assertRaisesRegex(PrivateSpoolRefusal,"absolute private"):
            write_private_trade_part(root=link,session=SESSION,ticker="SPY",
                                     events=[event()])

    def test_source_span_never_returns_public_url(self):
        a=self.commit()
        self.assertNotIn("url",a)
        self.assertNotIn("raw_quote",str(a))


    def test_immutable_file_collision_can_never_be_overwritten(self):
        def rival_created_target(src, dest, **kwargs):
            target = self.path / "2026-10-08" / "RTH" / "SPY" / dest
            target.write_bytes(b"rival-conflicting-part")
            target.chmod(0o600)
            raise FileExistsError()
        with patch("engine.tick_plane.private_spool.os.link",
                   side_effect=rival_created_target):
            with self.assertRaisesRegex(PrivateSpoolRefusal,
                                        "immutable part collision"):
                self.commit()
        targets=list(self.path.rglob("*.jsonl"))
        self.assertEqual(len(targets),1)
        self.assertEqual(targets[0].read_bytes(),b"rival-conflicting-part")
        self.assertEqual(list(self.path.rglob(".pending-*")),[])

    def test_file_collision_with_identical_content_is_idempotent(self):
        def rival_created_same_target(src,dest, **kwargs):
            output = self.path / "2026-10-08" / "RTH" / "SPY"
            target = output / dest
            target.write_bytes((output / src).read_bytes())
            target.chmod(0o600)
            raise FileExistsError()
        with patch("engine.tick_plane.private_spool.os.link",
                   side_effect=rival_created_same_target):
            result=self.commit()
        self.assertEqual(result["state"],"ALREADY_PRESENT")
        self.assertEqual(list(self.path.rglob(".pending-*")),[])

    def test_concurrent_same_digest_is_one_immutable_part(self):
        def attempt(_):
            try:
                return self.commit()
            except PrivateSpoolBusy as exc:
                return exc
        with ThreadPoolExecutor(max_workers=6) as pool:
            receipts = list(pool.map(attempt, range(6)))
        successful = [r for r in receipts if isinstance(r, dict)]
        self.assertEqual([r["state"] for r in successful].count("PART_CREATED"), 1)
        self.assertEqual(len(list(self.path.rglob("*.jsonl"))), 1)
        self.assertEqual(self.commit()["state"], "ALREADY_PRESENT")
        self.assertEqual(list(self.path.rglob(".pending-*")), [])

    def limits(self, **changes):
        policy = dict(max_stored_bytes=1024*1024, max_parts=10,
                      min_free_bytes=1, max_inventory_entries=64)
        policy.update(changes)
        return SpoolLimits(**policy)

    def payload_bytes(self, record=None):
        return len((json.dumps(record or event(), sort_keys=True,
                               separators=(",", ":"), ensure_ascii=True) + "\n").encode())

    def pending(self, size=0):
        output = self.path / "2026-10-08" / "RTH" / "SPY"
        for directory in (output.parent.parent, output.parent, output):
            directory.mkdir(exist_ok=True, mode=0o700)
        path = output / ".pending-abcdefgh"
        path.write_bytes(b"x" * size)
        path.chmod(0o600)
        return path

    def test_policy_requires_finite_positive_integers_before_effects(self):
        for name in ("max_stored_bytes", "max_parts", "min_free_bytes",
                     "max_inventory_entries"):
            for bad in (0, -1, True, 1.5, float("inf"), float("nan"), None):
                with self.subTest(name=name, bad=bad):
                    with self.assertRaises(PrivateSpoolRefusal):
                        self.limits(**{name: bad})
        with self.assertRaises(PrivateSpoolRefusal):
            self.commit(limits=None)
        self.assertEqual(list(self.path.iterdir()), [])

    def test_total_byte_ceiling_and_retry_at_full_capacity(self):
        size = self.payload_bytes()
        policy = self.limits(max_stored_bytes=size, max_parts=1)
        first = self.commit(limits=policy)
        inode = Path(first["path_private_only"]).stat().st_ino
        with self.assertRaisesRegex(PrivateSpoolRefusal, "stored-byte"):
            self.commit(events=[event(i="print-13")], limits=policy)
        with patch("engine.tick_plane.private_spool.os.fstatvfs",
                   side_effect=AssertionError("idempotence allocates no disk")):
            retry = self.commit(limits=policy)
        self.assertEqual(retry["state"], "ALREADY_PRESENT")
        self.assertEqual(Path(retry["path_private_only"]).stat().st_ino, inode)

    def test_part_ceiling_is_root_wide_across_partitions(self):
        policy = self.limits(max_parts=1)
        self.commit(limits=policy)
        other = event()
        other["session"] = "2026-10-09:RTH"
        with self.assertRaisesRegex(PrivateSpoolRefusal, "part-count"):
            write_private_trade_part(root=self.path, session=other["session"],
                                     ticker="SPY", events=[other], limits=policy)
        self.assertFalse((self.path / "2026-10-09").exists())

    def test_orphan_pending_bytes_and_slots_are_charged_never_pruned(self):
        pending = self.pending(23)
        for policy, reason in (
            (self.limits(max_stored_bytes=self.payload_bytes()+22), "stored-byte"),
            (self.limits(max_parts=1), "part-count"),
        ):
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(PrivateSpoolRefusal, reason):
                    self.commit(limits=policy)
                self.assertEqual(pending.read_bytes(), b"x"*23)
        self.assertEqual(self.commit(
            limits=self.limits(max_stored_bytes=self.payload_bytes()+23))["state"],
            "PART_CREATED")
        self.assertEqual(pending.read_bytes(), b"x"*23)

    def test_inventory_entry_budget_includes_directories_and_transient_names(self):
        with self.assertRaisesRegex(PrivateSpoolRefusal, "entry ceiling"):
            self.commit(limits=self.limits(max_inventory_entries=4))
        self.assertEqual(list(self.path.iterdir()), [])
        self.commit(limits=self.limits(max_inventory_entries=5))
        with self.assertRaisesRegex(PrivateSpoolRefusal, "entry ceiling"):
            self.commit(events=[event(i="another")],
                        limits=self.limits(max_inventory_entries=5))
        self.assertEqual(list(self.path.rglob(".pending-*")), [])

    def test_inventory_over_limit_refuses_even_identical_retry(self):
        self.commit()
        self.pending()
        with self.assertRaisesRegex(PrivateSpoolRefusal, "inventory entry ceiling"):
            self.commit(limits=self.limits(max_inventory_entries=4))

    def test_unknown_private_entries_and_empty_unknown_directories_fail_closed(self):
        for name, directory in (("foreign", False), ("foreign-dir", True)):
            path = self.path / name
            if directory:
                path.mkdir(mode=0o700)
            else:
                path.write_bytes(b"foreign")
                path.chmod(0o600)
            with self.assertRaisesRegex(PrivateSpoolRefusal, "unknown spool"):
                self.commit()
            path.unlink() if not directory else path.rmdir()

    def test_symlink_and_nonprivate_part_refused_even_on_identical_retry(self):
        first = self.commit()
        target = Path(first["path_private_only"])
        original = target.read_bytes()
        target.chmod(0o644)
        with self.assertRaisesRegex(PrivateSpoolRefusal, "private owned"):
            self.commit()
        target.chmod(0o600)
        target.unlink()
        target.symlink_to(self.path / "missing")
        with self.assertRaisesRegex(PrivateSpoolRefusal, "private owned"):
            self.commit()
        self.assertTrue(target.is_symlink())
        self.assertGreater(len(original), 0)

    def test_other_partition_symlink_is_not_traversed(self):
        foreign = self.path.parent / (self.path.name + "-foreign")
        foreign.mkdir(mode=0o700)
        self.addCleanup(foreign.rmdir)
        (self.path / "2026-10-09").symlink_to(foreign)
        with self.assertRaisesRegex(PrivateSpoolRefusal, "private owned"):
            self.commit()
        self.assertEqual(list(foreign.iterdir()), [])

    def test_special_file_and_external_hardlink_fail_closed(self):
        pending = self.pending()
        pending.unlink()
        os.mkfifo(pending, 0o600)
        with self.assertRaisesRegex(PrivateSpoolRefusal, "private owned"):
            self.commit()
        pending.unlink()
        first = self.commit()
        target = Path(first["path_private_only"])
        alias = self.path.parent / (self.path.name + "-alias")
        os.link(target, alias)
        self.addCleanup(alias.unlink)
        with self.assertRaisesRegex(PrivateSpoolRefusal, "single-link"):
            self.commit()
        self.assertEqual(alias.read_bytes(), target.read_bytes())

    def test_invalid_calendar_partition_never_created(self):
        row = event()
        row["session"] = "2026-02-30:RTH"
        with self.assertRaisesRegex(PrivateSpoolRefusal, "invalid session"):
            write_private_trade_part(root=self.path, session=row["session"],
                                     ticker="SPY", events=[row])
        self.assertEqual(list(self.path.iterdir()), [])

    def test_preflight_free_reserve_refuses_before_partition_creation(self):
        space = SimpleNamespace(f_frsize=4096, f_bavail=1)
        with patch("engine.tick_plane.private_spool.os.fstatvfs", return_value=space):
            with self.assertRaisesRegex(PrivateSpoolRefusal, "free-space"):
                self.commit(limits=self.limits())
        self.assertEqual(list(self.path.iterdir()), [])

    def test_postwrite_free_reserve_refuses_and_cleans_owned_pending(self):
        good = SimpleNamespace(f_frsize=4096, f_bavail=100)
        exhausted = SimpleNamespace(f_frsize=4096, f_bavail=0)
        with patch("engine.tick_plane.private_spool.os.fstatvfs",
                   side_effect=[good, exhausted]):
            with self.assertRaisesRegex(PrivateSpoolRefusal, "free-space"):
                self.commit(limits=self.limits())
        self.assertEqual(list(self.path.rglob("*.jsonl")), [])
        self.assertEqual(list(self.path.rglob(".pending-*")), [])
        self.assertEqual(self.commit()["state"], "PART_CREATED")

    def test_enospc_before_publish_preserves_prior_parts_and_releases_lock(self):
        first = self.commit()
        target = Path(first["path_private_only"])
        original = target.read_bytes()
        # ENOSPC may surface at flush/fsync after the temporary file was created.
        with patch("engine.tick_plane.private_spool.os.fsync",
                   side_effect=OSError(errno.ENOSPC, "injected no space")):
            with self.assertRaises(OSError) as caught:
                self.commit(events=[event(i="print-13")])
        self.assertEqual(caught.exception.errno, errno.ENOSPC)
        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(list(self.path.rglob(".pending-*")), [])
        self.assertEqual(self.commit(events=[event(i="print-13")])["state"],
                         "PART_CREATED")

    def test_distinct_writers_cannot_race_across_one_remaining_slot(self):
        from engine.tick_plane import private_spool
        entered, release = threading.Event(), threading.Event()
        original = private_spool._check_free
        def pause_admitted_writer(*args, **kwargs):
            if kwargs.get("incoming_bytes"):
                entered.set()
                if not release.wait(5):
                    raise AssertionError("writer was not released")
            return original(*args, **kwargs)
        policy = self.limits(max_parts=1)
        with ThreadPoolExecutor(max_workers=1) as pool:
            with patch.object(private_spool, "_check_free", side_effect=pause_admitted_writer):
                active = pool.submit(self.commit, limits=policy)
                self.assertTrue(entered.wait(5))
                try:
                    with self.assertRaises(PrivateSpoolBusy) as busy:
                        self.commit(events=[event(i="print-13")], limits=policy)
                    self.assertEqual(busy.exception.code, "SPOOL_BUSY")
                finally:
                    release.set()
                self.assertEqual(active.result(timeout=5)["state"], "PART_CREATED")
        with self.assertRaisesRegex(PrivateSpoolRefusal, "part-count"):
            self.commit(events=[event(i="print-13")], limits=policy)
        self.assertEqual(len(list(self.path.rglob("*.jsonl"))), 1)

    def test_separate_process_directory_lock_refuses_without_wait_or_effect(self):
        script = (
            "import fcntl, os, sys; "
            "fd=os.open(sys.argv[1], os.O_RDONLY|os.O_DIRECTORY); "
            "fcntl.flock(fd, fcntl.LOCK_EX); "
            "print('LOCKED', flush=True); sys.stdin.readline(); os.close(fd)"
        )
        process = subprocess.Popen([sys.executable, "-c", script, str(self.path)],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(process.stdout.readline().strip(), "LOCKED")
            with self.assertRaises(PrivateSpoolBusy):
                self.commit()
            self.assertEqual(list(self.path.iterdir()), [])
        finally:
            process.communicate(input="release\n", timeout=5)
        self.assertEqual(process.returncode, 0)
        self.assertEqual(self.commit()["state"], "PART_CREATED")

    def test_failed_pending_chmod_cleans_file_and_does_not_consume_slot(self):
        policy = self.limits(max_parts=1)
        with patch("engine.tick_plane.private_spool.os.fchmod",
                   side_effect=OSError(errno.EPERM, "injected mode refusal")):
            with self.assertRaises(OSError):
                self.commit(limits=policy)
        self.assertEqual(list(self.path.rglob(".pending-*")), [])
        self.assertEqual(list(self.path.rglob("*.jsonl")), [])
        self.assertEqual(self.commit(limits=policy)["state"], "PART_CREATED")

    def test_private_partition_permissions_checked_before_new_allocation(self):
        pending = self.pending()
        pending.parent.chmod(0o755)
        with self.assertRaisesRegex(PrivateSpoolRefusal, "private owned"):
            self.commit()
        self.assertEqual(list(self.path.rglob("*.jsonl")), [])
        self.assertEqual(pending.read_bytes(), b"")

    def test_repository_root_refused_without_source_write(self):
        with self.assertRaisesRegex(PrivateSpoolRefusal, "inside repository"):
            write_private_trade_part(root=Path(__file__).resolve().parents[1],
                                     session=SESSION, ticker="SPY", events=[event()])

    def test_new_partition_ancestors_are_fsynced_before_part_publication(self):
        mkdir, fsync, link = os.mkdir, os.fsync, os.link
        operations = []
        def observed_mkdir(name, *args, **kwargs):
            mkdir(name, *args, **kwargs)
            operations.append(("mkdir", os.fstat(kwargs["dir_fd"]).st_ino))
        def observed_fsync(fd):
            fsync(fd)
            operations.append(("fsync", os.fstat(fd).st_ino))
        def observed_link(*args, **kwargs):
            operations.append(("publish", None))
            return link(*args, **kwargs)
        with patch("engine.tick_plane.private_spool.os.mkdir", side_effect=observed_mkdir), \
             patch("engine.tick_plane.private_spool.os.fsync", side_effect=observed_fsync), \
             patch("engine.tick_plane.private_spool.os.link", side_effect=observed_link):
            self.commit()
        publication = operations.index(("publish", None))
        created = [(i, inode) for i, (kind, inode) in enumerate(operations)
                   if kind == "mkdir"]
        self.assertEqual(len(created), 3)
        for creation, parent_inode in created:
            with self.subTest(parent_inode=parent_inode):
                self.assertIn(("fsync", parent_inode), operations[creation+1:publication])

    def test_error_after_link_requires_digest_reconciliation_not_second_part(self):
        fsync, link = os.fsync, os.link
        published = False
        failed_once = False
        def observed_link(*args, **kwargs):
            nonlocal published
            result = link(*args, **kwargs)
            published = True
            return result
        def fail_after_link(fd):
            nonlocal failed_once
            if published and not failed_once:
                failed_once = True
                raise OSError(errno.EIO, "injected post-link durability error")
            return fsync(fd)
        policy = self.limits(max_parts=1)
        with patch("engine.tick_plane.private_spool.os.link", side_effect=observed_link), \
             patch("engine.tick_plane.private_spool.os.fsync", side_effect=fail_after_link):
            with self.assertRaises(OSError):
                self.commit(limits=policy)
        parts = list(self.path.rglob("*.jsonl"))
        self.assertEqual(len(parts), 1)
        inode, before = parts[0].stat().st_ino, parts[0].read_bytes()
        self.assertEqual(list(self.path.rglob(".pending-*")), [])
        retry = self.commit(limits=policy)
        self.assertEqual(retry["state"], "ALREADY_PRESENT")
        self.assertEqual((parts[0].stat().st_ino, parts[0].read_bytes()), (inode, before))

if __name__ == "__main__":
    unittest.main()
