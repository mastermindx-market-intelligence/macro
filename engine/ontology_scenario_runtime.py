"""Read-only request composition for F04-X2; no calendar, rights or beta invention.

Uses the existing X1 composer, its exact read manifest and native TXI definition.
The current native WTI adapter is a historical parquet reader, NOT a futures
calendar/vintage owner. The existing cash-session dispatcher explicitly excludes
CL=F. Consequently ordinary runtime returns a named unsupported-owner result
until native futures/calendar/vintage inputs are actually supplied. Rates use
their existing native calibration plus additive sample/clock metadata instead;
no future price calendar or request-time fitting is needed for that illustration.
"""
from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path

import yaml

from engine.ontology_explorer import DEFAULT_CHAIN, SourceIncoherent, compose_snapshot
from engine.ontology_scenario import SeriesBaseline, evaluate_scenario
from engine import transmission_chains as txi
from lib.market_session import cash_market_for_symbol

METHOD = 'ontology_scenario.runtime.v2'


class ScenarioSnapshotChanged(ValueError):
    """The explicitly selected reading no longer matches the native owner bytes."""


class NativeScenarioInputsUnavailable(ValueError):
    def __init__(self, reason: str, missing: tuple[str, ...]):
        self.reason, self.missing = reason, missing
        super().__init__(reason)


def _load_native_baseline(root: Path, snapshot: dict, assumption: dict) -> SeriesBaseline:
    """Actual native capability check, never a synthetic/calendar fallback.

    _SeriesAdapter reads data/yahoo/CL_F.parquet. Its bar index is historical;
    neither it nor chain_state binds future futures sessions or historical byte
    availability at a knowledge cutoff. NYSE cash sessions are not a substitute.
    No new registry, guessed calendar or claim that site_full grants data rights.
    """
    if assumption['node_ref'] == 'transmission:real10y_chg63':
        raise NativeScenarioInputsUnavailable('NUMERIC_OWNER_METADATA_UNAVAILABLE', (
            'scenario_beta_estimation_span', 'scenario_beta_sample_counts',
            'owner_calendar_and_knowledge_cutoff'))
    path = txi._SeriesAdapter(root / 'data', 'yahoo')._path('CL=F')
    missing = ['futures_calendar_id_and_version', 'future_owner_sessions',
               'native_series_generation_at_cutoff', 'source_use_receipt']
    if not path.is_file(): missing.append('native_wti_series_bytes')
    # The dispatcher currently returns None. Even a future cash-map change is
    # not authority to use an equity calendar for a futures contract.
    reason = ('WTI_FUTURES_CALENDAR_UNAVAILABLE' if cash_market_for_symbol('CL=F') is None
              else 'FUTURES_CALENDAR_OWNER_UNQUALIFIED')
    raise NativeScenarioInputsUnavailable(reason, tuple(missing))


def _read_bound(root: Path, receipt: dict) -> bytes:
    raw = (root / receipt['path']).read_bytes()
    if len(raw) > 2_000_000 or hashlib.sha256(raw).hexdigest() != receipt['sha256']:
        raise SourceIncoherent('scenario_source_changed')
    return raw


def evaluate_current_scenario(root: Path, assumption: dict, expected_manifest: str,
                              *, now: datetime | None = None) -> dict:
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
    from engine.ontology_scenario import _stamp
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
            baseline = _load_native_baseline(root, snapshot, assumption)
        except NativeScenarioInputsUnavailable as exc:
            refusal = dict(reason=exc.reason, missing_owner_inputs=list(exc.missing), adapter_method=METHOD)
    result = evaluate_scenario(assumption, snapshot=snapshot, chain=chain, baseline=baseline,
                               evaluated_at=now.isoformat(), owner_refusal=refusal,
                               rates_calibration=calibration, calibration_receipt=calibration_receipt)
    # Recheck the complete immutable X1 source set AFTER owner composition too.
    for receipt in receipts: _read_bound(root, receipt)
    return result
