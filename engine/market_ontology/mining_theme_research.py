"""Mining per-sector composition module (T04a).

Closed, pure composition over the Mining vertical's two economic definitions
(copper and rare earth), loaded once at import from the committed domain content
file ``research/mining/m1_integration_program/domain/MINING_DOMAIN_DEFINITIONS_M1_2026-09-24.md``.
Every output validates against ``contracts/market_ontology/mining_theme_research.v1.schema.json``
on every return path (R-MIN-22). No shared-kernel copy; no route; no I/O; no clock reads.

Binding seat rulings:

* R-MIN-21 — no shared kernel, route, publisher or framework is recreated here.
* R-MIN-22 — ``validate_mining_research`` runs on every return path; the shared kernel
  returns an unvalidated dict, but this module owns its own lazy validator (#7891 idiom).
* R-MIN-23 — ``limitations`` is closed-but-colon-aware (anyOf [enum] + [pattern]).
* R-MIN-24 — ``MiningResearchQuery`` / ``MiningOwnerBundle`` are imported from the existing
  ``mining_dependency_binding`` (T01'); Mining owns its refusals.
* R-MIN-25 — 14 closed top-level keys, ``authorized_coverage.industry_total`` is null,
  no ``neighborhood`` key, ``authority`` echoed on every response and evidence object.
* ADDENDUM §4 IR-01 — a ``definition_unqualified:*`` limitation may coexist with a
  ``comparable`` classification; NO badge / beat / miss / improvement / model-readable
  confirmed-surprise field may be emitted from it. Management point estimate stays a
  point estimate; no invented lower/upper range.
* PLAN §6 T04 — rows ordered by stable source identity, never by magnitude; unknown
  data never becomes zero; ``industry_total`` stays null; a missing cutoff, wrong version,
  wrong slice / theme, bool pagination or competing generation refuses with a typed reason.

The dataclasses and refusal codes live in ``mining_dependency_binding`` and are imported
here (SEAT NOTE in the spec). No import of ``semiconductor_theme_research`` or
``engine.theme_graph`` appears in this module (R-MIN-21 / R-MIN-26).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml
import jsonschema

from engine.market_ontology.mining_dependency_binding import (
    AUTHORITY,
    OMISSION_TO_LIMITATION,
    MiningOwnerBundle,
    MiningResearchQuery,
    MiningResearchRefusal,
    validate_query as _validate_query_kernel,
)


class _MiningCompositionRefusal(MiningResearchRefusal):
    """Mining composition-specific refusal that adds ``unknown_definition_version``.

    R-MIN-24 lists the closed Mining query-refusal vocabulary. The composition
    layer owns its own addition (``unknown_definition_version``) under IR-04; we
    subclass so the CODES check in the base class accepts the new code without
    requiring an edit to the T01' ``mining_dependency_binding`` module.
    """

    def __init__(self, code: str, detail: str = "") -> None:
        # The base class validates ``code in self.CODES``; the composition adds
        # ``unknown_definition_version`` (IR-04) and ``headline_uses_badge_vocabulary``
        # (IR-01 belt-and-braces guard) on top of the T01' vocabulary.
        _extra = {
            "unknown_definition_version",
            "headline_uses_badge_vocabulary",
            "interpretation_stale",
        }
        if code not in MiningResearchRefusal.CODES and code not in _extra:
            raise ValueError(f"unknown refusal code {code!r}")
        # Bypass the base class CODES check by setting attributes directly.
        Exception.__init__(self, f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail

__all__ = [
    "AUTHORITY",
    "MINING_DEFINITIONS",
    "CONTRACT_PATH",
    "VALID_DEFINITION_VERSIONS",
    "compose_mining_research",
    "select_mining_evidence",
    "validate_mining_research",
    "_make_industrial_views_bundle",
    "_add_omission",
    "_order_rows_by_stable_source_identity",
    "_signed_value",
    "_summarize_expectations",
]

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

# Closed, schema-pinned identity. The schema id is reproduced verbatim on every
# response so consumers can pin to it without parsing the file.
_SCHEMA_ID = "market_ontology.mining_theme_research/v1"
CONTRACT_PATH: Path = (
    Path(__file__).resolve().parent.parent.parent
    / "contracts"
    / "market_ontology"
    / "mining_theme_research.v1.schema.json"
)

# Frozen versions table (IR-04). Unknown versions refuse rather than collapse to v1.
VALID_DEFINITION_VERSIONS: frozenset[str] = frozenset({"v1", "v1.0"})

# Bad-vocabulary tokens that must never appear in a composed headline (IR-01).
_BADGE_VOCABULARY: tuple[str, ...] = (
    "beat",
    "miss",
    "improvement",
    "above",
    "below",
    "confirmed",
    "surprise",
)


# ---------------------------------------------------------------------------
# MINING_DEFINITIONS — loaded at import from the committed domain yaml
# ---------------------------------------------------------------------------

_DOMAIN_YAML_PATH: Path = (
    Path(__file__).resolve().parent.parent.parent
    / "research"
    / "mining"
    / "m1_integration_program"
    / "domain"
    / "MINING_DOMAIN_DEFINITIONS_M1_2026-09-24.md"
)


def _load_mining_definitions() -> dict[str, Mapping[str, Any]]:
    """Parse the two closed yaml blocks from the committed domain content file.

    The file contains prose and exactly two fenced ``yaml`` blocks (W-C copper;
    W-R rare earth). Each is parsed independently; we keep the *closed* slice map
    of slice_key -> the parsed block plus a few pinned mining-owned fields.
    Unknown slices KeyError on lookup, never silently default.
    """
    text = _DOMAIN_YAML_PATH.read_text(encoding="utf-8")
    blocks: list[Mapping[str, Any]] = []
    cursor = 0
    fence_open = "```yaml"
    fence_close = "```"
    while True:
        start = text.find(fence_open, cursor)
        if start == -1:
            break
        body_start = start + len(fence_open)
        end = text.find(fence_close, body_start)
        if end == -1:
            raise ValueError(
                f"unterminated yaml fence in {_DOMAIN_YAML_PATH} starting at offset {start}"
            )
        body = text[body_start:end].strip("\n")
        parsed = yaml.safe_load(body)
        if not isinstance(parsed, Mapping):
            raise ValueError(
                f"yaml block in {_DOMAIN_YAML_PATH} at offset {start} did not parse as a mapping"
            )
        blocks.append(parsed)
        cursor = end + len(fence_close)
    if len(blocks) != 2:
        raise ValueError(
            f"expected exactly two yaml blocks in {_DOMAIN_YAML_PATH}, found {len(blocks)}"
        )
    by_slice: dict[str, Mapping[str, Any]] = {}
    for block in blocks:
        slice_key = block.get("slice_key")
        if not isinstance(slice_key, str):
            raise ValueError(
                f"yaml block in {_DOMAIN_YAML_PATH} missing string 'slice_key': {sorted(block)}"
            )
        by_slice[slice_key] = block
    # Closed slice vocabulary — exactly the two definitions in the file.
    expected = {"mining_copper_economics", "mining_rare_earth_economics"}
    if set(by_slice) != expected:
        raise ValueError(
            f"closed slice vocabulary violated: expected {sorted(expected)}, "
            f"got {sorted(by_slice)}"
        )
    return by_slice


MINING_DEFINITIONS: Mapping[str, Mapping[str, Any]] = _load_mining_definitions()


# ---------------------------------------------------------------------------
# Internal helpers (test-importable so the suite can pin their behaviour)
# ---------------------------------------------------------------------------


def _order_rows_by_stable_source_identity(rows: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Order rows by stable source identity; magnitude is never the key (PLAN:203)."""
    return sorted(rows, key=lambda row: str(row.get("stable_subject_id", "")))


