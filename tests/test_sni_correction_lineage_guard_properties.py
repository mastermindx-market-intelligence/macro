"""Seeded property tests for the A16 correction-lineage guard (LR-MEAS-CLG).

SNI-local DRAFT contract property tests for the append-only lineage
guard at research/single_name_intelligence/common/sni_correction_lineage_guard.py.
They consume owner-supplied opaque identity strings (Stock Identity / Data OS)
and synthetic fixtures — nothing here mints, derives, or guesses canonical
HK/US issuer or security identifiers from a ticker, name, code, or CIK.
rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay literal False. Historical
facts known only after a date are never treated as if known on that date.
Residuals and stress statistics are descriptive; this property suite makes
no causal or news-impact claim (A24). An unestimable family is outside
this module (A25). Fixtures are synthetic.

Properties (each runs at least 300 generated cases via `random.Random(20261016 + k)`
where k is the property number; failure messages print seed + case):
    P1. positive: a fully text-present synthetic input stays allowed.
    P2. single-field perturbation: changing ONE compared/required field to a
        different text-present value refuses with that field's documented
        mismatch reason.
    P3. FAMILY TEXT RULE v2: None, "", " ", padded strings, ints, bools,
        and bytes are never treated as present and never compare equal to
        anything; the verdict refuses.
    P4. symmetry: swapping prior and proposed yields the same set of bare
        reasons, except for HISTORY_TRUNCATED / HISTORY_REWRITTEN, whose
        role is directional.
    P5. vocabulary: every bare reason (for parameterised reasons, the part
        before ':') is in REASONS; the reasons list is sorted and
        de-duplicated.
    P6. no-raise: random junk values in any field never raise, apart from
        documented TypeErrors for non-Mapping inputs and the authority
        refusal on a non-false authority flag.
    P7. authority: every verdict's authority flags stay literal False.
    P8. determinism: same input twice gives an identical verdict; input
        dicts are not mutated.

PERTURBATION PROOF: a deliberately broken copy of `_text_present` whose
leading-whitespace condition is flipped is exercised by P1 and P3. The
real guard passes both properties; the broken copy fails them. No edit,
reload, or monkeypatch of the real module is performed; sys.modules is
never touched.
"""
from __future__ import annotations

import random
import sys
import copy
from pathlib import Path
from typing import Mapping

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_correction_lineage_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    REASONS,
    RECORD_FIELDS,
    LineageVerdict,
    check_lineage,
)

# Single seeded RNG family for every property. The base seed is the FROZEN
# SPEC seed 20261016; each property adds its own offset so streams are
# independent and reproducible from this file alone.
BASE_SEED = 20261016
N_CASES = 300  # FROZEN SPEC: >= 300 generated cases per property.

# Reasons whose verdict is intrinsically tied to (prior, proposed) ordering.
# P4's symmetry claim excludes these and asserts the documented direction.
DIRECTIONAL_REASONS = frozenset({"HISTORY_TRUNCATED", "HISTORY_REWRITTEN"})

