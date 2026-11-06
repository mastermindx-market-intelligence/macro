#!/usr/bin/env python3
"""V91 §9.1 vertical proof V5 — rumor, denial and confirmation.

MASTERPLAN research/news_intelligence_estate_20261021/MASTERPLAN.md line 475
(row V5): "Original report, independent confirmations and denial remain
versioned; copied wires do not inflate corroboration" and consumer outcome
"Current view and historical replay differ correctly".

Offline, deterministic evidence, not narrative: every verdict below is PROVEN
only when this run itself observed the behaviour end to end on synthetic
SYNTH-* inputs. Standard library plus repository modules only; no network, no
model call, no wall clock (fixed 2026 ISO-8601 instants), and every SQLite
file lives under --scratch. Run from the repo root with PYTHONPATH=.:

    PYTHONPATH=. python3 research/news_intelligence_estate_20261021/v91_proofs/ \
        v5_rumor_denial_confirmation.py --scratch /tmp/any-dir

Output is exactly one line per property P1..P6 then one SUMMARY line; the
sibling .expected file pins the verdicts.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc

# Fixed synthetic story text: the rumor wire says a sale is explored; the
# update adds the reported 500 million figure; the issuer denies it. The
# expected roles come from these strings, never from producer output.
T_RUMOR_V1 = "Sources: SYNTH Corp explores sale"
T_RUMOR_V2 = "Sources: SYNTH Corp explores sale for 500 million"
T_DENIAL = "SYNTH Corp denies sale report"
T_REWORDED = "SYNTH Corp weighs sale after 500 million approach"
T_EDITED_COPY = "SYNTH Corp explores sale, sources say"

# Thesis-lane synthetic identities (schemas constrain id shapes).
CIK = "cik:0000999999"
RUMOR_FACT = "fact_570000000000000000000001"
CONFIRM_FACT = "fact_570000000000000000000002"
COPY_FACT = "fact_570000000000000000000003"
DENIAL_FACT = "fact_570000000000000000000004"
CONTROL_FACT = "fact_570000000000000000000005"
GROUP_DENIAL = "doc_synth_denial_20261020"
GROUP_REPRINT = "doc_synth_reprint_20261020"
GROUP_ORIGIN = "doc_synth_wire_20261020"
GROUP_INDEPENDENT = "doc_synth_confirm_20261020"
EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def T(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)


# ---------------------------------------------------------------- builders ----
def ws_payload(*, item, msg, title, url, created, updated, body=None):
    data = {
        "id": item,
        "action": "created",
        "timestamp": created,
        "content": {
            "id": item,
            "created": created,
            "updated": updated,
            "title": title,
            "url": url,
            "teaser": "SYNTH-TEASER",
            "stocks": ["SYNTH"],
            "body": body,
        },
    }
    return {"kind": "news", "id": msg, "data": data}


def massive_payload(item, domain, *, title, url, published):
    return {
        "id": item,
        "publisher": {"name": "SYNTH-PUB", "homepage_url": f"https://{domain}"},
        "published_utc": published,
        "article_url": url,
        "title": title,
        "description": "SYNTH-TEASER",
        "tickers": ["SYNTH"],
    }


def db_rows(path, sql, params=()):
    conn = sqlite3.connect(f"file:{Path(path)}?mode=ro", uri=True)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _rumor_key():
    return {
        "company_id": CIK,
        "template": "capital_allocation_event.v1",
        "slot": {
            "kind": "t1_authorization_program",
            "action_type": "share_repurchase",
            "horizon_token": "FY2028",
        },
    }


_ABSENCE_CI = {
    "schema": "field_absence.v1",
    "authority": "context_only",
    "reason": "not_stated",
    "subject": "ci_event_id",
    "detail": "synthetic news capital allocation has no ci_event_id",
    "missing_fields": ["ci_event_id"],
}
_ABSENCE_DL = {
    "schema": "field_absence.v1",
    "authority": "context_only",
    "reason": "not_stated",
    "subject": "stated_deadline",
    "detail": "the synthetic wire states no deadline",
    "missing_fields": ["stated_deadline"],
}


def _span(doc: str, n: int) -> dict:
    return {"form": "owner_span_ref", "document_id": doc, "span_id": f"span_{'d' * 16}{n:04d}"}


def rumor_record() -> dict:
    """The original rumor report: one provenance group, GROUP_ORIGIN."""
    return {
        "log_seq": 1,
        "record_kind": "fact_revision",
        "cluster_grain": "fact_revision",
        "fact_id": RUMOR_FACT,
        "document_id": GROUP_ORIGIN,
        "observed_at": "2026-10-20T14:00:00Z",
        "source_available_at": "2026-10-20T13:55:00Z",
        "supersedes_fact_id": None,
        "company_id": CIK,
        "cluster_id": "ev2_5700000000000001",
        "novelty": "new_magnitude_timing_commitment_counterparty",
        "polarity": "supporting",
        "fact_key": _rumor_key(),
        "provenance": {
            "origin_document_id": GROUP_ORIGIN,
            "origin_claim_id": "claim_synth_sale",
            "root_family_id": "root_synth_sale_20261020",
            "source_family": "secondary_outlet",
        },
        "evidence": _span(GROUP_ORIGIN, 1),
        "payload_schema": "capital_allocation_event.v1",
        "ci_event_id": dict(_ABSENCE_CI),
        "owner_claim_ids": ["claim_synth_sale"],
        "quantity_fingerprint": {"form": "present", "canonical_sha256": EMPTY_SHA},
        "reports_fact_id": None,
        "linked_fact_ids": [],
        "stated_deadline": dict(_ABSENCE_DL),
        "next_expected_observation": {
            "milestone_name": "executed_repurchase",
            "window_start": "2026-10-20T14:00:00Z",
            "window_end": "2028-01-30T00:00:00Z",
        },
        "unsolicited_instruction_detected": False,
    }


def followup_record(fact_id, *, document, group, observed, available, seq) -> dict:
    """A later article about the rumor: group decides copy vs confirmation."""
    return {
        "log_seq": seq,
        "record_kind": "manifestation",
        "cluster_grain": "article_manifestation",
        "fact_id": fact_id,
        "document_id": document,
        "observed_at": observed,
        "source_available_at": available,
        "supersedes_fact_id": None,
        "company_id": CIK,
        "cluster_id": "ev2_5700000000000001",
        "novelty": "new_reporting_of_old_fact",
        "polarity": "supporting",
        "fact_key": _rumor_key(),
        "provenance": {
            "origin_document_id": group,
            "origin_claim_id": "claim_synth_sale",
            "root_family_id": "root_synth_sale_20261020",
            "source_family": "wire_reprint",
        },
        "evidence": _span(document, seq),
        "payload_schema": "capital_allocation_event.v1",
        "ci_event_id": dict(_ABSENCE_CI),
        "owner_claim_ids": ["claim_synth_sale"],
        "quantity_fingerprint": {"form": "present", "canonical_sha256": EMPTY_SHA},
        "reports_fact_id": RUMOR_FACT,
        "linked_fact_ids": [],
        "stated_deadline": dict(_ABSENCE_DL),
        "unsolicited_instruction_detected": False,
    }


def rumor_owners(cut: str):
    from engine.news_impact.thesis import OwnerSnapshot

    # The wire's own text states the amounts: a reported 500 million program
    # with 120 million executed, so 380 million remains.
    return OwnerSnapshot(
        leaf_payloads={
            RUMOR_FACT: {
                "incremental": 500_000_000,
                "remaining": 380_000_000,
                "currency": "USD",
                "commitment_status": "authorized",
                "negated": False,
                "channel_hint": "capital_allocation",
            }
        },
        decision_cut=cut,
    )


def project_triggers(log_records):
    """Project the (prior, now] delta window and return the rumor view."""
    import engine.news_impact.thesis as thesis

    log = {
        "schema": "fact_log.v1",
        "authority": "context_only",
        "prophet_flags": {
            "may_rank": False,
            "may_size": False,
            "may_gate": False,
            "prophet_authority": False,
        },
        "unsolicited_instruction_detected": False,
        "records": log_records,
    }
    thesis.validate_log(log)
    views = thesis.F(
        log,
        rumor_owners("2026-10-20T16:00:00Z"),
        "2026-10-20T16:00:00Z",
        prior_as_of_utc="2026-10-20T14:30:00Z",
        prior_owners=rumor_owners("2026-10-20T14:30:00Z"),
        decision_cut="2026-10-20T16:00:00Z",
    )
    return next(
        v
        for v in views
        if v["company_id"] == CIK and v["original_proposition_fact_id"] == RUMOR_FACT
    )



def denial_record(polarity: str, fact_id: str) -> dict:
    """The issuer's later statement on the rumor, linked to it as a fact revision."""
    rec = rumor_record()
    rec.update(
        log_seq=2,
        fact_id=fact_id,
        document_id=GROUP_DENIAL,
        observed_at="2026-10-20T15:10:00Z",
        source_available_at="2026-10-20T15:05:00Z",
        polarity=polarity,
        linked_fact_ids=[RUMOR_FACT],
        owner_claim_ids=["claim_synth_denial"],
        evidence=_span(GROUP_DENIAL, 9),
    )
    rec["provenance"] = {
        "origin_document_id": GROUP_DENIAL,
        "origin_claim_id": "claim_synth_denial",
        "root_family_id": "root_synth_denial_20261020",
        "source_family": "issuer_primary",
    }
    return rec


