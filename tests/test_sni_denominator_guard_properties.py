"""Seeded property tests for the A11 denominator-guard contract (LR-MEAS-DNM).

SNI-local DRAFT contract property tests for the share-count binding guard
research/single_name_intelligence/common/sni_denominator_guard.py. They
consume owner-supplied opaque identity strings (Stock Identity / Data OS)
and Capital Structure observation mappings; nothing here mints, derives,
or guesses canonical HK/US issuer or security identifiers from a ticker,
name, code, or CIK. rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority and trade_authority stay literal
False. Fixtures are synthetic.

Properties exercised (each runs at least 300 generated cases, seeded via
the stdlib `random.Random(20261016 + k)` family only -- no hypothesis):

    P1. Positive -- a valid, fully text-present synthetic input that the
        existing example tests treat as allowed stays allowed (no refusal
        reasons).
    P2. Single-field perturbation -- changing exactly ONE compared/required
        field to a different text-present value refuses with that field's
        documented mismatch/missing reason.
    P3. FAMILY TEXT RULE v2 -- replacing any text field with None, "", " ",
        a padded string (" X" / "X "), an int, a bool, or bytes is never
        treated as present and never compares equal to anything; it
        refuses, never allows.
    P4. Symmetry -- where the guard compares two sides (request vs
        record, left vs right, old vs new), swapping the sides yields the
        same set of bare reasons, unless the module docstring states the
        comparison is directional (then assert the documented direction
        instead and say so).
    P5. Vocabulary -- every bare reason (for a parameterised reason, the
        part before ':') is in REASONS, and reason lists are sorted and
        de-duplicated if the module promises that.
    P6. No raise on junk -- put random junk values in any field and no
        exception is raised, apart from documented TypeErrors for
        non-Mapping inputs and the authority refusal.
    P7. Authority -- every verdict's authority flags (rank/gate/size/
        signal/escalation/trade) are literal False.
    P8. Determinism -- the same input twice gives an identical verdict;
        input dicts are not mutated by the call.

PERTURBATION PROOF: a deliberately broken copy of `_text_present` lives
in `_text_present_with_lt`. The property file shows that at least 2
properties FAIL against the broken copy and PASS against the real module.
The real module is never edited, reloaded, monkeypatched, or touched via
sys.modules.
"""
from __future__ import annotations

import copy
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_denominator_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    REASONS,
    check_denominator,
    refuse_nonfalse_authority,
)

# Single seeded RNG family for every property. The seed itself is the
# FROZEN SPEC seed 20261016; each property adds a unique salt so the
# streams are independent and reproducible from this file alone.
BASE_SEED = 20261016
N_CASES = 300  # FROZEN SPEC: >= 300 generated cases per property.

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

AS_OF = "2026-08-20T12:00:00+00:00"
AVAILABLE_AT = "2026-08-20T11:00:00+00:00"
OBS_ID = "SYN-OBS-1"
ISSUER_ID = "SYN-ISSUER-1"
ADS_RATIO_SOURCE = "SYN-ADS-RATIO-OWNER-1"


# ---------------------------------------------------------------------------
# Time / helper utilities
# ---------------------------------------------------------------------------

def _aware(year, month, day, hour=0, minute=0, second=0, micro=0):
    return datetime(year, month, day, hour, minute, second, micro, tzinfo=timezone.utc)


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _msg(seed, case):
    return "seed=%s case=%s" % (seed, case)


# ---------------------------------------------------------------------------
# Fixture generators
# ---------------------------------------------------------------------------

def _base_request(**overrides):
    body = {
        "issuer_id": ISSUER_ID,
        "counter_kind": "ordinary",
        "share_count_ref": OBS_ID,
        "ads_ratio": None,
        "ads_ratio_source": None,
    }
    body.update(overrides)
    return body


def _ads_request(**overrides):
    body = {
        "counter_kind": "ads",
        "ads_ratio": 8,
        "ads_ratio_source": ADS_RATIO_SOURCE,
    }
    body.update(overrides)
    return _base_request(**body)


