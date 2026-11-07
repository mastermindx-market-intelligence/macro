"""Source-to-calculation proof of the private broad/member contract.

Controlled incumbent acquisitions and real local publisher only. No network,
production files, runtime transfer, or authenticated beta proof is implied.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
from io import BytesIO
import json

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from collectors.breadth import BreadthAdapter
from collectors.smallcap_breadth import SmallCapBreadthAdapter
from collectors.midcap_breadth import MidCap400BreadthAdapter
from collectors.yahoo import YahooAdapter
from engine.baskets import compute_baskets_from_inputs
from lib import config, market_session, store
from lib import adjusted_price_capture as values
from lib import breadth_member_generation_contract as contract
from lib import yahoo_generation_contract as yahoo_contract
from lib.closes_panel import BROAD_GROUPS, merge_close_caches, merge_captured_close_caches
from lib.yahoo_runtime_profile import SECTOR_CLOSE_TICKERS
from scripts import fetch_basket_extras, vps_live_orchestrator as publisher

NOW = datetime(2026, 11, 3, 23, tzinfo=timezone.utc)
SOURCE = "2026-11-03"
REVISION = "a" * 40
CFG = {"ma_windows": [50, 200], "nhnl_window": 252, "lookback_days_live": 1100, "ticker_fixups": {}}
YCFG = {"batch_size": 1000, "retries": 2, "backoff_base_s": 0, "upsert_basis_tol": .001}
PREPARED = NOW + timedelta(seconds=3)
PUBLISHED = NOW + timedelta(seconds=4)


def _dates(count):
    index = pd.bdate_range(end=SOURCE, periods=count + 220)
    return index[[market_session.is_session_date("US", t.date()) for t in index]][-count:].as_unit("ns")


def _owner(root, now=PUBLISHED):
    return publisher.Orchestrator(live_dir=root / "public/live", state_dir=root / "private/state",
                                  data_dir=root / "legacy", now=now)


def forbidden(*args, **kwargs):
    raise AssertionError("Ambient checkout/provider/config access reached")


@pytest.fixture(scope="module")
def sources(tmp_path_factory):
    root = tmp_path_factory.mktemp("broad-source")
    yframes = {t: pd.DataFrame({"close": 100 + i + np.arange(1100) / 100,
        "close_price": 110 + i + np.arange(1100) / 100, "volume": np.full(1100, 1000.)},
        index=_dates(1100)) for i, t in enumerate(SECTOR_CLOSE_TICKERS)}
    adapter = YahooAdapter(yahoo_config=YCFG)
    adapter._download = lambda batch, period, **kwargs: pd.concat(
        {t: yframes[t].rename(columns={"close": "Adj Close", "close_price": "Close", "volume": "Volume"})
         for t in batch}, axis=1)
    acquired = adapter.acquire_cycle_benchmarks(SECTOR_CLOSE_TICKERS,
        prior_frames={t: None for t in SECTOR_CLOSE_TICKERS}, evaluation_instant=NOW, period="max")
    assert acquired.accepted
    yprior = {"kind": "bootstrap", "domain": yahoo_contract.YAHOO_GENERATION_DOMAIN,
        "source_ref": "fixture-absent-yahoo", "source_revision": "b" * 40, "content_id": None,
        "captured_at": (NOW - timedelta(seconds=1)).isoformat(),
        "member_sha256": {t: None for t in SECTOR_CLOSE_TICKERS},
        "member_bytes": {t: None for t in SECTOR_CLOSE_TICKERS}}
    encoded_yahoo = yahoo_contract.encode_yahoo_acquisition(acquired, prior_identity=yprior,
        prepared_at=NOW, source_revision=REVISION)
    yo = _owner(root, NOW + timedelta(seconds=1))
    yp = yo.publish_yahoo_inputs(encoded_yahoo, generation_id="yahoo-g1", source_revision=REVISION,
                                expected_current_content_id=None)
    assert yp.status == "published", yp.detail
    yahoo = yahoo_contract.read_verified_yahoo_cohort(generations_root=yo.state_dir / "generations",
                                                     now=PREPARED)
    groups = {}
    for group, klass, count in zip(BROAD_GROUPS, (BreadthAdapter, SmallCapBreadthAdapter, MidCap400BreadthAdapter),
                                   (400, 450, 350)):
        names = [f"T{i:04d}" for i in range(count)]
        close = pd.DataFrame(100 + np.arange(320)[:, None] / 10 + np.arange(count)[None, :] / 20,
                             index=_dates(320), columns=names)
        panels = {"close": close, "high": close + 2, "low": close - 2, "volume": close * 0 + 1000}
        a = klass(breadth_config=CFG, yahoo_config=YCFG)
        a._download_adjusted_capture = lambda symbols, period, panels=panels, **kwargs: values.AdjustedPriceCapture(
            {field: panel.loc[:, list(symbols)].copy() for field, panel in panels.items()},
            {t: (panels["close"].index[0], panels["close"].index[-1]) for t in symbols}, tuple(symbols))
        groups[group] = a.acquire_adjusted_prices(members=pd.DataFrame({"symbol": names,
            "name": [group + " " + t for t in names], "sector": ["Industrials"] * count}),
            prior_panels={field: None for field in values.FIELDS}, excluded_symbols=frozenset(), aliases={},
            evaluation_instant=NOW + timedelta(seconds=2), period="max")
        assert groups[group].accepted
    _, primary, meta, _ = contract.derive_primary({g: item.panels for g, item in groups.items()},
        yahoo.cohort.frames["SPY"], source_session=SOURCE)
    qualified = frozenset(t for t, group in meta["source"].items() if t in groups[group].current)
    membership = {"construction": "fixture", "baskets": {"test_theme": {"name": "Test theme", "name_zh": "测试",
        "category": "Other", "etf_proxy": ["QQQ", "IBIT"], "members": [
            *[{"ticker": f"T{i:04d}", "added": "2025-01-01"} for i in range(3)],
            {"ticker": "NEW", "added": "2026-11-02"}]}}}
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(fetch_basket_extras, "_download_closes", lambda names, **kwargs:
            pd.DataFrame({"NEW": [10., 11.]}, index=_dates(2)))
        extras = fetch_basket_extras.acquire_extras_from_inputs(membership=membership, primary_panel=primary,
            prior_extras=None, qualified_primary_members=qualified, primary_history_threshold=252,
            evaluation_instant=NOW + timedelta(seconds=2), yahoo_config=YCFG, aliases={},
            history_start="2023-01-01", primary_basis="provider_auto_adjusted")
    assert extras.status == "complete"
    capture = {"source_ref": "fixture-source-capture", "source_revision": "b" * 40,
               "captured_at": (NOW - timedelta(seconds=1)).isoformat()}
    prior = {"kind": "bootstrap", "domain": contract.DOMAIN, **capture, "content_id": None,
             "members": {name: None for name in contract.MEMBERS}}
    return dict(groups=groups, extras=extras, membership=membership, yahoo=yahoo,
        reference_frames={"IBIT": None}, reference_evidence={"IBIT": {"status": "absent", "reason": "not_captured"}},
        source_captures={key: deepcopy(capture) for key in (*BROAD_GROUPS, "membership")},
        prior_identity=prior, prepared_at=PREPARED, source_revision=REVISION)


@pytest.fixture(scope="module")
def original(sources):
    return contract.encode_breadth_member_acquisitions(**sources)


@pytest.fixture
def encoded(original):
    return contract.EncodedBreadthMemberInputs(dict(original.members),
        deepcopy(dict(original.input_identity)), original.yahoo)


def _validate(encoded, *, now=PUBLISHED, published=PUBLISHED, require_current=False):
    return contract.validate_breadth_member_bundle(member_bytes=encoded.members,
        input_identity=encoded.input_identity, yahoo=encoded.yahoo, published_at=published.isoformat(),
        now=now, source_revision=REVISION, computed_at=PREPARED.isoformat(), require_current=require_current)


def _receipt(encoded, update):
    value = json.loads(encoded.members["acquisition.json"])
    update(value)
    raw = contract._json_bytes(value)
    encoded.members["acquisition.json"] = raw
    encoded.input_identity["sector_breadth_members"]["acquisition_sha256"] = hashlib.sha256(raw).hexdigest()


def test_real_publication_read_and_basket_calculation_are_independent_of_checkout(tmp_path, encoded, monkeypatch):
    owner = _owner(tmp_path)
    result = owner.publish_breadth_member_inputs(encoded, generation_id="broad-g1",
        source_revision=REVISION, expected_current_content_id=None)
    assert result.status == "published", result.detail
    with monkeypatch.context() as mp:
        for obj, name in ((config, "load"), (config, "data_dir"), (store, "read"), (pd, "read_parquet")):
            mp.setattr(obj, name, forbidden)
        read = contract.read_verified_breadth_member_inputs(
            generations_root=owner.state_dir / "generations", yahoo=encoded.yahoo, now=PUBLISHED)
        baskets = compute_baskets_from_inputs(read.inputs.basket_inputs())
    assert read.snapshot.content_id == result.content_id
    assert len(read.snapshot.members) == 19
    assert baskets["as_of"] == SOURCE
    assert baskets["baskets"][0]["reference"] is None
    assert read.inputs.resolution["source_basis"]["primary_breadth"] == "provider_auto_adjusted"
    assert read.inputs.references["IBIT"] is None
    assert "QQQ" in read.inputs.references
    assert read.inputs.constituents["breadth"].iloc[0]["name"] == "breadth T0000"
    assert read.inputs.basket_inputs().names_sectors["T0000"][0] == "breadth T0000"
    assert read.prior_identity(captured_at=PUBLISHED)["content_id"] == result.content_id


def test_same_owner_last_generation_survives_rejected_current_observation(tmp_path, encoded):
    owner = _owner(tmp_path)
    first = owner.publish_breadth_member_inputs(encoded, generation_id="broad-g1",
        source_revision=REVISION, expected_current_content_id=None)
    assert first.status == "published"
    name = "groups/breadth/high.parquet"
    frame = contract.decode_panel(encoded.members[name], field="high", source_session=SOURCE)
    frame.loc[SOURCE, "T0000"] = np.nan
    encoded.members[name] = contract.encode_panel(frame, field="high", source_session=SOURCE)
    failed = owner.publish_breadth_member_inputs(encoded, generation_id="broad-bad",
        source_revision=REVISION, expected_current_content_id=first.content_id)
    assert failed.status == "rejected"
    selected = publisher.read_selected_generation(generations_root=owner.state_dir / "generations",
                                                  domain=contract.DOMAIN, members=contract.MEMBERS)
    assert selected.content_id == first.content_id


@pytest.mark.parametrize("field", values.FIELDS)
def test_primitive_panel_roundtrip_preserves_nulls_archives_and_zero_volume(field):
    frame = pd.DataFrame({"ZZZ": [12., np.nan, 14.], "AAA": [1., 2., 3.]}, index=_dates(3))
    if field == "volume":
        frame.iloc[0, 1] = 0
    raw = contract.encode_panel(frame, field=field, source_session=SOURCE)
    observed = contract.decode_panel(raw, field=field, source_session=SOURCE)
    pd.testing.assert_frame_equal(observed, frame.reindex(columns=["AAA", "ZZZ"]),
                                  check_names=False, check_freq=False)
    with pq.ParquetFile(BytesIO(raw)) as parquet:
        assert not parquet.metadata.metadata
        assert parquet.schema_arrow.field("session").type == pa.timestamp("ns")


def test_empty_optional_reference_is_a_real_fixed_member(encoded):
    assert "references/close.parquet" in encoded.members
    assert contract.decode_panel(encoded.members["references/close.parquet"], field="close", source_session=SOURCE).empty
    del encoded.members["references/close.parquet"]
    with pytest.raises(ValueError, match="member_set"):
        _validate(encoded)


@pytest.mark.parametrize("kind", ("metadata", "nested", "wrong_time_unit", "duplicate"))
def test_parquet_foreign_schema_is_rejected_before_read(kind, monkeypatch):
    field = pa.array([10.], type=pa.float64())
    table = pa.Table.from_arrays([pa.array([pd.Timestamp(SOURCE)], type=pa.timestamp("ms" if kind == "wrong_time_unit" else "ns")), field],
                                names=["session", "T"])
    if kind == "metadata":
        table = table.replace_schema_metadata({b"pandas": b"{}"})
    elif kind == "nested":
        table = pa.table({"session": pa.array([pd.Timestamp(SOURCE)], type=pa.timestamp("ns")),
                          "T": pa.array([[1.]], type=pa.list_(pa.float64()))})
    elif kind == "duplicate":
        table = pa.Table.from_arrays([table[0], field, field], names=["session", "T", "T"])
    stream = BytesIO()
    pq.write_table(table, stream, store_schema=kind == "metadata")
    with pytest.raises(ValueError):
        contract.decode_panel(stream.getvalue(), field="close", source_session=SOURCE)


def test_panel_footer_and_union_bounds_are_checked_before_materializing(monkeypatch):
    raw = b"PAR1" + b"x" * 8 + (contract.MAX_FOOTER_BYTES + 1).to_bytes(4, "little") + b"PAR1"
    with pytest.raises(ValueError, match="footer"):
        contract.decode_panel(raw, field="close", source_session=SOURCE)
    monkeypatch.setattr(values, "MAX_PANEL_CELLS", 5)
    a = pd.DataFrame({"A": [1., 2.], "B": [2., 3.]}, index=_dates(2))
    b = pd.DataFrame({"C": [4., 5.]}, index=_dates(2))
    with pytest.raises(ValueError, match="union"):
        contract._bound_union([a, b])


def test_yahoo_dependency_is_exact_and_raw_capture_not_mutable_frame_authority(encoded):
    frame = encoded.yahoo.cohort.frames["SPY"]
    before = frame.iloc[0, 0]
    frame.iloc[0, 0] = -1
    try:
        assert _validate(encoded).spy.iloc[0, 0] == before
    finally:
        frame.iloc[0, 0] = before
    _receipt(encoded, lambda value: value["yahoo"].update(content_id="c" * 64))
    with pytest.raises(ValueError, match="identity|dependency"):
        _validate(encoded)


@pytest.mark.parametrize("mutation,code", [
    (lambda v: v["groups"]["breadth"]["evidence"].update(current_members=999), "breadth_evidence"),
    (lambda v: v["groups"]["breadth"]["unresolved"].append("T0000"), "classification"),
    (lambda v: v["extras"]["evidence"]["members"]["NEW"].update(selected_history_sessions=1000), "selected_observation"),
    (lambda v: v["extras"]["resolution"]["price_source"].update(NEW="primary_breadth"), "resolution"),
    (lambda v: v["extras"]["evidence"]["members"]["NEW"].update(supplied_primary_qualified=True), "selected_observation"),
    (lambda v: v["extras"].update(status="partial"), "status"),
    (lambda v: v["source_captures"]["membership"].update(captured_at=(PUBLISHED + timedelta(days=1)).isoformat()), "source_capture"),
    (lambda v: v["prior"].update(captured_at=PUBLISHED.isoformat()), "source_capture"),
])
def test_semantics_are_recomputed_from_captured_values(encoded, mutation, code):
    _receipt(encoded, mutation)
    with pytest.raises(ValueError, match=code):
        _validate(encoded)


def test_preparation_and_publication_do_not_relabel_the_next_session(encoded):
    late = NOW + timedelta(days=1)
    assert _validate(encoded, now=late, require_current=False).source_session == SOURCE
    with pytest.raises(ValueError, match="clock|target"):
        _validate(encoded, now=late, require_current=True)
    with pytest.raises(ValueError, match="clock|target"):
        _validate(encoded, now=late, published=late)


def test_supplied_derived_extras_panel_must_equal_replay(sources):
    changed = dict(sources)
    panel = sources["extras"].resolved_panel.copy()
    panel.iloc[-1, 0] += 1
    changed["extras"] = replace(sources["extras"], resolved_panel=panel)
    with pytest.raises(ValueError, match="supplied_extras_panel"):
        contract.encode_breadth_member_acquisitions(**changed)


def test_live_reference_requires_actual_current_adjusted_observations(sources):
    changed = dict(sources)
    frame = pd.DataFrame({"close": 30 + np.arange(70) / 10}, index=_dates(70))
    changed["reference_frames"] = {"IBIT": frame}
    changed["reference_evidence"] = {"IBIT": {"status": "available", "basis": "provider_auto_adjusted",
        "source_ref": "fixture-reference-capture", "captured_at": (NOW + timedelta(seconds=2)).isoformat()}}
    encoded = contract.encode_breadth_member_acquisitions(**changed)
    read = _validate(encoded)
    assert read.references["IBIT"] is not None
    assert compute_baskets_from_inputs(read.basket_inputs())["baskets"][0]["reference"]["label"] == "QQQ+IBIT"
    changed["reference_frames"] = {"IBIT": frame.iloc[:-1]}
    with pytest.raises(ValueError, match="unqualified"):
        contract.encode_breadth_member_acquisitions(**changed)


def test_private_reference_cannot_override_a_captured_yahoo_member(sources):
    changed = dict(sources)
    changed["reference_frames"] = {"QQQ": sources["yahoo"].cohort.frames["QQQ"][["close"]], "IBIT": None}
    with pytest.raises(ValueError, match="reference_population"):
        contract.encode_breadth_member_acquisitions(**changed)


def test_shared_merge_matches_legacy_wrapper_and_preserves_labels(tmp_path):
    dates = _dates(8)
    a = pd.DataFrame({"MIG": [10., 11., 12., 13., 14., 15., np.nan, np.nan],
                      "SAME": range(20, 28)}, index=dates)
    b = pd.DataFrame({"MIG": [np.nan, 11., 12., 13., 14., 15., 16., 17.]}, index=dates)
    for group, frame in (("breadth", a), ("smallcap_breadth", b)):
        (tmp_path / group).mkdir()
        frame.to_parquet(tmp_path / group / "_closes_cache.parquet")
    from tests.fixtures.base_closes_merge_519b import merge_close_caches as base_merge
    legacy, old_receipt = base_merge(BROAD_GROUPS, data_dir=tmp_path)
    pure, receipt = merge_captured_close_caches({"breadth": a, "smallcap_breadth": b}, BROAD_GROUPS)
    pd.testing.assert_frame_equal(legacy, pure)
    assert old_receipt == receipt
    assert receipt["source"]["MIG"] == "smallcap_breadth"
    assert receipt["stitched"] == {}  # fresh leg has more observations; no donor needed


def test_receipt_unique_keys_and_json_bounds(encoded):
    raw = encoded.members["acquisition.json"]
    encoded.members["acquisition.json"] = raw[:-1] + b',"schema":"sector_breadth_members.v1"}'
    with pytest.raises(ValueError, match="duplicate"):
        _validate(encoded)


def _publish_with_dependency(tmp_path, encoded):
    yo = _owner(tmp_path, NOW + timedelta(seconds=1))
    snapshot = encoded.yahoo.snapshot
    base = yahoo_contract.EncodedYahooInputs(dict(snapshot.members),
                                             deepcopy(dict(snapshot.manifest["input_identity"])))
    first = yo.publish_yahoo_inputs(base, generation_id=snapshot.generation_id,
        source_revision=REVISION, expected_current_content_id=None)
    assert first.status == "published" and first.content_id == snapshot.content_id
    owner = _owner(tmp_path)
    broad = owner.publish_breadth_member_inputs(encoded, generation_id="broad-g1",
        source_revision=REVISION, expected_current_content_id=None)
    assert broad.status == "published", broad.detail
    newer = _owner(tmp_path, PUBLISHED + timedelta(seconds=1)).publish_yahoo_inputs(base,
        generation_id="yahoo-g2", source_revision=REVISION, expected_current_content_id=first.content_id)
    assert newer.status == "published"
    return owner, broad, first, newer


def test_recovery_after_yahoo_advance_reads_exact_retained_dependency(tmp_path, encoded, monkeypatch):
    owner, broad, old_yahoo, new_yahoo = _publish_with_dependency(tmp_path, encoded)
    root = owner.state_dir / "generations"
    # A damaged latest Yahoo pointer must not prevent verification of the old
    # dependency. The read neither uses nor repairs that pointer.
    pointer = root / yahoo_contract.YAHOO_GENERATION_DOMAIN / "current.json"
    pointer.write_text("invalid latest pointer")
    before = pointer.read_bytes()
    original_read = publisher._read_json_state
    import os
    from pathlib import Path
    parent_stat = pointer.parent.stat()
    def guarded(path, **kwargs):
        descriptor = kwargs.get("dir_fd")
        directory = os.fstat(descriptor) if descriptor is not None else None
        same_directory = directory is not None and (directory.st_dev, directory.st_ino) == (parent_stat.st_dev, parent_stat.st_ino)
        if Path(path) == pointer or (Path(path).name == pointer.name and same_directory):
            raise AssertionError("Latest Yahoo pointer was reopened")
        return original_read(path, **kwargs)
    monkeypatch.setattr(publisher, "_read_json_state", guarded)
    read = contract.read_verified_breadth_member_inputs(generations_root=root,
                                                       now=PUBLISHED + timedelta(seconds=2))
    assert read.snapshot.content_id == broad.content_id
    assert read.inputs.receipt["yahoo"]["content_id"] == old_yahoo.content_id
    assert read.inputs.receipt["yahoo"]["content_id"] != new_yahoo.content_id
    assert pointer.read_bytes() == before
    assert read.inputs.receipt["yahoo"]["published_at"] == (NOW + timedelta(seconds=1)).isoformat()


def test_retained_dependency_original_publication_clock_is_bound(tmp_path, encoded):
    owner, _, _, _ = _publish_with_dependency(tmp_path, encoded)
    root = owner.state_dir / "generations"
    path = root / yahoo_contract.YAHOO_GENERATION_DOMAIN / "yahoo-g1" / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["published_at"] = (NOW + timedelta(seconds=2)).isoformat()
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="dependency"):
        contract.read_verified_breadth_member_inputs(generations_root=root,
                                                     now=PUBLISHED + timedelta(seconds=2))


@pytest.mark.parametrize("change", [
    {"generation_id": "../elsewhere"}, {"generation_id": "current.json"},
    {"generation_id": "yahoo-g1\n"}, {"content_id": "f" * 64},
    {"domain": "../outside"}, {"members": ["yahoo/SPY.parquet", "yahoo/SPY.parquet"]},
])
def test_retained_facade_refuses_bad_identity_without_selection_fallback(tmp_path, encoded, change):
    owner, _, prior, _ = _publish_with_dependency(tmp_path, encoded)
    args = dict(generations_root=owner.state_dir / "generations",
        domain=yahoo_contract.YAHOO_GENERATION_DOMAIN, generation_id="yahoo-g1",
        content_id=prior.content_id, members=yahoo_contract.YAHOO_GENERATION_MEMBERS)
    args.update(change)
    with pytest.raises(publisher.SelectedGenerationUnavailable):
        publisher.read_retained_generation(**args)


def test_retained_facade_refuses_symlink_ancestors_and_relative_root(tmp_path, encoded):
    owner, _, prior, _ = _publish_with_dependency(tmp_path, encoded)
    alias = tmp_path / "alias"
    alias.symlink_to(owner.state_dir)
    for root in (alias / "generations", "relative-generations"):
        with pytest.raises(publisher.SelectedGenerationUnavailable):
            publisher.read_retained_generation(generations_root=root,
                domain=yahoo_contract.YAHOO_GENERATION_DOMAIN, generation_id="yahoo-g1",
                content_id=prior.content_id, members=yahoo_contract.YAHOO_GENERATION_MEMBERS)


def test_shared_private_staging_detaches_identity_before_member_writes(tmp_path, encoded, monkeypatch):
    owner = _owner(tmp_path)
    original_stage = owner._publish_private_members
    def mutate_after_prepare(captured, request, **kwargs):
        encoded.input_identity["sector_breadth_members"]["source_session"] = "2099-01-01"
        encoded.members["baskets/membership.json"] = b"{}"
        return original_stage(captured, request, **kwargs)
    monkeypatch.setattr(owner, "_publish_private_members", mutate_after_prepare)
    result = owner.publish_breadth_member_inputs(encoded, generation_id="detached",
        source_revision=REVISION, expected_current_content_id=None)
    assert result.status == "published", result.detail
    read = contract.read_verified_breadth_member_inputs(generations_root=owner.state_dir / "generations",
                                                       yahoo=encoded.yahoo, now=PUBLISHED)
    assert read.inputs.source_session == SOURCE
    assert "test_theme" in read.inputs.membership["baskets"]


@pytest.mark.parametrize("case", ("longest_donor", "basis_mismatch", "null_tail", "all_null", "legacy_normalize"))
def test_literal_base_merge_parity_across_price_selection_cases(tmp_path, case):
    from tests.fixtures.base_closes_merge_519b import merge_close_caches as base_merge
    dates = _dates(12)
    long = pd.DataFrame({"MIG": np.arange(12, dtype=float) + 100, "TIE": np.arange(12, dtype=float) + 200}, index=dates)
    long.iloc[-2:, 0] = np.nan
    short = pd.DataFrame({"MIG": np.arange(12, dtype=float) + 100}, index=dates)
    short.iloc[:5, 0] = np.nan
    mid = long.iloc[2:].copy()
    if case == "basis_mismatch":
        short *= 1.02
    elif case == "null_tail":
        for frame in (long, short, mid):
            frame.iloc[-1] = np.nan
            frame.iloc[-4] = np.nan
    elif case == "all_null":
        for frame in (long, short, mid):
            frame.iloc[:] = np.nan
    elif case == "legacy_normalize":
        long = pd.concat([long, long[["MIG"]]], axis=1).iloc[::-1]
    for group, frame in zip(BROAD_GROUPS, (long, short, mid)):
        (tmp_path / group).mkdir()
        # Pyarrow rejects duplicate parquet field names, as it should. Exercise
        # legacy index normalization while keeping on-disk columns representable.
        frame.loc[:, ~frame.columns.duplicated()].to_parquet(tmp_path / group / "_closes_cache.parquet")
    expected, prior_meta = base_merge(BROAD_GROUPS, data_dir=tmp_path)
    observed, meta = merge_close_caches(BROAD_GROUPS, data_dir=tmp_path)
    pd.testing.assert_frame_equal(expected, observed)
    assert prior_meta == meta
    if case == "longest_donor":
        assert meta["source"]["MIG"] == "smallcap_breadth"
        assert meta["stitched"]["MIG"][0] == "breadth"
    if case == "basis_mismatch":
        assert "MIG" not in meta["stitched"]


@pytest.mark.parametrize("number", (b"1e400", b"-1e400", b"NaN", b"Infinity"))
def test_membership_nonfinite_json_is_rejected_even_in_unscored_metadata(encoded, number):
    original = encoded.members["baskets/membership.json"]
    encoded.members["baskets/membership.json"] = original[:-1] + b',"annotation":' + number + b'}'
    with pytest.raises(ValueError, match="nonfinite_json"):
        _validate(encoded)


def test_complete_reference_mode_excludes_rows_with_only_one_leg_and_keeps_legacy_default():
    from engine.baskets import _proxy_returns_from_inputs
    dates = _dates(5)
    frames = {"LEFT": pd.DataFrame({"close": [1., 2., 3., 4., 5.]}, index=dates),
              "RIGHT": pd.DataFrame({"close": [np.nan, np.nan, 10., 11., 12.]}, index=dates)}
    legacy = _proxy_returns_from_inputs(["LEFT", "RIGHT"], dates, frames)
    complete = _proxy_returns_from_inputs(["LEFT", "RIGHT"], dates, frames, require_all=True)
    assert legacy.iloc[1:3].notna().all()
    assert complete.iloc[:3].isna().all()
    pd.testing.assert_series_equal(legacy.iloc[3:], complete.iloc[3:])
    frames["RIGHT"] = pd.DataFrame({"unrelated": [1.]}, index=dates[:1])
    assert _proxy_returns_from_inputs(["LEFT", "RIGHT"], dates, frames, require_all=True) is None


@pytest.mark.parametrize("change", ("content_id", "producer_revision"))
def test_encoder_recomputes_dependency_content_identity_using_incumbent_owner(sources, change):
    yahoo = sources["yahoo"]
    manifest = deepcopy(dict(yahoo.snapshot.manifest))
    if change == "content_id":
        manifest["content_id"] = "f" * 64
    else:
        manifest["source_revision"] = "e" * 40
        manifest["input_identity"]["yahoo_cohort"]["producer_source_sha"] = "e" * 40
    altered = replace(yahoo, snapshot=replace(yahoo.snapshot,
        manifest=manifest, content_id=manifest["content_id"]))
    with pytest.raises(ValueError, match="capture_content_mismatch"):
        contract.encode_breadth_member_acquisitions(**{**sources, "yahoo": altered})


def test_private_generation_supplies_sector_member_index_without_candle_fabrication(tmp_path, encoded, monkeypatch):
    from engine import basket_index, sector_cycles
    owner = _owner(tmp_path)
    result = owner.publish_breadth_member_inputs(encoded, generation_id="cycle-member-source",
        source_revision=REVISION, expected_current_content_id=None)
    assert result.status == "published", result.detail
    selected = contract.read_verified_breadth_member_inputs(generations_root=owner.state_dir / "generations",
                                                           yahoo=encoded.yahoo, now=PUBLISHED)
    with monkeypatch.context() as mp:
        for obj, name in ((config, "load"), (config, "data_dir"), (store, "read"),
                          (pd, "read_parquet"), (basket_index, "_load_member_ohlcv")):
            mp.setattr(obj, name, forbidden)
        candle, evidence = sector_cycles.member_candle_from_captured_inputs(
            selected.inputs.membership["baskets"]["test_theme"]["members"], captured=selected.inputs)
    assert candle is not None and len(candle.close) == 319
    assert str(candle.close.index[-1].date()) == SOURCE
    assert candle.coverage_pct == .75 and candle.n_live == 4
    assert evidence["volume_unavailable"] == ["NEW"]
    assert evidence["range_fields"] == "not_supplied"
    assert evidence["member_observation_session"] == SOURCE
    assert not hasattr(candle, "open") and not hasattr(candle, "high")


def test_member_source_mapping_does_not_borrow_volume_for_donated_or_different_closes(encoded):
    captured = _validate(encoded)
    # Isolated value-mapping counterexample: a donated historical close exists
    # where the selected primary source lacks that close; its volume cannot be attached.
    groups = {g: {field: panel.copy() for field, panel in panels.items()} for g, panels in captured.groups.items()}
    first, second = captured.resolved_panel.index[:2]
    groups["breadth"]["close"].at[first, "T0000"] = np.nan
    groups["breadth"]["close"].at[second, "T0000"] *= 1.1
    mapped = replace(captured, groups=groups)
    close, volume, evidence = mapped.member_index_inputs(captured.membership["baskets"]["test_theme"]["members"])
    assert close.at[first, "T0000"] > 0
    assert pd.isna(volume.at[first, "T0000"]) and pd.isna(volume.at[second, "T0000"])
    assert volume.at[close.index[-1], "T0000"] == 1000
    assert "NEW" not in volume


@pytest.mark.parametrize("removed_member_with_later_tape", [False, True])
def test_member_population_cannot_inherit_a_newer_unobserved_desk_tail(encoded, removed_member_with_later_tape):
    from engine.sector_cycles import member_candle_from_captured_inputs
    captured = _validate(encoded)
    panel = captured.resolved_panel.copy()
    panel.loc[panel.index[-4]:, ["T0000", "T0001", "T0002"]] = np.nan
    members = deepcopy(captured.membership["baskets"]["test_theme"]["members"][:3])
    if removed_member_with_later_tape:
        panel["NEW"] = np.linspace(10., 20., len(panel))
        members.append({"ticker": "NEW", "added": str(panel.index[0].date()),
                        "removed": str(panel.index[-20].date())})
    mapped = replace(captured, resolved_panel=panel)
    close, _, evidence = mapped.member_index_inputs(members)
    assert close.index[-1] == panel.index[-5]
    assert evidence["member_observation_session"] != evidence["bundle_source_session"]
    candle, current_evidence = member_candle_from_captured_inputs(members, captured=mapped)
    assert candle is None
    assert current_evidence["index_unavailable_reason"] == "member_population_session_mismatch"
    assert current_evidence["member_observation_session"] == str(panel.index[-5].date())


def test_thematic_capture_does_not_misclassify_an_uncaptured_amalgam_member(encoded):
    captured = _validate(encoded)
    assert "T0400" in captured.primary.columns
    with pytest.raises(contract.BreadthMemberContractError, match="uncaptured_member_index_population"):
        captured.member_index_inputs([{"ticker": "T0400", "added": "2025-01-01"}])



def _publish_current_pair(tmp_path, encoded):
    snapshot = encoded.yahoo.snapshot
    base = yahoo_contract.EncodedYahooInputs(dict(snapshot.members),
        deepcopy(dict(snapshot.manifest["input_identity"])))
    first = _owner(tmp_path, NOW + timedelta(seconds=1)).publish_yahoo_inputs(base,
        generation_id=snapshot.generation_id, source_revision=REVISION,
        expected_current_content_id=None)
    assert first.status == "published" and first.content_id == snapshot.content_id
    owner = _owner(tmp_path)
    broad = owner.publish_breadth_member_inputs(encoded, generation_id="broad-g1",
        source_revision=REVISION, expected_current_content_id=None)
    assert broad.status == "published", broad.detail
    return owner, first, broad


def test_sector_price_pair_reads_each_selection_once_without_ambient_fallback(tmp_path, encoded, monkeypatch):
    from lib.sector_input_capture import read_sector_price_captures
    owner, yahoo, broad = _publish_current_pair(tmp_path, encoded)
    original_read = publisher.read_selected_generation
    reads = []
    def read(**kwargs):
        reads.append(kwargs["domain"])
        return original_read(**kwargs)
    with monkeypatch.context() as mp:
        mp.setattr(publisher, "read_selected_generation", read)
        for obj, name in ((config, "load"), (config, "data_dir"), (store, "read"), (pd, "read_parquet")):
            mp.setattr(obj, name, forbidden)
        pair = read_sector_price_captures(generations_root=owner.state_dir / "generations", now=PUBLISHED)
        baskets = compute_baskets_from_inputs(pair.breadth.inputs.basket_inputs())
        lineage = pair.input_lineage()
    assert reads == [yahoo_contract.YAHOO_GENERATION_DOMAIN, contract.DOMAIN]
    assert pair.yahoo.snapshot.content_id == yahoo.content_id
    assert pair.breadth.snapshot.content_id == broad.content_id
    assert baskets["as_of"] == SOURCE
    assert lineage["yahoo"]["content_id"] == yahoo.content_id
    assert lineage["breadth_members"]["content_id"] == broad.content_id
    lineage["yahoo"]["member_sha256"]["SPY"] = "changed"
    assert pair.input_lineage()["yahoo"]["member_sha256"]["SPY"] != "changed"


def test_sector_price_pair_refuses_advanced_yahoo_instead_of_retained_fallback(tmp_path, encoded, monkeypatch):
    from lib.sector_input_capture import read_sector_price_captures
    owner, _, _, _ = _publish_with_dependency(tmp_path, encoded)
    original_read = publisher.read_selected_generation
    reads = []
    def read(**kwargs):
        reads.append(kwargs["domain"])
        return original_read(**kwargs)
    monkeypatch.setattr(publisher, "read_selected_generation", read)
    monkeypatch.setattr(publisher, "read_retained_generation", forbidden)
    with pytest.raises(ValueError, match="dependency"):
        read_sector_price_captures(generations_root=owner.state_dir / "generations",
                                   now=PUBLISHED + timedelta(seconds=2))
    assert reads == [yahoo_contract.YAHOO_GENERATION_DOMAIN, contract.DOMAIN]


def test_current_pair_refuses_old_cohort_while_explicit_recovery_remains_available(tmp_path, encoded, monkeypatch):
    from lib.sector_input_capture import read_sector_price_captures
    owner, first, broad = _publish_current_pair(tmp_path, encoded)
    root = owner.state_dir / "generations"
    later = PUBLISHED + timedelta(days=1)
    before = {str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mtime_ns)
              for p in root.rglob("*") if p.is_file()}
    reads = []
    original_read = publisher.read_selected_generation
    def read(**kwargs):
        reads.append(kwargs["domain"])
        return original_read(**kwargs)
    with monkeypatch.context() as mp:
        mp.setattr(publisher, "read_selected_generation", read)
        with pytest.raises(yahoo_contract.YahooGenerationContractError, match="^source_not_current_target$"):
            read_sector_price_captures(generations_root=root, now=later)
    assert reads == [yahoo_contract.YAHOO_GENERATION_DOMAIN]
    old = contract.read_verified_breadth_member_inputs(generations_root=root, now=later)
    assert old.snapshot.content_id == broad.content_id
    assert old.inputs.receipt["yahoo"]["content_id"] == first.content_id
    with pytest.raises(ValueError):
        contract.read_verified_breadth_member_inputs(generations_root=root, now=later, require_current=True)
    assert {str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()} == before