def producer_provenance() -> dict:
    """Read how the fact-log producer fills provenance, from its own source.

    Also counts non-test modules that name a wire provenance family at all, which
    is how a news-wire producer feeding the thesis lane would show up.
    """
    import ast

    root = Path(__file__).resolve().parents[3]
    path = root / "engine" / "news_impact" / "producer_facts.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = {
        "family": None,
        "family_line": 0,
        "origin_line": 0,
        "own_document": False,
        "origin_found": False,
    }
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "SOURCE_FAMILY" for t in node.targets)
            and isinstance(node.value, ast.Constant)
        ):
            out["family"], out["family_line"] = node.value.value, node.lineno
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value == "origin_document_id":
                    out["origin_line"] = key.lineno
                    out["origin_found"] = True
                    out["own_document"] = (
                        isinstance(value, ast.Name) and value.id == "document_id"
                    )
    skip = root / "engine" / "news_impact" / "thesis.py"
    writers = 0
    for top in ("engine", "app", "collectors", "scripts", "lib"):
        for module in sorted((root / top).rglob("*.py")):
            if module == skip:
                continue
            text = module.read_text(encoding="utf-8", errors="replace")
            if "wire_reprint" in text or "secondary_outlet" in text:
                writers += 1
    out["wire_writers"] = writers
    return out


