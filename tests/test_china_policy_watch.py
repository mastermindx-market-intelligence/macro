"""China Central Bank & Government Policy Watch — contract tests (network-free).

Covers the PBoC collector's pure parsers, the deterministic stance classifier, the
policy-watch assembler shape + the compact bus contract, and the curated intel substrate.
"""
from __future__ import annotations

import json

import pandas as pd

from collectors import china_pboc as cp
from engine import china_pboc_stance as ps
from engine import china_policy_watch as pw
from lib import config
from scripts import build_china_policy_watch as builder


EXPRESS_LANES = (
    config.ROOT / ".github" / "workflows" / "render.yml",
    config.ROOT / ".github" / "workflows" / "engine-render.yml",
)


# ---- collector pure parsers ------------------------------------------------ #
def test_parse_month_variants():
    assert cp._parse_month("2026年05月份") == pd.Timestamp(2026, 5, 1)
    assert cp._parse_month("2026-05") == pd.Timestamp(2026, 5, 1)
    assert cp._parse_month("garbage") is None


def test_col_fuzzy_match():
    df = pd.DataFrame(columns=["国家外汇储备-数值", "黄金储备-数值", "月份"])
    assert cp._col(df, "外汇储备-数值") == "国家外汇储备-数值"
    assert cp._col(df, "不存在") is None


# ---- stance classifier (pure) ---------------------------------------------- #
def test_classify_easing_neutral_tightening():
    # two easing legs -> easing
    assert ps._classify(-0.10, -0.5, -0.20)[1] == "easing"
    # two tightening legs -> tightening
    assert ps._classify(0.10, 0.5, 0.20)[1] == "tightening"
    # mixed / flat -> neutral
    assert ps._classify(0.0, -0.5, 0.0)[1] == "neutral"
    assert ps._classify(None, None, None)[1] == "neutral"


def test_stance_snapshot_shape_and_none_safe():
    s = ps.snapshot()
    if s is not None:
        assert s["schema"] == ps.SCHEMA
        assert s["stance"] in ("easing", "neutral", "tightening")
        assert isinstance(s["corridor"], list)
        assert "fx" in s and "last_moves" in s


# ---- policy-watch assembler ------------------------------------------------ #
def test_policy_snapshot_structure():
    vm = pw.snapshot()
    if vm is None:
        return
    assert vm["schema"] == pw.SCHEMA
    for k in ("pboc", "nbs_prints", "policy_feed", "policy_feed_status", "intel", "latest"):
        assert k in vm
    assert vm["policy_feed_status"] in ("ok", "quiet", "unavailable")
    assert isinstance(vm["policy_feed"], list)
    # compact contract keys the intel bus reads
    lc = vm["latest"]
    for k in ("stance", "lpr_1y", "lpr_5y", "rrr", "fx_reserves", "last_moves", "predictions"):
        assert k in lc


def test_compact_predictions_only_open():
    intel = {"predictions": [
        {"text_en": "A", "status": "open"}, {"text_en": "B", "status": "hit"}]}
    c = pw._compact({"corridor": [], "fx": {}}, intel)
    assert c["predictions"] == ["A"]


# ---- intel_dates staleness plumbing --------------------------------------- #
def test_snapshot_intel_dates_stale_flag(monkeypatch):
    """Audit fix B6b: snapshot() must wire policy_dates.annotate(intel) into intel_dates,
    and intel_dates.staleness.stale must be True when intel.as_of is >14d old."""
    from datetime import date, timedelta
    import engine.china_pboc_stance as ps

    stale_as_of = (date.today() - timedelta(days=20)).isoformat()
    stale_intel = {"as_of": stale_as_of, "thesis": {"en": "x", "zh": "x"},
                   "predictions": [], "sector_policy": []}

    monkeypatch.setattr(pw, "_intel", lambda: stale_intel)
    monkeypatch.setattr(pw, "_nbs_prints", lambda: [])
    monkeypatch.setattr(pw, "_policy_feed", lambda: ("quiet", []))
    # provide minimal pboc so snapshot doesn't return None
    monkeypatch.setattr(ps, "snapshot", lambda asof=None: {
        "schema": ps.SCHEMA, "stance": "neutral", "stance_en": "Neutral",
        "stance_zh": "中性", "rationale": {"en": "flat", "zh": "平稳"},
        "corridor": [], "fx": {}, "last_moves": [], "asof": stale_as_of,
    })

    vm = pw.snapshot()
    assert vm is not None, "snapshot must not return None with valid pboc stub"
    assert "intel_dates" in vm, "intel_dates key must be present in snapshot output"
    staleness = vm["intel_dates"]["staleness"]
    assert staleness["stale"] is True, "intel staleness must be True for as_of >14d ago"
    assert staleness["as_of"] == stale_as_of


