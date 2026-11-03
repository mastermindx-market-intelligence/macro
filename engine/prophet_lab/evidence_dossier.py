"""B04-A0 episode evidence dossier wrapper over the admitted D5 vector.

This module is the A0 slice of R6-B04-01a (ratified 2026-09-24): a read-only
wrapper around the existing earnings intelligence vector. It owns no route, no
renderer, no rights register, no correction comparison and no event-set
producer; those stay with B04-A1/B04-B/B04-C/B04-D. The wrapper consumes the
vector without mutating ``absence_reasons``, ``point_in_time`` or any
content-addressed identity: every projection works on a deepcopy.

A8 order inside :func:`build_evidence_dossier`: rights gate (fail-closed — a
lane without a rights decision is blocked, never waved through), prohibited-
field removal for gated lanes, content addressing of the projected views,
wrapper assembly, then ``dossier_id`` content addressing over the finished
gated wrapper. The projection touches only the fields the amendment lists:
``family_projection_id``/``projection_id`` recomputation, family ``source_refs``,
``evidence_roots``, ``explanation_facts`` and the gated lanes' observations.
``trajectory``, ``correction`` and the other family fields are outside the A8
touch list and are deliberately left untouched; per-field lane attribution for
them is the complete B04-B rights gate.

Clock reuse: time parsing and canonical content addressing come from
``engine.prophet_lab.intelligence_vector`` read-only, so the wrapper applies
the same owner clock contract and hash algorithm as the vector itself.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from engine.prophet_lab.intelligence_vector import (
    ALL_FALSE_AUTHORITY,
    _FORBIDDEN_KEYS,
    _OWNER_LANES,
    _canonical_bytes,
    _content_id,
    _parse_time,
)

SCHEMA = "prophet.episode_evidence_dossier/v1"
REASON_MAP_SCHEMA = "prophet.dossier_reason_map/v1"
REASON_MAP_RELPATH = "config/prophet_dossier_reason_map.v1.json"

#: A10 total order (amendment lines 73-89). The committed reason map's
#: ``display_codes`` list must equal this order exactly.
DISPLAY_CODE_PRECEDENCE: tuple[str, ...] = (
    "IDENTITY_BINDING_CONFLICT",
    "IDENTITY_UNRESOLVED",
    "RIGHTS_NOT_A_SOURCE",
    "RIGHTS_INTERNAL_ONLY",
    "RIGHTS_UNDETERMINED",
    "SOURCE_TEMPORARILY_UNAVAILABLE",
    "SOURCE_UNAVAILABLE",
    "CONFLICTING_SOURCE_SPANS",
    "CONFLICTING_SOURCE_CLOCKS",
    "NOT_PUBLISHED_AT_DECISION",
    "NOT_CAPTURED_AT_DECISION",
    "NOT_AVAILABLE_AT_DECISION",
    "HISTORICAL_EVENT_SET_UNAVAILABLE",
    "EXACT_LINEAGE_UNAVAILABLE",
    "STALE",
    "NOT_APPLICABLE",
    "UNKNOWN",
)
#: Annotation-only value; never participates in precedence and never appears
#: as a missingness code (A10/A12).
ANNOTATION_CODES: tuple[str, ...] = ("CORRECTED_LATER",)

VIEW_NAMES: tuple[str, ...] = ("original", "current")
VIEW_STATES: tuple[str, ...] = ("PRESENT", "ABSENT", "GATED")
MISSINGNESS_STATES: tuple[str, ...] = ("NONE", "PARTIAL", "FULL")
RIGHTS_STATES: tuple[str, ...] = ("ALLOWED", "INTERNAL_ONLY", "NOT_A_SOURCE", "ABSENT")
EVIDENCE_CLASS_STATES: tuple[str, ...] = ("NOT_ASSERTED", "ASSERTED")

#: Register ``user_redistribution`` posture vocabulary (A10/A11). The complete
#: lane-family map and route-boundary application are B04-B.
USER_REDISTRIBUTION_POSTURES: tuple[str, ...] = (
    "USER_FACING", "USER_FACING_WITH_LIMITS", "INTERNAL_ONLY", "NOT_A_SOURCE", "ABSENT",
)
_POSTURE_TO_STATE: dict[str, str] = {
    "USER_FACING": "ALLOWED",
    "USER_FACING_WITH_LIMITS": "ALLOWED",
    "INTERNAL_ONLY": "INTERNAL_ONLY",
    "NOT_A_SOURCE": "NOT_A_SOURCE",
    "ABSENT": "ABSENT",
}
_RIGHTS_DISPLAY_CODE: dict[str, str] = {
    "INTERNAL_ONLY": "RIGHTS_INTERNAL_ONLY",
    "NOT_A_SOURCE": "RIGHTS_NOT_A_SOURCE",
    "ABSENT": "RIGHTS_UNDETERMINED",
}

#: Dossier lane -> native metric carried by the vector family. Lanes without a
#: row have no observation-level evidence to remove (their content, if any,
#: lives outside the A8 touch list).
_LANE_METRIC_IDS: dict[str, str] = {
    "FACT_REVENUE": "fact:revenue",
    "GUIDANCE_REVENUE_YOY_PCT": "guidance:revenue_yoy_pct",
    "DELTA_REVENUE": "metric_delta:revenue",
}

#: Native receipt conditions that report a required-clock conflict; the A7
#: override is refused over them (amendment lines 17-20, 32-35).
_CLOCK_CONFLICT_FLAGS: frozenset[str] = frozenset({"unresolved_clock_tie"})

_DOSSIER_KEYS = frozenset({
    "schema", "dossier_id", "views", "evidence_class", "rights",
    "missingness", "messages", "authority",
})
_VIEW_KEYS = frozenset({
    "state", "view_basis", "view_decision_admissible", "vector_projection_id",
})
_REASON_MAP_ROW_KEYS = frozenset({"coverage_basis", "reason_id", "lane", "code"})
_REASON_MAP_OVERRIDE_KEYS = frozenset({"condition", "code", "annotation"})


class EvidenceDossierContractError(ValueError):
    """The dossier wrapper input or output is outside the closed B04-A contract."""


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _reject_forbidden_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in _FORBIDDEN_KEYS:
                raise EvidenceDossierContractError(
                    f"forbidden closed-contract field: {key}"
                )
            _reject_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_forbidden_keys(child)


def _validate_reason_map(payload: Any) -> None:
    if not isinstance(payload, Mapping):
        raise EvidenceDossierContractError("reason map must be an object")
    if payload.get("schema") != REASON_MAP_SCHEMA:
        raise EvidenceDossierContractError("reason map schema mismatch")
    if list(payload.get("display_codes") or []) != list(DISPLAY_CODE_PRECEDENCE):
        raise EvidenceDossierContractError(
            "reason map display codes must equal the A10 precedence order"
        )
    if list(payload.get("annotation_codes") or []) != list(ANNOTATION_CODES):
        raise EvidenceDossierContractError("reason map annotation codes are closed")
    sentences = payload.get("sentences")
    if not isinstance(sentences, Mapping):
        raise EvidenceDossierContractError("reason map sentences must be an object")
    expected_sentence_keys = set(DISPLAY_CODE_PRECEDENCE) | set(ANNOTATION_CODES)
    if set(sentences) != expected_sentence_keys:
        raise EvidenceDossierContractError("reason map sentences cover a closed code set")
    for code, sentence in sentences.items():
        if not isinstance(sentence, Mapping) or set(sentence) != {"en", "zh"}:
            raise EvidenceDossierContractError(f"reason map sentence shape invalid: {code}")
        if not isinstance(sentence["en"], str) or not isinstance(sentence["zh"], str):
            raise EvidenceDossierContractError(f"reason map sentence locales invalid: {code}")
    rows = payload.get("map")
    if not isinstance(rows, list) or not rows:
        raise EvidenceDossierContractError("reason map rows must be a non-empty list")
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != set(_REASON_MAP_ROW_KEYS):
            raise EvidenceDossierContractError("reason map row shape is closed")
        if row["coverage_basis"] is not None and not isinstance(row["coverage_basis"], str):
            raise EvidenceDossierContractError("reason map coverage basis must be a string or null")
        if not isinstance(row["reason_id"], str) or not row["reason_id"]:
            raise EvidenceDossierContractError("reason map reason id must be a string")
        if row["lane"] is not None and not isinstance(row["lane"], str):
            raise EvidenceDossierContractError("reason map lane must be a string or null")
        if row["code"] not in DISPLAY_CODE_PRECEDENCE:
            raise EvidenceDossierContractError("reason map row code is outside the closed set")
    overrides = payload.get("wrapper_overrides")
    if not isinstance(overrides, list):
        raise EvidenceDossierContractError("reason map wrapper overrides must be a list")
    for override in overrides:
        if not isinstance(override, Mapping) or not set(override) <= set(_REASON_MAP_OVERRIDE_KEYS):
            raise EvidenceDossierContractError("reason map override shape is closed")
        if not isinstance(override.get("condition"), str):
            raise EvidenceDossierContractError("reason map override condition must be a sentence")
        code = override.get("code")
        annotation = override.get("annotation")
        if code is not None and code not in DISPLAY_CODE_PRECEDENCE:
            raise EvidenceDossierContractError("reason map override code is outside the closed set")
        if annotation is not None and annotation not in ANNOTATION_CODES:
            raise EvidenceDossierContractError("reason map override annotation is outside the closed set")


def load_reason_map(root: Path | None = None) -> dict[str, Any]:
    """Load and close-check the committed A9 reason map.

    ``root`` is the repository root; the route composition root passes its own
    root, tests pass the checkout root, and the default resolves module-relative
    so the wrapper never depends on the process working directory.
    """
    base = Path(root) if root is not None else _repo_root()
    try:
        raw = (base / REASON_MAP_RELPATH).read_text(encoding="utf-8")
    except OSError as exc:
        raise EvidenceDossierContractError("dossier reason map is not installed") from exc
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        raise EvidenceDossierContractError("dossier reason map is not valid JSON") from exc
    _validate_reason_map(payload)
    return payload


def resolve_display_code(
    reason_map: Mapping[str, Any],
    coverage_basis: str | None,
    reason_id: str,
    lane: str | None = None,
) -> str:
    """A9 pure mapping from ``(coverage basis, reason ID, lane)`` to a display code.

    A null lane matches every lane and an explicit lane is more specific; the
    coverage basis is the primary key, so an explicit basis outranks an explicit
    lane. Resolution tiers in order: exact basis + lane, exact basis + null
    lane, null basis + explicit lane, null basis + null lane. An unmapped key
    resolves to the neutral ``UNKNOWN`` and never to a positive code.
    """
    tiers: tuple[tuple[bool, bool], ...] = (
        (True, True), (True, False), (False, True), (False, False),
    )
    for want_basis, want_lane in tiers:
        matches = [
            row for row in reason_map.get("map", [])
            if row.get("reason_id") == reason_id
            and (row.get("coverage_basis") is not None) == want_basis
            and (not want_basis or row.get("coverage_basis") == coverage_basis)
            and (row.get("lane") is not None) == want_lane
            and (not want_lane or row.get("lane") == lane)
        ]
        if not matches:
            continue
        codes = {row["code"] for row in matches}
        if len(codes) != 1:
            raise EvidenceDossierContractError(
                "reason map rows collide inside one specificity tier"
            )
        return codes.pop()
    return "UNKNOWN"


def select_display_code(codes: Sequence[str] | set[str]) -> str | None:
    """A10 precedence: the earliest present display code in the total order.

    ``CORRECTED_LATER`` is an annotation-only value and never participates.
    """
    present = set(codes)
    for code in DISPLAY_CODE_PRECEDENCE:
        if code in present:
            return code
    return None


def classify_point_in_time_clocks(
    *,
    source_available_at: Any,
    observed_at: Any,
    generated_at: Any,
    cut: Any,
    observed_at_attests_capture: bool = False,
) -> str | None:
    """A7 clock split over the four owner-supplied clocks.

    Returns the guarded display code, or ``None`` when no positive causal
    classification applies. Missing, invalid or unparsable required clocks
    return ``None`` (neutral display, native reasons preserved): the positive
    explanations below require all four clocks to parse under the existing
    owner clock contract. All clocks at or before the cut satisfy only the
    clock condition — never identity, rights or general decision admission —
    and also return ``None``. Native receipt conflicts (ordering ties) are
    carried by the coverage basis and are refused by the wrapper before this
    classification runs.
    """
    parsed_cut = _parse_time(cut)
    parsed = {
        "source_available_at": _parse_time(source_available_at),
        "observed_at": _parse_time(observed_at),
        "generated_at": _parse_time(generated_at),
    }
    if parsed_cut is None or any(value is None for value in parsed.values()):
        return None
    source = parsed["source_available_at"]
    observed = parsed["observed_at"]
    computed = parsed["generated_at"]
    if source > parsed_cut:
        return "NOT_PUBLISHED_AT_DECISION"
    if observed > parsed_cut:
        if observed_at_attests_capture:
            return "NOT_CAPTURED_AT_DECISION"
        # A late observation without an owner capture attestation may establish
        # decision unavailability, but must not be described as late capture.
        return "NOT_AVAILABLE_AT_DECISION"
    if computed > parsed_cut:
        return "NOT_AVAILABLE_AT_DECISION"
    return None


def _family_clock_override(
    family: Mapping[str, Any], cut: Any, *, observed_at_attests_capture: bool,
) -> str | None:
    """Run the A7 split on one family's point-in-time receipt.

    The family's own conflict/missing evidence suppresses the override: a
    native late-clock or tie reason alone cannot grant a positive claim.
    """
    coverage_basis = str(_mapping(family.get("coverage")).get("basis") or "")
    quality_flags = {
        str(flag) for flag in _list(_mapping(family.get("quality")).get("flags"))
    }
    point_in_time = _mapping(family.get("point_in_time"))
    missing_clocks = _list(point_in_time.get("missing_clocks"))
    if coverage_basis in _CLOCK_CONFLICT_FLAGS or quality_flags & _CLOCK_CONFLICT_FLAGS:
        return None
    if missing_clocks:
        return None
    return classify_point_in_time_clocks(
        source_available_at=_mapping(point_in_time.get("source_published_at")).get("value"),
        observed_at=_mapping(point_in_time.get("known_at")).get("value"),
        generated_at=_mapping(point_in_time.get("computed_at")).get("value"),
        cut=cut,
        observed_at_attests_capture=observed_at_attests_capture,
    )


def _single_family(vector: Mapping[str, Any]) -> Mapping[str, Any]:
    families = vector.get("evidence_families")
    if (
        not isinstance(families, list)
        or len(families) != 1
        or not isinstance(families[0], Mapping)
    ):
        raise EvidenceDossierContractError(
            "the dossier consumes exactly one closed evidence family"
        )
    return families[0]


def _dossier_lanes(family: Mapping[str, Any]) -> list[str]:
    rows = _list(_mapping(family.get("owner_lane_dispositions")).get("lanes"))
    lanes: list[str] = []
    for row in rows:
        if isinstance(row, Mapping) and isinstance(row.get("lane"), str):
            if row["lane"] not in lanes:
                lanes.append(row["lane"])
    return lanes or list(_OWNER_LANES)


def _lane_dispositions(family: Mapping[str, Any]) -> dict[str, str]:
    rows = _list(_mapping(family.get("owner_lane_dispositions")).get("lanes"))
    dispositions: dict[str, str] = {}
    for row in rows:
        if isinstance(row, Mapping) and isinstance(row.get("lane"), str):
            dispositions[row["lane"]] = str(row.get("disposition") or "ABSENT")
    return dispositions


def _rights_state_for_lane(rights: Mapping[str, Any] | None, lane: str) -> str:
    posture = _mapping(rights).get(lane)
    if posture is None:
        # Fail-closed: no rights decision is never an allowed decision.
        return "ABSENT"
    if posture not in _POSTURE_TO_STATE:
        raise EvidenceDossierContractError(
            "rights posture is outside the closed user_redistribution vocabulary"
        )
    return _POSTURE_TO_STATE[posture]


def _native_lane_codes(
    reason_map: Mapping[str, Any], family: Mapping[str, Any], lane: str,
) -> set[str]:
    """A9 resolution of the family's native coverage/reason vocabulary."""
    codes: set[str] = set()
    basis = _mapping(family.get("coverage")).get("basis")
    basis = basis if isinstance(basis, str) and basis else None
    for observation in _list(family.get("observations")):
        if _mapping(observation).get("value_state") != "ABSENT":
            continue
        for reason in _list(_mapping(observation).get("absence_reasons")):
            codes.add(resolve_display_code(reason_map, basis, str(reason), lane))
    metric = _LANE_METRIC_IDS.get(lane)
    if metric is not None:
        for dimension in _list(_mapping(family.get("trajectory")).get("dimensions")):
            if _mapping(dimension).get("native_metric_id") != metric:
                continue
            value = _mapping(dimension.get("value"))
            for side_name in ("prior", "consensus"):
                side = _mapping(value.get(side_name))
                if side.get("state") == "ABSENT" and isinstance(side.get("reason"), str):
                    codes.add(resolve_display_code(reason_map, None, side["reason"], lane))
    return codes