# -------------------------------------------------------------- properties ----
def p1_original_report_stays_versioned(scratch: Path) -> str:
    """Rumor v1 then updated v2 of one item: both revisions retained."""
    from engine.qbus_news_contract import normalize_news
    from engine.qbus_news_store import NewsStore, RoutedRevision

    def routed(rev):
        return RoutedRevision(
            revision=rev, security_ids=("SYNTH-SEC-1",), universe_revision="SYNTH-UNI-1"
        )

    db = scratch / "p1.db"
    store = NewsStore(db, source_key="SYNTH-KEY")
    v1 = normalize_news(
        ws_payload(
            item="SYNTH-ITEM-V5R",
            msg="SYNTH-MSG-1",
            title=T_RUMOR_V1,
            url="https://synthwire.example/SYNTH-R1",
            created="2026-10-20T14:00:00Z",
            updated="2026-10-20T14:00:00Z",
        ),
        transport="benzinga_ws",
        received_at=T("2026-10-20T14:05:00Z"),
    )
    v2 = normalize_news(
        ws_payload(
            item="SYNTH-ITEM-V5R",
            msg="SYNTH-MSG-2",
            title=T_RUMOR_V2,
            url="https://synthwire.example/SYNTH-R1",
            created="2026-10-20T14:00:00Z",
            updated="2026-10-20T16:00:00Z",
        ),
        transport="benzinga_ws",
        received_at=T("2026-10-20T16:05:00Z"),
    )
    store.commit([routed(v1)], expected_cursor=None, next_cursor="SYNTH-C-1")
    store.commit([routed(v2)], expected_cursor="SYNTH-C-1", next_cursor="SYNTH-C-2")
    replay = store.commit(
        [routed(v2)], expected_cursor="SYNTH-C-2", next_cursor="SYNTH-C-3"
    )
    store.close()

    rows = db_rows(db, "SELECT count(*) FROM news_revisions")[0][0]
    v1_json = json.loads(
        db_rows(
            db, "SELECT revision_json FROM news_revisions WHERE revision_id=?",
            (v1.revision_id,),
        )[0][0]
    )
    state = json.loads(db_rows(db, "SELECT state_json FROM news_states")[0][0])
    changes = db_rows(db, "SELECT count(*) FROM news_changes")[0][0]

    positive = (
        rows == 2
        and v1_json["title"] == T_RUMOR_V1
        and v1.revision_id != v2.revision_id
        and state["title"] == T_RUMOR_V2
        and state["current_revision_id"] == v2.revision_id
        and changes == 2
    )
    negative = (
        replay.duplicate_revisions == 1
        and replay.inserted_revisions == 0
        and db_rows(db, "SELECT count(*) FROM news_revisions")[0][0] == 2
    )
    verdict = "PROVEN" if positive and negative else "PARTIAL"
    print(
        f"V5 P1 {verdict} "
        f"v1+v2 retained revisions=2 states=1 v1_title_intact="
        f"{v1_json['title'] == T_RUMOR_V1} current_is_v2="
        f"{state['current_revision_id'] == v2.revision_id} changes={changes}; "
        f"identical replay dup={replay.duplicate_revisions} inserted="
        f"{replay.inserted_revisions} rows_still=2; "
        f"engine/qbus_news_store.py:242 engine/qbus_news_store.py:260 "
        f"engine/qbus_news_reducer.py:189 engine/qbus_news_reducer.py:274 "
        f"engine/qbus_news_store.py:1606 tests/test_qbus_news_store.py:177"
    )
    return verdict


