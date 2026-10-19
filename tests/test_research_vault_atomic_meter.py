"""Tests for atomic_view_ratelimit — RV W2 view cap + atomic Brain pair metering.

Stdlib + pytest only; no network, no live ledgers: every test roots the state
dir at tmp_path via MACRO_API_STATE_DIR. Covers (a) preserved legacy allow/peek
behavior, (b) the Brain pair API (preflight/commit, dedup cost, atomic
all-or-nothing charging, fail-closed state handling, redundant IP mirror),
(c) cross-process concurrency with no lost updates, (d) bounded lock behavior.
"""
import hashlib
import json
import logging
import multiprocessing
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from engine.research_vault import view_ratelimit as mod  # noqa: E402
from tests.test_research_vault_comparison import configured

NOW = datetime(2026, 10, 19, 14, 0, 0, tzinfo=timezone.utc)
PERIOD = "2026-10-19T14"
NEXT_HOUR = NOW + timedelta(hours=1)


@pytest.fixture
def rl(tmp_path, monkeypatch):
    """Isolated state root with a small, deterministic hourly cap of 5."""
    state = tmp_path / "state"
    monkeypatch.setenv("MACRO_API_STATE_DIR", str(state))
    monkeypatch.setenv("RESEARCH_VIEW_HOURLY", "5")
    monkeypatch.delenv("RESEARCH_VIEW_RL_LOCK_TIMEOUT", raising=False)
    return state / "research_view_rl"


def ucount(rl, uid, period=PERIOD):
    return mod._read(mod._user_file(uid, period)).get("count") or 0


def icount(rl, ip_hash, period=PERIOD):
    return mod._read(mod._ip_file(ip_hash, period)).get("count") or 0


