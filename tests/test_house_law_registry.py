"""Tests for the house-law registry meta-guard.

Three test suites:
  1. Integration: real registry passes all passes against the real repo.
  2. Selftest: --selftest flag passes via subprocess.
  3. Docs idempotency: --emit-docs regenerating into a tempfile equals the committed
     docs file byte-for-byte.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_house_law_registry.py"
COMMITTED_DOCS = REPO_ROOT / "docs" / "HOUSE_LAW_CI_GUARD_SUITE.md"

sys.path.insert(0, str(REPO_ROOT))

from scripts.check_house_law_registry import (  # noqa: E402
    _load_workflow_jobs,
    pass_c_wiring as _pass_c,
)
from scripts.workflow_run_source import WorkflowRunSourceError  # noqa: E402


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT)] + args,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


class TestRegistryIntegration:
    """The real registry must pass all passes against the real repo."""

    def test_real_registry_passes(self):
        result = _run([])
        assert result.returncode == 0, (
            f"check_house_law_registry.py exited {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        # Should print a PASS summary line
        assert "house-law registry OK" in result.stdout, (
            f"Expected 'house-law registry OK' in output, got:\n{result.stdout}"
        )

    def test_summary_contains_counts(self):
        result = _run([])
        assert result.returncode == 0
        # Summary line format: "house-law registry OK — N laws, M enforced in CI, K discipline/spurious-only"
        assert "laws" in result.stdout
        assert "enforced in CI" in result.stdout


class TestSelftest:
    """--selftest flag must pass."""

    def test_selftest_passes(self):
        result = _run(["--selftest"])
        assert result.returncode == 0, (
            f"--selftest exited {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        assert "selftest OK" in result.stdout, (
            f"Expected 'selftest OK' in output, got:\n{result.stdout}"
        )


class TestDocsIdempotency:
    """--emit-docs regenerating into a tempfile must equal the committed docs file byte-for-byte."""

    def test_emit_docs_idempotent(self):
        assert COMMITTED_DOCS.exists(), (
            f"Committed docs file {COMMITTED_DOCS} does not exist — "
            f"run `python3 scripts/check_house_law_registry.py --emit-docs` first"
        )

        committed_text = COMMITTED_DOCS.read_text()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, prefix="house_law_docs_test_"
        ) as f:
            tmp_path = f.name

        try:
            result = _run(["--emit-docs", tmp_path])
            assert result.returncode == 0, (
                f"--emit-docs exited {result.returncode}\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )

            regenerated_text = Path(tmp_path).read_text()
            # Strip the date line before comparing (it changes daily)
            # The last line contains the generation date; strip it for idempotency
            def strip_date_line(text: str) -> str:
                lines = text.splitlines()
                # Remove lines that contain _Generated YYYY-MM-DD
                return "\n".join(
                    line for line in lines
                    if "_Generated " not in line
                )

            committed_stripped = strip_date_line(committed_text)
            regenerated_stripped = strip_date_line(regenerated_text)

            assert committed_stripped == regenerated_stripped, (
                "Regenerated docs do not match committed docs (ignoring date line).\n"
                "Run `python3 scripts/check_house_law_registry.py --emit-docs` to update.\n"
                f"First difference at character "
                f"{_first_diff_pos(committed_stripped, regenerated_stripped)}"
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_emit_docs_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = str(Path(tmpdir) / "subdir" / "test_docs.md")
            result = _run(["--emit-docs", out_path])
            assert result.returncode == 0
            assert Path(out_path).exists(), f"docs file not created at {out_path}"
            content = Path(out_path).read_text()
            assert "AUTO-GENERATED" in content
            assert "House Law CI Guard Suite" in content

    def test_emit_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = str(Path(tmpdir) / "registry.json")
            result = _run(["--emit-json", out_path])
            assert result.returncode == 0
            import json
            data = json.loads(Path(out_path).read_text())
            assert isinstance(data, list)
            assert len(data) > 0
            # Each entry should have law_id
            assert all("law_id" in e for e in data)


class TestWiringCensusSeesThroughExtraction:
    """MUTATION-grade: a hard law wired ONLY inside an extracted script body.

    The 512KB-cap diet (PR #5431) moved four ``run: |`` bodies out of daily.yml
    into ``scripts/ci/daily_*.sh``. Pass C reads step ``run:`` bodies to prove a
    registered guard is actually invoked, so an extracted body makes every guard
    inside it read as UNWIRED. The heal shipped at the time plumbed the one
    affected module back into the YAML as a validated argument — that fixed the
    single law and left the NEXT extraction to red again. This pins the general
    property instead: the census resolves the indirection, so a module that
    appears nowhere in the workflow text still satisfies wiring.

    The negative case is what makes this a pin rather than a tautology — drop the
    provenance marker and the census must RAISE, never quietly report the law
    unwired (a finding a future session would "fix" by weakening the registry).
    """

    WF = """\
name: synthetic
on:
  push:
jobs:
  engine:
    runs-on: ubuntu-latest
    steps:
      - name: inline builder
        run: |
          python -m scripts.build_inline_thing
      - name: extracted band
        run: bash scripts/ci/daily_extracted.sh
"""

    SCRIPT = (
        "#!/usr/bin/env bash\n"
        "# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml\n"
        "set -e\n"
        "python -m scripts.check_synthetic_hard_law\n"
    )

    LAW_ID = "synthetic.extracted_wiring"

    def _build(self, tmp_path: Path, script_text: str) -> Path:
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "synthetic.yml").write_text(self.WF)
        ci_dir = tmp_path / "scripts" / "ci"
        ci_dir.mkdir(parents=True)
        (ci_dir / "daily_extracted.sh").write_text(script_text)
        (tmp_path / "scripts" / "check_synthetic_hard_law.py").write_text(
            "# --selftest\ndef main(): pass\n"
        )
        return tmp_path

    def _checks(self) -> list[dict]:
        return [
            {
                "law_id": self.LAW_ID,
                "summary": "A hard law invoked only from an extracted body",
                "source_ref": ["scripts/check_synthetic_hard_law.py"],
                "severity": "hard",
                "check_script": "scripts/check_synthetic_hard_law.py",
                "ci_wiring": [
                    {
                        "workflow": ".github/workflows/synthetic.yml",
                        "job": "engine",
                        "lane": "scheduled",
                    }
                ],
                "selftest": True,
                "allowlist": None,
                "ratchet": None,
                "known_limits": [],
                "owner_program": "test",
            }
        ]

    def test_module_only_in_the_extracted_script_satisfies_wiring(self, tmp_path):
        root = self._build(tmp_path, self.SCRIPT)
        # The guarantee is non-vacuous only while the module is absent from the YAML.
        assert "check_synthetic_hard_law" not in self.WF

        findings: list[str] = []
        _pass_c(self._checks(), root, findings)
        assert findings == [], (
            "the wiring census went blind to a guard invoked from an extracted "
            f"script body: {findings}"
        )

    def test_unresolvable_extraction_raises_instead_of_reporting_unwired(
        self, tmp_path
    ):
        root = self._build(
            tmp_path, self.SCRIPT.replace("# EXTRACTED-VERBATIM-FROM:", "# from:")
        )
        findings: list[str] = []
        with pytest.raises(WorkflowRunSourceError):
            _pass_c(self._checks(), root, findings)

    def test_live_daily_yml_keeps_the_delegated_theme_graph_law_wired(self):
        """The real case the argument plumbing was standing in for.

        ``scripts.check_theme_graph_contracts`` is invoked from inside
        ``scripts/ci/daily_engine_regional_desk_builders.sh`` and appears nowhere
        in daily.yml. If this reds, the seam broke — do NOT re-add an argument to
        the invocation line to paper over it.
        """
        daily = (REPO_ROOT / ".github" / "workflows" / "daily.yml").read_text()
        assert "check_theme_graph_contracts" not in daily, (
            "daily.yml names the delegated guard again — the census would then "
            "pass for the wrong reason and stop pinning the extraction seam"
        )
        jobs = _load_workflow_jobs(
            REPO_ROOT / ".github" / "workflows" / "daily.yml", REPO_ROOT
        )
        assert "check_theme_graph_contracts" in jobs["engine"]


def _first_diff_pos(a: str, b: str) -> int:
    for i, (ca, cb) in enumerate(zip(a, b)):
        if ca != cb:
            return i
    return min(len(a), len(b))


# ── The census must itself run in the gate that blocks a merge ────────────────

MANIFEST = REPO_ROOT / ".github" / "ci" / "legacy-jobs.yml"
REGISTRY = REPO_ROOT / "config" / "house_law_checks.yml"


def _yaml(path: Path) -> dict:
    import yaml

    return yaml.safe_load(path.read_text())


class TestCensusRunsInTheMergeGate:
    """The defect the 2026-09-28 backfill existed to repair.

    Ten ``scripts/check_*.py`` files sat unregistered in ``origin/main`` — which
    pass B calls a HARD finding with the text "before merging" — while main's CI
    was green. The reason was NOT scope inference (measured: the job's derived
    scope already covers ``scripts/**``). The job carried ``gate: data``, and
    ``ci.yml`` plans ``--gate code`` only, so ``load_legacy_jobs(gate="code")``
    dropped the job from the manifest before any path decision was taken — the
    job appeared in neither the eligible nor the skipped list.

    A ``gate: data`` job runs only in ``data-health.yml``, whose triggers are
    ``workflow_run`` / ``workflow_dispatch`` / ``schedule`` — never
    ``pull_request``. So the guard that says "before merging" could not block a
    merge, and a new check script joined nothing.
    """

    GLOB = "scripts/check_*.py"
    CENSUS = "scripts/check_house_law_registry.py"

    def _code_gated_census_jobs(self) -> dict[str, dict]:
        jobs = _yaml(MANIFEST)["jobs"]
        return {
            job_id: job
            for job_id, job in jobs.items()
            if job.get("gate") == "code"
            and any(
                self.CENSUS in str(step.get("run") or "")
                for step in (job.get("steps") or [])
            )
        }

    def test_a_code_gated_job_executes_the_census(self):
        owners = self._code_gated_census_jobs()
        assert owners, (
            "no `gate: code` job in .github/ci/legacy-jobs.yml executes "
            f"{self.CENSUS} in a run: step. ci.yml plans --gate code only, so "
            "the census is then dark on every pull request and an unregistered "
            "check script merges clean — exactly the 2026-09-28 defect."
        )

    def test_the_owning_job_declares_the_runtime_glob(self):
        """The load-bearing path row.

        Pass B globs ``scripts/check_*.py`` AT RUNTIME. A declared scope is
        UNIONed with ``infer_job_scopes``, and inference today reaches
        ``scripts/**`` only as a side effect of opaque-traversal widening in this
        job's other commands — accidental coverage that a future narrowing of
        the guard would silently remove. Declaring the glob makes the selection
        of this job by a brand-new check script a stated property.
        """
        owners = self._code_gated_census_jobs()
        assert any(
            self.GLOB in (job.get("paths") or []) for job in owners.values()
        ), (
            f"no `gate: code` job executing the census declares {self.GLOB!r} in "
            f"its paths: — candidates were {sorted(owners)}"
        )

    def test_a_brand_new_check_script_selects_that_job(self):
        """End-to-end through the real planner, not through the YAML text."""
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import run_ci_pack as PACK  # noqa: N812

        jobs = PACK.load_legacy_jobs(MANIFEST, gate="code")
        selected, reason = PACK.select_jobs(jobs, ["scripts/check_brand_new_guard.py"])
        owners = set(self._code_gated_census_jobs())
        assert owners & {job.job_id for job in selected}, (
            "a newly added scripts/check_*.py selects no census-executing "
            f"code-gate job (owners={sorted(owners)}): {reason}"
        )

    def test_the_data_gate_is_never_reachable_from_a_pull_request(self):
        """Why a `gate: data` home cannot be a merge gate — pinned, not assumed."""
        import yaml

        pack_workflows = sorted(
            p
            for p in (REPO_ROOT / ".github" / "workflows").glob("*.yml")
            if "--gate data" in p.read_text()
        )
        assert pack_workflows, "no workflow plans --gate data at all"
        for path in pack_workflows:
            doc = yaml.safe_load(path.read_text())
            triggers = doc.get(True) or doc.get("on") or {}
            names = set(triggers) if isinstance(triggers, dict) else {triggers}
            assert "pull_request" not in names, (
                f"{path.name} plans --gate data on a pull_request trigger; the "
                "registry's lane vocabulary and this suite both assume the data "
                "gate is scheduled-only"
            )


class TestLanePrCiIsNotSelfEvident:
    """`lane:` is prose. This ratchets the measured population of false claims.

    Pass C proves a named job INVOKES a script. Nothing proves that job runs in
    the lane the entry claims, so a `lane: pr_ci` row on a `gate: data` job
    reads as PR-enforced while being dark on every pull request. Measured
    2026-09-28 against this registry: 27 such rows across 26 laws, none of them
    in the house-law family after this PR.

    Repairing those 27 is NOT this suite's job — each belongs to another owner
    program, and the honest repair for some of them is a re-gating, not a
    relabelling. What this pins is that the population may only SHRINK: a new
    false `lane: pr_ci` row reds here with the law named.
    """

    #: law_id -> job_id, measured 2026-09-28. Remove a row when it is repaired;
    #: never add one.
    KNOWN_DARK_PR_CI_ROWS = {
        ("contracts.artifact_drift", "contract-drift"),
        ("contracts.reliability_contract", "trial-budgets"),
        ("cycles.cross_page_consistency", "cycle-consistency"),
        ("data.ohlc_basis_coherence", "ohlc-basis-coherence"),
        ("design.system_ratchet", "validated-claims"),
        ("epistemics.badge_passport", "outcome-spine"),
        ("epistemics.no_literal_ntrials", "trial-budgets"),
        ("epistemics.trial_registration", "trial-budgets"),
        ("epistemics.validated_claims", "validated-claims"),
        ("flow_continuity.statement_tape_schema", "engine-render-guards"),
        ("governance.private_boundary", "private-boundary"),
        ("metabolism.blocklist_drift", "capability-broker"),
        ("metabolism.capability_redline", "capability-broker"),
        ("nw.entity_thesis_registry", "neural-web"),
        ("nw.evidence_clock_display_only", "evidence-clock"),
        ("ops.government_revenue_amount_semantics", "unrun-government-revenue"),
        ("theme_graph.edge_contract", "unrun-intl-libraries"),
        ("ui.hub_a11y", "hub-a11y"),
        ("ui.inline_js_parses", "inline-js"),
        ("ui.interfonts_theme_sync", "template-site-sync"),
        ("ui.ms_board_coherence", "ms-board-coherence"),
        ("ui.nav_gap", "nav-gap"),
        ("ui.nav_mega", "nav-mega"),
        ("ui.site_js_parses", "inline-js"),
        ("ui.template_site_sync", "template-site-sync"),
        ("ui.title_i18n", "title-i18n"),
        ("ci.vintage_pin_fence", "vintage-pin-fence"),
    }

    def _dark_rows(self) -> set[tuple[str, str]]:
        jobs = _yaml(MANIFEST)["jobs"]
        dark: set[tuple[str, str]] = set()
        for entry in _yaml(REGISTRY)["checks"]:
            for row in entry.get("ci_wiring") or []:
                if row.get("lane") != "pr_ci":
                    continue
                job = jobs.get(row.get("job"))
                if job is not None and job.get("gate") != "code":
                    dark.add((entry["law_id"], row["job"]))
        return dark

    def test_no_new_dark_pr_ci_row(self):
        new = self._dark_rows() - self.KNOWN_DARK_PR_CI_ROWS
        assert not new, (
            "a registry row claims `lane: pr_ci` on a job that is not "
            f"`gate: code`, so it cannot run on a pull request: {sorted(new)}. "
            "ci.yml plans --gate code only. Either move the law onto a "
            "code-gated job or label the lane `scheduled` — do not widen the "
            "allowlist above."
        )

    def test_the_house_law_family_is_clean(self):
        """The three rows this PR repaired must not regress."""
        dark = self._dark_rows()
        offenders = {row for row in dark if row[1].startswith("house-law-registry")}
        assert not offenders, (
            f"the meta-guard's own family claims a dark pr_ci lane again: {sorted(offenders)}"
        )

    def test_the_allowlist_has_no_stale_rows(self):
        """A repaired row must be deleted from the allowlist, not left behind."""
        stale = self.KNOWN_DARK_PR_CI_ROWS - self._dark_rows()
        assert not stale, (
            "these rows are no longer dark — delete them from "
            f"KNOWN_DARK_PR_CI_ROWS: {sorted(stale)}"
        )


class TestSelftestTruthReadsTheFlagNotTheProse:
    """Pass D must not read a docstring's "self-tests" as a selftest flag.

    ``scripts/check_macro_anon_dependency.py`` exposes only ``--root`` and says
    "is how tests/test_macro_anon_dependency_guard.py self-tests it" in a
    docstring. Under a bare-substring predicate its honest ``selftest: false``
    became a HARD finding whose only cure was writing ``selftest: true`` about a
    flag that does not exist — a pass that can be satisfied only by a false
    entry, in the registry whose entire purpose is honesty.
    """

    ENTRY = {
        "law_id": "synthetic.prose_only",
        "check_script": "scripts/check_prose_only.py",
        "selftest": False,
    }

    def _root(self, tmp_path: Path, body: str) -> Path:
        (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
        (tmp_path / "scripts" / "check_prose_only.py").write_text(body)
        return tmp_path

    def test_prose_does_not_make_selftest_false_a_finding(self, tmp_path):
        from scripts.check_house_law_registry import pass_d_selftest_truth

        root = self._root(
            tmp_path,
            '"""A guard whose suite self-tests it."""\n'
            "import argparse\n"
            "argparse.ArgumentParser().add_argument('--root')\n",
        )
        findings: list[str] = []
        pass_d_selftest_truth([dict(self.ENTRY)], root, findings)
        assert findings == [], (
            "prose was read as a selftest flag, so an honest `selftest: false` "
            f"is a hard finding: {findings}"
        )

    def test_a_real_flag_still_makes_selftest_false_a_finding(self, tmp_path):
        """Non-vacuity: the pass still catches a registry entry that under-claims."""
        from scripts.check_house_law_registry import pass_d_selftest_truth

        root = self._root(
            tmp_path,
            "import argparse\n"
            "argparse.ArgumentParser().add_argument('--selftest')\n",
        )
        findings: list[str] = []
        pass_d_selftest_truth([dict(self.ENTRY)], root, findings)
        assert len(findings) == 1 and "selftest=false" in findings[0], findings

    def test_a_missing_flag_still_makes_selftest_true_a_finding(self, tmp_path):
        from scripts.check_house_law_registry import pass_d_selftest_truth

        root = self._root(tmp_path, '"""It self-tests, honestly."""\n')
        entry = dict(self.ENTRY, selftest=True)
        findings: list[str] = []
        pass_d_selftest_truth([entry], root, findings)
        assert len(findings) == 1 and "selftest=true" in findings[0], findings

    def test_the_live_registry_entry_stays_honest(self):
        """The real case: honest false, and the script really has no flag."""
        script = REPO_ROOT / "scripts" / "check_macro_anon_dependency.py"
        text = script.read_text()
        assert "--selftest" not in text and "--self-test" not in text, (
            "check_macro_anon_dependency.py grew a selftest flag — flip its "
            "registry entry to selftest: true and delete this pin"
        )
        assert "self-test" in text or "self-tests" in text, (
            "the prose that made this a trap is gone; the pin above is now "
            "vacuous for this script (the synthetic cases still hold)"
        )
        entry = next(
            e
            for e in _yaml(REGISTRY)["checks"]
            if e.get("check_script") == "scripts/check_macro_anon_dependency.py"
        )
        assert entry["selftest"] is False
