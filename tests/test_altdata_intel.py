"""Tests for the Signal Intelligence layer — newly-activated Quiver feeds, the weighted
convergence kernel, the multi-actor influence graph, the Opus brain, and the Mastermind
emit. No network, no LLM (the brain call is injected)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import altdata_models as M
from engine import altdata_brain as B
from engine import altdata_emit as EM
from engine import altdata_signals
from engine.influence import graph as IG
from lib import config


def _days_ago(days: int) -> str:
    """ISO date `days` before today (UTC) — NEVER hardcode a windowed feed date.

    ``engine/altdata_models.py:244`` keeps only rows with
    ``date >= _now() - window_days``, reading the real clock at :83-84.  A
    literal grant date is a scheduled red, and pushing ``window_days`` out to
    3650 to survive it (the prior half-defuse here) has a second cost: the
    SHIPPING default of 120 (:228) then never runs in any test, so a regression
    in the product window is invisible.  Three days is inside the real default
    at any clock, which is what puts that default back under test.
    """
    return (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)).date().isoformat()


# =========================================================================== new feeds
def test_app_ratings_momentum(monkeypatch):
    df = pd.DataFrame([
        {"Ticker": "AAA", "App": "Big App", "Rating": 4.6, "Count": 5000, "Time": "2026-06-13"},
        {"Ticker": "AAA", "App": "Tiny", "Rating": 3.0, "Count": 10, "Time": "2026-06-13"},
        {"Ticker": "BBB", "App": "Meh", "Rating": 3.2, "Count": 2000, "Time": "2026-06-13"},
    ])
    monkeypatch.setattr(M, "_read", lambda ds: df if ds == "appratings" else None)
    rows = M.app_ratings_momentum()
    aaa = next(r for r in rows if r["ticker"] == "AAA")
    assert aaa["reviews"] == 5010
    assert aaa["rating"] == pytest.approx((4.6 * 5000 + 3.0 * 10) / 5010, abs=0.01)
    assert aaa["lean"] == "strong"                       # >=4.3 rating AND >=1000 reviews
    assert next(r for r in rows if r["ticker"] == "BBB")["lean"] == "soft"   # rating < 3.5


def test_patent_velocity(monkeypatch):
    recent = _days_ago(3)
    df = pd.DataFrame(
        [{"Ticker": "QCOM", "Date": recent, "IPC": f"H04L9/4{i}", "Title": "x"} for i in range(4)]
        + [{"Ticker": "AAA", "Date": recent, "IPC": "G06F", "Title": "y"}])
    monkeypatch.setattr(M, "_read", lambda ds: df if ds == "patents" else None)
    rows = M.patent_velocity()   # the SHIPPING 120d default, no override
    q = next(r for r in rows if r["ticker"] == "QCOM")
    assert q["patents"] == 4 and q["ipc_classes"] >= 1


def test_bill_catalysts_sector_map(monkeypatch):
    df = pd.DataFrame([
        {"title": "Defense Appropriations", "summary": "funds the armed forces and missile defense",
         "billType": "HR", "number": "1", "currentChamber": "House", "lastActionDate": "2026-06-10",
         "url": "u", "lastAction": "Reported"},
        {"title": "Generic Naming Act", "summary": "renames a post office, nothing market-relevant",
         "billType": "HR", "number": "2", "currentChamber": "House", "lastActionDate": "2026-06-09",
         "url": "u", "lastAction": "x"},
    ])
    monkeypatch.setattr(M, "_read", lambda ds: df if ds == "bills" else None)
    rows = M.bill_catalysts()
    assert len(rows) == 1 and rows[0]["sector"] == "Defense"     # only the sector-mapped bill


def test_congress_holdings_parse(monkeypatch):
    df = pd.DataFrame([
        {"Politician": "A", "Holdings": '{"AAA": 24000, "BBB": 8000}', "Type": "Rep"},
        {"Politician": "B", "Holdings": '{"AAA": -40000}', "Type": "Sen"},   # |abs| size
        {"Politician": "C", "Holdings": "not json", "Type": "Rep"},          # skipped, no crash
    ])
    monkeypatch.setattr(M, "_read", lambda ds: df if ds == "congressholdings" else None)
    agg = M.congress_holdings()
    assert agg["AAA"]["position_usd"] == 64000 and agg["AAA"]["holders"] == 2


# =========================================================================== convergence kernel
def test_channel_records_upgrades_and_weights(monkeypatch):
    monkeypatch.setattr(M, "_dpi_z_lookup", lambda: {})
    signals = {
        "political": {"buys": [{"ticker": "AAA", "net": 5, "members": 4},
                               {"ticker": "BBB", "net": 1, "members": 1}]},
        "gov_contracts": [{"ticker": "AAA", "total_usd": 1e8, "accel_x": 3.0}],
        "insiders": {"buys": [{"ticker": "AAA", "net_usd": 1e6, "buyers": 4}]},
        "inst_13f": {"adds": [{"ticker": "AAA", "fund": "Berkshire Hathaway", "chg_usd": 5e6}]},
    }
    recs = M.channel_records(signals)
    aaa = recs["AAA"]
    # every strong read is UPGRADED and replaces its weaker base channel
    assert "congress_cluster" in aaa["channels"] and "congress_buy" not in aaa["channels"]
    assert "gov_contract_accel" in aaa["channels"] and "gov_contract" not in aaa["channels"]
    assert "insider_cluster" in aaa["channels"] and "insider_buy" not in aaa["channels"]
    assert "smart_money_13f" in aaa["channels"] and "13f_add" not in aaa["channels"]
    assert aaa["weighted_score"] == pytest.approx(1.0 + 0.9 + 0.85 + 0.8, abs=0.01)
    assert recs["BBB"]["channels"] == ["congress_buy"]          # single member, not a cluster


def test_channel_records_gov_accel_floor(monkeypatch):
    monkeypatch.setattr(M, "_dpi_z_lookup", lambda: {})
    # huge accel ratio but tiny absolute $ -> NOT an accel channel (floor kills the noise)
    recs = M.channel_records({"gov_contracts": [{"ticker": "AAA", "total_usd": 1000, "accel_x": 10.0}]})
    assert recs["AAA"]["channels"] == ["gov_contract"]


def test_channel_records_affiliation_channel(monkeypatch):
    monkeypatch.setattr(M, "_dpi_z_lookup", lambda: {})
    recs = M.channel_records({"political": {"buys": [{"ticker": "AAA", "net": 1, "members": 1}]}},
                             affiliations={"AAA": "Elon Musk controls"})
    assert "affiliation" in recs["AAA"]["channels"] and recs["AAA"]["count"] == 2


def test_by_ticker_uses_weighted_kernel(monkeypatch):
    monkeypatch.setattr(M, "_dpi_z_lookup", lambda: {})
    monkeypatch.setattr(altdata_signals, "_write", lambda out: None)
    feed = {"as_of": "2026-06-19", "signals": {
        "political": {"buys": [{"ticker": "AAA", "net": 5, "members": 4}]},
        "insiders": {"buys": [{"ticker": "AAA", "net_usd": 1e6, "buyers": 4}]},
    }}
    out = altdata_signals.build(feed, affiliations={"AAA": "Cathie Wood holds"})
    aaa = out["tickers"]["AAA"]
    assert aaa["convergence_score"] == 3                        # cluster + insider_cluster + affiliation
    assert aaa["weighted_score"] > 2.0 and aaa["affiliated"] is True
    assert out["schema"] == "altdata.by_ticker.v2"


# =========================================================================== influence graph
_INTEL = {"as_of": "2026-06-19",
          "people": [{"id": "eric_trump", "name": "Eric Trump"}],
          "themes": {"crypto": {"en": "Crypto", "zh": "加密"}},
          "entities": [{"id": "abtc", "name": "American Bitcoin", "ticker": "ABTC", "brand_theme": "crypto"}],
          "edges": [{"src": "eric_trump", "rel": "CONTROLS", "dst": "abtc", "confidence": 0.9, "provenance": "FACT"}]}
_SEED = {"schema": "influence.seed.v1", "as_of": "2026-06-19",
         "actors": [
             {"id": "musk", "name": "Elon Musk", "kind": "exec", "tickers": ["TSLA"]},
             {"id": "pelosi", "name": "Nancy Pelosi", "kind": "politician", "tickers": ["NVDA"]},
         ],
         "themes": {"ev": {"en": "EV", "zh": "电动车"}},
         "entities": [{"id": "tesla", "name": "Tesla", "ticker": "TSLA", "brand_theme": "ev"}],
         "edges": [
             {"src": "pelosi", "rel": "HOLDS_STAKE", "dst": "ticker:NVDA", "confidence": 0.9, "provenance": "DISCLOSED"},
             {"src": "musk", "rel": "TALKS_ABOUT", "dst": "theme:ev", "confidence": 0.7, "provenance": "INFERRED"},
         ]}


def _seed_dirs(tmp_path):
    (tmp_path / "data" / "trumpflow").mkdir(parents=True)
    (tmp_path / "data" / "altdata").mkdir(parents=True)
    (tmp_path / "data" / "trumpflow" / "intel.json").write_text(json.dumps(_INTEL))
    (tmp_path / "data" / "altdata" / "influence_seed.json").write_text(json.dumps(_SEED))


def test_influence_merge_and_kind_aware_synthesis(tmp_path):
    _seed_dirs(tmp_path)
    g = IG.load_seed(root=tmp_path)
    ids = {a["id"] for a in g["actors"]}
    assert {"eric_trump", "musk", "pelosi"} <= ids                # Trump cohort merged in
    affil = IG.affiliations(g)
    # exec -> CONTROLS from .tickers; politician -> NOT control (explicit HOLDS_STAKE wins)
    tsla = {a["rel"] for a in affil["TSLA"]}
    nvda = {a["rel"] for a in affil["NVDA"]}
    assert "CONTROLS" in tsla and "CONTROLS" not in nvda
    assert "HOLDS_STAKE" in nvda


def test_influence_label_mismatch(tmp_path, monkeypatch):
    # ABTC branded crypto but its OPERATED_BY/MEMBER_OF parent is in AI infra -> repoint
    intel = {"as_of": "x", "people": [{"id": "p", "name": "P"}],
             "themes": {"crypto": {"en": "Crypto"}, "ai": {"en": "AI"}},
             "entities": [{"id": "abtc", "name": "ABTC", "ticker": "ABTC", "brand_theme": "crypto"},
                          {"id": "hut", "name": "Hut 8", "ticker": "HUT", "brand_theme": "crypto"}],
             "edges": [{"src": "abtc", "rel": "OPERATED_BY", "dst": "hut", "confidence": 0.9, "provenance": "FACT"},
                       {"src": "hut", "rel": "MEMBER_OF", "dst": "theme:ai", "confidence": 0.85, "provenance": "INFERRED"}]}
    (tmp_path / "data" / "trumpflow").mkdir(parents=True)
    (tmp_path / "data" / "altdata").mkdir(parents=True)
    (tmp_path / "data" / "trumpflow" / "intel.json").write_text(json.dumps(intel))
    g = IG.load_seed(root=tmp_path)
    mm = IG.label_mismatches(g)
    assert any(m["entity_ticker"] == "ABTC" and m["repointed_ticker"] == "HUT" for m in mm)


# =========================================================================== brain
def test_brain_derive_check():
    assert B._derive_check("AAA", "overweight", 63, 0.05)["op"] == "<"
    assert B._derive_check("AAA", "avoid", 63, 0.05)["op"] == ">"
    assert B._derive_check("AAA", "overweight", 63, 0.05)["subject_ticker"] == "AAA"


def test_brain_reconcile_clamps():
    # _reconcile clamps the LLM to a deterministic ceiling derived from cluster
    # evidence (weighted_score / extended / rs_vs_spy_60d) — the extended hard
    # block is defense-in-depth behind that ceiling, so the audit witness cites
    # the ceiling, not the flag (full clamp matrix: test_altdata_brain_reconcile.py).
    # t1 vs t3 differ only in `extended`: the flag alone forfeits the buy.
    t1 = B._reconcile({"action": "ACCUMULATE", "extended": True, "lean": "overweight",
                       "weighted_score": 1.2, "rs_vs_spy_60d": 5.0})
    assert t1["action"] == "WATCH" and "clamped" in t1
    assert t1["det_baseline"]["action"] == "WATCH"
    t2 = B._reconcile({"action": "ACCUMULATE", "extended": False, "lean": "avoid",
                       "weighted_score": 1.2, "rs_vs_spy_60d": -10.0})
    assert t2["action"] == "AVOID"
    t3 = B._reconcile({"action": "ACCUMULATE", "extended": False, "lean": "overweight",
                       "weighted_score": 1.2, "rs_vs_spy_60d": 5.0})
    assert t3["action"] == "ACCUMULATE" and "clamped" not in t3       # legitimate buy untouched


def test_brain_synthesize_mocked(tmp_path, monkeypatch):
    # synthesize emits article3 governance events via append_event(root=None)
    # → config.data_dir(); redirect so they land in tmp, not the real
    # data/neuralweb/governance.jsonl.
    from lib import config
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path / "data")

    state = {"as_of": "2026-06-19", "n_clusters": 1, "clusters": [
        {"ticker": "AAA", "weighted_score": 1.5, "channels": ["x"], "rs_vs_spy_60d": 5,
         "extended": False, "scorable": True}]}
    reply = json.dumps({"regime_read": "aligned", "theses": [
        {"ticker": "AAA", "lean": "overweight", "conviction": "high", "action": "ACCUMULATE",
         "horizon_d": 63, "thesis": "t", "second_order": ["S1"], "evidence": ["e"],
         "dissent": "d", "falsifier_text": "f"}]})
    brief = B.synthesize(state, call=lambda sysp, usr: (reply, None))
    assert brief["regime_read"] == "aligned" and len(brief["theses"]) == 1
    th = brief["theses"][0]
    assert th["action"] == "ACCUMULATE" and th["falsifier"]["check"]["subject_ticker"] == "AAA"
    assert th["second_order"] == ["S1"]


def test_brain_no_call_degrades(tmp_path, monkeypatch):
    from lib import config
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path / "data")

    brief = B.synthesize({"as_of": "x", "n_clusters": 0, "clusters": []}, call=None)
    assert brief["degraded_reason"] == "no_client_or_token" and brief["theses"] == []


def test_brain_ledger_logs_only_scorable(tmp_path, monkeypatch):
    idx = pd.date_range("2026-01-01", "2026-05-01", freq="B")
    n = len(idx)

    def closes(tk, root):
        if tk == "SPY":
            return pd.Series([100 * (1 + 0.05 * i / n) for i in range(n)], index=idx)
        if tk == "WIN":
            return pd.Series([50 * (1 + 0.2 * i / n) for i in range(n)], index=idx)
        return None                                          # PRIV has no price -> unscorable
    monkeypatch.setattr(B._desk, "_close_series", closes)
    brief = {"generated_at": "2026-01-02T00:00:00Z", "state_asof": "2026-01-02", "theses": [
        {"ticker": "WIN", "lean": "overweight", "conviction": "high", "action": "ACCUMULATE",
         "horizon_d": 63, "scorable": True,
         "falsifier": {"text": "x", "check": B._derive_check("WIN", "overweight", 63, 0.05)},
         "check_by": "2026-04-03"},
        {"ticker": "PRIV", "lean": "overweight", "conviction": "low", "action": "WATCH",
         "horizon_d": 63, "scorable": True,
         "falsifier": {"text": "x", "check": B._derive_check("PRIV", "overweight", 63, 0.05)},
         "check_by": "2026-04-03"}]}
    logged = B._append_ledger(brief, tmp_path)
    assert {r["ticker"] for r in logged} == {"WIN"}          # PRIV has no price -> not logged


# =========================================================================== emit
def test_emit_ranking_score_and_filter(tmp_path):
    by_ticker = {"as_of": "2026-06-19", "tickers": {
        "AAA": {"ticker": "AAA", "convergence_score": 4, "weighted_score": 2.0,
                "channels": ["gov_contract_accel", "trump"], "trump_linked": True},
        "BBB": {"ticker": "BBB", "convergence_score": 1, "weighted_score": 0.4,
                "channels": ["retail_buzz"], "trump_linked": False},
    }}
    brain = {"theses": [{"ticker": "AAA", "conviction": "high", "action": "ACCUMULATE",
                         "lean": "overweight", "extended": False, "thesis": "t",
                         "second_order": ["S1"], "rs_vs_spy_60d": 5,
                         "falsifier": {"check": {}}}]}
    influence = {"watch": [{"ticker": "AAA", "n_actors": 3,
                            "actors": [{"actor": "Musk", "rel": "CONTROLS", "kind": "exec"}]}]}
    out = EM.build_mastermind(by_ticker, brain, influence, {}, {}, root=tmp_path, top=10)
    tickers = [s["ticker"] for s in out["signals"]]
    assert "AAA" in tickers and "BBB" not in tickers          # BBB: 1 channel, no brain, no affil -> filtered
    aaa = next(s for s in out["signals"] if s["ticker"] == "AAA")
    assert aaa["source"] == "brain" and aaa["action"] == "ACCUMULATE" and aaa["direction"] == "long"
    assert aaa["signal_score"] >= 90 and aaa["n_affiliated_actors"] == 3
    assert out["schema"] == "altdata.mastermind.v1"


def test_emit_deterministic_when_no_brain(tmp_path):
    by_ticker = {"as_of": "x", "tickers": {
        "AAA": {"ticker": "AAA", "convergence_score": 4, "weighted_score": 1.7,
                "channels": ["a", "b", "c", "d"], "trump_linked": False}}}
    out = EM.build_mastermind(by_ticker, {}, {}, {}, {}, root=tmp_path, top=10)
    aaa = out["signals"][0]
    assert aaa["source"] == "deterministic" and aaa["action"] == "WATCH"
    assert aaa["conviction"] == "high"                       # weighted 1.7 >= high band
    assert out["brain_present"] is False


# =========================================================================== emit honesty (W0 audit fixes)

def test_emit_det_conviction_no_double_count(tmp_path):
    """(a) Deterministic path: conviction bonus must NOT be added back to the score.
    A name with count=4, weighted=1.8 must score identically regardless of whether
    _det_conviction returns 'high' or 'medium' — both are derived from the same weighted
    base that already drives the score spine."""
    by_ticker = {"as_of": "x", "tickers": {
        # count=4 → _det_conviction="high"; weighted=1.8 → base = min(60, 1.8*32) = 57.6
        "HI": {"ticker": "HI", "convergence_score": 4, "weighted_score": 1.8,
               "channels": ["a", "b", "c", "d"], "trump_linked": False},
        # count=4 → _det_conviction="high" BUT force a scenario where we need to check
        # the medium path: weighted=0.5 (below _W_MED=0.9) but count>=4 → still "high"
        # We directly test _signal_score for the medium case to isolate the guard
    }}
    out = EM.build_mastermind(by_ticker, {}, {}, {}, {}, root=tmp_path, top=10)
    hi = out["signals"][0]
    assert hi["source"] == "deterministic"
    # Directly verify that changing conviction label does not affect deterministic score
    from engine.altdata_emit import _signal_score
    score_high = _signal_score(1.8, "high", "WATCH", None, False, 0, source="deterministic")
    score_med  = _signal_score(1.8, "medium", "WATCH", None, False, 0, source="deterministic")
    assert score_high == score_med, (
        f"deterministic score must be conviction-label-invariant: high={score_high}, med={score_med}")


def test_emit_det_extended_clamp_from_rs(tmp_path):
    """(b) Deterministic extended flag: rs > _EXTENDED_PP triggers the −15 dock even with
    no brain, and rs <= _EXTENDED_PP does not.

    RS is now computed DIRECTLY from yahoo parquets (not from the picks list).
    We build yahoo parquets where EXT outperforms SPY by ~40pp and NON by ~10pp.
    """
    import pandas as pd
    yahoo = tmp_path / "data" / "yahoo"
    yahoo.mkdir(parents=True)
    idx = pd.date_range("2025-01-01", periods=200, freq="B")
    # SPY: flat
    spy_p = [100.0] * 200
    pd.DataFrame({"close": spy_p}, index=idx).to_parquet(yahoo / "SPY.parquet")
    # EXT: up +40% over 60 days (from bar 140 onward) → RS ≈ +40pp
    ext_p = [50.0] * 140 + [50.0 * (1 + i * 0.40 / 60) for i in range(60)]
    pd.DataFrame({"close": ext_p}, index=idx).to_parquet(yahoo / "EXT.parquet")
    # NON: up +10% over 60 days → RS ≈ +10pp
    non_p = [50.0] * 140 + [50.0 * (1 + i * 0.10 / 60) for i in range(60)]
    pd.DataFrame({"close": non_p}, index=idx).to_parquet(yahoo / "NON.parquet")

    by_ticker = {"as_of": "x", "tickers": {
        "EXT": {"ticker": "EXT", "convergence_score": 3, "weighted_score": 1.5,
                "channels": ["a", "b", "c"], "trump_linked": False},
        "NON": {"ticker": "NON", "convergence_score": 3, "weighted_score": 1.5,
                "channels": ["a", "b", "c"], "trump_linked": False},
    }}
    out = EM.build_mastermind(by_ticker, {}, {}, {"picks": []}, {}, root=tmp_path, top=10)
    # EXT may be rolling_over (recently strong) or in signals — check both lists
    all_sigs = out["signals"] + out.get("broken_signals", [])
    by_tk = {s["ticker"]: s for s in all_sigs}
    assert by_tk["EXT"]["extended"] is True,  f"rs={by_tk['EXT']['rs_vs_spy_60d']} > 35 → extended must be True"
    assert by_tk["NON"]["extended"] is False, f"rs={by_tk['NON']['rs_vs_spy_60d']} ≤ 35 → extended must be False"
    # EXT gets the −15 dock; NON does not — so EXT must score lower (same weighted base).
    assert by_tk["EXT"]["signal_score"] < by_tk["NON"]["signal_score"], (
        f"extended name must score lower; got EXT={by_tk['EXT']['signal_score']}, NON={by_tk['NON']['signal_score']}")
    # Verify the -15 dock fires in isolation via _signal_score (same rs → isolates the extended flag)
    from engine.altdata_emit import _signal_score
    score_ext = _signal_score(1.5, "medium", "WATCH", 20.0, True,  0, source="deterministic")
    score_non = _signal_score(1.5, "medium", "WATCH", 20.0, False, 0, source="deterministic")
    assert score_non - score_ext == 15, (
        f"isolated −15 dock check failed: non={score_non}, ext={score_ext}")


def test_emit_brain_usable_flag(tmp_path):
    """(c) brain_usable is emitted and correctly False when brain is degraded."""
    by_ticker = {"as_of": "x", "tickers": {
        "AAA": {"ticker": "AAA", "convergence_score": 2, "weighted_score": 1.0,
                "channels": ["a", "b"], "trump_linked": False},
    }}
    # Healthy brain: theses present, no degraded_reason
    brain_ok = {"theses": [{"ticker": "AAA", "conviction": "high", "action": "ACCUMULATE",
                             "lean": "overweight", "extended": False, "thesis": "t",
                             "second_order": [], "rs_vs_spy_60d": 5, "falsifier": {}}]}
    out_ok = EM.build_mastermind(by_ticker, brain_ok, {}, {}, {}, root=tmp_path, top=10)
    assert out_ok["brain_usable"] is True, "healthy brain → brain_usable should be True"

    # Degraded brain: degraded_reason is set
    brain_deg = {"theses": [], "degraded_reason": "no_client_or_token"}
    out_deg = EM.build_mastermind(by_ticker, brain_deg, {}, {}, {}, root=tmp_path, top=10)
    assert out_deg["brain_usable"] is False, "degraded brain → brain_usable should be False"

    # No brain at all
    out_none = EM.build_mastermind(by_ticker, {}, {}, {}, {}, root=tmp_path, top=10)
    assert out_none["brain_usable"] is False, "absent brain → brain_usable should be False"
# ===================================================================== W16-B-FOA: federal pipeline
# counts (scripts.build_alt_data.theme_pipeline_counts + the alt_data.html.j2 card).
# Display-only per-theme SAM/FOA notice counts, 90d recent vs the prior 90d.
# Synthetic frames under tmp_path ONLY — the committed data/ parquets are never read.


def _write_velocity_parquet(path: Path, triples):
    """Producer-shaped frame: index basket_id, columns recent_count/prior_count/
    n_members/covered (collectors/sam_gov.py:142, collectors/grants_gov.py:76)."""
    df = pd.DataFrame(
        [{"basket_id": b, "recent_count": rc, "prior_count": pc,
          "n_members": 1, "covered": ""} for b, rc, pc in triples]
    ).set_index("basket_id")
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)


def _render_alt_data(overrides: dict) -> str:
    """Render the real page through the builder's Environment shape
    (scripts/build_alt_data.py:117 — FileSystemLoader(templates), autoescape=True)
    with the minimal context the page needs: the ungridged signal feeds as empty
    lists, an honest no-history track, everything else empty."""
    from jinja2 import Environment, FileSystemLoader

    root = Path(__file__).resolve().parent.parent
    env = Environment(loader=FileSystemLoader(str(root / "templates")), autoescape=True)
    feed = {"as_of": "2026-01-01", "source": "fixture", "datasets": {}, "signals": {
        "gov_contracts": [], "political": {"buys": []}, "insiders": {"buys": []},
        "app_ratings": [], "patents": [], "lobbying": [], "inst_13f": {"adds": []},
        "bills": []}}
    ctx = dict(
        feed=feed, alerts=[],
        track={"overall": {"hit_rate": None}, "scored_total": None},
        influence={}, picks={}, brain={},
        mastermind={"signals": [], "broken_signals": []},
        generated_utc="2026-01-01 00:00 UTC",
        qledger_chips={}, desk_grader={},
        active_section="research", active_page="alt_data",
    )
    ctx.update(overrides)
    return env.get_template("alt_data.html.j2").render(**ctx)


def test_pipeline_counts_reads_both_frames(tmp_path):
    from scripts.build_alt_data import theme_pipeline_counts

    _write_velocity_parquet(tmp_path / "data" / "sam_gov" / "opp_velocity.parquet",
                            [("fixture_robot", 12, 5), ("fixture_space", 3, 1)])
    _write_velocity_parquet(tmp_path / "data" / "grants_gov" / "foa_velocity.parquet",
                            [("fixture_robot", 7, 2), ("fixture_bio", 40, 9)])
    (tmp_path / "data" / "sam_gov" / "opp_velocity_meta.json").write_text(
        json.dumps({"as_of": {"fixture_robot": "2026-01-02"}}))

    out = theme_pipeline_counts(tmp_path)
    assert out["window_days"] == 90
    # exact rows, exact order: recent-max desc (40, 12, 3), then basket_id asc
    assert out["rows"] == [
        {"basket_id": "fixture_bio", "sam_recent": None, "sam_prior": None,
         "foa_recent": 40, "foa_prior": 9, "sam_as_of": None},
        {"basket_id": "fixture_robot", "sam_recent": 12, "sam_prior": 5,
         "foa_recent": 7, "foa_prior": 2, "sam_as_of": "2026-01-02"},
        {"basket_id": "fixture_space", "sam_recent": 3, "sam_prior": 1,
         "foa_recent": None, "foa_prior": None, "sam_as_of": None},
    ]
    for row in out["rows"]:        # plain int (never numpy); absent stays None
        for key in ("sam_recent", "sam_prior", "foa_recent", "foa_prior"):
            assert row[key] is None or type(row[key]) is int, (row["basket_id"], key)


def test_pipeline_counts_missing_files_is_empty(tmp_path):
    from scripts.build_alt_data import theme_pipeline_counts

    out = theme_pipeline_counts(tmp_path)   # no files at all — must not raise
    assert out["rows"] == []


def test_alt_data_template_renders_pipeline_counts():
    html = _render_alt_data({"pipeline_counts": {"rows": [
        {"basket_id": "fixture_robot", "sam_recent": 12, "sam_prior": 5,
         "foa_recent": None, "foa_prior": None, "sam_as_of": "2026-01-02"},
        {"basket_id": "<b>x</b>", "sam_recent": 1, "sam_prior": 0,
         "foa_recent": None, "foa_prior": None, "sam_as_of": None}],
        "window_days": 90}})
    assert "Federal pipeline counts" in html
    assert "fixture_robot" in html
    assert ">12<" in html                     # count lands in its own cell
    assert "2026-01-02" in html               # sam_as_of; page clock dates are 2026-01-01
    assert "&lt;b&gt;x&lt;/b&gt;" in html     # producer basket_id is escaped...
    assert "<b>x</b>" not in html             # ...never raw-marked-up
    assert "联邦项目管线数量" in html             # zh half of the fixed card title


def test_alt_data_template_hides_pipeline_counts_when_empty():
    # control first: the card DOES show when rows exist, so the negatives below
    # prove the guard (empty rows / absent key), not merely an absent feature.
    one_row = [{"basket_id": "fixture_robot", "sam_recent": 12, "sam_prior": 5,
                "foa_recent": None, "foa_prior": None, "sam_as_of": None}]
    assert "Federal pipeline counts" in _render_alt_data(
        {"pipeline_counts": {"rows": one_row}})
    assert "Federal pipeline counts" not in _render_alt_data(
        {"pipeline_counts": {"rows": []}})
    assert "Federal pipeline counts" not in _render_alt_data({})   # key absent entirely


def test_alt_data_main_passes_pipeline_counts():
    """main() must hand the card its data. Chosen: AST source assertion (commission
    fallback) — stubbing every main() collaborator to capture render kwargs is far
    beyond ~40 lines and write_page would land on the real site/ from a test."""
    import ast

    root = Path(__file__).resolve().parent.parent
    tree = ast.parse((root / "scripts" / "build_alt_data.py").read_text())
    main_fn = next(n for n in tree.body
                   if isinstance(n, ast.FunctionDef) and n.name == "main")
    renders = []
    for node in ast.walk(main_fn):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "render"
                and isinstance(node.func.value, ast.Call)
                and isinstance(node.func.value.func, ast.Attribute)
                and node.func.value.func.attr == "get_template"
                and node.func.value.args
                and isinstance(node.func.value.args[0], ast.Constant)
                and node.func.value.args[0].value == "alt_data.html.j2"):
            renders.append(node)
    assert len(renders) == 1, f"expected exactly one alt_data render in main()"
    assert "pipeline_counts" in {kw.arg for kw in renders[0].keywords}, (
        "main() must pass pipeline_counts= into the alt_data.html.j2 render call")


# ---- W16-B-FOA2 follow-ups: honest truncation + total guards (review items 1-6).
# Same rules as the block above: synthetic tmp_path fixtures only, no network,
# the committed data/ parquets never read by tests.

def _pipeline_card(html: str) -> str:
    """The card region only (title through the source-note marker), so "None"
    and count assertions can never trip over text elsewhere on the page."""
    start = html.index("Federal pipeline counts")
    return html[start:html.index("Source: SAM.gov", start)]


def test_alt_data_pipeline_card_as_of_dash_never_none():
    # item 1: a None as-of must render the em dash, never the literal "None"
    # (kills mA: dropping the template's `or '—'` prints "None" in the cell).
    html = _render_alt_data({"pipeline_counts": {"rows": [
        {"basket_id": "x", "sam_recent": None, "sam_prior": None,
         "foa_recent": 1, "foa_prior": 0, "sam_as_of": None}]}})
    card = _pipeline_card(html)
    assert "None" not in card
    assert '<td class="mut">—</td></tr>' in card   # the as-of cell is the dash


def test_pipeline_counts_sam_nan_is_none(tmp_path):
    # item 2: a NaN recent_count is an absent count (None), and the call
    # must not raise — the never-raise promise covers numeric poison too.
    from scripts.build_alt_data import theme_pipeline_counts
    _write_velocity_parquet(tmp_path / "data" / "sam_gov" / "opp_velocity.parquet",
                            [("alpha", float("nan"), 4)])
    out = theme_pipeline_counts(tmp_path)
    assert out["rows"][0]["sam_recent"] is None
    assert out["rows"][0]["sam_prior"] == 4


def test_pipeline_counts_nan_branch_pinned():
    # item 2 discrimination for mB: once int() is guarded, deleting the
    # explicit NaN branch is functionally invisible — pin the branch itself.
    import inspect
    from scripts.build_alt_data import theme_pipeline_counts
    src = inspect.getsource(theme_pipeline_counts)
    assert "pd.isna(v)" in src or "v != v" in src, (
        "_count must keep an explicit NaN branch, not lean on int(nan) raising")


def test_pipeline_counts_tiebreak_orders_by_basket_id(tmp_path):
    # item 3: tied maxima fall back to basket_id asc, never file order
    # (kills mC: dropping the r["basket_id"] tiebreak keeps zulu first).
    from scripts.build_alt_data import theme_pipeline_counts
    _write_velocity_parquet(tmp_path / "data" / "grants_gov" / "foa_velocity.parquet",
                            [("zulu", 10, 0), ("alpha", 10, 0)])
    out = theme_pipeline_counts(tmp_path)
    assert [r["basket_id"] for r in out["rows"]] == ["alpha", "zulu"]


def test_pipeline_counts_bad_meta_costs_only_the_as_of_column(tmp_path):
    # item 4: a truthy NON-dict as_of (a JSON list) must not raise, must not
    # drop the card — every sam_as_of is None, counts and rows survive.
    from scripts.build_alt_data import theme_pipeline_counts
    _write_velocity_parquet(tmp_path / "data" / "sam_gov" / "opp_velocity.parquet",
                            [("alpha", 5, 2)])
    _write_velocity_parquet(tmp_path / "data" / "grants_gov" / "foa_velocity.parquet",
                            [("zulu", 3, 1)])
    (tmp_path / "data" / "sam_gov" / "opp_velocity_meta.json").write_text(
        json.dumps({"as_of": ["2026-01-01", "2026-01-02"]}))
    out = theme_pipeline_counts(tmp_path)   # never raise
    assert [r["basket_id"] for r in out["rows"]] == ["alpha", "zulu"]
    assert all(r["sam_as_of"] is None for r in out["rows"])
    assert out["rows"][0]["sam_recent"] == 5   # a bad meta keeps its counts


def test_pipeline_counts_non_numeric_cells_are_none(tmp_path):
    # item 4: "abc" (ValueError from int) and inf (OverflowError) yield None
    # cells and surviving rows — a bad number costs one cell, never the card.
    # One dtype-homogeneous frame per case (pyarrow rejects mixed str/int).
    from scripts.build_alt_data import theme_pipeline_counts
    root_s = tmp_path / "str_junk"
    _write_velocity_parquet(root_s / "data" / "sam_gov" / "opp_velocity.parquet",
                            [("junk_s", "abc", 2), ("ok_s", "n/a", 7)])
    by_id = {r["basket_id"]: r for r in theme_pipeline_counts(root_s)["rows"]}
    assert by_id["junk_s"]["sam_recent"] is None   # "abc" cell -> None
    assert by_id["junk_s"]["sam_prior"] == 2       # row survives: other cells
    assert by_id["ok_s"]["sam_prior"] == 7         #          kept, all rows kept

    root_i = tmp_path / "inf_junk"
    _write_velocity_parquet(root_i / "data" / "sam_gov" / "opp_velocity.parquet",
                            [("junk_i", float("inf"), 2), ("ok_i", 9, 7)])
    by_id = {r["basket_id"]: r for r in theme_pipeline_counts(root_i)["rows"]}
    assert by_id["junk_i"]["sam_recent"] is None   # inf -> None, no raise
    assert by_id["ok_i"]["sam_recent"] == 9        # good float cell still int
    assert by_id["junk_i"]["sam_prior"] == 2


def test_pipeline_counts_total_is_pre_cap_count(tmp_path):
    # item 5: total counts all baskets BEFORE the cap; rows is the top slice.
    from scripts.build_alt_data import theme_pipeline_counts
    _write_velocity_parquet(tmp_path / "data" / "grants_gov" / "foa_velocity.parquet",
                            [(f"b{i:02d}", i, 0) for i in range(1, 18)])   # 17
    out = theme_pipeline_counts(tmp_path)
    assert out["total"] == 17
    assert len(out["rows"]) == 15
    assert out["rows"][0]["basket_id"] == "b17"     # recent desc still leads
    small = tmp_path / "small"
    _write_velocity_parquet(small / "data" / "grants_gov" / "foa_velocity.parquet",
                            [("alpha", 3, 1), ("zulu", 2, 0), ("mike", 1, 0)])
    out3 = theme_pipeline_counts(small)
    assert out3["total"] == 3
    assert len(out3["rows"]) == 3


def test_alt_data_pipeline_card_truncation_note(tmp_path):
    # item 5: the note renders ONLY when the cap dropped baskets, with both
    # numbers in plain autoescaped l-en/l-zh spans (never t() interpolation).
    from scripts.build_alt_data import theme_pipeline_counts
    _write_velocity_parquet(tmp_path / "data" / "grants_gov" / "foa_velocity.parquet",
                            [(f"b{i:02d}", i, 0) for i in range(1, 18)])
    html = _render_alt_data({"pipeline_counts": theme_pipeline_counts(tmp_path)})
    card = _pipeline_card(html)
    assert "Showing the top 15 of 17 themes by recent count." in card
    assert "按近期计数显示前15个主题（共17个）" in card
    # control (kills mG): 3 of 3 shows NO note at all
    small = tmp_path / "small"
    _write_velocity_parquet(small / "data" / "grants_gov" / "foa_velocity.parquet",
                            [("alpha", 3, 1), ("zulu", 2, 0), ("mike", 1, 0)])
    html3 = _render_alt_data({"pipeline_counts": theme_pipeline_counts(small)})
    assert "Showing the top" not in html3
    assert "个主题" not in _pipeline_card(html3)


def test_pipeline_window_days_matches_collector_constants(tmp_path):
    # item 6: the card window is the PRODUCERS' window. Pinned by parsing the
    # collector SOURCE with ast — importing them pulls network deps (rule:
    # no network), so the module-level int assignments are read, not executed.
    import ast
    from scripts.build_alt_data import theme_pipeline_counts
    root = Path(__file__).resolve().parent.parent
    wanted = {"RECENT_D", "PRIOR_D", "FOA_RECENT_D", "FOA_PRIOR_D"}
    vals = {}
    for rel in ("collectors/sam_gov.py", "collectors/grants_gov.py"):
        tree = ast.parse((root / rel).read_text())
        for node in tree.body:
            if not (isinstance(node, ast.Assign)
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, int)):
                continue
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id in wanted:
                    vals[tgt.id] = node.value.value
    assert set(vals) == wanted, vals
    wd = theme_pipeline_counts(tmp_path)["window_days"]
    assert all(v == wd for v in vals.values()), (vals, wd)


def test_alt_data_pipeline_card_label_reads_window_days():
    # item 6: "Nd vs prior Nd" renders FROM pipeline_counts.window_days —
    # the zh half follows the same number. (Kills mH: a hardcoded 90 here.)
    one = [{"basket_id": "x", "sam_recent": 1, "sam_prior": 0,
            "foa_recent": None, "foa_prior": None, "sam_as_of": None}]
    html60 = _render_alt_data({"pipeline_counts": {"rows": one, "window_days": 60}})
    assert "60d vs prior 60d" in html60
    assert "近60天 vs 前60天" in html60
    assert "90d" not in _pipeline_card(html60)
    html90 = _render_alt_data({"pipeline_counts": {"rows": one, "window_days": 90}})
    assert "90d vs prior 90d" in html90
    assert "近90天 vs 前90天" in _pipeline_card(html90)


# =========================================================================== W19-C1
# ALT-W19C-1 (convergence-onset strip) + ALT-W19C-3 (context-only grant reason).
# Inline fixtures shaped like the committed producer records (engine/altdata_alerts.py:49-53,
# engine/altdata_emit.py:239-240). No data/, no site/, no network.


def _w19c1_alert(i: int, **kw) -> dict:
    """Synthetic alert record; index 0 is the NEWEST ts — recent() sorts newest
    first (engine/altdata_alerts.py:102), so the strip must keep this order."""
    tk = kw.get("asset") or f"T{i}"
    date = f"2026-10-{18 - i:02d}"
    ev = {"id": f"altdata:{tk}:convergence:{date}:up", "ts": f"{date}T00:00:00",
          "source": "altdata", "asset": tk, "type": "convergence", "severity": "medium",
          "headline": f"2-channel convergence on {tk}", "detail": "lobbying, trump",
          "headline_zh": f"{tk} 2通道汇聚", "detail_zh": "游说、特朗普交易",
          "context": {"score": 2, "channels": ["lobbying", "trump"]},
          "anchor": "#convergence"}
    ev.update(kw)
    return ev


def _w19c1_cvx_alert() -> dict:
    """The committed 2026-10-18 CVX onset record (design F1), keys as _ev writes them."""
    return _w19c1_alert(0, asset="CVX", severity="high",
                        headline="4-channel convergence on CVX (Trump-linked)",
                        headline_zh="CVX 4通道汇聚（特朗普关联）", detail="score 4, 4 channels",
                        detail_zh="评分 4，4个通道",
                        context={"score": 4, "trump_linked": True,
                                 "channels": ["lobbying", "material_8k", "special_situation",
                                              "trump"]})


def _w19c1_article3() -> dict:
    """Committed article3 block (mastermind.json shape) — reason quoted, never parsed."""
    return {"granted": False, "lift_lb": None, "evidence_asof": "2026-10-16",
            "reason": "insufficient-n: n=17 < min_n=25"}


def _w19c1_mm(**kw) -> dict:
    mm = {"signals": [], "broken_signals": []}
    mm.update(kw)
    return mm


def _w19c1_strip(html: str) -> str:
    """Onset strip: its 'Newly converging' heading up to the next </section>."""
    i = html.index("Newly converging")
    return html[i:html.index("</section>", i)]


def _w19c1_board(html: str) -> str:
    """Conviction board: id="convergence" up to its </section>."""
    i = html.index('id="convergence"')
    return html[i:html.index("</section>", i)]


def test_alt_data_renders_onset_alert_from_committed_shape():
    # Spec 1: the alerts the builder already passes (scripts/build_alt_data.py:142, :220)
    strip = _w19c1_strip(_render_alt_data({"alerts": [_w19c1_cvx_alert()]}))
    assert "CVX" in strip
    assert "2026-10-18" in strip                          # a.ts[:10] date column
    assert "4-channel convergence on CVX" in strip        # EN headline
    assert "CVX 4通道汇聚" in strip                        # zh half is headline_zh
    assert "watch, not a buy" in strip and "观察，非买入信号" in strip


def test_alt_data_hides_onset_strip_when_alerts_empty():
    html = _render_alt_data({})                            # helper default: alerts=[]
    assert "Newly converging" not in html
    assert "新汇聚" not in html
    ctl = _render_alt_data({"alerts": [_w19c1_cvx_alert()]})   # control: guard, not absence
    assert "Newly converging" in ctl
    assert "新汇聚" in ctl


def test_alt_data_onset_strip_caps_at_eight_newest_first():
    ten = [_w19c1_alert(i) for i in range(10)]             # given NEWEST first
    strip = _w19c1_strip(_render_alt_data({"alerts": ten}))
    pos = [strip.index(f'class="tkc">T{i}<') for i in range(8)]
    assert pos == sorted(pos)                              # producer order kept, never re-sorted
    assert ">T8<" not in strip and ">T9<" not in strip     # the 8-row ceiling


def test_alt_data_board_carries_convergence_anchor():
    # every alert record carries "anchor": "#convergence" (engine/altdata_alerts.py:53) and
    # the feed deep-links alt_data.html#convergence; the always-rendering board lands it
    html = _render_alt_data({})
    assert html.count('id="convergence"') == 1
    assert "Conviction board" in _w19c1_board(html)


def test_alt_data_prints_article3_reason_from_committed_shape():
    # Spec 3: a context-only board prints the RECORDED reason, verbatim
    board = _w19c1_board(_render_alt_data(
        {"mastermind": _w19c1_mm(is_context_only=True, article3=_w19c1_article3())}))
    assert "Context only — not yet cleared as actionable" in board
    assert "仅作背景参考" in board
    assert "insufficient-n: n=17 &lt; min_n=25" in board  # autoescaped, not parsed
    assert "< min_n" not in board                        # never raw-marked-up


def test_alt_data_hides_article3_note_when_not_context_only():
    ctl = _w19c1_board(_render_alt_data(
        {"mastermind": _w19c1_mm(is_context_only=True, article3=_w19c1_article3())}))
    assert "Context only" in ctl                          # control
    for mm in (_w19c1_mm(is_context_only=False, article3=_w19c1_article3()),
               _w19c1_mm()):                               # key absent entirely
        assert "Context only" not in _w19c1_board(_render_alt_data({"mastermind": mm}))


def test_alt_data_context_only_without_article3_prints_no_none():
    board = _w19c1_board(_render_alt_data(
        {"mastermind": _w19c1_mm(is_context_only=True, article3=None)}))
    assert "Context only — not yet cleared as actionable" in board
    assert "None" not in board
    # clause ends clean: no dangling ": " when no reason was recorded
    assert "actionable</span>" in board
    board2 = _w19c1_board(_render_alt_data(
        {"mastermind": _w19c1_mm(is_context_only=True,
                                 article3={"granted": False, "lift_lb": None})}))
    assert "Context only — not yet cleared as actionable</span>" in board2
    assert "None" not in board2


# ---- W19-C2: prints the dates/fields the feeds already carry ---------------

def _w19c2_feed(datasets=None, **signals):
    """Feed shaped like _render_alt_data's default (seed :422-425) but with this
    lane's signal rows / datasets merged in."""
    sig = {"gov_contracts": [], "political": {"buys": []}, "insiders": {"buys": []},
           "app_ratings": [], "patents": [], "lobbying": [], "inst_13f": {"adds": []},
           "bills": []}
    sig.update(signals)
    return {"as_of": "2026-01-01", "source": "fixture",
            "datasets": datasets or {}, "signals": sig}