def _strip_gated_lane_evidence(family: dict[str, Any], metrics: set[str]) -> bool:
    """Remove the gated lanes' observations and their exclusive lineage.

    Only the A8 touch list is modified: ``observations``, ``source_refs``,
    ``evidence_roots`` and ``explanation_facts``. Source refs and roots that no
    surviving observation references were carried only for gated lanes and are
    dropped so no hash, document id, field path or root survives as an oracle.
    Explanation facts have no per-lane attribution in v1 (the family emits
    none), so any gated lane removes them wholesale — fail-closed, and the
    per-fact attribution is the complete B04-B gate.
    """
    if not metrics:
        return False
    observations = _list(family.get("observations"))
    survivors = [
        observation for observation in observations
        if not (
            isinstance(observation, Mapping)
            and observation.get("native_metric_id") in metrics
        )
    ]
    changed = len(survivors) != len(observations)
    family["observations"] = survivors
    kept_source_ids: set[str] = set()
    kept_root_ids: set[str] = set()
    for observation in survivors:
        if not isinstance(observation, Mapping):
            continue
        kept_source_ids.update(str(item) for item in _list(observation.get("source_ref_ids")))
        kept_root_ids.update(str(item) for item in _list(observation.get("evidence_root_ids")))
    source_refs = _list(family.get("source_refs"))
    roots = _list(family.get("evidence_roots"))
    kept_refs = [
        ref for ref in source_refs
        if not isinstance(ref, Mapping) or str(ref.get("source_ref_id") or "") in kept_source_ids
    ]
    kept_roots = [
        root for root in roots
        if not isinstance(root, Mapping) or str(root.get("evidence_root_id") or "") in kept_root_ids
    ]
    changed = changed or len(kept_refs) != len(source_refs) or len(kept_roots) != len(roots)
    family["source_refs"] = kept_refs
    family["evidence_roots"] = kept_roots
    if family.get("explanation_facts"):
        family["explanation_facts"] = []
        changed = True
    return changed


