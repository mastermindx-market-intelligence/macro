"""R1-B registered-run path, end to end on synthetic bars.  No market data is read.

The run is exercised through ``main`` against a stub of the Terminal qualification
module and a synthetic capture: two symbols carry bars, seven are empty.  The real
frozen config, prereg, registration receipt and ledger are used unchanged.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import math
import re
import socket
import statistics
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from engine.session_digest import session_window_et
from lib.nyse_calendar import is_session
from scripts.research import terminal_tactical_r1b_study as s

_REAL_COLLECTED_TEST_IDS = s._collected_test_ids

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "research/species/tti_r1b/config_v4.json").read_text())
CODE_SHA = "a" * 40
WARMUP, FIRING = 66, 24
CUT = 12          # bars missing from the end of the last session that has bars
PRE_OUTCOME_FILES = ("coverage.json", "events.jsonl", "census.jsonl", "pools.jsonl")
EXTRA_INIT_MODULES = (
    "engine/__init__.py",
    "engine/entry_radar/__init__.py",
    "engine/entry_radar/contracts.py",
    "lib/__init__.py",
    "scripts/__init__.py",
)

# A stand-in for the Terminal qualification module at the pinned dependency commit:
# the same three names, the same call shapes, no licensed code.
STUB = '''
import hashlib, json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

_ET = ZoneInfo("America/New_York")


class CalendarProjection:
    def __init__(self, start, end, sessions, sha256, source_revision):
        self.start, self.end, self.sessions = start, end, sessions
        self.sha256, self.source_revision = sha256, source_revision

    @classmethod
    def load(cls, path):
        raw = path.read_bytes()
        doc = json.loads(raw)
        return cls(doc["coverage"]["start"], doc["coverage"]["end"],
                   {k: tuple(v) for k, v in doc["sessions"].items()},
                   hashlib.sha256(raw).hexdigest(), doc["source"]["revision"])

    def window(self, day):
        if not (self.start <= day <= self.end):
            raise ValueError("calendar_coverage_unknown")
        return self.sessions.get(day)


def decode_display_epoch(seconds):
    wall = datetime.fromtimestamp(int(seconds), timezone.utc).replace(tzinfo=None)
    return int(wall.replace(tzinfo=_ET).timestamp())


def qualify_store(path, symbol, timeframe, calendar, start, end, cutoff, mode):
    return {"status": "qualified", "errors": {}}
'''

# One session's first six bars at a price level of 100 (open, high, low, close).  Bar 2
# is the first lawful anchor (decision 09:45); bars 3-5 then reclaim its low.
RECLAIM = [[100, 100.65, 99, 99.4], [99.4, 99.5, 98.8, 99], [99, 99.1, 98.6, 98.98],
           [98.98, 99.1, 98.55, 98.95], [98.95, 99.2, 98.8, 99.1], [99.1, 99.5, 99, 99.4]]
# The same anchor followed by a close well below it.
CONTINUE = [*RECLAIM[:3], [98.98, 99.0, 97.9, 98.0], [98.0, 98.2, 97.95, 98.1],
            [98.1, 98.3, 98.0, 98.1]]


def _sessions() -> list[date]:
    first, last = date.fromisoformat(CFG["start"]), date.fromisoformat(CFG["end"])
    days = (first + timedelta(days=n) for n in range((last - first).days + 1))
    return [day for day in days if is_session(day)]


def _window(day: date) -> tuple[int, int]:
    start, close = session_window_et(day)
    return start.hour * 60 + start.minute, close.hour * 60 + close.minute


def _display(day: date, minute: int) -> int:
    """The capture's display epoch: the ET wall clock written as if it were UTC."""
    return int(datetime(day.year, day.month, day.day, minute // 60, minute % 60,
                        tzinfo=timezone.utc).timestamp())


def _stock_rows(index: int, prior_close: float, bars: int) -> list[list[float]]:
    if index < WARMUP:
        level = prior_close
        return [[level, level + 1.4, level - 0.6, level],
                *([[level, level + .05, level - .05, level]] * (bars - 1))][:bars]
    firing = index - WARMUP
    scale = prior_close / 100
    head = CONTINUE if firing % 6 == 2 else RECLAIM
    slope = ((firing % 5) - 2) * .004
    base, wiggle = (98.1, .1) if head is CONTINUE else (99.4, .2)
    if head is CONTINUE:
        slope = abs(slope)
    rows = [list(row) for row in head]
    for step in range(bars - len(head)):
        a, b = base + slope * step, base + slope * (step + 1)
        rows.append([a, max(a, b) + wiggle, min(a, b) - wiggle, b])
    return [[round(value * scale, 6) for value in row] for row in rows[:bars]]


def _benchmark_rows(close: float, sign: int, bars: int) -> list[list[float]]:
    points = [close * (1 - sign * .004 * (1 - step / bars)) for step in range(bars + 1)]
    return [[round(points[i], 6), round(max(points[i], points[i + 1]) + .05, 6),
             round(min(points[i], points[i + 1]) - .05, 6), round(points[i + 1], 6)]
            for i in range(bars)]


def _bars(sessions: list[date]) -> dict[str, list[list[float]]]:
    """Ninety sessions for one stock and the benchmark; later sessions have no bars.

    The stock's last session stops an hour early, so its close-horizon outcome is censored.
    """
    out: dict[str, list[list[float]]] = {"AMD": [], "QQQ": []}
    stock, bench = 100.0, 400.0
    for index, day in enumerate(sessions[:WARMUP + FIRING]):
        opening, closing = _window(day)
        bars = (closing - opening) // 5
        step = (.0004 + (index % 7) * .0001) * (1 if index % 2 == 0 else -1)
        bench *= 1 + step
        if index < WARMUP:
            stock *= 1 + 2 * step
        sign = -1 if index >= WARMUP and (index - WARMUP) % 4 == 3 else 1
        stock_rows = _stock_rows(index, stock, bars)
        if index == WARMUP + FIRING - 1:
            stock_rows = stock_rows[:-CUT]      # the stock's last hour was never captured
        for name, rows in (("AMD", stock_rows), ("QQQ", _benchmark_rows(bench, sign, bars))):
            for position, (o, h, low, c) in enumerate(rows):
                out[name].append([_display(day, opening + 5 * position), o, h, low, c, 100.0])
        stock = stock_rows[-1][3]
    return out


def _junit(path: Path, modules=s.REQUIRED_TEST_MODULES, bad: str | None = None,
           suite: str = CODE_SHA) -> Path:
    cases = "".join(f'<testcase classname="{module}" name="test_ok"/>' for module in modules)
    if bad:
        cases += (f'<testcase classname="tests.test_tactical_r1b_run" name="test_bad">'
                  f'<{bad} message="x"/></testcase>')
    path.write_text(f'<?xml version="1.0"?><testsuites><testsuite name="{suite}">{cases}'
                    f'</testsuite></testsuites>')
    return path