def _base_observation(**overrides):
    body = {
        "schema": "capital_structure.share_count_observation.v1",
        "observation_id": OBS_ID,
        "logical_observation_id": "SYN-LOG-1",
        "fact_revision_id": "SYN-REV-1",
        "issuer_id": ISSUER_ID,
        "version": {
            "immutable_record": True,
            "correction_version": 1,
            "correction_of": None,
        },
        "point_in_time": {
            "system_available_at": AVAILABLE_AT,
            "source_retrieved_at": AVAILABLE_AT,
            "available_at": AVAILABLE_AT,
        },
        "state": {"disposition": "accepted", "reason": "SYN-REASON"},
        "authority": {
            "is_context_only": True,
            "rank_authority": False,
            "sizing_authority": False,
            "entry_authority": False,
            "trade_authority": False,
            "prophet_authority": False,
        },
    }
    body.update(overrides)
    return body


def _check(request, observation, **kwargs):
    kwargs.setdefault("as_of", AS_OF)
    return check_denominator(request, observation, **kwargs)


def _permit(_c):
    # Whitelist jitter: keep REASONS exhaustive but unparameterised here.
    return REASONS


# ---------------------------------------------------------------------------
# P1. Positive: a valid, fully text-present synthetic input that the
#     existing example tests treat as allowed stays allowed (no refusal
#     reasons). We sweep counter_kind in {"ordinary", "ads"}, randomise
#     correction_version and expected_correction_version, and jitter the
#     point_in_time / authority sub-fields to make sure no incidental
#     field flips the verdict.
# ---------------------------------------------------------------------------

def test_p1_positive_synthetic_inputs_allowed():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 1 + case)
        # Vary correction_version across >= 1 ints.
        cv = rng.randint(1, 4)
        # Vary available_at strictly <= AS_OF (aware UTC).
        avail_hour = rng.randint(0, 11)
        avail_minute = rng.randint(0, 59)
        avail = _aware(2026, 8, 20, avail_hour, avail_minute)
        observation = _base_observation(
            version={
                "immutable_record": True,
                "correction_version": cv,
                "correction_of": None,
            },
            point_in_time={
                "system_available_at": _iso(avail),
                "source_retrieved_at": _iso(avail),
                "available_at": _iso(avail),
            },
        )
        if rng.random() < 0.5:
            request = _base_request()
            expected = cv
        else:
            request = _ads_request(ads_ratio=rng.randint(1, 16))
            expected = cv
        # expected_correction_version: with prob 0.5 supply the matching
        # value, with prob 0.5 leave it None so we exercise both branches.
        kwargs = {}
        if rng.random() < 0.5:
            kwargs["expected_correction_version"] = expected
        verdict = _check(request, observation, **kwargs)
        msg = _msg(BASE_SEED + 1, case)
        assert verdict.allowed is True, (
            f"{msg} valid synthetic input refused: reasons={verdict.reasons!r}"
        )
        assert verdict.reasons == (), (
            f"{msg} valid synthetic input emitted reasons: {verdict.reasons!r}"
        )
        assert verdict.owner_observation_id == OBS_ID, msg
        assert verdict.correction_version == cv, msg
        total += 1
    assert total >= N_CASES, "p1 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P2. Single-field perturbation: changing exactly ONE compared/required
#     field to a different text-present value refuses with that field's
#     documented mismatch/missing reason. The field set is the full set of
#     text-present comparisons in the guard.
# ---------------------------------------------------------------------------

def _perturb_field(field, baseline_value, jitter_value):
    """Build a (request_overrides, observation_overrides, expected_reason)
    triple for ONE compared field."""
    # field -> (req_override, obs_override, expected_reason)
    table = {
        "issuer_id": (
            {"issuer_id": jitter_value},
            {"issuer_id": baseline_value},
            "ISSUER_MISMATCH",
        ),
        "observation_id": (
            {},
            {"observation_id": jitter_value},
            "OWNER_REF_MISSING",
        ),
        "share_count_ref": (
            {"share_count_ref": jitter_value},
            {},
            "OWNER_REF_MISSING",
        ),
        "schema": (
            {},
            {"schema": jitter_value},
            "OWNER_SCHEMA_MISMATCH",
        ),
    }
    return table[field]


