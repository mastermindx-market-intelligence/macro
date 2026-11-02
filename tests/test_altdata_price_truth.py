"""Tests for W1-B altdata price-truth fixes:

  T1  per-name RS resolved directly from yahoo parquets; breadth cache NEVER consulted
  T2  rolling_over demotion: off-high ≤ −15% AND 20d < 0 AND below 50dma → broken_signals
  T3  T1-T4 entry badge wired from signal_gate.json / on-demand
  T4  (brain autopsy) degraded_reason passthrough honest in mastermind output
  T5  ledger scoring path fires correctly on matured theses

All tests inject synthetic data; no network, no disk parquets touched.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from engine import altdata_emit as EM
from engine import altdata_picks as AP
from engine import altdata_brain as B


# =========================================================================== helpers

def _mk_dates(n=300):
    return pd.date_range("2025-01-01", periods=n, freq="B")


def _mk_series(prices, dates=None):
    if dates is None:
        dates = _mk_dates(len(prices))
    return pd.Series(prices, index=dates[:len(prices)])


# =========================================================================== T1: RS truth

def test_rs_uses_yahoo_only_not_breadth_cache(tmp_path, monkeypatch):
    """_rs_vs_spy must use only data/yahoo/<T>.parquet; if the yahoo parquet is absent
    it must return None, never the (split-corrupted) breadth cache value."""
    # Create a fake yahoo parquet only for SPY (not INTC)
    yahoo = tmp_path / "data" / "yahoo"
    yahoo.mkdir(parents=True)
    idx = _mk_dates(100)
    spy_s = pd.DataFrame({"close": [100.0 + i * 0.5 for i in range(100)]}, index=idx)
    spy_s.to_parquet(yahoo / "SPY.parquet")

    # INTC has no yahoo parquet → RS must be None (breadth cache not consulted)
    rs = AP._rs_vs_spy("INTC", tmp_path)
    assert rs is None, "no yahoo parquet → _rs_vs_spy must return None, not breadth-cache value"


def test_rs_computed_correctly_from_yahoo(tmp_path):
    """When yahoo parquet exists for both ticker and SPY, RS is correct."""
    yahoo = tmp_path / "data" / "yahoo"
    yahoo.mkdir(parents=True)
    idx = _mk_dates(100)
    # AAPL up 20% over 60d; SPY up 10%
    spy_p = [100.0] * 40 + [100.0 * (1 + i * 0.1 / 60) for i in range(60)]
    aapl_p = [50.0] * 40 + [50.0 * (1 + i * 0.2 / 60) for i in range(60)]
    pd.DataFrame({"close": spy_p}, index=idx).to_parquet(yahoo / "SPY.parquet")
    pd.DataFrame({"close": aapl_p}, index=idx).to_parquet(yahoo / "AAPL.parquet")

    rs = AP._rs_vs_spy("AAPL", tmp_path)
    assert rs is not None
    assert 5.0 < rs < 15.0, f"expected ~10pp RS, got {rs}"


def test_emit_rs_beyond_top15_picks(tmp_path):
    """Board names outside the top-15 picks (MSTR/BA-like scenario) get real RS, not None."""
    # Provide yahoo parquets for 20 tickers; build_mastermind should resolve RS for all of them
    yahoo = tmp_path / "data" / "yahoo"
    yahoo.mkdir(parents=True)
    idx = _mk_dates(200)
    spy_p = [100.0 + i * 0.1 for i in range(200)]
    pd.DataFrame({"close": spy_p}, index=idx).to_parquet(yahoo / "SPY.parquet")

    tickers = {f"T{i:02d}": {"convergence_score": 2, "weighted_score": 1.0,
                              "channels": ["a", "b"], "trump_linked": False}
               for i in range(20)}
    for tk in tickers:
        # Each ticker flat → RS close to 0
        pd.DataFrame({"close": spy_p}, index=idx).to_parquet(yahoo / f"{tk}.parquet")

    by_ticker = {"as_of": "2026-06-19", "tickers": tickers}
    out = EM.build_mastermind(by_ticker, {}, {}, {"picks": []}, {}, root=tmp_path)

    # All 20 tickers should have RS resolved (not None), despite the empty picks list
    for sig in out["signals"]:
        assert sig["rs_vs_spy_60d"] is not None, (
            f"{sig['ticker']} has rs=None even though yahoo parquet exists")


def test_emit_no_price_data_flag_when_yahoo_absent(tmp_path):
    """Names with no yahoo parquet get no_price_data=True and rs_vs_spy_60d=None."""
    yahoo = tmp_path / "data" / "yahoo"
    yahoo.mkdir(parents=True)
    idx = _mk_dates(200)
    spy_p = [100.0 + i * 0.1 for i in range(200)]
    pd.DataFrame({"close": spy_p}, index=idx).to_parquet(yahoo / "SPY.parquet")
    # NO yahoo parquet for PRIV

    by_ticker = {"as_of": "2026-06-19", "tickers": {
        "PRIV": {"convergence_score": 3, "weighted_score": 1.5,
                 "channels": ["a", "b", "c"], "trump_linked": False},
    }}
    out = EM.build_mastermind(by_ticker, {}, {}, {"picks": []}, {}, root=tmp_path)
    priv = next((s for s in out["signals"] + out.get("broken_signals", [])
                 if s["ticker"] == "PRIV"), None)
    assert priv is not None
    assert priv["no_price_data"] is True
    assert priv["rs_vs_spy_60d"] is None


def test_breadth_cache_never_consulted_for_rs(tmp_path, monkeypatch):
    """Even when the breadth cache exists and contains a value, _rs_vs_spy must not use it."""
    yahoo = tmp_path / "data" / "yahoo"
    yahoo.mkdir(parents=True)
    idx = _mk_dates(200)
    spy_p = [100.0] * 200
    pd.DataFrame({"close": spy_p}, index=idx).to_parquet(yahoo / "SPY.parquet")
    # Breadth cache has a bogus +114pp value for INTC
    breadth_dir = tmp_path / "data" / "breadth"
    breadth_dir.mkdir(parents=True)
    fake_bc = pd.DataFrame({"INTC": [52.0] + [120.0] * 199}, index=idx)
    fake_bc.index.name = "date"
    fake_bc.to_parquet(breadth_dir / "_closes_cache.parquet")
    # No yahoo parquet for INTC

    rs = AP._rs_vs_spy("INTC", tmp_path)
    # Must be None (no yahoo) — the breadth +114pp value must NOT appear
    assert rs is None, (
        f"breadth cache returned rs={rs}; _rs_vs_spy must return None when yahoo absent")


# =========================================================================== T2: rolling_over demotion

def test_trajectory_rolling_over_all_three_conditions(tmp_path):
    """off_high ≤ −15%, 20d < 0, below 50dma → rolling_over = True."""
    yahoo = tmp_path / "data" / "yahoo"
    yahoo.mkdir(parents=True)
    idx = _mk_dates(300)
    # Pattern: flat at 100 for 200 bars, then steadily falling to 80 over 100 bars
    # → off_high = −20%; 20d return negative (still falling); below 50dma
    prices = [100.0] * 200 + [100.0 - i * 0.2 for i in range(100)]
    assert len(prices) == 300
    assert prices[-1] < 100.0 * 0.85   # off_high ≤ −15%
    pd.DataFrame({"close": prices}, index=idx).to_parquet(yahoo / "CRASH.parquet")
    t = AP._trajectory("CRASH", tmp_path)
    assert t["rolling_over"] is True, f"expected rolling_over; got {t}"
    assert t["off_high_252"] is not None and t["off_high_252"] <= -15.0
    assert t["ret_20d"] is not None and t["ret_20d"] < 0
    assert t["above_50dma"] is False


def test_trajectory_not_rolling_over_when_above_50dma(tmp_path):
    """Same off-high/20d conditions but ABOVE 50dma → NOT rolling_over."""
    yahoo = tmp_path / "data" / "yahoo"
    yahoo.mkdir(parents=True)
    idx = _mk_dates(300)
    # Sharp initial dip but recent recovery → above 50dma
    prices = [100.0] * 100 + [80.0] * 100 + [95.0] * 100  # ended at 95, off-high=−5%
    pd.DataFrame({"close": prices}, index=idx[:len(prices)]).to_parquet(yahoo / "BOUNCE.parquet")
    t = AP._trajectory("BOUNCE", tmp_path)
    # off_high < −5%, but NOT below 50dma (averaging over 50 recent bars at 95)
    assert t["rolling_over"] is False


def test_trajectory_no_price_data_when_no_parquet(tmp_path):
    """No yahoo parquet → no_price_data=True, rolling_over=False."""
    yahoo = tmp_path / "data" / "yahoo"
    yahoo.mkdir(parents=True)
    t = AP._trajectory("NOPE", tmp_path)
    assert t["no_price_data"] is True
    assert t["rolling_over"] is False


def test_emit_rolling_over_demoted_to_broken_strip(tmp_path, monkeypatch):
    """A rolling_over name must NOT appear in signals; it must appear in broken_signals."""
    yahoo = tmp_path / "data" / "yahoo"
    yahoo.mkdir(parents=True)
    idx = _mk_dates(300)
    # CRASH: flat 200 bars then steadily falling → rolling_over
    crash_p = [100.0] * 200 + [100.0 - i * 0.2 for i in range(100)]
    pd.DataFrame({"close": crash_p}, index=idx).to_parquet(yahoo / "CRASH.parquet")
    # GOOD: rising → not rolling_over
    good_p = [50.0 + i * 0.1 for i in range(300)]
    pd.DataFrame({"close": good_p}, index=idx).to_parquet(yahoo / "GOOD.parquet")
    pd.DataFrame({"close": good_p}, index=idx).to_parquet(yahoo / "SPY.parquet")

    by_ticker = {"as_of": "2026-06-19", "tickers": {
        "CRASH": {"convergence_score": 4, "weighted_score": 2.0, "channels": ["a", "b", "c", "d"],
                  "trump_linked": False},
        "GOOD":  {"convergence_score": 3, "weighted_score": 1.5, "channels": ["a", "b", "c"],
                  "trump_linked": False},
    }}
    out = EM.build_mastermind(by_ticker, {}, {}, {"picks": []}, {}, root=tmp_path)
    main_tks = [s["ticker"] for s in out["signals"]]
    broken_tks = [s["ticker"] for s in out.get("broken_signals", [])]
    assert "CRASH" not in main_tks, "CRASH is rolling_over — must not appear on main board"
    assert "CRASH" in broken_tks, "CRASH must appear in broken_signals strip"
    assert "GOOD" in main_tks, "GOOD is not rolling_over — must appear on main board"
    assert "GOOD" not in broken_tks


def test_emit_broken_signals_have_rolling_over_flag(tmp_path):
    """Names in broken_signals carry rolling_over=True."""
    yahoo = tmp_path / "data" / "yahoo"
    yahoo.mkdir(parents=True)
    idx = _mk_dates(300)
    # flat then steadily falling → rolling_over
    crash_p = [100.0] * 200 + [100.0 - i * 0.2 for i in range(100)]
    pd.DataFrame({"close": crash_p}, index=idx).to_parquet(yahoo / "SINK.parquet")
    pd.DataFrame({"close": [100.0] * 300}, index=idx).to_parquet(yahoo / "SPY.parquet")
    by_ticker = {"as_of": "2026-06-19", "tickers": {
        "SINK": {"convergence_score": 2, "weighted_score": 1.0,
                 "channels": ["a", "b"], "trump_linked": False},
    }}
    out = EM.build_mastermind(by_ticker, {}, {}, {"picks": []}, {}, root=tmp_path)
    broken = out.get("broken_signals", [])
    assert broken, "SINK should appear in broken_signals"
    assert all(s["rolling_over"] for s in broken)


# =========================================================================== T3: entry badge

def test_entry_badge_from_gate_json(tmp_path):
    """Names in signal_gate.json with a buyable tier get entry_tier set."""
    import json
    from pathlib import Path
    fg = tmp_path / "site" / "factordata"
    fg.mkdir(parents=True)
    verdicts = {
        "APLE": {"eligible": True, "tier": "take", "tier_cascade": "T1"},
        "NOPE": {"eligible": False, "tier": None,   "tier_cascade": None},
    }
    (fg / "signal_gate.json").write_text(json.dumps({"as_of": "2026-06-19", "verdicts": verdicts}))
    # Minimal tickers — no yahoo parquets needed for gate-lookup (dict hit)
    by_ticker = {"as_of": "2026-06-19", "tickers": {
        "APLE": {"convergence_score": 2, "weighted_score": 1.0, "channels": ["a", "b"],
                 "trump_linked": False},
        "NOPE": {"convergence_score": 2, "weighted_score": 1.0, "channels": ["a", "b"],
                 "trump_linked": False},
    }}
    # Also provide SPY so RS compute doesn't crash
    yahoo = tmp_path / "data" / "yahoo"
    yahoo.mkdir(parents=True)
    idx = _mk_dates(100)
    pd.DataFrame({"close": [100.0] * 100}, index=idx).to_parquet(yahoo / "SPY.parquet")

    out = EM.build_mastermind(by_ticker, {}, {}, {"picks": []}, {}, root=tmp_path)
    by_tk = {s["ticker"]: s for s in out["signals"]}
    assert by_tk["APLE"].get("entry_tier") == "T1", "APLE buyable T1 must get entry_tier=T1"
    assert by_tk["NOPE"].get("entry_tier") is None, "NOPE not eligible must get entry_tier=None"


def test_entry_badge_absent_when_no_gate_file(tmp_path):
    """When signal_gate.json is absent, entry_tier is None (no crash)."""
    # No signal_gate.json, no yahoo for ticker
    yahoo = tmp_path / "data" / "yahoo"
    yahoo.mkdir(parents=True)
    idx = _mk_dates(100)
    pd.DataFrame({"close": [100.0] * 100}, index=idx).to_parquet(yahoo / "SPY.parquet")
    by_ticker = {"as_of": "2026-06-19", "tickers": {
        "AAA": {"convergence_score": 2, "weighted_score": 1.0, "channels": ["a", "b"],
                "trump_linked": False},
    }}
    out = EM.build_mastermind(by_ticker, {}, {}, {"picks": []}, {}, root=tmp_path)
    aaa = next((s for s in out["signals"] if s["ticker"] == "AAA"), None)
    assert aaa is not None
    assert aaa.get("entry_tier") is None


# =========================================================================== T4: brain honesty

def test_brain_degraded_reason_passthrough(tmp_path):
    """build_mastermind exposes brain_usable=False when brain has degraded_reason."""
    by_ticker = {"as_of": "x", "tickers": {
        "AAA": {"convergence_score": 2, "weighted_score": 1.0, "channels": ["a", "b"],
                "trump_linked": False},
    }}
    brain_deg = {"theses": [], "degraded_reason": "auth_invalid_all"}
    out = EM.build_mastermind(by_ticker, brain_deg, {}, {"picks": []}, {}, root=tmp_path)
    assert out["brain_present"] is False   # no theses
    assert out["brain_usable"] is False


def test_brain_no_theses_is_not_usable(tmp_path):
    """Empty theses list → brain_usable=False even if no degraded_reason."""
    by_ticker = {"as_of": "x", "tickers": {
        "AAA": {"convergence_score": 2, "weighted_score": 1.0, "channels": ["a", "b"],
                "trump_linked": False},
    }}
    brain_empty = {"theses": []}  # no degraded_reason, but no theses either
    out = EM.build_mastermind(by_ticker, brain_empty, {}, {"picks": []}, {}, root=tmp_path)
    assert out["brain_present"] is False
    assert out["brain_usable"] is False


# =========================================================================== T5: ledger health

def test_ledger_scores_matured_thesis(tmp_path):
    """_score_one fires correctly when check_by is in the past and price data exists."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from datetime import date, timedelta
    from engine import ai_desk_scorer as _scorer
    from engine import ai_desk as _desk

    yahoo = tmp_path / "data" / "yahoo"
    yahoo.mkdir(parents=True)
    idx = _mk_dates(400)
    # SPY: flat
    pd.DataFrame({"close": [100.0] * 400}, index=idx).to_parquet(yahoo / "SPY.parquet")
    # WIN: up 30% from day 0 to day 63
    win_p = [50.0 * (1 + i * 0.30 / 63) for i in range(63)] + [65.0] * 337
    pd.DataFrame({"close": win_p}, index=idx).to_parquet(yahoo / "WIN.parquet")

    asof = idx[0].date().isoformat()
    check_by = (idx[0].date() + timedelta(days=91)).isoformat()
    today = idx[200].date()   # well past check_by

    e0 = _desk._level_asof("WIN", tmp_path, asof)
    b0 = _desk._level_asof("SPY", tmp_path, asof)
    assert e0 is not None and b0 is not None, "entry levels must resolve for scorable name"

    row = {
        "id": "test-WIN-altconv", "ticker": "WIN", "state_asof": asof, "check_by": check_by,
        "lean": "overweight", "conviction": "low", "horizon_d": 63,
        "entry_levels": {"WIN": e0, "SPY": b0},
        "falsifier": {
            "check": {"kind": "rel_return", "subject_ticker": "WIN", "vs": "SPY",
                      "op": "<", "threshold": -0.05, "horizon_d": 63}
        },
    }
    result = _scorer._score_one(row, tmp_path, today)
    assert result is not None, "_score_one must return a result for a matured scorable thesis"
    assert result["outcome"] in ("hit", "miss"), f"unexpected outcome: {result['outcome']}"
    # WIN beat SPY by +30pp → outcome should be 'hit' (name did NOT underperform)
    assert result["outcome"] == "hit", f"WIN beat SPY by 30pp but got outcome={result['outcome']}"


