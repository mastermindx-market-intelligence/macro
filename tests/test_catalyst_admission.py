"""Session00 admitted SEC owner seam. All events/rights are synthetic.

No real SEC request, public display license, email, identity or database effects.
The canonical GMI source-rights registry remains the production gate.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.catalyst_integration import scan_with_reader
from app.catalyst_scan_authority import ScanReceiptAuthority
from engine.marketing import catalyst_admission, catalyst_scan
from engine.marketing.catalyst_packets import (
    PublicSourceGrant, VerifiedDocumentObservation, VerifiedEarningsFigure)
from engine.marketing.catalyst_scan import SourceCoverageReceipt


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
            document_url=event["source_url"], document_sha256="a" * 64,
        )

    def document_observation(source_event, clock):
        assert source_event is event
        return VerifiedDocumentObservation(
            source_id="sec:" + event["filing_key"],
            document_url=event["source_url"],
            document_sha256="a" * 64,
            receipt_id="fixture-document-observation",
            owner_ref="fixture-retained-edgar-reader",
            first_verified_at_utc=event["when"],
            checked_at_utc=clock,
            source_snapshot_version="fixture-source-snapshot-001",
            verified_figures=(
                VerifiedEarningsFigure("eps_actual", event["eps_actual"],
                                       event["_eps_basis"], "a" * 64, "b" * 64),
                VerifiedEarningsFigure("rev_actual", event["rev_actual"],
                                       "reported", "a" * 64, "c" * 64),
            ),
        )

    def source_coverage(since, current, checked):
        return SourceCoverageReceipt(
            source="edgar_8k_202",
            receipt_id="fixture-window-success-001",
            owner_ref="fixture-retained-edgar-reader",
            snapshot_version="fixture-source-snapshot-001",
            issuer_tickers=frozenset({"PFE"}),
            window_start_utc=since, window_end_utc=current, checked_at_utc=checked,
            outcome="COMPLETE", pagination_exhausted=True, truncated=False,
            returned_events=1, event_limit=20,
        )

    return catalyst_admission.AdmittedEdgarSource(
        read_universe, events, grant, document_observation, source_coverage)


@pytest.fixture(autouse=True)
def _unwire():
    catalyst_admission.configure(None)
    yield
    catalyst_admission.configure(None)


def test_missing_source_remains_true_unavailable():
    now = datetime.now(timezone.utc)
    assert catalyst_admission.read_qualified_event_context(now) == ((), {}, None)
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
    assert catalyst_admission.read_qualified_event_context(now) == ((), {}, None)
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
    assert result["schema"] == "catalyst.scan/v2"
    assert result["generation"] == 0
    assert result["results"][0]["status"] == "SUPPORTED"
    assert result["results"][1]["status"] == "NOT_COVERED"
    assert result["results"][0]["sources"][0]["rights_receipt_id"] == "test-only-rights-000001"
    assert "0.42" in str(result["results"][0]["what_changed"])
    assert called and control["rights_reads"] >= 1

    # Stage B signed proofs currently accept only vetted v1 scans.
    # Never misinterpret a newly displayed v2 result as consent, email scope,
    # or a valid signed proof without separate original Session02 admission.
    proof_owner = ScanReceiptAuthority(
        secret="pure_synthetic_hmac_key_for_tests_only" * 2,
        now=lambda: now)
    assert proof_owner.issue(result) is None

    # Live source rights can still withdraw after a positive v2 display.
    control["granted"] = False
    blocked = catalyst_scan.scan_tickers(["PFE"], now_utc=now)
    assert all(row["status"] != "SUPPORTED" for row in blocked["results"])
    assert all(not row["sources"] and not row["what_changed"]
               for row in blocked["results"])
    assert proof_owner.issue(blocked) is None


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
    assert catalyst_admission.read_qualified_event_context(now) == ((), {}, None)

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


def test_existing_registry_can_mark_other_names_unsupported_without_hiding_public_event(monkeypatch):
    """Supported direct issuer survives unrelated unsupported issuer metadata."""
    now = datetime.now(timezone.utc)
    from engine.theme_graph import rights
    monkeypatch.setattr(rights, "assert_public_emission_allowed",
                        lambda family: None if family == "sec_edgar" else 1 / 0)
    control = {"issuer_reads": 0, "event_reads": 0,
               "rights_reads": 0, "granted": True}
    provider = _source(now, control)
    original_issuers = provider.issuer_universe
    catalyst_admission.configure(catalyst_admission.AdmittedEdgarSource(
        lambda clock: {**original_issuers(clock), "ZZZZ": {"supported": False}},
        provider.recent_events, provider.public_grant,
        provider.document_observation, provider.source_coverage))
    result = scan_with_reader(["PFE", "ZZZZ"], now_utc=now)
    assert result["results"][0]["status"] == "SUPPORTED"
    assert result["results"][1]["status"] == "NOT_COVERED"
    assert control["rights_reads"] > 0