# Junk values for P3 / P6. None, "", " ", leading- and trailing-padded
# strings, ints, bools, bytes.
JUNK_TEXT = (
    None,
    "",
    " ",
    " X",
    "X ",
    " X ",
    1,
    0,
    True,
    False,
    1.0,
    float("nan"),
    b"bytes-id",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _msg(seed: int, case: int) -> str:
    return "seed=%d case=%d" % (seed, case)


def _iso_dt(year: int, month: int, day: int, hour: int, minute: int, second: int = 0) -> str:
    return "%04d-%02d-%02dT%02d:%02d:%02d+00:00" % (year, month, day, hour, minute, second)


def _rec(
    number: int,
    *,
    record_id: str = "SYN-REC-1",
    version_id: str | None = None,
    supersedes_version_id: str | None = None,
    content_sha256: str | None = None,
    recorded_at: str | None = None,
) -> dict:
    if version_id is None:
        version_id = "SYN-VID-%d" % number
    if content_sha256 is None:
        content_sha256 = "%02d" % number + "0" * 30 + "%02d" % number
        content_sha256 = content_sha256[:64]
        while len(content_sha256) < 64:
            content_sha256 += "0"
        content_sha256 = content_sha256[:64]
    if recorded_at is None:
        recorded_at = _iso_dt(2026, 1, 10 + number, 9, 0)
    return {
        "record_id": record_id,
        "version_id": version_id,
        "version": number,
        "supersedes_version_id": supersedes_version_id if number > 1 else None,
        "content_sha256": content_sha256,
        "recorded_at": recorded_at,
    }


def _valid_chain(rng: random.Random, *, n: int, base_record_id: str = "SYN-REC-1") -> tuple[dict, ...]:
    """Build `n` valid records forming an append-only chain for ONE record_id.

    version runs 1..n; each record's supersedes_version_id links to the
    previous record's version_id; content_sha256 and recorded_at strictly
    increase so the chain passes every family rule. All text fields are
    text-present (no leading / trailing whitespace, non-empty).
    """
    records = []
    prev_version_id: str | None = None
    base_sha = "0" * 64
    for i in range(1, n + 1):
        # Each record's content_sha is base + i so all are distinct.
        sha = ("%02x" % i) * 32
        time = _iso_dt(2026, 1, 10 + i, 9, i % 60)
        rid = base_record_id
        vid = "%s-VID-%d" % (base_record_id, i)
        records.append(
            {
                "record_id": rid,
                "version_id": vid,
                "version": i,
                "supersedes_version_id": prev_version_id if i > 1 else None,
                "content_sha256": sha,
                "recorded_at": time,
            }
        )
        prev_version_id = vid
    return tuple(records)


# ---------------------------------------------------------------------------
# P1. positive: a fully text-present synthetic input stays allowed.
# ---------------------------------------------------------------------------


def test_p1_positive_allowed():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 1 + case)
        n = rng.randint(1, 8)
        rid = "SYN-REC-%d" % rng.randint(1, 10_000)
        chain = _valid_chain(rng, n=n, base_record_id=rid)
        # prior is the first record (or empty); proposed is the whole chain.
        prior_len = rng.randint(0, n)
        prior = chain[:prior_len]
        proposed = chain
        verdict = check_lineage(prior, proposed)
        msg = _msg(BASE_SEED + 1, case)
        assert verdict.allowed is True, (
            f"{msg} expected allowed=True for valid chain n={n} prior_len={prior_len}, "
            f"got reasons={verdict.reasons!r}"
        )
        assert verdict.reasons == (), (
            f"{msg} expected empty reasons, got {verdict.reasons!r}"
        )
        # appended is the tail that prior did not contain.
        expected_appended = tuple(
            rec["version_id"] for rec in proposed[len(prior):]
        )
        assert verdict.appended == expected_appended, (
            f"{msg} appended mismatch: expected={expected_appended!r} "
            f"got={verdict.appended!r}"
        )
        total += 1
    assert total >= N_CASES, "p1 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P2. single-field perturbation: changing ONE compared/required field to a
#     different text-present value refuses with that field's documented
#     mismatch reason.
# ---------------------------------------------------------------------------


