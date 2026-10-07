"""Per-country feature frames for the International comparative dashboard.

Reads Plane A (group `intl`: index + FX closes, yfinance) and Plane B (group
`intl_macro`: FRED OECD CSV + ECB) and builds ONE uniform business-day frame per
country so every economy is scored on the SAME axes. Cross-asset cyclical inputs
(copper/gold, oil) come from the shared `yahoo` group already collected for the US
dashboard. Missing series yield NaN columns — the engine renormalizes over what
exists (degrade-don't-crash), which is how Taiwan (thin on keyless macro) and any
unresolved FRED id are handled.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from lib import config, store

log = logging.getLogger(__name__)

# macro metrics fetched per country (collectors/intl_macro stores "<CC>_<metric>")
_METRICS = ["yield_10y", "short_3m", "cpi_yoy", "unemployment", "gdp", "m2"]
# shared euro-area / periphery / anchor cols (collectors/intl_macro extra_series)
_EXTRAS = ["ez_depo_rate", "de_10y", "it_10y", "es_10y", "fr_10y", "us_10y", "us_2y"]


def countries() -> dict:
    return config.load()["intl"]["countries"]


def _intl_closes() -> pd.DataFrame:
    """Index + FX closes (group `intl`)."""
    cfg = config.load()["intl"]["countries"]
    tickers: list[str] = []
    for c in cfg.values():
        tickers += list(c.get("indices") or {c["index"]: None})
        tickers.append(c["fx"])
    cols = {}
    for t in dict.fromkeys(tickers):
        df = store.read("intl", t)
        if df is not None and "close" in df.columns:
            cols[t] = df["close"]
    return pd.DataFrame(cols).sort_index()


def read_intl_macro_col(col: str) -> pd.Series | None:
    """One `intl_macro` stored column as a clean Series (None if absent/empty).
    Shared single-column reader (engine.intl_rates + engine.intl_compare)."""
    df = store.read("intl_macro", col)
    return df.iloc[:, 0].dropna() if (df is not None and not df.empty) else None


def _macro_frame() -> pd.DataFrame:
    parts = []
    cc_metrics = [f"{cc}_{m}" for cc in countries() for m in _METRICS]
    for s in cc_metrics + _EXTRAS:
        df = store.read("intl_macro", s)
        if df is not None and not df.empty:
            parts.append(df)
    if not parts:
        return pd.DataFrame()
    out = pd.concat(parts, axis=1)
    return out[~out.index.duplicated(keep="last")].sort_index()


def _shared_ratio(num: str, den: str) -> pd.Series | None:
    a, b = store.read("yahoo", num), store.read("yahoo", den)
    if a is None or b is None or "close" not in a.columns or "close" not in b.columns:
        return None
    return (a["close"] / b["close"]).dropna()


def _shared_close(t: str) -> pd.Series | None:
    df = store.read("yahoo", t)
    return df["close"].dropna() if (df is not None and "close" in df.columns) else None


def country_frame(cc: str, closes: pd.DataFrame | None = None,
                  macro: pd.DataFrame | None = None) -> pd.DataFrame:
    """Uniform per-country daily feature frame (business-day indexed)."""
    c = countries()[cc]
    if closes is None:
        closes = _intl_closes()
    if macro is None:
        macro = _macro_frame()

    idx_col = c["index"]
    if idx_col not in closes or closes[idx_col].dropna().empty:
        return pd.DataFrame()
    px = closes[idx_col].dropna()
    end = px.index.max()
    bidx = pd.bdate_range(px.index.min(), end)
    f = pd.DataFrame(index=bidx)

    def put(name: str, s: pd.Series | None, ffill_limit: int | None = 5) -> None:
        if s is None or s.dropna().empty:
            f[name] = np.nan
            return
        s = s[~s.index.duplicated(keep="last")].sort_index()
        s = s.reindex(bidx.union(s.index))
        s = s.ffill(limit=ffill_limit) if ffill_limit else s
        f[name] = s.reindex(bidx)

    # --- market (always present) ----------------------------------------------
    put("index", px, ffill_limit=3)
    ret = px.pct_change(fill_method=None)
    put("realvol", ret.rolling(21).std() * np.sqrt(252) * 100, ffill_limit=3)  # annualised %
    dd = px / px.rolling(c_high_window(), min_periods=60).max() - 1.0
    put("drawdown", dd * 100, ffill_limit=3)                                   # % from 1y high

    fx = closes.get(c["fx"])
    put("fx", fx, ffill_limit=3)
    if fx is not None and not fx.dropna().empty:
        # currency STRESS direction: rising USD/XXX (invert) OR falling XXX/USD = weaker
        sgn = -1.0 if c.get("fx_invert") else 1.0
        put("fx_strength_3m", sgn * fx.pct_change(63) * 100, ffill_limit=3)

    # --- macro (per country; degrade per series) ------------------------------
    def mcol(metric: str) -> pd.Series | None:
        col = f"{cc}_{metric}"
        return macro[col] if (not macro.empty and col in macro.columns) else None

    # rates ffill generously (monthly source -> daily frame) so the curve / policy
    # stance reach the latest day; the direction diffs still span real changes.
    put("yield_10y", mcol("yield_10y"), ffill_limit=130)
    put("short_3m", mcol("short_3m"), ffill_limit=130)
    # CPI: some sources are an INDEX (2015=100 / 2010=100), others already YoY %.
    # Detect by the RECENT level — an index sits ~100+, a YoY rate ~0-15 — using a
    # trailing window so a long index history (e.g. India's 1957-base series) can't
    # drag the median below the threshold and get mis-read as a rate. For an index,
    # step YoY by the series' own cadence: 4 for quarterly (Australia), else 12
    # (monthly). ffill is short, so a STALE CPI (FRED's OECD MEI series are
    # discontinued for several economies) goes NaN at recent dates and is dropped
    # from scoring — only fresh CPI drives the axis.
    cpi_raw = mcol("cpi_yoy")
    if cpi_raw is not None and not cpi_raw.dropna().empty:
        cs = cpi_raw.dropna()
        is_index = float(cs.tail(24).median()) > 40
        cpi_yoy = (cs.pct_change(4 if _is_quarterly(cs) else 12) * 100) if is_index else cs
        put("cpi_yoy", cpi_yoy, ffill_limit=70)
    else:
        f["cpi_yoy"] = np.nan
    put("unemployment", mcol("unemployment"), ffill_limit=90)
    gdp = mcol("gdp")
    if gdp is not None and not gdp.dropna().empty:
        g = gdp.dropna()
        per = 4 if _is_quarterly(g) else 12                # quarterly vs monthly level
        put("gdp_yoy", g.pct_change(per) * 100, ffill_limit=160)
    else:
        f["gdp_yoy"] = np.nan
    m2 = mcol("m2")
    put("m2_yoy", (m2.dropna().pct_change(12) * 100) if (m2 is not None and not m2.dropna().empty) else None,
        ffill_limit=90)

    # EZ policy comes from the ECB deposit rate (no 3m interbank short leg)
    if cc == "EZ" and not macro.empty and "ez_depo_rate" in macro.columns:
        put("policy_rate", macro["ez_depo_rate"], ffill_limit=130)
    else:
        f["policy_rate"] = f["short_3m"]

    # --- derived rate reads ---------------------------------------------------
    f["curve"] = f["yield_10y"] - f["short_3m"]            # term slope
    f["real_yield"] = f["yield_10y"] - f["cpi_yoy"]        # ex-ante real 10y

    # --- shared global cyclical / inflation pulse -----------------------------
    put("copper_gold", _shared_ratio("HG=F", "GC=F"))
    put("oil", _shared_close("CL=F"))
    return f


def _is_quarterly(s: pd.Series) -> bool:
    d = s.index.to_series().diff().dt.days.dropna()
    return bool(len(d) and d.median() > 45)


def c_high_window() -> int:
    return int(config.load()["intl"]["engine"]["equity_risk"]["high_window_d"])


def latest_macro_snapshot(cc: str, f: pd.DataFrame) -> dict:
    """Latest-day comparison metrics for one country (levels + short-horizon dir)."""
    def lvl(col: str, nd: int = 2):
        if col not in f or f[col].dropna().empty:
            return None
        return round(float(f[col].dropna().iloc[-1]), nd)

    def chg(col: str, n: int = 63, nd: int = 2):
        if col not in f or f[col].dropna().empty:
            return None
        s = f[col].dropna()
        if len(s) <= n:
            return None
        return round(float(s.iloc[-1] - s.iloc[-1 - n]), nd)

    def real_yield():
        # real 10y = 10y − CPI, but ONLY when CPI is recent. Several keyless OECD
        # CPI series are discontinued (JP ends 2021, KR 2023), so the real_yield
        # column's last-valid value can be a years-old composite — showing it as a
        # current "real yield" would be a mislabel. Gate on the CPI leg being fresh.
        if "real_yield" not in f or "cpi_yoy" not in f:
            return None
        cpi = f["cpi_yoy"].dropna()
        ry = f["real_yield"].dropna()
        if cpi.empty or ry.empty:
            return None
        if (f.index[-1] - cpi.index[-1]).days > 490:      # CPI print >~16mo stale
            return None
        return round(float(ry.iloc[-1]), 2)

    return {
        "yield_10y": lvl("yield_10y"), "yield_10y_chg3m": chg("yield_10y"),
        "short_3m": lvl("short_3m"), "policy_rate": lvl("policy_rate"),
        "curve": lvl("curve"), "real_yield": real_yield(),
        "cpi_yoy": lvl("cpi_yoy"), "cpi_chg3m": chg("cpi_yoy"),
        "gdp_yoy": lvl("gdp_yoy"), "unemployment": lvl("unemployment"),
        "unemployment_chg6m": chg("unemployment", 126),
        "m2_yoy": lvl("m2_yoy"),
        "fx": lvl("fx", 4), "fx_strength_3m": lvl("fx_strength_3m"),
        "realvol": lvl("realvol", 1), "drawdown": lvl("drawdown", 1),
    }


def macro_freshness(cc: str, macro: pd.DataFrame | None = None) -> dict:
    """Last real-observation month per lagged macro metric — for honest dating in
    the comparison grid. FRED's OECD CPI series are discontinued for several
    economies, so a stale month is SHOWN (greyed) rather than silently hidden."""
    if macro is None:
        macro = _macro_frame()
    out = {}
    for metric in ("cpi_yoy", "gdp", "unemployment", "yield_10y"):
        col = f"{cc}_{metric}"
        s = macro[col].dropna() if (not macro.empty and col in macro.columns) else None
        out[metric] = str(s.index[-1].date())[:7] if (s is not None and not s.empty) else None
    return out


def _snapshot_close_scalar(value) -> tuple[int | float | None, str | None]:
    """Preserve numeric identity without DataFrame row coercion."""
    import math

    if value is None or value is pd.NA:
        return None, None
    if isinstance(value, (bool, np.bool_)):
        raise ValueError("snapshot close cannot be boolean")
    if isinstance(value, (int, np.integer)):
        plain = int(value)
        # Bounded decimal chunks avoid Python's process-wide integer-string
        # digit limit without changing that global setting or capping inputs.
        magnitude, chunks = abs(plain), []
        while magnitude:
            magnitude, remainder = divmod(magnitude, 1_000_000_000)
            chunks.append(remainder)
        decimal = (str(chunks[-1]) + "".join(f"{part:09d}" for part in reversed(chunks[:-1]))
                   if chunks else "0")
        return plain, "i:" + ("-" if plain < 0 else "") + decimal
    if isinstance(value, (float, np.floating)):
        plain = float(value)
        if math.isnan(plain):
            return None, None
        if not math.isfinite(plain):
            raise ValueError("snapshot close must be finite")
        # Extended NumPy floats cannot silently lose bits in a plain float.
        if isinstance(value, np.floating) and value != plain:
            raise ValueError("snapshot close is not representable as a plain float")
        return plain, "f:" + plain.hex()
    raise ValueError("snapshot close must be numeric or missing")


def source_snapshot(closes: pd.DataFrame, *, source_reference: str,
                    adjustment_bases: dict[str, str]) -> dict:
    """Fingerprint supplied primary-index/FX observations, without fetching.

    This records content and the caller's explicit basis labels. It does not
    attest freshness, calendar completion, source rights or financial fitness.
    A missing series remains empty; an observed row with a missing cell remains
    a dated null. Source-reference labels are outside the content digest.
    """
    import hashlib
    import json

    if type(source_reference) is not str or not source_reference.strip():
        raise ValueError("snapshot requires a nonempty source reference")
    if not isinstance(closes, pd.DataFrame):
        raise ValueError("snapshot requires a DataFrame")
    if not isinstance(closes.index, pd.DatetimeIndex):
        raise ValueError("snapshot requires a DatetimeIndex")
    if (closes.index.hasnans or not closes.index.is_unique
            or not closes.index.is_monotonic_increasing):
        raise ValueError("snapshot timestamps must be valid, unique and ascending")
    if not closes.columns.is_unique:
        raise ValueError("snapshot columns must be unique")

    series_ids = []
    for country in countries().values():
        for series_id in (country["index"], country["fx"]):
            if type(series_id) is not str or not series_id:
                raise ValueError("snapshot configuration has an invalid series identity")
            if series_id not in series_ids:
                series_ids.append(series_id)
    if (type(adjustment_bases) is not dict
            or any(type(k) is not str for k in adjustment_bases)
            or set(adjustment_bases) != set(series_ids)
            or any(type(v) is not str or not v.strip() for v in adjustment_bases.values())):
        raise ValueError("snapshot requires one explicit basis per configured series")

    timestamps = [timestamp.isoformat() for timestamp in closes.index]
    # Pandas MultiIndex membership permits partial-key matches. Only an exact
    # configured string label names a series; structured extra columns do not.
    positions = {label: position for position, label in enumerate(closes.columns)
                 if type(label) is str}
    series, digest_rows = [], []
    for series_id in series_ids:
        basis = adjustment_bases[series_id]
        observations, digest_observations = [], []
        if series_id in positions:
            # Series.array retains nullable integer and NumPy scalar identity;
            # iterrows() can instead coerce a large integer through a float.
            for timestamp, scalar in zip(timestamps, closes.iloc[:, positions[series_id]].array):
                value, token = _snapshot_close_scalar(scalar)
                observations.append({"timestamp": timestamp, "value": value})
                digest_observations.append([timestamp, token])
        series.append({"series_id": series_id, "adjustment_basis": basis,
                       "observations": observations})
        digest_rows.append([series_id, basis, digest_observations])

    encoded = json.dumps(digest_rows, ensure_ascii=False, separators=(",", ":"),
                         allow_nan=False).encode("utf-8")
    return {"source_reference": source_reference,
            "content_sha256": hashlib.sha256(encoded).hexdigest(), "series": series}


def _qualification_plain_json(value, *, numeric=False):
    if value is None:
        return not numeric
    if type(value) is bool:
        return not numeric
    if type(value) is str:
        return not numeric
    if type(value) is int:
        return True
    if type(value) is float:
        import math
        return math.isfinite(value)
    if type(value) is list:
        return all(_qualification_plain_json(item) for item in value)
    if type(value) is dict:
        return all(type(key) is str and _qualification_plain_json(item)
                   for key, item in value.items())
    return False


def _qualification_require_closed(value, keys, message):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(message)


def _qualification_text(value, message="invalid_qualification_input"):
    if type(value) is not str or not value.strip():
        raise ValueError(message)
    return value


def _qualification_typed(value):
    import math

    if value is None:
        return ["n"]
    if type(value) is bool:
        return ["b", value]
    if type(value) is str:
        return ["s", value]
    if type(value) is int:
        return ["i", format(value, "x") if value >= 0 else "-" + format(-value, "x")]
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("invalid_qualification_number")
        return ["f", value.hex()]
    if type(value) is list:
        return ["a", [_qualification_typed(item) for item in value]]
    if type(value) is dict:
        return ["o", [[key, _qualification_typed(value[key])] for key in sorted(value)]]
    raise ValueError("invalid_qualification_type")


def _qualification_typed_digest(value):
    import hashlib
    import json

    encoded = _qualification_typed(value)
    material = json.dumps(encoded, ensure_ascii=False, separators=(",", ":"),
                          allow_nan=False).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _qualification_parse_timestamp(value):
    import re
    from datetime import datetime, timedelta, timezone
    from fractions import Fraction

    pattern = re.fullmatch(
        r"([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(?:[.,]([0-9]+))?(Z|[+-][0-9]{2}:[0-9]{2})?",
        value,
    ) if type(value) is str else None
    if pattern is None:
        raise ValueError("invalid_qualification_timestamp")
    year, month, day, hour, minute, second, fraction, zone = pattern.groups()
    tzinfo = None
    if zone is not None and zone != "Z":
        sign = 1 if zone[0] == "+" else -1
        offset = timedelta(hours=int(zone[1:3]), minutes=int(zone[4:6]))
        if int(zone[4:6]) >= 60 or offset >= timedelta(days=1):
            raise ValueError("invalid_qualification_timestamp")
        tzinfo = timezone(sign * offset)
    elif zone == "Z":
        tzinfo = timezone.utc
    try:
        instant = datetime(int(year), int(month), int(day), int(hour), int(minute),
                           int(second), tzinfo=tzinfo)
    except ValueError as exc:
        raise ValueError("invalid_qualification_timestamp") from exc
    return instant, Fraction(int(fraction or 0), 10 ** len(fraction or "1"))


def _qualification_snapshot_digest(snapshot):
    import hashlib
    import json

    digest_rows = []
    all_zone_present = None
    for series in snapshot["series"]:
        digest_observations = []
        prior = None
        prior_zone = None
        for observation in series["observations"]:
            value = observation["value"]
            if value is None:
                token = None
            elif type(value) is int:
                token = _snapshot_close_scalar(value)[1]
            elif type(value) is float:
                import math
                if not math.isfinite(value):
                    raise ValueError("invalid_qualification_snapshot")
                token = "f:" + value.hex()
            else:
                raise ValueError("invalid_qualification_snapshot")
            instant, fraction = _qualification_parse_timestamp(observation["timestamp"])
            key = (instant, fraction)
            zone_present = observation["timestamp"].endswith(("Z", "+00:00")) or (
                len(observation["timestamp"]) >= 6
                and observation["timestamp"][-6] in "+-"
                and observation["timestamp"][-3] == ":"
            )
            if all_zone_present is None:
                all_zone_present = zone_present
            elif all_zone_present != zone_present:
                raise ValueError("invalid_qualification_snapshot")
            if prior is not None and (prior_zone != zone_present or key <= prior):
                raise ValueError("invalid_qualification_snapshot")
            prior, prior_zone = key, zone_present
            digest_observations.append([observation["timestamp"], token])
        digest_rows.append([series["series_id"], series["adjustment_basis"],
                            digest_observations])
    encoded = json.dumps(digest_rows, ensure_ascii=False, separators=(",", ":"),
                         allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _qualification_validate_inputs(records, snapshot, source_evidence,
                                   disclosure_decisions):
    inputs = (records, snapshot, source_evidence, disclosure_decisions)
    try:
        plain = all(_qualification_plain_json(value) for value in inputs)
    except RecursionError:
        plain = False
    if not plain:
        raise ValueError("invalid_qualification_input")
    _qualification_require_closed(records, {
        "source_reference", "source_reference_reason", "numerical_status", "reason", "records"
    }, "invalid_qualification_records")
    if type(records["records"]) is not list:
        raise ValueError("invalid_qualification_records")
    _qualification_text(records["source_reference"], "invalid_qualification_records")

    _qualification_require_closed(snapshot, {
        "source_reference", "content_sha256", "series"
    }, "invalid_qualification_snapshot")
    if type(snapshot["series"]) is not list:
        raise ValueError("invalid_qualification_snapshot")
    _qualification_text(snapshot["source_reference"], "invalid_qualification_snapshot")
    _qualification_text(snapshot["content_sha256"], "invalid_qualification_snapshot")
    series_by_id = {}
    for series in snapshot["series"]:
        _qualification_require_closed(series, {
            "series_id", "adjustment_basis", "observations"
        }, "invalid_qualification_snapshot")
        series_id = _qualification_text(series["series_id"], "invalid_qualification_snapshot")
        if series_id in series_by_id:
            raise ValueError("invalid_qualification_snapshot")
        _qualification_text(series["adjustment_basis"], "invalid_qualification_snapshot")
        if type(series["observations"]) is not list:
            raise ValueError("invalid_qualification_snapshot")
        for observation in series["observations"]:
            _qualification_require_closed(observation, {"timestamp", "value"},
                                          "invalid_qualification_snapshot")
            _qualification_parse_timestamp(observation["timestamp"])
            if observation["value"] is not None and type(observation["value"]) not in {int, float}:
                raise ValueError("invalid_qualification_snapshot")
        series_by_id[series_id] = series

    configured = []
    for country in countries().values():
        for series_id in (country["index"], country["fx"]):
            if series_id not in configured:
                configured.append(series_id)
    if list(series_by_id) != configured:
        raise ValueError("invalid_qualification_snapshot")
    if _qualification_snapshot_digest(snapshot) != snapshot["content_sha256"]:
        raise ValueError("invalid_qualification_snapshot")
    if snapshot["source_reference"] != records["source_reference"]:
        raise ValueError("invalid_qualification_snapshot")

    if type(source_evidence) is not list:
        raise ValueError("invalid_qualification_source_evidence")
    evidence_by_series = {}
    for evidence in source_evidence:
        _qualification_require_closed(evidence, {
            "source_reference", "content_sha256", "series_id", "adjustment_basis",
            "basis_state", "evaluated_at", "latest_completed_observation",
            "calendar_ref", "owner_ref", "decision_ref"
        }, "invalid_qualification_source_evidence")
        series_id = _qualification_text(evidence["series_id"],
                                        "invalid_qualification_source_evidence")
        if series_id in evidence_by_series:
            raise ValueError("invalid_qualification_source_evidence")
        _qualification_text(evidence["source_reference"], "invalid_qualification_source_evidence")
        _qualification_text(evidence["content_sha256"], "invalid_qualification_source_evidence")
        _qualification_text(evidence["adjustment_basis"], "invalid_qualification_source_evidence")
        for field in ("owner_ref", "decision_ref"):
            _qualification_text(evidence[field], "invalid_qualification_source_evidence")
        for field in ("evaluated_at", "latest_completed_observation", "calendar_ref"):
            if evidence[field] is not None and type(evidence[field]) is not str:
                raise ValueError("invalid_qualification_source_evidence")
        if series_id not in series_by_id:
            raise ValueError("invalid_qualification_source_evidence")
        if type(evidence["basis_state"]) is not str or evidence["basis_state"] not in {"accepted", "unknown", "failed"}:
            raise ValueError("invalid_qualification_source_evidence")
        evidence_by_series[series_id] = evidence

    if type(disclosure_decisions) is not list:
        raise ValueError("invalid_qualification_disclosure")
    disclosures = {}
    decision_fields = (
        "source_reference", "content_sha256", "market_id", "index_id", "fx_id",
        "horizon", "currency_basis", "return_basis", "leg", "owner_ref",
        "policy_ref", "decision_ref", "metadata", "value",
    )
    decision_identity_fields = decision_fields[:-2]
    decision_index_fields = (
        "source_reference", "content_sha256", "market_id", "index_id", "fx_id",
        "horizon", "currency_basis", "return_basis", "leg",
    )
    for decision in disclosure_decisions:
        _qualification_require_closed(decision, decision_fields,
                                      "invalid_qualification_disclosure")
        for field in decision_identity_fields:
            _qualification_text(decision[field], "invalid_qualification_disclosure")
        if (type(decision["metadata"]) is not str or type(decision["value"]) is not str
                or decision["metadata"] not in {"allowed", "denied", "unknown"}
                or decision["value"] not in {"allowed", "denied", "unknown"}):
            raise ValueError("invalid_qualification_disclosure")
        if (decision["leg"] not in {"local", "usd", "fx_contribution"}
                or decision["currency_basis"] not in {"local", "usd_unhedged"}
                or decision["return_basis"] != "price"):
            raise ValueError("invalid_qualification_disclosure")
        identity = tuple(decision[field] for field in decision_identity_fields)
        index = tuple(decision[field] for field in decision_index_fields)
        if identity in disclosures or index in disclosures:
            raise ValueError("invalid_qualification_disclosure")
        disclosures[index] = decision

    _qualification_validate_records(records)
    return series_by_id, evidence_by_series, disclosures


def _qualification_validate_records(records):
    error = "invalid_qualification_records"
    roster = countries()
    def text(value, nullable=False):
        if value is None and nullable:
            return
        _qualification_text(value, error)
    def member(value, choices):
        if type(value) is not str or value not in choices:
            raise ValueError(error)
    member(records["numerical_status"], {"available", "partial", "unavailable"})
    text(records["source_reference_reason"], True)
    text(records["reason"], True)
    seen = set()
    for record in records["records"]:
        _qualification_require_closed(record, {
            "market_id", "index_id", "index_label", "fx_id", "fx_quote_orientation",
            "horizon", "requested_observations", "return_basis", "qualification",
            "local", "usd", "fx_contribution"}, error)
        for field in ("market_id", "index_id", "index_label", "fx_id", "horizon"):
            text(record[field])
        if record["market_id"] not in roster:
            raise ValueError(error)
        country = roster[record["market_id"]]
        if record["index_id"] != country["index"] or record["fx_id"] != country["fx"]:
            raise ValueError(error)
        expected_label = (country.get("indices") or {}).get(country["index"], country["index"])
        if record["index_label"] != expected_label:
            raise ValueError(error)
        orientation = "local_per_USD" if country.get("fx_invert") else "USD_per_local"
        if record["fx_quote_orientation"] != orientation or record["return_basis"] != "price" or record["qualification"] != "not_evaluated":
            raise ValueError(error)
        n = record["requested_observations"]
        if record["horizon"] == "ytd":
            if n is not None:
                raise ValueError(error)
        elif type(n) is not int or n <= 0:
            raise ValueError(error)
        identity = record["market_id"], record["horizon"]
        if identity in seen:
            raise ValueError(error)
        seen.add(identity)
        for leg in ("local", "usd", "fx_contribution"):
            metric = record[leg]
            _qualification_require_closed(metric, {"value", "unit", "numerical_status", "reason", "window"}, error)
            member(metric["numerical_status"], {"available", "unavailable"})
            if metric["unit"] != ("percentage_points" if leg == "fx_contribution" else "percent"):
                raise ValueError(error)
            if metric["numerical_status"] == "available":
                if type(metric["value"]) not in (int, float) or metric["reason"] is not None or metric["window"] is None:
                    raise ValueError(error)
            elif metric["value"] is not None:
                raise ValueError(error)
            else:
                text(metric["reason"])
            window = metric["window"]
            if window is None:
                continue
            _qualification_require_closed(window, {"start", "end", "calendar_policy", "endpoint_observations"}, error)
            text(window["calendar_policy"])
            _qualification_require_closed(window["endpoint_observations"], {"price_start", "price_end", "fx_start", "fx_end"}, error)
            try:
                start = _qualification_parse_timestamp(window["start"])
                end = _qualification_parse_timestamp(window["end"])
                if (start[0].tzinfo is None) != (end[0].tzinfo is None) or start > end:
                    raise ValueError(error)
                for field, value in window["endpoint_observations"].items():
                    if value is None:
                        continue
                    contribution = _qualification_parse_timestamp(value)
                    endpoint = start if field.endswith("_start") else end
                    if (contribution[0].tzinfo is None) != (endpoint[0].tzinfo is None) or contribution > endpoint:
                        raise ValueError(error)
            except (TypeError, ValueError) as exc:
                raise ValueError(error) from exc


def _qualification_observation_by_instant(series):
    result = {}
    latest = None
    all_zone_present = None
    for observation in series["observations"]:
        timestamp = observation["timestamp"]
        key = _qualification_parse_timestamp(timestamp)
        zone_present = timestamp.endswith(("Z", "+00:00")) or (
            len(timestamp) >= 6 and timestamp[-6] in "+-" and timestamp[-3] == ":"
        )
        if all_zone_present is None:
            all_zone_present = zone_present
        elif all_zone_present != zone_present:
            raise ValueError("invalid_qualification_timestamp")
        result[key] = observation
        if observation["value"] is not None and (latest is None or key > latest):
            latest = key
    return result, latest


def _qualification_decision_key(record, currency_basis, leg, snapshot):
    return (
        snapshot["source_reference"], snapshot["content_sha256"], record["market_id"],
        record["index_id"], record["fx_id"], record["horizon"], currency_basis,
        record["return_basis"], leg,
    )


def qualify_return_records(records, *, snapshot, source_evidence,
                           disclosure_decisions, policy_id, currency_basis):
    """Evaluate completed-session endpoint evidence under the accepted policy only."""
    from copy import deepcopy

    policy = "intl-observed-endpoints-completed-session-v1"
    evaluator = "engine.intl_inputs:qualify_return_records"
    if policy_id != policy:
        raise ValueError("unknown_policy")
    if type(currency_basis) is not str or currency_basis not in {"local", "usd_unhedged"}:
        raise ValueError("invalid_currency_basis")

    series_by_id, evidence_by_series, disclosures = _qualification_validate_inputs(
        records, snapshot, source_evidence, disclosure_decisions
    )
    qualification_unknown = []
    receipts = []
    traces = []
    context_material = None
    context_digest = None
    for record in records["records"]:
        for leg in ("local", "usd", "fx_contribution"):
            decision = disclosures.get(_qualification_decision_key(
                record, currency_basis, leg, snapshot
            ))
            if decision is None:
                qualification_unknown.append({
                    "code": "qualification_unknown", "market_id": record["market_id"],
                    "horizon": record["horizon"], "leg": leg,
                    "currency_basis": currency_basis,
                })
                continue

            metric = record[leg]
            required_series = [record["index_id"]]
            if leg != "local":
                required_series.append(record["fx_id"])
            evidence_errors = []
            session_states = []
            observations_by_series = {}
            for series_id in required_series:
                series = series_by_id[series_id]
                observations, latest = _qualification_observation_by_instant(series)
                observations_by_series[series_id] = (observations, latest)
                item = evidence_by_series.get(series_id)
                if item is None:
                    evidence_errors.append("session_unknown")
                    session_states.append("unknown")
                    continue
                if (item["source_reference"] != snapshot["source_reference"]
                        or item["content_sha256"] != snapshot["content_sha256"]
                        or item["adjustment_basis"] != series["adjustment_basis"]):
                    evidence_errors.append("invalid_source_evidence")
                    session_states.append("unknown")
                    continue
                if not item["calendar_ref"] or not item["calendar_ref"].strip():
                    session_states.append("unknown")
                    continue
                try:
                    evaluated = _qualification_parse_timestamp(item["evaluated_at"])
                    completed = _qualification_parse_timestamp(
                        item["latest_completed_observation"]
                    )
                    if (completed[0].tzinfo is None) != (evaluated[0].tzinfo is None):
                        raise ValueError("invalid_qualification_timestamp")
                    if latest is not None and (latest[0].tzinfo is None) != (completed[0].tzinfo is None):
                        raise ValueError("invalid_qualification_timestamp")
                    if completed > evaluated:
                        raise ValueError("invalid_qualification_timestamp")
                except ValueError:
                    evidence_errors.append("invalid_source_evidence")
                    session_states.append("unknown")
                    continue
                if item["basis_state"] != "accepted":
                    evidence_errors.append("adjustment_basis_" + item["basis_state"])
                    continue
                if latest is None or latest < completed:
                    session_states.append("stale")
                elif latest > completed:
                    session_states.append("invalid")
                else:
                    session_states.append("current")

            quality = "qualified"
            reason = None
            if metric["numerical_status"] != "available":
                quality, reason = "missing", "missing_return"
            elif evidence_errors:
                quality, reason = "unknown", evidence_errors[0]
            elif "unknown" in session_states:
                quality, reason = "unknown", "session_unknown"
            elif "invalid" in session_states:
                quality, reason = "unknown", "invalid_source_evidence"
            elif "stale" in session_states:
                quality, reason = "stale", "source_session_missed"
            elif decision["metadata"] == "unknown":
                quality, reason = "unknown", "metadata_unknown"
            elif decision["metadata"] == "denied":
                quality, reason = "denied", "metadata_denied"
            elif decision["value"] == "unknown":
                quality, reason = "unknown", "value_unknown"
            elif decision["value"] == "denied":
                quality, reason = "denied", "value_denied"
            elif metric["window"] is None:
                quality, reason = "missing", "missing_return"
            else:
                window = metric["window"]
                for series_id in required_series:
                    observations, _ = observations_by_series[series_id]
                    fields = ("price_start", "price_end") if series_id == record["index_id"] else ("fx_start", "fx_end")
                    for field in fields:
                        contribution = window.get("endpoint_observations", {}).get(field)
                        if not contribution:
                            quality, reason = "unsupported", "carry_not_admitted"
                            break
                        key = _qualification_parse_timestamp(contribution)
                        endpoint = _qualification_parse_timestamp(window["start" if field.endswith("_start") else "end"])
                        if key != endpoint:
                            quality, reason = "unsupported", "carry_not_admitted"
                            break
                        if field.endswith("_end") and key != _qualification_parse_timestamp(evidence_by_series[series_id]["latest_completed_observation"]):
                            quality, reason = "unknown", "invalid_source_evidence"
                            break
                        observation = observations.get(key)
                        if observation is None or observation["value"] is None or not observation["value"] > 0:
                            quality, reason = "unsupported", "carry_not_admitted"
                            break
                    if quality != "qualified":
                        break

            if quality == "qualified" and leg != "local":
                paired = record["usd"]["window"]
                if paired is None or any(
                    _qualification_parse_timestamp(metric["window"][key]) != _qualification_parse_timestamp(paired[key])
                    for key in ("start", "end")
                ) or metric["window"]["calendar_policy"] != paired["calendar_policy"]:
                    quality, reason = "unsupported", "unequal_paired_window"

            if context_material is None:
                context_material = {
                    "domain": "intl-inputs-evaluation-context-v1", "evaluator_ref": evaluator,
                    "policy_id": policy,
                    "policy_acceptance_sha256": "29649f97e6bf408b730ef0f9f6c808738ef99a69da2fec9aa95f2595ddf23491",
                    "records": deepcopy(records), "snapshot": deepcopy(snapshot),
                    "source_evidence": deepcopy(source_evidence),
                    "disclosure_decisions": deepcopy(disclosure_decisions),
                    "currency_basis": currency_basis,
                }
                context_digest = _qualification_typed_digest(context_material)

            binding = {
                "source_reference": deepcopy(snapshot["source_reference"]),
                "market_id": deepcopy(record["market_id"]),
                "index_id": deepcopy(record["index_id"]),
                "fx_id": deepcopy(record["fx_id"]),
                "horizon": deepcopy(record["horizon"]),
                "currency_basis": currency_basis,
                "return_basis": deepcopy(record["return_basis"]),
                "leg": leg,
                "value": deepcopy(metric["value"]),
                "unit": deepcopy(metric["unit"]),
                "window": deepcopy(metric["window"]),
            }
            outcome = {"binding": binding, "quality": quality, "reason": reason,
                       "disclosure": {"metadata": deepcopy(decision["metadata"]),
                                      "value": deepcopy(decision["value"])}}
            trace_material = {
                "domain": "intl-inputs-evaluation-receipt-v1", "evaluator_ref": evaluator,
                "policy_id": policy, "context_sha256": context_digest,
                "outcome": deepcopy(outcome),
            }
            decision_ref = "derived-evaluation:sha256:" + _qualification_typed_digest(trace_material)
            receipts.append({
                "binding": binding, "owner_ref": evaluator, "policy_ref": policy,
                "decision_ref": decision_ref, "quality": quality, "reason": reason,
                "disclosure": deepcopy(outcome["disclosure"]),
            })
            traces.append({"code": "evaluation_trace", "decision_ref": decision_ref,
                           "material": trace_material})
    diagnostics = qualification_unknown
    if context_material is not None:
        diagnostics = [{
            "code": "evaluation_context", "context_sha256": context_digest,
            "material": context_material,
        }, *traces, *qualification_unknown]
    return {"qualifications": receipts, "diagnostics": diagnostics}
