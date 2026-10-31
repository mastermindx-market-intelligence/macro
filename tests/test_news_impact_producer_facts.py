"""Tests for engine.news_impact.producer_facts (W3 producer stage two).

Hermetic: no network, no repository data files, tmp_path only. Every event is synthetic
text about a fictional issuer with a neutral id; no filing text is used. Each event
builder is positive-controlled against the frozen news_impact_event.v1 contract before
the producer sees it, so a failure points at the producer rather than the fixture.
"""
from __future__ import annotations

import json
from collections import Counter
from hashlib import sha256
from pathlib import Path

import pytest

from engine.news_impact import producer_facts as pf
from engine.news_impact import thesis
from engine.news_impact.validate import validate_event

ISSUER = "cik:0000000001"
OTHER = "cik:0000000002"
THIRD = "cik:0000000003"
DOC = "sec:0000000000-26-000001:synth_a.htm"
DOC_B = "sec:0000000000-26-000002:synth_b.htm"
FLAGS = {"may_rank": False, "may_size": False, "may_gate": False, "prophet_authority": False}
FY27 = {"year": 2027, "quarter": None, "calendar_end": None, "period_kind": "fiscal_year"}
SOURCE_SHA = sha256(b"synthetic-source").hexdigest()

ACTION_TEXT = "The board authorized an additional repurchase program."
GUIDE_TEXT = "The company raised its full-year revenue outlook."
PARTNER_TEXT = "The company announced a partnership on its widget platform."
OBJECT = "Synthetic Widget Platform"


def fid(seed: str) -> str:
    return "fact_" + sha256(seed.encode()).hexdigest()[:24]


def at(day: int) -> str:
    return f"2026-10-{day:02d}T12:00:00Z"


def span(text: str, doc: str = DOC) -> dict:
    n = len(text.encode())
    h = sha256(text.encode()).hexdigest()
    return {
        "schema": "source_span.v1",
        "authority": "context_only",
        "span_id": "span_" + sha256((doc + text).encode()).hexdigest()[:20],
        "document_id": doc,
        "document_version": 1,
        "locator": {
            "kind": "text_span",
            "sub_kind": "transcript_segment",
            "segment_index": 0,
            "span_start_byte": 0,
            "span_end_byte": n,
        },
        "text_sha256": h,
        "display_excerpt": text,
        "rights_profile": "rp_unknown_v1",
        "receipt_state": "byte_replayed",
        "receipt": {
            "source_sha256": SOURCE_SHA,
            "segment_index": 0,
            "segment_sha256": SOURCE_SHA,
            "segment_bytes": 200,
            "span_start_byte": 0,
            "span_end_byte": n,
            "text_sha256": h,
        },
        "unreplayable_reason": None,
    }


def evidence(text: str, doc: str = DOC) -> dict:
    return {"claimed_quote": text, "span": span(text, doc)}


def absence(subject: str) -> dict:
    return {
        "schema": "field_absence.v1",
        "authority": "context_only",
        "reason": "not_stated",
        "subject": subject,
        "detail": "",
        "missing_fields": [subject],
    }


def qpoint(value, basis: str, text: str = ACTION_TEXT, doc: str = DOC) -> dict:
    return {
        "form": "point",
        "value": value,
        "bound": "exact",
        "unit": "USD",
        "currency": "USD",
        "basis": basis,
        "period": dict(FY27),
        "negated": False,
        "evidence": evidence(text, doc),
    }


def qrange(low, high, basis: str, text: str = ACTION_TEXT) -> dict:
    return {
        "form": "range",
        "low": low,
        "high": high,
        "unit": "USD",
        "currency": "USD",
        "basis": basis,
        "period": dict(FY27),
        "negated": False,
        "evidence": evidence(text),
    }


def qabsent(subject: str) -> dict:
    return {"form": "absent", "absence": absence(subject)}


def _envelope(schema: str, seed: str, day: int, doc: str) -> dict:
    return {
        "schema": schema,
        "authority": "context_only",
        "prophet_flags": dict(FLAGS),
        "unsolicited_instruction_detected": False,
        "fact_id": fid(seed),
        "document_id": doc,
        "observed_at": at(day),
        "source_available_at": at(day),
        "supersedes_fact_id": None,
        "company_id": ISSUER,
        "issuer_role": "subject",
        "novelty": "new_magnitude_timing_commitment_counterparty",
        "negated": False,
    }


def t1(seed: str = "t1", day: int = 1, doc: str = DOC, **overrides) -> dict:
    event = _envelope(pf.T1, seed, day, doc)
    event.update({
        "action_type": "share_repurchase",
        "commitment_status": "authorized",
        "primary_amount_role": "incremental_authorization",
        "incremental_amount": qpoint(50_000_000, "incremental", doc=doc),
        "remaining_authorization": qabsent("remaining_authorization"),
        "executed_amount": qabsent("executed_amount"),
        "horizon_period": dict(FY27),
        "action_span": evidence(ACTION_TEXT, doc),
    })
    event.update(overrides)
    return event


