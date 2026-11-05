"""Read coherence ACROSS dependencies (T02) — ``reconstruct`` composing D00.D1.

T01 pinned the read contract one dependency at a time.  T02 pins the composition
law that only shows up when ONE canonical read combines prices with corporate
actions, the identity generation and an index membership snapshot:

* ONE reconstruction cutoff governs EVERY dependency — there is no per-dependency
  cutoff to leak through (T02.02).
* A value binds the inputs ACTUALLY selected, digestibly: equal selections bind
  one digest whatever order the rows were supplied in, and a different selection
  can never present itself as the same input state (T02.01c).
* A checksum alone never satisfies exact replay — retained bytes or
  NO_RETAINED_OUTPUT (T02.01d / T02.03).
* A newer generation is never served under an older requested identity, and a
  missing dependency or a generation ledger a stale response omitted is
  UNBOUND, not silently read through (T02.04).

Fixture world (all synthetic, stated by hand): US listing ``SEC:US-XNYS-ABC``
("ABC") with daily bars 01-05 and 01-08, a 2-for-1 split action A1 corrected the
next day, polygon alias generations g1/g2 where g2 renames ABC -> ABCD, and an
index membership snapshot effective 01-09.

Run: python3 -m pytest tests/test_dataos_read_coherence.py -q
"""

from __future__ import annotations

import hashlib
from datetime import date

import pytest

from lib.dataos.identity import (
    AliasRow,
    VendorAliasTable,
    alias_binding_sha256,
)
from lib.dataos.read_contract import (
    Dependency,
    GenerationRef,
    ReadContractError,
    ReadMode,
    ReadRefusal,
    ReadRequest,
    RefusalCode,
    RetainedOutput,
    ViewContract,
    reconstruct,
    replay,
    selected_input_sha256s,
)
from lib.dataos.temporal import TemporalProfile

CODE_VERSION = "b2" * 20  # a 40-char lowercase code version, stated by hand
SECURITY_ID = "SEC:US-XNYS-ABC"  # stated by hand: a symbol is never an identity
VENDOR = "polygon"  # the reader's clocked vendor; decision_at is required

CUTOFF_EARLY = "2026-01-06T00:00:00+00:00"  # bar known, split/alias/membership not
CUTOFF_LATE = "2026-01-08T13:00:00+00:00"  # g2 + the correction + both bars known


class _Exploding:
    """Iterable whose iteration FAILS the test — proves a check fired first."""

    def __iter__(self):
        raise AssertionError("rows were iterated before the contract check fired")


def _contract() -> ViewContract:
    return ViewContract(
        purpose="T02 coherence: one cutoff governs every dependency of one read",
        identity={"security_id": SECURITY_ID, "listing_id": "LST:US-XNYS-ABC"},
        field_units={"close": "USD/share", "ratio": "shares/shares"},
        adjustment_reference={"basis": "raw"},
        coverage="synthetic fixture world local to this suite",
    )


# ── the fixture world: one security, one cutoff timeline ─────────────────────
# Bars: BARS rows carry the interval label plus BOTH knowledge clocks.
BAR_0105 = {
    "security_id": SECURITY_ID,
    "period_start": "2026-01-05T14:30:00+00:00",
    "period_end": "2026-01-05T21:00:00+00:00",
    "close": 100.0,
    "published_at": "2026-01-05T21:30:00+00:00",
    "ingested_at": "2026-01-05T21:30:00+00:00",
}
# Published before the late cutoff, so BOTH bars are known by 01-08T13:00Z.
BAR_0108 = {
    "security_id": SECURITY_ID,
    "period_start": "2026-01-08T14:30:00+00:00",
    "period_end": "2026-01-08T21:00:00+00:00",
    "close": 50.0,
    "published_at": "2026-01-08T12:45:00+00:00",
    "ingested_at": "2026-01-08T12:45:00+00:00",
}

