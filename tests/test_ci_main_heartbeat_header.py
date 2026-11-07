"""The ci-main-heartbeat.yml header must say what the heartbeat's jobs actually run.

Until 2026-11-02 the header read: "Job names + steps mirror ci.yml exactly, so
"green here" means the same thing as "green on the PR gate"". Each heartbeat job is
named after a job in .github/ci/legacy-jobs.yml, the manifest ci.yml's packs run on
pull requests. On main 45ba0510 that day, 8 of the heartbeat's 13 jobs ran fewer test
files than their namesake. workflow-yaml ran 0 of 17, engine-render-guards 79 of 178,
data-base-shim 1 of 9 and template-site-sync 5 of 12. Two of the 8 also ran a file the
namesake does not. A green heartbeat on main was read as the PR gate's green, but it
checked less.

This suite measures each heartbeat job against its namesake and holds the header's
words to that measure, both ways:

- while any job leaves out a file its namesake runs, or has no namesake, the header
  must say so with FEWER_WORDS;
- once no job does, the header must drop FEWER_WORDS;
- while any job's file set differs from its namesake's, the header must not claim
  equivalence (EQUIVALENCE_CLAIMS);
- while any job lacks a namesake, the header must not say every job has one;
- the comment banner directly above a job that differs from its namesake may not call
  that job a mirror.

The fix for a failure here is either to change the words or to make the jobs match.
Never edit this suite to fit.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
HEARTBEAT = ROOT / ".github" / "workflows" / "ci-main-heartbeat.yml"
MANIFEST = ROOT / ".github" / "ci" / "legacy-jobs.yml"

# Same shape as tests/test_ci_pack.py's _TEST_PATH_RE: a tests/*.py path not glued to
# a longer word or path on its left.
TEST_PATH_RE = re.compile(r"(?<![\w/-])(tests/[A-Za-z0-9_][A-Za-z0-9_./-]*\.py)")
TOP_LEVEL_ON_RE = re.compile(r"""^(?:on|"on"|'on')\s*:""", re.MULTILINE)
MIRROR_RE = re.compile(r"\bmirror", re.IGNORECASE)

NAMESAKE_CLAIM = "each job here takes its name from a job in .github/ci/legacy-jobs.yml"
FEWER_WORDS = (
    "some jobs here run fewer test files than their namesake",
    "green here covers less than green on the pr gate",
)
EQUIVALENCE_CLAIMS = (
    "mirror ci.yml exactly",
    "means the same thing",
    "same thing as",
)


def job_test_files(job: dict) -> set[str]:
    """Every tests/*.py path any `run:` step of this job names."""
    joined = "\n".join(str(step.get("run") or "") for step in job.get("steps") or [])
    return set(TEST_PATH_RE.findall(joined))


def job_gaps(heartbeat_jobs: dict, manifest_jobs: dict) -> dict[str, dict]:
    """Per heartbeat job whose test files differ from its namesake's: what differs."""
    gaps: dict[str, dict] = {}
    for name, job in heartbeat_jobs.items():
        namesake = manifest_jobs.get(name)
        here = job_test_files(job)
        if namesake is None:
            gaps[name] = {"namesake": False, "left_out": [], "extra": sorted(here)}
            continue
        there = job_test_files(namesake)
        if here != there:
            gaps[name] = {
                "namesake": True,
                "left_out": sorted(there - here),
                "extra": sorted(here - there),
            }
    return gaps


def _normalized(comment_lines: list[str]) -> str:
    words = " ".join(line.strip().lstrip("#") for line in comment_lines)
    return " ".join(words.split()).lower()


def header_text(workflow_text: str) -> str:
    """The comment lines above the top-level `on:` key, joined and lower-cased."""
    found = TOP_LEVEL_ON_RE.search(workflow_text)
    head = workflow_text[: found.start()] if found else workflow_text
    return _normalized([line for line in head.splitlines() if line.lstrip().startswith("#")])


def banner_above(workflow_text: str, job_name: str) -> str:
    """The comment block directly above the `  <job_name>:` key, or '' if none."""
    lines = workflow_text.splitlines()
    key = re.compile(rf"^  {re.escape(job_name)}:\s*$")
    for index, line in enumerate(lines):
        if key.match(line):
            block: list[str] = []
            cursor = index - 1
            while cursor >= 0 and lines[cursor].lstrip().startswith("#"):
                block.append(lines[cursor])
                cursor -= 1
            return "\n".join(reversed(block))
    return ""


def _describe(gaps: dict[str, dict], names: list[str]) -> str:
    rows = []
    for name in names:
        gap = gaps[name]
        if not gap["namesake"]:
            rows.append(f"  {name}: no job of that name in .github/ci/legacy-jobs.yml")
            continue
        left_out = gap["left_out"]
        shown = ", ".join(left_out[:5]) + (f", … ({len(left_out)} in all)" if len(left_out) > 5 else "")
        rows.append(f"  {name}: leaves out {shown or 'nothing'}"
                    + (f"; also runs {', '.join(gap['extra'])}" if gap["extra"] else ""))
    return "\n".join(rows)


def header_findings(workflow_text: str, heartbeat_jobs: dict, manifest_jobs: dict) -> list[str]:
    """Every way the header's words disagree with the measured jobs. Empty means they agree."""
    gaps = job_gaps(heartbeat_jobs, manifest_jobs)
    differing = sorted(gaps)
    fewer = sorted(name for name, gap in gaps.items() if gap["left_out"] or not gap["namesake"])
    header = header_text(workflow_text)
    findings: list[str] = []

    has_fewer_words = all(words in header for words in FEWER_WORDS)
    if fewer and not has_fewer_words:
        findings.append(
            "the header does not say that green here covers less than green on the PR "
            f"gate; it needs both of {list(FEWER_WORDS)}, because:\n" + _describe(gaps, fewer)
        )
    if not fewer and any(words in header for words in FEWER_WORDS):
        findings.append(
            "the header says some jobs here run fewer test files than their namesake, "
            "but every job now runs every file its namesake runs; drop those words"
        )

    claimed = [claim for claim in EQUIVALENCE_CLAIMS if claim in header]
    if differing and claimed:
        findings.append(
            f"the header claims equivalence ({claimed}) while these jobs differ from "
            "their namesake:\n" + _describe(gaps, differing)
        )

    orphans = sorted(name for name, gap in gaps.items() if not gap["namesake"])
    if orphans and NAMESAKE_CLAIM in header:
        findings.append(
            "the header says every job takes its name from a legacy job, but these have "
            f"none: {orphans}"
        )

    for name in differing:
        banner = banner_above(workflow_text, name)
        if MIRROR_RE.search(banner):
            findings.append(
                f"the banner above `{name}` calls it a mirror, but it differs from its "
                "namesake:\n" + _describe(gaps, [name])
            )
    return findings


def _load_jobs(path: Path) -> dict:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return document["jobs"]


def test_the_heartbeat_header_says_what_its_jobs_run() -> None:
    text = HEARTBEAT.read_text(encoding="utf-8")
    findings = header_findings(text, _load_jobs(HEARTBEAT), _load_jobs(MANIFEST))
    assert not findings, (
        "ci-main-heartbeat.yml's words disagree with what its jobs run:\n\n"
        + "\n\n".join(findings)
        + "\n\nChange the words, or make the jobs match their namesakes. The header is "
        "what a reader of a green heartbeat trusts."
    )


def test_the_measure_reads_real_jobs_on_both_sides() -> None:
    """A measure that finds no test files anywhere would agree with any words."""
    heartbeat_jobs, manifest_jobs = _load_jobs(HEARTBEAT), _load_jobs(MANIFEST)
    here = set().union(*(job_test_files(job) for job in heartbeat_jobs.values()))
    there = set().union(*(job_test_files(manifest_jobs[name])
                          for name in heartbeat_jobs if name in manifest_jobs))
    named = [name for name in heartbeat_jobs if name in manifest_jobs]
    assert len(heartbeat_jobs) >= 10 and len(named) >= 10, (len(heartbeat_jobs), named)
    assert len(here) >= 50 and len(there) >= 50, (len(here), len(there))
    missing = sorted(path for path in here | there if not (ROOT / path).exists())
    assert not missing, missing
    assert header_text(HEARTBEAT.read_text(encoding="utf-8")).startswith("─"), (
        "header_text no longer starts at the header's top rule; the measure is reading "
        "the wrong lines"
    )


# ── the rules, on synthetic workflows ─────────────────────────────────────────

_NEW_HEADER = (
    "# SCOPE — Each job here takes its name from a job in\n"
    "# .github/ci/legacy-jobs.yml, but its steps are a separate copy, and some\n"
    "# jobs here run fewer test files than their namesake. So green here covers less than\n"
    "# green on the PR gate, job for job.\n"
)
_OLD_HEADER = (
    "# SCOPE — Job names + steps mirror ci.yml exactly, so \"green here\" means the\n"
    "# same thing as \"green on the PR gate\".\n"
)
_NEUTRAL_HEADER = "# SCOPE — Each job here takes its name from a job in .github/ci/legacy-jobs.yml.\n"


def _workflow(header: str, banners: dict[str, str] | None = None, after_on: str = "") -> str:
    banners = banners or {}
    body = "".join(f"{banners.get(name, '')}  {name}:\n    steps: []\n" for name in ("alpha", "beta"))
    return f"name: hb\n{header}\non:\n  schedule: []\n{after_on}jobs:\n{body}"


def _job(*files: str) -> dict:
    return {"steps": [{"run": f"python -m pytest {' '.join(files)} -q"}] if files else []}


_SAME = ({"alpha": _job("tests/test_a.py"), "beta": _job("tests/test_b.py")},
         {"alpha": _job("tests/test_a.py"), "beta": _job("tests/test_b.py")})
_FEWER = ({"alpha": _job("tests/test_a.py"), "beta": _job("tests/test_b.py")},
          {"alpha": _job("tests/test_a.py", "tests/test_a2.py"), "beta": _job("tests/test_b.py")})
_EXTRA_ONLY = ({"alpha": _job("tests/test_a.py", "tests/test_x.py"), "beta": _job("tests/test_b.py")},
               {"alpha": _job("tests/test_a.py"), "beta": _job("tests/test_b.py")})
_ORPHAN = ({"alpha": _job("tests/test_a.py"), "beta": _job("tests/test_b.py")},
           {"alpha": _job("tests/test_a.py")})


@pytest.mark.parametrize(
    ("label", "text", "jobs", "expected"),
    [
        ("fewer, new words", _workflow(_NEW_HEADER), _FEWER, []),
        ("fewer, old words", _workflow(_OLD_HEADER), _FEWER, ["does not say", "claims equivalence"]),
        ("fewer, new words plus an equivalence claim",
         _workflow(_NEW_HEADER + "# Green here means the same thing as the PR gate.\n"), _FEWER,
         ["claims equivalence"]),
        ("fewer, only half the words",
         _workflow("# Some jobs here run fewer test files than their namesake.\n"), _FEWER,
         ["does not say"]),
        ("same, new words", _workflow(_NEW_HEADER), _SAME, ["drop those words"]),
        ("same, neutral words", _workflow(_NEUTRAL_HEADER), _SAME, []),
        ("same, old words", _workflow(_OLD_HEADER), _SAME, []),
        ("extra file only, neutral words", _workflow(_NEUTRAL_HEADER), _EXTRA_ONLY, []),
        ("extra file only, new words", _workflow(_NEW_HEADER), _EXTRA_ONLY, ["drop those words"]),
        ("extra file only, old words", _workflow(_OLD_HEADER), _EXTRA_ONLY, ["claims equivalence"]),
        ("orphan job, new words", _workflow(_NEW_HEADER), _ORPHAN, ["none: ['beta']"]),
        ("orphan job, no namesake claim",
         _workflow("# Some jobs here run fewer test files than their namesake, so green here\n"
                   "# covers less than green on the PR gate.\n"), _ORPHAN, []),
        ("mirror banner above a differing job",
         _workflow(_NEW_HEADER, {"alpha": "  # ── guard (mirror ci.yml: alpha) ──\n"}), _FEWER,
         ["banner above `alpha`"]),
        ("mirror banner above a matching job",
         _workflow(_NEW_HEADER, {"beta": "  # MIRROR OF legacy-jobs.yml's beta job\n"}), _FEWER, []),
        ("equivalence words below on: are not the header",
         _workflow(_NEW_HEADER, after_on="# steps mirror ci.yml exactly\n"), _FEWER, []),
    ],
)
def test_header_findings_rules(label: str, text: str, jobs: tuple, expected: list[str]) -> None:
    findings = header_findings(text, jobs[0], jobs[1])
    joined = "\n".join(findings)
    if not expected:
        assert findings == [], (label, findings)
        return
    assert len(findings) == len(expected), (label, findings)
    for fragment in expected:
        assert fragment in joined, (label, fragment, findings)


def test_job_gaps_names_left_out_and_extra_files() -> None:
    heartbeat = {"alpha": _job("tests/test_a.py", "tests/test_x.py"), "beta": _job()}
    manifest = {"alpha": _job("tests/test_a.py", "tests/test_a2.py"), "beta": _job()}
    assert job_gaps(heartbeat, manifest) == {
        "alpha": {"namesake": True, "left_out": ["tests/test_a2.py"], "extra": ["tests/test_x.py"]},
    }


def test_job_test_files_ignores_paths_glued_to_a_longer_path() -> None:
    job = {"steps": [{"run": "python -m pytest tests/test_a.py vendor/tests/test_b.py -q"},
                     {"uses": "actions/checkout@v4"}]}
    assert job_test_files(job) == {"tests/test_a.py"}
