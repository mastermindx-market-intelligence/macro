"""Hermetic tests for the Grey Deer EW-P3 forecast reader STUB (tmp_path only).

Proves the five refusal gates in order (prereg section 11.1), the §11.2
earliest-first-look vectors, the trial-ledger registration, the CLI, import
hygiene, and — load-bearing — that gate 3 refuses with ZERO data/ access.
"""
from __future__ import annotations

import builtins
import io
import json
import os
import pathlib
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from scripts import grey_deer_ew_forecast_reader as r

# Verified CAL vectors: (merge, prospective_start, L0). 2026-11-26 is
# Thanksgiving, 2026-11-07 a Saturday; the L0s are pinned by the packet.
VECTORS = [
    (date(2026, 11, 2), date(2026, 11, 3), date(2027, 12, 31)),
    (date(2026, 11, 25), date(2026, 11, 27), date(2027, 12, 31)),
    (date(2026, 11, 7), date(2026, 11, 9), date(2027, 12, 31)),
    (date(2026, 12, 24), date(2026, 12, 28), date(2028, 1, 31)),
    (date(2026, 12, 31), date(2027, 1, 4), date(2028, 2, 29)),
]

# Before every registered L0 (min = 2027-12-31), so gate 3 always fires on it.
EARLY_NOW = datetime(2027, 6, 30, 12, tzinfo=timezone.utc)


def lines(merge, start):
    """A prereg text carrying exactly the two machine lines (values as str)."""
    return f"EW_P3_MERGE_DATE_UTC: {merge}\nEW_P3_PROSPECTIVE_START: {start}\n"


def _forbid_data_opens(monkeypatch):
    """Wrap builtins.open/io.open/os.open/Path.open: record every path and raise
    AssertionError the moment a resolved path has a 'data' component or lies
    under REPO_ROOT/'data'. Returns the recorded-path list."""
    opened = []
    data_root = (r.REPO_ROOT / "data").resolve()
    real_open, real_io_open = builtins.open, io.open
    real_os_open, real_path_open = os.open, pathlib.Path.open

    def _is_data(p):
        rp = Path(p).resolve()
        return "data" in rp.parts or rp == data_root or data_root in rp.parents

    def _guard(p):
        opened.append(p)
        if _is_data(p):
            raise AssertionError(f"a data/ path was opened: {p}")

    def g_open(file, *a, **kw):
        _guard(file)
        return real_open(file, *a, **kw)

    def g_io_open(file, *a, **kw):
        _guard(file)
        return real_io_open(file, *a, **kw)

    def g_os_open(path, flag, *a, **kw):
        _guard(path)
        return real_os_open(path, flag, *a, **kw)

    def g_path_open(self, *a, **kw):
        _guard(self)
        return real_path_open(self, *a, **kw)

    monkeypatch.setattr(builtins, "open", g_open)
    monkeypatch.setattr(io, "open", g_io_open)
    monkeypatch.setattr(os, "open", g_os_open)
    monkeypatch.setattr(pathlib.Path, "open", g_path_open)
    return opened


def _assert_data_opens_empty(opened):
    data_root = (r.REPO_ROOT / "data").resolve()
    bad = [p for p in opened if "data" in Path(p).resolve().parts
           or data_root in Path(p).resolve().parents]
    assert bad == [], f"data/ paths opened: {bad}"


# ── T1: gate 1 — malformed / UNRECORDED machine lines ─────────────────────────

@pytest.mark.parametrize("text", [
    lines("UNRECORDED", "UNRECORDED"),                       # both UNRECORDED
    lines("2026-11-02", "UNRECORDED"),                       # one dated + one UNRECORDED
    lines("UNRECORDED", "2026-11-03"),
    "EW_P3_MERGE_DATE_UTC: 2026-11-02\n",                    # a missing line
    "EW_P3_PROSPECTIVE_START: 2026-11-03\n",
    "EW_P3_MERGE_DATE_UTC: 2026-11-02\n"
    "EW_P3_MERGE_DATE_UTC: 2026-11-02\n"
    "EW_P3_PROSPECTIVE_START: 2026-11-03\n",                 # a duplicated line
    "EW_P3_MERGE_DATE_UTC: 2026-11-02\n"
    "EW_P3_PROSPECTIVE_START: 2026-11-03\n"
    "EW_P3_PROSPECTIVE_START: 2026-11-03\n",                 # duplicated start line
    lines("2026-13-01", "2026-11-03"),                       # malformed month
    lines("2026-11-02", "2026-02-30"),                       # malformed day
])
def test_t1_gate1_prospective_start_unrecorded(text, tmp_path):
    out = r.evaluate(prereg_text=text, now_utc=EARLY_NOW,
                     issue_log_path=tmp_path / "unused.jsonl")
    assert out["refusal"] == "prospective_start_unrecorded"
    assert out["gate"] == 1
    assert out["verdict"] == "NOT_EXECUTABLE"
    assert r.parse_machine_lines(text) is None


