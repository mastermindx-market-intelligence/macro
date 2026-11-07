"""ONE coverage shape across the options family (OIP R8).

Four builders each answered "how much of the universe did we see?" differently, and one
of them (build_flow_desk) answered it in a STRING no machine could read.  No surface
could put two side by side; no audit could compare them.  ``lib/options_coverage.py``
defines the shape once and all four now emit it under ``coverage_v1``.

These tests pin: the schema, the honesty rules (unknown stays None, never 0 or a
fabricated 100%), the calendar-derived staleness (never wall-clock days), the plain-word
bilingual naming (gate 4/5: no slugs, no enums, no "n=", in either language), and — the
load-bearing part — that all four builders actually construct it, ADDITIVELY, with every
pre-existing key intact.

Run: .venv/bin/python -m pytest tests/test_options_coverage_object.py -q
"""

from __future__ import annotations

import re
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib import nyse_calendar, options_coverage  # noqa: E402

FAMILY = {
    "build_options_command": ROOT / "scripts" / "build_options_command.py",
    "build_gex_board": ROOT / "scripts" / "build_gex_board.py",
    "build_flow_desk": ROOT / "scripts" / "build_flow_desk.py",
    "build_options_screener": ROOT / "scripts" / "build_options_screener.py",
}


def _obj(**kw):
    base = dict(universe_name_en="Options names we track",
                universe_name_zh="我们跟踪的期权标的",
                universe_n=403, covered_n=370, asof="2026-07-28")
    base.update(kw)
    return options_coverage.coverage_object(**base)


# ────────────────────────────────────────────────────────────────── the schema


def test_schema_and_required_keys():
    o = _obj()
    assert o["schema"] == "options_coverage.v1"
    for k in ("schema", "universe", "covered", "coverage_pct", "asof",
              "sessions_behind", "sources"):
        assert k in o, f"missing required key {k}"
    assert set(o["universe"]) == {"name_en", "name_zh", "n"}


def test_coverage_pct_is_computed():
    assert _obj(universe_n=403, covered_n=370)["coverage_pct"] == 91.8


def test_source_row_shape():
    s = options_coverage.source("options_flow", "Options tape", "期权成交",
                                asof="2026-07-28", n=353)
    assert set(s) == {"key", "name_en", "name_zh", "asof", "n", "expected_session",
                      "sessions_behind", "status"}
    assert s["n"] == 353


def test_future_source_is_conflict_not_current():
    s = options_coverage.source("options_flow", "Options tape", "期权成交",
                                asof="2026-07-29", expected_session="2026-07-28")
    assert s["sessions_behind"] == 0
    assert s["status"] == "conflict"


# ─────────────────────────────────────────────────────────── honesty invariants


@pytest.mark.parametrize("uni,cov", [(None, 370), (403, None), (None, None), (0, 0)])
def test_an_unknown_denominator_is_null_not_a_fabricated_hundred_percent(uni, cov):
    o = _obj(universe_n=uni, covered_n=cov)
    assert o["coverage_pct"] is None, (
        "an uncountable universe must print as unknown, never as full coverage"
    )


def test_unknown_counts_stay_none_never_zero():
    """0 means 'we counted, and it was none'. None means 'we could not count'.
    Collapsing the two is how a dark feed reads as an empty market."""
    o = _obj(universe_n=None, covered_n=None)
    assert o["universe"]["n"] is None and o["covered"] is None
    s = options_coverage.source("x", "Store", "存储")
    assert s["n"] is None and s["asof"] is None and s["sessions_behind"] is None


def test_coverage_above_the_universe_is_clamped_not_published():
    o = _obj(universe_n=100, covered_n=140)
    assert o["coverage_pct"] == 100.0, "a >100% share is a counting bug, not a fact"
    assert o["covered"] == 140 and o["universe"]["n"] == 100, (
        "both raw counts must survive for inspection — clamping the SHARE, not the data"
    )


def test_no_exception_escapes_on_junk_input():
    for bad in (object(), "not-a-number", [], {}):
        o = options_coverage.coverage_object(
            universe_name_en="a", universe_name_zh="甲",
            universe_n=bad, covered_n=bad, asof=bad, sources=None)
        assert o["schema"] == "options_coverage.v1"
        assert o["coverage_pct"] is None


# ───────────────────────────────────── staleness is calendar-derived, not wall-clock


