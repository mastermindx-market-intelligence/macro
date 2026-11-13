"""Real PostgreSQL digest-consent fences, permissions and original API effects.

A new Unix-only temporary cluster is the sole database target. Missing binaries
fail qualification. No production account, PostgREST service or SMTP is contacted.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import tempfile
import time
import uuid

import pytest
from fastapi import HTTPException, Response
from app import account_prefs as prefs

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "scripts/deploy/portfolio_digest_consent_v1.sql"
BASE_SQL = ROOT / "scripts/deploy/0007_support_email.sql"
ROLLBACK = ROOT / "scripts/deploy/portfolio_digest_consent_v1_rollback.sql"
OWNER = "macro_digest_consent_owner"
PORT = "55464"

def quote(value):
    return "'" + value.replace("'", "''") + "'"


def jsql(value):
    return quote(json.dumps(value)) + "::jsonb"


def pg_bin(name):
    found = shutil.which(name)
    if found:
        return found
    config = shutil.which("pg_config")
    if config:
        directory = subprocess.check_output([config, "--bindir"], text=True).strip()
        path = Path(directory) / name
        if path.is_file():
            return str(path)
    raise AssertionError("PostgreSQL qualification binary missing: " + name)


class LocalPG:
    def __init__(self, root):
        self.root = Path(root)
        self.data = self.root / "data"
        self.socket = self.root / "socket"
        self.socket.mkdir()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("PG")}
        self.bins = {n: pg_bin(n) for n in ("initdb", "pg_ctl", "psql")}
        self.started = False

    def run(self, args, **kwargs):
        return subprocess.run(args, capture_output=True, text=True, env=self.env,
                              timeout=25, **kwargs)

    def start(self):
        r = self.run([self.bins["initdb"], "-D", str(self.data), "-A", "trust",
                      "--no-instructions", "--encoding=UTF8", "--locale=C"])
        assert r.returncode == 0, r.stderr
        r = self.run([self.bins["pg_ctl"], "-D", str(self.data),
                      "-l", str(self.root / "server.log"), "-o",
                      f"-k {self.socket} -p {PORT} -c listen_addresses='' "
                      "-c max_connections=20 -c shared_buffers=16MB -c fsync=off",
                      "-w", "start"])
        assert r.returncode == 0, r.stderr
        self.started = True

    def stop(self):
        if self.started:
            r = self.run([self.bins["pg_ctl"], "-D", str(self.data),
                          "-w", "stop", "-m", "immediate"])
            assert r.returncode == 0, r.stderr
            self.started = False

    def args(self, role=None):
        args = [self.bins["psql"], "-X", "-Aqt", "-v", "ON_ERROR_STOP=1",
                "-h", str(self.socket), "-p", PORT, "-d", "postgres"]
        if role in {"anon", "authenticated", "service_role"}:
            args += ["-U", "authenticator"]
        elif role == "supabase_auth_admin":
            args += ["-U", "supabase_auth_admin"]
        return args

    def prefix(self, role):
        return "SET ROLE " + role + "; " if role else ""

    def sql(self, command, role=None, denied=None):
        r = self.run(self.args(role) + ["-c", self.prefix(role) + command])
        if denied:
            assert r.returncode != 0 and denied in r.stderr, (r.stdout, r.stderr)
            return ""
        assert r.returncode == 0, r.stderr
        return r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""

    def apply(self, path=SQL, denied=None):
        r = self.run(self.args() + ["-f", str(path)])
        if denied:
            assert r.returncode != 0 and denied in r.stderr, r.stderr
        else:
            assert r.returncode == 0, r.stderr

    def read(self, uid):
        raw = self.sql("SELECT row_to_json(p) FROM public.email_prefs p WHERE user_id=" + quote(uid),
                       "service_role")
        return json.loads(raw) if raw else None

    def transition_sql(self, uid, enabled, revision=None):
        rev = "NULL" if revision is None else quote(revision)
        return (f"SELECT public.portfolio_digest_consent_set_v1({quote(uid)},"
                f"{'true' if enabled else 'false'},{rev});")

    def transition(self, uid, enabled, revision=None):
        return json.loads(self.sql(self.transition_sql(uid, enabled, revision), "service_role"))

    def holding(self, command, role):
        if command.startswith("SELECT public.portfolio_digest_consent_set_v1("):
            command = "DO $hold$ BEGIN PERFORM " + command[len("SELECT "):] + " END $hold$;"
        p = subprocess.Popen(self.args(role), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, bufsize=1, env=self.env)
        p.stdin.write("BEGIN; " + self.prefix(role) + command + " SELECT 'held';\n")
        p.stdin.flush()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            ready, _, _ = select.select([p.stdout], [], [], max(0, deadline-time.monotonic()))
            assert ready, "holding transaction did not reach barrier"
            line = p.stdout.readline().strip()
            if line == "held":
                return p
            if p.poll() is not None:
                raise AssertionError(p.stderr.read())
        raise AssertionError("holding transaction barrier expired")

    def waiting(self, command, role):
        name = "digest-fixture-" + uuid.uuid4().hex
        cmd = self.prefix(role) + "SET application_name=" + quote(name) + "; " + command
        p = subprocess.Popen(self.args(role) + ["-c", cmd], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, env=self.env)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            waiting = self.sql("SELECT count(*) FROM pg_stat_activity WHERE "
                              "application_name=" + quote(name) + " AND wait_event_type='Lock';")
            if waiting == "1":
                return p
            assert p.poll() is None, p.communicate()
            time.sleep(.02)
        raise AssertionError("second connection never waited on the actual row lock")

    def release(self, holding, waiting):
        holding.stdin.write("COMMIT;\n\\q\n")
        holding.stdin.flush()
        holding.stdin.close()
        holding.wait(timeout=5)
        assert holding.returncode == 0, holding.stderr.read()
        out, err = waiting.communicate(timeout=5)
        assert waiting.returncode == 0, err
        return out.strip().splitlines()[-1] if out.strip() else ""


@pytest.fixture(scope="module")
def db():
    with tempfile.TemporaryDirectory(prefix="digest-consent-", dir="/tmp") as root:
        db = LocalPG(root)
        try:
            db.start()
            db.sql("""
              CREATE ROLE anon NOLOGIN; CREATE ROLE authenticated NOLOGIN;
              CREATE ROLE service_role NOLOGIN BYPASSRLS;
              CREATE ROLE authenticator LOGIN NOINHERIT;
              CREATE ROLE supabase_auth_admin LOGIN NOSUPERUSER NOCREATEROLE;
              GRANT anon,authenticated,service_role TO authenticator;
              GRANT USAGE ON SCHEMA public TO anon,authenticated,service_role;
              ALTER DEFAULT PRIVILEGES IN SCHEMA public
                GRANT EXECUTE ON FUNCTIONS TO anon,authenticated,service_role;
              CREATE SCHEMA auth;
              GRANT USAGE ON SCHEMA auth TO supabase_auth_admin;
              CREATE TABLE auth.users(id uuid PRIMARY KEY);
              ALTER TABLE auth.users OWNER TO supabase_auth_admin;
            """)
            db.apply(BASE_SQL)
            db.sql("GRANT ALL ON public.email_prefs TO service_role; "
                   "GRANT SELECT,INSERT,UPDATE,DELETE ON public.email_prefs TO anon,authenticated")
            db.apply()
            yield db
        finally:
            db.stop()


@pytest.fixture
def user(db):
    uid = str(uuid.uuid4())
    db.sql("INSERT INTO auth.users VALUES(" + quote(uid) + ")", "supabase_auth_admin")
    return uid


def initial_revision(db, user, state):
    if state == "absent":
        return None
    row = db.transition(user, False)["state"]
    if state == "active":
        row = db.transition(user, True, row["portfolio_digest_revision"])["state"]
    return row["portfolio_digest_revision"]


def test_default_off_tombstone_and_explicit_reenable(db, user):
    assert db.read(user) is None
    stopped = db.transition(user, False)["state"]
    assert stopped["portfolio_digest_opt_in"] is False
    assert str(uuid.UUID(stopped["portfolio_digest_revision"])) == stopped["portfolio_digest_revision"]
    stopped_again = db.transition(user, False)["state"]
    assert stopped_again["portfolio_digest_revision"] != stopped["portfolio_digest_revision"]
    assert db.transition(user, True)["status"] == "stale_revision"
    assert db.transition(user, True, stopped["portfolio_digest_revision"])["status"] == "stale_revision"
    enabled = db.transition(user, True, stopped_again["portfolio_digest_revision"])
    assert enabled["status"] == "applied" and enabled["state"]["portfolio_digest_opt_in"]
    assert enabled["state"]["portfolio_digest_revision"] != stopped_again["portfolio_digest_revision"]


def test_fresh_null_observation_only_enables_a_truly_absent_row(db, user):
    result = db.transition(user, True)
    assert result["status"] == "applied" and result["state"]["portfolio_digest_opt_in"]
    again = db.transition(user, True)
    assert again["status"] == "stale_revision" and again["state"] == result["state"]


@pytest.mark.parametrize("state", ["absent", "inactive", "active"])
def test_withdrawal_holds_real_lock_and_rejects_waiting_old_enable(db, user, state):
    old = initial_revision(db, user, state)
    holding = db.holding(db.transition_sql(user, False), "service_role")
    waiting = db.waiting(db.transition_sql(user, True, old), "service_role")
    result = json.loads(db.release(holding, waiting))
    final = db.read(user)
    assert result["status"] == "stale_revision"
    assert final["portfolio_digest_opt_in"] is False
    assert final["portfolio_digest_revision"] != old


@pytest.mark.parametrize("state", ["absent", "inactive", "active"])
def test_enable_holds_real_lock_then_waiting_withdrawal_finishes_false(db, user, state):
    old = initial_revision(db, user, state)
    holding = db.holding(db.transition_sql(user, True, old), "service_role")
    waiting = db.waiting(db.transition_sql(user, False), "service_role")
    result = json.loads(db.release(holding, waiting))
    assert result["status"] == "applied" and result["state"]["portfolio_digest_opt_in"] is False
    assert db.read(user)["portfolio_digest_revision"] == result["state"]["portfolio_digest_revision"]


@pytest.mark.parametrize("state", ["absent", "inactive"])
def test_two_enables_of_one_observation_have_one_winner(db, user, state):
    old = initial_revision(db, user, state)
    holding = db.holding(db.transition_sql(user, True, old), "service_role")
    waiting = db.waiting(db.transition_sql(user, True, old), "service_role")
    result = json.loads(db.release(holding, waiting))
    assert result["status"] == "stale_revision"
    assert db.read(user)["portfolio_digest_opt_in"] is True


def test_language_mirror_and_global_unsubscribe_cannot_be_overwritten_by_digest(db, user):
    db.sql("INSERT INTO public.email_prefs(user_id,lang,marketing_opt_out) VALUES("
           + quote(user) + ",'zh',true)", "service_role")
    before = db.read(user)
    result = db.transition(user, True, before["portfolio_digest_revision"])
    assert result["status"] == "applied"
    active = db.read(user)
    assert active["lang"] == "zh" and active["marketing_opt_out"] is True
    db.sql("INSERT INTO public.email_prefs(user_id,lang) VALUES(" + quote(user)
           + ",'en') ON CONFLICT(user_id) DO UPDATE SET user_id=EXCLUDED.user_id,lang=EXCLUDED.lang", "service_role")
    mirrored = db.read(user)
    assert mirrored["lang"] == "en" and mirrored["portfolio_digest_opt_in"]
    assert mirrored["portfolio_digest_revision"] == active["portfolio_digest_revision"]
    db.sql("INSERT INTO public.email_prefs(user_id,marketing_opt_out) VALUES(" + quote(user)
           + ",true) ON CONFLICT(user_id) DO UPDATE SET user_id=EXCLUDED.user_id,marketing_opt_out=EXCLUDED.marketing_opt_out",
           "service_role")
    assert db.read(user)["portfolio_digest_revision"] == active["portfolio_digest_revision"]
    db.transition(user, False)
    final = db.read(user)
    assert final["lang"] == "en" and final["marketing_opt_out"] is True


def test_legacy_negative_write_fences_old_enable_and_positive_bypass_is_denied(db, user):
    before = db.transition(user, False)["state"]
    db.sql("UPDATE public.email_prefs SET portfolio_digest_opt_in=false WHERE user_id="
           + quote(user), "service_role")
    after = db.read(user)
    assert after["portfolio_digest_revision"] != before["portfolio_digest_revision"]
    assert db.transition(user, True, before["portfolio_digest_revision"])["status"] == "stale_revision"
    db.sql("SET mmx.digest_consent_owner='macro_digest_consent_owner'; "
           "UPDATE public.email_prefs SET portfolio_digest_opt_in=true WHERE user_id="
           + quote(user), "service_role", denied="requires the guarded RPC")
    enabled = db.transition(user, True, after["portfolio_digest_revision"])["state"]
    db.sql("UPDATE public.email_prefs SET portfolio_digest_revision=" + quote(str(uuid.uuid4()))
           + " WHERE user_id=" + quote(user), "service_role", denied="requires the guarded RPC")
    assert db.read(user)["portfolio_digest_revision"] == enabled["portfolio_digest_revision"]


def test_direct_positive_insert_is_denied_and_client_roles_cannot_invoke_rpc(db, user):
    db.sql("INSERT INTO public.email_prefs(user_id,portfolio_digest_opt_in) VALUES("
           + quote(user) + ",true)", "service_role", denied="requires the guarded RPC")
    assert db.read(user) is None
    for role in ("anon", "authenticated"):
        db.sql(db.transition_sql(user, True), role, denied="permission denied")
    db.sql("SET ROLE " + OWNER, "service_role", denied="permission denied")
    db.sql("ALTER FUNCTION public.portfolio_digest_consent_set_v1(uuid,boolean,uuid) "
           "RENAME TO stolen", "service_role", denied="must be owner")
    db.sql("ALTER TABLE public.email_prefs DISABLE TRIGGER portfolio_digest_consent_update_v1",
           "service_role", denied="must be owner")
    assert db.sql("SELECT rolcanlogin OR rolinherit OR rolsuper OR rolbypassrls FROM pg_roles "
                  "WHERE rolname=" + quote(OWNER)) == "f"
    assert db.sql("SELECT count(*) FROM pg_auth_members m JOIN pg_roles r "
                  "ON r.oid=m.roleid OR r.oid=m.member WHERE r.rolname=" + quote(OWNER)) == "0"
    db.sql("UPDATE public.email_prefs SET lang='zh' WHERE user_id=" + quote(user),
           OWNER, denied="permission denied")


def test_existing_preference_row_delete_is_not_a_supported_fence_reset(db, user):
    db.transition(user, False)
    db.sql("DELETE FROM public.email_prefs WHERE user_id=" + quote(user),
           "service_role", denied="permission denied")
    db.sql("TRUNCATE public.email_prefs", "service_role", denied="permission denied")
    assert db.read(user)["portfolio_digest_opt_in"] is False
    # The parent account's existing FK cascade remains supported.
    db.sql("DELETE FROM auth.users WHERE id=" + quote(user), "supabase_auth_admin")
    assert db.read(user) is None


@pytest.mark.parametrize("enabled", [False, True])
def test_actual_api_lost_commit_reply_stays_uncertain_without_replay(db, user, monkeypatch, enabled):
    old = db.transition(user, False)["state"]["portfolio_digest_revision"]
    calls = []
    def store(method, path, body=None, **kwargs):
        calls.append((method, path, dict(body)))
        assert method == "POST" and path == "rpc/portfolio_digest_consent_set_v1"
        db.transition(body["p_user_id"], body["p_enabled"], body["p_expected_revision"])
        raise TimeoutError("fixture committed then reply lost")
    monkeypatch.setattr(prefs, "_digest_pref_store", store)
    monkeypatch.setenv("PORTFOLIO_DIGEST_ENROLLMENT_ENABLED", "1")
    with pytest.raises(HTTPException) as error:
        prefs.set_portfolio_digest_choice(prefs.PortfolioDigestChoice(
            enabled=enabled, expected_revision=old), Response(), {"id": user})
    assert error.value.status_code == 503 and "unconfirmed" in error.value.detail
    final = db.read(user)
    assert final["portfolio_digest_opt_in"] is enabled
    assert final["portfolio_digest_revision"] != old and len(calls) == 1


def test_reapply_preserves_decisions_and_revisions(db, user):
    before = db.transition(user, True)["state"]
    db.apply()
    after = db.read(user)
    assert after["portfolio_digest_revision"] == before["portfolio_digest_revision"]
    assert after["portfolio_digest_opt_in"] is True


def test_reapply_refuses_membership_and_unrelated_definer_drift(db):
    db.sql("GRANT " + OWNER + " TO service_role")
    try:
        db.apply(denied="owner identity or membership mismatch")
    finally:
        db.sql("REVOKE " + OWNER + " FROM service_role")
    db.sql("GRANT CREATE ON SCHEMA public TO " + OWNER + "; SET ROLE " + OWNER + "; "
           "CREATE FUNCTION public.digest_fixture_poison() RETURNS integer "
           "LANGUAGE sql SECURITY DEFINER AS 'SELECT 1'; RESET ROLE; "
           "REVOKE CREATE ON SCHEMA public FROM " + OWNER)
    try:
        db.apply(denied="function or object ownership mismatch")
    finally:
        db.sql("DROP FUNCTION public.digest_fixture_poison()")


def test_rollback_retains_fences_and_negative_writes_without_positive_authority(db, user):
    old = db.transition(user, False)["state"]
    try:
        db.apply(ROLLBACK)
        assert db.read(user)["portfolio_digest_revision"] == old["portfolio_digest_revision"]
        db.sql(db.transition_sql(user, True, old["portfolio_digest_revision"]),
               "service_role", denied="does not exist")
        db.sql("UPDATE public.email_prefs SET portfolio_digest_opt_in=true WHERE user_id="
               + quote(user), "service_role", denied="requires the guarded RPC")
        db.sql("UPDATE public.email_prefs SET lang='zh' WHERE user_id=" + quote(user), "service_role")
        assert db.read(user)["lang"] == "zh"
    finally:
        db.apply()
    assert db.read(user)["portfolio_digest_revision"] == old["portfolio_digest_revision"]


def test_tombstone_cannot_move_to_another_existing_auth_account(db, user):
    old = db.transition(user, False)["state"]
    other = str(uuid.uuid4())
    db.sql("INSERT INTO auth.users VALUES(" + quote(other) + ")", "supabase_auth_admin")
    db.sql("UPDATE public.email_prefs SET user_id=" + quote(other)
           + " WHERE user_id=" + quote(user), "service_role", denied="identity is immutable")
    assert db.read(user)["portfolio_digest_revision"] == old["portfolio_digest_revision"]
    assert db.read(other) is None
    assert db.transition(user, True)["status"] == "stale_revision"


def test_reapply_refuses_effective_erasure_and_default_drift(db):
    db.sql("GRANT DELETE ON public.email_prefs TO service_role")
    try:
        db.apply(denied="application erasure privilege drift")
    finally:
        db.sql("REVOKE DELETE ON public.email_prefs FROM service_role")
    db.sql("ALTER TABLE public.email_prefs ALTER COLUMN portfolio_digest_opt_in SET DEFAULT true")
    try:
        db.apply(denied="column shape or default mismatch")
    finally:
        db.sql("ALTER TABLE public.email_prefs ALTER COLUMN portfolio_digest_opt_in SET DEFAULT false")


def test_reapply_refuses_an_unreviewed_before_trigger(db):
    db.sql("CREATE FUNCTION public.digest_fixture_trigger() RETURNS trigger LANGUAGE plpgsql "
           "AS 'BEGIN NEW.portfolio_digest_opt_in := true; RETURN NEW; END'; "
           "CREATE TRIGGER digest_fixture_unreviewed BEFORE UPDATE ON public.email_prefs "
           "FOR EACH ROW EXECUTE FUNCTION public.digest_fixture_trigger()")
    try:
        db.apply(denied="unqualified email_prefs trigger or policy")
    finally:
        db.sql("DROP TRIGGER digest_fixture_unreviewed ON public.email_prefs; "
               "DROP FUNCTION public.digest_fixture_trigger()")
