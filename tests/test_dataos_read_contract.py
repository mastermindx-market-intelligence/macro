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
import itertools
from datetime import datetime, timezone
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
    selected_input_sha256s,
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


# ── R01 heal: order independence, canonical keys, generation-bound rows ──────
# The heal_fix tests each pin one R01 finding and MUST fail against the
# pre-heal contract; the heal_guard/heal_cutoff tests hold on both sides.
HEAL_CUTOFF = "2026-01-08T13:00:00+00:00"


def test_heal_fix_m1_max_revision_wins_in_every_supply_order() -> None:
    """M1: [A(k=K,seq1,v1), B(k=K,seq1,v2), C(k=K,seq2,v3)] answers [C] in
    EVERY supply order — the best sequence is found over ALL rows first."""
    a = {"k": "K", "revision_seq": 1, "v": "v1"}
    b = {"k": "K", "revision_seq": 1, "v": "v2"}
    c = {"k": "K", "revision_seq": 2, "v": "v3"}
    for order in itertools.permutations((a, b, c)):
        assert resolve_revisions(list(order), key_fields=("k",)) == [c]


def test_heal_guard_m1_distinct_rows_at_the_winning_seq_refuse_in_every_order() -> None:
    """Two DIFFERENT rows claiming one revision of a key stay ambiguous from
    either side (pre-existing law), and an identical duplicate of the winner
    collapses instead of widening the answer."""
    a = {"k": "K", "revision_seq": 1, "v": "v1"}
    b = {"k": "K", "revision_seq": 1, "v": "v2"}
    for order in itertools.permutations((a, b)):
        with pytest.raises(ReadRefusal) as exc:
            resolve_revisions(list(order), key_fields=("k",))
        assert exc.value.code is RefusalCode.AMBIGUOUS_REVISION
    c = {"k": "K", "revision_seq": 2, "v": "v3"}
    assert resolve_revisions([c, dict(c), a], key_fields=("k",)) == [c]


def test_heal_fix_m2_one_instant_spelled_two_ways_is_one_key() -> None:
    """M2: one instant spelled two ways is ONE key, so rev2 replaces rev1
    instead of joining it — through strings, and through datetime objects."""
    rev1 = {"security_id": "SEC", "period_end": "2026-01-05T00:00:00Z",
            "value": 100.0, "revision_seq": 1,
            "published_at": "2026-01-04T09:00:00+00:00",
            "ingested_at": "2026-01-04T09:30:00+00:00"}
    rev2 = {**rev1, "period_end": "2026-01-05T00:00:00+00:00",
            "value": 100.4, "revision_seq": 2}
    out = resolve_revisions([rev1, rev2], key_fields=("security_id", "period_end"))
    assert out == [rev2]
    dt_rev1 = {**rev1, "period_end": datetime(2026, 1, 5, 0, 0, tzinfo=timezone.utc)}
    dt_rev2 = {**rev1, "period_end": "2026-01-05T08:00:00+08:00",
               "value": 100.4, "revision_seq": 2}
    out = resolve_revisions([dt_rev1, dt_rev2],
                            key_fields=("security_id", "period_end"))
    assert out == [dt_rev2]


def test_heal_fix_m2_mixed_key_types_refuse_typed_not_typeerror() -> None:
    """M2: a key position that mixes kinds across rows refuses KEY_TYPE_MISMATCH
    in both supply orders — never a bare TypeError out of sorted() — through the
    revision path AND the unique-key path of a read."""
    for first, second in ((1, "x"), ("x", 1)):
        rows = [{"k": first, "revision_seq": 1}, {"k": second, "revision_seq": 2}]
        with pytest.raises(ReadRefusal) as exc:
            resolve_revisions(rows, key_fields=("k",))
        assert exc.value.code is RefusalCode.KEY_TYPE_MISMATCH
    identity_rows = (
        {"action_id": datetime(2026, 1, 5, tzinfo=timezone.utc), "symbol": "new",
         "published_at": "2026-01-03T00:00:00+00:00",
         "ingested_at": "2026-01-03T01:00:00+00:00"},
        {"action_id": "AAPL", "symbol": "old",
         "published_at": "2026-01-03T00:00:00+00:00",
         "ingested_at": "2026-01-03T01:00:00+00:00"},
    )
    with pytest.raises(ReadRefusal) as exc:
        reconstruct(
            _reconstruct_request("published_at"),
            {"identity": Dependency(name="identity",
                                    profile=TemporalProfile.SNAPSHOT_SERIES,
                                    rows=identity_rows, key_fields=("action_id",))},
            required=("identity",),
            code_version=CODE_VERSION,
        )
    assert exc.value.code is RefusalCode.KEY_TYPE_MISMATCH


