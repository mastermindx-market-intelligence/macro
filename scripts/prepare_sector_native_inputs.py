"""Bounded native-input preparation for the incumbent VPS source owner.

Children capture or acquire values only. The invoking Orchestrator owns every
publication, its original selection fences and the actual publication clocks.
The private temporary handoff is neither a selected generation nor a cache.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import sys
from types import MappingProxyType

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from lib import breadth_member_generation_contract as broad
from lib import member_ohlcv_generation_contract as candles
from lib import yahoo_generation_contract as yahoo
from lib import adjusted_price_capture as values
from lib.yahoo_generation_contract import _instant
from scripts import vps_live_orchestrator as owner

SCHEMA = "sector_native_preparation.v1"
REQUEST_SCHEMA = "sector_native_request.v1"
METADATA = "prepared.json"
MAX_METADATA_BYTES = 8 * 1024 * 1024
MAX_REQUEST_BYTES = 32 * 1024 * 1024
KINDS = ("yahoo", "breadth", "member")
REQUEST_MEMBERS = ("config.yml", "delisted_symbols.yml", "membership.json",
    "indices/nasdaq.json", "indices/russell.json",
    *(f"constituents/{group}.parquet" for group in broad.BROAD_GROUPS))


def _contract(kind):
    if kind == "yahoo":
        return yahoo.YAHOO_GENERATION_DOMAIN, yahoo.YAHOO_GENERATION_MEMBERS
    if kind == "breadth":
        return broad.DOMAIN, broad.MEMBERS
    if kind == "member":
        return candles.DOMAIN, candles.MEMBERS
    raise ValueError("unknown_native_phase")


def _stage(stage, *, empty=False):
    path = Path(stage)
    if (not path.is_absolute() or path.is_symlink() or not path.is_dir()
            or path.stat().st_mode & 0o077 or any(p.is_symlink() for p in path.parents)
            or (empty and any(path.iterdir()))):
        raise ValueError("private_empty_native_stage_required" if empty else "private_native_stage_required")
    return path


def _write(stage, raw, metadata):
    stage = _stage(stage, empty=True)
    if any(owner._artifact_name_error(name) for name in raw) or owner._artifact_collision_error(tuple(raw)):
        raise ValueError("native_stage_member_name_invalid")
    for name, data in raw.items():
        target = stage / name
        owner._private_dir(target.parent)
        owner._write_private_bytes(target, data)
    encoded = owner._canonical_json(metadata)
    if len(encoded) > MAX_METADATA_BYTES:
        raise ValueError("native_metadata_bound")
    owner._write_private_bytes(stage / METADATA, encoded)


def _read(stage, names, *, total_limit):
    stage = _stage(stage)
    expected = set(names) | {METADATA}
    files, directories, errors = owner._tree_members(stage)
    if errors or files != expected or directories != owner._expected_directories(tuple(expected)):
        raise ValueError("incomplete_or_unsafe_native_stage")
    metadata = broad._json(owner._read_source_bytes(stage / METADATA,
        limit=MAX_METADATA_BYTES, require_stable=True))
    raw, total = {}, 0
    for name in names:
        item = owner._read_source_bytes(stage / name,
            limit=min(broad.MAX_MEMBER_BYTES, total_limit - total), require_stable=True)
        total += len(item)
        if total > total_limit:
            raise ValueError("native_stage_bundle_bound")
        raw[name] = item
    facts = {name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
             for name, data in raw.items()}
    if type(metadata) is not dict or metadata.get("members") != facts:
        raise ValueError("native_stage_bytes_changed")
    return raw, metadata


def _descriptor(snapshot, captured_at, *, absence=None):
    return {"generation_id": None if snapshot is None else snapshot.generation_id,
        "content_id": None if snapshot is None else snapshot.content_id,
        "published_at": None if snapshot is None else snapshot.published_at,
        "source_revision": None if snapshot is None else snapshot.manifest["source_revision"],
        "captured_at": _instant(captured_at).isoformat(), "absence_reason": absence}


def capture_request(*, repository_root, generations_root, source_revision,
                    attempt_id, allow_bootstrap, stage, clock):
    from lib import sector_auxiliary_capture as aux
    from lib.sector_input_capture import _observe_sector_source
    from lib.ticker_aliases import YAHOO_FETCH_ALIASES

    root = Path(repository_root)
    if (not root.is_absolute() or ".." in root.parts or type(allow_bootstrap) is not bool
            or not re.fullmatch(r"[0-9a-f]{40}", source_revision)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,100}", attempt_id)):
        raise ValueError("explicit_native_request_identity_required")
    last = _instant(clock())
    def observed_clock():
        nonlocal last
        stamp = _instant(clock())
        if stamp < last:
            raise ValueError("nonmonotonic_native_capture_clock")
        last = stamp
        return stamp
    observations = {}
    def observe(name, path, limit):
        item = _observe_sector_source(path, limit=limit, clock=observed_clock)
        if item.outcome != "present":
            raise ValueError("native_source_" + name + "_" + item.outcome)
        observations[name] = item
        return item.raw_bytes
    config_bytes = observe("config.yml", root / "config.yml", aux.MIB)
    cfg, _ = aux._yaml(config_bytes)
    storage = cfg.get("storage") if type(cfg) is dict else None
    setting = storage.get("data_dir") if type(storage) is dict else None
    if type(setting) is not str or not setting or len(setting) > 2048:
        raise ValueError("native_storage_root_required")
    data = root / setting
    if not data.is_absolute() or ".." in data.parts:
        raise ValueError("native_storage_root_invalid")
    observe("delisted_symbols.yml", root / "config/delisted_symbols.yml", aux.MIB)
    observe("membership.json", data / "baskets/membership.json", 8 * aux.MIB)
    for family in ("nasdaq", "russell"):
        observe("indices/" + family + ".json", data / ("baskets_" + family) / "membership.json", aux.MIB)
    for group in broad.BROAD_GROUPS:
        observe("constituents/" + group + ".parquet", data / group / "constituents.parquet", 4 * aux.MIB)
    raw = {name: item.raw_bytes for name, item in observations.items()}
    if set(raw) != set(REQUEST_MEMBERS) or sum(map(len, raw.values())) > MAX_REQUEST_BYTES:
        raise ValueError("native_request_bundle_bound")
    priors = {}
    for kind in KINDS:
        domain, members = _contract(kind)
        try:
            snapshot = owner.read_selected_generation(generations_root=Path(generations_root),
                domain=domain, members=members)
        except owner.SelectedGenerationAbsent as exc:
            if not allow_bootstrap:
                raise ValueError("native_bootstrap_required:" + domain) from exc
            priors[kind] = _descriptor(None, observed_clock(), absence=exc.reason)
        else:
            priors[kind] = _descriptor(snapshot, observed_clock())
    aliases = deepcopy(dict(YAHOO_FETCH_ALIASES))
    facts = {name: {"sha256": item.sha256, "bytes": item.byte_length} for name, item in observations.items()}
    fingerprint = hashlib.sha256(owner._canonical_json({"members": facts, "aliases": aliases})).hexdigest()
    metadata = {"schema": REQUEST_SCHEMA, "attempt_id": attempt_id, "source_revision": source_revision,
        "allow_bootstrap": allow_bootstrap, "captured_at": observed_clock().isoformat(),
        "fingerprint": fingerprint, "aliases": aliases, "priors": priors, "members": facts,
        "sources": {name: {"origin": item.origin, "source_revision": item.source_revision,
            "captured_at": item.captured_at.isoformat(), "sha256": item.sha256,
            "byte_length": item.byte_length} for name, item in observations.items()}}
    # Decode/preflight all declarations before any provider phase can start.
    _decode_inputs(raw, metadata)
    _write(stage, raw, metadata)
    return metadata


def read_request(stage, *, attempt_id, source_revision):
    raw, metadata = _read(stage, REQUEST_MEMBERS, total_limit=MAX_REQUEST_BYTES)
    if (set(metadata) != {"schema", "attempt_id", "source_revision", "allow_bootstrap", "captured_at",
            "fingerprint", "aliases", "priors", "members", "sources"}
            or metadata["schema"] != REQUEST_SCHEMA or metadata["attempt_id"] != attempt_id
            or metadata["source_revision"] != source_revision or type(metadata["allow_bootstrap"]) is not bool
            or type(metadata["aliases"]) is not dict or type(metadata["priors"]) is not dict
            or set(metadata["priors"]) != set(KINDS)
            or type(metadata["sources"]) is not dict or set(metadata["sources"]) != set(REQUEST_MEMBERS)):
        raise ValueError("native_request_identity_changed")
    fingerprint = hashlib.sha256(owner._canonical_json(
        {"members": metadata["members"], "aliases": metadata["aliases"]})).hexdigest()
    if metadata["fingerprint"] != fingerprint:
        raise ValueError("native_request_fingerprint_changed")
    stamp = _instant(metadata["captured_at"])
    for kind, prior in metadata["priors"].items():
        if type(prior) is not dict or set(prior) != {"generation_id", "content_id", "published_at",
                "source_revision", "captured_at", "absence_reason"} or _instant(prior["captured_at"]) > stamp:
            raise ValueError("native_prior_descriptor_invalid")
        if prior["content_id"] is None:
            if (not metadata["allow_bootstrap"] or prior["absence_reason"] not in {"domain_absent", "selection_absent"}
                    or any(prior[k] is not None for k in ("generation_id", "published_at", "source_revision"))):
                raise ValueError("native_prior_absence_invalid")
        elif (prior["absence_reason"] is not None
                or not isinstance(prior["generation_id"], str)
                or owner._generation_id_error(prior["generation_id"])
                or not re.fullmatch(r"[0-9a-f]{64}", prior["content_id"])
                or not re.fullmatch(r"[0-9a-f]{40}", prior["source_revision"])
                or _instant(prior["published_at"]) > _instant(prior["captured_at"])):
            raise ValueError("native_prior_descriptor_invalid")
    for name, fact in metadata["sources"].items():
        if (type(fact) is not dict or set(fact) != {"origin", "source_revision", "captured_at", "sha256", "byte_length"}
                or type(fact["origin"]) is not str or not 0 < len(fact["origin"]) <= 2048
                or fact["source_revision"] is not None
                or _instant(fact["captured_at"]) > stamp
                or fact["sha256"] != metadata["members"][name]["sha256"]
                or fact["byte_length"] != len(raw[name])):
            raise ValueError("native_source_identity_changed")
    return raw, metadata


def _constituents(raw, group):
    import pyarrow as pa
    from lib.sector_auxiliary_capture import _open, MAX_FOOTER_BYTES
    if (len(raw) < 12 or raw[:4] != b"PAR1" or raw[-4:] != b"PAR1"
            or not 0 < int.from_bytes(raw[-8:-4], "little") <= min(MAX_FOOTER_BYTES, len(raw) - 12)):
        raise ValueError("native_constituents_footer_invalid")
    with _open(raw) as parquet:
        schema = parquet.schema_arrow
        if (len(schema.names) != 3 or set(schema.names) != {"symbol", "name", "sector"}
                or not 0 < parquet.metadata.num_rows <= values.MAX_COLUMNS
                or any(not (pa.types.is_string(f.type) or pa.types.is_large_string(f.type)
                            or f.name == "sector" and pa.types.is_null(f.type)) for f in schema)
                or sum(parquet.metadata.row_group(i).total_byte_size
                       for i in range(parquet.metadata.num_row_groups)) > 16 * 1024 * 1024):
            raise ValueError("native_constituents_shape_or_decode_bound")
        frame = parquet.read().to_pandas(ignore_metadata=True)
    return broad._constituents(frame[["symbol", "name", "sector"]].to_dict("records"), group)


def _decode_inputs(raw, request):
    from lib import sector_auxiliary_capture as aux, delisted_symbols
    from lib.sector_index_membership_capture import capture_index_membership
    from collectors.yahoo import YahooRequestSettings
    from collectors.breadth import capture_adjusted_policy
    import pandas as pd

    cfg, _ = aux._yaml(raw["config.yml"])
    ledger, _ = aux._yaml(raw["delisted_symbols.yml"])
    if type(cfg) is not dict or type(ledger) is not dict:
        raise ValueError("native_configuration_mapping_required")
    YahooRequestSettings.capture(cfg.get("yahoo"))
    for group in broad.BROAD_GROUPS:
        cfg[group] = capture_adjusted_policy(cfg.get(group))
    membership, _ = aux._json(raw["membership.json"])
    # This index is a preflight calendar only; it is never a price observation.
    from lib.market_session import expected_session
    target = expected_session("US", _instant(request["captured_at"]))
    broad._membership(membership, pd.DataFrame(index=pd.DatetimeIndex([target])))
    index_sources = {}
    for family in ("nasdaq", "russell"):
        name = "indices/" + family + ".json"
        fact = request["sources"][name]
        index_sources[family] = aux.CapturedAuxiliarySource(fact["origin"], None,
            _instant(fact["captured_at"]), "present", "observed", raw[name], fact["byte_length"], fact["sha256"])
    index_membership = capture_index_membership(index_sources, before=request["captured_at"])
    members = {group: _constituents(raw["constituents/" + group + ".parquet"], group)
               for group in broad.BROAD_GROUPS}
    return cfg, membership, index_membership, members, frozenset(delisted_symbols.ledger_from_document(ledger))


def _breadth_classes():
    from collectors.breadth import BreadthAdapter
    from collectors.smallcap_breadth import SmallCapBreadthAdapter
    from collectors.midcap_breadth import MidCap400BreadthAdapter
    return dict(zip(broad.BROAD_GROUPS, (BreadthAdapter, SmallCapBreadthAdapter, MidCap400BreadthAdapter)))


def _source_captures(request):
    captures = {group: {"source_ref": "sha256:" + request["members"]["constituents/" + group + ".parquet"]["sha256"],
        "source_revision": request["source_revision"],
        "captured_at": request["sources"]["constituents/" + group + ".parquet"]["captured_at"]}
        for group in broad.BROAD_GROUPS}
    captures["membership"] = _policy_capture(request)
    return captures


def _policy_capture(request):
    return {"source_ref": "native-request:" + request["fingerprint"],
        "source_revision": request["source_revision"], "captured_at": request["captured_at"]}


def _breadth_prior_identity(request, prior):
    captured_at = request["priors"]["breadth"]["captured_at"]
    if prior is not None:
        return prior.prior_identity(captured_at=_instant(captured_at))
    return {"kind": "bootstrap", "domain": broad.DOMAIN,
        "source_ref": "native-absent:" + broad.DOMAIN, "source_revision": request["source_revision"],
        "captured_at": captured_at, "content_id": None, "members": {name: None for name in broad.MEMBERS}}


def _pinned(request, kind, generations_root):
    prior = request["priors"][kind]
    if prior["content_id"] is None:
        return None
    domain, members = _contract(kind)
    snapshot = owner.read_retained_generation(generations_root=Path(generations_root), domain=domain,
        generation_id=prior["generation_id"], content_id=prior["content_id"], members=members)
    if (snapshot.published_at != prior["published_at"]
            or snapshot.manifest["source_revision"] != prior["source_revision"]):
        raise ValueError("native_prior_identity_changed")
    return snapshot


def _dependency(kind, reference, generations_root, clock):
    if (type(reference) is not dict or set(reference) != {"generation_id", "content_id"}
            or not isinstance(reference["generation_id"], str)
            or owner._generation_id_error(reference["generation_id"])
            or not isinstance(reference["content_id"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", reference["content_id"])):
        raise ValueError("native_dependency_reference_invalid")
    domain, members = _contract(kind)
    return owner.read_retained_generation(generations_root=Path(generations_root), domain=domain,
        generation_id=reference["generation_id"], content_id=reference["content_id"], members=members)


def _member_prior(request, generations_root, *, source_session, clock):
    prior = request["priors"]["member"]
    snapshot = _pinned(request, "member", generations_root)
    if snapshot is None:
        # Positively observed native absence; no claim about any legacy file.
        return candles.MemberOHLCVPriorCapture({name: None for name in candles.PANEL_MEMBERS},
            "native-absent:" + candles.DOMAIN, request["source_revision"], source_session,
            _instant(prior["captured_at"]))
    verified = candles.read_verified_member_ohlcv_inputs(generations_root=generations_root,
        now=_instant(clock()), snapshot_reader=lambda **kwargs: snapshot)
    return verified.prior_capture(captured_at=_instant(prior["captured_at"]))


def _yahoo_prior(request, generations_root, clock):
    from lib.yahoo_runtime_profile import SECTOR_CLOSE_TICKERS
    snapshot = _pinned(request, "yahoo", generations_root)
    if snapshot is None:
        bootstrap = yahoo.YahooBootstrapCapture({ticker: None for ticker in SECTOR_CLOSE_TICKERS},
            "native-absent:" + yahoo.YAHOO_GENERATION_DOMAIN, request["source_revision"],
            _instant(request["priors"]["yahoo"]["captured_at"]))
        frames, prior = yahoo.decode_bootstrap_capture(bootstrap)
        return frames, prior, None
    else:
        selected = yahoo.verify_yahoo_snapshot(snapshot, now=_instant(clock()))
        prior = selected.prior_identity(captured_at=_instant(request["priors"]["yahoo"]["captured_at"]))
        return selected.cohort.frames, prior, selected


def _prepare_yahoo(request, cfg, generations_root, clock):
    from collectors.yahoo import YahooAdapter
    from lib.yahoo_runtime_profile import SECTOR_CLOSE_TICKERS
    frames, prior, selected = _yahoo_prior(request, generations_root, clock)
    if selected is not None and selected.cohort.source_session == yahoo._completed_target(_instant(clock())):
        return None
    period = "max" if selected is None else "1mo"
    acquisition = YahooAdapter(yahoo_config=cfg["yahoo"]).acquire_cycle_benchmarks(
        SECTOR_CLOSE_TICKERS, prior_frames=frames, evaluation_instant=_instant(clock()),
        completed_sessions_only=True, period=period)
    if acquisition.accepted is not True:
        raise ValueError("native_yahoo_acquisition_unqualified")
    return yahoo.encode_yahoo_acquisition(acquisition, prior_identity=prior,
        prepared_at=_instant(clock()), source_revision=request["source_revision"])


def _captured_yahoo(dependencies, generations_root, clock):
    return yahoo.verify_yahoo_snapshot(_dependency("yahoo", dependencies["yahoo"], generations_root, clock),
        now=_instant(clock()), require_current=True)


def _captured_breadth(dependencies, generations_root, captured_yahoo, clock):
    return broad.verify_breadth_snapshot(_dependency("breadth", dependencies["breadth"], generations_root, clock),
        yahoo=captured_yahoo, now=_instant(clock()), require_current=True)


def _references(membership, primary, captured_yahoo, cfg, aliases, clock):
    from collectors.yahoo import YahooRequestSettings
    from scripts.fetch_basket_extras import _download_closes, START
    _, _, _, _, required = broad._membership(membership, primary)
    names = sorted(set(required) - set(captured_yahoo.cohort.frames))
    mapping = {ticker: aliases.get(ticker, ticker) for ticker in names}
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("native_reference_alias_collision")
    frames = {ticker: None for ticker in names}
    evidence = {ticker: {"status": "absent", "reason": "acquisition_failed"} for ticker in names}
    if not names:
        return frames, evidence
    try:
        downloaded = _download_closes(list(mapping.values()), request_settings=YahooRequestSettings.capture(cfg["yahoo"]),
            history_start=START, source_session=captured_yahoo.cohort.source_session)
    except RuntimeError:
        return frames, evidence
    downloaded = values.capture_close_panel(downloaded, source_session=captured_yahoo.cohort.source_session)
    if not set(downloaded.columns).issubset(mapping.values()):
        raise ValueError("native_reference_population_changed")
    for ticker, vendor in mapping.items():
        if vendor not in downloaded:
            continue
        column = downloaded[vendor].dropna()
        if len(column) < 62:
            evidence[ticker]["reason"] = "insufficient_observations"
        elif column.index[-1].date().isoformat() != captured_yahoo.cohort.source_session:
            evidence[ticker]["reason"] = "not_current"
        else:
            frames[ticker] = column.to_frame("close")
            evidence[ticker] = {"status": "available", "basis": "provider_auto_adjusted",
                "source_ref": "yahoo:" + vendor, "captured_at": _instant(clock()).isoformat()}
    return frames, evidence


def _prepare_breadth(request, inputs, generations_root, dependencies, clock):
    from scripts.fetch_basket_extras import acquire_extras_from_inputs, START
    cfg, membership, index_membership, members, excluded = inputs
    captured_yahoo = _captured_yahoo(dependencies, generations_root, clock)
    snapshot = _pinned(request, "breadth", generations_root)
    prior = None
    if snapshot is not None:
        old_yahoo = broad.read_breadth_yahoo_dependency(snapshot=snapshot,
            generations_root=generations_root, now=_instant(clock()))
        prior = broad.verify_breadth_snapshot(snapshot, yahoo=old_yahoo, now=_instant(clock()))
        if (prior.inputs.source_session == captured_yahoo.cohort.source_session
                and prior.inputs.receipt["yahoo"]["content_id"] == captured_yahoo.snapshot.content_id
                and prior.inputs.receipt["source_captures"]["membership"]["source_ref"] ==
                    "native-request:" + request["fingerprint"]
                and prior.inputs.receipt.get("index_membership") is not None):
            return None
    groups = {}
    classes = _breadth_classes()
    for group in broad.BROAD_GROUPS:
        previous = ({field: None for field in values.FIELDS} if prior is None else prior.inputs.groups[group])
        period = f"{max(1, cfg[group]['lookback_days_live'] // 365 + 1)}y" if prior is None else "1mo"
        groups[group] = classes[group](breadth_config=cfg[group], yahoo_config=cfg["yahoo"]).acquire_adjusted_prices(
            members=members[group], prior_panels=previous, excluded_symbols=excluded,
            aliases=request["aliases"], evaluation_instant=_instant(clock()), period=period)
        if groups[group].accepted is not True:
            raise ValueError("native_" + group + "_acquisition_unqualified")
    _, primary, meta, _ = broad.derive_primary({key: value.panels for key, value in groups.items()},
        captured_yahoo.cohort.frames["SPY"], source_session=captured_yahoo.cohort.source_session)
    qualified = frozenset(t for t, group in meta["source"].items() if t in groups[group].current)
    extra = acquire_extras_from_inputs(membership=membership, primary_panel=primary,
        prior_extras=None if prior is None else prior.inputs.extras, qualified_primary_members=qualified,
        primary_history_threshold=max(max(cfg[g]["ma_windows"] + [cfg[g]["nhnl_window"]]) for g in broad.BROAD_GROUPS),
        evaluation_instant=_instant(clock()), yahoo_config=cfg["yahoo"], aliases=request["aliases"],
        history_start=START, primary_basis="provider_auto_adjusted", index_membership=index_membership)
    references, reference_evidence = _references(membership, primary, captured_yahoo,
        cfg, request["aliases"], clock)
    # This reference binds the whole captured request, including policy and the
    # actual index bytes. source_revision identifies the capture program; the
    # original mutable-file revisions remain explicitly unknown in the request.
    return broad.encode_breadth_member_acquisitions(groups=groups, extras=extra,
        membership=membership, yahoo=captured_yahoo, reference_frames=references,
        reference_evidence=reference_evidence, source_captures=_source_captures(request),
        prior_identity=_breadth_prior_identity(request, prior),
        prepared_at=_instant(clock()), source_revision=request["source_revision"], index_membership=index_membership)


def _prepare_member(request, inputs, generations_root, dependencies, clock):
    from collectors.yahoo import YahooRequestSettings
    from scripts import fetch_basket_ohlcv
    cfg, _, _, _, excluded = inputs
    captured_yahoo = _captured_yahoo(dependencies, generations_root, clock)
    breadth = _captured_breadth(dependencies, generations_root, captured_yahoo, clock)
    snapshot = _pinned(request, "member", generations_root)
    prior_frames = {}
    requested, *_ = broad._membership(breadth.inputs.membership, breadth.inputs.primary)
    if snapshot is not None:
        old = candles.read_verified_member_ohlcv_inputs(generations_root=generations_root,
            now=_instant(clock()), snapshot_reader=lambda **kwargs: snapshot)
        if (old.inputs.source_session == breadth.inputs.source_session
                and old.inputs.receipt["breadth"]["content_id"] == breadth.snapshot.content_id
                and old.inputs.receipt["policy_capture"]["source_ref"] == "native-request:" + request["fingerprint"]):
            return None
        prior_frames = old.inputs.frames([t for t in requested if t in old.inputs.panels["close"].columns])
    prior = _member_prior(request, generations_root, source_session=breadth.inputs.source_session, clock=clock)
    acquisition = fetch_basket_ohlcv.acquire_ohlcv_from_inputs(requested=requested, prior_frames=prior_frames,
        aliases=request["aliases"], excluded_symbols=excluded, request_settings=YahooRequestSettings.capture(cfg["yahoo"]),
        history_start=fetch_basket_ohlcv.START, evaluation_instant=_instant(clock()))
    return candles.encode_member_ohlcv_acquisition(acquisition=acquisition, breadth=breadth,
        yahoo=captured_yahoo, prior=prior, policy_capture=_policy_capture(request),
        prepared_at=_instant(clock()), source_revision=request["source_revision"])


def prepare_phase(*, kind, request_stage, stage, generations_root, attempt_id,
                  source_revision, dependencies, clock):
    raw, request = read_request(request_stage, attempt_id=attempt_id, source_revision=source_revision)
    inputs = _decode_inputs(raw, request)
    expected_dependencies = set() if kind == "yahoo" else {"yahoo"} if kind == "breadth" else {"yahoo", "breadth"}
    if kind not in KINDS or type(dependencies) is not dict or set(dependencies) != expected_dependencies:
        raise ValueError("native_dependency_set_invalid")
    if kind == "yahoo":
        encoded = _prepare_yahoo(request, inputs[0], generations_root, clock)
    elif kind == "breadth":
        encoded = _prepare_breadth(request, inputs, generations_root, dependencies, clock)
    else:
        encoded = _prepare_member(request, inputs, generations_root, dependencies, clock)
    members = {} if encoded is None else dict(encoded.members)
    if encoded is not None and set(members) != set(_contract(kind)[1]):
        raise ValueError("native_phase_member_set_invalid")
    metadata = {"schema": SCHEMA, "kind": kind, "source_revision": source_revision,
        "generation_id": attempt_id + "-" + kind, "request_fingerprint": request["fingerprint"],
        "expected_current_content_id": request["priors"][kind]["content_id"],
        "dependencies": deepcopy(dependencies), "reused": encoded is None,
        "input_identity": None if encoded is None else dict(encoded.input_identity),
        "members": {name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                    for name, data in members.items()}}
    _write(stage, members, metadata)
    return metadata


def _bind_candidate(kind, encoded, *, request, request_members, generations_root, clock):
    """Compare payload claims with the parent's original captured inputs.

    A semantically valid bundle from another request is not this preparation.
    Generic publication validates the bundle itself after this external binding.
    """
    from collectors.yahoo import YahooRequestSettings
    from scripts import fetch_basket_extras, fetch_basket_ohlcv

    facts = {name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
             for name, data in request_members.items()}
    if facts != request["members"]:
        raise ValueError("native_parent_request_bytes_changed")
    cfg, membership, index_membership, members, excluded = _decode_inputs(request_members, request)
    settings = YahooRequestSettings.capture(cfg["yahoo"])
    common = {key: getattr(settings, key) for key in
              ("batch_size", "retries", "backoff_base_s", "basis_tolerance")}

    def require(actual, expected):
        if actual != expected:
            raise ValueError("native_candidate_request_binding_mismatch")

    def policy(actual, expected):
        require({key: actual.get(key) for key in expected}, expected)

    def aliases(evidence):
        for ticker, row in evidence.items():
            require(row["vendor_symbol"], request["aliases"].get(ticker, ticker))

    if kind == "yahoo":
        value = encoded.input_identity["yahoo_cohort"]
        _, prior_identity, prior = _yahoo_prior(request, generations_root, clock)
        require(value["prior"], prior_identity)
        policy(value["clocks"]["known"], {**common, "fetch_period": "max" if prior is None else "1mo"})
        return
    receipt = broad._json(encoded.members["acquisition.json"])
    if kind == "member":
        _, prior_identity, _ = candles._prior(encoded.prior,
            before=_instant(receipt["prepared_at"]), source=receipt["source_session"])
        require(receipt["prior"], prior_identity)
        require(receipt["policy_capture"], _policy_capture(request))
        evidence = receipt["acquisition"]["evidence"]
        require(evidence["request"], {**common, "history_start": fetch_basket_ohlcv.START,
            "minimum_repair_sessions": 1, "full_replacement": True, "allow_historical_replacement": True})
        aliases(evidence["members"])
        for ticker, row in evidence["members"].items():
            require(row["excluded_by_captured_policy"], ticker in excluded)
        return
    snapshot = _pinned(request, "breadth", generations_root)
    prior = None
    if snapshot is not None:
        old_yahoo = broad.read_breadth_yahoo_dependency(snapshot=snapshot,
            generations_root=generations_root, now=_instant(clock()))
        prior = broad.verify_breadth_snapshot(snapshot, yahoo=old_yahoo, now=_instant(clock()))
    require(receipt["prior"], _breadth_prior_identity(request, prior))
    require(receipt["source_captures"], _source_captures(request))
    require(encoded.members["baskets/membership.json"], broad._json_bytes(membership))
    require(receipt.get("index_membership"), index_membership)
    for group, adapter_class in _breadth_classes().items():
        group_cfg = cfg[group]
        adapter = adapter_class(breadth_config=group_cfg, yahoo_config=cfg["yahoo"])
        expected_members = adapter.constituents_checked(adapter._repair(members[group],
            ticker_fixups=group_cfg["ticker_fixups"], excluded_symbols=excluded))
        require(broad._json(encoded.members[f"groups/{group}/constituents.json"]),
                expected_members.to_dict("records"))
        evidence = receipt["groups"][group]["evidence"]
        require(evidence["selection_policy"], {"ma_windows": group_cfg["ma_windows"],
            "nhnl_window": group_cfg["nhnl_window"], "ticker_fixups": group_cfg["ticker_fixups"],
            "excluded_symbols": sorted(excluded)})
        policy(evidence["request"], {**common, "period": "1mo" if prior is not None else
            f"{max(1, group_cfg['lookback_days_live'] // 365 + 1)}y",
            "minimum_repair_sessions": max(*group_cfg["ma_windows"], group_cfg["nhnl_window"]),
            "calculation_lookback_days": group_cfg["lookback_days_live"]})
        aliases(evidence["members"])
    extras = receipt["extras"]["evidence"]
    require(extras["request"], {key: value for key, value in common.items() if key != "basis_tolerance"} |
        {"history_start": fetch_basket_extras.START, "primary_history_threshold":
         max(max(*cfg[group]["ma_windows"], cfg[group]["nhnl_window"]) for group in broad.BROAD_GROUPS)})
    aliases(extras["members"])
    for ticker, evidence in receipt["references"].items():
        if evidence["status"] == "available":
            require(evidence["source_ref"], "yahoo:" + request["aliases"].get(ticker, ticker))


def read_prepared(stage, *, kind, request, request_members, generations_root, dependencies, clock):
    # Read the small discriminator, then require the exact closed phase inventory.
    stage = _stage(stage)
    header = broad._json(owner._read_source_bytes(stage / METADATA,
        limit=MAX_METADATA_BYTES, require_stable=True))
    if type(header) is not dict or type(header.get("reused")) is not bool:
        raise ValueError("native_candidate_header_invalid")
    _, names = _contract(kind)
    members, metadata = _read(stage, () if header["reused"] else names,
                             total_limit=owner.MAX_GENERATION_BYTES)
    if (metadata != header or set(metadata) != {"schema", "kind", "source_revision", "generation_id",
            "request_fingerprint", "expected_current_content_id", "dependencies", "reused", "input_identity", "members"}
            or metadata["schema"] != SCHEMA or metadata["kind"] != kind
            or metadata["source_revision"] != request["source_revision"]
            or metadata["generation_id"] != request["attempt_id"] + "-" + kind
            or metadata["request_fingerprint"] != request["fingerprint"]
            or metadata["expected_current_content_id"] != request["priors"][kind]["content_id"]
            or metadata["dependencies"] != dependencies):
        raise ValueError("native_candidate_identity_changed")
    if metadata["reused"]:
        if metadata["input_identity"] is not None or metadata["expected_current_content_id"] is None:
            raise ValueError("native_reuse_identity_invalid")
        domain, names = _contract(kind)
        selected = owner.read_selected_generation(generations_root=Path(generations_root), domain=domain, members=names)
        if selected.content_id != metadata["expected_current_content_id"]:
            raise ValueError("native_reuse_selection_changed")
        if kind == "yahoo":
            yahoo.verify_yahoo_snapshot(selected, now=_instant(clock()), require_current=True)
        else:
            captured_yahoo = _captured_yahoo(dependencies, generations_root, clock)
            if kind == "breadth":
                verified = broad.verify_breadth_snapshot(selected, yahoo=captured_yahoo,
                    now=_instant(clock()), require_current=True)
                if (verified.inputs.receipt["source_captures"]["membership"]["source_ref"] !=
                        "native-request:" + request["fingerprint"]
                        or verified.inputs.receipt.get("index_membership") is None):
                    raise ValueError("native_reuse_request_changed")
            else:
                breadth = _captured_breadth(dependencies, generations_root, captured_yahoo, clock)
                verified = candles.read_verified_member_ohlcv_inputs(generations_root=generations_root,
                    now=_instant(clock()), breadth=breadth, yahoo=captured_yahoo,
                    snapshot_reader=lambda **kwargs: selected, require_current=True)
                if verified.inputs.receipt["policy_capture"]["source_ref"] != "native-request:" + request["fingerprint"]:
                    raise ValueError("native_reuse_request_changed")
        return None, metadata, selected
    identity = metadata["input_identity"]
    if kind == "yahoo":
        declared_prior = identity["yahoo_cohort"]["prior"]
        encoded = yahoo.EncodedYahooInputs(MappingProxyType(members), identity)
    else:
        receipt = broad._json(members["acquisition.json"])
        declared_prior = receipt["prior"]
        captured_yahoo = _captured_yahoo(dependencies, generations_root, clock)
        if kind == "breadth":
            encoded = broad.EncodedBreadthMemberInputs(MappingProxyType(members), identity, captured_yahoo)
        else:
            breadth = _captured_breadth(dependencies, generations_root, captured_yahoo, clock)
            prior = _member_prior(request, generations_root, source_session=breadth.inputs.source_session, clock=clock)
            encoded = candles.EncodedMemberOHLCVInputs(MappingProxyType(members), identity, breadth, captured_yahoo, prior)
    if (declared_prior["content_id"] != metadata["expected_current_content_id"]
            or declared_prior["kind"] != ("bootstrap" if metadata["expected_current_content_id"] is None else "generation")):
        raise ValueError("native_candidate_original_fence_changed")
    _bind_candidate(kind, encoded, request=request, request_members=request_members,
        generations_root=generations_root, clock=clock)
    return encoded, metadata, None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("capture", *KINDS), required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--generations-root", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--request-stage", type=Path)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--allow-bootstrap", action="store_true")
    parser.add_argument("--yahoo-generation-id")
    parser.add_argument("--yahoo-content-id")
    parser.add_argument("--breadth-generation-id")
    parser.add_argument("--breadth-content-id")
    parser.add_argument("--now", help="deterministic test clock")
    args = parser.parse_args(argv)
    fixed = _instant(args.now) if args.now else None
    clock = lambda: fixed if fixed is not None else datetime.now(timezone.utc)
    if args.phase == "capture":
        capture_request(repository_root=args.repository_root, generations_root=args.generations_root,
            source_revision=args.source_revision, attempt_id=args.attempt_id, allow_bootstrap=args.allow_bootstrap,
            stage=args.stage, clock=clock)
    else:
        if args.request_stage is None or args.allow_bootstrap:
            parser.error("acquisition requires the original captured request")
        dependencies = {}
        for kind in ("yahoo", "breadth"):
            generation_id, content_id = getattr(args, kind + "_generation_id"), getattr(args, kind + "_content_id")
            if generation_id is not None or content_id is not None:
                dependencies[kind] = {"generation_id": generation_id, "content_id": content_id}
        prepare_phase(kind=args.phase, request_stage=args.request_stage, stage=args.stage,
            generations_root=args.generations_root, attempt_id=args.attempt_id,
            source_revision=args.source_revision, dependencies=dependencies, clock=clock)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
