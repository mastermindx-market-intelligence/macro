"""test_sni_us_stress_onboarding.py — synthetic A36/A37 onboarding proof.

SNI-local DRAFT contract consumer. This file exercises
research/single_name_intelligence/us_stress/stress_set.py with synthetic
closes and synthetic YAML profiles only. It does not mint issuer or
security identifiers, does not read data/yahoo, and does not feed a rank,
gate, size, signal, escalation, or trade path. Every authority flag in
every fixture stays false; the module under test raises if a caller sets
one true. Residuals are descriptive. An unestimable then-known window
abstains with a named reason.

Fixtures are synthetic. No real-company skill is claimed.
"""
from __future__ import annotations

import ast
import copy
import datetime
import random
import re
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/us_stress"),
)

from stress_set import (  # noqa: E402
    check_profile,
    check_profiles,
    load_profiles,
    stress_table,
)

ROOT = Path(__file__).resolve().parents[1]
PROFILES_DIR = ROOT / "research/single_name_intelligence/us_stress/profiles"
MODULE_PATH = ROOT / "research/single_name_intelligence/us_stress/stress_set.py"

COMMITTED_TICKERS = ("AAPL", "AMZN", "GOOGL", "META", "MSFT", "NVDA", "TSLA")
FORBIDDEN_TICKER_TOKENS = COMMITTED_TICKERS + ("SPY", "QQQ")
XL_ETF_TOKEN = re.compile(r"^XL[A-Z]{1,2}$")
WHOLE_TOKEN = re.compile(r"[A-Za-z0-9]+")

WINDOW = 63
SYNTH_SEED = 20261013
SYNTH_START = datetime.date(2018, 1, 2)
SYNTH_N = 400
PINNED_TICKER_NOT_THEN_KNOWN = "TICKER_NOT_THEN_KNOWN"

FLAGS = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)


def _docstring_constant_ids(tree):
    ids = set()
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            continue
        if not node.body:
            continue
        first = node.body[0]
        if not isinstance(first, ast.Expr):
            continue
        val = first.value
        if isinstance(val, ast.Constant) and isinstance(val.value, str):
            ids.add(id(val))
    return ids


def _ticker_hits_in_string(value):
    """Return forbidden whole tokens found in *value* (exact or tokenized)."""
    found = []
    seen = set()
    candidates = [value]
    candidates.extend(WHOLE_TOKEN.findall(value))
    for tok in candidates:
        if tok in seen:
            continue
        if tok in FORBIDDEN_TICKER_TOKENS or XL_ETF_TOKEN.match(tok):
            seen.add(tok)
            found.append(tok)
    return found


def scan_ticker_string_literals(source):
    """AST-scan *source* for forbidden ticker literals outside docstrings.

    Comments are absent from the AST and are therefore excluded. Module,
    function, and class docstrings (first-statement string Expr) are
    excluded. Every other ast.Constant str is checked as a whole token.
    """
    tree = ast.parse(source)
    skip = _docstring_constant_ids(tree)
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in skip:
            continue
        for token in _ticker_hits_in_string(node.value):
            hits.append(
                {
                    "lineno": getattr(node, "lineno", None),
                    "value": node.value,
                    "token": token,
                }
            )
    return hits


def _geom_walk_closes(
    rng, n=SYNTH_N, sigma=0.01, start_px=100.0, start_date=SYNTH_START
):
    px = start_px
    vals = [px]
    for _ in range(n - 1):
        px *= 1.0 + rng.gauss(0.0, sigma)
        if px <= 0.0:
            px = start_px
        vals.append(px)
    dates = []
    d = start_date
    while len(dates) < n:
        if d.weekday() < 5:
            dates.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return list(zip(dates, vals))


def _synth_closes_for(names, seed=SYNTH_SEED):
    rng = random.Random(seed)
    return {name: _geom_walk_closes(rng) for name in sorted(names)}


