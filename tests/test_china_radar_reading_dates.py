"""China Divergence Radar — every reading carries the date of the observation behind it.

RED-first (DESIGN W27B §SPEC 4): no sector card prints its reading date while the hero
labels the scan's build stamp `· as of` (templates/china_radar.html.j2:72,99-100), and the
sector signal producers return no `data_asof` (engine/china_radar.py:65-225) although the
venue producers already do (:311,437,505). Synthetic fixtures only: `store.read` and
`lib.config.data_dir` are monkeypatched, so nothing reads data/ or the network.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from engine import china_radar as cr

ROOT = Path(__file__).resolve().parent.parent

_ROW_KEYS = ["pair", "signal_key", "signal_en", "signal_zh", "sector", "sector_etf",
             "sector_en", "sector_zh", "sign", "strength", "conviction100", "signal_value",
             "signal_dir", "signal_detail_en", "signal_detail_zh", "price_rs", "price_rs_z",
             "reliability", "candidates", "thesis", "hypothesis_en", "hypothesis_zh"]


class _Cv:
    """Stand-in for engine.china_conviction (the only leg _build_row uses)."""

    @staticmethod
    def to_100(x, lo=0.0, hi=1.0):
        return int(round(max(lo, min(hi, float(x or 0.0))) * 100))


def _make_env():
    """Jinja2 environment mirroring tests/test_china_radar_venue.py::TestTemplateRender."""
    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=False,
    )
    try:
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    except Exception:  # noqa: BLE001
        env.globals.update(td=lambda en: en, tr=lambda en: en, t=lambda en, zh="": en)
    return env


def _card(**over):
    """The committed Banks card shape (a sector divergence; no venue rows in the fixture)."""
    row = {
        "pair": "credit_impulse->512800.SS", "signal_key": "credit_impulse", "family": None,
        "signal_en": "Total social financing", "signal_zh": "社会融资规模",
        "sector": "Banks", "sector_etf": "512800.SS",
        "sector_en": "Banks", "sector_zh": "银行",
        "sign": "negative", "strength": 0.42, "conviction100": 63,
        "signal_value": -6.4, "signal_dir": -1,
        "signal_detail_en": "TSF impulse -6.4% (6m chg of 12m sum)",
        "signal_detail_zh": "社融脉冲 -6.4%（12月滚动和的6月变化）",
        "price_rs": 12.4, "price_rs_z": 1.8,
        "reliability": {"hit_rate": None, "n_resolved": 0, "basis": "unproven"},
        "candidates": [], "thesis": "Credit impulse tends to lead bank prices.",
        "hypothesis_en": "Banks' lead should fade.", "hypothesis_zh": "银行的领先应消退。",
    }
    row.update(over)
    return row


def _render(card, asof="2026-10-16"):
    radar = {
        "schema": "china_radar.v1", "is_context_only": True,
        "asof": asof, "built": "2026-10-16T00:00:00Z",
        "divergences": [card], "in_line": [],
        "n_active": 1, "n_pairs": 1,
        "disclaimer_en": "Context only.", "disclaimer_zh": "仅供参考。",
    }
    return _make_env().get_template("china_radar.html.j2").render(radar=radar, ledger=None)


def _rs_div(html):
    """The sector card's .rs line only (the venue cards are absent from these fixtures)."""
    return html.split('<div class="rs">', 1)[1].split('<div class="strength">', 1)[0]


def _monthly(col, values, end, day=1):
    """A monthly frame whose last index lands on `end` at the given day-of-month."""
    idx = pd.date_range(end=end, periods=len(values), freq="MS")
    if day != 1:
        idx = idx + pd.Timedelta(days=day - 1)
    return pd.DataFrame({col: values}, index=idx)


def _reader(mapping):
    return lambda group, name: mapping.get(name)