def _write_manifest(path: Path, inputs: Path, symbols) -> Path:
    results = []
    for symbol in symbols:
        raw = (inputs / f"{symbol}.5m.json").read_bytes()
        results.append({"symbol": symbol, "timeframe": "5m", "source_kind": "synthetic",
                        "status": "captured", "http_status": 200,
                        "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                        "rows": len(json.loads(raw)["bars"])})
    path.write_text(json.dumps({"scope": "synthetic", "held_target": None, "results": results}))
    return path


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    mp = pytest.MonkeyPatch()
    mp.setattr(s, "_reviewed_blob_sha256", lambda code_sha, name: s._sha(s.ROOT / name))
    mp.setattr(s, "_collected_test_ids",
               lambda files: {f"{m}::test_ok" for m in s.REQUIRED_TEST_MODULES})
    root = tmp_path_factory.mktemp("r1b_run")
    terminal = root / "terminal_root"
    (terminal / "ingest").mkdir(parents=True)
    (terminal / "ingest/intraday_qualification.py").write_text(STUB)
    (terminal / "terminal/lib").mkdir(parents=True)
    sessions = _sessions()
    (terminal / "terminal/lib/usEquitySessionProjection.json").write_text(json.dumps({
        "coverage": {"start": CFG["start"], "end": CFG["end"]},
        "source": {"revision": "0" * 40},
        "sessions": {day.isoformat(): list(_window(day)) for day in sessions}}))
    inputs = root / "inputs"
    inputs.mkdir()
    bars = _bars(sessions)
    symbols = [*CFG["symbols"], CFG["benchmark"]]
    for symbol in symbols:
        (inputs / f"{symbol}.5m.json").write_text(json.dumps(
            {"t": symbol, "tf": "5m", "src": "polygon", "bars": bars.get(symbol, [])}))
    manifest = _write_manifest(root / "manifest.json", inputs, symbols)
    mp.setattr(
        s,
        "_terminal_dependency_probe",
        lambda root, sha: {
            "porcelain": "",
            "toplevel": str(Path(root).resolve()),
            "blobs": {p: s._sha(Path(root) / p) for p in s.TERMINAL_PINNED_FILES},
        },
    )
    try:
        yield SimpleNamespace(root=root, terminal=terminal, inputs=inputs, manifest=manifest,
                              junit=_junit(root / "junit.xml"), sessions=sessions,
                              symbols=symbols)
    finally:
        mp.undo()


def _patch(mp: pytest.MonkeyPatch, world, manifest: Path | None = None,
           attempt_root: Path | None = None) -> None:
    mp.setattr(s, "D0_MANIFEST_SHA256",
               hashlib.sha256((manifest or world.manifest).read_bytes()).hexdigest())
    mp.setattr(s.r1, "_git_head", lambda _root: CFG["terminal_dependency_sha"])
    # The published result may already exist in this checkout; the run must not see it.
    mp.setattr(s, "RESULT_PATH", world.root / "absent/RESULT_V4.json")
    mp.setattr(s, "REPORT_PATH", world.root / "absent/REPORT.md")
    mp.setattr(s, "ATTEMPT_ROOT", attempt_root or world.root)


def _out_dir(attempt_root: Path, name: str = "run1") -> Path:
    return attempt_root / "output" / name


def _argv(world, out: Path, *, junit: Path | None = None,
          code_sha: str = CODE_SHA, manifest: Path | None = None) -> list[str]:
    return ["--input-dir", str(world.inputs), "--manifest", str(manifest or world.manifest),
            "--terminal-root", str(world.terminal), "--output-dir", str(out),
            "--code-sha", code_sha, "--junit", str(junit or world.junit)]


@pytest.fixture(scope="module")
def run(world):
    """One refused attempt (unclean test receipt), then the one complete run."""
    mp = pytest.MonkeyPatch()
    out = _out_dir(world.root, "complete")
    attempts = world.root / "attempts"
    seen: list[dict[str, bool]] = []
    try:
        _patch(mp, world)
        refused = s.main(_argv(world, out,
                               junit=_junit(world.root / "junit_bad.xml", bad="failure")))
        real = s.te.measure_event_outcome

        def spy(*args, **kwargs):
            if not seen:
                files = {name: (out / name).is_file() for name in
                         (*PRE_OUTCOME_FILES, "pre_outcome_receipt.json", "result.json",
                          "report.md", "rows.jsonl", "outcomes.jsonl")}
                try:
                    socket.getaddrinfo("localhost", 80)
                    network = "open"
                except RuntimeError as exc:
                    network = str(exc)
                seen.append({"files": files, "network": network})
            return real(*args, **kwargs)

        mp.setattr(s.te, "measure_event_outcome", spy)
        rc = s.main(_argv(world, out))
    finally:
        mp.undo()
    result = json.loads((out / "result.json").read_text()) if (out / "result.json").is_file() else None
    return SimpleNamespace(refused=refused, rc=rc, out=out, attempts=attempts, result=result,
                           first_outcome_call=seen[0] if seen else None)


# --------------------------------------------------------------------------- the complete run

def test_the_run_completes_and_reports_all_sixty_registered_cells(run):
    assert (run.refused, run.rc) == (2, 0)
    result = run.result
    assert result["schema"] == s.RESULT_SCHEMA and result["study_id"] == s.STUDY_ID
    assert result["authority"] == "retrospective_research_only"
    assert [result[k] for k in ("may_rank", "may_alert", "may_size", "may_trade")] == [False] * 4
    assert result["research_admission"] == "corrected_archive_exploratory_only"
    wanted = {f"{sel}|{hor}|{cost}" for sel in CFG["selectors"] for hor in CFG["horizons"]
              for cost in CFG["round_trip_cost_bps"]}
    assert set(result["aggregate"]["cells"]) == wanted == set(result["descriptive"])
    assert len(wanted) == 60 == result["grid"]["cells"]
    assert set(result["matched_delta_once"]) == {f"{sel}|{hor}" for sel in CFG["selectors"]
                                                  for hor in CFG["horizons"]}
    # 24 firing sessions can never meet the 300-fire gate.
    assert result["disposition"] == "NO_PROMOTION"
    identity = result["identity"]
    assert identity["code_sha"] == CODE_SHA
    assert identity["config_sha256"] == hashlib.sha256(s.CONFIG_PATH.read_bytes()).hexdigest()
    assert identity["rulings_sha256"] == hashlib.sha256(s.RULINGS_PATH.read_bytes()).hexdigest()
    assert identity["grid_sha256"] == s.GRID_SHA256
    assert identity["registered_rows_sha256"] == s.R1B_ROWS_SHA256
    assert set(identity["code_files"]) >= set(s.CODE_FILES)
    for extra in EXTRA_INIT_MODULES:
        assert extra in identity["code_files"]
    assert identity["code_files_required"] == list(s.CODE_FILES)
    assert identity["code_files_late"] == []
    for name, digest in identity["code_files"].items():
        assert digest == hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    assert "NO_PROMOTION" in (run.out / "report.md").read_text()


def test_synthetic_sessions_produce_the_expected_events(run):
    counts = run.result["counts"]
    # 20 reclaim sessions and 4 continuation sessions; every session's first anchor is
    # the same bar, so each selector's count is fixed by construction.
    assert counts["events"] == {"BASE_FRESH_LOW": 24, "CONTINUATION_RISK": 4,
                                "EXHAUSTION_FORMING": 24, "EXHAUSTION_RECLAIM": 20,
                                "RECLAIM_ONLY": 20}
    assert counts["events_total"] == sum(counts["events"].values())
    assert counts["scheduled_sessions"] == len(_sessions())
    assert counts["symbol_sessions"] == len(_sessions()) * len(CFG["symbols"])
    assert counts["census_usable"] + counts["census_null_sign_rejected"] == counts["census_rows"]


def test_pools_are_written_and_hashed_before_the_first_outcome_call(run):
    assert run.first_outcome_call["files"] == {
        **{name: True for name in PRE_OUTCOME_FILES}, "pre_outcome_receipt.json": True,
        "result.json": False, "report.md": False, "rows.jsonl": False, "outcomes.jsonl": False}
    assert run.first_outcome_call["network"] == "network_path_refused"
    hashes = run.result["leak_audit"]["pre_outcome_hashes"]
    for name in PRE_OUTCOME_FILES:
        assert hashlib.sha256((run.out / name).read_bytes()).hexdigest() == hashes[name]
    receipt = json.loads((run.out / "pre_outcome_receipt.json").read_text())
    assert receipt["hashes"] == hashes
    assert receipt["market_outcomes_computed"] is False and receipt["code_sha"] == CODE_SHA
    assert receipt["counts"] == run.result["counts"]
    for name in ("events.jsonl", "census.jsonl", "pools.jsonl"):
        for line in (run.out / name).read_text().splitlines():
            row = json.loads(line)
            assert not ({"net_return", "raw_return", "net_beta_residual", "exit_close",
                         "mfe", "mae"} & set(row)), name


def test_private_files_reconcile_with_the_published_counts(run):
    result = run.result
    total = result["counts"]["events_total"]
    rows = (run.out / "rows.jsonl").read_text().splitlines()
    outcomes = (run.out / "outcomes.jsonl").read_text().splitlines()
    assert len(rows) == len(outcomes) == total * 12
    private = result["leak_audit"]["private_file_hashes"]
    for name in ("rows.jsonl", "outcomes.jsonl"):
        assert hashlib.sha256((run.out / name).read_bytes()).hexdigest() == private[name]
    for key, cell in result["aggregate"]["cells"].items():
        selector = key.split("|")[0]
        for reading in s.agg.READINGS:
            assert cell[reading]["fires_raw"] == result["counts"]["events"][selector]
    for key, cell in result["descriptive"].items():
        assert cell["events"] == result["counts"]["events"][key.split("|")[0]]
        assert cell["available"] + cell["censored"] == cell["events"]
    audit = result["leak_audit"]
    assert audit["network_refused"] is True
    assert audit["census_future_family_labels_used"] is False
    assert audit["pools_market_outcomes_computed"] is False and audit["pools_fallback_used"] is False
    assert audit["test_receipt"]["all_passed"] is True
    assert audit["ledger_prefix_matches_receipt"] is True


def test_coverage_names_what_was_and_was_not_there(run):
    coverage = run.result["coverage"]
    sessions = [day.isoformat() for day in _sessions()]
    data_days = sessions[:WARMUP + FIRING]
    assert coverage["scheduled_sessions"] == len(sessions)
    assert "2025-07-03" in coverage["shortened_sessions_excluded_from_decisions"]
    amd = coverage["symbols"]["AMD"]
    # The last session with bars stops an hour early: it is constructed from its usable
    # prefix, named as incomplete, and gives the following session no prior ATR.
    assert amd["complete_regular_sessions"] == len(data_days) - 1
    assert (amd["first_bar_date"], amd["last_bar_date"]) == (data_days[0], data_days[-1])
    assert amd["last_complete_session"] == data_days[-2]
    assert amd["incomplete_sessions"] == sessions[len(data_days) - 1:]
    assert amd["file_row_cap_reached"] is False
    assert amd["prefix_incomplete_session_dates"] == [data_days[-1]]
    assert amd["diagnostics"] == {"missing_bar": CUT}
    assert amd["construction"] == {"AVAILABLE": WARMUP + FIRING - 22,
                                   "PARTIAL:input_gaps_or_unusable_observations": 1}
    assert amd["sessions_not_constructed"] == len(sessions) - (WARMUP + FIRING - 21)
    assert amd["events"] == run.result["counts"]["events"]
    assert run.result["counts"]["pools"]["EXHAUSTION_RECLAIM"] == {
        "AVAILABLE": 14, "NO_CONTROL:matched_control_floor_not_met": 6}
    empty = coverage["symbols"]["NVDA"]
    assert empty["rows"] == 0 and empty["complete_regular_sessions"] == 0
    assert empty["scheduled_sessions_before_first_bar"] == len(sessions)
    assert empty["events"] == {} and empty["sessions_not_constructed"] == len(sessions)
    assert coverage["symbols"]["QQQ"]["complete_regular_sessions"] == len(data_days)
    assert "normalization" not in coverage["symbols"]["QQQ"]


def test_a_censored_outcome_is_counted_and_left_out_of_the_descriptive_means(run):
    outcomes = [json.loads(line) for line in (run.out / "outcomes.jsonl").read_text().splitlines()]
    for key, cell in run.result["descriptive"].items():
        selector, horizon, cost = key.split("|")
        mine = [row for row in outcomes
                if (row["selector"], row["horizon"], str(row["cost_bps"])) == (selector, horizon, cost)]
        available = [row for row in mine if row["status"] == "available"]
        assert (cell["events"], cell["available"]) == (len(mine), len(available))
        # Only the session that stops early loses its close-horizon outcome; that session
        # is a reclaim session, so the continuation selector has no event in it.
        cut_short = horizon == "close" and selector != "CONTINUATION_RISK"
        assert cell["censored"] == (1 if cut_short else 0), key
        assert cell["censor_reasons"] == ({"stock_path_missing_or_ambiguous": 1} if cut_short else {})
        for field in ("net_beta_residual", "raw_return", "mfe"):
            values = [row[field] for row in available]
            assert cell[field] == {"n": len(values), "mean": math.fsum(values) / len(values),
                                   "median": statistics.median(values)}, (key, field)
    for reading in s.agg.READINGS:
        cell = run.result["aggregate"]["cells"]["BASE_FRESH_LOW|close|25"][reading]
        assert (cell["no_control"], cell["selected_censored"], cell["no_control_and_censored"]) == (6, 1, 1)
        assert cell["fires_raw"] == 24 == cell["fires_delta"] + cell["control_evidence_unavailable"] + 6


def test_an_earlier_refused_attempt_is_disclosed_in_the_result(run):
    attempts = run.result["attempts"]
    assert [a["stage"] for a in attempts] == ["arguments"]
    assert attempts[0]["exception_type"] == "ValueError"
    assert attempts[0]["outcome_values_persisted"] is False
    assert sorted(p.name for p in run.attempts.iterdir()) == ["attempt-001.json", "attempt-002.json"]


# --------------------------------------------------------------------------- aborts and refusals

@pytest.mark.parametrize("how, kind", [("exception_with_a_value_in_its_text", "RuntimeError"),
                                       ("accounting_identity_broken", "ValueError")])
def test_an_abort_after_outcomes_records_type_and_frames_only(world, monkeypatch, tmp_path, capsys,
                                                              how, kind):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    real = s.agg.summarize

    def boom(rows, *, cfg):
        if how == "exception_with_a_value_in_its_text":
            raise RuntimeError("net_return=0.123456 secret")
        summary = real(rows, cfg=cfg)
        summary["cells"]["EXHAUSTION_RECLAIM|60m|25"]["S-B"]["fires_delta"] -= 1
        return summary

    monkeypatch.setattr(s.agg, "summarize", boom)
    out = _out_dir(tmp_path)
    assert s.main(_argv(world, out)) == 2
    captured = capsys.readouterr()
    # Once outcomes exist, not even one of the runner's own refusal codes is printed.
    assert captured.err.splitlines()[-1] == f"R1-B study aborted during aggregate: {kind}"
    assert "secret" not in captured.err + captured.out and "0.123456" not in captured.err + captured.out
    assert "event_accounting_identity_violated" not in captured.err + captured.out
    receipt = json.loads((tmp_path / "attempts/attempt-001.json").read_text())
    assert (receipt["stage"], receipt["exception_type"]) == ("aggregate", kind)
    assert receipt["outcome_stage_started"] is True
    assert receipt["outcome_values_persisted"] is False
    assert receipt["code_sha"] == CODE_SHA
    assert "secret" not in json.dumps(receipt)
    assert receipt["frames"] and all(re.fullmatch(r"[\w.]+:\d+", f) for f in receipt["frames"])
    assert (out / "pools.jsonl").is_file()
    assert not any((out / name).exists() for name in ("result.json", "report.md", "rows.jsonl",
                                                      "outcomes.jsonl"))
    # The used output directory can never be written again.
    assert s.main(_argv(world, out)) == 2
    assert "R1-B study refused: output_directory_exists" in capsys.readouterr().err
    second = json.loads((tmp_path / "attempts/attempt-002.json").read_text())
    assert second["stage"] == "arguments"


def test_a_selected_outcome_that_differs_from_its_direct_measurement_stops_the_run(
        world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    real = s.measure_event_grid

    def altered(*args, **kwargs):
        grid = real(*args, **kwargs)
        grid[0]["net_beta_residual"] = (grid[0]["net_beta_residual"] or 0.0) + 1e-9
        return grid

    monkeypatch.setattr(s, "measure_event_grid", altered)
    out = _out_dir(tmp_path)
    assert s.main(_argv(world, out)) == 2
    assert capsys.readouterr().err.splitlines()[-1] == "R1-B study aborted during outcomes: ValueError"
    receipt = json.loads((tmp_path / "attempts/attempt-001.json").read_text())
    assert (receipt["stage"], receipt["outcome_stage_started"]) == ("outcomes", True)
    assert receipt["outcome_values_persisted"] is False
    assert (out / "pre_outcome_receipt.json").is_file() and not (out / "result.json").exists()


def test_a_failure_while_writing_results_makes_that_attempt_the_registered_run(
        world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    real = Path.write_bytes

    def failing(self, data):
        if self.name == "rows.jsonl":
            raise OSError("disk full")
        return real(self, data)

    monkeypatch.setattr(Path, "write_bytes", failing)
    out = _out_dir(tmp_path)
    assert s.main(_argv(world, out)) == 2
    assert capsys.readouterr().err.splitlines()[-1] == "R1-B study aborted during persist: OSError"
    receipt = json.loads((tmp_path / "attempts/attempt-001.json").read_text())
    assert (receipt["stage"], receipt["outcome_values_persisted"]) == ("persist", True)
    assert (out / "result.json").is_file() and not (out / "rows.jsonl").exists()
    monkeypatch.setattr(Path, "write_bytes", real)
    assert s.main(_argv(world, _out_dir(tmp_path, "run2"))) == 2
    assert capsys.readouterr().err.splitlines()[-1] == (
        "R1-B study refused: registered_run_already_persisted")
    assert not _out_dir(tmp_path, "run2").exists()


@pytest.mark.parametrize("error, printed", [
    (KeyError("close=123.45"), "R1-B study aborted during inputs: KeyError"),
    (ValueError("12345"), "R1-B study aborted during inputs: ValueError"),
    (ValueError("last_close:123.45"), "R1-B study aborted during inputs: ValueError"),
    (ValueError("price 101.5 is off grid"), "R1-B study aborted during inputs: ValueError"),
    (ValueError("input_digest_mismatch:AMD"), "R1-B study refused: input_digest_mismatch:AMD"),
    (ValueError("session_clock_disagreement"), "R1-B study refused: session_clock_disagreement"),
])
def test_after_inputs_are_read_only_a_refusal_code_is_ever_printed(world, monkeypatch, tmp_path,
                                                                   capsys, error, printed):
    _patch(monkeypatch, world, attempt_root=tmp_path)

    def boom(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(s, "load_inputs", boom)
    assert s.main(_argv(world, _out_dir(tmp_path))) == 2
    err = capsys.readouterr().err
    assert err.splitlines()[-1] == printed
    receipt = json.loads((tmp_path / "attempts/attempt-001.json").read_text())
    assert receipt["stage"] == "inputs" and receipt["outcome_stage_started"] is False
    assert str(error.args[0]) not in json.dumps(receipt)
    assert not _out_dir(tmp_path).exists()


def test_a_run_that_already_persisted_outcomes_is_never_repeated(world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    attempt_dir = tmp_path / "attempts"
    attempt_dir.mkdir(parents=True)
    (attempt_dir / "attempt-001.json").write_text(json.dumps(
        {"stage": "persist", "outcome_values_persisted": True, "attempt": 1,
         "schema": s.ATTEMPT_SCHEMA, "study_id": s.STUDY_ID, "finalized": True}))
    assert s.main(_argv(world, _out_dir(tmp_path))) == 2
    assert "registered_run_already_persisted" in capsys.readouterr().err
    assert not _out_dir(tmp_path).exists()


@pytest.mark.parametrize("case, code", [
    ("code_sha", "code_sha_invalid"),
    ("empty_output_dir", "output_directory_exists"),
    ("result_artifact", "results_artifact_exists"),
    ("report_artifact", "results_artifact_exists"),
    ("missing_argument", "full_run_requires_input_manifest_terminal_output_code_sha_junit"),
])
def test_argument_stage_refusals(world, monkeypatch, tmp_path, capsys, case, code):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    out = _out_dir(tmp_path)
    argv = _argv(world, out)
    if case == "code_sha":
        argv = _argv(world, out, code_sha="abc123")
    elif case == "empty_output_dir":
        out.mkdir(parents=True)
    elif case in ("result_artifact", "report_artifact"):
        published = tmp_path / "published"
        published.write_text("{}")
        monkeypatch.setattr(s, "RESULT_PATH" if case == "result_artifact" else "REPORT_PATH",
                            published)
    else:
        argv = argv[:-2]
    assert s.main(argv) == 2
    assert f"R1-B study refused: {code}" in capsys.readouterr().err
    assert not (out / "pools.jsonl").exists()


def test_a_refusal_before_any_market_input_prints_its_whole_text(world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)

    def refuse(**_kwargs):
        raise ValueError("registered_grid_row_count_mismatch:59/60")

    def never(*_args, **_kwargs):
        raise AssertionError("inputs must not be read after a refused admission")

    monkeypatch.setattr(s, "verify_admission", refuse)
    monkeypatch.setattr(s, "load_inputs", never)
    assert s.main(_argv(world, _out_dir(tmp_path))) == 2
    assert capsys.readouterr().err.splitlines()[-1] == (
        "R1-B study refused: registered_grid_row_count_mismatch:59/60")
    receipt = json.loads((tmp_path / "attempts/attempt-001.json").read_text())
    assert (receipt["stage"], receipt["exception_type"]) == ("admission", "ValueError")


@pytest.mark.parametrize("field, value", [("bootstrap_repetitions", 3999), ("seed", 20260918)])
def test_a_config_with_another_bootstrap_identity_is_refused_before_any_input(
        world, monkeypatch, tmp_path, capsys, field, value):
    """The admission hash already pins the config; this is the runner's own second check."""
    _patch(monkeypatch, world, attempt_root=tmp_path)
    admitted = s.verify_admission()
    config = tmp_path / "config_v4.json"
    config.write_text(json.dumps({**json.loads(s.CONFIG_PATH.read_bytes()), field: value}))

    def never(*_args, **_kwargs):
        raise AssertionError("inputs must not be read after a refused bootstrap identity")

    monkeypatch.setattr(s, "verify_admission", lambda: admitted)
    monkeypatch.setattr(s, "CONFIG_PATH", config)
    monkeypatch.setattr(s, "load_inputs", never)
    assert s.main(_argv(world, _out_dir(tmp_path))) == 2
    assert capsys.readouterr().err.splitlines()[-1] == (
        "R1-B study refused: frozen_bootstrap_identity_mismatch")
    receipt = json.loads((tmp_path / "attempts/attempt-001.json").read_text())
    assert receipt["stage"] == "admission"


@pytest.mark.parametrize("bad, modules, code", [
    ("failure", s.REQUIRED_TEST_MODULES, "test_receipt_not_clean"),
    ("error", s.REQUIRED_TEST_MODULES, "test_receipt_not_clean"),
    ("skipped", s.REQUIRED_TEST_MODULES, "test_receipt_not_clean"),
    (None, (), "test_receipt_not_clean"),
    (None, s.REQUIRED_TEST_MODULES[:-1], "test_receipt_missing_suite"),
    (None, ("tests.test_tactical_research_cli_extra", *s.REQUIRED_TEST_MODULES[1:]),
     "test_receipt_missing_suite"),
])
def test_the_test_receipt_must_be_clean_and_name_every_required_suite(tmp_path, bad, modules, code):
    with pytest.raises(ValueError, match=code):
        s.junit_receipt(_junit(tmp_path / "junit.xml", modules=modules, bad=bad), CODE_SHA)


def test_a_clean_receipt_lists_every_case(tmp_path):
    modules = [*s.REQUIRED_TEST_MODULES, "tests.test_tactical_r1b_run.TestClass"]
    receipt = s.junit_receipt(_junit(tmp_path / "junit.xml", modules=modules), CODE_SHA)
    assert receipt["tests"] == len(modules) == len(receipt["cases"])
    assert receipt["all_passed"] is True
    assert receipt["sha256"] == hashlib.sha256((tmp_path / "junit.xml").read_bytes()).hexdigest()


def test_inputs_are_refused_on_a_manifest_or_dependency_mismatch(world, monkeypatch, tmp_path):
    with pytest.raises(ValueError, match="input_manifest_sha256_mismatch"):
        s.load_inputs(world.inputs, world.manifest, world.terminal, CFG)
    _patch(monkeypatch, world)
    monkeypatch.setattr(s.r1, "_git_head", lambda _root: "b" * 40)
    with pytest.raises(ValueError, match="terminal_dependency_head_mismatch"):
        s.load_inputs(world.inputs, world.manifest, world.terminal, CFG)
    short = _write_manifest(tmp_path / "manifest.json", world.inputs,
                            [name for name in world.symbols if name != "AMD"])
    _patch(monkeypatch, world, manifest=short)
    with pytest.raises(ValueError, match="manifest_5m_missing:AMD"):
        s.load_inputs(world.inputs, short, world.terminal, CFG)


def test_an_input_file_that_changed_after_the_manifest_is_refused(world, monkeypatch, tmp_path):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    for symbol in world.symbols:
        (inputs / f"{symbol}.5m.json").write_bytes((world.inputs / f"{symbol}.5m.json").read_bytes())
    (inputs / "AMD.5m.json").write_text(json.dumps({"t": "AMD", "tf": "5m", "src": "polygon",
                                                    "bars": []}))
    _patch(monkeypatch, world)
    with pytest.raises(ValueError, match="input_digest_mismatch:AMD"):
        s.load_inputs(inputs, world.manifest, world.terminal, CFG)


class _Calendar:
    def __init__(self, sessions):
        self.sessions = sessions

    def window(self, day):
        return self.sessions.get(day)


@pytest.mark.parametrize("case", ["agree", "missing_session", "extra_session", "wrong_close"])
def test_the_two_calendars_must_agree_on_every_date(case):
    sessions = {day.isoformat(): _window(day) for day in _sessions()}
    if case == "missing_session":
        del sessions["2025-09-02"]
    elif case == "extra_session":
        sessions["2025-09-01"] = (570, 960)       # Labor Day
    elif case == "wrong_close":
        sessions["2025-07-03"] = (570, 960)       # a 13:00 close reported as a full day
    if case == "agree":
        assert s.scheduled_sessions(_Calendar(sessions), CFG) == [d.isoformat() for d in _sessions()]
    else:
        with pytest.raises(ValueError, match="session_calendar_disagreement"):
            s.scheduled_sessions(_Calendar(sessions), CFG)


@pytest.mark.parametrize("column, value", [("minute", 400), ("date", "2025-06-17")])
def test_a_bar_whose_wall_clock_disagrees_with_its_true_time_is_refused(world, column, value):
    d0 = s.r1._load_terminal_module(world.terminal)
    path = world.inputs / "AMD.5m.json"
    frame = s.r1._load_symbol(path, "AMD", hashlib.sha256(path.read_bytes()).hexdigest(), d0)
    day = world.sessions[0].isoformat()
    good = s.session_frame(frame, s._minutes_by_day(frame), day, _window(world.sessions[0]))
    assert len(good) == 78 and list(good.columns) == ["open", "high", "low", "close", "volume"]
    assert good.index[0] == session_window_et(world.sessions[0])[0]
    frame = frame.copy()
    frame.iloc[5, frame.columns.get_loc(column)] = value
    with pytest.raises(ValueError, match="session_clock_disagreement"):
        s.session_frame(frame, s._minutes_by_day(frame), day, _window(world.sessions[0]))


def test_a_bar_filed_under_the_wrong_session_is_refused_even_when_the_counts_agree(world):
    d0 = s.r1._load_terminal_module(world.terminal)
    path = world.inputs / "AMD.5m.json"
    frame = s.r1._load_symbol(path, "AMD", hashlib.sha256(path.read_bytes()).hexdigest(), d0).copy()
    first, second = world.sessions[0].isoformat(), world.sessions[1].isoformat()
    column = frame.columns.get_loc("date")
    frame.iloc[5, column] = second          # a bar of the first session filed under the second
    frame.iloc[78 + 5, column] = first      # and the same minute of the second filed under the first
    minutes = s._minutes_by_day(frame)
    assert len(minutes[first]) == len(minutes[second]) == 78
    for day, session in ((first, world.sessions[0]), (second, world.sessions[1])):
        with pytest.raises(ValueError, match="session_clock_disagreement"):
            s.session_frame(frame, minutes, day, _window(session))
    # One extra bar filed under a session whose own bars are all in place.
    frame.iloc[78 + 5, column] = second
    third = world.sessions[2].isoformat()
    frame.iloc[2 * 78 + 5, column] = second
    minutes = s._minutes_by_day(frame)
    assert (len(minutes[first]), len(minutes[second]), len(minutes[third])) == (77, 80, 77)
    with pytest.raises(ValueError, match="session_clock_disagreement"):
        s.session_frame(frame, minutes, second, _window(world.sessions[1]))


def test_every_network_path_is_refused_during_the_run_and_restored_after():
    original = (socket.socket, socket.create_connection, socket.getaddrinfo)
    with s.no_network():
        assert issubclass(socket.socket, original[0])
        for call in (lambda: socket.socket(),
                     lambda: socket.create_connection(("127.0.0.1", 9)),
                     lambda: socket.getaddrinfo("localhost", 80)):
            with pytest.raises(RuntimeError, match="network_path_refused"):
                call()
    assert (socket.socket, socket.create_connection, socket.getaddrinfo) == original
    with pytest.raises(KeyError):
        with s.no_network():
            raise KeyError("x")
    assert (socket.socket, socket.create_connection, socket.getaddrinfo) == original


def _clean_rows():
    events = [{"market_outcomes_computed": False}]
    census = [{"future_family_labels_used": False}]
    days = {("AMD", "2025-06-16"): {"normalization": {"market_outcomes_computed": False},
                                    "construction": {"market_outcomes_computed": False}},
            ("AMD", "2025-06-17"): {"normalization": {"market_outcomes_computed": False},
                                    "construction": None}}
    return events, census, days


@pytest.mark.parametrize("where, code", [
    ("census", "census_future_label_flag"), ("event", "event_outcome_flag"),
    ("normalization", "normalization_outcome_flag"), ("construction", "construction_outcome_flag")])
@pytest.mark.parametrize("value", [True, None, "missing"])
def test_a_constructed_row_that_does_not_deny_using_outcomes_is_refused(where, code, value):
    events, census, days = _clean_rows()
    s.refuse_outcome_flags(events, census, days)
    target, key = {
        "census": (census[0], "future_family_labels_used"),
        "event": (events[0], "market_outcomes_computed"),
        "normalization": (days[("AMD", "2025-06-16")]["normalization"], "market_outcomes_computed"),
        "construction": (days[("AMD", "2025-06-16")]["construction"], "market_outcomes_computed"),
    }[where]
    if value == "missing":
        del target[key]
    else:
        target[key] = value
    with pytest.raises(ValueError, match=code):
        s.refuse_outcome_flags(events, census, days)


@pytest.mark.parametrize("key", ["market_outcomes_computed", "fallback_used"])
@pytest.mark.parametrize("value", [True, None, "missing"])
def test_a_pool_that_does_not_deny_outcomes_or_fallback_is_refused(key, value):
    pool = {"market_outcomes_computed": False, "fallback_used": False}
    s.refuse_pool_flags([pool, dict(pool)])
    if value == "missing":
        del pool[key]
    else:
        pool[key] = value
    with pytest.raises(ValueError, match="pool_outcome_flag"):
        s.refuse_pool_flags([dict(market_outcomes_computed=False, fallback_used=False), pool])


def test_the_run_checks_those_flags_before_anything_is_written_or_measured():
    source = inspect.getsource(s.execute)
    construction, rest = source.split('stage("pools"', 1)
    pools_stage, later = rest.split('stage("preflight")', 1)
    assert "refuse_outcome_flags(events, census, days)" in construction
    assert "refuse_pool_flags(built_pools)" in pools_stage
    assert pools_stage.index("refuse_pool_flags(built_pools)") < pools_stage.index("output_dir.mkdir(")
    assert later.index("pre_outcome_receipt.json") < later.index('stage("outcomes")')
    assert "measure_" not in construction + pools_stage


# --------------------------------------------------------------------------- attempt ledger (T5)

def test_t5a_second_run_refused_after_first_completes(world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    out1 = _out_dir(tmp_path, "run1")
    assert s.main(_argv(world, out1)) == 0
    out2 = _out_dir(tmp_path, "run2")
    assert s.main(_argv(world, out2)) == 2
    assert "registered_run_already_persisted" in capsys.readouterr().err
    attempt_dir = tmp_path / "attempts"
    first = json.loads((attempt_dir / "attempt-001.json").read_text())
    second = json.loads((attempt_dir / "attempt-002.json").read_text())
    assert first["completed"] is True and first["outcome_values_persisted"] is True
    assert second["finalized"] is True and second["stage"] == "arguments"


def test_t5b_keyboard_interrupt_during_outcomes(world, monkeypatch, tmp_path):
    _patch(monkeypatch, world, attempt_root=tmp_path)

    def interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(s, "measure_event_grid", interrupt)
    out = _out_dir(tmp_path)
    with pytest.raises(KeyboardInterrupt):
        s.main(_argv(world, out))
    receipt = json.loads((tmp_path / "attempts/attempt-001.json").read_text())
    assert receipt["stage"] == "outcomes"
    assert receipt["outcome_stage_started"] is True
    assert receipt["outcome_values_persisted"] is False
    assert receipt["exception_type"] == "KeyboardInterrupt"


def test_t5c_keyboard_interrupt_during_persist_refuses_followup(world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    real = Path.write_bytes

    def interrupt_on_report(self, data):
        if self.name == "report.md":
            raise KeyboardInterrupt
        return real(self, data)

    monkeypatch.setattr(Path, "write_bytes", interrupt_on_report)
    out = _out_dir(tmp_path, "run1")
    with pytest.raises(KeyboardInterrupt):
        s.main(_argv(world, out))
    receipt = json.loads((tmp_path / "attempts/attempt-001.json").read_text())
    assert receipt["outcome_values_persisted"] is True
    monkeypatch.setattr(Path, "write_bytes", real)
    assert s.main(_argv(world, _out_dir(tmp_path, "run2"))) == 2
    assert "registered_run_already_persisted" in capsys.readouterr().err


def test_t5d_aggregate_abort_blocks_same_code_sha(world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    real = s.agg.summarize

    def boom(rows, *, cfg):
        raise RuntimeError("aggregate boom")

    monkeypatch.setattr(s.agg, "summarize", boom)
    out = _out_dir(tmp_path)
    assert s.main(_argv(world, out)) == 2
    assert s.main(_argv(world, _out_dir(tmp_path, "run2"))) == 2
    assert "rerun_without_reviewed_fix" in capsys.readouterr().err
    monkeypatch.setattr(s.agg, "summarize", real)
    alt_sha = "b" * 40
    junit_b = _junit(tmp_path / "junit_b.xml", suite=alt_sha)
    assert s.main(_argv(world, _out_dir(tmp_path, "run3"), code_sha=alt_sha, junit=junit_b)) == 0
    receipt = json.loads((tmp_path / "attempts/attempt-003.json").read_text())
    assert receipt["stage"] not in s.PRE_INPUT_STAGES or receipt.get("completed")


def test_t5e_attempt_numbering_skips_deleted_middle(world, monkeypatch, tmp_path):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    attempt_dir = tmp_path / "attempts"
    attempt_dir.mkdir(parents=True)
    (attempt_dir / "attempt-001.json").write_text("{}")
    (attempt_dir / "attempt-003.json").write_text("{}")
    assert s.next_attempt_number(attempt_dir) == 4


def test_t5f_output_directory_placement_refusals(world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    bad = tmp_path / "elsewhere" / "run1"
    assert s.main(_argv(world, bad)) == 2
    assert "output_directory_outside_run_root" in capsys.readouterr().err
    git_root = tmp_path / "git_output"
    git_root.mkdir()
    import subprocess
    subprocess.run(["git", "init"], cwd=git_root, capture_output=True, check=True)
    monkeypatch.setattr(s, "ATTEMPT_ROOT", git_root)
    inside = git_root / "output" / "run1"
    assert s.main(_argv(world, inside)) == 2
    assert "output_directory_inside_git" in capsys.readouterr().err


def test_t5g_abort_dir_argument_is_rejected(world, monkeypatch, tmp_path):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    argv = _argv(world, _out_dir(tmp_path)) + ["--abort-dir", str(tmp_path / "aborts")]
    with pytest.raises(SystemExit) as exc:
        s.main(argv)
    assert exc.value.code == 2


def test_t6a_loaded_modules_are_hashed_in_identity(world, monkeypatch, tmp_path):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    out = _out_dir(tmp_path)
    assert s.main(_argv(world, out)) == 0
    identity = json.loads((out / "result.json").read_text())["identity"]
    assert set(identity["code_files"]) >= set(s.CODE_FILES)
    assert set(identity["code_files"]) == set(s._loaded_root_modules())
    for name in EXTRA_INIT_MODULES:
        assert name in identity["code_files"]
    assert identity["code_files_required"] == list(s.CODE_FILES)
    assert identity["code_files_late"] == []


def test_t6b_loaded_root_modules_excludes_tests_tree():
    keys = set(s._loaded_root_modules())
    assert not any(name.startswith("tests/") for name in keys)
    assert not any(name.endswith("conftest.py") for name in keys)


def test_t6c_reviewed_head_mismatch_refuses_before_inputs(world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    real = s._reviewed_blob_sha256

    def fake(code_sha, name):
        if name == "lib/nyse_calendar.py":
            return "0" * 64
        return real(code_sha, name)

    monkeypatch.setattr(s, "_reviewed_blob_sha256", fake)
    assert s.main(_argv(world, _out_dir(tmp_path))) == 2
    err = capsys.readouterr().err
    assert "code_identity_not_at_reviewed_head:lib/nyse_calendar.py" in err
    receipt = json.loads((tmp_path / "attempts/attempt-001.json").read_text())
    assert receipt["stage"] == "admission"
    assert receipt["outcome_values_persisted"] is False


def test_t6d_unreadable_commit_refuses(world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)

    def unreadable(_code_sha, _name):
        raise ValueError("code_identity_commit_unreadable:x")

    monkeypatch.setattr(s, "_reviewed_blob_sha256", unreadable)
    assert s.main(_argv(world, _out_dir(tmp_path))) == 2
    assert "code_identity_commit_unreadable:x" in capsys.readouterr().err


def test_t6e_drift_refuses_before_persist(world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    honest = s._loaded_root_modules()
    calls = 0

    def census():
        nonlocal calls
        calls += 1
        if calls == 1:
            return honest
        drifted = dict(honest)
        drifted["lib/nyse_calendar.py"] = "1" * 64
        return drifted

    monkeypatch.setattr(s, "_loaded_root_modules", census)
    out = _out_dir(tmp_path)
    assert s.main(_argv(world, out)) == 2
    assert "code_identity_drift:lib/nyse_calendar.py" in capsys.readouterr().err
    receipt = json.loads((tmp_path / "attempts/attempt-001.json").read_text())
    assert receipt["outcome_stage_started"] is True
    assert receipt["outcome_values_persisted"] is False
    assert not (out / "result.json").is_file()


def test_t6f_required_subset_missing_refuses(world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    honest = s._loaded_root_modules()
    trimmed = {k: v for k, v in honest.items() if k != "engine/session_digest.py"}
    monkeypatch.setattr(s, "_loaded_root_modules", lambda: trimmed)
    assert s.main(_argv(world, _out_dir(tmp_path))) == 2
    assert "code_identity_missing_required:engine/session_digest.py" in capsys.readouterr().err


def _honest_terminal_probe(root, sha):
    return {
        "porcelain": "",
        "toplevel": str(Path(root).resolve()),
        "blobs": {p: s._sha(Path(root) / p) for p in s.TERMINAL_PINNED_FILES},
    }


def test_t7a_terminal_dependency_dirty_refuses(world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)

    def dirty(root, sha):
        probe = _honest_terminal_probe(root, sha)
        probe["porcelain"] = " M ingest/intraday_qualification.py\n"
        return probe

    monkeypatch.setattr(s, "_terminal_dependency_probe", dirty)
    assert s.main(_argv(world, _out_dir(tmp_path))) == 2
    assert "terminal_dependency_dirty" in capsys.readouterr().err
    receipt = json.loads((tmp_path / "attempts/attempt-001.json").read_text())
    assert receipt["stage"] == "inputs"
    assert receipt["outcome_values_persisted"] is False


def test_t7b_terminal_dependency_not_a_root_refuses(world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)

    def nested(root, sha):
        probe = _honest_terminal_probe(root, sha)
        probe["toplevel"] = str(tmp_path)
        return probe

    monkeypatch.setattr(s, "_terminal_dependency_probe", nested)
    assert s.main(_argv(world, _out_dir(tmp_path))) == 2
    assert "terminal_dependency_not_a_root" in capsys.readouterr().err


def test_t7c_terminal_dependency_module_blob_mismatch_refuses(world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    path = "ingest/intraday_qualification.py"

    def bad_blob(root, sha):
        probe = _honest_terminal_probe(root, sha)
        probe["blobs"][path] = "0" * 64
        return probe

    monkeypatch.setattr(s, "_terminal_dependency_probe", bad_blob)
    assert s.main(_argv(world, _out_dir(tmp_path))) == 2
    assert f"terminal_dependency_blob_mismatch:{path}" in capsys.readouterr().err


def test_t7d_terminal_dependency_calendar_blob_mismatch_refuses(world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    path = "terminal/lib/usEquitySessionProjection.json"

    def bad_blob(root, sha):
        probe = _honest_terminal_probe(root, sha)
        probe["blobs"][path] = "0" * 64
        return probe

    monkeypatch.setattr(s, "_terminal_dependency_probe", bad_blob)
    assert s.main(_argv(world, _out_dir(tmp_path))) == 2
    assert f"terminal_dependency_blob_mismatch:{path}" in capsys.readouterr().err


def test_t7e_rulings_sha_mismatch_refuses(world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    edited = tmp_path / "rulings.md"
    edited.write_bytes(b"edited")
    monkeypatch.setattr(s, "RULINGS_PATH", edited)
    assert s.main(_argv(world, _out_dir(tmp_path))) == 2
    assert "rulings_sha_mismatch" in capsys.readouterr().err
    receipt = json.loads((tmp_path / "attempts/attempt-001.json").read_text())
    assert receipt["stage"] == "admission"
    real_rulings = s.ROOT / "research/species/tti_r1b/ANALYSIS_RULINGS_V4.md"
    assert s._sha(real_rulings) == s.RULINGS_SHA256


def test_t7f_terminal_dependency_probe_failure_refuses(world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)

    def fail(_root, _sha):
        raise ValueError("terminal_dependency_probe_failed:status")

    monkeypatch.setattr(s, "_terminal_dependency_probe", fail)
    assert s.main(_argv(world, _out_dir(tmp_path))) == 2
    assert "terminal_dependency_probe_failed:status" in capsys.readouterr().err


def test_t7g_result_records_terminal_dependency_pins(world, monkeypatch, tmp_path):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    out = _out_dir(tmp_path)
    assert s.main(_argv(world, out)) == 0
    terminal = json.loads((out / "result.json").read_text())["inputs"]["terminal_dependency"]
    assert terminal["worktree_clean"] is True
    assert terminal["toplevel"] == str(world.terminal.resolve())
    expected_blobs = {
        p: s._sha(world.terminal / p) for p in s.TERMINAL_PINNED_FILES
    }
    assert terminal["pinned_blobs"] == expected_blobs


def test_t5h_result_lists_prior_attempts_and_listing_hash(run):
    attempts = run.result["attempts"]
    assert len(attempts) == 1
    listing = hashlib.sha256(
        "\n".join(sorted(p.name for p in run.attempts.iterdir() if p.is_file())).encode("utf-8")
    ).hexdigest()
    assert run.result["attempt_listing_sha256"] == listing


# --------------------------------------------------------------------------- admission

def _ledger_lines() -> list[bytes]:
    return [line for line in s.LEDGER_PATH.read_bytes().split(b"\n") if line.strip()]


def _ledger(tmp_path: Path, lines: list[bytes]) -> Path:
    path = tmp_path / "ledger.jsonl"
    path.write_bytes(b"\n".join(lines) + b"\n")
    return path


def test_a_changed_non_grid_parameter_is_refused_even_with_a_matching_receipt(tmp_path):
    cfg = dict(CFG)
    assert cfg["local_touch_atr"] == 0.5
    cfg["local_touch_atr"] = 0.6
    config = tmp_path / "config.json"
    config.write_text(json.dumps(cfg))
    assert s._grid_sha256(cfg) == s.GRID_SHA256
    receipt = json.loads(s.RECEIPT_PATH.read_text())
    receipt["config_sha256"] = hashlib.sha256(config.read_bytes()).hexdigest()
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt))
    called: list[int] = []
    with pytest.raises(ValueError, match="config_sha256_mismatch"):
        s.verify_admission(config_path=config, receipt_path=receipt_path,
                           before_input=lambda: called.append(1))
    assert not called


def test_a_ledger_line_that_is_not_utf8_is_refused(tmp_path):
    lines = _ledger_lines()
    lines.insert(3, b'{"family": "other", "note": "\xff\xfe"}')
    with pytest.raises(ValueError, match="registered_row_unparseable"):
        s.verify_admission(ledger_path=_ledger(tmp_path, lines))


def test_a_registered_row_with_a_duplicated_key_is_refused(tmp_path):
    lines = _ledger_lines()
    registered = set(s.registered_rows(b"\n".join(lines) + b"\n"))
    position = next(i for i, line in enumerate(lines) if line in registered)
    assert lines[position].endswith(b"}")
    lines[position] = lines[position][:-1] + b', "family": "entry_radar"}'
    with pytest.raises(ValueError, match="registered_row_duplicate_key"):
        s.verify_admission(ledger_path=_ledger(tmp_path, lines))


def test_a_changed_ledger_prefix_is_disclosed_not_refused(tmp_path):
    assert s.verify_admission()["ledger_prefix_matches_receipt"] is True
    lines = _ledger_lines()
    registered = set(s.registered_rows(b"\n".join(lines) + b"\n"))
    first = next(i for i, line in enumerate(lines) if line in registered)
    assert first > 0
    lines.insert(0, b'{"family": "other", "config": {"study_id": "unrelated"}}')
    admitted = s.verify_admission(ledger_path=_ledger(tmp_path, lines))
    assert admitted["ledger_prefix_matches_receipt"] is False
    assert admitted["study_cells"] == 60


def test_t8a_suite_name_mismatch_refuses_at_arguments(world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    junit = _junit(tmp_path / "junit.xml", suite="pytest")
    assert s.main(_argv(world, _out_dir(tmp_path), junit=junit)) == 2
    assert "test_receipt_not_bound_to_head" in capsys.readouterr().err
    receipt = json.loads((tmp_path / "attempts/attempt-001.json").read_text())
    assert receipt["stage"] == "arguments"
    assert receipt["finalized"] is True


def test_t8b_extra_case_in_receipt_refuses(world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    extra = [*s.REQUIRED_TEST_MODULES, "tests.test_tactical_r1b_run.Extra"]
    junit = _junit(tmp_path / "junit.xml", modules=extra)
    assert s.main(_argv(world, _out_dir(tmp_path), junit=junit)) == 2
    assert "test_receipt_case_set_mismatch" in capsys.readouterr().err


def test_t8b2_missing_case_in_receipt_refuses(world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    forged = {f"{m}::test_ok" for m in s.REQUIRED_TEST_MODULES}
    forged.add("tests.test_tactical_r1b_run.Missing::test_never_ran")
    monkeypatch.setattr(s, "_collected_test_ids", lambda files: forged)
    assert s.main(_argv(world, _out_dir(tmp_path))) == 2
    assert "test_receipt_case_set_mismatch" in capsys.readouterr().err


def test_t8c_collected_test_ids_parser(tmp_path, monkeypatch):
    tiny_root = tmp_path / "proj"
    test_dir = tiny_root / "tests"
    test_dir.mkdir(parents=True)
    (test_dir / "test_tiny.py").write_text(
        'import pytest\n'
        'def test_one():\n    pass\n'
        'def test_two():\n    pass\n'
        'class TestCls:\n'
        '    @pytest.mark.parametrize("x", [1, 2])\n'
        '    def test_param(self, x):\n        pass\n'
    )
    monkeypatch.setattr(s, "ROOT", tiny_root)
    got = _REAL_COLLECTED_TEST_IDS(["tests/test_tiny.py"])
    assert got == {
        "tests.test_tiny::test_one",
        "tests.test_tiny::test_two",
        "tests.test_tiny.TestCls::test_param[1]",
        "tests.test_tiny.TestCls::test_param[2]",
    }


def test_t8d_collection_failure_refuses(world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)

    def fail(_files):
        raise ValueError("test_collection_failed")

    monkeypatch.setattr(s, "_collected_test_ids", fail)
    assert s.main(_argv(world, _out_dir(tmp_path))) == 2
    assert "test_collection_failed" in capsys.readouterr().err


def test_t8e_result_records_expected_cases_sha256(world, monkeypatch, tmp_path):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    out = _out_dir(tmp_path)
    assert s.main(_argv(world, out)) == 0
    forged = {f"{m}::test_ok" for m in s.REQUIRED_TEST_MODULES}
    expected_sha = hashlib.sha256("\n".join(sorted(forged)).encode()).hexdigest()
    receipt = json.loads((out / "result.json").read_text())["leak_audit"]["test_receipt"]
    assert receipt["expected_cases_sha256"] == expected_sha
    assert receipt["collected_from"] == list(s.TEST_FILES)


def test_t8f_test_file_not_at_reviewed_head_refuses(world, monkeypatch, tmp_path, capsys):
    _patch(monkeypatch, world, attempt_root=tmp_path)
    real = s._reviewed_blob_sha256
    bad_path = s.TEST_FILES[0]

    def fake(code_sha, name):
        if name == bad_path:
            return "0" * 64
        return real(code_sha, name)

    monkeypatch.setattr(s, "_reviewed_blob_sha256", fake)
    assert s.main(_argv(world, _out_dir(tmp_path))) == 2
    assert f"code_identity_not_at_reviewed_head:{bad_path}" in capsys.readouterr().err