def seed(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


# --------------------------------------------------------------------------
# Legacy allow/peek behavior (must be preserved verbatim in outcome)
# --------------------------------------------------------------------------

def test_allow_increments_both_ledgers_and_reports_remaining(rl):
    ok, meta = mod.allow("user-x", "1.2.3.4", now=NOW)
    assert ok is True and meta == {"remaining": 4, "limit": 5}
    assert ucount(rl, "user-x") == 1
    assert icount(rl, mod._hash_ip("1.2.3.4")) == 1
    ok, meta = mod.allow("user-x", "1.2.3.4", root=None, now=NOW)  # root parity kwarg
    assert ok is True and meta["remaining"] == 3


def test_allow_worse_of_two_remaining_and_deny(rl):
    seed(mod._user_file("user-x", PERIOD), {"count": 4})  # user nearly full
    ok, meta = mod.allow("user-x", "9.9.9.9", now=NOW)
    assert ok is True and meta["remaining"] == 0  # worse leg: user now at cap
    ok, meta = mod.allow("user-x", "9.9.9.9", now=NOW)
    assert ok is False and meta == {"remaining": 0, "limit": 5}


def test_allow_deny_writes_nothing(rl):
    seed(mod._user_file("user-x", PERIOD), {"count": 5})
    ok, meta = mod.allow("user-x", "1.2.3.4", now=NOW)
    assert ok is False
    assert ucount(rl, "user-x") == 5
    assert not mod._ip_file(mod._hash_ip("1.2.3.4"), PERIOD).exists()


def test_allow_ip_leg_independent_of_user_leg(rl):
    assert mod.allow("user-x", "1.1.1.1", now=NOW)[0] is True
    assert mod.allow("user-x", "2.2.2.2", now=NOW)[0] is True
    assert ucount(rl, "user-x") == 2
    assert icount(rl, mod._hash_ip("1.1.1.1")) == 1
    assert icount(rl, mod._hash_ip("2.2.2.2")) == 1


def test_ip_privacy_and_noip_fallback(rl):
    import hashlib
    mod.allow("user-x", "203.0.113.7", now=NOW)
    mod.allow("user-y", "", now=NOW)
    mod.allow("user-y", "unknown", now=NOW)
    names = [p.name for p in rl.glob("vip_*.json")]
    assert all("203.0.113.7" not in n for n in names)
    expected = hashlib.sha256(b"203.0.113.7").hexdigest()[:16]
    assert f"vip_{expected}_{PERIOD}.json" in names
    assert icount(rl, mod._hash_ip("203.0.113.7")) == 1
    assert icount(rl, "noip") == 2  # empty and 'unknown' share the noip bucket


def test_lossy_sanitization_is_not_the_canonical_user_key(rl):
    uid = "../etc/pass:wd"
    assert mod.allow(uid, "1.2.3.4", now=NOW)[0] is True
    assert mod._safe_uid(uid) == "___etc_pass_wd"  # legacy ambiguity locator only
    expected = "~" + hashlib.sha256(uid.encode("utf-8")).hexdigest()
    assert mod._user_component(uid) == expected
    assert (rl / f"vh_{expected}_{PERIOD}.json").exists()
    assert not mod._legacy_user_file(uid, PERIOD).exists()
    assert "/" not in expected and ":" not in expected


def test_peek_is_read_only(rl):
    mod.allow("user-x", "1.2.3.4", now=NOW)
    assert mod.peek("user-x", "1.2.3.4", now=NOW) == {"remaining": 4, "limit": 5}
    assert ucount(rl, "user-x") == 1
    assert mod.peek("ghost", "nowhere", now=NOW) == {"remaining": 5, "limit": 5}


def test_hourly_cap_env_override_and_garbage_fallback(rl, monkeypatch):
    monkeypatch.setenv("RESEARCH_VIEW_HOURLY", "2")
    assert mod._hourly_limit() == 2
    monkeypatch.setenv("RESEARCH_VIEW_HOURLY", "not-a-number")
    assert mod._hourly_limit() == 60
    monkeypatch.setenv("RESEARCH_VIEW_HOURLY", "-3")
    assert mod._hourly_limit() == 60


def test_period_key_hours_and_naive_utc(rl):
    key = mod._period_key(NOW)
    assert key == PERIOD
    # naive input is treated as UTC
    assert mod._period_key(NOW.replace(tzinfo=None)) == key
    assert mod.allow("user-x", "1.2.3.4", now=NOW)[0] is True
    # a different hour is a fresh, independent ledger
    ok, meta = mod.allow("user-x", "1.2.3.4", now=NEXT_HOUR)
    assert ok is True and meta["remaining"] == 4
    assert ucount(rl, "user-x", PERIOD) == 1
    assert ucount(rl, "user-x", "2026-10-19T15") == 1
    assert not (rl / "locks").exists() or True  # locks may exist; see lock tests


def test_allow_does_not_rewrite_malformed_canonical_counts(rl):
    # Availability is retained, but an ordinary view cannot reset unknown
    # historical usage into an apparently verified fresh canonical counter.
    for uid, value in (("a", "2"), ("b", True), ("c", None)):
        path = mod._user_file(uid, PERIOD)
        seed(path, {"count": value}); before = path.read_bytes()
        assert mod.allow(uid, "1.1.1.1", now=NOW)[0] is True
        assert path.read_bytes() == before
        assert mod.preflight_many(uid, ["r1"], now=NOW) is False


# --------------------------------------------------------------------------
# Brain pair API: validation, dedup cost, shared capacity, atomicity
# --------------------------------------------------------------------------

def test_commit_charges_deduped_cost_once(rl):
    assert mod.commit_many("user-x", ["r1", "r1"], now=NOW) is True
    assert ucount(rl, "user-x") == 1          # len(dedup(["r1","r1"])) == 1
    assert mod.commit_many("user-x", ("r2", "r2"), now=NOW) is True  # tuple ok
    assert ucount(rl, "user-x") == 2
    assert mod.commit_many("user-x", ["r3", "r4"], now=NOW) is True
    assert ucount(rl, "user-x") == 4          # two distinct ids cost 2


def test_commit_and_allow_share_one_user_ledger_and_cap(rl):
    assert mod.allow("user-x", "1.2.3.4", now=NOW)[0] is True
    assert mod.allow("user-x", "1.2.3.4", now=NOW)[0] is True
    assert mod.commit_many("user-x", ["r1", "r2"], now=NOW) is True
    assert ucount(rl, "user-x") == 4
    # 4 used, 1 left: a 1-id pair fits, a 2-id pair does not (all-or-nothing)
    assert mod.commit_many("user-x", ["r3", "r4"], now=NOW) is False
    assert ucount(rl, "user-x") == 4          # no partial charge
    assert mod.commit_many("user-x", ["r3"], now=NOW) is True
    assert ucount(rl, "user-x") == 5
    assert mod.allow("user-x", "1.2.3.4", now=NOW)[0] is False  # cap shared both ways


def test_commit_empty_pair_charges_nothing(rl):
    with pytest.raises(mod.RateLimitArgError): mod.commit_many("user-x", (), now=NOW)
    with pytest.raises(mod.RateLimitArgError): mod.preflight_many("user-x", (), now=NOW)
    assert not mod._user_file("user-x", PERIOD).exists()


def test_preflight_advisory_no_charge_and_agrees_with_commit(rl):
    for _ in range(10):
        assert mod.preflight_many("user-x", ["r1", "r2"], now=NOW) is True
    assert ucount(rl, "user-x") == 0          # preflight never charges
    assert mod.commit_many("user-x", ["r1", "r2"], now=NOW) is True
    assert ucount(rl, "user-x") == 2
    assert mod.preflight_many("user-x", ["r3", "r4"], now=NOW) is True   # 2+2 <= 5
    assert mod.commit_many("user-x", ["r3", "r4"], now=NOW) is True
    assert ucount(rl, "user-x") == 4
    assert mod.preflight_many("user-x", ["r5"], now=NOW) is True         # 4+1 <= 5
    assert mod.preflight_many("user-x", ["r5", "r6"], now=NOW) is False  # 4+2 > 5
    assert mod.commit_many("user-x", ["r5", "r6"], now=NOW) is False
    assert ucount(rl, "user-x") == 4          # over-cap commit charges nothing
    assert mod.commit_many("user-x", ["r5"], now=NOW) is True
    assert ucount(rl, "user-x") == 5
    assert mod.preflight_many("user-x", ["r7"], now=NOW) is False        # at cap


def test_commit_rechecks_under_lock_after_stale_preflight(rl):
    assert mod.preflight_many("user-x", ["r1"], now=NOW) is True
    for _ in range(5):  # someone else fills the cap between preflight and commit
        assert mod.allow("user-x", "1.2.3.4", now=NOW)[0] is True
    assert mod.commit_many("user-x", ["r1"], now=NOW) is False
    assert ucount(rl, "user-x") == 5


def test_pair_hours_are_independent(rl):
    assert mod.commit_many("user-x", ["r1", "r2"], now=NOW) is True
    assert mod.commit_many("user-x", ["r1", "r2"], now=NEXT_HOUR) is True
    assert ucount(rl, "user-x", PERIOD) == 2
    assert ucount(rl, "user-x", "2026-10-19T15") == 2


def test_commit_writes_no_extra_counter_or_budget_files(rl):
    mod.allow("user-x", "1.2.3.4", now=NOW)
    assert mod.commit_many("user-x", ["r1"], now=NOW) is True
    ledgers = {p.name for p in rl.glob("*.json")}
    assert ledgers == {
        f"vh_user-x_{PERIOD}.json",
        f"vip_{mod._hash_ip('1.2.3.4')}_{PERIOD}.json",
        f"vip_{mod._brain_ip_hash('user-x')}_{PERIOD}.json",
    }
    assert mod._brain_ip_hash("user-x") == mod._hash_ip("brain:user-x")
    assert icount(rl, mod._brain_ip_hash("user-x")) == 1  # mirror charged too
    assert all("budget" not in n and "counter" not in n for n in ledgers)


@pytest.mark.parametrize(
    "uid,ids",
    [
        ("", ["r1"]),                          # empty uid
        ("   ", ["r1"]),                       # whitespace uid
        ("u" * 257, ["r1"]),                   # overlong uid
        (None, ["r1"]),                        # non-string uid
        (7, ["r1"]),                           # non-string uid
        ("u", "r1"),                           # str is not a tuple/list of ids
        ("u", b"r1"),                          # bytes likewise
        ("u", {"r1": 1}),                      # dict likewise
        ("u", {"r1", "r2"}),                   # set likewise (not tuple/list)
        ("u", (r for r in ["r1"])),            # generator likewise
        ("u", ["r1", "r2", "r3"]),             # more than 2 report ids
        ("u", ["r1", ""]),                     # empty id
        ("u", ["r1", "   "]),                  # whitespace id
        ("u", ["r1", 42]),                     # non-string id
        ("u", ["r1", None]),                   # non-string id
        ("u", ["x" * 513]),                    # overlong id
    ],
)
def test_malformed_call_arguments_raise(rl, uid, ids):
    with pytest.raises(mod.RateLimitArgError):
        mod.preflight_many(uid, ids, now=NOW)
    with pytest.raises(mod.RateLimitArgError):
        mod.commit_many(uid, ids, now=NOW)
    assert not any(rl.glob("*.json"))          # nothing charged, nothing created


# --------------------------------------------------------------------------
# Malformed canonical state: Brain path fails closed, allow stays legacy
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "bad",
    [True, False, -3, "2", 2.5, [1], {"count": 1}],
)
def test_malformed_count_fail_closed_for_pair_only(rl, bad):
    seed(mod._user_file("user-x", PERIOD), {"count": bad})
    assert mod.preflight_many("user-x", ["r1"], now=NOW) is False
    assert mod.commit_many("user-x", ["r1"], now=NOW) is False
    # nothing charged: the malformed file is left exactly as found
    assert json.loads(mod._user_file("user-x", PERIOD).read_text()) == {"count": bad}
    # Legacy paid-view availability survives, but malformed historical state
    # is preserved rather than reset by that availability fallback.
    assert mod.allow("user-x", "1.2.3.4", now=NOW)[0] is True
    assert json.loads(mod._user_file("user-x", PERIOD).read_text()) == {"count": bad}