# ---- template: the sector card dates its own reading ------------------------ #
def test_sector_card_prints_its_reading_date():
    rs = _rs_div(_render(_card(data_asof="2026-09-01")))
    assert "2026-09-01" in rs
    assert "data as-of" in rs and "数据截至" in rs
    assert '<span class="mut">' in rs


def test_sector_card_without_a_date_prints_no_date_label():
    """No fabricated label when the producer could not date the reading."""
    html = _render(_card())
    assert "data as-of" not in html and "数据截至" not in html
    assert "2026-09-01" not in html
    assert _rs_div(html)                      # the card still renders


# ---- template: the hero stops calling the build stamp a data date ----------- #
def test_hero_says_scan_run_not_as_of():
    html = _render(_card(data_asof="2026-09-01"))
    lens = html.split('<p class="lens">', 1)[1].split("</p>", 1)[0]
    assert "· scan run" in lens and "· 扫描日期" in lens
    assert "· as of" not in lens and "· 截至" not in lens
    assert "2026-10-16" in lens               # the value itself is unchanged


# ---- producers: the observation date they actually used -------------------- #
def test_credit_impulse_signal_reports_its_observation_date(monkeypatch):
    df = _monthly("tsf_total", [2.5e12 + i * 1e10 for i in range(36)], "2026-09-01")
    monkeypatch.setattr(cr.store, "read", _reader({"tsf": df}))
    sig = cr._sig_credit_impulse()
    assert sig is not None
    assert sig["data_asof"] == "2026-09-01"     # the impulse series' last index
    # never fabricate: a non-datetime index omits the key instead of inventing one
    txt = df.copy()
    txt.index = [str(d.date()) for d in df.index]
    monkeypatch.setattr(cr.store, "read", _reader({"tsf": txt}))
    sig2 = cr._sig_credit_impulse()
    assert sig2 is not None and "data_asof" not in sig2


def test_pboc_easing_uses_the_newest_leg(monkeypatch):
    lpr = _monthly("lpr_1y", [3.45] * 18 + [3.35] * 12, "2026-09-01", day=20)
    rrr = _monthly("rrr_change", [0.0] * 24 + [-0.005] * 6, "2025-05-01", day=7)
    monkeypatch.setattr(cr.store, "read", _reader({"lpr_rate": lpr, "rrr": rrr}))
    assert cr._sig_pboc_easing()["data_asof"] == "2026-09-20"
    # reverse the vintages: the RRR leg is now the newest read, so its date wins
    lpr2 = _monthly("lpr_1y", [3.45] * 18 + [3.35] * 12, "2025-05-01", day=7)
    rrr2 = _monthly("rrr_change", [0.0] * 24 + [-0.005] * 6, "2026-09-01", day=20)
    monkeypatch.setattr(cr.store, "read", _reader({"lpr_rate": lpr2, "rrr": rrr2}))
    assert cr._sig_pboc_easing()["data_asof"] == "2026-09-20"
    # neither series read -> no key at all
    monkeypatch.setattr(cr.store, "read", lambda group, name: None)
    assert "data_asof" not in cr._sig_pboc_easing()


def test_pmi_ppi_southbound_report_their_observation_date(monkeypatch):
    pmi = _monthly("pmi_mfg", [50.1 + i * 0.05 for i in range(24)], "2026-09-01")
    monkeypatch.setattr(cr.store, "read", _reader({"pmi": pmi}))
    assert cr._sig_pmi()["data_asof"] == "2026-09-01"
    ppi = _monthly("ppi_yoy", [-2.1 + i * 0.02 for i in range(24)], "2026-08-01")
    monkeypatch.setattr(cr.store, "read", _reader({"ppi": ppi}))
    assert cr._sig_ppi()["data_asof"] == "2026-08-01"
    sb = pd.DataFrame({"net": [1.0e8] * 120},
                      index=pd.date_range(end="2026-10-16", periods=120, freq="B"))
    monkeypatch.setattr(cr.store, "read", _reader({"southbound": sb}))
    assert cr._sig_southbound()["data_asof"] == "2026-10-16"


