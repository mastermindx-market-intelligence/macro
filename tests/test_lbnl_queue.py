"""tests/test_lbnl_queue.py — hermetic tests for the LBNL interconnection-queue
collector and the engine._queue_pull() contract it feeds.

Three mandatory positive-control assertions:

1.  Percent-units contract: synthetic {"total_gw_yoy": 20.0} written to a
    tmp config-rooted path -> power_scarcity._queue_pull() returns 1.0.
    (20.0 / 20.0 = 1.0, within the ±2.0 clamp.)

2.  Fraction-unit tripwire: a value of 0.20 (which would be wrong — the
    reader expects percent, not a fraction) yields 0.01.
    Documents WHY the percent contract matters: if the collector emitted a
    fraction instead of a percent the signal would be ~100x too small and
    silently meaningless (0.01 instead of ~1.0 z-score).

3.  Collector transform tests: verify compute_yoy() arithmetic on a
    synthetic annual table, including edge cases.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd
import pytest

from engine import power_scarcity as ps
from collectors.lbnl_queue import compute_yoy, _parse_annual_totals, _find_col


# ──────────────────────────────────────────────────────────────────────────────
# 1. POSITIVE-CONTROL: percent-units contract
#    synthetic {"total_gw_yoy": 20.0} → _queue_pull() == 1.0
# ──────────────────────────────────────────────────────────────────────────────

def test_queue_pull_percent_units_contract(monkeypatch, tmp_path):
    """MANDATORY positive-control: 20.0%/yr is the ~+1 z baseline per the engine
    contract (scales /20.0 → 1.0).  If this fails the reader or writer broke."""
    (tmp_path / "eia").mkdir(parents=True, exist_ok=True)
    (tmp_path / "eia" / "interconnection_queue.json").write_text(
        json.dumps({"total_gw_yoy": 20.0})
    )
    monkeypatch.setattr(ps.config, "data_dir", lambda: tmp_path)
    result = ps._queue_pull()
    assert result == 1.0, (
        f"Expected 1.0 (20.0 / 20.0), got {result!r}. "
        "Check that the collector emits PERCENT units (18.5 == +18.5%/yr), "
        "not fractions."
    )


# ──────────────────────────────────────────────────────────────────────────────
# 2. FRACTION-UNIT TRIPWIRE
#    0.20 (wrong: fraction instead of percent) → _queue_pull() == 0.01
#    Documents the consequence of emitting the wrong unit.
# ──────────────────────────────────────────────────────────────────────────────

def test_queue_pull_fraction_unit_tripwire(monkeypatch, tmp_path):
    """MANDATORY tripwire: demonstrates why percent units matter.

    If the collector emitted a fraction (0.20) instead of a percent (20.0),
    the engine would receive 0.20 / 20.0 = 0.01 — a near-zero z-score that
    would silently make the queue-buildout leg worthless even in a capacity
    boom. This test documents that contract in an executable form."""
    (tmp_path / "eia").mkdir(parents=True, exist_ok=True)
    (tmp_path / "eia" / "interconnection_queue.json").write_text(
        json.dumps({"total_gw_yoy": 0.20})
    )
    monkeypatch.setattr(ps.config, "data_dir", lambda: tmp_path)
    result = ps._queue_pull()
    assert result == 0.01, (
        f"Expected 0.01 (0.20 / 20.0) — this tripwire confirms that a "
        f"fraction value (0.20) is nearly useless after /20.0 scaling. "
        f"Got {result!r}."
    )


# ──────────────────────────────────────────────────────────────────────────────
# 3. CLAMP: values outside ±2.0 are clamped
# ──────────────────────────────────────────────────────────────────────────────

def test_queue_pull_clamp_positive(monkeypatch, tmp_path):
    """40%/yr -> clamped to +2.0 (confirmed by existing test_power_scarcity.py)."""
    (tmp_path / "eia").mkdir(parents=True, exist_ok=True)
    (tmp_path / "eia" / "interconnection_queue.json").write_text(
        json.dumps({"total_gw_yoy": 40.0})
    )
    monkeypatch.setattr(ps.config, "data_dir", lambda: tmp_path)
    assert ps._queue_pull() == 2.0


def test_queue_pull_clamp_negative(monkeypatch, tmp_path):
    """-50%/yr -> clamped to -2.0."""
    (tmp_path / "eia").mkdir(parents=True, exist_ok=True)
    (tmp_path / "eia" / "interconnection_queue.json").write_text(
        json.dumps({"total_gw_yoy": -50.0})
    )
    monkeypatch.setattr(ps.config, "data_dir", lambda: tmp_path)
    assert ps._queue_pull() == -2.0


# ──────────────────────────────────────────────────────────────────────────────
# 4. ABSENT CACHE → None (graceful degradation)
# ──────────────────────────────────────────────────────────────────────────────

def test_queue_pull_absent_json(monkeypatch, tmp_path):
    """No JSON file → None; engine continues without the queue-buildout leg."""
    monkeypatch.setattr(ps.config, "data_dir", lambda: tmp_path)
    assert ps._queue_pull() is None


def test_queue_pull_missing_key(monkeypatch, tmp_path):
    """JSON exists but lacks total_gw_yoy → None (extra keys are OK)."""
    (tmp_path / "eia").mkdir(parents=True, exist_ok=True)
    (tmp_path / "eia" / "interconnection_queue.json").write_text(
        json.dumps({"asof_year": 2023, "total_gw": 2600.0})  # no yoy key
    )
    monkeypatch.setattr(ps.config, "data_dir", lambda: tmp_path)
    assert ps._queue_pull() is None


def test_queue_pull_corrupt_json(monkeypatch, tmp_path):
    """Corrupt JSON → None; engine continues (network write mid-collect)."""
    (tmp_path / "eia").mkdir(parents=True, exist_ok=True)
    (tmp_path / "eia" / "interconnection_queue.json").write_text("NOT_JSON{{{")
    monkeypatch.setattr(ps.config, "data_dir", lambda: tmp_path)
    assert ps._queue_pull() is None


# ──────────────────────────────────────────────────────────────────────────────
# 5. COLLECTOR TRANSFORM: compute_yoy() arithmetic
# ──────────────────────────────────────────────────────────────────────────────

def _make_tbl(rows: list[tuple[int, float]]) -> pd.DataFrame:
    """Build a minimal (year, total_gw) table for compute_yoy testing."""
    years, gws = zip(*rows)
    return pd.DataFrame({"year": list(years), "total_gw": list(gws)})


def test_compute_yoy_basic():
    """Basic YoY: 1000 -> 1200 GW == +20.0%."""
    tbl = _make_tbl([(2022, 1000.0), (2023, 1200.0)])
    out = compute_yoy(tbl)
    assert out["total_gw_yoy"] == pytest.approx(20.0, abs=0.01)
    assert out["asof_year"] == 2023
    assert out["total_gw"] == pytest.approx(1200.0, abs=0.1)
    assert out["prior_year"] == 2022
    assert out["prior_gw"] == pytest.approx(1000.0, abs=0.1)


def test_compute_yoy_negative():
    """Declining queue: 1200 -> 900 GW == -25.0%."""
    tbl = _make_tbl([(2022, 1200.0), (2023, 900.0)])
    out = compute_yoy(tbl)
    assert out["total_gw_yoy"] == pytest.approx(-25.0, abs=0.01)


def test_compute_yoy_multi_year_uses_last_two():
    """With multiple years, only the last two are used for YoY."""
    tbl = _make_tbl([(2019, 800.0), (2020, 900.0), (2021, 950.0), (2022, 2000.0)])
    out = compute_yoy(tbl)
    # 950 -> 2000: +110.5%
    assert out["total_gw_yoy"] == pytest.approx(
        (2000.0 / 950.0 - 1.0) * 100.0, abs=0.01
    )
    assert out["asof_year"] == 2022


def test_compute_yoy_source_string():
    """source field names the as-of year."""
    tbl = _make_tbl([(2022, 1000.0), (2023, 1100.0)])
    out = compute_yoy(tbl)
    assert "2023" in out["source"]
    assert "LBNL" in out["source"]


def test_compute_yoy_collected_iso():
    """_collected is an ISO datetime string."""
    tbl = _make_tbl([(2022, 1000.0), (2023, 1100.0)])
    out = compute_yoy(tbl)
    # should parse without exception
    datetime.fromisoformat(out["_collected"].replace("Z", "+00:00"))


# ──────────────────────────────────────────────────────────────────────────────
# 6. _find_col: column lookup helper
# ──────────────────────────────────────────────────────────────────────────────

def test_find_col_exact():
    df = pd.DataFrame({"Year": [2023], "Total capacity (GW)": [1000.0]})
    assert _find_col(df, ("Year", "year")) == "Year"
    assert _find_col(df, ("Total capacity (GW)",)) == "Total capacity (GW)"


def test_find_col_case_insensitive():
    df = pd.DataFrame({"year": [2023], "gw": [1000.0]})
    assert _find_col(df, ("Year", "year")) == "year"


def test_find_col_missing():
    df = pd.DataFrame({"foo": [1], "bar": [2]})
    assert _find_col(df, ("Year", "year", "YEAR")) is None


# ──────────────────────────────────────────────────────────────────────────────
# 7. ADAPTER: fetch() graceful failure when network is unavailable
# ──────────────────────────────────────────────────────────────────────────────

def test_lbnl_adapter_raises_when_network_dead(monkeypatch, tmp_path):
    """When every URL attempt fails, fetch() raises RuntimeError (not swallows)."""
    from collectors.lbnl_queue import LbnlQueueAdapter
    monkeypatch.setattr(
        "collectors.lbnl_queue._try_fetch_xlsx",
        lambda year: (None, ["https://x/a.xlsx -> HTTP 404"]),
    )
    monkeypatch.setattr("collectors.lbnl_queue.config.data_dir", lambda: tmp_path)
    adapter = LbnlQueueAdapter()
    with pytest.raises(RuntimeError, match="lbnl_queue"):
        adapter.fetch()


def test_failure_message_carries_the_real_per_url_outcome(monkeypatch, tmp_path):
    """The 26-night regression: every distinct failure collapsed into one hardcoded
    'emp.lbl.gov unreachable (Cloudflare WAF) ... Re-run from a browser session'.
    The host was reachable and answering 404. A collector that cannot say which wall
    it hit sends its reader to the wrong fix, which is what happened for a month."""
    from collectors.lbnl_queue import LbnlQueueAdapter
    monkeypatch.setattr(
        "collectors.lbnl_queue._try_fetch_xlsx",
        lambda year: (None, ["https://emp.lbl.gov/a.xlsx -> HTTP 404",
                             "https://emp.lbl.gov/b.xlsx -> HTTP 403"]),
    )
    monkeypatch.setattr("collectors.lbnl_queue.config.data_dir", lambda: tmp_path)
    with pytest.raises(RuntimeError) as ei:
        LbnlQueueAdapter().fetch()
    msg = str(ei.value)
    assert "HTTP 404" in msg and "HTTP 403" in msg, (
        f"the per-URL outcomes must reach the operator verbatim; got {msg!r}")
    assert "Cloudflare WAF" not in msg, (
        "the hardcoded WAF diagnosis is exactly the false claim this replaced")


def test_seed_present_degrades_to_blocked_not_a_nightly_hard_failure(monkeypatch, tmp_path):
    """'Queued Up' is an ANNUAL publication read through a committed seed, so a night
    that cannot reach it is the ordinary between-editions state — not an incident.
    expected_failure => the runner reports 'blocked', which per collectors/base.py
    update_breaker CLEARS the breaker instead of racking up a ×26 streak alarm."""
    from collectors.lbnl_queue import LbnlQueueAdapter
    monkeypatch.setattr(
        "collectors.lbnl_queue._try_fetch_xlsx",
        lambda year: (None, ["https://emp.lbl.gov/a.xlsx -> HTTP 404"]),
    )
    monkeypatch.setattr("collectors.lbnl_queue.config.data_dir", lambda: tmp_path)
    (tmp_path / "eia").mkdir(parents=True, exist_ok=True)
    (tmp_path / "eia" / "interconnection_queue.json").write_text('{"total_gw_yoy": 26.3}')
    adapter = LbnlQueueAdapter()
    with pytest.raises(RuntimeError):
        adapter.fetch()
    assert adapter.expected_failure, "seed present => known limitation, not a failure"
    assert "HTTP 404" in adapter.expected_failure
    assert "LBNL_QUEUE_XLSX_URL" in adapter.expected_failure, (
        "the reason must name the one operator action that re-arms the collector")


def test_missing_seed_stays_a_hard_failure(monkeypatch, tmp_path):
    """The other half, and the reason this is not just alarm-muting: with no seed the
    power_scarcity queue_buildout leg is DARK, and that must stay loud."""
    from collectors.lbnl_queue import LbnlQueueAdapter
    monkeypatch.setattr(
        "collectors.lbnl_queue._try_fetch_xlsx",
        lambda year: (None, ["https://emp.lbl.gov/a.xlsx -> HTTP 404"]),
    )
    monkeypatch.setattr("collectors.lbnl_queue.config.data_dir", lambda: tmp_path)
    adapter = LbnlQueueAdapter()
    with pytest.raises(RuntimeError) as ei:
        adapter.fetch()
    assert not getattr(adapter, "expected_failure", None), (
        "no seed => the leg is dark => must NOT be laundered into 'blocked'")
    assert "DARK" in str(ei.value)


def test_configured_override_url_is_tried_first(monkeypatch):
    """The re-arm path: an operator who reads the current filename off the
    WAF-challenged index sets LBNL_QUEUE_XLSX_URL and needs no code change."""
    import collectors.lbnl_queue as lq
    seen: list[str] = []
    monkeypatch.setattr(lq.config, "secret",
                        lambda k: "https://emp.lbl.gov/sites/default/files/2026-06/real.xlsx"
                        if k == "LBNL_QUEUE_XLSX_URL" else None)
    monkeypatch.setattr(lq, "_try_url",
                        lambda url, timeout=90: (seen.append(url), (None, "HTTP 404"))[1])
    lq._try_fetch_xlsx(2026)
    assert seen[0].endswith("2026-06/real.xlsx"), (
        f"override must be attempt #1, ahead of the legacy patterns; order was {seen}")


# ──────────────────────────────────────────────────────────────────────────────
# 8. INTEGRATION: compute_yoy output passes through _queue_pull correctly
#    (end-to-end test using the seed JSON format)
# ──────────────────────────────────────────────────────────────────────────────

def test_end_to_end_seed_format(monkeypatch, tmp_path):
    """The dict that compute_yoy() produces can be round-tripped through the
    _queue_pull() reader: write it as JSON, read it back, verify the z-score."""
    tbl = _make_tbl([(2022, 1000.0), (2023, 1200.0)])   # +20% -> z = 1.0
    seed = compute_yoy(tbl)

    (tmp_path / "eia").mkdir(parents=True, exist_ok=True)
    (tmp_path / "eia" / "interconnection_queue.json").write_text(
        json.dumps(seed)
    )
    monkeypatch.setattr(ps.config, "data_dir", lambda: tmp_path)
    z = ps._queue_pull()
    assert z == pytest.approx(1.0, abs=0.01), (
        f"compute_yoy output (+20% -> total_gw_yoy=20.0) should yield z=1.0, "
        f"got {z!r}"
    )


"""Synthetic XLSX -> native collector -> temporary cache -> native engine proof.