def test_corrupt_ledger_json_fail_closed_for_pair_only(rl, caplog):
    uf = mod._user_file("user-x", PERIOD)
    uf.parent.mkdir(parents=True, exist_ok=True)
    uf.write_text("{definitely not json", encoding="utf-8")
    with caplog.at_level(logging.ERROR, logger="research_vault.view_ratelimit"):
        assert mod.preflight_many("user-x", ["r1"], now=NOW) is False
        assert mod.commit_many("user-x", ["r1"], now=NOW) is False
    assert uf.read_text() == "{definitely not json"
    assert any("malformed" in r.getMessage().lower() for r in caplog.records)
    assert mod.allow("user-x", "1.2.3.4", now=NOW)[0] is True  # legacy fail-open


def test_non_dict_ledger_fail_closed_for_pair_only(rl):
    uf = mod._user_file("user-x", PERIOD)
    uf.parent.mkdir(parents=True, exist_ok=True)
    uf.write_text("[1, 2, 3]", encoding="utf-8")
    assert mod.commit_many("user-x", ["r1"], now=NOW) is False
    assert uf.read_text() == "[1, 2, 3]"


def test_only_explicit_zero_or_actual_absence_is_a_fresh_period(rl):
    seed(mod._user_file("user-x", PERIOD), {"count": 0})
    assert mod.preflight_many("user-x", ["r1"], now=NOW) is True
    assert mod.commit_many("user-x", ["r1"], now=NOW) is True
    seed(mod._user_file("user-y", PERIOD), {"note": "no count key"})
    assert mod.commit_many("user-y", ["r1"], now=NOW) is False
    assert "count" not in mod._read(mod._user_file("user-y", PERIOD))
    seed(mod._user_file("user-z", PERIOD), {"count": None})  # legacy reads as 0
    assert mod.preflight_many("user-z", ["r1"], now=NOW) is False
    assert mod.commit_many("user-z", ["r1"], now=NOW) is False
    assert mod._read(mod._user_file("user-z", PERIOD))["count"] is None