def test_heal_fix_m3_snapshot_series_corrections_resolve_like_revisable_ones() -> None:
    """M3: SNAPSHOT_SERIES rows that carry a revision_seq are corrections — the
    massive_split_evidence shape resolves like REVISABLE_RELEASE instead of
    serving both revisions of the split."""
    a1_rev1 = {"action_id": "A1", "ratio": 2.0,
               "effective_at": "2026-01-09T00:00:00+00:00", "revision_seq": 1,
               "published_at": "2026-01-07T12:00:00+00:00",
               "ingested_at": "2026-01-07T12:10:00+00:00"}
    a1_rev2 = {**a1_rev1, "ratio": 0.5, "revision_seq": 2,
               "published_at": "2026-01-08T12:00:00+00:00",
               "ingested_at": "2026-01-08T12:10:00+00:00"}
    result = reconstruct(
        _reconstruct_request("published_at", HEAL_CUTOFF),
        {"massive_split_evidence": Dependency(
            name="massive_split_evidence", profile=TemporalProfile.SNAPSHOT_SERIES,
            rows=(a1_rev1, a1_rev2), key_fields=("action_id",))},
        required=("massive_split_evidence",),
        code_version=CODE_VERSION,
    )
    assert [row["ratio"] for row in result.values["massive_split_evidence"]] == [0.5]
    assert result.evidence["revision_resolution"][
        "massive_split_evidence"] == "max_revision_seq_per_key"


def test_heal_fix_m3_key_fields_without_revision_ordering_refuse_duplicates() -> None:
    """M3: with NO revision ordering declared, two different rows of one key are
    a contradiction (DUPLICATE_KEY), never a silent pick — while a bit-exact
    duplicate collapses and the unique-key path is labelled in the evidence."""
    row_a = {"action_id": "A1", "ratio": 2.0,
             "effective_at": "2026-01-09T00:00:00+00:00",
             "published_at": "2026-01-07T12:00:00+00:00",
             "ingested_at": "2026-01-07T12:10:00+00:00"}
    row_b = {**row_a, "ratio": 0.5}
    with pytest.raises(ReadRefusal) as exc:
        reconstruct(
            _reconstruct_request("published_at", HEAL_CUTOFF),
            {"massive_split_evidence": Dependency(
                name="massive_split_evidence", profile=TemporalProfile.SNAPSHOT_SERIES,
                rows=(row_a, row_b), key_fields=("action_id",))},
            required=("massive_split_evidence",),
            code_version=CODE_VERSION,
        )
    assert exc.value.code is RefusalCode.DUPLICATE_KEY
    collapsed = reconstruct(
        _reconstruct_request("published_at", HEAL_CUTOFF),
        {"massive_split_evidence": Dependency(
            name="massive_split_evidence", profile=TemporalProfile.SNAPSHOT_SERIES,
            rows=(row_a, dict(row_a)), key_fields=("action_id",))},
        required=("massive_split_evidence",),
        code_version=CODE_VERSION,
    )
    assert len(collapsed.values["massive_split_evidence"]) == 1
    assert collapsed.evidence["revision_resolution"][
        "massive_split_evidence"] == "unique_key"


def test_heal_guard_m3_identical_duplicates_collapse_and_unique_keys_serve() -> None:
    """Whatever the resolution law, the DISTINCT rows are exactly what is served:
    one A1 and one A2 — a bit-exact duplicate never widens the answer."""
    row_a = {"action_id": "A1", "ratio": 2.0,
             "effective_at": "2026-01-09T00:00:00+00:00",
             "published_at": "2026-01-07T12:00:00+00:00",
             "ingested_at": "2026-01-07T12:10:00+00:00"}
    row_c = {**row_a, "action_id": "A2", "ratio": 1.5}
    result = reconstruct(
        _reconstruct_request("published_at", HEAL_CUTOFF),
        {"massive_split_evidence": Dependency(
            name="massive_split_evidence", profile=TemporalProfile.SNAPSHOT_SERIES,
            rows=(row_a, dict(row_a), row_c), key_fields=("action_id",))},
        required=("massive_split_evidence",),
        code_version=CODE_VERSION,
    )
    served = {(row["action_id"], row["ratio"])
              for row in result.values["massive_split_evidence"]}
    assert sorted(served) == [("A1", 2.0), ("A2", 1.5)]
    resolution = result.evidence["revision_resolution"]["massive_split_evidence"]
    assert resolution in ("unique_key", "none")


