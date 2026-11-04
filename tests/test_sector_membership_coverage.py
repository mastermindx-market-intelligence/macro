"""SIC-D-B03 — Central coverage truth: heat coverage counts, dated basket membership
disclosure, and the thin/gateable census.

Pure synthetic fixtures only — no site/ or data/ reads. Pins three disclosures:
(1) _aggregate_heat reports tile/weight coverage per sector and makes breadth ABSENT
    (not a fabricated 0) when no priced tile moved either way, while every legacy
    heat/adv/dec/breadth field keeps its pre-change formula byte-for-byte;
(2) _membership_coverage dates the roster (listed / effective at the as-of / removed /
    not-yet-added / back-projected) and reports what the crowding input actually
    received — without touching any conviction score;
(3) the confluence desks split "too few members" (n_below_min_members) from "could not
    be scored" (n_unscored), summing back to the legacy n_thin.
"""
from __future__ import annotations

from engine import sector_central as cen
from engine import subsector_confluence as sc

AS_OF = "2026-10-17"


def _rec(ticker="XLK", name="Technology", pos=10.0, phase="Recovery", signal="BUY",
         rs_rank=1, above200d=True, rs_63d=5.0, kind="sector"):
    """A bullish, washed-out cycle record (same shape as tests/test_sector_central.py)."""
    return {
        "id": ticker.lower(), "ticker": ticker, "kind": kind, "name": name,
        "accent": "#38bdf8", "group": "Growth",
        "proj": {"tilt": "tailwind", "nextTurn": "trough", "low": "2026-07", "high": "2027-01"},
        "now": {"pos": pos, "phase": phase, "phaseLabel": phase, "signal": signal,
                "osc_slope": 1.0, "rs_rank": rs_rank, "above200d": above200d, "rs_63d": rs_63d},
    }


def _mkt(risk_on=0.5, gate_factor=1.0):
    return {"risk_on": risk_on, "gate_factor": gate_factor, "state_en": "Risk-on",
            "quad_name": "Goldilocks", "liquidity": "expanding", "derisk_blended": 0.25,
            "_crowd_by_ticker": {}}


# ------------------------------------------------------------------ heat coverage ----

def test_aggregate_heat_mixed_coverage_cap_weighted():
    # mixed priced / None / zero / no-perf tiles: counts + cap-weight coverage, and the
    # unchanged (== 0) tile stays priced-but-excluded from adv/dec exactly as before.
    hm = {"size_basis": "marketcap", "tiles": [
        {"sector": "Technology", "size": 3000.0, "perf": {"1D": 1.0, "1M": 2.0, "YTD": 10.0}},
        {"sector": "Technology", "size": 1000.0, "perf": {"1D": -1.0, "1M": None, "YTD": 5.0}},
        {"sector": "Technology", "size": 1000.0, "perf": {"1D": 0.5, "1M": 0.0, "YTD": 3.0}},
        {"sector": "Technology", "size": 500.0, "perf": None},
    ]}
    row = cen._aggregate_heat(hm)["Technology"]
    assert row["n_tiles"] == 4
    assert row["n_priced_1M"] == 2               # +2.0 and the 0.0 (unchanged IS priced)
    assert row["n_unchanged_1M"] == 1
    assert row["weight_coverage_1M"] == round((3000.0 + 1000.0) / 5500.0, 4)
    assert (row["adv"], row["dec"]) == (1, 0)     # the 0.0 tile and the None tile never count
    assert row["breadth_pct"] == 100.0
    assert row["heat_1M"] == round((3000.0 * 2.0 + 1000.0 * 0.0) / 4000.0, 2)
    assert row["heat_1D"] == round((3000.0 * 1.0 + 1000.0 * -1.0 + 1000.0 * 0.5) / 5000.0, 2)
    assert row["breadth_basis"] == "adv_over_adv_plus_dec_excl_unchanged"


def test_aggregate_heat_weight_proxy_counts_tiles():
    hm = {"size_basis": "weight_proxy", "tiles": [
        {"sector": "Energy", "perf": {"1M": 1.0}},
        {"sector": "Energy", "perf": {"1M": -1.0}},
        {"sector": "Energy", "perf": {"1M": None}},
    ]}
    row = cen._aggregate_heat(hm)["Energy"]
    assert row["n_tiles"] == 3
    assert row["n_priced_1M"] == 2
    assert row["n_unchanged_1M"] == 0
    assert row["weight_coverage_1M"] == round(2 / 3, 4)   # 1 per tile, priced / all-tile
    assert row["breadth_pct"] == 50.0
    assert row["heat_1M"] == 0.0