# --------------------------------------------------------------------------
# Write failures: before vs after the canonical user commit
# --------------------------------------------------------------------------

def test_user_write_failure_fails_closed_and_charges_nothing(rl, monkeypatch, caplog):
    assert mod.commit_many("user-x", ["r1"], now=NOW) is True  # count -> 1
    real = mod._write_atomic

    def boom(path, data):
        if path.name.startswith("vh_"):
            raise OSError("disk on fire")
        return real(path, data)

    monkeypatch.setattr(mod, "_write_atomic", boom)
    with caplog.at_level(logging.ERROR, logger="research_vault.view_ratelimit"):
        assert mod.commit_many("user-x", ["r1"], now=NOW) is False
    assert ucount(rl, "user-x") == 1           # charge did not advance
    assert list(rl.glob("*.tmp")) == []        # no tmp left behind
    assert any("COMMIT UNCONFIRMED" in r.getMessage() for r in caplog.records)


def test_user_write_failure_on_fresh_period_charges_nothing(rl):
    seen = []

    def boom(path, data):
        seen.append(path.name)
        if path.name.startswith("vh_"):
            raise OSError("state dir readonly")
        raise AssertionError("mirror must not be attempted without user commit")

    orig = mod._write_atomic
    mod._write_atomic = boom
    try:
        assert mod.commit_many("user-x", ["r1"], now=NOW) is False
    finally:
        mod._write_atomic = orig
    assert seen == [f"vh_user-x_{PERIOD}.json"]
    assert not mod._user_file("user-x", PERIOD).exists()
    assert not mod._ip_file(mod._brain_ip_hash("user-x"), PERIOD).exists()


