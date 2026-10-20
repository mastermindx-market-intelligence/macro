"""Read-only country research inputs for the existing International publisher.

Network acquisition belongs to IntlMacroAdapter. This module combines the
reviewed initial source snapshot with its last successful refresh and retains
every source vintage. It does not write data, issue signals, or create a ledger.
"""
from __future__ import annotations

from calendar import monthrange
from copy import deepcopy
from datetime import date
from math import fsum, isclose, isfinite
from numbers import Real
import json
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse
from collectors.intl_country_sources import SCHEMA, merge_country_inputs

MAX_INPUT_BYTES = 1_500_000


def _read(path):
    try:
        if path.stat().st_size > MAX_INPUT_BYTES:
            raise ValueError("country_input_size_limit")
        result = json.loads(path.read_text(encoding="utf-8"))
        return result if type(result) is dict else {}
    except (OSError, ValueError):
        return {}


def load_country_inputs(data_root, source_root):
    source_root, data_root = Path(source_root), Path(data_root)
    baseline = _read(source_root / "config/intl_country_baseline.json")
    refreshed = _read(data_root / "intl_macro/country_inputs.json")
    inputs = merge_country_inputs(baseline, refreshed, preserve_custody=True)
    commentary = _read(source_root / "config/intl_country_commentary.json")
    inputs["commentary"] = (commentary.get("countries") or {}) if commentary.get("schema") == "intl_country_commentary.v1" else {}
    return inputs

# These identities are the actual IntlMacroAdapter plan, reviewed against each
# provider series definition. They are not alternative acquisition routes.
STORED_MACRO_SCHEMA = "intl_stored_macro_observation.v1"
_FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"
_EUROSTAT_BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
_EZ_LABOUR_PARAMS = {"geo": "EA21", "s_adj": "SA", "age": "TOTAL", "unit": "PC_ACT", "sex": "T"}
_GDP_SERIES = {
    "JP": ("JPNRGDPEXP", "JP. Cabinet Office", "Billions of chained 2015 yen", "Japan"),
    "KR": ("NGDPRSAXDCKRQ", "International Monetary Fund", "Millions of domestic currency", "Republic of Korea"),
    "AU": ("NGDPRSAXDCAUQ", "International Monetary Fund", "Millions of domestic currency", "Australia"),
    "GB": ("NGDPRSAXDCGBQ", "International Monetary Fund", "Millions of domestic currency", "United Kingdom"),
    "EZ": ("CLVMNACSCAB1GQEA19", "Eurostat", "Millions of chained 2010 euros", "Euro area (19 countries)"),
}
_UNEMPLOYMENT_SERIES = {
    "JP": "LRHUTTTTJPM156S", "KR": "LRHUTTTTKRM156S",
    "AU": "LRHUTTTTAUM156S", "GB": "LRHUTTTTGBM156S",
}


def _stored_day(value):
    if type(value) is not str or len(value) != 10:
        return None
    try:
        parsed = date.fromisoformat(value)
        return parsed if parsed.isoformat() == value else None
    except ValueError:
        return None


def _stored_number(value):
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    try:
        numeric = float(value)
        return numeric if isfinite(numeric) and numeric == value else None
    except (ValueError, OverflowError):
        return None


def _stored_definition(cc, metric):
    if metric == "gdp" and cc in _GDP_SERIES:
        series, publisher, native_unit, geography = _GDP_SERIES[cc]
    elif metric == "unemployment" and cc in _UNEMPLOYMENT_SERIES:
        series, publisher, native_unit = _UNEMPLOYMENT_SERIES[cc], "OECD", "Percent of labour force"
        geography = _GDP_SERIES[cc][3]
    elif (cc, metric) == ("EZ", "unemployment"):
        return {"series_id": "une_rt_m", "source": "Eurostat",
                "source_url": None, "native_unit": "Percent of active population",
                "geography": "Euro area (EA21)", "provider": "eurostat"}
    else:
        return None
    return {"series_id": series, "source": "FRED · " + publisher,
            "source_url": "https://fred.stlouisfed.org/series/" + series,
            "native_unit": native_unit, "geography": geography, "provider": "fred_fallback"}


def _query_matches(url, base, params):
    if type(url) is not str:
        return False
    try:
        parsed = urlparse(url)
        expected = urlparse(base)
        return (parsed.scheme == expected.scheme and parsed.netloc == expected.netloc
                and parsed.path == expected.path and not parsed.fragment
                and parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
                == {key: [value] for key, value in params.items()})
    except ValueError:
        return False