def t2(seed: str = "t2", day: int = 1, doc: str = DOC, **overrides) -> dict:
    event = _envelope(pf.T2, seed, day, doc)
    event.update({
        "demand_stage": "guidance",
        "metric": "revenue",
        "commitment_status": "announced",
        "stated_amount": qpoint(900_000_000, "total", GUIDE_TEXT, doc),
        "fiscal_period": dict(FY27),
        "revision_direction": "raised",
        "counterparty_company_id": absence("counterparty_company_id"),
        "baseline": {
            "type": "UNKNOWN",
            "timestamp": absence("baseline_timestamp"),
            "contributors": absence("baseline_contributors"),
            "coverage": absence("baseline_coverage"),
            "period": absence("baseline_period"),
            "basis": absence("baseline_basis"),
            "age_days": absence("baseline_age_days"),
        },
    })
    event.update(overrides)
    return event


def t3(seed: str = "t3", day: int = 1, doc: str = DOC, **overrides) -> dict:
    event = _envelope(pf.T3, seed, day, doc)
    event.update({
        "event_kind": "partnership",
        "object_name": OBJECT,
        "commitment_status": "announced",
        "counterparty_company_id": OTHER,
        "counterparty_role": "partner",
        "stated_quantity": qabsent("stated_quantity"),
        "economic_claim_class": "none_stated",
        "action_span": evidence(PARTNER_TEXT, doc),
    })
    event.update(overrides)
    return event


def assert_valid(event: dict) -> None:
    report = validate_event(event)
    assert report.ok, [(issue.code, issue.path) for issue in report.issues]


def row(event: dict, case: str = "case_001", shadow: bool = False) -> dict:
    return {"case_id": case, "shadow": shadow, "novelty_source": "label_provisional", "event": event}


def write_rows(path: Path, rows: list[dict]) -> Path:
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    return path


def run_rows(tmp_path: Path, rows: list[dict], name: str = "out", as_of: str | None = None):
    events = write_rows(tmp_path / f"{name}_events.jsonl", rows)
    out = tmp_path / name
    report = pf.run([events], out, as_of)
    log = json.loads((out / "fact_log.json").read_text())
    views = [json.loads(line) for line in (out / "thesis_views.jsonl").read_text().splitlines() if line]
    evidence_rows = [
        json.loads(line) for line in (out / "prophet_evidence.jsonl").read_text().splitlines() if line
    ]
    return report, log, views, evidence_rows


def by_fact(log: dict) -> dict:
    return {rec["fact_id"]: rec for rec in log["records"]}