def test_mirror_failure_never_denies_proven_user_commit(rl, monkeypatch, caplog):
    real = mod._write_atomic

    def boom(path, data):
        if path.name.startswith("vip_"):
            raise OSError("mirror unwritable")
        return real(path, data)

    monkeypatch.setattr(mod, "_write_atomic", boom)
    with caplog.at_level(logging.ERROR, logger="research_vault.view_ratelimit"):
        assert mod.commit_many("user-x", ["r1", "r2"], now=NOW) is True
    assert ucount(rl, "user-x") == 2           # canonical charge stands
    assert icount(rl, mod._brain_ip_hash("user-x")) == 0  # mirror stale, fine
    assert any("IP MIRROR" in r.getMessage() for r in caplog.records)


def test_unwritable_state_dir_fails_closed_for_pair_and_open_for_allow(
    rl, tmp_path, monkeypatch, caplog
):
    locked_dir = tmp_path / "readonly"
    locked_dir.mkdir()
    monkeypatch.setenv("MACRO_API_STATE_DIR", str(locked_dir))
    state = locked_dir / "research_view_rl"
    state.mkdir()
    (state / "locks").mkdir()
    os.chmod(state, 0o500)                     # read-only ledger dir
    try:
        with caplog.at_level(logging.ERROR, logger="research_vault.view_ratelimit"):
            assert mod.commit_many("user-x", ["r1"], now=NOW) is False
            ok, _meta = mod.allow("user-x", "1.2.3.4", now=NOW)
        assert ok is True                      # legacy fail-open-but-loud
        assert caplog.records                  # and LOUD on both paths
    finally:
        os.chmod(state, 0o700)


# --------------------------------------------------------------------------
# Bounded, process-safe locking
# --------------------------------------------------------------------------

def test_commit_fails_closed_on_lock_timeout_while_allow_fails_open(rl, monkeypatch):
    monkeypatch.setenv("RESEARCH_VIEW_RL_LOCK_TIMEOUT", "0.05")
    import fcntl as _fcntl

    mod._lock_dir().mkdir(parents=True, exist_ok=True)
    fd = os.open(str(mod._user_lock("user-x", PERIOD)), os.O_RDWR | os.O_CREAT, 0o600)
    _fcntl.flock(fd, _fcntl.LOCK_EX)  # someone else holds the user lock
    try:
        t0 = time.monotonic()
        assert mod.commit_many("user-x", ["r1"], now=NOW) is False
        assert time.monotonic() - t0 < 5.0     # bounded wait, not unbounded
        assert not mod._user_file("user-x", PERIOD).exists()  # nothing charged
        ok, meta = mod.allow("user-x", "1.2.3.4", now=NOW)
        assert ok is True and meta["remaining"] == 0   # fail-open, no invented remaining budget
        assert not mod._user_file("user-x", PERIOD).exists()
    finally:
        _fcntl.flock(fd, _fcntl.LOCK_UN)
        os.close(fd)
    # with the lock free, the very same pair commit proceeds
    assert mod.commit_many("user-x", ["r1"], now=NOW) is True
    assert ucount(rl, "user-x") == 1


def test_lock_timeout_is_clamped_to_a_bounded_window(rl, monkeypatch):
    monkeypatch.setenv("RESEARCH_VIEW_RL_LOCK_TIMEOUT", "99999")
    assert mod._lock_timeout() == 30.0
    monkeypatch.setenv("RESEARCH_VIEW_RL_LOCK_TIMEOUT", "0")
    assert mod._lock_timeout() == 0.05
    monkeypatch.setenv("RESEARCH_VIEW_RL_LOCK_TIMEOUT", "garbage")
    assert mod._lock_timeout() == 5.0


# --------------------------------------------------------------------------
# Cross-process concurrency: shared capacity with NO lost updates
# --------------------------------------------------------------------------

def _worker_allow(state_dir, uid, ip, hourly, now, barrier, q):
    os.environ["MACRO_API_STATE_DIR"] = state_dir
    os.environ["RESEARCH_VIEW_HOURLY"] = str(hourly)
    from engine.research_vault import view_ratelimit as m
    barrier.wait(timeout=30)
    try:
        ok, _ = m.allow(uid, ip, now=now)
        q.put(("allow", bool(ok)))
    except Exception as exc:  # pragma: no cover - surfaced via assertion below
        q.put(("allow-error", repr(exc)))


def _worker_commit(state_dir, uid, rid, hourly, now, barrier, q):
    os.environ["MACRO_API_STATE_DIR"] = state_dir
    os.environ["RESEARCH_VIEW_HOURLY"] = str(hourly)
    from engine.research_vault import view_ratelimit as m
    barrier.wait(timeout=30)
    try:
        q.put(("commit", bool(m.commit_many(uid, [rid], now=now))))
    except Exception as exc:  # pragma: no cover
        q.put(("commit-error", repr(exc)))


