"""One display-only asset read for commodity cards, detail and existing JSON.

Consumes existing model outputs. Never calculates a new exposure, signal, rank,
trade permission or market-data series, and never writes a second state store.
"""
from __future__ import annotations
from datetime import date, datetime
import math
from numbers import Real

CORE = frozenset({"gold", "silver", "copper", "oil"})
_ACTIONS = frozenset({"STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"})
_TITLES = {
    "incomplete": ("Evidence incomplete", "证据不完整", "mut"),
    "lagging": ("Older asset snapshot", "品种快照较旧", "amb"),
    "defensive": ("Defensive model posture", "模型偏防御", "dn"),
    "mixed": ("Signals disagree", "信号存在分歧", "amb"),
    "caution": ("Tactical caution", "短期需谨慎", "amb"),
    "positive": ("Positive model posture", "模型偏正面", "up"),
    "neutral": ("No aligned tactical read", "短期尚未共振", "mut"),
}
_REASONS = {
    "missing_evidence": ("Required evidence or identity is unavailable.", "必要证据或品种身份缺失。"),
    "snapshot_mismatch": ("Price and signal dates disagree, or exceed the comparison date.", "价格与信号日期不一致，或晚于比较日期。"),
    "older_snapshot": ("This asset predates the page comparison date; it is not a fresh signal.", "此品种早于页面比较日期，并非最新信号。"),
    "policy_disagreement": ("The model label and exposure target disagree; neither is entry clearance.", "模型标签与敞口目标存在分歧，均不代表入场许可。"),
    "zero_exposure": ("The existing policy targets zero exposure to this asset.", "现有策略对此品种的敞口目标为零。"),
    "model_defensive": ("The existing model label is defensive.", "现有模型标签偏防御。"),
    "tactical_disagreement": ("Positive model context coexists with weak daily or three-session evidence.", "正面模型背景与较弱的日线或三交易日证据并存。"),
    "tactical_weakness": ("Daily or three-session evidence is weak.", "日线或三交易日证据偏弱。"),
    "elevated_risk": ("This asset's risk model is elevated, even if its long trend is up.", "即使长期趋势向上，此品种风险模型仍处于高位。"),
    "timing_unconfirmed": ("The existing timeframe assessment is not an aligned uptrend.", "现有周期判断并非一致上升趋势。"),
    "aligned_context": ("The displayed inputs agree positively; this does not authorize a trade.", "所示输入一致偏正面，但不构成交易授权。"),
    "mixed_context": ("The inputs do not establish one aligned tactical view.", "输入尚未形成一致的短期判断。"),
}


def _number(value):
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def exposure_percent(value):
    """Preserve the existing fraction; invalid/absent is not a zero allocation."""
    v = _number(value)
    return round(100 * v, 4) if v is not None and 0 <= v <= 1 else None


def _date(value):
    if isinstance(value, datetime):
        return value.date() if str(value) != "NaT" else None
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except (ValueError, OverflowError):
        return None



_CALIBRATION_SCHEMA = "mastermind.commodity_calibration_evidence.v1"
_CALIBRATION_LABELS = {
    "defaults": ("Default parameters", "默认参数"),
    "stored": ("Stored calibration", "已存校准参数"),
    "weak": ("Stored calibration: weak", "已存校准：较弱"),
    "unrated": ("Stored calibration: unrated", "已存校准：未评级"),
    "unavailable": ("Calibration evidence unavailable", "校准证据暂缺"),
}


def _calibration_read(asset, status="unavailable", reliable=None, horizons=()):
    """Canonical copy only; stored metadata never authors user-facing promises."""
    en, zh = _CALIBRATION_LABELS[status]
    bars = sorted({v for v in horizons if type(v) is int and v > 0})
    return {
        "schema": _CALIBRATION_SCHEMA, "asset": asset,
        "status": status, "declared_reliable": reliable,
        "horizons_bars": bars, "label_en": en, "label_zh": zh,
        "disclosure_en": ("Parameter-source evidence, not a win probability. "
                          "Declared historical horizons do not validate a current entry."),
        "disclosure_zh": "仅说明参数来源，并非胜率；历史收益期限不代表当前入场已获验证。",
    }


