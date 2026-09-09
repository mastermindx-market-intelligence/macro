"""Pure user-adjustable valuation assumptions (B-F07-2).

No IO, no network, no clock. Reads a valuation_scenario.v1 blob and emits
valuation_scenario_controls.v1 for the sandbox panel. The three V1 server
cards stay the authority; this module only names the three free parameters
and evaluates the same closed-form per-share identity at caller-supplied
points.

Range derivation (frozen spec section 2.3, verbatim): each range is the V1
frozen triple's own span, widened to a round number that still contains
every V1 preset with headroom. V1 spans growth [-2, 7] -> [-10, 20];
margin [-1.5, 1.5] -> [-3.0, 3.0]; multiple [14, 22] -> [8, 35]. Defaults
are exactly V1's base case (3, 0, 18), so the panel's first paint is
numerically identical to the Base card.

Rounding: do not use Python round() (banker's rounding; JS has no equivalent).
round2(v) = floor(v * 100 + 0.5) / 100 for v > 0. The panel never paints
v <= 0.

SCENARIOS and MISSING_LABELS are imported read-only from
engine.valuation_scenario so presets cannot drift from V1's frozen triples
and a future null path can reuse V1 diction without re-typing.
"""
from __future__ import annotations

import math

from engine.valuation_scenario import MISSING_LABELS, SCENARIOS

# Each range is the V1 frozen triple's own span, widened to a round number
# that still contains every V1 preset with headroom. V1 spans growth
# [-2, 7] -> [-10, 20]; margin [-1.5, 1.5] -> [-3.0, 3.0]; multiple
# [14, 22] -> [8, 35]. Defaults are exactly V1's base case (3, 0, 18).
CONTROLS = (
    {"key": "sales_growth_pct", "min": -10, "max": 20, "step": 0.5, "default": 3},
    {"key": "margin_delta_pp", "min": -3.0, "max": 3.0, "step": 0.1, "default": 0},
    {"key": "earnings_multiple", "min": 8, "max": 35, "step": 1, "default": 18},
)

_MARGIN_BASE_FLOOR = 0.01

# Imported read-only; kept bound so a future null path can reuse V1 diction
# without re-typing. The sandbox panel's too-thin sentence is the B-F07-2
# verbatim copy, not MISSING_LABELS["margin_too_thin"].
_V1_MISSING_LABELS = MISSING_LABELS


def round2(v):
    """Half-up to two decimals for v > 0. Matches JS Math.floor(v*100+0.5)/100."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or f <= 0 or f == float("inf"):
        return None
    return math.floor(f * 100 + 0.5) / 100


def per_share_at(ni, revenue, shares, g, m_pp, mult):
    """Closed-form per-share value, or None when the setting is not paintable.

    Frozen identity (same four operations as V1, different rounding):
      per_share = ni * (1 + g/100) * (1 + (m_pp/100) / net_margin_base)
                  * mult / shares
    then round2. Returns None when any input is missing, shares is zero,
    |net_margin_base| is under the 1% floor, the per-setting margin gate
    fails (net_margin_base + m_pp/100 <= 0), or the result is not a
    positive finite number. No negative dollar figure is ever returned.
    """
    try:
        ni_f = float(ni)
        rev_f = float(revenue)
        sh_f = float(shares)
        g_f = float(g)
        m_f = float(m_pp)
        mult_f = float(mult)
    except (TypeError, ValueError):
        return None
    for x in (ni_f, rev_f, sh_f, g_f, m_f, mult_f):
        if x != x or x == float("inf") or x == float("-inf"):
            return None
    if ni_f <= 0 or rev_f == 0 or sh_f == 0:
        return None
    net_margin_base = ni_f / rev_f
    if abs(net_margin_base) < _MARGIN_BASE_FLOOR:
        return None
    if (net_margin_base + (m_f / 100.0)) <= 0:
        return None
    raw = ni_f * (1 + g_f / 100.0) * (1 + (m_f / 100.0) / net_margin_base) * mult_f / sh_f
    if raw != raw or raw <= 0 or raw == float("inf"):
        return None
    return round2(raw)


def _num(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:
        return None
    return f


def controls_blob(v1_blob):
    """Build valuation_scenario_controls.v1 from a V1 compute() blob, or None.

    Returns None when the V1 blob is missing, when net income is missing or
    not positive, when revenue is missing, when shares are missing or zero,
    when the margin base is under the 1% floor, or when V1's base scenario
    is not computable. Every key in the frozen contract is present or the
    whole blob is None. No key is ever 0 standing in for missing.
    """
    if not v1_blob or not isinstance(v1_blob, dict):
        return None
    base = v1_blob.get("base") or {}
    ni = _num((base.get("net_income") or {}).get("value"))
    revenue = _num((base.get("revenue") or {}).get("value"))
    shares = _num((base.get("share_count") or {}).get("value"))
    if ni is None or ni <= 0:
        return None
    if revenue is None:
        return None
    if shares is None or shares == 0:
        return None
    if revenue == 0:
        return None
    net_margin_base = ni / revenue
    if abs(net_margin_base) < _MARGIN_BASE_FLOOR:
        return None

    scenarios = v1_blob.get("scenarios") or []
    by_key = {s.get("key"): s for s in scenarios if isinstance(s, dict)}
    base_sc = by_key.get("base")
    if not base_sc:
        return None
    base_ps = base_sc.get("per_share")
    if not base_sc.get("computable") or base_ps is None or base_ps <= 0:
        return None

    presets = {}
    for key, g, m_pp, mult in SCENARIOS:
        presets[key] = {
            "sales_growth_pct": g,
            "margin_delta_pp": m_pp,
            "earnings_multiple": mult,
        }

    ticker = v1_blob.get("ticker") or ""
    fy = v1_blob.get("fy")
    period_end = v1_blob.get("period_end")
    if fy is None or not period_end:
        return None

    return {
        "schema": "valuation_scenario_controls.v1",
        "ticker": ticker,
        "tier": "research_display_only",
        "fy": fy,
        "period_end": period_end,
        "source": "SEC filings",
        "inputs": {
            "net_income": ni,
            "revenue": revenue,
            "shares": shares,
            "net_margin_base": net_margin_base,
        },
        "margin_base_floor": _MARGIN_BASE_FLOOR,
        "controls": [dict(c) for c in CONTROLS],
        "presets": presets,
        "server_default": {
            "sales_growth_pct": 3,
            "margin_delta_pp": 0,
            "earnings_multiple": 18,
            "per_share": base_ps,
        },
    }
