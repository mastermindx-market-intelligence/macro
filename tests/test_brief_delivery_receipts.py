"""Focused tests for ``observe_delivery_write``.

Purely synthetic: the PostgREST transport and the clock are stubs, so nothing
here touches a live database, network, filesystem or credentials.
"""

from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import io
import json
import pathlib
import sys
import urllib.error
from datetime import datetime, timedelta, timezone

import pytest


def _load_module():
    candidates = [
        pathlib.Path(__file__).resolve().parent / "brief_delivery_receipts.py",
        pathlib.Path(__file__).resolve().parent.parent / "engine" / "brief_delivery_receipts.py",
    ]
    try:
        from engine import brief_delivery_receipts as module

        return module
    except ImportError:
        pass
    spec = None
    for candidate in candidates:
        if candidate.is_file():
            spec = importlib.util.spec_from_file_location(
                "brief_delivery_receipts_under_test", candidate
            )
            break
    assert spec is not None and spec.loader is not None, "module file not found"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolves annotations via sys.modules
    spec.loader.exec_module(module)
    return module


mod = _load_module()

SUBSCRIPTION_ID = "11111111-2222-5333-8444-555555555555"
OTHER_SUBSCRIPTION_ID = "99999999-8888-5777-8666-555555555555"
OWNER_ID = "aaaaaaaa-bbbb-5ccc-8ddd-eeeeeeeeeeee"
OTHER_OWNER_ID = "77777777-6666-5ddd-8eee-ffffffffffff"
DELIVERY_ID = "24b3da20-9a6f-5e1f-8a0b-1c2d3e4f5a6b"
OTHER_DELIVERY_ID = "6c9cf3ae-1f2d-5b3e-9a4c-5d6e7f8091a2"
SLOT = "2026-11-03"
OBSERVED = datetime(2026, 11, 3, 12, 30, 0, tzinfo=timezone.utc)
BODY = {"headline": "nightly recap", "sections": ["top", "markets"], "words": 812}


def _row(**overrides):
    row = {
        "subscription_id": SUBSCRIPTION_ID,
        "slot_asof": SLOT,
        "state": "ready",
        "degraded_reason": None,
        "artifact_asof": "2026-11-03T05:30:00+05:30",
        "body": BODY,
    }
    row.update(overrides)
    return row


def _persisted_row(**overrides):
    # Same instant as the requested artifact_asof, expressed in UTC instead.
    row = {
        "delivery_id": DELIVERY_ID,
        "subscription_id": SUBSCRIPTION_ID,
        "slot_asof": SLOT,
        "state": "ready",
        "degraded_reason": None,
        "artifact_asof": "2026-11-03T00:00:00+00:00",
        "body": BODY,
        "brief_subscriptions": {"user_id": OWNER_ID},
    }
    row.update(overrides)
    return row


class Transport:
    """Synthetic ``_pg`` stand-in that records every call and raises on
    any unexpected method/path shape."""

    def __init__(self, *, post_error=None, post_result=None, rows=None, get_error=None):
        self.calls = []
        self.post_error = post_error
        self.post_result = post_result
        self.rows = rows
        self.get_error = get_error

    def __call__(self, method, path, body=None, prefer=None, timeout=None):
        self.calls.append(
            {"method": method, "path": path, "body": body, "prefer": prefer, "timeout": timeout}
        )
        if method == "POST":
            if self.post_error is not None:
                raise self.post_error
            return self.post_result
        if method == "GET":
            if self.get_error is not None:
                raise self.get_error
            return self.rows
        raise AssertionError(f"unexpected method {method!r}")


def _http_error(code, payload=b'{"message":"provider failure","secret_token":"do-not-leak"}'):
    return urllib.error.HTTPError(
        "https://supabase.invalid/rest/v1/brief_deliveries",
        code,
        "err",
        {},
        io.BytesIO(payload),
    )


def _clock():
    return OBSERVED


def _posts(transport):
    return [c for c in transport.calls if c["method"] == "POST"]


def _gets(transport):
    return [c for c in transport.calls if c["method"] == "GET"]


def _assert_incumbent_post(transport):
    (post,) = _posts(transport)
    assert post["path"] == "brief_deliveries?on_conflict=subscription_id,slot_asof"
    assert post["prefer"] == "resolution=ignore-duplicates,return=minimal"
    assert post["body"] == _row()
    assert post["timeout"] == 6


