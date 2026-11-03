"""In-repo tests for the bounded-concurrency ``_processed_index``.

Runs against the REAL ``engine.research_vault`` package: the patched
``ingest._processed_index`` and the sha-bound ``r2_store.R2Store`` with an
injected fake client (R2Store's constructor takes ``client=``). The only
concurrency claim made for the real store is the source-grounded one: ONE
client built before any worker starts, read-only ``get_object`` + independent
``Body.read``, no session creation or client mutation in workers (AWS Boto3
guide: "Multithreading or multiprocessing with clients").

All overlap/ordering synchronization uses conditions and events — never
sleep-ETA. No network, no provider calls, no timing benchmark: every
assertion is a structural/count/order equality.
"""
from __future__ import annotations

import json
import re
import sys
import threading
import time
import types
import unittest

BASELINE_FN = 'def _processed_index(store) -> tuple[set[str], dict[str, str]]:\n    """Read every receipt once → ``(done_pdf_keys, {doc_id: pdf_key})``.\n\n    ``done_pdf_keys`` drives idempotency: a receipt records the source ``pdf_key``\n    it consumed, so we skip re-ingesting that object even if the derived id later\n    shifts.\n\n    The ``{doc_id: pdf_key}`` map is the ONLY way back from a published catalog\n    row to the inbox object it came from — the public catalog carries no source\n    key — and it is what lets :func:`_refresh_sidecars` re-read a sidecar for a\n    document that is already receipted. It costs nothing extra: this pass was\n    already reading every receipt.\n    """\n    done: set[str] = set()\n    by_id: dict[str, str] = {}\n    for rk in store.list_prefix(PROCESSED_PREFIX):\n        if not rk.endswith(".json"):\n            continue\n        raw = store.get_bytes(rk)\n        if not raw:\n            continue\n        try:\n            rec = json.loads(raw)\n            src = rec.get("pdf_key")\n            if src:\n                done.add(src)\n                doc_id = rec.get("id")\n                if doc_id:\n                    by_id[doc_id] = src\n        except Exception:  # noqa: BLE001 — unreadable receipt: fall through\n            continue\n    return done, by_id\n'

INBOX = "research_inbox/"
PROCESSED = "research_inbox/_processed/"

import importlib

from engine.research_vault.r2_store import R2Store  # real, sha-bound store

# The patched function under test, from the real package.
_ingest = importlib.import_module("engine.research_vault.ingest")
new__processed_index = _ingest._processed_index

# Reference copy of the PRE-PATCH serial function (verbatim), exec'd against
# the real module constants, as the exact-semantics baseline.
_ns = {"json": json, "PROCESSED_PREFIX": _ingest.PROCESSED_PREFIX}
exec(compile(BASELINE_FN, "baseline__processed_index", "exec"), _ns)
baseline__processed_index = _ns["_processed_index"]


# ---------------------------------------------------------------------------
# Fakes: deterministic event/condition-synchronized fake boto3 client
# ---------------------------------------------------------------------------


class Boom(BaseException):
    """Deliberately BaseException: R2Store.get_bytes catches ``Exception``
    only, so this is the one escape route that makes the PARALLEL path's
    ordered-error handling observable through an exact-type R2Store."""

    def __init__(self, tag):
        super().__init__(tag)
        self.tag = tag


class FakeBody:
    def __init__(self, payload):
        self._p = payload

    def read(self):
        return self._p


