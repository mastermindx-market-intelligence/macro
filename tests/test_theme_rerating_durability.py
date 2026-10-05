"""Named price + analyst-revision durability evidence, never a fused score."""
import numpy as np
import pandas as pd

from engine import theme_repricing_context as price
from engine import theme_rerating_durability as dur


def _tree():
    return [{
        "theme": "Semiconductors",
        "subsectors": [
            {"key": "compute", "name": "Compute", "members": ["A", "B", "C", "D"]},
            {"key": "foundry", "name": "Foundry", "members": ["E", "F", "G", "H"]},
        ],
    }]


def _price_context():
    group = {
        "compute": {"1W": 5.0, "1M": 9.0, "3M": 12.0},
        "foundry": {"1W": 3.0, "1M": 5.0, "3M": 6.0},
    }
    members = {
        "A": {"1W": 7.0, "1M": 12.0, "3M": 15.0},
        "B": {"1W": 5.0, "1M": 9.0, "3M": 12.0},
        "C": {"1W": 4.0, "1M": 8.0, "3M": 10.0},
        "D": {"1W": 3.0, "1M": 6.0, "3M": 8.0},
        "E": {"1W": 12.0, "1M": 8.0, "3M": 5.0},
        "F": {"1W": -1.0, "1M": 4.0, "3M": 4.0},
        "G": {"1W": -1.0, "1M": 3.0, "3M": 3.0},
        "H": {"1W": -1.0, "1M": 2.0, "3M": 2.0},
    }
    return price.build_context(_tree(), group, members)


def _latest(breadths):
    rows = []
    for ticker, breadth in breadths.items():
        rows.append({
            "ticker": ticker,
            "n_analysts": 6,
            "n_covering": 8,
            "breadth": breadth,
            "breadth_cov": breadth,
            "est_chg_30d": 3.0,
            "est_chg_90d": 3.0,
            "net_up_30d": 2.0,
            "asof": "2026-01-16",
        })
    return pd.DataFrame(rows).set_index("ticker")


def _history(prior, current):
    rows = []
    for stamp, vals in [("2025-12-22", prior), ("2026-01-16", current)]:
        for ticker, breadth in vals.items():
            rows.append({
                "ticker": ticker,
                "asof": stamp,
                "n_analysts": 6,
                "breadth": breadth,
            })
    return pd.DataFrame(rows)


def test_broad_price_plus_rising_revisions_is_confirming_not_a_buy_signal():
    latest = _latest({
        "A": 0.8, "B": 0.7, "C": 0.6, "D": 0.5,
        "E": 0.2, "F": 0.1, "G": 0.0, "H": -0.1,
    })
    hist = _history(
        {"A": 0.1, "B": 0.1, "C": 0.0, "D": 0.0,
         "E": 0.1, "F": 0.1, "G": 0.0, "H": 0.0},
        latest["breadth"].to_dict(),
    )
    out = dur.build_durability(_tree(), _price_context(), latest, hist)
    compute = next(row for row in out["subthemes"] if row["key"] == "compute")

    assert compute["price"]["shape"] == "broad_price_repricing"
    assert compute["revisions"]["state"] == "broadening_confirmed"
    assert compute["joint_state"] == "price_and_revisions_confirming"
    assert compute["price"]["group_residual_leader_candidate"] is not None
    assert (
        compute["price"]["group_residual_leader_candidate"]["semantics"]
        == "group_relative_leader_candidate_not_alpha"
    )
    assert compute["decision_authority"]["can_support_buy_decision"] is False
    assert out["authority"]["may_trade"] is False


def test_narrow_price_can_have_revisions_ahead_of_diffusion():
    latest = _latest({
        "A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0,
        "E": 0.8, "F": 0.7, "G": 0.6, "H": 0.5,
    })
    hist = _history(
        {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0,
         "E": 0.0, "F": 0.0, "G": 0.0, "H": 0.0},
        latest["breadth"].to_dict(),
    )
    out = dur.build_durability(_tree(), _price_context(), latest, hist)
    foundry = next(row for row in out["subthemes"] if row["key"] == "foundry")

    assert foundry["price"]["shape"] == "single_name_impulse"
    assert foundry["revisions"]["state"] == "broadening_confirmed"
    assert foundry["joint_state"] == "revisions_ahead_of_price_diffusion"