# The page's related-news panel must not turn access/network failures into empty news.
def _news_client_result(tmp_path, scenario, actions=None):
    import json
    import re
    import shutil
    import subprocess

    root = Path(__file__).resolve().parents[1]
    html = (root / "templates/alt_data.html.j2").read_text()
    # Same harness consumes old and repaired scripts; before source is expected to fail.
    scripts = re.findall(r"<script(?: [^>]*)?>(.*?)</script>", html, re.S)
    source = next(s for s in scripts if 'news/by_ticker.json' in s)
    harness = r"""
const vm=require('node:vm'), fs=require('node:fs');
const fixture=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
let lang='en', calls=[], attempt=0;
const listeners={}; const elements={};
for(const id of ['sid-news','sid-news-status','sid-news-results','sid-news-retry','sid-news-open']) {
  elements[id]={id,innerHTML:'',textContent:'',hidden:false,disabled:false,dataset:{},attrs:{},handlers:{},
    setAttribute(k,v){this.attrs[k]=v;},addEventListener(k,fn){this.handlers[k]=fn;},focus(){doc.activeElement=this;}};
}
const doc={activeElement:null,documentElement:{getAttribute(){return lang;}},getElementById(id){return elements[id]||null;},addEventListener(k,fn){listeners[k]=fn;}};
Object.defineProperty(elements['sid-news-retry'],'disabled',{set(v){if(v&&doc.activeElement===this)doc.activeElement=null;}});
const endpoints=['altdata/mastermind.json','news/by_ticker.json','news/financial.json'];
const ctx={document:doc,window:{location:{href:'https://example.test/alt_data.html'}},URL,Promise,console,fetch:(url)=>{
  calls.push(url);const spec=(fixture.attempts||[fixture.responses])[attempt][endpoints.indexOf(url)];
  if(spec.network) return Promise.reject(new Error('network'));
  return Promise.resolve({status:spec.status,ok:spec.status>=200&&spec.status<300,json:()=>spec.invalid?Promise.reject(new Error('json')):Promise.resolve(spec.data)});
}};
vm.runInNewContext(fixture.source,ctx);
function settle(){return new Promise(r=>setImmediate(r));}
(async()=>{
 await settle();
 const initial={html:elements['sid-news-results'].innerHTML||elements['sid-news'].innerHTML,status:elements['sid-news-status'].textContent,retry:!elements['sid-news-retry'].hidden};
 for(const action of fixture.actions||[]){
   if(action==='language'){lang='zh';if(listeners.langchange)listeners.langchange();}
   if(action==='retry'){attempt++;doc.activeElement=elements['sid-news-retry'];const click=elements['sid-news-retry'].handlers.click;if(click){click();click();}await settle();}
 }
 await settle();
 console.log(JSON.stringify({initial,state:elements['sid-news'].dataset.state,status:elements['sid-news-status'].textContent,html:elements['sid-news-results'].innerHTML||elements['sid-news'].innerHTML,hidden:elements['sid-news-results'].hidden,retry:!elements['sid-news-retry'].hidden,calls,focused:doc.activeElement?.id,busy:elements['sid-news'].attrs['aria-busy']}));
})();
"""
    fixture = dict(scenario, source=source, actions=actions or [])
    payload = tmp_path / "fixture.json"
    script = tmp_path / "harness.cjs"
    payload.write_text(json.dumps(fixture))
    script.write_text(harness)
    node = shutil.which("node")
    assert node, "Node is required to execute the real page-script regression"
    result = subprocess.run([node, str(script), str(payload)], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _empty_news_responses():
    return [{"status":200,"data":{"signals":[]}}, {"status":200,"data":{"tickers":{}}}, {"status":200,"data":{"market":[]}}]


@pytest.mark.parametrize("code", [401, 403])
def test_altdata_news_signin_is_not_missing_feature(tmp_path, code):
    out = _news_client_result(tmp_path, {"responses":[{"status":code}]*3})
    assert out.get("state") == ("gated" if code == 401 else "restricted")
    assert ("Sign in" if code == 401 else "restricted") in out["status"]
    assert "next daily build" not in out["html"]
    assert not out["retry"]


@pytest.mark.parametrize("failure", [{"status":503}, {"status":404}, {"network":True}, {"status":200,"invalid":True}, {"status":200,"data":[]}])
def test_altdata_news_failure_is_not_no_headlines(tmp_path, failure):
    out = _news_client_result(tmp_path, {"responses":[failure]*3})
    assert out.get("state") == "unavailable"
    assert out["retry"] and "unavailable" in out["status"]
    assert "not built" not in out["html"]


def test_altdata_news_successfully_empty_snapshot(tmp_path):
    out = _news_client_result(tmp_path, {"responses":_empty_news_responses()})
    assert out.get("state") == "empty" and "No headlines in this snapshot" in out["status"]
    assert not out["retry"]


def test_altdata_market_fallback_does_not_claim_no_related_news_on_401(tmp_path):
    responses=[{"status":401}, {"status":401}, {"status":200,"data":{"market":[{"title":"Market headline","url":"https://example.test/story"}]}}]
    out = _news_client_result(tmp_path, {"responses":responses}, ["language"])
    assert out.get("state") == "market_gate" and "登录" in out["status"]
    assert "Market headline" in out["html"] and "No news yet" not in out["html"]
    assert len(out["calls"]) == 3  # translating does not refetch or widen access


def test_altdata_related_headlines_keep_chinese_order_and_escape_markup(tmp_path):
    responses=_empty_news_responses()
    responses[0]["data"]["signals"]=[{"ticker":"BBB","signal_score":99},{"ticker":"AAA"}]
    responses[1]["data"]["tickers"]={"BBB":{"top":[{"title":"<script>bad</script>","title_zh":"中文标题","url":"javascript:alert(1)","source":"<img>"}]},"AAA":{"top":[{"title":"Second story","url":"https://example.test/two"}]}}
    out = _news_client_result(tmp_path, {"responses":responses})
    assert out.get("state") == "related"
    assert out["html"].index("BBB") < out["html"].index("AAA")
    assert "中文标题" in out["html"] and "&lt;script&gt;" in out["html"]
    assert '<script>' not in out["html"] and 'href="javascript:' not in out["html"]
    assert "alt signal" not in out["html"]


def test_altdata_news_retry_is_single_flight_and_restores_focus(tmp_path):
    out = _news_client_result(tmp_path, {"attempts":[[{"status":503}]*3,_empty_news_responses()]}, ["retry"])
    assert out.get("state") == "empty" and out["initial"]["retry"]
    assert len(out["calls"]) == 6 and out["busy"] == "false"
    assert out["focused"] == "sid-news-open" and not out["retry"]


def test_altdata_news_template_preserves_native_loading_and_actions():
    source=(Path(__file__).resolve().parents[1]/"templates/alt_data.html.j2").read_text()
    assert 'id="sid-news-status" role="status"' in source
    assert 'id="sid-news-retry" type="button"' in source
    assert "document.addEventListener('langchange',localize)" in source
    assert "News surface not built yet" not in source


def test_altdata_news_generated_source_parity():
    import hashlib
    import re
    root = Path(__file__).resolve().parents[1]
    template = (root / "templates" / "alt_data.html.j2").read_text()
    page = (root / "site" / "alt_data.html").read_text()
    client = next(s for s in re.findall(r"<script(?: [^>]*)?>(.*?)</script>", template, re.S) if "news/by_ticker.json" in s)
    assert client in page
    body = re.search(r"{% block base_css %}(.*?){% endblock %}", template, re.S).group(1)
    refs = re.findall(r"assets/css/([0-9a-f]{8})\.css\?v=\1", page)
    matches = []
    for digest in set(refs):
        path = root / "site" / "assets" / "css" / (digest + ".css")
        if path.exists() and body in path.read_text():
            matches.append(digest)
            assert hashlib.sha256(path.read_bytes()).hexdigest()[:8] == digest
    assert len(matches) == 1, "page must bind the canonical inherited template CSS"
