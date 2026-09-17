"""REVIEW ONLY: map the R12 bridge to existing Brain tier/accounting contracts.

Not a registered Brain tool, permission registry, source-use grant or new ledger.
The source-scope and identity resolver remain injected OWNERS. Tests supply
synthetic entitlements and source grants; the exact existing quota and tier
normalizer modules perform real temporary-file operations.

Production must have ONE final debit owner. This reference exercises R12's
existing final-read callback mapped to Brain accounting. It never calls the full
metering report reader after that callback. Adopting the full reader instead
requires moving these checks inside its existing single-debit path.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any


def _failure(status: str) -> dict[str, Any]:
    return {'status': status, 'items': [], 'passages': []}


def _nonnegative_int(value: Any) -> int | None:
    return value if type(value) is int and value >= 0 else None


class OwnerAdapter:
    """Request-local orchestration; no persistent identity or permission state.

    ``resolve_tier`` is the existing gateway resolver, not request-body claims.
    ``source_scope`` is an independently admitted source-use owner; Pro is not a
    license. Both are looked up again during the selected read. The schema and
    concrete source-use owner are still adoption gates, not invented services.

    ``peek_view`` and ``charge_view`` map to Brain's existing wrappers. Their
    documented fail-open returns remain returns; a callback exception does not
    become a new permission or an instruction to retry a possible debit.
    """
    def __init__(self, **owners: Any) -> None:
        self.owners = owners

    def _product_gate(self, user_id: str, *, source_text: bool) -> str | None:
        if not isinstance(user_id, str) or not user_id.strip():
            return 'essential_required'
        try:
            entitlement = self.owners['resolve_tier'](user_id)
            if not isinstance(entitlement, dict):
                return 'entitlement_unavailable'
            tier = self.owners['normalize_tier'](entitlement.get('tier')) or 'free'
            # Preserve current gateway semantics; this is not an independent
            # authorization design or a new interpretation of absent status.
            status = entitlement.get('status') or 'active'
        except Exception:
            return 'entitlement_unavailable'
        if not (tier in ('essential', 'pro', 'unlimited')
                and status in ('active', 'trialing')):
            return 'essential_required'
        if source_text and tier not in ('pro', 'unlimited'):
            return 'pro_required'
        return None

    def dispatch(
        self, *, user_id: str, scope: str = 'metadata', action: str = 'discover',
        query: str = '', limit: int = 3, selection: dict | None = None,
        now: datetime,
    ) -> dict:
        if scope not in ('metadata', 'source_text'):
            return _failure('scope_not_selected')
        if action not in ('discover', 'read') or (scope == 'metadata' and action != 'discover'):
            return _failure('invalid_request')
        if not isinstance(now, datetime):
            return _failure('invalid_request')
        gate = self._product_gate(user_id, source_text=(scope == 'source_text'))
        if gate:
            return _failure(gate)
        if scope == 'metadata':
            # Existing summary consumer and policy stay intact, including when
            # the distinct full-report view allowance has been exhausted.
            return self.owners['metadata_search'](query=query, limit=limit, now=now)

        # Uniform before body-conditioned discovery and selected reads. Do NOT
        # put this into the repeated source/access callback: a successful final
        # debit may consume the last slot, yet that read must still be served.
        try:
            preflight = self.owners['peek_view'](user_id, now)
        except Exception:
            return _failure('accounting_unavailable')
        if isinstance(preflight, dict) and preflight.get('remaining') == 0:
            result = _failure('view_limit_reached')
            result['quota'] = {'remaining': 0, 'limit': _nonnegative_int(preflight.get('limit'))}
            return result

        def source_owner(purpose: str) -> dict:
            current_gate = self._product_gate(user_id, source_text=True)
            if current_gate == 'entitlement_unavailable':
                return {'decision': 'unavailable'}
            if current_gate:
                return {'decision': 'denied'}
            return self.owners['source_scope'](user_id, purpose)

        shared = {'corpus': self.owners['corpus'], 'scope_provider': source_owner,
                  'connection_factory': self.owners['connection_factory']}
        if action == 'discover':
            return self.owners['bridge'].discover(
                query=query, scope='source_text', limit=limit, **shared)

        accounting: dict = {'attempted': False, 'allow_returned': None,
                            'persistence': 'not_attested'}
        quota: dict | None = None

        def debit_once(_report_id: str) -> bool:
            nonlocal quota
            # R12 calls once after verified, usable support. No retry or refund
            # owner is introduced here, and no second body reader is invoked.
            accounting['attempted'] = True
            value = self.owners['charge_view'](user_id, now)
            if (not isinstance(value, tuple) or len(value) != 2
                    or type(value[0]) is not bool or not isinstance(value[1], dict)):
                raise ValueError('Accounting owner returned an invalid contract')
            allowed, info = value
            accounting['allow_returned'] = allowed
            quota = {'remaining': _nonnegative_int(info.get('remaining')),
                     'limit': _nonnegative_int(info.get('limit'))}
            # In particular, never bool((False, info)); that tuple is truthy.
            return allowed

        result = self.owners['bridge'].read_selected(
            selection=selection, source_reader=self.owners['source_reader'],
            meter=debit_once, **shared)
        if accounting['attempted']:
            # The legacy owner intentionally allows on some write failures and
            # does not return a durable receipt. Do not assert persistence.
            result['accounting'] = accounting
            result['quota'] = quota
        return result
