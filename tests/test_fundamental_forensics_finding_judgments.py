"""FIF Q2 tests: sequenced hash-chained judgment ledger and then-known replay (A48).

Every test runs against the in-memory strict conditional store double (whose
``raw_put``/``drop`` helpers seed hostile state) or a temporary local-dir
store for the CLI path. Delayed evidence must never rewrite a past belief:
the original batch bytes stay byte-identical after later corrections, and
the ledger is a numbered batch sequence committed by a compare-and-swap HEAD.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from engine.fundamental_forensics import finding_judgments as FJ
from engine.fundamental_forensics.models import stable_id, utc_text
from engine.fundamental_forensics.production_datasets import InMemoryStrictConditionalStore
from engine.research_vault.r2_store import VersionedBytes

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "engine" / "fundamental_forensics" / "finding_judgments.py"
CLI_PATH = ROOT / "scripts" / "fif_finding_judgments.py"

NIGHT1 = datetime(2026, 10, 10, 6, 0, tzinfo=timezone.utc)
NIGHT2 = datetime(2026, 10, 12, 6, 0, tzinfo=timezone.utc)
NIGHT3 = datetime(2026, 10, 14, 6, 0, tzinfo=timezone.utc)
NIGHT4 = datetime(2026, 10, 16, 6, 0, tzinfo=timezone.utc)

BATCH_PREFIX = FJ.JUDGMENT_PREFIX + "/batches/"
HEAD_KEY = FJ.JUDGMENT_HEAD_KEY


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


def _record_kernel(store, rows, clock, **kwargs):
    return FJ.record_judgments(store, kind="kernel", rows=rows, recorded_at=clock, **kwargs)


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


def _batch_key(sequence):
    return f"{BATCH_PREFIX}{sequence:08d}.json"


def _read_batch(store, sequence):
    return store.get_bytes_strict_bounded(_batch_key(sequence), FJ.HARD_MAX_BATCH_BYTES)


def _seed_head(store, sequence, tip_sha256):
    store.raw_put(HEAD_KEY, _canonical({
        "schema": FJ.JUDGMENT_HEAD_SCHEMA,
        "sequence": sequence,
        "tip_sha256": tip_sha256,
    }))


def _seed_batch(store, sequence, records, clock, predecessor_sha, source_generated_at=None):
    """Seed a hand-built sequenced batch (plus HEAD) bypassing the protocol."""
    body = {
        "schema": FJ.JUDGMENT_BATCH_SCHEMA,
        "sequence": sequence,
        "predecessor_sha256": predecessor_sha,
        "recorded_at": utc_text(clock),
        "source_generated_at": source_generated_at,
        "records": records,
    }
    payload = _canonical(body)
    store.raw_put(_batch_key(sequence), payload)
    _seed_head(store, sequence, hashlib.sha256(payload).hexdigest())
    return payload


def _seed_orphan(store, sequence, records, clock, predecessor_sha):
    """Seed a batch beyond HEAD: the residue of an interrupted HEAD write."""
    body = {
        "schema": FJ.JUDGMENT_BATCH_SCHEMA,
        "sequence": sequence,
        "predecessor_sha256": predecessor_sha,
        "recorded_at": utc_text(clock),
        "source_generated_at": None,
        "records": records,
    }
    payload = _canonical(body)
    store.raw_put(_batch_key(sequence), payload)
    return payload


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
        "source_generated_at": None,
        "change_reasons": ["content"],
    }


def _expect_code(excinfo):
    """Every FindingJudgmentError carries a non-empty machine code."""
    error = excinfo.value
    assert isinstance(error, FJ.FindingJudgmentError)
    assert isinstance(error.code, str) and error.code
    return error.code


class _NoListingStore(InMemoryStrictConditionalStore):
    """A listing-free double: the ledger must never depend on a listing."""

    def __init__(self, raising):
        super().__init__()
        self.raising = raising
        self.list_calls = 0

    def list_prefix(self, prefix):
        self.list_calls += 1
        if self.raising:
            raise AssertionError("the judgment ledger must never list the store")
        return []


class _HeadReadExplodingStore(InMemoryStrictConditionalStore):
    """A double whose versioned HEAD read raises."""

    def __init__(self):
        super().__init__()
        self.explode = False

    def get_bytes_strict_bounded_versioned(self, key, maximum_bytes):
        if self.explode and key == HEAD_KEY:
            raise RuntimeError("head channel down")
        return super().get_bytes_strict_bounded_versioned(key, maximum_bytes)


class _BatchReadExplodingStore(InMemoryStrictConditionalStore):
    """A double whose strict batch reads raise."""

    def __init__(self):
        super().__init__()
        self.explode = False

    def get_bytes_strict_bounded(self, key, maximum_bytes):
        if self.explode and key.startswith(BATCH_PREFIX):
            raise RuntimeError("batch channel down")
        return super().get_bytes_strict_bounded(key, maximum_bytes)


class _ExplodingBatchStore(InMemoryStrictConditionalStore):
    """A batch transport that explodes pre-commit and takes the read channel with it."""

    def __init__(self):
        super().__init__()
        self.explode_put = False
        self.explode_read = False
        self.conditional_calls = 0

    def put_bytes_strict_conditional(self, key, data, *, expected_version, content_type="application/octet-stream"):
        self.conditional_calls += 1
        if self.explode_put and key != HEAD_KEY:
            self.explode_put = False
            self.explode_read = True
            raise RuntimeError("batch transport exploded before any commit proof")
        return super().put_bytes_strict_conditional(
            key, data, expected_version=expected_version, content_type=content_type
        )

    def get_bytes_strict_bounded(self, key, maximum_bytes):
        if self.explode_read and key != HEAD_KEY:
            raise RuntimeError("read-back channel is down")
        return super().get_bytes_strict_bounded(key, maximum_bytes)


class _HeadCasExplodingStore(InMemoryStrictConditionalStore):
    """A double whose HEAD compare-and-swap fails before or after committing."""

    def __init__(self):
        super().__init__()
        self.explode_before_commit = False
        self.explode_after_commit = False

    def put_bytes_strict_conditional(self, key, data, *, expected_version, content_type="application/octet-stream"):
        if key == HEAD_KEY:
            if self.explode_after_commit:
                self.explode_after_commit = False
                self.raw_put(key, data)
                raise RuntimeError("head transport failed after commit")
            if self.explode_before_commit:
                raise RuntimeError("head cas exploded before commit")
        return super().put_bytes_strict_conditional(
            key, data, expected_version=expected_version, content_type=content_type
        )


class _LateWriterStore:
    """Writer B's carrier: everything read before its first write is the pre-A snapshot."""

    def __init__(self, backend):
        self._backend = backend
        self._frozen = True

    def validate_strict_conditional_write_capability(self):
        return self._backend.validate_strict_conditional_write_capability()

    def get_bytes_strict_bounded(self, key, maximum_bytes):
        if self._frozen and key.startswith(BATCH_PREFIX):
            return None
        return self._backend.get_bytes_strict_bounded(key, maximum_bytes)

    def get_bytes_strict_bounded_versioned(self, key, maximum_bytes):
        if self._frozen and key == HEAD_KEY:
            return VersionedBytes(data=None, version=None)
        return self._backend.get_bytes_strict_bounded_versioned(key, maximum_bytes)

    def put_bytes_strict_conditional(self, key, data, *, expected_version, content_type="application/octet-stream"):
        self._frozen = False
        return self._backend.put_bytes_strict_conditional(
            key, data, expected_version=expected_version, content_type=content_type
        )


