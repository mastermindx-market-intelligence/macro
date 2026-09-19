"""HK Opportunities projection — zero-authority view-model laws."""
from __future__ import annotations

from copy import deepcopy

from engine import hk_opportunity_projection as hop


ASOF = "2026-09-08"


def _official(
    ticker: str,
    status: str,
    *,
    name: str | None = None,
    group: str = "entry_open",
) -> dict:
    return {
        "ticker": ticker,
        "name": name or ticker,
        "sector": "Fixture sector",
        "group": group,
        "entry_signal": {
            "status": status,
            "headline": f"{ticker} {status}",
        },
    }


def _discovery(
    ticker: str,
    status: str,
    *,
    origin: str = "ripening",
    source: str = "hk_signal_gate",
    definition: str = "hk_discovery_v1",
) -> dict:
    return {
        "session_date": ASOF,
        "security_ref": ticker,
        "security_ref_raw": ticker,
        "challenger_definition": definition,
        "candidate_origin": origin,
        "availability_status": status,
        "availability_source": source,
        "visible_to_user": False,
        "published_authority": False,
    }


def _attention(ticker: str, rank: int, edge_z: float = 1.0) -> dict:
    return {
        "ticker": ticker,
        "rank": rank,
        "why": ["edge_z no-gate ablation"],
        "features": {"edge_z": edge_z, "tier": "screen"},
        "authority": "display_only",
    }


def test_asof_mismatch_fails_closed_without_rows():
    out = hop.project_opportunities(
        incumbent_asof=ASOF,
        discovery_asof=ASOF,
        attention_asof="2026-09-07",
        incumbent_buy=[_official("A.HK", "buy_now")],
        discovery_rows=[_discovery("A.HK", hop.ENTRY_OPEN)],
        attention_picks=[_attention("A.HK", 1)],
    )
    assert out == {
        "schema": hop.SCHEMA,
        "market": "HK",
        "available": False,
        "reason": "source_asof_mismatch",
        "source_asof": {
            "incumbent": ASOF,
            "discovery": ASOF,
            "attention": "2026-09-07",
        },
        "lanes": {
            hop.ENTRY_OPEN: [],
            hop.PREPARING: [],
            hop.MONITOR: [],
        },
        "diagnostics": {},
    }


def test_incumbent_board_is_the_only_entry_open_authority_and_preserves_order():
    official = [
        _official("OPEN1.HK", "buy_now"),
        _official("SOON.HK", "buy_soon"),
        _official("OPEN2.HK", "partial"),
    ]
    discovery = [
        _discovery("OPEN1.HK", hop.ENTRY_OPEN),
        _discovery("SOON.HK", hop.ENTRY_OPEN),
        _discovery("OPEN2.HK", hop.ENTRY_OPEN),
        _discovery("SHADOWOPEN.HK", hop.ENTRY_OPEN),
    ]
    attention = [
        _attention("SHADOWOPEN.HK", 1),
        _attention("SOON.HK", 2),
    ]
    out = hop.project_opportunities(
        incumbent_asof=ASOF,
        discovery_asof=ASOF,
        attention_asof=ASOF,
        incumbent_buy=official,
        discovery_rows=discovery,
        attention_picks=attention,
    )
    assert [r["ticker"] for r in out["lanes"][hop.ENTRY_OPEN]] == [
        "OPEN1.HK",
        "OPEN2.HK",
    ]
    assert all(r["permission_authority"] == "official_board" for r in out["lanes"][hop.ENTRY_OPEN])
    # Discovery saying ENTRY_OPEN cannot originate official permission.
    shadow = next(r for r in out["lanes"][hop.PREPARING] if r["ticker"] == "SHADOWOPEN.HK")
    assert shadow["permission_status"] == hop.ENTRY_OPEN
    assert shadow["permission_authority"] == "discovery_shadow"
    assert shadow["lane"] == hop.PREPARING


