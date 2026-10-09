"""Session 00 public-scan proof / Session 02 ScanAuthority handshake.

Uses a clearly synthetic portable fixture. No consent, OTP, SMTP, Supabase,
rights acquisition or real public-event claim is performed by these tests.
"""
import base64
import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.catalyst_integration import sanitize_public_scan
from app.catalyst_scan_authority import ScanReceiptAuthority

NOW = datetime(2026, 10, 9, 3, 30, tzinfo=timezone.utc)
SECRET = "s" * 40
FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "catalyst_scan_contract_v1.json").read_text()
)


def _reader(tickers, *, event_id=None, now_utc=None, packet=None):
    # Only synthetic issuer fixtures, never private market or paid data.
    result = copy.deepcopy(FIXTURE if packet is None else packet)
    result["requested_tickers"] = list(tickers)
    result["results"] = [row for row in result["results"] if row["ticker"] in tickers]
    return result


def _public():
    return sanitize_public_scan(FIXTURE, ["NVDA", "ZZZZ"], now_utc=NOW)


def _owner(*, reader=_reader, now=NOW, secret=SECRET):
    return ScanReceiptAuthority(reader=reader, secret=secret, now=lambda: now)


def test_qualified_first_result_mints_verifiable_proof_for_supported_ticker_only():
    auth = _owner()
    receipt = auth.issue(_public())
    assert receipt and len(receipt) <= 1024
    confirmed = auth.require_public_scan(receipt)
    assert confirmed.event_id == "fixture-earnings-20261008"
    assert confirmed.tickers == ("NVDA",)
    assert confirmed.as_of_utc == "2026-10-09T02:00:00Z"
    assert confirmed.public_safe is True
    # The receipt may be decoded by its holder; never put user PII there.
    raw = base64.urlsafe_b64decode(receipt.split(".")[0] + "==").decode()
    assert "email" not in raw and "secret" not in raw and "ZZZZ" not in raw


def test_no_issuer_secret_or_no_supported_source_never_mints_a_proof():
    assert _owner(secret="").issue(_public()) is None
    denied = copy.deepcopy(_public())
    denied["results"][0]["status"] = "RIGHTS_BLOCKED"
    assert _owner().issue(denied) is None


def test_forged_and_oversized_proofs_are_rejected_before_producer_use():
    calls = []
    auth = _owner(reader=lambda *a, **k: calls.append(True))
    valid = auth.issue(_public())
    assert valid
    body, sig = valid.split(".")
    corrupted = body[:-2] + ("A" if body[-2] != "A" else "B") + body[-1] + "." + sig
    for token in (corrupted, valid + "-bad", "x" * 1025, "token@example.com"):
        with pytest.raises(Exception):
            auth.require_public_scan(token)
    assert not calls



@pytest.mark.parametrize("malformed", ["x.x", "AAAAA.AAAAA", "x.AAAAA"])
def test_malformed_base64_signed_shape_is_typed_invalid_proof_not_server_error(malformed):
    called = []
    auth = _owner(reader=lambda *a, **k: called.append(True))
    with pytest.raises(Exception) as result:
        auth.require_public_scan(malformed)
    assert "INVALID_SCAN_PROOF" in str(result.value)
    assert called == []



def test_initial_generation_zero_scan_is_signed_and_verified():
    # Real Session 01 first-publication semantics begin at generation zero.
    # The producer/00 serializer admit this value; opt-in must not silently
    # disappear until the first correction (generation one).
    initial = copy.deepcopy(FIXTURE)
    initial["generation"] = 0
    scan = sanitize_public_scan(initial, ["NVDA", "ZZZZ"], now_utc=NOW)
    authority = _owner(reader=lambda tickers, *, event_id=None, now_utc=None:
                       _reader(tickers, event_id=event_id, now_utc=now_utc,
                               packet=initial))
    proof = authority.issue(scan)
    assert isinstance(proof, str) and proof.count(".") == 1
    accepted = authority.require_public_scan(proof)
    assert accepted.public_safe and accepted.tickers == ("NVDA",)
    assert accepted.event_id == scan["event_id"]
    # A negative revision is not a legitimate original publication.
    assert authority.issue({**scan, "generation": -1}) is None


def test_receipt_expires_in_twenty_minutes_even_when_mac_was_valid():
    issued = _owner()
    proof = issued.issue(_public())
    expired = _owner(now=NOW + timedelta(minutes=21))
    with pytest.raises(Exception) as err:
        expired.require_public_scan(proof)
    assert "INVALID_SCAN_PROOF" in str(err.value)


def test_rights_removed_or_correction_generation_changed_invalidates_live_proof():
    proof = _owner().issue(_public())
    bad_rights = copy.deepcopy(FIXTURE)
    bad_rights["results"][0]["status"] = "RIGHTS_BLOCKED"
    # This reader is authoritative at verification time and may retract rights.
    rights_owner = _owner(reader=lambda t, *, event_id=None, now_utc=None:
                          _reader(t, event_id=event_id, now_utc=now_utc, packet=bad_rights))
    with pytest.raises(Exception) as err:
        rights_owner.require_public_scan(proof)
    assert "SCAN_PROOF_SUPERSEDED" in str(err.value)

    new_gen = copy.deepcopy(FIXTURE)
    new_gen["generation"] = 3
    correction_owner = _owner(reader=lambda t, *, event_id=None, now_utc=None:
                              _reader(t, event_id=event_id, now_utc=now_utc, packet=new_gen))
    with pytest.raises(Exception) as err:
        correction_owner.require_public_scan(proof)
    assert "SCAN_PROOF_SUPERSEDED" in str(err.value)


def test_retracted_failing_producer_blocks_even_a_signed_unexpired_receipt():
    proof = _owner().issue(_public())

    def unavailable(*args, **kwargs):
        raise RuntimeError("Private upstream details must never reach public error text")

    with pytest.raises(Exception) as err:
        _owner(reader=unavailable).require_public_scan(proof)
    assert "SCAN_PROOF_SOURCE_UNAVAILABLE" in str(err.value)
    assert "Private upstream" not in str(err.value)
