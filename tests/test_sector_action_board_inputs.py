"""Captured board reducers preserve original rules and bind exact basket bytes."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from engine import sector_action_board as core

_FIXTURE = Path(__file__).parent / "fixtures" / "base_sector_action_board_b168.py"
_spec = importlib.util.spec_from_file_location("base_sector_action_board_b168", _FIXTURE)
baseline = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(baseline)


def _write_inputs(root, baskets, allocation):
    (root / "basketdata").mkdir(exist_ok=True)
    (root / "allocationdata").mkdir(exist_ok=True)
    (root / "basketdata" / "baskets.json").write_text(
        json.dumps(baskets, ensure_ascii=False), encoding="utf-8")
    (root / "allocationdata" / "allocation.json").write_text(
        json.dumps(allocation, ensure_ascii=False), encoding="utf-8")


def _inputs(overlay_reco="enter", *, count=17):
    themes = []
    for reco in ("accumulate", "enter", "hold", "trim", "avoid"):
        for i in range(count):
            themes.append({
                "id": f"{reco}-{i}", "name": f"{reco} {i}", "name_zh": f"主题{i}",
                "reco": reco, "score": 60 + i,
                "textures": {"clean_entry": {"flag": i % 3 != 0, "quality": .82},
                             "rollover_risk": {"band": "low", "band_zh": "低"}},
                "perf": {"20d": {"rel": .04}},
                "breadth": {"pct50": .7},
                "leadership": {"top": [{"ticker": "AAA"}, {"ticker": "BBB"}]},
            })
    themes.append({"id": "fallback", "name": "Fallback", "reco": "accumulate", "score": 99})
    if overlay_reco:
        for slug in ("us_sector_tech", "us_sector_health", "us_sector_unknown"):
            themes.append({"id": slug, "name": slug, "reco": overlay_reco,
                           "textures": {"clean_entry": {"flag": True}},
                           "reco_en": overlay_reco.upper(), "reco_zh": "评级"})
    baskets = {"as_of": "2026-11-04", "theme_intel": {
        "as_of": "2026-11-04", "themes": themes,
        "act_now": {"buy": [{"id": "fallback"}], "add_on_pullback": [],
                    "conflicted": [
                        {"id": "accumulate-2", "cooling": True,
                         "reason_en": "cooling", "reason_zh": "冷却"},
                        {"id": "enter-2", "reason_en": "sector Reduce", "reason_zh": "减配"},
                    ]}}}
    allocation = {"ranks": [
        {"id": row["id"], "rank": i + 1,
         "gate": {"above_200dma": i % 2 == 0}, "eligible": True,
         "durability": {"bar": "stable"}}
        for i, row in enumerate(themes)
    ], "allocation": {"weights": [{"id": "accumulate-2", "weight": .12}]}}
    timing = {}
    rules = [
        ("XLK", "now", "", ""), ("XLV", "hold", "", ""),
        ("XLC", "imminent", "", ""), ("XLY", "soon", "", ""),
        ("XLF", "exit", "", ""), ("XLI", "caution", "DON'T CHASE", ""),
        ("XLB", "caution", "UNCONFIRMED — HIGH RISK", ""),
        ("XLE", "caution", "TAKE PROFITS", ""), ("XLP", "caution", "unknown", ""),
        ("XLU", "caution", "BOTTOMING · EXTENDED — WAIT", "buy_soon"),
        ("XLRE", "caution", "BOTTOMING · UNCONFIRMED — WAIT", "buy_soon"),
        ("ZZZ", "unknown", "", ""),
    ]
    for i, (ticker, urgency, tag, hint) in enumerate(rules):
        timing[ticker] = {
            "label": "LEADER", "state": "RALLY ON", "state_style": "up",
            "entry": {"urgency": urgency, "tag": tag, "lane_hint": hint,
                      "days_hi": None if i % 2 else 4, "text": "Setup", "text_zh": "形态"},
            "age_short": "3d", "age_short_zh": "3日",
            "dc_day": 12, "buy_zone": 6, "n_holdings": 20,
        }
    notables = []
    for i in range(90):
        notables.append({
            "ticker": f"S{i}", "name": f"Company {i}", "sector": f"X{i % 8}",
            "urgency": ("now", "imminent", "exit")[i % 3],
            "eq_score": (-1 if i % 3 == 2 else 1) * (12 + i % 50),
            "alpha_z": None if i % 4 == 0 else (i % 9) / 3,
            "factor_z": (i % 4) / 2, "age_days": None if i % 5 == 0 else i % 12,
            "days": None if i % 7 == 0 else i % 9,
        })
    notables += [
        dict(notables[0], ticker="S0", alpha_z=100),
        dict(notables[1], ticker="GOOGL", name="Alphabet Inc. Class A", alpha_z=101),
        dict(notables[1], ticker="GOOG", name="Alphabet Inc. Class C", alpha_z=102),
    ]
    setups = {"sectors": [{
        "ticker": ticker, "rs_60d": .15, "above200": True, "above50": True,
        "rsi_3d": 55, "stoch_3d": 65, "rate_str": "context", "rate_pos": True,
        "season_str": "season", "season_tip": "tip",
        "two_reads_chip": {"cycle_label_en": "LEADER", "setup_label_en": "WAIT"},
    } for ticker in timing]}
    return baskets, allocation, timing, notables, setups


@pytest.mark.parametrize("overlay_reco", [None, "enter", "accumulate", "trim", "avoid", "hold"])
@pytest.mark.parametrize("count", [1, 17])
def test_literal_basket_and_board_parity(tmp_path, overlay_reco, count):
    baskets, allocation, timing, notables, setups = _inputs(overlay_reco, count=count)
    _write_inputs(tmp_path, baskets, allocation)
    expected_items = baseline.basket_action_items(tmp_path)
    actual_items = core.basket_action_items_from_inputs(baskets, allocation)
    assert actual_items == expected_items
    lookup = {row["ticker"]: row for row in setups["sectors"]}
    expected = baseline.action_board(
        deepcopy(timing), deepcopy(notables), deepcopy(expected_items), deepcopy(lookup))
    actual = core.action_board(
        deepcopy(timing), deepcopy(notables), deepcopy(actual_items), deepcopy(lookup))
    assert actual == expected
    assert actual["total"] == sum(len(actual[lane]) for lane in core.ACTION_LANES)
    assert len(actual["notable"]) <= 60
    for lane in core.ACTION_LANES:
        assert actual["more"][lane] == expected["more"][lane]


@pytest.mark.parametrize("basket_value", [None, {}, [], {"theme_intel": {}},
                                           {"theme_intel": {"themes": []}}])
@pytest.mark.parametrize("allocation_value", [None, {}, []])
def test_optional_empty_inputs_match_legacy(tmp_path, basket_value, allocation_value):
    _write_inputs(tmp_path, basket_value, allocation_value)
    assert core.basket_action_items_from_inputs(basket_value, allocation_value) == (
        baseline.basket_action_items(tmp_path))


@pytest.mark.parametrize("urgency,tag,hint", [
    ("caution", "DON'T CHASE", "buy_now"),
    ("caution", "TAKE PROFITS", "hold"),
    ("caution", "unknown", "avoid"),
    ("caution", "unknown", "invalid"),
    ("caution", "BOTTOMING · EXTENDED — WAIT", "buy_soon"),
    ("caution", "BOTTOMING · UNCONFIRMED — WAIT", "buy_soon"),
    ("now", "HALF SIZE", ""),
    ("hold", "", ""), ("unknown", "WAIT", ""),
])
def test_literal_caution_and_display_rules(urgency, tag, hint):
    timing = {"XLK": {"label": "TEST", "state": "RALLY ON",
                     "entry": {"urgency": urgency, "tag": tag, "lane_hint": hint}}}
    assert core.action_board(timing, []) == baseline.action_board(timing, [])


def test_composition_detaches_and_preserves_two_reads():
    baskets, allocation, timing, notables, setups = _inputs()
    before = deepcopy((baskets, allocation, timing, notables, setups))
    result = core.assemble_action_board_from_inputs(
        sector_timing=timing, notable=notables, baskets=baskets,
        allocation=allocation, sector_setups=setups)
    assert (baskets, allocation, timing, notables, setups) == before
    sector = next(row for lane in core.ACTION_LANES for row in result[lane]
                  if row["kind"] == "sector")
    sector["two_reads_chip"]["cycle_label_en"] = "mutated"
    result["notable"][0]["name"] = "mutated"
    assert (baskets, allocation, timing, notables, setups) == before


def test_value_composition_does_not_acquire_or_publish(monkeypatch):
    # Import the incumbent constant/ranking owners before forbidding acquisition.
    from engine import cycles, playbook, setups as setups_owner
    from lib import config, store
    assert cycles and playbook and setups_owner
    baskets, allocation, timing, notables, setups = _inputs()
    def forbidden(*args, **kwargs):
        raise AssertionError("value composition attempted ambient acquisition/publication")
    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", forbidden)
        patch.setattr(Path, "read_bytes", forbidden)
        patch.setattr(Path, "write_text", forbidden)
        patch.setattr(Path, "write_bytes", forbidden)
        patch.setattr(config, "load", forbidden)
        patch.setattr(store, "read", forbidden)
        patch.setattr(store, "upsert", forbidden)
        board = core.assemble_action_board_from_inputs(
            sector_timing=timing, notable=notables, baskets=baskets,
            allocation=allocation, sector_setups=setups)
        raw = json.dumps(baskets).encode()
        envelope = core.action_board_envelope(
            basket_raw=raw, action_board=board, generated_utc="2026-11-05T00:15:00Z")
    assert envelope["as_of"] == "2026-11-04"
    assert envelope["baskets_sha256"] == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("strict", [False, True])
def test_lookup_duplicate_and_empty_chip_policy(strict):
    rows = [
        {"ticker": "XLK", "rs_60d": 1, "two_reads_chip": {"label": "first"}},
        {"ticker": "XLK", "rs_60d": 2},
        {"ticker": "XLV", "two_reads_chip": {}},
        {"ticker": "XLF", "two_reads_chip": "legacy truthy"},
    ]
    lookup, chips = core.sector_setup_lookups({"sectors": rows}, strict=strict)
    assert lookup["XLK"] is rows[1]
    assert chips["XLK"] == {"label": "first"}
    assert ("XLV" in chips) is strict
    assert ("XLF" in chips) is (not strict)


def test_focused_lookup_skips_malformed_rows_and_attaches_only_sectors():
    lookup, chips = core.sector_setup_lookups({"sectors": [
        None, [], "bad", {}, {"ticker": "XLK", "two_reads_chip": {"label": "A"}}]})
    assert set(lookup) == {"XLK"}
    board = {"buy_now": [None, "bad", {"ticker": "XLK", "kind": "theme"},
                         {"ticker": "XLK", "kind": "sector"}]}
    core.attach_two_reads(board, chips)
    assert "two_reads_chip" not in board["buy_now"][2]
    assert board["buy_now"][3]["two_reads_chip"] == {"label": "A"}


@pytest.mark.parametrize("raw", [
    b'{"as_of":"2026-11-04","theme_intel":{"as_of":"2026-11-04"}}',
    b'{ "theme_intel": {"as_of": "2026-11-04"}, "as_of": "2026-11-04" }\n',
    '{"as_of":"2026-11-04T00:00:00Z","theme_intel":{"as_of":"2026-11-04T00:00:00Z"},"name":"主题"}'.encode(),
])
def test_envelope_matches_literal_writer_and_exact_bytes(tmp_path, monkeypatch, raw):
    source = tmp_path / "baskets.json"
    source.write_bytes(raw)
    board = {"buy_now": [{"ticker": "XLK", "kind": "sector"}], "total": 1}
    writes = []
    monkeypatch.setattr(baseline, "_atomic_json_write", lambda p, v: writes.append((p, v)))
    expected = baseline.write_action_board(
        tmp_path / "out.json", baskets_path=source, action_board=board,
        generated_utc="2026-11-05T00:15:00Z")
    actual = core.action_board_envelope(
        basket_raw=raw, action_board=board, generated_utc="2026-11-05T00:15:00Z")
    assert actual == expected
    assert actual["baskets_sha256"] == hashlib.sha256(raw).hexdigest()
    actual["action_board"]["buy_now"][0]["ticker"] = "mutated"
    assert board["buy_now"][0]["ticker"] == "XLK"
    assert len(writes) == 1


@pytest.mark.parametrize("raw", [
    b"", b"{", b"[]", b"null", b'{"as_of":"2026-11-04"}',
    b'{"as_of":"2026-11-04","theme_intel":{"as_of":"2026-11-03"}}',
    b'{"as_of":"bad","theme_intel":{"as_of":"bad"}}', b"\xff",
])
def test_invalid_basket_bytes_refused_by_original_and_shared(tmp_path, monkeypatch, raw):
    source = tmp_path / "baskets.json"
    source.write_bytes(raw)
    board = {"hold": [{"ticker": "XLK"}], "total": 1}
    def forbidden(*args):
        raise AssertionError("invalid input must not be published")
    monkeypatch.setattr(baseline, "_atomic_json_write", forbidden)
    with pytest.raises(baseline.ActionBoardContractError):
        baseline.write_action_board(tmp_path / "out.json", baskets_path=source,
                                    action_board=board, generated_utc="clock")
    with pytest.raises(core.ActionBoardContractError):
        core.action_board_envelope(basket_raw=raw, action_board=board, generated_utc="clock")


@pytest.mark.parametrize("board", [
    None, [], {}, {"notable": [{"ticker": "AAA"}], "total": 1},
    {"hold": [{"ticker": "XLK"}], "total": 0},
    {"hold": [{"ticker": "XLK"}], "total": -1},
    {"hold": "not rows", "total": 1},
])
def test_invalid_board_is_refused_before_publication(tmp_path, monkeypatch, board):
    source = tmp_path / "missing.json"
    with pytest.raises(baseline.ActionBoardContractError):
        baseline.write_action_board(tmp_path / "out.json", baskets_path=source,
                                    action_board=board, generated_utc="clock")
    with pytest.raises(core.ActionBoardContractError):
        core.action_board_envelope(basket_raw=b"{}", action_board=board, generated_utc="clock")


@pytest.mark.parametrize("total", [None, "1", True, 1])
def test_legacy_effective_total_contract_is_preserved(tmp_path, monkeypatch, total):
    raw = b'{"as_of":"2026-11-04","theme_intel":{"as_of":"2026-11-04"}}'
    source = tmp_path / "baskets.json"
    source.write_bytes(raw)
    board = {"hold": [{"ticker": "XLK"}], "total": total}
    monkeypatch.setattr(baseline, "_atomic_json_write", lambda *a: None)
    assert core.action_board_envelope(
        basket_raw=raw, action_board=board, generated_utc="clock") == baseline.write_action_board(
            tmp_path / "out.json", baskets_path=source, action_board=board, generated_utc="clock")


def test_legacy_writer_retains_shared_error_and_literal_envelope(tmp_path, monkeypatch):
    from scripts import build_sector_action_board as legacy
    assert legacy.ActionBoardContractError is core.ActionBoardContractError
    raw = '{"as_of":"2026-11-04","theme_intel":{"as_of":"2026-11-04"},"name":"主题"}'.encode()
    source = tmp_path / "baskets.json"
    source.write_bytes(raw)
    board = {"hold": [{"ticker": "XLK", "name": "科技"}], "total": 1}
    old_writes, new_writes = [], []
    monkeypatch.setattr(baseline, "_atomic_json_write", lambda p, v: old_writes.append((p, v)))
    monkeypatch.setattr(legacy, "_atomic_json_write", lambda p, v: new_writes.append((p, v)))
    output = tmp_path / "out.json"
    expected = baseline.write_action_board(
        output, baskets_path=source, action_board=board, generated_utc="clock")
    actual = legacy.write_action_board(
        output, baskets_path=source, action_board=board, generated_utc="clock")
    assert actual == expected
    assert new_writes == old_writes == [(output, expected)]


@pytest.mark.parametrize("board", [
    None, [], {}, {"notable": [{"ticker": "AAA"}], "total": 1},
    {"hold": [{"ticker": "XLK"}], "total": 0},
])
def test_legacy_invalid_board_never_reads_the_basket_source(tmp_path, monkeypatch, board):
    from scripts import build_sector_action_board as legacy
    def forbidden(*args, **kwargs):
        raise AssertionError("invalid board must be refused before the basket read")
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(legacy, "_atomic_json_write", forbidden)
    with pytest.raises(legacy.ActionBoardContractError, match="action_board (must|carries)"):
        legacy.write_action_board(tmp_path / "out.json", baskets_path=tmp_path / "baskets.json",
                                  action_board=board, generated_utc="clock")
