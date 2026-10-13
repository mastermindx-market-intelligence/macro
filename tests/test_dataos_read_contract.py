"""Explicit CURRENT/RECONSTRUCT/REPLAY read modes (D00.D1) — ``lib/dataos/read_contract.py``.

The defect pinned here is the one-coalesced-switch read.  ``temporal.as_of_filter``
merges published_at over ingested_at and returns every row known by the cutoff, so
a single switch quietly promises all three D00.D1 guarantees while honestly
delivering none of them: a row the publisher released at 09:00 but the house only
ingested at 11:00 looks "known at 10:00" when it is not, the reader cannot ASK for
the ingested_at answer, revisions are never resolved per key, a dependency's
identity generation is never bound, and what the system actually emitted cannot be
replayed.  Every test below pins one frozen clause: an explicit mode, an explicit
clock, an explicit revision resolution, an explicit generation binding, retained
bytes for replay — and the view contract declared before any result is seen.

Pure synthetic fixtures: aware instants or offset ISO strings only, no ``data/``
files, no network, no wall clock.

Run: python3 -m pytest tests/test_dataos_read_contract.py tests/test_dataos_temporal.py -q
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import pytest

from lib.dataos.read_contract import (
    READ_CONTRACT_VERSION,
    CurrentEvidence,
    Dependency,
    GenerationRef,
    ReadContractError,
    ReadMode,
    ReadRefusal,
    ReadRequest,
    RefusalCode,
    RetainedOutput,
    ViewContract,
    current,
    eligible_rows,
    reconstruct,
    replay,
    resolve_revisions,
    select_generation,
)
from lib.dataos.temporal import (
    PointInTimeError,
    TemporalError,
    TemporalProfile,
    as_of_filter,
)

CODE_VERSION = "a1" * 20  # a 40-char lowercase git sha
CUTOFF = "2026-01-05T10:00:00+00:00"


class _Exploding:
    """Iterable whose iteration FAILS the test — proves a check fired first."""

    def __iter__(self):
        raise AssertionError("rows were iterated before the contract check fired")


def _contract(**over) -> ViewContract:
    fields = dict(
        purpose="unit-test view pinning the D00.D1 read modes",
        identity={"security_id": "SEC-1", "listing_id": "LST-1"},
        field_units={"px": "USD/share"},
        adjustment_reference={"basis": "raw"},
        coverage="synthetic rows local to this suite",
    )
    fields.update(over)
    return ViewContract(**fields)


def _reconstruct_request(clock: str, cutoff: str = CUTOFF) -> ReadRequest:
    return ReadRequest(ReadMode.RECONSTRUCT, _contract(), cutoff=cutoff, clock=clock)


def _revisable(rows) -> dict:
    return {
        "revisions": Dependency(
            name="revisions",
            profile=TemporalProfile.REVISABLE_RELEASE,
            rows=rows,
            key_fields=("series", "period_end"),
        )
    }


def _reconstruct(rows, *, clock, cutoff=CUTOFF) -> object:
    return reconstruct(
        _reconstruct_request(clock, cutoff),
        _revisable(rows),
        required=("revisions",),
        code_version=CODE_VERSION,
    )


# ── T01.01 / V08: one row, two truths, two clocks ────────────────────────────
V08_ROW = {
    "series": "CPIAUCSL",
    "period_end": "2025-12-31T00:00:00+00:00",
    "value": 100.0,
    "published_at": "2026-01-05T09:00:00Z",
    "ingested_at": "2026-01-05T11:00:00Z",
    "revision_seq": 1,
}


def test_t01_01_v08_published_before_but_ingested_after_is_clock_dependent() -> None:
    """The row is ELIGIBLE under clock=published_at and INELIGIBLE under
    clock=ingested_at at the same cutoff — the caller must choose."""
    under_published = eligible_rows(
        [V08_ROW], TemporalProfile.REVISABLE_RELEASE, cutoff=CUTOFF, clock="published_at"
    )
    assert [row["value"] for row in under_published] == [100.0]
    under_ingested = eligible_rows(
        [V08_ROW], TemporalProfile.REVISABLE_RELEASE, cutoff=CUTOFF, clock="ingested_at"
    )
    assert under_ingested == []


def test_t01_01_v08_the_evidence_names_which_knowledge_answered() -> None:
    published_view = _reconstruct([V08_ROW], clock="published_at")
    ingested_view = _reconstruct([V08_ROW], clock="ingested_at")
    assert published_view.evidence["knowledge"] == "publisher_availability"
    assert ingested_view.evidence["knowledge"] == "system_observation"
    assert published_view.evidence["knowledge"] != ingested_view.evidence["knowledge"]


def test_t01_01_the_coalescing_helper_cannot_express_the_ingested_answer() -> None:
    """``as_of_filter`` coalesces published_at first, so it includes the row at
    10:00 — exactly why the explicit clock contract exists above it."""
    seen = as_of_filter([V08_ROW], CUTOFF, TemporalProfile.REVISABLE_RELEASE)
    assert [row["value"] for row in seen] == [100.0]


# ── T01.02: the clock vocabulary is closed ───────────────────────────────────
@pytest.mark.parametrize("clock", ["period_end", "event_at", "effective_at", "computed_at"])
@pytest.mark.parametrize(
    "profile",
    [TemporalProfile.BARS, TemporalProfile.EVENT, TemporalProfile.REVISABLE_RELEASE],
)
def test_t01_02_interval_and_off_clock_columns_are_never_knowledge_clocks(
    profile, clock
) -> None:
    with pytest.raises(ReadRefusal) as exc:
        eligible_rows([], profile, cutoff=CUTOFF, clock=clock)
    assert exc.value.code is RefusalCode.CLOCK_NOT_DECLARED


@pytest.mark.parametrize("clock", ["mtime", "query_date", "build_clock"])
def test_t01_02_a_word_that_is_no_named_time_at_all_is_an_unknown_clock(clock) -> None:
    with pytest.raises(ReadRefusal) as from_rows:
        eligible_rows([], TemporalProfile.BARS, cutoff=CUTOFF, clock=clock)
    assert from_rows.value.code is RefusalCode.UNKNOWN_CLOCK
    with pytest.raises(ReadRefusal) as from_request:
        ReadRequest(ReadMode.RECONSTRUCT, _contract(), cutoff=CUTOFF, clock=clock)
    assert from_request.value.code is RefusalCode.UNKNOWN_CLOCK


def test_t01_02_a_row_without_the_knowledge_column_is_refused_under_both_real_clocks() -> None:
    row = {"period_end": "2025-12-31T00:00:00+00:00", "mtime": "2026-01-05T09:00:00+00:00"}
    for clock in ("published_at", "ingested_at"):
        with pytest.raises(ReadRefusal) as exc:
            eligible_rows([row], TemporalProfile.BARS, cutoff=CUTOFF, clock=clock)
        assert exc.value.code is RefusalCode.MISSING_CLOCK_VALUE


def test_t01_02_a_reconstruct_request_without_a_cutoff_raises_not_defaults_to_now() -> None:
    with pytest.raises(TemporalError):
        ReadRequest(ReadMode.RECONSTRUCT, _contract(), clock="published_at")


def test_t01_02_the_module_never_consults_a_wall_clock() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        .joinpath("lib", "dataos", "read_contract.py")
        .read_text(encoding="utf-8")
    )
    assert "datetime.now(" not in source
    assert "time.time(" not in source


# ── T01.03: revision resolution is per key, max revision_seq ─────────────────
REV1 = {
    "series": "CPIAUCSL",
    "period_end": "2025-12-31T00:00:00+00:00",
    "value": 100.0,
    "published_at": "2026-01-05T09:00:00+00:00",
    "ingested_at": "2026-01-05T09:30:00+00:00",
    "revision_seq": 1,
}
REV2 = {
    "series": "CPIAUCSL",
    "period_end": "2025-12-31T00:00:00+00:00",
    "value": 100.4,
    "published_at": "2026-01-05T12:00:00+00:00",
    "ingested_at": "2026-01-05T12:30:00+00:00",
    "revision_seq": 2,
}


def test_t01_03_by_13z_only_the_latest_revision_is_the_answer() -> None:
    result = _reconstruct([REV1, REV2], clock="published_at",
                          cutoff="2026-01-05T13:00:00+00:00")
    assert [row["revision_seq"] for row in result.values["revisions"]] == [2]
    coalesced = as_of_filter(
        [REV1, REV2], "2026-01-05T13:00:00+00:00", TemporalProfile.REVISABLE_RELEASE
    )
    assert [row["revision_seq"] for row in coalesced] == [1, 2]


def test_t01_03_at_10z_the_revision_had_not_happened_v09() -> None:
    result = _reconstruct([REV1, REV2], clock="published_at", cutoff=CUTOFF)
    assert [row["revision_seq"] for row in result.values["revisions"]] == [1]


def test_t01_03_a_row_without_a_revision_seq_is_refused_not_silently_kept() -> None:
    naked = {key: value for key, value in REV1.items() if key != "revision_seq"}
    with pytest.raises(ReadRefusal) as exc:
        resolve_revisions([naked], key_fields=("series", "period_end"))
    assert exc.value.code is RefusalCode.MISSING_REVISION_SEQ


def test_t01_03_a_bool_revision_seq_is_not_an_int() -> None:
    flagged = {**REV1, "revision_seq": True}
    with pytest.raises(ReadRefusal) as exc:
        resolve_revisions([flagged], key_fields=("series", "period_end"))
    assert exc.value.code is RefusalCode.MISSING_REVISION_SEQ


def test_t01_03_two_different_rows_claiming_one_revision_seq_is_ambiguous() -> None:
    twin = {**REV1, "value": 999.0}
    with pytest.raises(ReadRefusal) as exc:
        resolve_revisions([REV1, twin], key_fields=("series", "period_end"))
    assert exc.value.code is RefusalCode.AMBIGUOUS_REVISION


def test_t01_03_identical_duplicates_collapse_to_one() -> None:
    out = resolve_revisions([REV1, dict(REV1)], key_fields=("series", "period_end"))
    assert len(out) == 1


def test_t01_03_published_at_evidence_is_publisher_availability() -> None:
    result = _reconstruct([REV1], clock="published_at")
    assert result.evidence["knowledge"] == "publisher_availability"
    assert result.evidence["knowledge"] != "system_observation"
    assert result.evidence["clock"] == "published_at"
    assert result.evidence["revision_resolution"] == {
        "revisions": "max_revision_seq_per_key"
    }


def test_t01_03_the_reconstruction_label_is_never_replay() -> None:
    result = _reconstruct([REV1], clock="published_at")
    assert result.label == "reconstruction"
    assert result.label != "replay"
    assert result.mode is ReadMode.RECONSTRUCT


# ── T01.04: fail closed on unusable time and unreadable profiles ─────────────
@pytest.mark.parametrize(
    "bad_cutoff", [datetime(2026, 1, 5, 10, 0), "2026-01-05", ""]
)
def test_t01_04_a_cutoff_that_names_no_instant_raises_temporal_error(bad_cutoff) -> None:
    with pytest.raises(TemporalError):
        ReadRequest(ReadMode.RECONSTRUCT, _contract(), cutoff=bad_cutoff,
                    clock="published_at")


def test_t01_04_a_naive_row_clock_value_raises_temporal_error() -> None:
    naive = {**V08_ROW, "published_at": datetime(2026, 1, 5, 9, 0)}
    with pytest.raises(TemporalError):
        eligible_rows(
            [naive], TemporalProfile.REVISABLE_RELEASE, cutoff=CUTOFF, clock="published_at"
        )


def test_t01_04_a_derived_dependency_refuses_before_its_rows_are_iterated() -> None:
    derived = Dependency(name="derived", profile=TemporalProfile.DERIVED, rows=_Exploding())
    with pytest.raises(PointInTimeError):
        reconstruct(
            _reconstruct_request("published_at"),
            {"derived": derived},
            required=("derived",),
            code_version=CODE_VERSION,
        )


def test_t01_04_intelligence_declares_no_published_at_knowledge_clock() -> None:
    intel = Dependency(name="intel", profile=TemporalProfile.INTELLIGENCE, rows=_Exploding())
    with pytest.raises(ReadRefusal) as exc:
        reconstruct(
            _reconstruct_request("published_at"),
            {"intel": intel},
            required=("intel",),
            code_version=CODE_VERSION,
        )
    assert exc.value.code is RefusalCode.CLOCK_NOT_DECLARED


# ── V10: an eligible REFUSED revision shadows an earlier BOUND one ───────────
BOUND_ROW = {**REV1, "status": "BOUND"}
REFUSED_ROW = {**REV2, "status": "REFUSED"}


def test_v10_an_eligible_refused_revision_shadows_an_earlier_bound_one() -> None:
    out = resolve_revisions([BOUND_ROW, REFUSED_ROW], key_fields=("series", "period_end"))
    assert [row["status"] for row in out] == ["REFUSED"]


def test_v10_before_the_refusal_existed_the_bound_revision_was_the_answer() -> None:
    result = _reconstruct([BOUND_ROW, REFUSED_ROW], clock="published_at", cutoff=CUTOFF)
    assert [row["status"] for row in result.values["revisions"]] == ["BOUND"]
    out = resolve_revisions([BOUND_ROW], key_fields=("series", "period_end"))
    assert [row["status"] for row in out] == ["BOUND"]


# ── contract before results ──────────────────────────────────────────────────
def test_a_request_without_a_view_contract_is_refused_before_anything_runs() -> None:
    with pytest.raises(ReadRefusal) as exc:
        ReadRequest(ReadMode.RECONSTRUCT, None, cutoff=CUTOFF, clock="published_at")
    assert exc.value.code is RefusalCode.NO_VIEW_CONTRACT
    assert str(exc.value).startswith("NO_VIEW_CONTRACT")


def test_a_view_contract_without_security_id_is_malformed() -> None:
    with pytest.raises(ReadContractError):
        _contract(identity={"listing_id": "LST-1"})


def test_a_missing_required_dependency_is_refused_before_any_rows_are_iterated() -> None:
    present = Dependency(name="present", profile=TemporalProfile.BARS, rows=_Exploding())
    with pytest.raises(ReadRefusal) as exc:
        reconstruct(
            _reconstruct_request("published_at"),
            {"present": present},
            required=("present", "absent"),
            code_version=CODE_VERSION,
        )
    assert exc.value.code is RefusalCode.UNBOUND_DEPENDENCY


def test_current_with_bad_evidence_refuses_before_rows_are_iterated() -> None:
    request = ReadRequest(ReadMode.CURRENT, _contract())
    holdings = Dependency(name="holdings", profile=TemporalProfile.BARS, rows=_Exploding())
    with pytest.raises(ReadRefusal) as exc:
        current(request, {"holdings": holdings}, evidence=None)
    assert exc.value.code is RefusalCode.MISSING_CURRENT_EVIDENCE


# ── dependency generations ───────────────────────────────────────────────────
GEN1 = GenerationRef(generation_id="gen-1", published_at="2026-01-05T09:00:00+00:00",
                     ingested_at="2026-01-05T09:30:00+00:00")
GEN2 = GenerationRef(generation_id="gen-2", published_at="2026-01-05T11:00:00+00:00",
                     ingested_at="2026-01-05T13:00:00+00:00")
GEN_CUTOFF = "2026-01-05T12:00:00+00:00"


def test_generation_binding_follows_the_clock_not_the_coalesce() -> None:
    """gen-2 was published before the cutoff but ingested after it: chosen under
    published_at, NOT under ingested_at."""
    assert select_generation(
        (GEN1, GEN2), cutoff=GEN_CUTOFF, clock="published_at"
    ).generation_id == "gen-2"
    assert select_generation(
        (GEN1, GEN2), cutoff=GEN_CUTOFF, clock="ingested_at"
    ).generation_id == "gen-1"


def test_no_eligible_generation_leaves_the_dependency_unbound() -> None:
    with pytest.raises(ReadRefusal) as exc:
        select_generation((GEN1, GEN2), cutoff="2026-01-05T08:00:00+00:00",
                          clock="published_at")
    assert exc.value.code is RefusalCode.UNBOUND_DEPENDENCY


def test_a_pinned_older_generation_is_stale_while_a_newer_one_is_eligible() -> None:
    with pytest.raises(ReadRefusal) as exc:
        select_generation((GEN1, GEN2), cutoff=GEN_CUTOFF, clock="published_at",
                          pinned_generation_id="gen-1")
    assert exc.value.code is RefusalCode.STALE_GENERATION
    assert select_generation((GEN1, GEN2), cutoff=GEN_CUTOFF, clock="published_at",
                             pinned_generation_id="gen-2") is GEN2


def test_a_pinned_generation_with_no_generations_at_all_is_unbound() -> None:
    with pytest.raises(ReadRefusal) as exc:
        select_generation((), cutoff=GEN_CUTOFF, clock="published_at",
                          pinned_generation_id="gen-1")
    assert exc.value.code is RefusalCode.UNBOUND_DEPENDENCY


def test_a_clock_tie_between_different_generations_is_ambiguous() -> None:
    twin = GenerationRef(generation_id="gen-2b", published_at="2026-01-05T11:00:00+00:00",
                         ingested_at="2026-01-05T13:00:00+00:00")
    with pytest.raises(ReadRefusal) as exc:
        select_generation((GEN2, twin), cutoff=GEN_CUTOFF, clock="published_at")
    assert exc.value.code is RefusalCode.AMBIGUOUS_REVISION


def test_a_generation_without_the_chosen_clock_value_is_refused_not_fallback_bound() -> None:
    blind = GenerationRef(generation_id="gen-0")
    with pytest.raises(ReadRefusal) as exc:
        select_generation((blind, GEN1), cutoff=GEN_CUTOFF, clock="published_at")
    assert exc.value.code is RefusalCode.MISSING_CLOCK_VALUE


def test_reconstruct_binds_the_chosen_generation_ids_in_the_evidence() -> None:
    master = Dependency(name="master", profile=TemporalProfile.SNAPSHOT_SERIES,
                        rows=(), generations=(GEN1, GEN2))
    plain = Dependency(name="plain", profile=TemporalProfile.BARS, rows=())
    result = reconstruct(
        _reconstruct_request("published_at", GEN_CUTOFF),
        {"master": master, "plain": plain},
        required=("master",),
        code_version=CODE_VERSION,
    )
    assert result.evidence["dependency_generation_ids"]["master"] == "gen-2"
    assert result.evidence["dependency_generation_ids"]["plain"] is None
    assert result.evidence["revision_resolution"] == {"master": "none", "plain": "none"}


# ── REPLAY: retained bytes or a typed refusal ────────────────────────────────
PAYLOAD = b"exact emitted bytes \x00\x01"
PAYLOAD_SHA = hashlib.sha256(PAYLOAD).hexdigest()
RECEIPT = "c0ffee" + "0" * 58


def _retained(**over) -> RetainedOutput:
    fields = dict(output_id="out-1", payload=PAYLOAD, sha256=PAYLOAD_SHA,
                  publishing_receipt_sha256=RECEIPT)
    fields.update(over)
    return RetainedOutput(**fields)


def _replay(retained) -> object:
    request = ReadRequest(ReadMode.REPLAY, _contract(), output_id="out-1")
    return replay(request, retained)


def test_replay_serves_the_exact_retained_bytes_with_digest_and_receipt() -> None:
    result = _replay(_retained())
    assert result.label == "replay"
    assert result.payload == PAYLOAD
    assert result.values == {}
    assert result.evidence["output_id"] == "out-1"
    assert result.evidence["sha256"] == PAYLOAD_SHA
    assert result.evidence["publishing_receipt_sha256"] == RECEIPT
    assert hashlib.sha256(result.payload).hexdigest() == result.evidence["sha256"]


@pytest.mark.parametrize(
    "fields",
    [
        {"payload": None},
        {"output_id": "out-9"},
        {"publishing_receipt_sha256": None},
        {"publishing_receipt_sha256": "NOT-HEX"},
    ],
)
def test_replay_without_retained_proof_is_refused_not_regenerated(fields) -> None:
    with pytest.raises(ReadRefusal) as exc:
        _replay(_retained(**fields))
    assert exc.value.code is RefusalCode.NO_RETAINED_OUTPUT


def test_replay_of_nothing_at_all_is_refused() -> None:
    request = ReadRequest(ReadMode.REPLAY, _contract(), output_id="out-1")
    with pytest.raises(ReadRefusal) as exc:
        replay(request, None)
    assert exc.value.code is RefusalCode.NO_RETAINED_OUTPUT


def test_replay_refuses_tampered_bytes() -> None:
    with pytest.raises(ReadRefusal) as exc:
        _replay(_retained(payload=b"tampered"))
    assert exc.value.code is RefusalCode.RETAINED_DIGEST_MISMATCH


# ── CURRENT: binds its evidence, and nothing historical ──────────────────────
def _evidence(**over) -> CurrentEvidence:
    fields = dict(
        receipt_sha256s=("ab" * 32,),
        identity_generation_id="ident-gen-7",
        action_revision_set_id="revset-3",
        code_version=CODE_VERSION,
    )
    fields.update(over)
    return CurrentEvidence(**fields)


def test_current_binds_receipts_generation_revision_set_and_code_and_no_clock() -> None:
    request = ReadRequest(ReadMode.CURRENT, _contract())
    holdings = Dependency(name="holdings", profile=TemporalProfile.BARS,
                          rows=({"qty": 1}, {"qty": 2}))
    result = current(request, {"holdings": holdings}, evidence=_evidence())
    assert result.label == "current"
    assert result.mode is ReadMode.CURRENT
    assert result.evidence["receipt_sha256s"] == ("ab" * 32,)
    assert result.evidence["identity_generation_id"] == "ident-gen-7"
    assert result.evidence["action_revision_set_id"] == "revset-3"
    assert result.evidence["code_version"] == CODE_VERSION
    assert "cutoff" not in result.evidence
    assert "clock" not in result.evidence
    assert result.values["holdings"] == ({"qty": 1}, {"qty": 2})


@pytest.mark.parametrize(
    "fields",
    [
        {"receipt_sha256s": ()},
        {"receipt_sha256s": ("AB" * 32,)},
        {"identity_generation_id": ""},
        {"action_revision_set_id": "   "},
        {"code_version": "a1" * 19},
    ],
)
def test_current_evidence_that_binds_nothing_is_a_refusal(fields) -> None:
    with pytest.raises(ReadRefusal) as exc:
        _evidence(**fields)
    assert exc.value.code is RefusalCode.MISSING_CURRENT_EVIDENCE


# ── structural pins ──────────────────────────────────────────────────────────
def test_the_contract_version_is_pinned() -> None:
    assert READ_CONTRACT_VERSION == "mastermind.read_contract.v1"


def test_a_revisable_dependency_must_declare_its_key_fields() -> None:
    revisions = Dependency(name="revisions", profile=TemporalProfile.REVISABLE_RELEASE,
                           rows=[REV1], key_fields=())
    with pytest.raises(ReadContractError):
        reconstruct(
            _reconstruct_request("published_at"),
            {"revisions": revisions},
            required=("revisions",),
            code_version=CODE_VERSION,
        )


def test_reconstruction_binds_a_real_code_version() -> None:
    with pytest.raises(ReadContractError):
        reconstruct(
            _reconstruct_request("published_at"),
            {"plain": Dependency(name="plain", profile=TemporalProfile.BARS)},
            required=("plain",),
            code_version="not-a-sha",
        )


def test_revision_resolution_without_key_fields_is_malformed() -> None:
    with pytest.raises(ReadContractError):
        resolve_revisions([REV1], key_fields=())


def test_resolved_rows_come_back_sorted_by_key() -> None:
    zeta = {**REV1, "series": "ZZZ"}
    alpha = {**REV1, "series": "AAA"}
    out = resolve_revisions([zeta, alpha], key_fields=("series", "period_end"))
    assert [row["series"] for row in out] == ["AAA", "ZZZ"]


def test_result_evidence_and_values_reject_item_assignment() -> None:
    result = _reconstruct([REV1], clock="published_at")
    with pytest.raises(TypeError):
        result.evidence["cutoff"] = "2026-01-05T23:00:00+00:00"
    with pytest.raises(TypeError):
        result.values["revisions"] = ()