def _walk_keys(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from _walk_keys(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk_keys(value)


# --------------------------------------------------------------------------- fixtures


@pytest.mark.parametrize("builder", [t1, t2, t3])
def test_fixture_events_satisfy_the_frozen_contract(builder):
    assert_valid(builder())


# --------------------------------------------------------------------------- 1. T1 key


def test_t1_authorization_key_carries_action_type_and_horizon_token():
    slot = pf.fact_slot(t1())
    assert slot == {
        "kind": "t1_authorization_program",
        "action_type": "share_repurchase",
        "horizon_token": "FY2027",
    }


def test_t1_executed_role_keys_as_execution_under_program():
    event = t1(
        primary_amount_role="executed",
        commitment_status="executed",
        incremental_amount=qabsent("incremental_amount"),
        executed_amount=qpoint(20_000_000, "total"),
    )
    assert_valid(event)
    assert pf.fact_slot(event)["kind"] == "t1_execution_under_program"


def test_t1_horizon_absence_omits_the_token():
    slot = pf.fact_slot(t1(horizon_period=absence("horizon_period")))
    assert "horizon_token" not in slot


# --------------------------------------------------------------------------- 2. period tokens


@pytest.mark.parametrize(
    ("period", "token"),
    [
        ({"year": 2027, "quarter": None, "calendar_end": None, "period_kind": "fiscal_year"}, "FY2027"),
        ({"year": 2027, "quarter": 3, "calendar_end": None, "period_kind": "quarter"}, "FY2027Q3"),
        ({"year": 2027, "quarter": None, "calendar_end": "2027-06-30", "period_kind": "half_year"}, "FY2027H-0630"),
        ({"year": 2027, "quarter": None, "calendar_end": None, "period_kind": "half_year"}, "FY2027H"),
        ({"year": 2027, "quarter": None, "calendar_end": "2027-09-30", "period_kind": "nine_months"}, "FY2027N-0930"),
        ({"year": 2027, "quarter": None, "calendar_end": None, "period_kind": "nine_months"}, "FY2027N"),
        (
            {"year": 2027, "quarter": None, "calendar_end": None, "period_kind": "multi_year", "end_year": 2029},
            "FY2027-2029",
        ),
        ({"year": 2027, "quarter": None, "calendar_end": None, "period_kind": "multi_year"}, "FY2027M"),
    ],
)
def test_period_token_table(period, token):
    assert pf.period_token(period) == token
    assert len(token) <= 16


@pytest.mark.parametrize(
    "period",
    [
        {"year": 2027, "quarter": None, "calendar_end": None, "period_kind": "quarter"},
        {"year": None, "quarter": None, "calendar_end": None, "period_kind": "fiscal_year"},
        {"year": True, "quarter": None, "calendar_end": None, "period_kind": "fiscal_year"},
        {"year": 2027, "quarter": None, "calendar_end": None, "period_kind": "season"},
    ],
)
def test_period_token_rejects_untokenizable_periods(period):
    with pytest.raises(pf.Reject) as exc:
        pf.period_token(period)
    assert exc.value.code == "period_not_tokenizable"


# --------------------------------------------------------------------------- 3. T2 counterparty


def test_t2_counterparty_absence_single_and_array():
    assert pf.fact_slot(t2())["counterparty_company_id"] is None
    single = t2(counterparty_company_id=OTHER)
    assert_valid(single)
    assert pf.fact_slot(single)["counterparty_company_id"] == OTHER
    assert pf.fact_slot(t2())["fiscal_period_token"] == "FY2027"
    many = t2(counterparty_company_id=[OTHER, THIRD])
    assert_valid(many)
    with pytest.raises(pf.Reject) as exc:
        pf.fact_slot(many)
    assert exc.value.code == "counterparty_set_not_keyable"


def test_t2_counterparty_array_is_rejected_by_the_run(tmp_path):
    report, log, _, _ = run_rows(tmp_path, [
        row(t2("a", 1, counterparty_company_id=[OTHER, THIRD])),
        row(t2("b", 2)),
    ])
    assert report["rejected"] == {"counterparty_set_not_keyable": 1}
    assert len(log["records"]) == 1


# --------------------------------------------------------------------------- 4. T3 object_name


def test_t3_object_name_over_the_fact_key_limit_rejects_without_truncating():
    base = " ".join(f"{OBJECT} Edition {n}" for n in range(1, 8))
    long_name = base[: pf.OBJECT_NAME_MAX + 1]
    at_limit = base[: pf.OBJECT_NAME_MAX]
    event = t3(object_name=long_name)
    assert_valid(event)
    with pytest.raises(pf.Reject) as exc:
        pf.fact_slot(event)
    assert exc.value.code == "object_name_over_fact_key_limit"
    assert pf.fact_slot(t3(object_name=at_limit))["object_name"] == at_limit


def test_t3_object_name_absence_is_not_keyable():
    with pytest.raises(pf.Reject) as exc:
        pf.fact_slot(t3(object_name=absence("object_name")))
    assert exc.value.code == "object_name_not_keyable"


def test_t3_slot_shape():
    assert pf.fact_slot(t3()) == {
        "kind": "t3_object_counterparty",
        "event_kind": "partnership",
        "object_name": OBJECT,
        "counterparty_company_id": OTHER,
    }


# --------------------------------------------------------------------------- 5. leaf payload


def test_leaf_point_int_and_integral_float_normalisation():
    counts: Counter = Counter()
    event = t1()
    leaf = pf.leaf_payload(event, pf.fact_slot(event), counts)
    assert leaf["incremental"] == 50_000_000 and type(leaf["incremental"]) is int
    assert "remaining" not in leaf and "executed" not in leaf
    assert leaf["currency"] == "USD"
    assert leaf["horizon_token"] == "FY2027"
    assert leaf["template"] == pf.T1 and leaf["commitment_status"] == "authorized" and leaf["negated"] is False
    assert counts == Counter()

    floaty = t1(incremental_amount=qpoint(50_000_000.0, "incremental"))
    leaf = pf.leaf_payload(floaty, pf.fact_slot(floaty), counts)
    assert leaf["incremental"] == 50_000_000 and type(leaf["incremental"]) is int
    assert counts["leaf_int_normalised"] == 1


def test_leaf_range_carries_low_and_high():
    counts: Counter = Counter()
    event = t1(incremental_amount=qrange(40_000_000, 60_000_000.0, "incremental"))
    assert_valid(event)
    leaf = pf.leaf_payload(event, pf.fact_slot(event), counts)
    assert leaf["incremental"] == {"low": 40_000_000, "high": 60_000_000}
    assert type(leaf["incremental"]["high"]) is int
    assert counts["leaf_range_carried"] == 1 and counts["leaf_int_normalised"] == 1


def test_leaf_absent_quantity_omits_key_and_fingerprint_is_absent():
    event = t3()
    leaf = pf.leaf_payload(event, pf.fact_slot(event), Counter())
    assert "stated_quantity" not in leaf and "currency" not in leaf
    assert leaf["object_name"] == OBJECT
    assert thesis.quantity_fingerprint(leaf, pf.T3) == {"form": "absent"}
    t1_event = t1()
    t1_leaf = pf.leaf_payload(t1_event, pf.fact_slot(t1_event), Counter())
    present = thesis.quantity_fingerprint(t1_leaf, pf.T1)
    assert present["form"] == "present" and len(present["canonical_sha256"]) == 64


# --------------------------------------------------------------------------- evidence ladder


def test_evidence_ref_prefers_action_span_and_binds_span_id():
    event = t1()
    ref = pf.evidence_ref(event)
    assert ref == {"form": "owner_span_ref", "document_id": DOC, "span_id": event["action_span"]["span"]["span_id"]}


def test_evidence_ref_t2_falls_back_to_field_absence_without_a_span():
    event = t2(stated_amount=qabsent("stated_amount"))
    assert_valid(event)
    ref = pf.evidence_ref(event)
    assert ref["schema"] == "field_absence.v1" and ref["missing_fields"] == ["evidence"]
    ceiling = t2(stated_amount=qabsent("stated_amount"), option_ceiling=qpoint(5_000_000, "total", GUIDE_TEXT))
    assert pf.evidence_ref(ceiling)["span_id"] == ceiling["option_ceiling"]["evidence"]["span"]["span_id"]


def test_evidence_ref_unbound_span_id_rejects():
    event = t1()
    event["action_span"]["span"]["span_id"] = "span_not_hex"
    with pytest.raises(pf.Reject) as exc:
        pf.evidence_ref(event)
    assert exc.value.code == "evidence_span_unbound"


# --------------------------------------------------------------------------- 6. novelty


def test_novelty_revision_manifestation_and_new_value(tmp_path):
    first = t1("n1", 1)
    repeat = t1("n2", 2, doc=DOC_B)
    changed = t1("n3", 3, incremental_amount=qpoint(75_000_000, "incremental"))
    report, log, _, _ = run_rows(tmp_path, [row(changed, "c3"), row(repeat, "c2"), row(first, "c1")])
    records = by_fact(log)
    assert records[first["fact_id"]]["record_kind"] == "fact_revision"
    assert records[first["fact_id"]]["novelty"] == "new_magnitude_timing_commitment_counterparty"
    assert records[first["fact_id"]]["reports_fact_id"] is None
    assert records[repeat["fact_id"]]["record_kind"] == "manifestation"
    assert records[repeat["fact_id"]]["cluster_grain"] == "article_manifestation"
    assert records[repeat["fact_id"]]["novelty"] == "new_reporting_of_old_fact"
    assert records[repeat["fact_id"]]["reports_fact_id"] == first["fact_id"]
    assert records[changed["fact_id"]]["record_kind"] == "fact_revision"
    assert report["n_records"] == {"fact_revision": 2, "manifestation": 1}
    assert report["rejected"] == {} and report["deferred"] == {}


def test_different_counterparty_is_a_separate_key(tmp_path):
    plain = t2("k1", 1)
    with_party = t2("k2", 2, counterparty_company_id=OTHER)
    _, log, _, _ = run_rows(tmp_path, [row(plain), row(with_party)])
    records = by_fact(log)
    assert records[plain["fact_id"]]["record_kind"] == "fact_revision"
    assert records[with_party["fact_id"]]["record_kind"] == "fact_revision"
    assert records[plain["fact_id"]]["fact_key"] != records[with_party["fact_id"]]["fact_key"]


# --------------------------------------------------------------------------- 7. N3 cycle


def test_cycling_values_report_the_equal_valued_revision(tmp_path):
    a1 = t1("a1", 1)
    b = t1("b", 2, incremental_amount=qpoint(75_000_000, "incremental"))
    a2 = t1("a2", 3)
    a3 = t1("a3", 4)
    _, log, _, _ = run_rows(tmp_path, [row(a1), row(b), row(a2), row(a3)])
    records = by_fact(log)
    assert records[b["fact_id"]]["record_kind"] == "fact_revision"
    for repeat in (a2, a3):
        assert records[repeat["fact_id"]]["record_kind"] == "manifestation"
        assert records[repeat["fact_id"]]["reports_fact_id"] == a1["fact_id"]


# --------------------------------------------------------------------------- 8. log validity


def test_fact_log_validates_with_dense_seq_and_no_forbidden_keys(tmp_path):
    rows = [row(t1("v1", 1)), row(t1("v2", 2)), row(t2("v3", 3)), row(t3("v4", 4, negated=True))]
    _, log, _, _ = run_rows(tmp_path, rows)
    thesis.validate_log(log)
    assert [rec["log_seq"] for rec in log["records"]] == [1, 2, 3, 4]
    assert not set(_walk_keys(log)) & thesis.FORBIDDEN_KEYS
    polarities = {rec["fact_id"]: rec["polarity"] for rec in log["records"]}
    assert polarities[rows[3]["event"]["fact_id"]] == "contrary"
    assert polarities[rows[0]["event"]["fact_id"]] == "unclassified"
    for rec in log["records"]:
        assert rec["provenance"]["root_family_id"] == "0000000000-26-000001"
        assert rec["cluster_id"].startswith("ev2_") and len(rec["cluster_id"]) == 20
        assert rec["ci_event_id"]["schema"] == "field_absence.v1"


# --------------------------------------------------------------------------- 9. projection


def test_projection_one_view_per_root_revision_and_empty_before_all_facts(tmp_path):
    rows = [row(t1("p1", 1)), row(t1("p2", 2)), row(t2("p3", 3)), row(t2("p4", 4))]
    report, _, views, _ = run_rows(tmp_path, rows)
    assert report["n_views"] == 2 and len(views) == 2
    assert report["project_error"] is None and report["as_of_utc"] == at(4)
    assert {view["view"]["company_id"] for view in views} == {ISSUER}

    early, _, early_views, _ = run_rows(tmp_path, rows, name="early", as_of="2020-01-01T00:00:00Z")
    assert early["n_views"] == 0 and early_views == []
    assert early["project_error"] is None


# --------------------------------------------------------------------------- 10. adapter


def test_adapter_counts_accepted_and_a_flagged_event_does_not_stop_the_run(tmp_path):
    flagged = t3("f1", 3)
    flagged["prophet_flags"]["may_rank"] = True
    rows = [row(t1("f2", 1), "c1"), row(t2("f3", 2), "c2"), row(flagged, "c3")]
    report, log, _, evidence_rows = run_rows(tmp_path, rows)
    assert len(log["records"]) == 3
    assert report["adapter"] == {"adapter:PROPHET_FLAG_TRUE": 1, "ok": 2}
    assert len(evidence_rows) == 2
    assert {r["case_id"] for r in evidence_rows} == {"c1", "c2"}
    assert all(r["shadow"] is False for r in evidence_rows)


def test_a_contract_valid_range_becomes_prophet_evidence(tmp_path):
    # The v1 range shape carries no ``bound``; since ni-prophet-adapter-2 the adapter
    # projects bound "exact" (DEC:NEWS-IMPACT-ADAPTER-RANGE-BOUND), so no event crashes.
    ranged = t1("g1", 1, incremental_amount=qrange(40_000_000, 60_000_000, "incremental"))
    assert_valid(ranged)
    report, log, views, evidence_rows = run_rows(tmp_path, [row(ranged, "c1"), row(t3("g2", 2), "c2")])
    assert len(log["records"]) == 2 and report["n_views"] == 2
    assert report["adapter"] == {"ok": 2}
    assert [r["case_id"] for r in evidence_rows] == ["c1", "c2"]
    ranges = [q for q in evidence_rows[0]["evidence"]["quantities"] if q["form"] == "range"]
    assert [(q["slot"], q["bound"]) for q in ranges] == [("incremental_amount", "exact")]


@pytest.mark.parametrize("error", [KeyError, TypeError, ValueError])
def test_adapter_owner_crash_is_counted_by_class_not_fatal(tmp_path, monkeypatch, error):
    # An owner crash on one event is counted by class; the rest of the batch still projects.
    real = pf.adapt_batch
    calls = []

    def crash_first(candidates):
        calls.append(len(candidates))
        if len(calls) == 1:
            raise error("synthetic")
        return real(candidates)

    monkeypatch.setattr(pf, "adapt_batch", crash_first)
    report, log, views, evidence_rows = run_rows(tmp_path, [row(t1("k1", 1), "c1"), row(t3("k2", 2), "c2")])
    assert calls == [1, 1]
    assert len(log["records"]) == 2 and report["n_views"] == 2
    assert report["adapter"] == {f"adapter_crash:{error.__name__}": 1, "ok": 1}
    assert [r["case_id"] for r in evidence_rows] == ["c2"]


# --------------------------------------------------------------------------- 11. refused out


def test_out_under_the_shared_fact_log_directory_is_refused(tmp_path, monkeypatch):
    events = write_rows(tmp_path / "events.jsonl", [row(t1())])
    monkeypatch.chdir(tmp_path)
    log_dir = Path(thesis.DEFAULT_LOG_PATH).parent
    assert pf.main(["--events", str(events), "--out", str(tmp_path / log_dir / "x")]) == 2
    assert pf.main(["--events", str(events), "--out", str(log_dir)]) == 2
    assert not (tmp_path / log_dir).exists()
    repo_log_dir = Path(pf.__file__).resolve().parents[2] / log_dir
    with pytest.raises(pf.Reject) as exc:
        pf.run([events], repo_log_dir / "x")
    assert exc.value.code == "out_refused"
    assert not (repo_log_dir / "x").exists()
    assert pf.main(["--events", str(events), "--out", str(tmp_path / "ok")]) == 0


# --------------------------------------------------------------------------- 12. row rejects


def test_shadow_rows_propagate_shadow_mode(tmp_path):
    rows = [row(t1("s1", 1), "c1", shadow=True), row(t1("s2", 2, doc=DOC_B), "c2", shadow=True)]
    report, _, views, evidence_rows = run_rows(tmp_path, rows)
    assert report["mode"] == "shadow"
    assert views and all(v["shadow"] is True for v in views)
    assert evidence_rows and all(r["shadow"] is True for r in evidence_rows)


def test_mixed_shadow_duplicate_and_unsolicited_rows_are_rejected(tmp_path):
    mixed, _, _, _ = run_rows(tmp_path, [row(t1("m1", 1), shadow=True), row(t1("m2", 2))], name="mixed")
    assert mixed["rejected"] == {"shadow_mixed": 2} and mixed["n_records"] == {}

    dup = t1("d1", 1)
    flagged = t1("u1", 2)
    flagged["unsolicited_instruction_detected"] = True
    foreign = t1("x1", 3)
    foreign["authority"] = "authoritative"
    report, log, _, _ = run_rows(tmp_path, [
        row(dup, "c1"), row(dict(dup), "c2"), row(flagged, "c3"), row(foreign, "c4"), {"case_id": "c5"},
    ])
    assert report["rejected"] == {
        "authority_not_context_only": 1,
        "duplicate_fact_id": 1,
        "event_missing": 1,
        "unsolicited_instruction": 1,
    }
    assert len(log["records"]) == 1 and report["mode"] == "adjudicated"


# --------------------------------------------------------------------------- 13. report


def test_report_holds_counts_and_codes_only(tmp_path):
    report, _, _, _ = run_rows(tmp_path, [row(t1("r1", 1)), row(t3("r2", 2))])
    text = (tmp_path / "out" / "facts_report.json").read_text()
    assert OBJECT not in text
    assert "50000000" not in text
    assert ISSUER not in text and DOC not in text
    assert json.loads(text) == report
    assert report["producer_facts_version"] == pf.PRODUCER_FACTS_VERSION


# --------------------------------------------------------------------------- 14. determinism


def test_two_runs_write_byte_identical_outputs(tmp_path):
    rows = [row(t1("z1", 1)), row(t1("z2", 2)), row(t2("z3", 3)), row(t3("z4", 4))]
    run_rows(tmp_path, rows, name="one")
    run_rows(tmp_path, list(reversed(rows)), name="two")
    for name in pf.OUTPUT_NAMES:
        assert (tmp_path / "one" / name).read_bytes() == (tmp_path / "two" / name).read_bytes(), name


# --------------------------------------------------------------------------- R6 canonical amount terms / directional evidence
# Explicit correction records below use the existing fact-log owner; stage-two
# novelty assignment is not being claimed as a native correction acquisition path.


def _r6_correction_projection(tmp_path, events, *, mutate_leaf=None, links=None):
    import copy

    for event in events:
        assert_valid(event)
    _, produced, _, _ = run_rows(tmp_path, [row(e, f"r6_{i}") for i, e in enumerate(events)])
    records = by_fact(produced)
    log = thesis.FactLog(records=()).to_dict()
    leaves = {}
    latest = {}
    for event in events:
        rec = copy.deepcopy(records[event["fact_id"]])
        rec.pop("log_seq", None)
        key = thesis.canonical_json(rec["fact_key"])
        if key in latest:
            rec.update(record_kind="fact_revision", cluster_grain="fact_revision",
                       novelty="corrected_fact", supersedes_fact_id=latest[key],
                       reports_fact_id=None)
        if links and event["fact_id"] in links:
            rec["linked_fact_ids"] = links[event["fact_id"]]
        latest[key] = event["fact_id"]
        log = thesis.append_records(log, [rec])
        leaves[event["fact_id"]] = pf.leaf_payload(event, pf.fact_slot(event), Counter())
    if mutate_leaf:
        mutate_leaf(leaves)
    owners = thesis.OwnerSnapshot(leaf_payloads=leaves)
    views = thesis.project(log, owners, events[-1]["observed_at"],
                           prior_as_of_utc=events[0]["observed_at"],
                           prior_owners=thesis.OwnerSnapshot(leaf_payloads={
                               events[0]["fact_id"]: leaves[events[0]["fact_id"]]
                           }))
    return views, log, leaves


def _r6_condition(view):
    return next(w for w in view["weakening_conditions"]
                if w["code"] == "source_correction_reduces_magnitude")


def test_r6_preserves_each_canonical_quantity_and_its_evidence_without_aliasing():
    import copy

    event = t1(remaining_authorization=qpoint(80_000_000, "total"))
    event["remaining_authorization"]["unit"] = "EUR"
    event["remaining_authorization"]["currency"] = "EUR"
    assert_valid(event)
    before = copy.deepcopy(event)
    leaf = pf.leaf_payload(event, pf.fact_slot(event), Counter())
    assert leaf["currency"] == "USD"  # legacy display field, not comparison authority
    assert leaf["quantity_terms"] == {
        "incremental": event["incremental_amount"],
        "remaining": event["remaining_authorization"],
    }
    leaf["quantity_terms"]["remaining"]["evidence"]["claimed_quote"] = "changed locally"
    assert event == before
    assert thesis.quantity_fingerprint(leaf, pf.T1) == thesis.quantity_fingerprint(
        {"incremental": 50_000_000, "remaining": 80_000_000}, pf.T1)


@pytest.mark.parametrize("builder,field,basis", [
    (t1, "incremental_amount", "incremental"),
    (t1, "remaining_authorization", "total"),
    (t1, "executed_amount", "total"),
    (t2, "stated_amount", "total"),
])
def test_r6_exact_lower_amount_qualifies_through_real_leaf_adapter(tmp_path, builder, field, basis):
    first = builder("r6_old", 1, **{field: qpoint(80_000_000, basis)})
    later = builder("r6_new", 2, doc=DOC_B, **{field: qpoint(70_000_000, basis, doc=DOC_B)})
    views, log, leaves = _r6_correction_projection(tmp_path, [first, later])
    view = next(v for v in views if v["original_proposition_fact_id"] == first["fact_id"])
    assert _r6_condition(view) == {
        "code": "source_correction_reduces_magnitude", "armed": True,
        "evidence_fact_ids": [later["fact_id"]],
    }
    assert {"source_correction", "changed_numeric_terms"} <= set(view["material_delta_triggers"])
    assert view["prophet_flags"] == FLAGS and view["authority"] == "context_only"
    assert "28 September" not in json.dumps(view["display"])
    assert "remaining authorization" not in view["display"]["plain_status"]
    assert "source correction" in view["display"]["plain_status"].lower()


@pytest.mark.parametrize("value", [80_000_000, 90_000_000])
def test_r6_equal_or_increased_amount_does_not_qualify(tmp_path, value):
    first = t1("r6_old", 1, incremental_amount=qpoint(80_000_000, "incremental"))
    later = t1("r6_new", 2, incremental_amount=qpoint(value, "incremental"))
    views, _, _ = _r6_correction_projection(tmp_path, [first, later])
    assert _r6_condition(views[0])["armed"] is False
    assert _r6_condition(views[0])["evidence_fact_ids"] == []
    assert "source_correction" in views[0]["material_delta_triggers"]


@pytest.mark.parametrize("change", [
    "legacy_only", "missing_current", "missing_prior", "wrong_predecessor",
    "bool", "nan", "infinite", "negative", "string", "over_limit",
    "leaf_conflict", "leaf_bool", "currency", "unit", "scaled_unit",
    "basis", "period", "period_absent", "invalid_calendar", "reversed_period",
    "bound", "negated", "leaf_negated", "range", "missing_evidence",
    "missing_currency", "horizon", "basis_run_rate", "basis_per_share",
    "basis_percent", "period_multi_year", "period_half_year",
    "period_nine_months", "extra_period_end", "template_old",
    "template_new", "template_absent",
])
def test_r6_unqualified_pairs_preserve_correction_without_direction(tmp_path, change):
    import copy

    first = t1("r6_old", 1, incremental_amount=qpoint(80_000_000, "incremental"))
    later = t1("r6_new", 2, incremental_amount=qpoint(70_000_000, "incremental"))

    def mutate(leaves):
        old = leaves[first["fact_id"]]
        current = leaves[later["fact_id"]]
        quantity = current["quantity_terms"]["incremental"]
        old_quantity = old["quantity_terms"]["incremental"]
        if change == "legacy_only":
            old.pop("quantity_terms"); current.pop("quantity_terms")
        elif change == "missing_current":
            leaves.pop(later["fact_id"])
        elif change == "missing_prior":
            # Preserve the first leaf for the comparison snapshot, but no terms.
            old.clear()
        elif change == "wrong_predecessor":
            unrelated = copy.deepcopy(old)
            leaves[fid("unrelated")] = unrelated
            old.clear()
        elif change in {"bool", "nan", "infinite", "negative", "string", "over_limit"}:
            value = {"bool": True, "nan": float("nan"), "infinite": float("inf"),
                     "negative": -1, "string": "70000000", "over_limit": 10**16}[change]
            quantity["value"] = value
            if change not in {"nan", "infinite"}:
                current["incremental"] = value
        elif change == "leaf_conflict":
            current["incremental"] = 90_000_000
        elif change == "leaf_bool":
            current["incremental"] = True
        elif change == "currency":
            quantity["currency"] = "EUR"; quantity["unit"] = "EUR"
        elif change == "unit":
            quantity["unit"] = "USD millions"
        elif change == "scaled_unit":
            quantity["unit"] = old_quantity["unit"] = "USD millions"
        elif change == "basis":
            quantity["basis"] = "total"
        elif change == "period":
            quantity["period"]["year"] = 2028
        elif change == "period_absent":
            quantity["period"] = old_quantity["period"] = absence("period")
        elif change == "invalid_calendar":
            quantity["period"]["calendar_end"] = old_quantity["period"]["calendar_end"] = "2027-02-30"
        elif change == "reversed_period":
            quantity["period"]["end_year"] = old_quantity["period"]["end_year"] = 2026
        elif change == "bound":
            quantity["bound"] = old_quantity["bound"] = "up_to"
        elif change == "negated":
            quantity["negated"] = True
        elif change == "leaf_negated":
            current["negated"] = True
        elif change == "range":
            quantity.pop("value"); quantity.pop("bound")
            quantity.update(form="range", low=60_000_000, high=70_000_000)
            current["incremental"] = {"low": 60_000_000, "high": 70_000_000}
        elif change == "missing_evidence":
            quantity.pop("evidence")
        elif change == "missing_currency":
            quantity.pop("currency")
        elif change == "horizon":
            current["horizon_token"] = "FY2028"
        elif change.startswith("basis_"):
            quantity["basis"] = old_quantity["basis"] = change.removeprefix("basis_")
        elif change.startswith("period_"):
            quantity["period"]["period_kind"] = old_quantity["period"]["period_kind"] = change.removeprefix("period_")
        elif change == "extra_period_end":
            quantity["period"]["end_year"] = old_quantity["period"]["end_year"] = 2027
        elif change == "template_old":
            old["template"] = pf.T2
        elif change == "template_new":
            current["template"] = pf.T2
        elif change == "template_absent":
            current.pop("template")

    if change in {"nan", "infinite"}:
        with pytest.raises(ValueError, match="Out of range float values"):
            _r6_correction_projection(tmp_path, [first, later], mutate_leaf=mutate)
        return
    views, _, _ = _r6_correction_projection(tmp_path, [first, later], mutate_leaf=mutate)
    condition = _r6_condition(views[0])
    assert condition["armed"] is False and condition["evidence_fact_ids"] == []
    assert {"source_correction", "changed_numeric_terms"} <= set(views[0]["material_delta_triggers"])


def test_r6_superseded_reduction_does_not_support_current_condition(tmp_path):
    events = [
        t1("r6_initial", 1, incremental_amount=qpoint(80_000_000, "incremental")),
        t1("r6_lower", 2, incremental_amount=qpoint(60_000_000, "incremental")),
        t1("r6_recovery", 3, incremental_amount=qpoint(70_000_000, "incremental")),
    ]
    views, _, _ = _r6_correction_projection(tmp_path, events)
    assert _r6_condition(views[0]) == {
        "code": "source_correction_reduces_magnitude", "armed": False, "evidence_fact_ids": [],
    }
    assert views[0]["live_fact_ids"] == [events[-1]["fact_id"]]
    assert "source_correction" in views[0]["material_delta_triggers"]


def test_r6_only_live_reducing_corrections_are_attributed(tmp_path):
    first = t1("r6_auth", 1, incremental_amount=qpoint(80_000_000, "incremental"))
    execution = t1("r6_exec", 2, primary_amount_role="executed",
                   incremental_amount=qabsent("incremental_amount"),
                   executed_amount=qpoint(20_000_000, "total"))
    reduction = t1("r6_auth_lower", 3, incremental_amount=qpoint(70_000_000, "incremental"))
    increase = t1("r6_exec_higher", 4, primary_amount_role="executed",
                  incremental_amount=qabsent("incremental_amount"),
                  executed_amount=qpoint(30_000_000, "total"))
    links = {event["fact_id"]: [first["fact_id"]] for event in (execution, increase)}
    views, _, _ = _r6_correction_projection(tmp_path, [first, execution, reduction, increase], links=links)
    view = next(v for v in views if v["original_proposition_fact_id"] == first["fact_id"])
    assert _r6_condition(view)["evidence_fact_ids"] == [reduction["fact_id"]]
    assert _r6_condition(view)["armed"] is True


def test_r6_nonmonetary_quantity_remains_direction_unqualified(tmp_path):
    first = t3("r6_qold", 1, stated_quantity=qpoint(80, "total"))
    later = t3("r6_qnew", 2, stated_quantity=qpoint(70, "total"))
    views, _, _ = _r6_correction_projection(tmp_path, [first, later])
    assert _r6_condition(views[0])["armed"] is False


def test_r6_matching_concrete_quarter_can_qualify(tmp_path):
    first = t2("r6_qtr_old", 1, stated_amount=qpoint(80_000_000, "total"))
    later = t2("r6_qtr_new", 2, stated_amount=qpoint(70_000_000, "total"))
    for event in (first, later):
        period = {"year": 2027, "quarter": 1, "calendar_end": "2027-03-31", "period_kind": "quarter"}
        event["fiscal_period"] = dict(period)
        event["stated_amount"]["period"] = dict(period)
    views, _, _ = _r6_correction_projection(tmp_path, [first, later])
    assert _r6_condition(views[0])["armed"] is True
    assert _r6_condition(views[0])["evidence_fact_ids"] == [later["fact_id"]]