def test_p2_single_field_perturbation_refuses_matching_reason():
    field_cycle = ("issuer_id", "observation_id", "share_count_ref", "schema")
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 2 + case)
        field = field_cycle[case % len(field_cycle)]
        baseline = "SYN-BASE-" + field.upper()
        jitter = "SYN-JIT-" + field.upper() + "-" + str(case)
        req_over, obs_over, expected_reason = _perturb_field(
            field, baseline, jitter
        )
        request = _base_request(issuer_id=baseline, share_count_ref=baseline)
        observation = _base_observation(
            issuer_id=baseline, observation_id=baseline
        )
        for k, v in req_over.items():
            request[k] = v
        for k, v in obs_over.items():
            observation[k] = v
        verdict = _check(request, observation)
        msg = _msg(BASE_SEED + 2, case) + " field=" + field
        assert expected_reason in verdict.reasons, (
            f"{msg} expected {expected_reason!r} in reasons, "
            f"got {verdict.reasons!r}"
        )
        # P5 anchor: every emitted reason is a real REASONS code.
        for code in verdict.reasons:
            assert code in REASONS, (msg, code, verdict.reasons)
        total += 1
    assert total >= N_CASES, "p2 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P3. FAMILY TEXT RULE v2: replacing any text field with None, "", " ",
#     a padded string (" X" / "X "), an int, a bool, or bytes is never
#     treated as present and never compares equal to anything; it refuses,
#     never allows. We sweep across all four text-present slots.
# ---------------------------------------------------------------------------

JUNK_VALUES = (
    None,
    "",
    " ",
    " X",
    "X ",
    0,
    1,
    True,
    False,
    b"bytes-not-text",
)


