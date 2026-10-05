"""Concurrency proof for the Elements subscription lane (app/billing.py).

The sibling suite tests/test_billing_subscribe.py already covers the SEQUENTIAL double-subscribe:
a second /complete arriving AFTER a first subscription exists is refused 409 by the
_has_live_subscription guard. That guard is a check, and the create is a separate write, so it
says nothing about two requests that are in flight at the same time:

    A: list subscriptions -> none
    B: list subscriptions -> none        <- both crossed the guard before either wrote
    A: Subscription.create               -> sub_1
    B: Subscription.create               -> sub_2   (the double charge)

These tests reproduce that interleaving DETERMINISTICALLY with a threading.Barrier planted in
the fake's Subscription.list, so both requests are forced to finish the guard read before either
is allowed to create. Nothing here sleeps to "hope for" a race.

The fake Stripe account implements the DOCUMENTED idempotency contract, so what is being proved
is the app's behavior under Stripe's real semantics rather than under a convenient stub:

  * a key whose request is still executing is refused, and NOTHING is saved for it
    ("the request conflicts with another request that's executing concurrently, we don't save
    the idempotent result... You can retry these requests" -- docs.stripe.com/api/idempotent_requests);
  * a key that already has a saved result REPLAYS that result instead of executing again;
  * a key replayed with different parameters raises `idempotency_error`
    ("re-used on a request that does not match the first request's API endpoint and parameters"
    -- docs.stripe.com/api/errors);
  * no key at all means no deduplication -- which is what makes the pre-fix RED reproduction
    produce two subscriptions.

Run:
    python -m pytest tests/test_billing_subscribe_concurrency.py -v
"""
from __future__ import annotations

import threading
import types

import pytest
from fastapi import HTTPException

from app import billing

USER = {"id": "user_1", "email": "buyer@example.com"}
OTHER_USER = {"id": "user_2", "email": "second@example.com"}


# --------------------------------------------------------------------------- #
# A Stripe double that honours the documented idempotency contract
# --------------------------------------------------------------------------- #
class _StripeConflict(Exception):
    """Same key, request still executing. Stripe saves nothing; the caller may retry."""

    http_status = 409


class _IdempotencyMismatch(Exception):
    """Same key, different parameters -- Stripe's `idempotency_error`."""

    def __init__(self):
        super().__init__("Keys for idempotent requests can only be used with the same parameters")
        self.error = types.SimpleNamespace(type="idempotency_error")


class _ListResp:
    def __init__(self, data):
        self.data = data