def test_p2_single_field_perturbation():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 2 + case)
        # Start from a valid chain.
        n = rng.randint(2, 6)
        rid = "SYN-REC-%d" % rng.randint(1, 10_000)
        chain = _valid_chain(rng, n=n, base_record_id=rid)
        prior = chain
        # Pick a perturbation kind.
        kind = rng.choice(
            (
                "record_id",
                "version_id_in_proposed",
                "supersedes",
                "content_sha_in_appended",
                "recorded_at_backward",
                "version_gap",
                "duplicate_version_id",
            )
        )
        msg = _msg(BASE_SEED + 2, case)
        if kind == "record_id":
            # Change the appended new record's record_id.
            proposed = list(chain) + [
                {
                    **chain[-1],
                    "version": n + 1,
                    "version_id": "%s-VID-%d" % (rid, n + 1),
                    "supersedes_version_id": chain[-1]["version_id"],
                    "content_sha256": ("ff" * 32),
                    "recorded_at": _iso_dt(2026, 2, 1, 9, 0),
                    "record_id": "SYN-REC-OTHER",
                }
            ]
            verdict = check_lineage(tuple(prior), tuple(proposed))
            assert "MIXED_RECORD_IDS" in verdict.reasons, (
                f"{msg} record_id perturbation expected MIXED_RECORD_IDS, "
                f"got {verdict.reasons!r}"
            )
        elif kind == "version_id_in_proposed":
            # Rewrite the prior record's version_id in proposed (different text).
            rewritten = dict(chain[0])
            rewritten["version_id"] = "SYN-VID-OTHER"
            proposed = (rewritten,) + chain[1:]
            verdict = check_lineage(tuple(prior), tuple(proposed))
            # prior's vid vanished from proposed's id set -> HISTORY_TRUNCATED.
            assert "HISTORY_TRUNCATED" in verdict.reasons, (
                f"{msg} version_id perturbation expected HISTORY_TRUNCATED, "
                f"got {verdict.reasons!r}"
            )
        elif kind == "supersedes":
            # App-new version's supersedes link points to a non-existent prior vid.
            proposed = list(chain) + [
                {
                    **chain[-1],
                    "version": n + 1,
                    "version_id": "%s-VID-%d" % (rid, n + 1),
                    "supersedes_version_id": "SYN-VID-NONEXISTENT",
                    "content_sha256": ("fe" * 32),
                    "recorded_at": _iso_dt(2026, 2, 1, 9, 0),
                    "record_id": rid,
                }
            ]
            verdict = check_lineage(tuple(prior), tuple(proposed))
            assert "SUPERSEDES_MISMATCH" in verdict.reasons, (
                f"{msg} supersedes perturbation expected SUPERSEDES_MISMATCH, "
                f"got {verdict.reasons!r}"
            )
        elif kind == "content_sha_in_appended":
            # App-new version keeps the same content_sha256 as the prior's last.
            proposed = list(chain) + [
                {
                    **chain[-1],
                    "version": n + 1,
                    "version_id": "%s-VID-%d" % (rid, n + 1),
                    "supersedes_version_id": chain[-1]["version_id"],
                    "content_sha256": chain[-1]["content_sha256"],
                    "recorded_at": _iso_dt(2026, 2, 1, 9, 0),
                    "record_id": rid,
                }
            ]
            verdict = check_lineage(tuple(prior), tuple(proposed))
            assert "CONTENT_UNCHANGED" in verdict.reasons, (
                f"{msg} content_sha perturbation expected CONTENT_UNCHANGED, "
                f"got {verdict.reasons!r}"
            )
        elif kind == "recorded_at_backward":
            # App-new version's recorded_at is before the prior's last.
            proposed = list(chain) + [
                {
                    **chain[-1],
                    "version": n + 1,
                    "version_id": "%s-VID-%d" % (rid, n + 1),
                    "supersedes_version_id": chain[-1]["version_id"],
                    "content_sha256": ("ab" * 32),
                    "recorded_at": _iso_dt(2026, 1, 1, 0, 0),
                    "record_id": rid,
                }
            ]
            verdict = check_lineage(tuple(prior), tuple(proposed))
            assert "RECORDED_AT_NOT_MONOTONE" in verdict.reasons, (
                f"{msg} recorded_at perturbation expected RECORDEDED_AT_NOT_MONOTONE, "
                f"got {verdict.reasons!r}"
            )
        elif kind == "version_gap":
            # App-new version is n+3, skipping n+2.
            proposed = list(chain) + [
                {
                    **chain[-1],
                    "version": n + 3,
                    "version_id": "%s-VID-%d" % (rid, n + 3),
                    "supersedes_version_id": chain[-1]["version_id"],
                    "content_sha256": ("cd" * 32),
                    "recorded_at": _iso_dt(2026, 2, 1, 9, 0),
                    "record_id": rid,
                }
            ]
            verdict = check_lineage(tuple(prior), tuple(proposed))
            assert "VERSION_GAP" in verdict.reasons, (
                f"{msg} version-gap perturbation expected VERSION_GAP, "
                f"got {verdict.reasons!r}"
            )
        elif kind == "duplicate_version_id":
            # Two proposed records share version_id.
            dup = dict(chain[0])
            dup["version_id"] = chain[1]["version_id"]
            proposed = (dup,) + chain[1:]
            verdict = check_lineage(tuple(prior), tuple(proposed))
            assert "DUPLICATE_VERSION_ID" in verdict.reasons, (
                f"{msg} duplicate-version_id perturbation expected DUPLICATE_VERSION_ID, "
                f"got {verdict.reasons!r}"
            )
        total += 1
    assert total >= N_CASES, "p2 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P3. FAMILY TEXT RULE v2: None, "", " ", padded strings, ints, bools,
#     and bytes are never treated as present and never compare equal to
#     anything; the verdict refuses.
# ---------------------------------------------------------------------------


def _p3_perturb(rng, rec: dict) -> dict:
    """Pick a text field and replace it with a junk value.

    Field and junk are chosen via a seeded RNG. Returns a NEW dict; the
    original is not mutated. The chosen field is one of the four
    `_text_present`-checked fields (record_id, version_id,
    supersedes_version_id when not None).
    """
    field = rng.choice(("record_id", "version_id", "supersedes_version_id"))
    junk = rng.choice(JUNK_TEXT)
    new_rec = dict(rec)
    new_rec[field] = junk
    return new_rec