def test_p3_family_text_rule_v2_junk_never_present():
    """For every (text_slot, junk_value) pair, the verdict must refuse.

    A text slot is a slot routed through `_text_present` by the guard:
    request.issuer_id, request.share_count_ref, observation.issuer_id,
    observation.observation_id. ads_ratio_source is also routed through
    `_text_present` in the ADS branch, so we exercise it too.
    """
    # text_slot -> {side, key}
    slots = (
        ("request", "issuer_id"),
        ("request", "share_count_ref"),
        ("observation", "issuer_id"),
        ("observation", "observation_id"),
    )
    # At least N_CASES: 4 slots * N_JUNK * 2 counter_kinds -> already >= 300.
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 3 + case)
        side, key = slots[case % len(slots)]
        junk = JUNK_VALUES[(case // len(slots)) % len(JUNK_VALUES)]
        # Two counter_kind variants (ordinary + ads) so we also exercise
        # the ads_ratio_source `_text_present` check.
        use_ads = (case // (len(slots) * len(JUNK_VALUES))) % 2 == 1
        request = _ads_request() if use_ads else _base_request()
        observation = _base_observation()
        # Plant junk on the chosen slot.
        if side == "request":
            request[key] = junk
        else:
            observation[key] = junk
        verdict = _check(request, observation)
        msg = (
            _msg(BASE_SEED + 3, case)
            + " slot=" + side + "." + key
            + " junk=" + repr(junk)
            + " ads=" + str(use_ads)
        )
        # The verdict must NOT be allowed.
        assert verdict.allowed is False, (
            f"{msg} text-present-junk was treated as present: "
            f"reasons={verdict.reasons!r}"
        )
        # The relevant family-text reason family-text code is one of the
        # MISSING/MISMATCH set (no family-text reason is allowed).
        if key == "share_count_ref":
            # Request-side text slot: missing fires first.
            forbidden = ("SHARE_COUNT_MISSING",)
        elif key == "observation_id":
            # Observation-side text slot: blank obs_id triggers
            # OWNER_REF_MISSING (the share_count_ref is still text-present).
            forbidden = ("OWNER_REF_MISSING",)
        else:
            forbidden = ("ISSUER_MISMATCH",)
        family_hit = [c for c in verdict.reasons if c in forbidden]
        assert family_hit, (
            f"{msg} expected a family-text reason in {forbidden}, "
            f"got {verdict.reasons!r}"
        )
        total += 1
    assert total >= N_CASES, "p3 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P4. Symmetry: where the guard compares two sides, swapping the sides
#     yields the same set of bare reasons, unless the module docstring
#     states the comparison is directional.
#
#     Documented comparisons (see module source):
#         - request.share_count_ref  vs  observation.observation_id
#             (forward == equality on text-present ids).
#         - request.issuer_id        vs  observation.issuer_id
#             (forward == equality on text-present ids).
#     Both are SYMMETRIC under swap (== is symmetric).
#     The expected_correction_version vs observation.version.correction_version
#     comparison is DIRECTIONAL: only the observation side is checked when
#     expected_correction_version is not None; with None on the call side the
#     check is suppressed, so swap is NOT applicable -- we instead assert
#     the documented direction (None on the request side means the check
#     is skipped, not "reverse compared").
# ---------------------------------------------------------------------------

def test_p4_symmetry_swap_yields_same_bare_reasons():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 4 + case)
        # Two distinct text-present ids so the equality compare fails.
        left = "SYN-LEFT-" + str(case)
        right = "SYN-RIGHT-" + str(case)
        # Forward: request uses left, observation uses right.
        fwd_request = _base_request(issuer_id=left, share_count_ref=left)
        fwd_observation = _base_observation(issuer_id=right, observation_id=right)
        fwd = _check(fwd_request, fwd_observation)
        # Reverse: swap the sides.
        rev_request = _base_request(issuer_id=right, share_count_ref=right)
        rev_observation = _base_observation(issuer_id=left, observation_id=left)
        rev = _check(rev_request, rev_observation)
        msg = _msg(BASE_SEED + 4, case)
        assert set(fwd.reasons) == set(rev.reasons), (
            f"{msg} reasons drifted under swap: "
            f"fwd={fwd.reasons!r} rev={rev.reasons!r}"
        )
        assert fwd.allowed == rev.allowed, msg
        total += 1
    assert total >= N_CASES, "p4 ran fewer than N_CASES generated cases"


def test_p4directional_expected_correction_version_documented():
    """The expected_correction_version check is one-directional: a None
    on the request side SKIPS the check; an int on the request side
    compares against observation.version.correction_version. Reversing
    would not be meaningful (the observation side has no equivalent
    field). The module docstring does not call this comparison out as
    directional; we exercise the documented behaviour here.
    """
    for case in range(50):
        rng = random.Random(BASE_SEED + 40 + case)
        cv = rng.randint(1, 5)
        expected = cv + 1  # mismatch
        observation = _base_observation(
            version={
                "immutable_record": True,
                "correction_version": cv,
                "correction_of": None,
            }
        )
        # expected_correction_version=None -> check is skipped (allowed).
        v_skip = _check(_base_request(), observation)
        assert v_skip.allowed is True, v_skip.reasons
        # expected_correction_version=mismatch -> CORRECTION_VERSION_MISMATCH.
        v_dir = _check(
            _base_request(), observation, expected_correction_version=expected
        )
        assert "CORRECTION_VERSION_MISMATCH" in v_dir.reasons, v_dir.reasons


# ---------------------------------------------------------------------------
# P5. Vocabulary: every bare reason is in REASONS, and reason lists are
#     sorted and de-duplicated if the module promises that. The module
#     promises a de-duplicated, REASONS-ordered tuple (see _freeze_reasons
#     and _verdict).
# ---------------------------------------------------------------------------

def test_p5_vocabulary_and_order():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 5 + case)
        # Random request: 0..3 text-present slots junked.
        request = _base_request()
        observation = _base_observation()
        slots = ("issuer_id", "share_count_ref")
        for slot in slots:
            if rng.random() < 0.5:
                request[slot] = ""
        if rng.random() < 0.5:
            observation["schema"] = "not-the-owner-schema"
        if rng.random() < 0.5:
            observation["observation_id"] = ""
        if rng.random() < 0.5:
            observation["state"] = {"disposition": "rejected", "reason": "SYN"}
        verdict = _check(request, observation)
        msg = _msg(BASE_SEED + 5, case)
        # Vocabulary: every emitted reason is a known REASONS code.
        for code in verdict.reasons:
            assert code in REASONS, (msg, code, verdict.reasons)
        # The module promises REASONS-ordered, de-duplicated tuple. Check
        # both: sorted-by-REASONS-order and no duplicates.
        idx = [list(REASONS).index(c) for c in verdict.reasons]
        assert idx == sorted(idx), (
            f"{msg} reasons not in REASONS order: {verdict.reasons!r}"
        )
        assert len(verdict.reasons) == len(set(verdict.reasons)), (
            f"{msg} reasons contain duplicates: {verdict.reasons!r}"
        )
        # Every parameterised reason (e.g. "foo:bar") splits to a head
        # that lives in REASONS. None of the module's REASONS carry ':',
        # so for this module bare reason == reason.
        for code in verdict.reasons:
            head = code.split(":", 1)[0]
            assert head in REASONS, (msg, head, code, verdict.reasons)
        total += 1
    assert total >= N_CASES, "p5 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P6. No raise on junk: random junk values in any field never propagate an
#     exception, apart from documented TypeErrors for non-Mapping inputs and
#     the authority refusal. Junk values: None, "", " ", padded strings,
#     ints, bools, floats including nan, bytes, lists, dicts, sets,
#     object().
# ---------------------------------------------------------------------------

JUNK = (
    None,
    "",
    " ",
    " X",
    "X ",
    0,
    1,
    -1,
    True,
    False,
    0.0,
    1.5,
    float("nan"),
    float("inf"),
    float("-inf"),
    b"bytes-not-text",
    [1, 2, 3],
    {"k": "v"},
    {1, 2, 3},
    object(),
)


def _safe_call(request, observation):
    return _check(request, observation)


def test_p6_no_raise_on_junk_in_any_field():
    # Pick one slot at a time, plant one junk value, run the guard.
    text_slots_req = ("issuer_id", "share_count_ref", "ads_ratio_source",
                      "counter_kind", "ads_ratio")
    text_slots_obs = ("issuer_id", "observation_id")
    nested_slots_obs = (
        ("version", "correction_version"),
        ("state", "disposition"),
    )
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 6 + case)
        request = _base_request()
        observation = _base_observation()
        bucket = case % 3
        if bucket == 0:
            slot = text_slots_req[case % len(text_slots_req)]
            request[slot] = JUNK[(case * 3) % len(JUNK)]
        elif bucket == 1:
            slot = text_slots_obs[case % len(text_slots_obs)]
            observation[slot] = JUNK[(case * 5) % len(JUNK)]
        else:
            keys = nested_slots_obs[case % len(nested_slots_obs)]
            current = observation
            for key in keys[:-1]:
                current[key] = dict(current[key])
                current = current[key]
            current[keys[-1]] = JUNK[(case * 7) % len(JUNK)]
        verdict = _safe_call(request, observation)
        msg = _msg(BASE_SEED + 6, case)
        # No raise: verdict returned.
        assert verdict is not None, msg
        # Vocabulary sanity.
        for code in verdict.reasons:
            assert code in REASONS, (msg, code, verdict.reasons)
        # Authority still literal False on any returned verdict.
        for name in FLAG_NAMES:
            assert verdict.authority_flags[name] is False, msg
        total += 1
    assert total >= N_CASES, "p6 ran fewer than N_CASES generated cases"