def _synthetic_profile_yaml(
    *,
    issuer_key,
    display_name,
    ticker,
    sector_etf="XLK",
    ticker_valid_from="2015-01-02",
    trade_authority="false",
    security_id="null",
):
    return """\
# Synthetic test fixture. Not a real issuer. data_read is false.
schema_version: coverage_profile.v1
as_of: "2026-10-12"
profile_kind: qualification_facts
cohort_selection:
  rule: "largest-seven US market cap as of 2026-10-12"
  hindsight: true
  survivorship: true
  representative_sample: false
  transfer_evidence: false
issuer_key: {issuer_key}
display_name: {display_name}
canonical_issuer_id: null
canonical_issuer_id_owner: stock_identity
canonical_issuer_id_scope: "NOT CONSULTED IN THIS DRAFT — stress set only"
observation:
  repo_ref: synthetic-test-fixture
  data_read: false
  observed_at_utc: "2026-10-13T00:00:00Z"
  census:
    yahoo_parquet_path: null
    present_on_main: false
authority:
  rank_authority: false
  gate_authority: false
  size_authority: false
  signal_authority: false
  escalation_authority: false
  trade_authority: {trade_authority}
counters:
  {issuer_key}:
    label: NASDAQ {ticker}
    venue_mic: XNAS
    local_code: {ticker}
    currency: USD
    security_id: {security_id}
    security_id_owner: stock_identity
    issuer_link: UNRESOLVED
    issuer_link_owner: stock_identity
stress_set:
  benchmarks:
    - SPY
    - QQQ
  sector_etf: {sector_etf}
  descriptive_only: true
then_known:
  - field: ticker
    value: {ticker}
    valid_from: "{ticker_valid_from}"
    valid_to: null
    source: "synthetic test fixture"
    verified: false
  - field: listing
    value: NASDAQ
    valid_from: "2015-01-02"
    valid_to: null
    source: "synthetic test fixture"
    verified: false
  - field: share_class
    value: common
    valid_from: "2015-01-02"
    valid_to: null
    source: "synthetic test fixture"
    verified: false
  - field: sector_etf
    value: {sector_etf}
    valid_from: "2015-01-02"
    valid_to: null
    source: "synthetic test fixture"
    verified: false
""".format(
        issuer_key=issuer_key,
        display_name=display_name,
        ticker=ticker,
        sector_etf=sector_etf,
        ticker_valid_from=ticker_valid_from,
        trade_authority=trade_authority,
        security_id=security_id,
    )


def _write_zzzq(directory, **kwargs):
    params = dict(
        issuer_key="zzzq",
        display_name="Synthetic Held-Out Co (test fixture)",
        ticker="ZZZQ",
        sector_etf="XLK",
        ticker_valid_from="2015-01-02",
        trade_authority="false",
        security_id="null",
    )
    params.update(kwargs)
    path = Path(directory) / "ZZZQ.yml"
    path.write_text(_synthetic_profile_yaml(**params), encoding="utf-8")
    return path


def _write_zzzr(directory):
    path = Path(directory) / "ZZZR.yml"
    path.write_text(
        _synthetic_profile_yaml(
            issuer_key="zzzr",
            display_name="Synthetic Held-Out Co (test fixture)",
            ticker="ZZZR",
            sector_etf="XLK",
            ticker_valid_from="2024-06-03",
        ),
        encoding="utf-8",
    )
    return path


def _copy_committed_profiles(tmp_path):
    dst = tmp_path / "profiles"
    shutil.copytree(PROFILES_DIR, dst)
    return dst


def _numeric_fields(stats):
    return [stats.get(k) for k in ("mean", "stdev", "min", "max", "last")]


def test_onb_01_ast_no_ticker_literals():
    control_src = 'TICKER = "NVDA"\n'
    control_hits = scan_ticker_string_literals(control_src)
    assert control_hits, "positive control must report TICKER = \"NVDA\""
    assert any(hit["token"] == "NVDA" and hit["value"] == "NVDA" for hit in control_hits)

    docstring_src = (
        '"""Module docstring names NVDA SPY QQQ XLK AAPL."""\n'
        "def helper():\n"
        '    """Function docstring AMZN META."""\n'
        "    return 1\n"
        "class Holder:\n"
        '    """Class docstring MSFT GOOGL TSLA."""\n'
        "    pass\n"
        'OK = "no ticker here"\n'
    )
    assert scan_ticker_string_literals(docstring_src) == []

    source = MODULE_PATH.read_text(encoding="utf-8")
    hits = scan_ticker_string_literals(source)
    assert hits == [], "stress_set.py ticker-literal AST hits: %r" % hits