def _w19c2_card(html, marker):
    """One signal-grid card: h3 text through the next </div> (see _pipeline_card)."""
    start = html.index(marker)
    return html[start:html.index("</div>", start)]


def _w19c2_cov(html):
    """Coverage-chip strip only (the sid-cov div), never the page CSS."""
    start = html.index('class="sid-cov"')
    return html[start:html.index("</div>", start)]


def _w19c2_oe_row(tk="OFAL", dpi=0.549, lean="balanced", stale=False):
    """Producer shape of signals.offexchange (engine/altdata.py:917-953)."""
    return {"ticker": tk, "date": "2026-10-09", "otc_total": 190618890.0,
            "dpi": dpi, "lean": lean, "stale": stale}


def test_alt_data_fda_card_prints_event_date():
    # R1: FDA records carry an ISO "date" (engine/altdata.py:813-814); the card
    # must print it, and a missing date is the em dash — never the literal None.
    html = _render_alt_data({"feed": _w19c2_feed(fda=[
        {"ticker": "NVS", "kind": "label_expansion", "drug": "RHAPSIDO",
         "date": "2026-10-06"},
        {"ticker": "ABBV", "kind": "approval", "drug": "JUVMO",
         "date": "2026-09-25"},
        {"ticker": "ZZZ", "kind": "approval", "drug": None, "date": None}])})
    card = _w19c2_card(html, "FDA catalysts")
    assert "2026-10-06" in card and "2026-09-25" in card
    assert '<td class="mut">—</td></tr>' in card   # None date -> last cell dash
    assert "None" not in card


