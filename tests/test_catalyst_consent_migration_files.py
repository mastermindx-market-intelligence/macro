"""File-level fences for the 0009 consent migration (no database needed).

The real behavioural proof is scripts/test_catalyst_consent_rpc_review.py against a
fresh local PostgreSQL; these checks keep the three deploy files consistent with each
other in CI, where no PostgreSQL binaries are assumed.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "scripts" / "deploy"
APPLY = (DEPLOY / "0009_catalyst_consent_rpc_v2.sql").read_text()
ROLLBACK = (DEPLOY / "0009_catalyst_consent_rpc_v2_rollback.sql").read_text()
APPLIER = (DEPLOY / "catalyst_consent_migrate.py").read_text()
STUB = (ROOT / "research/marketing_dockets/MKT_CATALYST_CONSENT_RPC_V2_REVIEW_ONLY.sql").read_text()

_CREATE = re.compile(r"create or replace function public\.(catalyst_consent_\w+)\(([^)]*)\)", re.I)
_DROP = re.compile(r"drop function if exists public\.(catalyst_consent_\w+)\(([^)]*)\)", re.I)
_TRIGGER = re.compile(r"create trigger (catalyst_consent_\w+)", re.I)
_DROP_TRIGGER = re.compile(r"drop trigger if exists (catalyst_consent_\w+)", re.I)


def _norm(sig: str) -> str:
    """Signature as types only: 'p_user_id uuid, p_tickers text[]' -> 'uuid,text[]'."""
    return ",".join(part.split()[-1] for part in sig.split(",") if part.strip())


def test_rollback_drops_every_function_the_migration_creates():
    created = {(n, _norm(a)) for n, a in _CREATE.findall(APPLY)}
    dropped = {(n, _norm(a)) for n, a in _DROP.findall(ROLLBACK)}
    assert created, "migration creates no function?"
    assert created == dropped, {"missing_from_rollback": created - dropped,
                                "extra_in_rollback": dropped - created}


def test_rollback_drops_every_trigger_first_and_keeps_the_tables():
    created = set(_TRIGGER.findall(APPLY))
    dropped = set(_DROP_TRIGGER.findall(ROLLBACK))
    assert created == dropped and len(created) == 3
    # Triggers before functions, functions before RPCs, tables never dropped.
    first_drop_fn = ROLLBACK.lower().index("drop function")
    assert all(ROLLBACK.index(f"drop trigger if exists {t}") < first_drop_fn for t in dropped)
    assert "drop table" not in ROLLBACK.lower()
    assert "retained" in ROLLBACK.lower()


def test_migration_is_one_transaction_with_lock_and_statement_timeouts():
    body = APPLY.lower()
    assert body.count("\nbegin;") == 1 and body.rstrip().endswith("commit;")
    assert "set local lock_timeout" in body and "set local statement_timeout" in body
    # Both timeouts sit inside the transaction, right after BEGIN.
    assert body.index("set local lock_timeout") > body.index("\nbegin;")
    assert body.index("set local lock_timeout") < body.index("create table")


def test_every_client_role_is_revoked_from_both_tables_and_the_sequence():
    body = APPLY.lower()
    for obj in ("public.catalyst_consent_pending", "public.catalyst_consent_grants",
                "sequence public.catalyst_consent_grants_grant_id_seq"):
        line = next(l for l in body.splitlines() if l.startswith(f"revoke all on {obj}"))
        tail = line + (body.splitlines()[body.splitlines().index(line) + 1] if line.rstrip().endswith("seq") else "")
        for role in ("public", "anon", "authenticated", "service_role"):
            assert role in tail, (obj, role)
    assert "has_table_privilege('service_role'" in body
    assert "has_sequence_privilege('service_role'" in body


def test_only_service_role_may_execute_and_contract_is_not_security_definer():
    body = APPLY
    rpcs = [n for n, _ in _CREATE.findall(APPLY)
            if n not in ("catalyst_consent_grant_guard", "catalyst_consent_on_global_address_suppression",
                         "catalyst_consent_on_global_user_optout")]
    assert len(rpcs) == 7
    for name in rpcs:
        assert re.search(rf"grant execute on function public\.{name}\([^)]*\) to service_role", body), name
        assert re.search(rf"revoke all on function public\.{name}\([^)]*\) from public, anon, authenticated", body), name
    contract = body[body.index("function public.catalyst_consent_contract()"):body.index("catalyst_consent_begin(")]
    assert "security definer" not in contract.lower()


def test_null_safety_markers_and_named_refusals_present():
    body = APPLY
    for marker in ("p_intent is null or p_email_tag is null or p_expires_at_utc is null",
                   "p_public_ref is null or p_email_tag is null",
                   "p_user_id is null or p_event_id is null or p_tickers is null",
                   "p_limit is null or p_limit not between 1 and 100",
                   "p_user_id is null or p_event_id is null or p_revoked_at_utc is null",
                   "when unique_violation then", "PENDING_INTENT_REPLAY",
                   "interval '1 hour'", "CATALYST_CONSENT_GRANT_IMMUTABLE",
                   "array_agg(t order by t)", "CATALYST_CONSENT_RPC_OWNER_BLOCK",
                   "CATALYST_CONSENT_RLS_MODE_BLOCK"):
        assert marker in body, marker
    # The address trigger returns NEW on a blank address instead of raising.
    trig = body[body.index("catalyst_consent_on_global_address_suppression()"):body.index("catalyst_consent_on_global_user_optout()")]
    assert "CATALYST_SUPPRESSION_ADDRESS_INVALID" not in trig
    assert "return new;" in trig.split("pg_advisory_xact_lock")[0]


def test_applier_points_at_the_deploy_files_and_prints_no_values():
    assert '"0009_catalyst_consent_rpc_v2.sql"' in APPLIER
    assert '"0009_catalyst_consent_rpc_v2_rollback.sql"' in APPLIER
    assert "SUPABASE_ACCESS_TOKEN" in APPLIER and "print(pat" not in APPLIER
    assert "api.supabase.com/v1/projects/" in APPLIER
    for name in ("catalyst_consent_contract", "catalyst_consent_revoke", "catalyst_consent_grant_guard",
                 "catalyst_consent_grant_immutable", "catalyst_consent_pending"):
        assert name in APPLIER, name


def test_review_only_file_is_a_stub_with_no_sql():
    assert "SUPERSEDED" in STUB
    assert not any(l.strip() and not l.lstrip().startswith("--") for l in STUB.splitlines())


def test_round2_review_fixes_are_present():
    # F1: every apply reconciles grants against the incumbent opt-out/suppression state
    # BEFORE the install fence, so a rollback window cannot resurrect a withdrawn grant.
    fence_at = APPLY.index("do $consent_install_fence$")
    recon = re.search(r"update public\.catalyst_consent_grants g\s+set revoked_at_utc = pg_catalog\.now\(\)"
                      r".*?marketing_opt_out.*?email_suppression", APPLY, re.S)
    assert recon and recon.start() < fence_at
    # F3: a second user on the same intent is a named refusal.
    assert "exception when unique_violation then" in APPLY[APPLY.index("catalyst_consent_confirm("):]
    assert "CONSENT_INTENT_ALREADY_USED" in APPLY
    # F2/F6: the fence covers the pending table owner and the incumbent tables' readability.
    fence = APPLY[fence_at:]
    for name in ("CATALYST_CONSENT_TABLE_OWNER_BLOCK: pending", "CATALYST_CONSENT_INCUMBENT_TABLE_ACCESS_BLOCK",
                 "CATALYST_CONSENT_INCUMBENT_TABLE_MISSING_BLOCK", "CATALYST_CONSENT_AUTH_USERS_READ_BLOCK"):
        assert name in fence
    # F8: the applier's census checks authenticated too, counts enabled triggers on the
    # right tables, and never exits a failed apply without a census.
    for key in ("authenticated_execute_begin", "authenticated_table_select", "triggers_enabled"):
        assert key in APPLIER
    assert 'call("rollback;")' in APPLIER
    # Round 3 (post-PASS nits): transport failures still take the census, replica-only
    # triggers do not count as enabled, a BYPASSRLS owner still needs SELECT.
    assert "urllib.error.URLError" in APPLIER and "_effect=UNKNOWN" in APPLIER
    assert "t.tgenabled in ('O','A')" in APPLIER
    assert "has_table_privilege(v_owner_name, 'public.'||v_rec.relname, 'SELECT')" in fence
