"""Unit tests for app/billing.py — the Stripe billing spine (MNZ W2).

Fully offline: no network, no real Stripe, no Supabase. Stripe/PostgREST calls are
monkeypatched; the only "real" Stripe code exercised is the pure-crypto webhook
signature verification (stripe.Webhook.construct_event does no I/O).

Categories:
  1. Pure reducer (_entitlement_from_state) — tier precedence + negative path.
  2. Subscription field extraction (_sub_tier / _sub_period_end) incl. the
     API-version change that moved current_period_end to the item level.
  3. Live-state recompute (_compute_entitlement) against a fake Stripe.
  4. Webhook signature verification — good sig dispatches, bad sig -> 400.
  5. Idempotency — seen-event short-circuits; recompute is replay-stable.
  6. Negative propagation — subscription.deleted -> tier 'free', cache busted.

Run:
    python -m pytest tests/test_billing_webhook.py -v
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
import types

import pytest
from fastapi import HTTPException

from app import billing

WHSEC = "whsec_test_secret_123"


def _get_api_me(app):
    """Exercise the HTTP issuer without httpx, absent from the billing CI install."""
    scope = {
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1", "method": "GET", "scheme": "http",
        "path": "/api/me", "raw_path": b"/api/me", "query_string": b"",
        "root_path": "", "headers": [(b"host", b"testserver")],
        "client": ("testclient", 50000), "server": ("testserver", 80),
    }
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    asyncio.run(app(scope, receive, send))
    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    return status, json.loads(body)


@pytest.mark.parametrize("status", [
    "past_due", "canceled", "unpaid", "incomplete", "incomplete_expired", "paused",
])
def test_private_feature_is_revoked_for_inactive_pro_even_with_stale_keys(status):
    """No inactive subscription can retain the private capability through stale keys."""
    row = billing._entitlement_from_state(
        [{"status": status, "tier": "pro", "current_period_end": 1900000000}],
        ["site_full", "company_intelligence_private_read"],
    )
    assert row["tier"] == "free" and row["status"] == status
    assert row["features"] == []


@pytest.mark.parametrize("status", ["active", "trialing"])
def test_private_feature_explicit_stripe_keys_are_authoritative(status):
    """A Pro label never supplements a nonempty explicit Stripe feature list."""
    subs = [{"status": status, "tier": "pro", "current_period_end": 1900000000}]
    keys = ["site_full", "chat_opus"]
    assert billing._entitlement_from_state(subs, keys)["features"] == keys
    granted = keys + ["company_intelligence_private_read"]
    assert billing._entitlement_from_state(subs, granted)["features"] == granted


def test_private_feature_uses_existing_fallback_when_stripe_feature_read_fails(monkeypatch):
    """The existing provider-lag fallback remains an authoritative catalog computation."""
    stripe = _fake_stripe([_sub("trialing", "pro_monthly", 1900000000)], [])

    def unavailable(**kwargs):
        raise RuntimeError("offline simulated entitlement propagation failure")

    stripe.entitlements.ActiveEntitlement.list = unavailable
    monkeypatch.setattr(billing, "_stripe", lambda: stripe)
    row = billing._compute_entitlement("cus_private_test")
    assert row["tier"] == "pro" and row["status"] == "trialing"
    assert "company_intelligence_private_read" in row["features"]


def test_api_me_private_feature_requires_verified_principal(monkeypatch):
    from app import main

    monkeypatch.setattr(billing, "read_entitlement", lambda uid: pytest.fail(
        "unverified caller must never reach entitlement issuance",
    ))
    status, _ = _get_api_me(main.app)
    assert status == 401


@pytest.mark.parametrize(
    "status,lookup_key,keys,read_failed,expected_private",
    [
        ("active", "pro_monthly", [], False, True),
        ("trialing", "pro_annual", [], False, True),
        ("active", "insider_monthly", [], False, False),
        ("active", "unrecognized_price", [], False, False),
        ("active", "pro_monthly", ["site_full", "chat_opus"], False, False),
        ("canceled", "pro_monthly", ["company_intelligence_private_read"], False, False),
        ("active", "pro_monthly", [], True, False),
    ],
)
def test_private_feature_recompute_row_reaches_api_me(
    monkeypatch, status, lookup_key, keys, read_failed, expected_private,
):
    """The existing issuer forwards persisted features, including under an unlimited label.

    This exercises the compute/write/read/HTTP chain with isolated Stripe and PostgREST
    transports. It proves source behavior, never external provisioning or real user grants.
    """
    from app import main

    stored = []

    def fake_pg(method, path, **kwargs):
        assert path.startswith("user_entitlements?")
        if method == "POST":
            stored[:] = kwargs["body"]
            return []
        assert method == "GET" and "user_id=eq.user_private_test" in path
        if read_failed:
            raise RuntimeError("offline simulated persisted-row read failure")
        return stored

    monkeypatch.setattr(billing, "_pg", fake_pg)
    monkeypatch.setattr(billing, "SUPABASE_SERVICE_ROLE_KEY", "offline-test-key")
    monkeypatch.setattr(
        billing, "_stripe",
        lambda: _fake_stripe([_sub(status, lookup_key, 1900000000)], keys),
    )
    monkeypatch.setattr(
        main, "_brain_module",
        lambda: types.SimpleNamespace(
            get_user_quotas=lambda *a, **kw: {"tier": "unlimited", "quotas": {}},
        ),
    )
    monkeypatch.setitem(
        main.app.dependency_overrides, main.require_user,
        lambda: {"id": "user_private_test", "role": "authenticated"},
    )
    ent = billing._compute_entitlement("cus_private_test")
    billing._upsert_entitlement("user_private_test", "cus_private_test", ent)
    response_status, issued = _get_api_me(main.app)
    assert response_status == 200
    assert ent["features"] == stored[0]["features"]
    assert issued["features"] == ([] if read_failed else ent["features"])
    assert ("company_intelligence_private_read" in issued["features"]) is expected_private
    assert issued["tier"] == "unlimited"  # display overlay grants no additional feature


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _price(lk):
    return types.SimpleNamespace(lookup_key=lk, metadata={})


def _item(lk, cpe=None):
    return types.SimpleNamespace(price=_price(lk), current_period_end=cpe)


def _sub(status, lk, cpe, top_cpe=None):
    return types.SimpleNamespace(
        status=status,
        current_period_end=top_cpe,
        items=types.SimpleNamespace(data=[_item(lk, cpe)]),
    )


class _ListResp:
    def __init__(self, data):
        self.data = data


def _fake_stripe(subs, ent_keys):
    ents = [types.SimpleNamespace(lookup_key=k) for k in ent_keys]
    return types.SimpleNamespace(
        Subscription=types.SimpleNamespace(list=lambda **kw: _ListResp(subs)),
        entitlements=types.SimpleNamespace(
            ActiveEntitlement=types.SimpleNamespace(list=lambda **kw: _ListResp(ents))
        ),
    )


class _FakeRequest:
    def __init__(self, body: bytes, headers: dict):
        self._body = body
        self.headers = headers

    async def body(self) -> bytes:
        return self._body


def _sign(payload: bytes, secret: str = WHSEC) -> str:
    ts = int(time.time())
    signed = f"{ts}.".encode() + payload
    mac = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={ts},v1={mac}"


def _event(etype: str, obj: dict, event_id: str = "evt_1") -> bytes:
    return json.dumps({"id": event_id, "type": etype, "data": {"object": obj}}).encode()


# --------------------------------------------------------------------------- #
# 1. pure reducer
# --------------------------------------------------------------------------- #
def test_reducer_picks_highest_active_tier():
    r = billing._entitlement_from_state(
        [
            {"status": "active", "current_period_end": 1900000000, "tier": "pro"},
            {"status": "active", "current_period_end": 1900000000, "tier": "essential"},
        ],
        [],
    )
    assert r["tier"] == "pro" and r["status"] == "active"
    # empty entitlement keys -> config fallback features for the tier
    assert "chat_opus" in r["features"]


def test_reducer_uses_entitlement_keys_when_present():
    r = billing._entitlement_from_state(
        [{"status": "trialing", "current_period_end": 1, "tier": "essential"}],
        ["site_full", "terminal_live_options"],
    )
    assert r["tier"] == "essential" and r["status"] == "trialing"
    assert r["features"] == ["site_full", "terminal_live_options"]


def test_reducer_no_active_sub_is_free():
    r = billing._entitlement_from_state(
        [{"status": "canceled", "current_period_end": 5, "tier": "pro"}], []
    )
    assert r["tier"] == "free" and r["features"] == [] and r["status"] == "canceled"


def test_reducer_empty_is_free_none():
    r = billing._entitlement_from_state([], [])
    assert r["tier"] == "free" and r["status"] == "none" and r["current_period_end"] is None


# --------------------------------------------------------------------------- #
# 2. subscription field extraction
# --------------------------------------------------------------------------- #
def test_sub_tier_from_lookup_key():
    assert billing._sub_tier(_sub("active", "pro_annual", 1)) == "pro"
    # a retired lookup_key still resolves, via the catalog's legacy_lookup_keys
    assert billing._sub_tier(_sub("active", "insider_monthly", 1)) == "essential"


def test_sub_period_end_prefers_item_level():
    # top-level absent (new API), item-level present -> item wins
    s = _sub("active", "pro_monthly", cpe=1755555555, top_cpe=None)
    assert billing._sub_period_end(s) == 1755555555
    # legacy top-level present -> used
    s2 = _sub("active", "pro_monthly", cpe=None, top_cpe=1700000000)
    assert billing._sub_period_end(s2) == 1700000000


# --------------------------------------------------------------------------- #
# 3. live-state recompute
# --------------------------------------------------------------------------- #
def test_compute_entitlement_active(monkeypatch):
    subs = [_sub("active", "pro_monthly", 1755555555)]
    monkeypatch.setattr(billing, "_stripe", lambda: _fake_stripe(subs, ["site_full", "chat_opus"]))
    ent = billing._compute_entitlement("cus_x")
    assert ent["tier"] == "pro" and ent["status"] == "active"
    assert ent["features"] == ["site_full", "chat_opus"]
    assert ent["current_period_end"].startswith("20")  # ISO


def test_compute_entitlement_canceled_is_free(monkeypatch):
    subs = [_sub("canceled", "pro_monthly", 1755555555)]
    monkeypatch.setattr(billing, "_stripe", lambda: _fake_stripe(subs, []))
    ent = billing._compute_entitlement("cus_x")
    assert ent["tier"] == "free" and ent["features"] == []


# --------------------------------------------------------------------------- #
# 4. webhook signature verification
# --------------------------------------------------------------------------- #
def test_webhook_good_signature_dispatches(monkeypatch, tmp_path):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", WHSEC)
    monkeypatch.setenv("MACRO_API_STATE_DIR", str(tmp_path))
    seen = {}
    monkeypatch.setattr(billing, "_event_seen", lambda eid: False)
    monkeypatch.setattr(billing, "_record_event", lambda eid, t: seen.setdefault("recorded", (eid, t)))
    monkeypatch.setattr(billing, "_handle_event", lambda ev: seen.setdefault("handled", ev["id"]))

    payload = _event("customer.subscription.updated", {"customer": "cus_1"}, "evt_good")
    req = _FakeRequest(payload, {"stripe-signature": _sign(payload)})
    out = asyncio.run(billing.webhook(req))
    assert out["status"] == "ok" and out["id"] == "evt_good"
    assert seen["handled"] == "evt_good" and seen["recorded"][0] == "evt_good"
    from lib.commercial_path import load_events
    rows = load_events(root=tmp_path / "commercial_path")
    assert any(r.get("kind") == "webhook.ok" and r.get("event_id") == "evt_good" for r in rows)


def test_webhook_bad_signature_400(monkeypatch, tmp_path):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", WHSEC)
    monkeypatch.setenv("MACRO_API_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(billing, "_handle_event", lambda ev: pytest.fail("must not dispatch on bad sig"))
    payload = _event("customer.subscription.updated", {"customer": "cus_1"})
    req = _FakeRequest(payload, {"stripe-signature": "t=1,v1=deadbeef"})
    with pytest.raises(HTTPException) as ei:
        asyncio.run(billing.webhook(req))
    assert ei.value.status_code == 400
    from lib.commercial_path import load_events
    rows = load_events(root=tmp_path / "commercial_path")
    assert any(r.get("kind") == "webhook.error" and r.get("reason") == "invalid_signature"
               for r in rows)


def test_webhook_missing_secret_503(monkeypatch):
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    payload = _event("customer.subscription.updated", {"customer": "cus_1"})
    req = _FakeRequest(payload, {"stripe-signature": _sign(payload)})
    with pytest.raises(HTTPException) as ei:
        asyncio.run(billing.webhook(req))
    assert ei.value.status_code == 503


# --------------------------------------------------------------------------- #
# 5. idempotency
# --------------------------------------------------------------------------- #
def test_webhook_duplicate_short_circuits(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", WHSEC)
    monkeypatch.setattr(billing, "_event_seen", lambda eid: True)  # already processed
    monkeypatch.setattr(billing, "_handle_event", lambda ev: pytest.fail("duplicate must not re-dispatch"))
    payload = _event("customer.subscription.updated", {"customer": "cus_1"}, "evt_dup")
    req = _FakeRequest(payload, {"stripe-signature": _sign(payload)})
    out = asyncio.run(billing.webhook(req))
    assert out["status"] == "duplicate" and out["id"] == "evt_dup"


def test_handle_event_is_replay_stable(monkeypatch):
    """Processing the same event twice writes the identical entitlement (minus timestamp)."""
    upserts = []
    monkeypatch.setattr(billing, "_customer_id_for_event", lambda t, o: "cus_1")
    monkeypatch.setattr(billing, "_user_id_for_event", lambda t, o, c: "user_1")
    monkeypatch.setattr(
        billing, "_compute_entitlement",
        lambda cid: {"tier": "pro", "status": "active", "current_period_end": "2026-08-21T00:00:00+00:00",
                     "features": ["site_full", "chat_opus"]},
    )
    monkeypatch.setattr(billing, "_upsert_entitlement",
                        lambda uid, cid, ent: upserts.append((uid, cid, ent)))
    monkeypatch.setattr(billing, "_invalidate", lambda uid: None)

    ev = {"id": "evt_x", "type": "customer.subscription.updated", "data": {"object": {"customer": "cus_1"}}}
    billing._handle_event(ev)
    billing._handle_event(ev)
    assert len(upserts) == 2
    assert upserts[0] == upserts[1]  # same user, customer, entitlement — convergent


# --------------------------------------------------------------------------- #
# 6. negative propagation
# --------------------------------------------------------------------------- #
def test_subscription_deleted_downgrades_and_busts_cache(monkeypatch):
    captured = {}
    subs = [_sub("canceled", "pro_monthly", 1755555555)]
    monkeypatch.setattr(billing, "_stripe", lambda: _fake_stripe(subs, []))
    monkeypatch.setattr(billing, "_customer_id_for_event", lambda t, o: "cus_1")
    monkeypatch.setattr(billing, "_user_id_for_event", lambda t, o, c: "user_1")
    monkeypatch.setattr(billing, "_upsert_entitlement",
                        lambda uid, cid, ent: captured.update(ent=ent, uid=uid))
    monkeypatch.setattr(billing, "_invalidate", lambda uid: captured.update(invalidated=uid))

    ev = {"id": "evt_del", "type": "customer.subscription.deleted", "data": {"object": {"customer": "cus_1"}}}
    billing._handle_event(ev)
    assert captured["ent"]["tier"] == "free" and captured["ent"]["features"] == []
    assert captured["invalidated"] == "user_1"  # cache bust fired


# --------------------------------------------------------------------------- #
# 7. review remediation — chargeback, multi-item tier, out-of-order resolution
# --------------------------------------------------------------------------- #
def test_multi_item_sub_resolves_highest_tier():
    # M2: a sub carrying both an essential and a pro price resolves to pro, not item order.
    item = lambda lk: types.SimpleNamespace(price=types.SimpleNamespace(lookup_key=lk, metadata={}), current_period_end=1)
    sub = types.SimpleNamespace(status="active", current_period_end=None,
                                items=types.SimpleNamespace(data=[item("insider_monthly"), item("pro_monthly")]))
    assert billing._sub_tier(sub) == "pro"


def test_chargeback_cancels_subs_then_downgrades(monkeypatch):
    # C1: a dispute must cancel the live subs (so the free downgrade sticks) AND downgrade the row.
    calls = {}
    monkeypatch.setattr(billing, "_customer_id_for_event", lambda t, o: "cus_1")
    monkeypatch.setattr(billing, "_user_id_for_event", lambda t, o, c: "user_1")
    monkeypatch.setattr(billing, "_cancel_subscriptions", lambda cid: calls.__setitem__("canceled", cid))
    monkeypatch.setattr(billing, "_compute_entitlement",
                        lambda cid: {"tier": "free", "status": "canceled", "current_period_end": None, "features": []})
    monkeypatch.setattr(billing, "_upsert_entitlement", lambda u, c, e: calls.__setitem__("ent", e))
    monkeypatch.setattr(billing, "_invalidate", lambda u: None)
    billing._handle_event({"id": "evt_disp", "type": "charge.dispute.created", "data": {"object": {"charge": "ch_1"}}})
    assert calls.get("canceled") == "cus_1"       # subs cancelled on chargeback
    assert calls["ent"]["tier"] == "free"         # ...and entitlement revoked


def test_subscription_created_before_checkout_resolves_via_metadata(monkeypatch):
    # H2: out-of-order — subscription.created arrives before checkout.session.completed, so no
    # persisted customer->user row exists yet; the mm_user_id we stamp on the sub must resolve it.
    monkeypatch.setattr(billing, "_user_for_customer", lambda cid: None)  # mapping row not written yet
    obj = {"customer": "cus_9", "metadata": {"mm_user_id": "user_9"}}
    assert billing._user_id_for_event("customer.subscription.created", obj, "cus_9") == "user_9"


def test_unresolved_subscription_event_without_metadata_or_row_is_dropped(monkeypatch):
    # H2 corollary: no metadata AND no mapping row → unresolved → None (event is skipped, not misapplied).
    monkeypatch.setattr(billing, "_user_for_customer", lambda cid: None)
    assert billing._user_id_for_event("customer.subscription.updated", {"customer": "cus_x"}, "cus_x") is None


# --------------------------------------------------------------------------- #
# 8. SEE W3 — the handler must not block the event loop, and one user's events
#    must not interleave now that they can run concurrently.
# --------------------------------------------------------------------------- #
def test_webhook_runs_the_handler_off_the_event_loop(monkeypatch):
    """_handle_event is fully blocking (Supabase + Stripe + SMTP). Left inline in the
    async route it stalls EVERY other request on this single-process API, so it has to
    take the threadpool hop."""
    import threading

    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", WHSEC)
    monkeypatch.setattr(billing, "_event_seen", lambda eid: False)
    monkeypatch.setattr(billing, "_record_event", lambda eid, t: None)

    seen = {}

    def _slow(ev):
        seen["thread"] = threading.current_thread().name

    monkeypatch.setattr(billing, "_handle_event", _slow)

    async def _drive():
        seen["loop_thread"] = threading.current_thread().name
        payload = _event("customer.subscription.updated", {"customer": "cus_1"}, "evt_tp")
        req = _FakeRequest(payload, {"stripe-signature": _sign(payload)})
        return await billing.webhook(req)

    out = asyncio.run(_drive())
    assert out["status"] == "ok"
    assert seen["thread"] != seen["loop_thread"], "_handle_event ran ON the event loop"


def test_concurrent_events_for_one_user_do_not_interleave(monkeypatch):
    """The email hook compares the entitlement before the upsert with the one after, so
    two events for the SAME user must be serialised — otherwise both read the same
    'before' and both can decide an upgrade happened. Guards the threadpool change."""
    import threading

    order: list[str] = []
    barrier_hit = threading.Event()

    def _snapshot(etype, uid):
        order.append(f"snap-{threading.current_thread().name}")
        barrier_hit.set()
        time.sleep(0.05)          # a window wide enough for the other thread to race in
        return {"tier": "essential"}

    def _upsert(uid, cid, ent):
        order.append(f"write-{threading.current_thread().name}")

    fake_emails = types.SimpleNamespace(
        pre_upsert_snapshot=_snapshot,
        on_event=lambda *a, **kw: None,
    )
    monkeypatch.setattr(billing, "_billing_emails", lambda: fake_emails)
    monkeypatch.setattr(billing, "_customer_id_for_event", lambda t, o: "cus_1")
    monkeypatch.setattr(billing, "_user_id_for_event", lambda t, o, c: "user_same")
    monkeypatch.setattr(billing, "_compute_entitlement",
                        lambda cid: {"tier": "pro", "status": "active",
                                     "current_period_end": None, "features": []})
    monkeypatch.setattr(billing, "_upsert_entitlement", _upsert)
    monkeypatch.setattr(billing, "_invalidate", lambda uid: None)

    ev = {"id": "evt_race", "type": "customer.subscription.updated",
          "data": {"object": {"customer": "cus_1"}}}
    threads = [threading.Thread(target=billing._handle_event, args=(dict(ev),), name=f"w{i}")
               for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    # Each snapshot must be followed by ITS OWN write before the other thread snapshots.
    assert len(order) == 4, order
    assert order[0].startswith("snap-") and order[1].startswith("write-")
    assert order[0].split("-")[1] == order[1].split("-")[1], f"interleaved: {order}"
    assert order[2].split("-")[1] == order[3].split("-")[1], f"interleaved: {order}"


def test_different_users_are_not_serialised_against_each_other(monkeypatch):
    """The lock is per user — one customer's slow SMTP must not queue everyone else's."""
    assert billing._user_lock("a") is billing._user_lock("a")
    assert billing._user_lock("a") is not billing._user_lock("b")


def test_the_send_happens_outside_the_per_user_lock(monkeypatch):
    """N2 — the lock covers the DECISION, not the SMTP conversation.

    mailer.send is ledger-first on a UNIQUE idem_key, so delivery needs no serialisation;
    holding the lock across it would make the second of two events that arrive together
    (invoice.payment_failed + customer.subscription.updated on a failed renewal) wait out
    the first's entire send while pinning an anyio threadpool token.
    """
    from app import billing_emails as be

    seen = {}

    def _spy_deliver(outbox):
        seen["locked_during_send"] = billing._user_lock("user_1").locked()
        return "sent"

    monkeypatch.setattr(be, "deliver", _spy_deliver)
    monkeypatch.setattr(be, "prepare", lambda *a, **kw: "an-outbox")
    monkeypatch.setattr(billing, "_customer_id_for_event", lambda t, o: "cus_1")
    monkeypatch.setattr(billing, "_user_id_for_event", lambda t, o, c: "user_1")
    monkeypatch.setattr(billing, "_compute_entitlement",
                        lambda cid: {"tier": "pro", "status": "active",
                                     "current_period_end": None, "features": []})
    monkeypatch.setattr(billing, "_upsert_entitlement", lambda u, c, e: None)
    monkeypatch.setattr(billing, "_invalidate", lambda u: None)

    billing._handle_event({"id": "evt_lk", "type": "customer.subscription.updated",
                           "data": {"object": {"customer": "cus_1"}}})
    assert seen["locked_during_send"] is False, "the SMTP send ran while holding the lock"


def test_the_decision_still_happens_inside_the_lock(monkeypatch):
    """The other half of N2: prepare() must stay serialised or the upgrade comparison
    can straddle another event's write."""
    from app import billing_emails as be

    seen = {}
    monkeypatch.setattr(be, "prepare",
                        lambda *a, **kw: seen.setdefault(
                            "locked_during_decide", billing._user_lock("user_1").locked()))
    monkeypatch.setattr(be, "deliver", lambda outbox: None)
    monkeypatch.setattr(billing, "_customer_id_for_event", lambda t, o: "cus_1")
    monkeypatch.setattr(billing, "_user_id_for_event", lambda t, o, c: "user_1")
    monkeypatch.setattr(billing, "_compute_entitlement",
                        lambda cid: {"tier": "pro", "status": "active",
                                     "current_period_end": None, "features": []})
    monkeypatch.setattr(billing, "_upsert_entitlement", lambda u, c, e: None)
    monkeypatch.setattr(billing, "_invalidate", lambda u: None)

    billing._handle_event({"id": "evt_lk2", "type": "customer.subscription.updated",
                           "data": {"object": {"customer": "cus_1"}}})
    assert seen["locked_during_decide"] is True