def test_sessions_behind_uses_the_exchange_calendar_not_calendar_days():
    """THE trap this guards: a store holding Friday's close is 0 sessions behind all
    weekend and on Monday morning. A wall-clock day count would call it 3 days stale
    and trip an SLA that is not actually blown."""
    friday = nyse_calendar.last_session_on_or_before(date.today())
    o = _obj(asof=friday.isoformat())
    expected = nyse_calendar.sessions_behind(friday)
    assert o["sessions_behind"] == expected
    # and it must equal what the calendar says, not (today - asof).days
    assert o["sessions_behind"] <= (date.today() - friday).days + 1


def test_sessions_behind_is_none_for_an_unparseable_stamp():
    for bad in (None, "", "not-a-date", "0000"):
        assert options_coverage._sessions_behind(bad) is None


def test_a_stale_source_reports_a_positive_lag():
    old = (date.today() - timedelta(days=40)).isoformat()
    s = options_coverage.source("x", "Store", "存储", asof=old)
    assert isinstance(s["sessions_behind"], int) and s["sessions_behind"] > 10


# ──────────────────────────────────── plain-word bilingual naming (gates 4/5)


_SLUGGY = re.compile(r"[_:]|\bn=|\bpct\b|\bidx\b|\basof\b", re.I)


def _display_names(obj) -> list[str]:
    out = [obj["universe"]["name_en"], obj["universe"]["name_zh"]]
    for s in obj["sources"]:
        out += [s["name_en"], s["name_zh"]]
    return out


def test_display_names_are_plain_words_in_both_languages():
    o = _obj(sources=[
        options_coverage.source("options_flow", "Options tape", "期权成交",
                                asof="2026-07-28", n=353),
        options_coverage.source("polygon_gex", "Option chains", "期权链",
                                asof="2026-07-28", n=403),
    ])
    for name in _display_names(o):
        assert name, "every display name must be non-empty in BOTH languages"
        assert not _SLUGGY.search(name), f"slug/enum leaked into display copy: {name!r}"


def test_zh_names_carry_no_english_state_words():
    """ZH must be independently plain — not an English name with Chinese around it."""
    o = _obj(sources=[options_coverage.source("options_flow", "Options tape", "期权成交")])
    for s in o["sources"]:
        assert not re.search(r"[A-Za-z]{3,}", s["name_zh"]), (
            f"ZH display name contains English: {s['name_zh']!r}"
        )
    assert not re.search(r"[A-Za-z]{3,}", o["universe"]["name_zh"])


def test_the_machine_key_is_separate_from_the_display_names():
    """`key` may be sluggy precisely BECAUSE it is never rendered."""
    s = options_coverage.source("options_ivspread", "Volatility vs peers", "波动率对比同业")
    assert "_" in s["key"]
    assert not _SLUGGY.search(s["name_en"]) and not _SLUGGY.search(s["name_zh"])


# ─────────────────────────────── all four builders emit it, additively


@pytest.mark.parametrize("name", sorted(FAMILY))
def test_every_family_builder_emits_the_shared_object(name):
    src = FAMILY[name].read_text()
    assert "options_coverage" in src, f"{name} does not import lib.options_coverage"
    assert '"coverage_v1"' in src or "coverage_v1" in src, \
        f"{name} does not emit the coverage_v1 key"
    assert "options_coverage.coverage_object(" in src, \
        f"{name} does not construct the shared object"


@pytest.mark.parametrize("name", sorted(FAMILY))
def test_every_family_builder_names_its_universe_bilingually(name):
    src = FAMILY[name].read_text()
    block = src.split("options_coverage.coverage_object(", 1)[1][:900]
    assert "universe_name_en=" in block and "universe_name_zh=" in block, (
        f"{name}'s coverage object must name its universe in both languages"
    )


def test_the_pre_existing_coverage_keys_survive():
    """ADDITIVE ONLY. These keys ship on live pages today; coverage_v1 must sit beside
    them, never replace them."""
    cmd = FAMILY["build_options_command"].read_text()
    for k in ('"covered"', '"universe"', '"coverage_pct"', '"quality_en"', '"quality_zh"'):
        assert k in cmd, f"build_options_command lost {k}"

    scr = FAMILY["build_options_screener"].read_text()
    for k in ('"n_names"', '"n_young"', '"median_depth_days"', '"n_skew"', '"n_ivspread"'):
        assert k in scr, f"build_options_screener lost {k}"

    fd = FAMILY["build_flow_desk"].read_text()
    assert '"coverage_note"' in fd, "build_flow_desk lost its coverage_note string"

    gb = FAMILY["build_gex_board"].read_text()
    assert 'coverage["__all__"]' in gb, "build_gex_board lost its __all__ roll-up"