def test_onb_02_eighth_profile_onboards_without_code_change(tmp_path):
    seven_dir = _copy_committed_profiles(tmp_path / "seven")
    eight_dir = _copy_committed_profiles(tmp_path / "eight")
    _write_zzzq(eight_dir)

    names = set(COMMITTED_TICKERS) | {"ZZZQ", "SPY", "QQQ", "XLK"}
    closes = _synth_closes_for(names)

    seven = load_profiles(seven_dir)
    assert len(seven) == 7
    assert set(seven) == set(COMMITTED_TICKERS)
    check_profiles(seven)
    table_seven = stress_table(seven, closes, window=WINDOW)

    eight = load_profiles(eight_dir)
    assert len(eight) == 8
    assert "ZZZQ" in eight
    assert eight["ZZZQ"]["issuer_key"] == "zzzq"
    assert eight["ZZZQ"]["display_name"] == "Synthetic Held-Out Co (test fixture)"
    assert eight["ZZZQ"]["canonical_issuer_id"] is None
    for flag in FLAGS:
        assert eight["ZZZQ"]["authority"][flag] is False
    check_profiles(eight)
    table_eight = stress_table(eight, closes, window=WINDOW)

    assert "ZZZQ" in table_eight["summaries"]
    zzzq_row = table_eight["summaries"]["ZZZQ"]
    assert set(zzzq_row) >= {"SPY", "QQQ", "XLK"}
    for bench, stats in zzzq_row.items():
        assert stats["n"] > 0, bench
        assert stats["mean"] is not None, bench
        assert stats["stdev"] is not None, bench
        assert stats.get("reason") is None
        for val in _numeric_fields(stats):
            assert val is not None

    restricted_seven = {k: table_seven["summaries"][k] for k in COMMITTED_TICKERS}
    restricted_eight = {k: table_eight["summaries"][k] for k in COMMITTED_TICKERS}
    assert restricted_eight == restricted_seven
    for key in ("descriptive_only", "causal_claims", "window", "authority_flags"):
        assert table_eight[key] == table_seven[key]


def test_onb_03_then_known_ticker_after_window_abstains(tmp_path):
    dst = tmp_path / "profiles"
    dst.mkdir()
    _write_zzzr(dst)
    loaded = load_profiles(dst)
    assert "ZZZR" in loaded
    assert loaded["ZZZR"]["issuer_key"] == "zzzr"
    check_profiles(loaded)
    closes = _synth_closes_for({"ZZZR", "SPY", "QQQ", "XLK"})
    table = stress_table(loaded, closes, window=WINDOW)
    row = table["summaries"]["ZZZR"]
    assert row
    observed_reasons = []
    for bench, stats in row.items():
        reason = stats["reason"]
        observed_reasons.append(reason)
        assert reason == PINNED_TICKER_NOT_THEN_KNOWN, bench
        assert stats["n"] == 0, bench
        assert stats["n_shared_dates"] == 0, bench
        for val in _numeric_fields(stats):
            assert val is None, (bench, val)
        assert stats["first_date"] is None
        assert stats["last_date"] is None
        assert stats.get("then_known_valid_from") == "2024-06-03"
    assert set(observed_reasons) == {PINNED_TICKER_NOT_THEN_KNOWN}


def test_onb_04_refusals_bind_for_onboarded_name(tmp_path):
    good_dir = tmp_path / "good"
    good_dir.mkdir()
    _write_zzzq(good_dir)
    good = load_profiles(good_dir)
    check_profiles(good)

    auth_dir = tmp_path / "auth"
    auth_dir.mkdir()
    _write_zzzq(auth_dir, trade_authority="true")
    with pytest.raises(ValueError) as auth_load:
        load_profiles(auth_dir)
    assert type(auth_load.value) is ValueError
    assert "trade_authority" in str(auth_load.value)

    mutated_auth = copy.deepcopy(dict(good["ZZZQ"]))
    mutated_auth["authority"] = dict(mutated_auth["authority"])
    mutated_auth["authority"]["trade_authority"] = True
    with pytest.raises(ValueError) as auth_check:
        check_profile(mutated_auth)
    assert type(auth_check.value) is ValueError
    assert "trade_authority" in str(auth_check.value)

    id_dir = tmp_path / "ident"
    id_dir.mkdir()
    _write_zzzq(id_dir, security_id='"SEC:US-XNAS-ZZZQ"')
    with pytest.raises(ValueError) as id_load:
        load_profiles(id_dir)
    assert type(id_load.value) is ValueError
    assert "security_id" in str(id_load.value)

    mutated_id = copy.deepcopy(dict(good["ZZZQ"]))
    mutated_id["authority"] = dict(mutated_id["authority"])
    counters = dict(mutated_id["counters"])
    counter = dict(next(iter(counters.values())))
    counter["security_id"] = "SEC:US-XNAS-ZZZQ"
    mutated_id["counters"] = {next(iter(counters)): counter}
    with pytest.raises(ValueError) as id_check:
        check_profile(mutated_id)
    assert type(id_check.value) is ValueError
    assert "security_id" in str(id_check.value)


def test_onb_05_stress_table_deterministic(tmp_path):
    dst = _copy_committed_profiles(tmp_path)
    _write_zzzq(dst)
    profiles = load_profiles(dst)
    check_profiles(profiles)
    names = set(profiles) | {"SPY", "QQQ", "XLK"}
    closes = _synth_closes_for(names)
    first = stress_table(profiles, closes, window=WINDOW)
    second = stress_table(profiles, closes, window=WINDOW)
    assert first == second
