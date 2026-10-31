"""Relationship observation package v2 — the derivation from pinned extraction rows.

Pure module: no network, no wall clock, no store.  ``computed_at`` is the caller's
``--as-of`` instant, never "now".  The v1 relationship-observation module
(``engine.company_intelligence.relationship_observations``) is untouched; this is
its versioned successor and re-declares its purpose/content-boundary dicts
identically (contracts 3/4 const-pin every value) instead of importing the C01
chain behind v1.

Every derived fact here is transcription or bookkeeping over rows that are already
hash-pinned: directed edges keyed to named counterparties, magnitude revisions that
are never summed, averaged or netted, document-scoped non-edges, and correction
lineage from document assessments.  A row published after ``as_of`` leaves no trace
of any kind.  Nothing in the output scores, ranks, sizes, gates or predicts.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime, timedelta, timezone

from engine.company_intelligence.relationships.clock import (
    ClockRefused,
    et_acceptance_to_utc,
)
from lib.dataos.temporal import TemporalProfile, as_of_filter

PACKAGE_SCHEMA = "company_intelligence.relationship_observation_package/v2"
EDGES_SCHEMA = "company_intelligence.relationship_edges/v1"

#: The closed species set.  Anything else is refused with
#: ``relationship-species-refused`` (the extraction schema's enum excludes it too).
#: species -> (from_role, to_role, default subject_role, theme_graph_mapping)
SPECIES_ROLES = {
    "supplier_customer": ("supplier", "customer", "supplier", "SUPPLIES"),
    "contract_manufacturing": ("manufacturer", "client", "manufacturer", "SUPPLIES"),
    "licensing": ("licensor", "licensee", "licensor", "NO_MAPPING"),
    "distribution": ("manufacturer", "distributor", "manufacturer", "SUPPLIES"),
    "component_dependency": ("provider", "dependent", "provider", "SUPPLIES"),
}

FRESHNESS_DAYS = 456
EXCERPT_PATH_TEMPLATE = (
    "research/theme_graph/gmi_relationships_20261021/sources/{accession}.json"
)
#: Sentinel for the ``excerpts`` map: the caller knows the file fails verification.
CORRUPT = "corrupt"

_PACKAGE_SHA_PLACEHOLDER = "0" * 64


# --- canonicalization and identity formulas ---------------------------------


def canon(value) -> str:
    """The one canonical JSON form used by every identity formula."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(text) -> str:
    """sha256 of a str (utf-8) or bytes, as lowercase hex."""
    data = text.encode("utf-8") if isinstance(text, str) else text
    return hashlib.sha256(data).hexdigest()


def observation_identity(
    accession: str,
    byte_start: int,
    byte_end: int,
    species: str,
    subject_issuer_id,
    object_issuer_id,
) -> str:
    return "obs:" + sha(
        canon(
            [
                accession,
                byte_start,
                byte_end,
                species,
                subject_issuer_id,
                object_issuer_id,
            ]
        )
    )[:20]


def assessment_identity(
    accession: str, byte_start: int, byte_end: int, assessment: str
) -> str:
    return "asm:" + sha(
        canon([accession, byte_start, byte_end, assessment])
    )[:20]


def relationship_identity(
    species: str, from_issuer_id: str, to_issuer_id: str, product_key: str
) -> str:
    return "rel:" + sha(
        canon([species, from_issuer_id, to_issuer_id, product_key])
    )[:20]


def non_edge_identity(
    accession: str, species: str, label, reason: str
) -> str:
    return "nonedge:" + sha(canon([accession, species, label, reason]))[:20]


def revision_identity(
    relationship_key: str,
    kind: str,
    period_start,
    period_end: str,
    asserting_party: str,
    revision_seq: int,
) -> str:
    return "rev:" + sha(
        canon(
            [
                relationship_key,
                kind,
                period_start,
                period_end,
                asserting_party,
                revision_seq,
            ]
        )
    )[:20]


