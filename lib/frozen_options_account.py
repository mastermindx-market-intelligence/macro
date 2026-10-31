"""Read-only same-host account observations for the incumbent Terminal alert worker.

No authentication endpoint or new policy. The caller is the existing privileged
local service; GoTrue admin is the identity authority. Canonical /api/me callable
owns effective billing and private unlimited overlay. No browser is impersonated.
"""
from __future__ import annotations

import contextlib
import io
from uuid import UUID


def frozen_options_account(principal, evaluation_at):
    try:
        if not isinstance(principal, str) or str(UUID(principal)) != principal:
            return None
        if not isinstance(evaluation_at, str) or not evaluation_at or len(evaluation_at) > 64:
            return None
        # Import/call the actual owners only after an explicit local invocation.
        # Captured incidental owner stdout must never contaminate the protocol.
        with contextlib.redirect_stdout(io.StringIO()):
            from engine.alert_delivery_drain import fetch_user_record, READ_OK
            state, user = fetch_user_record(principal)
            if state != READ_OK or not isinstance(user, dict) or user.get('id') != principal:
                return None  # Never invoke canonical account for a mismatched record.
            from app.main import me
            account = me(user=user)  # Actual callable has no Request/token dependency.
        if not isinstance(account, dict) or account.get('id') != principal:
            return None
        meta = user.get('user_metadata')
        if not isinstance(meta, dict):
            return None
        from lib.user_prefs import read_user_prefs
        prefs = read_user_prefs(user)
        # Preserve invalid present values as observations, so the native policy
        # refuses them instead of silently reinterpreting missing consent.
        consent = {key: prefs[key] if key in prefs else meta[key]
                   for key in ('alert_email_optin', 'alert_categories') if key in meta}
        # Only account/consent facts needed by the ONE native policy cross this
        # private pipe. No token, email, name, quota, unrelated metadata or secret.
        return {'kind': 'observed', 'principal': principal, 'evaluationAt': evaluation_at,
                'account': {'user': {'id': principal, 'user_metadata': consent},
                    'me': {key: account[key] for key in (
                        'id', 'tier', 'features', 'status', 'current_period_end', 'source') if key in account}}}
    except Exception:
        return None