def test_gex_board_key_cannot_collide_with_a_group_name():
    """build_gex_board's coverage dict is keyed by GROUP name and site/gex.js reads
    COV[grp] directly. `coverage_v1` must not be a group label."""
    gb = FAMILY["build_gex_board"].read_text()
    assert 'coverage["coverage_v1"]' in gb
    groups = re.findall(r'"(Core Index|Theme · [^"]+)"', gb)
    assert "coverage_v1" not in groups


# ──────────────────────────────────────────────── the real artifacts, if built


def test_the_screener_export_round_trips_the_object(tmp_path):
    """The export must carry whatever coverage the builder hands it — including the new
    key — without the builder having to know about the export.

    NOT asserted against the committed site/screenerdata/rows.json: that artifact is the
    last render's vintage and will not carry coverage_v1 until the next render lands, so
    an assertion on it would be red on a fresh checkout and green only by luck of local
    build order (the stale-artifact class).  The soft check below covers it when built."""
    import json

    import scripts.build_options_screener as bos

    coverage = {
        "n_names": 3, "n_young": 3, "n_mature": 0, "median_depth_days": 24,
        "young_threshold": 252, "tape_flow_present": False,
        "n_skew": 3, "n_ivspread": 2, "n_relvol": 1,
        "built": "2026-07-29 21:00 UTC",
        "coverage_v1": _obj(universe_n=3, covered_n=3, asof="2026-07-29", sources=[
            options_coverage.source("polygon_gex", "Option chains", "期权链",
                                    asof="2026-07-29", n=3)]),
    }
    out = bos.write_rows_export([{"ticker": "AAA"}], coverage,
                                out_path=tmp_path / "rows.json")
    doc = json.loads(Path(out).read_text())
    cov = doc["coverage"]
    assert cov["coverage_v1"]["schema"] == "options_coverage.v1"
    assert cov["coverage_v1"]["sources"], "the object must name its sources"
    for k in ("n_names", "n_skew", "n_ivspread", "median_depth_days"):
        assert k in cov, f"the export dropped the pre-existing key {k}"


# ─────────── MINOR 1: assert by CALLING the builders, never by skipping
#
# The first version of this section read site/screenerdata/rows.json and
# site/flow_desk.json and called `pytest.skip("predates this change")` when the key was
# absent — i.e. it skipped on exactly its own detection condition, so it could never fail.
# These call the builder functions that CONSTRUCT the object, so a removed emit reds.


def test_options_command_build_session_emits_the_object():
    """build_session() is the function that assembles the workspace's session receipt."""
    import scripts.build_options_command as boc
    stores = {"flow_desk": {"asof": "2026-07-28", "read": {"n_names": 353}},
              "screener": {"coverage": {"n_names": 400}},
              "leaders": {"session_date": "2026-07-28", "coverage": {"n_universe": 352}},
              "market_structure": {"asof": "2026-07-28"},
              "vol": {"asof": "2026-07-28"},
              "gex": {"SPX": {}, "SPY": {}},
              "gex_index": [{"key": "SPY", "asof": "2026-07-28"}]}
    sess = boc.build_session(stores, [])
    assert "coverage_v1" in sess, "build_session no longer emits coverage_v1"
    o = sess["coverage_v1"]
    assert o["schema"] == "options_coverage.v1"
    assert {s["key"] for s in o["sources"]} >= {"flow_desk", "screener", "leaders", "gex"}
    # every pre-existing session key survives
    for k in ("date", "covered", "universe", "coverage_pct", "quality_en", "quality_zh"):
        assert k in sess, f"build_session lost {k}"


def test_options_command_source_extractions_are_not_always_none():
    """MINOR 6 regression: three source rows read the wrong path and were always None —
    flow_desk's n_names lives under `read`, leaders' count under `coverage.n_universe`,
    and site/gex/index.json is a LIST that the dict reader could never parse."""
    import scripts.build_options_command as boc
    stores = {"flow_desk": {"asof": "2026-07-28", "read": {"n_names": 353}},
              "screener": None,
              "leaders": {"session_date": "2026-07-28", "coverage": {"n_universe": 352}},
              "market_structure": None, "vol": None, "gex": {},
              "gex_index": [{"key": "SPY", "asof": "2026-07-28"},
                            {"key": "QQQ", "asof": "2026-07-27"}]}
    by_key = {s["key"]: s for s in boc.build_session(stores, [])["coverage_v1"]["sources"]}
    assert by_key["flow_desk"]["n"] == 353
    assert by_key["leaders"]["n"] == 352
    assert by_key["gex"]["n"] == 2
    assert by_key["gex"]["asof"] == "2026-07-28", "the list's newest asof, not None"


