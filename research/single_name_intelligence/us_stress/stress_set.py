"""SNI US stress set — descriptive contemporaneous residuals (draft contract).

SNI-local DRAFT contract. Consumes owner-supplied closes and caller-supplied
profile facts. Does not fork or re-implement Data OS identity, Company
Event/Earnings, FIF, Capital Structure, Stock Identity, Options, Research
Vault, or qledger/Evaluation. Identity ids are opaque strings owned by Stock
Identity / Data OS; this module never mints, derives, or guesses them.

Ticker universe comes only from the profiles directory. This source file has
no per-name branches.

Every authority flag stays false: rank, gate, size, signal, escalation, trade.
Setting any of them to a value other than literal False raises. Residuals are
descriptive, never causal, never a news-impact claim. Unestimable windows
abstain (None), never a default 50/50.

Closes are calendar-dated (date_iso, close) pairs. Returns are computed
between consecutive rows of that series, then stock and benchmark returns
are inner-joined on the return's end date before beta/residual. A missing,
non-finite, or non-positive close leaves the date in the series and sets
the returns that touch it to None (no bridged multi-day return).

Optional pandas for parquet. Pure-python paths work without pandas and
without PyYAML (a nested-map / scalar-list subset parser is built in;
limitation: no anchors, aliases, merge keys, flow collections, multiline
scalars, tags, or document markers).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

AUTHORITY_FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

_IDENTITY_ID_KEYS = (
    "canonical_issuer_id",
    "issuer_id",
    "security_id",
    "canonical_security_id",
    "instrument_id",
    "listing_id",
)

_REFUSE_MSG = "stress profiles never carry identity ids"


class AuthorityMap(dict):
    """Mapping that refuses any authority flag other than literal False."""

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.update(*args, **kwargs)

    def __setitem__(self, key, value):
        if key in AUTHORITY_FLAG_NAMES and value is not False:
            raise ValueError(_REFUSE_MSG)
        super().__setitem__(key, value)

    def update(self, *args, **kwargs):
        incoming = dict(*args, **kwargs)
        for key, value in incoming.items():
            self[key] = value

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]

    def copy(self):
        return AuthorityMap(self)

    def __copy__(self):
        return self.copy()

    def __or__(self, other):
        dup = self.copy()
        dup.update(other)
        return dup

    def __ror__(self, other):
        dup = AuthorityMap(other)
        dup.update(self)
        return dup

    def __ior__(self, other):
        self.update(other)
        return self

    def __deepcopy__(self, memo):
        import copy as copy_mod

        dup = AuthorityMap()
        memo[id(self)] = dup
        for key, value in self.items():
            dup[key] = copy_mod.deepcopy(value, memo)
        return dup


def authority_flags(**kwargs):
    """Return all-false authority flags. Refuse any flag not literal False."""
    out = AuthorityMap((name, False) for name in AUTHORITY_FLAG_NAMES)
    for key, value in kwargs.items():
        if key not in AUTHORITY_FLAG_NAMES:
            raise ValueError("unknown authority flag: %s" % key)
        out[key] = value
    return out


def _walk_refuse(obj):
    """Refuse non-False authority flags and non-null identity ids at any depth."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in AUTHORITY_FLAG_NAMES and value is not False:
                raise ValueError(_REFUSE_MSG)
            if key in _IDENTITY_ID_KEYS and value is not None:
                raise ValueError(_REFUSE_MSG)
            if key == "issuer_link" and value is not None and value != "UNRESOLVED":
                raise ValueError(_REFUSE_MSG)
            _walk_refuse(value)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _walk_refuse(item)


def check_profile(profile):
    """Refuse any authority flag other than literal False, and any identity id.

    Walks the whole profile recursively. Keys in the identity-id set whose
    value is not None raise. issuer_link must be the literal "UNRESOLVED"
    or None. Authority flags that are present must satisfy `value is False`.
    """
    if not isinstance(profile, dict):
        raise ValueError(_REFUSE_MSG)
    auth = profile.get("authority") or {}
    if not isinstance(auth, dict):
        raise ValueError(_REFUSE_MSG)
    _walk_refuse(profile)
    return profile


def check_profiles(profiles):
    if not isinstance(profiles, dict):
        raise ValueError(_REFUSE_MSG)
    for profile in profiles.values():
        check_profile(profile)
    return profiles


def _strip_inline_comment(line):
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i].rstrip()
    return line.rstrip()


def _parse_scalar(raw):
    s = raw.strip()
    if s == "" or s == "~" or s == "null":
        return None
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        return s[1:-1]
    if s[0] in "0123456789.+-" and not s.startswith(".-") and s not in ("+", "-", "."):
        try:
            if any(c in s for c in ".eE"):
                return float(s)
            return int(s)
        except ValueError:
            pass
    return s