class _FakeAccount:
    """One Stripe account shared by every concurrent 'request' in a test."""

    def __init__(self, *, si_by_id=None, existing=None, hold_inflight=False):
        self.subs: list = list(existing or [])
        self.create_calls: list[dict] = []
        self.cancelled: list[str] = []
        self._idem: dict[str, dict] = {}       # key -> {"done": bool, "params": ..., "result": ...}
        self._lock = threading.RLock()
        self._si = si_by_id or {}
        self._barrier: threading.Barrier | None = None
        self._barrier_seen: set[int] = set()
        self._hold_inflight = hold_inflight     # leave the first key marked in-flight (no result)
        self._seq = 0
        self.list_calls = 0

        outer = self

        class _SetupIntent:
            @staticmethod
            def retrieve(sid):
                return outer._si[sid]

        class _Subscription:
            @staticmethod
            def list(**kw):
                # Snapshot FIRST, then wait: the barrier must not release until every racer is
                # holding its guard read, or the "race" degenerates into one request finishing
                # before the other looks. This is what makes the reproduction deterministic
                # rather than a sleep-and-hope.
                with outer._lock:
                    outer.list_calls += 1
                    snapshot = list(outer.subs)
                outer._maybe_wait_barrier()
                return _ListResp(snapshot)

            @staticmethod
            def create(**kw):
                return outer._create(kw)

            @staticmethod
            def cancel(sub_id):
                with outer._lock:
                    outer.cancelled.append(sub_id)
                    outer.subs = [s for s in outer.subs if s.id != sub_id]

        self.SetupIntent = _SetupIntent
        self.Subscription = _Subscription

    # -- race control ------------------------------------------------------- #
    def arm_barrier(self, parties: int) -> None:
        """Force the first `parties` threads to finish their guard READ before any may create."""
        self._barrier = threading.Barrier(parties, timeout=10)

    def _maybe_wait_barrier(self) -> None:
        b = self._barrier
        if b is None:
            return
        ident = threading.get_ident()
        with self._lock:
            if ident in self._barrier_seen:
                return                      # each thread waits once, on its guard read only
            self._barrier_seen.add(ident)
        b.wait()

    # -- the idempotency contract ------------------------------------------- #
    @staticmethod
    def _params(kw: dict) -> str:
        return repr(sorted((k, repr(v)) for k, v in kw.items()))

    def _create(self, kw: dict):
        key = kw.pop("idempotency_key", None)
        params = self._params(kw)
        with self._lock:
            if key is not None:
                entry = self._idem.get(key)
                if entry is not None:
                    if not entry["done"]:
                        raise _StripeConflict("request with this key is already executing")
                    if entry["params"] != params:
                        raise _IdempotencyMismatch()
                    return entry["result"]          # replay -- no second subscription
                self._idem[key] = {"done": False, "params": params, "result": None}

            self.create_calls.append(dict(kw))
            self._seq += 1
            sub = types.SimpleNamespace(
                id=f"sub_{self._seq}",
                status="trialing" if kw.get("trial_period_days") else "active",
                trial_end=1900000000 if kw.get("trial_period_days") else None,
                created=1_700_000_000,
            )
            self.subs.append(sub)
            if key is not None and not self._hold_inflight:
                self._idem[key] = {"done": True, "params": params, "result": sub}
            return sub


def _si(customer="cus_1", pm="pm_777", sid="seti_abc", metadata=None):
    return types.SimpleNamespace(
        id=sid, status="succeeded", customer=customer, payment_method=pm,
        metadata=metadata or {})


def _sub_row(sub_id, status="active", created=1_700_000_000):
    return types.SimpleNamespace(id=sub_id, status=status, created=created, trial_end=None)


@pytest.fixture()
def wired(monkeypatch):
    """Patch away everything the route touches except Stripe itself."""
    monkeypatch.setattr(billing, "_price_id", lambda lk: f"price_{lk}")
    monkeypatch.setattr(billing, "_compute_entitlement",
                        lambda cid: {"tier": "pro", "status": "trialing",
                                     "current_period_end": None, "features": []})
    monkeypatch.setattr(billing, "_upsert_entitlement", lambda *a, **k: None)
    monkeypatch.setattr(billing, "_invalidate", lambda *a, **k: None)
    monkeypatch.setattr(billing, "_IDEMPOTENCY_RETRY_DELAYS_SEC", (0.01, 0.02), raising=False)
    # No test here buys an offer; without this the grandfathered-offer probe reaches for
    # stripe.Customer on doubles that only model the Subscription surface.
    monkeypatch.setattr(billing, "_customer_offer_entitled", lambda cid, key: False)
    return monkeypatch


def _body(sid="seti_abc", tier="pro", interval="monthly", offer=None):
    return billing.SubscribeCompleteRequest(
        setup_intent_id=sid, tier=tier, interval=interval, offer=offer)


def _run_concurrently(fns):
    """Run callables in threads; return (results, exceptions) positionally."""
    results: list = [None] * len(fns)
    errors: list = [None] * len(fns)

    def _wrap(i, fn):
        try:
            results[i] = fn()
        except BaseException as exc:            # noqa: BLE001 -- recorded for assertions
            errors[i] = exc

    threads = [threading.Thread(target=_wrap, args=(i, fn)) for i, fn in enumerate(fns)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)
    assert not any(t.is_alive() for t in threads), "a completion thread deadlocked"
    return results, errors