def _load_cli():
    spec = importlib.util.spec_from_file_location("fif_finding_judgments_cli_under_test", CLI_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# 1. Then-known replay: delayed evidence does not rewrite past beliefs
# ---------------------------------------------------------------------------


def test_then_known_replay_returns_prior_value_before_the_correction() -> None:
    store = InMemoryStrictConditionalStore()
    subject = FJ.kernel_row(_kernel_row())
    v1 = _kernel_row(derived_values={"growth": "-0.42"})
    v2 = _kernel_row(derived_values={"growth": "-0.55"}, source_ready_at="2026-10-13T00:00:00Z")
    report1 = _record_kernel(store, [v1], NIGHT1)
    original_payload = _read_batch(store, 1)
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
    assert _read_batch(store, 1) == original_payload
    chain = FJ.history(store, subject["subject_key"])
    assert [record["relation"] for record in chain] == ["original", "correction"]
    assert FJ.load_ledger(store).head_sequence == 2


# ---------------------------------------------------------------------------
# 2. Re-recording identical content appends nothing
# ---------------------------------------------------------------------------


def test_identical_content_records_nothing_and_writes_no_batch() -> None:
    store = InMemoryStrictConditionalStore()
    rows = [_kernel_row()]
    first = _record_kernel(store, rows, NIGHT1)
    assert first["originals"] == 1 and first["batch_key"] == _batch_key(1)
    assert first["sequence"] == 1
    second = _record_kernel(store, rows, NIGHT2)
    assert second["batch_key"] is None and second["sequence"] is None
    assert second["unchanged"] == 1
    assert second["originals"] == second["corrections"] == second["withdrawals"] == 0
    assert FJ.load_ledger(store).batch_keys == (_batch_key(1),)
    assert len(FJ.history(store, FJ.kernel_row(rows[0])["subject_key"])) == 1


# ---------------------------------------------------------------------------
# 3. Withdrawal respects the run's entity scope
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
    rows1, scope1, generated1 = FJ.workbench_rows_from_state(state_night1)
    FJ.record_judgments(
        store, kind="workbench", rows=rows1, recorded_at=NIGHT1,
        source_generated_at=generated1, scope_entities=scope1,
    )

    # Night 3 fully covers only FXA (which now reports no findings) and FXB
    # (same finding). FXC is absent, so it is out of scope and untouched.
    state_night3 = _workbench_state(
        {
            "FXA": _company(1111111, []),
            "FXB": _company(2222222, [_wfinding("gm-compress:q2-2026", "margin_compression")]),
        },
        utc_text(NIGHT3),
    )
    rows3, scope3, generated3 = FJ.workbench_rows_from_state(state_night3)
    report = FJ.record_judgments(
        store, kind="workbench", rows=rows3, recorded_at=NIGHT3,
        source_generated_at=generated3, scope_entities=scope3,
    )
    assert report["withdrawals"] == 1
    assert report["unchanged"] == 1
    assert report["corrections"] == 0 and report["originals"] == 0

    subject_a = stable_id("fjsubject", "workbench", "0001111111", "rev-collapse:q2-2026")
    subject_b = stable_id("fjsubject", "workbench", "0002222222", "gm-compress:q2-2026")
    subject_c = stable_id("fjsubject", "workbench", "0003333333", "accrual-spike:q2-2026")

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
    state = _workbench_state(
        {"FXA": _company(1111111, [_wfinding("rev-collapse:q2-2026", "revenue_collapse")])}, utc_text(NIGHT1)
    )
    rows, scope, generated = FJ.workbench_rows_from_state(state)
    FJ.record_judgments(
        store, kind="workbench", rows=rows, recorded_at=NIGHT1,
        source_generated_at=generated, scope_entities=scope,
    )
    report = _record_kernel(store, [], NIGHT3)
    assert report["withdrawals"] == 0
    assert report["batch_key"] is None and report["sequence"] is None


# ---------------------------------------------------------------------------
# 4. A -> B -> A records three judgments with distinct ids
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
# 5. Chain corruption refuses with the matching code
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
    _seed_batch(store, 3, [forged], NIGHT3, hashlib.sha256(_read_batch(store, 2)).hexdigest())
    with pytest.raises(FJ.FindingJudgmentChainError) as excinfo:
        FJ.load_ledger(store)
    assert _expect_code(excinfo) == "judgment_id_mismatch"


def test_forked_chain_is_refused() -> None:
    store = InMemoryStrictConditionalStore()
    original, correction = _two_step_chain(store)
    rival = _correction_record(original, correction["content"], original["judgment_id"], NIGHT3)
    _seed_batch(store, 3, [rival], NIGHT3, hashlib.sha256(_read_batch(store, 2)).hexdigest())
    with pytest.raises(FJ.FindingJudgmentChainError) as excinfo:
        FJ.load_ledger(store)
    assert _expect_code(excinfo) == "fork"


def test_dangling_supersedes_is_refused() -> None:
    store = InMemoryStrictConditionalStore()
    original, _ = _two_step_chain(store)
    dangling = _correction_record(
        original, original["content"], "fjudgment_missing0000000000000000000000000", NIGHT3
    )
    _seed_batch(store, 3, [dangling], NIGHT3, hashlib.sha256(_read_batch(store, 2)).hexdigest())
    with pytest.raises(FJ.FindingJudgmentChainError) as excinfo:
        FJ.load_ledger(store)
    assert _expect_code(excinfo) == "dangling_supersedes"


def test_missing_and_duplicate_originals_are_refused() -> None:
    store = InMemoryStrictConditionalStore()
    original, _ = _two_step_chain(store)
    twin = dict(original)
    twin["judgment_id"] = _judgment_id(original["subject_key"], original["content_sha256"], None)
    twin["recorded_at"] = utc_text(NIGHT3)
    _seed_batch(store, 3, [twin], NIGHT3, hashlib.sha256(_read_batch(store, 2)).hexdigest())
    with pytest.raises(FJ.FindingJudgmentChainError) as excinfo:
        FJ.load_ledger(store)
    assert _expect_code(excinfo) == "duplicate_original"

    # A chain whose original never existed: only a correction is seeded.
    orphaned = InMemoryStrictConditionalStore()
    subject = {
        "subject_key": stable_id("fjsubject", "kernel", "revenue_collapse", "0001234567", "2026-06-30"),
        "kind": "kernel",
        "entity_ref": "0001234567",
        "finding_ref": "find-rev-collapse-fixture-2026q2",
        "source_ready_at": None,
    }
    lonely = _correction_record(subject, _kernel_row(), "fjudgment_missing0000000000000000000000000", NIGHT2)
    _seed_batch(orphaned, 1, [lonely], NIGHT2, "")
    with pytest.raises(FJ.FindingJudgmentChainError) as excinfo:
        FJ.load_ledger(orphaned)
    assert _expect_code(excinfo) == "missing_original"


def test_duplicate_subject_within_one_call_is_refused() -> None:
    store = InMemoryStrictConditionalStore()
    rows = [_kernel_row(), _kernel_row(derived_values={"growth": "-0.55"})]
    with pytest.raises(FJ.FindingJudgmentError) as excinfo:
        _record_kernel(store, rows, NIGHT1)
    assert _expect_code(excinfo) == "duplicate_subject"
    assert FJ.load_ledger(store).batch_keys == ()


# ---------------------------------------------------------------------------
# 6. Clock discipline: caller-supplied clocks only
# ---------------------------------------------------------------------------


def test_missing_or_naive_clocks_are_refused() -> None:
    store = InMemoryStrictConditionalStore()
    rows = [_kernel_row()]
    for bad in (None, "2026-10-10T06:00:00", datetime(2026, 10, 10, 6, 0), 42):
        with pytest.raises(FJ.FindingJudgmentError) as excinfo:
            FJ.record_judgments(store, kind="kernel", rows=rows, recorded_at=bad)
        assert _expect_code(excinfo) == "recorded_at_required"
    for bad in (None, "2026-10-12 06:00:00", datetime(2026, 10, 12, 6, 0)):
        with pytest.raises(FJ.FindingJudgmentError) as excinfo:
            FJ.replay_then_known(store, recorded_cutoff=bad)
        assert _expect_code(excinfo) == "cutoff_required"
    with pytest.raises(FJ.FindingJudgmentError) as excinfo:
        FJ.record_judgments(
            store, kind="kernel", rows=rows, recorded_at=NIGHT1,
            source_generated_at=datetime(2026, 10, 9, 6, 0),
        )
    assert _expect_code(excinfo) == "source_generated_at_required"
    naive_state = _workbench_state(
        {"FXA": _company(1111111, [_wfinding("rev-collapse:q2-2026", "revenue_collapse")])},
        "2026-10-10T06:00:00",
    )
    with pytest.raises(FJ.FindingJudgmentError) as excinfo:
        FJ.workbench_rows_from_state(naive_state)
    assert _expect_code(excinfo) == "recorded_at_required"
    with pytest.raises(FJ.FindingJudgmentError) as excinfo:
        FJ.workbench_rows_from_state({})
    assert _expect_code(excinfo) == "recorded_at_required"


def test_stale_rerun_clock_is_refused_and_the_ledger_still_loads() -> None:
    store = InMemoryStrictConditionalStore()
    state_night1 = _workbench_state(
        {
            "FXA": _company(1111111, [_wfinding("rev-collapse:q2-2026", "revenue_collapse")]),
            "FXB": _company(2222222, [_wfinding("gm-compress:q2-2026", "margin_compression")]),
        },
        utc_text(NIGHT1),
    )
    rows1, scope1, generated1 = FJ.workbench_rows_from_state(state_night1)
    FJ.record_judgments(
        store, kind="workbench", rows=rows1, recorded_at=NIGHT1,
        source_generated_at=generated1, scope_entities=scope1,
    )
    # Night 2 corrects FXA's finding and withdraws FXB's.
    state_night2 = _workbench_state(
        {
            "FXA": _company(1111111, [_wfinding("rev-collapse:q2-2026", "revenue_collapse", priority="critical")]),
            "FXB": _company(2222222, []),
        },
        utc_text(NIGHT2),
    )
    rows2, scope2, generated2 = FJ.workbench_rows_from_state(state_night2)
    night2 = FJ.record_judgments(
        store, kind="workbench", rows=rows2, recorded_at=NIGHT2,
        source_generated_at=generated2, scope_entities=scope2,
    )
    assert night2["withdrawals"] == 1 and night2["corrections"] == 1
    writes = len(store.conditional_writes)

    # A stale night-1-clock rerun with a different (FXA-only, rowless) scope
    # must be refused by the ledger-wide clock and never wedge the ledger
    # behind a backdated withdrawal.
    state_stale = _workbench_state({"FXA": _company(1111111, [])}, utc_text(NIGHT1))
    rows_stale, scope_stale, _ = FJ.workbench_rows_from_state(state_stale)
    assert rows_stale == []
    with pytest.raises(FJ.FindingJudgmentError) as excinfo:
        FJ.record_judgments(
            store, kind="workbench", rows=rows_stale, recorded_at=NIGHT1,
            source_generated_at=utc_text(NIGHT1), scope_entities=scope_stale,
        )
    assert _expect_code(excinfo) == "clock_regression"
    assert len(store.conditional_writes) == writes
    view = FJ.load_ledger(store)
    assert view.head_sequence == 2
    assert len(view.batch_keys) == 2


def test_backdated_run_for_a_brand_new_subject_is_refused() -> None:
    store = InMemoryStrictConditionalStore()
    _record_kernel(store, [_kernel_row()], NIGHT2)
    writes = len(store.conditional_writes)
    fresh = _kernel_row(entity_cik="0000999999")
    with pytest.raises(FJ.FindingJudgmentError) as excinfo:
        _record_kernel(store, [fresh], NIGHT1)
    assert _expect_code(excinfo) == "clock_regression"
    assert len(store.conditional_writes) == writes
    view = FJ.load_ledger(store)
    assert view.head_sequence == 1
    assert FJ.history(store, FJ.kernel_row(fresh)["subject_key"]) == ()


def test_equal_clock_with_changed_content_is_refused() -> None:
    store = InMemoryStrictConditionalStore()
    _record_kernel(store, [_kernel_row()], NIGHT1)
    writes = len(store.conditional_writes)
    with pytest.raises(FJ.FindingJudgmentError) as excinfo:
        _record_kernel(store, [_kernel_row(derived_values={"growth": "-0.55"})], NIGHT1)
    assert _expect_code(excinfo) == "clock_regression"
    assert len(store.conditional_writes) == writes


def test_equal_clock_with_identical_inputs_is_a_noop() -> None:
    store = InMemoryStrictConditionalStore()
    _record_kernel(store, [_kernel_row()], NIGHT1)
    writes = len(store.conditional_writes)
    again = _record_kernel(store, [_kernel_row()], NIGHT1)
    assert again["batch_key"] is None and again["sequence"] is None
    assert again["unchanged"] == 1
    assert again["originals"] == again["corrections"] == again["withdrawals"] == 0
    assert len(store.conditional_writes) == writes
    assert FJ.load_ledger(store).head_sequence == 1


# ---------------------------------------------------------------------------
# 7. Listing independence and strict reads
# ---------------------------------------------------------------------------


def test_recording_and_loading_never_call_list_prefix() -> None:
    for store in (_NoListingStore(raising=True), _NoListingStore(raising=False)):
        _record_kernel(store, [_kernel_row()], NIGHT1)
        _record_kernel(store, [_kernel_row(derived_values={"growth": "-0.55"})], NIGHT2)
        view = FJ.load_ledger(store)
        assert view.head_sequence == 2
        assert view.batch_keys == (_batch_key(1), _batch_key(2))
        assert store.list_calls == 0


def test_head_read_failure_refuses_with_head_read_failed() -> None:
    store = _HeadReadExplodingStore()
    store.explode = True
    with pytest.raises(FJ.FindingJudgmentChainError) as excinfo:
        _record_kernel(store, [_kernel_row()], NIGHT1)
    assert _expect_code(excinfo) == "head_read_failed"
    assert store.conditional_writes == []


def test_batch_read_failure_refuses_with_batch_read_failed() -> None:
    store = _BatchReadExplodingStore()
    _record_kernel(store, [_kernel_row()], NIGHT1)
    writes = len(store.conditional_writes)
    store.explode = True
    with pytest.raises(FJ.FindingJudgmentChainError) as excinfo:
        _record_kernel(store, [_kernel_row(derived_values={"growth": "-0.55"})], NIGHT2)
    assert _expect_code(excinfo) == "batch_read_failed"
    assert len(store.conditional_writes) == writes


# ---------------------------------------------------------------------------
# 8. Key/body binding: the hash chain and canonical bytes
# ---------------------------------------------------------------------------


def test_body_sequence_disagreeing_with_its_key_is_refused() -> None:
    store = InMemoryStrictConditionalStore()
    _record_kernel(store, [_kernel_row()], NIGHT1)
    _record_kernel(store, [_kernel_row(derived_values={"growth": "-0.55"})], NIGHT2)
    body = json.loads(_read_batch(store, 1).decode("utf-8"))
    body["sequence"] = 7
    store.raw_put(_batch_key(1), _canonical(body))
    with pytest.raises(FJ.FindingJudgmentChainError) as excinfo:
        FJ.load_ledger(store)
    assert _expect_code(excinfo) == "batch_key_mismatch"


def test_noncanonical_batch_bytes_are_refused() -> None:
    store = InMemoryStrictConditionalStore()
    _record_kernel(store, [_kernel_row()], NIGHT1)
    body = json.loads(_read_batch(store, 1).decode("utf-8"))
    assert json.loads(json.dumps(body)) == body  # equal JSON, different bytes
    store.raw_put(_batch_key(1), json.dumps(body, indent=1).encode("utf-8"))
    with pytest.raises(FJ.FindingJudgmentChainError) as excinfo:
        FJ.load_ledger(store)
    assert _expect_code(excinfo) == "batch_noncanonical"


def test_edited_batch_records_break_the_hash_chain() -> None:
    store = InMemoryStrictConditionalStore()
    _record_kernel(store, [_kernel_row()], NIGHT1)
    _record_kernel(store, [_kernel_row(derived_values={"growth": "-0.55"})], NIGHT2)
    body = json.loads(_read_batch(store, 1).decode("utf-8"))
    body["records"] = []
    store.raw_put(_batch_key(1), _canonical(body))
    with pytest.raises(FJ.FindingJudgmentChainError) as excinfo:
        FJ.load_ledger(store)
    assert _expect_code(excinfo) == "chain_hash_mismatch"


def test_head_tip_pointing_at_different_bytes_is_refused() -> None:
    store = InMemoryStrictConditionalStore()
    _record_kernel(store, [_kernel_row()], NIGHT1)
    _record_kernel(store, [_kernel_row(derived_values={"growth": "-0.55"})], NIGHT2)
    _seed_head(store, 2, "0" * 64)
    with pytest.raises(FJ.FindingJudgmentChainError) as excinfo:
        FJ.load_ledger(store)
    assert _expect_code(excinfo) == "chain_hash_mismatch"


def test_equal_or_decreasing_batch_clocks_are_refused() -> None:
    for clock in (NIGHT1, datetime(2026, 10, 9, 6, 0, tzinfo=timezone.utc)):
        store = InMemoryStrictConditionalStore()
        _record_kernel(store, [_kernel_row()], NIGHT1)
        _record_kernel(store, [_kernel_row(derived_values={"growth": "-0.55"})], NIGHT2)
        body = json.loads(_read_batch(store, 2).decode("utf-8"))
        body["recorded_at"] = utc_text(clock)
        for record in body["records"]:
            record["recorded_at"] = utc_text(clock)
        payload = _canonical(body)
        store.raw_put(_batch_key(2), payload)
        _seed_head(store, 2, hashlib.sha256(payload).hexdigest())
        with pytest.raises(FJ.FindingJudgmentChainError) as excinfo:
            FJ.load_ledger(store)
        assert _expect_code(excinfo) == "batch_clock_regression"


def test_naive_record_clock_raises_record_clock_not_typeerror() -> None:
    store = InMemoryStrictConditionalStore()
    _record_kernel(store, [_kernel_row()], NIGHT1)
    body = json.loads(_read_batch(store, 1).decode("utf-8"))
    body["records"][0]["recorded_at"] = "2026-10-10T06:00:00"  # naive text
    payload = _canonical(body)
    store.raw_put(_batch_key(1), payload)
    _seed_head(store, 1, hashlib.sha256(payload).hexdigest())
    with pytest.raises(FJ.FindingJudgmentError) as excinfo:
        FJ.load_ledger(store)
    assert _expect_code(excinfo) == "record_clock"


# ---------------------------------------------------------------------------
# 9. Concurrency: create-only batches and CAS HEAD
# ---------------------------------------------------------------------------


def test_concurrent_writer_with_different_content_loses_the_sequence() -> None:
    backend = InMemoryStrictConditionalStore()
    rows_a = [_kernel_row()]
    rows_b = [_kernel_row(entity_cik="0000999999")]
    writer_a = _LateWriterStore(backend)
    report_a = _record_kernel(writer_a, rows_a, NIGHT1)
    assert report_a["sequence"] == 1
    writes = len(backend.conditional_writes)

    writer_b = _LateWriterStore(backend)  # loads the same (empty) HEAD as A did
    with pytest.raises(FJ.FindingJudgmentError) as excinfo:
        _record_kernel(writer_b, rows_b, NIGHT1)
    assert _expect_code(excinfo) == "head_conflict"
    # B attempted only its batch create and wrote nothing else.
    assert len(backend.conditional_writes) == writes + 1
    assert backend.conditional_writes[-1] == (_batch_key(1), None)
    view = FJ.load_ledger(backend)
    assert view.head_sequence == 1
    assert FJ.history(backend, FJ.kernel_row(rows_b[0])["subject_key"]) == ()


def test_concurrent_identical_writer_completes_idempotently() -> None:
    backend = InMemoryStrictConditionalStore()
    rows = [_kernel_row()]
    report_a = _record_kernel(_LateWriterStore(backend), rows, NIGHT1)
    assert report_a["sequence"] == 1

    writer_b = _LateWriterStore(backend)
    report_b = _record_kernel(writer_b, rows, NIGHT1)
    assert report_b["sequence"] == 1
    assert report_b["batch_key"] == report_a["batch_key"]
    view = FJ.load_ledger(backend)
    assert view.head_sequence == 1
    assert len(FJ.history(backend, FJ.kernel_row(rows[0])["subject_key"])) == 1


# ---------------------------------------------------------------------------
# 10. Effect-unknown: one write attempt, no retry
# ---------------------------------------------------------------------------


def test_batch_write_with_unreadable_readback_is_effect_unknown_and_never_retried() -> None:
    store = _ExplodingBatchStore()
    store.explode_put = True
    with pytest.raises(FJ.FindingJudgmentEffectUnknownError) as excinfo:
        _record_kernel(store, [_kernel_row()], NIGHT1)
    assert _expect_code(excinfo) == "effect_unknown"
    assert store.conditional_calls == 1
    assert store.unconditional_writes == []
    assert FJ.load_ledger(store).head_sequence == 0


def test_batch_raise_after_commit_completes_via_read_back() -> None:
    store = InMemoryStrictConditionalStore()
    store.raise_on_conditional_after_commit = True
    report = _record_kernel(store, [_kernel_row()], NIGHT1)
    assert report["sequence"] == 1
    assert FJ.load_ledger(store).head_sequence == 1


def test_batch_raise_after_commit_with_drop_is_effect_unknown() -> None:
    store = InMemoryStrictConditionalStore()
    store.raise_on_conditional_after_commit = True
    store.drop_after_commit = True
    with pytest.raises(FJ.FindingJudgmentEffectUnknownError) as excinfo:
        _record_kernel(store, [_kernel_row()], NIGHT1)
    assert _expect_code(excinfo) == "effect_unknown"
    assert len(store.conditional_writes) == 1  # nothing else was written
    assert FJ.load_ledger(store).head_sequence == 0

    # The next run (later clock) writes a correct batch at the same sequence.
    report = _record_kernel(store, [_kernel_row()], NIGHT2)
    assert report["sequence"] == 1 and report["batch_key"] == _batch_key(1)
    view = FJ.load_ledger(store)
    assert view.head_sequence == 1
    assert len(FJ.history(store, FJ.kernel_row(_kernel_row())["subject_key"])) == 1


def test_head_cas_raise_after_commit_reconciles_to_success() -> None:
    store = _HeadCasExplodingStore()
    store.explode_after_commit = True
    report = _record_kernel(store, [_kernel_row()], NIGHT1)
    assert report["sequence"] == 1
    assert FJ.load_ledger(store).head_sequence == 1


def test_head_cas_raise_before_commit_is_effect_unknown_then_rolls_forward() -> None:
    store = _HeadCasExplodingStore()
    store.explode_before_commit = True
    with pytest.raises(FJ.FindingJudgmentEffectUnknownError) as excinfo:
        _record_kernel(store, [_kernel_row()], NIGHT1)
    assert _expect_code(excinfo) == "effect_unknown"
    batch1_bytes = _read_batch(store, 1)
    assert batch1_bytes is not None  # the batch exists; HEAD never advanced
    assert FJ.load_ledger(store).head_sequence == 0
    writes = list(store.conditional_writes)

    store.explode_before_commit = False
    report = _record_kernel(store, [_kernel_row(derived_values={"growth": "-0.55"})], NIGHT2)
    assert report["sequence"] == 2
    view = FJ.load_ledger(store)
    assert view.head_sequence == 2
    # Batch 1 was rolled forward, never rewritten, then batch 2 was appended.
    assert _read_batch(store, 1) == batch1_bytes
    run2_writes = [key for key, _ in store.conditional_writes[len(writes):]]
    assert run2_writes == [HEAD_KEY, _batch_key(2), HEAD_KEY]


# ---------------------------------------------------------------------------
# 11. Roll-forward refusals
# ---------------------------------------------------------------------------


def test_orphan_with_wrong_predecessor_is_refused() -> None:
    store = InMemoryStrictConditionalStore()
    _record_kernel(store, [_kernel_row()], NIGHT1)
    writes = list(store.conditional_writes)
    _seed_orphan(store, 2, [], NIGHT2, "0" * 64)  # wrong predecessor, HEAD stays at 1
    with pytest.raises(FJ.FindingJudgmentChainError) as excinfo:
        _record_kernel(store, [_kernel_row(derived_values={"growth": "-0.55"})], NIGHT3)
    assert _expect_code(excinfo) == "orphan_batch_invalid"
    assert store.conditional_writes == writes  # nothing was written
    assert FJ.load_ledger(store).head_sequence == 1  # the orphan stays invisible


def test_orphan_chain_is_refused() -> None:
    store = InMemoryStrictConditionalStore()
    _record_kernel(store, [_kernel_row()], NIGHT1)
    sha1 = hashlib.sha256(_read_batch(store, 1)).hexdigest()
    _seed_orphan(store, 2, [], NIGHT2, sha1)
    sha2 = hashlib.sha256(_read_batch(store, 2)).hexdigest()
    _seed_orphan(store, 3, [], NIGHT3, sha2)
    writes = list(store.conditional_writes)

    with pytest.raises(FJ.FindingJudgmentChainError) as excinfo:
        _record_kernel(store, [_kernel_row(derived_values={"growth": "-0.55"})], NIGHT4)
    assert _expect_code(excinfo) == "orphan_chain"
    # Only the single permitted roll-forward HEAD advance happened.
    assert [key for key, _ in store.conditional_writes[len(writes):]] == [HEAD_KEY]
    view = FJ.load_ledger(store)
    assert view.head_sequence == 2
    assert view.batch_keys == (_batch_key(1), _batch_key(2))


# ---------------------------------------------------------------------------
# 12. Write-side limits
# ---------------------------------------------------------------------------


def test_write_side_batch_limit_is_refused(monkeypatch) -> None:
    store = InMemoryStrictConditionalStore()
    _record_kernel(store, [_kernel_row()], NIGHT1)
    monkeypatch.setattr(FJ, "HARD_MAX_BATCHES", 1)
    writes = len(store.conditional_writes)
    with pytest.raises(FJ.FindingJudgmentError) as excinfo:
        _record_kernel(store, [_kernel_row(derived_values={"growth": "-0.55"})], NIGHT2)
    assert _expect_code(excinfo) == "batch_limit"
    assert len(store.conditional_writes) == writes


def test_oversize_payload_is_refused_before_any_write(monkeypatch) -> None:
    store = InMemoryStrictConditionalStore()
    monkeypatch.setattr(FJ, "HARD_MAX_BATCH_BYTES", 64)
    with pytest.raises(FJ.FindingJudgmentError) as excinfo:
        _record_kernel(store, [_kernel_row()], NIGHT1)
    assert _expect_code(excinfo) == "batch_oversize"
    assert store.conditional_writes == []


# ---------------------------------------------------------------------------
# 13. Kernel adapter contracts
# ---------------------------------------------------------------------------


def test_kernel_row_missing_required_key_is_refused() -> None:
    for key in ("finding_id", "detector_id", "detector_version", "entity_cik", "state", "period_ends"):
        row = _kernel_row()
        del row[key]
        with pytest.raises(FJ.FindingJudgmentError) as excinfo:
            FJ.kernel_row(row)
        assert _expect_code(excinfo) == "kernel_row_required"
        with pytest.raises(FJ.FindingJudgmentError) as excinfo:
            _record_kernel(InMemoryStrictConditionalStore(), [row], NIGHT1)
        assert _expect_code(excinfo) == "kernel_row_required"


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
# 14. Workbench adapter identity
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
    rows, scope_entities, generated_at = FJ.workbench_rows_from_state(state)
    assert len(rows) == 3
    assert scope_entities == {"0001111111", "symbol:FXA", "symbol:FXNO"}
    assert generated_at == NIGHT1
    by_ref = {row["finding_ref"]: row for row in rows}
    assert set(by_ref) == {"rev-collapse:q2-2026", "gm-compress:q2-2026", "accrual-spike:q1-2026"}
    assert by_ref["rev-collapse:q2-2026"]["subject_key"] == stable_id(
        "fjsubject", "workbench", "0001111111", "rev-collapse:q2-2026"
    )
    # A null CIK falls back to the normalized symbol identity.
    assert by_ref["accrual-spike:q1-2026"]["subject_key"] == stable_id(
        "fjsubject", "workbench", "symbol:FXNO", "accrual-spike:q1-2026"
    )
    assert by_ref["accrual-spike:q1-2026"]["entity_ref"] == "symbol:FXNO"
    assert by_ref["rev-collapse:q2-2026"]["content"] == finding_a1
    assert by_ref["rev-collapse:q2-2026"]["source_ready_at"] is None
    for row in rows:
        assert row["content_sha256"] == hashlib.sha256(_canonical(row["content"])).hexdigest()


def test_cik_normalization_pads_int_and_digit_string() -> None:
    state = _workbench_state(
        {
            "fxa": _company(320193, [_wfinding("rev-collapse:q2-2026", "revenue_collapse")]),
            " FXB ": _company("320193", [_wfinding("gm-compress:q2-2026", "margin_compression")]),
        },
        utc_text(NIGHT1),
    )
    rows, scope_entities, _ = FJ.workbench_rows_from_state(state)
    by_ref = {row["finding_ref"]: row for row in rows}
    assert by_ref["rev-collapse:q2-2026"]["entity_ref"] == "0000320193"
    assert by_ref["rev-collapse:q2-2026"]["subject_key"] == stable_id(
        "fjsubject", "workbench", "0000320193", "rev-collapse:q2-2026"
    )
    assert by_ref["gm-compress:q2-2026"]["entity_ref"] == "0000320193"
    assert scope_entities == {"0000320193", "symbol:FXA", "symbol:FXB"}


def test_symbol_subjects_are_withdrawn_when_the_cik_appears() -> None:
    store = InMemoryStrictConditionalStore()
    state_night1 = _workbench_state(
        {"FXA": _company(None, [_wfinding("rev-collapse:q2-2026", "revenue_collapse")])},
        utc_text(NIGHT1),
    )
    rows1, scope1, generated1 = FJ.workbench_rows_from_state(state_night1)
    report1 = FJ.record_judgments(
        store, kind="workbench", rows=rows1, recorded_at=NIGHT1,
        source_generated_at=generated1, scope_entities=scope1,
    )
    assert report1["originals"] == 1

    state_night2 = _workbench_state(
        {"FXA": _company(320193, [_wfinding("rev-collapse:q2-2026", "revenue_collapse")])},
        utc_text(NIGHT2),
    )
    rows2, scope2, generated2 = FJ.workbench_rows_from_state(state_night2)
    report2 = FJ.record_judgments(
        store, kind="workbench", rows=rows2, recorded_at=NIGHT2,
        source_generated_at=generated2, scope_entities=scope2,
    )
    assert report2["withdrawals"] == 1
    assert report2["originals"] == 1

    symbol_subject = stable_id("fjsubject", "workbench", "symbol:FXA", "rev-collapse:q2-2026")
    chain = FJ.history(store, symbol_subject)
    assert [record["status"] for record in chain] == ["present", "withdrawn"]
    cik_subject = stable_id("fjsubject", "workbench", "0000320193", "rev-collapse:q2-2026")
    cik_chain = FJ.history(store, cik_subject)
    assert [record["status"] for record in cik_chain] == ["present"]


def test_malformed_cik_or_symbol_is_refused() -> None:
    for bad_cik in ("12-34", "abc", "", 10**10, -5, 1.5, True):
        state = _workbench_state({"FXA": _company(bad_cik, [])}, utc_text(NIGHT1))
        with pytest.raises(FJ.FindingJudgmentError) as excinfo:
            FJ.workbench_rows_from_state(state)
        assert _expect_code(excinfo) == "state_shape"
    blank_symbol_state = _workbench_state({"  ": _company(1111111, [])}, utc_text(NIGHT1))
    with pytest.raises(FJ.FindingJudgmentError) as excinfo:
        FJ.workbench_rows_from_state(blank_symbol_state)
    assert _expect_code(excinfo) == "state_shape"


# ---------------------------------------------------------------------------
# 15. Reappearance and source clocks
# ---------------------------------------------------------------------------


def test_reappearance_after_withdrawal_records_status_only() -> None:
    store = InMemoryStrictConditionalStore()
    content = _kernel_row()
    subject = FJ.kernel_row(content)
    _record_kernel(store, [content], NIGHT1)
    withdrawn = FJ.record_judgments(
        store, kind="kernel", rows=[], recorded_at=NIGHT2, scope_entities={subject["entity_ref"]}
    )
    assert withdrawn["withdrawals"] == 1
    reapplied = _record_kernel(store, [content], NIGHT3)
    assert reapplied["corrections"] == 1
    chain = FJ.history(store, subject["subject_key"])
    assert [record["status"] for record in chain] == ["present", "withdrawn", "present"]
    assert chain[2]["change_reasons"] == ["status"]


def test_source_after_recorded_is_refused() -> None:
    store = InMemoryStrictConditionalStore()
    with pytest.raises(FJ.FindingJudgmentError) as excinfo:
        FJ.record_judgments(
            store, kind="kernel", rows=[_kernel_row()], recorded_at=NIGHT1, source_generated_at=NIGHT2
        )
    assert _expect_code(excinfo) == "recorded_before_source"
    assert store.conditional_writes == []


def test_records_carry_source_generated_at() -> None:
    store = InMemoryStrictConditionalStore()
    source = datetime(2026, 10, 9, 18, 0, tzinfo=timezone.utc)
    report = FJ.record_judgments(
        store, kind="kernel", rows=[_kernel_row()], recorded_at=NIGHT1, source_generated_at=source
    )
    assert report["source_generated_at"] == utc_text(source)
    assert _all_records(store)[0]["source_generated_at"] == utc_text(source)
    replayed = FJ.replay_then_known(store, recorded_cutoff=NIGHT2)
    assert replayed["subjects"][0]["visible"]["source_generated_at"] == utc_text(source)


# ---------------------------------------------------------------------------
# 16. Static guards: no wall clock, no listing, no unconditional put, no consumers
# ---------------------------------------------------------------------------


_WALL_CLOCK_ATTRS = {"now", "utcnow", "today", "time", "time_ns", "monotonic"}


def test_module_and_cli_avoid_wall_clocks_listings_and_unconditional_puts() -> None:
    hits = []
    for path in (MODULE_PATH, CLI_PATH):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "list_prefix":
                hits.append((path.name, node.lineno, "list_prefix"))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in _WALL_CLOCK_ATTRS:
                    hits.append((path.name, node.lineno, node.func.attr))
                if node.func.attr == "put_bytes":
                    hits.append((path.name, node.lineno, "put_bytes"))
    assert not hits, f"forbidden store/clock operations: {hits}"


_IMPORT_TARGET = "engine.fundamental_forensics.finding_judgments"


def _import_offenders(tree):
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == _IMPORT_TARGET or alias.name.startswith(_IMPORT_TARGET + "."):
                    hits.append(node.lineno)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                if node.module == _IMPORT_TARGET or node.module.startswith(_IMPORT_TARGET + "."):
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
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "import_module"
        ):
            for argument in node.args:
                if (
                    isinstance(argument, ast.Constant)
                    and isinstance(argument.value, str)
                    and "finding_judgments" in argument.value
                ):
                    hits.append(node.lineno)
    return hits