# Actions: A1 is a 2-for-1 split (ex-date 01-09) whose ratio a correction changed.
ACTION_A1_REV1 = {
    "action_id": "A1",
    "event_at": "2026-01-09T00:00:00+00:00",  # the ex-date
    "ratio": 2.0,
    "status": "BOUND",
    "revision_seq": 1,
    "published_at": "2026-01-07T12:00:00+00:00",
    "ingested_at": "2026-01-07T12:10:00+00:00",
}
ACTION_A1_REV2 = {
    **ACTION_A1_REV1,
    "ratio": 0.5,  # the correction: the ratio itself changed
    "revision_seq": 2,
    "published_at": "2026-01-08T12:00:00+00:00",
    "ingested_at": "2026-01-08T12:10:00+00:00",
}
# Published before the early cutoff but ingested after it — the V08 cross-check.
ACTION_A0_UNINGESTED = {
    "action_id": "A0",
    "event_at": "2026-01-06T00:00:00+00:00",
    "ratio": 1.0,
    "status": "BOUND",
    "revision_seq": 1,
    "published_at": "2026-01-05T20:00:00+00:00",
    "ingested_at": "2026-01-06T09:00:00+00:00",
}

# Membership: an index snapshot that only exists from 01-09 — after both cutoffs.
MEMBERSHIP_ROW = {
    "index_id": "IDX-TEST",
    "security_id": SECURITY_ID,
    "weight": 0.01,
    "effective_at": "2026-01-09T00:00:00+00:00",
    "published_at": "2026-01-09T00:00:00+00:00",
    "ingested_at": "2026-01-09T01:00:00+00:00",
}

# Identity generations: g2 renames ABC -> ABCD on the vendor.
G1 = GenerationRef(generation_id="g1", published_at="2026-01-02T00:00:00+00:00",
                   ingested_at="2026-01-02T01:00:00+00:00")
G2 = GenerationRef(generation_id="g2", published_at="2026-01-08T06:00:00+00:00",
                   ingested_at="2026-01-08T07:00:00+00:00")

_EVIDENCE_ABC = "cd" * 32  # 64-hex evidence digests, stated by hand
_EVIDENCE_ABCD = "ef" * 32


def _sealed_row(**over) -> AliasRow:
    """A polygon AliasRow sealed with the module's own public seal function.

    Calling ``alias_binding_sha256`` here is INPUT CONSTRUCTION (the row must
    carry a valid seal to exist at all), never an expected value in an assert.
    """
    fields = dict(vendor=VENDOR, vendor_symbol="ABC", security_id=SECURITY_ID,
                  valid_from=date(2026, 1, 1), valid_to=None,
                  known_at="2026-01-02T00:00:00+00:00",
                  evidence_sha256=_EVIDENCE_ABC)
    fields.update(over)
    seal = alias_binding_sha256(
        fields["vendor"], fields["vendor_symbol"], fields["security_id"],
        fields["valid_from"], fields["valid_to"], fields["known_at"],
        fields["evidence_sha256"])
    return AliasRow(binding_sha256=seal, **fields)


# g1: ABC under its original name, unbounded.  g2: the name is bounded to the
# rename day (valid_to EXCLUSIVE) and ABCD takes over from 2026-01-08.
TABLE_G1 = VendorAliasTable((_sealed_row(),))
TABLE_G2 = VendorAliasTable((
    _sealed_row(valid_to=date(2026, 1, 8)),
    _sealed_row(vendor_symbol="ABCD", valid_from=date(2026, 1, 8),
                known_at="2026-01-08T06:00:00+00:00",
                evidence_sha256=_EVIDENCE_ABCD),
))


def _world(*, prices=(BAR_0105, BAR_0108),
           actions=(ACTION_A1_REV1, ACTION_A1_REV2),
           pinned_generation_id: str | None = None) -> dict:
    return {
        "prices": Dependency(name="prices", profile=TemporalProfile.BARS,
                             rows=tuple(prices),
                             key_fields=("security_id", "period_end")),
        "actions": Dependency(name="actions",
                              profile=TemporalProfile.REVISABLE_RELEASE,
                              rows=tuple(actions), key_fields=("action_id",)),
        "identity": Dependency(name="identity",
                               profile=TemporalProfile.SNAPSHOT_SERIES, rows=(),
                               generations=(G1, G2),
                               pinned_generation_id=pinned_generation_id),
        "membership": Dependency(name="membership",
                                 profile=TemporalProfile.SNAPSHOT_SERIES,
                                 rows=(MEMBERSHIP_ROW,),
                                 key_fields=("index_id", "security_id")),
    }


def _read(world, cutoff, *, clock="published_at") -> object:
    request = ReadRequest(ReadMode.RECONSTRUCT, _contract(), cutoff=cutoff,
                          clock=clock)
    return reconstruct(
        request, world,
        required=("prices", "actions", "identity", "membership"),
        code_version=CODE_VERSION)