# --------------------------------------------------------------------------- #
# 1. the race itself: two requests cross the live-sub check before either creates
# --------------------------------------------------------------------------- #
def test_two_concurrent_completions_create_exactly_one_subscription(wired):
    """THE defect. Both threads are held at the guard read until the other has finished it, so
    both provably see 'no live subscription' before either writes. Exactly one subscription may
    exist afterwards."""
    acct = _FakeAccount(si_by_id={"seti_abc": _si()})
    acct.arm_barrier(2)
    wired.setattr(billing, "_stripe", lambda: acct)
    wired.setattr(billing, "_existing_customer", lambda uid: "cus_1")

    results, errors = _run_concurrently([
        lambda: billing.subscribe_complete(_body(), user=USER),
        lambda: billing.subscribe_complete(_body(), user=USER),
    ])

    assert len(acct.create_calls) == 1, (
        f"expected ONE Subscription.create, got {len(acct.create_calls)} -- "
        "the check-then-create window is still open")
    assert len(acct.subs) == 1

    # One logical checkout: both callers are told about the SAME subscription, or the loser is
    # honestly refused 409. Neither may be told it created a second one.
    ok = [r for r in results if r]
    assert ok, f"both completions failed: {errors}"
    assert {r["subscription_id"] for r in ok} == {"sub_1"}
    for err in (e for e in errors if e is not None):
        assert isinstance(err, HTTPException) and err.status_code == 409


def test_idempotency_key_is_the_setup_intent_checkout_identity(wired):
    """Asserted LITERALLY, like the sibling suite's create kwargs: the dedupe identity is the
    canonical checkout identity, not a fresh random value (which would dedupe nothing)."""
    acct = _FakeAccount(si_by_id={"seti_abc": _si()})
    seen: dict = {}
    real_create = acct.Subscription.create

    def _spy(**kw):
        seen.update(kw)
        return real_create(**kw)

    acct.Subscription.create = _spy
    wired.setattr(billing, "_stripe", lambda: acct)
    wired.setattr(billing, "_existing_customer", lambda uid: "cus_1")

    billing.subscribe_complete(_body(), user=USER)
    assert seen["idempotency_key"] == "mm_sub_create:v1:seti_abc"


def test_key_prefers_the_stripe_echoed_id_over_the_client_string(wired):
    """A client that sends the id with stray whitespace must not mint a second key (and so a
    second subscription) for the same checkout."""
    acct = _FakeAccount(si_by_id={" seti_abc ": _si(sid="seti_abc")})
    seen: dict = {}
    real_create = acct.Subscription.create
    acct.Subscription.create = lambda **kw: (seen.update(kw), real_create(**kw))[1]
    wired.setattr(billing, "_stripe", lambda: acct)
    wired.setattr(billing, "_existing_customer", lambda uid: "cus_1")

    billing.subscribe_complete(_body(sid=" seti_abc "), user=USER)
    assert seen["idempotency_key"] == "mm_sub_create:v1:seti_abc"


# --------------------------------------------------------------------------- #
# 2. same-request retry / SetupIntent replay
# --------------------------------------------------------------------------- #
def test_same_request_retried_replays_one_subscription(wired):
    """A transport retry (or an impatient second click) re-sends the same SetupIntent. The second
    call must replay the first result, not create again. Note the live-sub guard is bypassed here
    on purpose -- `subs` is not repopulated -- so the KEY is what is under test, not the guard."""
    acct = _FakeAccount(si_by_id={"seti_abc": _si()})
    wired.setattr(billing, "_stripe", lambda: acct)
    wired.setattr(billing, "_existing_customer", lambda uid: "cus_1")
    wired.setattr(billing, "_has_live_subscription", lambda cid: False)   # isolate the key
    wired.setattr(billing, "_live_subscriptions", lambda cid: [])

    first = billing.subscribe_complete(_body(), user=USER)
    second = billing.subscribe_complete(_body(), user=USER)

    assert len(acct.create_calls) == 1
    assert first["subscription_id"] == second["subscription_id"] == "sub_1"