def test_price_strength_with_negative_revisions_surfaces_divergence():
    latest = _latest({
        "A": -0.8, "B": -0.7, "C": -0.6, "D": -0.5,
        "E": 0.0, "F": 0.0, "G": 0.0, "H": 0.0,
    })
    hist = _history(
        {"A": -0.4, "B": -0.3, "C": -0.2, "D": -0.1,
         "E": 0.0, "F": 0.0, "G": 0.0, "H": 0.0},
        latest["breadth"].to_dict(),
    )
    out = dur.build_durability(_tree(), _price_context(), latest, hist)
    compute = next(row for row in out["subthemes"] if row["key"] == "compute")

    assert compute["revisions"]["state"] == "negative"
    assert compute["joint_state"] == "price_revision_divergence"


def test_thin_revision_coverage_is_insufficient_not_negative():
    latest = _latest({"A": 0.9, "B": 0.8})
    latest["n_analysts"] = 2
    out = dur.build_durability(_tree(), _price_context(), latest, None)
    compute = next(row for row in out["subthemes"] if row["key"] == "compute")

    assert compute["revisions"]["state"] == "insufficient"
    assert compute["joint_state"] == "price_only_unconfirmed"
    assert "catalyst_structure" in compute["missing_named_legs"]


def test_revision_proxy_never_impersonates_pit_broadening_confirmation():
    latest = _latest({
        "A": 0.6, "B": 0.5, "C": 0.4, "D": 0.3,
        "E": 0.0, "F": 0.0, "G": 0.0, "H": 0.0,
    })
    latest.loc[["A", "B", "C", "D"], "est_chg_30d"] = 6.0
    latest.loc[["A", "B", "C", "D"], "est_chg_90d"] = 3.0

    out = dur.build_durability(_tree(), _price_context(), latest, None)
    compute = next(row for row in out["subthemes"] if row["key"] == "compute")

    assert compute["revisions"]["broadening_state"] == "INSUFFICIENT_HISTORY"
    assert compute["revisions"]["broadening_proxy"] is True
    assert compute["revisions"]["state"] == "positive_level_proxy_broadening"
    assert compute["joint_state"] == "price_leads_positive_revisions"


def test_existing_heatmap_owner_projection_can_attach_named_revision_leg():
    from engine import themes_heatmap as th
    from scripts import build_themes_heatmap as builder

    tree = _tree()
    group = {
        "compute": {"1D": 1.0, "1W": 5.0, "1M": 9.0, "3M": 12.0},
        "foundry": {"1D": 1.0, "1W": 3.0, "1M": 5.0, "3M": 6.0},
    }
    member = {
        "A": {"1W": 7.0, "1M": 12.0, "3M": 15.0},
        "B": {"1W": 5.0, "1M": 9.0, "3M": 12.0},
        "C": {"1W": 4.0, "1M": 8.0, "3M": 10.0},
        "D": {"1W": 3.0, "1M": 6.0, "3M": 8.0},
        "E": {"1W": 12.0, "1M": 8.0, "3M": 5.0},
        "F": {"1W": -1.0, "1M": 4.0, "3M": 4.0},
        "G": {"1W": -1.0, "1M": 3.0, "3M": 3.0},
        "H": {"1W": -1.0, "1M": 2.0, "3M": 2.0},
    }
    payload = th.build_themes_heatmap(tree, group, member)
    latest = _latest({
        "A": 0.8, "B": 0.7, "C": 0.6, "D": 0.5,
        "E": 0.2, "F": 0.1, "G": 0.0, "H": -0.1,
    })
    hist = _history(
        {"A": 0.1, "B": 0.1, "C": 0.0, "D": 0.0,
         "E": 0.0, "F": 0.0, "G": 0.0, "H": 0.0},
        latest["breadth"].to_dict(),
    )

    events = {
        "compute": {
            "results": {
                "n_beat": 3, "n_miss": 1, "n_inline": 0, "n_no_data": 0,
                "beat_basis": "fixture",
            },
            "guidance": {"band": "RAISING", "n_filers": 2, "basis": "fixture"},
        }
    }
    fragility = {
        "compute": {
            "crowding": {"state": "crowded"},
            "extension": {"state": "not_extended"},
            "valuation": {
                "n_members": 4,
                "n_covered": 4,
                "coverage": 1.0,
                "band_counts": {
                    "cheap": 1, "fair": 1, "stretched": 1, "extreme": 1,
                },
            },
        }
    }
    assert builder._attach_revision_durability(
        payload, tree, latest=latest, hist=hist,
        events=events, fragility=fragility,
    ) is True
    compute = next(tile for tile in payload["tiles"] if tile["t"] == "compute")
    assert compute["durability"]["joint_state"] == "price_and_revisions_confirming"
    assert compute["durability"]["events"]["state"] == "earnings_and_guidance_positive"
    assert compute["durability"]["fragility"]["crowding"]["state"] == "crowded"
    assert payload["durability"]["crowding_state_counts"]["crowded"] == 1
    assert payload["durability"]["schema"] == dur.SCHEMA
    assert payload["durability"]["authority"]["may_trade"] is False


