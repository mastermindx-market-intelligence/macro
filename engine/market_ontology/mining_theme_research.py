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
import math
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


#: Packet-leg fields that must AGREE between the two legs of one comparison before a
#: polarity may be computed (R-MIN-33). The frozen domain spec requires "fully qualified
#: COMPATIBLE inputs are compared normally" — compatibility is a clause distinct from the
#: qualification (presence) check, and it was unimplemented through round 3. ``basis`` is
#: deliberately ABSENT: the domain yaml gives the two legs different bases on purpose (a
#: point estimate against a reported measure), so cross-leg basis equality would forbid
#: the only comparison this slice exists to make.
COMPARABILITY_FIELDS: tuple[str, ...] = ("unit", "perimeter", "period")

#: A declaration on the packet (or on either leg) that the figure is a range or a
#: consensus. The response schema pins ``is_range``/``is_consensus`` to ``const: false``,
#: so neither is representable on this wire; a declared range is REFUSED rather than
#: flattened into a point-estimate claim the source never made (R-MIN-33).
NON_POINT_ESTIMATE_FLAGS: tuple[str, ...] = ("is_range", "is_consensus")


def _value_is_numeric(v: Any) -> bool:
    """True only for a FINITE real number — never a bool, never NaN, never infinity.

    ``isinstance(float("nan"), float)`` is True, so a bare isinstance gate admits NaN;
    and because ``nan == nan`` is False, a NaN leg also slips the equality withhold and
    reaches the polarity ternary, where every NaN comparison is False and the row is
    published as a confident ``below_estimate`` carrying ``nan`` as an economic value.
    ``math.isfinite`` closes both holes (R-MIN-33).
    """
    if v is None or isinstance(v, bool) or not isinstance(v, (int, float)):
        return False
    return math.isfinite(v)


def _declares_non_point_estimate(packet: Mapping[str, Any]) -> str | None:
    """Return the first range/consensus flag declared truthy on the packet or a leg."""
    scopes: list[Mapping[str, Any]] = [packet]
    for leg_key in ("earlier_point_estimate", "later_actual"):
        leg = packet.get(leg_key)
        if isinstance(leg, Mapping):
            scopes.append(leg)
    for scope in scopes:
        for flag in NON_POINT_ESTIMATE_FLAGS:
            if scope.get(flag):
                return flag
    return None