def _assert_single_readback_get(transport):
    (get,) = _gets(transport)
    assert get["timeout"] == 6
    assert get["path"].startswith("brief_deliveries?select=")
    assert "brief_subscriptions!inner(user_id)" in get["path"]
    assert f"subscription_id=eq.{SUBSCRIPTION_ID}" in get["path"]
    assert f"slot_asof=eq.{SLOT}" in get["path"]
    assert f"brief_subscriptions.user_id=eq.{OWNER_ID}" in get["path"]
    assert "limit=2" in get["path"]
    assert "delivery_id,subscription_id,slot_asof" in get["path"]


# --- acknowledged / ignored duplicate -------------------------------------


def test_acknowledged_insert_reads_back_the_persisted_row():
    transport = Transport(rows=[_persisted_row()])
    observation = mod.observe_delivery_write(transport, _row(), OWNER_ID, clock=_clock)

    assert observation.post_outcome is mod.PostOutcome.ACKNOWLEDGED
    assert observation.reason is mod.ObservationReason.READBACK_MATCHED
    receipt = observation.receipt
    assert receipt is not None
    assert receipt.delivery_id == DELIVERY_ID  # persisted value, never generated
    assert receipt.slot_asof == SLOT
    assert receipt.observed_at == "2026-11-03T12:30:00+00:00"
    assert len(receipt.observation_sha256) == 64
    int(receipt.observation_sha256, 16)  # pure hex digest

    assert len(transport.calls) == 2
    _assert_incumbent_post(transport)
    _assert_single_readback_get(transport)


@pytest.mark.parametrize("post_result", [None, []])
def test_ignored_duplicate_post_still_reads_back(post_result):
    transport = Transport(post_result=post_result, rows=[_persisted_row()])
    observation = mod.observe_delivery_write(transport, _row(), OWNER_ID, clock=_clock)

    assert observation.post_outcome is mod.PostOutcome.ACKNOWLEDGED
    assert observation.receipt is not None
    assert observation.receipt.delivery_id == DELIVERY_ID
    assert len(_posts(transport)) == 1
    assert len(_gets(transport)) == 1


def test_duplicate_conflict_23505_reads_back():
    transport = Transport(
        post_error=_http_error(409, b'{"code":"23505","message":"duplicate key value"}'),
        rows=[_persisted_row()],
    )
    observation = mod.observe_delivery_write(transport, _row(), OWNER_ID, clock=_clock)

    assert observation.post_outcome is mod.PostOutcome.DUPLICATE
    assert observation.reason is mod.ObservationReason.READBACK_MATCHED
    assert observation.receipt is not None
    assert observation.receipt.delivery_id == DELIVERY_ID
    assert len(_posts(transport)) == 1
    assert len(_gets(transport)) == 1


# --- lost write response ---------------------------------------------------


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("lost response"),
        urllib.error.URLError("lost response"),
        ConnectionError("lost response"),
    ],
)
def test_lost_write_response_recovers_with_exactly_one_get(error):
    transport = Transport(post_error=error, rows=[_persisted_row()])
    observation = mod.observe_delivery_write(transport, _row(), OWNER_ID, clock=_clock)

    assert observation.post_outcome is mod.PostOutcome.AMBIGUOUS
    assert observation.reason is mod.ObservationReason.READBACK_MATCHED
    assert observation.receipt is not None
    assert observation.receipt.delivery_id == DELIVERY_ID
    assert len(_posts(transport)) == 1  # never a second POST
    assert len(_gets(transport)) == 1


# --- refusals: no read recovery -------------------------------------------


@pytest.mark.parametrize("code", [400, 401, 403, 404, 429, 500, 503])
def test_provider_http_refusal_stops_before_any_readback(code):
    transport = Transport(post_error=_http_error(code), rows=[_persisted_row()])
    observation = mod.observe_delivery_write(transport, _row(), OWNER_ID, clock=_clock)

    assert observation.post_outcome is (mod.PostOutcome.AMBIGUOUS if code >= 500 else mod.PostOutcome.REFUSED)
    expected = (mod.ObservationReason.PERMISSION_DENIED if code in {401, 403}
                else mod.ObservationReason.PROVIDER_REFUSED if code == 429
                else mod.ObservationReason.HTTP_UNCONFIRMED if code >= 500
                else mod.ObservationReason.REQUEST_REJECTED)
    assert observation.reason is expected
    assert observation.receipt is None
    assert len(transport.calls) == 1  # exactly the original POST