def _split_key_value(content):
    in_single = False
    in_double = False
    for i, ch in enumerate(content):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == ":" and not in_single and not in_double:
            return content[:i].strip(), content[i + 1 :].strip()
    return None, content


def _minimal_yaml_load(text):
    """Indent-based subset parser for these flat nested-map drafts.

    Limitation: no anchors, aliases, merge keys, flow {}/[], multiline
    scalars (|/>), tags, or '---' documents. PyYAML is used when importable.
    """
    lines = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        line = _strip_inline_comment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        lines.append((indent, line.strip()))
    n = len(lines)

    def parse_list(i, list_indent):
        result = []
        while i < n and lines[i][0] == list_indent and lines[i][1].startswith("- "):
            item = lines[i][1][2:].strip()
            if item == "":
                if i + 1 < n and lines[i + 1][0] > list_indent:
                    child, i = parse_map(i + 1, lines[i + 1][0])
                    result.append(child)
                else:
                    result.append(None)
                    i += 1
            else:
                result.append(_parse_scalar(item))
                i += 1
        return result, i

    def parse_map(i, map_indent):
        result = {}
        while i < n and lines[i][0] == map_indent and not lines[i][1].startswith("- "):
            key, rest = _split_key_value(lines[i][1])
            if key is None:
                raise ValueError("unparsable yaml line: %s" % lines[i][1])
            if rest != "":
                result[key] = _parse_scalar(rest)
                i += 1
            elif i + 1 < n and lines[i + 1][0] > map_indent:
                nxt_indent, nxt = lines[i + 1]
                if nxt.startswith("- "):
                    child, i = parse_list(i + 1, nxt_indent)
                    result[key] = child
                else:
                    child, i = parse_map(i + 1, nxt_indent)
                    result[key] = child
            else:
                result[key] = None
                i += 1
        return result, i

    if n == 0:
        return {}
    obj, _ = parse_map(0, lines[0][0])
    return obj


def _load_yaml(text):
    try:
        import yaml
    except ImportError:
        return _minimal_yaml_load(text)
    return yaml.safe_load(text)