# ── T2: the REAL prereg on disk — structure and zero data/ access ─────────────

def test_t2_real_prereg_structure_and_no_data_access(monkeypatch):
    opened = _forbid_data_opens(monkeypatch)
    text = (r.REPO_ROOT / r.PREREG_RELPATH).read_text(encoding="utf-8")
    # Exactly one match of each machine line, dated or not.
    assert len(r.MERGE_LINE_RE.findall(text)) == 1
    assert len(r.START_LINE_RE.findall(text)) == 1
    # The registered data/ issue-log path is never opened on the way to gate 1/3.
    forbidden = r.REPO_ROOT / r.ISSUE_LOG_RELPATH
    out = r.evaluate(now_utc=EARLY_NOW, issue_log_path=forbidden)
    assert out["refusal"] in {"prospective_start_unrecorded", "window_not_elapsed"}
    assert out["verdict"] == "NOT_EXECUTABLE"
    _assert_data_opens_empty(opened)


# ── T3: gate 2 — start must be the first CAL session strictly after merge ─────

@pytest.mark.parametrize("merge,start", [
    ("2026-11-02", "2026-11-04"),
    ("2026-11-25", "2026-11-26"),  # Thanksgiving Thursday is not a session
])
def test_t3_gate2_inconsistent(merge, start, tmp_path):
    out = r.evaluate(prereg_text=lines(merge, start), now_utc=EARLY_NOW,
                     issue_log_path=tmp_path / "unused.jsonl")
    assert out["refusal"] == "prospective_start_inconsistent"
    assert out["gate"] == 2
    assert out["verdict"] == "NOT_EXECUTABLE"


@pytest.mark.parametrize("merge,start,l0", VECTORS)
def test_t3_gate2_vectors_pass(merge, start, l0, tmp_path):
    out = r.evaluate(prereg_text=lines(merge.isoformat(), start.isoformat()),
                     now_utc=EARLY_NOW, issue_log_path=tmp_path / "unused.jsonl")
    assert out["refusal"] == "window_not_elapsed"  # gate 2 passed, gate 3 fired
    assert out["gate"] == 3
    assert out["merge_date"] == merge.isoformat()
    assert out["prospective_start"] == start.isoformat()


# ── T4: gate 3 — ZERO DATA ACCESS (the load-bearing proof) ─────────────────────

def _ny(year, month, day, hour, minute, second=0):
    return datetime(year, month, day, hour, minute, second,
                    tzinfo=r.cal.ET).astimezone(timezone.utc)


def test_t4_gate3_zero_data_access(monkeypatch):
    opened = _forbid_data_opens(monkeypatch)

    def _fail_if_called(*a, **kw):
        raise AssertionError("has_receipted_issue must not run before the window gate passes")

    monkeypatch.setattr(r, "has_receipted_issue", _fail_if_called)

    out = r.evaluate(prereg_text=lines("2026-11-02", "2026-11-03"),
                     now_utc=_ny(2027, 12, 31, 15, 59), issue_log_path=None)
    assert out["refusal"] == "window_not_elapsed"
    assert out["gate"] == 3
    assert out["verdict"] == "NOT_EXECUTABLE"
    assert out["earliest_first_look"] == "2027-12-31"
    assert out["merge_date"] == "2026-11-02"
    assert out["prospective_start"] == "2026-11-03"
    _assert_data_opens_empty(opened)

    # Exactly 16:00:00 NY on L0 is STILL not elapsed — strictly after only.
    out2 = r.evaluate(prereg_text=lines("2026-11-02", "2026-11-03"),
                      now_utc=_ny(2027, 12, 31, 16, 0, 0), issue_log_path=None)
    assert out2["refusal"] == "window_not_elapsed"
    assert out2["gate"] == 3
    _assert_data_opens_empty(opened)


# ── T5: boundary — one second past the 16:00 NY close on L0 ────────────────────

def test_t5_boundary_16_00_01_ny(tmp_path):
    missing = tmp_path / "missing_issue_log.jsonl"
    out = r.evaluate(prereg_text=lines("2026-11-02", "2026-11-03"),
                     now_utc=_ny(2027, 12, 31, 16, 0, 1), issue_log_path=missing)
    assert out["refusal"] == "no_receipted_issue"
    assert out["gate"] == 4
    assert out["earliest_first_look"] == "2027-12-31"


# ── T6: gate 4 — the issue log must carry a receipted issue row ────────────────