def _stored_request_matches(url, definition):
    if definition["provider"] == "fred_fallback":
        return _query_matches(url, _FRED_BASE, {"id": definition["series_id"]})
    if type(url) is not str:
        return False
    try:
        params = parse_qs(urlparse(url).query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        return False
    since = params.get("sinceTimePeriod", [])
    if len(since) > 1 or (since and _stored_day(since[0] + "-01") is None):
        return False
    expected = {"lang": "en", **_EZ_LABOUR_PARAMS}
    if since:
        expected["sinceTimePeriod"] = since[0]
    return _query_matches(url, _EUROSTAT_BASE + "/une_rt_m", expected)


def _stored_observation(cc, metric, rows, source_request_url, *, today):
    """Build a trace from exact stored levels, without assigning an acquisition clock."""
    definition = _stored_definition(cc, metric)
    needed = 5 if metric == "gdp" else 1
    if (definition is None or type(today) is not date or type(rows) is not list
            or len(rows) != needed or not _stored_request_matches(source_request_url, definition)):
        return None
    observations, days = [], []
    for row in rows:
        if type(row) is not dict or set(row) != {"date", "value"}:
            return None
        day, value = _stored_day(row["date"]), _stored_number(row["value"])
        if day is None or day.day != 1 or value is None:
            return None
        if (metric == "gdp" and (day.month not in (1, 4, 7, 10) or value <= 0)
                or metric == "unemployment" and not 0 <= value <= 100):
            return None
        observations.append({"date": day.isoformat(), "value": value})
        days.append(day)
    end = days[-1]
    if metric == "gdp":
        quarters = [day.year * 4 + (day.month - 1) // 3 for day in days]
        if quarters != list(range(quarters[-1] - 4, quarters[-1] + 1)):
            return None
        month = end.month + 2
        period = f"{end.year}-Q{(end.month - 1) // 3 + 1}"
        value = (observations[-1]["value"] / observations[0]["value"] - 1) * 100
        if not isfinite(value):
            return None
    else:
        month, period, value = end.month, end.strftime("%Y-%m"), observations[-1]["value"]
    period_end = date(end.year, month, monthrange(end.year, month)[1])
    if period_end > today:
        return None
    return {
        "schema": STORED_MACRO_SCHEMA, "cc": cc, "metric": metric,
        "kind": "calculated_from_stored_levels" if metric == "gdp" else "stored_observation",
        "value": value, "unit": "% y/y" if metric == "gdp" else "%",
        "period": period, "period_end": period_end.isoformat(),
        "source": definition["source"],
        "source_url": definition["source_url"] or source_request_url,
        "series_id": definition["series_id"], "source_request_url": source_request_url,
        "native_unit": definition["native_unit"], "unit_basis": "reviewed_series_definition",
        "frequency": "quarterly" if metric == "gdp" else "monthly",
        "seasonal_adjustment": "seasonally_adjusted", "geography": definition["geography"],
        "stored_path": f"intl_macro/{cc}_{metric}.parquet", "stored_column": f"{cc}_{metric}",
        "method": "(end / start - 1) * 100" if metric == "gdp" else "reported_level",
        "observations": observations, "retrieved_at": None, "vintage_custody": "not_recorded",
    }


def stored_observation_view(raw, cc, metric, *, today):
    """Recheck the explicit mapping; anonymous legacy scalars are never receipts."""
    if type(raw) is not dict:
        return None
    expected = _stored_observation(cc, metric, raw.get("observations"),
                                   raw.get("source_request_url"), today=today)
    if expected is None or _stored_number(raw.get("value")) is None or raw != expected:
        return None
    return expected


def _configured_stored_source(cc, metric, intl_config, metadata):
    definition = _stored_definition(cc, metric)
    if definition is None or type(intl_config) is not dict or type(metadata) is not dict:
        return False
    countries, macro = intl_config.get("countries"), intl_config.get("macro")
    if type(countries) is not dict or type(macro) is not dict or type(countries.get(cc)) is not dict:
        return False
    if (metadata.get("provider") != definition["provider"]
            or metadata.get("source_id") != definition["series_id"]
            or not _stored_request_matches(metadata.get("source_url"), definition)):
        return False
    if definition["provider"] == "fred_fallback":
        fred = countries[cc].get("fred")
        return (type(fred) is dict and fred.get(metric) == definition["series_id"]
                and macro.get("fred_base_url") == _FRED_BASE
                and metadata.get("status") == "fallback" and metadata.get("unit") is None)
    official = macro.get("official_series")
    spec = official.get("EZ_unemployment") if type(official) is dict else None
    if type(spec) is not dict:
        return False
    params = {"lang": "en", **_EZ_LABOUR_PARAMS}
    if spec.get("since"):
        params["sinceTimePeriod"] = str(spec["since"])
    return (spec.get("provider") == "eurostat" and spec.get("dataset") == "une_rt_m"
            and spec.get("unit") == "PC_ACT" and spec.get("params") == _EZ_LABOUR_PARAMS
            and type(spec.get("base_url") or _EUROSTAT_BASE) is str
            and (spec.get("base_url") or _EUROSTAT_BASE).rstrip("/") == _EUROSTAT_BASE
            and metadata.get("unit") == "PC_ACT" and metadata.get("status") == "official"
            and _query_matches(metadata["source_url"], _EUROSTAT_BASE + "/une_rt_m", params))


def load_stored_country_observations(data_root, intl_config, *, today):
    """Read canonical macro files and their actual producer identities, without I/O effects.

    IntlMacroAdapter writes its provenance before the store upsert and does not
    retain a row-bound acquisition or revision receipt. Matching series and raw
    dates support a descriptive observation; requested_at, source_updated, file
    mtime and render time do not establish its stored vintage.
    """
    import pandas as pd

    data_root = Path(data_root)
    provenance = _read(data_root / "intl_macro/provenance.json")
    if provenance.get("schema") != "intl_macro_provenance.v1" or type(today) is not date:
        return {}
    series = provenance.get("series")
    if type(series) is not dict:
        return {}
    result = {}
    for cc in _GDP_SERIES:
        for metric in ("gdp", "unemployment"):
            column = f"{cc}_{metric}"
            metadata = series.get(column)
            if not _configured_stored_source(cc, metric, intl_config, metadata):
                continue
            path = data_root / "intl_macro" / (column + ".parquet")
            try:
                if path.stat().st_size > MAX_INPUT_BYTES:
                    continue
                frame = pd.read_parquet(path)
                if (not frame.columns.is_unique or column not in frame
                        or not isinstance(frame.index, pd.DatetimeIndex)
                        or frame.index.tz is not None or frame.index.hasnans
                        or not frame.index.is_unique or not frame.index.equals(frame.index.normalize())):
                    continue
                values = frame[column].dropna().sort_index()
                if values.empty or metadata.get("last_observation") != values.index[-1].date().isoformat():
                    continue
                tail = values.iloc[-(5 if metric == "gdp" else 1):]
                rows = [{"date": stamp.date().isoformat(), "value": value}
                        for stamp, value in tail.items()]
                observation = _stored_observation(cc, metric, rows, metadata["source_url"], today=today)
                if observation:
                    result.setdefault(cc, {})[metric] = observation
            except (OSError, ValueError, TypeError, KeyError, ImportError):
                # A corrupt optional macro file cannot remove other country inputs.
                continue
    return result

# Equity evidence describes provider-labelled rows in the canonical price store.
# It is not an acquisition receipt or proof of exchange-session finality.
EQUITY_OBSERVATION_SCHEMA = "intl_equity_observation.v1"
_EQUITY_SYMBOLS = {"JP": "^N225", "KR": "^KS11", "TW": "^TWII", "IN": "^NSEI",
                   "AU": "^AXJO", "GB": "^FTSE", "EZ": "^STOXX"}
_EQUITY_EVIDENCE_KEYS = {"schema", "source", "as_of", "rows", "latest_close",
                         "mean_50", "mean_200", "recent_high"}
_EQUITY_WINDOW_KEYS = {"method", "target_observations", "minimum_observations",
                       "observations", "start", "end", "value"}


def equity_source_for(cc):
    """Identity of the incumbent canonical index price source."""
    if type(cc) is not str or cc not in _EQUITY_SYMBOLS:
        return None
    symbol = _EQUITY_SYMBOLS[cc]
    return {"provider": "Yahoo Finance", "adapter": "yfinance", "symbol": symbol,
            "source_url": "https://finance.yahoo.com/quote/" + quote(symbol, safe="") + "/",
            "store_group": "intl", "price_field": "Close", "auto_adjust": True,
            "interval": "1d", "date_basis": "provider_daily_label"}


def _equity_number(value):
    # JSON evidence must already contain plain numbers, never bool/string coercions.
    return _stored_number(value) if type(value) in (int, float) else None


def _equity_keys(value, keys):
    return type(value) is dict and set(value) == keys


def _equity_window_matches(actual, rows, *, target, minimum, method):
    high = method == "maximum"
    keys = _EQUITY_WINDOW_KEYS | ({"high_date", "tie_policy"} if high else set())
    if not _equity_keys(actual, keys):
        return False, None
    selected = rows[-target:]
    count = len(selected)
    for key, expected in (("target_observations", target), ("minimum_observations", minimum),
                          ("observations", count)):
        if type(actual[key]) is not int or actual[key] != expected:
            return False, None
    for key, expected in (("method", method), ("start", selected[0][0]), ("end", selected[-1][0])):
        if type(actual[key]) is not str or actual[key] != expected:
            return False, None
    values = [row[1] for row in selected]
    try:
        expected_value = (None if count < minimum else max(values) if high else fsum(values) / count)
    except (OverflowError, ValueError):
        return False, None
    if expected_value is None:
        if actual["value"] is not None:
            return False, None
    else:
        value = _equity_number(actual["value"])
        if value is None or not isclose(value, expected_value, rel_tol=1e-12, abs_tol=1e-10):
            return False, None
    if high:
        high_date = next(stamp for stamp, value in reversed(selected) if value == expected_value)
        if actual["high_date"] != high_date or actual["tie_policy"] != "most_recent":
            return False, None
    return True, expected_value


def validate_equity_evidence(equity, cc, *, today):
    """Reproduce displayed arithmetic and bind it to the incumbent output.

    Rolling means have a small floating-point tolerance against an independently
    summed window. The resulting comparison flags must still agree exactly;
    threshold disagreements withhold evidence rather than change legacy values.
    """
    if type(today) is not date or type(equity) is not dict:
        return None
    evidence = equity.get("observation_evidence")
    if (not _equity_keys(evidence, _EQUITY_EVIDENCE_KEYS)
            or evidence["schema"] != EQUITY_OBSERVATION_SCHEMA):
        return None
    source = equity_source_for(cc)
    actual_source = evidence["source"]
    if source is None or not _equity_keys(actual_source, set(source)):
        return None
    if any(type(actual_source[key]) is not type(expected) or actual_source[key] != expected
           for key, expected in source.items()):
        return None
    observed = _stored_day(evidence["as_of"])
    if observed is None or observed > today:
        return None
    supplied_rows = evidence["rows"]
    if type(supplied_rows) is not list or not 60 <= len(supplied_rows) <= 252:
        return None
    rows, previous = [], None
    for row in supplied_rows:
        if type(row) is not list or len(row) != 2:
            return None
        stamp, value = _stored_day(row[0]), _equity_number(row[1])
        if (stamp is None or value is None or value <= 0
                or previous is not None and stamp <= previous):
            return None
        rows.append([stamp.isoformat(), value])
        previous = stamp
    if previous != observed:
        return None
    close = rows[-1][1]
    if _equity_number(evidence["latest_close"]) != close:
        return None
    valid_fast, fast_mean = _equity_window_matches(
        evidence["mean_50"], rows, target=50, minimum=25, method="arithmetic_mean")
    valid_slow, slow_mean = _equity_window_matches(
        evidence["mean_200"], rows, target=200, minimum=100, method="arithmetic_mean")
    valid_high, high = _equity_window_matches(
        evidence["recent_high"], rows, target=252, minimum=60, method="maximum")
    if not (valid_fast and valid_slow and valid_high):
        return None
    above_fast = close > fast_mean
    above_slow = close > slow_mean if slow_mean is not None else None
    complete = len(rows) >= 200
    drawdown = (close / high - 1.0) * 100
    if (equity.get("as_of") != evidence["as_of"]
            or _equity_number(equity.get("price")) != round(close, 2)
            or _equity_number(equity.get("off_52w_high")) != round(drawdown, 1)
            or type(equity.get("above_50d")) is not bool or equity["above_50d"] is not above_fast
            or type(equity.get("above_200d")) is not bool
            or equity["above_200d"] is not (above_slow if above_slow is not None else False)
            or type(equity.get("trend_200d_complete")) is not bool
            or equity["trend_200d_complete"] is not complete
            or type(equity.get("high_window_observations")) is not int
            or equity["high_window_observations"] != len(rows)
            or equity.get("high_window_start") != rows[0][0]):
        return None
    result = deepcopy(evidence)
    result.update({"drawdown_pct": drawdown, "above_50d": above_fast, "above_200d": above_slow,
                   "trend_200d_complete": complete, "observation_age_days": (today - observed).days,
                   "retrieved_at": None, "vintage_custody": "not_recorded",
                   "session_finality": "not_verified"})
    return result
