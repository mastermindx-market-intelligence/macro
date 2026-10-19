"""FIF Q2 tests: append-only judgment ledger and then-known replay (A48).

Every test runs against the in-memory strict conditional store double (whose
``raw_put``/``drop`` helpers seed hostile state) or a temporary local-dir
store for the CLI path. Delayed evidence must never rewrite a past belief:
the original record's bytes stay byte-identical after later corrections.
"""
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from engine.fundamental_forensics import finding_judgments as FJ
from engine.fundamental_forensics.models import stable_id, utc_text
from engine.fundamental_forensics.production_datasets import InMemoryStrictConditionalStore

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "engine" / "fundamental_forensics" / "finding_judgments.py"

NIGHT1 = datetime(2026, 10, 10, 6, 0, tzinfo=timezone.utc)
NIGHT2 = datetime(2026, 10, 12, 6, 0, tzinfo=timezone.utc)
NIGHT3 = datetime(2026, 10, 14, 6, 0, tzinfo=timezone.utc)

BATCH_PREFIX = FJ.JUDGMENT_PREFIX + "/batches/"


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _kernel_row(**overrides):
    row = {
        "finding_id": "find-rev-collapse-fixture-2026q2",
        "detector_id": "revenue_collapse",
        "detector_version": "1.4.0",
        "detector_rule_available_at": "2026-01-15T00:00:00Z",
        "entity_cik": "0001234567",
        "state": "triggered",
        "applicability": "quarterly_revenue",
        "formula": "revenue_growth(current, prior)",
        "thresholds": {"floor": "-0.30"},
        "derived_values": {"growth": "-0.42"},
        "period_ends": ["2026-06-30", "2026-03-31"],
        "inputs": [],
        "missing_inputs": [],
        "evidence_observation_ids": [],
        "evidence_fact_ids": [],
        "source_ready_at": "2026-07-28T00:00:00Z",
        "recorded_ready_at": "2026-07-29T00:00:00Z",
        "computed_at": "2026-10-10T06:00:00.000000Z",
        "limitations": [],
        "display_only": True,
        "authority": "review_priority_only",
    }
    row.update(overrides)
    return row


def _record_kernel(store, rows, clock):
    return FJ.record_judgments(store, kind="kernel", rows=rows, recorded_at=clock)


def _wfinding(fid, detector, **overrides):
    finding = {
        "id": fid,
        "detector": detector,
        "priority": "high",
        "topic": "growth",
        "title_en": f"{detector} review item",
        "title_zh": "审阅条目",
        "summary_en": "quarter over quarter contraction",
        "summary_zh": "季度环比收缩",
        "period_current": "Q2 2026",
        "period_prior": "Q1 2026",
        "formula_en": "revenue_growth(current, prior)",
        "formula_zh": "revenue_growth(current, prior)",
        "threshold_en": "growth < -0.30",
        "threshold_zh": "growth < -0.30",
        "values": [
            {
                "key": "growth",
                "label_en": "Revenue growth",
                "label_zh": "营收增长",
                "current": -0.42,
                "prior": 0.11,
                "delta": None,
                "format": "pct",
            }
        ],
        "evidence": [],
        "limitations_en": [],
        "limitations_zh": [],
        "occurrence_id": None,
        "source_span": None,
        "occurrence_basis": "panel_projection_not_occurrence_bound",
        "display_only": True,
        "authority": "review_priority_only",
    }
    finding.update(overrides)
    return finding


def _workbench_state(companies, generated_at):
    return {
        "schema": "fundamental_forensics.workbench_state/v1",
        "generated_at": generated_at,
        "as_of": "2026-09-30",
        "companies": companies,
    }


def _company(cik, findings):
    return {
        "symbol": "FX",
        "cik": cik,
        "entity_id": None if cik is None else f"mmx.issuer.{cik}",
        "findings": findings,
    }


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _judgment_id(subject_key, content_sha256, supersedes):
    return stable_id("fjudgment", subject_key, content_sha256 or "withdrawn", supersedes or "")


def _all_records(store):
    view = FJ.load_ledger(store)
    return [record for chain in view.chains.values() for record in chain]


