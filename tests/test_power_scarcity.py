"""engine.power_scarcity — the physical bottleneck read for the power cluster from FRED
electricity series. Verifies graceful None without FRED, and a TIGHT band on rising demand/
price. FRED access (_first) is monkeypatched so no network/store is needed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine import power_scarcity as ps


def _accel(n=60):
    # flat then a recent surge -> YoY rising AND the latest level well above its history (so both
    # _z(_yoy(.)) and _z(level) are positive — a genuine recent tightening, not a linear drift)
    idx = pd.date_range("2020-01-01", periods=n, freq="MS")
    vals = np.concatenate([np.full(n - 12, 100.0), np.linspace(102.0, 140.0, 12)])
    return pd.Series(vals, index=idx)


def test_none_without_fred(monkeypatch):
    monkeypatch.setattr(ps, "_first", lambda ids: None)
    monkeypatch.setattr(ps, "_queue_pull", lambda: None)
    assert ps.compute_power_scarcity(write_ledger=False) is None


def test_tight_on_rising_demand_and_price(monkeypatch):
    monkeypatch.setattr(ps, "_first", lambda ids: _accel())      # every leg gets a surging series
    monkeypatch.setattr(ps, "_queue_pull", lambda: None)
    out = ps.compute_power_scarcity(write_ledger=False)
    assert out is not None
    assert out["band"] in ("TIGHTENING", "TIGHT", "SOLD_OUT") and out["tightness"] > 0
    assert out["regime"] is True                                 # all present legs positive
    # the read is applied to every power-cluster theme
    assert "data_center_power" in out["themes"] and "nuclear_power" in out["themes"]
    assert out["themes"]["data_center_power"]["band"] == out["band"]


def test_queue_pull_from_cache(monkeypatch, tmp_path):
    (tmp_path / "eia").mkdir(parents=True, exist_ok=True)
    (tmp_path / "eia" / "interconnection_queue.json").write_text('{"total_gw_yoy": 40.0}')
    monkeypatch.setattr(ps.config, "data_dir", lambda: tmp_path)
    assert ps._queue_pull() == 2.0                               # +40%/yr -> clamped to +2 z


# ── W16-B: the LBNL queued-GW figures ride the payload — display-only ────
# The queue leg reaches the composite as one squashed z; the physical GW the reader
# can actually check (2,061 GW queued at end-2025 vs 2,290 GW at end-2024)
# was dropped on the floor and never printed. These tests pin the disclosure, and pin
# that it stays a disclosure: the composite must not move when the figures move.

_FIG_JSON = ('{"total_gw": 1234.0, "prior_gw": 1000.0, "prior_year": 2019,'
             ' "asof_year": 2020, "total_gw_yoy": 20.0}')


def _queue_cache(tmp_path, monkeypatch, text):
    """Point config.data_dir() at a tmp cache carrying exactly `text`."""
    (tmp_path / "eia").mkdir(parents=True, exist_ok=True)
    (tmp_path / "eia" / "interconnection_queue.json").write_text(text)
    monkeypatch.setattr(ps.config, "data_dir", lambda: tmp_path)


def test_queue_figures_returns_only_the_positive_figures(monkeypatch, tmp_path):
    _queue_cache(tmp_path, monkeypatch, _FIG_JSON)
    out = ps._queue_figures()
    assert out == {"queue_total_gw": 1234.0, "queue_prior_gw": 1000.0,
                   "queue_prior_year": 2019}
    assert isinstance(out["queue_prior_year"], int)


def test_queue_figures_junk_table_never_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(ps.config, "data_dir", lambda: tmp_path)
    assert ps._queue_figures() == {}                       # missing file
    cases = [
        ("[]", {}),                                         # non-dict JSON
        ("{not json", {}),                                  # bad JSON
        ('{"total_gw": null}', {}),                         # absent value
        ('{"total_gw": "abc"}', {}),                        # non-numeric
        ('{"total_gw": Infinity}', {}),                     # not finite
        ('{"total_gw": NaN}', {}),                          # not a number
        ('{"total_gw": 0}', {}),                            # not positive
        ('{"total_gw": -5}', {}),                           # not positive
        ('{"prior_year": "x", "total_gw": 10}', {"queue_total_gw": 10.0}),
        ('{"prior_gw": 1000.0, "prior_year": 2019}',
         {"queue_prior_gw": 1000.0, "queue_prior_year": 2019}),
    ]
    for text, want in cases:
        _queue_cache(tmp_path, monkeypatch, text)
        assert ps._queue_figures() == want, text


def test_figures_are_display_only(monkeypatch, tmp_path):
    monkeypatch.setattr(ps, "_first", lambda ids: _accel())
    _queue_cache(tmp_path, monkeypatch, _FIG_JSON)
    out = ps.compute_power_scarcity(write_ledger=False)
    assert out["queue_total_gw"] == 1234.0
    assert out["queue_buildout_asof_year"] == 2020
    monkeypatch.setattr(ps, "_queue_figures", lambda: {})
    plain = ps.compute_power_scarcity(write_ledger=False)
    assert plain["tightness"] == out["tightness"]           # the z math is untouched
    assert plain["band"] == out["band"]
    assert plain["n_legs"] == out["n_legs"]
    assert plain["legs"] == out["legs"]
    assert "queue_total_gw" not in plain
    # and the figures ride ONLY while the queue leg is in the composite
    monkeypatch.setattr(ps, "_queue_pull", lambda: None)
    monkeypatch.setattr(ps, "_queue_figures", lambda: {"queue_total_gw": 1234.0})
    no_leg = ps.compute_power_scarcity(write_ledger=False)
    assert "queue_total_gw" not in no_leg
    assert "queue_buildout_asof_year" not in no_leg


_POWER_CTX = dict(
    cascade={"sizing": None, "demand_pool": None, "dislocation": None},
    themes=[], stage_counts={}, stage_order=[],
    demand_pool=None, dislocation=None,
    track={"foresight": 0, "bottleneck": 0, "glut": 0, "revisions": 0,
           "guidance": 0, "emergence": 0, "subsector": 0, "recent": []},
    grade=None, emergence=None, subsectors=None,
    convergence=None, analyst=None, monitor=None, health=None,
    asof="2026-07-02", generated_utc="2026-07-02 00:00 UTC",
    nav_prefix="", active_section="research", active_page="foresight",
)


def _render_power_card(power):
    """The electricity card out of the real template with a synthetic payload.
    Minimal-context shape mirrors the Jinja renders in test_foresight_cascade.py."""
    import pathlib
    from jinja2 import Environment, FileSystemLoader
    repo = pathlib.Path(__file__).resolve().parent.parent
    env = Environment(loader=FileSystemLoader(str(repo / "templates")), autoescape=True)
    html = env.get_template("foresight.html.j2").render(**dict(_POWER_CTX, power=power))
    start = html.index('<div class="fx-bd tight"')
    return html[start:html.index("\n  </div>", start)]


def test_card_renders_the_queued_gw_figures_bilingually():
    card = _render_power_card({"band": "TIGHT", "tightness": 1.2, "regime": False,
                               "queue_total_gw": 1234.0, "queue_prior_gw": 1000.0,
                               "queue_prior_year": 2019,
                               "queue_buildout_asof_year": 2020})
    assert "1,234 GW" in card
    assert "2020" in card and "1,000 GW" in card and "2019" in card
    assert "排队等待并网" in card
    assert "2,600" not in card                              # only payload numbers
    assert "None" not in card


def test_card_without_figures_stays_quiet_and_labels_a_stale_edition():
    base = {"band": "TIGHT", "tightness": 1.2, "regime": False}
    card = _render_power_card(dict(base, queue_buildout_asof_year=2020,
                                   queue_buildout_stale="the LBNL 2020 edition is old"))
    assert "Tight" in card and "+1.20" in card              # the card still renders
    assert "GW" not in card                                 # no figure -> no clause
    assert "older edition" in card and "待更新" in card
    plain = _render_power_card(base)
    assert "GW" not in plain and "older edition" not in plain


# ── The year is a DATA year, not an edition year ────────────────────────
# `asof_year` is the end-of-year queue snapshot (collectors/lbnl_queue.py
# OUTPUT: "latest data year"). LBNL names each "Queued Up" edition a year
# after its data — the 2026 Edition reports queues at end-2025 — so
# "(LBNL 2025 edition)" named an edition that does not hold these figures.

def test_card_dates_the_queue_by_data_year_not_edition():
    card = _render_power_card({"band": "TIGHT", "tightness": 1.2, "regime": False,
                               "queue_total_gw": 2061.0, "queue_prior_gw": 2290.0,
                               "queue_prior_year": 2024,
                               "queue_buildout_asof_year": 2025})
    assert "2,061 GW queued for grid connection (LBNL, end-2025)" in card
    assert "vs 2,290 GW at end-2024" in card
    assert "排队等待并网 2,061 GW（LBNL，2025 年末）" in card
    assert "，2024 年末为 2,290 GW" in card
    assert "edition)" not in card and "版）" not in card


def test_stale_message_names_the_data_year(monkeypatch, tmp_path):
    monkeypatch.setattr(ps, "_first", lambda ids: _accel())
    _queue_cache(tmp_path, monkeypatch, _FIG_JSON)          # asof_year 2020 -> stale
    out = ps.compute_power_scarcity(write_ledger=False)
    msg = out["queue_buildout_stale"]
    assert "LBNL data through end-2020" in msg
    assert "2020 edition" not in msg
    assert "collectors/lbnl_queue.py" in msg                # the remedy pointer stays