def load_profiles(profiles_dir):
    """Parse YAML profiles in *profiles_dir* keyed by filename stem.

    Refuses any profile with an authority flag other than literal False
    or a non-null identity id at any depth.
    """
    directory = Path(profiles_dir)
    out = {}
    files = sorted(
        p
        for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in (".yml", ".yaml")
    )
    for path in files:
        payload = _load_yaml(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(_REFUSE_MSG)
        auth = payload.get("authority")
        if isinstance(auth, dict):
            payload["authority"] = AuthorityMap(auth)
        else:
            payload["authority"] = AuthorityMap()
        check_profile(payload)
        out[path.stem] = payload
    return out


def _is_defined_number(x):
    if x is None:
        return False
    try:
        f = float(x)
    except (TypeError, ValueError):
        return False
    return math.isfinite(f)


def _is_bad_close(x):
    """True when a close cannot form a simple return (None/non-finite/<=0)."""
    if not _is_defined_number(x):
        return True
    return float(x) <= 0.0


def _looks_dated(closes):
    if not closes:
        return False
    first = closes[0]
    return (
        isinstance(first, (tuple, list))
        and len(first) == 2
        and isinstance(first[0], str)
    )


def _check_sorted_unique_dates(dates):
    prev = None
    seen = set()
    for d in dates:
        if not isinstance(d, str) or d == "":
            raise ValueError("close dates must be ISO date strings")
        if d in seen:
            raise ValueError("duplicate close dates")
        seen.add(d)
        if prev is not None and d <= prev:
            raise ValueError("close dates must be strictly sorted")
        prev = d


def _simple_return_values(closes):
    """Simple returns from a close-value series.

    A None, non-finite, or <=0 close yields None for the returns that
    touch it (the interval ending on that close and the interval starting
    from it). The slot stays in the series; the next finite positive close
    does not bridge across the gap. Never returns NaN or a float derived
    from a non-positive price.
    """
    out = []
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        cur = closes[i]
        if _is_bad_close(prev) or _is_bad_close(cur):
            out.append(None)
            continue
        out.append(float(cur) / float(prev) - 1.0)
    return out


def simple_returns(closes):
    """Simple returns from a close series: r_t = close_t / close_{t-1} - 1.

    Dated input: an ordered list of (date_iso_str, close) pairs. Returns an
    ordered list of (end_date, return_or_none) pairs — one per interval
    between consecutive rows of that series. Unsorted or duplicate dates
    raise ValueError.

    Undated input: a list of close values. Returns a list of return_or_none
    in the same positional order.

    A missing/non-finite/<=0 close abstains (None) for the returns that
    touch it; it does not raise and it does not bridge the gap.
    """
    if not closes:
        return []
    if _looks_dated(closes):
        dates = [row[0] for row in closes]
        values = [row[1] for row in closes]
        _check_sorted_unique_dates(dates)
        rets = _simple_return_values(values)
        return [(dates[i + 1], rets[i]) for i in range(len(rets))]
    return _simple_return_values(closes)


def _mean(xs):
    return sum(xs) / float(len(xs))


def _beta(stock_win, bench_win):
    mb = _mean(bench_win)
    ms = _mean(stock_win)
    var_b = sum((b - mb) ** 2 for b in bench_win)
    if var_b == 0.0:
        return None
    cov = sum((s - ms) * (b - mb) for s, b in zip(stock_win, bench_win))
    return cov / var_b


def _window_defined(seq):
    return all(_is_defined_number(x) for x in seq)


def rolling_beta_residual(stock_ret, bench_ret, *, window=63):
    """Contemporaneous residual with beta from the trailing window ending at t-1.

    For t >= window, beta uses stock_ret/bench_ret over [t-window, t-1]
    (strictly before t — no look-ahead). residual_t = r_t - beta * b_t.
    Earlier entries are None. Zero benchmark variance abstains (None).
    Non-finite inputs abstain (None); NaN never appears in the output.
    """
    if len(stock_ret) != len(bench_ret):
        raise ValueError("stock_ret and bench_ret length mismatch")
    n = len(stock_ret)
    out = [None] * n
    if window <= 0:
        raise ValueError("window must be positive")
    for t in range(window, n):
        s_win = stock_ret[t - window : t]
        b_win = bench_ret[t - window : t]
        if not _window_defined(s_win) or not _window_defined(b_win):
            continue
        beta = _beta(s_win, b_win)
        if beta is None or not _is_defined_number(beta):
            continue
        r_t = stock_ret[t]
        b_t = bench_ret[t]
        if not _is_defined_number(r_t) or not _is_defined_number(b_t):
            continue
        resid = float(r_t) - float(beta) * float(b_t)
        if not math.isfinite(resid):
            continue
        out[t] = resid
    return out


def hist_vol_normalize(series, *, window=63):
    """Divide each point by the trailing (t-1) stdev over *window*.

    None where the window is undefined, shorter than window, or stdev == 0.
    Stdev is population (n in the divisor) of the trailing window, not
    including time t. Non-finite inputs abstain; NaN never appears in output.
    """
    n = len(series)
    out = [None] * n
    if window <= 0:
        raise ValueError("window must be positive")
    for t in range(window, n):
        win = series[t - window : t]
        if not _window_defined(win) or not _is_defined_number(series[t]):
            continue
        m = _mean(win)
        var = sum((x - m) ** 2 for x in win) / float(window)
        stdev = math.sqrt(var)
        if stdev == 0.0 or not math.isfinite(stdev):
            out[t] = None
        else:
            val = float(series[t]) / stdev
            out[t] = val if math.isfinite(val) else None
    return out


def _summary(values, dates=None):
    """Descriptive stats of defined finite values. Never reports NaN.

    None and non-finite entries are excluded. When *dates* is aligned with
    *values*, first_date/last_date are the dates of the first and last
    defined finite values (normalized residuals in the stress table).
    """
    xs = []
    defined_dates = []
    for i, x in enumerate(values):
        if not _is_defined_number(x):
            continue
        xs.append(float(x))
        if dates is not None:
            defined_dates.append(dates[i])
    n = len(xs)
    if n == 0:
        return {
            "n": 0,
            "mean": None,
            "stdev": None,
            "min": None,
            "max": None,
            "last": None,
            "first_date": None,
            "last_date": None,
        }
    mean = _mean(xs)
    if n > 1:
        var = sum((x - mean) ** 2 for x in xs) / float(n - 1)
        stdev = math.sqrt(var)
        if not math.isfinite(stdev):
            stdev = None
    else:
        stdev = None
    first_date = defined_dates[0] if defined_dates else None
    last_date = defined_dates[-1] if defined_dates else None
    return {
        "n": n,
        "mean": mean,
        "stdev": stdev,
        "min": min(xs),
        "max": max(xs),
        "last": xs[-1],
        "first_date": first_date,
        "last_date": last_date,
    }


def _empty_summary():
    stats = _summary([])
    stats["n_shared_dates"] = 0
    return stats


def _benchmarks_of(profile):
    stress = profile.get("stress_set") or {}
    benches = list(stress.get("benchmarks") or [])
    sector = stress.get("sector_etf")
    if sector is not None and sector not in benches:
        benches.append(sector)
    return benches


def _inner_join_returns(stock_rets, bench_rets):
    """Inner-join dated returns on end date. Returns (dates, stock, bench)."""
    stock_map = dict(stock_rets)
    bench_map = dict(bench_rets)
    shared = sorted(set(stock_map) & set(bench_map))
    return (
        shared,
        [stock_map[d] for d in shared],
        [bench_map[d] for d in shared],
    )


def stress_table(profiles, closes_by_ticker, *, window=63):
    """Normalized-residual summaries per (profile ticker, benchmark).

    Closes are ordered (date_iso, close) pairs. Returns are formed between
    consecutive rows of each series, then inner-joined on the return end
    date before beta/residual. Undated close lists are accepted only when
    both legs have the same length (caller already aligned them).

    Descriptive only. The returned dict carries authority_flags (all false),
    descriptive_only True, window, and causal_claims "none". Each per-
    benchmark summary includes first_date, last_date (of defined normalized
    residuals) and n_shared_dates (inner-join size).
    """
    check_profiles(profiles)
    summaries = {}
    for ticker, profile in profiles.items():
        check_profile(profile)
        stock_closes = (closes_by_ticker or {}).get(ticker)
        per_bench = {}
        if stock_closes is None:
            for bench in _benchmarks_of(profile):
                per_bench[bench] = _empty_summary()
            summaries[ticker] = per_bench
            continue
        stock_dated = _looks_dated(stock_closes)
        stock_rets = simple_returns(stock_closes)
        for bench in _benchmarks_of(profile):
            bench_closes = (closes_by_ticker or {}).get(bench)
            if bench_closes is None:
                per_bench[bench] = _empty_summary()
                continue
            bench_dated = _looks_dated(bench_closes)
            if stock_dated != bench_dated:
                raise ValueError("stock and benchmark closes must both be dated or both undated")
            if stock_dated:
                bench_rets = simple_returns(bench_closes)
                dates, stock_al, bench_al = _inner_join_returns(stock_rets, bench_rets)
            else:
                bench_rets = simple_returns(bench_closes)
                if len(stock_rets) != len(bench_rets):
                    raise ValueError(
                        "undated close series lengths differ; supply calendar dates"
                    )
                dates = None
                stock_al = stock_rets
                bench_al = bench_rets
            resid = rolling_beta_residual(stock_al, bench_al, window=window)
            normed = hist_vol_normalize(resid, window=window)
            stats = _summary(normed, dates=dates)
            stats["n_shared_dates"] = len(stock_al)
            per_bench[bench] = stats
        summaries[ticker] = per_bench
    return {
        "descriptive_only": True,
        "causal_claims": "none",
        "window": window,
        "authority_flags": dict(authority_flags()),
        "summaries": summaries,
    }


def _iso_date_from_value(value, pd):
    try:
        ts = pd.Timestamp(value)
    except Exception:
        return None
    if pd.isna(ts):
        return None
    return ts.strftime("%Y-%m-%d")


def _dates_from_frame(df, pd):
    """ISO dates from a DatetimeIndex, else a date/Date column. Else None.

    Never fabricates dates. Returns None when neither a datetime index nor
    a date/Date column exists.
    """
    idx = df.index
    datetime_index = isinstance(idx, pd.DatetimeIndex)
    if not datetime_index:
        try:
            datetime_index = pd.api.types.is_datetime64_any_dtype(idx)
        except Exception:
            datetime_index = False
    if datetime_index:
        out = []
        for v in idx:
            iso = _iso_date_from_value(v, pd)
            if iso is None:
                raise ValueError("parquet DatetimeIndex contains missing dates")
            out.append(iso)
        return out
    for col_name in ("date", "Date"):
        if col_name not in df.columns:
            continue
        out = []
        try:
            values = df[col_name].tolist()
        except Exception:
            return None
        for v in values:
            iso = _iso_date_from_value(v, pd)
            if iso is None:
                raise ValueError("parquet date column contains missing dates")
            out.append(iso)
        return out
    return None


def _close_or_none(v):
    if v is None:
        return None
    try:
        fv = float(v)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(fv):
        return None
    return fv


def load_closes_from_parquet(path):
    """Load dated closes from parquet. Return None if unavailable.

    Uses pandas if importable (imported here, not at module import). Returns
    an ordered list of (date_iso_str, close_or_none) pairs taken from the
    parquet's DatetimeIndex, or from a date/Date column when the index is
    not datetime. Returns None (never fabricates dates) when pandas is
    missing, the file does not exist, the file cannot be read as closes, or
    neither a datetime index nor a date/Date column exists.

    Missing/non-finite/unparsable closes stay in the series as None on that
    date so returns that touch the date abstain; they are not dropped, so
    the next finite close cannot silently span the gap. Unsorted or
    duplicate dates raise ValueError.
    """
    try:
        import pandas as pd
    except ImportError:
        return None
    if pd is None:
        return None
    p = Path(path)
    if not p.is_file():
        return None
    try:
        df = pd.read_parquet(p)
    except Exception:
        return None
    col = None
    for name in ("close", "Close", "adj_close", "Adj Close", "close_price"):
        if name in df.columns:
            col = df[name]
            break
    if col is None:
        return None
    dates = _dates_from_frame(df, pd)
    if dates is None:
        return None
    try:
        values = col.tolist()
    except Exception:
        return None
    if len(values) != len(dates):
        return None
    if not dates:
        return None
    _check_sorted_unique_dates(dates)
    out = [(d, _close_or_none(v)) for d, v in zip(dates, values)]
    return out


def _parquet_path_for(profile, ticker, data_dir):
    census = ((profile or {}).get("observation") or {}).get("census") or {}
    rel = census.get("yahoo_parquet_path")
    data_dir = Path(data_dir)
    if rel:
        return data_dir / Path(rel).name
    return data_dir / ("%s.parquet" % ticker)


def _load_closes_map(profiles, data_dir):
    closes = {}
    needed = set(profiles)
    for profile in profiles.values():
        needed.update(_benchmarks_of(profile))
    for ticker, profile in profiles.items():
        path = _parquet_path_for(profile, ticker, data_dir)
        series = load_closes_from_parquet(path)
        if series is not None:
            closes[ticker] = series
    for name in needed:
        if name in closes:
            continue
        series = load_closes_from_parquet(Path(data_dir) / ("%s.parquet" % name))
        if series is not None:
            closes[name] = series
    return closes


def _write_absent_report(out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    body = (
        "# SNI US stress set report\n\n"
        "data absent in this checkout; no statistics computed\n\n"
        "descriptive_only: true\n"
        "causal_claims: none\n"
        "authority flags: all false\n"
    )
    (out_dir / "STRESS_SET_REPORT.md").write_text(body, encoding="utf-8")
    payload = {
        "descriptive_only": True,
        "causal_claims": "none",
        "data_absent": True,
        "authority_flags": dict(authority_flags()),
        "note": "data absent in this checkout; no statistics computed",
    }
    (out_dir / "STRESS_SET.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def _write_table_report(out_dir, table, data_absent=False):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = dict(table)
    payload["data_absent"] = data_absent
    (out_dir / "STRESS_SET.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# SNI US stress set report",
        "",
        "descriptive_only: true",
        "causal_claims: none",
        "authority flags: all false",
        "window: %s" % table.get("window"),
        "",
        "Residuals are descriptive contemporaneous leftovers after a trailing",
        "beta. They are not causal and they are not a news-impact claim.",
        "Stock and benchmark returns are inner-joined on calendar date.",
        "",
    ]
    summaries = table.get("summaries") or {}
    for ticker in sorted(summaries):
        lines.append("## %s" % ticker)
        for bench, stats in summaries[ticker].items():
            lines.append(
                "- %s: n=%s mean=%s stdev=%s min=%s max=%s last=%s "
                "first_date=%s last_date=%s n_shared_dates=%s"
                % (
                    bench,
                    stats.get("n"),
                    stats.get("mean"),
                    stats.get("stdev"),
                    stats.get("min"),
                    stats.get("max"),
                    stats.get("last"),
                    stats.get("first_date"),
                    stats.get("last_date"),
                    stats.get("n_shared_dates"),
                )
            )
        lines.append("")
    (out_dir / "STRESS_SET_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "SNI US stress set: descriptive residual summaries. "
            "Not a signal, rank, gate, or forecast."
        )
    )
    parser.add_argument("--profiles-dir", required=True)
    parser.add_argument("--data-dir", default="data/yahoo")
    parser.add_argument("--out", required=True)
    parser.add_argument("--window", type=int, default=63)
    args = parser.parse_args(argv)
    profiles = load_profiles(args.profiles_dir)
    closes = _load_closes_map(profiles, args.data_dir)
    stock_loaded = any(name in closes for name in profiles)
    if not stock_loaded:
        _write_absent_report(args.out)
        return 0
    table = stress_table(profiles, closes, window=args.window)
    _write_table_report(args.out, table, data_absent=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