def _hostile_batch(store, records, clock):
    """Seed a hand-built batch bypassing the conditional protocol."""
    recorded_at = utc_text(clock)
    body = {"schema": FJ.JUDGMENT_BATCH_SCHEMA, "recorded_at": recorded_at, "records": records}
    digest = hashlib.sha256(_canonical(records)).hexdigest()[:16]
    key = f"{BATCH_PREFIX}{clock.strftime('%Y%m%dT%H%M%SZ')}-{digest}-hostile.json"
    store.raw_put(key, _canonical(body))
    return key


def _correction_record(subject, content, supersedes, clock):
    sha = hashlib.sha256(_canonical(content)).hexdigest()
    return {
        "schema": FJ.JUDGMENT_SCHEMA,
        "judgment_id": _judgment_id(subject["subject_key"], sha, supersedes),
        "kind": subject["kind"],
        "subject_key": subject["subject_key"],
        "entity_ref": subject["entity_ref"],
        "finding_ref": subject["finding_ref"],
        "content_sha256": sha,
        "content": content,
        "status": "present",
        "relation": "correction",
        "supersedes": supersedes,
        "recorded_at": utc_text(clock),
        "source_ready_at": subject["source_ready_at"],
        "change_reasons": ["content"],
    }


class _UnlistedStore(InMemoryStrictConditionalStore):
    """A listing-inconsistent double: hides keys that still exist on read."""

    def __init__(self):
        super().__init__()
        self.hidden: set[str] = set()

    def list_prefix(self, prefix):
        return [key for key in super().list_prefix(prefix) if key not in self.hidden]


class _ExplodingStore(InMemoryStrictConditionalStore):
    """A store whose conditional put and read-back both fail."""

    def __init__(self):
        super().__init__()
        self.conditional_calls = 0

    def put_bytes_strict_conditional(self, key, data, *, expected_version, content_type="application/octet-stream"):
        self.conditional_calls += 1
        raise RuntimeError("transport exploded before any commit proof")

    def get_bytes_strict_bounded(self, key, maximum_bytes):
        raise RuntimeError("read-back channel is down")


# ---------------------------------------------------------------------------
# 1. Then-known replay: delayed evidence does not rewrite past beliefs
# ---------------------------------------------------------------------------


def test_then_known_replay_returns_prior_value_before_the_correction() -> None:
    store = InMemoryStrictConditionalStore()
    subject = FJ.kernel_row(_kernel_row())
    v1 = _kernel_row(derived_values={"growth": "-0.42"})
    v2 = _kernel_row(derived_values={"growth": "-0.55"}, source_ready_at="2026-10-13T00:00:00Z")
    report1 = _record_kernel(store, [v1], NIGHT1)
    original_payload = store.get_bytes_strict_bounded(report1["batch_key"], FJ.HARD_MAX_BATCH_BYTES)
    _record_kernel(store, [v2], NIGHT3)

    replay_early = FJ.replay_then_known(store, recorded_cutoff=NIGHT2)
    assert replay_early["schema"] == FJ.JUDGMENT_REPLAY_SCHEMA
    assert len(replay_early["subjects"]) == 1
    early = replay_early["subjects"][0]
    assert early["visible"]["relation"] == "original"
    assert early["visible"]["content"]["derived_values"] == {"growth": "-0.42"}
    assert early["versions_visible"] == 1
    assert early["versions_total"] == 2

    replay_late = FJ.replay_then_known(store, recorded_cutoff=NIGHT3)
    late = replay_late["subjects"][0]
    assert late["visible"]["relation"] == "correction"
    assert late["visible"]["content"]["derived_values"] == {"growth": "-0.55"}
    assert late["visible"]["change_reasons"] == ["content"]
    assert late["visible"]["supersedes"] == early["visible"]["judgment_id"]
    assert late["versions_visible"] == 2

    # The original batch bytes are untouched after the correction landed.
    assert store.get_bytes_strict_bounded(report1["batch_key"], FJ.HARD_MAX_BATCH_BYTES) == original_payload
    chain = FJ.history(store, subject["subject_key"])
    assert [record["relation"] for record in chain] == ["original", "correction"]


# ---------------------------------------------------------------------------
# 2. Re-recording identical content appends nothing
# ---------------------------------------------------------------------------


def test_identical_content_records_nothing_and_writes_no_batch() -> None:
    store = InMemoryStrictConditionalStore()
    rows = [_kernel_row()]
    first = _record_kernel(store, rows, NIGHT1)
    assert first["originals"] == 1 and first["batch_key"]
    second = _record_kernel(store, rows, NIGHT2)
    assert second["batch_key"] is None
    assert second["unchanged"] == 1
    assert second["originals"] == second["corrections"] == second["withdrawals"] == 0
    assert store.list_prefix(BATCH_PREFIX) == [first["batch_key"]]
    assert len(FJ.history(store, FJ.kernel_row(rows[0])["subject_key"])) == 1