def test_aggregate_heat_all_none_sector_breadth_is_absent_not_zero():
    hm = {"tiles": [
        {"sector": "Utilities", "size": 10.0, "perf": {"1M": None, "1D": None}},
        {"sector": "Utilities", "size": 20.0, "perf": {"1M": None}},
    ]}
    row = cen._aggregate_heat(hm)["Utilities"]
    assert row["breadth_pct"] is None              # absent — never a fabricated 0
    assert row["n_priced_1M"] == 0
    assert row["weight_coverage_1M"] == 0.0        # all-tile weight > 0, priced weight 0
    assert row["heat_1M"] is None


def test_aggregate_heat_all_unchanged_breadth_absent_coverage_full():
    hm = {"tiles": [{"sector": "Staples", "size": 5.0, "perf": {"1M": 0.0}}]}
    row = cen._aggregate_heat(hm)["Staples"]
    assert row["breadth_pct"] is None              # priced, but nothing moved either way
    assert (row["n_priced_1M"], row["n_unchanged_1M"]) == (1, 1)
    assert row["weight_coverage_1M"] == 1.0
    assert row["heat_1M"] == 0.0


def test_aggregate_heat_legacy_fields_match_prechange_formula():
    # nine priced tiles with no exact-zero 1M: every legacy field equals the original
    # cap-weighted expressions (heat = Σsz·v/Σsz over PRICED tiles; breadth = the old
    # round(100·adv/max(adv+dec,1)), identical whenever adv+dec > 0).
    tiles = [{"sector": "Financials", "size": 100.0 + 30.0 * i,
              "perf": {"1D": 0.3 * i - 0.4, "1M": 0.7 * i - 1.2, "YTD": 0.11 * i - 0.3}}
             for i in range(9)]
    row = cen._aggregate_heat({"tiles": tiles})["Financials"]
    for tf in ("1D", "1M", "YTD"):
        vals = [(t["size"], t["perf"][tf]) for t in tiles]
        w = sum(sz for sz, _ in vals)
        assert row["heat_" + tf] == round(sum(sz * v for sz, v in vals) / w, 2)
    adv = sum(1 for t in tiles if t["perf"]["1M"] > 0)
    dec = sum(1 for t in tiles if t["perf"]["1M"] < 0)
    assert (row["adv"], row["dec"]) == (adv, dec)
    assert adv + dec == 9
    assert row["breadth_pct"] == round(100.0 * adv / max(adv + dec, 1), 0)


def test_trace_breadth_text_reads_na_when_absent():
    heat = {"heat_1M": 1.5, "breadth_pct": None}
    out = cen._fuse(_rec(), _mkt(), 11, trend={"pass": True}, heat=heat)
    joined = "\n".join(l["en"] + l["zh"] for l in out["reasoning"])
    assert "breadth n/a" in joined
    assert "宽度 不可用" in joined
    assert "None%" not in joined


def test_trace_breadth_text_byte_identical_when_present():
    heat = {"heat_1M": 1.5, "breadth_pct": 57.0}
    out = cen._fuse(_rec(), _mkt(), 11, trend={"pass": True}, heat=heat)
    layer = next(l for l in out["reasoning"] if l["layer"] == "Heat")
    assert layer["en"] == "breadth 57.0% adv · +1.5% 1M (cap-wt)"
    assert layer["zh"] == "宽度 57.0% 上涨 · 近月 +1.5%（市值加权）"


def test_carry_carries_cycle_basis():
    rec = _rec()
    rec["now"]["basis"] = "price"
    assert cen._carry(rec)["cycle"]["basis"] == "price"
    assert cen._carry(_rec())["cycle"]["basis"] is None   # absent basis never raises


# ------------------------------------------------------- dated membership disclosure ----

def _spec(members):
    return {"name": "Synthetic", "members": members}