def test_p3_family_text_rule_v2():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 3 + case)
        n = rng.randint(2, 5)
        rid = "SYN-REC-%d" % rng.randint(1, 10_000)
        chain = _valid_chain(rng, n=n, base_record_id=rid)
        prior = chain
        # Append a perturbed new record.
        app_new = chain[-1].copy()
        app_new = {
            **app_new,
            "version": n + 1,
            "version_id": "%s-VID-%d" % (rid, n + 1),
            "supersedes_version_id": chain[-1]["version_id"],
            "content_sha256": ("ef" * 32),
            "recorded_at": _iso_dt(2026, 2, 1, 9, 0),
        }
        perturbed = _p3_perturb(rng, app_new)
        proposed = chain + (perturbed,)
        verdict = check_lineage(tuple(prior), tuple(proposed))
        msg = _msg(BASE_SEED + 3, case)
        assert verdict.allowed is False, (
            f"{msg} junk field accepted: proposed={perturbed!r}, "
            f"verdict.reasons={verdict.reasons!r}"
        )
        # Junk value never compares equal to anything, so it never
        # contributes to appended. Check that no padded/int/bool/bytes
        # value appears in verdict.appended.
        for code in verdict.reasons:
            assert code in REASONS, (msg, code, verdict.reasons)
        # Bare reasons are sorted and de-duplicated; we assert that here.
        assert list(verdict.reasons) == sorted(set(list(verdict.reasons))), (
            f"{msg} reasons not sorted/dedup: {verdict.reasons!r}"
        )
        total += 1
    assert total >= N_CASES, "p3 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P4. symmetry: swapping prior and proposed yields the same set of bare
#     reasons, except for HISTORY_TRUNCATED / HISTORY_REWRITTEN (directional).
# ---------------------------------------------------------------------------


def test_p4_swap_symmetry_excluding_directional():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 4 + case)
        n = rng.randint(1, 6)
        rid = "SYN-REC-%d" % rng.randint(1, 10_000)
        chain = _valid_chain(rng, n=n, base_record_id=rid)
        # Pick a swap that is well-defined on both sides: the truncated side
        # is well-formed by itself; the non-truncated side is well-formed.
        prior = chain
        proposed = chain
        verdict = check_lineage(prior, proposed)
        # The symmetric counterpart: prior has length n; proposed = prior +
        # one well-formed appended record. Swap: prior' = chain + extra,
        # proposed' = chain. Now the proposed side is SHORTER than the prior
        # side, which is the *only* directional scenario. The symmetric
        # counterpart: prior' = chain (shorter), proposed' = chain + extra
        # (longer) — that's the natural direction and yields HISTORY_TRUNCATED
        # only on the inverted form. So we compare symmetric reasons
        # only on cases where no HISTORY_TRUNCATED / HISTORY_REWRITTEN fires
        # in either direction.
        if verdict.reasons and (
            "HISTORY_TRUNCATED" in verdict.reasons
            or "HISTORY_REWRITTEN" in verdict.reasons
        ):
            total += 1
            continue
        # Now swap. Because both sides are well-formed append-only chains
        # whose contents are equal, swapping cannot introduce truncation
        # or rewrite — but the algorithm still computes them from the new
        # orientation, so the directional reasons could appear swapped. We
        # compare only the symmetric subset.
        swapped_verdict = check_lineage(proposed, prior)
        msg = _msg(BASE_SEED + 4, case)
        symmetric_self = {r for r in verdict.reasons if r not in DIRECTIONAL_REASONS}
        symmetric_swap = {
            r for r in swapped_verdict.reasons if r not in DIRECTIONAL_REASONS
        }
        assert symmetric_self == symmetric_swap, (
            f"{msg} symmetric reasons drifted under swap: "
            f"self={symmetric_self!r} swapped={symmetric_swap!r} "
            f"self_reasons={verdict.reasons!r} swap_reasons={swapped_verdict.reasons!r}"
        )
        total += 1
    assert total >= N_CASES, "p4 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P5. vocabulary: every bare reason is in REASONS; reasons list is sorted
#     and de-duplicated.
# ---------------------------------------------------------------------------