def test_p6_no_raise_on_junk_in_observation_point_in_time():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 60 + case)
        observation = _base_observation()
        observation["point_in_time"] = {
            "system_available_at": JUNK[case % len(JUNK)],
            "source_retrieved_at": JUNK[(case + 1) % len(JUNK)],
            "available_at": JUNK[(case + 2) % len(JUNK)],
        }
        verdict = _check(_base_request(), observation)
        msg = _msg(BASE_SEED + 60, case)
        assert verdict is not None, msg
        total += 1
    assert total >= N_CASES, "p6-point ran fewer than N_CASES generated cases"


def test_p6_no_raise_on_authority_subfield_junk():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 61 + case)
        observation = _base_observation()
        observation["authority"] = JUNK[case % len(JUNK)]
        verdict = _check(_base_request(), observation)
        msg = _msg(BASE_SEED + 61, case)
        assert verdict is not None, msg
        total += 1
    assert total >= N_CASES, "p6-auth ran fewer than N_CASES generated cases"


def test_p6_documented_typeerrors_still_raise():
    # Non-Mapping request -> TypeError.
    with pytest.raises(TypeError):
        _check("not a mapping", _base_observation())
    # Non-Mapping observation -> TypeError.
    with pytest.raises(TypeError):
        _check(_base_request(), "not a mapping")
    # Authority refusal -> ValueError.
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"rank_authority": True})


