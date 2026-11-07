"""A02-1 — update and correction acceptance across CURRENT, RECONSTRUCT, REPLAY.

ONE hermetic SYNTHETIC timeline drives the real read seams on main through a
full update-then-correction sequence and records what each mode answers at
every step: an ordinary new-day update (SYN-G2 supersedes SYN-G1), a controlled
SYNTHETIC correction (SYN-S1C, a 3/1 forward split superseding SYN-S1's 2/1 —
this is NOT a natural vendor event), and a receipt-only superseding generation
(SYN-G3: identical row values, a new receipt, D5.3).

Every fixture generation, action row and correction below is SYNTHETIC; the
suite reads no stored tree, keeps all instants as fixed UTC literals and asserts
all three modes at each step of the sequence.  Sequence-level by design: the
existing tests/test_dataos_price_revisions.py P05/P06 units pin single-step
facts; this module moves ONE fixture world through A02.01-A02.04.

Run: ~/lanes/venv/bin/python -m pytest tests/verification/test_a02_corrections.py -q
"""
from __future__ import annotations

import hashlib
import inspect
import sys
from dataclasses import replace
from datetime import date, datetime, timezone
from fractions import Fraction
from pathlib import Path

import pytest

from lib.dataos.price_views import (
    RefusalReason,
    ViewRefusal,
    ViewVintage,
    reconstruct_price_view,
    reopen_view,
    retain_view,
    simple_returns,
    view_label,
    view_receipt_sha256,
)
from lib.dataos.read_contract import (
    CurrentEvidence,
    Dependency,
    GenerationRef,
    ReadContractError,
    ReadMode,
    ReadRefusal,
    ReadRequest,
    RefusalCode,
    ViewContract,
    current,
)
from lib.dataos.registry import DatasetContract, Registry
from lib.dataos.temporal import TemporalProfile

UTC = timezone.utc

# ── the frozen SYNTHETIC legs this lane can never close from here ────────────

PENDING_LEGS = (
    "UNFINISHED: natural new-day update through the original owner — hermetic lane; routed to the R03 cycle plan",
    "UNFINISHED: actual recorded revisions — hermetic lane, no data/ reads; every revision case here is a controlled SYNTHETIC case",
    "GAP: no refusal/rights generation field on GenerationRef or ViewVintage; A02.03 is tested as a receipt-only superseding generation (D5.3)",
    "GAP: no CURRENT-mode price-view composition; CURRENT is exercised at read_contract.current, the price view B is a RECONSTRUCT composition",
)

# ── the SYNTHETIC fixture world (one module-level timeline, fixed literals) ──
#
# Listing SYN-LST.A02 (one hyphen, so it is an identity string, never a parsed
# listing key) on venue XNYS; five trading days D1..D5, then the new day D6.
#   T_S1  SYN-S1 (2/1 forward split, ex D3) and actions generation SYN-AG1
#   T1    bars generation SYN-G1  — D1..D5, the day-5 view's source
#   T2    bars generation SYN-G2  — supersedes SYN-G1; D1..D5 identical + D6,
#                                   the ordinary NEW-DAY update
#   T3    SYN-S1C (3/1, supersedes SYN-S1) and actions generation SYN-AG2 —
#         a controlled SYNTHETIC correction, NOT a natural vendor event
#   T4    bars generation SYN-G3  — supersedes SYN-G2; row values identical to
#         SYN-G2's except generation_id/published_at/ingested_at (D5.3)

SECURITY_ID = "SYN-SEC-A02"
LISTING_ID = "SYN-LST.A02"
DATASET_ID = "SYN-DS-A02-SPLITS"
IDENTITY_GENERATION = "SYN-IDGEN-1"
CODE_VERSION = hashlib.sha256(b"SYN-A02-CODE-VERSION").hexdigest()[:40]

D1, D2, D3, D4, D5, D6 = ("2026-06-01", "2026-06-02", "2026-06-03",
                          "2026-06-04", "2026-06-05", "2026-06-08")
EX_DATE = D3  # the split's ex-date, inside D1..D5