def test_membership_coverage_dated_roster():
    spec = _spec([
        # live since 2023, never touched
        {"ticker": "AAA", "added": "2023-01-01", "curated_added": "2023-01-01", "removed": None},
        # live, but the curation back-projected the add date (curated_added > added)
        {"ticker": "BBB", "added": "2026-01-01", "curated_added": "2026-06-01", "removed": None},
        # removed BEFORE the as-of → not effective
        {"ticker": "CCC", "added": "2022-01-01", "curated_added": "2022-01-01",
         "removed": "2026-06-01"},
        # removal dated AFTER the as-of → still effective at the as-of
        {"ticker": "DDD", "added": "2022-01-01", "curated_added": "2022-01-01",
         "removed": "2026-12-01"},
        # listed, but not added until after the as-of
        {"ticker": "EEE", "added": "2027-01-01", "curated_added": "2027-01-01", "removed": None},
    ])
    cov = cen._membership_coverage(spec, as_of=AS_OF, used_members=[], source_version="2026-08-07")
    assert cov["schema"] == "sector_central.basket_membership.v1"
    assert cov["as_of"] == AS_OF
    assert cov["source"] == "data/baskets/membership.json"
    assert cov["source_version"] == "2026-08-07"
    assert cov["status"] == "ok"
    assert cov["n_listed"] == 5
    assert cov["n_effective"] == 3                    # AAA, BBB, DDD
    assert cov["n_removed_by_asof"] == 1              # CCC
    assert cov["n_not_yet_added"] == 1                # EEE
    assert cov["n_back_projected"] == 1               # BBB
    assert cov["crowding_input_members"] == 0
    assert cov["crowding_input_status"] == "no_members_resolved"
    # the roster partition adds up: every listed member is effective, removed, or pending
    assert cov["n_effective"] + cov["n_removed_by_asof"] + cov["n_not_yet_added"] == cov["n_listed"]


def test_membership_coverage_symbol_keyed_member_counts():
    # member id resolves via `ticker` OR `symbol` — a symbol-keyed member is still counted,
    # and when the crowding input actually received it the status flips to resolved.
    spec = _spec([{"symbol": "XYZ", "added": "2020-01-01", "curated_added": "2020-01-01",
                   "removed": None}])
    cov = cen._membership_coverage(spec, as_of=AS_OF, used_members=["XYZ"], source_version="v")
    assert cov["status"] == "ok"
    assert cov["n_listed"] == 1
    assert cov["n_effective"] == 1
    assert cov["crowding_input_members"] == 1
    assert cov["crowding_input_status"] == "resolved"


def test_membership_coverage_unknown_basket_and_none_spec():
    cov = cen._membership_coverage(None, as_of=AS_OF, used_members=[], source_version="v")
    assert cov["status"] == "basket_not_listed"
    for k in ("n_listed", "n_effective", "n_removed_by_asof", "n_not_yet_added",
              "n_back_projected"):
        assert cov[k] is None
    # the crowding-input side is still reported — it exists independent of the roster
    assert cov["crowding_input_members"] == 0
    assert cov["crowding_input_status"] == "no_members_resolved"


def test_membership_coverage_source_unavailable():
    cov = cen._membership_coverage(cen._MEMB_SOURCE_UNAVAILABLE, as_of=AS_OF,
                                   used_members=[], source_version=None)
    assert cov["status"] == "source_unavailable"
    assert cov["n_effective"] is None
    assert cov["crowding_input_status"] == "no_members_resolved"


def test_membership_coverage_never_raises_on_junk():
    cov = cen._membership_coverage(
        {"members": ["junk", {"added": 7, "removed": []}, None]},
        as_of=None, used_members=None, source_version=None)
    assert cov["status"] == "ok"
    assert cov["n_listed"] == 3
    assert cov["crowding_input_members"] == 0


def test_disclosure_does_not_touch_conviction():
    # attach the disclosure to a fully-fused basket row and the conviction score must not
    # move: the coverage dict is a parallel disclosure, never a _fuse input.
    rec = _rec(ticker="QQQ", kind="basket")
    rec["id"] = "b-ai"
    spec = _spec([{"ticker": "AAA", "added": "2023-01-01", "curated_added": "2023-01-01",
                   "removed": None}])
    fused = cen._fuse(rec, _mkt(), 5, trend={"pass": True}, members=[])
    row_before = {**cen._carry(rec), **fused}
    cov = cen._membership_coverage(spec, as_of=AS_OF, used_members=[], source_version="v")
    row_after = {**cen._carry(rec), **fused, "membership_coverage": cov}
    assert row_after["conviction"]["score"] == row_before["conviction"]["score"]
    assert (cen._fuse(rec, _mkt(), 5, trend={"pass": True}, members=[])
            ["conviction"]["score"] == row_before["conviction"]["score"])


