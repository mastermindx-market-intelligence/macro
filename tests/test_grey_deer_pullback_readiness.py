"""Synthetic tests for the Grey Deer pullback readiness-floor reporter.

No price store, no network, no ``data/`` tree. Session dates come from
``lib.nyse_calendar``. Outcome placement is deliberate. Numpy draws, where
used, are seeded.

Run:
    python3 -m pytest tests/test_grey_deer_pullback_readiness.py -rA -q
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import nyse_calendar  # noqa: E402
import scripts.research.grey_deer_pullback_readiness as reporter  # noqa: E402
import scripts.research.grey_deer_pullback_stage1 as s1  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "research" / "grey_deer_pullback_readiness.py"
RNG = np.random.default_rng(20261013)

ISSUE_SCHEMA = "grey_deer_pullback_forward_issue.v1"
GRADE_SCHEMA = "grey_deer_pullback_forward_grade.v1"
BLOCKED = "underpowered/blocked claim"
MET = "floors_met"


def _take_sessions(n: int, start: date = date(2023, 1, 3)) -> list[date]:
    found = nyse_calendar.sessions_between(start, start + timedelta(days=n * 3 + 14))
    assert len(found) >= n
    return found[:n]


def _dumps(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _write_jsonl(path: Path, lines: list[bytes]) -> None:
    payload = b"\n".join(lines)
    if lines:
        payload += b"\n"
    path.write_bytes(payload)


def _make_issue(asof: date, **overrides: object) -> dict:
    row: dict = {
        "schema": ISSUE_SCHEMA,
        "evidence_class": "GENUINELY_ISSUED",
        "writer_lane": "nightly",
        "backfill": False,
        "rerun": False,
        "intraday": False,
        "asof": asof.isoformat(),
        "ticker": "SPY",
        "horizon": 5,
        "config_id": "M3-ALL@C=1.0",
        "abstention_reason": None,
        "prereg_blob": "blob-1",
        "recipe_fingerprint": "fp-1",
        "realized_A": None,
        "Y": None,
        "graded_at": None,
        "grader_sha": None,
    }
    row.update(overrides)
    return row


def _make_grade(issue_line: bytes, issue: dict, **overrides: object) -> dict:
    row: dict = {
        "schema": GRADE_SCHEMA,
        "asof": issue["asof"],
        "ticker": issue["ticker"],
        "horizon": issue["horizon"],
        "config_id": issue["config_id"],
        "issue_line_sha256": hashlib.sha256(issue_line).hexdigest(),
        "prereg_blob": issue["prereg_blob"],
        "Y": 0,
        "revision_flag": False,
    }
    row.update(overrides)
    return row


def _write_logs(directory: Path, issues: list[dict], grades: list[dict]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    _write_jsonl(directory / "forward_log.jsonl", [_dumps(row) for row in issues])
    _write_jsonl(directory / "forward_log_graded.jsonl", [_dumps(row) for row in grades])


def _paired(issues: list[dict], outcomes: list[int]) -> tuple[list[dict], list[dict]]:
    grades: list[dict] = []
    for issue, outcome in zip(issues, outcomes, strict=True):
        line = _dumps(issue)
        grades.append(_make_grade(line, issue, Y=int(outcome)))
    return issues, grades


def _hashes(directory: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            found[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


def _cell(payload: dict, *, fingerprint: str = "fp-1", horizon: int = 5, family: str = "binary") -> dict:
    cohorts = [row for row in payload["cohorts"] if row["recipe_fingerprint"] == fingerprint]
    assert len(cohorts) == 1
    cells = [
        row for row in cohorts[0]["cells"]
        if row["horizon"] == horizon and row["family"] == family
    ]
    assert len(cells) == 1
    return cells[0]


def _direct_honest(asofs: list[date], y: np.ndarray, h: int) -> dict:
    """Call ``s1.honest_n`` on the NYSE session axis, matching the reporter."""
    ordinals = nyse_calendar.session_ordinals(list(asofs))
    assert all(item is not None for item in ordinals)
    calendar = [day.isoformat() for day in nyse_calendar.sessions_between(asofs[0], asofs[-1])]
    return s1.honest_n(
        np.asarray(ordinals, dtype=int),
        np.asarray(y) == 1,
        calendar,
        h,
    )


def _zero_excluded() -> dict[str, int]:
    return {
        "malformed_grade": 0,
        "malformed_issue": 0,
        "non_issued_rows": 0,
        "orphan_grade": 0,
    }


def test_t1_absent_logs_are_empty(tmp_path: Path) -> None:
    missing = tmp_path / "no-such-logs"
    payload = reporter.readiness(missing)
    assert payload["schema"] == reporter.SCHEMA
    assert payload["cohorts"] == []
    assert payload["excluded"] == _zero_excluded()
    assert payload["note"] == reporter.NOTE
    assert "adjudication" in payload["note"]
    assert not missing.exists()

    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "forward_log.jsonl").write_bytes(b"")
    (empty / "forward_log_graded.jsonl").write_bytes(b"")
    assert reporter.readiness(empty)["cohorts"] == []
    assert reporter.readiness(empty)["excluded"] == _zero_excluded()

    proc = subprocess.run(
        [
            sys.executable, "-m", "scripts.research.grey_deer_pullback_readiness",
            "--log-dir", str(missing),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    cli_payload = json.loads(proc.stdout)
    assert cli_payload["cohorts"] == []
    assert cli_payload["excluded"] == _zero_excluded()
    assert not missing.exists()


def test_t2_below_floors(tmp_path: Path) -> None:
    days = _take_sessions(100)
    # First 25 sessions are one tight event run. The rest are non-events.
    y = np.zeros(len(days), dtype=int)
    y[:25] = 1
    y += RNG.integers(0, 1, size=len(days))
    issues = [_make_issue(day) for day in days]
    issue_rows, grade_rows = _paired(issues, [int(v) for v in y])
    log_dir = tmp_path / "logs"
    _write_logs(log_dir, issue_rows, grade_rows)

    payload = reporter.readiness(log_dir)
    assert payload["excluded"] == _zero_excluded()
    cohort = payload["cohorts"]
    assert len(cohort) == 1
    assert len(cohort[0]["cells"]) == len(s1.HORIZONS) * len(reporter.FAMILIES)

    cell = _cell(payload)
    direct = _direct_honest(days, y, 5)
    span = (days[-1] - days[0]).days
    assert cell["issued_sessions"] == 100
    assert cell["abstained_sessions"] == 0
    assert cell["span_days"] == span
    assert cell["graded"] == 100
    assert cell["events"] == 25
    assert cell["non_events"] == 75
    assert cell["clusters"] == direct["clusters"] == 1
    assert cell["episodes"] == direct["episodes"] == 1
    assert cell["event_months"] == direct["event_months"] == 2
    assert cell["revision_flagged"] == 0
    assert cell["revision_flag_null"] == 0

    expect_met = {
        "issued_sessions": False,
        "span_days": False,
        "graded": False,
        "events": True,
        "non_events": True,
        "clusters": False,
        "episodes": False,
        "event_months": False,
    }
    assert span < reporter.FLOORS["span_days"]
    for name, met in expect_met.items():
        floor = cell["floors"][name]
        assert floor["min"] == reporter.FLOORS[name]
        assert floor["value"] == cell[name]
        assert floor["met"] is met
        assert floor["met"] is (floor["value"] >= floor["min"])
    assert cell["all_met"] is False
    assert cell["verdict"] == BLOCKED

    for horizon in (10, 21):
        other = _cell(payload, horizon=horizon)
        assert other["issued_sessions"] == 0
        assert other["graded"] == 0
        assert other["verdict"] == BLOCKED
        assert other["all_met"] is False
    quantile = _cell(payload, family="quantile")
    assert quantile["issued_sessions"] == 0
    assert quantile["graded"] == 0
    assert quantile["verdict"] == BLOCKED


def test_t3_meets_floors(tmp_path: Path) -> None:
    h = 5
    n = 320
    days = _take_sessions(n)
    # A companion sits one session after each anchor, so the next anchor has to
    # clear EPISODE_PRE + h beyond that companion or the episode windows merge.
    step = s1.EPISODE_PRE + h + 2
    anchors = [i * step for i in range(s1.POWER_MIN_EPISODES + 2)]
    assert len(anchors) == 12
    assert anchors[-1] + 2 < n
    positions = []
    for anchor in anchors:
        positions.append(anchor)
        positions.append(anchor + 1)
    positions.append(anchors[-1] + 2)
    assert len(positions) == 25
    y = np.zeros(n, dtype=int)
    y[np.asarray(positions, dtype=int)] = 1
    assert int(y.sum()) == 25
    assert int(RNG.integers(0, 1)) == 0

    issues: list[dict] = []
    grades: list[dict] = []
    for config_id in ("M3-ALL@C=1.0", "Q3-ALL"):
        config_issues = [_make_issue(day, config_id=config_id) for day in days]
        paired_issues, paired_grades = _paired(config_issues, [int(v) for v in y])
        issues.extend(paired_issues)
        grades.extend(paired_grades)
    log_dir = tmp_path / "logs"
    _write_logs(log_dir, issues, grades)

    payload = reporter.readiness(log_dir)
    assert payload["excluded"] == _zero_excluded()
    assert len(payload["cohorts"]) == 1
    order = [(cell["horizon"], cell["family"]) for cell in payload["cohorts"][0]["cells"]]
    assert order == [(horizon, family) for horizon in s1.HORIZONS for family, _cid in reporter.FAMILIES]

    direct = _direct_honest(days, y, h)
    span = (days[-1] - days[0]).days
    assert span >= 300
    assert direct["episodes"] == 12
    assert direct["clusters"] == 12
    assert direct["event_months"] >= s1.POWER_MIN_MONTHS
    for family in ("binary", "quantile"):
        cell = _cell(payload, family=family, horizon=h)
        assert cell["config_id"] == dict(reporter.FAMILIES)[family]
        assert cell["issued_sessions"] == n
        assert cell["abstained_sessions"] == 0
        assert cell["span_days"] == span
        assert cell["graded"] == n
        assert cell["events"] == 25
        assert cell["non_events"] == n - 25
        assert cell["clusters"] == direct["clusters"]
        assert cell["episodes"] == direct["episodes"]
        assert cell["event_months"] == direct["event_months"]
        assert cell["episodes"] == s1.honest_n(
            np.asarray(nyse_calendar.session_ordinals(list(days)), dtype=int),
            y == 1,
            [day.isoformat() for day in nyse_calendar.sessions_between(days[0], days[-1])],
            h,
        )["episodes"]
        assert cell["all_met"] is True
        assert cell["verdict"] == MET
        for name, floor in cell["floors"].items():
            assert floor["met"] is True
            assert floor["value"] >= floor["min"]
            assert floor["min"] == reporter.FLOORS[name]
    for horizon in (10, 21):
        for family in ("binary", "quantile"):
            cell = _cell(payload, horizon=horizon, family=family)
            assert cell["issued_sessions"] == 0
            assert cell["graded"] == 0
            assert cell["verdict"] == BLOCKED
            assert cell["all_met"] is False


def test_t3_session_index_not_graded_position(tmp_path: Path) -> None:
    """Two graded rows, 40 sessions apart, are two clusters at h=5.

    Positional indices into the graded pair would be 0 and 1 and would merge.
    """
    days = _take_sessions(41)
    graded_days = [days[0], days[40]]
    ordinals = nyse_calendar.session_ordinals(graded_days)
    assert ordinals == [0, 40]
    y = np.ones(2, dtype=int)
    issues = [_make_issue(day) for day in graded_days]
    issue_rows, grade_rows = _paired(issues, [int(v) for v in y])
    log_dir = tmp_path / "logs"
    _write_logs(log_dir, issue_rows, grade_rows)

    cell = _cell(reporter.readiness(log_dir))
    direct = _direct_honest(graded_days, y, 5)
    assert direct["clusters"] == 2
    assert direct["episodes"] == 2
    assert cell["clusters"] == direct["clusters"]
    assert cell["episodes"] == direct["episodes"]
    assert cell["event_months"] == direct["event_months"]
    assert cell["events"] == 2
    assert cell["graded"] == 2


def test_t4_exclusions(tmp_path: Path) -> None:
    days = _take_sessions(16)
    issues: list[dict] = [
        _make_issue(days[0]),
        _make_issue(days[1]),
        _make_issue(days[2]),
        _make_issue(days[3], abstention_reason="FIT_NONCONVERGENCE"),
        _make_issue(days[5], config_id="B0"),
    ]
    grade_flags: list[tuple[object, object]] = [
        (1, True),
        (1, None),
        (0, False),
        (1, False),
        (1, False),
    ]
    grades: list[dict] = []
    issue_lines = [_dumps(row) for row in issues]
    for line, issue, (outcome, flag) in zip(issue_lines, issues, grade_flags, strict=True):
        grades.append(_make_grade(line, issue, Y=outcome, revision_flag=flag))

    rejected_specs = [
        {"backfill": True},
        {"rerun": True},
        {"intraday": True},
        {"writer_lane": "intraday"},
        {"evidence_class": "REPLAY"},
        {"schema": "not-the-issue-schema"},
        {"Y": 1},
    ]
    for offset, spec in enumerate(rejected_specs, start=6):
        issues.append(_make_issue(days[offset], **spec))

    orphan = _make_grade(issue_lines[0], issues[0], Y=1, revision_flag=False)
    orphan["issue_line_sha256"] = "0" * 64
    grades.append(orphan)

    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    raw_issues = issue_lines + [_dumps(row) for row in issues[5:]] + [b"not-json"]
    raw_grades = [_dumps(row) for row in grades] + [b"{not-json"]
    _write_jsonl(log_dir / "forward_log.jsonl", raw_issues)
    _write_jsonl(log_dir / "forward_log_graded.jsonl", raw_grades)

    payload = reporter.readiness(log_dir)
    assert payload["excluded"] == {
        "malformed_grade": 1,
        "malformed_issue": 1,
        "non_issued_rows": len(rejected_specs),
        "orphan_grade": 1,
    }
    assert len(payload["cohorts"]) == 1
    config_ids = {cell["config_id"] for cell in payload["cohorts"][0]["cells"]}
    assert config_ids == {"M3-ALL@C=1.0", "Q3-ALL"}
    assert "B0" not in config_ids

    cell = _cell(payload)
    assert cell["issued_sessions"] == 3
    assert cell["abstained_sessions"] == 1
    assert cell["span_days"] == (days[2] - days[0]).days
    assert cell["revision_flagged"] == 1
    assert cell["revision_flag_null"] == 1
    assert cell["graded"] == 2
    assert cell["events"] == 1
    assert cell["non_events"] == 1
    assert cell["clusters"] == 1
    assert cell["episodes"] == 1
    assert cell["event_months"] == 1
    assert cell["verdict"] == BLOCKED

    quantile = _cell(payload, family="quantile")
    assert quantile["issued_sessions"] == 0
    assert quantile["graded"] == 0
    assert quantile["events"] == 0


def test_t5_cohorts_do_not_pool(tmp_path: Path) -> None:
    days = _take_sessions(4)
    issues: list[dict] = []
    grades: list[dict] = []
    for fingerprint, count in (("fp-a", 2), ("fp-b", 4)):
        group = [
            _make_issue(days[i], recipe_fingerprint=fingerprint, prereg_blob="blob-shared")
            for i in range(count)
        ]
        paired_issues, paired_grades = _paired(group, [0] * count)
        issues.extend(paired_issues)
        grades.extend(paired_grades)
    log_dir = tmp_path / "logs"
    _write_logs(log_dir, issues, grades)

    payload = reporter.readiness(log_dir)
    assert [row["recipe_fingerprint"] for row in payload["cohorts"]] == ["fp-a", "fp-b"]
    assert {row["prereg_blob"] for row in payload["cohorts"]} == {"blob-shared"}
    short = _cell(payload, fingerprint="fp-a")
    long = _cell(payload, fingerprint="fp-b")
    assert short["issued_sessions"] == 2
    assert short["graded"] == 2
    assert long["issued_sessions"] == 4
    assert long["graded"] == 4
    assert short["events"] == 0
    assert long["events"] == 0
    assert short["verdict"] == BLOCKED
    assert long["verdict"] == BLOCKED


def test_t6_cli_writes_out_and_leaves_log_dir_unchanged(tmp_path: Path) -> None:
    days = _take_sessions(2)
    issues = [_make_issue(day) for day in days]
    issue_rows, grade_rows = _paired(issues, [0, 1])
    log_dir = tmp_path / "logs"
    _write_logs(log_dir, issue_rows, grade_rows)
    before = _hashes(log_dir)
    names_before = sorted(path.name for path in log_dir.iterdir())
    out = tmp_path / "readiness.json"

    proc = subprocess.run(
        [
            sys.executable, "-m", "scripts.research.grey_deer_pullback_readiness",
            "--log-dir", str(log_dir),
            "--out", str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert out.read_text(encoding="utf-8") == proc.stdout
    parsed = json.loads(proc.stdout)
    assert proc.stdout == json.dumps(parsed, sort_keys=True, indent=2) + "\n"
    assert parsed == reporter.readiness(log_dir)
    assert _hashes(log_dir) == before
    assert sorted(path.name for path in log_dir.iterdir()) == names_before
    assert set(names_before) == {"forward_log.jsonl", "forward_log_graded.jsonl"}

    defaults = reporter.build_parser().parse_args([])
    assert defaults.log_dir == Path("data/grey_deer_pullback")
    assert defaults.out is None


def test_unreadable_input_exits_2(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "forward_log.jsonl").mkdir()
    out = tmp_path / "should-not-exist.json"
    with pytest.raises(reporter.ReadinessInputError):
        reporter.readiness(log_dir)
    proc = subprocess.run(
        [
            sys.executable, "-m", "scripts.research.grey_deer_pullback_readiness",
            "--log-dir", str(log_dir),
            "--out", str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2, proc.stderr
    assert not out.exists()


def test_cli_refuses_to_write_inside_log_dir(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    out = log_dir / "readiness.json"
    proc = subprocess.run(
        [
            sys.executable, "-m", "scripts.research.grey_deer_pullback_readiness",
            "--log-dir", str(log_dir),
            "--out", str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1, proc.stderr
    assert not out.exists()
    assert list(log_dir.iterdir()) == []


def test_module_counts_only() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert re.search(r"brier|pinball|skill|auc", source) is None
    assert "s1.honest_n" in source
    assert "event_clusters" not in source
    assert reporter.FLOORS["episodes"] == s1.POWER_MIN_EPISODES
    assert reporter.FLOORS["event_months"] == s1.POWER_MIN_MONTHS
    assert reporter.FLOORS["issued_sessions"] == 252
    assert reporter.FLOORS["span_days"] == 300
    assert reporter.FLOORS["graded"] == 200
    assert reporter.FLOORS["events"] == 20
    assert reporter.FLOORS["non_events"] == 50
    assert reporter.FLOORS["clusters"] == 5