def test_t6_gate4_no_receipted_issue(tmp_path):
    log = tmp_path / "issue_log.jsonl"
    log.write_text(
        "\n"                                          # blank line
        "this is not json\n"                          # non-JSON line
        "[1, 2, 3]\n"                                 # a JSON list, not an object
        '{"contract": "some_other.v1", "model_fingerprint": "f00d"}\n'
        '{"contract": "grey_deer_ew_forecast_issue.v1", "model_fingerprint": ""}\n'
        '{"contract": "grey_deer_ew_forecast_issue.v1"}\n',
        encoding="utf-8")
    out = r.evaluate(prereg_text=lines("2026-11-02", "2026-11-03"),
                     now_utc=datetime(2028, 1, 3, tzinfo=timezone.utc),
                     issue_log_path=log)
    assert out["refusal"] == "no_receipted_issue"
    assert out["gate"] == 4
    assert out["verdict"] == "NOT_EXECUTABLE"
    assert r.has_receipted_issue(log) is False
    assert r.has_receipted_issue(tmp_path / "does_not_exist.jsonl") is False


# ── T7: gate 5 — a receipted issue still cannot score ──────────────────────────

def test_t7_gate5_scorer_not_implemented(tmp_path):
    log = tmp_path / "issue_log.jsonl"
    log.write_text(
        '{"contract": "grey_deer_ew_forecast_issue.v1", "model_fingerprint": "f00d"}\n',
        encoding="utf-8")
    assert r.has_receipted_issue(log) is True
    out = r.evaluate(prereg_text=lines("2026-11-02", "2026-11-03"),
                     now_utc=datetime(2028, 1, 3, tzinfo=timezone.utc),
                     issue_log_path=log)
    assert out["refusal"] == "scorer_not_implemented"
    assert out["gate"] == 5
    assert out["verdict"] == "NOT_EXECUTABLE"
    assert r.SCORER_IMPLEMENTED is False
    assert out["scorer_implemented"] is False


# ── T8: earliest_first_look vectors and input validation ───────────────────────

@pytest.mark.parametrize("merge,start,l0", VECTORS)
def test_t8_earliest_first_look_vectors(merge, start, l0):
    assert r.first_session_strictly_after(merge) == start
    assert r.earliest_first_look(start) == l0


def test_t8_rejections():
    with pytest.raises(ValueError):  # 2026-11-07 is a Saturday
        r.earliest_first_look(date(2026, 11, 7))
    with pytest.raises(ValueError):  # naive now
        r.window_elapsed(date(2026, 11, 3), datetime(2027, 12, 31, 21, 0, 1))


# ── T9: register_families against a temporary ledger ───────────────────────────

def test_t9_register_families(tmp_path):
    from engine.trial_ledger import TrialLedger

    ledger_path = tmp_path / "trial_ledger.jsonl"
    led = TrialLedger(ledger_path)
    assert r.register_families(led) == [True, True]
    for fam in r.FAMILIES:
        assert led.declared_budget(fam) == 3
    assert r.register_families(led) == [False, False]  # idempotent second call

    rows = [json.loads(ln) for ln in ledger_path.read_text(encoding="utf-8").splitlines()
            if ln.strip()]
    assert len(rows) == 2
    for row, fam in zip(rows, r.FAMILIES):
        assert row["kind"] == "declared_budget"
        assert row["n"] == 3
        assert row["family"] == fam
        assert row["reason"] == r.REGISTRATION_REASON


# ── T10: CLI ───────────────────────────────────────────────────────────────────

def test_t10_cli_default_and_register(tmp_path, capsys):
    assert r.main(["--issue-log", str(tmp_path / "x.jsonl")]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["verdict"] == "NOT_EXECUTABLE"
    assert out["refusal"] in r.REFUSALS

    assert r.main(["--register-families", "--ledger-path",
                   str(tmp_path / "tl.jsonl")]) == 0
    out2 = json.loads(capsys.readouterr().out)
    assert out2 == {"families": list(r.FAMILIES), "registered": [True, True]}


# ── T11: import hygiene and source hygiene ─────────────────────────────────────

def test_t11_import_hygiene():
    proc = subprocess.run(
        [sys.executable, "-c",
         "import sys, scripts.grey_deer_ew_forecast_reader; "
         "print(sorted(m for m in ('pandas','numpy','pyarrow','engine.trial_ledger') "
         "if m in sys.modules))"],
        cwd=str(r.REPO_ROOT), capture_output=True, text=True, check=True)
    assert proc.stdout.strip() == "[]"

    src = Path(r.__file__).read_text(encoding="utf-8")
    assert "SCORER_IMPLEMENTED = False" in src
    for forbidden in ("parquet", "grade_log", "read_csv"):
        assert forbidden not in src, forbidden