# ---------------------------------------------------------------------------
# 3. Batch idempotency and collision
# ---------------------------------------------------------------------------


def test_identical_batch_already_present_is_idempotent() -> None:
    store = _UnlistedStore()
    rows = [_kernel_row()]
    first = _record_kernel(store, rows, NIGHT1)
    key = first["batch_key"]
    store.hidden = {key}
    # The listing misses the batch (an eventually-consistent read), so the run
    # recomputes the identical batch and must reconcile to idempotent success.
    again = _record_kernel(store, rows, NIGHT1)
    assert again["batch_key"] == key
    assert again["originals"] == 1
    assert store.conditional_writes


def test_different_bytes_at_the_same_key_raise_batch_collision() -> None:
    store = _UnlistedStore()
    rows = [_kernel_row()]
    first = _record_kernel(store, rows, NIGHT1)
    key = first["batch_key"]
    store.raw_put(key, b'{"schema":"fundamental_forensics.finding_judgment_batch/v1"}')
    store.hidden = {key}
    with pytest.raises(FJ.FindingJudgmentError) as excinfo:
        _record_kernel(store, rows, NIGHT1)
    assert excinfo.value.code == "batch_collision"


# ---------------------------------------------------------------------------
# 4. Withdrawal respects the run's entity scope
# ---------------------------------------------------------------------------


def test_withdrawal_only_touches_in_scope_subjects_missing_from_the_run() -> None:
    store = InMemoryStrictConditionalStore()
    state_night1 = _workbench_state(
        {
            "FXA": _company(1111111, [_wfinding("rev-collapse:q2-2026", "revenue_collapse")]),
            "FXB": _company(2222222, [_wfinding("gm-compress:q2-2026", "margin_compression")]),
            "FXC": _company(3333333, [_wfinding("accrual-spike:q2-2026", "accrual_spike")]),
        },
        utc_text(NIGHT1),
    )
    rows1, scope1, clock1 = FJ.workbench_rows_from_state(state_night1)
    FJ.record_judgments(store, kind="workbench", rows=rows1, recorded_at=clock1, scope_entities=scope1)

    # Night 3 fully covers only FXA (which now reports no findings) and FXB
    # (same finding). FXC is absent, so it is out of scope and untouched.
    state_night3 = _workbench_state(
        {
            "FXA": _company(1111111, []),
            "FXB": _company(2222222, [_wfinding("gm-compress:q2-2026", "margin_compression")]),
        },
        utc_text(NIGHT3),
    )
    rows3, scope3, clock3 = FJ.workbench_rows_from_state(state_night3)
    report = FJ.record_judgments(store, kind="workbench", rows=rows3, recorded_at=clock3, scope_entities=scope3)
    assert report["withdrawals"] == 1
    assert report["unchanged"] == 1
    assert report["corrections"] == 0 and report["originals"] == 0

    subject_a = stable_id("fjsubject", "workbench", "1111111", "rev-collapse:q2-2026")
    subject_b = stable_id("fjsubject", "workbench", "2222222", "gm-compress:q2-2026")
    subject_c = stable_id("fjsubject", "workbench", "3333333", "accrual-spike:q2-2026")

    replay_before = FJ.replay_then_known(store, recorded_cutoff=NIGHT2)
    visible = {row["subject_key"]: row["visible"] for row in replay_before["subjects"]}
    assert visible[subject_a]["status"] == "present"
    assert visible[subject_a]["relation"] == "original"

    replay_after = FJ.replay_then_known(store, recorded_cutoff=NIGHT3)
    rows_by_key = {row["subject_key"]: row for row in replay_after["subjects"]}
    visible = {key: row["visible"] for key, row in rows_by_key.items()}
    withdrawn = visible[subject_a]
    assert withdrawn["status"] == "withdrawn"
    assert withdrawn["content"] is None and withdrawn["content_sha256"] is None
    assert withdrawn["change_reasons"] == ["status"]
    assert visible[subject_b]["status"] == "present"
    assert rows_by_key[subject_b]["versions_total"] == 1
    # Out of scope: untouched, still the original tip.
    assert visible[subject_c]["status"] == "present"
    assert visible[subject_c]["relation"] == "original"
    assert len(FJ.history(store, subject_c)) == 1
    assert len(FJ.history(store, subject_a)) == 2


