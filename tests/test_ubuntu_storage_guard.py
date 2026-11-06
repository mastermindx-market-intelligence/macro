import importlib.util
import json
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
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

    def test_missing_scratch_is_absent(self):
        self.assertEqual(guard.scratch_snapshot("/definitely/unavailable")["present"], False)

    def _run_with_maintenance_mock(self, level, vacuum, outcome):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            receipt = root / "state" / "latest.json"
            kept_source = root / "source-kept.txt"
            kept_source.write_text("resumable source")
            disk = {"level": level, "available_bytes": 200 * guard.GIB,
                    "available_gib": 200, "used_percent": 80}
            with (
                mock.patch.object(guard, "disk_status", return_value=disk),
                mock.patch.object(guard, "systemd_units", return_value={"pc-ci-1": "active"}),
                mock.patch.object(guard, "scratch_snapshot", return_value={"present": False}),
                mock.patch.object(guard.subprocess, "run") as invoke,
            ):
                if isinstance(outcome, BaseException):
                    invoke.side_effect = outcome
                else:
                    invoke.return_value = outcome
                report = guard.run(SimpleNamespace(receipt=str(receipt), vacuum=vacuum))
            written = json.loads(receipt.read_text())
            self.assertEqual(written, report)
            self.assertIs(written["source_delete_enabled"], False)
            self.assertEqual(written["gc_mode"], "read_only")
            self.assertEqual(kept_source.read_text(), "resumable source")
            self.assertEqual(list(receipt.parent.glob(".storage-status-*")), [])
            return report, invoke

    def test_run_never_maintains_without_pressure_and_opt_in(self):
        cases = [(level, False) for level in
                 ("HEALTHY", "WARNING", "CRITICAL", "EMERGENCY")]
        cases.append(("HEALTHY", True))
        for level, vacuum in cases:
            with self.subTest(level=level, vacuum=vacuum):
                report, invoke = self._run_with_maintenance_mock(
                    level, vacuum, subprocess.CompletedProcess([], 0, "", ""))
                invoke.assert_not_called()
                self.assertEqual(report["journal_maintenance"], {"attempted": False})

    def _assert_only_fixed_vacuum(self, invoke):
        invoke.assert_called_once_with(
            ["journalctl", "--vacuum-size=800M"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, check=False, timeout=40,
        )

    def test_run_vacuums_only_fixed_argv_for_each_pressure_level(self):
        for level in ("WARNING", "CRITICAL", "EMERGENCY"):
            with self.subTest(level=level):
                report, invoke = self._run_with_maintenance_mock(
                    level, True, subprocess.CompletedProcess([], 0, "", "archived only"))
                self._assert_only_fixed_vacuum(invoke)
                self.assertEqual(report["journal_maintenance"],
                                 {"attempted": True, "exit_code": 0,
                                  "detail": "archived only"})

    def test_run_nonzero_vacuum_is_recorded_without_fallback(self):
        report, invoke = self._run_with_maintenance_mock(
            "CRITICAL", True, subprocess.CompletedProcess([], 7, "", "refused"))
        self._assert_only_fixed_vacuum(invoke)
        self.assertEqual(report["journal_maintenance"],
                         {"attempted": True, "exit_code": 7, "detail": "refused"})

    def test_run_vacuum_errors_are_recorded_without_fallback(self):
        for error in (OSError("unavailable"),
                      subprocess.TimeoutExpired(["journalctl"], 40)):
            with self.subTest(error=type(error).__name__):
                report, invoke = self._run_with_maintenance_mock("EMERGENCY", True, error)
                self._assert_only_fixed_vacuum(invoke)
                self.assertEqual(report["journal_maintenance"],
                                 {"attempted": True, "error": type(error).__name__})

    @staticmethod
    def _source_layout(path):
        (path / ".github").mkdir(parents=True)
        (path / "scripts").mkdir()
        return path

    def test_scratch_recognizes_nested_direct_and_both_once(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._source_layout(root / "nested" / "tree")
            self._source_layout(root / "direct")
            self._source_layout(root / "both")
            self._source_layout(root / "both" / "tree")
            result = guard.scratch_snapshot(str(root))
            self.assertEqual(result["subdirs"], 3)
            self.assertEqual(result["materialized_tree_dirs"], 3)
            self.assertEqual(result["nested_tree_dirs"], 2)
            self.assertEqual(result["direct_source_dirs"], 1)
            self.assertEqual(result["unclassified_stage_dirs"], 0)

    def test_scratch_partial_empty_and_file_markers_are_unclassified(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "partial" / "scripts").mkdir(parents=True)
            (root / "empty" / "tree").mkdir(parents=True)
            (root / "file-marker" / ".github").mkdir(parents=True)
            (root / "file-marker" / "scripts").write_text("not a directory")
            result = guard.scratch_snapshot(str(root))
            self.assertEqual(result["subdirs"], 3)
            self.assertEqual(result["materialized_tree_dirs"], 0)
            self.assertEqual(result["unclassified_stage_dirs"], 3)

    def test_scratch_does_not_follow_stage_tree_or_marker_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            root = base / "stages"
            root.mkdir()
            outside = self._source_layout(base / "outside")
            (root / "linked-stage").symlink_to(outside, target_is_directory=True)
            (root / "linked-tree").mkdir()
            (root / "linked-tree" / "tree").symlink_to(outside, target_is_directory=True)
            (root / "linked-marker" / ".github").mkdir(parents=True)
            (root / "linked-marker" / "scripts").symlink_to(
                outside / "scripts", target_is_directory=True)
            result = guard.scratch_snapshot(str(root))
            self.assertEqual(result["subdirs"], 2)
            self.assertEqual(result["materialized_tree_dirs"], 0)
            self.assertEqual(result["unclassified_stage_dirs"], 2)
            link = base / "linked-root"
            link.symlink_to(root, target_is_directory=True)
            self.assertEqual(guard.scratch_snapshot(str(link)), {"present": False})

    def test_scratch_unreadable_root_is_incomplete(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(guard.os, "open", side_effect=PermissionError("denied")):
                self.assertEqual(guard.scratch_snapshot(d),
                                 {"present": True, "inventory": "incomplete"})

    def test_scratch_unreadable_or_disappearing_stage_is_incomplete(self):
        for error in (PermissionError("denied"), FileNotFoundError("disappeared")):
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                self._source_layout(root / "blocked")
                real_open = guard.os.open

                def guarded_open(path, flags, *args, **kwargs):
                    if path == "blocked":
                        raise error
                    return real_open(path, flags, *args, **kwargs)

                with mock.patch.object(guard.os, "open", side_effect=guarded_open):
                    result = guard.scratch_snapshot(str(root))
                self.assertEqual(result, {"present": True, "inventory": "incomplete"})


if __name__ == "__main__":
    unittest.main()

