"""Additive native Provider Control producer, acquired from fixed Control custody.

No caller facts, clock, path, status or callback enter the public API. This module
is loaded from its sealed Macro source by the Control composition owner. Direct
CLI/import invocation without that live owner refuses. V1 is untouched.
"""
from __future__ import annotations

import copy
import hashlib
import json
import time

SCHEMA = 'mastermind.provider_capacity.v2'


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _normalize(acquired, generated_at_ms):
    """Private normalization seam; dictionaries are observations, never authority."""
    registration, observation = acquired['registration'], acquired['observation']
    if (registration['registration_state'] != 'registered'
            or registration['provider'] != 'minimax'
            or registration['capacity_capability_id'] != observation['capacity_capability_id']
            or registration['capability_generation'] != observation['capability_generation']
            or registration['source_receipt_digest'] != observation['source_receipt_digest']):
        raise ValueError('NATIVE_CAPACITY_SOURCE_JOIN_REFUSED')
    # Enrollment/registration/ModelRouter are NOT provider enablement/auth/health.
    # This first actual reader knows no provider-domain enablement observation.
    # Its unknowns survive normalization and refuse conservative admission.
    row = {
        'host_ref': observation['host_ref'], 'boot_ref': observation['boot_ref'],
        'capacity_capability_id': registration['capacity_capability_id'],
        'capability_generation': registration['capability_generation'],
        'realm_generation': observation['realm_generation'],
        'enrollment_receipt_digest': observation['enrollment_receipt_digest'],
        'provider': registration['provider'], 'provider_enabled': None,
        'worker_source_config_digest': acquired['worker_source_config_digest'],
        'observed_at': observation['observed_at'],
        **{key: copy.deepcopy(observation[key]) for key in (
            'realm_auth', 'provider_health', 'cooling', 'quota_horizons', 'last_provider_outcome')},
    }
    value = {'schema': SCHEMA, 'generated_at_ms': generated_at_ms,
        'source': {key: registration[key] for key in (
            'source_release_commit', 'previous_release_commit', 'material_source_digest',
            'source_receipt_digest', 'registration_receipt_digest')},
        'producer_sha256': acquired['producer_sha256'], 'slots': [row]}
    value['snapshot_hash'] = _digest(value)
    return value


async def build_snapshot():
    """One authenticated current-owner read; no probe, cache, retry or dispatch."""
    from control_plane.native_capacity_acquisition import _acquire_for_macro
    acquired = await _acquire_for_macro()
    return _normalize(acquired, time.time_ns() // 1_000_000)