def p2_independent_confirmation_recognised(scratch: Path) -> str:
    """new_independent_source fires for an unseen provenance group only.

    The rule is exercised with provenance groups supplied as input, then with the
    group the fact-log producer actually writes for a reprint (its own document).
    """
    confirm = followup_record(
        CONFIRM_FACT,
        document=GROUP_INDEPENDENT,
        group=GROUP_INDEPENDENT,
        observed="2026-10-20T15:00:00Z",
        available="2026-10-20T14:55:00Z",
        seq=2,
    )
    copy = followup_record(
        COPY_FACT,
        document=GROUP_REPRINT,
        group=GROUP_ORIGIN,
        observed="2026-10-20T15:30:00Z",
        available="2026-10-20T15:25:00Z",
        seq=2,
    )
    producer = producer_provenance()
    producer_copy = followup_record(
        COPY_FACT,
        document=GROUP_REPRINT,
        group=GROUP_REPRINT if producer["own_document"] else GROUP_ORIGIN,
        observed="2026-10-20T15:30:00Z",
        available="2026-10-20T15:25:00Z",
        seq=2,
    )

    pos = project_triggers([rumor_record(), confirm])
    neg = project_triggers([rumor_record(), copy])
    shaped = project_triggers([rumor_record(), producer_copy])
    pos_fired = "new_independent_source" in pos["material_delta_triggers"]
    neg_silent = neg["material_delta_triggers"] == []
    shaped_silent = "new_independent_source" not in shaped["material_delta_triggers"]
    # Fail closed: PROVEN needs the producer to write its own document as the
    # origin (the shape the reprint case models); a missing or unrecognised
    # origin value cannot evidence it.
    if pos_fired and neg_silent and shaped_silent and producer["own_document"]:
        verdict = "PROVEN"
    elif pos_fired:
        verdict = "PARTIAL"
    else:
        verdict = "ABSENT"
    print(
        f"V5 P2 {verdict} "
        f"supplied groups: unseen-group confirmation "
        f"triggers={sorted(pos['material_delta_triggers'])} "
        f"view_groups={len(pos['provenance_group_ids'])}, same-group reprint "
        f"triggers={sorted(neg['material_delta_triggers'])} "
        f"groups={len(neg['provenance_group_ids'])}; producer-shaped reprint "
        f"(origin_document_id key found={producer['origin_found']}, "
        f"own document is {producer['own_document']}, "
        f"source_family={producer['family']}) "
        f"triggers={sorted(shaped['material_delta_triggers'])} "
        f"groups={len(shaped['provenance_group_ids'])}; non-test modules naming a "
        f"wire provenance family={producer['wire_writers']}; "
        f"engine/news_impact/thesis.py:1608 engine/news_impact/thesis.py:1839 "
        f"engine/news_impact/producer_facts.py:{producer['origin_line']} "
        f"engine/news_impact/producer_facts.py:{producer['family_line']} "
        f"tests/test_news_impact_thesis.py:1034"
    )
    return verdict


