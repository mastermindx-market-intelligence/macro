"""Local fake consumers only; never invoke installed product CLIs."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from bind_followon_adoption_probe import bind as source_binding


spec = importlib.util.spec_from_file_location(
    "probe", Path(__file__).with_name("followon_adoption_probe.py"))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

TIER = {"schema": "intelligence_registry.required_tier_cli.v1",
        "query": {"schema": "intelligence_registry.required_tier.v1",
                  "scope": "exact_registered_producer_paths", "status": "unresolved",
                  "changed_paths": ["engine/a.py"], "engines": [],
                  "unresolved": [{"path": "engine/a.py", "reason": "unmatched_producer"}],
                  "evaluation_status": "not_assessed", "required_tier": None,
                  "maximum_supported_tier": None},
        "source_report": {"DO_NOT_EXPORT": "private source detail"}}
HEALTH = {"schema": "postmortem.source_findings.v1", "scope": "source_data_observations",
          "evaluation_status": "not_assessed", "count_unit": "health_observations",
          "observation_identity_scope": "this_snapshot_only", "n_outputs": 0,
          "observation_unit": "output_reason_pair_in_supplied_snapshot", "observed_at": None,
          "unavailable_output_count": 0, "unclassified_observation_count": 0,
          "observations": [], "groups": [], "unaffected_outputs": []}


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.binding = self.root / "binding.json"
        self.python = str(Path(sys.executable).resolve())
        for path in probe.FILES:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# inert direct identity input\n")
        self.script(1, "print(" + repr(json.dumps(TIER)) + ")\n")
        self.script(3, "print(" + repr(json.dumps(HEALTH)) + ")\n")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Test",
                        "-c", "user.email=test@example.invalid", "commit", "--allow-empty",
                        "-qm", "fake consumer test"], check=True)
        self.bind()

    def script(self, index, text):
        (self.root / probe.FILES[index]).write_text(text)

    def bind(self):
        self.binding.write_text(json.dumps({"schema": "eval_os.followon_probe_binding.v1",
                                           "source_commit": "a" * 40,
                                           "files": probe.snapshot(self.root)}))

    def observe(self, **changes):
        args = {"root": self.root, "binding_path": self.binding,
                "producers": ["engine/a.py"], "python": self.python}
        args.update(changes)
        return probe.observe(**args)

    def test_real_subprocess_contracts_keep_unknown_and_hide_details(self):
        result = self.observe()
        self.assertEqual(result["status"], "observed", result)
        self.assertIsNone(result["commands"][0]["summary"]["required_tier"])
        self.assertEqual(result["commands"][1]["summary"]["n_outputs"], 0)
        self.assertEqual(result["before"], result["after"])
        self.assertEqual(result["head_before"], result["head_after"])
        self.assertNotEqual(result["source_commit"], result["head_before"])
        self.assertNotIn("private source detail", json.dumps(result))
        self.assertTrue(all(result[k] is False for k in
                            ("production_proven", "programme_complete", "discovery_adopted")))
        self.assertFalse(list(self.root.rglob("__pycache__")))

    def test_binding_mismatch_stops_before_any_child(self):
        self.script(1, "raise RuntimeError('not allowed to run')\n")
        with mock.patch.object(probe, "capture", side_effect=AssertionError("child called")):
            self.assertEqual(self.observe()["reason"], "source_binding_mismatch")

    def test_native_numeric_source_changes_refuse_before_cli_execution(self):
        for source in ("engine/neuralweb/response_eval.py", "engine/neuralweb/native_facts.py",
                       "engine/neuralweb/brain_gateway.py", "lib/mastermind_response_log.py"):
            with self.subTest(source=source):
                original = (self.root / source).read_text()
                (self.root / source).write_text(original + "# changed installed source\n")
                with mock.patch.object(probe, "capture", side_effect=AssertionError("child called")):
                    self.assertEqual(self.observe()["reason"], "source_binding_mismatch")
                (self.root / source).write_text(original)

    def test_stale_updater_refuses_before_cli_execution(self):
        updater = self.root / "app/deploy/update.sh"
        updater.parent.mkdir(parents=True, exist_ok=True)
        updater.write_text("# stale updater missing the numeric-checker restart rule\n")
        with mock.patch.object(probe, "capture", side_effect=AssertionError("child called")):
            self.assertEqual(self.observe()["reason"], "source_binding_mismatch")

    def test_older_binding_without_updater_refuses_before_cli_execution(self):
        binding = json.loads(self.binding.read_text())
        binding["files"].pop("app/deploy/update.sh", None)
        self.binding.write_text(json.dumps(binding))
        with mock.patch.object(probe, "capture", side_effect=AssertionError("child called")):
            self.assertEqual(self.observe()["reason"], "invalid_binding")

    def test_symlink_file_and_parent_stop_before_any_child(self):
        target = self.root / probe.FILES[0]
        original = self.root / "saved.py"
        target.rename(original)
        target.symlink_to(original)
        with mock.patch.object(probe, "capture", side_effect=AssertionError("child called")):
            self.assertEqual(self.observe()["status"], "refused")
        target.unlink()
        original.rename(target)
        engine = self.root / "engine"
        engine.rename(self.root / "moved")
        engine.symlink_to(self.root / "moved", target_is_directory=True)
        with mock.patch.object(probe, "capture", side_effect=AssertionError("child called")):
            self.assertEqual(self.observe()["status"], "refused")

    def test_bad_binding_and_paths_stop_before_any_child(self):
        with mock.patch.object(probe, "capture", side_effect=AssertionError("child called")):
            for value in ["{}", '{"x":1,"x":2}', '{"x":NaN}', '{"x":1e999}', "[[]]"]:
                with self.subTest(value=value):
                    self.binding.write_text(value)
                    self.assertEqual(self.observe()["status"], "refused")
            self.bind()
            for path in ["../x", "/x", "x//y", "x/./y", "x\\y", ""]:
                self.assertEqual(self.observe(producers=[path])["status"], "refused")

    def test_invalid_child_json_and_rc_stop_second_command(self):
        second_marker = self.root / "second_ran"
        self.script(3, "from pathlib import Path\nPath(" + repr(str(second_marker)) + ").touch()\n")
        for text in ["not json", '{"x":NaN}', '{"x":1e999}', '{"x":1,"x":2}', "[]"]:
            with self.subTest(text=text):
                self.script(1, "print(" + repr(text) + ")\n")
                self.bind()
                self.assertEqual(self.observe()["status"], "refused")
                self.assertFalse(second_marker.exists())
        self.script(1, "import sys\nprint('secret-looking error', file=sys.stderr)\nsys.exit(4)\n")
        self.bind()
        result = self.observe()
        self.assertEqual(result["reason"], "consumer_execution_failed")
        self.assertEqual(result["commands"][0]["returncode"], 4)
        self.assertNotIn("secret-looking error", json.dumps(result))
        self.assertFalse(second_marker.exists())

    def test_source_change_between_commands_prevents_second_invocation(self):
        marker = self.root / "second_ran"
        self.script(1, "from pathlib import Path\nPath(" + repr(str(self.root / probe.FILES[2]))
                    + ").write_text('changed')\nprint(" + repr(json.dumps(TIER)) + ")\n")
        self.script(3, "from pathlib import Path\nPath(" + repr(str(marker)) + ").touch()\n")
        self.bind()
        result = self.observe()
        self.assertEqual(result["reason"], "source_changed_during_observation")
        self.assertEqual(len(result["commands"]), 1)
        self.assertFalse(marker.exists())

    def test_last_consumer_mutation_cannot_report_observed(self):
        self.script(3, "from pathlib import Path\nPath(" + repr(str(self.root / probe.FILES[2]))
                    + ").write_text('changed')\nprint(" + repr(json.dumps(HEALTH)) + ")\n")
        self.bind()
        result = self.observe()
        self.assertEqual(result["reason"], "source_changed_during_observation")
        self.assertNotEqual(result["before"], result["after"])

    def test_wrong_query_identity_cannot_report_observed(self):
        for mutation in ("paths", "schema", "source_report"):
            value = json.loads(json.dumps(TIER))
            if mutation == "paths":
                value["query"]["changed_paths"] = ["engine/someone_else.py"]
            elif mutation == "schema":
                value["query"]["schema"] = "some_other_contract"
            else:
                value["source_report"] = None
            self.script(1, "print(" + repr(json.dumps(value)) + ")\n")
            self.bind()
            with self.subTest(mutation=mutation):
                self.assertEqual(self.observe()["status"], "refused")

    def test_missing_observation_identity_cannot_report_observed(self):
        value = json.loads(json.dumps(HEALTH))
        del value["observation_unit"]
        self.script(3, "print(" + repr(json.dumps(value)) + ")\n")
        self.bind()
        self.assertEqual(self.observe()["status"], "refused")

    def test_hanging_and_overflowing_children_are_reaped(self):
        for code, condition in [("import time; time.sleep(30)", "timeout"),
                                ("import os; os.write(1,b'x'*8192)", "output_limit"),
                                ("import os; os.write(2,b'x'*8192)", "output_limit")]:
            with self.subTest(condition=condition):
                created = []
                popen = subprocess.Popen
                def tracked(*args, **kwargs):
                    p = popen(*args, **kwargs)
                    created.append(p)
                    return p
                with mock.patch.object(probe.subprocess, "Popen", side_effect=tracked):
                    record, _ = probe.capture([self.python, "-c", code], self.root, 0.5, 1024)
                self.assertEqual(record["condition"], condition)
                self.assertTrue(all(p.poll() is not None for p in created))
                self.assertLessEqual(record["streams"]["stdout"]["captured_bytes"], 1025)
                self.assertLessEqual(record["streams"]["stderr"]["captured_bytes"], 1025)

    def test_actual_command_line_prints_bounded_receipt(self):
        p = subprocess.run([self.python, "-B", str(Path(probe.__file__)), "--root", str(self.root),
                            "--binding", str(self.binding), "--producer", "engine/a.py",
                            "--python", self.python], capture_output=True, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["status"], "observed")
        self.assertLess(len(p.stdout), 8192)

    def test_offline_binding_uses_commit_bytes_not_working_tree(self):
        subprocess.run(["git", "-C", str(self.root), "add", *probe.FILES], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Test",
                        "-c", "user.email=test@example.invalid", "commit", "-qm", "bound bytes"], check=True)
        revision = subprocess.check_output(["git", "-C", str(self.root), "rev-parse", "HEAD"],
                                           text=True).strip()
        original = probe.snapshot(self.root)
        self.script(1, "changed working tree\n")
        self.assertEqual(source_binding(self.root, revision)["files"], original)
        with self.assertRaises(ValueError):
            source_binding(self.root, "HEAD")

    def test_offline_binding_refuses_git_symlink(self):
        target = self.root / probe.FILES[0]
        target.unlink()
        target.symlink_to("../scripts/agentos.py")
        subprocess.run(["git", "-C", str(self.root), "add", *probe.FILES], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Test",
                        "-c", "user.email=test@example.invalid", "commit", "-qm", "bad input"], check=True)
        revision = subprocess.check_output(["git", "-C", str(self.root), "rev-parse", "HEAD"],
                                           text=True).strip()
        with self.assertRaises(ValueError):
            source_binding(self.root, revision)


if __name__ == "__main__":
    unittest.main()