def package_identity(as_of: str, manifest_version: str, input_sha256s) -> str:
    return "pkg:" + sha(
        canon([as_of, manifest_version, sorted(input_sha256s)])
    )[:20]


def normalize_span(raw: bytes) -> str:
    """The one span normalization: strip tags, unescape entities, squeeze space."""
    text = re.sub(rb"<[^>]+>", b"", raw).decode("utf-8")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


# --- instants ----------------------------------------------------------------


def _instant_dt(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _known_at(row: dict) -> str:
    """coalesce(published_at, ingested_at) — the row's own canonical string."""
    return row.get("published_at") or row.get("ingested_at")


def _pit_visible(rows, as_of_dt: datetime) -> list[dict]:
    """The PIT law's as_of reader over extraction rows (REVISABLE_RELEASE).

    Shallow copies carry ``revision_seq=0`` because the profile declares it; the
    extraction rows themselves never mutate.
    """
    copies = []
    for row in rows:
        copy = dict(row)
        copy.setdefault("revision_seq", 0)
        copies.append(copy)
    return as_of_filter(copies, as_of_dt, TemporalProfile.REVISABLE_RELEASE)


# --- manifest ----------------------------------------------------------------


def load_manifest_issuers(manifest_path) -> tuple[str, dict]:
    """(manifest_version, {issuer_id: sorted security_ids}) from the universe manifest."""
    with open(manifest_path, "rb") as handle:
        manifest = json.loads(handle.read().decode("utf-8"))
    securities = manifest["core_markets"]["us"]["securities"]
    columns = securities["columns"].split("|")
    issuers: dict = {}
    for pipe_row in securities["rows"]:
        record = dict(zip(columns, pipe_row.split("|")))
        issuers.setdefault(record["issuer_id"], []).append(record["security_id"])
    return manifest["manifest_version"], {
        issuer_id: sorted(ids) for issuer_id, ids in issuers.items()
    }


# --- derivation --------------------------------------------------------------


def _resolve_direction(row: dict) -> tuple:
    """(from_issuer_id, to_issuer_id, from_role, to_role) with the role flip rule."""
    from_role, to_role, default_subject_role, _ = SPECIES_ROLES[row["species"]]
    subject_role = row.get("subject_role") or default_subject_role
    subject_iid = row["subject"]["issuer_id"]
    object_iid = row["object"]["issuer_id"]
    if subject_role == to_role:
        # The filer names itself as the to-party; direction flips so from/to keep
        # their species roles.  Same real-world relationship, same key.
        return object_iid, subject_iid, from_role, to_role
    return subject_iid, object_iid, from_role, to_role


def _excerpt_state(row: dict, excerpts: dict, match_row_span: bool) -> tuple:
    """(source_state, usable) for one row against the pinned excerpt map."""
    accession = (row.get("source_ref") or {}).get("accession")
    excerpt = excerpts.get(accession)
    if excerpt is None:
        return "source_unavailable", False
    if isinstance(excerpt, str):  # CORRUPT sentinel from the caller
        return "source_corrupt", False
    from engine.company_intelligence.relationships.replay import verify_excerpt

    if verify_excerpt(excerpt):
        return "source_corrupt", False
    if match_row_span:
        source = row.get("source_ref") or {}
        span = excerpt.get("span") or {}
        if (
            span.get("raw_sha256") != source.get("span_sha256")
            or span.get("normalized_sha256") != source.get("normalized_span_sha256")
        ):
            return "source_corrupt", False
    return "verified", True


def _warn(warnings: list, title: str, message: str) -> None:
    warnings.append({"title": title, "message": message})


def clock_refusal(row: dict, excerpt) -> str | None:
    """A24 refusal reason for one row, or None when its clock fields agree.

    Only rows that carry ``sec_index_header_acceptance_et`` (observation and
    document-assessment rows) are checkable.  The header must convert to the
    row's own ``published_at``, and a dict ``excerpt``'s ``accepted_at`` must
    equal it; anything else, including a converter refusal, is a refusal reason
    in the ``clock_mismatch`` / ``clock_refused:<reason>`` family.
    """
    header = row.get("sec_index_header_acceptance_et")
    if not header:
        return None
    published_at = row.get("published_at")
    try:
        converted = et_acceptance_to_utc(header)
    except ClockRefused as error:
        return f"clock_refused:{error.args[0] if error.args else 'refused'}"
    if converted != published_at:
        return "clock_mismatch"
    if isinstance(excerpt, dict) and excerpt.get("accepted_at") != published_at:
        return "clock_mismatch"
    return None


def rights_block(rights: dict | None) -> dict:
    """The per-edge rights block (A7): unknown/null until a ruling binds.

    ``rights`` is the producer's validated ruling binding (display fields plus
    ``ruling_ref``) or None — an absent or refused ruling grants nothing.
    """
    block = {
        "source_class": "SEC_PUBLIC_ACCESS",
        "purpose_permitted": ["private_api", "research"],
        "public_display": "unknown",
        "excerpt_display": "unknown",
        "magnitude_display": "unknown",
        "ruling_ref": None,
    }
    if rights is not None:
        block["public_display"] = rights["public_display"]
        block["excerpt_display"] = rights["excerpt_display"]
        block["magnitude_display"] = rights["magnitude_display"]
        block["ruling_ref"] = rights["ruling_ref"]
    return block


def build_package(rows, excerpts: dict, issuers: dict, as_of: str,
                  manifest_version: str, inputs, *, enforce_clock: bool = False,
                  rights: dict | None = None):  # noqa: C901
    """Derive (package, edges_doc_without_package_sha256) from pinned rows.

    ``rows`` are contract-checked extraction rows of all three kinds.  ``excerpts``
    maps accession -> excerpt dict | None (missing) | CORRUPT.  ``issuers`` maps
    issuer_id -> sorted manifest security_ids.  The returned edges doc carries a
    placeholder ``package_sha256``; the producer replaces it with the hash of the
    package bytes it just wrote.

    ``enforce_clock`` applies the A24 clock rule (the contracts'
    ``x-gmi-clock-rule``): a row whose ``sec_index_header_acceptance_et`` does
    not convert to its own ``published_at`` — or whose source excerpt's
    ``accepted_at`` disagrees — is not used (observation: quarantined;
    assessment: excluded and counted under quarantined).  The producer always
    enables it; direct callers (the synthetic battery) own their rows' clock
    consistency and may leave it off.

    ``rights`` binds the A7 public-display fields on every edge and the
    package's ``rights_ruling_ref``; None keeps the committed unknown/null
    default.  A binding is all-or-nothing by construction — the producer never
    passes a partial one.
    """
    as_of_dt = _instant_dt(as_of)
    obs_rows = [r for r in rows if r.get("row_kind") == "observation"]
    asm_rows = [r for r in rows if r.get("row_kind") == "document_assessment"]
    cov_rows = [r for r in rows if r.get("row_kind") == "coverage"]

    pit_obs = sorted(
        _pit_visible(obs_rows, as_of_dt),
        key=lambda r: (_known_at(r), r.get("observation_id") or ""),
    )
    pit_asm = _pit_visible(asm_rows, as_of_dt)
    pit_cov = _pit_visible(cov_rows, as_of_dt)

    warnings: list = []
    observations: list = []
    non_edges: list = []
    assessments: list = []
    accs: dict = {}
    excluded_assessments = 0

    for row in pit_obs:
        obs_id = row.get("observation_id")
        source = row.get("source_ref") or {}
        accession = source.get("accession")
        known_at = _known_at(row)
        species = row.get("species")
        source_state, usable = _excerpt_state(row, excerpts, match_row_span=True)
        rel_key = None
        non_edge_key = None
        refusal_reason = None
        clock_problem = (
            clock_refusal(row, excerpts.get(accession)) if enforce_clock else None
        )

        if clock_problem is not None:
            disposition = "quarantined"
            refusal_reason = clock_problem
            _warn(
                warnings,
                "CLOCK_MISMATCH",
                f"{obs_id}: {clock_problem}; the row is not used (x-gmi-clock-rule A24)",
            )
        elif species not in SPECIES_ROLES:
            disposition = "refused"
            refusal_reason = "species_refused"
            _warn(
                warnings,
                "relationship-species-refused",
                f"{obs_id}: species {species!r} is outside the closed set; no edge",
            )
        elif not usable:
            disposition = "quarantined"
            title = (
                "relationship-source-unavailable"
                if source_state == "source_unavailable"
                else "relationship-source-corrupt"
            )
            _warn(
                warnings,
                title,
                f"{obs_id}: excerpt for {accession} does not corroborate the row; "
                "quarantined with no edge contribution",
            )
        else:
            subject_iid = row["subject"]["issuer_id"]
            from_iid, to_iid, _from_role, _to_role = _resolve_direction(row)
            object_iid = row["object"]["issuer_id"]
            if subject_iid not in issuers:
                disposition = "refused"
                refusal_reason = "subject_out_of_manifest"
                _warn(
                    warnings,
                    "relationship-subject-out-of-manifest",
                    f"{obs_id}: subject {subject_iid} is not in the universe manifest",
                )
            elif species == "component_dependency" and from_iid is None:
                disposition = "refused"
                refusal_reason = "provider_unnamed"
                _warn(
                    warnings,
                    "relationship-provider-unnamed",
                    f"{obs_id}: component_dependency has no named provider",
                )
            elif object_iid is not None and object_iid not in issuers:
                disposition = "non_edge"
                non_edge_key = _record_non_edge(
                    non_edges, row, accession, known_at, "UNRESOLVED_COUNTERPARTY"
                )
                _warn(
                    warnings,
                    "relationship-unresolved-issuer",
                    f"{obs_id}: object issuer {object_iid} is not in the manifest; "
                    "kept as a document-scoped non-edge",
                )
            elif from_iid is not None and from_iid == to_iid:
                disposition = "refused"
                refusal_reason = "self_edge"
                _warn(
                    warnings,
                    "relationship-self-edge",
                    f"{obs_id}: self-edge {from_iid} refused",
                )
            elif object_iid is None:
                disposition = "non_edge"
                non_edge_key = _record_non_edge(
                    non_edges,
                    row,
                    accession,
                    known_at,
                    row["object"]["non_edge_reason"],
                )
            else:
                disposition = "edge"
                rel_key = relationship_identity(
                    species, from_iid, to_iid, row["scope"]["product_key"]
                )
                acc = accs.setdefault(
                    rel_key,
                    {"observations": [], "from_iid": from_iid, "to_iid": to_iid},
                )
                acc["observations"].append(row)

        observations.append(
            {
                "observation_id": obs_id,
                "accession": accession,
                "known_at": known_at,
                "source_state": source_state,
                "disposition": disposition,
                "relationship_key": rel_key,
                "non_edge_key": non_edge_key,
                "refusal_reason": refusal_reason,
            }
        )

    for row in sorted(
        pit_asm, key=lambda r: (_known_at(r), r.get("assessment_id") or "")
    ):
        asm_id = row.get("assessment_id")
        source = row.get("source_ref") or {}
        clock_problem = (
            clock_refusal(row, excerpts.get(source.get("accession")))
            if enforce_clock
            else None
        )
        if clock_problem is not None:
            # Excluded entirely and counted under quarantined; it contributes
            # no assessments entry and never reaches correction lineage.
            excluded_assessments += 1
            _warn(
                warnings,
                "CLOCK_MISMATCH",
                f"{asm_id}: {clock_problem}; the row is not used (x-gmi-clock-rule A24)",
            )
            continue
        source_state, _usable = _excerpt_state(row, excerpts, match_row_span=False)
        assessments.append(
            {
                "assessment_id": asm_id,
                "accession": source.get("accession"),
                "amends_accession": row.get("amends_accession"),
                "assessment": row.get("assessment"),
                "reason": row.get("reason"),
                "known_at": _known_at(row),
                "source_state": source_state,
            }
        )

    edges = [
        _build_edge(
            rel_key, accs[rel_key], pit_asm, issuers, as_of_dt, excerpts, rights
        )
        for rel_key in sorted(accs)
    ]
    coverage = _build_coverage(cov_rows, pit_cov)
    revisions_flat = [
        rev for edge in edges for rev in edge["magnitude_history"]
    ]
    revisions_flat.sort(
        key=lambda r: (
            r["relationship_key"],
            r["kind"],
            r["period"]["start"] or "",
            r["period"]["end"],
            r["revision_seq"],
            r["revision_id"],
        )
    )

    package_counts = {
        "observations_in": len(obs_rows),
        "observations_pit_visible": len(pit_obs),
        "observations_quarantined": sum(
            1 for o in observations if o["disposition"] == "quarantined"
        )
        + excluded_assessments,
        "observations_refused": sum(
            1 for o in observations if o["disposition"] == "refused"
        ),
        "edges": len(edges),
        "non_edges": len(non_edges),
        "revisions": len(revisions_flat),
        "assessments": len(assessments),
        "coverage_rows": len(coverage),
        "warnings": len(warnings),
        "edges_by_species": {
            species: sum(1 for edge in edges if edge["species"] == species)
            for species in SPECIES_ROLES
        },
    }
    warnings.sort(key=lambda w: (w["title"], w["message"]))

    package = {
        "schema": PACKAGE_SCHEMA,
        "adoption_state": "proposed",
        "package_id": package_identity(
            as_of, manifest_version, [entry["sha256"] for entry in inputs]
        ),
        "as_of": as_of,
        "computed_at": as_of,
        "manifest_version": manifest_version,
        "inputs": sorted(
            ({"path": entry["path"], "sha256": entry["sha256"]} for entry in inputs),
            key=lambda entry: entry["path"],
        ),
        "authority": {key: False for key in ("rank", "gate", "size", "trade", "prediction")},
        "purpose": _v1_purpose_v2(),
        "content_boundary": _v1_content_boundary(),
        "rights_ruling_ref": rights["ruling_ref"] if rights else None,
        "observations": sorted(observations, key=lambda o: o["observation_id"] or ""),
        "assessments": sorted(assessments, key=lambda a: a["assessment_id"] or ""),
        "coverage": coverage,
        "non_edges": sorted(non_edges, key=lambda n: n["non_edge_key"]),
        "magnitude_revisions": revisions_flat,
        "warnings": warnings,
        "counts": package_counts,
    }

    edges_doc = {
        "schema": EDGES_SCHEMA,
        "adoption_state": "proposed",
        "as_of": as_of,
        "manifest_version": manifest_version,
        "package_id": package["package_id"],
        "package_sha256": _PACKAGE_SHA_PLACEHOLDER,
        "authority": package["authority"],
        "edges": edges,
        "non_edges": sorted(non_edges, key=lambda n: n["non_edge_key"]),
        "coverage": coverage,
        "counts": package_counts,
    }
    return package, edges_doc


def _v1_purpose_v2() -> dict:
    """The v1 purpose dict with this package's operation.

    Re-declared identical to ``engine.company_intelligence.relationship_observations``
    ``_purpose()`` (v1, read-only) rather than imported: the v1 module drags the
    C01 candidate-inspection chain with it, and this derivation must stay a bounded
    closure.  Contracts 3/4 const-pin every value, so any drift from v1 fails the
    output conformance check and the producer writes nothing.
    """
    return {
        "operation": "relationship_observation_package_v2",
        "source_purpose_permission": "NOT_ESTABLISHED",
        "production": False,
        "public_export": False,
        "training": False,
    }


def _v1_content_boundary() -> dict:
    """Re-declared identical to the v1 module's ``_content_boundary()`` (see above)."""
    return {
        "private_evidence": True,
        "source_text_may_be_present": True,
        "quote_free_payload": "NOT_CERTIFIED",
        "public_safe_payload": "NOT_CERTIFIED",
    }


def _record_non_edge(non_edges: list, row: dict, accession: str, known_at: str,
                    reason: str) -> str:
    object_party = row["object"]
    label = object_party.get("anonymous_alias") or object_party.get("name_as_filed")
    key = non_edge_identity(accession, row["species"], label, reason)
    non_edges.append(
        {
            "non_edge_key": key,
            "species": row["species"],
            "observation_id": row.get("observation_id"),
            "accession": accession,
            "subject_issuer_id": row["subject"]["issuer_id"],
            "object_name_as_filed": object_party.get("name_as_filed"),
            "anonymous_alias": object_party.get("anonymous_alias"),
            "non_edge_reason": reason,
            "known_at": known_at,
        }
    )
    return key


def _build_edge(rel_key: str, acc: dict, pit_asm, issuers: dict,
                as_of_dt: datetime, excerpts: dict, rights: dict | None) -> dict:
    rows = sorted(
        acc["observations"],
        key=lambda r: (_known_at(r), r.get("observation_id") or ""),
    )
    species = rows[0]["species"]
    from_role, to_role, _default, mapping = SPECIES_ROLES[species]
    from_iid = acc["from_iid"]
    to_iid = acc["to_iid"]

    known_ats = [_known_at(row) for row in rows]
    first_known_at = min(known_ats)
    last_asserted_at = max(known_ats)

    accessions = {row["source_ref"]["accession"] for row in rows}
    lineage = []
    for row in sorted(
        pit_asm, key=lambda r: (_known_at(r), r.get("assessment_id") or "")
    ):
        source_state, usable = _excerpt_state(row, excerpts, match_row_span=False)
        if not usable:
            continue  # kept in `assessments`, never contributes lineage
        if row.get("amends_accession") not in accessions:
            continue
        lineage.append(
            {
                "assessment_id": row["assessment_id"],
                "accession": row["source_ref"]["accession"],
                "amends_accession": row["amends_accession"],
                "assessment": row["assessment"],
                "reason": row.get("reason"),
                "known_at": _known_at(row),
                "effect": (
                    "superseded_by_restatement_revisions"
                    if row["assessment"] == "restatement"
                    else "none"
                ),
            }
        )
    assessed_ats = known_ats + [entry["known_at"] for entry in lineage]
    last_assessed_at = max(assessed_ats)

    revisions = _build_revisions(rel_key, rows)
    conflicts, conflicted_kinds = _build_conflicts(revisions)
    current_magnitudes = _current_magnitudes(revisions, conflicted_kinds)

    if revisions:
        starts = [r["period"]["start"] for r in revisions if r["period"]["start"]]
        asserted_start = min(starts) if starts else None
        asserted_end = max(r["period"]["end"] for r in revisions)
    else:
        asserted_start = None
        asserted_end = max(row["period_end"] for row in rows)

    freshness = (
        "stale"
        if as_of_dt - _instant_dt(last_asserted_at) > timedelta(days=FRESHNESS_DAYS)
        else "fresh"
    )

    conditions = sorted(
        (
            {
                "kind": condition["kind"],
                "text": condition["text"],
                "byte_start": condition["byte_start"],
                "byte_end": condition["byte_end"],
                "span_sha256": condition["span_sha256"],
                "accession": row["source_ref"]["accession"],
            }
            for row in rows
            for condition in row.get("conditions") or []
        ),
        key=lambda c: (c["accession"], c["byte_start"], c["kind"], c["text"]),
    )
    source_refs = sorted(
        (
            {
                "observation_id": row["observation_id"],
                "accession": row["source_ref"]["accession"],
                "form": row["source_ref"]["form"],
                "url": row["source_ref"]["url"],
                "byte_start": row["source_ref"]["byte_start"],
                "byte_end": row["source_ref"]["byte_end"],
                "span_sha256": row["source_ref"]["span_sha256"],
                "excerpt_path": EXCERPT_PATH_TEMPLATE.format(
                    accession=row["source_ref"]["accession"]
                ),
            }
            for row in rows
        ),
        key=lambda s: (s["accession"], s["observation_id"]),
    )

    return {
        "relationship_key": rel_key,
        "species": species,
        "direction": {
            "from_issuer_id": from_iid,
            "to_issuer_id": to_iid,
            "from_role": from_role,
            "to_role": to_role,
        },
        "from": {"issuer_id": from_iid, "security_ids": list(issuers[from_iid])},
        "to": {"issuer_id": to_iid, "security_ids": list(issuers[to_iid])},
        "scope": {
            "product_key": rows[0]["scope"]["product_key"],
            "segment": rows[0]["scope"]["segment"],
            "geography": rows[0]["scope"]["geography"],
        },
        "relation_status": rows[-1]["relation_status"],
        "admission_state": "proposed",
        "theme_graph_mapping": mapping,
        "asserting_parties": sorted({row["asserting_party"] for row in rows}),
        "first_known_at": first_known_at,
        "last_asserted_at": last_asserted_at,
        "last_assessed_at": last_assessed_at,
        "freshness_state": freshness,
        "asserted_period": {"start": asserted_start, "end": asserted_end},
        "magnitude_state": (
            "conflicted"
            if conflicted_kinds
            else ("disclosed" if revisions else "undisclosed")
        ),
        "current_magnitudes": current_magnitudes,
        "magnitude_history": revisions,
        "conflicts": conflicts,
        "conditions": conditions,
        "source_refs": source_refs,
        "rights": rights_block(rights),
        "correction_lineage": lineage,
    }


def _build_revisions(rel_key: str, rows) -> list:
    groups: dict = {}
    for row in rows:
        for magnitude in row.get("magnitudes") or []:
            period = magnitude["period"]
            key = (
                magnitude["kind"],
                period["start"] or "",
                period["end"],
                row["asserting_party"],
            )
            groups.setdefault(key, []).append(
                (_known_at(row), row["observation_id"], magnitude, row)
            )

    revisions = []
    for key in sorted(groups):
        entries = sorted(groups[key])
        previous = None
        for seq, (known_at, _obs_id, magnitude, row) in enumerate(entries, start=1):
            if seq == 1:
                revision_kind = "new_period"
            elif magnitude["value"] == previous["value"]:
                revision_kind = "reassertion"
            else:
                revision_kind = "restatement"
            source = row["source_ref"]
            revision = {
                "revision_id": revision_identity(
                    rel_key,
                    magnitude["kind"],
                    magnitude["period"]["start"],
                    magnitude["period"]["end"],
                    row["asserting_party"],
                    seq,
                ),
                "relationship_key": rel_key,
                "kind": magnitude["kind"],
                "value": magnitude["value"],
                "value_high": magnitude.get("value_high"),
                "unit": magnitude["unit"],
                "precision": magnitude["precision"],
                "period": {
                    "start": magnitude["period"]["start"],
                    "end": magnitude["period"]["end"],
                    "label": magnitude["period"]["label"],
                },
                "numerator_scope": magnitude["numerator_scope"],
                "denominator_scope": magnitude["denominator_scope"],
                "asserting_party": row["asserting_party"],
                "revision_seq": seq,
                "revision_kind": revision_kind,
                "supersedes": previous["revision_id"] if previous else None,
                "known_at": known_at,
                "source_ref": {
                    "accession": source["accession"],
                    "form": source["form"],
                    "byte_start": source["byte_start"],
                    "byte_end": source["byte_end"],
                    "span_sha256": source["span_sha256"],
                    "xbrl_fact_id": magnitude.get("xbrl_fact_id"),
                    "excerpt_path": EXCERPT_PATH_TEMPLATE.format(
                        accession=source["accession"]
                    ),
                },
            }
            revisions.append(revision)
            previous = revision

    revisions.sort(
        key=lambda r: (
            r["kind"],
            r["period"]["start"] or "",
            r["period"]["end"],
            r["revision_seq"],
            r["revision_id"],
        )
    )
    return revisions


def _build_conflicts(revisions) -> tuple:
    """Per (kind, period): distinct asserting parties with distinct values."""
    latest_by_party: dict = {}
    for rev in revisions:
        key = (
            rev["kind"],
            rev["period"]["start"] or "",
            rev["period"]["end"],
        )
        by_party = latest_by_party.setdefault(key, {})
        held = by_party.get(rev["asserting_party"])
        if held is None or rev["revision_seq"] > held["revision_seq"]:
            by_party[rev["asserting_party"]] = rev

    conflicts = []
    conflicted_kinds = set()
    for key in sorted(latest_by_party):
        by_party = latest_by_party[key]
        if len(by_party) < 2:
            continue
        values = {rev["value"] for rev in by_party.values()}
        if len(values) < 2:
            continue
        kind = key[0]
        conflicted_kinds.add(kind)
        sample = next(iter(by_party.values()))
        conflicts.append(
            {
                "kind": kind,
                "period": dict(sample["period"]),
                "values": [
                    {
                        "asserting_party": party,
                        "value": rev["value"],
                        "revision_id": rev["revision_id"],
                    }
                    for party, rev in sorted(by_party.items())
                ],
            }
        )
    return conflicts, conflicted_kinds


def _current_magnitudes(revisions, conflicted_kinds) -> list:
    current = []
    for kind in sorted({rev["kind"] for rev in revisions}):
        candidates = [rev for rev in revisions if rev["kind"] == kind]
        selected = dict(
            max(
                candidates,
                key=lambda r: (r["period"]["end"], r["revision_seq"], r["revision_id"]),
            )
        )
        if kind in conflicted_kinds:
            # Disagreeing parties are preserved in `conflicts`; the current entry
            # carries no number — values are never averaged, summed or netted.
            selected["value"] = None
        current.append(selected)
    return current


def _build_coverage(cov_rows, pit_cov) -> list:
    """Latest PIT-visible coverage row per issuer; else not_assessed, known_at null."""
    issuers = sorted({row["issuer_id"] for row in cov_rows})
    latest: dict = {}
    for index, row in enumerate(pit_cov):
        known_at = _known_at(row)
        held = latest.get(row["issuer_id"])
        if held is None or (known_at, index) >= held[0]:
            latest[row["issuer_id"]] = ((known_at, index), row)
    coverage = []
    for issuer_id in issuers:
        held = latest.get(issuer_id)
        if held is None:
            coverage.append(
                {
                    "issuer_id": issuer_id,
                    "state": "not_assessed",
                    "period_end": None,
                    "documents": [],
                    "known_at": None,
                }
            )
        else:
            row = held[1]
            coverage.append(
                {
                    "issuer_id": issuer_id,
                    "state": row["state"],
                    "period_end": row.get("period_end"),
                    "documents": list(row.get("documents") or []),
                    "known_at": _known_at(row),
                }
            )
    return coverage


# --- path validity (chainability of two edges) --------------------------------


def path_validity(edge_ab: dict, edge_bc: dict) -> tuple:
    """(ok, reason) for chaining ab -> bc.  Reasons are checked in order."""
    if edge_ab["direction"]["to_issuer_id"] != edge_bc["direction"]["from_issuer_id"]:
        return False, "not_chained"
    if (
        edge_ab["relation_status"] != "asserted"
        or edge_bc["relation_status"] != "asserted"
    ):
        return False, "not_asserted"
    if edge_ab["scope"]["product_key"] != edge_bc["scope"]["product_key"]:
        # "all" matches only "all" — no wildcard semantics.
        return False, "product_key_mismatch"
    period_ab = edge_ab["asserted_period"]
    period_bc = edge_bc["asserted_period"]
    start_ab = period_ab["start"] or period_ab["end"]  # null start = end
    start_bc = period_bc["start"] or period_bc["end"]
    if start_ab > period_bc["end"] or start_bc > period_ab["end"]:
        return False, "period_disjoint"
    return True, "ok"