def p3_copied_wires_do_not_inflate(scratch: Path) -> str:
    """Store source count and thesis groups both treat a copy as one origin."""
    from engine.qbus_news_contract import normalize_massive_news
    from engine.qbus_news_store import NewsReadRights, NewsStore, RoutedRevision

    def routed(rev):
        return RoutedRevision(
            revision=rev, security_ids=("SYNTH-SEC-3",), universe_revision="SYNTH-UNI-1"
        )

    db = scratch / "p3.db"
    rights = NewsReadRights(
        frozenset({"massive:synthoutleta.example", "massive:synthoutletb.example"})
    )
    store = NewsStore(db, source_key="SYNTH-KEY")
    outlet_a = normalize_massive_news(
        massive_payload(
            "SYNTH-P3-A",
            "synthoutleta.example",
            title=T_RUMOR_V1,
            url="https://synthoutleta.example/SYNTH-P3-A",
            published="2026-10-20T14:00:00Z",
        ),
        received_at=T("2026-10-20T14:05:00Z"),
    )
    # Outlet B syndicates the identical wire (own publisher, own URL).
    outlet_b_wire = normalize_massive_news(
        massive_payload(
            "SYNTH-P3-B",
            "synthoutletb.example",
            title=T_RUMOR_V1,
            url="https://synthoutletb.example/SYNTH-P3-B",
            published="2026-10-20T14:10:00Z",
        ),
        received_at=T("2026-10-20T14:15:00Z"),
    )
    store.commit([routed(outlet_a)], expected_cursor=None, next_cursor="SYNTH-P-1")
    store.commit([routed(outlet_b_wire)], expected_cursor="SYNTH-P-1", next_cursor="SYNTH-P-2")
    reader = NewsStore.open_readonly(db, source_key="SYNTH-KEY")
    snap = reader.snapshot("SYNTH-SEC-3", limit=10, cursor=None, rights=rights)
    detail = reader.story(snap.rows[0].story_id, rights=rights)
    copied_one_source = (
        len(snap.rows) == 1
        and detail.source_count == 1
        and detail.publisher_count == 2
        and detail.item_count == 2
    )
    reader.close()

    # Outlet B then rewords its own item to genuinely independent reporting.
    outlet_b_own = normalize_massive_news(
        massive_payload(
            "SYNTH-P3-B",
            "synthoutletb.example",
            title=T_REWORDED,
            url="https://synthoutletb.example/SYNTH-P3-B",
            published="2026-10-20T15:00:00Z",
        ),
        received_at=T("2026-10-20T15:05:00Z"),
    )
    store.commit([routed(outlet_b_own)], expected_cursor="SYNTH-P-2", next_cursor="SYNTH-P-3")
    store.close()
    reader = NewsStore.open_readonly(db, source_key="SYNTH-KEY")
    snap2 = reader.snapshot("SYNTH-SEC-3", limit=10, cursor=None, rights=rights)
    details2 = [reader.story(row.story_id, rights=rights) for row in snap2.rows]
    reader.close()
    independent_two = any(
        d.source_count == 2 and d.publisher_count == 2 and d.item_count == 2
        for d in details2
    )

    # A syndicated copy whose outlet edited the headline (own publisher, own URL).
    db_e = scratch / "p3e.db"
    rights_e = NewsReadRights(
        frozenset({"massive:synthoutleta.example", "massive:synthoutletc.example"})
    )
    store = NewsStore(db_e, source_key="SYNTH-KEY")
    outlet_c_edit = normalize_massive_news(
        massive_payload(
            "SYNTH-P3-C",
            "synthoutletc.example",
            title=T_EDITED_COPY,
            url="https://synthoutletc.example/SYNTH-P3-C",
            published="2026-10-20T14:10:00Z",
        ),
        received_at=T("2026-10-20T14:15:00Z"),
    )
    store.commit([routed(outlet_a)], expected_cursor=None, next_cursor="SYNTH-E-1")
    store.commit([routed(outlet_c_edit)], expected_cursor="SYNTH-E-1", next_cursor="SYNTH-E-2")
    store.close()
    reader = NewsStore.open_readonly(db_e, source_key="SYNTH-KEY")
    snap_e = reader.snapshot("SYNTH-SEC-3", limit=10, cursor=None, rights=rights_e)
    edited_sources = sum(
        reader.story(row.story_id, rights=rights_e).source_count for row in snap_e.rows
    )
    reader.close()

    # Thesis lane: a reprint carrying the provenance group the producer writes.
    producer = producer_provenance()
    copy_view = project_triggers(
        [
            rumor_record(),
            followup_record(
                COPY_FACT,
                document=GROUP_REPRINT,
                group=GROUP_REPRINT if producer["own_document"] else GROUP_ORIGIN,
                observed="2026-10-20T15:30:00Z",
                available="2026-10-20T15:25:00Z",
                seq=2,
            ),
        ]
    )
    confirm_view = project_triggers(
        [
            rumor_record(),
            followup_record(
                CONFIRM_FACT,
                document=GROUP_INDEPENDENT,
                group=GROUP_INDEPENDENT,
                observed="2026-10-20T15:00:00Z",
                available="2026-10-20T14:55:00Z",
                seq=2,
            ),
        ]
    )
    store_ok = copied_one_source and independent_two
    thesis_copy_one = len(copy_view["provenance_group_ids"]) == 1
    if store_ok and edited_sources == 1 and thesis_copy_one and producer["own_document"]:
        verdict = "PROVEN"
    elif store_ok:
        verdict = "PARTIAL"
    else:
        verdict = "ABSENT"
    print(
        f"V5 P3 {verdict} "
        f"store: identical wire 2 outlets 1 story source_count="
        f"{detail.source_count} publishers={detail.publisher_count}; reworded "
        f"independent item source_count=2={independent_two}; edited-headline copy "
        f"source_count={edited_sources}; thesis with producer-shaped reprint group: "
        f"copy groups={len(copy_view['provenance_group_ids'])} confirm groups="
        f"{len(confirm_view['provenance_group_ids'])}; "
        f"engine/qbus_news_quality.py:97 engine/qbus_news_quality.py:105 "
        f"engine/news_impact/thesis.py:882 "
        f"engine/news_impact/producer_facts.py:{producer['origin_line']} "
        f"tests/test_shared_news_intelligence.py:1242"
    )
    return verdict