def test_no_consumer_module_imports_finding_judgments() -> None:
    offenders: list[tuple[str, list[int]]] = []
    scanned = 0
    for base in ("engine", "app"):
        for path in sorted((ROOT / base).rglob("*.py")):
            scanned += 1
            rel = path.relative_to(ROOT).as_posix()
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            hits = _import_offenders(tree)
            if hits:
                offenders.append((rel, hits))
    assert scanned > 500, "the source walk unexpectedly missed the repository trees"
    assert not offenders, (
        "modules under engine/ and app/ import the judgment ledger; the only "
        f"allowed importers are the CLI and the test file: {offenders}"
    )


# ---------------------------------------------------------------------------
# 17. CLI against a temporary local store
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
        [
            sys.executable,
            str(CLI_PATH),
            "record-state",
            "--state",
            str(state_path),
            "--recorded-at",
            utc_text(NIGHT1),
            "--local-store",
            str(store_dir),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert recorded.returncode == 0, recorded.stderr
    report = json.loads(recorded.stdout)
    assert report["schema"] == FJ.JUDGMENT_BATCH_SCHEMA
    assert report["originals"] == 1
    assert report["sequence"] == 1
    assert report["batch_key"] == _batch_key(1)
    assert report["source_generated_at"] == utc_text(NIGHT1)

    replayed = subprocess.run(
        [
            sys.executable,
            str(CLI_PATH),
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
            str(CLI_PATH),
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
            str(CLI_PATH),
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


def test_cli_effect_unknown_exits_three(monkeypatch, capsys, tmp_path) -> None:
    cli = _load_cli()
    store = InMemoryStrictConditionalStore()
    store.raise_on_conditional_after_commit = True
    store.drop_after_commit = True
    monkeypatch.setattr(cli, "build_production_dataset_store", lambda root: store)
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
    code = cli.main(
        [
            "record-state",
            "--state",
            str(state_path),
            "--recorded-at",
            utc_text(NIGHT1),
            "--local-store",
            str(tmp_path / "store"),
        ]
    )
    assert code == 3
    document = json.loads(capsys.readouterr().out)
    assert document["ok"] is False
    assert document["error"]["code"] == "effect_unknown"
    assert document["error"]["type"] == "FindingJudgmentEffectUnknownError"


def test_cli_state_file_failures_exit_two(monkeypatch, capsys, tmp_path) -> None:
    cli = _load_cli()
    monkeypatch.setattr(cli, "build_production_dataset_store", lambda root: InMemoryStrictConditionalStore())
    cases = []
    missing = tmp_path / "missing.json"
    cases.append((missing, None))
    malformed = tmp_path / "malformed.json"
    malformed.write_text("not-json{", encoding="utf-8")
    cases.append((malformed, None))
    corrupt = tmp_path / "corrupt-state.json"
    corrupt.write_bytes(b"\x1f\x8b\x00garbage-not-really-gzip")
    cases.append((corrupt, None))
    for path, _ in cases:
        code = cli.main(
            [
                "record-state",
                "--state",
                str(path),
                "--recorded-at",
                utc_text(NIGHT1),
                "--local-store",
                str(tmp_path / "store"),
            ]
        )
        assert code == 2
        document = json.loads(capsys.readouterr().out)
        assert document["ok"] is False
        assert document["error"]["code"] == "unexpected_error"


def test_cli_record_state_requires_recorded_at(capsys, tmp_path) -> None:
    cli = _load_cli()
    state_path = tmp_path / "state.json"
    state_path.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["record-state", "--state", str(state_path), "--local-store", str(tmp_path / "store")])
    assert excinfo.value.code == 2  # argparse's own usage error
    assert "usage" in capsys.readouterr().err.lower()


def test_cli_record_kernel_accepts_source_generated_at(monkeypatch, capsys, tmp_path) -> None:
    cli = _load_cli()
    store = InMemoryStrictConditionalStore()
    monkeypatch.setattr(cli, "build_production_dataset_store", lambda root: store)
    findings_path = tmp_path / "findings.json"
    findings_path.write_text(json.dumps([_kernel_row()]), encoding="utf-8")
    source_text = utc_text(datetime(2026, 10, 9, 18, 0, tzinfo=timezone.utc))
    code = cli.main(
        [
            "record-kernel",
            "--findings",
            str(findings_path),
            "--recorded-at",
            utc_text(NIGHT1),
            "--source-generated-at",
            "2026-10-09T18:00:00Z",
            "--local-store",
            str(tmp_path / "store"),
        ]
    )
    assert code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["sequence"] == 1
    assert report["source_generated_at"] == source_text
    assert _all_records(store)[0]["source_generated_at"] == source_text
