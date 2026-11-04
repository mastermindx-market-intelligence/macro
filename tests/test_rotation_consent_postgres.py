"""Exercise real PostgreSQL locking in a new Unix-only temporary cluster.

No existing database, Supabase project, production role or external service is
contacted. Missing PostgreSQL is a qualification failure, never a silent skip.
"""
from __future__ import annotations
import io
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import tempfile
import threading
import time
import uuid

import pytest
from lib import user_prefs as P

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "scripts/deploy/rotation_notification_consent_v1.sql"
ROLLBACK = ROOT / "scripts/deploy/rotation_notification_consent_v1_rollback.sql"
KEY = "rotation_notification_consent"
YES = {"alert_email_optin": True, "alert_categories": ["sector_rotation_relative"],
       "lang": "en", "foreign_preference": "preserve"}
OWNER = "macro_rotation_consent_owner"
PORT = "55463"


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
        return json.loads(self.sql(
            f"SELECT public.rotation_consent_read_v1({quote(uid)});", "service_role"))

    def transition_sql(self, uid, enabled, revision=None):
        rev = "NULL" if revision is None else quote(revision)
        return (f"SELECT public.rotation_consent_set_v1({quote(uid)},"
                f"{'true' if enabled else 'false'},{rev});")

    def transition(self, uid, enabled, revision=None):
        return json.loads(self.sql(self.transition_sql(uid, enabled, revision), "service_role"))

    def update(self, uid, meta, app=None):
        fields = "raw_user_meta_data=" + jsql(meta)
        if app is not None:
            fields += ",raw_app_meta_data=" + jsql(app)
        self.sql(f"UPDATE auth.users SET {fields} WHERE id={quote(uid)};",
                 "supabase_auth_admin")

    def holding(self, command, role):
        if command.startswith("SELECT public.rotation_consent_set_v1("):
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
        name = "rotation-fixture-" + uuid.uuid4().hex
        cmd = self.prefix(role) + "SET application_name=" + quote(name) + "; " + command
        p = subprocess.Popen(self.args(role) + ["-c", cmd], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, env=self.env)
        deadline = time.monotonic() + 1.2
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
    with tempfile.TemporaryDirectory(prefix="rot-consent-", dir="/tmp") as root:
        db = LocalPG(root)
        try:
            db.start()
            db.sql("""
              CREATE ROLE anon NOLOGIN; CREATE ROLE authenticated NOLOGIN;
              CREATE ROLE service_role NOLOGIN; CREATE ROLE authenticator LOGIN NOINHERIT;
              CREATE ROLE supabase_auth_admin LOGIN NOSUPERUSER NOCREATEROLE;
              GRANT anon,authenticated,service_role TO authenticator;
              GRANT USAGE ON SCHEMA public TO anon,authenticated,service_role;
              ALTER DEFAULT PRIVILEGES IN SCHEMA public
                GRANT EXECUTE ON FUNCTIONS TO anon,authenticated,service_role;
              CREATE SCHEMA auth;
              GRANT USAGE ON SCHEMA auth TO supabase_auth_admin;
              CREATE TABLE auth.users(id uuid PRIMARY KEY,
                raw_user_meta_data jsonb,raw_app_meta_data jsonb,unrelated text);
              ALTER TABLE auth.users OWNER TO supabase_auth_admin;
            """)
            db.apply()
            yield db
        finally:
            db.stop()


@pytest.fixture
def user(db):
    uid = str(uuid.uuid4())
    db.sql(f"INSERT INTO auth.users VALUES({quote(uid)},{jsql(YES)},"
           "'{\"provider\":\"fixture\"}'::jsonb,'keep');", "supabase_auth_admin")
    return uid


def test_default_off_and_fresh_positive_control(db, user):
    initial = db.read(user)["state"]
    assert initial["active"] is False and initial["revision"] is None
    active = db.transition(user, True)["state"]
    assert active["active"] is True and active["revision"] is not None
    assert active["activated_at"].endswith("Z")
    assert db.read(user)["state"] == active
    revoked = db.transition(user, False, str(uuid.uuid4()))["state"]
    assert revoked["status"] == "inactive" and revoked["revision"] != active["revision"]
    again = db.transition(user, True, revoked["revision"])["state"]
    assert again["active"] and again["revision"] not in {active["revision"],revoked["revision"]}