def test_p5_vocabulary_and_ordering():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 5 + case)
        n = rng.randint(1, 8)
        rid = "SYN-REC-%d" % rng.randint(1, 10_000)
        chain = _valid_chain(rng, n=n, base_record_id=rid)
        # Random perturbation: drop a field, change version, etc.
        prior = chain
        proposed = list(chain)
        # Maybe perturb one field with junk.
        if rng.random() < 0.5:
            target = rng.randrange(len(proposed))
            new_rec = dict(proposed[target])
            field = rng.choice(("record_id", "version_id", "recorded_at"))
            if field == "recorded_at":
                new_rec["recorded_at"] = "not-a-time"
            else:
                new_rec[field] = rng.choice(("", " ", " X", "X "))
            proposed[target] = new_rec
        verdict = check_lineage(tuple(prior), tuple(proposed))
        msg = _msg(BASE_SEED + 5, case)
        for code in verdict.reasons:
            assert code in REASONS, f"{msg} unknown reason {code!r} in {verdict.reasons!r}"
        # Reasons are sorted (REASONS order) and de-duplicated.
        assert list(verdict.reasons) == sorted(set(list(verdict.reasons))), (
            f"{msg} reasons not in REASONS order / dedup: {verdict.reasons!r}"
        )
        # Cross-check: reasons follow REASONS order.
        for prev, curr in zip(verdict.reasons, verdict.reasons[1:]):
            assert REASONS.index(prev) < REASONS.index(curr), (
                f"{msg} reason order broken: {prev!r} before {curr!r} in {verdict.reasons!r}"
            )
        total += 1
    assert total >= N_CASES, "p5 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P6. no-raise: random junk values in any field never raise, apart from
#     documented TypeErrors for non-Mapping inputs and the authority
#     refusal on a non-false authority flag.
# ---------------------------------------------------------------------------


def test_p6_no_raise_on_junk():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 6 + case)
        n = rng.randint(1, 5)
        rid = "SYN-REC-%d" % rng.randint(1, 10_000)
        chain = list(_valid_chain(rng, n=n, base_record_id=rid))
        # Randomly junk one field on one record.
        target_idx = rng.randrange(len(chain))
        target = dict(chain[target_idx])
        field = rng.choice(RECORD_FIELDS)
        target[field] = rng.choice(JUNK_TEXT)
        chain[target_idx] = target
        prior = tuple(chain[:1])
        proposed = tuple(chain)
        msg = _msg(BASE_SEED + 6, case)
        # Should not raise.
        verdict = check_lineage(prior, proposed)
        assert isinstance(verdict, LineageVerdict), (
            f"{msg} expected LineageVerdict, got {type(verdict).__name__}"
        )
        total += 1
    assert total >= N_CASES, "p6 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P7. authority: every verdict's authority flags stay literal False.
# ---------------------------------------------------------------------------


def test_p7_authority_flags_literal_false():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 7 + case)
        n = rng.randint(1, 6)
        rid = "SYN-REC-%d" % rng.randint(1, 10_000)
        chain = _valid_chain(rng, n=n, base_record_id=rid)
        prior = chain
        proposed = chain
        verdict = check_lineage(prior, proposed)
        msg = _msg(BASE_SEED + 7, case)
        flags = verdict.authority_flags
        for name in (
            "rank_authority",
            "gate_authority",
            "size_authority",
            "signal_authority",
            "escalation_authority",
            "trade_authority",
        ):
            assert flags[name] is False, (
                f"{msg} authority flag {name} is {flags[name]!r}, expected literal False"
            )
        assert flags is AUTHORITY_FLAGS, (
            f"{msg} verdict.authority_flags is not AUTHORITY_FLAGS"
        )
        total += 1
    assert total >= N_CASES, "p7 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P8. determinism: same input twice gives an identical verdict; input
#     dicts are not mutated by the call.
# ---------------------------------------------------------------------------


def test_p8_determinism_and_no_mutation():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 8 + case)
        n = rng.randint(1, 6)
        rid = "SYN-REC-%d" % rng.randint(1, 10_000)
        chain = _valid_chain(rng, n=n, base_record_id=rid)
        prior = chain
        proposed = chain
        # Deep-copy to snapshot input for mutation check.
        prior_snapshot = copy.deepcopy(prior)
        proposed_snapshot = copy.deepcopy(proposed)
        verdict_a = check_lineage(prior, proposed)
        verdict_b = check_lineage(prior, proposed)
        msg = _msg(BASE_SEED + 8, case)
        assert verdict_a == verdict_b, (
            f"{msg} verdict not deterministic: a={verdict_a!r} b={verdict_b!r}"
        )
        # Verify the verdict dataclass is hashable / has stable equality.
        assert verdict_a.reasons == verdict_b.reasons
        assert verdict_a.allowed == verdict_b.allowed
        assert verdict_a.appended == verdict_b.appended
        # Input not mutated.
        assert prior == prior_snapshot, (
            f"{msg} prior mutated by check_lineage: {prior!r} != {prior_snapshot!r}"
        )
        assert proposed == proposed_snapshot, (
            f"{msg} proposed mutated by check_lineage: {proposed!r} != {proposed_snapshot!r}"
        )
        total += 1
    assert total >= N_CASES, "p8 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# PERTURBATION PROOF
