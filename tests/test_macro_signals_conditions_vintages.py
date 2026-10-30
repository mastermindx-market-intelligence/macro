"""MS-W32A-3 — date and qualify each Real-time-conditions tile; absent data is not green.

Two defects in the nine-tile grid at `templates/macro_signals.html.j2`:
  (a) no tile printed an as-of, although `engine/conditions.py:570-604` records the
      LAST DATE EACH INPUT PRINTED in `conditions.vintages` plus a `stale_inputs` list;
  (b) `_fc_state` / `_ln_state` fell through to their `else 'good'` arm when the driving
      field was null, so a tile with NO data painted the measured-good colour and the
      Jobs tile asserted "layoffs steady" off a null claims print.

Fixtures are synthetic dicts carrying exactly the committed values quoted in the W32A
design packet (F3). No `data/`, no network, no builder run.
"""
from __future__ import annotations

import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Undefined

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "templates"

# conditions.vintages entries, verbatim from data/regime/latest.json (packet F3).
_VINTAGES = {
    "nfci": {"asof": "2026-10-02", "age_days": 17, "stale": True,
             "label": "NFCI (financial conditions)", "cadence_days": 14},
    "hy_oas": {"asof": "2026-10-13", "age_days": 6, "stale": True,
               "label": "High-yield OAS", "cadence_days": 5},
    "us10y": {"asof": "2026-10-13", "age_days": 6, "stale": True,
              "label": "10-year Treasury yield", "cadence_days": 5},
    "ebp": {"asof": "2026-09-01", "age_days": 48, "stale": False,
            "label": "Excess bond premium", "cadence_days": 70},
    "vix_term": {"asof": "2026-10-19", "age_days": 0, "stale": False,
                 "label": "VIX term structure", "cadence_days": 5},
}
_STALE_INPUTS = ["anfci", "hy_oas", "nfci", "ofr_fsi", "us10y"]
_FC_NULL = {"nfci": None, "nfci_pctile": None, "state": None, "trend": None}
# Committed record quoted in the design packet F3 (data/regime/latest.json).
_LN_NULL_CLAIMS = {
    "claims_yoy_pct": None,
    "claims_z": None,
    "claims_trend": None,
    "indeed_chg_3m_pct": 1.9017633708617199,
    "withheld_tax_yoy_pct": 6.424586312369773,
    "read": "labor firm",
}
_RA = {"roro": 0.4, "roro_state": "risk-on", "vrp": 3.2, "vix_term": 1.08,
       "stock_bond_corr": 0.32}