def test_checkout_failure_emits_commercial_path_event(monkeypatch, tmp_path):
    """GATE-4: a Stripe Checkout create failure must land on the commercial ledger."""
    monkeypatch.setenv("MACRO_API_STATE_DIR", str(tmp_path))

    class _Boom:
        class Session:
            @staticmethod
            def create(**kwargs):
                raise RuntimeError("stripe down")

        checkout = types.SimpleNamespace(Session=Session)

    monkeypatch.setattr(billing, "_stripe", lambda: _Boom())
    monkeypatch.setattr(billing, "_existing_customer", lambda uid: None)
    monkeypatch.setattr(billing, "_price_id", lambda lk: f"price_{lk}")
    with pytest.raises(HTTPException) as ei:
        billing.checkout(
            billing.CheckoutRequest(tier="pro", interval="monthly"),
            user={"id": "user_1", "email": "buyer@example.com"},
        )
    assert ei.value.status_code == 502
    from lib.commercial_path import load_events
    rows = load_events(root=tmp_path / "commercial_path")
    assert any(r.get("kind") == "checkout.fail" and r.get("reason") == "RuntimeError"
               for r in rows)


@pytest.mark.parametrize("etype,status", [
    ("customer.subscription.deleted", "canceled"),
    ("invoice.payment_failed", "past_due"),
])
@pytest.mark.parametrize("failure", [
    "timeout", "http_503", "invalid_json", "empty_body", "object", "missing_user",
    "blank_user", "nonstring_user", "invalid_row",
])
def test_signed_revocation_retries_failed_mapping_then_reaches_api_me(
    monkeypatch, etype, status, failure,
):
    """A failed authority lookup must not settle the event or strand paid access.

    Only signature verification and the HTTP issuer are real; all provider, database,
    mail and telemetry transports are isolated. The retained ledger remains the sole
    duplicate authority, and later out-of-order events recompute current Stripe state.
    """
    import urllib.error
    import stripe
    from app import main

    row = {
        "user_id": "user_retry_test", "stripe_customer_id": "cus_retry_test",
        "tier": "pro", "status": "active", "current_period_end": None,
        "features": ["site_full", "terminal_live_options"], "source": "stripe",
    }
    recorded, invalidated, emitted = set(), [], []
    mapping_available = False
    writes = []
    errors = {
        "timeout": TimeoutError("offline simulated mapping timeout"),
        "http_503": urllib.error.HTTPError("https://db.invalid", 503, "unavailable", {}, None),
        "invalid_json": json.JSONDecodeError("invalid mapping response", "!", 0),
    }

    malformed = {
        "empty_body": None, "object": {}, "missing_user": [{}],
        "blank_user": [{"user_id": "  "}], "nonstring_user": [{"user_id": 123}],
        "invalid_row": [None],
    }

    def fake_pg(method, path, **kwargs):
        if path.startswith("stripe_events?"):
            if method == "GET":
                return [{"id": "found"}] if path.split("id=eq.")[1].split("&")[0] in recorded else []
            assert method == "POST"
            recorded.add(kwargs["body"][0]["id"])
            return None
        assert path.startswith("user_entitlements?")
        if method == "GET":
            if "stripe_customer_id=eq." in path:
                if not mapping_available:
                    if failure in malformed:
                        return malformed[failure]
                    raise errors[failure]
                return [{"user_id": row["user_id"]}]
            assert "user_id=eq.user_retry_test" in path
            return [row.copy()]
        assert method == "POST"
        writes.append(kwargs["body"][0])
        row.update(writes[-1])

    fake_stripe = _fake_stripe([_sub(status, "pro_monthly", 1900000000)], [])
    fake_stripe.Webhook, fake_stripe.error = stripe.Webhook, stripe.error
    monkeypatch.setattr(billing, "_stripe", lambda: fake_stripe)
    monkeypatch.setattr(billing, "_pg", fake_pg)
    monkeypatch.setattr(billing, "SUPABASE_SERVICE_ROLE_KEY", "offline-test-key")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", WHSEC)
    monkeypatch.setattr(billing, "_billing_emails", lambda: None)
    monkeypatch.setattr(billing, "_invalidate", invalidated.append)
    monkeypatch.setattr(billing, "_commercial_emit", lambda kind, **fields: emitted.append(kind))
    monkeypatch.setattr(main, "_brain_module", lambda: types.SimpleNamespace(
        get_user_quotas=lambda *a, **kw: {"tier": "free", "quotas": {}},
    ))
    monkeypatch.setitem(main.app.dependency_overrides, main.require_user,
                        lambda: {"id": "user_retry_test", "role": "authenticated"})

    assert "terminal_live_options" in _get_api_me(main.app)[1]["features"]
    payload = _event(etype, {"customer": "cus_retry_test"}, "evt_retry_test")
    request = _FakeRequest(payload, {"stripe-signature": _sign(payload)})
    error_type = type(errors[failure]) if failure in errors else ValueError
    with pytest.raises(error_type):
        asyncio.run(billing.webhook(request))
    assert not recorded and not writes and not invalidated
    assert emitted == ["webhook.error"]
    assert row["tier"] == "pro"

    mapping_available = True
    assert asyncio.run(billing.webhook(request))["status"] == "ok"
    assert recorded == {"evt_retry_test"} and invalidated == ["user_retry_test"]
    response_status, issued = _get_api_me(main.app)
    assert response_status == 200
    assert issued["tier"] == "free" and issued["status"] == status and issued["features"] == []
    assert asyncio.run(billing.webhook(request))["status"] == "duplicate"
    assert len(writes) == 1 and len(invalidated) == 1

    # A delayed older positive notification cannot re-grant after current-state revocation.
    old_payload = _event("customer.subscription.updated", {
        "customer": "cus_retry_test", "status": "active",
    }, "evt_delayed_test")
    assert asyncio.run(billing.webhook(_FakeRequest(
        old_payload, {"stripe-signature": _sign(old_payload)},
    )))["status"] == "ok"
    assert row["tier"] == "free" and row["features"] == []