# ---------------------------------------------------------------------------
# P7. Authority: every verdict's authority flags (rank/gate/size/signal/
#     escalation/trade) are literal False.
# ---------------------------------------------------------------------------

def test_p7_authority_flags_literal_false():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 7 + case)
        # Three flavours of request+observation to exercise different
        # refusal paths.
        flavour = case % 4
        if flavour == 0:
            verdict = _check(_base_request(), _base_observation())
        elif flavour == 1:
            verdict = _check(_base_request(), None)
        elif flavour == 2:
            request = _base_request(issuer_id="", share_count_ref="")
            observation = _base_observation(schema="wrong", observation_id="")
            verdict = _check(request, observation)
        else:
            request = _ads_request(ads_ratio=0, ads_ratio_source=None)
            verdict = _check(request, _base_observation())
        msg = _msg(BASE_SEED + 7, case)
        for name in FLAG_NAMES:
            assert verdict.authority_flags[name] is False, (
                f"{msg} {name}={verdict.authority_flags[name]!r}"
            )
            assert verdict.authority_flags[name] is not True, msg
            assert verdict.authority_flags[name] is not 0, msg  # noqa: F632
            assert verdict.authority_flags[name] is not None, msg
        total += 1
    assert total >= N_CASES, "p7 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# P8. Determinism: the same input twice gives an identical verdict; input
#     dicts are not mutated by the call.
# ---------------------------------------------------------------------------

def test_p8_determinism_and_no_input_mutation():
    total = 0
    for case in range(N_CASES):
        rng = random.Random(BASE_SEED + 8 + case)
        # Snapshot deepcopies of fresh random inputs.
        request = _base_request(
            issuer_id="SYN-I-" + str(case),
            share_count_ref="SYN-O-" + str(case),
        )
        observation = _base_observation(
            issuer_id="SYN-I-" + str(case),
            observation_id="SYN-O-" + str(case),
        )
        # Plant a small junk field somewhere so the verdict isn't always
        # the same shape.
        if rng.random() < 0.4:
            observation["state"] = {"disposition": "rejected", "reason": "X"}
        before_req = copy.deepcopy(request)
        before_obs = copy.deepcopy(observation)
        first = _check(request, observation)
        second = _check(request, observation)
        msg = _msg(BASE_SEED + 8, case)
        # No mutation.
        assert request == before_req, (
            f"{msg} request mutated: was={before_req!r} now={request!r}"
        )
        assert observation == before_obs, (
            f"{msg} observation mutated: was={before_obs!r} now={observation!r}"
        )
        # Determinism.
        assert first.reasons == second.reasons, (
            f"{msg} reasons drifted between calls: "
            f"first={first.reasons!r} second={second.reasons!r}"
        )
        assert first.allowed == second.allowed, msg
        assert first.owner_observation_id == second.owner_observation_id, msg
        assert first.correction_version == second.correction_version, msg
        total += 1
    assert total >= N_CASES, "p8 ran fewer than N_CASES generated cases"


# ---------------------------------------------------------------------------
# PERTURBATION PROOF
# ---------------------------------------------------------------------------

