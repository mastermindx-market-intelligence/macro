"""Real archive pipeline tests for the offline Terminal BOATS exporter."""
import json

import pytest
import collectors.tiingo_archive as a
from lib.dataos.tiingo_reader import TiingoViewRefusal
from scripts.tiingo_chart_history import build_chart_history
from scripts.tiingo_materialize import materialize_one


@pytest.fixture
def lake(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "EXTERNAL_MOUNT", tmp_path)
    return a.Archive(tmp_path / "lake", check_mount=False, free_floor=0)


def capture(lake, rows, *, symbol="AMD", observed="2026-10-11T17:51:06Z", freq="1min"):
    saved = lake.store_response("boats-bars", symbol,
        a.request_path("boats-bars", symbol, {"resampleFreq": freq}),
        json.dumps(rows).encode(), received_at=observed)
    rec = next(json.loads(p.read_text()) for p in (lake.root / "receipts").rglob("*.json")
               if json.loads(p.read_text())["receipt_id"] == saved["receipt_id"])
    materialize_one(lake.root, rec, free_floor=0)
    return (observed[:10], saved["receipt_id"])


def bar(**changes):
    return {"date": "2026-10-09T02:00:00Z", "open": 10, "high": 12, "low": 9,
            "close": 11, "volume": 13, **changes}


def test_real_pipeline_preserves_source_values_receipt_and_utc(lake):
    ref = capture(lake, [bar()])
    out = build_chart_history("AMD", [ref], root=lake.root, check_mount=False)
    assert out["bars"] == [[1791511200, 10., 12., 9., 11., 13.]]
    assert out["bar_receipt_ids"] == [[ref[1]]]
    assert out["receipts"][0]["receipt_id"] == ref[1]
    assert out["complete"] is False and out["price_basis"] == "vendor_reported_unqualified"


def test_identical_overlap_retains_both_receipts(lake):
    a1 = capture(lake, [bar()])
    a2 = capture(lake, [bar()], observed="2026-10-12T12:00:00Z")
    out = build_chart_history("AMD", [a1, a2], root=lake.root, check_mount=False)
    assert len(out["bars"]) == 1 and out["bar_receipt_ids"] == [[a1[1], a2[1]]]


def test_conflicting_revision_refuses_entire_series(lake):
    refs = [capture(lake, [bar()]), capture(lake, [bar(close=10)], observed="2026-10-12T12:00:00Z")]
    with pytest.raises(TiingoViewRefusal, match="conflicting"):
        build_chart_history("AMD", refs, root=lake.root, check_mount=False)


@pytest.mark.parametrize("change", [{"volume": None}, {"volume": -1}, {"open": None},
    {"high": 8}, {"low": 12}, {"date": "2026-10-09T14:00:00Z"},
    {"date": "2026-10-09T02:00:01Z"}])
def test_unusable_bars_are_refused_not_dropped_or_zero_filled(lake, change):
    ref = capture(lake, [bar(**change)])
    with pytest.raises(TiingoViewRefusal):
        build_chart_history("AMD", [ref], root=lake.root, check_mount=False)


def test_wrong_symbol_and_interval_refuse(lake):
    ref = capture(lake, [bar()])
    with pytest.raises(TiingoViewRefusal):
        build_chart_history("NVDA", [ref], root=lake.root, check_mount=False)
    other = capture(lake, [bar()], freq="5min")
    with pytest.raises(TiingoViewRefusal, match="one-minute"):
        build_chart_history("AMD", [other], root=lake.root, check_mount=False)


def test_empty_raw_without_a_materialized_view_is_unavailable(lake):
    ref = capture(lake, [])
    with pytest.raises(TiingoViewRefusal, match="artifact-bound"):
        build_chart_history("AMD", [ref], root=lake.root, check_mount=False)