def test_customer_mapping_absence_remains_unresolved(monkeypatch):
    """A successful empty lookup still ignores an unrelated customer without writing."""
    monkeypatch.setattr(billing, "_pg", lambda *a, **kw: [])
    monkeypatch.setattr(billing, "_compute_entitlement", lambda cid: pytest.fail("unmapped customer"))
    assert billing._user_for_customer("cus_unmapped") is None
    billing._handle_event({"id": "evt_unmapped", "type": "invoice.payment_failed",
                           "data": {"object": {"customer": "cus_unmapped"}}})


@pytest.fixture
def conversion_system(monkeypatch):
    """Actual reducer, signed ingress and analytics request; isolated provider/DB transports."""
    import copy
    import stripe
    from app import main

    uid, cid, created = "11111111-1111-4111-8111-111111111111", "cus_conversion_test", 1790000000
    price = {"id": "price_conversion", "lookup_key": "pro_monthly", "currency": "usd",
             "recurring": {"interval": "month", "interval_count": 1}}
    sub = {"id": "sub_conversion", "customer": cid, "created": created - 20,
           "livemode": False, "status": "active", "trial_start": None, "trial_end": None,
           "metadata": {"mm_user_id": uid}, "current_period_end": 1900000000,
           "items": {"has_more": False, "data": [{"price": price, "current_period_end": 1900000000}]}}
    session = {"id": "cs_conversion", "customer": cid, "client_reference_id": uid,
               "livemode": False, "mode": "subscription", "status": "complete",
               "payment_status": "paid", "amount_total": 12345, "currency": "usd",
               "metadata": {"mm_user_id": uid}, "subscription": sub,
               "line_items": {"has_more": False, "data": [{"price": price}]}}
    row, ledger, analytics, requests, invalidations = {}, set(), {}, [], []
    failure = {"mode": None}
    provider_reads = []

    def pg(method, path, body=None, **kwargs):
        if path.startswith("stripe_events?"):
            if method == "GET":
                eid = path.split("id=eq.")[1].split("&")[0]
                return [{"id": eid}] if eid in ledger else []
            ledger.add(body[0]["id"])
            return None
        assert path.startswith("user_entitlements?")
        if method == "GET":
            return [{"user_id": uid}] if "stripe_customer_id=eq." in path else [copy.deepcopy(row)]
        if failure["mode"] == "entitlement":
            raise TimeoutError("isolated entitlement write failed")
        row.update(copy.deepcopy(body[0]))

    def urlopen(req, timeout=5):
        if req.get_method() == "GET":
            assert "/analytics_events?eid=eq." in req.full_url
            eid = req.full_url.split("eid=eq.")[1].split("&")[0]
            return types.SimpleNamespace(read=lambda: json.dumps([analytics[eid]] if eid in analytics else []).encode())
        assert req.full_url.endswith("/analytics_events?on_conflict=eid")
        assert req.headers["Prefer"] == "resolution=ignore-duplicates,return=minimal"
        rows = json.loads(req.data)
        requests.append(rows)
        if failure["mode"] == "analytics":
            raise TimeoutError("isolated analytics failure before write")
        for item in rows:
            analytics.setdefault(item["eid"], item)
        if failure["mode"] == "lost_ack":
            failure["mode"] = None
            raise TimeoutError("isolated analytics ACK lost after write")
        return types.SimpleNamespace(read=lambda: b"")

    def retrieve_session(sid, **kwargs):
        assert sid == session["id"] and kwargs["expand"] == ["subscription", "line_items.data.price"]
        provider_reads.append("session")
        return copy.deepcopy(session)

    def retrieve_sub(sid):
        assert sid == sub["id"]
        provider_reads.append("subscription")
        return copy.deepcopy(sub)

    fake = types.SimpleNamespace(
        Webhook=stripe.Webhook, error=stripe.error,
        Customer=types.SimpleNamespace(modify=lambda *args, **kwargs: {}),
        Subscription=types.SimpleNamespace(
            list=lambda **kw: _ListResp([stripe.StripeObject.construct_from(sub, "sk_test_offline")]),
            retrieve=retrieve_sub),
        checkout=types.SimpleNamespace(Session=types.SimpleNamespace(retrieve=retrieve_session)),
        entitlements=types.SimpleNamespace(ActiveEntitlement=types.SimpleNamespace(list=lambda **kw: _ListResp([]))),
    )
    monkeypatch.setattr(billing, "_stripe", lambda: fake)
    monkeypatch.setattr(billing, "_pg", pg)
    monkeypatch.setattr(billing, "_billing_emails", lambda: None)
    monkeypatch.setattr(billing, "_commercial_emit", lambda *a, **kw: None)
    monkeypatch.setattr(billing, "_invalidate", invalidations.append)
    monkeypatch.setattr(billing, "SUPABASE_SERVICE_ROLE_KEY", "offline-key")
    monkeypatch.setattr(main, "SUPABASE_SERVICE_ROLE_KEY", "offline-key")
    monkeypatch.setattr(main.urllib.request, "urlopen", urlopen)
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", WHSEC)

    def event(etype="checkout.session.completed", eid="evt_conversion"):
        obj = copy.deepcopy(session if etype == "checkout.session.completed" else sub)
        if etype == "checkout.session.completed":
            obj["subscription"] = sub["id"]
            obj.pop("line_items")
        return {"id": eid, "type": etype, "created": created, "livemode": False, "data": {"object": obj}}

    def send(ev):
        payload = json.dumps(ev).encode()
        return asyncio.run(billing.webhook(_FakeRequest(payload, {"stripe-signature": _sign(payload)})))

    return types.SimpleNamespace(
        uid=uid, cid=cid, created=created, sub=sub, session=session, row=row, ledger=ledger,
        analytics=analytics, requests=requests, invalidations=invalidations, failure=failure,
        provider_reads=provider_reads, event=event, send=send, main=main,
    )


