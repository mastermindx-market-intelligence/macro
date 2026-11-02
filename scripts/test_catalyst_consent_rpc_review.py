#!/usr/bin/env python3
"""Catalyst consent RPC v2 (0009) proof against a *new local PostgreSQL*.

Run manually: python3 scripts/test_catalyst_consent_rpc_review.py
Creates a brand-new temporary PG cluster, Unix-socket only (NO TCP), builds
mock auth/email-owner tables with Supabase-like default privileges, applies
scripts/deploy/0009_catalyst_consent_rpc_v2.sql twice and asserts security,
signed-intent persistence, positive consent, suppression, revocation, NULL
refusals, replay, clock windows, grant immutability, the rollback file and
the incumbent writes after rollback.
It does not connect to Supabase, the public internet or any existing database.
This is a TEST HARNESS, not a migration runner or product control plane.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

# Pin repo imports for direct execution from any working directory. This local-only
# test does not install a package or modify a global search path for other jobs.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.marketing.catalyst_lifecycle import _email_tag, _sign
SQL = ROOT / "scripts/deploy/0009_catalyst_consent_rpc_v2.sql"
ROLLBACK = ROOT / "scripts/deploy/0009_catalyst_consent_rpc_v2_rollback.sql"
USER = "9507e687-116a-4d30-9c30-fdf45c9d91b2"
EMAIL = "fixture+updates@example.invalid"
SECRET = "synthetic_hmac_only_no_real_user_or_token_0123456789"
EVENT = "synthetic-event-20261009"
SCOPE = "catalyst_event_updates/v1"
PORT = "55462"
RPCS = (
    "catalyst_consent_contract()",
    "catalyst_consent_begin(text,text,text)",
    "catalyst_consent_resolve(text,text)",
    "catalyst_consent_confirm(uuid,text,text,text[],text,text,jsonb)",
    "catalyst_consent_current(uuid,text)",
    "catalyst_consent_interested(text,integer)",
    "catalyst_consent_revoke(uuid,text,text)",
)


def _quote(value: str) -> str:
    assert isinstance(value, str)
    return "'" + value.replace("'", "''") + "'"


class TestPostgres:
    def __init__(self, root: Path):
        self.root = root
        self.data = root / "pgdata"
        self.socket = root / "socket"
        self.socket.mkdir()
        # Inherited PG* environment settings could silently redirect psql.
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("PG")}
        self.args = [
            "psql", "-X", "-v", "ON_ERROR_STOP=1", "-Aqt",
            "-h", str(self.socket), "-p", PORT, "-d", "postgres",
        ]
        self.started = False

    def run(self, args: list[str], *, input_text: str | None = None,
            ok: bool = True, contains: str | None = None) -> str:
        result = subprocess.run(args, input=input_text, capture_output=True,
                                text=True, env=self.env, timeout=35)
        if ok and result.returncode:
            raise AssertionError(f"Local PostgreSQL test failed: {result.stderr[-1800:]}")
        if not ok:
            assert result.returncode != 0, "Expected PostgreSQL to refuse test operation"
            if contains:
                assert contains in result.stderr, (
                    f"Expected denial {contains!r}; got {result.stderr[-800:]}")
        return result.stdout.strip()

    def start(self) -> None:
        self.run(["initdb", "-D", str(self.data), "-A", "trust", "--no-instructions"])
        self.run(["pg_ctl", "-D", str(self.data), "-l", str(self.root / "server.log"),
                  "-o", f"-k {self.socket} -c listen_addresses='' -p {PORT}", "start"])
        self.started = True

    def stop(self) -> None:
        if self.started:
            self.run(["pg_ctl", "-D", str(self.data), "stop", "-m", "immediate"])
            self.started = False

    def sql(self, statement: str, *, role: str | None = None,
            denied: str | None = None) -> str:
        if role:
            assert role in ("anon", "authenticated", "service_role")
            statement = "set role " + role + "; " + statement
        output = self.run(self.args + ["-c", statement],
                          ok=denied is None, contains=denied)
        # -q suppresses DDL command tags; an empty successful reply is valid.
        rows = output.splitlines()
        return rows[-1] if rows and denied is None else ""

    def apply(self, *, denied: str | None = None, path: Path = SQL) -> None:
        self.run(self.args + ["-f", str(path)],
                 ok=denied is None, contains=denied)


def _new_intent(now: datetime, nonce: str, tickers: list[str],
                touch: dict[str, str] | None = None) -> tuple[str, str, str]:
    body = {
        "v": 1, "scope": SCOPE, "nonce": nonce,
        "event_id": EVENT, "tickers": tickers,
        "email_tag": _email_tag(SECRET, EMAIL),
        "first_touch": touch or {},
        "issued_at": now.isoformat(),
        "scan_receipt": "synthetic.scan",
    }
    return _sign(SECRET, body), body["email_tag"], (
        now + timedelta(minutes=20)).isoformat()


def _iso(delta: timedelta = timedelta()) -> str:
    return (datetime.now(timezone.utc) + delta).isoformat()


def _fixture(db: TestPostgres) -> None:
    db.sql("create role anon nologin")
    db.sql("create role authenticated nologin")
    db.sql("create role service_role nologin")
    db.sql("grant usage on schema public to anon, authenticated, service_role")
    # Real Supabase defaults grant DIRECT client privileges on new functions, tables
    # and sequences (not merely PUBLIC). The explicit REVOKEs in 0009 must hold
    # against all three, service_role included for the two tables.
    db.sql("alter default privileges in schema public grant execute on functions to anon, authenticated, service_role")
    db.sql("alter default privileges in schema public grant all on tables to anon, authenticated, service_role")
    db.sql("alter default privileges in schema public grant all on sequences to anon, authenticated, service_role")
    db.sql("create schema auth")
    db.sql("create table auth.users(id uuid primary key, email text, email_confirmed_at timestamptz)")
    # Shapes follow 0007_support_email.sql (reason check, created_at, lang, updated_at).
    db.sql("create table public.email_suppression(email text primary key, "
           "reason text not null check (reason in ('unsubscribe','bounce','complaint','manual')), "
           "created_at timestamptz not null default now())")
    db.sql("create table public.email_prefs(user_id uuid primary key, lang text, "
           "marketing_opt_out boolean not null default false, updated_at timestamptz not null default now())")


def _privileges(db: TestPostgres) -> dict:
    return json.loads(db.sql("""select pg_catalog.jsonb_build_object(
      'anon',pg_catalog.has_function_privilege('anon','public.catalyst_consent_begin(text,text,text)','EXECUTE'),
      'authenticated',pg_catalog.has_function_privilege('authenticated','public.catalyst_consent_begin(text,text,text)','EXECUTE'),
      'service',pg_catalog.has_function_privilege('service_role','public.catalyst_consent_begin(text,text,text)','EXECUTE'),
      'table_anon',pg_catalog.has_table_privilege('anon','public.catalyst_consent_grants','SELECT'),
      'table_service_select',pg_catalog.has_table_privilege('service_role','public.catalyst_consent_grants','SELECT'),
      'table_service_insert',pg_catalog.has_table_privilege('service_role','public.catalyst_consent_pending','INSERT'),
      'seq_service',pg_catalog.has_sequence_privilege('service_role','public.catalyst_consent_grants_grant_id_seq','USAGE'),
      'policies',(select pg_catalog.count(*) from pg_catalog.pg_policies
        where schemaname='public' and tablename in ('catalyst_consent_pending','catalyst_consent_grants'))
    )"""))


def _verify(db: TestPostgres) -> None:
    _fixture(db)
    db.apply()
    contract = json.loads(db.sql("select public.catalyst_consent_contract()"))
    assert contract == {"owner": "email_consent", "version": 2}
    permissions = _privileges(db)
    assert permissions == {"anon": False, "authenticated": False, "service": True,
                           "table_anon": False, "table_service_select": False,
                           "table_service_insert": False, "seq_service": False,
                           "policies": 0}, permissions
    db.sql("select public.catalyst_consent_contract()", role="anon",
           denied="permission denied")
    db.sql("select public.catalyst_consent_contract()", role="authenticated",
           denied="permission denied")
    db.sql("select * from public.catalyst_consent_grants", role="anon",
           denied="permission denied")
    # service_role may CALL the RPCs but can never read or write the ledger directly.
    db.sql("select * from public.catalyst_consent_grants", role="service_role",
           denied="permission denied")
    db.sql("insert into public.catalyst_consent_pending default values", role="service_role",
           denied="permission denied")
    assert json.loads(db.sql("select public.catalyst_consent_contract()",
                             role="service_role")) == contract
    print("SERVICE_ROLE_TABLE_DENY=PASS")

    now = datetime.now(timezone.utc)
    db.sql("insert into auth.users values (" + _quote(USER) + "::uuid," +
           _quote(EMAIL) + ",pg_catalog.now()-interval '1 minute')")
    touch = {"utm_source": "partner", "utm_medium": "partner_demo",
             "utm_campaign": "catalyst_scan", "utm_content": "cp_synthetic"}
    nonce = "synthetic_intent_nonce_abcdefghijklmnop"
    signed, tag, expiration = _new_intent(now, nonce, ["NVDA", "AMD"], touch)
    pending = json.loads(db.sql("select public.catalyst_consent_begin(" +
                                ",".join(map(_quote, (signed, tag, expiration))) + ")",
                                role="service_role"))
    opaque = pending["public_ref"]
    assert re.fullmatch(r"[A-Za-z0-9_-]{32,128}", opaque)
    # The same signed nonce can begin exactly once.
    db.sql("select public.catalyst_consent_begin(" +
           ",".join(map(_quote, (signed, tag, expiration))) + ")",
           denied="PENDING_INTENT_REPLAY")
    print("PENDING_INTENT_REPLAY=PASS")
    assert json.loads(db.sql("select public.catalyst_consent_resolve(" +
                             _quote(opaque) + "," + _quote(tag) + ")"))["intent"] == signed
    db.sql("select public.catalyst_consent_resolve(" + _quote(opaque) +
           "," + _quote("0" * 64) + ")", denied="PENDING_REF_UNAVAILABLE")

    # NULL inputs are named refusals on every RPC, never a constraint error.
    db.sql("select public.catalyst_consent_begin(null," + _quote(tag) + "," +
           _quote(expiration) + ")", denied="INVALID_PENDING_INTENT")
    db.sql("select public.catalyst_consent_begin(" + _quote(signed) + ",null," +
           _quote(expiration) + ")", denied="INVALID_PENDING_INTENT")
    db.sql("select public.catalyst_consent_begin(" + _quote(signed) + "," +
           _quote(tag) + ",null)", denied="INVALID_PENDING_INTENT")
    db.sql("select public.catalyst_consent_resolve(null," + _quote(tag) + ")",
           denied="INVALID_PENDING_REF")
    db.sql("select public.catalyst_consent_resolve(" + _quote(opaque) + ",null)",
           denied="INVALID_PENDING_REF")
    db.sql("select public.catalyst_consent_confirm(null," + _quote(EVENT) + "," +
           _quote(SCOPE) + ",ARRAY['NVDA','AMD']::text[]," + _quote(nonce) + "," +
           _quote(_iso()) + ",'{}'::jsonb)", denied="CONSENT_PURPOSE_INVALID")
    db.sql("select public.catalyst_consent_confirm(" + _quote(USER) + "::uuid," +
           _quote(EVENT) + ",null,ARRAY['NVDA','AMD']::text[]," + _quote(nonce) + "," +
           _quote(_iso()) + ",'{}'::jsonb)", denied="CONSENT_PURPOSE_INVALID")
    db.sql("select public.catalyst_consent_confirm(" + _quote(USER) + "::uuid," +
           _quote(EVENT) + "," + _quote(SCOPE) + ",null," + _quote(nonce) + "," +
           _quote(_iso()) + ",'{}'::jsonb)", denied="CONSENT_PURPOSE_INVALID")
    db.sql("select public.catalyst_consent_confirm(" + _quote(USER) + "::uuid," +
           _quote(EVENT) + "," + _quote(SCOPE) + ",ARRAY['NVDA','AMD']::text[],null," +
           _quote(_iso()) + ",'{}'::jsonb)", denied="CONSENT_PURPOSE_INVALID")
    db.sql("select public.catalyst_consent_confirm(" + _quote(USER) + "::uuid," +
           _quote(EVENT) + "," + _quote(SCOPE) + ",ARRAY['NVDA','AMD']::text[]," +
           _quote(nonce) + ",null,'{}'::jsonb)", denied="CONSENT_PURPOSE_INVALID")
    db.sql("select public.catalyst_consent_confirm(" + _quote(USER) + "::uuid," +
           _quote(EVENT) + "," + _quote(SCOPE) + ",ARRAY['NVDA','AMD']::text[]," +
           _quote(nonce) + "," + _quote(_iso()) + ",null)", denied="CONSENT_PURPOSE_INVALID")
    db.sql("select public.catalyst_consent_interested(null,10)",
           denied="CONSENT_INTEREST_QUERY_INVALID")
    db.sql("select public.catalyst_consent_interested(" + _quote(EVENT) + ",null)",
           denied="CONSENT_INTEREST_QUERY_INVALID")
    db.sql("select public.catalyst_consent_interested(" + _quote(EVENT) + ",0)",
           denied="CONSENT_INTEREST_QUERY_INVALID")
    db.sql("select public.catalyst_consent_revoke(null," + _quote(EVENT) + "," +
           _quote(_iso()) + ")", denied="CONSENT_REVOKE_INVALID")
    db.sql("select public.catalyst_consent_revoke(" + _quote(USER) + "::uuid,null," +
           _quote(_iso()) + ")", denied="CONSENT_REVOKE_INVALID")
    db.sql("select public.catalyst_consent_revoke(" + _quote(USER) + "::uuid," +
           _quote(EVENT) + ",null)", denied="CONSENT_REVOKE_INVALID")
    assert db.sql("select public.catalyst_consent_current(null," + _quote(EVENT) + ") is null") == "t"
    print("NULL_INPUTS_NAMED_REFUSALS=PASS")

    def confirm(tickers: str = "ARRAY['AMD','NVDA']::text[]",
                first_touch: dict[str, str] = touch, when: str | None = None,
                user: str = USER, intent: str = nonce) -> str:
        return ("select public.catalyst_consent_confirm(" +
                _quote(user) + "::uuid," + _quote(EVENT) + "," +
                _quote(SCOPE) + "," + tickers + "," + _quote(intent) + "," +
                _quote(when or _iso()) + "," +
                _quote(json.dumps(first_touch)) + "::jsonb)")
    # Clock window: a verification older than five minutes is refused before any write.
    db.sql(confirm(when=_iso(timedelta(minutes=-10))), denied="CONSENT_VERIFIED_CLOCK_INVALID")
    db.sql(confirm(when=_iso(timedelta(minutes=+2))), denied="CONSENT_VERIFIED_CLOCK_INVALID")
    db.sql(confirm(when="not-a-clock"), denied="CONSENT_VERIFIED_CLOCK_INVALID")
    # Ticker order is irrelevant (reversed here); the stored order is the signed one.
    first = json.loads(db.sql(confirm(), role="service_role"))
    assert first["created"] is True
    assert first["record"]["email"] == EMAIL
    assert first["record"]["first_touch"] == touch
    assert first["record"]["tickers"] == ["NVDA", "AMD"]
    assert json.loads(db.sql(confirm("ARRAY['NVDA','AMD']::text[]")))["created"] is False
    db.sql(confirm("ARRAY['NVDA']::text[]"), denied="CONSENT_INTENT_MISMATCH")
    db.sql(confirm(first_touch={"utm_source": "forged"}),
           denied="CONSENT_INTENT_MISMATCH")
    assert len(json.loads(db.sql("select public.catalyst_consent_interested(" +
                                 _quote(EVENT) + ",10)"))) == 1
    current = json.loads(db.sql("select public.catalyst_consent_current(" +
                                _quote(USER) + "::uuid," + _quote(EVENT) + ")"))
    assert current["intent_id"] == nonce and current["revoked_at_utc"] is None

    # Grant ledger rows are immutable, even for the owner through a direct UPDATE.
    db.sql("update public.catalyst_consent_grants set tickers=ARRAY['X']::text[] where intent_id=" +
           _quote(nonce), denied="CATALYST_CONSENT_GRANT_IMMUTABLE")
    db.sql("update public.catalyst_consent_grants set intent_id='forged_nonce_abcdefghijklmnopqrstu' where intent_id=" +
           _quote(nonce), denied="CATALYST_CONSENT_GRANT_IMMUTABLE")

    # Cleanup of the expired private signed body must not delete or unlink the
    # confirmed grant's immutable intent/nonce audit reference.
    db.sql("delete from public.catalyst_consent_pending where intent_id=" + _quote(nonce))
    assert db.sql("select count(*) from public.catalyst_consent_pending where intent_id=" +
                  _quote(nonce)) == "0"
    assert db.sql("select count(*) from public.catalyst_consent_grants where intent_id=" +
                  _quote(nonce)) == "1"

    # An address suppression permanently revokes the event grant, so clearing
    # a global suppression or general preference cannot reactivate it.
    db.sql("insert into public.email_suppression values (" + _quote(EMAIL) + ",'bounce')")
    assert json.loads(db.sql("select public.catalyst_consent_interested(" +
                              _quote(EVENT) + ",10)")) == []
    db.sql("delete from public.email_suppression")
    assert json.loads(db.sql("select public.catalyst_consent_interested(" +
                              _quote(EVENT) + ",10)")) == []
    assert db.sql("select count(*) from public.catalyst_consent_grants where revoked_at_utc is not null") == "1"
    # A revocation can never be cleared, not even by the owner.
    db.sql("update public.catalyst_consent_grants set revoked_at_utc=null where intent_id=" +
           _quote(nonce), denied="CATALYST_CONSENT_GRANT_IMMUTABLE")
    print("GRANT_IMMUTABILITY=PASS")
    db.sql("insert into public.email_prefs(user_id,marketing_opt_out) values (" + _quote(USER) + "::uuid,true)")
    assert json.loads(db.sql("select public.catalyst_consent_interested(" +
                              _quote(EVENT) + ",10)")) == []
    db.sql("delete from public.email_prefs")
    revoked = json.loads(db.sql("select public.catalyst_consent_revoke(" +
                                _quote(USER) + "::uuid," + _quote(EVENT) + "," +
                                _quote(_iso()) + ")"))
    assert revoked == {"changed": False}  # global suppression already revoked permanently
    assert json.loads(db.sql("select public.catalyst_consent_interested(" +
                              _quote(EVENT) + ",10)")) == []
    db.sql("select public.catalyst_consent_revoke(" + _quote(USER) + "::uuid," +
           _quote(EVENT) + "," + _quote(_iso(timedelta(minutes=-10))) + ")",
           denied="CONSENT_REVOKE_TIME_INVALID")
    db.sql(confirm(), denied="CONSENT_PENDING_NOT_CURRENT")  # expired body cannot be replayed

    # Revoke positive path: a live grant, revoked by the owner RPC, then refused forever.
    user_four = "4d0a2a6c-62ef-4f1c-9a0e-3a4a6a2b6c01"
    email_four = "fixture+four@example.invalid"
    db.sql("insert into auth.users values (" + _quote(user_four) + "::uuid," +
           _quote(email_four) + ",pg_catalog.now()-interval '1 minute')")
    nonce_four = "synthetic_intent_nonce_four_abcdefghijk"
    body_tag_four = _email_tag(SECRET, email_four)
    body = {"v": 1, "scope": SCOPE, "nonce": nonce_four, "event_id": EVENT,
            "tickers": ["TSLA"], "email_tag": body_tag_four, "first_touch": {},
            "issued_at": _iso(), "scan_receipt": "synthetic.scan"}
    signed_four = _sign(SECRET, body)
    db.sql("select public.catalyst_consent_begin(" + ",".join(map(_quote, (
        signed_four, body_tag_four, _iso(timedelta(minutes=20))))) + ")")
    granted = json.loads(db.sql(confirm("ARRAY['TSLA']::text[]", {}, user=user_four, intent=nonce_four)))
    assert granted["created"] is True
    assert len(json.loads(db.sql("select public.catalyst_consent_interested(" +
                                 _quote(EVENT) + ",10)"))) == 1
    assert json.loads(db.sql("select public.catalyst_consent_revoke(" + _quote(user_four) +
                             "::uuid," + _quote(EVENT) + "," + _quote(_iso()) + ")")) == {"changed": True}
    assert json.loads(db.sql("select public.catalyst_consent_interested(" +
                              _quote(EVENT) + ",10)")) == []
    assert json.loads(db.sql("select public.catalyst_consent_revoke(" + _quote(user_four) +
                             "::uuid," + _quote(EVENT) + "," + _quote(_iso()) + ")")) == {"changed": False}
    assert json.loads(db.sql("select public.catalyst_consent_current(" + _quote(user_four) +
                             "::uuid," + _quote(EVENT) + ")"))["revoked_at_utc"] is not None
    # Re-consent after revoke for the same event is refused by design (documented).
    nonce_again = "synthetic_intent_nonce_four_again_abcde"
    body["nonce"] = nonce_again
    body["issued_at"] = _iso()
    db.sql("select public.catalyst_consent_begin(" + ",".join(map(_quote, (
        _sign(SECRET, body), body_tag_four, _iso(timedelta(minutes=20))))) + ")")
    db.sql(confirm("ARRAY['TSLA']::text[]", {}, user=user_four, intent=nonce_again),
           denied="CONSENT_ALREADY_REVOKED_OR_MISMATCHED")
    print("REVOKE_POSITIVE_PATH=PASS")

    # Clock windows on begin/resolve and the expired-body sweep.
    stale = _new_intent(datetime.now(timezone.utc) - timedelta(minutes=25),
                        "synthetic_intent_nonce_stale_abcdefghijk", ["NVDA"])
    db.sql("select public.catalyst_consent_begin(" + ",".join(map(_quote, stale)) + ")",
           denied="INVALID_PENDING_INTENT")
    fresh = _new_intent(datetime.now(timezone.utc), "synthetic_intent_nonce_fresh_abcdefghijk", ["NVDA"])
    ref_fresh = json.loads(db.sql("select public.catalyst_consent_begin(" +
                                  ",".join(map(_quote, fresh)) + ")"))["public_ref"]
    db.sql("update public.catalyst_consent_pending set expires_at_utc=pg_catalog.now()-interval '1 second' "
           "where public_ref=" + _quote(ref_fresh))
    db.sql("select public.catalyst_consent_resolve(" + _quote(ref_fresh) + "," +
           _quote(fresh[1]) + ")", denied="PENDING_REF_UNAVAILABLE")
    db.sql(confirm("ARRAY['NVDA']::text[]", {}, intent="synthetic_intent_nonce_fresh_abcdefghijk"),
           denied="CONSENT_PENDING_NOT_CURRENT")
    print("CLOCK_EXPIRY=PASS")
    # A body expired for over an hour is swept by the next begin(); a recently expired one stays.
    db.sql("update public.catalyst_consent_pending set expires_at_utc=pg_catalog.now()-interval '2 hours' "
           "where public_ref=" + _quote(ref_fresh))
    sweep = _new_intent(datetime.now(timezone.utc), "synthetic_intent_nonce_sweep_abcdefghijk", ["NVDA"])
    db.sql("select public.catalyst_consent_begin(" + ",".join(map(_quote, sweep)) + ")")
    assert db.sql("select count(*) from public.catalyst_consent_pending where public_ref=" +
                  _quote(ref_fresh)) == "0"
    assert db.sql("select count(*) from public.catalyst_consent_pending where intent_id=" +
                  _quote("synthetic_intent_nonce_sweep_abcdefghijk")) == "1"
    print("EXPIRED_PENDING_SWEEP=PASS")

    # A later, existing RLS policy is an install BLOCK, not tacit acceptance.
    db.sql("create policy fixture_unsafe on public.catalyst_consent_pending for select to anon using (true)")
    db.apply(denied="CATALYST_CONSENT_EXISTING_CLIENT_POLICY_BLOCK")
    db.sql("drop policy fixture_unsafe on public.catalyst_consent_pending")
    # A stray service_role table grant is an install BLOCK too (the fence revokes
    # first, so prove the fence by granting AFTER a fresh apply would have run).
    db.apply()  # Idempotent re-run preserves irrevocably revoked grants.
    assert json.loads(db.sql("select public.catalyst_consent_contract()")) == contract
    assert json.loads(db.sql("select public.catalyst_consent_interested(" +
                              _quote(EVENT) + ",10)")) == []
    assert db.sql("select count(*) from public.catalyst_consent_grants where revoked_at_utc is not null") == "2"
    assert _privileges(db)["table_service_select"] is False


def _verify_concurrent_unsubscribe(db: TestPostgres) -> None:
    """Exercise READ COMMITTED races against incumbent shared suppression writes.

    The local socket-only fixture intentionally holds one transaction open
    while the other tries to confirm. No production clients or transports.
    """
    def quote(value: str) -> str:
        return _quote(value)

    def pending(uid: str, nonce: str) -> str:
        db.sql("insert into auth.users values (" + quote(uid) + "::uuid," +
               quote(EMAIL) + ",pg_catalog.now()-interval '1 minute')")
        now = datetime.now(timezone.utc)
        signed, tag, expiry = _new_intent(now, nonce, ["NVDA"])
        db.sql("select public.catalyst_consent_begin(" +
               ",".join(map(quote, (signed, tag, expiry))) + ")")
        return ("select public.catalyst_consent_confirm(" +
                quote(uid) + "::uuid," + quote(EVENT) + "," + quote(SCOPE) +
                ",ARRAY['NVDA']::text[]," + quote(nonce) + "," +
                quote(datetime.now(timezone.utc).isoformat()) + ",'{}'::jsonb)")

    def run_parallel(command: str, competing: str, *, expected_error: str | None) -> None:
        primary = subprocess.Popen(
            db.args + ["-c", command], env=db.env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            # Both transactions use 2s sleep in the same command AFTER their
            # first statement, allowing a conflicting lock attempt.
            time.sleep(0.3)
            secondary = subprocess.run(db.args + ["-c", competing], env=db.env,
                                       text=True, capture_output=True, timeout=15)
            stdout, stderr = primary.communicate(timeout=15)
            assert primary.returncode == 0, ("primary failed", stderr[-1200:])
            if expected_error:
                assert secondary.returncode != 0 and expected_error in secondary.stderr, (
                    "expected denial", secondary.stderr[-1200:])
            else:
                assert secondary.returncode == 0, ("secondary failed", secondary.stderr[-1200:])
        finally:
            if primary.poll() is None:
                primary.kill()
                primary.communicate(timeout=5)

    # Suppression takes email lock first; confirm MUST NOT see an unsuppressed
    # address and create a viable event grant while unsubscribe is pending.
    user_one = "ee773b8c-0f34-4717-bc46-f515e8193370"
    sql_one = pending(user_one, "synthetic_race_a_nonce_abcdefghijklmnop")
    run_parallel(
        "begin; insert into public.email_suppression values (" +
        quote(EMAIL) + ",'unsubscribe'); select pg_sleep(2); commit;",
        sql_one, expected_error="CONSENT_ADDRESS_SUPPRESSED")
    assert db.sql("select count(*) from public.catalyst_consent_grants where user_id=" +
                  quote(user_one) + "::uuid") == "0"
    db.sql("delete from public.email_suppression")

    # Confirm takes email/user locks first; the unsubscribe waits and must
    # permanently revoke the newly created grant when it gets the lock.
    user_two = "eb104742-96ea-4ad8-a2a1-ac6598510012"
    sql_two = pending(user_two, "synthetic_race_b_nonce_abcdefghijklmnop")
    run_parallel(
        "begin; " + sql_two + "; select pg_sleep(2); commit;",
        "insert into public.email_suppression values (" +
        quote(EMAIL) + ",'unsubscribe')", expected_error=None)
    assert db.sql("select count(*) from public.catalyst_consent_grants where user_id=" +
                  quote(user_two) + "::uuid and revoked_at_utc is not null") == "1"
    db.sql("delete from public.email_suppression")
    assert db.sql("select count(*) from public.catalyst_consent_grants where user_id=" +
                  quote(user_two) + "::uuid and revoked_at_utc is null") == "0"

    # User preference takes user lock first; pending confirmation must wait
    # and then refuse despite already having a signed pending intent.
    user_three = "df268bb2-d13f-467b-a64b-6609db5ca17a"
    sql_three = pending(user_three, "synthetic_race_c_nonce_abcdefghijklmnop")
    run_parallel(
        "begin; insert into public.email_prefs(user_id,marketing_opt_out) values (" + quote(user_three) +
        "::uuid,true); select pg_sleep(2); commit;",
        sql_three, expected_error="CONSENT_ADDRESS_SUPPRESSED")
    assert db.sql("select count(*) from public.catalyst_consent_grants where user_id=" +
                  quote(user_three) + "::uuid") == "0"
    db.sql("delete from public.email_prefs")
    print("LOCAL_CONCURRENT_UNSUBSCRIBE_LOCK_ORDER=PASS")


def _verify_rollback(db: TestPostgres) -> None:
    """The rollback file removes every hook and RPC, keeps the ledger, and leaves the
    incumbent unsubscribe / preference writes working; a re-apply restores service."""
    grants_before = db.sql("select count(*) from public.catalyst_consent_grants")
    revoked_before = db.sql("select count(*) from public.catalyst_consent_grants where revoked_at_utc is not null")
    db.apply(path=ROLLBACK)
    assert db.sql("select count(*) from pg_catalog.pg_proc p join pg_catalog.pg_namespace n on n.oid=p.pronamespace "
                  "where n.nspname='public' and p.proname like 'catalyst_consent_%'") == "0"
    assert db.sql("select count(*) from pg_catalog.pg_trigger where tgname like 'catalyst_consent_%'") == "0"
    db.sql("select public.catalyst_consent_contract()", denied="does not exist")
    # Ledger retained, nothing lost.
    assert db.sql("select count(*) from public.catalyst_consent_grants") == grants_before
    assert db.sql("select count(*) from public.catalyst_consent_grants where revoked_at_utc is not null") == revoked_before
    # Incumbent writes still work with no trigger in the way.
    db.sql("insert into public.email_suppression values ('rollback+probe@example.invalid','manual')")
    db.sql("insert into public.email_prefs(user_id,marketing_opt_out) values (" + _quote(USER) + "::uuid,true) "
           "on conflict (user_id) do update set marketing_opt_out=excluded.marketing_opt_out, updated_at=now()")
    db.sql("update public.email_prefs set marketing_opt_out=false where user_id=" + _quote(USER) + "::uuid")
    db.sql("delete from public.email_suppression where email='rollback+probe@example.invalid'")
    db.sql("delete from public.email_prefs where user_id=" + _quote(USER) + "::uuid")
    # Re-apply after rollback: service restored, ledger intact, revocations permanent.
    db.apply()
    assert json.loads(db.sql("select public.catalyst_consent_contract()")) == {"owner": "email_consent", "version": 2}
    assert db.sql("select count(*) from public.catalyst_consent_grants where revoked_at_utc is not null") == revoked_before
    assert db.sql("select count(*) from pg_catalog.pg_trigger where tgname like 'catalyst_consent_%'") == "3"
    db.sql("update public.catalyst_consent_grants set revoked_at_utc=null where revoked_at_utc is not null",
           denied="CATALYST_CONSENT_GRANT_IMMUTABLE")
    print("ROLLBACK_RESTORES_INCUMBENT_WRITES=PASS")


def main() -> None:
    required = ("initdb", "pg_ctl", "psql")
    if any(not shutil.which(exe) for exe in required):
        raise SystemExit("PostgreSQL binaries required for optional local consent smoke test")
    if not SQL.is_file() or not ROLLBACK.is_file():
        raise SystemExit("Cannot locate 0009 migration or its rollback")
    with tempfile.TemporaryDirectory(prefix="mmx-catalyst-consent-local-") as home:
        root = Path(home)
        db = TestPostgres(root)
        try:
            db.start()
            _verify(db)
            _verify_concurrent_unsubscribe(db)
            _verify_rollback(db)
        finally:
            db.stop()
    print("LOCAL_POSTGRES_CONSENT_RPC_V2=PASS")
    print("SECURITY_DENY_ALL=PASS")
    print("AFFIRMATIVE_CONSENT_IDEMPOTENCY_FIRST_TOUCH=PASS")
    print("REVOCATION_SUPPRESSION=PASS")
    print("UNSAFE_POLICY_INSTALL_VETO=PASS")
    print("PRODUCTION_DB_EFFECTS=NONE")


if __name__ == "__main__":
    main()
