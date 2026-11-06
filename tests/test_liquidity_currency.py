# tests/test_liquidity_currency.py
"""Success and negative coverage for the dated trading-currency validator.

Only the public entry point ``qualify_currency`` is exercised: every test
asserts either the exact qualification contract or a None result, and no test
presents synthetic data as scientific/product acceptance.
"""

import copy
import hashlib
import json
from datetime import date, datetime, timedelta, timezone

import pytest

from engine.liquidity_currency import qualify_currency

TICKER = "MU"
SCHEMA_IN = "liquidity_currency_observations.v1"
SCHEMA_OUT = "liquidity_currency_dated.v1"
PATH = "/v3/reference/tickers/MU"
RECORDED_AT = datetime(2026, 10, 20, 8, 0, tzinfo=timezone.utc)
BODY_LIMIT = 131072


def _sessions():
    sessions = []
    day = date(2026, 9, 21)
    while len(sessions) < 20:
        if day.weekday() < 5:
            sessions.append(day)
        day += timedelta(days=1)
    return sessions


SESSIONS = _sessions()


def _body(*, status="OK", ticker=TICKER, currency="usd", results_extra=None, top_extra=None, raw=None):
    if raw is not None:
        return raw
    results = {
        "ticker": ticker,
        "currency_name": currency,
        "market": "stocks",
        "locale": "us",
        "type": "ADRC",
        "active": True,
        "currency_symbol": "$",
    }
    if results_extra:
        results.update(results_extra)
    payload = {"status": status, "results": results}
    if top_extra:
        payload.update(top_extra)
    return json.dumps(payload)


def _digest(body):
    raw = body if isinstance(body, bytes) else body.encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _observation(session, index, *, body=None, drop=None, **overrides):
    body = _body() if body is None else body
    observation = {
        "session": session.isoformat(),
        "request_path": PATH,
        "request_params": {"date": session.isoformat()},
        "request_started_at": f"2026-10-20T07:00:{index:02d}Z",
        "response_received_at": f"2026-10-20T07:00:{index + 1:02d}Z",
        "http_status": 200,
        "response_sha256": _digest(body),
        "response_body": body,
    }
    observation.update(overrides)
    for key in drop or ():
        del observation[key]
    return observation


def _evidence(bodies=None):
    return {
        "schema": SCHEMA_IN,
        "ticker": TICKER,
        "observations": [
            _observation(session, index, body=None if bodies is None else bodies(index))
            for index, session in enumerate(SESSIONS)
        ],
    }


def _mutate(base=None, **changes):
    evidence = copy.deepcopy(_evidence() if base is None else base)
    evidence.update(changes)
    return evidence


def _obs(index, base=None, **changes):
    evidence = copy.deepcopy(_evidence() if base is None else base)
    evidence["observations"][index].update(changes)
    return evidence


def _drop(index, key, base=None):
    evidence = copy.deepcopy(_evidence() if base is None else base)
    del evidence["observations"][index][key]
    return evidence


