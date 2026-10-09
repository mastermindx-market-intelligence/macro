"""Private T.* spool: no Q.* retention, immutable parts and crash-safe IO."""

import copy
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
    PrivateSpoolRefusal, write_private_trade_part,
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
        def rival_created_target(src, dest):
            Path(dest).write_bytes(b"rival-conflicting-part")
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
        def rival_created_same_target(src,dest):
            Path(dest).write_bytes(Path(src).read_bytes())
            raise FileExistsError()
        with patch("engine.tick_plane.private_spool.os.link",
                   side_effect=rival_created_same_target):
            result=self.commit()
        self.assertEqual(result["state"],"ALREADY_PRESENT")
        self.assertEqual(list(self.path.rglob(".pending-*")),[])

    def test_concurrent_same_digest_is_one_immutable_part(self):
        # Production requires one writer; this synthetic race proves that
        # unexpected concurrent attempts cannot overwrite source receipts.
        with ThreadPoolExecutor(max_workers=6) as pool:
            receipts=list(pool.map(lambda _ : self.commit(),range(6)))
        self.assertEqual({r["sha256"] for r in receipts},
                         {receipts[0]["sha256"]})
        self.assertEqual([r["state"] for r in receipts].count("PART_CREATED"),1)
        self.assertEqual(len(list(self.path.rglob("*.jsonl"))),1)
        self.assertEqual(list(self.path.rglob(".pending-*")),[])

if __name__ == "__main__":
    unittest.main()