def test_scope_none_never_withdraws() -> None:
    store = InMemoryStrictConditionalStore()
    state = _workbench_state({"FXA": _company(1111111, [_wfinding("rev-collapse:q2-2026", "revenue_collapse")])}, utc_text(NIGHT1))
    rows, scope, clock = FJ.workbench_rows_from_state(state)
    FJ.record_judgments(store, kind="workbench", rows=rows, recorded_at=clock, scope_entities=scope)
    report = FJ.record_judgments(store, kind="workbench", rows=[], recorded_at=NIGHT3, scope_entities=None)
    assert report["withdrawals"] == 0
    assert report["batch_key"] is None


# ---------------------------------------------------------------------------
# 5. A -> B -> A records three judgments with distinct ids
# ---------------------------------------------------------------------------


def test_content_round_trip_records_three_distinct_judgments() -> None:
    store = InMemoryStrictConditionalStore()
    content_a = _kernel_row(derived_values={"growth": "-0.42"})
    content_b = _kernel_row(derived_values={"growth": "-0.55"})
    subject = FJ.kernel_row(content_a)
    _record_kernel(store, [content_a], NIGHT1)
    _record_kernel(store, [content_b], NIGHT2)
    _record_kernel(store, [content_a], NIGHT3)

    chain = FJ.history(store, subject["subject_key"])
    assert len(chain) == 3
    ids = [record["judgment_id"] for record in chain]
    assert len(set(ids)) == 3
    assert chain[1]["supersedes"] == ids[0]
    assert chain[2]["supersedes"] == ids[1]
    assert chain[2]["content_sha256"] == chain[0]["content_sha256"]

    for cutoff, expected_growth, expected_relation in (
        (NIGHT1, "-0.42", "original"),
        (NIGHT2, "-0.55", "correction"),
        (NIGHT3, "-0.42", "correction"),
    ):
        replay = FJ.replay_then_known(store, recorded_cutoff=cutoff)
        visible = replay["subjects"][0]["visible"]
        assert visible["content"]["derived_values"] == {"growth": expected_growth}
        assert visible["relation"] == expected_relation


# ---------------------------------------------------------------------------
# 6. Chain corruption refuses with the matching code
# ---------------------------------------------------------------------------


def _two_step_chain(store):
    v1 = _kernel_row(derived_values={"growth": "-0.42"})
    v2 = _kernel_row(derived_values={"growth": "-0.55"})
    _record_kernel(store, [v1], NIGHT1)
    _record_kernel(store, [v2], NIGHT2)
    records = _all_records(store)
    original = next(record for record in records if record["relation"] == "original")
    correction = next(record for record in records if record["relation"] == "correction")
    return original, correction


def test_forged_judgment_id_is_refused() -> None:
    store = InMemoryStrictConditionalStore()
    original, _ = _two_step_chain(store)
    forged = dict(original)
    forged["judgment_id"] = "fjudgment_forged0000000000000000000000000000000000000000000000000000"
    _hostile_batch(store, [forged], NIGHT2)
    with pytest.raises(FJ.FindingJudgmentChainError) as excinfo:
        FJ.load_ledger(store)
    assert excinfo.value.code == "judgment_id_mismatch"


def test_forked_chain_is_refused() -> None:
    store = InMemoryStrictConditionalStore()
    original, correction = _two_step_chain(store)
    rival = _correction_record(original, correction["content"], original["judgment_id"], NIGHT3)
    _hostile_batch(store, [rival], NIGHT3)
    with pytest.raises(FJ.FindingJudgmentChainError) as excinfo:
        FJ.load_ledger(store)
    assert excinfo.value.code == "fork"


def test_dangling_supersedes_is_refused() -> None:
    store = InMemoryStrictConditionalStore()
    original, _ = _two_step_chain(store)
    dangling = _correction_record(original, original["content"], "fjudgment_missing0000000000000000000000000", NIGHT3)
    _hostile_batch(store, [dangling], NIGHT3)
    with pytest.raises(FJ.FindingJudgmentChainError) as excinfo:
        FJ.load_ledger(store)
    assert excinfo.value.code == "dangling_supersedes"


