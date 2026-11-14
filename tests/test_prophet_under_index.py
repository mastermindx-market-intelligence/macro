"""Fixed rev 2 acceptance; full desk files are optional, never vendored."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine.prophet_under_index import (
    Config, ELEVEN, NINE, SECTORS, daily_fields, display_form, member_counts, offsetting_band,
)
from scripts.build_prophet_under_index import build, load_close

REFERENCE_SHA256 = {
    9: "2b68c9ef57a0cb36c59218bd1a763440ae9a6c7646b87f14c8d4c4908fc9c7f9",
    11: "472933502a4999d3c2dbf5919f7f6c7d24c4524fc6ceb5e17aa9566efe8bc45a",
}


@pytest.mark.parametrize("state,band,expected", [
    ("rising together", "flat", "compact"), ("quiet", "up", "compact"),
    ("falling together", "down", "falling_with_index"),
    ("pulling apart", "flat", "full"), ("rising together", "down", "full"),
    ("n/a", "flat", "unavailable"), ("quiet", "n/a", "unavailable"),
])
def test_forms(state, band, expected):
    assert display_form(state, band) == expected


@pytest.mark.parametrize("value,expected", [
    (0, "almost none"), (.011158, "almost none"), (.011159, "about usual"),
    (.346229, "about usual"), (.346230, "more than usual"), (np.nan, "n/a"),
])
def test_offsetting(value, expected):
    assert offsetting_band(value) == expected


def test_full_precision_cut_boundaries():
    config = Config()
    assert config.offsetting_low == 0.011158259853538948
    assert config.offsetting_high == 0.34622932464889694
    assert offsetting_band(config.offsetting_low) == "almost none"
    assert offsetting_band(config.offsetting_high) == "about usual"
    assert offsetting_band(np.nextafter(config.offsetting_high, np.inf)) == "more than usual"


def test_warmup_zero_missing_and_eleven_majority():
    ix = pd.bdate_range("2020-01-01", periods=400)
    close = pd.DataFrame({t: np.exp(np.arange(400) * (.001 if i < 8 else -.001))
                          for i, t in enumerate(ELEVEN)}, index=ix)
    result = daily_fields(close, close.iloc[:, 0])
    assert (result.iloc[:272].reader_state == "n/a").all()
    assert result.iloc[-1].reader_state in ("pulling apart", "quiet")
    assert result.iloc[-1].up_n == 8
    zero = daily_fields(close * 0 + 100, close.iloc[:, 0])
    assert zero.iloc[-1].groups_N == 11
    assert zero.iloc[-1].up_n == zero.iloc[-1].down_n == 0
    assert pd.isna(zero.iloc[-1].cancelled_share_median_21)


def test_drill_counts_only_and_full_window():
    ix = pd.bdate_range("2020-01-01", periods=252)
    prices = {"a": pd.Series(100., index=ix),
              "b": pd.Series([100.] * 251 + [70.], index=ix)}
    assert member_counts(prices, ["a", "b", "missing"], ix, ix[-1]) == {
        "within_5pct_high": 1, "at_least_20pct_below_high": 1,
        "member_total": 3, "eligible_members": 2,
    }


def test_fixed_sample():
    sample = json.loads((Path(__file__).parent / "fixtures/prophet_under_index_sample.json").read_text())
    assert sample["reference_sha256"] == {str(k): v for k, v in REFERENCE_SHA256.items()}
    assert len(sample["rows"]) == 6
    for row in sample["rows"]:
        n = row["groups_N"]
        assert row["up_n"] + row["down_n"] <= n
        if row["reader_state"] == "rising together":
            assert row["up_n"] >= np.ceil(.75 * n)
        elif row["reader_state"] == "falling together":
            assert row["down_n"] >= np.ceil(.75 * n)
        else:
            assert max(row["up_n"], row["down_n"]) < np.ceil(.75 * n)


@pytest.mark.parametrize("hour,expected,fresh", [(20, "2023-12-28", True),
                                               (23, "2023-12-29", True)])
def test_completed_bar_publication(tmp_path, hour, expected, fresh):
    from lib.nyse_calendar import is_session
    dates = pd.date_range("2018-06-19", "2024-01-05")
    dates = dates[[is_session(d.date()) for d in dates]]
    directory = tmp_path / "data/yahoo"
    directory.mkdir(parents=True)
    for ticker in (*ELEVEN, "SPY", "MEMBER"):
        pd.DataFrame({"close": np.exp(np.arange(len(dates)) * .001)}, index=dates).to_parquet(
            directory / f"{ticker}.parquet")
    baskets = {f"us_sector_{i}": {"etf_proxy": t, "members": [
        {"ticker": "MEMBER", "added": "2018-01-01", "removed": None}]}
        for i, t in enumerate(ELEVEN)}
    membership = tmp_path / "data/baskets"
    membership.mkdir()
    (membership / "membership.json").write_text(json.dumps({"baskets": baskets}))
    now = datetime(2023, 12, 29, hour, tzinfo=timezone.utc)
    payload = build(tmp_path, now)
    assert payload["date"] == expected
    assert payload["fresh"] is fresh
    assert len(payload["sectors"]) == 11
    assert all(s["within_5pct_high"] == 1 for s in payload["sectors"])
    serialized = json.dumps(payload, allow_nan=False)
    assert "MEMBER" not in serialized
    assert not any(t in serialized for t in (*ELEVEN, "SPY"))
    assert payload["method_label"] == "counts sectors equally; not an attribution of the index's return"
    assert "not been shown to predict turns" in payload["limit_line"]
    assert payload["description"] == "description only"
    # A missing latest sector bar must not yield a confident live state.
    path = directory / f"{ELEVEN[0]}.parquet"
    frame = pd.read_parquet(path)
    frame = frame.drop(pd.Timestamp(expected))
    frame.to_parquet(path)
    unavailable = build(tmp_path, now)
    assert unavailable["display_form"] == "unavailable"
    assert unavailable["fresh"] is False


def test_nightly_checkpoint_wiring():
    root = Path(__file__).resolve().parents[1]
    nightly = (root / "scripts/ci/daily_engine_prophet_nightly.sh").read_text()
    checkpoint = (root / "scripts/ci/daily_engine_prophet_checkpoint.sh").read_text()
    assert nightly.count('"site/prophet/under_index.json"') == 2
    assert "python -m scripts.build_prophet_under_index" in nightly
    assert "site/prophet/under_index.json|" in checkpoint


@pytest.mark.parametrize("size,start,count", [(9, "2004-01-02", 5033), (11, "2019-07-19", 1121)])
def test_full_reference(size, start, count):
    location = os.environ.get("PROPHET_UNDER_INDEX_REFERENCE_DIR")
    prices = os.environ.get("PROPHET_UNDER_INDEX_PRICE_DIR")
    if not location or not prices:
        pytest.skip("explicit reference and price directories required")
    reference = Path(location) / f"REFERENCE_DAILY_{size}.csv"
    assert hashlib.sha256(reference.read_bytes()).hexdigest() == REFERENCE_SHA256[size]
    expected = pd.read_csv(reference, keep_default_na=False).set_index("date")
    groups = NINE if size == 9 else ELEVEN
    raw = {t: load_close(Path(prices), t) for t in groups}
    calendar = pd.DatetimeIndex(sorted(set().union(*(set(s.index) for s in raw.values()))))
    calendar = calendar[(calendar >= ("1998-12-22" if size == 9 else "2018-06-19"))
                        & (calendar <= "2023-12-29")]
    close = pd.DataFrame({t: s.reindex(calendar) for t, s in raw.items()})
    actual = daily_fields(close, load_close(Path(prices), "SPY")).loc[start:"2023-12-29"]
    actual.index = actual.index.strftime("%Y-%m-%d")
    assert len(actual) == len(expected) == count
    assert actual.index.equals(expected.index)
    mismatches = {}
    for column in expected:
        left = actual[column]
        right = expected[column]
        if column.endswith("_names"):
            right = right.map(lambda value: [SECTORS[t] for t in value.split()])
        elif column == "display_form":
            right = right.replace("falling with the index", "falling_with_index")
        elif pd.api.types.is_numeric_dtype(left):
            right = pd.to_numeric(right)
        bad = left != right
        if bad.any():
            mismatches[column] = int(bad.sum())
    print(f"S{size}: rows compared={count}, mismatches={sum(mismatches.values())}, columns={mismatches}")
    assert not mismatches
    sample = json.loads((Path(__file__).parent / "fixtures/prophet_under_index_sample.json").read_text())
    for row in sample["rows"]:
        if row["panel"] == size:
            for key, value in row.items():
                if key not in ("date", "panel"):
                    assert actual.loc[row["date"], key] == value
