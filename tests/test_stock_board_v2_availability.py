"""D03 T46: unknown source coverage is not a successful empty shadow board.

All input, output, context and ledger paths are temporary. The real builder,
template, gate functions and grader are exercised; no signal engine is replaced.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
import pytest

import engine.group_context as gcmod
from scripts import build_stock_board_v2 as v2


ROOT = Path(__file__).resolve().parents[1]
OBS = "2026-11-02"


class _Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 11, 4, 6, 0, tzinfo=timezone.utc)
        return value.astimezone(tz) if tz else value.replace(tzinfo=None)


@pytest.fixture
def site(tmp_path, monkeypatch):
    monkeypatch.setattr(gcmod, "_ROOT", tmp_path)
    monkeypatch.setattr(v2.config, "ROOT", tmp_path)
    monkeypatch.setattr(v2, "datetime", _Clock)
    site = tmp_path / "site"
    (site / "factordata").mkdir(parents=True)
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "us_stocks_v2.html.j2").write_text(
        (ROOT / "templates" / "us_stocks_v2.html.j2").read_text())
    return site


def _rich(ticker="AAA", z=0.5, tier="T2"):
    return {
        "ticker": ticker, "name": ticker, "sector": "Technology",
        "alpha": 0.5, "off_high": -3.0,
        "conviction": {"verdict": "Constructive — building", "composite_z": z,
                       "trust_tier": {"tier": "context"}, "drivers": []},
        "signal": {"eligible": True, "tier_cascade": tier, "above200": True,
                   "weekly_bull": True, "ticks": 1, "last": {"quality": "pending"}},
    }


def _inputs(rows=None):
    return ({"as_of": OBS, "buy": list(rows or []), "watch": [], "laggards": []},
            {"as_of": OBS, "buy": []})


def _write(site, name, value):
    (site / "factordata" / name).write_text(json.dumps(value))


def _write_pair(site, std, setups):
    _write(site, v2._STD, std)
    _write(site, v2._SETUPS, setups)


def _html(payload):
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    return env.get_template("us_stocks_v2.html.j2").render(
        d=payload, built="2026-11-04 06:00 UTC", rx=None)


@pytest.mark.parametrize("raw", [None, "{", "null", "[]", "true", "1", '"text"',
                                  "{}", '{"as_of":"2026-11-02"}', "NaN", "Infinity", "-Infinity"])
def test_unavailable_inputs_never_become_current_empty_result(site, raw):
    if raw is not None:
        for name in (v2._STD, v2._SETUPS):
            (site / "factordata" / name).write_text(raw)
    result = v2.compute(site)
    assert result["status"] == "unavailable"
    assert result["as_of"] is None
    assert result["source_coverage"]["state"] == "unavailable"
    assert result["lanes"] == {"entry_open": [], "setting_up": []}
    assert result["counts"] == {"entry_open": 0, "setting_up": 0, "candidates": 0}
    html = _html(result)
    assert 'data-source-state="unavailable"' in html
    assert "Sources unavailable" in html and "数据源暂不可用" in html
    assert "No names clear both gates" not in html
    assert "No imminent-cross names" not in html
    assert 'name="robots" content="noindex"' in html
    assert "SHADOW" in html


def test_unreadable_file_has_explicit_reason(site, monkeypatch):
    original = Path.read_text
    def read(path, *args, **kwargs):
        if path.name in (v2._STD, v2._SETUPS):
            raise PermissionError("fixture unreadable")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", read)
    result = v2.compute(site)
    assert result["status"] == "unavailable"
    assert {r["reason"] for r in result["source_coverage"]["sources"].values()} == {"unreadable"}


@pytest.mark.parametrize("name,key", [(v2._STD, "buy"), (v2._STD, "watch"),
                                      (v2._STD, "laggards"), (v2._SETUPS, "buy")])
@pytest.mark.parametrize("bad", [None, "bad", {}, [None], [{}], [{"ticker": []}]])
def test_malformed_consumed_collection_is_not_confirmed_empty(site, name, key, bad):
    std, setups = _inputs()
    source = std if name == v2._STD else setups
    source[key] = bad
    _write_pair(site, std, setups)
    result = v2.compute(site)
    assert result["status"] == "partial"
    assert result["as_of"] is None
    assert result["source_coverage"]["sources"][name]["collections"][key] == "invalid"
    assert result["counts"]["candidates"] == 0
    html = _html(result)
    assert "Partial coverage" in html and "覆盖不完整" in html
    assert "No names clear both gates" not in html


@pytest.mark.parametrize("missing_key", ["buy", "watch", "laggards"])
def test_omitted_standouts_collection_is_partial(site, missing_key):
    std, setups = _inputs()
    del std[missing_key]
    _write_pair(site, std, setups)
    result = v2.compute(site)
    assert result["status"] == "partial"
    assert result["source_coverage"]["sources"][v2._STD]["collections"][missing_key] == "missing"


@pytest.mark.parametrize("field,value", [
    ("conviction", None), ("conviction", "bad"),
    ("conviction.composite_z", "0.9"), ("conviction.verdict", True),
    ("conviction.trust_tier", "bad"), ("conviction.drivers", 1),
    ("signal", "bad"), ("signal.last", "bad"),
    ("signal.ticks", float("nan")), ("signal.fresh_bars", float("inf")),
    ("alpha", "bad"), ("off_high", "bad"), ("sector", []),
])
def test_malformed_row_shape_does_not_abort_and_leave_old_preview(site, field, value):
    row = _rich()
    target = row
    parts = field.split(".")
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = value
    std, setups = _inputs([row])
    _write_pair(site, std, setups)
    result = v2.compute(site)
    assert result["status"] == "partial"
    assert result["as_of"] is None
    assert result["lanes"] == {"entry_open": [], "setting_up": []}
    assert result["source_coverage"]["sources"][v2._STD]["state"] in {"partial", "unavailable"}
    # Strict JSON output remains possible even when input JSON contains nonfinite tokens.
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("available", [v2._STD, v2._SETUPS])
def test_one_source_preserves_available_candidates_but_not_full_population_claim(site, available):
    std, setups = _inputs([_rich()])
    setups["buy"] = [_rich()]
    _write(site, available, std if available == v2._STD else setups)
    result = v2.compute(site)
    assert result["status"] == "partial"
    assert result["as_of"] is None  # existing grader cannot reserve an incomplete day
    assert result["source_coverage"]["sources"][available]["as_of"] == OBS
    assert result["counts"] == {"entry_open": 1, "setting_up": 0, "candidates": 1}
    assert result["lanes"]["entry_open"][0]["ticker"] == "AAA"
    html = _html(result)
    assert "Partial coverage" in html
    assert "Available candidates" in html
    assert "stock.html?t=AAA" in html


def test_explicit_empty_sources_remain_valid_empty(site):
    _write_pair(site, *_inputs())
    result = v2.compute(site)
    assert result["status"] == "ok"
    assert result["as_of"] == OBS
    assert result["source_coverage"]["state"] == "complete"
    assert result["counts"]["candidates"] == 0
    html = _html(result)
    assert "No names clear both gates in the published inputs." in html
    assert "No imminent-cross names in the published inputs." in html
    assert "No names clear both gates today" not in html
    assert "live now" not in html


def test_undated_empty_setups_is_structurally_valid_not_a_new_gate(site):
    std, _ = _inputs([_rich()])
    std["buy"][0]["conviction"]["verdict"] = "Lagging — weak"
    _write_pair(site, std, {"buy": []})
    result = v2.compute(site)
    assert result["status"] == "ok"
    assert result["counts"] == {"entry_open": 0, "setting_up": 0, "candidates": 1}
    assert result["source_coverage"]["observation_state"] == "unknown"
    assert result["as_of"] is None


@pytest.mark.parametrize("value", [None, "", True, 1, [], {}, "2026-02-29",
                                    "2026-13-01", "2026-1-02", "2026-11-02extra",
                                    "2026-11-02T00:00:00Z", " 2026-11-02"])
def test_invalid_or_missing_source_clock_is_not_build_date(site, value):
    std, setups = _inputs([_rich()])
    std["as_of"] = value
    setups["as_of"] = value
    _write_pair(site, std, setups)
    result = v2.compute(site)
    assert result["status"] == "ok"  # clock quality never changes the dual gates
    assert result["counts"]["entry_open"] == 1
    assert result["as_of"] is None
    assert result["generated_utc"] == "2026-11-04T06:00:00Z"
    assert result["source_coverage"]["observation_state"] == "unknown"
    assert all(r["as_of"] is None for r in result["source_coverage"]["sources"].values())
    html = _html(result)
    assert "Shared observation unavailable" in html
    assert ">None<" not in html and "2026-13-01" not in html


def test_one_known_date_is_visible_without_becoming_shared_date(site):
    std, setups = _inputs([_rich()])
    std.pop("as_of")
    _write_pair(site, std, setups)
    result = v2.compute(site)
    assert result["as_of"] is None
    assert result["source_coverage"]["sources"][v2._SETUPS]["as_of"] == OBS
    assert OBS in _html(result)


@pytest.mark.parametrize("other,expected", [("2026-11-01", "mixed"),
                                           ("2030-01-01", "future")])
def test_mixed_or_future_dates_are_not_a_shared_observation(site, other, expected):
    std, setups = _inputs([_rich()])
    setups["as_of"] = other
    _write_pair(site, std, setups)
    result = v2.compute(site)
    assert result["status"] == "ok"
    assert result["as_of"] is None
    assert result["source_coverage"]["observation_state"] == expected
    assert result["source_coverage"]["sources"][v2._SETUPS]["as_of"] == other


def test_real_calendar_leap_day_is_retained(site):
    std, setups = _inputs()
    std["as_of"] = setups["as_of"] = "2024-02-29"
    _write_pair(site, std, setups)
    assert v2.compute(site)["as_of"] == "2024-02-29"


def test_valid_rows_keep_gates_order_rich_precedence_and_provisional_flags(site):
    std, setups = _inputs([_rich("AAA", 0.5), _rich("BBB", 0.9), _rich("CCC", 0.7, "T4")])
    slim = _rich("DDD")
    slim.pop("conviction")
    setups["buy"] = [_rich("AAA", 9.0), slim]
    original = deepcopy((std, setups))
    _write_pair(site, std, setups)
    result = v2.compute(site)
    assert result["status"] == "ok"
    assert result["as_of"] == OBS
    assert result["counts"] == {"entry_open": 3, "setting_up": 1, "candidates": 4}
    opened = result["lanes"]["entry_open"]
    assert [r["ticker"] for r in opened] == ["BBB", "AAA", "DDD"]
    assert [r["rank"] for r in opened] == [1, 2, 3]
    assert opened[1]["composite_z"] == 0.5
    assert opened[1]["gates_passed"] == {"what": True, "when": True, "in_setups": True}
    assert opened[2]["what"]["conviction_missing"] is True
    assert result["lanes"]["setting_up"][0]["ticker"] == "CCC"
    assert result["lanes"]["setting_up"][0]["provisional"] is True
    assert (std, setups) == original


@pytest.mark.parametrize("kind", ["missing", "malformed", "partial", "complete"])
def test_build_keeps_live_inputs_and_uses_existing_shadow_publication(site, kind):
    if kind == "malformed":
        for name in (v2._STD, v2._SETUPS):
            (site / "factordata" / name).write_text("{")
    elif kind == "partial":
        _write(site, v2._STD, _inputs([_rich()])[0])
    elif kind == "complete":
        _write_pair(site, *_inputs([_rich()]))
    (site / "us_stocks.html").write_text("LIVE PAGE SENTINEL")
    before = {p.relative_to(site): p.read_bytes() for p in site.rglob("*") if p.is_file()}
    payload = v2.build(write=True, site=site)
    after = {p.relative_to(site): p.read_bytes() for p in site.rglob("*") if p.is_file()}
    assert all(after[p] == data for p, data in before.items())
    # The existing write_page owner also materializes its two shared-shell assets.
    # This is pre-existing publication behavior, not a new T46 writer or control plane.
    assert set(after) - set(before) == {
        Path("factordata/us_standouts_v2.json"), Path("us_stocks_v2.html"),
        Path("shared_shell.css"), Path("shared_shell_bridge.js"),
    }
    assert json.loads(after[Path("factordata/us_standouts_v2.json")]) == payload
    assert 'name="robots" content="noindex"' in after[Path("us_stocks_v2.html")].decode()


@pytest.mark.parametrize("degraded", ["unavailable", "malformed", "partial", "unknown", "mixed", "future"])
def test_degraded_day_does_not_reserve_grader_snapshot_then_valid_day_can_arrive(site, monkeypatch, degraded):
    from scripts import grade_us_board as grader
    ledger = site.parent / "ledger"
    ledger.mkdir()
    live = ledger / "snapshots.jsonl"
    live.write_text("LIVE LEDGER SENTINEL")
    snaps = ledger / "snapshots_v2.jsonl"
    monkeypatch.setattr(grader, "ROOT", site.parent)
    monkeypatch.setattr(grader, "LEDGER_DIR", ledger)
    monkeypatch.setattr(grader, "V2_SNAPSHOTS_JSONL", snaps)
    monkeypatch.setattr(grader, "SNAPSHOTS_JSONL", live)
    std, setups = _inputs([_rich()])
    if degraded == "malformed":
        for name in (v2._STD, v2._SETUPS):
            (site / "factordata" / name).write_text("{")
    elif degraded == "partial":
        _write(site, v2._STD, std)
    elif degraded != "unavailable":
        if degraded == "unknown":
            std.pop("as_of")
        elif degraded == "mixed":
            setups["as_of"] = "2026-11-01"
        elif degraded == "future":
            setups["as_of"] = "2030-01-01"
        _write_pair(site, std, setups)
    unreserved = v2.compute(site)
    assert unreserved["as_of"] is None
    _write(site, v2._OUT, unreserved)
    assert grader.snapshot_v2_today() is None
    assert not snaps.exists()
    _write_pair(site, *_inputs([_rich()]))
    _write(site, v2._OUT, v2.compute(site))
    assert grader.snapshot_v2_today() == OBS
    recovered_bytes = snaps.read_bytes()
    records = [json.loads(line) for line in recovered_bytes.splitlines()]
    assert len(records) == 1
    assert records[0]["as_of"] == OBS
    assert [row["ticker"] for row in records[0]["lanes"]["entry_open"]] == ["AAA"]
    assert records[0]["lanes"]["setting_up"] == []
    assert grader.snapshot_v2_today() == OBS  # valid replays remain idempotent
    assert snaps.read_bytes() == recovered_bytes
    assert live.read_text() == "LIVE LEDGER SENTINEL"