def test_heal_fix_m4_rows_of_an_unselected_generation_are_not_served() -> None:
    """M4 (D00.D5.1, EXCLUDE): a read that binds g1 serves ONLY g1's rows — the
    g2-tagged row is another generation's content, not this read's input."""
    g1 = GenerationRef("g1", published_at="2026-01-02T00:00:00+00:00")
    g2 = GenerationRef("g2", published_at="2026-01-09T00:00:00+00:00")
    row_g1 = {"action_id": "A1", "ratio": 4.0, "generation_id": "g1",
              "effective_at": "2026-01-03T00:00:00+00:00",
              "published_at": "2026-01-03T00:00:00+00:00",
              "ingested_at": "2026-01-03T01:00:00+00:00"}
    row_g2 = {"action_id": "A1", "ratio": 0.5, "generation_id": "g2",
              "effective_at": "2026-01-05T00:00:00+00:00",
              "published_at": "2026-01-05T00:00:00+00:00",
              "ingested_at": "2026-01-05T01:00:00+00:00"}
    result = reconstruct(
        _reconstruct_request("published_at", HEAL_CUTOFF),
        {"splits": Dependency(name="splits", profile=TemporalProfile.SNAPSHOT_SERIES,
                              rows=(row_g1, row_g2), key_fields=("action_id",),
                              generations=(g1, g2))},
        required=("splits",), code_version=CODE_VERSION)
    assert result.evidence["dependency_generation_ids"]["splits"] == "g1"
    assert [row["ratio"] for row in result.values["splits"]] == [4.0]


def test_heal_fix_m4_an_untagged_row_under_a_generation_ledger_refuses() -> None:
    """M4: under a generation ledger, a row bound to no generation is never
    served under one — it refuses, it is not silently swept in."""
    g1 = GenerationRef("g1", published_at="2026-01-02T00:00:00+00:00")
    naked = {"action_id": "A1", "ratio": 2.0,
             "effective_at": "2026-01-09T00:00:00+00:00",
             "published_at": "2026-01-03T00:00:00+00:00",
             "ingested_at": "2026-01-03T01:00:00+00:00"}
    with pytest.raises(ReadRefusal) as exc:
        reconstruct(
            _reconstruct_request("published_at"),
            {"splits": Dependency(name="splits", profile=TemporalProfile.SNAPSHOT_SERIES,
                                  rows=(naked,), key_fields=("action_id",),
                                  generations=(g1,))},
            required=("splits",), code_version=CODE_VERSION)
    assert exc.value.code is RefusalCode.UNBOUND_DEPENDENCY


def test_heal_fix_m5_current_serves_only_the_max_revision() -> None:
    """M5: CURRENT resolves revisions like every other read — the corrected
    ratio is the answer, not both revisions side by side."""
    rev1 = {"action_id": "A1", "ratio": 2.0, "revision_seq": 1,
            "effective_at": "2026-01-09T00:00:00+00:00",
            "published_at": "2026-01-07T12:00:00+00:00",
            "ingested_at": "2026-01-07T12:10:00+00:00"}
    rev2 = {**rev1, "ratio": 0.5, "revision_seq": 2,
            "published_at": "2026-01-08T12:00:00+00:00",
            "ingested_at": "2026-01-08T12:10:00+00:00"}
    result = current(
        ReadRequest(ReadMode.CURRENT, _contract()),
        {"splits": Dependency(name="splits", profile=TemporalProfile.SNAPSHOT_SERIES,
                              rows=(rev1, rev2), key_fields=("action_id",))},
        evidence=_evidence())
    assert [row["ratio"] for row in result.values["splits"]] == [0.5]
    assert result.evidence["revision_resolution"]["splits"] == "max_revision_seq_per_key"


