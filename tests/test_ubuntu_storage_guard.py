import argparse
import importlib.util
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("ubuntu_storage_guard", HERE.parent / "scripts" / "ubuntu_storage_guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class GuardTests(unittest.TestCase):
    def test_pressure_ceiling_matches_ci_guard(self):
        self.assertEqual(guard.pressure(150 * guard.GIB, 1000 * guard.GIB)[0], "CRITICAL")
        self.assertEqual(guard.pressure(200 * guard.GIB, 1000 * guard.GIB)[0], "WARNING")
        self.assertEqual(guard.pressure(250 * guard.GIB, 1000 * guard.GIB)[0], "HEALTHY")
        self.assertEqual(guard.pressure(34 * guard.GIB, 1000 * guard.GIB)[0], "EMERGENCY")

    def test_floor_is_independent_of_percent(self):
        level, reasons, _ = guard.pressure(99 * guard.GIB, 200 * guard.GIB)
        self.assertEqual(level, "CRITICAL")
        self.assertIn("ci_disk_free_floor_100gib", reasons)
        level, reasons, _ = guard.pressure(100 * guard.GIB, 200 * guard.GIB)
        self.assertEqual(level, "WARNING")
        self.assertEqual(reasons, ["early_warning_margin"])

    def test_invalid_fs_fails_closed(self):
        for free, total in [(-1, 10), (11, 10), (0, 0)]:
            with self.assertRaises(ValueError):
                guard.pressure(free, total)

    def test_growth_rate_with_valid_predecessor(self):
        t = time.time()
        prev = {"schema": guard.SCHEMA, "observed_epoch": t - 3600,
                "disk": {"available_bytes": 200 * guard.GIB}}
        cur = {"available_bytes": 189 * guard.GIB}
        result = guard.compute_growth(prev, cur, t)
        self.assertEqual(result["trend"], "rapid_filling")
        self.assertEqual(result["available_gib_per_hour"], -11)
        self.assertEqual(guard.compute_growth(None, cur, t)["trend"], "no_previous_sample")
        prev["observed_epoch"] = t - 10
        self.assertEqual(guard.compute_growth(prev, cur, t)["trend"], "interval_out_of_range")

    def test_receipt_atomic_and_no_symlink_follow(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = root / "state" / "latest.json"
            guard.save_receipt(p, {"schema": guard.SCHEMA, "disk": {"available_bytes": 42}})
            self.assertEqual(json.loads(p.read_text())["disk"]["available_bytes"], 42)
            self.assertEqual(p.stat().st_mode & 0o777, 0o600)
            guard.save_receipt(p, {"schema": guard.SCHEMA, "disk": {"available_bytes": 99}})
            self.assertEqual(guard.load_previous(p)["disk"]["available_bytes"], 99)
            link = root / "link.json"
            link.symlink_to(p)
            with self.assertRaises(RuntimeError):
                guard.save_receipt(link, {"a": 1})
            self.assertIsNone(guard.load_previous(link))
            self.assertEqual(guard.load_previous(p)["disk"]["available_bytes"], 99)

    def test_existing_sentinel_remains_default_off(self):
        with tempfile.TemporaryDirectory() as d:
            args = argparse.Namespace(receipt=str(Path(d) / "latest.json"),
                                      vacuum=False, reclaim_pytest_garbage=False)
            with mock.patch.object(guard, "disk_status", return_value={
                "level": "EMERGENCY", "available_bytes": 0,
            }), mock.patch.object(guard, "systemd_units", return_value={}), \
                 mock.patch.object(guard, "scratch_snapshot", return_value={"present": False}):
                report = guard.run(args)
            self.assertEqual(report["gc_mode"], "read_only")
            self.assertEqual(report["pytest_reclaim"], {"attempted": False})
            self.assertFalse(report["source_delete_enabled"])

    def test_unenrolled_host_refuses_generated_temp_reclaim(self):
        with tempfile.TemporaryDirectory() as d:
            args = argparse.Namespace(receipt=str(Path(d) / "latest.json"),
                                      vacuum=False, reclaim_pytest_garbage=True)
            with mock.patch.object(guard, "disk_status", return_value={
                "level": "EMERGENCY", "available_bytes": 0,
            }), mock.patch.object(guard, "systemd_units", return_value={}), \
                 mock.patch.object(guard, "scratch_snapshot", return_value={"present": False}), \
                 mock.patch.object(guard.socket, "gethostname", return_value="untrusted-host"):
                report = guard.run(args)
            self.assertEqual(report["pytest_reclaim"]["status"], "REFUSED_UNENROLLED_HOST")
            self.assertFalse(report["pytest_reclaim"]["attempted"])
            self.assertFalse(report["source_delete_enabled"])

    def test_no_source_deletion_in_public_surface(self):
        self.assertNotIn("source", guard.vacuum_archived_journals.__doc__.lower() if guard.vacuum_archived_journals.__doc__ else "")
        self.assertEqual(guard.scratch_snapshot("/definitely/unavailable")["present"], False)


if __name__ == "__main__":
    unittest.main()