def test_flow_desk_build_market_tide_emits_the_object(tmp_path):
    """build_market_tide() is the function that publishes the desk's coverage."""
    import scripts.build_flow_desk as bfd
    rows = [{"ticker": f"T{i}", "premium_mn": 10.0, "net_premium_mn": 1.0,
             "zerodte_share": 0.2, "asof": "2026-07-28"} for i in range(5)]
    tide = bfd.build_market_tide(rows, tmp_path)
    assert isinstance(tide, dict)
    assert "coverage_v1" in tide, "build_market_tide no longer emits coverage_v1"
    assert tide["coverage_v1"]["schema"] == "options_coverage.v1"
    assert "coverage_note" in tide, "the human-readable note must survive alongside"


def test_flow_desk_publishes_no_fabricated_hundred_percent(tmp_path):
    """MINOR/M8: universe_n was the covered count, so the share was 100% by construction."""
    import scripts.build_flow_desk as bfd
    rows = [{"ticker": f"T{i}", "premium_mn": 10.0, "net_premium_mn": 1.0,
             "zerodte_share": 0.2, "asof": "2026-07-28"} for i in range(5)]
    o = bfd.build_market_tide(rows, tmp_path)["coverage_v1"]
    assert o["coverage_pct"] is None, (
        "the desk does not know its denominator, so it must publish None — not 100%"
    )
    assert o["universe"]["n"] is None
    assert o["covered"] is not None


def test_gex_board_constructs_the_object_with_a_session_asof():
    """build_gex_board's coverage dict is assembled inline in main(), which needs ~700 live
    chain fetches. Exercise the CONSTRUCTION with the builder's own arguments instead of
    skipping: the load-bearing properties are the schema, the group-key safety and the
    settled-session stamp (a wall clock or in-progress session inside an honesty schema
    would be false)."""
    import scripts.build_gex_board as bgb
    src = (ROOT / "scripts" / "build_gex_board.py").read_text()
    block = src.split('coverage["coverage_v1"] = ', 1)[1][:900]
    # Strip comments before asserting on CODE. A comment saying "never date.today()" would
    # otherwise fail the very check it documents — the same prose-satisfies-a-check trap
    # that let a YAML comment convince audit_unrun_tests.py a dark suite was covered.
    code = "\n".join(ln.split("#", 1)[0] for ln in block.splitlines())
    assert code.count("asof=session_str") == 2, (
        "the envelope and source must reuse the board's one settled-session stamp"
    )
    assert "date.today()" not in code
    session_str = bgb._resolve_session().isoformat()
    o = options_coverage.coverage_object(
        universe_name_en="Symbols with liquid options",
        universe_name_zh="有活跃期权的标的",
        universe_n=646, covered_n=646,
        asof=session_str,
        sources=[options_coverage.source("cboe_chains", "Option chains", "期权链",
                                         asof=session_str, n=646)])
    assert o["schema"] == "options_coverage.v1"
    assert nyse_calendar.is_session(pd.Timestamp(o["asof"]).date()), (
        "the published asof must be a real trading session"
    )
    assert o["sessions_behind"] == 0


def test_screener_assembles_the_object_into_its_coverage_dict():
    """The screener's coverage dict is returned by assemble_rows(); the export then carries
    it verbatim (round-tripped separately above)."""
    src = (ROOT / "scripts" / "build_options_screener.py").read_text()
    body = src.split('coverage["coverage_v1"]', 1)[1][:700]
    assert "universe_n=None" in body, (
        "M8: len(rows) on both sides published a fabricated 100%"
    )
    assert "covered_n=len(rows)" in body


# Source-clock alignment is not qualification, and row as_of cannot replace it.
def _session_report(frame, *, comparison="2026-09-28", columns=("src_gex_asof", "src_skew_asof")):
    assert hasattr(options_coverage, "source_session_coverage"), "source-session coverage missing"
    return options_coverage.source_session_coverage(
        frame, comparison_session=comparison, date_columns=columns)


