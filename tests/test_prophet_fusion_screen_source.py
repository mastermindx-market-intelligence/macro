"""Synthetic Parquet/clock contracts; no real outcome data or holdout access."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lib.nyse_calendar import sessions_between
from scripts import prophet_fusion_screen_source as s
from scripts.prophet_fusion_cohort_diagnostics import implied_volatility_trajectory


def repin_source(manifest_path, root, monkeypatch):
    manifest = json.loads(manifest_path.read_text())
    for relative in s.PROJECTIONS:
        path = root / relative
        manifest["files"][relative] = {"sha256": s.sha256(path), "bytes": path.stat().st_size}
    manifest_path.write_text(json.dumps(manifest, sort_keys=True))
    monkeypatch.setattr(s, "MANIFEST_SHA256", s.sha256(manifest_path))


@pytest.fixture
def archive(tmp_path, monkeypatch):
    root = tmp_path / "original"
    days = pd.to_datetime(["2018-03-01", "2018-03-02", "2018-03-05",
                           "2018-03-06", "2020-01-02"])
    frame = pd.DataFrame({
        "event_id": [f"G3:{ticker}:{day.date()}" for ticker, day in zip("ABCDE", days)],
        "ticker": list("ABCDE"), "table": "G3", "date": days,
        "bar_label": days - pd.Timedelta(days=3),
        "window": ["SCREEN"] * 4 + ["HOLD"], "group": list("XXYYZ"),
        "family": "synthetic", "coverage_grade": "usable",
        "counting": True, "in_washout_context": False,
        "real63": [True, False, True, False, True],
        "fwd63_rel_spy": [0.1, -0.2, 0.3, -0.4, 99.0],
    })
    guard = frame[["event_id", "ticker", "date"]].assign(agree=True)
    primary = frame.iloc[:3][["event_id", "ticker", "date", "group"]].copy()
    primary["A1"], primary["A2"], primary["A3"] = [True, True, False], False, False
    primary["ANY"], primary["A4"], primary["defined"] = [True, True, False], [False, False, True], True
    primary["real63"] = [True, False, True]
    for relative, data in [(s.EVENTS, frame), (s.GUARD, guard), (s.PRIMARY, primary)]:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        data.to_parquet(path, index=False)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "schema": "prophet.recovered_screen_source/v1", "window": ["2013-01-02", "2019-12-31"],
        "outcome_access_authorized": False, "source_mode": "SYNTHETIC",
        "files": {}, "expected_counts": {"screen_retained": 4, "primary_analytic": 3,
                                       "primary_any": 2, "primary_none": 1},
    }))
    repin_source(manifest, root, monkeypatch)
    return root, manifest, tmp_path / "metadata"


@pytest.fixture
def context():
    grid = pd.DatetimeIndex(sessions_between(
        pd.Timestamp("2017-01-03").date(), pd.Timestamp("2018-03-06").date()))
    vix = pd.Series(np.linspace(12, 35, len(grid)), index=grid)
    vvix = pd.Series(np.linspace(80, 140, len(grid)), index=grid)
    return grid, vix, vvix, implied_volatility_trajectory(vix, vvix, grid)


def extracted(archive):
    root, manifest, out = archive
    receipt = s.extract_metadata(root, manifest, out)
    digest = s.sha256(out / "receipt.json")
    frame, _ = s.load_export(out, manifest, digest)
    return frame, receipt, digest


def test_original_ids_population_and_undefined_rows_survive(archive, monkeypatch):
    calls = []
    native = s.pq.read_table

    def read_only_projection(path, **kwargs):
        calls.append((str(path), kwargs["columns"], kwargs["filters"]))
        assert "real63" not in kwargs["columns"] and "fwd63_rel_spy" not in kwargs["columns"]
        assert kwargs["filters"] == [("date", ">=", s.START), ("date", "<=", s.END)]
        return native(path, **kwargs)

    monkeypatch.setattr(s.pq, "read_table", read_only_projection)
    frame, receipt, _ = extracted(archive)
    assert len(calls) == 4
    assert len(frame) == 4 and frame.event_id.nunique() == 4
    assert frame.event_id.tolist() == [
        "G3:A:2018-03-01", "G3:B:2018-03-02", "G3:C:2018-03-05", "G3:D:2018-03-06"]
    assert receipt["counts"]["outside_primary_analytic"] == 1
    assert frame.loc[~frame.primary_analytic, s.GATES].isna().all().all()
    assert frame.loc[frame.primary_analytic, "ANY"].sum() == 2
    assert frame.loc[frame.primary_analytic, "A4"].sum() == 1
    assert "real63" not in frame and "fwd63_rel_spy" not in frame
    assert frame.date.max() < pd.Timestamp("2020-01-01")


def test_changed_original_source_fails_before_export(archive):
    root, manifest, out = archive
    with (root / s.EVENTS).open("ab") as handle:
        handle.write(b"changed")
    with pytest.raises(s.ScreenSourceRefusal, match="SOURCE_DIGEST_MISMATCH"):
        s.extract_metadata(root, manifest, out)
    assert not out.exists()


def test_substituted_manifest_is_not_self_authenticating(archive):
    root, manifest, out = archive
    manifest.write_text(manifest.read_text() + "\n")
    with pytest.raises(s.ScreenSourceRefusal, match="UNPINNED_SOURCE_MANIFEST"):
        s.extract_metadata(root, manifest, out)


@pytest.mark.parametrize("failure", ["missing", "false", "date", "ticker", "duplicate"])
def test_prefix_proof_must_match_each_retained_identity(archive, monkeypatch, failure):
    root, manifest, out = archive
    guard = pd.read_parquet(root / s.GUARD)
    if failure == "missing":
        guard = guard.iloc[1:]
    elif failure == "false":
        guard.loc[0, "agree"] = False
    elif failure == "date":
        guard.loc[0, "date"] += pd.Timedelta(days=1)
    elif failure == "ticker":
        guard.loc[0, "ticker"] = "WRONG"
    else:
        guard = pd.concat([guard, guard.iloc[:1]], ignore_index=True)
    guard.to_parquet(root / s.GUARD, index=False)
    repin_source(manifest, root, monkeypatch)
    with pytest.raises(s.ScreenSourceRefusal, match="PREFIX_PROOF|DUPLICATE"):
        s.extract_metadata(root, manifest, out)


@pytest.mark.parametrize("failure", ["undefined", "overlap", "any", "identity"])
def test_primary_membership_is_not_silently_repaired(archive, monkeypatch, failure):
    root, manifest, out = archive
    primary = pd.read_parquet(root / s.PRIMARY)
    if failure == "undefined":
        primary.loc[0, "defined"] = False
    elif failure == "overlap":
        primary.loc[0, "A4"] = True
    elif failure == "any":
        primary.loc[0, "ANY"] = False
    else:
        primary.loc[0, "ticker"] = "WRONG"
    primary.to_parquet(root / s.PRIMARY, index=False)
    repin_source(manifest, root, monkeypatch)
    with pytest.raises(s.ScreenSourceRefusal, match="PARTITION|IDENTITY"):
        s.extract_metadata(root, manifest, out)


def test_archive_and_existing_export_cannot_be_overwritten(archive):
    root, manifest, out = archive
    with pytest.raises(s.ScreenSourceRefusal, match="INSIDE_ORIGINAL"):
        s.extract_metadata(root, manifest, root / "consumer")
    extracted(archive)
    with pytest.raises(s.ScreenSourceRefusal, match="ALREADY_EXISTS"):
        s.extract_metadata(root, manifest, out)


def test_consumer_requires_independently_pinned_receipt(archive):
    _, manifest, out = archive
    _, _, digest = extracted(archive)
    (out / "receipt.json").write_text((out / "receipt.json").read_text() + "\n")
    with pytest.raises(s.ScreenSourceRefusal, match="UNPINNED_EXPORT_RECEIPT"):
        s.load_export(out, manifest, digest)


def test_consumer_refuses_altered_export(archive):
    _, manifest, out = archive
    frame, _, digest = extracted(archive)
    frame.loc[0, "event_id"] = "REPLACED"
    frame.to_parquet(out / "metadata.parquet", index=False)
    with pytest.raises(s.ScreenSourceRefusal, match="EXPORT_DIGEST_MISMATCH"):
        s.load_export(out, manifest, digest)


def test_even_receipted_extra_outcome_column_is_rejected(archive):
    _, manifest, out = archive
    frame, receipt, _ = extracted(archive)
    frame["real63"] = True
    frame.to_parquet(out / "metadata.parquet", index=False)
    receipt["export"]["sha256"] = s.sha256(out / "metadata.parquet")
    receipt["export"]["bytes"] = (out / "metadata.parquet").stat().st_size
    (out / "receipt.json").write_text(json.dumps(receipt))
    with pytest.raises(s.ScreenSourceRefusal, match="COLUMN_ALLOWLIST"):
        s.load_export(out, manifest, s.sha256(out / "receipt.json"))


def test_join_uses_original_declared_date_and_exact_single_lag(archive, context):
    frame, _, _ = extracted(archive)
    grid, vix, _, ctx = context
    joined = s.join_screen_context(frame, ctx)
    assert joined.event_id.tolist() == frame.event_id.tolist()
    assert set(joined.join_status) == {"JOINED_DATE_PROXY_ONLY"}
    for row in joined.itertuples():
        previous = grid[grid.get_loc(row.date) - 1]
        assert row.context_feature_session == previous
        assert row.context_vix_level == vix.loc[previous]


@pytest.mark.parametrize("offset", [0, 2])
def test_same_day_or_double_lag_cannot_be_presented_as_prior_session(archive, context, offset):
    frame, _, _ = extracted(archive)
    grid, _, _, ctx = context
    day = frame.iloc[0].date
    ctx.at[day, "feature_session"] = grid[grid.get_loc(day) - offset]
    with pytest.raises(s.ScreenSourceRefusal, match="NOT_PREVIOUS_EXPECTED_SESSION"):
        s.join_screen_context(frame, ctx)


def test_missing_feed_observation_abstains_without_removing_events(archive, context):
    frame, _, _ = extracted(archive)
    grid, vix, vvix, _ = context
    vvix.loc["2018-02-15"] = np.nan
    joined = s.join_screen_context(frame, implied_volatility_trajectory(vix, vvix, grid))
    assert len(joined) == 4 and joined.event_id.tolist() == frame.event_id.tolist()
    assert set(joined.join_status) == {"CONTEXT_WINDOW_INCOMPLETE"}


def test_unavailable_and_invalid_dates_remain_visible(archive, context):
    frame, _, _ = extracted(archive)
    _, _, _, ctx = context
    frame.loc[0, "date"] = pd.NaT
    frame.loc[1, "date"] = pd.Timestamp("2018-03-03")  # Saturday.
    frame.loc[2, "date"] = pd.Timestamp("2018-03-07")  # Beyond context.
    joined = s.join_screen_context(frame, ctx)
    assert joined.join_status.tolist() == [
        "DECLARED_DATE_UNAVAILABLE", "INVALID_DECLARED_SESSION",
        "CONTEXT_SESSION_UNAVAILABLE", "JOINED_DATE_PROXY_ONLY"]
    assert joined.event_id.tolist() == frame.event_id.tolist()


def test_real_parquet_consumer_path_preserves_denominators(archive, context, monkeypatch, tmp_path):
    from scripts import prophet_fusion_cohort_census as census
    frame, _, digest = extracted(archive)
    grid, vix, vvix, _ = context

    def inputs(pin, start, end):
        assert pin == census.DATA_PIN
        assert (start, end) == ("2013-01-02", "2019-12-31")
        return grid, {"vix": vix, "vvix": vvix}, [{"synthetic": True}]

    monkeypatch.setattr(census, "read_inputs", inputs)
    out = tmp_path / "consumer"
    report = s.consume(archive[2], archive[1], digest, out)
    assert report["source_counts"]["screen_retained"] == 4
    assert report["source_counts"]["primary_analytic"] == 3
    assert report["outside_primary_remains_unclassified"] == 1
    assert report["join_status_counts"] == {"JOINED_DATE_PROXY_ONLY": 4}
    assert report["primary_direction_counts"] == {"ANY": {"BOTH_RISING": 2},
                                                 "A4": {"BOTH_RISING": 1}}
    assert not report["outcomes_decoded"] and not report["promotion_eligible"]
    joined = pd.read_parquet(out / "joined_metadata.parquet")
    assert joined.event_id.tolist() == frame.event_id.tolist()
    assert not any("real63" in col or "fwd" in col for col in joined)


def test_extra_out_of_screen_export_row_cannot_disappear_in_filter(archive):
    _, manifest, out = archive
    frame, receipt, _ = extracted(archive)
    extra = frame.iloc[:1].copy()
    extra["event_id"], extra["date"], extra["window"] = "HOLD:EXTRA", pd.Timestamp("2020-01-02"), "HOLD"
    pd.concat([frame, extra], ignore_index=True).to_parquet(out / "metadata.parquet", index=False)
    receipt["export"]["sha256"] = s.sha256(out / "metadata.parquet")
    receipt["export"]["bytes"] = (out / "metadata.parquet").stat().st_size
    (out / "receipt.json").write_text(json.dumps(receipt))
    with pytest.raises(s.ScreenSourceRefusal, match="EXPORT_ROW_COUNT_MISMATCH"):
        s.load_export(out, manifest, s.sha256(out / "receipt.json"))


def test_source_writer_change_during_projection_is_detected(archive, monkeypatch):
    root, manifest, out = archive
    native = s.pq.read_table

    def changed_during_read(path, **kwargs):
        result = native(path, **kwargs)
        if str(path).endswith(s.EVENTS):
            with Path(path).open("ab") as handle:
                handle.write(b"concurrent change")
        return result

    monkeypatch.setattr(s.pq, "read_table", changed_during_read)
    with pytest.raises(s.ScreenSourceRefusal, match="SOURCE_CHANGED_DURING_READ"):
        s.extract_metadata(root, manifest, out)
    assert not out.exists()
