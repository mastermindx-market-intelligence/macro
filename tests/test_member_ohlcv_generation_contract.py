"""Genuine captured candles through the incumbent private publisher; no provider traffic."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
from types import MappingProxyType

import numpy as np
import pandas as pd
import pytest

from collectors.yahoo import YahooRequestSettings
from lib import adjusted_price_capture as values, config, store
from lib import breadth_member_generation_contract as broad
from lib import member_ohlcv_generation_contract as contract
from lib.sector_input_capture import SectorPriceCaptures, read_sector_member_ohlcv_capture
from scripts import fetch_basket_ohlcv as fetch, vps_live_orchestrator as publisher
from tests.test_breadth_member_generation_contract import (
    sources, original, NOW, SOURCE, REVISION, PUBLISHED as BROAD_PUBLICATION, _dates, _owner, forbidden,
)

EVALUATION = NOW + timedelta(seconds=5)
PREPARED = NOW + timedelta(seconds=6)
PUBLISHED = NOW + timedelta(seconds=7)
POLICY = YahooRequestSettings.capture({"batch_size": 4, "retries": 1, "backoff_base_s": 0,
                                     "upsert_basis_tol": .001})


@pytest.fixture(scope="module")
def dependency(original, tmp_path_factory):
    owner = _owner(tmp_path_factory.mktemp("ohlcv-breadth"), BROAD_PUBLICATION)
    result = owner.publish_breadth_member_inputs(original, generation_id="broad-for-candles",
        source_revision=REVISION, expected_current_content_id=None)
    assert result.status == "published", result.detail
    capture = broad.read_verified_breadth_member_inputs(generations_root=owner.state_dir / "generations",
        yahoo=original.yahoo, now=EVALUATION, require_current=True)
    return capture, original.yahoo


def frame(count=7, offset=0, end=None):
    index = _dates(count) if end is None else _dates(count + 1)[:-1]
    close = np.arange(len(index), dtype=float) + 100 + offset
    return pd.DataFrame({"open": close - .25, "high": close + 2, "low": close - 2,
                         "close": close, "volume": close * 0 + 1000}, index=index)


def population(dependency):
    breadth, _ = dependency
    return broad._membership(breadth.inputs.membership, breadth.inputs.primary)[0]


def prior_capture(frames=None):
    if frames is None:
        raw = {name: None for name in contract.PANEL_MEMBERS}
    else:
        panels = fetch._capture_ohlcv_frames(frames, requested=tuple(frames), source_session=SOURCE)
        raw = {name: broad.encode_panel(panels[field], field=field, source_session=SOURCE)
               for field, name in zip(values.OHLCV_FIELDS, contract.PANEL_MEMBERS)}
    return contract.MemberOHLCVPriorCapture(raw, "fixture-observed-prior", "b" * 40, SOURCE,
                                            BROAD_PUBLICATION)


def acquire(dependency, fresh=None, prior_frames=None, excluded=frozenset(), aliases=None):
    requested = population(dependency)
    if fresh is None:
        fresh = {t: frame(offset=i * 10) for i, t in enumerate(requested)}
    old = {} if prior_frames is None else {t: value for t, value in prior_frames.items() if t in requested}
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(fetch, "_download_ohlcv", lambda names, **kwargs: deepcopy(fresh))
        return fetch.acquire_ohlcv_from_inputs(requested=requested, prior_frames=old,
            aliases={} if aliases is None else aliases, excluded_symbols=excluded,
            request_settings=POLICY, history_start="2014-01-01", evaluation_instant=EVALUATION)


def encode(dependency, acquisition=None, prior=None):
    breadth, yahoo = dependency
    return contract.encode_member_ohlcv_acquisition(
        acquisition=acquire(dependency) if acquisition is None else acquisition,
        breadth=breadth, yahoo=yahoo, prior=prior_capture() if prior is None else prior,
        policy_capture={"source_ref": "fixture-effective-config", "source_revision": "b" * 40,
                        "captured_at": BROAD_PUBLICATION.isoformat()},
        prepared_at=PREPARED, source_revision=REVISION)


@pytest.fixture
def encoded(dependency):
    item = encode(dependency)
    return replace(item, members=dict(item.members), input_identity=deepcopy(dict(item.input_identity)))


def validate(item, *, now=PUBLISHED, published=PUBLISHED, require_current=True, prior=True):
    return contract.validate_member_ohlcv_bundle(member_bytes=item.members,
        input_identity=item.input_identity, breadth=item.breadth, yahoo=item.yahoo,
        published_at=published, now=now, source_revision=REVISION, computed_at=PREPARED.isoformat(),
        require_current=require_current, prior=item.prior if prior else None)


def receipt(item, change):
    data = json.loads(item.members["acquisition.json"])
    change(data)
    raw = broad._json_bytes(data)
    item.members["acquisition.json"] = raw
    item.input_identity["sector_member_ohlcv"]["acquisition_sha256"] = hashlib.sha256(raw).hexdigest()


def test_real_private_publication_and_existing_price_pair_binding(tmp_path, encoded, monkeypatch):
    owner = _owner(tmp_path, PUBLISHED)
    with monkeypatch.context() as mp:
        for obj, name in ((config, "load"), (config, "data_dir"), (store, "read"),
                          (pd, "read_parquet"), (fetch, "_download_ohlcv")):
            mp.setattr(obj, name, forbidden)
        result = owner.publish_member_ohlcv_inputs(encoded, generation_id="candles-1",
            source_revision=REVISION, expected_current_content_id=None)
        assert result.status == "published", result.detail
        prices = SectorPriceCaptures(encoded.yahoo, encoded.breadth, EVALUATION)
        captured = read_sector_member_ohlcv_capture(prices=prices,
            generations_root=owner.state_dir / "generations", now=PUBLISHED)
    assert captured.snapshot.content_id == result.content_id
    assert len(captured.snapshot.members) == 6
    assert captured.inputs.receipt["acquisition"]["status"] == "complete"
    ticker = population((encoded.breadth, encoded.yahoo))[0]
    pd.testing.assert_frame_equal(captured.inputs.frames()[ticker], frame(), check_names=False, check_freq=False)
    assert captured.inputs.frames()[ticker]["open"].iloc[-1] != captured.inputs.frames()[ticker]["close"].iloc[-1]
    got = captured.inputs.frames()
    got[ticker].iloc[0, 0] = -1
    assert captured.inputs.frames()[ticker].iloc[0, 0] > 0
    previous = captured.prior_capture(captured_at=PUBLISHED)
    assert previous.snapshot.content_id == result.content_id


def test_failed_current_historical_and_archive_names_stay_distinct(dependency):
    names = population(dependency)
    old = {names[0]: frame(), "ARCHIVE": frame(count=10)}
    fresh = {names[0]: frame().drop(columns="open"), names[1]: frame(end="previous"),
             names[2]: frame(), names[3]: frame(count=1)}
    item = encode(dependency, acquire(dependency, fresh, old), prior_capture(old))
    actual = validate(item)
    acq = actual.receipt["acquisition"]
    assert names[0] in acq["retained"] and names[0] in acq["unresolved"]
    assert names[0] not in acq["current"]
    assert names[1] in acq["acquired"] and names[1] not in acq["current"]
    assert acq["evidence"]["members"][names[1]]["reason"] == "historical_only"
    assert acq["status"] == "partial"
    assert actual.receipt["archive_only"] == ["ARCHIVE"]
    assert "ARCHIVE" not in acq["requested"]
    pd.testing.assert_frame_equal(actual.frames(["ARCHIVE"])["ARCHIVE"], old["ARCHIVE"],
                                  check_names=False, check_freq=False)
    assert len(actual.frames([names[3]])[names[3]]) == 1


def test_excluded_policy_keeps_prior_without_current_claim(dependency):
    names = population(dependency)
    old = {names[0]: frame()}
    fresh = {t: frame() for t in names[1:]}
    item = encode(dependency, acquire(dependency, fresh, old, frozenset((names[0],))), prior_capture(old))
    acq = validate(item).receipt["acquisition"]
    assert acq["status"] == "complete"
    row = acq["evidence"]["members"][names[0]]
    assert row["excluded_by_captured_policy"] and row["prior_retained"]
    assert not row["current_acquisition"] and row["prior_qualification"] == "not_requalified"


@pytest.mark.parametrize("case", ["retained_value", "lost_prior_date", "archive_dropped", "prior_hash"])
def test_prior_retention_is_checked_on_exact_captured_bytes(dependency, case):
    names = population(dependency)
    old = {names[0]: frame(count=10), "ARCHIVE": frame(count=10)}
    if case == "lost_prior_date":
        acquisition = acquire(dependency)  # downloaded without the longer real prior
        with pytest.raises(ValueError, match="prior_observation_lost"):
            encode(dependency, acquisition, prior_capture(old))
        return
    acquisition = acquire(dependency, {t: frame() for t in names[1:]}, old)
    item = encode(dependency, acquisition, prior_capture(old))
    item = replace(item, members=dict(item.members), input_identity=deepcopy(dict(item.input_identity)))
    if case == "retained_value":
        key = "members/volume.parquet"
        panel = broad.decode_panel(item.members[key], field="volume", source_session=SOURCE)
        panel.iloc[0, panel.columns.get_loc(names[0])] += 1
        item.members[key] = broad.encode_panel(panel, field="volume", source_session=SOURCE)
    elif case == "archive_dropped":
        for field, key in zip(values.OHLCV_FIELDS, contract.PANEL_MEMBERS):
            panel = broad.decode_panel(item.members[key], field=field, source_session=SOURCE).drop(columns="ARCHIVE")
            item.members[key] = broad.encode_panel(panel, field=field, source_session=SOURCE)
        receipt(item, lambda d: d.update(archive_only=[]))
    else:
        receipt(item, lambda d: d["prior"]["members"]["members/open.parquet"].update(sha256="c" * 64))
    with pytest.raises(ValueError, match="retained_values_changed|archive_not_preserved|prior_identity"):
        validate(item)


@pytest.mark.parametrize("change,code", [
    (lambda d: d["acquisition"]["evidence"]["members"]["NEW"]["selected_fields"]["open"].update(count=999), "selected_observation"),
    (lambda d: d["acquisition"].update(current=[]), "classification|currentness"),
    (lambda d: d["acquisition"].update(status="unavailable"), "status"),
    (lambda d: d["acquisition"]["evidence"]["unknown"].update(provider_available_at="2026-11-03"), "unknown_clock"),
    (lambda d: d["acquisition"]["evidence"]["members"]["NEW"].update(prior_qualification="current"), "retained_requalified"),
    (lambda d: d["breadth"].update(content_id="c" * 64), "input_identity|dependency"),
    (lambda d: d["acquisition"]["evidence"].update(evaluation_instant=(NOW + timedelta(days=1)).isoformat()), "evaluation_clock"),
    (lambda d: d["policy_capture"].update(captured_at=(PUBLISHED + timedelta(seconds=1)).isoformat()), "source_capture"),
    (lambda d: d["acquisition"]["evidence"]["members"]["NEW"].update(response_span=[SOURCE, "2026-11-04"]), "response_span"),
    (lambda d: d["acquisition"]["evidence"]["request"].update(minimum_repair_sessions=0), "request_policy"),
    (lambda d: d["acquisition"]["evidence"]["members"]["NEW"].update(vendor_symbol="0700.HK"), "vendor_symbol"),
    (lambda d: d["acquisition"]["evidence"]["members"]["NEW"].update(vendor_symbol="T0000"), "duplicate_ohlcv_vendor"),
])
def test_receipt_cannot_relabel_actual_selected_values(encoded, change, code):
    receipt(encoded, change)
    with pytest.raises(ValueError, match=code):
        validate(encoded)


@pytest.mark.parametrize("field", values.OHLCV_FIELDS)
def test_actual_field_hole_cannot_be_called_current(encoded, field):
    key = f"members/{field}.parquet"
    panel = broad.decode_panel(encoded.members[key], field=field, source_session=SOURCE)
    panel.at[pd.Timestamp(SOURCE), "NEW"] = np.nan
    encoded.members[key] = broad.encode_panel(panel, field=field, source_session=SOURCE)
    with pytest.raises(ValueError, match="selected_observation"):
        validate(encoded)


def test_impossible_candle_rejected_jointly(encoded):
    key = "members/open.parquet"
    panel = broad.decode_panel(encoded.members[key], field="open", source_session=SOURCE)
    panel.iloc[-1, 0] = 1e9
    encoded.members[key] = broad.encode_panel(panel, field="open", source_session=SOURCE)
    with pytest.raises(ValueError, match="panel_values"):
        validate(encoded)


def test_bundle_allocation_checked_before_any_panel_decode(encoded, monkeypatch):
    monkeypatch.setattr(contract, "MAX_DECODE_BYTES", 1)
    monkeypatch.setattr(broad, "decode_panel", forbidden)
    with pytest.raises(ValueError, match="decode_bound"):
        contract._panels(encoded.members, SOURCE)


def test_exact_breadth_bytes_override_mutable_derived_values(encoded):
    before = encoded.breadth.inputs.membership["baskets"]["test_theme"]["name"]
    original_value = encoded.breadth.inputs.primary.iloc[0, 0]
    encoded.breadth.inputs.membership["baskets"]["test_theme"]["name"] = "mutated"
    encoded.breadth.inputs.primary.iloc[0, 0] = -1
    try:
        assert validate(encoded).source_session == SOURCE
    finally:
        encoded.breadth.inputs.membership["baskets"]["test_theme"]["name"] = before
        encoded.breadth.inputs.primary.iloc[0, 0] = original_value


def test_changed_breadth_bytes_fail_before_use(encoded):
    snapshot = encoded.breadth.snapshot
    raw = dict(snapshot.members)
    raw["baskets/membership.json"] += b" "
    altered = replace(snapshot, members=raw)
    item = replace(encoded, breadth=replace(encoded.breadth, snapshot=altered))
    with pytest.raises(ValueError, match="capture_content"):
        validate(item)


def test_delayed_republication_refused_and_previous_selection_retained(tmp_path, encoded):
    owner = _owner(tmp_path, PUBLISHED)
    first = owner.publish_member_ohlcv_inputs(encoded, generation_id="candles-1",
        source_revision=REVISION, expected_current_content_id=None)
    assert first.status == "published"
    late = _owner(tmp_path, NOW + timedelta(days=3))
    result = late.publish_member_ohlcv_inputs(encoded, generation_id="candles-1",
        source_revision=REVISION, expected_current_content_id=first.content_id)
    assert result.status == "rejected"
    selected = publisher.read_selected_generation(generations_root=owner.state_dir / "generations",
                                                   domain=contract.DOMAIN, members=contract.MEMBERS)
    assert selected.content_id == first.content_id and selected.published_at == first.published_at
    captured = contract.read_verified_member_ohlcv_inputs(generations_root=owner.state_dir / "generations",
        now=NOW + timedelta(days=3), breadth=encoded.breadth, yahoo=encoded.yahoo, require_current=False)
    assert captured.inputs.source_session == SOURCE
    with pytest.raises(ValueError):
        read_sector_member_ohlcv_capture(
            prices=SectorPriceCaptures(encoded.yahoo, encoded.breadth, EVALUATION),
            generations_root=owner.state_dir / "generations", now=NOW + timedelta(days=3))


def test_same_owner_cas_refuses_stale_selection(tmp_path, encoded):
    owner = _owner(tmp_path, PUBLISHED)
    first = owner.publish_member_ohlcv_inputs(encoded, generation_id="candles-1",
        source_revision=REVISION, expected_current_content_id=None)
    assert first.status == "published"
    other = owner.publish_member_ohlcv_inputs(encoded, generation_id="candles-2",
        source_revision=REVISION, expected_current_content_id=None)
    assert other.status == "rejected"
    selected = publisher.read_selected_generation(generations_root=owner.state_dir / "generations",
                                                   domain=contract.DOMAIN, members=contract.MEMBERS)
    assert selected.content_id == first.content_id


def test_verified_generation_prior_retains_original_publication_identity(tmp_path, encoded, dependency):
    owner = _owner(tmp_path, PUBLISHED)
    result = owner.publish_member_ohlcv_inputs(encoded, generation_id="candles-prior",
        source_revision=REVISION, expected_current_content_id=None)
    assert result.status == "published"
    capture = contract.read_verified_member_ohlcv_inputs(generations_root=owner.state_dir / "generations",
        now=PUBLISHED, breadth=encoded.breadth, yahoo=encoded.yahoo)
    prior = capture.prior_capture(captured_at=PUBLISHED)
    panels, identity, _ = contract._prior(prior, before=PUBLISHED, source=SOURCE)
    assert identity["kind"] == "generation"
    assert identity["content_id"] == result.content_id
    assert identity["published_at"] == result.published_at
    changed = dict(prior.members)
    changed["members/open.parquet"] += b" "
    with pytest.raises(ValueError, match="prior_snapshot"):
        contract._prior(replace(prior, members=changed), before=PUBLISHED, source=SOURCE)


@pytest.mark.parametrize("requested", [
    tuple(f"TOO{i}" for i in range(values.MAX_COLUMNS + 1)), ("NEW", "NEW"), ["NEW"], ("FOREIGN",),
])
def test_invalid_population_rejected_before_frame_allocation(dependency, monkeypatch, requested):
    acquisition = replace(acquire(dependency), requested=requested, frames={})
    monkeypatch.setattr(fetch, "_capture_ohlcv_frames", forbidden)
    with pytest.raises(ValueError, match="membership_population"):
        encode(dependency, acquisition)


def test_no_returned_candles_are_explicitly_unavailable(dependency):
    item = encode(dependency, acquire(dependency, fresh={}))
    actual = validate(item)
    assert actual.frames() == {}
    assert actual.receipt["acquisition"]["status"] == "unavailable"
    assert actual.receipt["acquisition"]["current"] == []
    assert set(actual.receipt["acquisition"]["unresolved"]) == set(population(dependency))