def _recompute_family_projection_id(family: dict[str, Any]) -> None:
    semantic = {key: deepcopy(value) for key, value in family.items() if key != "family_projection_id"}
    family["family_projection_id"] = _content_id("pif", semantic)


def _recompute_vector_projection_id(projected: dict[str, Any]) -> None:
    semantic = {
        key: deepcopy(value) for key, value in projected.items()
        if key not in {"projection_id", "assembly_receipt"}
    }
    projected["projection_id"] = _content_id("piv", semantic)


def project_view(
    vector: Mapping[str, Any],
    *,
    gated_lanes: Sequence[str] = (),
    view: str = "original",
) -> dict[str, Any]:
    """A8 gated projection of one view; returns the projected vector.

    For the ``current`` view the projection never emits the inner
    ``point_in_time.decision_admissibility`` (A8): that key is removed before
    the view is content-addressed. A view with no gated lane and no current-view
    emission change is returned byte-identical to its input — a lane that
    passes all rights checks is projected without mutation. Identity is
    recomputed only after gated families change.
    """
    if not isinstance(vector, Mapping):
        raise EvidenceDossierContractError("vector must be a mapping")
    if view not in VIEW_NAMES:
        raise EvidenceDossierContractError("view must be original or current")
    _reject_forbidden_keys(vector)
    _single_family(vector)
    projected = deepcopy(vector)
    families = projected["evidence_families"]
    changed = False
    if view == "current":
        for family in families:
            point_in_time = family.get("point_in_time")
            if isinstance(point_in_time, dict) and "decision_admissibility" in point_in_time:
                del point_in_time["decision_admissibility"]
                changed = True
    if gated_lanes:
        metrics = {
            metric for metric in (
                _LANE_METRIC_IDS.get(str(lane)) for lane in gated_lanes
            ) if metric is not None
        }
        for family in families:
            changed = _strip_gated_lane_evidence(family, metrics) or changed
    if changed:
        for family in families:
            _recompute_family_projection_id(family)
        _recompute_vector_projection_id(projected)
    return projected