def test_setup_intent_replayed_after_the_key_expires_is_refused_by_the_guard(wired):
    """Past Stripe's >=24h retention the key no longer dedupes -- so the guard must still hold.
    Modelled by a fresh account (empty key registry) that already carries the live subscription."""
    acct = _FakeAccount(si_by_id={"seti_abc": _si()}, existing=[_sub_row("sub_old", "active")])
    wired.setattr(billing, "_stripe", lambda: acct)
    wired.setattr(billing, "_existing_customer", lambda uid: "cus_1")

    with pytest.raises(HTTPException) as ei:
        billing.subscribe_complete(_body(), user=USER)
    assert ei.value.status_code == 409 and ei.value.detail == "already subscribed"
    assert acct.create_calls == []


def test_replay_with_different_parameters_is_refused_not_duplicated(wired):
    """Same checkout identity, different purchase -- Stripe raises `idempotency_error`. The route
    must convert that into an honest refusal, never a second subscription."""
    acct = _FakeAccount(si_by_id={"seti_abc": _si()})
    wired.setattr(billing, "_stripe", lambda: acct)
    wired.setattr(billing, "_existing_customer", lambda uid: "cus_1")

    billing.subscribe_complete(_body(tier="pro", interval="monthly"), user=USER)
    with pytest.raises(HTTPException) as ei:
        billing.subscribe_complete(_body(tier="pro", interval="annual"), user=USER)

    assert ei.value.status_code == 409            # the live sub is there -> honest 409
    assert len(acct.create_calls) == 1