def test_checkout_conversion_requires_persisted_entitlement_and_real_facts(conversion_system):
    import uuid
    f = conversion_system
    ev = f.event()
    f.failure["mode"] = "entitlement"
    with pytest.raises(TimeoutError):
        f.send(ev)
    assert not f.analytics and not f.requests and not f.ledger and not f.provider_reads
    f.failure["mode"] = None
    assert f.send(ev)["status"] == "ok"
    assert f.row["tier"] == "pro" and f.row["status"] == "active"
    item = next(iter(f.analytics.values()))
    assert item["eid"] == str(uuid.uuid5(uuid.NAMESPACE_URL, "mastermind:stripe:evt_conversion:checkout.completed"))
    assert item["user_id"] == f.uid and item["type"] == "checkout.completed"
    assert item["meta"] == {"tier": "pro", "interval": "month", "offer_key": None,
                             "amount_cents": 12345, "is_trial": False}
    assert item["client_ts"] == billing._iso(f.created)
    assert "created_at" not in item  # DB observation time is not overwritten by Stripe time.
    assert f.send(ev)["status"] == "duplicate" and len(f.requests) == 1


@pytest.mark.parametrize("mode,rows_before_retry", [("analytics", 0), ("lost_ack", 1)])
def test_conversion_ack_failure_retries_same_identity_without_double_count(
    conversion_system, mode, rows_before_retry,
):
    f = conversion_system
    ev = f.event()
    f.failure["mode"] = mode
    with pytest.raises(TimeoutError):
        f.send(ev)
    assert f.row["tier"] == "pro" and not f.ledger and len(f.analytics) == rows_before_retry
    f.failure["mode"] = None
    assert f.send(ev)["status"] == "ok"
    assert len(f.analytics) == 1 and f.ledger == {ev["id"]}
    assert f.requests[0][0]["eid"] == f.requests[1][0]["eid"]
    assert f.requests[0] == f.requests[1]
    assert f.send(ev)["status"] == "duplicate" and len(f.requests) == 2