def test_wrong_409_without_unique_violation_is_refused():
    transport = Transport(
        post_error=_http_error(409, b'{"code":"23514","message":"check constraint"}'),
        rows=[_persisted_row()],
    )
    observation = mod.observe_delivery_write(transport, _row(), OWNER_ID, clock=_clock)

    assert observation.post_outcome is mod.PostOutcome.REFUSED
    assert observation.reason is mod.ObservationReason.REQUEST_REJECTED
    assert observation.receipt is None
    assert len(transport.calls) == 1


def test_sql_permission_code_is_permission_denied_without_readback():
    transport = Transport(
        post_error=_http_error(
            403, b'{"code":"42501","message":"permission denied for table brief_deliveries"}'
        ),
        rows=[_persisted_row()],
    )
    observation = mod.observe_delivery_write(transport, _row(), OWNER_ID, clock=_clock)

    assert observation.post_outcome is mod.PostOutcome.REFUSED
    assert observation.reason is mod.ObservationReason.PERMISSION_DENIED
    assert observation.receipt is None
    assert len(transport.calls) == 1


def test_programmer_failure_is_unconfirmed_without_readback():
    transport = Transport(post_error=TypeError("bad pg signature"), rows=[_persisted_row()])
    observation = mod.observe_delivery_write(transport, _row(), OWNER_ID, clock=_clock)

    assert observation.post_outcome is mod.PostOutcome.AMBIGUOUS
    assert observation.reason is mod.ObservationReason.PROGRAMMER_ERROR
    assert observation.receipt is None
    assert len(transport.calls) == 1


def test_refusal_does_not_leak_provider_details():
    transport = Transport(
        post_error=_http_error(500, b'{"message":"role private_role does not exist token=xyz"}')
    )
    observation = mod.observe_delivery_write(transport, _row(), OWNER_ID, clock=_clock)
    rendered = f"{observation!r} {observation} {observation.reason.value}"
    assert "private_role" not in rendered
    assert "token=xyz" not in rendered
    assert "provider failure" not in rendered


# --- changed persisted row: no receipt -------------------------------------


@pytest.mark.parametrize(
    "override",
    [
        {"body": {**BODY, "words": 813}},
        {"body": [BODY]},
        {"slot_asof": "2026-11-02"},
        {"subscription_id": OTHER_SUBSCRIPTION_ID},
        {"state": "degraded"},
        {"degraded_reason": "late_source"},
        {"artifact_asof": "2026-11-03T00:00:01+00:00"},
        {"artifact_asof": None},
        {"delivery_id": "not-a-uuid"},
        {"delivery_id": DELIVERY_ID.upper()},
        {"delivery_id": None},
        {"brief_subscriptions": {"user_id": OTHER_OWNER_ID}},
        {"brief_subscriptions": None},
        {"extra_field": 1},
    ],
)
def test_changed_persisted_row_yields_no_receipt(override):
    transport = Transport(rows=[_persisted_row(**override)])
    observation = mod.observe_delivery_write(transport, _row(), OWNER_ID, clock=_clock)

    assert observation.post_outcome is mod.PostOutcome.ACKNOWLEDGED
    assert observation.reason is mod.ObservationReason.READBACK_MISMATCH
    assert observation.receipt is None
    assert len(_posts(transport)) == 1  # no retry, no recovery


def test_persisted_row_with_missing_field_yields_no_receipt():
    row = _persisted_row()
    del row["artifact_asof"]
    transport = Transport(rows=[row])
    observation = mod.observe_delivery_write(transport, _row(), OWNER_ID, clock=_clock)
    assert observation.receipt is None
    assert observation.reason is mod.ObservationReason.READBACK_MISMATCH


# --- missing / multiple / malformed readback -------------------------------


def test_missing_row_is_missing():
    transport = Transport(rows=[])
    observation = mod.observe_delivery_write(transport, _row(), OWNER_ID, clock=_clock)

    assert observation.post_outcome is mod.PostOutcome.ACKNOWLEDGED
    assert observation.reason is mod.ObservationReason.READBACK_MISSING
    assert observation.receipt is None
    assert len(_gets(transport)) == 1


