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
are exactly V1's base case, read from CONTROLS (never re-typed as literals
next to the derived per_share), so the panel's first paint is numerically
identical to the Base card under the same round2 rule.

Rounding: do not use Python round() (banker's rounding; JS has no equivalent).
round2(v) = floor(v * 100 + 0.5) / 100 for v > 0. The panel never paints
v <= 0. server_default.per_share is computed through the same rule.

SCENARIOS is imported read-only from engine.valuation_scenario so presets
cannot drift from V1's frozen triples.
"""
from __future__ import annotations

import math

from engine.valuation_scenario import SCENARIOS

# Each range is the V1 frozen triple's own span, widened to a round number
# that still contains every V1 preset with headroom. V1 spans growth
# [-2, 7] -> [-10, 20]; margin [-1.5, 1.5] -> [-3.0, 3.0]; multiple
# [14, 22] -> [8, 35]. Defaults are exactly V1's base case.
CONTROLS = (
    {"key": "sales_growth_pct", "min": -10, "max": 20, "step": 0.5, "default": 3},
    {"key": "margin_delta_pp", "min": -3.0, "max": 3.0, "step": 0.1, "default": 0},
    {"key": "earnings_multiple", "min": 8, "max": 35, "step": 1, "default": 18},
)

_MARGIN_BASE_FLOOR = 0.01


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
    out = round2(raw)
    # round2 collapses a positive sub-half-cent raw to 0.0, and 0.00 is not a
    # paintable per-share value. Return None, which is what the JS twin returns
    # at the same point, so the two languages cannot disagree there.
    if out is None or out <= 0:
        return None
    return out


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


def _control_defaults():
    return {c["key"]: c["default"] for c in CONTROLS}


def controls_blob(v1_blob):
    """Build valuation_scenario_controls.v1 from a V1 compute() blob, or None.

    Returns None when the V1 blob is missing, when net income is missing or
    not positive, when revenue is missing, when shares are missing or zero,
    or when V1's base scenario is not computable. When |net_margin_base| is
    under the 1% floor, returns a blob with too_thin_base True and no
    controls (the panel then renders only the single-line copy). Every key
    in the frozen contract is present on the interactive blob, or the whole
    blob is None. No key is ever 0 standing in for missing.
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

    ticker = v1_blob.get("ticker") or ""
    fy = v1_blob.get("fy")
    period_end = v1_blob.get("period_end")
    if fy is None or not period_end:
        return None

    if abs(net_margin_base) < _MARGIN_BASE_FLOOR:
        return {
            "schema": "valuation_scenario_controls.v1",
            "ticker": ticker,
            "tier": "research_display_only",
            "fy": fy,
            "period_end": period_end,
            "source": "SEC filings",
            "too_thin_base": True,
            "inputs": {
                "net_income": ni,
                "revenue": revenue,
                "shares": shares,
                "net_margin_base": net_margin_base,
            },
            "margin_base_floor": _MARGIN_BASE_FLOOR,
        }

    scenarios = v1_blob.get("scenarios") or []
    by_key = {s.get("key"): s for s in scenarios if isinstance(s, dict)}
    base_sc = by_key.get("base")
    if not base_sc:
        return None
    base_ps = base_sc.get("per_share")
    if not base_sc.get("computable") or base_ps is None or base_ps <= 0:
        return None

    defaults = _control_defaults()
    g = defaults["sales_growth_pct"]
    m_pp = defaults["margin_delta_pp"]
    mult = defaults["earnings_multiple"]
    default_ps = per_share_at(ni, revenue, shares, g, m_pp, mult)
    if default_ps is None:
        return None
    # Section 2.6 makes this an equality, not a coincidence: the sandbox's first
    # paint IS V1's Base card, so the two figures can never disagree on screen.
    # The rules can disagree in principle -- round2 here is half-up, V1's
    # round() is half-to-even, so an exact half-cent splits them -- and when
    # they do, the panel is not shown at all rather than contradicting the
    # authority directly above it. The null shape is the same one every other
    # unusable-V1 branch returns.
    if default_ps != base_ps:
        return None

    presets = {}
    for key, g_s, m_s, mult_s in SCENARIOS:
        presets[key] = {
            "sales_growth_pct": g_s,
            "margin_delta_pp": m_s,
            "earnings_multiple": mult_s,
        }

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
            "sales_growth_pct": g,
            "margin_delta_pp": m_pp,
            "earnings_multiple": mult,
            "per_share": default_ps,
        },
    }