def test_rpc_and_role_privileges_are_real_session_boundaries(db, user):
    for role in ("anon", "authenticated"):
        db.sql(db.transition_sql(user, True), role, denied="permission denied")
        db.sql(f"SELECT public.rotation_consent_read_v1({quote(user)});",
               role, denied="permission denied")
    db.sql("SET ROLE " + OWNER, "service_role", denied="permission denied")
    db.sql("ALTER FUNCTION public.rotation_consent_set_v1(uuid,boolean,uuid) "
           "RENAME TO stolen", "service_role", denied="must be owner")
    db.sql("ALTER TABLE auth.users DISABLE TRIGGER mmx_rotation_consent_guard_v1",
           "service_role", denied="permission denied")
    assert db.sql("SELECT rolcanlogin OR rolsuper OR rolbypassrls FROM pg_roles WHERE "
                  "rolname=" + quote(OWNER)) == "f"
    assert db.sql("SELECT count(*) FROM pg_auth_members m JOIN pg_roles r "
                  "ON r.oid=m.roleid OR r.oid=m.member WHERE r.rolname=" + quote(OWNER)) == "0"


@pytest.mark.parametrize("negative", [
    {"alert_email_optin": False}, {"alert_categories": []},
    {"alert_email_optin": "true"}, {"alert_categories": None},
    {"alert_categories": ["sector_rotation_relative", 1]},
])
def test_legacy_optout_then_stale_whole_object_cannot_reactivate(db, user, negative):
    old = db.transition(user, True)["state"]
    stale = {"provider":"fixture", KEY:dict(v=1,revision=old["revision"],
              active=True,activated_at=old["activated_at"])}
    db.update(user, YES | negative)
    revoked = db.read(user)["state"]
    assert not revoked["active"] and revoked["revision"] != old["revision"]
    db.update(user, YES | {"lang":"zh"}, stale | {"other_app_key":"new"})
    final = db.read(user)["state"]
    assert final == revoked
    raw = json.loads(db.sql(f"SELECT raw_app_meta_data FROM auth.users WHERE id={quote(user)}"))
    assert raw["provider"] == "fixture" and raw["other_app_key"] == "new"
    assert db.transition(user, True, old["revision"])["status"] == "stale_revision"
    assert db.transition(user, True)["status"] == "stale_revision"
    assert db.transition(user, True, final["revision"])["state"]["active"]


def test_absent_marker_tombstone_and_null_cas(db, user):
    db.update(user, YES | {"alert_email_optin":False})
    revoked = db.read(user)["state"]
    assert revoked["revision"] is not None
    db.update(user, YES)
    assert db.read(user)["state"] == revoked
    assert db.transition(user, True)["status"] == "stale_revision"


def test_forgery_deletion_and_guc_do_not_create_authority(db, user):
    fake = dict(v=1, revision=str(uuid.uuid4()), active=True,
                activated_at="2026-11-04T00:00:00Z")
    db.update(user, YES, {KEY:fake,"provider":"fixture"})
    assert db.read(user)["state"]["revision"] is None
    state = db.transition(user, True)["state"]
    revoked = db.transition(user, False)["state"]
    db.sql("SET mmx.rotation_consent_owner='macro_rotation_consent_owner'; "
           f"UPDATE auth.users SET raw_app_meta_data={jsql({KEY:fake,'fresh':1})} "
           f"WHERE id={quote(user)};", "supabase_auth_admin")
    assert db.read(user)["state"] == revoked
    db.update(user, YES, {"fresh":2})
    assert db.read(user)["state"] == revoked
    assert state["revision"] != revoked["revision"]


@pytest.mark.parametrize("bad", [None, {}, {"revision":"bad","active":True},
                               {"v":1,"revision":None,"active":False,"activated_at":None}])
def test_malformed_is_not_absent_and_optout_repairs_without_old_token_cast(db, user, bad):
    # Privileged fixture corruption is deliberately outside the application threat
    # boundary; a table owner can disable triggers. No production connection exists.
    db.sql("ALTER TABLE auth.users DISABLE TRIGGER mmx_rotation_consent_guard_v1; "
           f"UPDATE auth.users SET raw_app_meta_data={jsql({'provider':'fixture',KEY:bad})} "
           f"WHERE id={quote(user)}; "
           "ALTER TABLE auth.users ENABLE TRIGGER mmx_rotation_consent_guard_v1;")
    assert db.read(user)["state"]["status"] == "corrupt"
    assert db.transition(user, True)["status"] == "metadata_unreadable"
    fixed = db.transition(user, False)["state"]
    assert fixed["status"] == "inactive" and fixed["revision"]
    assert db.transition(user, True)["status"] == "stale_revision"
    assert db.transition(user, True, fixed["revision"])["state"]["active"]


@pytest.mark.parametrize("initially_active", [False, True])
def test_optout_first_makes_waiting_stale_enable_refuse(db, user, initially_active):
    revision = db.transition(user, True)["state"]["revision"] if initially_active else None
    holding = db.holding(
        f"UPDATE auth.users SET raw_user_meta_data={jsql(YES|{'alert_email_optin':False})} "
        f"WHERE id={quote(user)};", "supabase_auth_admin")
    waiting = db.waiting(db.transition_sql(user, True, revision), "service_role")
    result = json.loads(db.release(holding, waiting))
    assert result["status"] == "stale_revision"
    assert not db.read(user)["state"]["active"]