def test_concurrent_allow_and_commit_never_lose_updates(rl, tmp_path):
    cap = 8
    state = str(tmp_path / "state")
    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(12)
    q = ctx.Queue()
    procs = []
    for i in range(6):
        procs.append(ctx.Process(
            target=_worker_allow,
            args=(state, "user-x", f"10.0.0.{i}", cap, NOW, barrier, q)))
        procs.append(ctx.Process(
            target=_worker_commit,
            args=(state, "user-x", f"rep-{i}", cap, NOW, barrier, q)))
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=60)
    assert all(p.exitcode == 0 for p in procs), [p.exitcode for p in procs]

    results = []
    for _ in range(len(procs)):
        results.append(q.get(timeout=30))
    assert q.empty()
    kinds = [k for k, _ in results]
    assert sorted(kinds) == ["allow"] * 6 + ["commit"] * 6  # no worker errored

    wins = sum(1 for _, ok in results if ok)
    wins_allow = sum(1 for k, ok in results if ok and k == "allow")
    wins_commit = sum(1 for k, ok in results if ok and k == "commit")
    assert wins == cap                       # exactly the cap, no lost updates
    assert ucount(rl, "user-x") == cap       # one canonical ledger, exact total

    # every win charged exactly one IP leg: real IPs for allows, the synthetic
    # brain:<uid> mirror for commits
    ip_totals = sum(icount(rl, p.stem.split("vip_")[1].split("_" + PERIOD)[0])
                    for p in rl.glob("vip_*.json"))
    assert ip_totals == wins
    assert icount(rl, mod._brain_ip_hash("user-x")) == wins_commit
    assert wins_allow + wins_commit == wins
    assert not list(rl.glob("*.tmp"))


def test_concurrent_pair_commits_do_not_overcharge(rl, tmp_path):
    cap = 4
    monkey_state = str(tmp_path / "state")
    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(8)
    q = ctx.Queue()
    procs = [ctx.Process(
        target=_worker_commit,
        args=(monkey_state, "user-x", f"r{i}", cap, NOW, barrier, q))
        for i in range(8)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=60)
    assert all(p.exitcode == 0 for p in procs)
    results = [q.get(timeout=30) for _ in range(len(procs))]
    assert sum(1 for _, ok in results if ok) == cap
    assert ucount(rl, "user-x") == cap
    assert not list(rl.glob("*.tmp"))


@pytest.mark.parametrize('raw', [b'{"count":null}', b'{}', b'{"count":4,"count":0}'])
def test_uncertain_canonical_count_is_not_a_fresh_period(rl, raw):
    path = mod._user_file('user-x', PERIOD)
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    assert mod.preflight_many('user-x', ['r1', 'r2'], now=NOW) is False
    assert mod.commit_many('user-x', ['r1', 'r2'], now=NOW) is False
    assert path.read_bytes() == raw


def test_empty_pair_is_not_zero_cost_success(rl):
    with pytest.raises(mod.RateLimitArgError): mod.preflight_many('user-x', [], now=NOW)
    with pytest.raises(mod.RateLimitArgError): mod.commit_many('user-x', [], now=NOW)


def test_ordinary_lock_failure_cannot_overwrite_a_concurrent_commit(rl, monkeypatch):
    seed(mod._user_file('user-x', PERIOD), {'count': 4})
    monkeypatch.setattr(mod, '_acquire_pair_locks', lambda *args: None)
    assert mod.allow('user-x', '1.2.3.4', now=NOW)[0] is True  # legacy availability
    assert ucount(rl, 'user-x') == 4  # no unlocked read-modify-write permitted
    assert not mod._ip_file(mod._hash_ip('1.2.3.4'), PERIOD).exists()


def test_lost_ack_after_whole_canonical_replace_is_confirmed_once(rl, monkeypatch):
    original = mod._write_atomic; user_writes = []
    def lost(path, data):
        original(path, data)
        if path == mod._user_file('user-x', PERIOD):
            user_writes.append(data['count'])
            raise OSError('synthetic lost ack after replace')
    monkeypatch.setattr(mod, '_write_atomic', lost)
    assert mod.commit_many('user-x', ['r1', 'r2'], now=NOW) is True
    assert user_writes == [2] and ucount(rl, 'user-x') == 2


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_nonfinite_lock_timeout_never_disables_deadline(rl, monkeypatch, value):
    monkeypatch.setenv("RESEARCH_VIEW_RL_LOCK_TIMEOUT", value)
    assert mod._lock_timeout() == mod._LOCK_TIMEOUT_DEFAULT


