"""Read-only request composition for F04-X2; no calendar, rights or beta invention.

Uses the existing X1 composer, its exact read manifest and native TXI definition.
WTI history comes from the snapshot-bound Yahoo export and matching TXI read.
A separate server-side owner must verify the mapping of vendor labels to
completed sessions, future sessions, cutoff and source use. Rates use
their existing native calibration plus additive sample/clock metadata instead;
no future price calendar or request-time fitting is needed for that illustration.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, date, datetime
import hashlib
import json
from pathlib import Path

import pandas as pd
import yaml

from engine.ontology_explorer import DEFAULT_CHAIN, SourceIncoherent, compose_snapshot
from engine.ontology_scenario import SeriesBaseline, evaluate_scenario, _stamp
from engine import transmission_chains as txi
from lib import store

METHOD = 'ontology_scenario.runtime.v2'


class ScenarioSnapshotChanged(ValueError):
    """The explicitly selected reading no longer matches the native owner bytes."""


class NativeScenarioInputsUnavailable(ValueError):
    def __init__(self, reason: str, missing: tuple[str, ...]):
        self.reason, self.missing = reason, missing
        super().__init__(reason)


@dataclass(frozen=True)
class VerifiedWTISessions:
    """Server-only evidence from an admitted owner. Never deserialize from a POST or export.

    historical_labels pairs every raw CL=F bar label with its verified completed
    session. known_by covers the calendar, completed labels and source-use receipt.
    No production authority for these facts is installed today.
    """
    observation_sha256: str
    txi_generation: str
    manifest_hash: str
    knowledge_cutoff: str
    known_by: str
    last_session_completed_at: str
    historical_labels: tuple[tuple[str, str], ...]
    future_sessions: tuple[str, ...]
    calendar_id: str
    calendar_version: str
    rights_ref: str


_WTI_FILE = 'data/yahoo/CL_F.parquet'
_WTI_EXPORT = 'data/yahoo/CL_F.observation.json'
_TXI_STATE = 'data/transmission/chain_state.json'


def _unqualified(*missing: str) -> NativeScenarioInputsUnavailable:
    return NativeScenarioInputsUnavailable('WTI_FUTURES_CALENDAR_UNAVAILABLE', missing)


def _image_bytes(envelope: dict) -> bytes:
    raw = base64.b64decode(envelope['content_base64'], validate=True)
    if len(raw) != envelope['bytes'] or hashlib.sha256(raw).hexdigest() != envelope['sha256']:
        raise ValueError('capture image binding')
    return raw


def _wti_history(root: Path, observation: dict, cutoff: datetime) -> tuple[dict, str, dict, str]:
    """Validate and read the same capture image that the exporter checked against parquet."""
    export = json.loads(_read_bound(root, observation))
    if export['schema'] != 'yahoo.wti_observation_export.v1' or export['ticker'] != 'CL=F':
        raise ValueError('observation identity')
    receipt = json.loads(_image_bytes(export['capture_receipt']))
    provider = _image_bytes(export['provider_return_image'])
    merged = _image_bytes(export['merged_capture_image'])
    generation = 'sha256:' + hashlib.sha256(merged).hexdigest()
    if (receipt['schema'] != 'yahoo.wti_observation_capture.v1' or receipt['ticker'] != 'CL=F'
            or receipt['series_generation'] != generation
            or any(receipt[k]['sha256'] != export[k]['sha256'] or receipt[k]['bytes'] != len(raw)
                   for k, raw in [('provider_return_image', provider), ('merged_capture_image', merged)])):
        raise ValueError('capture generation')
    lineage = receipt['source_lineage']
    if (lineage['provider'], lineage['ticker'], lineage['series_identity']) != (
            'yahoo', 'CL=F', 'vendor_continuous_CL=F') or (lineage['field'], lineage['basis']) not in {
            ('Adj Close', 'vendor_continuous_adjusted_close'), ('Close', 'vendor_continuous_close_no_adj_close_returned')}:
        raise ValueError('WTI source basis')
    clocks = [_stamp(receipt['provider_return_image']['adapter_return_known_by_utc']),
              _stamp(receipt['merged_capture_image']['captured_known_by_utc']),
              _stamp(receipt['merged_capture_image']['immutable_publication_durable_at_utc']),
              _stamp(export['exported_known_by_utc']), cutoff]
    if clocks != sorted(clocks):
        raise _unqualified('native_series_generation_at_cutoff')
    parquet = store._wti_parquet_bytes(root / _WTI_FILE)
    binding = dict(path=_WTI_FILE, bytes=len(parquet), sha256=hashlib.sha256(parquet).hexdigest())
    if export['canonical_parquet'] != binding or store._wti_parquet_image(parquet) != merged:
        raise ValueError('published WTI parquet')
    return json.loads(merged), generation, binding, receipt['effective_bar_date']


def _wti_txi_generation(root: Path, state_receipt: dict, source: dict, binding: dict, cutoff: datetime) -> str:
    state = json.loads(_read_bound(root, state_receipt))
    capture = state['input_capture']
    # The WTI input of this selected generation, not a claim about other TXI inputs.
    txi_generation = capture['generation_id']
    capture_digest = hashlib.sha256(txi._capture_json(
        {k: v for k, v in capture.items() if k != 'generation_id'})).hexdigest()
    if (capture['schema'] != 'txi.prospective_input_read.v1' or capture['status'] != 'observed_input_bytes'
            or txi_generation != 'sha256:' + capture_digest or capture['observation_asof'] != source['asof']
            or state['built'] != source['built'] or state['asof'] != source['asof']
            or capture['causal_state_sha256'] != hashlib.sha256(txi._capture_json(txi._causal_projection(state))).hexdigest()
            or [r for r in capture['reads'] if r['path'] == _WTI_FILE] != [{**binding, 'status': 'present'}]):
        raise _unqualified('native_txi_generation_binding')
    if not (_stamp(capture['capture_started_at']) <= _stamp(capture['capture_completed_at']) <= cutoff):
        raise _unqualified('native_txi_generation_at_cutoff')
    return txi_generation


def _load_native_baseline(root: Path, snapshot: dict, assumption: dict, *,
                          verified_sessions: VerifiedWTISessions | None = None) -> SeriesBaseline:
    """Compose the existing series contract from one pinned publication and owner admission."""
    if assumption['node_ref'] != 'yahoo:CL=F':
        raise NativeScenarioInputsUnavailable('NUMERIC_OWNER_METADATA_UNAVAILABLE', (
            'scenario_beta_estimation_span', 'scenario_beta_sample_counts',
            'owner_calendar_and_knowledge_cutoff'))

    source = snapshot['source']
    receipts = {row['path']: row for row in source.get('reads', ())}
    if _WTI_EXPORT not in receipts:
        raise _unqualified('native_wti_observation', 'futures_calendar_id_and_version',
                           'future_owner_sessions', 'native_series_generation_at_cutoff', 'source_use_receipt')
    try:
        cutoff = _stamp(source['built'])
        image, generation, binding, last_label = _wti_history(root, receipts[_WTI_EXPORT], cutoff)
        txi_generation = _wti_txi_generation(root, receipts[_TXI_STATE], source, binding, cutoff)
        sessions = verified_sessions
        if sessions is None:
            raise _unqualified('vendor_session_label_mapping', 'futures_calendar_id_and_version',
                               'future_owner_sessions', 'source_use_receipt')
        if (sessions.observation_sha256 != receipts[_WTI_EXPORT]['sha256'] or sessions.txi_generation != txi_generation
                or sessions.manifest_hash != source['source_manifest_hash'] or _stamp(sessions.knowledge_cutoff) != cutoff
                or not (_stamp(sessions.last_session_completed_at) <= _stamp(sessions.known_by) <= cutoff)
                or assumption['baseline_effective_at'] != source['asof']
                or _stamp(assumption['baseline_knowledge_cutoff']) != cutoff):
            raise _unqualified('verified_sessions_at_selected_cutoff')
        labels = [row[0] for row in image['rows']]
        pairs = sessions.historical_labels
        if (labels != [label for label, _ in pairs] or labels[-1] != last_label
                or pairs[-1][1] != source['asof']):
            raise _unqualified('vendor_session_label_mapping')
        dates = [date.fromisoformat(session) for _, session in pairs]
        if dates != sorted(set(dates)):
            raise _unqualified('vendor_session_label_mapping')
        close = image['columns'].index('close') + 1
        series = pd.Series([row[close] for row in image['rows']], index=pd.DatetimeIndex(dates), dtype=float)
        return SeriesBaseline(series, sessions.future_sessions, sessions.calendar_id, sessions.calendar_version,
                              generation, sessions.manifest_hash, source['asof'], source['built'], sessions.rights_ref)
    except NativeScenarioInputsUnavailable:
        raise
    except (OSError, AttributeError, KeyError, IndexError, TypeError, ValueError, OverflowError) as exc:
        raise _unqualified('native_wti_publication_binding') from exc


def _read_bound(root: Path, receipt: dict) -> bytes:
    with (root / receipt['path']).open('rb') as stream:
        raw = stream.read(2_000_001)
    if len(raw) != receipt['bytes'] or len(raw) > 2_000_000 or hashlib.sha256(raw).hexdigest() != receipt['sha256']:
        raise SourceIncoherent('scenario_source_changed')
    return raw


def evaluate_current_scenario(root: Path, assumption: dict, expected_manifest: str,
                              *, now: datetime | None = None,
                              verified_wti_sessions: VerifiedWTISessions | None = None) -> dict:
    """Authorize before calling; no user/body/assumption logging or persistence."""
    now = now or datetime.now(UTC)
    snapshot = compose_snapshot(root, chain=DEFAULT_CHAIN, now=now)
    source = snapshot['source']
    if source['source_manifest_hash'] != expected_manifest:
        raise ScenarioSnapshotChanged('SOURCE_CHANGED')
    definition_path = f'knowledge/transmission/{DEFAULT_CHAIN}.yaml'
    receipts = source['reads']
    definition_receipt = next(r for r in receipts if r['path'] == definition_path)
    chain = yaml.safe_load(_read_bound(root, definition_receipt))
    # The assumption binds the selected baseline, never today's inputs in place
    # of a historical reading. This check runs even on a typed unavailable path.
    try:
        same_cutoff = _stamp(assumption['baseline_knowledge_cutoff']) == _stamp(source['built'])
    except (ValueError, TypeError):
        raise SourceIncoherent('scenario_owner_clock_unavailable') from None
    if assumption['baseline_effective_at'] != source['asof'] or not same_cutoff:
        raise ScenarioSnapshotChanged('BASELINE_CHANGED')
    refusal = None
    baseline = None
    calibration = None
    calibration_receipt = None
    if assumption['node_ref'] == 'transmission:real10y_chg63':
        calibration_receipt = next((r for r in receipts if r['path'] == 'data/transmission/calibration.json'), None)
        if calibration_receipt:
            def unique(pairs):
                result = {}
                for key, value in pairs:
                    if key in result: raise ValueError('duplicate native field')
                    result[key] = value
                return result
            try:
                calibration = json.loads(_read_bound(root, calibration_receipt), object_pairs_hook=unique)
            except (ValueError, UnicodeError, RecursionError):
                pass  # Native malformed/old metadata stays a typed unavailable.
    else:
        try:
            baseline = _load_native_baseline(root, snapshot, assumption, verified_sessions=verified_wti_sessions)
        except NativeScenarioInputsUnavailable as exc:
            refusal = dict(reason=exc.reason, missing_owner_inputs=list(exc.missing), adapter_method=METHOD)
    result = evaluate_scenario(assumption, snapshot=snapshot, chain=chain, baseline=baseline,
                               evaluated_at=now.isoformat(), owner_refusal=refusal,
                               rates_calibration=calibration, calibration_receipt=calibration_receipt)
    # Recheck the complete immutable X1 source set AFTER owner composition too.
    if baseline is not None and verified_wti_sessions is not None:
        export_receipt = next(r for r in receipts if r['path'] == _WTI_EXPORT)
        export = json.loads(_read_bound(root, export_receipt))
        if hashlib.sha256(store._wti_parquet_bytes(root / _WTI_FILE)).hexdigest() != export['canonical_parquet']['sha256']:
            raise SourceIncoherent('scenario_source_changed')
    for receipt in receipts: _read_bound(root, receipt)
    return result
