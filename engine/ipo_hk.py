"""Hong Kong IPO backdrop — DISPLAY-ONLY, NEVER-SCORED (Phase 3).

The US-vs-HK story (research/IPO_RADAR.md): HK is structurally MORE retail-tradeable
than the US — a mandatory public-offer tranche with a clawback, a published
over-subscription multiple, and a grey market (暗盘) that trades the night before
listing. The cruel irony is that the keyless data for those PRIMARY-market signals is
currently broken/blocked (akshare's HK IPO endpoint returns A-share data; the grey
market is broker-proprietary). So we cannot show the HK deal-level demand.

What we CAN show, keylessly, is the LIQUIDITY BACKDROP that drives HK's hot windows:
  southbound Stock Connect flow   mainland capital into HK (the 2025 boom's fuel)
  HIBOR (1-month)                 the cost of margin-financing IPO subscriptions
  HKD peg state                   strong-side (inflow) vs weak-side (outflow) pressure
  HK global risk state            risk-on/off receptiveness (engine/hk regime)

This is the backdrop, NOT a deal signal, and it is never scored. Reuses the existing
HK collectors; degrades gracefully (available=False) when the HK build hasn't run.
"""
from __future__ import annotations

import json
import math
from datetime import date
from numbers import Number

import pandas as pd

from lib import config, store

SCORED = False


def _series(group: str, name: str, col: str) -> pd.Series | None:
    try:
        df = store.read(group, name)
        if not isinstance(df, pd.DataFrame) or df.empty or col not in df:
            return None
        values = df[col]
        return values.copy() if isinstance(values, pd.Series) else None
    except Exception:  # noqa: BLE001
        return None


def _date_label(value) -> str | None:
    """Describe a stored date, without inventing an exchange calendar or age limit."""
    if isinstance(value, Number):
        return None
    if isinstance(value, str):
        value = value.strip()
        try:
            # Relative tokens ("now"/"today") and incomplete dates must not become
            # apparently observed dates. Provider indexes are already timestamps.
            if len(value) < 10 or date.fromisoformat(value[:10]).isoformat() != value[:10]:
                return None
            if len(value) > 10 and value[10] not in ("T", " "):
                return None
        except ValueError:
            return None
    try:
        stamp = pd.Timestamp(value)
        return None if pd.isna(stamp) else stamp.date().isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def _observations(series: pd.Series | None, required: int) -> tuple[pd.Series | None, dict]:
    """Keep the original nonmissing-row window; never replace a malformed operand."""
    evidence = {
        "status": "missing", "observations": 0, "required": required,
        "observation_dates": [], "source_date": None, "trailing_missing": 0,
        "dated_observations": 0, "dates_in_order": False,
    }
    if series is None or series.empty:
        return None, evidence
    evidence["source_date"] = _date_label(series.index[-1])
    positions = [i for i, present in enumerate(series.notna()) if present]
    evidence["trailing_missing"] = len(series) - 1 - positions[-1] if positions else len(series)
    selected = series.iloc[positions[-required:]]
    dates = [_date_label(value) for value in selected.index]
    evidence.update({
        "observations": len(selected), "observation_dates": dates,
        "dated_observations": sum(value is not None for value in dates),
        "dates_in_order": bool(dates) and all(value is not None for value in dates)
                          and all(left < right for left, right in zip(dates, dates[1:])),
    })
    if len(selected) < required:
        evidence["status"] = "insufficient_history" if len(selected) else "missing"
        return None, evidence
    values = []
    for value in selected:
        # bool and complex are not provider readings, even if float() could coerce them.
        if (not pd.api.types.is_scalar(value) or isinstance(value, (bool, complex))
                or pd.api.types.is_bool(value) or pd.api.types.is_complex(value)):
            evidence["status"] = "invalid_value"
            return None, evidence
        try:
            numeric = float(value)
        except (TypeError, ValueError, OverflowError):
            evidence["status"] = "invalid_value"
            return None, evidence
        if not math.isfinite(numeric):
            evidence["status"] = "invalid_value"
            return None, evidence
        values.append(numeric)
    evidence["status"] = "available"
    return pd.Series(values, index=selected.index, dtype=float), evidence