def p4_denial_stays_versioned_as_denial(scratch: Path) -> str:
    """Probe every lane that could type a denial as a denial of the rumor."""
    from engine import news_events
    from engine.news_events import classify_event
    from engine.qbus_news_contract import normalize_news
    from engine.qbus_news_store import NewsStore, RoutedRevision

    rumor_class = classify_event(T_RUMOR_V1)
    denial_class = classify_event(T_DENIAL)
    class_names = [c["name"] for c in news_events._EVENT_CLASSES]
    denial_members = [n for n in class_names if "deni" in n or "deny" in n]

    def routed(rev):
        return RoutedRevision(
            revision=rev, security_ids=("SYNTH-SEC-4",), universe_revision="SYNTH-UNI-1"
        )

    db = scratch / "p4.db"
    store = NewsStore(db, source_key="SYNTH-KEY")
    rumor = normalize_news(
        ws_payload(
            item="SYNTH-ITEM-V5R",
            msg="SYNTH-MSG-1",
            title=T_RUMOR_V1,
            url="https://synthwire.example/SYNTH-R1",
            created="2026-10-20T14:00:00Z",
            updated="2026-10-20T14:00:00Z",
        ),
        transport="benzinga_ws",
        received_at=T("2026-10-20T14:05:00Z"),
    )
    denial = normalize_news(
        ws_payload(
            item="SYNTH-ITEM-V5D",
            msg="SYNTH-MSG-D",
            title=T_DENIAL,
            url="https://synthwire.example/SYNTH-D1",
            created="2026-10-20T16:00:00Z",
            updated="2026-10-20T16:00:00Z",
        ),
        transport="benzinga_ws",
        received_at=T("2026-10-20T16:05:00Z"),
    )
    store.commit([routed(rumor)], expected_cursor=None, next_cursor="SYNTH-D-1")
    store.commit([routed(denial)], expected_cursor="SYNTH-D-1", next_cursor="SYNTH-D-2")
    store.close()
    states = {
        json.loads(row[0])["source_item_id"]: json.loads(row[0])
        for row in db_rows(db, "SELECT state_json FROM news_states")
    }
    denial_state = states.get("SYNTH-ITEM-V5D", {})
    denial_keys = sorted(k for k in denial_state if "denial" in k or "denies" in k)
    classified_denial = bool(denial_class) and "den" in denial_class["event_type"]
    news_typed = classified_denial or bool(denial_keys)

    # Thesis lane: the denial as a contrary fact revision linked to the rumor,
    # against an otherwise identical revision with unclassified polarity.
    contrary = project_triggers([rumor_record(), denial_record("contrary", DENIAL_FACT)])
    control = project_triggers(
        [rumor_record(), denial_record("unclassified", CONTROL_FACT)]
    )
    thesis_typed = (
        "contradiction" in contrary["material_delta_triggers"]
        and DENIAL_FACT in contrary["contrary_claim_ids"]
        and RUMOR_FACT in contrary["supporting_claim_ids"]
        and "contradiction" not in control["material_delta_triggers"]
        and control["contrary_claim_ids"] == []
    )
    producer = producer_provenance()
    news_reaches_thesis = producer["wire_writers"] > 0
    if news_typed and thesis_typed and news_reaches_thesis:
        verdict = "PROVEN"
    elif news_typed or thesis_typed:
        verdict = "PARTIAL"
    else:
        verdict = "ABSENT"
    print(
        f"V5 P4 {verdict} "
        f"news lane: classify rumor="
        f"{rumor_class['event_type'] if rumor_class else None} "
        f"deny={denial_class['event_type'] if denial_class else None}, "
        f"{len(class_names)} event classes with denial members={denial_members}, "
        f"store keeps the denial as a plain {denial_state.get('status')} item with "
        f"denial fields={denial_keys}; thesis lane: contrary revision linked to the "
        f"rumor triggers={sorted(contrary['material_delta_triggers'])} "
        f"contrary_claims={len(contrary['contrary_claim_ids'])} rumor still "
        f"supporting={RUMOR_FACT in contrary['supporting_claim_ids']}, unclassified "
        f"control contradiction="
        f"{'contradiction' in control['material_delta_triggers']}; fact-log producer "
        f"source_family={producer['family']} wire writers={producer['wire_writers']}; "
        f"engine/news_events.py:303 engine/news_events.py:398 "
        f"engine/news_impact/thesis.py:1606 engine/news_impact/thesis.py:424 "
        f"engine/news_impact/producer_facts.py:{producer['family_line']} "
        f"tests/test_news_impact_thesis.py:627"
    )
    return verdict