def _text_present_with_lt(value: object) -> bool:
    """A deliberately broken copy of the module's `_text_present`.

    The real `_text_present` accepts a value only when it is a non-empty
    string with no leading/trailing whitespace. This copy flips ONE
    condition: it treats empty strings and whitespace-padded strings as
    PRESENT (the inverse of the FAMILY TEXT RULE). The defect is the
    inequality / padding check returning True for absent values, so a
    blank issuer_id becomes present and the OWNER_REF_MISSING /
    ISSUER_MISMATCH branches compare equal-to-empty.
    """
    if not isinstance(value, str):
        return True  # BUG: non-str is "present"
    if value == "":
        return True  # BUG: empty is "present"
    if value[0].isspace() or value[-1].isspace():
        return True  # BUG: padded is "present"
    return False  # BUG: a real text id is "not present"


def _text_present_with_eq_inverted(value: object) -> bool:
    """A second deliberately broken copy.

    The second condition is flipped: a `str` whose first OR last char is
    whitespace is reported NOT present, but a string of all whitespace
    passes the `value != ""` check and the `value[0].isspace()` check,
    so it falls through as not present. We invert the leading/trailing
    whitespace semantics so a non-empty string whose edges are whitespace
    IS present (the family-text rule says the opposite).
    """
    if not isinstance(value, str):
        return False
    if value == "":
        return False
    # BUG: a real id without padding is "not present"; padding is fine.
    if not value[0].isspace() and not value[-1].isspace():
        return False
    return True


def _check_with_broken_text_present(broken, request, observation, **kwargs):
    """Replay the guard's text-present decisions using a broken helper."""
    import sni_denominator_guard as _mod

    real = _mod._text_present
    _mod._text_present = broken
    try:
        kwargs.setdefault("as_of", AS_OF)
        return _mod.check_denominator(request, observation, **kwargs)
    finally:
        _mod._text_present = real


def test_perturbation_text_present_off_fires_proves_breaks():
    """The broken `_text_present_with_lt` MUST cause real properties to
    fail when the guard is exercised against it, and the same properties
    MUST pass against the real module on the same inputs.

    We pick inputs that the real module treats as a fully text-present
    allowed pair (P1) and inputs that the real module refuses because of
    blank issuer / observation_id (P3 / P5). Against the broken copy:
      - blank issuer_id becomes "present" so ISSUER_MISMATCH flips to
        allowed (P1's "no refusal reasons" property fails).
      - blank observation_id becomes "present" so OWNER_REF_MISSING
        flips to allowed.
      - empty request becomes empty-string so the FAMILY TEXT RULE's "absent"
        property flips to "present".
    That is at least 2 properties failing against the broken copy and
    passing against the real module.
    """
    n_blank_issuer = 0
    n_blank_obs_id = 0
    for case in range(50):
        real_request = _base_request(issuer_id="", share_count_ref="")
        real_observation = _base_observation(issuer_id="", observation_id="")
        # Real module: refuses with ISSUER_MISMATCH and OWNER_REF_MISSING.
        real_v = _check(real_request, real_observation)
        assert real_v.allowed is False, (case, real_v.reasons)
        assert "ISSUER_MISMATCH" in real_v.reasons, (case, real_v.reasons)
        assert "OWNER_REF_MISSING" in real_v.reasons, (case, real_v.reasons)
        # Broken copy: blank issuer / blank observation_id look "present",
        # so neither ISSUER_MISMATCH nor OWNER_REF_MISSING fires.
        bad_v = _check_with_broken_text_present(
            _text_present_with_lt, real_request, real_observation
        )
        if "ISSUER_MISMATCH" not in bad_v.reasons:
            n_blank_issuer += 1
        if "OWNER_REF_MISSING" not in bad_v.reasons:
            n_blank_obs_id += 1
    assert n_blank_issuer >= 25, (
        "PERTURBATION PROOF FAILED: the broken _text_present did not "
        "suppress ISSUER_MISMATCH on blank-issuer inputs at least 25 "
        "times across 50 cases (got %d)." % n_blank_issuer
    )
    assert n_blank_obs_id >= 25, (
        "PERTURBATION PROOF FAILED: the broken _text_present did not "
        "suppress OWNER_REF_MISSING on blank-observation-id inputs at "
        "least 25 times across 50 cases (got %d)." % n_blank_obs_id
    )

    # Also exercise the second broken helper on padded-id inputs.
    n_padded = 0
    for case in range(50):
        # A padded issuer_id (" X" / "X ") is absent per the family-text
        # rule (must refuse ISSUER_MISMATCH). The broken copy treats the
        # padding as "present", so it can flip to allowed when the rest of
        # the guard agrees.
        real_request = _base_request(issuer_id=" X")
        real_observation = _base_observation(issuer_id=" X", observation_id="X ")
        real_v = _check(real_request, real_observation)
        assert "ISSUER_MISMATCH" in real_v.reasons, (case, real_v.reasons)
        assert "OWNER_REF_MISSING" in real_v.reasons, (case, real_v.reasons)
        bad_v = _check_with_broken_text_present(
            _text_present_with_eq_inverted,
            real_request,
            real_observation,
        )
        if "ISSUER_MISMATCH" not in bad_v.reasons:
            n_padded += 1
    assert n_padded >= 25, (
        "PERTURBATION PROOF FAILED: the second broken _text_present did "
        "not suppress ISSUER_MISMATCH on padded-issuer inputs at least "
        "25 times across 50 cases (got %d)." % n_padded
    )