def test_retry_after_revocation_does_not_invent_delayed_conversion(conversion_system):
    f = conversion_system
    ev = f.event()
    f.failure["mode"] = "analytics"
    with pytest.raises(TimeoutError):
        f.send(ev)
    f.failure["mode"] = None
    f.sub["status"] = "canceled"
    assert f.send(ev)["status"] == "ok"
    assert f.row["tier"] == "free" and f.row["features"] == [] and not f.analytics
    assert len(f.requests) == 1 and f.ledger == {ev["id"]}


@pytest.mark.parametrize("etype", ["customer.subscription.updated", "invoice.payment_succeeded"])
def test_generic_paid_state_is_not_a_conversion(conversion_system, etype):
    f = conversion_system
    assert f.send(f.event(etype))["status"] == "ok"
    assert f.row["tier"] == "pro" and not f.analytics and not f.provider_reads


@pytest.mark.parametrize("trial", [False, True])
def test_zero_amount_does_not_define_trial(conversion_system, trial):
    f = conversion_system
    f.session["amount_total"] = 0
    if trial:
        f.sub.update(status="trialing", trial_start=f.created - 10, trial_end=f.created - 10 + 14 * 86400)
        f.session["payment_status"] = "no_payment_required"
    assert f.send(f.event())["status"] == "ok"
    assert next(iter(f.analytics.values()))["meta"]["is_trial"] is trial