def test_sector_flow_signal_carries_the_snapshot_date():
    sig = cr._sector_flow_signal("银行", {"银行": 5.0}, asof="2026-10-16")
    assert sig["data_asof"] == "2026-10-16"
    assert sig["dir"] == 1 and sig["value"] == 5.0        # existing legs unchanged


def test_sector_flow_signal_omits_the_date_without_a_snapshot():
    assert "data_asof" not in cr._sector_flow_signal("银行", {"银行": 5.0})
    assert "data_asof" not in cr._sector_flow_signal("银行", {"银行": 5.0}, asof=None)
    assert "data_asof" not in cr._sector_flow_signal("银行", {"银行": 5.0}, asof="")
    assert cr._sector_flow_signal("不存在", {"银行": 5.0}, asof="2026-10-16") is None


def test_sector_flow_asof_reads_the_snapshot(monkeypatch, tmp_path):
    import lib.config as cfg
    monkeypatch.setattr(cfg, "data_dir", lambda: tmp_path)
    assert cr._sector_flow_asof() is None                 # no snapshot on disk
    (tmp_path / "tushare").mkdir(parents=True)
    pd.DataFrame([
        {"sector_code": "BK0001.DC", "name": "银行", "net_amount_rate": 4.0,
         "content_type": "行业", "trade_date": "20261015"},
        {"sector_code": "BK0001.DC", "name": "银行", "net_amount_rate": 5.0,
         "content_type": "行业", "trade_date": "20261016"},
    ]).to_parquet(tmp_path / "tushare" / "moneyflow_sector.parquet", index=False)
    assert cr._sector_flow_asof() == "2026-10-16"         # MAX trade_date, not the min
    assert cr._sector_flow_boards() == {"银行": 5.0}       # pinned return shape unchanged


# ---- _build_row stays additive --------------------------------------------- #
def test_build_row_is_additive(monkeypatch):
    monkeypatch.setattr(cr, "_price_rs", lambda etf, lookback=63: (12.4, 1.8))
    sig = {"value": -6.4, "dir": -1, "strength": 0.42,
           "detail_en": "TSF impulse -6.4% (6m chg of 12m sum)",
           "detail_zh": "社融脉冲 -6.4%（12月滚动和的6月变化）",
           "data_asof": "2026-09-01"}
    args = (_Cv, "credit_impulse", "Total social financing", "社会融资规模",
            "512800.SS", "Banks", "银行", sig, "thesis", {}, {}, {})
    row = cr._build_row(*args)
    assert [k for k in row if k != "data_asof"] == _ROW_KEYS    # order + keys unchanged
    assert row["data_asof"] == "2026-09-01"
    # a signal that could not be dated leaves the key out entirely (never "")
    sig.pop("data_asof")
    assert "data_asof" not in cr._build_row(*args)
    sig["data_asof"] = ""
    assert "data_asof" not in cr._build_row(*args)


def test_scan_passes_the_flow_snapshot_to_the_sector_rows(monkeypatch):
    monkeypatch.setattr(cr, "_ledger_reliability", lambda: ({}, {}))
    monkeypatch.setattr(cr, "_PAIRS", [])
    monkeypatch.setattr(cr, "_VENUE_PAIRS", [])
    monkeypatch.setattr(cr, "_sector_flow_boards", lambda: {"银行": 5.0})
    monkeypatch.setattr(cr, "_sector_flow_asof", lambda: "2026-10-16")
    monkeypatch.setattr(cr, "_price_rs", lambda etf, lookback=63: (-8.6, -1.5))
    out = cr.scan(asof="2026-10-16")
    rows = [r for r in out["divergences"] if r["signal_key"] == "sector_flow"]
    assert rows, out["n_pairs"]
    assert all(r["data_asof"] == "2026-10-16" for r in rows)