class FakeClient:
    """Thread-safe fake boto3 client: records attempts/completions/method
    names; per-key Events gate returns; per-key Boom instances raise."""

    def __init__(self, order, bodies, gate=None, boom=None, hold=None,
                 missing=()):
        self.order = list(order)
        self.bodies = dict(bodies)
        self.gate = gate
        self.boom = dict(boom or {})
        self.hold = dict(hold or {})
        self.missing = set(missing)
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        self.active = 0
        self.max_active = 0
        self.submitted = 0
        self.finished = 0
        self.max_pending = 0
        self.attempts = []
        self.completions = []
        self.calls = []

    def _enter(self, key):
        with self.cond:
            self.active += 1
            self.submitted += 1
            self.max_active = max(self.max_active, self.active)
            self.max_pending = max(self.max_pending,
                                   self.submitted - self.finished)
            self.attempts.append(key)
            self.calls.append("get_object")
            self.cond.notify_all()

    def _exit(self, key):
        with self.cond:
            self.active -= 1
            self.finished += 1
            self.completions.append(key)
            self.cond.notify_all()

    def wait_submitted(self, n, timeout=10.0):
        with self.cond:
            return self.cond.wait_for(lambda: self.submitted >= n, timeout)

    def wait_finished(self, n, timeout=10.0):
        with self.cond:
            return self.cond.wait_for(lambda: self.finished >= n, timeout)

    def get_object(self, Bucket=None, Key=None):
        self._enter(Key)
        try:
            if self.gate is not None:
                self.gate.enter()
            ev = self.hold.get(Key)
            if ev is not None and not ev.wait(timeout=15.0):
                raise AssertionError("hold for %s never released" % Key)
            b = self.boom.get(Key)
            if b is not None:
                raise b
            if Key in self.missing:
                raise KeyError(Key)
            return {"Body": FakeBody(self.bodies.get(Key))}
        finally:
            self._exit(Key)

    def list_objects_v2(self, Bucket=None, Prefix=None, ContinuationToken=None):
        with self.lock:
            self.calls.append("list_objects_v2")
        keys = [k for k in self.order if k.startswith(Prefix)]
        return {"Contents": [{"Key": k} for k in keys], "IsTruncated": False}


class OverlapGate:
    """Deterministic overlap detector: each read blocks at a cyclic
    ``threading.Barrier`` until ``expected`` reads are simultaneously inside,
    so release slots can never be stolen by stragglers of a previous cycle.
    If the expected overlap never forms, the barrier breaks (bounded wait)
    and every caller proceeds anyway — results stay VALID and the caller
    asserts on ``broken``/``max_active`` — so a serial implementation fails
    fast instead of hanging."""

    def __init__(self, expected, timeout=10.0):
        self._barrier = threading.Barrier(expected, timeout=timeout)
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()

    @property
    def broken(self):
        return self._barrier.broken

    def enter(self):
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            self._barrier.wait()
        except threading.BrokenBarrierError:
            pass
        finally:
            with self.lock:
                self.active -= 1


class DuckStore:
    """Unknown custom store — NOT qualified for concurrent reads."""

    def __init__(self, keys, bodies, hold=None, raiser=None):
        self.keys = list(keys)
        self.bodies = dict(bodies)
        self.hold = dict(hold or {})
        self.raiser = dict(raiser or {})
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        self.active = 0
        self.max_active = 0
        self.reads = []

    def list_prefix(self, prefix):
        return [k for k in self.keys if k.startswith(prefix)]

    def get_bytes(self, key):
        with self.cond:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            self.reads.append(key)
            self.cond.notify_all()
        try:
            ev = self.hold.get(key)
            if ev is not None and not ev.wait(timeout=15.0):
                raise AssertionError("hold never released for %s" % key)
            r = self.raiser.get(key)
            if r is not None:
                raise r
            return self.bodies.get(key)
        finally:
            with self.cond:
                self.active -= 1
                self.cond.notify_all()

    def wait_reads(self, n, timeout=10.0):
        with self.cond:
            return self.cond.wait_for(lambda: len(self.reads) >= n, timeout)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def j(obj):
    return json.dumps(obj).encode()


def weird_spec():
    """16 .json receipts (4 full gate cycles) + hostile extras: missing/
    empty/malformed/non-JSON/duplicate pdf_key/duplicate doc_id/id-less/
    pdf_key-less/non-string truthy pdf_key and id/json list+str+null."""
    order, bodies, missing = [], {}, set()
    spec = [
        ("r01", j({"pdf_key": "inbox/p01.pdf", "id": "doc-a"})),
        ("r02", j({"pdf_key": "inbox/p02.pdf"})),
        ("r03", j({"id": "doc-c"})),
        ("r04", b"{not-json"),
        ("r05", b""),
        ("r06", None),
        ("r07", j({"pdf_key": "inbox/p07.pdf", "id": "doc-07"})),
        ("r08", j({"pdf_key": 123})),
        ("r09", b"[1, 2]"),
        ("r10", b'"x"'),
        ("r11", b"null"),
        ("r12", j({"pdf_key": "inbox/p12.pdf", "id": 123})),
        ("r13", j({"pdf_key": "inbox/p13.pdf", "id": "doc-dup"})),
        ("r14", j({"pdf_key": "inbox/p14.pdf", "id": "doc-dup"})),
        ("r15", j({"pdf_key": "inbox/p01.pdf", "id": "doc-e"})),
        ("r16", j({"pdf_key": "inbox/p16.pdf", "id": "doc-a"})),
    ]
    for suffix, body in spec:
        key = PROCESSED + suffix + ".json"
        order.append(key)
        if body is None:
            missing.add(key)
        else:
            bodies[key] = body
    order.append(PROCESSED + "notes.txt")          # non-.json: never read
    bodies[PROCESSED + "notes.txt"] = b"hello"
    order.append(INBOX + "p01.pdf")                # outside prefix: never read
    bodies[INBOX + "p01.pdf"] = b"%PDF-1.4"
    return order, bodies, missing