def _signed_value(block: Mapping[str, Any]) -> Any:
    """Return the value of a signed native block, preserving its sign.

    Unknown data is None, never zero (PLAN §6); missing is distinct from zero; a
    signed loss keeps its sign (MGD-15). The ``sign_preserved`` marker is accepted
    but never required — the value itself travels with its sign.
    """
    if "value" not in block:
        return None
    return block["value"]


def _summarize_expectations(
    expectations: list[Mapping[str, Any]],
    *,
    defined_fields: set[str] | None = None,
) -> dict[str, Any]:
    """Build a bounded headline + limitations fragment from the expectations list.

    IR-01 binding: a ``definition_unqualified:<field>`` may coexist with a
    ``comparable`` classification; no badge / beat / miss / improvement /
    confirmed-surprise / above / below word may be emitted; the headline stays a
    plain sentence; no model-readable ``confirmed_surprise`` or ``comparison_badge``
    field is minted; management point estimates stay point estimates.

    Each field listed in an expectation's ``definition_unqualified_fields`` is
    minted as a ``definition_unqualified:<field>`` limitation (MAJOR-5 — mint on
    MEMBERSHIP, not skip). The ``defined_fields`` kwarg is retained for
    production-call compatibility but is no longer the skip filter: a real test
    of this contract would load the same production defined_fields that
    compose_mining_research supplies, so the prior test/production divergence
    is gone.

    The function returns a dict with ``headline`` and ``limitations``. The headline
    is intentionally brief — the row-level explanation lives on the response.
    """
    del defined_fields  # no longer a skip filter — see docstring.
    limitations: list[str] = []
    for entry in expectations:
        for field in entry.get("definition_unqualified_fields", []) or []:
            code = f"definition_unqualified:{field}"
            if code not in limitations:
                limitations.append(code)

    if not expectations:
        headline = "No expectations comparison is available in this revision."
    elif limitations:
        headline = (
            "Estimates are inspectable; the comparison is held while definitions are unqualified."
        )
    else:
        # Plain words; no badge vocabulary; never synthesises a beat / miss / above / below claim.
        headline = (
            "Estimate and observation are inspectable side by side; both definitions are present."
        )

    return {"headline": headline, "limitations": limitations}