def calibration_evidence(asset, calibration):
    """Describe the exact object supplied to the existing scorer; do not score."""
    if not isinstance(asset, str) or not asset.strip():
        return _calibration_read(None)
    if not isinstance(calibration, dict):
        return _calibration_read(asset)
    assets = calibration.get("assets", {})
    if not isinstance(assets, dict):
        return _calibration_read(asset)
    asset_config = assets.get(asset, {})
    if not isinstance(asset_config, dict):
        return _calibration_read(asset)
    weights = asset_config.get("weights")
    if weights is None or (isinstance(weights, dict) and not weights):
        return _calibration_read(asset, "defaults")
    if not isinstance(weights, dict) or any(
            not isinstance(k, str) or _number(v) is None for k, v in weights.items()):
        return _calibration_read(asset)
    if not any(v != 0 for v in weights.values()):
        return _calibration_read(asset)
    reliable = asset_config.get("score_reliable")
    reliable = reliable if type(reliable) is bool else None
    status = "stored" if reliable is True else "weak" if reliable is False else "unrated"
    meta = calibration.get("meta")
    horizons = meta.get("horizons", []) if isinstance(meta, dict) else []
    horizons = horizons if isinstance(horizons, (list, tuple)) else []
    return _calibration_read(asset, status, reliable, horizons)


def model_evidence_read(asset, receipt):
    """Qualify the asset-bound receipt and reconstruct labels without trusting copy."""
    if not isinstance(asset, str) or not asset.strip():
        return _calibration_read(None)
    if not isinstance(receipt, dict):
        return _calibration_read(asset)
    schema = receipt.get("schema")
    if not isinstance(schema, str) or schema != _CALIBRATION_SCHEMA:
        return _calibration_read(asset)
    identity = receipt.get("asset")
    status = receipt.get("status")
    if (not isinstance(identity, str) or identity != asset or
            not isinstance(status, str) or status not in _CALIBRATION_LABELS):
        return _calibration_read(asset)
    reliable = receipt.get("declared_reliable")
    expected = {"stored": True, "weak": False}.get(status)
    if reliable is not expected:
        return _calibration_read(asset)
    horizons = receipt.get("horizons_bars", [])
    if not isinstance(horizons, (list, tuple)):
        return _calibration_read(asset)
    if status in ("defaults", "unavailable"):
        horizons = []
    return _calibration_read(asset, status, reliable, horizons)