# ------------------------------------------------------- thin/gateable census ----

def _fake_scored(key):
    """A minimal scored-group stand-in good enough for sort/funnel/_breadth_coverage."""
    return {"key": key, "label": key, "sector": "X", "kind": "subsector",
            "as_of": AS_OF, "class": "neutral", "reliability": "high",
            "entry": {"tier": None, "weight": 0.0, "buyable": False},
            "regime": {"state": "NEUTRAL", "side": "neutral", "tailwind": False,
                       "headwind": False, "rs_60d": None},
            "members": []}


def _fake_safe(fail_label):
    def _safe(label, *args, **kw):
        return None if label == fail_label else _fake_scored(label)
    return _safe


def test_basket_confluence_census_splits_thin_causes(monkeypatch):
    memberships = {
        "big": {"name": "Big", "members": [{"ticker": t, "removed": None}
                                           for t in ("A", "B", "C", "D")]},
        "thin": {"name": "Thin", "members": [{"ticker": t, "removed": None}
                                             for t in ("E", "F")]},
        "broken": {"name": "Broken", "members": [{"ticker": t, "removed": None}
                                                 for t in ("G", "H", "I")]},
    }
    monkeypatch.setattr(sc, "_safe_score", _fake_safe("broken"))
    out = sc.compute_basket_confluence(memberships)
    cov = out["coverage"]
    assert cov["n_listed"] == 3
    assert cov["n_gateable"] == 1
    assert cov["n_baskets"] == 1                       # keeps its legacy meaning (scored)
    assert cov["n_thin"] == 2
    assert cov["n_below_min_members"] == 1             # thin: below MIN_MEMBERS
    assert cov["n_unscored"] == 1                      # broken: could not be scored
    assert cov["n_below_min_members"] + cov["n_unscored"] == cov["n_thin"]
    assert cov["n_listed"] - cov["n_gateable"] == cov["n_thin"]
    assert [b["basket_id"] for b in out["baskets"]] == ["big"]


def test_partition_census_splits_thin_causes(monkeypatch):
    subsectors = {
        "ok1": {"name": "OK1", "sector": "X", "members": ["A", "B", "C"]},
        "ok2": {"name": "OK2", "sector": "X", "members": ["D", "E", "F"]},
        "thin": {"name": "Thin", "sector": "X", "members": ["G", "H"]},
        "bad": {"name": "Bad", "sector": "X", "members": ["I", "J", "K"]},
    }
    monkeypatch.setattr(sc, "_safe_score", _fake_safe("bad"))
    out = sc._compute_partition(subsectors, {}, benchmark="SPY", universe="u",
                                region="us", notes="n")
    cov = out["coverage"]
    assert cov["n_subsectors"] == 4
    assert cov["n_gateable"] == 2
    assert cov["n_thin"] == 2
    assert cov["n_below_min_members"] == 1
    assert cov["n_unscored"] == 1
    assert cov["n_below_min_members"] + cov["n_unscored"] == cov["n_thin"]


def test_subsector_confluence_census_splits_thin_causes(monkeypatch):
    groups_map = {
        ("X", "ok1"): ["A", "B", "C"],
        ("X", "ok2"): ["D", "E", "F"],
        ("X", "thin"): ["G", "H"],
        ("X", "bad"): ["I", "J", "K"],
    }
    monkeypatch.setattr(sc.subsector_scan, "_industry_map", lambda: groups_map)
    monkeypatch.setattr(sc, "_safe_score", _fake_safe("bad"))
    out = sc.compute_subsector_confluence()
    cov = out["coverage"]
    assert cov["n_subsectors"] == 4
    assert cov["n_gateable"] == 2
    assert cov["n_thin"] == 2
    assert cov["n_below_min_members"] == 1
    assert cov["n_unscored"] == 1
    assert cov["n_below_min_members"] + cov["n_unscored"] == cov["n_thin"]