Run against source/ and candidate/ separately by placing that directory first
on PYTHONPATH. Network and clock-independent FRED reads are injected only at I/O.
"""
import io
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from collectors import lbnl_queue as q
from engine import power_scarcity as p

SEED = b'{"total_gw_yoy":-10.0,"asof_year":2025,"total_gw":2061.0,"prior_year":2024,"prior_gw":2290.0}'


def workbook(rows):
    buf = io.BytesIO()
    pd.DataFrame(rows, columns=['Year', 'Total capacity (GW)']).to_excel(
        buf, index=False, sheet_name='Annual totals')
    return buf.getvalue()


def point_cache(monkeypatch, tmp_path, contents=SEED):
    f = tmp_path / 'eia' / 'interconnection_queue.json'
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(contents)
    monkeypatch.setattr(q.config, 'data_dir', lambda: tmp_path)
    return f


def inject_workbook(monkeypatch, rows):
    blob = workbook(rows)
    monkeypatch.setattr(q, '_try_fetch_xlsx', lambda year: (blob, []))


INVALID_ROWS = [
    ('missing_prior_year', [(2023, 1000), (2025, 2000)]),
    ('duplicate_latest_year', [(2025, 1000), (2025, 2000)]),
    ('duplicate_prior_year', [(2024, 500), (2024, 1000), (2025, 2000)]),
    ('fractional_years', [(2024.5, 1000), (2025.5, 2000)]),
    ('positive_infinite_latest', [(2024, 1000), (2025, 'inf')]),
    ('negative_infinite_latest', [(2024, 1000), (2025, '-inf')]),
    ('infinite_prior', [(2024, 'inf'), (2025, 1000)]),
    ('negative_latest', [(2024, 1000), (2025, -1)]),
    ('negative_prior', [(2024, -1000), (2025, 1000)]),
    ('zero_prior', [(2024, 0), (2025, 1000)]),
    ('overflow_ratio', [(2024, 1e-300), (2025, 1e300)]),
]


@pytest.mark.parametrize('label,rows', INVALID_ROWS, ids=[x[0] for x in INVALID_ROWS])
def test_invalid_workbook_preserves_prior_cache(monkeypatch, tmp_path, label, rows):
    f = point_cache(monkeypatch, tmp_path)
    inject_workbook(monkeypatch, rows)
    with pytest.raises(ValueError, match='lbnl_queue:'):
        q.LbnlQueueAdapter().fetch()
    assert f.read_bytes() == SEED, label
    assert p._queue_pull() == -0.5, label


VALID_ROWS = [
    ('positive', [(2024, 1000), (2025, 1200)], 20.0, 1.0),
    ('negative', [(2024, 1200), (2025, 900)], -25.0, -1.25),
    ('unchanged', [(2024, 1000), (2025, 1000)], 0.0, 0.0),
    ('zero_latest', [(2024, 1000), (2025, 0)], -100.0, -2.0),
    ('fraction_unit_tripwire', [(2024, 1000), (2025, 1002)], 0.2, 0.01),
    ('descending_sheet', [(2025, 1200), (2024, 1000)], 20.0, 1.0),
    ('older_gap_not_latest', [(2020, 10), (2024, 1000), (2025, 1200)], 20.0, 1.0),
    ('current_seed_figures', [(2024, 2290), (2025, 2061)], -10.0, -0.5),
]


@pytest.mark.parametrize('label,rows,yoy,z', VALID_ROWS, ids=[x[0] for x in VALID_ROWS])
def test_valid_workbook_retains_native_contract(monkeypatch, tmp_path, label, rows, yoy, z):
    f = point_cache(monkeypatch, tmp_path)
    inject_workbook(monkeypatch, rows)
    frames = q.LbnlQueueAdapter().fetch()
    data = json.loads(f.read_text(), parse_constant=lambda v: pytest.fail(v))
    assert data['total_gw_yoy'] == yoy
    assert data['asof_year'] == 2025 and data['prior_year'] == 2024
    assert p._queue_pull() == z
    assert frames['lbnl_queue__ingest'].iloc[0]['total_gw_yoy'] == yoy
    monkeypatch.setattr(p, '_first', lambda ids: None)
    payload = p.compute_power_scarcity(write_ledger=False)
    assert payload['legs'] == {'queue_buildout': z}
    assert payload['n_legs'] == 1
    assert len(payload['themes']) == 5
    json.dumps(payload, allow_nan=False)


BAD_CACHES = [
    ('array', '[]'), ('null_root', 'null'),
    ('nan', '{"total_gw_yoy":NaN}'),
    ('infinity', '{"total_gw_yoy":Infinity}'),
    ('negative_infinity', '{"total_gw_yoy":-Infinity}'),
    ('string_nan', '{"total_gw_yoy":"NaN"}'),
    ('overflow', '{"total_gw_yoy":1e999}'),
    ('bool', '{"total_gw_yoy":true}'),
    ('junk', '{"total_gw_yoy":"unavailable"}'),
    ('nested', '{"total_gw_yoy":[]}'),
]


@pytest.mark.parametrize('label,raw', BAD_CACHES, ids=[x[0] for x in BAD_CACHES])
def test_bad_cache_omits_queue_without_losing_fred(monkeypatch, tmp_path, label, raw):
    point_cache(monkeypatch, tmp_path, raw.encode())
    idx = pd.date_range('2020-01-01', periods=60, freq='MS')
    s = pd.Series(np.r_[np.full(48, 100.), np.linspace(102., 140., 12)], index=idx)
    monkeypatch.setattr(p, '_first', lambda ids: s)
    assert p._queue_pull() is None
    out = p.compute_power_scarcity(write_ledger=False)
    assert out['n_legs'] == 3
    assert 'queue_buildout' not in out['legs']
    assert len(out['themes']) == 5
    assert all(math.isfinite(v) for v in out['legs'].values())
    json.dumps(out, allow_nan=False)


@pytest.mark.parametrize('value,want', [(0,0.),(20.,1.),(-20.,-1.),(100.,2.),(-100.,-2.),('20',1.)])
def test_finite_reader_controls(monkeypatch, tmp_path, value, want):
    point_cache(monkeypatch, tmp_path, json.dumps({'total_gw_yoy':value}).encode())
    assert p._queue_pull() == want
