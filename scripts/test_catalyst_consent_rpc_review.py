#!/usr/bin/env python3
"""Review-only Catalyst consent RPC v2 smoke test against a *new local PostgreSQL*.

Run manually: python -m scripts.test_catalyst_consent_rpc_review
Creates a brand-new temporary PG cluster, Unix-socket only (NO TCP), builds
mock auth/email-owner tables, applies the held SQL twice and asserts security,
signed-intent persistence, positive consent, suppression and revocation.
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
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

# Pin repo imports for direct execution from any working directory. This local-only
# test does not install a package or modify a global search path for other jobs.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.marketing.catalyst_lifecycle import _email_tag, _sign
SQL = ROOT / "research/marketing_dockets/MKT_CATALYST_CONSENT_RPC_V2_REVIEW_ONLY.sql"
USER = "9507e687-116a-4d30-9c30-fdf45c9d91b2"
EMAIL = "fixture+updates@example.invalid"
SECRET = "synthetic_hmac_only_no_real_user_or_token_0123456789"
EVENT = "synthetic-event-20261009"
SCOPE = "catalyst_event_updates/v1"
PORT = "55462"


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

    def apply(self, *, denied: str | None = None) -> None:
        self.run(self.args + ["-f", str(SQL)],
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


def _verify(db: TestPostgres) -> None:
    db.sql("create role anon nologin")
    db.sql("create role authenticated nologin")
    db.sql("create role service_role nologin")
    db.sql("grant usage on schema public to anon, authenticated, service_role")
    db.sql("create schema auth")
    db.sql("create table auth.users(id uuid primary key, email text, email_confirmed_at timestamptz)")
    db.sql("create table public.email_suppression(email text primary key, reason text)")
    db.sql("create table public.email_prefs(user_id uuid primary key,marketing_opt_out boolean not null default false)")
    db.apply()
    contract = json.loads(db.sql("select public.catalyst_consent_contract()"))
    assert contract == {"owner": "email_consent", "version": 2}
    permissions = json.loads(db.sql("""select pg_catalog.jsonb_build_object(
      'anon',pg_catalog.has_function_privilege('anon','public.catalyst_consent_begin(text,text,text)','EXECUTE'),
      'authenticated',pg_catalog.has_function_privilege('authenticated','public.catalyst_consent_begin(text,text,text)','EXECUTE'),
      'service',pg_catalog.has_function_privilege('service_role','public.catalyst_consent_begin(text,text,text)','EXECUTE'),
      'table',pg_catalog.has_table_privilege('anon','public.catalyst_consent_grants','SELECT'),
      'policies',(select pg_catalog.count(*) from pg_catalog.pg_policies
        where schemaname='public' and tablename in ('catalyst_consent_pending','catalyst_consent_grants'))
    )"""))
    assert permissions == {"anon": False, "authenticated": False, "service": True,
                           "table": False, "policies": 0}, permissions
    db.sql("select public.catalyst_consent_contract()", role="anon",
           denied="permission denied")
    db.sql("select public.catalyst_consent_contract()", role="authenticated",
           denied="permission denied")
    db.sql("select * from public.catalyst_consent_grants", role="anon",
           denied="permission denied")

    now = datetime.now(timezone.utc)
    db.sql("insert into auth.users values (" + _quote(USER) + "::uuid," +
           _quote(EMAIL) + ",pg_catalog.now()-interval '1 minute')")
    touch = {"utm_source": "partner", "utm_medium": "partner_demo",
             "utm_campaign": "catalyst_scan", "utm_content": "cp_synthetic"}
    nonce = "synthetic_intent_nonce_abcdefghijklmnop"
    signed, tag, expiration = _new_intent(now, nonce, ["NVDA", "AMD"], touch)
    future = _quote(expiration)
    pending = json.loads(db.sql("select public.catalyst_consent_begin(" +
                                ",".join(map(_quote, (signed, tag, expiration))) + ")"))
    opaque = pending["public_ref"]
    assert re.fullmatch(r"[A-Za-z0-9_-]{32,128}", opaque)
    assert json.loads(db.sql("select public.catalyst_consent_resolve(" +
                             _quote(opaque) + "," + _quote(tag) + ")"))["intent"] == signed
    db.sql("select public.catalyst_consent_resolve(" + _quote(opaque) +
           "," + _quote("0" * 64) + ")", denied="PENDING_REF_UNAVAILABLE")
    def confirm(tickers: str = "ARRAY['NVDA','AMD']::text[]",
                first_touch: dict[str, str] = touch) -> str:
        return ("select public.catalyst_consent_confirm(" +
                _quote(USER) + "::uuid," + _quote(EVENT) + "," +
                _quote(SCOPE) + "," + tickers + "," + _quote(nonce) + "," +
                _quote(datetime.now(timezone.utc).isoformat()) + "," +
                _quote(json.dumps(first_touch)) + "::jsonb)")
    first = json.loads(db.sql(confirm()))
    assert first["created"] is True
    assert first["record"]["email"] == EMAIL
    assert first["record"]["first_touch"] == touch
    assert json.loads(db.sql(confirm()))["created"] is False
    db.sql(confirm("ARRAY['NVDA']::text[]"), denied="CONSENT_INTENT_MISMATCH")
    db.sql(confirm(first_touch={"utm_source": "forged"}),
           denied="CONSENT_INTENT_MISMATCH")
    assert len(json.loads(db.sql("select public.catalyst_consent_interested(" +
                                 _quote(EVENT) + ",10)"))) == 1

    # An address suppression and an account opt-out independently hide a
    # positive grant from the recipient selection; neither creates consent.
    db.sql("insert into public.email_suppression values (" + _quote(EMAIL) + ",'bounce')")
    assert json.loads(db.sql("select public.catalyst_consent_interested(" +
                              _quote(EVENT) + ",10)")) == []
    db.sql("delete from public.email_suppression")
    db.sql("insert into public.email_prefs values (" + _quote(USER) + "::uuid,true)")
    assert json.loads(db.sql("select public.catalyst_consent_interested(" +
                              _quote(EVENT) + ",10)")) == []
    db.sql("delete from public.email_prefs")
    revoked = json.loads(db.sql("select public.catalyst_consent_revoke(" +
                                _quote(USER) + "::uuid," + _quote(EVENT) + "," +
                                _quote(datetime.now(timezone.utc).isoformat()) + ")"))
    assert revoked == {"changed": True}
    assert json.loads(db.sql("select public.catalyst_consent_interested(" +
                              _quote(EVENT) + ",10)")) == []
    assert json.loads(db.sql("select public.catalyst_consent_revoke(" +
                              _quote(USER) + "::uuid," + _quote(EVENT) + "," +
                              _quote(datetime.now(timezone.utc).isoformat()) + ")")) == {"changed": False}
    db.sql(confirm(), denied="CONSENT_ALREADY_REVOKED_OR_MISMATCHED")

    # A later, existing RLS policy is an install BLOCK, not tacit acceptance.
    db.sql("create policy fixture_unsafe on public.catalyst_consent_pending for select to anon using (true)")
    db.apply(denied="CATALYST_CONSENT_EXISTING_CLIENT_POLICY_BLOCK")
    db.sql("drop policy fixture_unsafe on public.catalyst_consent_pending")
    db.apply()  # Idempotent re-run preserves irrevocably revoked grants.
    assert json.loads(db.sql("select public.catalyst_consent_contract()")) == contract
    assert json.loads(db.sql("select public.catalyst_consent_interested(" +
                              _quote(EVENT) + ",10)")) == []


def main() -> None:
    required = ("initdb", "pg_ctl", "psql")
    if any(not shutil.which(exe) for exe in required):
        raise SystemExit("PostgreSQL binaries required for optional local consent smoke test")
    if not SQL.is_file():
        raise SystemExit("Cannot locate owner-review-only SQL")
    with tempfile.TemporaryDirectory(prefix="mmx-catalyst-consent-local-") as home:
        root = Path(home)
        db = TestPostgres(root)
        try:
            db.start()
            _verify(db)
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