def test_snapshot_intel_dates_none_safe(monkeypatch):
    """Audit fix B6b: snapshot() must not crash when intel.json has no as_of field."""
    import engine.china_pboc_stance as ps

    monkeypatch.setattr(pw, "_intel", lambda: {"thesis": {"en": "x", "zh": "x"}})
    monkeypatch.setattr(pw, "_nbs_prints", lambda: [])
    monkeypatch.setattr(pw, "_policy_feed", lambda: ("quiet", []))
    monkeypatch.setattr(ps, "snapshot", lambda asof=None: {
        "schema": ps.SCHEMA, "stance": "neutral", "stance_en": "Neutral",
        "stance_zh": "中性", "rationale": {"en": "flat", "zh": "平稳"},
        "corridor": [], "fx": {}, "last_moves": [], "asof": "2026-01-01",
    })

    vm = pw.snapshot()
    assert vm is not None
    # intel with no as_of → staleness.stale must be False (None age treated as not-stale)
    assert vm["intel_dates"]["staleness"]["stale"] is False


# ---- curated intel substrate ----------------------------------------------- #
def test_intel_json_loads_and_has_sections():
    p = config.ROOT / "data" / "china_policy" / "intel.json"
    d = json.loads(p.read_text())
    assert d["schema"] == "china_policy_intel.v1"
    assert d["thesis"]["en"] and d["thesis"]["zh"]
    assert len(d["sector_policy"]) >= 8
    assert all(s["stance"] in ("supportive", "restrictive", "neutral")
               for s in d["sector_policy"])
    assert len(d["npc_targets_2026"]) >= 3
    assert all(p.get("check_by") for p in d["predictions"])


# ---- express-render ownership --------------------------------------------- #
def test_site_only_cli_does_not_request_a_data_write(monkeypatch):
    seen: list[bool] = []
    monkeypatch.setattr(builder, "build", lambda *, site_only=False: seen.append(site_only))

    assert builder.main(["--site-only"]) == 0
    assert seen == [True]


def test_default_cli_preserves_the_asia_lane_data_contract(monkeypatch):
    seen: list[bool] = []
    monkeypatch.setattr(builder, "build", lambda *, site_only=False: seen.append(site_only))

    assert builder.main([]) == 0
    assert seen == [False]


def test_both_express_lanes_render_policy_watch_site_only():
    command = "scripts.build_china_policy_watch --site-only"
    for lane in EXPRESS_LANES:
        workflow = lane.read_text(encoding="utf-8")
        assert workflow.count(command) >= 2, (
            f"{lane.name} must own Policy Watch in all-scope and narrow China renders"
        )
        assert "cn_policy" in workflow.split('local ORDER="', 1)[1].split('"', 1)[0]


def test_render_trigger_and_scope_own_policy_watch_sources():
    workflow = EXPRESS_LANES[0].read_text(encoding="utf-8")
    assert '- "scripts/build_china_policy_watch.py"' in workflow
    assert "templates/china_policy_watch.html.j2" in workflow
    assert "scripts/build_china_policy_watch.py) echo china;;" in workflow