def test_source_sessions_do_not_inherit_newer_row_or_generation_dates():
    frame = pd.DataFrame([
        {"ticker": "AAPL", "as_of": "2026-09-29", "src_gex_asof": "2026-09-28",
         "src_skew_asof": "2026-09-23"},
        {"ticker": "MU", "as_of": "2026-09-28", "src_gex_asof": None,
         "src_skew_asof": "2026-09-28"},
    ])
    before = frame.copy(deep=True)
    report = _session_report(frame)
    assert report["sources"]["src_gex_asof"]["tickers_by_status"]["matching_session"] == ["AAPL"]
    assert report["sources"]["src_gex_asof"]["tickers_by_status"]["missing"] == ["MU"]
    assert report["sources"]["src_skew_asof"]["tickers_by_status"]["older_session"] == ["AAPL"]
    assert report["n_all_source_dates_matching"] == 0
    assert report["qualified_ticker_count"] is None
    assert report["basis"] == "source_session_alignment_only"
    pd.testing.assert_frame_equal(frame, before)


def test_source_sessions_deduplicate_identical_rows_but_refuse_conflicting_dates():
    frame = pd.DataFrame([
        {"ticker": " aapl ", "src_gex_asof": "2026-09-28"},
        {"ticker": "AAPL", "src_gex_asof": "2026-09-28"},
        {"ticker": "MU", "src_gex_asof": "2026-09-28"},
        {"ticker": "MU", "src_gex_asof": "2026-09-25"},
        {"ticker": "ARM", "src_gex_asof": "2026-09-28"},
        {"ticker": "ARM", "src_gex_asof": None},
    ])
    report = _session_report(frame, columns=("src_gex_asof",))
    source = report["sources"]["src_gex_asof"]
    assert report["n_tickers"] == 3
    assert report["n_duplicate_tickers"] == 3
    assert source["counts"]["matching_session"] == 1
    assert source["tickers_by_status"]["conflict"] == ["ARM", "MU"]
    assert sum(source["counts"].values()) == 3
    assert report["n_all_source_dates_matching"] == 1


@pytest.mark.parametrize("clock,status", [
    ("2026-09-29", "future_session"), ("2026-09-27", "invalid"),
    ("20260928", "invalid"), (True, "invalid"), (20260928, "invalid"),
    ("2026-09-28T23:00:00-04:00", "invalid"), ("not-a-date", "invalid"),
    (None, "missing"), (float("nan"), "missing"), (pd.NaT, "missing"),
    (date(2026, 9, 28), "matching_session"),
])
def test_source_sessions_classify_bad_missing_future_and_native_date_values(clock, status):
    result = _session_report(pd.DataFrame({"ticker": ["AAPL"], "src_gex_asof": [clock]}),
                             columns=("src_gex_asof",))
    assert result["sources"]["src_gex_asof"]["counts"][status] == 1
    assert result["qualified_ticker_count"] is None


def test_source_sessions_missing_column_never_falls_back_to_row_asof():
    result = _session_report(pd.DataFrame({"ticker": ["AAPL"], "as_of": ["2026-09-28"]}))
    assert result["sources"]["src_gex_asof"]["column_present"] is False
    assert result["sources"]["src_gex_asof"]["counts"]["missing"] == 1
    assert result["n_all_source_dates_matching"] == 0


def test_source_sessions_unavailable_input_is_not_zero_observed_coverage():
    for frame in (None, pd.DataFrame({"as_of": ["2026-09-28"]})):
        result = _session_report(frame)
        assert result["status"] == "unavailable"
        assert result["n_tickers"] is None
        assert result["n_all_source_dates_matching"] is None
    result = _session_report(pd.DataFrame({"ticker": [], "src_gex_asof": []}))
    assert result["status"] == "measured"
    assert result["n_tickers"] == 0


def test_source_sessions_invalid_tickers_never_inflate_unique_coverage():
    frame = pd.DataFrame({"ticker": [None, "", True, "BRK.B", "BRK-B"],
                          "src_gex_asof": ["2026-09-28"] * 5})
    result = _session_report(frame, columns=("src_gex_asof",))
    assert result["n_invalid_ticker_rows"] == 3
    assert result["n_tickers"] == 2
    assert result["sources"]["src_gex_asof"]["tickers_by_status"]["matching_session"] == ["BRK-B", "BRK.B"]


def test_source_sessions_reject_invalid_comparison_and_empty_source_set():
    frame = pd.DataFrame({"ticker": ["AAPL"]})
    with pytest.raises(ValueError, match="comparison_session"):
        _session_report(frame, comparison="2026-09-27")
    with pytest.raises(ValueError, match="date_columns"):
        _session_report(frame, columns=())