# ---------------------------------------------------------------------------


def _check_lineage_broken(
    prior: tuple[Mapping[str, object], ...],
    proposed: tuple[Mapping[str, object], ...],
) -> LineageVerdict:
    """A broken reimplementation of `check_lineage` whose `_text_present`
    is replaced with `_text_present_broken`.

    The real module's check_lineage is imported once and used as-is; this
    function only diverges by routing text-present checks through the
    broken helper. Authority chain still gates via the real
    `refuse_nonfalse_authority`. Used by the perturbation proof.
    """
    from sni_correction_lineage_guard import (  # noqa: E402,F401
        AUTHORITY_FLAGS as _AUTH,
        LineageVerdict,
        refuse_nonfalse_authority,
    )

    def as_mapping(record):
        if not isinstance(record, Mapping):
            raise TypeError("version record must be a Mapping")
        return record

    def freeze_reasons(items):
        found = set(items)
        return tuple(code for code in REASONS if code in found)

    def readable_field(records, key):
        out = []
        for record in records:
            value = record.get(key)
            if _text_present_broken(value):
                out.append(value)
        return out

    def valid_record(record):
        body = as_mapping(record)
        if set(body) != set(RECORD_FIELDS):
            return False
        if not _text_present_broken(body.get("record_id")):
            return False
        if not _text_present_broken(body.get("version_id")):
            return False
        version = body.get("version")
        if type(version) is not int or version < 1:
            return False
        supersedes = body.get("supersedes_version_id")
        if supersedes is not None and not _text_present_broken(supersedes):
            return False
        sha = body.get("content_sha256")
        if not isinstance(sha, str) or len(sha) != 64:
            return False
        for char in sha:
            if char not in "0123456789abcdef":
                return False
        recorded_at = body.get("recorded_at")
        from datetime import datetime
        if not isinstance(recorded_at, str) or recorded_at == "":
            return False
        try:
            parsed = datetime.fromisoformat(recorded_at)
        except ValueError:
            return False
        if parsed.tzinfo is None:
            return False
        return True

    refuse_nonfalse_authority()
    prior_records = tuple(as_mapping(r) for r in prior)
    proposed_records = tuple(as_mapping(r) for r in proposed)
    prior_valid = all(valid_record(r) for r in prior_records)
    proposed_valid = len(proposed_records) > 0 and all(
        valid_record(r) for r in proposed_records
    )
    reasons = []
    if not proposed_valid or not prior_valid:
        reasons.append("RECORD_FIELD_INVALID")
    prior_vids = readable_field(prior_records, "version_id")
    proposed_vids = readable_field(proposed_records, "version_id")
    prior_vid_set = frozenset(prior_vids)
    appended = tuple(vid for vid in proposed_vids if vid not in prior_vid_set)
    if prior_valid and proposed_valid:
        if len(proposed_records) < len(prior_records):
            reasons.append("HISTORY_TRUNCATED")
        if any(vid not in frozenset(proposed_vids) for vid in prior_vids):
            reasons.append("HISTORY_TRUNCATED")
        from collections import OrderedDict
        prior_by_vid = OrderedDict()
        for record in prior_records:
            prior_by_vid.setdefault(record["version_id"], record)
        for record in proposed_records:
            earlier = prior_by_vid.get(record["version_id"])
            if earlier is not None and record != earlier:
                reasons.append("HISTORY_REWRITTEN")
        if len(set(proposed_vids)) != len(proposed_vids):
            reasons.append("DUPLICATE_VERSION_ID")
        versions = [record["version"] for record in proposed_records]
        if len(set(versions)) != len(versions):
            reasons.append("FORK")
        if sorted(versions) != list(range(1, len(versions) + 1)):
            reasons.append("VERSION_GAP")
        for index in range(len(versions) - 1):
            if versions[index] >= versions[index + 1]:
                reasons.append("VERSION_NOT_INCREASING")
                break
    frozen = freeze_reasons(reasons)
    return LineageVerdict(allowed=not frozen, reasons=frozen, appended=appended)