# ---- P0 #1: FX reserves level and MoM share one 亿美元 basis ----------------- #
def test_fx_reserves_level_and_delta_share_yi_usd_basis(monkeypatch):
    """Producer path: fixture frame → china_pboc_stance.snapshot() → view-model.

    SAFE/akshare stores 国家外汇储备-数值 in 亿美元. Display: bn = yi/10
    (same arithmetic as the template's fx.reserves_mom/10). A producer that
    switched `_change_over` to a % change, or a unit-basis swap, must fail here.
    """
    level_yi, prior_yi = 34187.76, 34162.62
    mom_yi = level_yi - prior_yi  # 25.14 亿美元
    fx_df = pd.DataFrame(
        {"fx_reserves": [prior_yi, level_yi], "gold_reserves": [72.0, 72.1]},
        index=pd.to_datetime(["2026-06-01", "2026-07-01"]),
    )
    lpr_df = pd.DataFrame(
        {"lpr_1y": [3.00, 3.00], "lpr_5y": [3.50, 3.50]},
        index=pd.to_datetime(["2026-06-20", "2026-07-20"]),
    )

    def fake_read(group, name):
        if (group, name) == ("china_pboc", "fx_reserves"):
            return fx_df
        if (group, name) == ("china_macro", "lpr_rate"):
            return lpr_df
        return None

    monkeypatch.setattr(ps.store, "read", fake_read)
    s = ps.snapshot()
    assert s is not None, "snapshot must not return None with LPR + FX fixtures"
    got_level = s["fx"]["reserves"]
    got_mom = s["fx"]["reserves_mom"]
    assert abs(got_level - level_yi) < 1e-9
    assert abs(got_mom - mom_yi) < 1e-9
    level_bn = got_level / 10.0
    mom_bn = got_mom / 10.0
    assert abs(level_bn - level_yi / 10.0) < 1e-9
    assert abs(mom_bn - mom_yi / 10.0) < 1e-9
    assert abs(mom_bn - 2.514) < 1e-9

    monkeypatch.setattr(pw, "_intel", lambda: {})
    monkeypatch.setattr(pw, "_nbs_prints", lambda: [])
    monkeypatch.setattr(pw, "_policy_feed", lambda: ("quiet", []))
    monkeypatch.setattr("engine.china_national_team.snapshot", lambda asof=None: None)
    vm = pw.snapshot()
    assert vm is not None
    assert abs(vm["pboc"]["fx"]["reserves"] - level_yi) < 1e-9
    assert abs(vm["pboc"]["fx"]["reserves_mom"] - mom_yi) < 1e-9
    assert abs(vm["pboc"]["fx"]["reserves"] / 10.0 - level_bn) < 1e-9
    assert abs(vm["pboc"]["fx"]["reserves_mom"] / 10.0 - mom_bn) < 1e-9

    tpl = (config.ROOT / "templates" / "china_policy_watch.html.j2").read_text()
    assert "fx.reserves/10000" in tpl
    assert "fx.reserves_mom/10" in tpl
    assert "bn MoM" in tpl and "十亿美元环比" in tpl


# ---- P0 #3: theme word, China-gated tape, designed empty state -------------- #
def test_monetary_theme_label_is_theme_not_issuer():
    from engine.china_news import THEME_LABEL
    from engine.china_news_intel import THEME_LABEL as INTEL_THEME_LABEL
    assert THEME_LABEL["monetary"] == ("Monetary policy", "货币政策")
    assert INTEL_THEME_LABEL["monetary"] == ("Monetary policy", "货币政策")


def test_policy_feed_drops_non_china_rows():
    """ECB/Fed monetary flashes must not survive the China gate; PBoC official
    and China-anchored wire rows must."""
    dropped = [
        ("ECB holds rates steady", "https://www.reuters.com/markets/ecb-holds", 2),
        ("Fed signals pause in tightening cycle", "https://www.bloomberg.com/news/fed", 2),
        ("Eurozone inflation cools", "https://www.ft.com/content/ez-cpi", 2),
    ]
    kept = [
        ("PBoC injects 100bn yuan via 7-day reverse repos",
         "https://www.reuters.com/markets/pboc-omo", 2),
        ("Open market operations",
         "https://www.pbc.gov.cn/en/3688006/index.html", 1),
        ("中国人民银行开展逆回购操作",
         "https://www.stats.gov.cn/english/PressRelease/x", 1),
    ]
    for title, url, tier in dropped:
        assert pw.row_is_china_policy(title, url, tier) is False, title
    for title, url, tier in kept:
        assert pw.row_is_china_policy(title, url, tier) is True, title