@pytest.mark.parametrize("initially_active", [False, True])
def test_enable_first_then_waiting_optout_finishes_revoked(db, user, initially_active):
    revision = db.transition(user, True)["state"]["revision"] if initially_active else None
    holding = db.holding(db.transition_sql(user, True, revision), "service_role")
    waiting = db.waiting(
        f"UPDATE auth.users SET raw_user_meta_data={jsql(YES|{'alert_email_optin':False})} "
        f"WHERE id={quote(user)};", "supabase_auth_admin")
    db.release(holding, waiting)
    assert not db.read(user)["state"]["active"]


def test_two_enables_with_one_revision_have_one_winner(db, user):
    holding = db.holding(db.transition_sql(user, True), "service_role")
    waiting = db.waiting(db.transition_sql(user, True), "service_role")
    result = json.loads(db.release(holding, waiting))
    assert result["status"] == "stale_revision"


def test_actual_existing_preference_writer_stale_save_cannot_restore_activation(db, user, monkeypatch):
    old = db.transition(user, True)["state"]
    read_done, resume = threading.Event(), threading.Event()
    saved = []
    def transport(request, **kwargs):
        if request.method == "GET":
            meta = json.loads(db.sql(
                f"SELECT raw_user_meta_data FROM auth.users WHERE id={quote(user)}"))
            if threading.current_thread().name == "stale-language-save":
                read_done.set()
                assert resume.wait(5)
            return io.BytesIO(json.dumps({"user_metadata":meta}).encode())
        meta = json.loads(request.data)["user_metadata"]
        db.update(user, meta)
        return io.BytesIO(b"{}")
    monkeypatch.setattr(P.urllib.request, "urlopen", transport)
    thread = threading.Thread(name="stale-language-save", target=lambda:saved.append(
        P.write_user_prefs(user, {"lang":"zh"}, supabase=("https://fixture.invalid","fake"))))
    thread.start()
    assert read_done.wait(5)
    assert P.write_user_prefs(user, {"alert_email_optin":False},
                              supabase=("https://fixture.invalid","fake"))
    revoked = db.read(user)["state"]
    resume.set()
    thread.join(5)
    assert not thread.is_alive() and saved == [True]
    assert db.read(user)["state"] == revoked
    assert not revoked["active"] and revoked["revision"] != old["revision"]
    # This C0 guard protects rotation activation, not the legacy metadata projection.
    raw = json.loads(db.sql(f"SELECT raw_user_meta_data FROM auth.users WHERE id={quote(user)}"))
    assert raw["lang"] == "zh" and raw["alert_email_optin"] is True


def test_reapply_preserves_revisions_and_does_not_backfill(db, user):
    before = db.transition(user, True)["state"]
    db.apply()
    assert db.read(user)["state"] == before



def test_reapply_refuses_an_extra_definer_owned_by_the_privilege_role(db):
    db.sql("GRANT CREATE ON SCHEMA public TO macro_rotation_consent_owner; "
           "SET ROLE macro_rotation_consent_owner; "
           "CREATE FUNCTION public.rotation_fixture_poison() RETURNS integer "
           "LANGUAGE sql SECURITY DEFINER AS 'SELECT 1'; RESET ROLE; "
           "REVOKE CREATE ON SCHEMA public FROM macro_rotation_consent_owner;")
    try:
        db.apply(denied="function or trigger ownership mismatch")
    finally:
        db.sql("DROP FUNCTION public.rotation_fixture_poison()")


def test_reapply_refuses_role_membership_drift(db):
    db.sql("GRANT macro_rotation_consent_owner TO service_role")
    try:
        db.apply(denied="owner identity or membership mismatch")
    finally:
        db.sql("REVOKE macro_rotation_consent_owner FROM service_role")


def test_rls_incompatibility_never_grants_bypass_to_make_the_call_work(db, user):
    before = db.read(user)["state"]
    db.sql("ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY")
    try:
        assert db.read(user)["status"] == "user_not_found"
        assert db.transition(user, True)["status"] == "user_not_found"
        assert db.sql("SELECT rolbypassrls FROM pg_roles WHERE "
                      "rolname='macro_rotation_consent_owner'") == "f"
    finally:
        db.sql("ALTER TABLE auth.users DISABLE ROW LEVEL SECURITY")
    assert db.read(user)["state"] == before

def test_rollback_retains_marker_and_removes_rpc_authority(db, user):
    inactive = db.transition(user, False)["state"]
    try:
        db.apply(ROLLBACK)
        raw = json.loads(db.sql(f"SELECT raw_app_meta_data FROM auth.users WHERE id={quote(user)}"))
        assert raw[KEY]["revision"] == inactive["revision"]
        db.sql(db.transition_sql(user, True), "service_role", denied="does not exist")
        db.update(user, YES | {"lang":"zh"})
    finally:
        db.apply()