def test_oversized_or_fifo_counter_refuses_without_blocking(rl):
    path = mod._user_file("user-x", PERIOD)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * (mod._MAX_LEDGER_BYTES + 1))
    assert mod.preflight_many("user-x", ["r1"], now=NOW) is False
    path.unlink(); os.mkfifo(path)
    started = time.monotonic()
    assert mod.commit_many("user-x", ["r1"], now=NOW) is False
    assert time.monotonic() - started < 2


def test_comparison_and_web_use_the_same_real_user_budget(configured, rl):
    from engine.research_intelligence import comparison_qualification as q
    from engine.research_vault.comparison_runtime import build_comparison_owners
    from tests.test_research_comparison_qualification import proposal, pair_request
    from tests.test_research_vault_comparison import prepare, compare
    service = configured[0]; store = service._catalog_store
    actor = object(); refs = set()
    authority = q.QualificationAuthority(lambda actual, _: "synthetic-adjudicator" if actual is actor else None,
        lambda ctx, record, ref: ctx.principal_id == "member" and ref in refs)
    ref = q.publish_qualification(store, proposal(configured), actor=actor, authority=authority); refs.add(ref)
    service._comparison_owners = build_comparison_owners(store, authority=authority)
    # Use the service's exact UTC period, not this module's separate fixture time.
    now = service._now(); period = mod._period_key(now)
    assert mod.allow("member", "actual-web-ip", now=now)[0] is True
    prepared = prepare(service); assert prepared["state"] == "INPUTS_ONLY"
    assert compare(service, pair_request(prepared))["state"] == "AVAILABLE"
    assert ucount(rl, "member", period) == 5
    before_reads = len(configured[4]["load"])
    assert prepare(service)["reason"] == "QUOTA_UNAVAILABLE"
    assert len(configured[4]["load"]) == before_reads
    assert mod.allow("member", "another-web-ip", now=now)[0] is False


# Complete-principal keys and conservative legacy compatibility (review repair).
@pytest.mark.parametrize("left,right", [
    ("a" * 64 + "1", "a" * 64 + "2"),
    ("a:b", "a/b"),
    ("a:b", "a_b"),
])
def test_distinct_complete_principals_never_share_budget_or_canonical_lock(rl, left, right):
    assert mod._safe_uid(left) == mod._safe_uid(right)
    assert mod._user_file(left, PERIOD) != mod._user_file(right, PERIOD)
    assert mod._user_lock(left, PERIOD) != mod._user_lock(right, PERIOD)
    # Unsafe principals first: no legacy bucket exists to assign to either.
    assert mod.commit_many(left, ["r1", "r2"], now=NOW) is True
    assert mod.peek(right, "web-right", now=NOW)["remaining"] == 5
    assert mod.allow(left, "web-left", now=NOW)[0] is True
    assert mod.peek(left, "web-left", now=NOW)["remaining"] == 2
    assert mod.commit_many(left, ["r3", "r4"], now=NOW) is True
    assert mod.preflight_many(left, ["r5"], now=NOW) is False
    assert mod.commit_many(right, ["r1", "r2"], now=NOW) is True
    assert ucount(rl, left) == 5 and ucount(rl, right) == 2


@pytest.mark.parametrize("uid", [
    "user-x", "0c1394da-506d-4b7d-b2a5-2b8f185e09a8", "a" * 64,
])
def test_existing_short_safe_counter_and_lock_are_not_migrated_or_reset(rl, uid):
    expected = rl / f"vh_{uid}_{PERIOD}.json"
    assert mod._user_file(uid, PERIOD) == expected
    assert mod._user_lock(uid, PERIOD) == rl / "locks" / f"lku_{uid}_{PERIOD}.lock"
    assert mod._user_lock_paths(uid, PERIOD) == (mod._user_lock(uid, PERIOD),)
    seed(expected, {"count": 3, "retained": "historical metadata"})
    assert mod.peek(uid, "web", now=NOW)["remaining"] == 2
    assert mod.preflight_many(uid, ["r1", "r2"], now=NOW) is True
    assert mod.allow(uid, "web", now=NOW)[0] is True
    assert mod.preflight_many(uid, ["r1", "r2"], now=NOW) is False
    assert mod.commit_many(uid, ["r1"], now=NOW) is True
    assert json.loads(expected.read_text()) == {"count": 5, "retained": "historical metadata"}
    assert mod.commit_many(uid, ["r2"], now=NOW) is False
    assert mod.peek(uid, "different-web-ip", now=NOW)["remaining"] == 0
    assert not list(rl.glob("vh_~*.json"))