def test_multiple_rows_are_ambiguous():
    transport = Transport(
        rows=[_persisted_row(), _persisted_row(delivery_id=OTHER_DELIVERY_ID)]
    )
    observation = mod.observe_delivery_write(transport, _row(), OWNER_ID, clock=_clock)

    assert observation.reason is mod.ObservationReason.READBACK_AMBIGUOUS
    assert observation.receipt is None


@pytest.mark.parametrize("rows", [None, {}, {"delivery_id": DELIVERY_ID}, "rows"])
def test_malformed_readback_response_is_unavailable(rows):
    transport = Transport(rows=rows)
    observation = mod.observe_delivery_write(transport, _row(), OWNER_ID, clock=_clock)

    assert observation.reason is mod.ObservationReason.READBACK_UNAVAILABLE
    assert observation.receipt is None


@pytest.mark.parametrize(
    "error",
    [
        urllib.error.URLError("connection reset"),
        TimeoutError("read timeout"),
        ConnectionError("refused"),
        ValueError("bad json"),
    ],
)
def test_readback_failure_returns_no_receipt_and_no_retry(error):
    transport = Transport(get_error=error)
    observation = mod.observe_delivery_write(transport, _row(), OWNER_ID, clock=_clock)

    assert observation.post_outcome is mod.PostOutcome.ACKNOWLEDGED
    assert observation.reason is mod.ObservationReason.READBACK_UNAVAILABLE
    assert observation.receipt is None
    assert len(_posts(transport)) == 1
    assert len(_gets(transport)) == 1  # one bounded GET, never retried


# --- dry run / not ready / invalid: zero calls -----------------------------


def test_dry_run_makes_no_calls():
    transport = Transport(rows=[_persisted_row()])
    observation = mod.observe_delivery_write(transport, _row(), OWNER_ID, dry_run=True, clock=_clock)

    assert observation.post_outcome is mod.PostOutcome.NOT_ATTEMPTED
    assert observation.reason is mod.ObservationReason.DRY_RUN
    assert observation.receipt is None
    assert transport.calls == []


@pytest.mark.parametrize(
    "row",
    [
        _row(state="degraded"),
        _row(state="degraded", degraded_reason="late_source"),
        _row(degraded_reason="late_source"),
    ],
)
def test_not_ready_row_is_not_attempted(row):
    transport = Transport()
    observation = mod.observe_delivery_write(transport, row, OWNER_ID, clock=_clock)

    assert observation.post_outcome is mod.PostOutcome.NOT_ATTEMPTED
    assert observation.reason is mod.ObservationReason.INPUT_NOT_READY
    assert observation.receipt is None
    assert transport.calls == []


@pytest.mark.parametrize(
    "row,owner",
    [
        (_row(subscription_id=OWNER_ID.upper()), OWNER_ID),  # non-canonical
        (_row(subscription_id=DELIVERY_ID[:-1] + "g"), OWNER_ID),
        (_row(subscription_id=12345), OWNER_ID),
        (_row(slot_asof="2026-11-3"), OWNER_ID),
        (_row(slot_asof="2026-11-03T00:00:00"), OWNER_ID),
        (_row(slot_asof="20261103"), OWNER_ID),
        (_row(artifact_asof="2026-11-03T05:30:00"), OWNER_ID),  # naive
        (_row(artifact_asof="not-a-time"), OWNER_ID),
        (_row(artifact_asof=123), OWNER_ID),
        (_row(body={"x": float("nan")}), OWNER_ID),
        (_row(body=object()), OWNER_ID),
        ({**_row(), "extra": 1}, OWNER_ID),
        ({k: v for k, v in _row().items() if k != "body"}, OWNER_ID),
        ("row", OWNER_ID),
        (None, OWNER_ID),
        (_row(), "owner"),
        (_row(), OWNER_ID.upper()),
        (_row(), DELIVERY_ID[:-1] + "g"),
        (_row(), 42),
    ],
)
def test_invalid_input_is_not_attempted(row, owner):
    transport = Transport(rows=[_persisted_row()])
    observation = mod.observe_delivery_write(transport, row, owner, clock=_clock)

    assert observation.post_outcome is mod.PostOutcome.NOT_ATTEMPTED
    assert observation.reason is mod.ObservationReason.INPUT_INVALID
    assert observation.receipt is None
    assert transport.calls == []


# --- body budget -----------------------------------------------------------