def test_chain_clock_regression_is_refused() -> None:
    store = InMemoryStrictConditionalStore()
    _, correction = _two_step_chain(store)
    regressive = _correction_record(correction, correction["content"], correction["judgment_id"], NIGHT1)
    _hostile_batch(store, [regressive], NIGHT1)
    with pytest.raises(FJ.FindingJudgmentChainError) as excinfo:
        FJ.load_ledger(store)
    assert excinfo.value.code == "clock_regression"


def test_missing_and_duplicate_originals_are_refused() -> None:
    store = InMemoryStrictConditionalStore()
    original, _ = _two_step_chain(store)
    twin = dict(original)
    twin["judgment_id"] = _judgment_id(original["subject_key"], original["content_sha256"], None)
    twin["recorded_at"] = utc_text(NIGHT3)
    _hostile_batch(store, [twin], NIGHT3)
    with pytest.raises(FJ.FindingJudgmentChainError) as excinfo:
        FJ.load_ledger(store)
    assert excinfo.value.code == "duplicate_original"

    # A chain whose original never existed: only a correction is seeded.
    only_correction = InMemoryStrictConditionalStore()
    _, correction = _two_step_chain(only_correction)
    original_batch_keys = list(only_correction.list_prefix(BATCH_PREFIX))
    for key in original_batch_keys:
        only_correction.drop(key)
    orphaned = InMemoryStrictConditionalStore()
    _hostile_batch(orphaned, [correction], NIGHT2)
    with pytest.raises(FJ.FindingJudgmentChainError) as excinfo:
        FJ.load_ledger(orphaned)
    assert excinfo.value.code == "missing_original"


def test_duplicate_subject_within_one_call_is_refused() -> None:
    store = InMemoryStrictConditionalStore()
    rows = [_kernel_row(), _kernel_row(derived_values={"growth": "-0.55"})]
    with pytest.raises(FJ.FindingJudgmentError) as excinfo:
        _record_kernel(store, rows, NIGHT1)
    assert excinfo.value.code == "duplicate_subject"
    assert store.list_prefix(BATCH_PREFIX) == []


# ---------------------------------------------------------------------------
# 7. Clock discipline: caller-supplied clocks only
# ---------------------------------------------------------------------------


def test_missing_or_naive_clocks_are_refused() -> None:
    store = InMemoryStrictConditionalStore()
    rows = [_kernel_row()]
    for bad in (None, "2026-10-10T06:00:00", datetime(2026, 10, 10, 6, 0), 42):
        with pytest.raises(FJ.FindingJudgmentError) as excinfo:
            FJ.record_judgments(store, kind="kernel", rows=rows, recorded_at=bad)
        assert excinfo.value.code == "recorded_at_required"
    for bad in (None, "2026-10-12 06:00:00", datetime(2026, 10, 12, 6, 0)):
        with pytest.raises(FJ.FindingJudgmentError) as excinfo:
            FJ.replay_then_known(store, recorded_cutoff=bad)
        assert excinfo.value.code == "cutoff_required"
    naive_state = _workbench_state(
        {"FXA": _company(1111111, [_wfinding("rev-collapse:q2-2026", "revenue_collapse")])},
        "2026-10-10T06:00:00",
    )
    with pytest.raises(FJ.FindingJudgmentError) as excinfo:
        FJ.workbench_rows_from_state(naive_state)
    assert excinfo.value.code == "recorded_at_required"
    with pytest.raises(FJ.FindingJudgmentError) as excinfo:
        FJ.workbench_rows_from_state({})
    assert excinfo.value.code == "recorded_at_required"


def test_recording_behind_a_tip_is_refused() -> None:
    store = InMemoryStrictConditionalStore()
    _record_kernel(store, [_kernel_row()], NIGHT2)
    with pytest.raises(FJ.FindingJudgmentError) as excinfo:
        _record_kernel(store, [_kernel_row(derived_values={"growth": "-0.55"})], NIGHT1)
    assert excinfo.value.code == "clock_regression"
    assert store.list_prefix(BATCH_PREFIX)  # the earlier run's batch is the only one


def test_module_source_contains_no_wall_clock_call() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    for forbidden in ("datetime.now", "datetime.utcnow", "time.time", "date.today"):
        assert forbidden not in source


# ---------------------------------------------------------------------------
# 8. Effect-unknown: one write attempt, no retry
# ---------------------------------------------------------------------------