def _make_industrial_views_bundle(
    views: list[Mapping[str, Any]],
    *,
    account_generation: str = "synthetic-test",
) -> MiningOwnerBundle:
    """Test seam: build a MiningOwnerBundle that carries the given industrial views."""
    return MiningOwnerBundle(
        revision_tuple=(
            ("account_generation", account_generation),
            ("source", "synthetic-test-source"),
        ),
        rights_revision="synthetic-rights-test",
        assertions=(),
        identity_results=(),
        event_workspaces=(),
        financial_packets=(),
        interpretation_blocks=tuple(dict(v) for v in views),
        native_refs=(),
        omissions=(),
    )


def _add_omission(bundle: MiningOwnerBundle, omission: str) -> MiningOwnerBundle:
    """Test seam: extend a bundle's omission set with a closed vocabulary word."""
    from engine.market_ontology.mining_dependency_binding import OMISSION_REASONS

    if omission not in OMISSION_REASONS:
        raise ValueError(f"unknown omission word {omission!r}")
    current = tuple(bundle.omissions)
    if omission not in current:
        current = current + (omission,)
    return MiningOwnerBundle(
        revision_tuple=bundle.revision_tuple,
        rights_revision=bundle.rights_revision,
        assertions=bundle.assertions,
        identity_results=bundle.identity_results,
        event_workspaces=bundle.event_workspaces,
        financial_packets=bundle.financial_packets,
        interpretation_blocks=bundle.interpretation_blocks,
        native_refs=bundle.native_refs,
        omissions=current,
    )


# ---------------------------------------------------------------------------
# validate_mining_research — lazy jsonschema, owns its own CONTRACT_PATH
# ---------------------------------------------------------------------------


def validate_mining_research(payload: Mapping[str, Any]) -> None:
    """Validate a composed payload against the closed Mining schema.

    Lazy: the schema is read at call time so a missing or broken schema raises at
    the point the caller actually depends on it (mirrors ``validate_dossier``,
    technology_economic_change.py:298-318@pr/7891). The schema file is the
    single source of truth for the closed response shape.
    """
    schema = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(payload)


# ---------------------------------------------------------------------------
# compose_mining_research — the closed composition entry point
# ---------------------------------------------------------------------------


