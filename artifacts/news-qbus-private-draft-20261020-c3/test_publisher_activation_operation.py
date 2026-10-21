"""Local, isolated operation discrimination; never calls systemd or the VPS."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
FIXTURES = json.loads((HERE / "publisher_activation_fixture_receipts.json").read_text())
MERGE = "a" * 40
SECRET = "FAKE_TEST_SECRET_`touch /tmp/never_execute_activation`_$(false)"


class OperationTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("activation_test_subject", HERE / "publisher_activation_operation.py")
        self.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.m)
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        m = self.m
        m.ROOT = self.base / "macro"
        m.ROOT.mkdir()
        m.STATE = self.base / "state"
        m.STATE.mkdir(mode=0o700)
        m.CARRIER = m.STATE / m.OPERATION
        m.PHASE_FILE = m.CARRIER / "phase.json"
        m.BACKUPS = m.CARRIER / "backups"
        m.LOCK = self.base / "update.lock"
        m.LOCK.write_bytes(b"")
        m.LOCK.chmod(0o600)
        m.PYTHON = sys.executable
        self.etc = self.base / "etc"
        self.etc.mkdir()
        m.WRITER_ENV = self.etc / "writer.env"
        m.API_ENV = self.etc / "api.env"
        m.API_LATER_ENV = self.etc / "ollama.env"
        m.LIVE_ENV = self.etc / "live.env"
        m.PRIMARY_RIGHTS = self.etc / "primary.json"
        m.RIGHTS_PATHS = [str(self.etc / (slug + ".json")) for slug, _, _ in m.RECEIPTS]
        self.writer_before = b"# incumbent\nQBUS_NEWS_PROVIDER=alpaca\nALPACA_API_KEY_ID=fake\nALPACA_API_SECRET_KEY=fake\nOTHER_WRITER_KEY=preserve\n"
        self.api_before = b"# existing API\nOTHER_API_KEY=preserve\n"
        self.write(m.WRITER_ENV, self.writer_before)
        self.write(m.API_ENV, self.api_before)
        self.write(m.LIVE_ENV, ("MASSIVE_API_KEY='" + SECRET + "'\nOTHER_LIVE=preserve\n").encode())
        self.write(m.PRIMARY_RIGHTS, b"{}\n")
        repo_receipts = m.ROOT / "artifacts/news-shared-integration-20261020-c3/activation"
        repo_receipts.mkdir(parents=True)
        for name, content in FIXTURES.items():
            (repo_receipts / name).write_text(content)
        self.services = {unit: {"ActiveState": "active", "MainPID": str(10 + i),
                               "SubState": "running"} for i, unit in enumerate((m.API_UNIT, m.WRITER_UNIT))}
        self.real_source_and_services = m.source_and_services
        self.real_service_state = m.service_state
        m.source_and_services = lambda expected: (MERGE, copy.deepcopy(self.services))
        m.service_state = lambda unit: copy.deepcopy(self.services[unit])
        self.commands = []
        self.fail_check = False

        def fake_command(argv, label, timeout=30):
            self.assertNotIn(SECRET, " ".join(argv))
            self.commands.append((label, argv))
            if label == "network_dark_check":
                if self.fail_check:
                    raise m.Refusal("network_dark_check_nonzero")
                report = {"schema": "qbus.news_runner_preflight.v1", "provider": "alpaca",
                          "run_requested": False, "check_requested": True,
                          "additional_sources_qualified": 3, "database": str(m.STATE / "qbus.sqlite3"),
                          "universe_count": 1500, "universe_revision": "canonical-revision"}
                for field in ("activation_qualified", "token_present", "universe_present",
                              "rights_receipt_present", "health_path_present", "additional_sources_enabled"):
                    report[field] = True
                sources = {"schema": "shared_news.activation_sources_check.v1",
                           "qualified_sources": {aud: m.SOURCES for aud in m.AUDIENCES}}
                return json.dumps(report) + "\n" + json.dumps(sources) + "\n"
            if label.startswith("restart_"):
                self.services[argv[2]]["MainPID"] = str(int(self.services[argv[2]]["MainPID"]) + 100)
                return ""
            raise AssertionError("Unexpected external command")

        m.command = fake_command

    def tearDown(self):
        self.temp.cleanup()

    def write(self, path, data):
        path.write_bytes(data)
        path.chmod(0o600)

    def invoke(self, apply=False):
        previous = sys.argv
        sys.argv = [str(HERE / "publisher_activation_operation.py"), "--expected-merge", MERGE] + (["--apply"] if apply else [])
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                result = self.m.main()
        finally:
            sys.argv = previous
        self.assertNotIn(SECRET, out.getvalue())
        return result, json.loads(out.getvalue())

    def test_preview_has_no_effect(self):
        result, output = self.invoke()
        self.assertEqual(result, 0)
        self.assertEqual(output["state"], "preview_qualified")
        self.assertFalse(self.m.CARRIER.exists())
        self.assertEqual(self.m.WRITER_ENV.read_bytes(), self.writer_before)
        self.assertEqual(self.m.API_ENV.read_bytes(), self.api_before)
        self.assertEqual(self.commands, [])

    def test_apply_preserves_values_orders_effects_and_never_replays(self):
        result, output = self.invoke(True)
        self.assertEqual(result, 0)
        self.assertEqual(output["state"], "applied_awaiting_live_proof")
        self.assertFalse(output["live_coverage_verified"])
        self.assertTrue(self.m.WRITER_ENV.read_bytes().startswith(self.writer_before))
        self.assertIn(("POLYGON_API_KEY='" + SECRET + "'\n").encode(), self.m.WRITER_ENV.read_bytes())
        self.assertTrue(self.m.API_ENV.read_bytes().startswith(self.api_before))
        self.assertNotIn(SECRET.encode(), self.m.API_ENV.read_bytes())
        self.assertEqual((self.m.BACKUPS / self.m.WRITER_ENV.name).read_bytes(), self.writer_before)
        self.assertEqual([name for name, _ in self.commands],
                         ["network_dark_check", "restart_macro-api.service", "restart_macro-ticker-news.service"])
        phase = json.loads(self.m.PHASE_FILE.read_text())
        events = [e["phase"] for e in phase["events"]]
        self.assertLess(events.index("backups_complete"), events.index("environment_write_requested"))
        self.assertLess(events.index("network_dark_check_passed"), events.index("restart_requested"))
        for path in [self.m.PHASE_FILE, self.m.WRITER_ENV, self.m.API_ENV, *map(Path, self.m.RIGHTS_PATHS)]:
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.m.BACKUPS.stat().st_mode), 0o700)
        replay_result, replay = self.invoke(True)
        self.assertEqual(replay_result, 0)
        self.assertEqual(replay["state"], "same_carrier_readback_only")
        self.assertEqual(len(self.commands), 3)

    def test_failed_check_retains_phase_and_refuses_automatic_retry(self):
        self.fail_check = True
        result, output = self.invoke(True)
        self.assertEqual(result, 3)
        self.assertEqual(output["state"], "effect_requires_readback")
        self.assertEqual(len(self.commands), 1)
        self.assertEqual(self.services[self.m.WRITER_UNIT]["MainPID"], "11")
        again, readback = self.invoke(True)
        self.assertEqual(again, 3)
        self.assertEqual(readback["recorded_phase"], "stopped_requires_same_carrier_reconciliation")
        self.assertEqual(len(self.commands), 1)

    def test_optional_key_without_prior_carrier_refused(self):
        self.write(self.m.WRITER_ENV, self.writer_before + b"MM_TICKER_NEWS_MASSIVE_ENABLED=1\n")
        with self.assertRaisesRegex(self.m.Refusal, "without_carrier"):
            self.invoke(True)
        self.assertFalse(self.m.CARRIER.exists())

    def test_non_alpaca_and_duplicate_key_refused(self):
        self.write(self.m.WRITER_ENV, self.writer_before.replace(b"=alpaca", b"=benzinga"))
        with self.assertRaisesRegex(self.m.Refusal, "primary_provider"):
            self.invoke(True)
        self.write(self.m.WRITER_ENV, self.writer_before + b"QBUS_NEWS_PROVIDER=alpaca\n")
        with self.assertRaisesRegex(self.m.Refusal, "duplicate_key"):
            self.invoke(True)
        self.assertFalse(self.m.CARRIER.exists())

    def test_receipt_symlink_is_preserved_and_refused(self):
        target = self.etc / "other-file"
        self.write(target, b"preserve")
        Path(self.m.RIGHTS_PATHS[0]).symlink_to(target)
        with self.assertRaisesRegex(self.m.Refusal, "regular_file_unreadable"):
            self.invoke(True)
        self.assertEqual(target.read_bytes(), b"preserve")
        self.assertFalse(self.m.CARRIER.exists())

    def test_atomic_no_clobber_and_stale_preimage(self):
        path = self.etc / "atomic"
        self.m.atomic_write(path, b"before", absent=True)
        with self.assertRaises(FileExistsError):
            self.m.atomic_write(path, b"after", absent=True)
        self.assertEqual(path.read_bytes(), b"before")
        with self.assertRaisesRegex(self.m.Refusal, "changed_since_preflight"):
            self.m.atomic_write(path, b"after", previous=b"stale")
        self.assertEqual(path.read_bytes(), b"before")

    def test_malformed_env_is_not_evaluated(self):
        for data in (b"KEY=first\\\nsecond\n", b"KEY='first\nsecond'\n", b"KEY=value\r\n"):
            with self.assertRaises(self.m.Refusal):
                self.m.env_assignments(data, "fictional")
        self.assertFalse(Path("/tmp/never_execute_activation").exists())

    def test_unrelated_duplicate_keys_remain_untouched(self):
        original = self.api_before + b"OTHER_API_KEY=incumbent_later_assignment\n"
        self.write(self.m.API_ENV, original)
        result, output = self.invoke(True)
        self.assertEqual(result, 0)
        self.assertTrue(self.m.API_ENV.read_bytes().startswith(original))

    def qualify_service_fixture(self, api_environment_lines):
        """Exercise the real source/service gate with local units and fake systemctl.

        The repeated EnvironmentFiles lines match the production preview format.
        Source/installed-unit bytes are an isolated two-unit fixture; no /etc file,
        /proc entry, systemd service, git repository, or VPS is accessed.
        """
        m = self.m
        m.API_ENV = Path("/etc/macro-api.env")
        m.API_LATER_ENV = Path("/etc/macro-ollama.env")
        m.WRITER_ENV = Path("/etc/macro-ticker-news.env")
        unit_bytes = {unit: ("[Service]\n# " + unit + " fixture\n").encode()
                      for unit in (m.API_UNIT, m.WRITER_UNIT)}
        m.SOURCE_BLOBS = {"app/deploy/" + unit: m.git_blob(data)
                          for unit, data in unit_bytes.items()}
        for unit, data in unit_bytes.items():
            path = m.ROOT / "app/deploy" / unit
            path.parent.mkdir(parents=True, exist_ok=True)
            self.write(path, data)
        original_read = m.regular_bytes

        def local_read(path, **kwargs):
            installed = Path("/etc/systemd/system")
            if path.parent == installed and path.name in unit_bytes:
                return unit_bytes[path.name]
            return original_read(path, **kwargs)

        m.regular_bytes = local_read
        m.service_state = self.real_service_state
        m.sole_writer = lambda pid: [int(pid)]

        def fixture_command(argv, label, timeout=30):
            if label == "git_head":
                return MERGE + "\n"
            if label == "expected_merge_not_deployed":
                return ""
            if label == "git_source_tree":
                return "".join("100644 blob " + pin + "\t" + path + "\n"
                               for path, pin in m.SOURCE_BLOBS.items())
            if label == "service_read":
                unit = argv[2]
                self.assertIn(unit, unit_bytes)
                pid = "3217327" if unit == m.API_UNIT else "3217613"
                environment = (api_environment_lines if unit == m.API_UNIT else
                               "EnvironmentFiles=/etc/macro-ticker-news.env (ignore_errors=yes)\n")
                return ("ActiveState=active\nSubState=running\nMainPID=" + pid +
                        "\nExecMainStartTimestamp=Tue 2026-10-20 17:10:39 UTC\n" +
                        "FragmentPath=/etc/systemd/system/" + unit +
                        "\nDropInPaths=\nNeedDaemonReload=no\n" + environment)
            raise AssertionError("Unexpected external command: " + label)

        m.command = fixture_command
        return self.real_source_and_services(MERGE)

    def test_service_state_preserves_repeated_environment_files_in_order(self):
        _head, services = self.qualify_service_fixture(
            "EnvironmentFiles=/etc/macro-api.env (ignore_errors=yes)\n"
            "EnvironmentFiles=/etc/macro-ollama.env (ignore_errors=yes)\n")
        self.assertEqual(
            services[self.m.API_UNIT]["EnvironmentFiles"],
            "/etc/macro-api.env (ignore_errors=yes) /etc/macro-ollama.env (ignore_errors=yes)")
        self.assertEqual(services[self.m.API_UNIT]["MainPID"], "3217327")

    def test_service_state_supports_combined_environment_files_property(self):
        self.qualify_service_fixture(
            "EnvironmentFiles=/etc/macro-api.env (ignore_errors=yes) "
            "/etc/macro-ollama.env (ignore_errors=yes)\n")

    def test_duplicate_missing_reordered_or_extra_environment_file_refused(self):
        api = "EnvironmentFiles=/etc/macro-api.env (ignore_errors=yes)\n"
        ollama = "EnvironmentFiles=/etc/macro-ollama.env (ignore_errors=yes)\n"
        extra = "EnvironmentFiles=/etc/unreviewed.env (ignore_errors=yes)\n"
        for case in (api + api + ollama, api + ollama + ollama, ollama,
                     ollama + api, api + ollama + extra):
            with self.subTest(environment=case):
                with self.assertRaisesRegex(
                        self.m.Refusal, "loaded_environment_files_drift:macro-api.service"):
                    self.qualify_service_fixture(case)

    def test_duplicate_single_value_service_property_refused(self):
        self.m.command = lambda *args, **kwargs: "MainPID=3217327\nMainPID=9999\n"
        with self.assertRaisesRegex(self.m.Refusal, "duplicate_service_property"):
            self.real_service_state(self.m.API_UNIT)


if __name__ == "__main__":
    unittest.main()