def test_source_sessions_real_audit_writer_preserves_inputs_and_uses_settled_session(tmp_path, monkeypatch):
    import json
    from datetime import datetime, timezone
    import scripts.audit_options_entry_coverage as audit

    class MondayMorning(datetime):
        @classmethod
        def now(cls, tz=None):
            instant = cls(2026, 9, 28, 14, 0, tzinfo=timezone.utc)
            return instant.astimezone(tz) if tz is not None else instant.replace(tzinfo=None)

    monkeypatch.setattr(audit, "datetime", MondayMorning)
    state = tmp_path / "data" / "options_entry" / "state.parquet"
    state.parent.mkdir(parents=True)
    pd.DataFrame({"ticker": ["AAPL", "MU"], "as_of": ["2026-09-28"] * 2,
                  "gex_confirm_verdict": ["confirm", "neutral"],
                  "src_gex_asof": ["2026-09-25", "2026-09-23"],
                  "src_skew_asof": ["2026-09-23", "2026-09-25"],
                  "src_ivspread_asof": ["2026-09-25"] * 2,
                  "src_flow_asof": ["2026-09-25"] * 2}).to_parquet(state, index=False)
    before = state.read_bytes()
    result = audit.run(root=tmp_path, write=True)
    assert "source_session_coverage" in result, "real coverage writer lacks source-clock section"
    section = result["source_session_coverage"]
    assert section["comparison_session"] == "2026-09-25"
    assert section["sources"]["src_gex_asof"]["counts"]["matching_session"] == 1
    assert section["sources"]["src_gex_asof"]["tickers_by_status"]["older_session"] == ["MU"]
    assert section["n_all_source_dates_matching"] == 0
    assert section["qualified_ticker_count"] is None
    feature = next(row for row in result["feature_coverage"]["features"]
                   if row["feature"] == "gex_confirm_verdict")
    assert feature["n_nonnull"] == 2  # preserved presence is not qualified coverage
    assert json.loads((state.parent / "coverage.json").read_text())["source_session_coverage"] == section
    assert state.read_bytes() == before


def test_source_sessions_absent_audit_inputs_report_unknown_without_writes(tmp_path):
    import scripts.audit_options_entry_coverage as audit
    result = audit.run(root=tmp_path, write=False)
    assert "source_session_coverage" in result
    assert result["source_session_coverage"]["n_tickers"] is None
    assert result["source_session_coverage"]["qualified_ticker_count"] is None
    assert not (tmp_path / "data").exists()


def test_source_sessions_non_scalar_clock_cells_are_invalid_not_a_crash():
    import numpy as np
    for clock in (["2026-09-28"], {"date": "2026-09-28"},
                  np.array(["2026-09-28", "2026-09-25"]),
                  pd.Series(["2026-09-28", "2026-09-25"])):
        frame = pd.DataFrame({"ticker": ["AAPL"], "src_gex_asof": [None]})
        frame.at[0, "src_gex_asof"] = clock
        result = _session_report(frame, columns=("src_gex_asof",))
        assert result["sources"]["src_gex_asof"]["counts"]["invalid"] == 1


@pytest.mark.parametrize("clock,status", [
    (pd.Timestamp("2026-09-28"), "matching_session"),
    (pd.Timestamp("2026-09-28T16:00:00"), "invalid"),
    (pd.Timestamp("2026-09-28T00:00:00Z"), "invalid"),
])
def test_source_sessions_naive_midnight_storage_is_not_an_instant_conversion(clock, status):
    frame = pd.DataFrame({"ticker": ["AAPL"], "src_gex_asof": [clock]})
    result = _session_report(frame, columns=("src_gex_asof",))
    assert result["sources"]["src_gex_asof"]["counts"][status] == 1


def test_source_sessions_duplicate_columns_report_unknown():
    frame = pd.DataFrame([["AAPL", "2026-09-28", "2026-09-25"]],
                         columns=["ticker", "src_gex_asof", "src_gex_asof"])
    report = _session_report(frame)
    assert report["status"] == "unavailable"
    assert report["reason"] == "ambiguous_columns"
    assert report["n_tickers"] is None


def test_source_sessions_row_order_does_not_change_the_report():
    frame = pd.DataFrame({"ticker": ["MU", "AAPL", "MU"],
                          "src_gex_asof": ["2026-09-28", "2026-09-25", "2026-09-23"]})
    assert _session_report(frame) == _session_report(frame.iloc[::-1].reset_index(drop=True))
