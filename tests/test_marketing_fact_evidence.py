"""The original writer facts must survive plan -> outbox -> approval, safely."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from engine.marketing import approval_desk, outbox
from engine.marketing.content_studio import drop_degenerate_facts, strip_scaffolding
from engine.marketing.copywriter import build_context
from engine.marketing.fact_evidence import (
    WRITER_PACKET_PRODUCER,
    capture_writer_packet,
    valid_writer_packet,
)

_DAY = "2026-11-14"
_NOW = datetime(2026, 11, 14, 12, tzinfo=timezone.utc)
_CFG = {"sentinel": {"max_posts_per_account_per_day": 8}}


def _source_packet() -> dict:
    item = {"type": "macro", "account": "flagship"}
    facts = {
        "facts": [{
            "id": "labor_print", "text": "The latest weekly claims print was 221,000.",
            "numbers": ["221,000"],
        }, {
            "id": "rates_print", "text": "The quoted market move is +4.2%.",
            "numbers": ["+4.2%"],
        }],
        "numbers_whitelist": ["221,000", "+4.2%"],
    }
    ctx = build_context(item, facts=facts)
    packet = capture_writer_packet(ctx, facts, as_of=_DAY)
    assert packet and valid_writer_packet(packet, as_of=_DAY)
    return packet


def _plan(text: str, packet: dict | None) -> dict:
    post = {
        "id": "macro-001", "type": "macro", "account": "flagship",
        "slot": "D1-AM", "headline": "", "body": text,
        "_copy_mode": "llm", "status": "drafted",
    }
    if packet is not None:
        post["_writer_fact_packet"] = packet
    return {"as_of": _DAY, "accounts": [{"id": "flagship", "queue": [post]}]}


def _emitted(tmp_path, text: str, packet: dict | None) -> dict:
    result = outbox.emit_from_content_plan(
        _plan(text, packet), root=tmp_path, cfg=_CFG, day_prefix="D1", now=_NOW,
    )
    assert result["emitted"] == 1, result
    items = outbox.read_items(root=tmp_path)
    assert len(items) == 1
    return items[0]


def test_macro_writer_evidence_reaches_outbox_and_desk(tmp_path):
    item = _emitted(
        tmp_path, "Weekly claims were 221,000. The market move is +4.2%.",
        _source_packet(),
    )
    packet = item["source"]["fact_packet"]
    assert packet["producer"] == WRITER_PACKET_PRODUCER
    assert packet["as_of"] == item["as_of"]
    assert packet["facts"][0]["text"] == "The latest weekly claims print was 221,000."
    assert item["source"]["value_gate"]["components"]["numbers_whitelist_supplied"]
    evidence = approval_desk.item_evidence(item)
    assert evidence["writer_packet_verified"] is True
    assert "221,000" in evidence["numbers_whitelist"]
    assert approval_desk.check_number_sanity(item, evidence).status == approval_desk.PASS
    assert approval_desk.audit_item(item, now=_NOW).action == "approve"


def test_source_fact_does_not_launder_an_invented_market_number(tmp_path):
    item = _emitted(
        tmp_path, "Weekly claims were 221,000, and the dollar rallied +9.9%.",
        _source_packet(),
    )
    outcome = approval_desk.check_number_sanity(item, approval_desk.item_evidence(item))
    assert outcome.status == approval_desk.UNVERIFIABLE
    assert "+9.9%" in outcome.evidence
    verdict = approval_desk.audit_item(item, now=_NOW)
    assert verdict.action == "quarantine"
    assert verdict.check == "number_sanity"


def test_an_unlicensed_thousands_count_is_also_stopped(tmp_path):
    item = _emitted(tmp_path, "Weekly claims were 222,000.", _source_packet())
    outcome = approval_desk.check_number_sanity(item, approval_desk.item_evidence(item))
    assert outcome.status == approval_desk.UNVERIFIABLE
    assert "222,000" in outcome.evidence


def test_sourced_fact_does_not_qualify_as_unsourced_forward_target(tmp_path):
    item = _emitted(
        tmp_path, "Weekly claims were 221,000. Target 221,000 next week.",
        _source_packet(),
    )
    outcome = approval_desk.check_number_sanity(item, approval_desk.item_evidence(item))
    assert outcome.status == approval_desk.FAIL
    assert outcome.name == "invented_level"


def test_bad_or_different_day_packet_does_not_rescue_unsupported_copy(tmp_path):
    packet = _source_packet()
    packet["as_of"] = "2026-11-13"
    item = _emitted(tmp_path, "Weekly claims were 221,000.", packet)
    assert "fact_packet" not in item["source"]
    assert approval_desk.check_number_sanity(
        item, approval_desk.item_evidence(item),
    ).status == approval_desk.UNVERIFIABLE


def test_manual_old_outbox_row_with_bad_writer_packet_is_not_laundered():
    item = {
        "as_of": _DAY, "kind": "macro", "text": "Claims were 221,000.",
        "source": {"fact_packet": {**_source_packet(), "as_of": "2026-11-13"}},
    }
    evidence = approval_desk.item_evidence(item)
    assert evidence["writer_packet_verified"] is False
    assert evidence["has_evidence"] is False


def test_packet_is_bounded_and_artifact_does_not_leak_writer_scaffolding():
    packet = _source_packet()
    assert valid_writer_packet(packet, as_of=_DAY)
    too_many = dict(packet, numbers_whitelist=["1"] * 129)
    assert not valid_writer_packet(too_many, as_of=_DAY)
    oversized = dict(packet, facts=[{
        "id": "huge", "text": "a" * 400, "numbers": ["10"]
    }])
    assert not valid_writer_packet(oversized, as_of=_DAY)
    bad_number = dict(packet, numbers_whitelist=["javascript:999"])
    assert not valid_writer_packet(bad_number, as_of=_DAY)

    plan = _plan("The market move is +4.2%.", packet)
    saved = strip_scaffolding(plan)
    assert "_writer_fact_packet" in plan["accounts"][0]["queue"][0]
    assert "_writer_fact_packet" not in saved["accounts"][0]["queue"][0]


def test_missing_source_facts_do_not_become_an_empty_verified_packet():
    ctx = {"numbers_whitelist": ["221,000"]}
    assert capture_writer_packet(ctx, {"facts": [], "numbers_whitelist": ["221,000"]},
                                 as_of=_DAY) is None
    assert capture_writer_packet(ctx, None, as_of=_DAY) is None


def test_removed_degenerate_count_cannot_be_relicensed_by_outbox():
    facts = {"facts": [
        {"id": "vacuous", "text": "231 of 231 tracked names are green.",
         "numbers": ["231"]},
        {"id": "real_print", "text": "The observed move was +4.2%.",
         "numbers": ["+4.2%"]},
    ], "numbers_whitelist": ["231", "+4.2%"]}
    pruned, removed = drop_degenerate_facts(facts)
    assert removed == 1
    ctx = build_context({"type": "macro", "account": "flagship"}, facts=pruned)
    packet = capture_writer_packet(ctx, pruned, as_of=_DAY)
    assert packet and "+4.2%" in packet["numbers_whitelist"]
    assert "231" not in packet["numbers_whitelist"]
    assert all(f["id"] != "vacuous" for f in packet["facts"])


def test_grading_receipt_preserves_own_stop_and_target(tmp_path):
    plan = _plan("The earlier $AAPL target 190 was reached.", None)
    post = plan["accounts"][0]["queue"][0]
    post.update({"id": "receipt-001", "type": "receipt", "ticker": "AAPL",
                 "_receipt": {"stop": 162.2, "target": 190.0}})
    result = outbox.emit_from_content_plan(
        plan, root=tmp_path, cfg=_CFG, day_prefix="D1", now=_NOW,
    )
    assert result["emitted"] == 1, result
    item = outbox.read_items(root=tmp_path)[0]
    assert item["source"]["stop"] == 162.2
    assert item["source"]["target"] == 190.0
    ev = approval_desk.item_evidence(item)
    assert ev["target_str"] == "190.0"
    assert ev["stop_str"] == "162.2"


def _packet_for_number(number):
    packet = _source_packet()
    packet["facts"][0]["text"] = f"The reported total was {number}."
    packet["facts"][0]["numbers"] = [number]
    packet["numbers_whitelist"] = [number, "+4.2%"]
    assert valid_writer_packet(packet, as_of=_DAY)
    return packet


@pytest.mark.parametrize("malformed,licensed", [
    ("221,000,00", "221,000"),
    ("1,000,00", "1,000"),
    ("1,,000", "1,000"),
    ("1000,000", "1,000,000"),
    ("1,000.00.5", "1,000.00"),
    ("1,234.50,00", "1,234.50"),
    (".5,000", "5,000"),
    ("-.5,000", "5,000"),
    ("--1,000", "-1,000"),
    ("1,000k%", "1,000k"),
    ("1,000%%", "1,000%"),
])
def test_malformed_grouped_run_is_quarantined_after_original_fact_handoff(tmp_path, malformed, licensed):
    item = _emitted(tmp_path, f"The reported total was {malformed}.", _packet_for_number(licensed))
    outcome = approval_desk.check_number_sanity(item, approval_desk.item_evidence(item))
    assert outcome.status == approval_desk.UNVERIFIABLE
    assert malformed in outcome.evidence
    verdict = approval_desk.audit_item(item, now=_NOW)
    assert verdict.action == "quarantine"
    assert verdict.check == "number_sanity"


@pytest.mark.parametrize("number", [".", ",", "1..2", "221,000,00", "1,000k%", "--1,000"])
def test_malformed_numeric_license_is_not_a_verified_writer_packet(number):
    packet = _source_packet()
    packet["numbers_whitelist"] = [number]
    assert not valid_writer_packet(packet, as_of=_DAY)
    packet = _source_packet()
    packet["facts"][0]["numbers"] = [number]
    assert not valid_writer_packet(packet, as_of=_DAY)


@pytest.mark.parametrize("number", ["221000", "221,000", "+1,234.50", "-1,000.25%", "1,000k", ".5"])
def test_canonical_numeric_license_remains_valid(number):
    assert valid_writer_packet(_packet_for_number(number), as_of=_DAY)


@pytest.mark.parametrize("printed,licensed", [
    ("221,000", "221000"), ("221000", "221,000"),
    ("+1,234.50", "+1234.50"), ("-1,000.25%", "-1000.25%"),
    ("1,000k", "1000k"),
])
def test_approval_preserves_valid_grouping_equivalence_and_sentence_comma(tmp_path, printed, licensed):
    item = _emitted(tmp_path, f"The reported total was {printed}, according to the source.", _packet_for_number(licensed))
    outcome = approval_desk.check_number_sanity(item, approval_desk.item_evidence(item))
    assert outcome.status == approval_desk.PASS