def test_heatmap_revision_leg_is_honest_noop_when_owner_store_absent():
    from engine import themes_heatmap as th
    from scripts import build_themes_heatmap as builder

    payload = th.build_themes_heatmap(_tree(), {}, {})
    before = set(payload)
    assert builder._attach_revision_durability(
        payload, _tree(), latest=None, hist=None, events={}, fragility={}
    ) is False
    assert set(payload) == before
    assert "durability" not in payload


def test_event_confirmation_is_a_named_leg_not_part_of_joint_score():
    latest = _latest({
        "A": 0.8, "B": 0.7, "C": 0.6, "D": 0.5,
        "E": 0.0, "F": 0.0, "G": 0.0, "H": 0.0,
    })
    hist = _history(
        {"A": 0.1, "B": 0.1, "C": 0.0, "D": 0.0,
         "E": 0.0, "F": 0.0, "G": 0.0, "H": 0.0},
        latest["breadth"].to_dict(),
    )
    events = {
        "compute": {
            "season": {"n_members": 4, "n_reported": 4, "n_upcoming_14d": 0, "next": []},
            "results": {
                "n_beat": 3, "n_miss": 1, "n_inline": 0, "n_no_data": 0,
                "beat_basis": "fixture",
            },
            "guidance": {"band": "RAISING", "n_filers": 2, "basis": "fixture"},
            "limits": {"drift": "not_computed", "sympathy": "not_computed"},
        }
    }
    out = dur.build_durability(
        _tree(), _price_context(), latest, hist, event_context_by_key=events
    )
    compute = next(row for row in out["subthemes"] if row["key"] == "compute")

    assert compute["events"]["state"] == "earnings_and_guidance_positive"
    assert compute["joint_state"] == "price_and_revisions_confirming"
    assert compute["joint_scope"] == "price_plus_revisions_only"
    assert out["event_state_counts"]["earnings_and_guidance_positive"] == 1
    assert out["method"]["event_owner"] == "engine.group_earnings.member_event_context"
    assert out["authority"]["may_trade"] is False


def test_cutting_guidance_and_miss_skew_are_descriptive_negative_context_only():
    latest = _latest({
        "A": 0.8, "B": 0.7, "C": 0.6, "D": 0.5,
        "E": 0.0, "F": 0.0, "G": 0.0, "H": 0.0,
    })
    event = {
        "compute": {
            "results": {
                "n_beat": 1, "n_miss": 3, "n_inline": 0, "n_no_data": 0,
                "beat_basis": "fixture",
            },
            "guidance": {"band": "CUTTING", "n_filers": 2, "basis": "fixture"},
        }
    }
    out = dur.build_durability(
        _tree(), _price_context(), latest, None, event_context_by_key=event
    )
    compute = next(row for row in out["subthemes"] if row["key"] == "compute")

    assert compute["events"]["state"] == "earnings_and_guidance_negative"
    assert compute["decision_authority"]["can_support_exit_decision"] is False


def test_missing_event_context_is_unavailable_not_negative():
    latest = _latest({
        "A": 0.8, "B": 0.7, "C": 0.6, "D": 0.5,
        "E": 0.0, "F": 0.0, "G": 0.0, "H": 0.0,
    })
    out = dur.build_durability(_tree(), _price_context(), latest, None)
    compute = next(row for row in out["subthemes"] if row["key"] == "compute")
    assert compute["events"]["state"] == "unavailable"


def test_event_projection_precomputes_report_events_once(monkeypatch):
    from scripts import build_themes_heatmap as builder

    tree = _tree()
    calls = {"events": 0, "contexts": 0}

    def fake_events(tickers, sessions, earn, eightk):
        calls["events"] += 1
        assert set(tickers) == set("ABCDEFGH")
        return {}

    def fake_context(members, **kwargs):
        calls["contexts"] += 1
        assert kwargs["events"] == {}
        return {
            "season": {"n_members": len(members), "n_reported": 0,
                       "n_upcoming_14d": 0, "next": []},
            "results": {"n_beat": None, "n_miss": None, "n_inline": None,
                        "n_no_data": len(members), "beat_basis": "fixture"},
            "guidance": {"band": None, "n_filers": 0, "basis": "fixture"},
            "limits": {},
        }

    monkeypatch.setattr(builder.ge, "build_report_events", fake_events)
    monkeypatch.setattr(builder.ge, "member_event_context", fake_context)

    out = builder._event_context_by_key(
        tree,
        "2026-09-24",
        earn=pd.DataFrame(),
        eightk=None,
        hits=None,
    )
    assert set(out) == {"compute", "foundry"}
    assert calls == {"events": 1, "contexts": 2}