def test_unreconcilable_write_is_effect_unknown_and_never_retried() -> None:
    store = _ExplodingStore()
    with pytest.raises(FJ.FindingJudgmentEffectUnknownError) as excinfo:
        _record_kernel(store, [_kernel_row()], NIGHT1)
    assert excinfo.value.code == "effect_unknown"
    assert store.conditional_calls == 1
    assert store.unconditional_writes == []
    assert store.list_prefix(BATCH_PREFIX) == []


# ---------------------------------------------------------------------------
# 9. Kernel adapter contracts
# ---------------------------------------------------------------------------


def test_kernel_row_missing_required_key_is_refused() -> None:
    for key in ("finding_id", "detector_id", "detector_version", "entity_cik", "state", "period_ends"):
        row = _kernel_row()
        del row[key]
        with pytest.raises(FJ.FindingJudgmentError) as excinfo:
            FJ.kernel_row(row)
        assert excinfo.value.code == "kernel_row_required"
        with pytest.raises(FJ.FindingJudgmentError) as excinfo:
            _record_kernel(InMemoryStrictConditionalStore(), [row], NIGHT1)
        assert excinfo.value.code == "kernel_row_required"


def test_computed_at_alone_does_not_create_a_correction() -> None:
    store = InMemoryStrictConditionalStore()
    _record_kernel(store, [_kernel_row(computed_at="2026-10-10T06:00:00.000000Z")], NIGHT1)
    report = _record_kernel(store, [_kernel_row(computed_at="2026-10-11T09:30:00.000000Z")], NIGHT2)
    assert report["unchanged"] == 1
    assert report["corrections"] == 0
    assert report["batch_key"] is None


def test_detector_version_change_records_detector_version_reason() -> None:
    store = InMemoryStrictConditionalStore()
    _record_kernel(store, [_kernel_row(detector_version="1.4.0")], NIGHT1)
    report = _record_kernel(store, [_kernel_row(detector_version="1.5.0")], NIGHT2)
    assert report["corrections"] == 1
    chain = FJ.history(store, FJ.kernel_row(_kernel_row())["subject_key"])
    assert chain[-1]["change_reasons"] == ["content", "detector_version"]


# ---------------------------------------------------------------------------
# 10. Workbench adapter on a synthetic state
# ---------------------------------------------------------------------------


def test_workbench_rows_from_state_two_companies_three_findings() -> None:
    finding_a1 = _wfinding("rev-collapse:q2-2026", "revenue_collapse")
    finding_a2 = _wfinding("gm-compress:q2-2026", "margin_compression")
    finding_b1 = _wfinding("accrual-spike:q1-2026", "accrual_spike")
    state = _workbench_state(
        {
            "FXA": _company(1111111, [finding_a1, finding_a2]),
            "FXNO": _company(None, [finding_b1]),
        },
        "2026-10-10T06:00:00+00:00",
    )
    rows, scope_entities, recorded_at = FJ.workbench_rows_from_state(state)
    assert len(rows) == 3
    assert scope_entities == {"1111111", "FXNO"}
    assert recorded_at == NIGHT1
    by_ref = {row["finding_ref"]: row for row in rows}
    assert set(by_ref) == {"rev-collapse:q2-2026", "gm-compress:q2-2026", "accrual-spike:q1-2026"}
    assert by_ref["rev-collapse:q2-2026"]["subject_key"] == stable_id(
        "fjsubject", "workbench", "1111111", "rev-collapse:q2-2026"
    )
    # A null CIK falls back to the symbol identity.
    assert by_ref["accrual-spike:q1-2026"]["subject_key"] == stable_id(
        "fjsubject", "workbench", "FXNO", "accrual-spike:q1-2026"
    )
    assert by_ref["accrual-spike:q1-2026"]["entity_ref"] == "FXNO"
    assert by_ref["rev-collapse:q2-2026"]["content"] == finding_a1
    assert by_ref["rev-collapse:q2-2026"]["source_ready_at"] is None
    for row in rows:
        assert row["content_sha256"] == hashlib.sha256(_canonical(row["content"])).hexdigest()


# ---------------------------------------------------------------------------
# 11. No consumer writes: the import guard
# ---------------------------------------------------------------------------


