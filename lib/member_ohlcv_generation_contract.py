"""Genuine member candles under the incumbent private generation publisher.

Encoding and reading do not acquire market data. Retention is checked against
captured prior bytes at publication; reading preserves that admission evidence
without recursively replaying the entire historical generation chain.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime
import hashlib
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pandas as pd

from lib import adjusted_price_capture as values
from lib import breadth_member_generation_contract as broad
from lib.yahoo_generation_contract import _instant, _session, _completed_target

DOMAIN = "sector-member-ohlcv"
SCHEMA = "sector_member_ohlcv.v1"
PANEL_MEMBERS = tuple(f"members/{field}.parquet" for field in values.OHLCV_FIELDS)
MEMBERS = PANEL_MEMBERS + ("acquisition.json",)
MAX_MEMBER_BYTES = broad.MAX_MEMBER_BYTES
MAX_BUNDLE_BYTES = 384 * 1024 * 1024
MAX_DECODE_BYTES = 256 * 1024 * 1024


class MemberOHLCVContractError(ValueError):
    """Closed domain error; paths, credentials and responses are not attached."""


def _error(code):
    raise MemberOHLCVContractError(code)


@dataclass(frozen=True)
class MemberOHLCVPriorCapture:
    """Explicit canonical prior bytes or observed absence, never implicit loading."""
    members: Mapping[str, bytes | None]
    source_ref: str
    source_revision: str
    source_session: str
    captured_at: datetime
    snapshot: Any = None


@dataclass(frozen=True)
class EncodedMemberOHLCVInputs:
    members: Mapping[str, bytes]
    input_identity: Mapping[str, Any]
    breadth: broad.VerifiedBreadthMemberGeneration
    yahoo: Any
    prior: MemberOHLCVPriorCapture


@dataclass(frozen=True)
class CapturedMemberOHLCVInputs:
    source_session: str
    panels: Mapping[str, pd.DataFrame]
    receipt: Mapping[str, Any]

    def frames(self, tickers=None) -> dict[str, pd.DataFrame]:
        requested = self.receipt["acquisition"]["requested"] if tickers is None else tickers
        if (not isinstance(requested, (list, tuple)) or len(requested) > values.MAX_COLUMNS
                or len(set(requested)) != len(requested)
                or any(t not in self.panels["close"].columns for t in requested)):
            _error("uncaptured_member_population")
        return {ticker: frame for ticker in requested
                if not (frame := pd.DataFrame({field: self.panels[field][ticker].copy(deep=True)
                    for field in values.OHLCV_FIELDS}).dropna(how="all")).empty}


@dataclass(frozen=True)
class VerifiedMemberOHLCVGeneration:
    inputs: CapturedMemberOHLCVInputs
    snapshot: Any

    def prior_capture(self, *, captured_at):
        stamp = _instant(captured_at)
        if stamp < _instant(self.snapshot.published_at):
            _error("prior_capture_before_publication")
        return MemberOHLCVPriorCapture(
            MappingProxyType({name: self.snapshot.members[name] for name in PANEL_MEMBERS}),
            self.snapshot.generation_id, self.snapshot.manifest["source_revision"],
            self.inputs.source_session, stamp, self.snapshot)


def _member_set(raw):
    if (not isinstance(raw, Mapping) or set(raw) != set(MEMBERS)
            or any(type(data) is not bytes or not 0 < len(data) <= MAX_MEMBER_BYTES for data in raw.values())
            or sum(map(len, raw.values())) > MAX_BUNDLE_BYTES):
        _error("invalid_ohlcv_member_set")


def _snapshot_bytes(snapshot):
    raw = dict(snapshot.members)
    _member_set(raw)
    manifest = broad._copy(dict(snapshot.manifest))
    if (snapshot.domain != DOMAIN or manifest.get("domain") != DOMAIN
            or manifest.get("generation_id") != snapshot.generation_id
            or manifest.get("content_id") != snapshot.content_id
            or manifest.get("published_at") != snapshot.published_at):
        _error("ohlcv_capture_identity_mismatch")
    from scripts.vps_live_orchestrator import _generation_content_id
    artifacts = sorted(({"name": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                        for name, data in raw.items()), key=lambda row: row["name"])
    if (manifest.get("artifacts") != artifacts or _generation_content_id(
            domain=DOMAIN, generation_id=snapshot.generation_id, lane=manifest.get("lane"),
            source_revision=manifest.get("source_revision"), input_identity=manifest.get("input_identity"),
            captured=artifacts) != snapshot.content_id):
        _error("ohlcv_capture_content_mismatch")
    return raw, manifest


def _panels(raw, source):
    allocated = 0
    for name in PANEL_MEMBERS:
        try:
            with broad._open_panel(raw[name]) as parquet:
                allocated += parquet.metadata.num_rows * parquet.metadata.num_columns * 8
        except Exception:
            _error("ohlcv_panel_metadata_invalid")
    if allocated > MAX_DECODE_BYTES:
        _error("ohlcv_decode_bound")
    panels = {field: broad.decode_panel(raw[name], field=field, source_session=source)
              for field, name in zip(values.OHLCV_FIELDS, PANEL_MEMBERS)}
    reference = panels["close"]
    if any(not frame.index.equals(reference.index) or not frame.columns.equals(reference.columns)
           for frame in panels.values()):
        _error("ohlcv_panel_axes_mismatch")
    try:
        return values.capture_ohlcv_panels(panels, source_session=source)
    except values.AdjustedCaptureError:
        _error("ohlcv_panel_values_invalid")


def _prior(capture, *, before, source):
    if not isinstance(capture, MemberOHLCVPriorCapture):
        _error("explicit_ohlcv_prior_required")
    stamp = _instant(capture.captured_at)
    prior_source = _session(capture.source_session)
    broad._source_capture({"source_ref": capture.source_ref, "source_revision": capture.source_revision,
                           "captured_at": stamp.isoformat()}, before=before)
    if prior_source > source:
        _error("future_ohlcv_prior")
    raw = dict(capture.members)
    if (set(raw) != set(PANEL_MEMBERS) or any(data is not None and
            (type(data) is not bytes or not 0 < len(data) <= MAX_MEMBER_BYTES) for data in raw.values())
            or sum(len(data) for data in raw.values() if data is not None) > MAX_BUNDLE_BYTES):
        _error("invalid_ohlcv_prior_bytes")
    if any(data is None for data in raw.values()) and not all(data is None for data in raw.values()):
        _error("partial_ohlcv_prior_capture")
    if capture.snapshot is None:
        kind, content_id, publication = "bootstrap", None, None
    else:
        original, manifest = _snapshot_bytes(capture.snapshot)
        receipt = broad._json(original["acquisition.json"])
        if (any(raw[name] != original[name] for name in PANEL_MEMBERS)
                or capture.source_ref != capture.snapshot.generation_id
                or capture.source_revision != manifest["source_revision"]
                or prior_source != receipt.get("source_session")
                or _instant(capture.snapshot.published_at) > stamp):
            _error("ohlcv_prior_snapshot_mismatch")
        kind, content_id, publication = "generation", capture.snapshot.content_id, capture.snapshot.published_at
    panels = ({field: values.empty_panel() for field in values.OHLCV_FIELDS}
              if all(data is None for data in raw.values()) else _panels(raw, prior_source))
    identity = {"kind": kind, "domain": DOMAIN, "source_ref": capture.source_ref,
        "source_revision": capture.source_revision, "source_session": prior_source,
        "captured_at": stamp.isoformat(), "content_id": content_id, "published_at": publication,
        "members": {name: None if data is None else
            {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)} for name, data in raw.items()}}
    detached = replace(capture, members=MappingProxyType(raw), captured_at=stamp)
    return panels, identity, detached


def _prior_identity(value, *, before, source):
    if (not isinstance(value, dict) or set(value) != {"kind", "domain", "source_ref", "source_revision",
            "source_session", "captured_at", "content_id", "published_at", "members"}
            or value["domain"] != DOMAIN or value["kind"] not in ("bootstrap", "generation")):
        _error("invalid_ohlcv_prior_identity")
    broad._source_capture({key: value[key] for key in ("source_ref", "source_revision", "captured_at")},
                          before=before)
    if _session(value["source_session"]) > source:
        _error("future_ohlcv_prior")
    if value["kind"] == "bootstrap":
        if value["content_id"] is not None or value["published_at"] is not None:
            _error("invalid_ohlcv_prior_identity")
    elif (not isinstance(value["content_id"], str) or not broad._HEX.fullmatch(value["content_id"])
          or _instant(value["published_at"]) > _instant(value["captured_at"])):
        _error("invalid_ohlcv_prior_identity")
    members = value["members"]
    if not isinstance(members, dict) or set(members) != set(PANEL_MEMBERS):
        _error("invalid_ohlcv_prior_identity")
    for entry in members.values():
        if entry is None and value["kind"] == "bootstrap":
            continue
        if (not isinstance(entry, dict) or set(entry) != {"sha256", "bytes"}
                or not isinstance(entry["sha256"], str) or not broad._HEX.fullmatch(entry["sha256"])
                or type(entry["bytes"]) is not int or not 0 < entry["bytes"] <= MAX_MEMBER_BYTES):
            _error("invalid_ohlcv_prior_identity")
    if any(v is None for v in members.values()) and not all(v is None for v in members.values()):
        _error("partial_ohlcv_prior_capture")


def _breadth(value, yahoo, *, now, require_current):
    if not isinstance(value, broad.VerifiedBreadthMemberGeneration):
        _error("captured_breadth_required")
    return broad.verify_breadth_snapshot(value.snapshot, yahoo=yahoo, now=now,
                                        require_current=require_current)


def _dependency(value):
    snap = value.snapshot
    return {"domain": broad.DOMAIN, "generation_id": snap.generation_id, "content_id": snap.content_id,
        "source_revision": snap.manifest["source_revision"], "source_session": value.inputs.source_session,
        "published_at": snap.published_at,
        "members": {name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                    for name, data in snap.members.items()}}


def _observation(series):
    found = series.dropna()
    return {"count": len(found), "first": found.index[0].date().isoformat() if len(found) else None,
            "last": found.index[-1].date().isoformat() if len(found) else None}


def _observed(value, *, source):
    if (not isinstance(value, dict) or set(value) != {"count", "first", "last"}
            or type(value["count"]) is not int or not 0 <= value["count"] <= values.MAX_ROWS):
        _error("invalid_ohlcv_observation")
    if value["count"] == 0:
        if value["first"] is not None or value["last"] is not None:
            _error("invalid_ohlcv_observation")
    elif not _session(value["first"]) <= _session(value["last"]) <= source:
        _error("invalid_ohlcv_observation")


def _population(value, requested, name):
    if (not isinstance(value, list) or len(value) != len(set(value))
            or any(type(t) is not str or t not in requested for t in value)):
        _error("invalid_ohlcv_" + name)
    return set(value)


def _acquisition(receipt, panels, expected, *, prepared, source):
    from collectors.yahoo import YahooRequestSettings
    from lib import market_session
    acq = receipt["acquisition"]
    if (not isinstance(acq, dict) or set(acq) != {"status", "source_session", "requested",
            "acquired", "current", "retained", "unresolved", "evidence"}
            or acq["source_session"] != source):
        _error("invalid_ohlcv_acquisition")
    requested = acq["requested"]
    if (not isinstance(requested, list) or len(requested) != len(expected)
            or len(set(requested)) != len(requested) or set(requested) != set(expected)):
        _error("ohlcv_membership_population_mismatch")
    if any(not broad._SYMBOL.fullmatch(t) or market_session.cash_market_for_symbol(t) != "us" for t in requested):
        _error("ohlcv_requires_us_members")
    evidence = acq["evidence"]
    if (not isinstance(evidence, dict) or set(evidence) != {"evaluation_instant", "source_session", "market",
            "completed_sessions_only", "request", "current_session_shortfalls", "members", "unknown"}
            or evidence["source_session"] != source or evidence["market"] != "US"
            or evidence["completed_sessions_only"] is not True):
        _error("invalid_ohlcv_evidence")
    evaluation = _instant(evidence["evaluation_instant"])
    if evaluation > prepared or _completed_target(evaluation) != source:
        _error("ohlcv_evaluation_clock_mismatch")
    policy = evidence["request"]
    if (not isinstance(policy, dict) or set(policy) != {"history_start", "batch_size", "retries",
            "backoff_base_s", "basis_tolerance", "minimum_repair_sessions", "full_replacement",
            "allow_historical_replacement"} or policy["minimum_repair_sessions"] != 1
            or type(policy["minimum_repair_sessions"]) is not int or policy["full_replacement"] is not True
            or policy["allow_historical_replacement"] is not True or _session(policy["history_start"]) > source):
        _error("invalid_ohlcv_request_policy")
    YahooRequestSettings.capture({"batch_size": policy["batch_size"], "retries": policy["retries"],
        "backoff_base_s": policy["backoff_base_s"], "upsert_basis_tol": policy["basis_tolerance"]})
    if evidence["unknown"] != {
            "vendor_publication_clock": "Not supplied per bar by yfinance",
            "provider_available_at": "First retrievable time is not observed"}:
        _error("ohlcv_unknown_clock_claim_changed")
    members = evidence["members"]
    if not isinstance(members, dict) or set(members) != set(requested):
        _error("ohlcv_evidence_population_mismatch")
    acquired, current, retained, unresolved = (
        _population(acq[name], requested, name) for name in ("acquired", "current", "retained", "unresolved"))
    archive = receipt["archive_only"]
    if (not isinstance(archive, list) or archive != sorted(set(archive)) or set(archive) & set(requested)
            or set(panels["close"].columns) != set(requested) | set(archive)):
        _error("ohlcv_archive_population_mismatch")
    any_selected, vendors, active = set(), [], set()
    for ticker in requested:
        row = members[ticker]
        keys = {"vendor_symbol", "download_requested", "excluded_by_captured_policy", "accepted_replacement",
                "current_acquisition", "prior_retained", "unresolved_replacement", "reason",
                "acquisition_basis", "prior_qualification", "response_span", "observed_fields", "selected_fields"}
        if not isinstance(row, dict) or set(row) != keys:
            _error("invalid_ohlcv_member_evidence")
        vendor = row["vendor_symbol"]
        if (not isinstance(vendor, str) or not broad._SYMBOL.fullmatch(vendor)
                or market_session.cash_market_for_symbol(vendor) != "us"):
            _error("invalid_ohlcv_vendor_symbol")
        vendors.append(vendor)
        flags = ("download_requested", "excluded_by_captured_policy", "accepted_replacement",
                 "current_acquisition", "prior_retained", "unresolved_replacement")
        if any(type(row[k]) is not bool for k in flags):
            _error("invalid_ohlcv_boolean")
        if row["download_requested"] == row["excluded_by_captured_policy"]:
            _error("invalid_ohlcv_exclusion")
        if row["download_requested"]:
            active.add(ticker)
        selected = {field: _observation(panels[field][ticker]) for field in values.OHLCV_FIELDS}
        if row["selected_fields"] != selected:
            _error("ohlcv_selected_observation_mismatch")
        if any(item["count"] for item in selected.values()):
            any_selected.add(ticker)
        observed = row["observed_fields"]
        if not isinstance(observed, dict) or set(observed) != set(values.OHLCV_FIELDS):
            _error("invalid_ohlcv_observed_fields")
        for item in observed.values():
            _observed(item, source=source)
        span = row["response_span"]
        if span is not None and (not isinstance(span, list) or len(span) != 2
                or not _session(span[0]) <= _session(span[1]) <= source
                or any(item["count"] and not span[0] <= item["first"] <= item["last"] <= span[1]
                       for item in observed.values())):
            _error("invalid_ohlcv_response_span")
        for key, population in (("accepted_replacement", acquired), ("current_acquisition", current),
                                ("prior_retained", retained), ("unresolved_replacement", unresolved)):
            if row[key] != (ticker in population):
                _error("ohlcv_classification_mismatch")
        if row["acquisition_basis"] != ("provider_auto_adjusted" if ticker in acquired else None):
            _error("ohlcv_basis_mismatch")
        if row["prior_qualification"] != ("not_requalified" if ticker in retained else None):
            _error("ohlcv_retained_requalified")
        if ticker in acquired:
            tips = {v["last"] for v in selected.values()}
            if (not all(v["count"] for v in selected.values()) or len(tips) != 1
                    or observed != selected or span is None
                    or not pd.concat([panels[f][ticker] for f in values.OHLCV_FIELDS], axis=1).notna().all(axis=1).any()):
                _error("ohlcv_replacement_incomplete")
            at_target = tips == {source}
            if (ticker in current) != at_target or row["reason"] != ("full_history_request" if at_target else "historical_only"):
                _error("ohlcv_currentness_mismatch")
        elif row["reason"] != ("full_history_request" if row["download_requested"] else "excluded_by_captured_policy"):
            _error("ohlcv_replacement_reason_mismatch")
        if row["excluded_by_captured_policy"] and (span is not None or any(v["count"] for v in observed.values())):
            _error("excluded_ohlcv_response_claim")
    if len(set(vendors)) != len(vendors):
        _error("duplicate_ohlcv_vendor_mapping")
    if (not acquired <= active or current - acquired or unresolved != active - acquired
            or retained != any_selected - acquired
            or evidence["current_session_shortfalls"] != [t for t in requested if t in active - current]):
        _error("ohlcv_classification_mismatch")
    expected_status = "complete" if active and active == current else "partial" if any_selected else "unavailable"
    if acq["status"] != expected_status:
        _error("ohlcv_status_mismatch")
    return evaluation


def _retention(panels, prior, receipt):
    requested = set(receipt["acquisition"]["requested"])
    acquired = set(receipt["acquisition"]["acquired"])
    archive = sorted(set(prior["close"].columns) - requested)
    if receipt["archive_only"] != archive:
        _error("ohlcv_archive_not_preserved")
    for field in values.OHLCV_FIELDS:
        for ticker in panels[field]:
            selected = panels[field][ticker].dropna()
            old = prior[field][ticker].dropna() if ticker in prior[field] else pd.Series(index=pd.DatetimeIndex([]), dtype=float)
            if ticker in acquired:
                if not old.index.isin(selected.index).all():
                    _error("ohlcv_prior_observation_lost")
            elif not selected.equals(old):
                _error("ohlcv_retained_values_changed")


def validate_member_ohlcv_bundle(*, member_bytes, input_identity, breadth, yahoo,
        published_at, now, source_revision, computed_at, require_current=False, prior=None):
    _member_set(member_bytes)
    receipt = broad._json(member_bytes["acquisition.json"])
    if (not isinstance(receipt, dict) or set(receipt) != {"schema", "source_session", "prepared_at",
            "producer_source_sha", "breadth", "policy_capture", "prior", "archive_only", "acquisition"}
            or receipt["schema"] != SCHEMA):
        _error("invalid_ohlcv_receipt")
    expected_identity = {"sector_member_ohlcv": {"schema": SCHEMA, "source_session": receipt["source_session"],
        "prepared_at": receipt["prepared_at"], "producer_source_sha": receipt["producer_source_sha"],
        "breadth_content_id": receipt["breadth"].get("content_id"),
        "acquisition_sha256": hashlib.sha256(member_bytes["acquisition.json"]).hexdigest()}}
    if input_identity != expected_identity:
        _error("ohlcv_input_identity_mismatch")
    source = _session(receipt["source_session"])
    prepared, publication, admission = map(_instant, (receipt["prepared_at"], published_at, now))
    if (not isinstance(source_revision, str) or not broad._REVISION.fullmatch(source_revision)
            or receipt["producer_source_sha"] != source_revision or computed_at != receipt["prepared_at"]
            or not prepared <= publication <= admission or _completed_target(publication) != source
            or require_current and _completed_target(admission) != source):
        _error("ohlcv_publication_clock_or_revision_mismatch")
    dependency = _breadth(breadth, yahoo, now=admission, require_current=require_current)
    if receipt["breadth"] != _dependency(dependency) or dependency.inputs.source_session != source:
        _error("ohlcv_breadth_dependency_mismatch")
    expected, *_ = broad._membership(dependency.inputs.membership, dependency.inputs.primary)
    panels = _panels(member_bytes, source)
    evaluation = _acquisition(receipt, panels, expected, prepared=prepared, source=source)
    if _instant(dependency.snapshot.published_at) > evaluation:
        _error("ohlcv_dependency_after_acquisition")
    broad._source_capture(receipt["policy_capture"], before=evaluation)
    _prior_identity(receipt["prior"], before=evaluation, source=source)
    if prior is not None:
        old, identity, _ = _prior(prior, before=evaluation, source=source)
        if identity != receipt["prior"]:
            _error("ohlcv_prior_identity_mismatch")
        _retention(panels, old, receipt)
    return CapturedMemberOHLCVInputs(source, MappingProxyType(panels), MappingProxyType(receipt))


def encode_member_ohlcv_acquisition(*, acquisition, breadth, yahoo, prior,
                                    policy_capture, prepared_at, source_revision):
    from scripts.fetch_basket_ohlcv import BasketOHLCVAcquisition, _capture_ohlcv_frames
    if not isinstance(acquisition, BasketOHLCVAcquisition):
        _error("captured_ohlcv_acquisition_required")
    prepared = _instant(prepared_at)
    dependency = _breadth(breadth, yahoo, now=prepared, require_current=True)
    source = dependency.inputs.source_session
    if acquisition.source_session != source:
        _error("ohlcv_acquisition_source_mismatch")
    expected, *_ = broad._membership(dependency.inputs.membership, dependency.inputs.primary)
    if (not isinstance(acquisition.requested, tuple) or not 0 < len(acquisition.requested) <= values.MAX_COLUMNS
            or any(type(t) is not str for t in acquisition.requested)
            or len(set(acquisition.requested)) != len(acquisition.requested)
            or set(acquisition.requested) != set(expected)):
        _error("ohlcv_membership_population_mismatch")
    evidence = broad._copy(dict(acquisition.evidence))
    evaluation = _instant(evidence.get("evaluation_instant"))
    old, prior_identity, captured_prior = _prior(prior, before=evaluation, source=source)
    current = _capture_ohlcv_frames(acquisition.frames, requested=acquisition.requested, source_session=source)
    archive = sorted(set(old["close"].columns) - set(acquisition.requested))
    broad._bound_union([*current.values(), *old.values()])
    index = current["close"].index.union(old["close"].index).sort_values()
    names = sorted(set(acquisition.requested) | set(archive))
    if len(index) * (len(names) + 1) * 8 * len(values.OHLCV_FIELDS) > MAX_DECODE_BYTES:
        _error("ohlcv_decode_bound")
    panels = {field: current[field].reindex(index=index, columns=names) for field in values.OHLCV_FIELDS}
    for field in values.OHLCV_FIELDS:
        for ticker in archive:
            panels[field][ticker] = old[field][ticker].reindex(index)
    raw = {name: broad.encode_panel(panels[field], field=field, source_session=source)
           for field, name in zip(values.OHLCV_FIELDS, PANEL_MEMBERS)}
    receipt = {"schema": SCHEMA, "source_session": source, "prepared_at": prepared.isoformat(),
        "producer_source_sha": source_revision, "breadth": _dependency(dependency),
        "policy_capture": broad._copy(dict(policy_capture)), "prior": prior_identity,
        "archive_only": archive, "acquisition": {"status": acquisition.status,
            "source_session": acquisition.source_session,
            **{key: list(getattr(acquisition, key)) for key in
               ("requested", "acquired", "current", "retained", "unresolved")}, "evidence": evidence}}
    raw["acquisition.json"] = broad._json_bytes(receipt)
    identity = {"sector_member_ohlcv": {"schema": SCHEMA, "source_session": source,
        "prepared_at": prepared.isoformat(), "producer_source_sha": source_revision,
        "breadth_content_id": dependency.snapshot.content_id,
        "acquisition_sha256": hashlib.sha256(raw["acquisition.json"]).hexdigest()}}
    validate_member_ohlcv_bundle(member_bytes=raw, input_identity=identity, breadth=dependency, yahoo=yahoo,
        published_at=prepared, now=prepared, source_revision=source_revision, computed_at=prepared.isoformat(),
        require_current=True, prior=captured_prior)
    return EncodedMemberOHLCVInputs(MappingProxyType(raw), MappingProxyType(identity),
                                   dependency, yahoo, captured_prior)


def prepare_member_ohlcv_generation_request(*, sources, input_identity, breadth, yahoo, prior,
                                            generation_id, source_revision, lane):
    from scripts.vps_live_orchestrator import GenerationArtifact, GenerationRequest
    if (not isinstance(sources, Mapping) or set(sources) != set(MEMBERS)
            or not isinstance(generation_id, str) or not broad._REF.fullmatch(generation_id)):
        _error("invalid_ohlcv_generation_request")
    identity = broad._copy(dict(input_identity))
    declared = identity.get("sector_member_ohlcv", {})
    source, prepared = _session(declared.get("source_session")), declared.get("prepared_at")
    if declared.get("producer_source_sha") != source_revision:
        _error("ohlcv_producer_revision_mismatch")
    dependency = _breadth(breadth, yahoo, now=_instant(prepared), require_current=True)
    _, _, captured_prior = _prior(prior, before=prepared, source=source)
    if declared.get("breadth_content_id") != dependency.snapshot.content_id:
        _error("ohlcv_breadth_dependency_mismatch")

    def member_validator(name):
        def validate(path):
            try:
                if name in PANEL_MEMBERS:
                    broad.decode_panel(path.read_bytes(), field=name.split("/")[-1].removesuffix(".parquet"),
                                       source_session=source)
                else:
                    broad._json(path.read_bytes())
            except Exception as exc:
                return "ohlcv_member_rejected:" + type(exc).__name__
            return None
        return validate

    def validate_bundle(context):
        if (context.domain != DOMAIN or context.generation_id != generation_id
                or context.input_identity != identity or context.source_revision != source_revision
                or context.computed_at != prepared):
            return "ohlcv_identity_changed_during_admission"
        try:
            validate_member_ohlcv_bundle(member_bytes=context.members, input_identity=context.input_identity,
                breadth=dependency, yahoo=yahoo, prior=captured_prior, published_at=context.published_at,
                now=context.admission_time, source_revision=context.source_revision,
                computed_at=context.computed_at, require_current=True)
        except Exception as exc:
            return "ohlcv_semantic_rejected:" + type(exc).__name__
        return None

    return GenerationRequest(generation_id=generation_id, domain=DOMAIN, lane=lane,
        source_revision=source_revision, computed_at=prepared, input_identity=deepcopy(identity),
        artifacts=tuple(GenerationArtifact(name=name, source=Path(sources[name]),
            validator=member_validator(name)) for name in MEMBERS), bundle_validator=validate_bundle)


def read_verified_member_ohlcv_inputs(*, generations_root, now, breadth=None, yahoo=None,
                                     snapshot_reader=None, dependency_reader=None, require_current=False):
    """Read one selection, using supplied dependencies or its exact retained pair.

    Recovery uses actual current observation time and old publication identities.
    It never substitutes today's selected dependencies for a stale member prior.
    """
    from scripts.vps_live_orchestrator import read_selected_generation, read_retained_generation
    root = Path(generations_root)
    if not root.is_absolute():
        _error("absolute_private_root_required")
    snapshot = (snapshot_reader or read_selected_generation)(
        generations_root=root, domain=DOMAIN, members=MEMBERS)
    raw, manifest = _snapshot_bytes(snapshot)
    if (breadth is None) != (yahoo is None):
        _error("complete_dependency_pair_required")
    if breadth is None:
        receipt = broad._json(raw["acquisition.json"])
        dependency = receipt.get("breadth") if isinstance(receipt, dict) else None
        if (not isinstance(dependency, dict) or set(dependency) != {"domain", "generation_id", "content_id",
                "source_revision", "source_session", "published_at", "members"}
                or dependency["domain"] != broad.DOMAIN):
            _error("invalid_breadth_dependency")
        reader = dependency_reader or read_retained_generation
        pinned = reader(generations_root=root, domain=dependency["domain"],
            generation_id=dependency["generation_id"], content_id=dependency["content_id"], members=broad.MEMBERS)
        yahoo = broad.read_breadth_yahoo_dependency(snapshot=pinned, generations_root=root,
            now=now, dependency_reader=reader, require_current=require_current)
        breadth = broad.verify_breadth_snapshot(pinned, yahoo=yahoo, now=now, require_current=require_current)
    inputs = validate_member_ohlcv_bundle(member_bytes=raw, input_identity=manifest.get("input_identity"),
        breadth=breadth, yahoo=yahoo, published_at=snapshot.published_at, now=now,
        source_revision=manifest.get("source_revision"), computed_at=manifest.get("computed_at"),
        require_current=require_current)
    return VerifiedMemberOHLCVGeneration(inputs,
        replace(snapshot, manifest=MappingProxyType(manifest), members=MappingProxyType(raw)))