# ── T02.01a: one cutoff, one generation, only the rows known then ────────────
def test_t02_01_a_one_early_cutoff_binds_g1_and_only_the_known_bar() -> None:
    result = _read(_world(), CUTOFF_EARLY)
    assert result.evidence["dependency_generation_ids"]["identity"] == "g1"
    assert [(row["period_end"], row["close"]) for row in result.values["prices"]] == [
        ("2026-01-05T21:00:00+00:00", 100.0)]
    assert result.values["actions"] == ()
    assert result.values["membership"] == ()


# ── T02.01b: the later cutoff sees the correction, never the future ──────────
def test_t02_01_b_later_cutoff_binds_g2_both_bars_and_only_the_correction() -> None:
    result = _read(_world(), CUTOFF_LATE)
    assert result.evidence["dependency_generation_ids"]["identity"] == "g2"
    assert sorted(row["period_end"] for row in result.values["prices"]) == [
        "2026-01-05T21:00:00+00:00", "2026-01-08T21:00:00+00:00"]
    assert sorted(row["close"] for row in result.values["prices"]) == [50.0, 100.0]
    assert [row["revision_seq"] for row in result.values["actions"]] == [2]
    assert [row["ratio"] for row in result.values["actions"]] == [0.5]  # V09
    assert result.values["membership"] == ()


# ── T02.01c: a value binds the inputs actually selected ──────────────────────
EMPTY_SELECTION_SHA256 = (  # sha256 of b"[]" — the digest of selecting nothing
    "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945")


def test_t02_01_c_equal_selections_bind_one_digest_whatever_the_supply_order() -> None:
    forward = _read(_world(), CUTOFF_LATE)
    reversed_world = _world(prices=(BAR_0108, BAR_0105),
                            actions=(ACTION_A1_REV2, ACTION_A1_REV1))
    backward = _read(reversed_world, CUTOFF_LATE)
    # The selected TUPLES differ (supply order survives the read) ...
    assert forward.values["prices"] != backward.values["prices"]
    # ... yet the input binding does not: selection, not supply order, digests.
    assert selected_input_sha256s(forward) == selected_input_sha256s(backward)


def test_t02_01_c_different_cutoffs_bind_different_input_states() -> None:
    early = selected_input_sha256s(_read(_world(), CUTOFF_EARLY))
    late = selected_input_sha256s(_read(_world(), CUTOFF_LATE))
    assert early != late  # the bindings differ as MAPPINGS ...
    assert early["prices"] != late["prices"]  # ... because prices differ
    assert early["actions"] != late["actions"]  # ... and the action state differs
    assert early["membership"] == late["membership"]  # both selected nothing
    assert early["membership"] == EMPTY_SELECTION_SHA256
    assert early["identity"] != late["identity"]  # g1 vs g2 selected: the generation binds the input state (R01 M6)
    assert EMPTY_SELECTION_SHA256 not in (early["identity"], late["identity"])
    for digest in (*early.values(), *late.values()):
        assert len(digest) == 64 and digest == digest.lower()


# ── T02.01d: exact replay only when material is retained ─────────────────────
PAYLOAD = b"exact emitted bytes \x00\x01 of output out-abc"
PAYLOAD_SHA256 = hashlib.sha256(PAYLOAD).hexdigest()
RECEIPT = "ca" * 32
OUTPUT_ID = "out-abc"


def _replay_request() -> ReadRequest:
    return ReadRequest(ReadMode.REPLAY, _contract(), output_id=OUTPUT_ID)


def test_t02_01_d_replay_serves_retained_bytes_under_their_own_label() -> None:
    retained = RetainedOutput(output_id=OUTPUT_ID, payload=PAYLOAD,
                              sha256=PAYLOAD_SHA256,
                              publishing_receipt_sha256=RECEIPT)
    result = replay(_replay_request(), retained)
    assert result.label == "replay"
    assert result.payload == PAYLOAD
    assert result.evidence["sha256"] == PAYLOAD_SHA256
    assert result.evidence["publishing_receipt_sha256"] == RECEIPT


def test_t02_01_d_a_checksum_for_unretained_bytes_is_not_retained_material() -> None:
    checksum_only = RetainedOutput(output_id=OUTPUT_ID, payload=None,
                                   sha256=PAYLOAD_SHA256,  # the TRUE digest
                                   publishing_receipt_sha256=RECEIPT)
    with pytest.raises(ReadRefusal) as exc:
        replay(_replay_request(), checksum_only)
    assert exc.value.code is RefusalCode.NO_RETAINED_OUTPUT


