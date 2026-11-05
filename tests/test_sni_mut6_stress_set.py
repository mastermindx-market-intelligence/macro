"""MUT6G killing tests for stress_set.py (SNI US-stress YAML fallback and CLI).

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) and never mint, derive, or guess issuer
or security identifiers. HISTORICAL-DESCRIPTIVE only: rank_authority,
gate_authority, size_authority, signal_authority, escalation_authority and
trade_authority stay false. Fixtures are synthetic. Residuals are
descriptive, never causal, never a news-impact claim.

Each test_m6g_stress_set_<function>_<n> docstring names one non-equivalent
mutant that survived the MUT6G importer suite (file:line, original -> mutated).
The harness applied text-level mutations to a fresh copy of the module
under test, ran the existing importer suite, and listed every non-equivalent
survivor. This file adds one targeted assertion per survivor that the
harness could kill.

Some survivors (`*STILL_PASS*` in the review) were re-applied with the
same text-level patcher and these new tests did not detect a behavior
difference on the chosen input. Those mutants are documented in the
review as "STILL_PASS / unkillable by a single-input test" and removed
from this file to keep the test suite clean.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(
    0,
    str(ROOT / "research" / "single_name_intelligence" / "us_stress"),
)

import stress_set as ss  # noqa: E402
from stress_set import (  # noqa: E402
    _minimal_yaml_load,
    _parse_scalar,
    _split_key_value,
    _strip_inline_comment,
    stress_table,
)


SYN_NAME = "SyntheticAlpha"


def _auth():
    return {n: False for n in (
        "rank_authority", "gate_authority", "size_authority",
        "signal_authority", "escalation_authority", "trade_authority",
    )}


# ---------------------------------------------------------------------------
# 01 — const_stress_table_925_24 — L925 col 24: `n_zero > 0` -> `n_zero > 1`
# ---------------------------------------------------------------------------
def test_m6g_stress_set_stress_table_01():
    """stress_set.py:925, `n_zero > 0` -> `n_zero > 1`. The unmutated
    branch sets `n_zero_variance_skipped` for any n_zero >= 1; the
    mutation skips the assignment when n_zero is exactly 1. We
    construct an inner-join run where exactly one trailing window has
    var_b = 0, so the unmutated code adds the meta line and the mutated
    code does not."""
    import datetime as _dt
    # First 63 returns are 0.0; the rest alternate to keep var_b > 0 in
    # every 63-wide trailing window starting at t=64 or later.
    n_returns = 130
    bench_returns = [0.0] * 63 + [0.001] + [0.001 * ((-1) ** i) for i in range(66)]
    # Stock returns: same shape with non-zero variance.
    stock_returns = [0.0] * 63 + [0.002] + [0.002 * ((-1) ** i) for i in range(66)]
    n_zero = ss._zero_variance_skip_count(stock_returns, bench_returns, 63)
    assert n_zero == 1, n_zero
    # Now wire the same into a stress_table run that produces the meta
    # line. Build dated closes whose inner-join yields the same
    # return series.
    n = n_returns + 1
    base = _dt.date(2020, 1, 1)
    dates = [(base + _dt.timedelta(days=i)).isoformat() for i in range(n)]
    stock_prices = [100.0]
    for r in stock_returns:
        stock_prices.append(stock_prices[-1] * (1.0 + r))
    bench_prices = [100.0]
    for r in bench_returns:
        bench_prices.append(bench_prices[-1] * (1.0 + r))
    profiles = {
        "TME": {
            "ticker": "TME",
            "display_name": SYN_NAME,
            "canonical_issuer_id": None,
            "issuer_link": "UNRESOLVED",
            "authority": _auth(),
            "stress_set": {"benchmarks": ["SPY"]},
        }
    }
    closes = {
        "TME": list(zip(dates, stock_prices)),
        "SPY": list(zip(dates, bench_prices)),
    }
    table = stress_table(profiles, closes, window=63, join_policy="inner")
    bench_stats = table["summaries"]["TME"]["SPY"]
    # The unmutated branch sets n_zero_variance_skipped = 1.
    # The mutation `> 1` is False, so the field is missing.
    assert bench_stats.get("n_zero_variance_skipped", 0) == 1, bench_stats


# ---------------------------------------------------------------------------
# 02 — const__parse_scalar_259_17 — L259 col 17: `len(s) >= 2` -> `>= 3`
# ---------------------------------------------------------------------------
def test_m6g_stress_set__parse_scalar_02():
    """stress_set.py:259, `len(s) >= 2` -> `>= 3`. A two-character
    quoted scalar like `\"\"` (an empty quoted string) is no longer
    recognized as a quoted string and falls through to `return s`
    (returns the raw 2-char string)."""
    out = _parse_scalar('""')
    assert out == "", out
    assert isinstance(out, str)
    assert len(out) == 0


# ---------------------------------------------------------------------------
# 03 — const__minimal_yaml_load_345_21 — L345 col 21
# ---------------------------------------------------------------------------
def test_m6g_stress_set__minimal_yaml_load_03():
    """stress_set.py:345, a constant in `elif i + 1 < n and lines[i + 1]`
    is incremented by 1, so the inline-child map parser targets the
    next-next line and the value of the inner child is dropped."""
    text = "outer:\n  inner:\n    a: 1\n    b: 2\n"
    out = _minimal_yaml_load(text)
    assert out == {"outer": {"inner": {"a": 1, "b": 2}}}, out


# ---------------------------------------------------------------------------
# 05 — bool__split_key_value_279 — L279: `and` -> `or`
# ---------------------------------------------------------------------------
def test_m6g_stress_set__split_key_value_05():
    """stress_set.py:279, `ch == \":\" and not in_single and not in_double`
    -> `or`. A key/value split is now triggered for any character (because
    `not in_double` is True on the first iteration), so a key with a
    colon mid-line is mangled."""
    k, v = _split_key_value("name: Alice")
    assert k == "name", (k, v)
    assert v == "Alice", (k, v)


# ---------------------------------------------------------------------------
# 06 — const__minimal_yaml_load_307_43 — L307 col 43
# ---------------------------------------------------------------------------
def test_m6g_stress_set__minimal_yaml_load_06():
    """stress_set.py:307, `lines[i + 1][0]` -> `lines[i + 2][0]`. The
    list-of-map parser mis-targets the indent of the next-next line, so
    a nested dash child whose value spans one indented line is dropped."""
    text = "outer:\n  - a: 1\n    b: 2\n"
    out = _minimal_yaml_load(text)
    assert out == {"outer": [{"a": 1, "b": 2}]}, out


# ---------------------------------------------------------------------------
# 07 — bool__strip_inline_comment_246 — L246: second `and` -> `or`
# ---------------------------------------------------------------------------
def test_m6g_stress_set__strip_inline_comment_07():
    """stress_set.py:246, `ch == \"#\" and not in_single and not in_double`
    -> `or` (the second `and`). The comment-strip branch now fires for
    any char when `in_double` is False (i.e. always on the first half of
    an unquoted line), so a line like `key: val # comment` is cut at the
    first space after `val` rather than at the `#`."""
    out = _strip_inline_comment("key: value # trailing")
    assert out == "key: value", out


# ---------------------------------------------------------------------------
# 08 — ret__parse_scalar_264 — L264: `return float(s)` -> `return None`
# ---------------------------------------------------------------------------
def test_m6g_stress_set__parse_scalar_08():
    """stress_set.py:264, `return float(s)` -> `return None`. A scalar
    that contains `.` or `e`/`E` no longer parses as a float and the
    function returns None."""
    assert _parse_scalar("1.5") == 1.5
    assert _parse_scalar("1e3") == 1000.0
    assert isinstance(_parse_scalar("1.5"), float)


# ---------------------------------------------------------------------------
# 09 — arith__minimal_yaml_load_307 — L307: `+` -> `-`
# ---------------------------------------------------------------------------
def test_m6g_stress_set__minimal_yaml_load_09():
    """stress_set.py:307, `i + 1` -> `i - 1`. The list-of-map parser
    regresses its cursor; the resulting parse differs from unmutated
    bytes on multi-line key lists."""
    text = "items:\n  - name: alpha\n    val: 1\n  - name: beta\n    val: 2\n"
    out = _minimal_yaml_load(text)
    assert out == {
        "items": [
            {"name": "alpha", "val": 1},
            {"name": "beta", "val": 2},
        ],
    }, out


# ---------------------------------------------------------------------------
# 10 — ret__parse_scalar_268 — L268: `return s` -> `return None`
# ---------------------------------------------------------------------------
def test_m6g_stress_set__parse_scalar_10():
    """stress_set.py:268, the final `return s` -> `return None`. A scalar
    that does not match any recognised form (e.g. a name token) no
    longer returns the string but returns None."""
    assert _parse_scalar("hello") == "hello"


# ---------------------------------------------------------------------------
# 11 — ret__split_key_value_281 — L281: `return None, content` -> `return None`
# ---------------------------------------------------------------------------
def test_m6g_stress_set__split_key_value_11():
    """stress_set.py:281, `return None, content` -> `return None`. The
    not-split branch now returns a bare None instead of the
    `(None, content)` tuple that the caller expects."""
    k, v = _split_key_value("nocolonhere")
    assert k is None, (k, v)
    assert v == "nocolonhere", (k, v)


# ---------------------------------------------------------------------------
# 12 — const_stress_table_823_55 — L823 col 55: `window=63` -> `window=64`
# ---------------------------------------------------------------------------
def test_m6g_stress_set_stress_table_12():
    """stress_set.py:823, the default `window=63` is perturbed to
    `window=64`. The returned `table['window']` carries the changed
    default unless the caller overrides it."""
    profiles = {
        "TME": {
            "ticker": "TME",
            "display_name": SYN_NAME,
            "canonical_issuer_id": None,
            "issuer_link": "UNRESOLVED",
            "authority": _auth(),
        }
    }
    table = stress_table(profiles, {})
    assert table["window"] == 63, table


# ---------------------------------------------------------------------------
# 13 — cmp__minimal_yaml_load_322_0 — L322: `!=` -> `==`
# ---------------------------------------------------------------------------
def test_m6g_stress_set__minimal_yaml_load_13():
    """stress_set.py:322, `if rest != \"\":` -> `==`. The map parser
    inverts which key/value lines carry inline scalars, so a value
    on the same line as the dash is dropped."""
    text = "list:\n  - a: 1\n  - b: 2\n"
    out = _minimal_yaml_load(text)
    assert out == {"list": [{"a": 1}, {"b": 2}]}, out


# ---------------------------------------------------------------------------
# 14 — arith__minimal_yaml_load_346 — L346: `+` -> `-`
# ---------------------------------------------------------------------------
def test_m6g_stress_set__minimal_yaml_load_14():
    """stress_set.py:346, `lines[i + 1]` -> `lines[i - 1]`. The map
    parser looks at the previous line instead of the next; nested
    child values are mis-attributed or missing."""
    text = "outer:\n  child:\n    a: 1\n    b: 2\n"
    out = _minimal_yaml_load(text)
    assert out == {"outer": {"child": {"a": 1, "b": 2}}}, out


# ---------------------------------------------------------------------------
# 15 — bool__parquet_path_for_1053 — L1053: `or` -> `and`
# ---------------------------------------------------------------------------
def test_m6g_stress_set__parquet_path_for_15(tmp_path):
    """stress_set.py:1053, `(profile or {}).get(\"observation\") or {}`
    -> `and`. When `profile` is None, `None and {}.get(...)` short-
    circuits to None, then `.get('census')` raises AttributeError. The
    unmutated path returns the default `<ticker>.parquet`."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    out = ss._parquet_path_for(None, "TME", data_dir)
    assert out == data_dir / "TME.parquet", out


# ---------------------------------------------------------------------------
# 16 — const__minimal_yaml_load_345_44 — L345 col 44
# ---------------------------------------------------------------------------
def test_m6g_stress_set__minimal_yaml_load_16():
    """stress_set.py:345, an int in `lines[i + 1]` is incremented by 1.
    The map parser targets the next-next line's indent, so a nested
    child key on the very next line is treated as a sibling."""
    text = "outer:\n  child:\n    a: 1\n    b: 2\n"
    out = _minimal_yaml_load(text)
    assert out == {"outer": {"child": {"a": 1, "b": 2}}}, out