def test_trial_started_uses_original_exact_duration_not_catalog(conversion_system):
    f = conversion_system
    f.sub.update(status="trialing", trial_start=f.created - 10, trial_end=f.created - 10 + 14 * 86400)
    assert f.send(f.event("customer.subscription.created"))["status"] == "ok"
    assert next(iter(f.analytics.values()))["meta"] == {"tier": "pro", "trial_days": 14}


@pytest.mark.parametrize("field,value", [
    ("amount_total", None), ("amount_total", True), ("amount_total", -1),
    ("currency", "jpy"), ("payment_status", "unpaid"), ("status", "open"),
    ("client_reference_id", "foreign-user"), ("subscription", "sub_foreign"),
])
def test_unknown_or_foreign_checkout_facts_suppress_positive(conversion_system, field, value):
    f = conversion_system
    ev = f.event(); ev["data"]["object"][field] = value
    assert f.send(ev)["status"] == "ok"
    assert not f.analytics


@pytest.mark.parametrize("bad", [None, "unknown", "fractional", "expired", "changed"])
def test_trial_missing_malformed_or_stale_bounds_never_become_guessed_days(conversion_system, bad):
    f = conversion_system
    f.sub.update(status="trialing", trial_start=f.created - 10, trial_end=f.created - 10 + 14 * 86400)
    ev = f.event("customer.subscription.created")
    if bad is None:
        ev["data"]["object"].pop("trial_end")
    elif bad == "unknown":
        ev["data"]["object"]["trial_end"] = "tomorrow"
    elif bad == "fractional":
        f.sub["trial_end"] += 1; ev = f.event("customer.subscription.created")
    elif bad == "expired":
        f.sub["status"] = "active"
    else:
        f.sub["trial_end"] += 86400
    assert f.send(ev)["status"] == "ok"
    assert not f.analytics