def test_raw_corruption_still_refused_by_incumbent_reader(lake):
    ref = capture(lake, [bar()])
    next((lake.root / "raw").rglob("*.gz")).write_bytes(b"broken")
    with pytest.raises(TiingoViewRefusal):
        build_chart_history("AMD", [ref], root=lake.root, check_mount=False)


def test_duplicate_capture_refs_are_not_coverage(lake):
    ref = capture(lake, [bar()])
    with pytest.raises(TiingoViewRefusal, match="duplicate capture"):
        build_chart_history("AMD", [ref, ref], root=lake.root, check_mount=False)


def receipt_hints(lake, ref):
    return {ref: next(p for p in (lake.root / "receipts").rglob("*.json")
                      if json.loads(p.read_text())["receipt_id"] == ref[1])}


def test_exact_receipt_hint_matches_full_scan_without_directory_scan(lake, monkeypatch):
    from pathlib import Path
    ref = capture(lake, [bar()])
    expected = build_chart_history("AMD", [ref], root=lake.root, check_mount=False)
    hints = receipt_hints(lake, ref)
    def no_scan(*args, **kwargs):
        raise AssertionError("exact receipt lookup must not scan the directory")
    monkeypatch.setattr(Path, "glob", no_scan)
    actual = build_chart_history("AMD", [ref], root=lake.root, check_mount=False, receipt_paths=hints)
    assert actual == expected


def test_receipt_hint_cannot_select_another_receipt_or_hide_raw_collision(lake):
    from lib.dataos.tiingo_reader import read_research_view
    ref = capture(lake, [bar()])
    other = capture(lake, [bar()], symbol="OTHER")
    hints = receipt_hints(lake, other)
    with pytest.raises(TiingoViewRefusal):
        build_chart_history("AMD", [ref], root=lake.root, check_mount=False,
                            receipt_paths={ref: hints[other]})
    own = receipt_hints(lake, ref)[ref]
    digest = json.loads(own.read_text())["raw_sha256"]
    with pytest.raises(TiingoViewRefusal):
        read_research_view("boats-bars", ref[0], digest, root=lake.root,
                           check_mount=False, receipt_path=own)
    # Exact receipt selection remains valid even for identical vendor payloads.
    assert build_chart_history("AMD", [ref], root=lake.root, check_mount=False,
                               receipt_paths={ref: own})["symbol"] == "AMD"


@pytest.mark.parametrize("escape", ["outside", "symlink", "missing", "wrong_day"])
def test_receipt_hint_refuses_path_evasion(lake, tmp_path, escape):
    ref = capture(lake, [bar()])
    own = receipt_hints(lake, ref)[ref]
    if escape == "outside":
        bad = tmp_path / "outside.json"; bad.write_bytes(own.read_bytes())
    elif escape == "symlink":
        bad = own.with_name("link.json"); bad.symlink_to(own)
    elif escape == "wrong_day":
        bad = own.parent.parent / "2026-10-12" / own.name
        bad.parent.mkdir(); bad.write_bytes(own.read_bytes())
    else:
        bad = own.with_name("missing.json")
    with pytest.raises(TiingoViewRefusal):
        build_chart_history("AMD", [ref], root=lake.root, check_mount=False, receipt_paths={ref: bad})


def test_receipt_hint_still_verifies_raw_and_receipt_bytes(lake):
    ref = capture(lake, [bar()]); hints = receipt_hints(lake, ref)
    p = hints[ref]; original = p.read_bytes(); r = json.loads(original)
    r["symbol"] = "OTHER"; p.write_text(json.dumps(r))
    with pytest.raises(TiingoViewRefusal):
        build_chart_history("AMD", [ref], root=lake.root, check_mount=False, receipt_paths=hints)
    p.write_bytes(original)
    next((lake.root / "raw").rglob("*.gz")).write_bytes(b"broken")
    with pytest.raises(TiingoViewRefusal):
        build_chart_history("AMD", [ref], root=lake.root, check_mount=False, receipt_paths=hints)