def _resolve_lane_codes(
    *,
    reason_map: Mapping[str, Any],
    family: Mapping[str, Any],
    lanes: Sequence[str],
    rights_states: Mapping[str, str],
    clock_override: str | None,
    historical_event_set: bool,
    identity_binding_conflict: bool,
) -> dict[str, str | None]:
    codes: dict[str, str | None] = {}
    for lane in lanes:
        candidates: set[str] = set()
        if identity_binding_conflict:
            candidates.add("IDENTITY_BINDING_CONFLICT")
        rights_code = _RIGHTS_DISPLAY_CODE.get(rights_states[lane])
        if rights_code is not None:
            candidates.add(rights_code)
        if clock_override is not None:
            candidates.add(clock_override)
        if historical_event_set:
            candidates.add("HISTORICAL_EVENT_SET_UNAVAILABLE")
        candidates |= _native_lane_codes(reason_map, family, lane)
        codes[lane] = select_display_code(candidates)
    return codes


def _missingness_row(view: str, lane: str, disposition: str, rights_state: str, code: str | None) -> dict[str, Any]:
    if rights_state != "ALLOWED" or disposition == "ABSENT":
        state = "FULL"
    elif code is not None:
        state = "PARTIAL"
    else:
        state = "NONE"
    if state == "NONE":
        return {"view": view, "lane": lane, "state": "NONE", "code": None}
    return {
        "view": view, "lane": lane, "state": state,
        "code": code if code is not None else "UNKNOWN",
    }