def _make_env() -> Environment:
    """Jinja2 env with FileSystemLoader on templates/ and minimal globals."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        undefined=Undefined,  # silent undefined — mirrors build_site behaviour
    )

    def _td(val, *_args, **_kw):
        return val if val is not None else ""

    def _tr(*args, **kwargs):
        return args[0] if args else ""

    env.globals.update(td=_td, tr=_tr, zip=zip)
    return env


def _render(vm: dict) -> str:
    return _make_env().get_template("macro_signals.html.j2").render(**vm)


def _base_vm() -> dict:
    """Absolute-minimum vm — every optional key None, cycle panel reachable."""
    return {
        "latest": {
            "date": "2026-10-19",
            "growth_score": None,
            "inflation_score": None,
            "business_cycle": {"available": True, "phase": {"label": "Expansion"}},
            "conditions": {},
        },
        "market_state": None,
        "msig_stances": None,
        "fear_greed": None,
        "fear_euphoria": None,
        "vix": None,
        "chart_liquidity": None,
        "chart_credit_breadth": None,
        "chart_vix": None,
        "commodities": [],
        "positioning": [],
        "cross_asset": None,
        "fx_context": None,
    }


def _vm(conditions: dict) -> dict:
    vm = _base_vm()
    vm["latest"]["conditions"] = conditions
    return vm


def _tile(html: str, label_en: str) -> str:
    """The sig-tile block whose l-en sig-label carries `label_en`."""
    i = html.index(">%s</span>" % label_en)
    start = html.rindex('<div class="sig-tile', 0, i)
    end = html.find('<div class="sig-tile', i)
    if end == -1:
        end = html.find('<div class="panel', i)
    return html[start:end if end != -1 else len(html)]


def test_financial_conditions_tile_prints_its_vintage():
    """The NFCI vintage (asof + age vs cadence) renders inside its own tile."""
    conds = {"financial_conditions": dict(_FC_NULL), "vintages": dict(_VINTAGES)}
    tile = _tile(_render(_vm(conds)), "Financial conditions")
    assert "2026-10-02" in tile
    assert "17" in tile and "14" in tile
    assert "data-vin-stale>" in tile, "a stale input must carry the stale marker"


def test_absent_state_is_neutral_not_good():
    """A null `state` paints the neutral tile colour, never the measured-good one."""
    conds = {"financial_conditions": dict(_FC_NULL), "vintages": dict(_VINTAGES)}
    tile = _tile(_render(_vm(conds)), "Financial conditions")
    assert '<div class="sig-tile flat">' in tile
    assert '<div class="sig-tile good">' not in tile


def test_jobs_tile_does_not_claim_a_direction_from_a_null():
    """A null claims print must not read as `layoffs steady / 裁员平稳`."""
    conds = {"labor_nowcast": dict(_LN_NULL_CLAIMS)}
    html = _render(_vm(conds))
    tile = _tile(html, "Jobs & activity")
    assert "layoffs steady" not in tile
    assert "裁员平稳" not in tile
    assert "layoffs rising" not in tile
    assert '<div class="sig-tile flat">' in tile


def test_stale_inputs_list_is_disclosed_once():
    """The producer's stale_inputs list is disclosed once, by its own labels."""
    conds = {"financial_conditions": dict(_FC_NULL), "vintages": dict(_VINTAGES),
             "stale_inputs": list(_STALE_INPUTS)}
    html = _render(_vm(conds))
    assert html.count("data-vin-stale-list") == 1
    for expect in ("NFCI (financial conditions)", "High-yield OAS",
                   "10-year Treasury yield", "anfci", "ofr_fsi"):
        assert expect in html, expect


def test_fresh_vintage_prints_the_date_without_a_stale_flag():
    """A fresh input prints its date and no stale marker (kills flag-everything)."""
    conds = {"risk_appetite": dict(_RA),
             "vintages": {"vix_term": dict(_VINTAGES["vix_term"])}}
    tile = _tile(_render(_vm(conds)), "Risk appetite")
    assert "2026-10-19" in tile
    assert "data-vin-stale>" not in tile
    assert ">stale<" not in tile and "已过期" not in tile


def test_legacy_payload_without_vintages_renders():
    """A payload with no `vintages` key at all renders, with no vintage markup."""
    html = _render(_vm({"financial_conditions": dict(_FC_NULL)}))
    assert ">Financial conditions</span>" in html
    assert "data-vin>" not in html
    assert "data-vin-stale-list" not in html


def test_every_null_driver_renders_neutral():
    """Each scored tile whose driving field is null paints `flat`, never a verdict."""
    conds = {
        "recession": {"score": None, "sahm": None, "ny_fed_prob": None, "ebp": None},
        "drawdown_risk": {"score": None, "dd10_prob_pct": None, "base_rate_pct": None},
        "systemic_stress": {"state": None, "ofr_fsi": None, "leading_driver": None,
                            "cp_stress": None},
        "growth_nowcast": {"gdpnow": None, "wei": None},
        "inflation_nowcast": {"sticky_ann": None, "flexible_ann": None},
    }
    html = _render(_vm(conds))
    for label in ("Recession risk", "Drawdown risk", "System stress",
                  "Growth right now", "Inflation right now"):
        tile = _tile(html, label)
        assert '<div class="sig-tile flat">' in tile, label


def test_never_printed_input_prints_no_date():
    """The producer's `asof: None` record (input never printed) renders no vintage."""
    conds = {"financial_conditions": {"nfci": 0.1, "nfci_pctile": 0.4,
                                      "state": "loose", "trend": None},
             "vintages": {"nfci": {"asof": None, "age_days": None, "stale": None,
                                   "label": "NFCI (financial conditions)",
                                   "cadence_days": 14}}}
    tile = _tile(_render(_vm(conds)), "Financial conditions")
    assert "data-vin>" not in tile
    assert "None" not in tile
    assert '<div class="sig-tile good">' in tile, "a measured loose read keeps its colour"
