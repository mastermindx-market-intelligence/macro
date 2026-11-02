#!/usr/bin/env python3
"""Apply, verify or roll back the Catalyst consent v2 RPCs (0009) through the Supabase
Management API SQL endpoint — the same route 0004 (analytics) used.

Intended to run ON the VPS with /etc/macro-admin.env sourced, so SUPABASE_ACCESS_TOKEN
never leaves the operator's box:

    set -a; . /etc/macro-admin.env; set +a
    python3 scripts/deploy/catalyst_consent_migrate.py --verify     # read-only census
    python3 scripts/deploy/catalyst_consent_migrate.py --apply      # 0009, then verify
    python3 scripts/deploy/catalyst_consent_migrate.py --rollback   # rollback, then verify

Prints names, counts and booleans only — never a key, token, address or row. Exit 0 means
the requested end state is observed (installed after --apply/--verify, absent after
--rollback); 2 means the opposite clean state; 1 means a partial install or an HTTP error.
Idempotent: both SQL files may be re-run. Sends a browser User-Agent because Cloudflare's
WAF in front of api.supabase.com 403s the default Python UA (edge error 1010).
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
APPLY_SQL = HERE / "0009_catalyst_consent_rpc_v2.sql"
ROLLBACK_SQL = HERE / "0009_catalyst_consent_rpc_v2_rollback.sql"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
RPCS = (
    "catalyst_consent_contract", "catalyst_consent_begin", "catalyst_consent_resolve",
    "catalyst_consent_confirm", "catalyst_consent_current", "catalyst_consent_interested",
    "catalyst_consent_revoke",
)
TRIGGER_FUNCTIONS = (
    "catalyst_consent_grant_guard", "catalyst_consent_on_global_address_suppression",
    "catalyst_consent_on_global_user_optout",
)
TRIGGERS = (
    "catalyst_consent_global_address_revocation", "catalyst_consent_global_user_revocation",
    "catalyst_consent_grant_immutable",
)
TABLES = ("catalyst_consent_pending", "catalyst_consent_grants")

CENSUS_SQL = """
select pg_catalog.jsonb_build_object(
  'functions', (select coalesce(pg_catalog.jsonb_agg(p.proname order by p.proname), '[]'::jsonb)
                  from pg_catalog.pg_proc p join pg_catalog.pg_namespace n on n.oid = p.pronamespace
                 where n.nspname = 'public' and p.proname like 'catalyst\\_consent\\_%'),
  'triggers', (select coalesce(pg_catalog.jsonb_agg(t.tgname order by t.tgname), '[]'::jsonb)
                 from pg_catalog.pg_trigger t where t.tgname like 'catalyst\\_consent\\_%' and not t.tgisinternal),
  'tables', (select coalesce(pg_catalog.jsonb_agg(c.relname order by c.relname), '[]'::jsonb)
               from pg_catalog.pg_class c join pg_catalog.pg_namespace n on n.oid = c.relnamespace
              where n.nspname = 'public' and c.relkind = 'r' and c.relname like 'catalyst\\_consent\\_%'),
  'policies', (select pg_catalog.count(*) from pg_catalog.pg_policies
                where schemaname = 'public' and tablename like 'catalyst\\_consent\\_%'),
  'anon_execute_begin', pg_catalog.has_function_privilege('anon', 'public.catalyst_consent_begin(text,text,text)', 'EXECUTE'),
  'authenticated_execute_begin', pg_catalog.has_function_privilege('authenticated', 'public.catalyst_consent_begin(text,text,text)', 'EXECUTE'),
  'authenticated_table_select', pg_catalog.has_table_privilege('authenticated', 'public.catalyst_consent_grants', 'SELECT'),
  'triggers_enabled', (select pg_catalog.count(*) from pg_catalog.pg_trigger t join pg_catalog.pg_class c on c.oid = t.tgrelid
                        where t.tgname like 'catalyst\\_consent\\_%' and not t.tgisinternal and t.tgenabled in ('O','A')
                          and ((t.tgname = 'catalyst_consent_global_address_revocation' and c.relname = 'email_suppression')
                               or (t.tgname = 'catalyst_consent_global_user_revocation' and c.relname = 'email_prefs')
                               or (t.tgname = 'catalyst_consent_grant_immutable' and c.relname = 'catalyst_consent_grants'))),
  'service_execute_begin', pg_catalog.has_function_privilege('service_role', 'public.catalyst_consent_begin(text,text,text)', 'EXECUTE'),
  'service_table_select', pg_catalog.has_table_privilege('service_role', 'public.catalyst_consent_grants', 'SELECT'),
  'anon_table_select', pg_catalog.has_table_privilege('anon', 'public.catalyst_consent_grants', 'SELECT'),
  'contract', public.catalyst_consent_contract()
) as census
"""

# Same census without the function-dependent fields, for the absent / rollback state.
CENSUS_ABSENT_SQL = """
select pg_catalog.jsonb_build_object(
  'functions', (select coalesce(pg_catalog.jsonb_agg(p.proname order by p.proname), '[]'::jsonb)
                  from pg_catalog.pg_proc p join pg_catalog.pg_namespace n on n.oid = p.pronamespace
                 where n.nspname = 'public' and p.proname like 'catalyst\\_consent\\_%'),
  'triggers', (select coalesce(pg_catalog.jsonb_agg(t.tgname order by t.tgname), '[]'::jsonb)
                 from pg_catalog.pg_trigger t where t.tgname like 'catalyst\\_consent\\_%' and not t.tgisinternal),
  'tables', (select coalesce(pg_catalog.jsonb_agg(c.relname order by c.relname), '[]'::jsonb)
               from pg_catalog.pg_class c join pg_catalog.pg_namespace n on n.oid = c.relnamespace
              where n.nspname = 'public' and c.relkind = 'r' and c.relname like 'catalyst\\_consent\\_%')
) as census
"""


def _endpoint() -> tuple[str, str]:
    pat = os.environ.get("SUPABASE_ACCESS_TOKEN", "")
    if not pat:
        raise SystemExit("SUPABASE_ACCESS_TOKEN unset — source /etc/macro-admin.env on the VPS first")
    ref = os.environ.get("SUPABASE_PROJECT_REF") or "fsldfzlxyavsuwqbceod"
    return pat, f"https://api.supabase.com/v1/projects/{ref}/database/query"


def call(sql: str):
    pat, url = _endpoint()
    req = urllib.request.Request(
        url, data=json.dumps({"query": sql}).encode(), method="POST",
        headers={"Authorization": "Bearer " + pat, "Content-Type": "application/json", "User-Agent": UA})
    try:
        resp = urllib.request.urlopen(req, timeout=90)
        return resp.getcode(), resp.read().decode()
    except urllib.error.HTTPError as e:
        # Error bodies name the SQL failure (fence names, lock timeouts); never a secret.
        return e.code, e.read().decode()[:600]
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        # Transport failure: the request may or may not have reached the server, so the
        # caller must treat the effect as unknown and take the census regardless.
        return 0, type(e).__name__


def _census(absent_ok: bool) -> dict | None:
    code, body = call(CENSUS_SQL)
    if code not in (200, 201) and absent_ok:
        code, body = call(CENSUS_ABSENT_SQL)
    if code not in (200, 201):
        print(f"census_http={code} {body}")
        return None
    try:
        rows = json.loads(body)
        census = rows[0]["census"] if isinstance(rows, list) else rows["census"]
        if isinstance(census, str):
            census = json.loads(census)
        return census
    except (ValueError, KeyError, IndexError, TypeError):
        print(f"census_http={code} unparseable")
        return None


def _report(census: dict) -> str:
    fns = set(census.get("functions") or [])
    trg = set(census.get("triggers") or [])
    tbl = set(census.get("tables") or [])
    installed = (set(RPCS) <= fns and set(TRIGGER_FUNCTIONS) <= fns and set(TRIGGERS) <= trg and set(TABLES) <= tbl
                 and ("triggers_enabled" not in census or census.get("triggers_enabled") == len(TRIGGERS)))
    absent = not (fns & (set(RPCS) | set(TRIGGER_FUNCTIONS))) and not (trg & set(TRIGGERS))
    contract_ok = census.get("contract") == {"owner": "email_consent", "version": 2}
    grants_ok = (census.get("anon_execute_begin") is False and census.get("service_execute_begin") is True
                 and census.get("service_table_select") is False and census.get("anon_table_select") is False
                 and census.get("authenticated_execute_begin") is False and census.get("authenticated_table_select") is False
                 and census.get("policies") == 0)
    print(f"functions={len(fns & (set(RPCS) | set(TRIGGER_FUNCTIONS)))}/{len(RPCS) + len(TRIGGER_FUNCTIONS)} "
          f"triggers={len(trg & set(TRIGGERS))}/{len(TRIGGERS)} tables={len(tbl & set(TABLES))}/{len(TABLES)} "
          f"policies={census.get('policies', '?')}")
    if "contract" in census:
        print(f"contract_ok={contract_ok} grants_ok={grants_ok}")
    if installed and contract_ok and grants_ok:
        return "INSTALLED"
    if absent:
        return "ABSENT"
    return "PARTIAL"


def main() -> int:
    mode = "--verify"
    for arg in ("--apply", "--rollback", "--verify"):
        if arg in sys.argv[1:]:
            mode = arg
    failed = False
    if mode in ("--apply", "--rollback"):
        src = APPLY_SQL if mode == "--apply" else ROLLBACK_SQL
        code, body = call(src.read_text())
        print(f"{mode[2:]}_http={code} {'ok' if code in (200, 201) else body}")
        if code == 0:
            print(f"{mode[2:]}_effect=UNKNOWN (transport failure; the census below is the truth)")
        failed = code not in (200, 201)
    if failed:
        # The file is one explicit transaction; a failure inside it commits nothing. Clear
        # any aborted transaction the pooled connection might still hold, then take the
        # census anyway so the operator sees the resulting state, never a bare exit code.
        try:
            call("rollback;")
        except Exception:  # best effort only; the census is what matters
            pass
        census = _census(absent_ok=True)
        print(f"state={_report(census)}" if census is not None else "state=UNKNOWN (census unavailable)")
        return 1
    census = _census(absent_ok=True)
    if census is None:
        return 1
    state = _report(census)
    print(f"state={state}")
    if mode == "--rollback":
        return 0 if state == "ABSENT" else (2 if state == "INSTALLED" else 1)
    return 0 if state == "INSTALLED" else (2 if state == "ABSENT" else 1)


if __name__ == "__main__":
    sys.exit(main())
