"""Native retained Treasury contract; synthetic inputs only, no collection."""
import hashlib
import importlib
import importlib.util
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

NOW = datetime(2026, 10, 20, 13, tzinfo=timezone.utc)


def test_contract_exists():
    assert importlib.util.find_spec("lib.treasury_daily_history") is not None


def compose(frame, **kw):
    return importlib.import_module("lib.treasury_daily_history").compose_history(
        frame, start="2026-10-13", end="2026-10-19",
        expected_through="2026-10-16", read_at=NOW, **kw)


def frame(values=(4.26, 4.28), dates=("2026-10-13", "2026-10-16")):
    return pd.DataFrame({"us3m": values}, index=dates)


def test_sorted_dates_units_clocks_and_deterministic_coverage():
    r = compose(frame((4.28, 4.26), ("2026-10-16", "2026-10-13")))
    assert r == compose(frame())
    assert r["status"] == "read"
    assert r["unit"] == "percent_per_annum"
    assert r["basis"] == "investment"
    assert r["points"] == [{"date": "2026-10-13", "value": 4.26},
                            {"date": "2026-10-16", "value": 4.28}]
    assert r["coverage"] == {"observation_count": 2, "requested_calendar_days": 7,
                              "first": "2026-10-13", "last": "2026-10-16"}
    assert r["clocks"] == {"read_at": NOW.isoformat(), "release_at": None,
                            "knowledge_at": None, "vintage_at": None}
    assert r["source"]["source_id"] == "DGS3MO"
    assert r["source"]["publication_status"] == "not_qualified"


def test_stale_keeps_real_points_and_never_fills_missing_dates():
    r = compose(frame((4.26,), ("2026-10-13",)))
    assert r["status"] == "stale"
    assert r["reason"] == "before_expected_through"
    assert len(r["points"]) == 1
    assert r["source"]["last_observation_date"] == "2026-10-13"


def test_source_tail_and_requested_coverage_are_distinct_and_future_excluded():
    r = compose(frame((4, 5, 6), ("2026-10-12", "2026-10-16", "2026-10-20")))
    assert r["source"]["last_observation_date"] == "2026-10-20"
    assert r["coverage"]["last"] == "2026-10-16"
    assert r["points"] == [{"date": "2026-10-16", "value": 5.0}]


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), None, True, "4.26"])
def test_invalid_values_fail_closed(bad):
    r = compose(frame((bad,), ("2026-10-13",)))
    assert (r["status"], r["reason"], r["points"]) == ("unavailable", "invalid", [])


@pytest.mark.parametrize("dates", [("2026-10-13", "2026-10-13"),
                                    ("bad", "2026-10-13"),
                                    ("2026-10-13T10:00:00", "2026-10-16")])
def test_invalid_or_duplicate_dates_fail_closed(dates):
    assert compose(frame(dates=dates))["reason"] == "invalid"


def test_wrong_schema_and_empty_are_explicit():
    assert compose(frame().rename(columns={"us3m": "us3m_bill"}))["reason"] == "invalid"
    assert compose(frame().assign(other=0))["reason"] == "invalid"
    assert compose(frame((), ()))["reason"] == "empty"
    assert compose(None)["reason"] == "missing"
    assert compose(frame((1,), ("2026-10-12",)))["reason"] == "no_coverage"


def test_negative_yield_is_not_clamped_or_replaced():
    assert compose(frame((-0.1,), ("2026-10-16",)))["points"][0]["value"] == -0.1


@pytest.mark.parametrize("start,end,expected", [("2026-10-19", "2026-10-13", "2026-10-16"),
    ("2026-1-13", "2026-10-19", "2026-10-16"), ("2000-01-01", "2026-10-19", "2026-10-16"),
    ("2026-10-13", "2026-10-19", "2026-10-20")])
def test_invalid_window_rejected(start, end, expected):
    m = importlib.import_module("lib.treasury_daily_history")
    with pytest.raises(ValueError, match="invalid_window"):
        m.compose_history(frame(), start=start, end=end, expected_through=expected, read_at=NOW)


def test_fixed_native_read_hash_missing_corrupt_and_no_mkdir(tmp_path):
    m = importlib.import_module("lib.treasury_daily_history")
    args = dict(start="2026-10-13", end="2026-10-19", expected_through="2026-10-16", read_at=NOW)
    assert m.read_history(tmp_path, **args)["reason"] == "missing"
    assert list(tmp_path.iterdir()) == []
    p = tmp_path / "data/fred/DGS3MO.parquet"
    p.parent.mkdir(parents=True)
    frame().to_parquet(p)
    before = p.read_bytes()
    r = m.read_history(tmp_path, **args)
    assert r["status"] == "read"
    assert r["source"]["sha256"] == hashlib.sha256(before).hexdigest()
    assert p.read_bytes() == before
    p.write_bytes(b"corrupt")
    assert m.read_history(tmp_path, **args)["reason"] == "unreadable"


def test_future_source_date_is_not_admitted():
    assert compose(frame((4,), ("2026-10-21",)))["reason"] == "invalid"


def test_subday_timestamp_is_not_silently_normalized():
    stamp = pd.Timestamp("2026-10-16T00:00:00.000000001")
    assert compose(frame((4,), (stamp,)))["reason"] == "invalid"


def test_import_envelope_and_missing_input_do_not_require_pandas(tmp_path):
    # The lean API can authenticate/refuse without loading the data-reader stack.
    code = '''
import sys, importlib.abc
from datetime import datetime, timezone
from pathlib import Path
class NoPandas(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'pandas' or fullname.startswith('pandas.'):
            raise ModuleNotFoundError('pandas deliberately absent')
sys.meta_path.insert(0, NoPandas())
from lib.treasury_daily_history import compose_history, read_history
args=dict(start='2026-10-13',end='2026-10-19',expected_through='2026-10-16',
          read_at=datetime(2026,10,20,tzinfo=timezone.utc))
assert compose_history(None,**args)['reason']=='missing'
assert read_history(Path(sys.argv[1]),**args)['reason']=='missing'
assert 'pandas' not in sys.modules
'''
    result = subprocess.run([sys.executable, "-c", code, str(tmp_path)],
                            cwd=Path(__file__).parents[1], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
