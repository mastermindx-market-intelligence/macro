"""Private breadth/member values carried by the incumbent generation publisher.

This adapter owns a bounded domain contract, not acquisition, a scheduler,
selection, authentication, or another publication store. Its calculations reuse
the incumbent panel and basket owners on the exact captured member bytes.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any

import pandas as pd

from lib import adjusted_price_capture as values
from lib.closes_panel import (
    BROAD_GROUPS, align_latest_common_observation, merge_captured_close_caches,
    population_observation, resolve_thematic_close_panel,
)
from lib.yahoo_generation_contract import (
    VerifiedYahooGeneration, YAHOO_GENERATION_DOMAIN, _completed_target,
    _instant, _session, _UNKNOWN_CLOCKS, validate_yahoo_bundle,
)

DOMAIN = "sector-breadth-members"
SCHEMA = "sector_breadth_members.v1"
PANEL_MEMBERS = tuple(f"groups/{group}/{field}.parquet"
    for group in BROAD_GROUPS for field in values.FIELDS) + (
    "baskets/extras_close.parquet", "references/close.parquet")
CONSTITUENT_MEMBERS = tuple(f"groups/{group}/constituents.json" for group in BROAD_GROUPS)
MEMBERS = PANEL_MEMBERS + CONSTITUENT_MEMBERS + ("baskets/membership.json", "acquisition.json")
MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_BUNDLE_BYTES = 512 * 1024 * 1024
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_FOOTER_BYTES = 8 * 1024 * 1024
MAX_PANEL_DECODE_BYTES = 64 * 1024 * 1024
MAX_BUNDLE_DECODE_BYTES = 256 * 1024 * 1024
_FLOORS = {"breadth": 400, "smallcap_breadth": 450, "midcap_breadth": 350}
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_REVISION = re.compile(r"[0-9a-f]{40}\Z")
_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:@-]{0,191}\Z")
_SYMBOL = re.compile(r"[A-Z][A-Z0-9.-]{0,23}\Z")
_ABSENT_REFERENCE = frozenset(("not_captured", "not_current", "insufficient_observations",
                              "basis_unverified", "acquisition_failed", "no_qualified_source"))


class BreadthMemberContractError(ValueError):
    """Closed private input failure; no source path or provider response attached."""


@dataclass(frozen=True)
class EncodedBreadthMemberInputs:
    members: Mapping[str, bytes]
    input_identity: Mapping[str, Any]
    yahoo: VerifiedYahooGeneration


@dataclass(frozen=True)
class CapturedBreadthMemberInputs:
    source_session: str
    groups: Mapping[str, Mapping[str, pd.DataFrame]]
    constituents: Mapping[str, pd.DataFrame]
    membership: dict
    extras: pd.DataFrame
    references: Mapping[str, pd.DataFrame | None]
    broad_panel: pd.DataFrame
    primary: pd.DataFrame
    primary_metadata: Mapping[str, Any]
    spy: pd.DataFrame
    resolved_panel: pd.DataFrame
    resolution: Mapping[str, Any]
    receipt: Mapping[str, Any]

    def basket_inputs(self):
        """Return values to the existing basket core, preserving its calendar receipt."""
        from engine.baskets import BasketInputs
        from engine.equity_factors import names_sectors_from_frames
        names = names_sectors_from_frames(
            {g: self.constituents[g].set_index("symbol") for g in BROAD_GROUPS}, BROAD_GROUPS)
        return BasketInputs(deepcopy(self.membership), self.broad_panel.copy(deep=True),
            self.spy.copy(deep=True), self.extras.copy(deep=True), names,
            {t: None if frame is None else frame.copy(deep=True) for t, frame in self.references.items()},
            source_basis=dict(self.resolution["source_basis"]), require_complete_proxy_legs=True)

    def member_index_inputs(self, members):
        """Actual member closes and matching-source volume; no candle synthesis.

        Index-only members require the receipt's actual index-membership adjunct.
        Remove only a suffix with no eligible member observation; interior holes
        retain the incumbent index semantics.
        """
        if (not isinstance(members, (list, tuple)) or len(members) > values.MAX_COLUMNS
                or any(not isinstance(row, Mapping) or not isinstance(row.get("ticker"), str)
                       for row in members)):
            _error("invalid_member_index_population")
        tickers = [row["ticker"] for row in members]
        if len(set(tickers)) != len(tickers) or len(self.primary) * len(tickers) > values.MAX_PANEL_CELLS:
            _error("invalid_member_index_population")
        if any(ticker not in self.resolved_panel.columns for ticker in tickers):
            _error("uncaptured_member_index_population")
        from engine.basket_index import _live_mask
        members = deepcopy(list(members))
        close = self.resolved_panel.reindex(columns=tickers).copy(deep=True)
        eligible = _live_mask(members, close.index, tickers, pit=False, close=close)
        observed = (close.notna() & eligible).any(axis=1)
        close = close.iloc[:int(observed.to_numpy().nonzero()[0][-1]) + 1] if bool(observed.any()) else close.iloc[:0]
        volumes, origins = {}, {}
        for ticker in tickers:
            if self.resolution["price_source"].get(ticker) != "primary_breadth":
                continue
            group = self.primary_metadata["merge"]["source"].get(ticker)
            if group not in self.groups or ticker not in self.groups[group]["volume"]:
                continue
            original = self.groups[group]["close"][ticker].reindex(close.index)
            matching = original.notna() & close[ticker].notna() & original.eq(close[ticker])
            actual = self.groups[group]["volume"][ticker].reindex(close.index).where(matching)
            if bool(actual.notna().any()):
                volumes[ticker] = actual.copy(deep=True)
                origins[ticker] = group
        volume = pd.DataFrame(volumes, index=close.index) if volumes else None
        evidence = {"bundle_source_session": self.source_session,
            "member_observation_session": str(close.index[-1].date()) if len(close) else None,
            "close_source": {t: self.resolution["price_source"].get(t) for t in tickers},
            "volume_source": origins, "volume_unavailable": [t for t in tickers if t not in volumes],
            "range_fields": "not_supplied", "index_construction": "equal_weight_close_returns",
            "source_basis": dict(self.resolution["source_basis"])}
        return close, volume, evidence


@dataclass(frozen=True)
class VerifiedBreadthMemberGeneration:
    inputs: CapturedBreadthMemberInputs
    snapshot: Any

    def prior_identity(self, *, captured_at: datetime) -> dict:
        stamp = _instant(captured_at)
        if stamp < _instant(self.snapshot.published_at):
            raise BreadthMemberContractError("prior_capture_before_publication")
        return {"kind": "generation", "domain": DOMAIN, "source_ref": self.snapshot.generation_id,
            "content_id": self.snapshot.content_id, "source_revision": self.snapshot.manifest["source_revision"],
            "captured_at": stamp.isoformat(),
            "members": {name: {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
                        for name, raw in self.snapshot.members.items()}}


def _error(code: str):
    raise BreadthMemberContractError(code)


def _json_bytes(value) -> bytes:
    try:
        raw = json.dumps(value, allow_nan=False, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError):
        _error("invalid_json_value")
    if len(raw) > MAX_JSON_BYTES:
        _error("json_bound")
    return raw


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _error("duplicate_json_key")
        result[key] = value
    return result


def _finite_float(text):
    number = float(text)
    if not math.isfinite(number):
        _error("nonfinite_json")
    return number


def _json(raw: bytes):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_JSON_BYTES:
        _error("json_bound")
    try:
        return json.loads(raw, object_pairs_hook=_unique, parse_float=_finite_float,
            parse_constant=lambda _: _error("nonfinite_json"))
    except BreadthMemberContractError:
        raise
    except (ValueError, TypeError, UnicodeError, RecursionError):
        _error("invalid_json_bytes")


def _copy(value):
    return _json(_json_bytes(value))


def _panel(frame, *, field: str, source: str):
    if field not in values.OHLCV_FIELDS:
        _error("invalid_panel_field")
    try:
        return values._capture_panels({field: frame}, fields=(field,), source_session=source)[field]
    except values.AdjustedCaptureError:
        _error("invalid_panel_values")


def encode_panel(frame, *, field: str, source_session: str) -> bytes:
    import pyarrow as pa
    import pyarrow.parquet as pq
    panel = _panel(frame, field=field, source=source_session)
    # The ticker order is not economic evidence; canonicalize only columns.
    names = sorted(panel.columns)
    if "session" in names:
        _error("reserved_panel_column")
    arrays = [pa.array(panel.index.to_numpy(dtype="datetime64[ns]"), type=pa.timestamp("ns"))]
    arrays += [pa.array(panel[t].to_numpy(dtype=float), type=pa.float64(), from_pandas=True) for t in names]
    output = BytesIO()
    pq.write_table(pa.Table.from_arrays(arrays, names=["session", *names]), output,
        version="2.6", compression="snappy", use_dictionary=False, row_group_size=4096,
        store_schema=False, write_page_checksum=True)
    raw = output.getvalue()
    if len(raw) > MAX_MEMBER_BYTES:
        _error("panel_encoded_bound")
    return raw


def _open_panel(raw: bytes):
    import pyarrow as pa
    import pyarrow.parquet as pq
    if (type(raw) is not bytes or not 12 <= len(raw) <= MAX_MEMBER_BYTES
            or raw[:4] != b"PAR1" or raw[-4:] != b"PAR1"):
        _error("invalid_panel_bytes")
    footer = int.from_bytes(raw[-8:-4], "little")
    if not 0 < footer <= min(MAX_FOOTER_BYTES, len(raw) - 12):
        _error("panel_footer_bound")
    parquet = pq.ParquetFile(BytesIO(raw), thrift_string_size_limit=MAX_FOOTER_BYTES,
        thrift_container_size_limit=512_000, arrow_extensions_enabled=False,
        page_checksum_verification=True)
    try:
        meta = parquet.metadata
        if (meta.metadata or not 0 <= meta.num_rows <= values.MAX_ROWS
                or not 1 <= meta.num_columns <= values.MAX_COLUMNS + 1
                or meta.num_rows * (meta.num_columns - 1) > values.MAX_PANEL_CELLS
                or not 1 <= meta.num_row_groups <= 32
                or sum(meta.row_group(i).total_byte_size for i in range(meta.num_row_groups)) > MAX_PANEL_DECODE_BYTES):
            _error("panel_metadata_bound")
        schema = parquet.schema_arrow
        names = schema.names
        if (len(set(names)) != len(names) or names[0] != "session" or names[1:] != sorted(names[1:])
                or any(not isinstance(t, str) or not t or len(t) > 24 for t in names[1:])
                or schema.field(0).type != pa.timestamp("ns")
                or any(field.type != pa.float64() for field in list(schema)[1:])
                or any(field.metadata for field in schema)):
            _error("invalid_panel_schema")
        return parquet
    except BaseException:
        parquet.close()
        raise


def decode_panel(raw: bytes, *, field: str, source_session: str) -> pd.DataFrame:
    try:
        with _open_panel(raw) as parquet:
            declared = parquet.metadata.num_rows
            table = parquet.read(use_threads=False, use_pandas_metadata=False)
        if table.num_rows != declared or table.nbytes > MAX_PANEL_DECODE_BYTES:
            _error("panel_decode_bound")
        panel = pd.DataFrame({t: table[t].to_numpy() for t in table.column_names[1:]},
                             index=pd.DatetimeIndex(table["session"].to_numpy()))
        return _panel(panel, field=field, source=source_session)
    except BreadthMemberContractError:
        raise
    except Exception:
        _error("panel_decode_invalid")


def _constituents(rows, group):
    if not isinstance(rows, list) or not _FLOORS[group] <= len(rows) <= values.MAX_COLUMNS:
        _error("constituent_population_invalid")
    seen = set()
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {"symbol", "name", "sector"}
                or not isinstance(row["symbol"], str) or not _SYMBOL.fullmatch(row["symbol"])
                or row["symbol"] in seen or not isinstance(row["name"], str) or len(row["name"]) > 512
                or not (row["sector"] is None or isinstance(row["sector"], str) and len(row["sector"]) <= 256)):
            _error("constituent_rows_invalid")
        seen.add(row["symbol"])
    return pd.DataFrame(rows, columns=["symbol", "name", "sector"])


def _membership(document, primary):
    """Validate identities; population/date eligibility stays with its existing owner."""
    baskets = document.get("baskets") if isinstance(document, dict) else None
    if not isinstance(baskets, dict) or not 0 < len(baskets) <= 1000:
        _error("invalid_basket_membership")
    requested, required_end, active, populations, references = set(), {}, set(), {}, set()
    for bid, basket in baskets.items():
        if (not isinstance(bid, str) or not isinstance(basket, dict)
                or not isinstance(basket.get("name"), str) or not isinstance(basket.get("members"), list)
                or len(basket["members"]) > values.MAX_COLUMNS):
            _error("invalid_basket_membership")
        seen = set()
        for row in basket["members"]:
            ticker = row.get("ticker") if isinstance(row, dict) else None
            if not isinstance(ticker, str) or not _SYMBOL.fullmatch(ticker) or ticker in seen:
                _error("invalid_basket_member_symbol")
            seen.add(ticker); requested.add(ticker)
            # The basket core requires added. Refuse to invent an inception date.
            if row.get("added") is None:
                _error("basket_member_added_required")
            for when in (row.get("added"), row.get("removed")):
                if when is not None:
                    _session(when)
            if row.get("removed") is not None and row["removed"] <= row["added"]:
                _error("invalid_basket_member_interval")
            eligible = primary.index[primary.index >= pd.Timestamp(row["added"])]
            if row.get("removed"):
                eligible = eligible[eligible < pd.Timestamp(row["removed"])]
            if len(eligible):
                required_end[ticker] = max(required_end.get(ticker, eligible[-1]), eligible[-1])
        observation = population_observation(primary, basket["members"], primary.index[-1])
        populations[bid] = observation["configured_members"]
        active.update(observation["configured_members"])
        proxy = basket.get("etf_proxy")
        legs = proxy if isinstance(proxy, list) else [] if proxy is None else [proxy]
        if (len(legs) > 32 or len(set(legs)) != len(legs)
                or any(not isinstance(t, str) or not _SYMBOL.fullmatch(t) for t in legs)):
            _error("invalid_reference_symbols")
        references.update(legs)
    if not requested or len(requested) > values.MAX_COLUMNS or len(primary) * len(requested) > values.MAX_PANEL_CELLS:
        _error("membership_projection_bound")
    return tuple(sorted(requested)), active, required_end, populations, tuple(sorted(references))


def _bound_union(frames):
    dates, columns = set(), set()
    for frame in frames:
        dates.update(frame.index); columns.update(frame.columns)
    if (len(dates) > values.MAX_ROWS or len(columns) > values.MAX_COLUMNS
            or len(dates) * len(columns) > values.MAX_PANEL_CELLS):
        _error("derived_union_bound")


def derive_primary(groups, spy, *, source_session):
    """One incumbent merge, then the existing exact-observation alignment."""
    closes = {g: groups[g]["close"] for g in BROAD_GROUPS}
    _bound_union(closes.values())
    broad, meta = merge_captured_close_caches(closes, BROAD_GROUPS)
    primary, _, observation = align_latest_common_observation(broad, spy["close"])
    if primary.empty or observation["effective_as_of"] != source_session:
        _error("primary_not_current_common_observation")
    return broad, primary, meta, observation


def _captured_yahoo(yahoo, *, now, require_current):
    from lib.yahoo_runtime_profile import VerifiedYahooCohort
    if not isinstance(yahoo, VerifiedYahooGeneration):
        _error("verified_yahoo_capture_required")
    snapshot = yahoo.snapshot
    manifest = _copy(dict(snapshot.manifest))
    raw = dict(snapshot.members)
    if (snapshot.domain != YAHOO_GENERATION_DOMAIN or manifest.get("domain") != snapshot.domain
            or manifest.get("content_id") != snapshot.content_id
            or manifest.get("generation_id") != snapshot.generation_id
            or manifest.get("published_at") != snapshot.published_at):
        _error("yahoo_capture_identity_mismatch")
    # A detached snapshot object is not a substitute for the publisher's content
    # identity. Recompute with its incumbent hash function over these exact bytes.
    from scripts.vps_live_orchestrator import _generation_content_id
    artifacts = sorted(({"name": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                        for name, data in raw.items()), key=lambda row: row["name"])
    if (manifest.get("artifacts") != artifacts or _generation_content_id(
            domain=snapshot.domain, generation_id=snapshot.generation_id,
            lane=manifest.get("lane"), source_revision=manifest.get("source_revision"),
            input_identity=manifest.get("input_identity"), captured=artifacts) != snapshot.content_id):
        _error("yahoo_capture_content_mismatch")
    frames = validate_yahoo_bundle(member_bytes=raw, input_identity=manifest["input_identity"],
        published_at=snapshot.published_at, now=_instant(now),
        source_revision=manifest["source_revision"], computed_at=manifest["computed_at"],
        require_current=require_current)
    source = manifest["input_identity"]["yahoo_cohort"]["source_session"]
    captured = replace(snapshot, manifest=MappingProxyType(manifest), members=MappingProxyType(raw))
    return VerifiedYahooGeneration(VerifiedYahooCohort(snapshot.generation_id, source,
        MappingProxyType(frames)), captured)


def verify_breadth_snapshot(snapshot, *, yahoo, now, require_current=False):
    """Revalidate exact captured bytes; mutable derived frames are not authority."""
    manifest = _copy(dict(snapshot.manifest))
    raw = dict(snapshot.members)
    if (snapshot.domain != DOMAIN or manifest.get("domain") != DOMAIN
            or manifest.get("content_id") != snapshot.content_id
            or manifest.get("generation_id") != snapshot.generation_id
            or manifest.get("published_at") != snapshot.published_at
            or set(raw) != set(MEMBERS)
            or any(type(data) is not bytes or not 0 < len(data) <= MAX_MEMBER_BYTES for data in raw.values())
            or sum(map(len, raw.values())) > MAX_BUNDLE_BYTES):
        _error("breadth_capture_identity_mismatch")
    from scripts.vps_live_orchestrator import _generation_content_id
    artifacts = sorted(({"name": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                        for name, data in raw.items()), key=lambda row: row["name"])
    if (manifest.get("artifacts") != artifacts or _generation_content_id(
            domain=DOMAIN, generation_id=snapshot.generation_id, lane=manifest.get("lane"),
            source_revision=manifest.get("source_revision"), input_identity=manifest.get("input_identity"),
            captured=artifacts) != snapshot.content_id):
        _error("breadth_capture_content_mismatch")
    inputs = validate_breadth_member_bundle(member_bytes=raw, input_identity=manifest.get("input_identity"),
        yahoo=yahoo, published_at=snapshot.published_at, now=now,
        source_revision=manifest.get("source_revision"), computed_at=manifest.get("computed_at"),
        require_current=require_current)
    return VerifiedBreadthMemberGeneration(inputs,
        replace(snapshot, manifest=MappingProxyType(manifest), members=MappingProxyType(raw)))


def _yahoo_identity(yahoo):
    snap = yahoo.snapshot
    return {"domain": snap.domain, "generation_id": snap.generation_id,
        "content_id": snap.content_id, "source_revision": snap.manifest["source_revision"],
        "source_session": yahoo.cohort.source_session, "published_at": snap.published_at,
        "members": {name: {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
                    for name, raw in snap.members.items()}}


def _source_capture(value, *, before):
    if (not isinstance(value, dict) or set(value) != {"source_ref", "source_revision", "captured_at"}
            or not isinstance(value["source_ref"], str) or not _REF.fullmatch(value["source_ref"])
            or not isinstance(value["source_revision"], str) or not _REVISION.fullmatch(value["source_revision"])
            or _instant(value["captured_at"]) > _instant(before)):
        _error("invalid_source_capture")


def _prior(value, *, before):
    if (not isinstance(value, dict)
            or set(value) != {"kind", "domain", "source_ref", "source_revision", "captured_at", "content_id", "members"}
            or value["domain"] != DOMAIN or value["kind"] not in ("generation", "bootstrap")):
        _error("invalid_prior_identity")
    _source_capture({k: value[k] for k in ("source_ref", "source_revision", "captured_at")}, before=before)
    if ((value["kind"] == "generation" and (not isinstance(value["content_id"], str) or not _HEX.fullmatch(value["content_id"])))
            or (value["kind"] == "bootstrap" and value["content_id"] is not None)
            or not isinstance(value["members"], dict) or set(value["members"]) != set(MEMBERS)):
        _error("invalid_prior_identity")
    for entry in value["members"].values():
        if entry is None and value["kind"] == "bootstrap":
            continue
        if (not isinstance(entry, dict) or set(entry) != {"sha256", "bytes"}
                or not isinstance(entry["sha256"], str) or not _HEX.fullmatch(entry["sha256"])
                or type(entry["bytes"]) is not int or not 0 < entry["bytes"] <= MAX_MEMBER_BYTES):
            _error("invalid_prior_identity")


def _group_evidence(declared, *, panels, members, source, prepared):
    from collectors.yahoo import YahooRequestSettings
    keys = {"accepted", "reason", "current", "unresolved", "repaired", "departed", "evidence"}
    if (not isinstance(declared, dict) or set(declared) != keys
            or declared["accepted"] is not True or declared["reason"] != "accepted"):
        _error("breadth_acquisition_not_accepted")
    active = list(members["symbol"])
    sets = {}
    for name in ("current", "unresolved", "repaired", "departed"):
        seq = declared[name]
        if not isinstance(seq, list) or any(not isinstance(t, str) for t in seq) or len(set(seq)) != len(seq):
            _error("invalid_breadth_classification")
        sets[name] = set(seq)
    if (not sets["current"].issubset(active) or not sets["unresolved"].issubset(active)
            or not sets["repaired"].issubset(sets["current"])
            or sets["current"] & sets["unresolved"]
            or sets["departed"] != set(panels["close"].columns) - set(active)):
        _error("invalid_breadth_classification")
    first = panels["close"]
    if any(not first.index.equals(panel.index) or not first.columns.equals(panel.columns) for panel in panels.values()):
        _error("group_panel_axes_mismatch")
    evidence = declared["evidence"]
    expected_keys = {"evaluation_instant", "source_session", "completed_sessions_only", "target_calendar_verified",
        "basis", "fields", "selection_policy", "active_members", "current_members", "required_current", "request", "members", "unknown"}
    if (not isinstance(evidence, dict) or set(evidence) != expected_keys
            or evidence["source_session"] != source or evidence["basis"] != "provider_auto_adjusted"
            or evidence["fields"] != list(values.FIELDS) or evidence["completed_sessions_only"] is not True
            or evidence["target_calendar_verified"] is not True or evidence["active_members"] != len(active)
            or evidence["current_members"] != len(sets["current"])
            or evidence["required_current"] != math.ceil(len(active) * 0.8)
            or len(sets["current"]) < math.ceil(len(active) * 0.8)
            or not isinstance(evidence["members"], dict) or set(evidence["members"]) != set(active)):
        _error("invalid_breadth_evidence")
    evaluation = _instant(evidence["evaluation_instant"])
    if evaluation > prepared or _completed_target(evaluation) != source:
        _error("invalid_breadth_clock")
    if evidence["unknown"] != {key: _UNKNOWN_CLOCKS[key] for key in ("vendor_publication_clock", "provider_available_at")}:
        _error("invalid_acquisition_unknown_clocks")
    policy = evidence["selection_policy"]
    if (not isinstance(policy, dict) or set(policy) != {"ma_windows", "nhnl_window", "ticker_fixups", "excluded_symbols"}
            or not isinstance(policy["ma_windows"], list) or len(policy["ma_windows"]) != 2
            or any(type(n) is not int or n < 1 for n in policy["ma_windows"])
            or type(policy["nhnl_window"]) is not int or policy["nhnl_window"] < 1
            or not isinstance(policy["ticker_fixups"], dict)
            or any(not isinstance(k, str) or not isinstance(v, str) for k, v in policy["ticker_fixups"].items())
            or not isinstance(policy["excluded_symbols"], list)
            or any(not isinstance(t, str) for t in policy["excluded_symbols"])
            or policy["excluded_symbols"] != sorted(set(policy["excluded_symbols"]))
            or set(active) & set(policy["excluded_symbols"])):
        _error("invalid_breadth_selection_policy")
    request = evidence["request"]
    if (not isinstance(request, dict) or set(request) != {"period", "recovery_period", "batch_size", "retries",
            "backoff_base_s", "basis_tolerance", "minimum_repair_sessions", "calculation_lookback_days"}
            or request["recovery_period"] not in (None, "max")
            or type(request["minimum_repair_sessions"]) is not int
            or request["minimum_repair_sessions"] != max(*policy["ma_windows"], policy["nhnl_window"])
            or type(request["calculation_lookback_days"]) is not int or request["calculation_lookback_days"] < 1):
        _error("invalid_breadth_request_policy")
    cold_period = f"{max(1, request['calculation_lookback_days'] // 365 + 1)}y"
    if (request["period"] not in ("1mo", "max", cold_period)
            or (request["period"] == cold_period and request["recovery_period"] is not None)):
        _error("invalid_breadth_request_policy")
    YahooRequestSettings.capture({**request, "upsert_basis_tol": request["basis_tolerance"]})
    vendors = set()
    for ticker in active:
        row = evidence["members"][ticker]
        if (not isinstance(row, dict) or set(row) != {"vendor_symbol", "initial_span", "accepted_span",
                "repair_reason", "repaired", "current", "unresolved"}
                or not isinstance(row["vendor_symbol"], str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.^=-]{0,23}", row["vendor_symbol"])
                or row["vendor_symbol"] in vendors
                or any(type(row[key]) is not bool or row[key] != (ticker in sets[key])
                       for key in ("repaired", "current", "unresolved"))):
            _error("invalid_breadth_member_evidence")
        vendors.add(row["vendor_symbol"])
        for key in ("initial_span", "accepted_span"):
            span = row[key]
            if span is not None:
                if not isinstance(span, list) or len(span) != 2 or _session(span[0]) > _session(span[1]) or span[1] > source:
                    _error("invalid_breadth_span")
        if ticker in sets["current"]:
            if (row["accepted_span"] is None or row["accepted_span"][-1] != source
                    or ticker not in first or pd.Timestamp(source) not in first.index
                    or any(pd.isna(panel.at[pd.Timestamp(source), ticker]) for panel in panels.values())):
                _error("breadth_current_observation_missing")
            observed = pd.concat([panels[field][ticker] for field in values.FIELDS], axis=1).notna().all(axis=1)
            if int(observed.sum()) < request["minimum_repair_sessions"]:
                _error("breadth_current_history_insufficient")
        elif row["accepted_span"] is not None:
            _error("unqualified_breadth_span")
    return evaluation, sets["current"]


def _extras_evidence(declared, *, primary, archive, membership, group_current, merge_meta, source,
                     prepared, index_membership=None):
    keys = {"status", "source_session", "effective_as_of", "requested", "downloaded", "retained",
            "unresolved", "resolution", "evidence"}
    if not isinstance(declared, dict) or set(declared) != keys or declared["source_session"] != source:
        _error("invalid_extras_evidence")
    requested, active, required_end, populations, references = _membership(membership, primary)
    index_populations = None
    if index_membership is not None:
        from lib.sector_index_membership_capture import index_population
        # Replay actual index membership independently. It never enters the
        # thematic basket document or its original population evidence.
        additional, eligible, ends, index_populations = index_population(
            index_membership, primary=primary, before=prepared)
        requested = tuple(sorted(set(requested) | additional))
        active.update(eligible)
        for ticker, end in ends.items():
            required_end[ticker] = max(required_end.get(ticker, end), end)
        if len(requested) > values.MAX_COLUMNS or len(primary) * len(requested) > values.MAX_PANEL_CELLS:
            _error("membership_projection_bound")
    if declared["requested"] != list(requested) or declared["effective_as_of"] != source:
        _error("extras_membership_or_clock_mismatch")
    sets = {}
    for key in ("downloaded", "retained", "unresolved"):
        seq = declared[key]
        if not isinstance(seq, list) or any(not isinstance(t, str) for t in seq) or len(set(seq)) != len(seq):
            _error("invalid_extras_classification")
        sets[key] = set(seq)
    if (not sets["downloaded"].issubset(requested) or not sets["unresolved"].issubset(requested)
            or not sets["retained"].issubset(archive.columns) or sets["downloaded"] & sets["unresolved"]
            or sets["downloaded"] & sets["retained"]):
        _error("invalid_extras_classification")
    evidence = declared["evidence"]
    keys = {"evaluation_instant", "source_session", "effective_as_of", "completed_sessions_only", "request",
            "skipped_qualified_primary", "basket_populations", "currently_eligible",
            "no_visible_history_obligation", "selection_history_shortfalls", "members", "unknown"}
    if index_membership is not None:
        keys.add("index_populations")
    if (not isinstance(evidence, dict) or set(evidence) != keys or evidence["source_session"] != source
            or evidence["effective_as_of"] != source or evidence["completed_sessions_only"] is not True
            or evidence["currently_eligible"] != sorted(active) or evidence["basket_populations"] != populations
            or evidence["no_visible_history_obligation"] != [t for t in requested if t not in required_end]
            or (index_membership is not None and evidence.get("index_populations") != index_populations)
            or not isinstance(evidence["members"], dict) or set(evidence["members"]) != set(requested)):
        _error("invalid_extras_evidence")
    if evidence["unknown"] != {key: _UNKNOWN_CLOCKS[key] for key in ("vendor_publication_clock", "provider_available_at")}:
        _error("invalid_acquisition_unknown_clocks")
    evaluation = _instant(evidence["evaluation_instant"])
    if evaluation > prepared or _completed_target(evaluation) != source:
        _error("invalid_extras_clock")
    if index_membership is not None:
        from lib.sector_index_membership_capture import decode_index_membership
        decode_index_membership(index_membership, before=evaluation)
    request = evidence["request"]
    if (not isinstance(request, dict) or set(request) != {"history_start", "batch_size", "retries",
            "backoff_base_s", "primary_history_threshold"}
            or _session(request["history_start"]) > source
            or type(request["primary_history_threshold"]) is not int or request["primary_history_threshold"] < 1):
        _error("invalid_extras_request_policy")
    from collectors.yahoo import YahooRequestSettings
    YahooRequestSettings.capture(request)
    resolution = declared["resolution"]
    basis = resolution.get("source_basis") if isinstance(resolution, dict) else None
    if basis != {"primary_breadth": "provider_auto_adjusted", "baskets_extras": "unrecorded"}:
        _error("extras_basis_mismatch")
    view = archive.loc[:, [t for t in requested if t in archive]]
    if len(primary) * len(view.columns) > values.MAX_PANEL_CELLS:
        _error("membership_projection_bound")
    resolved, replay = resolve_thematic_close_panel(primary, view, requested, source_basis=basis)
    if resolution != replay:
        _error("extras_resolution_mismatch")
    qualified = {t for t, group in merge_meta["source"].items() if t in group_current[group]}
    skipped = evidence["skipped_qualified_primary"]
    if (not isinstance(skipped, list) or len(set(skipped)) != len(skipped)
            or not set(skipped).issubset(qualified & set(requested))):
        _error("invalid_primary_skip")
    shortfalls, targets, desk, vendors = [], [], [], set()
    for ticker in requested:
        row = evidence["members"][ticker]
        if not isinstance(row, dict):
            _error("invalid_extras_member_evidence")
        observed = resolved[ticker].dropna() if ticker in resolved else pd.Series(dtype=float)
        chosen = replay["price_source"].get(ticker)
        expected = {
            "selected_source": chosen, "selection_reason": replay["selection_reason"].get(ticker),
            "selected_history_sessions": len(observed),
            "selected_history_start": observed.index[0].date().isoformat() if len(observed) else None,
            "selected_observation_date": observed.index[-1].date().isoformat() if len(observed) else None,
            "target_observed": bool(len(observed) and observed.index[-1] == pd.Timestamp(source)),
            "currently_eligible": ticker in active,
            "required_history_end": required_end[ticker].date().isoformat() if ticker in required_end else None,
            "required_history_end_observed": bool(ticker in required_end and required_end[ticker] in observed.index),
            "desk_observed": bool(primary.index[-1] in observed.index),
            "chosen_prior_retained": chosen == "baskets_extras" and ticker in sets["retained"],
            "chosen_acquired_this_attempt": chosen == "baskets_extras" and ticker in sets["downloaded"],
            "supplied_primary_qualified": ticker in qualified,
            "stitched": replay["stitched"].get(ticker),
            "selection_history_shortfall": ticker in required_end and required_end[ticker] not in observed.index,
            "downloaded": ticker in sets["downloaded"], "refresh_unresolved": ticker in sets["unresolved"],
            "acquisition_basis": "provider_auto_adjusted" if ticker in sets["downloaded"] else None,
            "download_requested": ticker not in skipped and ticker in required_end,
        }
        if (set(row) != set(expected) | {"vendor_symbol", "returned_span", "archive_prior_retained", "refresh_reason"}
                or not isinstance(row["vendor_symbol"], str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.^=-]{0,23}", row["vendor_symbol"])
                or row["vendor_symbol"] in vendors or type(row["archive_prior_retained"]) is not bool
                or row["archive_prior_retained"] and ticker not in sets["retained"]
                or (row["refresh_reason"] not in ("download_failed", "missing_target_or_prior_observations")
                    if ticker in sets["unresolved"] else row["refresh_reason"] is not None)):
            _error("invalid_extras_member_evidence")
        vendors.add(row["vendor_symbol"])
        span = row["returned_span"]
        if span is not None and (not isinstance(span, list) or len(span) != 2
                or _session(span[0]) > _session(span[1]) or span[1] > source):
            _error("invalid_extras_span")
        if any(row.get(key) != value or (isinstance(value, bool) and type(row.get(key)) is not bool)
               for key, value in expected.items()):
            _error("extras_selected_observation_mismatch")
        if ticker in skipped and (chosen != "primary_breadth"
                or len(primary[ticker].dropna()) < request["primary_history_threshold"]
                or required_end.get(ticker) not in primary[ticker].dropna().index):
            _error("invalid_primary_skip")
        if ticker in sets["downloaded"]:
            column = archive[ticker].dropna() if ticker in archive else pd.Series(dtype=float)
            required = pd.Timestamp(source) if ticker in active else required_end.get(ticker)
            if (required is None or required not in column.index
                    or row.get("returned_span") != [column.index[0].date().isoformat(), column.index[-1].date().isoformat()]):
                _error("extras_downloaded_observation_missing")
        if expected["selection_history_shortfall"]:
            shortfalls.append(ticker)
        if ticker in active:
            targets.append(expected["target_observed"])
        desk.append(expected["desk_observed"])
    complete = not sets["unresolved"] and not shortfalls and all(targets)
    status = "complete" if complete else "partial" if any(desk) else "unavailable"
    if declared["status"] != status or evidence["selection_history_shortfalls"] != shortfalls:
        _error("extras_status_mismatch")
    return resolved, replay, references, evaluation


def _references(panel, declared, *, required, yahoo, source, prepared):
    available_yahoo = set(required) & set(yahoo.cohort.frames)
    optional = set(required) - available_yahoo
    if not isinstance(declared, dict) or set(declared) != optional or not set(panel.columns).issubset(optional):
        _error("reference_population_mismatch")
    result = {ticker: yahoo.cohort.frames[ticker].copy(deep=True) for ticker in available_yahoo}
    present = set()
    for ticker in sorted(optional):
        row = declared[ticker]
        if not isinstance(row, dict) or row.get("status") not in ("available", "absent"):
            _error("reference_evidence_invalid")
        if row["status"] == "absent":
            if set(row) != {"status", "reason"} or row["reason"] not in _ABSENT_REFERENCE:
                _error("reference_absence_invalid")
            result[ticker] = None
            continue
        if (set(row) != {"status", "basis", "source_ref", "captured_at"}
                or row["basis"] not in ("provider_auto_adjusted", "total_return")
                or not isinstance(row["source_ref"], str) or not _REF.fullmatch(row["source_ref"])
                or _instant(row["captured_at"]) > prepared or ticker not in panel):
            _error("reference_evidence_invalid")
        column = panel[ticker].dropna()
        if len(column) < 62 or column.index[-1] != pd.Timestamp(source):
            _error("reference_observations_unqualified")
        present.add(ticker)
        result[ticker] = column.to_frame("close")
    if set(panel.columns) != present:
        _error("reference_population_mismatch")
    return result


def validate_breadth_member_bundle(*, member_bytes, input_identity, yahoo, published_at, now,
                                  source_revision, computed_at, require_current=False):
    if (not isinstance(member_bytes, Mapping) or set(member_bytes) != set(MEMBERS)
            or any(type(raw) is not bytes or not 0 < len(raw) <= MAX_MEMBER_BYTES for raw in member_bytes.values())
            or sum(map(len, member_bytes.values())) > MAX_BUNDLE_BYTES):
        _error("invalid_breadth_member_set")
    receipt = _json(member_bytes["acquisition.json"])
    keys = {"schema", "source_session", "prepared_at", "producer_source_sha", "yahoo",
            "source_captures", "prior", "groups", "extras", "references"}
    if (not isinstance(receipt, dict) or set(receipt) not in (keys, keys | {"index_membership"})
            or receipt["schema"] != SCHEMA
            or ("index_membership" in receipt and receipt["index_membership"] is None)):
        _error("invalid_breadth_receipt")
    identity = {"sector_breadth_members": {
        "schema": SCHEMA, "source_session": receipt["source_session"], "prepared_at": receipt["prepared_at"],
        "producer_source_sha": receipt["producer_source_sha"], "yahoo_content_id": receipt["yahoo"].get("content_id"),
        "acquisition_sha256": hashlib.sha256(member_bytes["acquisition.json"]).hexdigest()}}
    if input_identity != identity:
        _error("breadth_input_identity_mismatch")
    source = _session(receipt["source_session"])
    prepared, publication, admission = map(_instant, (receipt["prepared_at"], published_at, now))
    if (not isinstance(source_revision, str) or not _REVISION.fullmatch(source_revision)
            or receipt["producer_source_sha"] != source_revision or computed_at != receipt["prepared_at"]
            or not prepared <= publication <= admission
            or _completed_target(publication) != source or (require_current and _completed_target(admission) != source)):
        _error("breadth_publication_clock_or_revision_mismatch")
    captured_yahoo = _captured_yahoo(yahoo, now=admission, require_current=require_current)
    if (receipt["yahoo"] != _yahoo_identity(captured_yahoo) or captured_yahoo.cohort.source_session != source
            or _instant(captured_yahoo.snapshot.published_at) > prepared):
        _error("yahoo_dependency_mismatch")
    if not isinstance(receipt["groups"], dict) or set(receipt["groups"]) != set(BROAD_GROUPS):
        _error("breadth_group_set_mismatch")
    declared_decode = 0
    for name in PANEL_MEMBERS:
        try:
            with _open_panel(member_bytes[name]) as parquet:
                declared_decode += parquet.metadata.num_rows * parquet.metadata.num_columns * 8
        except BreadthMemberContractError:
            raise
        except Exception:
            _error("panel_decode_invalid")
    if declared_decode > MAX_BUNDLE_DECODE_BYTES:
        _error("bundle_decode_bound")
    groups, constituents, current, evaluations = {}, {}, {}, []
    for group in BROAD_GROUPS:
        groups[group] = {field: decode_panel(member_bytes[f"groups/{group}/{field}.parquet"],
            field=field, source_session=source) for field in values.FIELDS}
        constituents[group] = _constituents(_json(member_bytes[f"groups/{group}/constituents.json"]), group)
        evaluation, current[group] = _group_evidence(receipt["groups"][group],
            panels=groups[group], members=constituents[group], source=source, prepared=prepared)
        evaluations.append(evaluation)
    spy = captured_yahoo.cohort.frames["SPY"]
    broad, primary, meta, observation = derive_primary(groups, spy, source_session=source)
    membership = _json(member_bytes["baskets/membership.json"])
    extras = decode_panel(member_bytes["baskets/extras_close.parquet"], field="close", source_session=source)
    resolved, resolution, required_refs, extras_evaluation = _extras_evidence(receipt["extras"],
        primary=primary, archive=extras, membership=membership, group_current=current,
        merge_meta=meta, source=source, prepared=prepared,
        index_membership=receipt.get("index_membership"))
    evaluations.append(extras_evaluation)
    captures = receipt["source_captures"]
    if not isinstance(captures, dict) or set(captures) != {*BROAD_GROUPS, "membership"}:
        _error("source_capture_set_mismatch")
    for group in BROAD_GROUPS:
        _source_capture(captures[group], before=receipt["groups"][group]["evidence"]["evaluation_instant"])
    _source_capture(captures["membership"], before=extras_evaluation)
    _prior(receipt["prior"], before=min(evaluations))
    refs = decode_panel(member_bytes["references/close.parquet"], field="close", source_session=source)
    reference_frames = _references(refs, receipt["references"], required=required_refs,
        yahoo=captured_yahoo, source=source, prepared=prepared)
    return CapturedBreadthMemberInputs(source, MappingProxyType(groups), MappingProxyType(constituents),
        membership, extras, MappingProxyType(reference_frames), broad, primary,
        MappingProxyType({"merge": meta, "observation": observation}), spy, resolved,
        MappingProxyType(resolution), MappingProxyType(receipt))


def encode_breadth_member_acquisitions(*, groups, extras, membership, yahoo,
        reference_frames, reference_evidence, source_captures, prior_identity,
        prepared_at, source_revision, index_membership=None) -> EncodedBreadthMemberInputs:
    from collectors.breadth import BreadthPriceAcquisition
    from scripts.fetch_basket_extras import BasketExtrasAcquisition
    if (not isinstance(groups, Mapping) or set(groups) != set(BROAD_GROUPS)
            or any(not isinstance(item, BreadthPriceAcquisition) or item.accepted is not True for item in groups.values())
            or not isinstance(extras, BasketExtrasAcquisition)):
        _error("captured_acquisitions_required")
    prepared = _instant(prepared_at)
    captured_yahoo = _captured_yahoo(yahoo, now=prepared, require_current=True)
    source = captured_yahoo.cohort.source_session
    if any(item.source_session != source for item in groups.values()) or extras.source_session != source:
        _error("acquisition_source_mismatch")
    # Materialize only after the aggregate prospective allocation is bounded.
    all_frames = [frame for item in groups.values() for frame in item.panels.values()] + [extras.archive]
    if (any(not isinstance(frame, pd.DataFrame) for frame in all_frames)
            or sum((len(frame) * (len(frame.columns) + 1) * 8) for frame in all_frames) > MAX_BUNDLE_DECODE_BYTES):
        _error("bundle_decode_bound")
    raw, captured_groups, group_receipts = {}, {}, {}
    for group in BROAD_GROUPS:
        acquisition = groups[group]
        if not isinstance(acquisition.panels, Mapping) or set(acquisition.panels) != set(values.FIELDS):
            _error("group_fields_mismatch")
        captured_groups[group] = values.capture_panels(acquisition.panels, source_session=source)
        frame = acquisition.members
        if (not isinstance(frame, pd.DataFrame) or frame.columns.has_duplicates
                or not {"symbol", "name", "sector"}.issubset(frame.columns)):
            _error("constituent_rows_invalid")
        rows = []
        for row in frame[["symbol", "name", "sector"]].to_dict("records"):
            if row["sector"] is None or row["sector"] is pd.NA or isinstance(row["sector"], float) and math.isnan(row["sector"]):
                row["sector"] = None
            rows.append(row)
        _constituents(rows, group)
        raw[f"groups/{group}/constituents.json"] = _json_bytes(rows)
        for field in values.FIELDS:
            raw[f"groups/{group}/{field}.parquet"] = encode_panel(
                captured_groups[group][field], field=field, source_session=source)
        group_receipts[group] = {"accepted": acquisition.accepted, "reason": acquisition.reason,
            **{key: list(getattr(acquisition, key)) for key in ("current", "unresolved", "repaired", "departed")},
            "evidence": _copy(dict(acquisition.evidence))}
    document = _copy(dict(membership))
    _, primary, _, _ = derive_primary(captured_groups, captured_yahoo.cohort.frames["SPY"], source_session=source)
    _, _, _, _, required_refs = _membership(document, primary)
    optional = set(required_refs) - set(captured_yahoo.cohort.frames)
    if (not isinstance(reference_frames, Mapping) or set(reference_frames) != optional
            or not isinstance(reference_evidence, Mapping) or set(reference_evidence) != optional):
        _error("explicit_reference_population_required")
    ref_panels = {}
    for ticker in sorted(optional):
        frame = reference_frames[ticker]
        if frame is None:
            continue
        if not isinstance(frame, pd.DataFrame) or list(frame.columns) != ["close"]:
            _error("reference_frame_invalid")
        ref_panels[ticker] = values.capture_close_panel(frame.rename(columns={"close": ticker}), source_session=source)
    _bound_union(ref_panels.values())
    refs = (pd.concat([frame for frame in ref_panels.values()], axis=1).sort_index()
            if ref_panels else values.empty_panel())
    raw["references/close.parquet"] = encode_panel(refs, field="close", source_session=source)
    raw["baskets/membership.json"] = _json_bytes(document)
    raw["baskets/extras_close.parquet"] = encode_panel(extras.archive, field="close", source_session=source)
    receipt = {"schema": SCHEMA, "source_session": source, "prepared_at": prepared.isoformat(),
        "producer_source_sha": source_revision, "yahoo": _yahoo_identity(captured_yahoo),
        "source_captures": _copy(dict(source_captures)), "prior": _copy(dict(prior_identity)),
        "groups": group_receipts,
        "extras": {"status": extras.status, "source_session": extras.source_session,
            "effective_as_of": extras.effective_as_of,
            **{key: list(getattr(extras, key)) for key in ("requested", "downloaded", "retained", "unresolved")},
            "resolution": _copy(dict(extras.resolution)), "evidence": _copy(dict(extras.evidence))},
        "references": _copy(dict(reference_evidence))}
    if index_membership is not None:
        receipt["index_membership"] = _copy(dict(index_membership))
    raw["acquisition.json"] = _json_bytes(receipt)
    identity = {"sector_breadth_members": {"schema": SCHEMA, "source_session": source,
        "prepared_at": prepared.isoformat(), "producer_source_sha": source_revision,
        "yahoo_content_id": captured_yahoo.snapshot.content_id,
        "acquisition_sha256": hashlib.sha256(raw["acquisition.json"]).hexdigest()}}
    admitted = validate_breadth_member_bundle(member_bytes=raw, input_identity=identity,
        yahoo=captured_yahoo, published_at=prepared.isoformat(), now=prepared,
        source_revision=source_revision, computed_at=prepared.isoformat(), require_current=True)
    # A caller's supplied derived values must agree with an independent replay.
    # They are never stored as another price matrix or used as read authority.
    try:
        pd.testing.assert_frame_equal(admitted.resolved_panel, extras.resolved_panel,
            check_names=False, check_dtype=False, check_freq=False, check_exact=True)
    except (AssertionError, TypeError):
        _error("supplied_extras_panel_mismatch")
    return EncodedBreadthMemberInputs(MappingProxyType(raw), MappingProxyType(identity), captured_yahoo)


def prepare_breadth_member_generation_request(*, sources, input_identity, yahoo,
                                             generation_id, source_revision, lane):
    from scripts.vps_live_orchestrator import GenerationArtifact, GenerationRequest
    if not isinstance(sources, Mapping) or set(sources) != set(MEMBERS):
        _error("invalid_breadth_member_set")
    if not isinstance(generation_id, str) or not _REF.fullmatch(generation_id):
        _error("invalid_generation_id")
    identity = _copy(dict(input_identity))
    declared = identity.get("sector_breadth_members", {})
    source, prepared = _session(declared.get("source_session")), declared.get("prepared_at")
    if declared.get("producer_source_sha") != source_revision:
        _error("producer_revision_mismatch")
    captured_yahoo = _captured_yahoo(yahoo, now=_instant(prepared), require_current=True)
    if declared.get("yahoo_content_id") != captured_yahoo.snapshot.content_id:
        _error("yahoo_dependency_mismatch")

    def member_validator(name):
        def validate(path):
            try:
                if name in PANEL_MEMBERS:
                    field = name.rsplit("/", 1)[-1].removesuffix(".parquet")
                    if field not in values.FIELDS:
                        field = "close"
                    decode_panel(path.read_bytes(), field=field, source_session=source)
                else:
                    _json(path.read_bytes())
            except Exception as exc:
                return "breadth_member_rejected:" + type(exc).__name__
            return None
        return validate

    def validate_bundle(context):
        if (context.domain != DOMAIN or context.generation_id != generation_id
                or context.input_identity != identity or context.source_revision != source_revision
                or context.computed_at != prepared):
            return "breadth_identity_changed_during_admission"
        try:
            validate_breadth_member_bundle(member_bytes=context.members,
                input_identity=context.input_identity, yahoo=captured_yahoo,
                published_at=context.published_at, now=context.admission_time,
                source_revision=context.source_revision, computed_at=context.computed_at, require_current=True)
        except Exception as exc:
            return "breadth_semantic_rejected:" + type(exc).__name__
        return None

    return GenerationRequest(generation_id=generation_id, domain=DOMAIN, lane=lane,
        source_revision=source_revision, computed_at=prepared, input_identity=deepcopy(identity),
        artifacts=tuple(GenerationArtifact(name=name, source=Path(sources[name]),
                                           validator=member_validator(name)) for name in MEMBERS),
        bundle_validator=validate_bundle)


def read_breadth_yahoo_dependency(*, snapshot, generations_root, now, dependency_reader=None,
                                 require_current=False):
    """Resolve only the exact retained Yahoo identity sealed by this snapshot."""
    from scripts.vps_live_orchestrator import read_retained_generation
    from lib.yahoo_generation_contract import YAHOO_GENERATION_MEMBERS, verify_yahoo_snapshot
    root = Path(generations_root)
    if not root.is_absolute() or snapshot.domain != DOMAIN:
        _error("absolute_private_root_required")
    receipt = _json(snapshot.members["acquisition.json"])
    dependency = receipt.get("yahoo") if isinstance(receipt, dict) else None
    if (not isinstance(dependency, dict) or set(dependency) != {"domain", "generation_id", "content_id",
            "source_revision", "source_session", "published_at", "members"}
            or dependency["domain"] != YAHOO_GENERATION_DOMAIN):
        _error("invalid_yahoo_dependency")
    pinned = (dependency_reader or read_retained_generation)(generations_root=root,
        domain=dependency["domain"], generation_id=dependency["generation_id"],
        content_id=dependency["content_id"], members=YAHOO_GENERATION_MEMBERS)
    return verify_yahoo_snapshot(pinned, now=now, require_current=require_current)


def read_verified_breadth_member_inputs(*, generations_root, now, yahoo=None, snapshot_reader=None,
                                       dependency_reader=None, require_current=False):
    from scripts.vps_live_orchestrator import read_selected_generation
    root = Path(generations_root)
    if not root.is_absolute():
        _error("absolute_private_root_required")
    snapshot = (snapshot_reader or read_selected_generation)(
        generations_root=root, domain=DOMAIN, members=MEMBERS)
    if snapshot.domain != DOMAIN:
        _error("invalid_breadth_domain")
    if yahoo is None:
        # Prior recovery must bind the old dependency even when current Yahoo
        # advanced before a failed breadth attempt. Never refresh either pointer.
        yahoo = read_breadth_yahoo_dependency(snapshot=snapshot, generations_root=root,
            now=now, dependency_reader=dependency_reader, require_current=require_current)
    return verify_breadth_snapshot(snapshot, yahoo=yahoo, now=now, require_current=require_current)