def test_official_non_open_rows_remain_official_but_are_not_mislabeled_open():
    official = [
        _official("SOON.HK", "buy_soon"),
        _official("PULL.HK", "wait_pullback"),
        _official("HOLD.HK", "hold"),
        _official("BLOCK.HK", "blocked"),
    ]
    out = hop.project_opportunities(
        incumbent_asof=ASOF,
        discovery_asof=ASOF,
        attention_asof=ASOF,
        incumbent_buy=official,
        discovery_rows=[],
        attention_picks=[],
    )
    assert [r["ticker"] for r in out["lanes"][hop.PREPARING]] == ["SOON.HK", "PULL.HK"]
    assert [r["ticker"] for r in out["lanes"][hop.MONITOR]] == ["HOLD.HK"]
    assert "BLOCK.HK" not in {
        r["ticker"] for lane in out["lanes"].values() for r in lane
    }
    assert out["diagnostics"]["official_excluded_by_permission"] == 1


def test_attention_screen_only_intersects_existing_discovery_and_never_originates():
    discovery = [
        _discovery("PREP.HK", hop.WAIT_CONFLUENCE, origin="ripening+hk_native_onset(southbound)"),
        _discovery("PULL.HK", hop.WAIT_PULLBACK, source="knife_read"),
        _discovery("RAN.HK", hop.RAN_DONT_CHASE, source="extension_read"),
        _discovery("BLOCK.HK", hop.BLOCKED),
        _discovery("OTHERDEF.HK", hop.WAIT_CONFLUENCE, definition="some_other_challenger"),
    ]
    attention = [
        _attention("MISS.HK", 1, 2.0),
        _attention("PREP.HK", 2, 1.8),
        _attention("RAN.HK", 3, 1.7),
        _attention("PULL.HK", 4, 1.6),
        _attention("BLOCK.HK", 5, 1.5),
        _attention("OTHERDEF.HK", 6, 1.4),
    ]
    out = hop.project_opportunities(
        incumbent_asof=ASOF,
        discovery_asof=ASOF,
        attention_asof=ASOF,
        incumbent_buy=[],
        discovery_rows=discovery,
        attention_picks=attention,
    )
    assert [r["ticker"] for r in out["lanes"][hop.PREPARING]] == ["PREP.HK", "PULL.HK"]
    assert [r["ticker"] for r in out["lanes"][hop.MONITOR]] == ["RAN.HK"]
    assert out["diagnostics"]["attention_not_in_discovery"] == 2
    assert out["diagnostics"]["attention_excluded_by_permission"] == 1
    prep = out["lanes"][hop.PREPARING][0]
    assert prep["attention_rank"] == 2
    assert prep["attention_authority"] == "display_only_screen"
    assert prep["candidate_origin"] == "ripening+hk_native_onset(southbound)"
    assert "rank" not in prep
    assert "trade_rank" not in prep


def test_official_identity_wins_dedupe_and_screen_cannot_reorder_it():
    official = [
        _official("A.HK", "buy_soon"),
        _official("B.HK", "buy_soon"),
    ]
    discovery = [
        _discovery("A.HK", hop.WAIT_CONFLUENCE),
        _discovery("B.HK", hop.WAIT_CONFLUENCE),
    ]
    attention = [
        _attention("B.HK", 1, 2.0),
        _attention("A.HK", 2, 1.0),
    ]
    out = hop.project_opportunities(
        incumbent_asof=ASOF,
        discovery_asof=ASOF,
        attention_asof=ASOF,
        incumbent_buy=official,
        discovery_rows=discovery,
        attention_picks=attention,
    )
    rows = out["lanes"][hop.PREPARING]
    assert [r["ticker"] for r in rows[:2]] == ["A.HK", "B.HK"]
    assert [r["source_lane"] for r in rows[:2]] == ["incumbent_buy", "incumbent_buy"]


def test_inputs_are_not_mutated_and_projection_does_not_invent_trade_geometry():
    official = [_official("A.HK", "buy_now")]
    discovery = [_discovery("B.HK", hop.WAIT_CONFLUENCE)]
    attention = [_attention("B.HK", 1)]
    before = (deepcopy(official), deepcopy(discovery), deepcopy(attention))
    out = hop.project_opportunities(
        incumbent_asof=ASOF,
        discovery_asof=ASOF,
        attention_asof=ASOF,
        incumbent_buy=official,
        discovery_rows=discovery,
        attention_picks=attention,
    )
    assert (official, discovery, attention) == before
    forbidden = {"buy_zone", "stop", "confidence", "target", "size", "score", "trade_rank"}
    for lane in out["lanes"].values():
        for row in lane:
            assert not forbidden.intersection(row)