def test_null_body_qualifies_only_against_null_persisted_body():
    transport = Transport(rows=[_persisted_row(body=None)])
    observation = mod.observe_delivery_write(transport, _row(body=None), OWNER_ID, clock=_clock)
    assert observation.receipt is not None

    transport = Transport(rows=[_persisted_row()])
    observation = mod.observe_delivery_write(transport, _row(body=None), OWNER_ID, clock=_clock)
    assert observation.receipt is None
    assert observation.reason is mod.ObservationReason.READBACK_MISMATCH


def test_body_at_budget_limit_is_accepted():
    limit = mod.MAX_BODY_BYTES
    body = {"pad": "x" * (limit - len('{"pad":""}'))}
    assert len(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")) == limit
    transport = Transport(rows=[_persisted_row(body=body)])
    observation = mod.observe_delivery_write(transport, _row(body=body), OWNER_ID, clock=_clock)
    assert observation.receipt is not None


def test_body_over_budget_rejected_before_any_call():
    body = {"pad": "x" * mod.MAX_BODY_BYTES}
    transport = Transport()
    observation = mod.observe_delivery_write(transport, _row(body=body), OWNER_ID, clock=_clock)

    assert observation.reason is mod.ObservationReason.INPUT_INVALID
    assert observation.receipt is None
    assert transport.calls == []


def test_oversized_persisted_body_is_not_qualified():
    body = {"pad": "x" * mod.MAX_BODY_BYTES}
    transport = Transport(rows=[_persisted_row(body=body)])
    observation = mod.observe_delivery_write(transport, _row(), OWNER_ID, clock=_clock)

    assert observation.reason is mod.ObservationReason.READBACK_MISMATCH
    assert observation.receipt is None


# --- timezone equivalence ---------------------------------------------------


@pytest.mark.parametrize(
    "artifact",
    [
        "2026-11-03T05:30:00+05:30",
        "2026-11-02T20:00:00-04:00",
        "2026-11-03T00:00:00Z",
        "2026-11-03T00:00:00+00:00",
    ],
)
def test_artifact_instant_matches_across_equivalent_offsets(artifact):
    transport = Transport(rows=[_persisted_row()])
    observation = mod.observe_delivery_write(
        transport, _row(artifact_asof=artifact), OWNER_ID, clock=_clock
    )
    assert observation.receipt is not None, artifact


def test_artifact_datetime_input_is_normalized():
    artifact = datetime(2026, 11, 3, 5, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    transport = Transport(rows=[_persisted_row()])
    observation = mod.observe_delivery_write(
        transport, _row(artifact_asof=artifact), OWNER_ID, clock=_clock
    )
    assert observation.receipt is not None


def test_artifact_instant_difference_is_rejected():
    transport = Transport(rows=[_persisted_row()])
    observation = mod.observe_delivery_write(
        transport,
        _row(artifact_asof="2026-11-03T05:31:00+05:30"),
        OWNER_ID,
        clock=_clock,
    )
    assert observation.receipt is None
    assert observation.reason is mod.ObservationReason.READBACK_MISMATCH


# --- digest contract --------------------------------------------------------


def test_digest_matches_documented_canonical_document():
    transport = Transport(rows=[_persisted_row()])
    observation = mod.observe_delivery_write(transport, _row(), OWNER_ID, clock=_clock)

    document = {
        "schema": "macro.brief_delivery.owner_readback.v1",
        "delivery_id": DELIVERY_ID,
        "subscription_id": SUBSCRIPTION_ID,
        "slot_asof": SLOT,
        "state": "ready",
        "degraded_reason": None,
        "artifact_asof": "2026-11-03T00:00:00+00:00",
        "body": BODY,
        "owner_user_id": OWNER_ID,
        "observed_at": "2026-11-03T12:30:00+00:00",
    }
    expected = hashlib.sha256(
        json.dumps(
            document, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    ).hexdigest()
    assert observation.receipt.observation_sha256 == expected


def test_digest_is_deterministic_and_instant_sensitive():
    a = mod.observe_delivery_write(Transport(rows=[_persisted_row()]), _row(), OWNER_ID, clock=_clock)
    b = mod.observe_delivery_write(Transport(rows=[_persisted_row()]), _row(), OWNER_ID, clock=_clock)
    assert a.receipt.observation_sha256 == b.receipt.observation_sha256

    later = lambda: OBSERVED + timedelta(minutes=1)  # noqa: E731
    c = mod.observe_delivery_write(Transport(rows=[_persisted_row()]), _row(), OWNER_ID, clock=later)
    assert c.receipt.observed_at != a.receipt.observed_at
    assert c.receipt.observation_sha256 != a.receipt.observation_sha256


def test_naive_clock_is_read_as_utc():
    transport = Transport(rows=[_persisted_row()])
    observation = mod.observe_delivery_write(
        transport, _row(), OWNER_ID, clock=lambda: datetime(2026, 11, 3, 12, 30)
    )
    assert observation.receipt.observed_at == "2026-11-03T12:30:00+00:00"


def test_default_clock_is_utc():
    transport = Transport(rows=[_persisted_row()])
    observation = mod.observe_delivery_write(transport, _row(), OWNER_ID)
    assert observation.receipt is not None
    assert observation.receipt.observed_at.endswith("+00:00")


# --- shape of the returned types --------------------------------------------


def test_observations_are_frozen():
    observation = mod.observe_delivery_write(
        Transport(rows=[_persisted_row()]), _row(), OWNER_ID, clock=_clock
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        observation.post_outcome = mod.PostOutcome.REFUSED  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        observation.receipt.delivery_id = "x"  # type: ignore[misc]


def test_receipt_has_exactly_the_documented_fields():
    assert {f.name for f in dataclasses.fields(mod.PersistedDeliveryObservation)} == {
        "delivery_id",
        "slot_asof",
        "observed_at",
        "observation_sha256",
    }


def test_outcomes_and_reasons_are_closed_sets():
    assert {m.value for m in mod.PostOutcome} == {
        "ACKNOWLEDGED",
        "DUPLICATE",
        "AMBIGUOUS",
        "REFUSED",
        "NOT_ATTEMPTED",
    }
    assert {m.value for m in mod.ObservationReason} == {
        "DRY_RUN",
        "INPUT_NOT_READY",
        "INPUT_INVALID",
        "READBACK_MATCHED",
        "READBACK_MISSING",
        "READBACK_AMBIGUOUS",
        "READBACK_MISMATCH",
        "READBACK_UNAVAILABLE",
        "PROVIDER_REFUSED",
        "PERMISSION_DENIED",
        "PROGRAMMER_ERROR",
        "HTTP_UNCONFIRMED",
        "REQUEST_REJECTED",
    }


@pytest.mark.parametrize("body", [b'{"code":"42501","detail":"23505"}', b'{"code":"XX000","detail":"23505"}', b'{"code":"23505","message":"permission denied"}', b'23505 is just detail, not a code'])
def test_conflict_cannot_disguise_a_refusal_as_duplicate_recovery(body):
    transport = Transport(post_error=_http_error(409, body), rows=[_persisted_row()])
    observed = mod.observe_delivery_write(transport, _row(), OWNER_ID, clock=_clock)
    assert observed.post_outcome is mod.PostOutcome.REFUSED
    assert observed.receipt is None
    assert len(transport.calls) == 1


def test_lone_surrogate_is_an_invalid_source_without_network():
    row = _row(); row["body"] = {"text": "\ud800"}
    transport = Transport(rows=[_persisted_row()])
    observed = mod.observe_delivery_write(transport, row, OWNER_ID, clock=_clock)
    assert observed.post_outcome is mod.PostOutcome.NOT_ATTEMPTED
    assert transport.calls == []


def test_post_transport_mutation_cannot_rewrite_the_frozen_expected_source():
    row = _row()
    def pg(method, path, **kwargs):
        if method == "POST":
            kwargs["body"]["body"] = {"changed": True}
            row["body"] = {"changed": True}
            return None
        persisted = _persisted_row(); persisted["body"] = {"changed": True}
        return [persisted]
    observed = mod.observe_delivery_write(pg, row, OWNER_ID, clock=_clock)
    assert observed.receipt is None
    assert observed.reason is mod.ObservationReason.READBACK_MISMATCH


def test_readback_auth_refusal_retains_original_post_phase_without_retry():
    transport = Transport(get_error=_http_error(403), rows=[_persisted_row()])
    observed = mod.observe_delivery_write(transport, _row(), OWNER_ID, clock=_clock)
    assert observed.post_outcome is mod.PostOutcome.ACKNOWLEDGED
    assert observed.reason is mod.ObservationReason.PERMISSION_DENIED
    assert observed.receipt is None
    assert len(transport.calls) == 2