def _generation_for(query: MiningResearchQuery, bundle: MiningOwnerBundle) -> str:
    """Compute the closed generation string from the bundle's revision tuple."""
    for key, value in bundle.revision_tuple:
        if key == "account_generation":
            return f"{value}"
    # A revision tuple without an account_generation is malformed; this is a typed refusal.
    raise _MiningCompositionRefusal(
        "expected_generation_required",
        "bundle.revision_tuple must carry an account_generation pair",
    )


def _headline_for(
    status: str,
    *,
    limitations: list[str],
    domain_label: str,
) -> str:
    """Plain-language headline; never carries badge vocabulary."""
    if status == "refused":
        return f"{domain_label}: the response is refused for this revision."
    if "missing_issuer" in limitations:
        return f"{domain_label}: source is useful; the issuer axis is unresolved."
    if "source_only" in limitations:
        return f"{domain_label}: the source is retained; no economic packet is admitted."
    if "missing_basis" in limitations:
        return f"{domain_label}: the source figure is held while its reporting basis is absent."
    if "stream_threshold_unknown" in limitations:
        return (
            f"{domain_label}: the contract explanation is retained; the stream threshold is "
            "unknown."
        )
    if "changed_source" in limitations:
        return f"{domain_label}: a changed source is held; the bound interpretation is stale."
    if "page_generation_change" in limitations:
        return f"{domain_label}: the page generation changed between request and delivery."
    if "denied_source" in limitations:
        return f"{domain_label}: source rights deny display for this revision."
    if "industry_total_unknown" in limitations:
        return f"{domain_label}: the industry total is unknown; partial coverage is visible."
    return f"{domain_label}: the selected revisions are inspectable side by side."


def _summarize_status(
    limitations: list[str],
    *,
    has_native_blocks: bool,
) -> str:
    if "denied_source" in limitations:
        return "refused"
    # The contract explanation is retained even with no native block (PLAN §6 verbatim test);
    # MGD-18 / R-MIN-15: a missing threshold keeps the contract explanation -> ready.
    if "stream_threshold_unknown" in limitations:
        return "ready"
    if has_native_blocks:
        return "ready"
    if not limitations:
        return "degraded"
    return "degraded"