def test_projection_is_deterministic_for_duplicate_attention_rows():
    discovery = [_discovery("A.HK", hop.WAIT_CONFLUENCE)]
    attention = [
        _attention("A.HK", 2, 1.0),
        _attention("A.HK", 1, 9.0),
    ]
    out = hop.project_opportunities(
        incumbent_asof=ASOF,
        discovery_asof=ASOF,
        attention_asof=ASOF,
        incumbent_buy=[],
        discovery_rows=discovery,
        attention_picks=attention,
    )
    rows = out["lanes"][hop.PREPARING]
    assert len(rows) == 1
    assert rows[0]["attention_rank"] == 2
    assert rows[0]["attention_features"]["edge_z"] == 1.0

def test_attention_missing_discovery_can_only_recover_from_existing_owner_context():
    attention = [
        _attention("LEAD.HK", 1, 2.0),
        _attention("RIPE.HK", 2, 1.8),
        _attention("MISS.HK", 3, 1.6),
    ]
    context = [
        {
            "ticker": "RIPE.HK",
            "owner_context_lane": "ripening",
            "name": "Ripening fixture",
            "stance": "setup forming — no entry signal yet; watch, don't chase",
        },
        {
            "ticker": "LEAD.HK",
            "owner_context_lane": "leaders",
            "name": "Leader fixture",
            "stance": "watch — don't chase",
        },
    ]
    out = hop.project_opportunities(
        incumbent_asof=ASOF,
        discovery_asof=ASOF,
        attention_asof=ASOF,
        incumbent_buy=[],
        discovery_rows=[],
        attention_picks=attention,
        owner_context_rows=context,
    )
    assert [r["ticker"] for r in out["lanes"][hop.PREPARING]] == ["RIPE.HK"]
    assert [r["ticker"] for r in out["lanes"][hop.MONITOR]] == ["LEAD.HK"]
    assert out["lanes"][hop.ENTRY_OPEN] == []
    lead = out["lanes"][hop.MONITOR][0]
    assert lead["permission_status"] == hop.MONITOR_ONLY
    assert lead["permission_authority"] == "official_display"
    assert lead["source_lane"] == "incumbent_leaders"
    assert lead["attention_rank"] == 1
    ripe = out["lanes"][hop.PREPARING][0]
    assert ripe["permission_status"] == hop.WAIT_CONFLUENCE
    assert ripe["permission_authority"] == "official_display"
    assert out["diagnostics"]["attention_not_in_discovery"] == 3
    assert out["diagnostics"]["attention_recovered_by_owner_context"] == 2
    assert out["diagnostics"]["attention_without_context"] == 1

def test_blocked_official_identity_cannot_be_resurrected_by_screen_or_context():
    official = [_official("BLOCK.HK", "blocked")]
    attention = [_attention("BLOCK.HK", 1, 2.0)]
    context = [{
        "ticker": "BLOCK.HK",
        "owner_context_lane": "leaders",
        "stance": "watch — don't chase",
    }]
    out = hop.project_opportunities(
        incumbent_asof=ASOF,
        discovery_asof=ASOF,
        attention_asof=ASOF,
        incumbent_buy=official,
        discovery_rows=[_discovery("BLOCK.HK", hop.WAIT_CONFLUENCE)],
        attention_picks=attention,
        owner_context_rows=context,
    )
    assert all(not rows for rows in out["lanes"].values())
    assert out["diagnostics"]["official_excluded_by_permission"] == 1
    assert out["diagnostics"]["attention_shadowed_by_official"] == 1


def test_projection_cli_is_read_only_and_module_has_no_data_io_surface():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    cli = (root / "scripts" / "project_hk_opportunities.py").read_text()
    module = (root / "engine" / "hk_opportunity_projection.py").read_text()
    forbidden_cli = (
        ".to_parquet(",
        ".write_text(",
        "store.write(",
        "write_shadow(",
        "write_snapshot(",
        "append_board(",
    )
    assert not any(token in cli for token in forbidden_cli)
    assert "Path(" not in module
    assert "pandas" not in module
    assert "signal_gate" not in module