def _canonical_sha(evidence):
    rendered = json.dumps(
        evidence, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _padded_body(total_bytes):
    payload = {"status": "OK", "results": {"ticker": TICKER, "currency_name": "usd"}, "note": ""}
    payload["note"] = "x" * (total_bytes - len(json.dumps(payload).encode("utf-8")))
    body = json.dumps(payload)
    assert len(body.encode("utf-8")) == total_bytes
    return body


def qualify(evidence, *, ticker=TICKER, sessions=None, recorded_at=RECORDED_AT):
    return qualify_currency(
        evidence,
        ticker=ticker,
        sessions=SESSIONS if sessions is None else sessions,
        recorded_at=recorded_at,
    )


# --------------------------------------------------------------------------
# success
# --------------------------------------------------------------------------


def test_success_exact_output_contract():
    evidence = _evidence()
    assert qualify(evidence) == {
        "schema": SCHEMA_OUT,
        "ticker": TICKER,
        "currency": "USD",
        "source_sha256": _canonical_sha(evidence),
        "source_asof": SESSIONS[-1].isoformat(),
        "dated_sessions": [day.isoformat() for day in SESSIONS],
        "observation_started_at": "2026-10-20T07:00:00Z",
        "observation_completed_at": "2026-10-20T07:00:20Z",
        "known_at": None,
        "published_at": None,
        "basis": "retrospective_dated_reference",
    }
    assert len(SESSIONS) == 20


def test_sessions_are_20_distinct_ascending_dates():
    assert len(SESSIONS) == 20
    assert all(type(day) is date for day in SESSIONS)
    assert all(earlier < later for earlier, later in zip(SESSIONS, SESSIONS[1:]))


def test_success_never_leaks_raw_bodies():
    rendered = json.dumps(qualify(_evidence()))
    assert "response_body" not in rendered
    assert '"status"' not in rendered
    assert "OK" not in rendered.split("basis")[0]


def test_success_is_deterministic_and_key_order_insensitive():
    evidence = _evidence()
    first = qualify(evidence)
    reordered = {key: evidence[key] for key in reversed(list(evidence))}
    reordered["observations"] = [
        dict(reversed(list(observation.items()))) for observation in reordered["observations"]
    ]
    second = qualify(reordered)
    assert first is not None and second is not None
    assert first == second
    assert first["source_sha256"] == _canonical_sha(evidence)


def test_success_currency_case_insensitive_usd_only():
    assert qualify(_evidence(bodies=lambda _: _body(currency="USD"))) is not None
    assert qualify(_evidence(bodies=lambda _: _body(currency="Usd"))) is not None


def test_success_extra_provider_fields_allowed():
    bodies = lambda _: _body(results_extra={"filing_date": "2026-10-17"}, top_extra={"next_url": "x"})  # noqa: E731
    assert qualify(_evidence(bodies=bodies)) is not None


def test_success_body_exactly_at_size_bound():
    edge = _padded_body(BODY_LIMIT)
    assert qualify(_evidence(bodies=lambda _: edge)) is not None


def test_success_twenty_max_bodies_stay_under_receipt_bound():
    edge = _padded_body(BODY_LIMIT)
    assert qualify(_evidence(bodies=lambda _: edge)) is not None


# --------------------------------------------------------------------------
# body content negatives
# --------------------------------------------------------------------------


def test_mutated_body_without_hash_update_rejected():
    evidence = _obs(7, response_body=_body(currency="EUR"))
    assert qualify(evidence) is None


def test_mutated_hash_without_body_change_rejected():
    evidence = _obs(3, response_sha256="0" * 64)
    assert qualify(evidence) is None


def test_wrong_currency_rejected_even_with_consistent_hash():
    for currency in ("eur", "EUR", "gbp", "usdollar", "usd ", ""):
        evidence = _evidence(bodies=lambda _, c=currency: _body(currency=c))
        assert qualify(evidence) is None, currency


def test_missing_currency_field_rejected():
    body = json.dumps({"status": "OK", "results": {"ticker": TICKER}})
    assert qualify(_evidence(bodies=lambda _: body)) is None


def test_wrong_status_rejected():
    for status in ("NOT_FOUND", "ok", "DELAYED", "", 200, None):
        evidence = _evidence(bodies=lambda _, s=status: _body(status=s))
        assert qualify(evidence) is None, status


def test_missing_status_rejected():
    body = json.dumps({"results": {"ticker": TICKER, "currency_name": "usd"}})
    assert qualify(_evidence(bodies=lambda _: body)) is None


def test_body_not_a_json_object_rejected():
    for raw in ("[]", '"ok"', "42", "null", ""):
        assert qualify(_evidence(bodies=lambda _, r=raw: _body(raw=r))) is None, raw


def test_malformed_json_body_rejected():
    assert qualify(_evidence(bodies=lambda _: _body(raw="{not json"))) is None


def test_results_missing_or_wrong_type_rejected():
    for body in (
        json.dumps({"status": "OK"}),
        json.dumps({"status": "OK", "results": [1]}),
        json.dumps({"status": "OK", "results": None}),
    ):
        assert qualify(_evidence(bodies=lambda _, b=body: _body(raw=b))) is None


# --------------------------------------------------------------------------
# per-day identity, parameters and digest negatives
# --------------------------------------------------------------------------


@pytest.mark.parametrize("index", [0, 9, 19])
def test_wrong_request_path_rejected(index):
    for path in ("/v3/reference/tickers/INTC", "/v2/reference/tickers/MU",
                 "/v3/reference/tickers/MU/", "/v3/reference/tickers/mu",
                 "/v3/reference/tickers/%4DU", "/v1/aggs/ticker/MU/range"):
        assert qualify(_obs(index, request_path=path)) is None, path


@pytest.mark.parametrize("index", [0, 9, 19])
def test_request_params_date_mismatch_rejected(index):
    other = SESSIONS[0 if index != 0 else 1].isoformat()
    assert qualify(_obs(index, request_params={"date": other})) is None
    assert qualify(_obs(index, request_params={"date": index})) is None
    assert qualify(_obs(index, request_params={"Date": SESSIONS[index].isoformat()})) is None


def test_request_params_extra_key_credentials_rejected():
    evidence = _obs(4, request_params={"date": SESSIONS[4].isoformat(), "apiKey": "secret"})
    assert qualify(evidence) is None
    assert qualify(_obs(4, request_params={})) is None
    assert qualify(_obs(4, request_params="date=2026-09-24")) is None


@pytest.mark.parametrize("index", [0, 19])
def test_session_string_mismatch_rejected(index):
    other = SESSIONS[(index + 1) % 20].isoformat()
    assert qualify(_obs(index, session=other)) is None
    assert qualify(_obs(index, session=SESSIONS[index].isoformat() + "T00:00:00")) is None


def test_missing_observation_key_rejected():
    evidence = _evidence()
    for key in ("session", "request_path", "request_params", "request_started_at",
                "response_received_at", "http_status", "response_sha256", "response_body"):
        assert qualify(_drop(11, key)) is None, key


def test_extra_observation_key_rejected():
    assert qualify(_obs(0, api_key="x")) is None
    assert qualify(_obs(0, currency="USD")) is None


def test_digest_format_negatives_rejected():
    body = _body()
    real = _digest(body)
    for digest in (real.upper(), real[:-1] + "g", "0" * 63, "0" * 65,
                   real + " ", 12345, None):
        assert qualify(_obs(2, response_sha256=digest)) is None, digest


def test_body_type_and_size_negatives_rejected():
    assert qualify(_obs(5, response_body=None)) is None
    assert qualify(_obs(5, response_body=123)) is None
    assert qualify(_obs(5, response_body=_body(raw=b"bytes"))) is None
    assert qualify(_evidence(bodies=lambda _: _padded_body(BODY_LIMIT + 1))) is None
    assert qualify(_evidence(bodies=lambda _: _padded_body(BODY_LIMIT * 4))) is None


def test_oversized_receipt_input_rejected():
    # The per-body bound rejects first; the 3 MiB canonical-receipt bound in
    # the module stays as a layered guard for any structurally valid receipt.
    oversized = _padded_body(BODY_LIMIT * 8)
    assert qualify(_evidence(bodies=lambda _: oversized)) is None


# --------------------------------------------------------------------------
# clock negatives
# --------------------------------------------------------------------------


def test_reversed_start_response_rejected():
    evidence = _evidence()
    for index in range(20):
        candidate = copy.deepcopy(evidence)
        candidate["observations"][index]["request_started_at"] = f"2026-10-20T07:05:00Z"
        candidate["observations"][index]["response_received_at"] = f"2026-10-20T07:04:00Z"
        assert qualify(candidate) is None


def test_future_clock_beyond_recorded_at_rejected():
    evidence = _obs(3, response_received_at="2026-10-20T09:00:00Z")
    assert qualify(evidence) is None
    assert qualify(_obs(3, request_started_at="2026-10-20T09:00:00Z")) is None
    assert qualify(_obs(3, request_started_at="2026-10-21T07:00:00Z",
                        response_received_at="2026-10-21T07:00:01Z")) is None
    assert qualify(_evidence(), recorded_at=datetime(2026, 10, 19, tzinfo=timezone.utc)) is None


def test_naive_and_malformed_timestamps_rejected():
    for stamp in ("2026-10-20T07:00:00", "2026-10-20 07:00:00Z", "2026-10-20",
                  "2026-10-20T07:00:00+25:00", "2026-10-20T07:00:00-25:00",
                  "not-a-time", "", "2026-13-40T99:00:00Z", 1760000000, None):
        evidence = _obs(6, request_started_at=stamp)
        assert qualify(evidence) is None, stamp
        assert qualify(_obs(6, response_received_at=stamp)) is None, stamp


def test_naive_recorded_at_rejected():
    assert qualify(_evidence(), recorded_at=datetime(2026, 10, 20, 8, 0)) is None
    assert qualify(_evidence(), recorded_at=None) is None
    assert qualify(_evidence(), recorded_at=date(2026, 10, 20)) is None
    assert qualify(_evidence(), recorded_at="2026-10-20T08:00:00Z") is None


def test_session_date_after_request_utc_date_rejected():
    # Dated reference for 2026-10-16 observed by a request that ran on 10-14.
    evidence = _evidence()
    late = SESSIONS[19]
    evidence["observations"][19]["request_started_at"] = "2026-10-14T07:00:00Z"
    evidence["observations"][19]["response_received_at"] = "2026-10-14T07:00:01Z"
    assert late > datetime(2026, 10, 14, tzinfo=timezone.utc).date()
    assert qualify(evidence) is None


# --------------------------------------------------------------------------
# window / sessions negatives
# --------------------------------------------------------------------------


@pytest.mark.parametrize("drop", [0, 9, 19])
def test_missing_session_rejected(drop):
    evidence = _evidence()
    del evidence["observations"][drop]
    assert len(evidence["observations"]) == 19
    assert qualify(evidence) is None


def test_extra_observation_rejected():
    evidence = _evidence()
    evidence["observations"].append(_observation(SESSIONS[-1], 20))
    assert qualify(evidence) is None


def test_duplicate_session_rejected():
    evidence = _evidence()
    evidence["observations"][18] = copy.deepcopy(evidence["observations"][17])
    assert qualify(evidence) is None


def test_shuffled_or_misaligned_sessions_rejected():
    evidence = _evidence()
    evidence["observations"][0], evidence["observations"][1] = (
        evidence["observations"][1],
        evidence["observations"][0],
    )
    assert qualify(evidence) is None
    assert qualify(_evidence(), sessions=list(reversed(SESSIONS))) is None


def test_invalid_sessions_argument_rejected():
    assert qualify(_evidence(), sessions=SESSIONS[:19]) is None
    assert qualify(_evidence(), sessions=SESSIONS + [SESSIONS[-1]]) is None
    assert qualify(_evidence(), sessions=SESSIONS + [SESSIONS[-1] + timedelta(days=1)]) is None
    assert qualify(_evidence(), sessions=[s.isoformat() for s in SESSIONS]) is None
    assert qualify(_evidence(), sessions=[datetime(2026, 10, 16, tzinfo=timezone.utc)] + SESSIONS[1:]) is None
    assert qualify_currency(_evidence(), ticker=TICKER, sessions=None, recorded_at=RECORDED_AT) is None
    assert qualify(_evidence(), sessions="2026-09-21") is None
    assert qualify(_evidence(), sessions=tuple(SESSIONS)) is not None


# --------------------------------------------------------------------------
# envelope / ticker negatives
# --------------------------------------------------------------------------


def test_evidence_envelope_negatives_rejected():
    for evidence in (None, [], "evidence", 27, (), object()):
        assert qualify(evidence) is None, evidence
    assert qualify(_mutate(schema="liquidity_currency_observations.v2")) is None
    assert qualify(_mutate(schema="liquidity_currency_observations.V1")) is None
    assert qualify(_mutate(ticker="INTC")) is None
    assert qualify(_mutate(extra="field")) is None
    assert qualify(_mutate(observations={})) is None
    assert qualify(_mutate(observations="x" * 20)) is None
    bad_item = _evidence()
    bad_item["observations"][7] = "observation"
    assert qualify(bad_item) is None
    bad_item["observations"][7] = None
    assert qualify(bad_item) is None


def test_ticker_argument_negatives_rejected():
    for ticker in ("mu", "MU ", " MU", "M/U", "", None, 7, b"MU", "M" * 33):
        assert qualify(_evidence(), ticker=ticker) is None, ticker


def test_nan_and_unserializable_evidence_rejected():
    evidence = _obs(1, http_status=float("nan"))
    assert qualify(evidence) is None
    evidence = _obs(1, http_status=float("inf"))
    assert qualify(evidence) is None
    poisoned = _evidence()
    poisoned["observations"][0]["response_body"] = float("nan")
    assert qualify(poisoned) is None
    poisoned = _evidence()
    poisoned["observations"][0]["request_params"] = {"date": SESSIONS[0], "x": object()}
    assert qualify(poisoned) is None


def test_http_status_bool_and_types_rejected():
    for status in (True, False, "200", 200.0, 404, 500, 301, None, [200], 200 + 0j):
        assert qualify(_obs(0, http_status=status)) is None, status


def test_hostile_objects_never_raise():
    class Hostile:
        def __eq__(self, other):
            raise RuntimeError("boom")

        def __ne__(self, other):
            raise RuntimeError("boom")

        def __len__(self):
            raise RuntimeError("boom")

    hostile = _evidence()
    hostile["observations"][3]["request_path"] = Hostile()
    assert qualify(hostile) is None
    assert qualify(_evidence(), sessions=[Hostile()] + SESSIONS[1:]) is None


def test_every_observation_must_qualify_individually():
    for index in range(20):
        evidence = _evidence()
        victim = evidence["observations"][index]
        victim["response_sha256"] = "f" * 64
        assert qualify(evidence) is None, index



def test_equivalent_aware_offset_clocks_normalize_to_the_same_instants():
    evidence=_evidence()
    expected=qualify(evidence)
    for observation in evidence['observations']:
        for key in ['request_started_at','response_received_at']:
            observation[key]=datetime.fromisoformat(observation[key].replace('Z','+00:00')).astimezone(timezone(timedelta(hours=9))).isoformat()
    actual=qualify(evidence)
    assert actual is not None
    assert actual['observation_started_at']==expected['observation_started_at']
    assert actual['observation_completed_at']==expected['observation_completed_at']
    assert actual['known_at'] is None


@pytest.mark.parametrize('body',[
    '{"status":"OK","results":{"ticker":"MU","currency_name":"usd"},"extra":NaN}',
    '{"status":"OK","results":{"ticker":"MU","currency_name":"usd"},"extra":Infinity}',
    '{"status":"OK","results":{"ticker":"MU","currency_name":"EUR","currency_name":"usd"}}',
])
def test_nonstandard_or_ambiguous_provider_json_never_qualifies(body):
    evidence=_evidence()
    observation=evidence['observations'][0]
    observation['response_body']=body
    observation['response_sha256']=_digest(body)
    assert qualify(evidence) is None



def test_requested_session_is_compared_to_the_actual_utc_request_date():
    evidence=_evidence()
    evidence['observations'][0]['request_started_at']='2026-09-21T00:30:00+09:00'
    evidence['observations'][0]['response_received_at']='2026-09-21T00:30:01+09:00'
    assert qualify(evidence) is None  # actual request UTCdate is September20