@pytest.mark.parametrize("uid", ["x" * 64 + "tail", "reader@example.com"])
def test_ambiguous_old_bucket_refuses_all_paths_without_attribution_or_reset(rl, monkeypatch, uid):
    old = mod._legacy_user_file(uid, PERIOD)
    current = mod._user_file(uid, PERIOD)
    seed(old, {"count": 4, "note": "no owner binding"})
    seed(current, {"count": 1})  # even an existing digest file cannot erase ambiguity
    before = {p: p.read_bytes() for p in rl.glob("*.json")}
    def no_write(*args):
        raise AssertionError("ambiguous counter must never be modified")
    with monkeypatch.context() as patcher:
        patcher.setattr(mod, "_write", no_write)
        patcher.setattr(mod, "_write_atomic", no_write)
        assert mod.preflight_many(uid, ["r1"], now=NOW) is False
        assert mod.commit_many(uid, ["r1"], now=NOW) is False
        assert mod.allow(uid, "web", now=NOW) == (False, {"remaining": 0, "limit": 5})
        assert mod.peek(uid, "web", now=NOW) == {"remaining": 0, "limit": 5}
    assert {p: p.read_bytes() for p in rl.glob("*.json")} == before
    # Normal new-period accounting is not an old-count reset or migration.
    assert mod.commit_many(uid, ["r1", "r2"], now=NEXT_HOUR) is True
    assert all(p.read_bytes() == raw for p, raw in before.items())


@pytest.mark.parametrize("raw", ['{"count":0}', '{"count":null}', '{"count":4}', 'not-json'])
def test_any_present_lossy_legacy_bucket_is_unowned_even_zero(rl, raw):
    uid = "alias:principal"
    old = mod._legacy_user_file(uid, PERIOD)
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_text(raw)
    assert mod.preflight_many(uid, ["r1"], now=NOW) is False
    assert mod.commit_many(uid, ["r1"], now=NOW) is False
    assert not mod._user_file(uid, PERIOD).exists()
    assert old.read_text() == raw


def test_dangling_legacy_symlink_is_present_ambiguity_not_a_fresh_budget(rl):
    uid = "alias:principal"
    old = mod._legacy_user_file(uid, PERIOD)
    old.parent.mkdir(parents=True, exist_ok=True)
    old.symlink_to(rl / "not-present")
    assert mod.commit_many(uid, ["r1"], now=NOW) is False
    assert not mod._user_file(uid, PERIOD).exists()
    assert old.is_symlink()


def test_legacy_guard_lock_excludes_safe_alias_during_hashed_principal_commit(rl, monkeypatch):
    uid = "a:b"
    safe_alias = "a_b"
    canonical = mod._user_lock(uid, PERIOD)
    guard = mod._user_lock(safe_alias, PERIOD)
    assert canonical != guard
    assert set(mod._user_lock_paths(uid, PERIOD)) == {canonical, guard}
    guard.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(guard, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        mod.fcntl.flock(fd, mod.fcntl.LOCK_EX | mod.fcntl.LOCK_NB)
        monkeypatch.setenv("RESEARCH_VIEW_RL_LOCK_TIMEOUT", "0.05")
        assert mod.preflight_many(uid, ["r1"], now=NOW) is True  # advisory only
        assert mod.commit_many(uid, ["r1"], now=NOW) is False
        assert not mod._user_file(uid, PERIOD).exists()
        assert not mod._user_file(safe_alias, PERIOD).exists()
    finally:
        mod.fcntl.flock(fd, mod.fcntl.LOCK_UN)
        os.close(fd)
    assert mod.commit_many(uid, ["r1"], now=NOW) is True
    assert ucount(rl, uid) == 1


@pytest.mark.parametrize("uid", [None, "", "  ", "x" * 257, "\ud800"])
def test_all_entrypoints_validate_the_same_complete_principal_before_io(rl, uid):
    calls = [lambda: mod.allow(uid, "web", now=NOW),
             lambda: mod.peek(uid, "web", now=NOW),
             lambda: mod.preflight_many(uid, ["r1"], now=NOW),
             lambda: mod.commit_many(uid, ["r1"], now=NOW)]
    for call in calls:
        with pytest.raises(mod.RateLimitArgError):
            call()
    assert not rl.exists()