_T_S1 = datetime(2026, 5, 20, tzinfo=UTC)
T1 = datetime(2026, 6, 6, tzinfo=UTC)
T2 = datetime(2026, 6, 9, tzinfo=UTC)
T3 = datetime(2026, 6, 10, tzinfo=UTC)
T4 = datetime(2026, 6, 11, tzinfo=UTC)
CUT_A = datetime(2026, 6, 7, tzinfo=UTC)        # A's cutoff, in [T1, T2)
CUT_B = datetime(2026, 6, 9, 12, tzinfo=UTC)    # B's cutoff, in [T2, T3)
CUT_C = datetime(2026, 6, 10, 12, tzinfo=UTC)   # the corrected cutoff, in [T3, T4)
INSTANTS = (_T_S1, T1, T2, T3, T4, CUT_A, CUT_B, CUT_C)

FIXTURE_IDS = (
    SECURITY_ID, LISTING_ID, DATASET_ID, IDENTITY_GENERATION,
    "SYN-G1", "SYN-G2", "SYN-G3", "SYN-AG1", "SYN-AG2",
    "SYN-S1", "SYN-S1C", "SYN-OUT-A", "SYN-OUT-B",
)

_CLOSES_G1 = (200, 202, 204, 206, 208)                    # D1..D5
_CLOSES_G2 = (200, 202, 204, 206, 208, 212)               # D1..D5 + D6
_VOLUMES = (1200, 1210, 1220, 1230, 1240, 1250)


def _iso(at: datetime) -> str:
    return at.isoformat()


def _syn_bar_rows(generation_id: str, published_at: datetime, days, closes) -> tuple[dict, ...]:
    """SYNTHETIC bar rows: the P05 observation shape, this suite's own values."""
    return tuple(
        {"date": day,
         "period_start": f"{day}T00:00:00+00:00",
         "period_end": f"{day}T23:59:59+00:00",
         "published_at": _iso(published_at),
         "ingested_at": _iso(published_at),
         "generation_id": generation_id,
         "close_raw": close,
         "volume_raw": volume}
        for day, close, volume in zip(days, closes, _VOLUMES)
    )


_BARS_G1 = _syn_bar_rows("SYN-G1", T1, (D1, D2, D3, D4, D5), _CLOSES_G1)
_BARS_G2 = _syn_bar_rows("SYN-G2", T2, (D1, D2, D3, D4, D5, D6), _CLOSES_G2)
_BARS_G3 = _syn_bar_rows("SYN-G3", T4, (D1, D2, D3, D4, D5, D6), _CLOSES_G2)

_G1_REF = GenerationRef("SYN-G1", published_at=_iso(T1), ingested_at=_iso(T1))
_G2_REF = GenerationRef("SYN-G2", published_at=_iso(T2), ingested_at=_iso(T2),
                       supersedes="SYN-G1")
_G3_REF = GenerationRef("SYN-G3", published_at=_iso(T4), ingested_at=_iso(T4),
                       supersedes="SYN-G2")

BARS_AT_B = Dependency("bars", TemporalProfile.BARS, rows=_BARS_G1 + _BARS_G2,
                       generations=(_G1_REF, _G2_REF))          # the step-2 world
BARS_FULL = Dependency("bars", TemporalProfile.BARS,
                       rows=_BARS_G1 + _BARS_G2 + _BARS_G3,
                       generations=(_G1_REF, _G2_REF, _G3_REF))  # after T4

# The actions ledger rows.  The RECONSTRUCT composition binds events by their
# published_at knowledge (the P05 idiom): both SYN-S1 and SYN-S1C are supplied
# and the cutoff decides which are known; SYN-S1C is a controlled SYNTHETIC
# correction, NOT a natural vendor event.
def _syn_action(event_id: str, *, ratio: str, published_at: datetime,
                generation_id: str, supersedes: str | None = None) -> dict:
    row = {"event_id": event_id, "family": "forward_split", "ex_date": EX_DATE,
           "event_at": _iso(_T_S1), "published_at": _iso(published_at),
           "ingested_at": _iso(published_at), "ratio": ratio,
           "source_receipt": hashlib.sha256(event_id.encode()).hexdigest(),
           "generation_id": generation_id}
    if supersedes is not None:
        row["supersedes"] = supersedes
    return row


