"""Session00 admitted SEC owner seam. All events/rights are synthetic.

No real SEC request, public display license, email, identity or database effects.
The canonical GMI source-rights registry remains the production gate.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.catalyst_integration import scan_with_reader
from app.catalyst_scan_authority import ScanReceiptAuthority
from engine.marketing import catalyst_admission, catalyst_scan
from engine.marketing.catalyst_packets import PublicSourceGrant


def _fixture(now):
    ts = (now - timedelta(minutes=5)).isoformat()
    seen = (now - timedelta(minutes=4)).isoformat()
    event = {
        "source": "edgar_8k_202",
        "filing_key": "0000078003:0000078003-26-000094",
        "cik": 78003, "ticker": "PFE",
        "acceptance_datetime": ts, "when": seen,
        "publication_time_utc": seen,
        "source_url": ("https://www.sec.gov/Archives/edgar/data/78003/"
                       "000007800326000094/0000078003-26-000094-index.htm"),
        "eps_actual": 0.42, "_eps_basis": "gaap", "rev_actual": 10_000_000.0,
    }
    issuers = {"PFE": {"supported": True, "issuer_id": "cik:0000078003",
                        "company_name": "Synthetic issuer (NOT live)",
                        "dossier_path": "/stocks/PFE/"}}
    return event, issuers


def _source(now, control):
    event, issuers = _fixture(now)

    def read_universe(clock):
        control["issuer_reads"] += 1
        return issuers

    def events(since, current, limit):
        control["event_reads"] += 1
        assert limit == 20
        assert 0 < (current - since).days <= 7
        return [event]

    def grant(source_id, clock):
        control["rights_reads"] += 1
        if not control["granted"]:
            return None
        return PublicSourceGrant(
            source_id=source_id, receipt_id="test-only-rights-000001",
            owner_ref="test-only-existing-rights-owner",
            audience="public_anonymous", effective_at_utc=now - timedelta(days=1),
            expires_at_utc=now + timedelta(days=1),
            display_link=True, display_title=True, display_facts=True,
        )
    return catalyst_admission.AdmittedEdgarSource(read_universe, events, grant)


@pytest.fixture(autouse=True)
def _unwire():
    catalyst_admission.configure(None)
    yield
    catalyst_admission.configure(None)


def test_missing_source_remains_true_unavailable():
    now = datetime.now(timezone.utc)
    assert catalyst_admission.read_qualified_event_context(now) == ((), {})
    response = catalyst_scan.scan_tickers(["PFE"], now_utc=now)
    assert response["publication_state"] == "UNAVAILABLE"
    assert response["event_id"] is None
    with pytest.raises(Exception) as exc:
        scan_with_reader(["PFE"], now_utc=now)
    assert getattr(exc.value, "status_code", None) == 503


def test_registry_refusal_prevents_calling_any_owner_and_issuer(monkeypatch):
    now = datetime.now(timezone.utc)
    control = {"issuer_reads": 0, "event_reads": 0,
               "rights_reads": 0, "granted": True}
    catalyst_admission.configure(_source(now, control))
    from engine.theme_graph import rights
    monkeypatch.setattr(rights, "assert_public_emission_allowed",
                        lambda family: (_ for _ in ()).throw(
                            rights.RightsRefusal("sec_edgar not admitted")))
    assert catalyst_admission.read_qualified_event_context(now) == ((), {})
    assert all(control[k] == 0 for k in ("issuer_reads", "event_reads", "rights_reads"))
    assert catalyst_scan.scan_tickers(["PFE"], now_utc=now)["publication_state"] == "UNAVAILABLE"


def test_qualified_owner_to_anonymous_scan_and_rights_revocation(monkeypatch):
    now = datetime.now(timezone.utc)
    from engine.theme_graph import rights
    called = []
    def qualify(family):
        called.append(family)
        assert family == "sec_edgar"

    monkeypatch.setattr(rights, "assert_public_emission_allowed", qualify)
    control = {"issuer_reads": 0, "event_reads": 0,
               "rights_reads": 0, "granted": True}
    catalyst_admission.configure(_source(now, control))
    result = scan_with_reader(["PFE", "ZZZZ"], now_utc=now)
    assert result["schema"] == "catalyst.scan/v1"
    assert result["generation"] == 0
    assert result["results"][0]["status"] == "SUPPORTED"
    assert result["results"][1]["status"] == "NOT_COVERED"
    assert result["results"][0]["sources"][0]["rights_receipt_id"] == "test-only-rights-000001"
    assert "0.42" in str(result["results"][0]["what_changed"])
    assert called and control["rights_reads"] >= 1

    # Signed scan proof is separate from affirmative consent/GoTrue.
    proof_owner = ScanReceiptAuthority(
        secret="pure_synthetic_hmac_key_for_tests_only" * 2,
        now=lambda: now)
    proof = proof_owner.issue(result)
    assert proof and proof.count(".") == 1
    confirmed = proof_owner.require_public_scan(proof)
    assert confirmed.public_safe is True and confirmed.tickers == ("PFE",)

    # The same source can withdraw permission even with a still-valid MAC.
    control["granted"] = False
    blocked = catalyst_scan.scan_tickers(["PFE"], now_utc=now)
    assert all(row["status"] != "SUPPORTED" for row in blocked["results"])
    with pytest.raises(Exception):
        proof_owner.require_public_scan(proof)


def test_owner_errors_and_unbounded_events_refuse_without_leak(monkeypatch):
    now = datetime.now(timezone.utc)
    from engine.theme_graph import rights
    monkeypatch.setattr(rights, "assert_public_emission_allowed", lambda family: None)
    event, issuers = _fixture(now)
    bad = catalyst_admission.AdmittedEdgarSource(
        lambda clock: issuers,
        lambda since, current, limit: [event] * 21,
        lambda source, current: None)
    catalyst_admission.configure(bad)
    assert catalyst_admission.read_qualified_event_context(now) == ((), {})

    def broken(since, current, limit):
        raise RuntimeError("private upstream API token must never leak")

    catalyst_admission.configure(catalyst_admission.AdmittedEdgarSource(
        lambda clock: issuers, broken, lambda src, clock: None))
    with pytest.raises(Exception) as exc:
        scan_with_reader(["PFE"], now_utc=now)
    assert "private upstream" not in str(exc.value)
    assert getattr(exc.value, "status_code", None) == 503


def test_no_admission_can_be_created_from_untrusted_object():
    with pytest.raises(ValueError):
        catalyst_admission.configure({"source_url": "https://www.sec.gov"})