def test_fragility_context_reuses_owner_crowding_and_valuation_without_fused_score():
    from scripts import build_themes_heatmap as builder

    idx = pd.bdate_range("2025-01-02", periods=320)
    x = np.arange(len(idx), dtype=float)
    member_close = {}
    for i, ticker in enumerate("ABCDEFGH"):
        daily = 0.0010 + 0.00015 * i + 0.0012 * np.sin(x / (7.0 + i))
        member_close[ticker] = 100.0 * np.cumprod(1.0 + daily)
    closes = pd.DataFrame(member_close, index=idx)
    bench = pd.Series(
        100.0 * np.cumprod(1.0 + 0.0008 + 0.0005 * np.sin(x / 13.0)),
        index=idx,
    )
    valuation = {
        "A": {"forward_pe": 45.0},
        "B": {"forward_pe": 34.0},
        "C": {"forward_pe": 24.0},
        "D": {"forward_pe": 14.0},
        "E": {"forward_pe": 46.0},
        "F": {"forward_pe": 33.0},
        "G": {"forward_pe": 25.0},
        # H intentionally uncovered — coverage must stay explicit.
    }

    frag = builder._fragility_context_by_key(
        _tree(),
        closes=closes,
        bench_close=bench,
        valuation_by_ticker=valuation,
    )
    compute = frag["compute"]

    assert compute["authority"]["may_trade"] is False
    assert compute["decision_authority"]["can_support_exit_decision"] is False
    assert compute["basis"]["crowding_owner"] == "engine.theme_crowding.basket_crowding"
    assert compute["basis"]["valuation_owner"] == "engine.valuation.read"
    assert compute["crowding"]["n_price_covered"] == 4
    assert compute["crowding"]["state"] in {"crowded", "not_crowded"}
    assert compute["extension"]["state"] in {
        "not_extended", "stretched_present", "parabolic_present"
    }
    assert compute["valuation"]["n_covered"] == 4
    assert compute["valuation"]["coverage"] == 1.0
    assert compute["valuation"]["band_counts"] == {
        "cheap": 1, "fair": 1, "stretched": 1, "extreme": 1,
    }
    assert compute["valuation"]["watch_count"] == 1
    assert compute["valuation"]["forward_pe_covered"] == 4
    assert "score" not in compute

    latest = _latest({
        "A": 0.8, "B": 0.7, "C": 0.6, "D": 0.5,
        "E": 0.2, "F": 0.1, "G": 0.0, "H": -0.1,
    })
    out = dur.build_durability(
        _tree(),
        _price_context(),
        latest,
        None,
        fragility_context_by_key=frag,
    )
    joined = next(row for row in out["subthemes"] if row["key"] == "compute")
    assert joined["fragility"]["valuation"]["band_counts"]["extreme"] == 1
    assert "valuation" not in joined["missing_named_legs"]
    assert "crowding_fragility" not in joined["missing_named_legs"]
    assert out["method"]["crowding_owner"] == "engine.theme_crowding.basket_crowding"
    assert out["method"]["valuation_owner"] == "engine.valuation.read"


def test_fragility_valuation_coverage_does_not_infer_missing_names_are_cheap():
    from scripts import build_themes_heatmap as builder

    idx = pd.bdate_range("2025-01-02", periods=320)
    closes = pd.DataFrame(
        {
            ticker: 100.0 * np.cumprod(np.repeat(1.001 + i * 0.0001, len(idx)))
            for i, ticker in enumerate("ABCDEFGH")
        },
        index=idx,
    )
    bench = pd.Series(100.0 * np.cumprod(np.repeat(1.0008, len(idx))), index=idx)
    frag = builder._fragility_context_by_key(
        _tree(),
        closes=closes,
        bench_close=bench,
        valuation_by_ticker={"A": {"forward_pe": 45.0}},
    )
    compute = frag["compute"]["valuation"]

    assert compute["n_members"] == 4
    assert compute["n_covered"] == 1
    assert compute["coverage"] == 0.25
    assert compute["band_counts"]["extreme"] == 1
    assert compute["band_counts"]["cheap"] == 0