def test_policy_feed_gate_adversarial_rows(monkeypatch):
    """Decisive gate cases the round-1 slice omitted (review M1/M2/M6)."""
    # Residual risk, pinned AS PASSING per packet semantics: a title substring
    # "China" is a China anchor, so a Fed story about a China tariff response
    # fills the policy tape. Officialness is now per-row (source chip), not
    # the card title — this row's chip will read bloomberg.com, not PBoC.
    assert pw.row_is_china_policy(
        "Fed weighs China tariff response",
        "https://www.bloomberg.com/news/fed-china-tariff",
        2,
    ) is True

    # Host-only anchor (no title token). Casefold makes "China" match
    # chinadaily.com.cn; yicai.com lands via the china_native page list.
    assert pw.row_is_china_policy(
        "Open market operations expand",
        "https://www.chinadaily.com.cn/a/202609/10/x.html",
        2,
    ) is True
    assert pw.row_is_china_policy(
        "Brokerage survey of listed firms",
        "https://www.yicai.com/news/101234.html",
        2,
    ) is True

    # Documented drop: genuine PBoC EN headline with no China/PBoC/yuan token,
    # from a non-official host. "Central bank" is not an anchor (央行 is CJK-only).
    assert pw.row_is_china_policy(
        "Central bank injects 100bn via reverse repos",
        "https://www.reuters.com/markets/central-bank-omo",
        2,
    ) is False

    # Config-added official page: host matching uses the same source as the
    # fetcher (cfg['official_pages'] or OFFICIAL_PAGES). source_tier=2 so this
    # is the host path, not the tier-1 shortcut.
    monkeypatch.setattr(pw, "_china_news_cfg", lambda: {
        "official_pages": [{
            "name": "Custom PBoC",
            "url": "https://policy.custom-pboc.test/en/",
            "theme": "monetary",
            "tier": "official",
        }],
    })
    assert pw.row_is_china_policy(
        "Open market operations announced",
        "https://policy.custom-pboc.test/en/omo-100bn.html",
        2,
    ) is True
    # Honor source_tier==1 (official-pages fetch tag) even on an unknown host.
    assert pw.row_is_china_policy(
        "Rates held",
        "https://totally-unknown.test/x",
        1,
    ) is True


def test_select_policy_feed_rows_never_falls_back_unfiltered():
    """A tape of only non-China monetary rows yields [] — the designed empty,
    never the unfiltered theme slice."""
    df = pd.DataFrame([
        {"title": "ECB holds rates", "url": "https://www.reuters.com/ecb",
         "source": "reuters", "theme": "monetary", "source_tier": 2,
         "first_seen_utc": "2026-09-10T08:00:00Z", "scheduled_ref": ""},
        {"title": "Fed holds rates", "url": "https://www.bloomberg.com/fed",
         "source": "bloomberg", "theme": "monetary", "source_tier": 2,
         "first_seen_utc": "2026-09-10T07:00:00Z", "scheduled_ref": ""},
        {"title": "PBoC keeps LPR unchanged", "url": "https://www.reuters.com/pboc-lpr",
         "source": "reuters", "theme": "monetary", "source_tier": 2,
         "first_seen_utc": "2026-09-10T06:00:00Z", "scheduled_ref": ""},
    ])
    out = pw._select_policy_feed_rows(df, top_n=12)
    titles = [r["title"] for r in out]
    assert "ECB holds rates" not in titles
    assert "Fed holds rates" not in titles
    assert titles == ["PBoC keeps LPR unchanged"]
    assert out[0]["theme_en"] == "Monetary policy"
    assert out[0]["theme_zh"] == "货币政策"
    assert out[0]["source_chip"] == "reuters.com"

    empty = pw._select_policy_feed_rows(df.iloc[:2], top_n=12)
    assert empty == []

    official = pd.DataFrame([{
        "title": "Open market operations",
        "url": "https://www.pbc.gov.cn/en/3688006/index.html",
        "source": "official", "theme": "monetary", "source_tier": 1,
        "first_seen_utc": "2026-09-10T09:00:00Z", "scheduled_ref": "",
    }])
    off = pw._select_policy_feed_rows(official, top_n=12)
    assert off and off[0]["source_chip"] == "PBoC"