EXPECTED_WEIRD = (
    {"inbox/p01.pdf", "inbox/p02.pdf", 123, "inbox/p07.pdf",
     "inbox/p12.pdf", "inbox/p13.pdf", "inbox/p14.pdf",
     "inbox/p16.pdf"},
    {"doc-a": "inbox/p16.pdf", 123: "inbox/p12.pdf",
     "doc-dup": "inbox/p14.pdf", "doc-07": "inbox/p07.pdf",
     "doc-e": "inbox/p01.pdf"},
)


def simple_keys(n):
    return [PROCESSED + "r%02d.json" % i for i in range(1, n + 1)]


def simple_bodies(order):
    return {key: j({"pdf_key": "inbox/p%02d.pdf" % i, "id": "doc-%02d" % i})
            for i, key in enumerate(order, 1)}


def r2_with(order, bodies, **kw):
    client = FakeClient(order, bodies, **kw)
    # Emulate the ordinary constructor factory, preserving provenance semantics.
    from unittest.mock import patch
    with patch("engine.research_vault.r2_store._r2_client", return_value=client):
        store = R2Store("research-vault")
    return store, client


def key_of(i):
    return PROCESSED + "r%02d.json" % i


def release_all_pending(recorder, keys, wait_n=None):
    """Director body: wait until ``wait_n`` (default: all of ``keys``) reads
    are pending, then release the per-key holds in the given order, each step
    gated on the completion counter — never on sleep."""
    ok = recorder.wait_submitted(wait_n or len(keys))
    try:
        done = 0
        for k in keys:
            if not ok:
                break
            ev = recorder.hold.get(k)
            if ev is not None:
                ev.set()
            done += 1
            if done < len(keys):
                ok = recorder.wait_finished(done)
    finally:
        for ev in recorder.hold.values():
            ev.set()


def release_incremental(recorder, keys):
    """Director body for serial-expected runs: release hold k as soon as k
    reads have started, so a strictly serial pass never stalls."""
    try:
        done = 0
        for k in keys:
            recorder.wait_reads(done + 1)
            ev = recorder.hold.get(k)
            if ev is not None:
                ev.set()
            done += 1
    finally:
        for ev in recorder.hold.values():
            ev.set()


def direct(mode, recorder, keys, wait_n=None):
    if mode == "incremental":
        fn, args = release_incremental, (recorder, keys)
    else:
        fn, args = release_all_pending, (recorder, keys, wait_n)
    t = threading.Thread(target=fn, args=args, name="director", daemon=True)
    t.start()
    return t