def _view_has_present_observation(projected: Mapping[str, Any]) -> bool:
    """A view carries evidence when any projected observation holds a value.

    ``MEASURED_NEUTRAL`` observations carry a measured value (only ``ABSENT``
    observations are value-free), so both count as present evidence.
    """
    return any(
        _mapping(observation).get("value_state") in {"PRESENT", "MEASURED_NEUTRAL"}
        for family in _list(projected.get("evidence_families"))
        for observation in _list(_mapping(family).get("observations"))
    )


def build_evidence_dossier(
    vector: Mapping[str, Any],
    *,
    rights: Mapping[str, Any] | None = None,
    current_vector: Mapping[str, Any] | None = None,
    observed_at_attests_capture: bool = False,
    historical_event_set_unavailable: bool = False,
    identity_binding_conflict: bool = False,
    corrected_later_lanes: Sequence[str] = (),
    reason_map: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the closed B04-A0 evidence dossier wrapper.

    The vector and current vector are consumed read-only. ``rights`` maps each
    dossier lane to its register ``user_redistribution`` posture; a lane with
    no supplied decision is blocked fail-closed. ``observed_at_attests_capture``
    is the explicit owner capture attestation input (default: no attestation).
    ``historical_event_set_unavailable`` may only be supplied after a successful,
    sufficiently complete existing-owner event-set read established that no
    source-dated point-in-time row can reconstruct the requested event-set
    population at the cut (A11); the wrapper applies it to the original view
    only. ``identity_binding_conflict`` is the explicit A0 wrapper input; the
    typed production exception is B04-A1. ``corrected_later_lanes`` carries the
    caller-established owner correction lineage plus versioned comparable-field
    comparison (the comparison engine itself is B04-C).
    """
    if reason_map is None:
        reason_map = load_reason_map()
    else:
        _validate_reason_map(reason_map)
    if not isinstance(vector, Mapping):
        raise EvidenceDossierContractError("vector must be a mapping")
    _reject_forbidden_keys(vector)
    family = _single_family(vector)
    cut = _mapping(vector.get("decision_cut")).get("opened_at")
    lanes = _dossier_lanes(family)
    dispositions = _lane_dispositions(family)
    rights_states = {lane: _rights_state_for_lane(rights, lane) for lane in lanes}
    gated_lanes = [lane for lane in lanes if rights_states[lane] != "ALLOWED"]

    # A8 order: rights gate (above) -> removal -> projected-view addressing.
    original_projected = project_view(vector, gated_lanes=gated_lanes, view="original")
    if current_vector is not None:
        if not isinstance(current_vector, Mapping):
            raise EvidenceDossierContractError("current vector must be a mapping")
        _reject_forbidden_keys(current_vector)
        current_family = _single_family(current_vector)
        current_lanes = _dossier_lanes(current_family)
        current_projected = project_view(
            current_vector, gated_lanes=gated_lanes, view="current",
        )
        current_state = (
            "GATED" if gated_lanes
            else ("PRESENT" if _view_has_present_observation(current_projected) else "ABSENT")
        )
        current_projection_id = current_projected.get("projection_id")
    else:
        current_family = None
        current_lanes = []
        current_state = "ABSENT"
        current_projection_id = None
    original_state = (
        "GATED" if gated_lanes
        else ("PRESENT" if _view_has_present_observation(original_projected) else "ABSENT")
    )

    clock_override = _family_clock_override(
        family, cut, observed_at_attests_capture=observed_at_attests_capture,
    )
    original_codes = _resolve_lane_codes(
        reason_map=reason_map, family=family, lanes=lanes,
        rights_states=rights_states, clock_override=clock_override,
        historical_event_set=historical_event_set_unavailable,
        identity_binding_conflict=identity_binding_conflict,
    )
    if current_vector is not None:
        current_rights_states = {
            lane: _rights_state_for_lane(rights, lane) for lane in current_lanes
        }
        current_codes = _resolve_lane_codes(
            reason_map=reason_map, family=current_family, lanes=current_lanes,
            rights_states=current_rights_states,
            clock_override=None, historical_event_set=False,
            identity_binding_conflict=identity_binding_conflict,
        )
    else:
        current_rights_states = {}
        current_codes = {}

    sentences = reason_map["sentences"]
    corrected = set(corrected_later_lanes)
    messages: list[dict[str, Any]] = []
    for lane in lanes:
        code = original_codes[lane]
        if code is not None:
            messages.append({
                "lane": lane, "code": code,
                "en": sentences[code]["en"], "zh": sentences[code]["zh"],
            })
        if lane in corrected and dispositions.get(lane) == "PROJECTED":
            # A10: the annotation attaches to a present original value only.
            messages.append({
                "lane": lane, "code": "CORRECTED_LATER",
                "en": sentences["CORRECTED_LATER"]["en"],
                "zh": sentences["CORRECTED_LATER"]["zh"],
            })

    missingness: list[dict[str, Any]] = []
    for lane in lanes:
        missingness.append(_missingness_row(
            "original", lane, dispositions.get(lane, "ABSENT"),
            rights_states[lane], original_codes[lane],
        ))
    current_dispositions = (
        _lane_dispositions(current_family) if current_family is not None else {}
    )
    for lane in current_lanes:
        missingness.append(_missingness_row(
            "current", lane, current_dispositions.get(lane, "ABSENT"),
            current_rights_states[lane], current_codes[lane],
        ))

    rights_rows = [{"lane": lane, "state": rights_states[lane]} for lane in lanes]
    for lane in current_lanes:
        if lane not in rights_states:
            # A current-only lane still owes a fail-closed wrapper rights row.
            rights_states[lane] = current_rights_states[lane]
            rights_rows.append({"lane": lane, "state": current_rights_states[lane]})
    dossier: dict[str, Any] = {
        "schema": SCHEMA,
        "dossier_id": "",
        "views": {
            "original": {
                "state": original_state,
                "view_basis": None,
                "view_decision_admissible": False,
                "vector_projection_id": original_projected.get("projection_id"),
            },
            "current": {
                "state": current_state,
                "view_basis": "RESEARCH_KNOWN_NOW",
                "view_decision_admissible": False,
                "vector_projection_id": current_projection_id,
            },
        },
        "evidence_class": {"state": "NOT_ASSERTED"},
        "rights": rights_rows,
        "missingness": missingness,
        "messages": messages,
        "authority": dict(ALL_FALSE_AUTHORITY),
    }
    # A8: dossier_id content addressing over the finished gated wrapper.
    semantic = {key: value for key, value in dossier.items() if key != "dossier_id"}
    dossier["dossier_id"] = _content_id("dos", semantic)
    validate_evidence_dossier(dossier, reason_map=reason_map)
    return dossier


def validate_evidence_dossier(
    dossier: Mapping[str, Any], *, reason_map: Mapping[str, Any] | None = None,
) -> None:
    """Fail closed on unknown keys, open enums, leakage or dossier-id drift."""
    if reason_map is None:
        reason_map = load_reason_map()
    _reject_forbidden_keys(dossier)
    if not isinstance(dossier, Mapping) or set(dossier) != set(_DOSSIER_KEYS):
        raise EvidenceDossierContractError("dossier closed keys mismatch")
    if dossier["schema"] != SCHEMA:
        raise EvidenceDossierContractError("dossier schema mismatch")
    views = dossier["views"]
    if not isinstance(views, Mapping) or set(views) != set(VIEW_NAMES):
        raise EvidenceDossierContractError("dossier must carry exactly original and current views")
    for name in VIEW_NAMES:
        view = views[name]
        if not isinstance(view, Mapping) or set(view) != set(_VIEW_KEYS):
            raise EvidenceDossierContractError(f"views.{name} closed keys mismatch")
        if view["state"] not in VIEW_STATES:
            raise EvidenceDossierContractError(f"views.{name}.state is outside the closed enum")
        expected_basis = "RESEARCH_KNOWN_NOW" if name == "current" else None
        if view["view_basis"] != expected_basis:
            raise EvidenceDossierContractError(f"views.{name}.view_basis is fixed")
        if type(view["view_decision_admissible"]) is not bool or view["view_decision_admissible"] is not False:
            raise EvidenceDossierContractError(
                f"views.{name}.view_decision_admissible must be the literal false"
            )
        projection_id = view["vector_projection_id"]
        if projection_id is not None and not isinstance(projection_id, str):
            raise EvidenceDossierContractError(f"views.{name}.vector_projection_id must be a string or null")
    evidence_class = dossier["evidence_class"]
    if not isinstance(evidence_class, Mapping) or set(evidence_class) != {"state"}:
        raise EvidenceDossierContractError("evidence_class closed keys mismatch")
    if evidence_class["state"] not in EVIDENCE_CLASS_STATES:
        raise EvidenceDossierContractError("evidence_class.state is outside the closed enum")
    rights = dossier["rights"]
    if not isinstance(rights, list) or not rights:
        raise EvidenceDossierContractError("rights must be a non-empty list")
    rights_lanes: list[str] = []
    for row in rights:
        if not isinstance(row, Mapping) or set(row) != {"lane", "state"}:
            raise EvidenceDossierContractError("rights row closed keys mismatch")
        if not isinstance(row["lane"], str) or not row["lane"]:
            raise EvidenceDossierContractError("rights row lane must be a non-empty string")
        if row["state"] not in RIGHTS_STATES:
            raise EvidenceDossierContractError("rights row state is outside the closed enum")
        rights_lanes.append(row["lane"])
    if len(set(rights_lanes)) != len(rights_lanes):
        raise EvidenceDossierContractError("rights rows must be unique per lane")
    sentences = reason_map["sentences"]
    message_codes = set(DISPLAY_CODE_PRECEDENCE) | set(ANNOTATION_CODES)
    message_lanes: set[str] = set()
    for message in dossier["messages"]:
        if not isinstance(message, Mapping) or set(message) != {"lane", "code", "en", "zh"}:
            raise EvidenceDossierContractError("message closed keys mismatch")
        if not isinstance(message["lane"], str) or not message["lane"]:
            raise EvidenceDossierContractError("message lane must be a non-empty string")
        if message["code"] not in message_codes:
            raise EvidenceDossierContractError("message code is outside the closed set")
        if message["en"] != sentences[message["code"]]["en"] or message["zh"] != sentences[message["code"]]["zh"]:
            raise EvidenceDossierContractError("message sentences must come from the committed table")
        message_lanes.add(message["lane"])
    if not message_lanes <= set(rights_lanes):
        raise EvidenceDossierContractError("message lanes must be dossier lanes")
    missingness_keys = ("view", "lane", "state", "code")
    seen_missingness: set[tuple[str, str]] = set()
    for row in dossier["missingness"]:
        if not isinstance(row, Mapping) or set(row) != set(missingness_keys):
            raise EvidenceDossierContractError("missingness closed keys mismatch")
        if row["view"] not in VIEW_NAMES:
            raise EvidenceDossierContractError("missingness view is outside the closed enum")
        if not isinstance(row["lane"], str) or row["lane"] not in rights_lanes:
            raise EvidenceDossierContractError("missingness lane must be a dossier lane")
        if row["state"] not in MISSINGNESS_STATES:
            raise EvidenceDossierContractError("missingness state is outside the closed enum")
        if (row["view"], row["lane"]) in seen_missingness:
            raise EvidenceDossierContractError("missingness rows must be unique per view and lane")
        seen_missingness.add((row["view"], row["lane"]))
        code = row["code"]
        if row["state"] == "NONE":
            if code is not None:
                raise EvidenceDossierContractError("missingness NONE requires a null code")
        else:
            if code not in DISPLAY_CODE_PRECEDENCE:
                raise EvidenceDossierContractError(
                    "missingness PARTIAL/FULL requires one A10 display code; annotations never appear here"
                )
    authority = dossier["authority"]
    if authority != ALL_FALSE_AUTHORITY or set(authority) != set(ALL_FALSE_AUTHORITY):
        raise EvidenceDossierContractError("dossier authority must be the six all-false booleans")
    if any(type(value) is not bool or value is not False for value in authority.values()):
        raise EvidenceDossierContractError("dossier authority must be all literal false")
    semantic = {key: value for key, value in dossier.items() if key != "dossier_id"}
    if dossier["dossier_id"] != _content_id("dos", semantic):
        raise EvidenceDossierContractError("dossier_id does not address the finished wrapper")
