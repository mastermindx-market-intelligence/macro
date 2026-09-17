"""Calendar context must not depend on a numerical forecast (F05/RIC composition)."""
from datetime import date
import json
import pytest
from engine import event_calendar as ec

TODAY = date(2026, 9, 17)
END = date(2026, 9, 30)


def auction(**changes):
    row = {"securityType": "Note", "securityTerm": "9-Year 10-Month",
           "cusip": "91282TEST", "auctionDate": "2026-09-22T00:00:00",
           "announcementDate": "2026-09-17T00:00:00", "issueDate": "2026-09-30T00:00:00",
           "maturityDate": "2036-07-31T00:00:00", "offeringAmount": "39000000000",
           "closingTimeCompetitive": "01:00 PM", "nonclosingTimeCompetitive": "12:00 PM",
           "reopening": "Yes"}
    row.update(changes)
    return row


def events(monkeypatch, rows):
    monkeypatch.setattr(ec, "_fetch_upcoming_auctions", lambda today: rows)
    return ec._auction_events(TODAY, END)


def test_official_auction_terms_reach_context_without_a_forecast(monkeypatch):
    ev = events(monkeypatch, [auction()])[0]
    assert ev["source"] == "treasurydirect"
    ctx = ev["intelligence"]
    assert ctx["schema"] == "calendar_event_context.v1"
    assert ctx["event_date"] == "2026-09-22"
    assert ctx["coverage"] == "official_terms"
    facts = {r["key"]: r for r in ctx["facts"]}
    assert facts["cusip"]["value"] == "91282TEST"
    assert facts["offering_amount_usd"]["value"] == "39000000000"
    assert facts["issue_date"]["value"] == "2026-09-30"
    assert ctx["questions"] and ctx["limitations"]
    assert ctx["source_url"].startswith("https://www.treasurydirect.gov/")
    assert ctx["can_rank"] is ctx["can_size"] is ctx["can_trade"] is False
    assert "forecast" not in facts and "tail" not in facts


def test_distinct_securities_same_day_and_term_are_not_collapsed(monkeypatch):
    rows = events(monkeypatch, [auction(), auction(cusip="91282DIFF")])
    assert len(rows) == 2
    assert len(events(monkeypatch, [auction(), auction()])) == 1


def test_reopening_cusip_is_not_treated_as_a_unique_event(monkeypatch):
    assert len(events(monkeypatch, [auction(), auction(auctionDate="2026-09-23T00:00:00")])) == 2


@pytest.mark.parametrize("amount", [None, "", "NaN", "Infinity", "-10", "0", "<script>x</script>", "1e999"])
def test_missing_or_invalid_amount_is_not_fabricated(monkeypatch, amount):
    ctx = events(monkeypatch, [auction(offeringAmount=amount)])[0]["intelligence"]
    fact = next(r for r in ctx["facts"] if r["key"] == "offering_amount_usd")
    assert fact["value"] is None
    assert fact["state"] == "unavailable"
    assert ctx["questions"]


def test_missing_metadata_preserves_a_useful_limited_context(monkeypatch):
    ctx = events(monkeypatch, [auction(cusip=None, maturityDate="not a date", issueDate="")])[0]["intelligence"]
    assert ctx["coverage"] == "partial_terms"
    assert next(r for r in ctx["facts"] if r["key"] == "maturity_date")["value"] is None
    assert ctx["questions"]
    assert ctx["known_at"] is None  # A date is not an intraday observation receipt.


def test_reference_playbook_exists_for_every_calendar_type():
    for family in ec._META:
        ctx = ec._event(family, TODAY)["intelligence"]
        assert ctx["summary"]["en"] and ctx["summary"]["zh"]
        assert ctx["questions"]
        assert ctx["coverage"] == "reference_only"
        assert ctx["can_rank"] is ctx["can_size"] is ctx["can_trade"] is False
        json.dumps(ctx, allow_nan=False)


def test_floating_rate_and_inflation_linked_auction_context_is_not_nominal(monkeypatch):
    tips = events(monkeypatch, [auction(securityType="TIPS")])[0]["intelligence"]
    frn = events(monkeypatch, [auction(securityType="FRN")])[0]["intelligence"]
    assert "real yield" in tips["summary"]["en"].lower()
    assert "discount margin" in frn["summary"]["en"].lower()


def test_official_time_overrides_generic_calendar_time(monkeypatch):
    ev = events(monkeypatch, [auction(closingTimeCompetitive="11:30 AM")])[0]
    assert ev["time_et"] == "11:30"


def test_projection_does_not_mutate_source_or_add_a_truth_store(monkeypatch):
    row = auction()
    before = json.dumps(row, sort_keys=True)
    ev = events(monkeypatch, [row])[0]
    assert json.dumps(row, sort_keys=True) == before
    assert "intelligence" in ev
    assert "event_id" not in ev["intelligence"]


def test_real_api_type_flags_distinguish_tips_and_frn(monkeypatch):
    tips = events(monkeypatch, [auction(securityType="Note", tips="Yes")])[0]["intelligence"]
    frn = events(monkeypatch, [auction(securityType="Note", floatingRate="Yes")])[0]["intelligence"]
    assert "real yield" in tips["summary"]["en"].lower()
    assert "discount margin" in frn["summary"]["en"].lower()


def test_conflicting_same_auction_terms_are_withheld_not_first_wins(monkeypatch):
    a, b = auction(), auction(offeringAmount="40000000000")
    for rows in [[a, b], [b, a]]:
        ev = events(monkeypatch, rows)[0]
        assert ev["intelligence"]["coverage"] == "conflicting_terms"
        assert all(f["value"] is None for f in ev["intelligence"]["facts"])


def test_captured_official_api_contract_has_usable_terms(monkeypatch):
    from pathlib import Path
    rows = json.loads((Path(__file__).parent / "fixtures/treasury_auction_official_20260917.json").read_text())
    projected = events(monkeypatch, rows)
    assert projected
    for ev in projected:
        ctx = ev["intelligence"]
        assert ctx["coverage"] == "official_terms"
        assert ev["time_et"] in ("13:00", "11:30")
    frn = next(e for e in projected if "FRN" in e["label"])
    assert frn["time_et"] == "11:30"
    assert "discount margin" in frn["intelligence"]["summary"]["en"]


def test_one_malformed_provider_row_does_not_erase_other_events(monkeypatch):
    rows = events(monkeypatch, [auction(cusip=[], reopening={"bad": True}, securityTerm=["bad"]), auction()])
    assert any(any(f['key']=='cusip' and f['value']=='91282TEST' for f in e['intelligence']['facts']) for e in rows)