def settle_threads(baseline_names, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        cur = {t.name for t in threading.enumerate()}
        if not any(n.startswith("rv-receipt") for n in cur - baseline_names):
            return True
        time.sleep(0.01)
    return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestExactSemantics(unittest.TestCase):
    def test_matches_serial_baseline_on_hostile_fixture(self):
        order, bodies, missing = weird_spec()
        gate = OverlapGate(expected=4)
        store, client = r2_with(order, bodies, gate=gate, missing=missing)
        self.assertEqual(new__processed_index(store), EXPECTED_WEIRD)
        base_store, _ = r2_with(order, bodies, missing=missing)
        self.assertEqual(baseline__processed_index(base_store),
                         EXPECTED_WEIRD)
        self.assertFalse(gate.broken)
        self.assertGreaterEqual(gate.max_active, 2)    # real overlap happened
        self.assertLessEqual(client.max_active, 4)
        self.assertLessEqual(client.max_pending, 4)    # finite window held
        self.assertNotIn(PROCESSED + "notes.txt", client.attempts)
        self.assertNotIn(INBOX + "p01.pdf", client.attempts)

    def test_out_of_order_completion_duplicate_winner(self):
        order = simple_keys(4)
        bodies = simple_bodies(order)
        bodies[key_of(3)] = j({"pdf_key": "inbox/p03.pdf", "id": "doc-01"})
        hold = {k: threading.Event() for k in order}
        store, client = r2_with(order, bodies, hold=hold)
        t = direct("pending", client, list(reversed(order)))
        try:
            got = new__processed_index(store)
        finally:
            for ev in hold.values():
                ev.set()
            t.join(timeout=5)
        base_store, _ = r2_with(order, bodies)
        self.assertEqual(baseline__processed_index(base_store), got)
        self.assertEqual(got[1]["doc-01"], "inbox/p03.pdf")  # list-order wins
        self.assertEqual(client.completions, list(reversed(order)))
        self.assertEqual(client.attempts, order)

    def test_ordered_first_exception_not_first_finished(self):
        order = simple_keys(8)
        bodies = simple_bodies(order)
        hold = {key_of(3): threading.Event()}
        # position 2 (key_of(3)) is held until every windowed submission has
        # happened; position 4 (key_of(5)) fails instantly. "First finished"
        # would be Boom("four"); "first in list order" is Boom("two").
        store, client = r2_with(
            order, bodies, hold=hold,
            boom={key_of(3): Boom("two"), key_of(5): Boom("four")})
        t = direct("pending-until", client, [key_of(3)], wait_n=6)
        try:
            with self.assertRaises(Boom) as ctx:
                new__processed_index(store)
        finally:
            for ev in hold.values():
                ev.set()
            t.join(timeout=5)
        self.assertEqual(ctx.exception.tag, "two")     # list order wins
        self.assertEqual(client.submitted, 6)          # indices 0..5, no 6/7
        self.assertEqual(len(client.attempts), 6)
        self.assertEqual(client.attempts.count(key_of(3)), 1)  # no replay
        self.assertEqual(client.attempts.count(key_of(5)), 1)
        self.assertEqual(sorted(client.attempts), sorted(order[:6]))

    def test_error_bounds_launches_and_absorbs_nothing_after_failure(self):
        order = simple_keys(6)
        bodies = simple_bodies(order)
        store, client = r2_with(order, bodies,
                                boom={key_of(1): Boom("one")})
        with self.assertRaises(Boom):
            new__processed_index(store)
        self.assertEqual(client.attempts[0], key_of(1))
        self.assertLessEqual(len(client.attempts), 4)  # window bound held
        self.assertNotIn(key_of(5), client.attempts)   # nothing past window
        self.assertNotIn(key_of(6), client.attempts)

    def test_serial_path_get_bytes_exception_propagates_in_order(self):
        keys = simple_keys(3)
        bodies = simple_bodies(keys)
        reads = []

        class RaisingDuck(DuckStore):
            def get_bytes(self, key):
                reads.append(key)
                if key == keys[1]:
                    raise ValueError("store refused")
                return self.bodies.get(key)

        store = RaisingDuck(keys, bodies)
        with self.assertRaises(ValueError):
            new__processed_index(store)
        self.assertEqual(reads, keys[:2])              # stop at first raise

    def test_list_prefix_raising_iterator_propagates(self):
        keys = simple_keys(4)

        class BadList(DuckStore):
            def list_prefix(self, prefix):
                yield keys[0]
                yield keys[1]
                raise RuntimeError("list blew up mid-iteration")

        store = BadList(keys, simple_bodies(keys))
        with self.assertRaises(RuntimeError):
            new__processed_index(store)
        self.assertEqual(store.reads, keys[:2])

    def test_empty_prefix_and_all_nonjson(self):
        store, _ = r2_with([], {})
        self.assertEqual(new__processed_index(store), (set(), {}))
        order = [PROCESSED + "a.txt", PROCESSED + "b.PDF"]
        store2, client2 = r2_with(order, {order[0]: b"x", order[1]: b"y"})
        self.assertEqual(new__processed_index(store2), (set(), {}))
        self.assertEqual(client2.attempts, [])         # non-json never read

    def test_concurrency_one_is_the_exact_serial_pass(self):
        order, bodies, missing = weird_spec()
        gate = OverlapGate(expected=2, timeout=4.0)
        store, client = r2_with(order, bodies, gate=gate, missing=missing)
        self.assertEqual(new__processed_index(store, concurrency=1),
                         EXPECTED_WEIRD)
        self.assertTrue(gate.broken)                   # could never overlap
        self.assertEqual(gate.max_active, 1)           # strictly serial
        self.assertLessEqual(client.max_pending, 1)

    def test_unknown_duck_store_stays_serial_by_default(self):
        order = simple_keys(6)
        bodies = simple_bodies(order)
        hold = {k: threading.Event() for k in order}
        store = DuckStore(order, bodies, hold=hold)
        t = direct("incremental", store, order)
        try:
            got = new__processed_index(store)          # default concurrency
        finally:
            for ev in hold.values():
                ev.set()
            t.join(timeout=5)
        self.assertEqual(got, baseline__processed_index(DuckStore(order,
                                                                  bodies)))
        self.assertEqual(store.max_active, 1)          # never parallelized
        self.assertEqual(store.reads, order)           # strict list order


class TestBoundedWindowAndHygiene(unittest.TestCase):
    def test_window_never_exceeds_four(self):
        order = simple_keys(12)
        bodies = simple_bodies(order)
        gate = OverlapGate(expected=4)
        store, client = r2_with(order, bodies, gate=gate)
        got = new__processed_index(store)
        base_store, _ = r2_with(order, bodies)
        self.assertEqual(got, baseline__processed_index(base_store))
        self.assertFalse(gate.broken)
        self.assertEqual(gate.max_active, 4)
        self.assertLessEqual(client.max_active, 4)
        self.assertLessEqual(client.max_pending, 4)

    def test_no_writes_and_threads_settle(self):
        order = simple_keys(8)
        bodies = simple_bodies(order)
        before = {t.name for t in threading.enumerate()}
        store, client = r2_with(order, bodies)
        new__processed_index(store)
        self.assertTrue(settle_threads(before))
        self.assertEqual(set(client.calls),
                         {"get_object", "list_objects_v2"})
        self.assertIsNone(store.last_put_error)
        # every launched read settled exactly once (multiset, any order)
        self.assertEqual(sorted(client.completions), sorted(client.attempts))

    def test_threads_settle_after_error(self):
        order = simple_keys(8)
        bodies = simple_bodies(order)
        hold = {key_of(3): threading.Event()}
        store, client = r2_with(order, bodies, hold=hold,
                                boom={key_of(3): Boom("two")})
        before = {t.name for t in threading.enumerate()}
        t = direct("pending-until", client, [key_of(3)], wait_n=6)
        try:
            with self.assertRaises(Boom):
                new__processed_index(store)
        finally:
            for ev in hold.values():
                ev.set()
            t.join(timeout=5)
        self.assertTrue(settle_threads(before))
        self.assertEqual(sorted(client.completions),
                         sorted(client.attempts))


class TestPatchIntegrity(unittest.TestCase):
    def test_real_function_signature(self):
        import inspect
        sig = inspect.signature(new__processed_index)
        self.assertEqual(list(sig.parameters), ["store", "concurrency", "read_cache"])
        self.assertTrue(sig.parameters["concurrency"].kind is
                        inspect.Parameter.KEYWORD_ONLY)
        self.assertEqual(sig.parameters["concurrency"].default, 4)
        self.assertIs(sig.parameters['read_cache'].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertIsNone(sig.parameters['read_cache'].default)

    def test_real_r2store_qualifies_and_duck_store_does_not(self):
        order = simple_keys(4)
        bodies = simple_bodies(order)
        gate = OverlapGate(expected=2)
        store, client = r2_with(order, bodies, gate=gate)
        new__processed_index(store)
        self.assertFalse(gate.broken)
        self.assertGreaterEqual(gate.max_active, 2)   # real concurrency
        duck = DuckStore(order, bodies)
        got = new__processed_index(duck)              # default concurrency
        self.assertEqual(got, baseline__processed_index(
            DuckStore(order, bodies)))
        self.assertEqual(duck.max_active, 1)          # stayed serial


if __name__ == "__main__":
    unittest.main(verbosity=2)


def test_injected_exact_r2store_retains_serial_semantics():
    order = simple_keys(12)
    bodies = simple_bodies(order)
    client = FakeClient(order, bodies)
    store = R2Store("research-vault", client=client)
    assert store._receipt_reads_thread_safe is False
    assert _ingest._receipt_read_workers(store, 4) == 1
    assert new__processed_index(store) == baseline__processed_index(R2Store("research-vault", client=FakeClient(order, bodies)))
    assert client.max_active == 1
    assert client.attempts == order


def test_ordinary_factory_concurrency_cannot_exceed_four():
    order = simple_keys(12)
    store, client = r2_with(order, simple_bodies(order), gate=OverlapGate(4))
    assert store._receipt_reads_thread_safe is True
    assert _ingest._receipt_read_workers(store, 1000) == 4
    assert new__processed_index(store, concurrency=1000) == baseline__processed_index(R2Store("research-vault", client=FakeClient(order, simple_bodies(order))))
    assert client.max_active == 4
    assert client.max_pending <= 4