_S1_ROW = _syn_action("SYN-S1", ratio="2/1", published_at=_T_S1,
                      generation_id="SYN-AG1")
_S1C_ROW = _syn_action("SYN-S1C", ratio="3/1", published_at=T3,
                       generation_id="SYN-AG2", supersedes="SYN-S1")
ACTIONS_ALL = (_S1_ROW, _S1C_ROW)

_AG1_REF = GenerationRef("SYN-AG1", published_at=_iso(_T_S1), ingested_at=_iso(_T_S1))
_AG2_REF = GenerationRef("SYN-AG2", published_at=_iso(T3), ingested_at=_iso(T3),
                         supersedes="SYN-AG1")
ACTIONS_LEDGER = Dependency("actions", TemporalProfile.EVENT, rows=ACTIONS_ALL,
                            generations=(_AG1_REF, _AG2_REF))

_CONTRACT = ViewContract(
    purpose="A02 update-and-correction acceptance witness (SYNTHETIC)",
    identity={"security_id": SECURITY_ID, "listing_id": LISTING_ID, "mic": "XNYS"},
    field_units={"close_sadj": "USD/share"},
    adjustment_reference={"basis": "sadj"},
    coverage="SYNTHETIC rows local to this suite; no stored tree is read",
)

_REGISTRY = Registry([DatasetContract.from_mapping({
    "dataset_id": DATASET_ID, "layer": "L1", "status": "PRODUCED",
    "owner": "macro-dashboard", "producer": "collectors/synthetic.py",
    "storage": "synthetic://SYN-A02/splits", "format": "parquet",
    "grain": ["event_id", "ex_date"], "temporal_profile": "EVENT",
    "version": "1.0.0"})])


def _obs(receipt: str) -> dict:
    """A qualifying source_record observation for one SYNTHETIC action row."""
    return {"dataset_id": DATASET_ID, "endpoint": "synthetic/SYN-A02/splits",
            "field_convention": "as_observed_split_ratio", "receipt": receipt,
            "origin": "source_record", "response": "events", "rights_limited": False}