def p5_current_view_and_replay_differ(scratch: Path) -> str:
    """Journal replay at t1 serves v1; current read serves v2; receipt bounds."""
    from engine.qbus_news_contract import normalize_news
    from engine.qbus_news_store import NewsReadRights, NewsStore, RoutedRevision

    def routed(rev):
        return RoutedRevision(
            revision=rev, security_ids=("SYNTH-SEC-5",), universe_revision="SYNTH-UNI-1"
        )

    db = scratch / "p5.db"
    store = NewsStore(db, source_key="SYNTH-KEY")
    v1 = normalize_news(
        ws_payload(
            item="SYNTH-ITEM-V5S",
            msg="SYNTH-MSG-S1",
            title=T_RUMOR_V1,
            url="https://synthwire.example/SYNTH-S1",
            created="2026-10-20T14:00:00Z",
            updated="2026-10-20T14:00:00Z",
        ),
        transport="benzinga_ws",
        received_at=T("2026-10-20T14:05:00Z"),
    )
    v2 = normalize_news(
        ws_payload(
            item="SYNTH-ITEM-V5S",
            msg="SYNTH-MSG-S2",
            title=T_DENIAL,
            url="https://synthwire.example/SYNTH-S1",
            created="2026-10-20T14:00:00Z",
            updated="2026-10-20T18:00:00Z",
        ),
        transport="benzinga_ws",
        received_at=T("2026-10-20T18:05:00Z"),
    )
    # Archive copy of the morning report: published 10:00Z, only received the
    # next day. Possession, not publication, must decide what replay sees.
    archive = normalize_news(
        ws_payload(
            item="SYNTH-ITEM-V5ARCH",
            msg="SYNTH-MSG-A1",
            title="Archive: SYNTH Corp sale report",
            url="https://synthwire.example/SYNTH-ARCH",
            created="2026-10-20T10:00:00Z",
            updated="2026-10-20T10:00:00Z",
        ),
        transport="benzinga_ws",
        received_at=T("2026-10-21T09:00:00Z"),
    )
    store.commit([routed(v1)], expected_cursor=None, next_cursor="SYNTH-K-1")
    store.commit([routed(v2)], expected_cursor="SYNTH-K-1", next_cursor="SYNTH-K-2")
    store.commit([routed(archive)], expected_cursor="SYNTH-K-2", next_cursor="SYNTH-K-3")
    store.close()

    rights = NewsReadRights(frozenset({"benzinga"}))
    reader = NewsStore.open_readonly(db, source_key="SYNTH-KEY")
    page = reader.changes_for_security(
        "SYNTH-SEC-5", after_sequence=0, limit=20, rights=rights
    )
    as_of_t1 = T("2026-10-20T15:00:00Z")
    replay_at_t1 = [r.title for r in page.rows if r.observed_at <= as_of_t1]
    snap = reader.snapshot("SYNTH-SEC-5", limit=10, cursor=None, rights=rights)
    current_titles = [r.title for r in snap.rows]
    projected = reader.projected_changes_for_security(
        "SYNTH-SEC-5", after_sequence=0, limit=20, rights=rights
    )
    projected_titles = [r.title for r in projected.rows]
    flow_before = reader.news_flow("SYNTH-SEC-5", now=T("2026-10-20T19:00:00Z"), rights=rights)
    flow_after = reader.news_flow("SYNTH-SEC-5", now=T("2026-10-21T10:00:00Z"), rights=rights)
    reader.close()

    replay_ok = replay_at_t1 == [T_RUMOR_V1]
    current_ok = (
        T_DENIAL in current_titles
        and T_RUMOR_V1 not in current_titles
        and T_RUMOR_V1 not in projected_titles
    )
    possession = (
        flow_before["reports_24h"] == 1 and flow_after["reports_24h"] == 2
    )
    # The as-of replay below is this script filtering the journal by observed_at;
    # no engine or API reader takes an as-of time, so the replay half is not
    # producer evidence and the property cannot reach PROVEN here.
    verdict = "PARTIAL" if replay_ok and current_ok and possession else "ABSENT"
    print(
        f"V5 P5 {verdict} "
        f"gap: no engine or API reader gives content as of a time; only the "
        f"24h/7d flow counts are bounded by possession "
        f"(engine/qbus_news_velocity.py:303); script-side journal cut as-of 20T15Z "
        f"titles={replay_at_t1} (not producer evidence); current read has "
        f"v2={T_DENIAL in current_titles} v1_never_current="
        f"{T_RUMOR_V1 not in current_titles and T_RUMOR_V1 not in projected_titles}; "
        f"archive pub=20T10Z rcv=21T09Z flow_24h as-of 20T19Z="
        f"{flow_before['reports_24h']} as-of 21T10Z={flow_after['reports_24h']} "
        f"(possession bound); the as-of cut is applied by this proof to the "
        f"journal observed_at because the reader takes no as-of time "
        f"(app/ticker_news.py:912); engine/qbus_news_store.py:2197 "
        f"engine/qbus_news_store.py:1696 "
        f"engine/qbus_news_velocity.py:303 tests/test_qbus_news_velocity.py:1270"
    )
    return verdict


