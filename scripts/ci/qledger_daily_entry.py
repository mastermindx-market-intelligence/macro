"""Qualified same-process daily producer entry; no evidence or identity issuer.

An assigning owner entry may import build_producer alongside its actual
build_evidence/reader. The programmatic LoadedBootstrap.producer accepts the
existing typed original inputs after qualification; JSON and the CLI cannot
transfer a live binding. Missing inputs are a refusal, never auto-construction.
"""
from pathlib import Path
import os
import sys
import time
from types import SimpleNamespace

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from engine.qledger_original_result import OriginalResultClaimsBinding
from engine.qledger_store_native import NativeClaimsIntent
from scripts.ci.qledger_host_gate import GateRefusal


def _require(value, message):
    if not value:
        raise GateRefusal(message)


def build_producer(context, *, owner_binding=None, regions=None, native_intents=None, call=None, publication=None):
    """Select the real native factory/finalizer from explicit original facts."""
    loader = globals().get('__loader__')
    _require(getattr(loader, '_qledger_bootstrap_active', False), 'daily entry requires qualified outside-checkout code')
    loader.check()
    _require(type(owner_binding) is OriginalResultClaimsBinding
             and owner_binding.original_process_id == os.getpid()
             and owner_binding.repo_root == context.repo,
             'missing or transferred exact original producer binding')
    _require(type(regions) in (tuple, list) and regions and len(regions) <= 4
             and len(set(regions)) == len(regions) and type(native_intents) is dict
             and set(native_intents) == set(regions)
             and all(type(x) is NativeClaimsIntent for x in native_intents.values()),
             'explicit finite original regions/intents required')
    from scripts.ci.qledger_owner_invocation import load_conversion
    conversion = load_conversion(context.repo, result_path=context.result_path, manifest_digest=context.manifest_digest)
    accepted_data=context.candidate_oid
    if any(owner_binding._target_for(intent).accepted_tip_oid!=accepted_data for intent in native_intents.values()):
        from scripts.ci.qledger_owner_invocation import require_live_producer
        live=require_live_producer(owner_binding)
        accepted_data=live.gate.native_data_tip(owner_binding,
            original_deadline_monotonic_ns=context.original_deadline_monotonic_ns)
    for intent in native_intents.values():
        owner_binding._check_intent(intent)
        target = owner_binding._target_for(intent)
        _require((intent.operation_id, intent.lane_id, intent.transaction_id) !=
                 (conversion.owner.intent.operation_id, conversion.owner.intent.lane_id, conversion.owner.intent.transaction_id)
                 and not target.result_path.is_relative_to(context.result_path)
                 and not context.result_path.is_relative_to(target.result_path),
                 'original producer cannot borrow conversion identity/result')
        _require(target.accepted_tip_oid == accepted_data, 'original producer accepted data differs from verified generation')

    from lib import config
    _require(config.ROOT == context.repo
             and (not config.load.cache_info().currsize or
                  (config._LOAD_ROOT == context.repo and config._LOAD_DIGEST == loader.config_digest())),
             'actual original ROOT or cached configuration differs')
    _require(config.data_dir() == context.repo/'data' and config.site_dir() == context.repo/'site',
             'original producer configuration redirects mutation roots')
    def deadline():
        _require(type(context.original_deadline_monotonic_ns) is int
                 and time.monotonic_ns() < context.original_deadline_monotonic_ns, 'original producer endpoint absent or expired')
        loader.check()
    # This is metadata inspection under the caller's existing gate lease,
    # not a fabricated live finalizer/admission or another native operation.
    from scripts.ci.qledger_engine_publication import (
        _qualify_daily_destinations, build_native_engine_producer, finalize_daily_engine_outputs)
    if publication is not None:
        from scripts.ci.qledger_engine_publisher import NativePublicationFinalizer
        _require(type(publication) is NativePublicationFinalizer and publication.pid == os.getpid(),
                 'exact same-process original publication finalizer required')
    inspection = SimpleNamespace(invocation=SimpleNamespace(binding=owner_binding), _deadline=deadline)
    deadline()
    owner_binding.read_snapshot()
    _qualify_daily_destinations(inspection, accepted_tip_oid=accepted_data)
    deadline()
    return build_native_engine_producer(context, owner_binding=owner_binding, regions=regions,
        native_intents=native_intents, finalizer=finalize_daily_engine_outputs if publication is None else publication, call=call)
