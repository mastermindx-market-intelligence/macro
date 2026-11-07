"""Actual index populations and retained native dependencies; no provider traffic."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta
import hashlib
import json

import pandas as pd
import pytest

from lib import breadth_member_generation_contract as broad
from lib import member_ohlcv_generation_contract as candles
from lib import sector_index_membership_capture as indices
from lib import yahoo_generation_contract as yahoo_contract
from lib.sector_auxiliary_capture import CapturedAuxiliarySource
from scripts import fetch_basket_extras as extras
from tests.test_breadth_member_generation_contract import (
    sources, NOW, SOURCE, REVISION, PREPARED, PUBLISHED, CFG, YCFG, _dates, _owner,
)
from tests.test_member_ohlcv_generation_contract import (
    original, dependency, encoded, PUBLISHED as MEMBER_PUBLICATION,
)


def observed(document, family, *, stamp=NOW):
    raw = json.dumps(document, indent=2).encode()
    return CapturedAuxiliarySource("/captured/baskets_" + family + "/membership.json",
        None, stamp, "present", "observed", raw, len(raw), hashlib.sha256(raw).hexdigest())


def capture():
    documents = {
        "nasdaq": {"amalgamations": {"compute": {"name": "Compute", "members": [
            {"ticker": "INDEXONLY"}, {"ticker": "T0001", "added": "2025-01-01"}]}}},
        "russell": {"amalgamations": {"industry": {"name": "Industry", "members": [
            {"ticker": "INDEXONLY"}, {"ticker": "OLDIDX", "removed": "2026-11-03"}]}}},
    }
    return indices.capture_index_membership(
        {family: observed(document, family) for family, document in documents.items()}, before=NOW)


def test_index_union_keeps_actual_missing_added_and_separate_populations(sources):
    adjunct = capture()
    _, primary, _, _ = broad.derive_primary(
        {g: a.panels for g, a in sources["groups"].items()},
        sources["yahoo"].cohort.frames["SPY"], source_session=SOURCE)
    requested, active, end, populations = indices.index_population(adjunct, primary=primary, before=NOW)
    assert requested == {"INDEXONLY", "T0001", "OLDIDX"}
    assert active == {"INDEXONLY", "T0001"}
    assert end["OLDIDX"] < pd.Timestamp(SOURCE)
    assert populations["nasdaq"]["compute"] == ["INDEXONLY", "T0001"]
    documents, raw = indices.decode_index_membership(adjunct, before=NOW)
    assert "added" not in documents["nasdaq"]["amalgamations"]["compute"]["members"][0]
    assert raw["nasdaq"].decode() == adjunct["sources"]["nasdaq"]["content"]
    assert all(row["source_revision"] is None for row in adjunct["sources"].values())


@pytest.mark.parametrize("case", ["hash", "length", "future", "null", "extra_family",
                                  "duplicate", "bad_symbol", "bad_interval", "duplicate_json", "nonfinite"])
def test_index_capture_rejects_forged_or_malformed_observations(case):
    adjunct = capture()
    row = adjunct["sources"]["nasdaq"]
    if case == "hash":
        row["sha256"] = "0" * 64
    elif case == "length":
        row["byte_length"] += 1
    elif case == "future":
        row["captured_at"] = (NOW + timedelta(seconds=1)).isoformat()
    elif case == "null":
        adjunct = None
    elif case == "extra_family":
        adjunct["sources"]["invented"] = deepcopy(row)
    else:
        document = json.loads(row["content"])
        members = document["amalgamations"]["compute"]["members"]
        if case == "duplicate":
            members.append(deepcopy(members[0]))
        elif case == "bad_symbol":
            members[0]["ticker"] = "../escape"
        elif case == "bad_interval":
            members[0].update(added="2026-11-03", removed="2026-11-02")
        raw = (b'{"amalgamations":{},"amalgamations":{}}' if case == "duplicate_json" else
               b'{"amalgamations":{},"hidden":1e999}' if case == "nonfinite" else
               json.dumps(document).encode())
        row.update(content=raw.decode(), byte_length=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    with pytest.raises(ValueError, match="index_membership_"):
        indices.decode_index_membership(adjunct, before=NOW)


def acquired_with_indices(sources, monkeypatch, *, unresolved=False, aliases=None):
    adjunct = capture()
    _, primary, meta, _ = broad.derive_primary(
        {g: a.panels for g, a in sources["groups"].items()},
        sources["yahoo"].cohort.frames["SPY"], source_session=SOURCE)
    def download(names, **kwargs):
        frame = pd.DataFrame({t: 30. + pd.Series(range(len(primary)), index=primary.index)
                              for t in names}, index=primary.index)
        if unresolved and "INDEXONLY" in frame:
            frame.loc[SOURCE, "INDEXONLY"] = float("nan")
        return frame
    monkeypatch.setattr(extras, "_download_closes", download)
    acquired = extras.acquire_extras_from_inputs(
        membership=sources["membership"], primary_panel=primary, prior_extras=None,
        qualified_primary_members=frozenset(t for t, group in meta["source"].items()
                                             if t in sources["groups"][group].current),
        primary_history_threshold=252, evaluation_instant=NOW + timedelta(seconds=2),
        yahoo_config={"batch_size": 1000, "retries": 2, "backoff_base_s": 0},
        aliases={} if aliases is None else aliases, history_start="2023-01-01",
        primary_basis="provider_auto_adjusted", index_membership=adjunct)
    return acquired, adjunct


def test_index_only_close_reaches_same_generation_without_becoming_a_thematic_member(
        sources, monkeypatch, tmp_path):
    acquired, adjunct = acquired_with_indices(sources, monkeypatch)
    encoded_broad = broad.encode_breadth_member_acquisitions(
        **{**sources, "extras": acquired, "index_membership": adjunct})
    owner = _owner(tmp_path)
    publication = owner.publish_breadth_member_inputs(encoded_broad, generation_id="index-native",
        source_revision=REVISION, expected_current_content_id=None)
    assert publication.status == "published", publication.detail
    actual = broad.read_verified_breadth_member_inputs(generations_root=owner.state_dir / "generations",
        yahoo=encoded_broad.yahoo, now=PUBLISHED, require_current=True)
    assert set(actual.snapshot.members) == set(broad.MEMBERS)
    assert actual.inputs.membership == sources["membership"]
    assert "INDEXONLY" not in broad._membership(actual.inputs.membership, actual.inputs.primary)[0]
    assert "INDEXONLY" in actual.inputs.resolved_panel
    assert acquired.evidence["basket_populations"] == sources["extras"].evidence["basket_populations"]
    close, volume, facts = actual.inputs.member_index_inputs([{"ticker": "INDEXONLY"}])
    assert close["INDEXONLY"].dropna().index[-1] == pd.Timestamp(SOURCE)
    assert volume is None and facts["volume_unavailable"] == ["INDEXONLY"]
    assert facts["range_fields"] == "not_supplied"
    assert actual.inputs.receipt["index_membership"] == adjunct


def test_missing_index_observation_stays_unresolved(sources, monkeypatch):
    acquired, adjunct = acquired_with_indices(sources, monkeypatch, unresolved=True)
    encoded_broad = broad.encode_breadth_member_acquisitions(
        **{**sources, "extras": acquired, "index_membership": adjunct})
    actual = broad.validate_breadth_member_bundle(member_bytes=encoded_broad.members,
        input_identity=encoded_broad.input_identity, yahoo=encoded_broad.yahoo,
        published_at=PUBLISHED, now=PUBLISHED, source_revision=REVISION, computed_at=PREPARED.isoformat())
    assert acquired.status == "partial" and "INDEXONLY" in acquired.unresolved
    assert "INDEXONLY" not in actual.resolved_panel
    with pytest.raises(broad.BreadthMemberContractError, match="uncaptured_member_index_population"):
        actual.member_index_inputs([{"ticker": "INDEXONLY"}])


def test_index_alias_cannot_collapse_a_thematic_identity(sources, monkeypatch):
    with pytest.raises(ValueError, match="alias_collision"):
        acquired_with_indices(sources, monkeypatch, aliases={"INDEXONLY": "NEW"})


def test_index_evidence_cannot_be_relabelled_as_legacy(sources, monkeypatch):
    acquired, _ = acquired_with_indices(sources, monkeypatch)
    with pytest.raises(broad.BreadthMemberContractError, match="extras_membership_or_clock_mismatch"):
        broad.encode_breadth_member_acquisitions(**{**sources, "extras": acquired})


@pytest.mark.parametrize("case", ["missing_added", "duplicate", "interval", "missing_name"])
def test_native_thematic_preflight_refuses_before_any_download(sources, monkeypatch, case):
    inputs = {**sources, "membership": deepcopy(sources["membership"])}
    spec = inputs["membership"]["baskets"]["test_theme"]
    if case == "missing_added":
        del spec["members"][0]["added"]
    elif case == "duplicate":
        spec["members"].append(deepcopy(spec["members"][0]))
    elif case == "interval":
        spec["members"][0]["removed"] = spec["members"][0]["added"]
    else:
        del spec["name"]
    _, primary, _, _ = broad.derive_primary({g: a.panels for g, a in sources["groups"].items()},
        sources["yahoo"].cohort.frames["SPY"], source_session=SOURCE)
    def forbidden(*args, **kwargs):
        pytest.fail("malformed thematic input reached provider")
    monkeypatch.setattr(extras, "_download_closes", forbidden)
    with pytest.raises(broad.BreadthMemberContractError):
        extras.acquire_extras_from_inputs(membership=inputs["membership"], primary_panel=primary,
            prior_extras=None, qualified_primary_members=frozenset(), primary_history_threshold=252,
            evaluation_instant=NOW + timedelta(seconds=2), yahoo_config=YCFG, aliases={},
            history_start="2023-01-01", index_membership=capture())


@pytest.mark.parametrize("short", [False, True])
def test_native_cold_breadth_uses_policy_period_once_without_unbounded_repair(sources, short):
    from collectors.breadth import BreadthAdapter
    from lib import adjusted_price_capture as values
    original_group = sources["groups"]["breadth"]
    panels = {field: panel.iloc[-100:] if short else panel
              for field, panel in original_group.panels.items()}
    calls = []
    def download(symbols, period, **kwargs):
        calls.append(period)
        return values.AdjustedPriceCapture(panels,
            {t: (panels["close"].index[0], panels["close"].index[-1]) for t in symbols}, tuple(symbols))
    adapter = BreadthAdapter(breadth_config=CFG, yahoo_config=YCFG)
    adapter._download_adjusted_capture = download
    acquisition = adapter.acquire_adjusted_prices(members=original_group.members,
        prior_panels={field: None for field in values.FIELDS}, excluded_symbols=frozenset(),
        aliases={}, evaluation_instant=NOW + timedelta(seconds=2), period="4y")
    assert calls == ["4y"] and acquisition.accepted is (not short)
    assert acquisition.evidence["request"]["recovery_period"] is None
    if not short:
        encoded_broad = broad.encode_breadth_member_acquisitions(
            **{**sources, "groups": {**sources["groups"], "breadth": acquisition}})
        assert json.loads(encoded_broad.members["acquisition.json"])["groups"]["breadth"]["evidence"]["request"]["period"] == "4y"


def test_finite_cold_breadth_cannot_truncate_a_retained_archive(sources):
    from collectors.breadth import BreadthAdapter
    original_group = sources["groups"]["breadth"]
    adapter = BreadthAdapter(breadth_config=CFG, yahoo_config=YCFG)
    adapter._download_adjusted_capture = lambda *a, **kw: pytest.fail("retained prior reached cold downloader")
    with pytest.raises(ValueError, match="finite_cold_period_requires_empty_prior"):
        adapter.acquire_adjusted_prices(members=original_group.members,
            prior_panels=original_group.panels, excluded_symbols=frozenset(), aliases={},
            evaluation_instant=NOW + timedelta(seconds=2), period="4y")


def test_member_prior_recovers_exact_retained_pair_after_current_pointers_advance(encoded, tmp_path):
    yahoo = encoded.yahoo
    yencoded = yahoo_contract.EncodedYahooInputs(dict(yahoo.snapshot.members),
                                                dict(yahoo.snapshot.manifest["input_identity"]))
    yowner = _owner(tmp_path, datetime.fromisoformat(yahoo.snapshot.published_at))
    yp = yowner.publish_yahoo_inputs(yencoded, generation_id=yahoo.snapshot.generation_id,
        source_revision=REVISION, expected_current_content_id=None)
    assert yp.status == "published" and yp.content_id == yahoo.snapshot.content_id
    breadth = encoded.breadth
    bencoded = broad.EncodedBreadthMemberInputs(dict(breadth.snapshot.members),
        dict(breadth.snapshot.manifest["input_identity"]), yahoo)
    bowner = _owner(tmp_path, datetime.fromisoformat(breadth.snapshot.published_at))
    bp = bowner.publish_breadth_member_inputs(bencoded, generation_id=breadth.snapshot.generation_id,
        source_revision=REVISION, expected_current_content_id=None)
    assert bp.status == "published" and bp.content_id == breadth.snapshot.content_id
    owner = _owner(tmp_path, MEMBER_PUBLICATION)
    mp = owner.publish_member_ohlcv_inputs(encoded, generation_id="member-old-pair",
        source_revision=REVISION, expected_current_content_id=None)
    assert mp.status == "published", mp.detail
    advanced = _owner(tmp_path, MEMBER_PUBLICATION + timedelta(seconds=1))
    yp2 = advanced.publish_yahoo_inputs(yencoded, generation_id="yahoo-advanced",
        source_revision=REVISION, expected_current_content_id=yp.content_id)
    bp2 = advanced.publish_breadth_member_inputs(bencoded, generation_id="breadth-advanced",
        source_revision=REVISION, expected_current_content_id=bp.content_id)
    assert yp2.status == bp2.status == "published"
    root = owner.state_dir / "generations"
    later = MEMBER_PUBLICATION + timedelta(days=1)
    recovered = candles.read_verified_member_ohlcv_inputs(generations_root=root, now=later)
    assert recovered.snapshot.content_id == mp.content_id
    assert recovered.inputs.receipt["breadth"]["content_id"] == bp.content_id
    assert recovered.prior_capture(captured_at=later).captured_at == later
    with pytest.raises(ValueError):
        candles.read_verified_member_ohlcv_inputs(generations_root=root, now=later, require_current=True)
    wrong_breadth = broad.read_verified_breadth_member_inputs(generations_root=root, now=later)
    with pytest.raises(candles.MemberOHLCVContractError, match="dependency_mismatch"):
        candles.read_verified_member_ohlcv_inputs(generations_root=root, now=later,
            breadth=wrong_breadth, yahoo=yahoo)
    old = root / broad.DOMAIN / breadth.snapshot.generation_id / "acquisition.json"
    old.write_bytes(b"corrupt")
    with pytest.raises(Exception):
        candles.read_verified_member_ohlcv_inputs(generations_root=root, now=later)