def test_heal_fix_m5_current_binds_the_newest_non_superseded_generation() -> None:
    """M5 (D00.D5.2): CURRENT binds the ledger's newest non-superseded
    generation and serves only that generation's rows, like a read binds."""
    g1 = GenerationRef("g1", published_at="2026-01-02T00:00:00+00:00")
    g3 = GenerationRef("g3", published_at="2026-01-09T00:00:00+00:00", supersedes="g1")
    row_g1 = {"action_id": "A1", "ratio": 2.0, "generation_id": "g1",
              "effective_at": "2026-01-03T00:00:00+00:00",
              "published_at": "2026-01-03T00:00:00+00:00",
              "ingested_at": "2026-01-03T01:00:00+00:00"}
    row_g3 = {"action_id": "A1", "ratio": 0.5, "generation_id": "g3",
              "effective_at": "2026-01-05T00:00:00+00:00",
              "published_at": "2026-01-05T00:00:00+00:00",
              "ingested_at": "2026-01-05T01:00:00+00:00"}
    result = current(
        ReadRequest(ReadMode.CURRENT, _contract()),
        {"splits": Dependency(name="splits", profile=TemporalProfile.SNAPSHOT_SERIES,
                              rows=(row_g1, row_g3), key_fields=("action_id",),
                              generations=(g1, g3))},
        evidence=_evidence(identity_generation_id="g3"))
    assert result.evidence["dependency_generation_ids"]["splits"] == "g3"
    assert [row["generation_id"] for row in result.values["splits"]] == ["g3"]


def test_heal_fix_m5_current_refuses_evidence_naming_a_superseded_generation() -> None:
    """M5 (D00.D5.2): CURRENT evidence naming a superseded generation is STALE —
    a superseded generation is readable by id only for RECONSTRUCT/REPLAY."""
    g1 = GenerationRef("g1", published_at="2026-01-02T00:00:00+00:00")
    g3 = GenerationRef("g3", published_at="2026-01-09T00:00:00+00:00", supersedes="g1")
    with pytest.raises(ReadRefusal) as exc:
        current(
            ReadRequest(ReadMode.CURRENT, _contract()),
            {"splits": Dependency(name="splits", profile=TemporalProfile.SNAPSHOT_SERIES,
                                  rows=(), generations=(g1, g3))},
            evidence=_evidence(identity_generation_id="g1"))
    assert exc.value.code is RefusalCode.STALE_GENERATION


def test_heal_fix_m6_fingerprint_binds_the_selected_generation() -> None:
    """M6: two reads selecting the same (empty) rows under DIFFERENT selected
    generations can never present themselves as the same input state."""
    gen1 = GenerationRef("gen-1", published_at="2026-01-02T00:00:00+00:00")
    gen2 = GenerationRef("gen-2", published_at="2026-01-09T00:00:00+00:00")
    dependencies = {"identity": Dependency(name="identity",
                                           profile=TemporalProfile.SNAPSHOT_SERIES,
                                           rows=(), generations=(gen1, gen2))}
    early = selected_input_sha256s(reconstruct(
        _reconstruct_request("published_at", "2026-01-05T00:00:00+00:00"),
        dependencies, required=("identity",), code_version=CODE_VERSION))
    late = selected_input_sha256s(reconstruct(
        _reconstruct_request("published_at", "2026-01-10T00:00:00+00:00"),
        dependencies, required=("identity",), code_version=CODE_VERSION))
    assert early["identity"] != late["identity"]


def test_heal_cutoff_a_row_stamped_exactly_at_the_cutoff_is_known() -> None:
    """m1: the cutoff is INCLUSIVE for rows — known_at == cutoff is known."""
    exact = {"action_id": "A1", "ratio": 2.0,
             "effective_at": "2026-01-09T00:00:00+00:00",
             "published_at": CUTOFF, "ingested_at": CUTOFF}
    eligible = eligible_rows([exact], TemporalProfile.SNAPSHOT_SERIES,
                             cutoff=CUTOFF, clock="published_at")
    assert [row["action_id"] for row in eligible] == ["A1"]


def test_heal_cutoff_a_generation_published_exactly_at_the_cutoff_is_selectable() -> None:
    """m1: the cutoff is INCLUSIVE for generations — published exactly at the
    cutoff, the generation is the one the read binds."""
    gen = GenerationRef("gen-x", published_at=CUTOFF)
    chosen = select_generation((gen,), cutoff=CUTOFF, clock="published_at")
    assert chosen.generation_id == "gen-x"


def test_heal_fix_ro_served_rows_are_read_only() -> None:
    """m7: served rows are read-only mappings — mutating one would rewrite the
    very inputs the evidence just bound."""
    result = _reconstruct([REV1], clock="published_at")
    with pytest.raises(TypeError):
        result.values["revisions"][0]["value"] = 999.0
    holdings = current(
        ReadRequest(ReadMode.CURRENT, _contract()),
        {"holdings": Dependency(name="holdings", profile=TemporalProfile.BARS,
                                rows=({"qty": 1},))},
        evidence=_evidence())
    with pytest.raises(TypeError):
        holdings.values["holdings"][0]["qty"] = 2