def test_alt_data_earnings_card_prints_committed_last_surprise():
    # R2: last_surprise_pct (engine/altdata.py:430-436) prints signed, 1 dp.
    html = _render_alt_data({"feed": _w19c2_feed(earnings=[
        {"ticker": "CCK", "next_date": "2026-10-20", "days_to": 1,
         "eps_forecast": 2.25, "last_surprise_pct": 15.8},
        {"ticker": "DWN", "next_date": "2026-10-21", "days_to": 2,
         "eps_forecast": None, "last_surprise_pct": -4.1}])})
    card = _w19c2_card(html, "Earnings imminent")
    assert "+15.8%" in card and "-4.1%" in card
    assert "上次业绩意外" in card
    assert "watch, not a buy" in card   # seat ruling: existing note unchanged


def test_alt_data_earnings_surprise_none_is_dash():
    html = _render_alt_data({"feed": _w19c2_feed(earnings=[
        {"ticker": "FITB", "next_date": "2026-10-20", "days_to": 1,
         "eps_forecast": 1.09, "last_surprise_pct": None}])})
    card = _w19c2_card(html, "Earnings imminent")
    assert '<span class="mut">—</span></td></tr>' in card   # last cell is dash
    assert "None" not in card


def test_alt_data_renders_offexchange_row_from_committed_shape():
    # R3 (Spec 4): new card for s.offexchange; otc_total units unverified -> absent.
    html = _render_alt_data({"feed": _w19c2_feed(offexchange=[
        _w19c2_oe_row(), _w19c2_oe_row("WFF", 0.633, "distribution"),
        _w19c2_oe_row("T", 0.571, "balanced")])})
    card = _w19c2_card(html, "Off-exchange flow")
    for want in ("OFAL", "0.549", "均衡", "WFF", "0.633", "派发", "T", "0.571",
                 "2026-10-09", "FINRA", "卖空比例"):
        assert want in card, want
    assert "190618890" not in card and "190,618,890" not in card
    assert "None" not in card