def _feed_frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_policy_feed_tristate(monkeypatch, tmp_path):
    """(a) rows / (b) tape loaded but zero China rows / (c) missing or unreadable."""
    cols = dict(source="reuters", theme="monetary", source_tier=2,
                first_seen_utc="2026-09-10T08:00:00Z", scheduled_ref="")

    # (c) missing parquet
    missing = tmp_path / "absent" / "events.parquet"
    monkeypatch.setattr("engine.china_news_intel._events_path", lambda: missing)
    status, rows = pw._policy_feed()
    assert status == "unavailable" and rows == []

    # (c) read exception (bytes that are not parquet)
    bad = tmp_path / "bad.parquet"
    bad.write_bytes(b"not a parquet file")
    monkeypatch.setattr("engine.china_news_intel._events_path", lambda: bad)
    status, rows = pw._policy_feed()
    assert status == "unavailable" and rows == []

    # (b) tape read OK, only non-China rows survived the gate
    quiet_path = tmp_path / "quiet.parquet"
    _feed_frame([
        {"title": "ECB holds rates", "url": "https://www.reuters.com/ecb", **cols},
        {"title": "Fed holds rates", "url": "https://www.bloomberg.com/fed", **cols},
    ]).to_parquet(quiet_path, index=False)
    monkeypatch.setattr("engine.china_news_intel._events_path", lambda: quiet_path)
    status, rows = pw._policy_feed()
    assert status == "quiet" and rows == []

    # (a) China rows survive
    ok_path = tmp_path / "ok.parquet"
    _feed_frame([
        {"title": "ECB holds rates", "url": "https://www.reuters.com/ecb", **cols},
        {"title": "PBoC keeps LPR unchanged",
         "url": "https://www.reuters.com/pboc-lpr", **cols},
    ]).to_parquet(ok_path, index=False)
    monkeypatch.setattr("engine.china_news_intel._events_path", lambda: ok_path)
    status, rows = pw._policy_feed()
    assert status == "ok"
    assert [r["title"] for r in rows] == ["PBoC keeps LPR unchanged"]


def test_snapshot_surfaces_policy_feed_status(monkeypatch):
    import engine.china_pboc_stance as pboc
    stub = {
        "schema": pboc.SCHEMA, "stance": "neutral", "stance_en": "Neutral",
        "stance_zh": "中性", "rationale": {"en": "flat", "zh": "平稳"},
        "corridor": [], "fx": {}, "last_moves": [], "asof": "2026-01-01",
    }
    monkeypatch.setattr(pw, "_intel", lambda: {"thesis": {"en": "x", "zh": "x"}})
    monkeypatch.setattr(pw, "_nbs_prints", lambda: [])
    monkeypatch.setattr(pboc, "snapshot", lambda asof=None: stub)
    monkeypatch.setattr("engine.china_national_team.snapshot", lambda asof=None: None)

    monkeypatch.setattr(pw, "_policy_feed", lambda: ("ok", [{"title": "x", "source_chip": "PBoC"}]))
    vm = pw.snapshot()
    assert vm["policy_feed_status"] == "ok" and vm["policy_feed"][0]["title"] == "x"

    monkeypatch.setattr(pw, "_policy_feed", lambda: ("quiet", []))
    vm = pw.snapshot()
    assert vm["policy_feed_status"] == "quiet" and vm["policy_feed"] == []

    monkeypatch.setattr(pw, "_policy_feed", lambda: ("unavailable", []))
    vm = pw.snapshot()
    assert vm["policy_feed_status"] == "unavailable" and vm["policy_feed"] == []


def test_policy_tape_empty_state_is_designed():
    tpl = (config.ROOT / "templates" / "china_policy_watch.html.j2").read_text()
    assert "t('Policy tape', '政策快讯')" in tpl
    assert "Official policy tape" not in tpl
    assert "t('官方政策快讯'" not in tpl
    assert 'class="empty"' in tpl
    assert 'class="empty-why"' in tpl
    # (b) quiet tape — round-1 sentence kept
    assert "No China official policy items on the tape right now." in tpl
    assert "当前暂无中国官方政策快讯。" in tpl
    # (c) DATA null — distinct from quiet; never the quiet-tape denial
    assert "Policy tape unavailable right now — source didn't load" in tpl
    assert "政策快讯暂不可用——数据源未加载" in tpl
    assert "pw.policy_feed_status == 'unavailable'" in tpl
    assert "data-tip-en=" in tpl and "data-tip-zh=" in tpl
    assert "data-tip-rc-en=" in tpl and "data-tip-rc-zh=" in tpl
    assert 'tabindex="0"' in tpl
    assert "it.source_chip" in tpl
    lens_lines = [ln for ln in tpl.splitlines() if "data-tip-en" in ln]
    assert lens_lines, "LENS host missing"
    for ln in lens_lines:
        assert "title=" not in ln, f"LENS host must not use title=: {ln}"