def _receipt(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def compose(cutoff, action_rows, bars_dep):
    """The RECONSTRUCT composition at ``cutoff`` over the SYNTHETIC world."""
    return reconstruct_price_view(
        ReadRequest(ReadMode.RECONSTRUCT, _CONTRACT, cutoff=cutoff,
                    clock="published_at"),
        bars=bars_dep,
        actions=Dependency("actions", TemporalProfile.EVENT, rows=tuple(action_rows)),
        observations={row["event_id"]: _obs(row["source_receipt"])
                      for row in action_rows},
        registry=_REGISTRY, code_version=CODE_VERSION,
        identity_generation_id=IDENTITY_GENERATION, basis="SADJ")


def current_read(deps, evidence):
    """A CURRENT read over the SYNTHETIC ledgers."""
    return current(ReadRequest(ReadMode.CURRENT, _CONTRACT), deps, evidence=evidence)


def _replay(output_id: str) -> ReadRequest:
    return ReadRequest(ReadMode.REPLAY, _CONTRACT, output_id=output_id)


def _evidence(identity_generation_id: str) -> CurrentEvidence:
    return CurrentEvidence(
        receipt_sha256s=(_receipt("SYN-RCPT-BARS-A02"),),
        identity_generation_id=identity_generation_id,
        action_revision_set_id="actions:" + _receipt("SYN-A02-REVSET-EVIDENCE"),
        code_version=CODE_VERSION)


def _close(view, day: str) -> Fraction:
    (row,) = [row for row in view.rows if row["date"] == date.fromisoformat(day)]
    return row["close_sadj"]


def view_a_and_retained():
    """Step 1 of the sequence: view A at CUT_A, retained under SYN-OUT-A."""
    a = compose(CUT_A, (_S1_ROW,), BARS_FULL)
    return a, retain_view(a.view, a.vintage, output_id="SYN-OUT-A")


# ── A02.01 — a new eligible current view B, retained A intact ────────────────

def test_a02_01_step1_retain_view_a_under_its_receipt() -> None:
    a, retained_a = view_a_and_retained()
    assert a.vintage.source_generation_id == "SYN-G1"
    assert a.result.label == "reconstruction"
    assert _close(a.view, D1) == Fraction(100)   # 200 / 2, the SYN-S1 ratio
    assert retained_a.publishing_receipt_sha256 == view_receipt_sha256(
        "SYN-OUT-A", a.vintage, retained_a.view_digest)
    assert "source_generation=SYN-G1" in retained_a.label


def test_a02_01_step2_new_day_generation_is_current() -> None:
    result = current_read({"bars": BARS_AT_B}, _evidence("SYN-G2"))
    assert result.label == "current"
    assert result.evidence["dependency_generation_ids"]["bars"] == "SYN-G2"
    assert any(row["date"] == D6 for row in result.values["bars"])
    assert "cutoff" not in result.evidence
    assert "clock" not in result.evidence


@pytest.mark.parametrize("parameter", ["cutoff", "clock", "output_id"])
def test_a02_01_step2_current_takes_no_mode_parameters(parameter: str) -> None:
    value = {"cutoff": _iso(CUT_B), "clock": "published_at",
             "output_id": "SYN-OUT-B"}[parameter]
    with pytest.raises(ReadContractError):
        ReadRequest(ReadMode.CURRENT, _CONTRACT, **{parameter: value})


def test_a02_01_step2_view_b_composes_from_the_new_generation() -> None:
    b = compose(CUT_B, (_S1_ROW,), BARS_FULL)
    assert b.vintage.source_generation_id == "SYN-G2"
    assert len(b.view.rows) == 6
    assert "source_generation=SYN-G2" in b.label
    assert _close(b.view, D6) == Fraction(212)          # D6 is post-ex: raw
    assert _close(b.view, D1) == Fraction(100)          # pre-ex day still /2


def test_a02_01_retained_a_reopens_byte_exact_after_b() -> None:
    _, retained_a = view_a_and_retained()
    compose(CUT_B, (_S1_ROW,), BARS_FULL)               # view B now exists
    reopened = reopen_view(retained_a, _replay("SYN-OUT-A"))
    assert reopened.result.label == "replay"
    assert reopened.result.payload == retained_a.payload
    assert reopened.view.rows == compose(CUT_A, (_S1_ROW,), BARS_FULL).view.rows
    assert reopened.vintage == retained_a.vintage
    assert reopened.vintage.source_generation_id == "SYN-G1"


def test_a02_01_old_cutoff_reconstruction_binds_g1_and_is_labelled_reconstruction() -> None:
    # After SYN-G2, SYN-G3 and the correction all exist in the ledgers, A's own
    # cutoff still binds SYN-G1 and the old ratio — equal values to A's, but a
    # reconstruction label, never "replay" (D5.5).
    a, _ = view_a_and_retained()
    again = compose(CUT_A, ACTIONS_ALL, BARS_FULL)
    assert again.vintage.source_generation_id == "SYN-G1"
    assert again.result.label == "reconstruction"
    assert _close(again.view, D1) == Fraction(100)      # 2/1, not the 3/1 correction
    assert [row["close_sadj"] for row in again.view.rows] == \
        [row["close_sadj"] for row in a.view.rows]


def test_a02_01_superseded_generation_is_never_current_even_if_stamped_later() -> None:
    # SYNTHETIC ledger: the superseded generation carries the LATER stamp; the
    # supersedes edge, not the stamp, decides what CURRENT binds (D5.2).
    gx = GenerationRef("SYN-GX-LATE", published_at=_iso(datetime(2026, 6, 20, tzinfo=UTC)),
                       ingested_at=_iso(datetime(2026, 6, 20, tzinfo=UTC)))
    gy = GenerationRef("SYN-GY-LIVE", published_at=_iso(datetime(2026, 6, 12, tzinfo=UTC)),
                       ingested_at=_iso(datetime(2026, 6, 12, tzinfo=UTC)),
                       supersedes="SYN-GX-LATE")
    rows = (_syn_bar_rows("SYN-GX-LATE", datetime(2026, 6, 20, tzinfo=UTC),
                          (D1,), (200,))
            + _syn_bar_rows("SYN-GY-LIVE", datetime(2026, 6, 12, tzinfo=UTC),
                            (D1,), (200,)))
    ledger = Dependency("bars", TemporalProfile.BARS, rows=rows, generations=(gx, gy))
    result = current_read({"bars": ledger}, _evidence("SYN-GY-LIVE"))
    assert result.evidence["dependency_generation_ids"]["bars"] == "SYN-GY-LIVE"
    assert all(row["generation_id"] == "SYN-GY-LIVE" for row in result.values["bars"])


@pytest.mark.parametrize("mode", ["reconstruct_at_a_cutoff", "replay_of_a", "current"])
def test_a02_mode_matrix_after_the_full_sequence(mode: str) -> None:
    """The record's mode matrix, asserted: what each mode answers once the
    world holds SYN-G1..SYN-G3 and the SYNTHETIC correction."""
    a, retained_a = view_a_and_retained()
    if mode == "reconstruct_at_a_cutoff":
        again = compose(CUT_A, ACTIONS_ALL, BARS_FULL)
        assert again.result.label == "reconstruction"
        assert again.vintage.source_generation_id == "SYN-G1"
    elif mode == "replay_of_a":
        reopened = reopen_view(retained_a, _replay("SYN-OUT-A"))
        assert reopened.result.label == "replay"
        assert reopened.result.payload == retained_a.payload
    else:
        result = current_read({"bars": BARS_FULL}, _evidence("SYN-G3"))
        assert result.label == "current"
        assert result.evidence["dependency_generation_ids"]["bars"] == "SYN-G3"


# ── A02.02 — the SYNTHETIC correction moves view, vintage and receipt ────────

def _view_b_and_corrected():
    b = compose(CUT_B, (_S1_ROW,), BARS_FULL)
    corrected = compose(CUT_C, ACTIONS_ALL, BARS_FULL)
    return b, corrected


def test_a02_02_synthetic_correction_is_a_new_revision_set_vintage_and_receipt() -> None:
    b, corrected = _view_b_and_corrected()
    assert _close(corrected.view, D1) == Fraction(200, 3)   # the corrected 3/1 ratio
    assert corrected.vintage.revision_set_id != b.vintage.revision_set_id
    assert corrected.vintage != b.vintage
    assert corrected.vintage.source_generation_id == b.vintage.source_generation_id
    retained_b = retain_view(b.view, b.vintage, output_id="SYN-OUT-B")
    retained_c = retain_view(corrected.view, corrected.vintage, output_id="SYN-OUT-B")
    assert retained_c.publishing_receipt_sha256 != retained_b.publishing_receipt_sha256
    assert retained_c.view_digest != retained_b.view_digest


def test_a02_02_old_receipt_cannot_publish_the_corrected_view() -> None:
    b, corrected = _view_b_and_corrected()
    retained_b = retain_view(b.view, b.vintage, output_id="SYN-OUT-B")
    with pytest.raises(ViewRefusal) as raised:
        retain_view(corrected.view, corrected.vintage, output_id="SYN-OUT-B",
                    publishing_receipt_sha256=retained_b.publishing_receipt_sha256)
    assert raised.value.reason is RefusalReason.MIXED_GENERATION


def test_a02_02_every_correction_fixture_is_labelled_synthetic() -> None:
    assert FIXTURE_IDS and all(fid.startswith("SYN-") for fid in FIXTURE_IDS)
    assert PENDING_LEGS and len(PENDING_LEGS) == 4
    # No pending leg claims a correction tested here was natural: any leg that
    # mentions "natural" is itself an UNFINISHED/GAP statement of absence.
    for leg in PENDING_LEGS:
        if "natural" in leg:
            assert leg.startswith(("UNFINISHED:", "GAP:"))
    record = (Path(__file__).resolve().parents[2]
              / "research/data_os_completion/2026-10-13/A02_UPDATE_CORRECTION.md")
    if record.exists():  # asserted on when present; nothing is skipped
        for line in record.read_text(encoding="utf-8").splitlines():
            if "natural" in line:
                low = line.lower()
                assert ("not" in low or "never" in low or "no " in low
                        or "unfinished" in low), line


def test_a02_02_returns_before_and_after_the_correction_differ_only_where_the_factor_moved() -> None:
    b, corrected = _view_b_and_corrected()
    before = simple_returns(b.view)             # 2/1 over SYN-G2 bars
    after = simple_returns(corrected.view)      # 3/1 over the same SYN-G2 bars
    assert before[0] == after[0] == Fraction(1, 100)        # D1->D2, both pre-ex
    assert before[2] == after[2] == Fraction(1, 102)        # D3->D4, both post-ex
    assert before[3] == after[3] == Fraction(1, 103)
    assert before[4] == after[4] == Fraction(1, 52)
    # the one return spanning the ex-date moves: 204/101-1 vs 204/(202/3)-1
    assert before[1] == Fraction(103, 101)
    assert after[1] == Fraction(205, 101)
    assert before[1] != after[1]


# ── A02.03 — a receipt-only generation retires the old current ───────────────

@pytest.mark.parametrize("stale_id", ["SYN-G1", "SYN-G2"])
def test_a02_03_evidence_naming_a_superseded_generation_is_stale(stale_id: str) -> None:
    with pytest.raises(ReadRefusal) as raised:
        current_read({"bars": BARS_FULL}, _evidence(stale_id))
    assert raised.value.code is RefusalCode.STALE_GENERATION


def test_a02_03_receipt_only_generation_is_current_although_the_rows_did_not_move() -> None:
    result = current_read({"bars": BARS_FULL}, _evidence("SYN-G3"))
    assert result.evidence["dependency_generation_ids"]["bars"] == "SYN-G3"
    volatile = ("generation_id", "published_at", "ingested_at")
    stripped = [{k: v for k, v in row.items() if k not in volatile}
                for row in result.values["bars"]]
    expected = [{k: v for k, v in row.items() if k not in volatile}
                for row in _BARS_G2]
    assert stripped == expected


def test_a02_03_pinned_superseded_generation_is_stale_for_current() -> None:
    pinned = replace(BARS_FULL, pinned_generation_id="SYN-G2")
    with pytest.raises(ReadRefusal) as raised:
        current_read({"bars": pinned}, _evidence("SYN-G3"))
    assert raised.value.code is RefusalCode.STALE_GENERATION


def test_a02_dependent_current_evidence_naming_the_pre_correction_actions_generation_is_stale() -> None:
    with pytest.raises(ReadRefusal) as raised:
        current_read({"actions": ACTIONS_LEDGER}, _evidence("SYN-AG1"))
    assert raised.value.code is RefusalCode.STALE_GENERATION


# ── retained A still refuses bad material after the full sequence ────────────

@pytest.mark.parametrize("case", ["tampered", "missing", "wrong_id"])
def test_a02_retained_a_still_refuses_tampered_or_missing_material(case: str) -> None:
    _, retained_a = view_a_and_retained()
    compose(CUT_C, ACTIONS_ALL, BARS_FULL)      # the correction world exists
    if case == "tampered":
        payload = retained_a.payload
        tampered = payload[:-1] + bytes([payload[-1] ^ 0x01])
        with pytest.raises(ReadRefusal) as raised:
            reopen_view(replace(retained_a, payload=tampered), _replay("SYN-OUT-A"))
        assert raised.value.code is RefusalCode.RETAINED_DIGEST_MISMATCH
    elif case == "missing":
        with pytest.raises(ReadRefusal) as raised:
            reopen_view(replace(retained_a, payload=None), _replay("SYN-OUT-A"))
        assert raised.value.code is RefusalCode.NO_RETAINED_OUTPUT
    else:
        with pytest.raises(ReadRefusal) as raised:
            reopen_view(retained_a, _replay("SYN-OUT-OTHER"))
        assert raised.value.code is RefusalCode.NO_RETAINED_OUTPUT


# ── A02.04 — deterministic: no wall clock, no future event ───────────────────

def test_a02_04_no_wall_clock_and_no_future_event() -> None:
    source = inspect.getsource(sys.modules[__name__])
    forbidden = ("date" + "time.now", "time" + ".time", "date" + ".today",
                 "sleep" + "(")
    assert not any(pattern in source for pattern in forbidden)
    assert INSTANTS and all(instant < datetime(2026, 10, 13, tzinfo=UTC)
                            for instant in INSTANTS)
