"""C0 adapter receipts only; no real Auth/database/network effects."""
import io
import json
import urllib.error
from unittest.mock import patch

import pytest
from lib import user_prefs as P

USER = "00000000-0000-4000-8000-000000000101"
REV = "00000000-0000-4000-8000-000000000202"
CREDS = ("https://fixture.invalid", "synthetic-only")


def state(is_active=False, **changes):
    value = dict(schema="macro.rotation_consent.v1", user_id=USER,
                 status="active" if is_active else "inactive", active=is_active,
                 revision=REV, activated_at="2026-11-04T00:00:00Z" if is_active else None)
    value.update(changes)
    return value


def reply(value):
    return io.BytesIO(json.dumps(value).encode())


def test_explicit_enable_binds_observed_revision_and_only_one_existing_rpc():
    with patch.object(P.urllib.request, "urlopen", return_value=reply(
            {"status": "applied", "state": state(True)})) as send:
        result = P.write_rotation_consent(USER, True, expected_revision=REV, supabase=CREDS)
    assert result["effect"] == "APPLIED"
    assert send.call_count == 1
    request = send.call_args.args[0]
    assert request.full_url == "https://fixture.invalid/rest/v1/rpc/rotation_consent_set_v1"
    assert json.loads(request.data) == dict(
        p_user_id=USER, p_enabled=True, p_expected_revision=REV)


@pytest.mark.parametrize("value", [1, 0, "true", None, {}, []])
def test_enable_requires_boolean_before_any_request(value):
    with patch.object(P.urllib.request, "urlopen") as send:
        result = P.write_rotation_consent(USER, value, expected_revision=None, supabase=CREDS)
    assert result["effect"] == "NOT_APPLIED"
    send.assert_not_called()


@pytest.mark.parametrize("uid,rev", [
    ("../admin", REV), (USER.upper(), "junk"), (USER, "junk"), (None, REV)
])
def test_identifiers_fail_before_any_request(uid, rev):
    with patch.object(P.urllib.request, "urlopen") as send:
        result = P.write_rotation_consent(uid, True, expected_revision=rev, supabase=CREDS)
    assert result["effect"] == "NOT_APPLIED"
    send.assert_not_called()


@pytest.mark.parametrize("body", [
    [], {}, {"status": "applied"}, {"status": "applied", "state": state(True), "extra": 1},
    {"status": "applied", "state": state(True, user_id="other")},
    {"status": "applied", "state": state(True, revision=None)},
    {"status": "applied", "state": state(True, activated_at="2026-11-04T00:00:00")},
    {"status": "applied", "state": state(True, active=1)},
    {"status": "applied", "state": state(False)},
])
def test_malformed_or_wrong_generation_receipt_holds_the_original_write(body):
    with patch.object(P.urllib.request, "urlopen", return_value=reply(body)) as send:
        result = P.write_rotation_consent(USER, True, expected_revision=REV, supabase=CREDS)
    assert result["effect"] == "EFFECT_UNKNOWN"
    assert send.call_count == 1


@pytest.mark.parametrize("enabled", [True, False])
def test_lost_write_receipt_is_not_retried_or_replaced(enabled):
    with patch.object(P.urllib.request, "urlopen", side_effect=TimeoutError) as send:
        result = P.write_rotation_consent(USER, enabled, expected_revision=REV, supabase=CREDS)
    assert result == dict(effect="EFFECT_UNKNOWN", status="receipt_unavailable", state=None)
    assert send.call_count == 1


@pytest.mark.parametrize("status", [
    "stale_revision", "preferences_not_enabled", "metadata_unreadable"
])
def test_explicit_refusal_preserves_current_owner_state_without_retry(status):
    with patch.object(P.urllib.request, "urlopen", return_value=reply(
            {"status": status, "state": state()})) as send:
        result = P.write_rotation_consent(USER, True, expected_revision=None, supabase=CREDS)
    assert result == dict(effect="NOT_APPLIED", status=status, state=state())
    assert send.call_count == 1


def test_current_read_is_database_rpc_not_cached_user_or_jwt():
    with patch.object(P.urllib.request, "urlopen", return_value=reply(
            {"status": "ok", "state": state()})) as send:
        result = P.read_rotation_consent(USER, supabase=CREDS)
    assert result["state"] == state()
    assert send.call_args.args[0].full_url.endswith("/rotation_consent_read_v1")
    assert json.loads(send.call_args.args[0].data) == {"p_user_id": USER}


def test_unknown_read_cannot_authorize_activation():
    with patch.object(P.urllib.request, "urlopen", side_effect=TimeoutError):
        result = P.read_rotation_consent(USER, supabase=CREDS)
    assert result["effect"] == "NOT_APPLIED"
    assert result["state"] is None


def test_revocation_receipt_must_be_valid_inactive_not_corrupt():
    with patch.object(P.urllib.request, "urlopen", return_value=reply(
            {"status": "applied", "state": state(status="corrupt")})):
        result = P.write_rotation_consent(USER, False, expected_revision=None, supabase=CREDS)
    assert result["effect"] == "EFFECT_UNKNOWN"


@pytest.mark.parametrize("code", [401, 403])
def test_explicit_authorization_denial_has_no_retry_or_alternate_credential(code):
    error = urllib.error.HTTPError("https://fixture.invalid", code, "denied", {}, None)
    with patch.object(P.urllib.request, "urlopen", side_effect=error) as send:
        result = P.write_rotation_consent(USER, True, expected_revision=None, supabase=CREDS)
    assert result["effect"] == "NOT_APPLIED"
    assert result["status"] == "authorization_denied"
    assert send.call_count == 1