def compose_mining_research(
    query: MiningResearchQuery | Mapping[str, Any],
    bundle: MiningOwnerBundle | Mapping[str, Any],
    *,
    definition_version: str = "v1",
) -> dict[str, Any]:
    """Compose the closed Mining per-sector response and validate it on the way out.

    The function is pure: no I/O, no clock reads, no network. Refusals are typed
    (``MiningResearchRefusal``) and surface in the caller's try/except — they are
    never caught and silently downgraded here. The schema validator runs on every
    return path (R-MIN-22) including the ready, degraded and refused shapes.
    """
    if isinstance(query, Mapping):
        query = MiningResearchQuery(
            anchor_theme_id=query["anchor_theme_id"],
            slice_key=query["slice_key"],
            view=query.get("view", "economics"),
            time_mode=query.get("time_mode", "system_replay"),
            source_cutoff=query.get("source_cutoff"),
            recorded_cutoff=query.get("recorded_cutoff"),
            offset=query.get("offset", 0),
            limit=query.get("limit", 50),
            expected_generation=query.get("expected_generation"),
        )
    if isinstance(bundle, Mapping):
        bundle = MiningOwnerBundle(
            revision_tuple=tuple((str(k), str(v)) for k, v in bundle["revision_tuple"]),
            rights_revision=bundle["rights_revision"],
            assertions=tuple(bundle.get("assertions", ())),
            identity_results=tuple(bundle.get("identity_results", ())),
            event_workspaces=tuple(bundle.get("event_workspaces", ())),
            financial_packets=tuple(bundle.get("financial_packets", ())),
            interpretation_blocks=tuple(bundle.get("interpretation_blocks", ())),
            native_refs=tuple(bundle.get("native_refs", ())),
            omissions=tuple(bundle.get("omissions", ())),
        )

    # IR-04 — unknown versions refuse rather than collapse to v1.
    if definition_version not in VALID_DEFINITION_VERSIONS:
        raise _MiningCompositionRefusal(
            "unknown_definition_version",
            f"version {definition_version!r} is not in {sorted(VALID_DEFINITION_VERSIONS)}",
        )

    # Refusals for slice / theme / pagination / generation (R-MIN-24). A bundle that
    # carries the page_generation omission is a *supervised* generation change: the case
    # has labelled the mismatch; we propagate it as a page_generation_change limitation
    # rather than refusing with generation_changed. Any other competing generation is a
    # typed refusal.
    if "page_generation" in bundle.omissions:
        _validate_query_kernel(query, account_generation=None)
    else:
        _validate_query_kernel(query, account_generation=_generation_for(query, bundle))

    # Translate omission set -> closed limitation codes (R-MIN-30 / F3 colon-aware).
    limitations: list[str] = []
    for omission in bundle.omissions:
        code = OMISSION_TO_LIMITATION.get(omission)
        if code and code not in limitations:
            limitations.append(code)

    # MGD-09 — a missing issuer axis blocks any financial join. The native-block list is
    # suppressed in this case so the response cannot fabricate an issuer-bound block.
    # EVERY closed T04 limitation that is mapped from an omission code withdraws the
    # reported-economics channel: a missing basis, missing threshold, source-only, changed
    # source, denied source, missing issuer, missing_derivation (same-horizon revision),
    # and page_generation_change all collapse the native-block list to []; the contract
    # explanation survives as a limitation. The signed_loss case has no omission and keeps
    # its retained block (IR-02).
    _suppress_native_blocks = bool(
        set(limitations) & set(OMISSION_TO_LIMITATION.values())
    )

    # Build the closed native-blocks list. Unknown data is None, never zero; signed
    # values travel with their sign (MGD-15). Order is by stable source identity.
    # The block's stable_subject_id is bound to the bundle's identity_results
    # (issuer axis) — never the literal "subject:unknown" fallback that hid
    # MAJOR-9's degenerate ordering. A packet carrying its own non-empty
    # stable_subject_id keeps it; otherwise we use the identity sid.
    identity_sid = "subject:unknown"
    for ident in bundle.identity_results:
        cand = str(ident.get("stable_subject_id") or ident.get("cik") or "")
        if cand:
            identity_sid = cand
            break
    raw_blocks: list[dict[str, Any]] = []
    if not _suppress_native_blocks:
        for packet in bundle.financial_packets:
            packet_sid = str(packet.get("stable_subject_id") or "")
            if not packet_sid or packet_sid == "subject:unknown":
                packet_sid = identity_sid
            raw_blocks.append(
                {
                    "stable_subject_id": packet_sid,
                    "measure": str(packet.get("measure", "")),
                    "value": _signed_value(packet),
                    "sign": "+" if (_signed_value(packet) or 0) >= 0 else "-",
                    "basis": str(packet.get("basis", "") or "fictional reported dollars"),
                    "source_label": str(
                        packet.get("source_label", packet.get("selection_label", "") or "synthetic-source")
                    ),
                }
            )
    native_blocks = _order_rows_by_stable_source_identity(raw_blocks)

    # Native subjects come from identity_results (a stable_subject_id axis) and never
    # from a guess — a source-only case keeps no subject axis (MGD-11).
    native_subjects: list[dict[str, Any]] = []
    for ident in bundle.identity_results:
        sid = str(ident.get("stable_subject_id") or ident.get("cik") or "subject:unknown")
        native_subjects.append(
            {
                "stable_subject_id": sid,
                "kind": str(ident.get("kind", "issuer")),
                "label": str(ident.get("name") or ident.get("label") or sid),
            }
        )

    companies: list[dict[str, Any]] = []
    for ident in bundle.identity_results:
        sid = str(ident.get("stable_subject_id") or ident.get("cik") or "subject:unknown")
        cik = str(ident.get("cik", ""))
        if not cik:
            # missing_issuer is the limitation for an empty CIK; do NOT invent one.
            if "missing_issuer" not in limitations:
                limitations.append("missing_issuer")
            continue
        companies.append(
            {
                "stable_subject_id": sid,
                "name": str(ident.get("name", "")),
                "cik": cik,
                "role": "issuer",
            }
        )

    # Industrial views are pulled from interpretation_blocks verbatim and ordered by
    # stable_subject_id (PLAN:203). Duplicate local asset labels stay visible but are
    # never additional supply (MGD-12).
    industrial_views: list[dict[str, Any]] = []
    for view in bundle.interpretation_blocks:
        industrial_views.append(
            {
                "stable_subject_id": str(view.get("stable_subject_id", "subject:unknown")),
                "view_kind": str(view.get("view_kind", "industrial")),
                "description": str(view.get("description", "")),
                "evidence_refs": [str(r) for r in view.get("evidence_refs", [])],
            }
        )
    industrial_views = _order_rows_by_stable_source_identity(industrial_views)

    # Evidence refs are derived from native_refs; authority is echoed on every object.
    evidence_refs: list[dict[str, Any]] = []
    for ref in bundle.native_refs:
        evidence_refs.append(
            {
                "stable_source_id": str(ref.get("digest") or ref.get("stable_source_id") or "source:unknown"),
                "url": str(ref.get("url", "")),
                "rights_revision": str(ref.get("rights_revision", bundle.rights_revision)),
                "native_subject_id": str(ref.get("native_subject_id", "subject:unknown")),
                "rights_entitled": bool(ref.get("rights_entitled", True)),
                "digest": str(ref.get("digest", "")),
                "authority": dict(AUTHORITY),
            }
        )

    # Expectations are bound from the CLOSED domain definition for the queried
    # slice (R-MIN-23 / BLOCKER-1 / seat note). The bundle's financial_packets no
    # longer influence expectation composition: every ``management_estimate_vs_actual``
    # claim — and its single ``pairs`` object on the COPPER block — is read from
    # ``MINING_DEFINITIONS[query.slice_key]``. Management point estimates stay
    # point estimates (ADDENDUM §4 IR-02). A row may carry null
    # ``earlier_point_estimate`` / ``later_actual`` (W-R), in which case
    # ``missing_derivation`` is the limitation — never an invented zero.
    expectations: list[dict[str, Any]] = []
    slice_def = MINING_DEFINITIONS[query.slice_key]
    mev = slice_def.get("management_estimate_vs_actual") or {}

    # Subject identity is bound to the first identity_results entry; the
    # open fallback stays as a literal default (Step 7 finishes the binding
    # for the native_blocks channel; here we only need a non-empty
    # stable_subject_id so the schema item stays valid).
    subject_id = "subject:unknown"
    for ident in bundle.identity_results:
        cand = str(ident.get("stable_subject_id") or "")
        if cand:
            subject_id = cand
            break

    def _leg(leg: Mapping[str, Any] | None) -> dict[str, Any] | None:
        """Map a domain-yaml leg object to the schema-valid leg dict.

        The yaml leg carries ``metric / source_family / selection_label /
        period_kind / definition_fields_required``. The schema item requires
        ``metric / value / basis / source_label`` — all four required, with
        ``metric / basis / source_label`` typed string minLength: 1.
        ``value`` accepts a number, integer or string. ``source_label`` falls
        back to ``selection_label``. ``value`` falls back to the metric or
        period_kind string when the leg has no literal number.
        ``basis`` falls back to "fictional point estimate" for the
        management-issued estimate legs (they have no reported basis yet).
        """
        if leg is None or not isinstance(leg, Mapping):
            return None
        metric = str(leg.get("metric") or "")
        if not metric:
            return None
        basis = str(leg.get("basis") or "fictional point estimate")
        source_label = str(
            leg.get("source_label")
            or leg.get("selection_label")
            or "synthetic-selection"
        )
        raw_value = leg.get("value")
        if raw_value is None:
            raw_value = str(leg.get("period_kind") or leg.get("metric") or "")
        return {
            "metric": metric,
            "value": raw_value,
            "basis": basis,
            "source_label": source_label,
        }

    def _unq(leg: Mapping[str, Any] | None) -> list[str]:
        if leg is None or not isinstance(leg, Mapping):
            return []
        return [str(f) for f in (leg.get("definition_fields_required") or [])]

    def _expectation_row(
        epe: Mapping[str, Any] | None,
        la: Mapping[str, Any] | None,
        comparison: str,
        unq_fields: list[str],
    ) -> dict[str, Any]:
        return {
            "stable_subject_id": subject_id,
            "comparison_kind": "earlier_point_estimate_vs_later_actual",
            "earlier_point_estimate": _leg(epe),
            "later_actual": _leg(la),
            "comparison": comparison,
            "definition_unqualified_fields": list(unq_fields),
            "is_range": False,
            "is_consensus": False,
        }

    # The closed defined_fields: union of every leg's definition_fields_required
    # across the mev + its pairs. Falls back to the canonical closed set when the
    # yaml drops the field.
    defined_fields: set[str] = set()
    for leg in (mev.get("earlier_point_estimate"), mev.get("later_actual")):
        for f in _unq(leg):
            defined_fields.add(f)
    for pair in mev.get("pairs", []) or []:
        for leg in (pair.get("earlier_point_estimate"), pair.get("later_actual")):
            for f in _unq(leg):
                defined_fields.add(f)
    if not defined_fields:
        defined_fields = {"basis", "unit", "perimeter"}

    if mev:
        main_epe = mev.get("earlier_point_estimate")
        main_la = mev.get("later_actual")
        main_comparison = str(mev.get("comparison", "") or "")
        main_unq = _unq(main_epe) + _unq(main_la)
        expectations.append(
            _expectation_row(main_epe, main_la, main_comparison, main_unq)
        )
        # W-R null legs -> missing_derivation limitation (R-MIN-15 / BLOCKER-1).
        if main_epe is None and main_la is None:
            if "missing_derivation" not in limitations:
                limitations.append("missing_derivation")
        # The COPPER block carries a single ``pairs`` object surfaced as a SECOND
        # comparison row, never merged with the sales pair (seat note / BLOCKER-1).
        pairs = mev.get("pairs", []) or []
        for pair in pairs:
            pair_epe = pair.get("earlier_point_estimate")
            pair_la = pair.get("later_actual")
            pair_comparison = str(pair.get("comparison", "") or main_comparison)
            pair_unq = _unq(pair_epe) + _unq(pair_la)
            expectations.append(
                _expectation_row(pair_epe, pair_la, pair_comparison, pair_unq)
            )
    else:
        # A slice with no mev declared at all: surface as missing_derivation;
        # no expectation row is invented.
        if "missing_derivation" not in limitations:
            limitations.append("missing_derivation")

    # IR-01: limitations now include any definition_unqualified:<field> markers; headline must
    # stay plain-language without badge vocabulary.
    summary_block = _summarize_expectations(expectations, defined_fields=defined_fields)
    for code in summary_block["limitations"]:
        if code not in limitations:
            limitations.append(code)

    domain_label = MINING_DEFINITIONS[query.slice_key]["anchor_theme_id"]
    status = _summarize_status(limitations, has_native_blocks=bool(native_blocks))
    headline = _headline_for(status, limitations=limitations, domain_label=domain_label)
    # Belt-and-braces: assert the headline contains no badge vocabulary.
    lowered = headline.lower()
    for word in _BADGE_VOCABULARY:
        if word in lowered:
            raise _MiningCompositionRefusal(
                "headline_uses_badge_vocabulary",
                f"headline {headline!r} contains forbidden token {word!r}",
            )

    payload: dict[str, Any] = {
        "schema": _SCHEMA_ID,
        "definition_version": definition_version,
        "generation": _generation_for(query, bundle),
        "request": {
            "slice_key": query.slice_key,
            "anchor_theme_id": query.anchor_theme_id,
            "replay_cutoff": str(query.recorded_cutoff or ""),
            "page": int(query.offset // max(query.limit, 1)) + 1,
        },
        "native_subjects": native_subjects,
        "summary": {
            "status": status,
            "headline": headline,
            "selected_revisions": [list(pair) for pair in bundle.revision_tuple],
        },
        "companies": companies,
        "industrial_views": industrial_views,
        "economics": {
            "status": status,
            "native_blocks": native_blocks,
            "reported_economic_context": {
                "policy": "reported_economic_context",
                "context_block_count": len(native_blocks),
                "notes": (
                    "Native financial blocks travel with their sign; unknown data is never zero; "
                    "industry_total is null until admitted."
                ),
            },
            "derived": [],
        },
        "expectations": expectations,
        "evidence_refs": evidence_refs,
        "authorized_coverage": {
            "count_scope": "two_closed_definitions",
            "industry_total": None,
        },
        "limitations": limitations,
        "authority": dict(AUTHORITY),
    }

    # R-MIN-22: validate on every return path. This is the contract; do not remove.
    validate_mining_research(payload)
    return payload


# ---------------------------------------------------------------------------
# select_mining_evidence — bind mechanism/counter-thesis to the exact revisions
# ---------------------------------------------------------------------------


def select_mining_evidence(
    query: MiningResearchQuery | Mapping[str, Any],
    bundle: MiningOwnerBundle | Mapping[str, Any],
    assertion_ref: str,
) -> dict[str, Any]:
    """Return an evidence drawer object bound to the bundle's selected revisions.

    A refresh that pairs changed quantities with stale causal text refuses with
    ``interpretation_stale`` (PLAN §6 T04 last bullet; ADDENDUM §4 IR-01). The
    ``authority`` const is echoed on every evidence object (R-MIN-25).
    """
    omissions = tuple(getattr(bundle, "omissions", ()) or ())
    mapped = {OMISSION_TO_LIMITATION.get(o) for o in omissions}
    if "changed_source" in mapped:
        raise _MiningCompositionRefusal(
            "interpretation_stale",
            "the bound source revision changed; a refresh cannot pair changed quantities with stale causal text",
        )

    if isinstance(query, Mapping):
        query = MiningResearchQuery(
            anchor_theme_id=query["anchor_theme_id"],
            slice_key=query["slice_key"],
            view=query.get("view", "economics"),
            time_mode=query.get("time_mode", "system_replay"),
            source_cutoff=query.get("source_cutoff"),
            recorded_cutoff=query.get("recorded_cutoff"),
            offset=query.get("offset", 0),
            limit=query.get("limit", 50),
            expected_generation=query.get("expected_generation"),
        )
    if isinstance(bundle, Mapping):
        bundle = MiningOwnerBundle(
            revision_tuple=tuple((str(k), str(v)) for k, v in bundle["revision_tuple"]),
            rights_revision=bundle["rights_revision"],
            assertions=tuple(bundle.get("assertions", ())),
            identity_results=tuple(bundle.get("identity_results", ())),
            event_workspaces=tuple(bundle.get("event_workspaces", ())),
            financial_packets=tuple(bundle.get("financial_packets", ())),
            interpretation_blocks=tuple(bundle.get("interpretation_blocks", ())),
            native_refs=tuple(bundle.get("native_refs", ())),
            omissions=tuple(bundle.get("omissions", ())),
        )

    payload = {
        "assertion_ref": assertion_ref,
        "slice_key": query.slice_key,
        "anchor_theme_id": query.anchor_theme_id,
        "selected_revisions": [list(pair) for pair in bundle.revision_tuple],
        "evidence_refs": [
            {
                "stable_source_id": str(ref.get("digest") or ref.get("stable_source_id") or "source:unknown"),
                "url": str(ref.get("url", "")),
                "rights_revision": str(ref.get("rights_revision", bundle.rights_revision)),
                "native_subject_id": str(ref.get("native_subject_id", "subject:unknown")),
                "rights_entitled": bool(ref.get("rights_entitled", True)),
                "digest": str(ref.get("digest", "")),
                "authority": dict(AUTHORITY),
            }
            for ref in bundle.native_refs
        ],
        "authority": dict(AUTHORITY),
    }
    return payload


# ---------------------------------------------------------------------------
# Belt-and-braces: ensure no kernel module accidentally got pulled in
# ---------------------------------------------------------------------------

# This module must NEVER import the shared semiconductor / theme_graph kernel.
# R-MIN-21 / R-MIN-26: the composition is Mining-owned; if a future refactor adds
# such a line the test suite fails closed via the grep proof test. We do not
# re-export or alias any kernel name here.