# --------------------------------------------------------------------------- #
# 3. in-flight conflict: Stripe saves nothing, the loser retries
# --------------------------------------------------------------------------- #
def test_inflight_key_conflict_is_retried_until_the_winner_is_replayed(wired):
    """Stripe refuses a key that is still executing WITHOUT saving a result. The loser has to come
    back for the winner's cached response -- otherwise a real race surfaces as a 502."""
    acct = _FakeAccount(si_by_id={"seti_abc": _si()})
    calls = {"n": 0}
    real_create = acct.Subscription.create

    def _flaky(**kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise _StripeConflict("already executing")
        return real_create(**kw)

    acct.Subscription.create = _flaky
    wired.setattr(billing, "_stripe", lambda: acct)
    wired.setattr(billing, "_existing_customer", lambda uid: "cus_1")

    out = billing.subscribe_complete(_body(), user=USER)
    assert calls["n"] == 2 and out["subscription_id"] == "sub_1"


def test_persistent_inflight_conflict_ends_as_409_not_a_duplicate(wired):
    """If the conflict never clears, the caller is refused. What must NOT happen is a retry that
    drops the key and creates a second subscription."""
    acct = _FakeAccount(si_by_id={"seti_abc": _si()}, existing=[])

    def _always_conflict(**kw):
        acct.subs.append(_sub_row("sub_winner", "trialing"))   # the winner landed meanwhile
        raise _StripeConflict("still executing")

    acct.Subscription.create = _always_conflict
    wired.setattr(billing, "_stripe", lambda: acct)
    wired.setattr(billing, "_existing_customer", lambda uid: "cus_1")

    with pytest.raises(HTTPException) as ei:
        billing.subscribe_complete(_body(), user=USER)
    assert ei.value.status_code == 409
    assert acct.create_calls == []


# --------------------------------------------------------------------------- #
# 4. failed create followed by a retry
# --------------------------------------------------------------------------- #
def test_failed_create_then_successful_retry_yields_one_subscription(wired):
    """A genuine Stripe failure still reports 502 -- and the client's retry must then succeed
    exactly once, not compound into two subscriptions."""
    acct = _FakeAccount(si_by_id={"seti_abc": _si()})
    calls = {"n": 0}
    real_create = acct.Subscription.create

    def _boom_once(**kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("stripe 500")
        return real_create(**kw)

    acct.Subscription.create = _boom_once
    wired.setattr(billing, "_stripe", lambda: acct)
    wired.setattr(billing, "_existing_customer", lambda uid: "cus_1")

    with pytest.raises(HTTPException) as ei:
        billing.subscribe_complete(_body(), user=USER)
    assert ei.value.status_code == 502

    out = billing.subscribe_complete(_body(), user=USER)
    assert out["subscription_id"] == "sub_1"
    assert len(acct.create_calls) == 1


def test_failed_create_converges_to_409_when_a_racer_already_won(wired):
    """Losing the race must not be reported as 'try again' -- that invites the client to retry
    into a duplicate. If the customer is live by the time we fail, the answer is 409."""
    acct = _FakeAccount(si_by_id={"seti_abc": _si()})

    def _lose(**kw):
        acct.subs.append(_sub_row("sub_winner", "trialing"))
        raise RuntimeError("stripe 500")

    acct.Subscription.create = _lose
    wired.setattr(billing, "_stripe", lambda: acct)
    wired.setattr(billing, "_existing_customer", lambda uid: "cus_1")

    with pytest.raises(HTTPException) as ei:
        billing.subscribe_complete(_body(), user=USER)
    assert ei.value.status_code == 409 and ei.value.detail == "already subscribed"


# --------------------------------------------------------------------------- #
# 5. different users must not collide
# --------------------------------------------------------------------------- #
def test_two_different_users_each_get_their_own_subscription(wired):
    """The key is per-SetupIntent and a SetupIntent is server-verified against ONE customer, so
    two users completing at the same instant must both succeed."""
    acct = _FakeAccount(si_by_id={
        "seti_a": _si(customer="cus_1", sid="seti_a"),
        "seti_b": _si(customer="cus_2", sid="seti_b"),
    })
    acct.arm_barrier(2)
    wired.setattr(billing, "_stripe", lambda: acct)
    wired.setattr(billing, "_existing_customer",
                  lambda uid: {"user_1": "cus_1", "user_2": "cus_2"}[uid])
    # each customer sees only their own rows
    wired.setattr(billing, "_has_live_subscription", lambda cid: False)
    wired.setattr(billing, "_live_subscriptions", lambda cid: [])

    results, errors = _run_concurrently([
        lambda: billing.subscribe_complete(_body(sid="seti_a"), user=USER),
        lambda: billing.subscribe_complete(_body(sid="seti_b"), user=OTHER_USER),
    ])

    assert errors == [None, None], errors
    assert len(acct.create_calls) == 2
    assert results[0]["subscription_id"] != results[1]["subscription_id"]
    assert {c["customer"] for c in acct.create_calls} == {"cus_1", "cus_2"}


def test_a_setup_intent_belonging_to_another_customer_is_still_refused(wired):
    """The key can only be as trustworthy as the identity behind it: a borrowed SetupIntent is
    rejected before any create, so one user can never consume another's checkout identity."""
    acct = _FakeAccount(si_by_id={"seti_a": _si(customer="cus_OTHER", sid="seti_a")})
    wired.setattr(billing, "_stripe", lambda: acct)
    wired.setattr(billing, "_existing_customer", lambda uid: "cus_1")

    with pytest.raises(HTTPException) as ei:
        billing.subscribe_complete(_body(sid="seti_a"), user=USER)
    assert ei.value.status_code == 400
    assert acct.create_calls == []


# --------------------------------------------------------------------------- #
# 6. a SECOND checkout identity: two tabs that each ran /subscribe/init
# --------------------------------------------------------------------------- #
def test_two_distinct_setup_intents_leave_exactly_one_live_subscription(wired):
    """Two tabs that each ran /init hold DIFFERENT SetupIntents -- different Stripe request
    identities that no idempotency key can merge. Both creates land, so the loser must stand its
    own row down. Exactly one live subscription may survive, and the loser is told 409."""
    acct = _FakeAccount(si_by_id={
        "seti_a": _si(sid="seti_a"),
        "seti_b": _si(sid="seti_b"),
    })
    acct.arm_barrier(2)
    wired.setattr(billing, "_stripe", lambda: acct)
    wired.setattr(billing, "_existing_customer", lambda uid: "cus_1")

    results, errors = _run_concurrently([
        lambda: billing.subscribe_complete(_body(sid="seti_a"), user=USER),
        lambda: billing.subscribe_complete(_body(sid="seti_b"), user=USER),
    ])

    assert [type(e).__name__ for e in errors if e] in ([], ["HTTPException"]), errors
    assert len(acct.create_calls) == 2, f"both tabs should create: {acct.create_calls}"
    assert len(acct.subs) == 1, f"expected one surviving subscription, got {acct.subs}"
    assert len(acct.cancelled) == 1
    survivors = [r for r in results if r]
    assert len(survivors) == 1
    assert survivors[0]["subscription_id"] == acct.subs[0].id
    refusals = [e for e in errors if e is not None]
    assert len(refusals) == 1
    assert isinstance(refusals[0], HTTPException) and refusals[0].status_code == 409


def test_an_already_billed_duplicate_is_kept_not_silently_cancelled(wired, caplog):
    """A plans.yml `trial_days: 0` tier bills at creation. Cancelling that row would strand a paid
    invoice, so the duplicate is KEPT and reported for reconciliation -- refunding is not this
    route's decision to make."""
    ours = _sub_row("sub_z", status="active", created=1_700_000_500)     # newer, already billed
    theirs = _sub_row("sub_a", status="active", created=1_700_000_000)   # older winner
    wired.setattr(billing, "_stripe", lambda: types.SimpleNamespace(
        Subscription=types.SimpleNamespace(cancel=lambda sid: pytest.fail("must not cancel"))))
    wired.setattr(billing, "_live_subscriptions", lambda cid: [ours, theirs])

    with caplog.at_level("ERROR"):
        stood_down = billing._converge_duplicate_subscription(ours, "cus_1", "user_1")

    assert stood_down is False
    assert "manual reconciliation" in caplog.text


def test_the_older_row_never_cancels_itself(wired):
    """Symmetry check: both racers run the same rule, so exactly one of them elects to stand down.
    The winner must leave the loser's row alone -- a request only ever cancels what it created."""
    ours = _sub_row("sub_a", status="trialing", created=1_700_000_000)
    theirs = _sub_row("sub_z", status="trialing", created=1_700_000_500)
    wired.setattr(billing, "_stripe", lambda: types.SimpleNamespace(
        Subscription=types.SimpleNamespace(cancel=lambda sid: pytest.fail("must not cancel"))))
    wired.setattr(billing, "_live_subscriptions", lambda cid: [ours, theirs])

    assert billing._converge_duplicate_subscription(ours, "cus_1", "user_1") is False


def test_equal_timestamps_still_elect_exactly_one_survivor(wired):
    """Stripe `created` is second-granularity, so a real race very plausibly ties. The id tiebreak
    must make the two racers reach OPPOSITE conclusions, never the same one."""
    a = _sub_row("sub_a", status="trialing", created=1_700_000_000)
    z = _sub_row("sub_z", status="trialing", created=1_700_000_000)
    wired.setattr(billing, "_live_subscriptions", lambda cid: [a, z])
    cancelled: list[str] = []
    wired.setattr(billing, "_stripe", lambda: types.SimpleNamespace(
        Subscription=types.SimpleNamespace(cancel=cancelled.append)))

    a_stands_down = billing._converge_duplicate_subscription(a, "cus_1", "user_1")
    z_stands_down = billing._converge_duplicate_subscription(z, "cus_1", "user_1")

    assert [a_stands_down, z_stands_down] == [False, True]
    assert cancelled == ["sub_z"]


# --------------------------------------------------------------------------- #
# 7. lifecycle actions must not be suppressed
# --------------------------------------------------------------------------- #
def test_a_later_checkout_uses_a_new_identity_and_is_not_deduped(wired):
    """After a cancellation the user re-subscribes through /subscribe/init, which mints a NEW
    SetupIntent -- a new key. The old result must not be replayed onto the new purchase."""
    acct = _FakeAccount(si_by_id={"seti_1": _si(sid="seti_1"), "seti_2": _si(sid="seti_2")})
    wired.setattr(billing, "_stripe", lambda: acct)
    wired.setattr(billing, "_existing_customer", lambda uid: "cus_1")

    first = billing.subscribe_complete(_body(sid="seti_1"), user=USER)
    acct.subs.clear()                                   # user cancels
    second = billing.subscribe_complete(_body(sid="seti_2"), user=USER)

    assert len(acct.create_calls) == 2
    assert first["subscription_id"] != second["subscription_id"]


def test_upgrade_is_untouched_by_the_dedupe(wired):
    """The upgrade lane MODIFIES the live subscription; it never routes through the keyed create,
    so tier changes stay possible while a subscription is live."""
    modified: dict = {}
    live = types.SimpleNamespace(
        id="sub_live", status="active", created=1_700_000_000,
        items=types.SimpleNamespace(data=[types.SimpleNamespace(
            id="si_item", price=types.SimpleNamespace(lookup_key="essential_2026_v2_monthly",
                                                      interval="month"))]))
    fake = types.SimpleNamespace(Subscription=types.SimpleNamespace(
        modify=lambda sid, **kw: modified.update(sid=sid, **kw) or live))
    wired.setattr(billing, "_stripe", lambda: fake)
    wired.setattr(billing, "_existing_customer", lambda uid: "cus_1")
    wired.setattr(billing, "_live_subscription", lambda cid: live)
    wired.setattr(billing, "_price_id", lambda lk: f"price_{lk}")

    billing.upgrade(billing.UpgradeRequest(tier="pro", interval="annual"), user=USER)
    assert modified["sid"] == "sub_live"
    assert "idempotency_key" not in modified


# --------------------------------------------------------------------------- #
# 8. a webhook arriving mid-completion
# --------------------------------------------------------------------------- #
def test_webhook_during_completion_never_mints_a_second_subscription(wired):
    """Stripe fires customer.subscription.created while /complete is still running. The webhook
    lane only RECOMPUTES the entitlement row -- it must never create, and both writers must
    converge on the one subscription."""
    acct = _FakeAccount(si_by_id={"seti_abc": _si()})
    acct.arm_barrier(2)
    upserts: list = []
    wired.setattr(billing, "_stripe", lambda: acct)
    wired.setattr(billing, "_existing_customer", lambda uid: "cus_1")
    wired.setattr(billing, "_customer_id_for_event", lambda etype, obj: "cus_1")
    wired.setattr(billing, "_user_id_for_event", lambda etype, obj, cid: "user_1")
    wired.setattr(billing, "_upsert_entitlement",
                  lambda uid, cid, ent: upserts.append((uid, cid, ent["status"])))

    event = {"type": "customer.subscription.created",
             "data": {"object": {"id": "sub_1", "customer": "cus_1", "status": "trialing"}}}

    def _webhook():
        acct.Subscription.list(customer="cus_1", status="all", limit=20)   # cross the barrier
        billing._handle_event(event)
        return "webhook-ok"

    results, errors = _run_concurrently([
        lambda: billing.subscribe_complete(_body(), user=USER),
        _webhook,
    ])

    assert errors == [None, None], errors
    assert len(acct.create_calls) == 1, "the webhook lane must never create a subscription"
    assert results[1] == "webhook-ok"
    assert all(u[:2] == ("user_1", "cus_1") for u in upserts)


def test_a_failing_probe_does_not_mask_the_real_create_failure(wired):
    """The post-failure live-sub probe is best-effort. If the probe itself raises an
    HTTPException -- _stripe() answers 503 when unconfigured -- the caller must still get the
    502 for the create that actually failed, not the probe's status."""
    acct = _FakeAccount(si_by_id={"seti_abc": _si()})
    acct.Subscription.create = lambda **kw: (_ for _ in ()).throw(RuntimeError("stripe 500"))
    wired.setattr(billing, "_stripe", lambda: acct)
    wired.setattr(billing, "_existing_customer", lambda uid: "cus_1")

    def _probe_explodes(cid):
        raise HTTPException(503, "billing not configured")

    wired.setattr(billing, "_has_live_subscription", _probe_explodes)

    with pytest.raises(HTTPException) as ei:
        billing.subscribe_complete(_body(), user=USER)
    assert ei.value.status_code == 502
    assert ei.value.detail == "subscribe complete failed, please try again"