def build_asset_read(name, row, display, *, signal_asof=None, price_asof=None,
                     reference_asof=None, instrument=None):
    """Reconcile descriptions without overriding any numerical model policy.

    Dates are source observation dates, not live-price update times. Lag is only
    relative to the declared comparison date, never a fabricated live SLA.
    """
    row = row if isinstance(row, dict) else {}
    display = display if isinstance(display, dict) else {}
    valid_name = isinstance(name, str) and bool(name.strip())
    name = name if valid_name else None
    core = valid_name and name in CORE
    identity_mismatch = any(
        key in source and (not isinstance(source[key], str) or source[key] != name)
        for source, key in ((row, "asset"), (display, "name"), (display, "key"))
    )
    conv = display.get("conviction")
    conv = conv if core and isinstance(conv, dict) else {}
    action = conv.get("action")
    action = action if isinstance(action, str) and action in _ACTIONS else None
    exposure = exposure_percent(row.get("alloc_optimal")) if core else None
    risk = row.get("risk_regime")
    risk = risk if isinstance(risk, str) and risk in ("low_risk", "high_risk") else None
    mom = row.get("momentum_state")
    mom = mom if isinstance(mom, str) and mom in ("bull", "bear", "neutral") else None
    trend = row.get("ts_trend")
    trend = trend if isinstance(trend, str) and trend in ("up", "down", "flat") else None
    signal_day, price_day, reference_day = map(_date, (signal_asof, price_asof, reference_asof))
    symbol = instrument if isinstance(instrument, str) and instrument.strip() else None
    verdict = display.get("verdict")
    grade = verdict.get("grade") if isinstance(verdict, dict) else None
    grade = grade if isinstance(grade, str) and grade in ("TREND-FOLLOW", "BUY-THE-DIP", "WAIT", "CAUTION", "AVOID", "DON'T CHASE") else None
    by_tf = {}
    duplicates = False
    timeframe_source = display.get("mtf_rows")
    malformed_frames = not isinstance(timeframe_source, (list, tuple))
    for item in (() if malformed_frames else timeframe_source):
        if not isinstance(item, dict):
            malformed_frames = True
            continue
        key = item.get("key")
        if not isinstance(key, str):
            malformed_frames = True
            continue
        if key in ("D", "3D", "W"):
            duplicates |= key in by_tf
            by_tf[key] = item
    frames = []
    for key, en, zh in (("D", "Daily", "日线"), ("3D", "3-session", "三交易日"), ("W", "Weekly", "周线")):
        item = by_tf.get(key, {})
        value = item.get("trend")
        value = value if isinstance(value, str) and value in ("up", "down", "flat") else None
        frames.append({"key":key, "label_en":en, "label_zh":zh, "trend":value})
    missing = (not valid_name or identity_mismatch or malformed_frames or
               grade is None or not symbol or not all((signal_day, price_day, reference_day)) or
               risk is None or mom is None or trend is None or duplicates or
               any(frame["trend"] is None for frame in frames) or
               (core and (exposure is None or action is None)))
    mismatch = bool(signal_day and price_day and reference_day and
                    (signal_day != price_day or signal_day > reference_day))
    lag = (reference_day - signal_day).days if signal_day and reference_day and not mismatch else None
    negative_tape = mom == "bear" or any(f["trend"] == "down" for f in frames[:2])
    buy = action in ("BUY", "STRONG BUY")
    sell = action in ("SELL", "STRONG SELL")
    policy_conflict = (buy and exposure == 0) or (sell and exposure is not None and exposure > 0)
    codes = []
    if exposure == 0:
        codes.append("zero_exposure")
    if sell:
        codes.append("model_defensive")
    if risk == "high_risk":
        codes.append("elevated_risk")
    if negative_tape:
        codes.append("tactical_disagreement" if buy else "tactical_weakness")
    if grade and grade != "TREND-FOLLOW":
        codes.append("timing_unconfirmed")
    if policy_conflict:
        codes.insert(0, "policy_disagreement")
    if missing or mismatch:
        state, quality = "incomplete", "incomplete"
        codes.insert(0, "snapshot_mismatch" if mismatch else "missing_evidence")
    elif lag and lag > 0:
        state, quality = "lagging", "lagging"
        codes.insert(0, "older_snapshot")
    else:
        quality = "dated"
        if policy_conflict or (buy and (negative_tape or grade != "TREND-FOLLOW")):
            state = "mixed"
        elif sell or exposure == 0:
            state = "defensive"
        elif negative_tape or risk == "high_risk" or grade != "TREND-FOLLOW":
            state = "caution"
        elif mom == "bull" and all(f["trend"] == "up" for f in frames) and (buy or not core):
            state = "positive"
        else:
            state = "neutral"
    if not codes:
        codes = ["aligned_context" if state == "positive" else "mixed_context"]
    en, zh, tone = _TITLES[state]
    return {
        "schema":"mastermind.commodity_asset_read.v1", "asset":name if valid_name else None,
        "instrument":symbol, "state":state, "quality":quality,
        "title_en":en, "title_zh":zh, "tone":tone,
        "reason_codes":codes,
        "reasons":[{"code":c,"en":_REASONS[c][0],"zh":_REASONS[c][1]} for c in codes],
        "signal_asof":signal_day.isoformat() if signal_day else None,
        "price_asof":price_day.isoformat() if price_day else None,
        "reference_asof":reference_day.isoformat() if reference_day else None,
        "lag_calendar_days":lag, "allocation_applicable":core,
        "exposure_pct":exposure, "model_action":action,
        "model_score":_number(conv.get("score")),
        "model_evidence":model_evidence_read(name if valid_name else None, conv.get("calibration_evidence")),
        "risk":risk, "momentum":mom, "structural_trend":trend,
        "raw_driver_score":_number(row.get("driver_score")),
        "timeframes":frames, "timing_grade":grade, "authority":"display_only", "new_entry_permission":None,
    }


def attach_asset_reads(detail, member_results, assets, cfg):
    """Add one shared projection to existing detail records and return its index.

    No new computation of technical indicators; use the already-rendered rows.
    A later caller/consumer reads these same dictionaries, not a second model.
    """
    views = {a.get("key"):a for a in assets if isinstance(a, dict)}
    dates = []
    for frame in member_results.values():
        if frame is not None and not frame.empty:
            day = _date(frame.index[-1])
            if day:
                dates.append(day)
    reference = max(dates) if dates else None
    reads = {}
    for item in detail:
        name = item["name"]
        frame = member_results.get(name)
        signal_asof = price_asof = None
        row = {}
        if frame is not None and not frame.empty and "close" in frame:
            row = frame.iloc[-1].to_dict()
            if frame.index.is_monotonic_increasing and frame.index.is_unique:
                signal_asof = frame.index[-1]
                # Only actual finite numerical observations may advance this clock.
                closes = frame["close"].map(_number).dropna()
                if len(closes):
                    price_asof = closes.index[-1]
        identity = cfg.get("assets", {}).get(name) or cfg.get("complex_members", {}).get(name)
        symbol = identity[0] if isinstance(identity, (list,tuple)) and identity else None
        display = dict(item)
        if name in views:
            display["conviction"] = views[name].get("conviction")
        read = build_asset_read(name, row, display, signal_asof=signal_asof,
                                price_asof=price_asof, reference_asof=reference, instrument=symbol)
        item["asset_read"] = read
        reads[name] = read
    return reads