def test_delayed_checkout_preserves_trial_at_event_clock_after_current_status_changes(conversion_system):
    f = conversion_system
    # Stripe retains historical trial bounds after conversion. Current active status
    # cannot rewrite the original checkout's trial flag or provider event timestamp.
    f.sub.update(trial_start=f.created - 10, trial_end=f.created - 10 + 14 * 86400)
    f.session.update(amount_total=0, payment_status="no_payment_required")
    assert f.sub["status"] == "active"
    assert f.send(f.event())["status"] == "ok"
    item = next(iter(f.analytics.values()))
    assert item["meta"]["is_trial"] is True
    assert item["client_ts"] == billing._iso(f.created)


@pytest.mark.parametrize("raw_offer", [None, "", "unrecognized_offer", True])
def test_missing_or_unqualified_offer_remains_unknown_not_known_none(conversion_system, raw_offer):
    f = conversion_system
    if raw_offer is not None:
        f.session["metadata"]["mm_offer"] = raw_offer
        f.sub["metadata"]["mm_offer"] = raw_offer
    assert f.send(f.event())["status"] == "ok"
    assert next(iter(f.analytics.values()))["meta"]["offer_key"] is None


def test_qualified_offer_uses_exact_catalog_key_without_inventing_amount(conversion_system):
    f = conversion_system
    price = f.sub["items"]["data"][0]["price"]
    price["lookup_key"] = "pro_2026_v2_annual"
    price["recurring"]["interval"] = "year"
    f.session["metadata"]["mm_offer"] = f.sub["metadata"]["mm_offer"] = "founding_pro"
    assert f.send(f.event())["status"] == "ok"
    props = next(iter(f.analytics.values()))["meta"]
    assert props["offer_key"] == "founding_pro" and props["interval"] == "year"
    assert props["amount_cents"] == 12345  # the exact receipt, never catalog 90000/130800