def _hk_regime() -> dict:
    p = config.data_dir() / "hk_regime" / "latest.json"
    if not p.exists():
        return {}
    try:
        value = json.loads(p.read_text())
        return value if isinstance(value, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _regime_evidence(value, date) -> dict:
    available = isinstance(value, str) and bool(value.strip())
    return {
        "status": "available" if available else "missing" if value is None or value == "" else "invalid_value",
        "snapshot_date": _date_label(date),
    }


def hk_backdrop() -> dict:
    legs: list[dict] = []
    coverage: dict[str, dict] = {}

    def add(key, label, value, state, note):
        legs.append({"key": key, "label": label, "value": value, "state": state, "note": note})

    # 1) southbound Stock Connect — mainland $ into HK (the boom's fuel)
    sb, coverage["southbound"] = _observations(_series("china_connect", "southbound", "net"), 20)
    if sb is not None:
        cum20 = float(sb.sum())
        if math.isfinite(cum20):
            state = "constructive" if cum20 > 0 else "cautious" if cum20 < 0 else "neutral"
            add("southbound", "Southbound flow (20d net)", round(cum20),
                state, "mainland capital into HK = primary-market fuel")
        else:
            coverage["southbound"]["status"] = "invalid_value"

    # 2) HIBOR 1m — cost of margin-financing IPO subscriptions (low = froth-enabling)
    hb, coverage["hibor"] = _observations(_series("hkma", "interbank_liquidity", "hibor_1m"), 1)
    if hb is not None:
        v = float(hb.iloc[-1])
        state = "constructive" if v < 2.5 else "neutral" if v < 4.0 else "cautious"
        add("hibor", "Subscription funding (1M HIBOR)", round(v, 2),
            state, "cheap HK$ funding = leveraged retail subscription")

    # 3) HKD peg — strong-side (inflow) tailwind vs weak-side (outflow) headwind
    reg = _hk_regime()
    peg = reg.get("peg_state")
    coverage["peg"] = _regime_evidence(peg, reg.get("date"))
    if coverage["peg"]["status"] == "available":
        state = ("constructive" if "strong" in peg else
                 "cautious" if "weak" in peg else "neutral")
        add("peg", "HKD peg pressure", peg, state, "inflow side supports issuance")

    # 4) HK global risk receptiveness
    risk = reg.get("risk_state")
    coverage["risk"] = _regime_evidence(risk, reg.get("date"))
    if coverage["risk"]["status"] == "available":
        state = ("constructive" if "on" in risk.lower() else
                 "cautious" if "off" in risk.lower() else "neutral")
        add("risk", "HK risk appetite", risk, state, "risk-on tape welcomes new issues")

    cons = sum(1 for l in legs if l["state"] == "constructive")
    caut = sum(1 for l in legs if l["state"] == "cautious")
    n = len(legs)
    if n == 0:
        verdict = "unavailable"
    elif cons >= max(2, n * 0.5) and cons > caut:
        verdict = "receptive"
    elif caut >= max(2, n * 0.5) and caut > cons:
        verdict = "poor"
    else:
        verdict = "mixed"

    # coverage disclosure — the full leg set is southbound/hibor/peg/risk (4);
    # missing_legs names which expected keys did not fire this run.
    expected = ["southbound", "hibor", "peg", "risk"]
    fired = {l["key"] for l in legs}
    missing_legs = [k for k in expected if k not in fired]
    n_expected = len(expected)
    low_confidence = n < 3

    return {
        "available": n > 0,
        "verdict": verdict, "constructive": cons, "cautious": caut, "n_legs": n,
        "n_expected": n_expected, "low_confidence": low_confidence,
        "missing_legs": missing_legs,
        "legs": legs, "as_of": _date_label(reg.get("date")),
        "coverage": coverage,
        "note": ("Liquidity backdrop only — HK is structurally more retail-tradeable "
                 "(public-offer tranche + clawback, published subscription multiple, "
                 "grey market) but those keyless primary-market feeds are currently "
                 "broken/blocked, so this is the issuance environment, not a deal signal. "
                 "Never scored."),
    }