# ── T02.02: nothing leaks through a permitted old price row ──────────────────
def test_t02_02_one_old_cutoff_governs_every_dependency_at_once() -> None:
    """ONE reconstruct call at 01-06: the 01-05 bar is served while the split,
    the rename generation and the membership snapshot are all still absent."""
    result = _read(_world(), CUTOFF_EARLY)
    assert [row["period_end"] for row in result.values["prices"]] == [
        "2026-01-05T21:00:00+00:00"]  # the permitted old price row
    # (i) neither revision of the split existed yet
    assert result.values["actions"] == ()
    # (ii) identity is g1, and the reader's own clocked lookup at the SAME
    # cutoff knows only the old name: the id by hand, the new symbol absent.
    assert result.evidence["dependency_generation_ids"]["identity"] == "g1"
    on = date(2026, 1, 5)
    assert TABLE_G1.resolve(VENDOR, "ABC", on,
                            decision_at=CUTOFF_EARLY) == SECURITY_ID
    assert TABLE_G1.resolve(VENDOR, "ABCD", on, decision_at=CUTOFF_EARLY) is None
    # The g2 table's rename row exists, but its own known_at clock agrees with
    # the contract cutoff: at 01-06 it resolves nothing, at 01-08T13Z it does.
    assert TABLE_G2.resolve(VENDOR, "ABCD", date(2026, 1, 8),
                            decision_at=CUTOFF_EARLY) is None
    assert TABLE_G2.resolve(VENDOR, "ABCD", date(2026, 1, 8),
                            decision_at=CUTOFF_LATE) == SECURITY_ID
    assert TABLE_G2.resolve(VENDOR, "ABC", date(2026, 1, 8),
                            decision_at=CUTOFF_LATE) is None  # rename day
    # (iii) the membership snapshot is 01-09 news
    assert result.values["membership"] == ()


def test_t02_02_iv_the_ingested_clock_keeps_a_published_but_uningested_action_out() -> None:
    """V08 across dependencies: under clock=ingested_at the same cutoff holds
    the A0 action OUT (published 01-05, ingested 01-06T09Z) while the bar stays."""
    world = _world(actions=(ACTION_A0_UNINGESTED, ACTION_A1_REV1, ACTION_A1_REV2))
    result = _read(world, CUTOFF_EARLY, clock="ingested_at")
    assert result.values["actions"] == ()
    assert [row["period_end"] for row in result.values["prices"]] == [
        "2026-01-05T21:00:00+00:00"]
    assert result.evidence["clock"] == "ingested_at"
    assert result.evidence["knowledge"] == "system_observation"


# ── T02.03: a checksum alone never satisfies exact replay ────────────────────
def test_t02_03_a_valid_checksum_with_no_bytes_refuses_not_regenerates() -> None:
    """Even a digest of the reconstruction's REAL selected inputs, presented as
    a retained sha256, is not retained material."""
    result = _read(_world(), CUTOFF_LATE)
    input_digest = selected_input_sha256s(result)["prices"]
    checksum_only = RetainedOutput(output_id=OUTPUT_ID, payload=None,
                                   sha256=input_digest,
                                   publishing_receipt_sha256=RECEIPT)
    with pytest.raises(ReadRefusal) as exc:
        replay(_replay_request(), checksum_only)
    assert exc.value.code is RefusalCode.NO_RETAINED_OUTPUT


def test_t02_03_a_reconstruction_is_never_labelled_replay_even_on_a_digest_hit() -> None:
    result = _read(_world(), CUTOFF_LATE)
    assert result.label == "reconstruction"
    assert result.label != "replay"
    assert result.mode is ReadMode.RECONSTRUCT
    assert result.payload is None


def test_t02_03_tampered_retained_bytes_refuse_instead_of_serving() -> None:
    retained = RetainedOutput(output_id=OUTPUT_ID, payload=b"tampered bytes",
                              sha256=PAYLOAD_SHA256,  # the ORIGINAL digest
                              publishing_receipt_sha256=RECEIPT)
    with pytest.raises(ReadRefusal) as exc:
        replay(_replay_request(), retained)
    assert exc.value.code is RefusalCode.RETAINED_DIGEST_MISMATCH


def test_t02_03_asking_a_replay_for_its_inputs_is_a_type_error_not_a_digest() -> None:
    """A replay binds the retained sha256; it selected no inputs to bind."""
    retained = RetainedOutput(output_id=OUTPUT_ID, payload=PAYLOAD,
                              sha256=PAYLOAD_SHA256,
                              publishing_receipt_sha256=RECEIPT)
    with pytest.raises(ReadContractError):
        selected_input_sha256s(replay(_replay_request(), retained))


