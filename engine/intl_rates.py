"""Rates / curve / carry desk for the International dashboard.

Takes the rates story the comparison grid showed as two bare numbers (10y, curve)
and turns it into a proper desk: per-country curve shape (10y-3m), real yield
(10y-CPI), the 3-month direction of the long end, and the CARRY each market's 10y
offers over the US 10y anchor (the single biggest pull on global fixed-income
flows). Plus a 10y-yield history sparkline, an ECB balance-sheet liquidity-impulse
context read, and a pass-through of the existing Eurozone BTP-Bund periphery panel.

DISPLAY-ONLY / descriptive. Macro series are monthly OECD/ECB on FRED and several
lag or are discontinued (JP CPI ends 2021, EZ unemployment 2023) — every leg
degrades independently and stale values are dated, not hidden.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from engine import intl_compare, intl_inputs
from engine.ird_velocity import velocity_fields_bp as _ird_velocity
from lib import config, store

log = logging.getLogger(__name__)


def _rcfg() -> dict:
    return config.load()["intl"]["engine"].get("rates", {}) or {}


_series = intl_inputs.read_intl_macro_col   # shared single-column intl_macro reader


# US anchor: the intl_macro seed doesn't always carry us_10y/us_2y, but the daily
# US Treasury series (DGS10/DGS2) are always present in the `fred` group for the US
# dashboard — fall back to those so carry is never silently None.
def _us_series(intl_col: str, fred_id: str) -> pd.Series | None:
    s = _series(intl_col)
    if s is not None and not s.empty:
        return s
    df = store.read("fred", fred_id)
    return df.iloc[:, 0].dropna() if (df is not None and not df.empty) else None


def _spark(s: pd.Series | None, n: int = 48, years: int = 6) -> list[float]:
    if s is None:
        return []
    s = s.dropna()
    if s.empty:
        return []
    s = s[s.index >= (s.index[-1] - pd.DateOffset(years=years))]
    if len(s) < 6:
        return []
    step = max(1, len(s) // n)
    return [round(float(v), 3) for v in s.iloc[::step]]


def _curve_shape(slope: float | None) -> tuple[str, str, str]:
    if slope is None:
        return "na", "—", "—"
    if slope < 0:
        return "inverted", "inverted", "倒挂"
    if slope < 0.5:
        return "flat", "flat", "平坦"
    if slope < 2.0:
        return "normal", "normal", "正常"
    return "steep", "steep", "陡峭"


def us_anchor() -> dict:
    """Latest US 2y / 10y / curve — the global rate yard-stick every carry is vs."""
    us10 = _us_series("us_10y", "DGS10")
    us2 = _us_series("us_2y", "DGS2")
    v10 = float(us10.iloc[-1]) if us10 is not None and not us10.empty else None
    v2 = float(us2.iloc[-1]) if us2 is not None and not us2.empty else None
    asof = None
    if us10 is not None and not us10.empty:
        asof = str(us10.index[-1].date())
    return {"y10": round(v10, 2) if v10 is not None else None,
            "y2": round(v2, 2) if v2 is not None else None,
            "curve": round(v10 - v2, 2) if (v10 is not None and v2 is not None) else None,
            "asof": asof, "spark": _spark(us10)}


def rates_desk(records: list[dict]) -> dict:
    """Per-country rates row + the US anchor + ECB liquidity impulse + periphery."""
    anchor = us_anchor()
    us10 = anchor.get("y10")
    rows: list[dict] = []
    for r in records:
        cc = r["cc"]
        m = r.get("macro") or {}
        af = r.get("macro_asof") or {}
        y10 = m.get("yield_10y")
        slope = m.get("curve")
        shape_key, shape_en, shape_zh = _curve_shape(slope)
        carry = round(y10 - us10, 2) if (y10 is not None and us10 is not None) else None
        # IRD-R13 velocity fields on the 10y series (fail-open)
        y10_series = _series(f"{cc}_yield_10y")
        vel = _ird_velocity(y10_series) if y10_series is not None else {"vel_5d_bp": None, "vel_20d_bp": None, "vel_20d_z": None, "window_days": None}
        rows.append({
            "cc": cc, "name": r["name"], "name_zh": r.get("name_zh", r["name"]),
            "flag": r["flag"], "region": r.get("region"),
            "y10": y10, "short": m.get("short_3m"), "policy": m.get("policy_rate"),
            "curve": slope, "shape": shape_key, "shape_en": shape_en, "shape_zh": shape_zh,
            "real_yield": m.get("real_yield"), "cpi": m.get("cpi_yoy"),
            "y10_chg3m": m.get("yield_10y_chg3m"), "carry_vs_us": carry,
            "stance": r.get("liquidity"),
            "y10_asof": af.get("yield_10y"), "cpi_asof": af.get("cpi_yoy"),
            "spark": _spark(_series(f"{cc}_yield_10y")),
            # IRD-R13 velocity (basis-point changes; window_days disclosed)
            "vel_5d_bp": vel["vel_5d_bp"],
            "vel_20d_bp": vel["vel_20d_bp"],
            "vel_20d_z": vel["vel_20d_z"],
            "vel_window_days": vel["window_days"],
        })
    # rank by carry (highest real pull first) where present
    have_carry = [r for r in rows if r["carry_vs_us"] is not None]
    have_carry.sort(key=lambda r: r["carry_vs_us"], reverse=True)
    return {"anchor": anchor, "rows": rows,
            "carry_ranked": [r["cc"] for r in have_carry],
            "liquidity": ecb_liquidity_impulse(),
            "periphery": intl_compare.periphery_panel()}


def ecb_liquidity_impulse() -> dict | None:
    """ECB balance-sheet impulse — the euro-area liquidity tide. 13- & 52-week %
    change of ECB total assets. Honest scope: ECB only (the one major CB with a
    clean keyless weekly series here); a falling balance sheet = QT drain."""
    s = _series("ez_cb_assets")
    if s is None or len(s) < 60:
        return None
    s = s[~s.index.duplicated(keep="last")].sort_index()
    w = s.resample("W").last().ffill()
    if len(w) < 54:
        return None
    last = float(w.iloc[-1])
    chg13 = float(w.iloc[-1] / w.iloc[-14] - 1.0) * 100 if len(w) > 14 else None
    chg52 = float(w.iloc[-1] / w.iloc[-53] - 1.0) * 100 if len(w) > 53 else None
    drain = bool(chg52 is not None and chg52 < 0)
    return {"asof": str(w.index[-1].date()),
            "level_eur_tn": round(last / 1e6, 2),   # source is EUR millions -> trillions
            "chg_13w": round(chg13, 1) if chg13 is not None else None,
            "chg_52w": round(chg52, 1) if chg52 is not None else None,
            "draining": drain,
            "read_en": ("QT — balance sheet still draining" if drain else "Balance sheet stabilising / expanding"),
            "read_zh": ("缩表 — 资产负债表仍在收缩" if drain else "资产负债表企稳／扩张"),
            "spark": _spark(w, n=52, years=4)}


# Pure nominal-policy comparison. Observation acquisition and instrument admission
# remain with their existing owners; these arguments carry already made decisions.
def _policy_tree(value, ancestors=None, depth=0, count=None):
    import math
    if ancestors is None:
        ancestors, count = set(), [0]
    count[0] += 1
    if depth > 32 or count[0] > 10000:
        raise ValueError
    if value is None or type(value) in (bool, int):
        return
    if type(value) is str:
        if len(value) > 4096:
            raise ValueError
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError
        return
    if type(value) not in (dict, list) or id(value) in ancestors:
        raise ValueError
    ancestors.add(id(value))
    try:
        if type(value) is dict:
            if any(type(key) is not str or len(key) > 4096 for key in value):
                raise ValueError
            children = value.values()
        else:
            children = value
        for child in children:
            _policy_tree(child, ancestors, depth + 1, count)
    finally:
        ancestors.remove(id(value))


def _policy_shape(value, keys):
    if type(value) is not dict or set(value) != set(keys.split()):
        raise ValueError


def _policy_text(value, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError


def _policy_date(value):
    import re
    from datetime import date
    if type(value) is not str or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
        raise ValueError
    date.fromisoformat(value)


def _policy_number(value):
    import math
    if type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)):
        raise ValueError


def _policy_instrument(value):
    _policy_shape(value, 'economy instrument_id instrument_kind')
    for item in value.values():
        _policy_text(item)


def _policy_validate(intent, observations, mapping_receipt):
    import re
    for value in (intent, observations, mapping_receipt):
        _policy_tree(value)
    _policy_shape(intent, 'economy_a economy_b lens definition method_version period vintage_policy identity')
    for key in ('economy_a', 'economy_b'):
        value = intent[key]
        if type(value) is not str or not re.fullmatch(r'[A-Z]{2}', value):
            raise ValueError
    if intent['economy_a'] == intent['economy_b']:
        raise ValueError
    if intent['lens'] != 'nominal_policy_point_gap' or intent['definition'] != 'absolute_gap_change_bp':
        raise ValueError
    _policy_text(intent['method_version'])
    if intent['vintage_policy'] not in ('latest_vintage', 'original_known'):
        raise ValueError
    _policy_shape(intent['identity'], 'principal_partition saved_id saved_revision source_generation')
    for key in ('principal_partition', 'saved_id', 'source_generation'):
        _policy_text(intent['identity'][key], nullable=True)
    revision = intent['identity']['saved_revision']
    if revision is not None and (type(revision) is not int or revision < 1):
        raise ValueError
    period = intent['period']
    if type(period) is not dict:
        raise ValueError
    if period.get('mode') == 'fixed_dates':
        _policy_shape(period, 'mode start end')
        _policy_date(period['start'])
        _policy_date(period['end'])
        if period['end'] < period['start']:
            raise ValueError
    elif period.get('mode') == 'owner_horizon':
        _policy_shape(period, 'mode key')
        _policy_text(period['key'])
    else:
        raise ValueError
    _policy_shape(observations, 'a_start a_end b_start b_end')
    for row in observations.values():
        if row is None:
            continue
        _policy_shape(row, 'economy instrument_id instrument_kind observation_at unit value quality metadata value_permission source_reference qualification_ref')
        _policy_number(row['value'])
        _policy_date(row['observation_at'])
        if row['unit'] not in ('percent', 'bp'):
            raise ValueError
        for key, value in row.items():
            if key != 'value':
                _policy_text(value)
    if mapping_receipt is not None:
        _policy_shape(mapping_receipt, 'status method_version instruments')
        _policy_text(mapping_receipt['status'])
        _policy_text(mapping_receipt['method_version'])
        _policy_shape(mapping_receipt['instruments'], 'a b')
        for entry in mapping_receipt['instruments'].values():
            _policy_instrument(entry)


def _policy_output_number(value):
    import math
    if value.denominator == 1:
        return value.numerator
    out = float(value)
    if not math.isfinite(out) or (out == 0 and value != 0):
        raise OverflowError
    return out


def compare_policy_points(intent, observations, mapping_receipt):
    """Compare four supplied, qualified nominal point settings without I/O.

    Fixed-date endpoints must match exactly. Mapping, freshness and disclosure
    assertions come from the caller's admitted owners, never this arithmetic.
    Inputs have a 32-level, 10,000-node, 4096-character resource boundary; no
    financial magnitude cap is applied. Any incomplete comparison emits no
    numeric answer or observation references. Original-known replay is withheld.
    """
    from copy import deepcopy
    from fractions import Fraction
    import json
    invalid = dict(state='invalid', identity=None,
                   reasons=['invalid_policy_comparison'], missing_refs=[])
    try:
        _policy_validate(intent, observations, mapping_receipt)
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        return invalid
    try:
        json.dumps(intent, allow_nan=False)
    except (ValueError, OverflowError):
        return invalid
    identity = deepcopy(intent)

    def unavailable(reasons, slots=()):
        return dict(state='unavailable', identity=identity,
                    reasons=list(dict.fromkeys(reasons)), missing_refs=list(slots))

    if intent['vintage_policy'] != 'latest_vintage':
        return unavailable(['original_known_unavailable'])
    if intent['period']['mode'] != 'fixed_dates':
        return unavailable(['unsupported_period_mode'])
    if mapping_receipt is None:
        return unavailable(['mapping_not_supplied'])
    if mapping_receipt['status'] != 'qualified':
        return unavailable(['mapping_unqualified'])
    mapping = mapping_receipt['instruments']
    if mapping_receipt['method_version'] != intent['method_version'] or any(
        mapping[side]['economy'] != intent['economy_'+side]
        or mapping[side]['instrument_kind'] != 'nominal_policy_point'
        for side in ('a', 'b')
    ):
        return unavailable(['mapping_incompatible'])
    slots = ('a_start', 'a_end', 'b_start', 'b_end')
    reasons, missing = [], []
    for slot in slots:
        row = observations[slot]
        reason = None
        if row is None:
            reason = 'observation_missing'
        elif row['metadata'] != 'allowed' or row['value_permission'] != 'allowed':
            reason = 'observation_not_disclosed'
        elif row['quality'] != 'qualified':
            reason = 'observation_unqualified'
        elif any(row[key] != mapping[slot[0]][key] for key in ('economy','instrument_id','instrument_kind')):
            reason = 'observation_identity_mismatch'
        elif row['observation_at'] != intent['period'][slot.split('_')[1]]:
            reason = 'observation_cutoff_mismatch'
        if reason:
            reasons.append(reason)
            missing.append(slot)
    if reasons:
        return unavailable(reasons, missing)
    values = [Fraction(observations[slot]['value']) * (100 if observations[slot]['unit'] == 'percent' else 1)
              for slot in slots]
    if intent['period']['start'] == intent['period']['end']:
        conflicts = [slot for side, offset in (('a', 0), ('b', 2))
                     if values[offset] != values[offset + 1]
                     for slot in (side + '_start', side + '_end')]
        if conflicts:
            return unavailable(['observation_conflict'], conflicts)
    start, end = values[0] - values[2], values[1] - values[3]
    absolute_change = abs(end) - abs(start)
    try:
        result = dict(state='qualified', identity=identity,
                      signed_start_bp=_policy_output_number(start), signed_end_bp=_policy_output_number(end),
                      signed_change_bp=_policy_output_number(end - start),
                      absolute_change_bp=_policy_output_number(absolute_change),
                      direction='narrowed' if absolute_change < 0 else 'widened' if absolute_change > 0 else 'unchanged_at_endpoints',
                      crosses_zero=(start < 0 < end or end < 0 < start),
                      evidence_refs=[dict(slot=slot, **{key: observations[slot][key]
                          for key in ('source_reference','qualification_ref','observation_at')}) for slot in slots])
        json.dumps(result, allow_nan=False)
        return result
    except (ValueError, OverflowError):
        return unavailable(['arithmetic_unrepresentable'])