@pytest.mark.parametrize("mismatch", ["customer", "user", "price", "mode", "bounds", "cadence"])
def test_contradictory_provider_linkage_or_unknown_facts_suppress_conversion(conversion_system, mismatch):
    import copy
    f = conversion_system
    ev = f.event()
    if mismatch == "customer":
        f.session["customer"] = "cus_foreign"
    elif mismatch == "user":
        f.sub["metadata"]["mm_user_id"] = "foreign-user"
    elif mismatch == "price":
        f.session["line_items"] = copy.deepcopy(f.session["line_items"])
        f.session["line_items"]["data"][0]["price"]["id"] = "price_original_other"
    elif mismatch == "mode":
        f.session["livemode"] = True
    elif mismatch == "bounds":
        f.sub.pop("trial_end")
    else:
        f.sub["items"]["data"][0]["price"]["recurring"]["interval_count"] = True
    assert f.send(ev)["status"] == "ok"
    assert not f.analytics


def test_legacy_analytics_failure_remains_best_effort(conversion_system):
    f = conversion_system
    f.failure["mode"] = "analytics"
    f.main._mm_analytics_insert([{"eid": "legacy-fixture", "type": "pageview"}])
    assert not f.analytics


def test_server_analytics_missing_configuration_cannot_settle_event(conversion_system, monkeypatch):
    f = conversion_system
    monkeypatch.setattr(f.main, "SUPABASE_SERVICE_ROLE_KEY", "")
    with pytest.raises(RuntimeError, match="not configured"):
        f.send(f.event())
    assert f.row["tier"] == "pro" and not f.ledger and not f.analytics


def test_client_eid_collision_is_not_a_falsely_acknowledged_conversion(conversion_system):
    import uuid
    f = conversion_system
    eid = str(uuid.uuid5(uuid.NAMESPACE_URL, "mastermind:stripe:evt_conversion:checkout.completed"))
    foreign = {"eid": eid, "type": "intelligence.viewed", "site": "macro", "user_id": f.uid,
               "client_ts": billing._iso(f.created), "meta": {"rows_visible": 3}}
    f.analytics[eid] = foreign.copy()
    with pytest.raises(RuntimeError, match="identity conflict"):
        f.send(f.event())
    assert f.row["tier"] == "pro" and not f.ledger
    assert f.analytics == {eid: foreign}  # first fact is retained, never overwritten/coerced
    assert not any(r["type"] == "checkout.completed" for r in f.analytics.values())


@pytest.mark.parametrize("etype", ["checkout.session.completed", "customer.subscription.created"])
@pytest.mark.parametrize("page_state", ["missing", True, None])
def test_incomplete_subscription_page_cannot_qualify_single_price_conversion(conversion_system, etype, page_state):
    f = conversion_system
    if etype == "customer.subscription.created":
        f.sub.update(status="trialing", trial_start=f.created - 10, trial_end=f.created - 10 + 14 * 86400)
    ev = f.event(etype)
    # A visible first item is insufficient: the fresh provider page must attest
    # that no unseen subscription item can change the purported single purchase.
    if page_state == "missing":
        f.sub["items"].pop("has_more")
    else:
        f.sub["items"]["has_more"] = page_state
    assert f.send(ev)["status"] == "ok"
    assert not f.analytics and not f.requests