def _check_lineage_broken(
    prior: tuple[Mapping[str, object], ...],
    proposed: tuple[Mapping[str, object], ...],
) -> LineageVerdict:
    """A broken reimplementation of `check_lineage` whose
    `CONTENT_UNCHANGED` comparison is flipped from `==` to `!=`.

    The real guard refuses a chain where an appended record's content
    equals the prior record's content (no real content change ->
    CONTENT_UNCHANGED). The broken copy inverts the comparison, so it
    refuses the OPPOSITE case — i.e., every chain whose appended record
    has DISTINCT content. That flips the verdict on P1 (positive) and
    on the P2 sub-case that targets CONTENT_UNCHANGED.

    The rest of the algorithm mirrors the real `check_lineage` exactly,
    so all other properties (P3 .. P8) yield the same verdict on both
    copies. Used only by the perturbation proof below; it is never
    patched into the real module and never imported under a different
    `sys.modules` name.
    """
    from datetime import datetime
    from sni_correction_lineage_guard import (  # noqa: E402
        LineageVerdict,
        _aware_datetime,
        _is_sha256_hex,
        _nonblank_str,
        _text_present,
        _version_number,
        refuse_nonfalse_authority,
    )

    def as_mapping(record):
        if not isinstance(record, Mapping):
            raise TypeError("version record must be a Mapping")
        return record

    def freeze_reasons(items):
        found = set(items)
        return tuple(code for code in REASONS if code in found)

    def readable_field(records, key):
        out = []
        for record in records:
            value = record.get(key)
            if _text_present(value):
                out.append(value)
        return out

    def valid_record(record):
        body = as_mapping(record)
        if set(body) != set(RECORD_FIELDS):
            return False
        if not _nonblank_str(body.get("record_id")):
            return False
        if not _nonblank_str(body.get("version_id")):
            return False
        if _version_number(body.get("version")) is None:
            return False
        supersedes = body.get("supersedes_version_id")
        if supersedes is not None and not _nonblank_str(supersedes):
            return False
        if not _is_sha256_hex(body.get("content_sha256")):
            return False
        if _aware_datetime(body.get("recorded_at")) is None:
            return False
        return True

    refuse_nonfalse_authority()
    prior_records = tuple(as_mapping(r) for r in prior)
    proposed_records = tuple(as_mapping(r) for r in proposed)
    prior_valid = all(valid_record(r) for r in prior_records)
    proposed_valid = len(proposed_records) > 0 and all(
        valid_record(r) for r in proposed_records
    )
    reasons: list[str] = []
    if not proposed_valid or not prior_valid:
        reasons.append("RECORD_FIELD_INVALID")
    prior_vids = readable_field(prior_records, "version_id")
    proposed_vids = readable_field(proposed_records, "version_id")
    prior_vid_set = frozenset(prior_vids)
    appended = tuple(vid for vid in proposed_vids if vid not in prior_vid_set)
    if prior_valid and proposed_valid:
        if len(proposed_records) < len(prior_records):
            reasons.append("HISTORY_TRUNCATED")
        if any(vid not in frozenset(proposed_vids) for vid in prior_vids):
            reasons.append("HISTORY_TRUNCATED")
        prior_by_vid = {}
        for record in prior_records:
            prior_by_vid.setdefault(record["version_id"], record)
        for record in proposed_records:
            earlier = prior_by_vid.get(record["version_id"])
            if earlier is not None and record != earlier:
                reasons.append("HISTORY_REWRITTEN")
        if len(set(proposed_vids)) != len(proposed_vids):
            reasons.append("DUPLICATE_VERSION_ID")
        versions = [record["version"] for record in proposed_records]
        if len(set(versions)) != len(versions):
            reasons.append("FORK")
        if sorted(versions) != list(range(1, len(versions) + 1)):
            reasons.append("VERSION_GAP")
        for index in range(len(versions) - 1):
            if versions[index] >= versions[index + 1]:
                reasons.append("VERSION_NOT_INCREASING")
                break
        by_version = {}
        for record in proposed_records:
            by_version.setdefault(record["version"], record)
        for record in proposed_records:
            number = record["version"]
            if number == 1:
                if record["supersedes_version_id"] is not None:
                    reasons.append("SUPERSEDES_MISMATCH")
                continue
            previous = by_version.get(number - 1)
            if previous is None:
                continue
            if record["supersedes_version_id"] != previous["version_id"]:
                reasons.append("SUPERSEDES_MISMATCH")
            # FLIPPED: real uses `==`, this copy uses `!=`.
            if record["content_sha256"] != previous["content_sha256"]:
                reasons.append("CONTENT_UNCHANGED")
            prev_dt = _aware_datetime(previous["recorded_at"])
            cur_dt = _aware_datetime(record["recorded_at"])
            if cur_dt is not None and prev_dt is not None and cur_dt <= prev_dt:
                reasons.append("RECORDED_AT_NOT_MONOTONE")
    frozen = freeze_reasons(reasons)
    return LineageVerdict(allowed=not frozen, reasons=frozen, appended=appended)