def p6_signed_in_view(scratch: Path) -> str:
    """The news views sit behind the signed-in registration tier."""
    gate = Path(__file__).resolve().parents[3] / "config" / "site_access.yml"
    lines = gate.read_text(encoding="utf-8").splitlines()
    news_entry = next(
        (i + 1 for i, line in enumerate(lines) if line.strip() == "- /news/"), None
    )
    tier, tier_line = None, 0
    if news_entry:
        # The access tier is the enclosing top-level key (exact:/prefixes: sit under it).
        for back in range(news_entry - 2, -1, -1):
            text = lines[back]
            stripped = text.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if text == text.lstrip() and stripped.endswith(":"):
                tier, tier_line = stripped[:-1], back + 1
                break
    api_lines = (
        (gate.parent.parent / "app" / "main.py").read_text(encoding="utf-8").splitlines()
    )
    api_gate = next(
        (i + 1 for i, line in enumerate(api_lines) if line.startswith("def require_user(")),
        0,
    )
    verdict = "HUMAN_GATE" if tier and tier not in ("public", "anonymous") else "ABSENT"
    print(
        f"V5 P6 {verdict} "
        f"news view path /news/ is listed at config/site_access.yml:{news_entry or 1} "
        f"under tier {tier} (config/site_access.yml:{tier_line or 1}); the news API "
        f"reads verify a user token at app/main.py:{api_gate or 1}: viewing the "
        f"versioned stories needs a signed-in human session, not reproducible offline; "
        f"no-test"
    )
    return verdict


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scratch",
        default=None,
        help="directory for every synthetic sqlite file this proof writes",
    )
    args = parser.parse_args()
    scratch = Path(args.scratch or tempfile.mkdtemp(prefix="v91-v5-proof-"))
    scratch.mkdir(parents=True, exist_ok=True)

    tally = {"PROVEN": 0, "PARTIAL": 0, "ABSENT": 0, "HUMAN_GATE": 0}
    for verdict in (
        p1_original_report_stays_versioned(scratch),
        p2_independent_confirmation_recognised(scratch),
        p3_copied_wires_do_not_inflate(scratch),
        p4_denial_stays_versioned_as_denial(scratch),
        p5_current_view_and_replay_differ(scratch),
        p6_signed_in_view(scratch),
    ):
        tally[verdict] += 1
    print(
        "V5 SUMMARY "
        f"proven={tally['PROVEN']} partial={tally['PARTIAL']} "
        f"absent={tally['ABSENT']} human_gate={tally['HUMAN_GATE']} "
        f"rung=OFFLINE_FIXTURE"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