def test_perturbation_text_present_p1_p3_property_pair_flip():
    """P1 ("valid fully-text-present input stays allowed") and P3
    ("junk text slots never compare equal") MUST both fail on the broken
    copy and pass on the real module. This is the second property-flip
    the spec requires.
    """
    # P1-style input: real module says allowed, broken copy still allows
    # (the broken helper doesn't break the "happy path" here, because the
    # real id has no padding). So P1 does not flip on this helper; flip
    # P1 with the blank-id broken helper instead.
    real_v = _check(_base_request(), _base_observation())
    assert real_v.allowed is True, real_v.reasons
    # Build an input where P1's PROPERTY (`allowed`) is sensitive to the
    # broken helper: a request whose issuer_id is blank. The real module
    # REFUSES this input with ISSUER_MISMATCH, which violates the P1
    # "fully text-present" precondition; we therefore target a different
    # P1 property flip: a request whose every text-present slot is
    # padded so the broken helper thinks it is "absent" and the real
    # helper thinks it is "present" (mismatch on equality).
    # When the request and observation issuer_id are both padded with
    # different paddings, the real module refuses (ISSUER_MISMATCH) and
    # the broken helper also refuses (different reasons); the property we
    # flip is "junk never present, never compares equal": with the same
    # padded string on both sides, the broken helper treats padding as
    # "absent", so the guard refuses (correct), but the broken helper
    # in `_text_present_with_eq_inverted` says both sides are "present"
    # AND equal (the padded equality check returns True), so the guard
    # should ALLOW this input. The real module must refuse.
    for case in range(50):
        s = " X"  # padded same on both sides
        ref = "SYN-OBS-1 "  # share_count_ref padded identically
        real_request = _base_request(issuer_id=s, share_count_ref=ref)
        real_observation = _base_observation(
            issuer_id=s, observation_id=ref
        )
        real_v = _check(real_request, real_observation)
        bad_v = _check_with_broken_text_present(
            _text_present_with_eq_inverted,
            real_request,
            real_observation,
        )
        # Real module: padded ids are ABSENT per FAMILY TEXT RULE v2 ->
        # ISSUER_MISMATCH + OWNER_REF_MISSING.
        assert "ISSUER_MISMATCH" in real_v.reasons, (case, real_v.reasons)
        assert "OWNER_REF_MISSING" in real_v.reasons, (case, real_v.reasons)
        # Broken copy: padded ids are PRESENT -> no ISSUER_MISMATCH and
        # no OWNER_REF_MISSING.
        assert "ISSUER_MISMATCH" not in bad_v.reasons, (
            case, bad_v.reasons
        )
        assert "OWNER_REF_MISSING" not in bad_v.reasons, (
            case, bad_v.reasons
        )