# ── T02.04: stale generation / missing dependency ────────────────────────────
def test_t02_04_a_newer_generation_is_never_served_under_an_older_pinned_id() -> None:
    world = _world(pinned_generation_id="g1")
    with pytest.raises(ReadRefusal) as exc:
        _read(world, CUTOFF_LATE)  # g2 is eligible, the caller asked for g1
    assert exc.value.code is RefusalCode.STALE_GENERATION


def test_t02_04_a_pin_from_before_the_new_generation_is_served_honestly() -> None:
    result = _read(_world(pinned_generation_id="g1"), CUTOFF_EARLY)
    assert result.evidence["dependency_generation_ids"]["identity"] == "g1"


def test_t02_04_a_pin_for_a_generation_not_yet_eligible_is_stale() -> None:
    world = _world(pinned_generation_id="g2")
    with pytest.raises(ReadRefusal) as exc:
        _read(world, CUTOFF_EARLY)  # g2 postdates the cutoff entirely
    assert exc.value.code is RefusalCode.STALE_GENERATION


def test_t02_04_a_stale_response_that_omitted_the_ledger_is_unbound() -> None:
    world = _world()
    world["identity"] = Dependency(name="identity",
                                   profile=TemporalProfile.SNAPSHOT_SERIES,
                                   rows=(), generations=(),
                                   pinned_generation_id="g1")
    with pytest.raises(ReadRefusal) as exc:
        _read(world, CUTOFF_EARLY)
    assert exc.value.code is RefusalCode.UNBOUND_DEPENDENCY


def test_t02_04_a_missing_required_dependency_refuses_before_any_rows() -> None:
    world = _world()
    world["prices"] = Dependency(name="prices", profile=TemporalProfile.BARS,
                                 rows=_Exploding(),
                                 key_fields=("security_id", "period_end"))
    del world["membership"]  # required, absent from the mapping
    with pytest.raises(ReadRefusal) as exc:
        _read(world, CUTOFF_EARLY)
    assert exc.value.code is RefusalCode.UNBOUND_DEPENDENCY


# ── R01 heal: the served rows belong to the bound generation; cutoff inclusive
def test_heal_fix_m4_t02_served_identity_rows_belong_to_the_bound_generation() -> None:
    """The R01 reproduction across a real read: identity rows tagged per
    generation under one ledger — a read that binds g2 serves ONLY g2's rows,
    never the g1 row sitting in the same supply."""
    g1_row = {"security_id": SECURITY_ID, "vendor_symbol": "ABC",
              "generation_id": "g1",
              "published_at": "2026-01-02T00:00:00+00:00",
              "ingested_at": "2026-01-02T01:00:00+00:00"}
    g2_row = {"security_id": SECURITY_ID, "vendor_symbol": "ABCD",
              "generation_id": "g2",
              "published_at": "2026-01-08T06:00:00+00:00",
              "ingested_at": "2026-01-08T07:00:00+00:00"}
    world = _world()
    world["identity"] = Dependency(name="identity",
                                   profile=TemporalProfile.SNAPSHOT_SERIES,
                                   rows=(g1_row, g2_row), generations=(G1, G2))
    result = _read(world, CUTOFF_LATE)
    assert result.evidence["dependency_generation_ids"]["identity"] == "g2"
    assert [row["vendor_symbol"] for row in result.values["identity"]] == ["ABCD"]


def test_heal_cutoff_t02_exact_cutoff_includes_the_row_and_the_generation() -> None:
    """The cutoff is INCLUSIVE on both sides of one read: a bar stamped exactly
    at the cutoff is known, and a generation published exactly at the cutoff is
    the one the read binds."""
    exact = "2026-01-05T21:30:00+00:00"  # exactly BAR_0105.published_at
    gen = GenerationRef("gen-exact", published_at=exact, ingested_at=exact)
    world = _world()
    world["identity"] = Dependency(name="identity",
                                   profile=TemporalProfile.SNAPSHOT_SERIES,
                                   rows=(), generations=(gen,))
    result = _read(world, exact)
    assert [row["period_end"] for row in result.values["prices"]] == [
        "2026-01-05T21:00:00+00:00"]  # the bar stamped AT the cutoff is known
    assert result.evidence["dependency_generation_ids"]["identity"] == "gen-exact"