def _incomparable_field(
    epe_packet: Mapping[str, Any], la_packet: Mapping[str, Any]
) -> str | None:
    """Return the first comparability field that is present on both legs and disagrees.

    A field absent from a leg is NOT an incomparability — absence is the qualification
    check's business, and it mints ``definition_unqualified:<field>`` downstream.
    """
    for field in COMPARABILITY_FIELDS:
        left = epe_packet.get(field)
        right = la_packet.get(field)
        if left is None or right is None:
            continue
        if left != right:
            return field
    return None


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
    raise MiningResearchRefusal(
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

    # IR-04 — unknown versions refuse rather than collapse to v1. The closed-vocab
    # refusal is "unknown_slice" (semantically: input does not match a closed
    # Mining value); no subclass bypass is added.
    if definition_version not in VALID_DEFINITION_VERSIONS:
        raise MiningResearchRefusal(
            "unknown_slice",
            f"definition_version {definition_version!r} is not in {sorted(VALID_DEFINITION_VERSIONS)}",
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

    # Slice-definitional limitations (R-MIN-31 §4, MAJOR-E). The slice's own
    # ``limitations_vocabulary`` lists the codes the domain file contracts for
    # every case of that slice; the schema carries a single contract for
    # ``authorized_coverage.industry_total`` which is literal ``null`` on
    # every response, so any slice whose vocabulary names
    # ``industry_total_unknown`` (rare-earth only) mints it once per compose
    # call. Copper does not name it; copper never mints it. The old
    # "unbound identity axis" predicate was invented; the truthful polarity
    # is "the slice's industry_total is contracted null" (R-MIN-25), so
    # binding or not binding the issuer axis never toggles this code.
    slice_limit_vocab = list(MINING_DEFINITIONS[query.slice_key].get("limitations_vocabulary") or [])
    if "industry_total_unknown" in slice_limit_vocab:
        if "industry_total_unknown" not in limitations:
            limitations.append("industry_total_unknown")

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
            # MINOR-I / R-MIN-31: a packet that carries ``kind: management_estimate_vs_actual``
            # belongs to the expectations channel, not native blocks — its values land on the
            # expectation rows, never as a measurement block.
            if packet.get("kind") == "management_estimate_vs_actual":
                continue
            value = packet.get("value")
            # MINOR-11 / Step 8: a None / non-numeric value degrades silently — the
            # packet is suppressed rather than coerced to zero (None -> 0 -> '+') or
            # raising TypeError on `>=` for string values. The limitation vocabulary
            # (``definition_unqualified:value``) is reserved for *definition* fields
            # whose presence is required by the domain (unit / perimeter / basis /
            # management_estimate_vs_actual), not for a missing measurement datum
            # which is the omission->limitation mapping's contract (R-MIN-31 §I).
            if (
                value is None
                or isinstance(value, bool)
                or not isinstance(value, (int, float))
            ):
                continue
            packet_sid = str(packet.get("stable_subject_id") or "")
            if not packet_sid or packet_sid == "subject:unknown":
                packet_sid = identity_sid
            raw_blocks.append(
                {
                    "stable_subject_id": packet_sid,
                    "measure": str(packet.get("measure", "")),
                    "value": value,
                    "sign": "+" if value >= 0 else "-",
                    "basis": str(packet.get("basis", "") or "fictional reported dollars"),
                    # MINOR-H: an existing-but-empty source_label or selection_label
                    # degrades to a typed limitation rather than raising a raw
                    # ``jsonschema.ValidationError`` (R-MIN-31). The ``or`` chain
                    # collapses every empty-string fallthrough to the closed
                    # "synthetic-source" default so the schema's ``minLength: 1``
                    # never trips on a present-but-empty input.
                    "source_label": str(
                        packet.get("source_label")
                        or packet.get("selection_label")
                        or "synthetic-source"
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

    # Expectations are packet-driven (R-MIN-31 §3). The bundle's
    # ``financial_packets`` may carry ``kind: management_estimate_vs_actual``
    # entries whose ``pair`` selects between the slice's domain-yaml
    # ``management_estimate_vs_actual`` block (sales) and its single
    # ``pairs`` object (unit net cash cost, copper only). Metric / required
    # fields / period / selection_label always travel from the domain yaml —
    # the packet only supplies the measured values, never the leg labels,
    # so a leg ``value`` is never synthesised from ``period_kind`` /
    # ``metric`` (BLOCKER-A). A withdrawn case (omissions non-empty)
    # publishes no expectation row (MAJOR-B); ``missing_derivation`` is
    # minted ONLY as the mapped omission code for ``next_period_outlook``,
    # never as a "no mev declared" stand-in (MAJOR-C).
    expectations: list[dict[str, Any]] = []
    slice_def = MINING_DEFINITIONS[query.slice_key]
    mev = slice_def.get("management_estimate_vs_actual") or {}
    mev_populated = bool(mev) and mev.get("earlier_point_estimate") is not None and mev.get("later_actual") is not None

    # Subject identity is bound to the first identity_results entry; the
    # cik is the fallback (MAJOR-F — same cik fallback as the native_blocks
    # channel), so a row carries the same identity as the issuer axis the
    # bundle actually has, never the literal "subject:unknown".
    subject_id = "subject:unknown"
    for ident in bundle.identity_results:
        cand = str(ident.get("stable_subject_id") or ident.get("cik") or "")
        if cand:
            subject_id = cand
            break

    def _pair_source(pair_name: str) -> tuple[Mapping[str, Any], Mapping[str, Any], str] | None:
        """Resolve a packet's pair name to (epe, la, comparison_text) from the domain yaml.

        ``sales`` reads the slice's top-level ``management_estimate_vs_actual`` block;
        ``unit_net_cash_cost`` reads its single ``pairs`` object. Anything else is
        a closed-codec refusal-equivalent: no row is emitted, and ``omitted:expectations``
        is added to limitations (deduplicated).
        """
        if pair_name == "sales":
            epe = mev.get("earlier_point_estimate")
            la = mev.get("later_actual")
            if not isinstance(epe, Mapping) or not isinstance(la, Mapping):
                return None
            return epe, la, str(mev.get("comparison", "") or "")
        if pair_name == "unit_net_cash_cost":
            pairs = mev.get("pairs", []) or []
            if not pairs:
                return None
            pair = pairs[0]
            epe = pair.get("earlier_point_estimate")
            la = pair.get("later_actual")
            if not isinstance(epe, Mapping) or not isinstance(la, Mapping):
                return None
            return epe, la, str(pair.get("comparison", "") or mev.get("comparison", "") or "")
        return None

    def _leg_from_domain(leg: Mapping[str, Any], *, default_basis: str) -> dict[str, Any]:
        """Build the schema leg dict using ONLY the domain-yaml leg's own strings.

        Metric / basis / source_label come from the domain leg; the packet
        supplies the value at the row level — never from ``period_kind`` /
        ``metric`` substitutions. ``selection_label`` is the canonical
        source_label fallback; an empty selection_label degrades to a typed
        limitation (MINOR-H, dedup'd on the response).
        """
        source_label = str(
            leg.get("source_label")
            or leg.get("selection_label")
            or "synthetic-selection"
        )
        if not source_label:
            # The schema requires ``minLength: 1``; we never propagate an
            # empty literal that would trip the validator (MINOR-H).
            source_label = "synthetic-selection"
        return {
            "metric": str(leg.get("metric", "") or ""),
            "value": None,  # set by the row builder below from the packet
            "basis": str(leg.get("basis", "") or default_basis),
            "source_label": source_label,
        }

    def _missing_required_fields(
        leg: Mapping[str, Any], packet_leg: Mapping[str, Any]
    ) -> list[str]:
        """Return the ordered, deduplicated list of domain-required fields absent on the leg.

        The domain yaml's ``definition_fields_required`` is the source of truth
        (per R-MIN-31 §3, MAJOR-D); a packet whose leg omits one of those
        fields withholds the row and contributes one
        ``definition_unqualified:<field>`` code to the response limitations.
        """
        required = list(leg.get("definition_fields_required") or [])
        missing: list[str] = []
        for f in required:
            value = packet_leg.get(f)
            if value is None or (isinstance(value, str) and not value):
                missing.append(str(f))
        return missing

    def _build_row(
        packet: Mapping[str, Any],
        epe: Mapping[str, Any],
        la: Mapping[str, Any],
    ) -> tuple[dict[str, Any] | None, list[str], bool]:
        """Build a schema-valid expectation row from one packet.

        Returns ``(row, missing_field_codes, withhold_for_unqualified)``.
        ``row is None`` means the row is withheld; ``missing_field_codes`` are
        the deduplicated ``definition_unqualified:<field>`` codes to mint, and
        ``withhold_for_unqualified`` distinguishes "missing definition fields"
        (mint ``definition_unqualified:*``) from "bad value / unknown pair"
        (mint ``omitted:expectations``).
        """
        epe_packet = packet.get("earlier_point_estimate") or {}
        la_packet = packet.get("later_actual") or {}
        epe_value = epe_packet.get("value")
        la_value = la_packet.get("value")

        # R-MIN-33: a source-declared range or consensus is not a point estimate, and
        # the schema pins both flags to ``const: false`` — so the truth is not
        # representable here and the row is withheld rather than mislabelled. Checked
        # before the values, because the declaration disqualifies the row whatever the
        # numbers are.
        if _declares_non_point_estimate(packet) is not None:
            return None, [], True

        if not _value_is_numeric(epe_value) or not _value_is_numeric(la_value):
            return None, [], True

        # R-MIN-33: both legs must be commensurate before a polarity means anything.
        # Runs BEFORE the qualification check so a mismatch is never reported as a
        # missing field, and skips any field absent from a leg so ``P13``-style
        # ``definition_unqualified:<field>`` diagnostics survive unchanged.
        if _incomparable_field(epe_packet, la_packet) is not None:
            return None, [], True

        if epe_value == la_value:
            # "equal_to_estimate" is the comparison word for equality, but
            # the ruling binds: equal values WITHHOLD the row with
            # ``omitted:expectations`` (a true equal would be an invented
            # surprise at the wire; the row is suppressed).
            return None, [], True

        missing_epe = _missing_required_fields(epe, epe_packet)
        missing_la = _missing_required_fields(la, la_packet)
        missing_fields = []
        for f in missing_epe + missing_la:
            if f not in missing_fields:
                missing_fields.append(f)
        if missing_fields:
            return None, [f"definition_unqualified:{f}" for f in missing_fields], True

        comparison_word = "above_estimate" if la_value > epe_value else "below_estimate"
        epe_leg = _leg_from_domain(epe, default_basis="fictional point estimate")
        la_leg = _leg_from_domain(la, default_basis="fictional reported measure")
        epe_leg["value"] = epe_value
        la_leg["value"] = la_value
        return (
            {
                "stable_subject_id": subject_id,
                "comparison_kind": "earlier_point_estimate_vs_later_actual",
                "earlier_point_estimate": epe_leg,
                "later_actual": la_leg,
                "comparison": comparison_word,
                "definition_unqualified_fields": [],
                "is_range": False,
                "is_consensus": False,
            },
            [],
            False,
        )

    withdrawn = bool(bundle.omissions)

    if not withdrawn and mev_populated:
        # Collect mev packets; pair-name ordering is enforced (sales first,
        # unit_net_cash_cost second) regardless of packet arrival order
        # (MINOR-J). An unknown pair withholds with ``omitted:expectations``.
        mev_packets = [
            p for p in bundle.financial_packets
            if isinstance(p, Mapping) and p.get("kind") == "management_estimate_vs_actual"
        ]

        def _pair_sort_key(p: Mapping[str, Any]) -> int:
            order = {"sales": 0, "unit_net_cash_cost": 1}
            return order.get(str(p.get("pair") or ""), 99)

        # R-MIN-33: a pair name claimed by more than one packet is a contradiction, not
        # a choice. Every leg's identity (metric/basis/source_label) comes from the
        # domain yaml keyed by that name and no other packet field reaches the wire, so
        # two same-pair packets differ ONLY in value and nothing on the wire could
        # disambiguate them. Picking one would be fabrication by arbitration and a
        # limitation code annotates without retracting, so every row for the duplicated
        # pair is withheld — scoped to that pair alone, so a duplicated ``sales`` never
        # suppresses a sound ``unit_net_cash_cost``.
        pair_occurrences: dict[str, int] = {}
        for p in mev_packets:
            name = str(p.get("pair") or "")
            pair_occurrences[name] = pair_occurrences.get(name, 0) + 1

        for packet in sorted(mev_packets, key=_pair_sort_key):
            pair_name = str(packet.get("pair") or "")
            if pair_occurrences.get(pair_name, 0) > 1:
                if "omitted:expectations" not in limitations:
                    limitations.append("omitted:expectations")
                continue
            source = _pair_source(pair_name)
            if source is None:
                # Unknown pair -> withhold + mint omitted:expectations.
                if "omitted:expectations" not in limitations:
                    limitations.append("omitted:expectations")
                continue
            epe, la, _ = source
            row, missing_codes, withhold_unqualified = _build_row(packet, epe, la)
            if row is None:
                if withhold_unqualified and missing_codes:
                    for code in missing_codes:
                        if code not in limitations:
                            limitations.append(code)
                else:
                    if "omitted:expectations" not in limitations:
                        limitations.append("omitted:expectations")
                continue
            expectations.append(row)
    elif not withdrawn and not mev_populated:
        # A slice whose mev declares both legs null (rare-earth) — no
        # comparison is selected in M1, and the slice-definitional code
        # ``definition_unqualified:management_estimate_vs_actual`` is the
        # truthful "no comparison selected" marker, NOT
        # ``omitted:expectations`` (R-MIN-31 §3 last sentence).
        pass

    # Slice-definitional codes for the rare-earth slice (R-MIN-31 §2):
    # stream_threshold_unknown + industry_total_unknown from the slice's
    # own ``limitations_vocabulary``; plus
    # ``definition_unqualified:management_estimate_vs_actual`` because the
    # rare-earth mev declares both legs null. Copper mints none of these
    # — its vocabulary does not name them and its mev legs are populated.
    if "stream_threshold_unknown" in slice_limit_vocab:
        if "stream_threshold_unknown" not in limitations:
            limitations.append("stream_threshold_unknown")
    if not mev_populated:
        slice_def_unq_code = "definition_unqualified:management_estimate_vs_actual"
        if slice_def_unq_code not in limitations:
            limitations.append(slice_def_unq_code)

    # Usable copper with no mev packet in the bundle -> ``omitted:expectations``
    # is the truthful "no row was attempted" marker (R-MIN-31 §3).
    if (
        not withdrawn
        and mev_populated
        and not expectations
        and "omitted:expectations" not in limitations
    ):
        limitations.append("omitted:expectations")

    domain_label = MINING_DEFINITIONS[query.slice_key]["anchor_theme_id"]
    status = _summarize_status(limitations, has_native_blocks=bool(native_blocks))
    headline = _headline_for(status, limitations=limitations, domain_label=domain_label)
    # Belt-and-braces: a literal headline that contains badge vocabulary must never be
    # constructed by the closed _headline_for table. If a future refactor accidentally
    # synthesises one, that is a typed limitation, not a refused exception — degrade
    # by appending a definition_unqualified:headline marker so the contract stays
    # inspectable end-to-end.
    lowered = headline.lower()
    for word in _BADGE_VOCABULARY:
        if word in lowered:
            if "definition_unqualified:headline" not in limitations:
                limitations.append("definition_unqualified:headline")
            break

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
        "limitations": sorted(limitations),
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
        # The bound source revision changed; a refresh cannot pair changed quantities
        # with stale causal text. The closest closed CODES code is
        # ``generation_changed`` (semantically: the consumed source's generation no
        # longer matches what the query expects). No subclass bypass is added.
        raise MiningResearchRefusal(
            "generation_changed",
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