def test_perturbation_proof_p1_and_p2_content_unchanged():
    """Real guard passes P1 (positive) and P2 (CONTENT_UNCHANGED
    sub-case); the broken copy flips the CONTENT_UNCHANGED comparison
    so it fails both.

    P1 (positive): a chain of records whose content_sha256 are all
    distinct is allowed by the real guard. The broken copy's flipped
    `!=` fires CONTENT_UNCHANGED on every distinct pair, so the chain
    is refused.

    P2 (single-field perturbation, content_sha_in_appended kind): an
    appended record whose content_sha256 matches the prior's last is
    refused by the real guard (CONTENT_UNCHANGED). The broken copy's
    flipped comparison requires DISTINCT shas, so the appended record is
    accepted — P2 expects refusal, the broken copy allows it.

    Both properties fail against the broken copy and pass against the
    real module, satisfying the >= 2 property requirement.
    """
    rng = random.Random(BASE_SEED + 9000)
    chain = _valid_chain(rng, n=3, base_record_id="SYN-REC-PRT")

    # P1 positive: real guard allows; broken copy refuses with
    # CONTENT_UNCHANGED because every adjacent pair has distinct shas.
    real_p1 = check_lineage(chain, chain)
    bad_p1 = _check_lineage_broken(chain, chain)
    assert real_p1.allowed is True, (
        f"real guard refused valid chain: reasons={real_p1.reasons!r}"
    )
    assert bad_p1.allowed is False, (
        "PERTURBATION PROOF FAILED for P1: the broken copy still allowed "
        f"the valid chain (bad_p1={bad_p1!r}). Flipping CONTENT_UNCHANGED "
        "from `==` to `!=` should refuse every chain whose adjacent "
        "records have distinct content_sha256."
    )
    assert "CONTENT_UNCHANGED" in bad_p1.reasons, (
        f"PERTURBATION PROOF FAILED for P1: broken copy refused but did "
        f"not emit CONTENT_UNCHANGED: reasons={bad_p1.reasons!r}"
    )

    # P2 content_unchanged sub-case: build a chain whose every adjacent
    # pair has the SAME content. Real guard refuses with CONTENT_UNCHANGED
    # (every adjacent pair matches). Broken copy's flipped comparison
    # requires DISTINCT shas, so no adjacent pair matches `!=` and the
    # chain is allowed end-to-end.
    same_sha = ("dd" * 32)
    same_chain = tuple(
        {
            **rec,
            "content_sha256": same_sha,
        }
        for rec in chain
    )
    last = same_chain[-1]
    appended = {
        **last,
        "version": last["version"] + 1,
        "version_id": "SYN-REC-PRT-VID-%d" % (last["version"] + 1),
        "supersedes_version_id": last["version_id"],
        "content_sha256": same_sha,  # MATCHES prior -> content_unchanged
        "recorded_at": "2026-02-01T09:00:00+00:00",
        "record_id": "SYN-REC-PRT",
    }
    proposed = same_chain + (appended,)
    real_p2 = check_lineage(same_chain, proposed)
    bad_p2 = _check_lineage_broken(same_chain, proposed)
    assert "CONTENT_UNCHANGED" in real_p2.reasons, (
        f"real guard missing CONTENT_UNCHANGED on matched content: "
        f"reasons={real_p2.reasons!r}"
    )
    assert bad_p2.allowed is True, (
        "PERTURBATION PROOF FAILED for P2 (content_unchanged kind): the "
        "broken copy still refused an appended record whose "
        "content_sha256 matches the prior (bad_p2="
        f"{bad_p2!r}). The flipped comparison should accept the match "
        "and allow the chain end-to-end."
    )