def test_alt_data_offexchange_stale_flag():
    # R3: first record's stale -> "stale"/数据滞后 in the h3; false -> neither;
    # an empty list hides the whole card.
    html = _render_alt_data({"feed": _w19c2_feed(offexchange=[
        _w19c2_oe_row(stale=True)])})
    i = html.index("Off-exchange flow")
    h3 = html[i:html.index("</h3>", i)]
    assert "数据滞后" in h3 and "stale" in h3
    html2 = _render_alt_data({"feed": _w19c2_feed(offexchange=[_w19c2_oe_row()])})
    j = html2.index("Off-exchange flow")
    h3b = html2[j:html2.index("</h3>", j)]
    assert "数据滞后" not in h3b and "stale" not in h3b
    html3 = _render_alt_data({"feed": _w19c2_feed(offexchange=[])})
    assert "Off-exchange flow" not in html3


def test_alt_data_coverage_chip_prints_committed_last_seen():
    # R4 (Spec 2): feed.datasets[..].last_seen (engine/altdata.py:1250-1265)
    # rides on the chip; row count stays.
    html = _render_alt_data({"feed": _w19c2_feed(datasets={"senate": {
        "rows": 5069, "last_seen": "2026-09-04", "label_en": "Senate trading",
        "label_zh": "参议院交易", "emoji": "🏛"}})})
    cov = _w19c2_cov(html)
    assert "5,069" in cov and "2026-09-04" in cov
    assert "None" not in cov


def test_alt_data_coverage_last_seen_none_is_dash():
    html = _render_alt_data({"feed": _w19c2_feed(datasets={"senate": {
        "rows": 5069, "last_seen": None, "label_en": "Senate trading",
        "label_zh": "参议院交易", "emoji": "🏛"}})})
    cov = _w19c2_cov(html)
    assert "—</span>" in cov   # chip ends with the dash
    assert "None" not in cov