def _import_offenders(tree):
    target = "engine.fundamental_forensics.finding_judgments"
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == target or alias.name.startswith(target + "."):
                    hits.append(node.lineno)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                if node.module == target or node.module.startswith(target + "."):
                    hits.append(node.lineno)
                elif node.module == "engine.fundamental_forensics":
                    if any(alias.name == "finding_judgments" for alias in node.names):
                        hits.append(node.lineno)
            elif node.level >= 1:
                if node.module == "finding_judgments" or (
                    node.module is None
                    and any(alias.name == "finding_judgments" for alias in node.names)
                ):
                    hits.append(node.lineno)
    return hits


def test_no_consumer_module_imports_finding_judgments() -> None:
    allowed_prefix = "engine/fundamental_forensics/"
    allowed_exact = {"scripts/fif_finding_judgments.py"}
    offenders: list[tuple[str, list[int]]] = []
    scanned = 0
    for base in ("engine", "app", "lib", "scripts"):
        for path in sorted((ROOT / base).rglob("*.py")):
            scanned += 1
            rel = path.relative_to(ROOT).as_posix()
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            hits = _import_offenders(tree)
            if hits and not rel.startswith(allowed_prefix) and rel not in allowed_exact:
                offenders.append((rel, hits))
    assert scanned > 500, "the source walk unexpectedly missed the repository trees"
    assert not offenders, (
        "modules outside engine/fundamental_forensics and scripts/fif_finding_judgments.py "
        f"import the judgment ledger (prophet/risk/sni consumers included): {offenders}"
    )
    for family in ("engine/prophet*", "engine/risk*", "engine/sni*"):
        for path in sorted(ROOT.glob(family)):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            assert not _import_offenders(tree), f"{rel} imports the judgment ledger"


# ---------------------------------------------------------------------------
# 12. CLI against a temporary local store
# ---------------------------------------------------------------------------


def _local_conditional_store_available(tmp_path):
    pytest.importorskip("engine.research_vault.r2_store")
    from engine.research_vault.r2_store import LocalStore

    try:
        probe = LocalStore(tmp_path / "probe")
        if not callable(getattr(probe, "put_bytes_strict_conditional", None)):
            return False
        probe.validate_strict_conditional_write_capability()
    except Exception as exc:  # noqa: BLE001 - any unavailability skips the CLI lane
        pytest.skip(f"local-dir store cannot perform conditional writes: {exc}")
    return True


def test_cli_record_state_then_replay(tmp_path) -> None:
    if not _local_conditional_store_available(tmp_path):
        pytest.skip("local-dir store lacks strict conditional writes")
    script = ROOT / "scripts" / "fif_finding_judgments.py"
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            _workbench_state(
                {"FXA": _company(1111111, [_wfinding("rev-collapse:q2-2026", "revenue_collapse")])},
                utc_text(NIGHT1),
            )
        ),
        encoding="utf-8",
    )
    store_dir = tmp_path / "store"

    recorded = subprocess.run(
        [sys.executable, str(script), "record-state", "--state", str(state_path), "--local-store", str(store_dir)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert recorded.returncode == 0, recorded.stderr
    report = json.loads(recorded.stdout)
    assert report["schema"] == FJ.JUDGMENT_BATCH_SCHEMA
    assert report["originals"] == 1
    assert report["batch_key"] and report["batch_key"].startswith(BATCH_PREFIX)

    replayed = subprocess.run(
        [
            sys.executable,
            str(script),
            "replay",
            "--recorded-cutoff",
            "2026-10-11T00:00:00Z",
            "--local-store",
            str(store_dir),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert replayed.returncode == 0, replayed.stderr
    document = json.loads(replayed.stdout)
    assert document["schema"] == FJ.JUDGMENT_REPLAY_SCHEMA
    assert len(document["subjects"]) == 1
    subject = document["subjects"][0]
    assert subject["visible"]["relation"] == "original"
    assert subject["visible"]["content"]["id"] == "rev-collapse:q2-2026"

    history = subprocess.run(
        [
            sys.executable,
            str(script),
            "history",
            "--subject",
            subject["subject_key"],
            "--local-store",
            str(store_dir),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert history.returncode == 0, history.stderr
    chain = json.loads(history.stdout)["records"]
    assert [record["relation"] for record in chain] == ["original"]

    refused = subprocess.run(
        [
            sys.executable,
            str(script),
            "replay",
            "--recorded-cutoff",
            "2026-10-11T00:00:00",
            "--local-store",
            str(store_dir),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert refused.returncode == 2
    assert json.loads(refused.stdout)["error"]["code"] == "cutoff_required"
