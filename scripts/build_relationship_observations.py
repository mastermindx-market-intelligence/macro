#!/usr/bin/env python3
"""Build the relationship observation package v2 + relationship edges record.

Off-render: this is never on the nightly render path.  Fail-open: a missing
extraction input, a row that violates its contract, or outputs that would not
conform to the package/edges contracts produce a ``::warning`` line and exit 0
WITHOUT writing — a partial or malformed record never clobbers the committed
one.  There is no wall clock anywhere: ``computed_at`` is the ``--as-of`` value.

Warnings are bare prints at line start (never a logger) so CI annotation
parsers see them::

  ::warning title=<slug>::<message>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import jsonschema  # noqa: E402

from engine.company_intelligence.relationships import (  # noqa: E402
    SPECIES_ROLES,
    build_package,
    load_manifest_issuers,
)

DEFAULT_EXTRACTION = (
    REPO_ROOT
    / "research/theme_graph/gmi_relationships_20261021/extraction/swks_aapl_m1.jsonl"
)
DEFAULT_SOURCES = (
    REPO_ROOT / "research/theme_graph/gmi_relationships_20261021/sources"
)
DEFAULT_MANIFEST = (
    REPO_ROOT / "research/theme_graph/coverage_20261019/UNIVERSE_MANIFEST.json"
)
DEFAULT_OUT_DIR = REPO_ROOT / "data/company_intelligence/relationships"
CONTRACT_DIR = REPO_ROOT / "contracts/company_intelligence"
PACKAGE_CONTRACT = CONTRACT_DIR / "relationship_observation_package.v2.schema.json"
EDGES_CONTRACT = CONTRACT_DIR / "relationship_edges.v1.schema.json"
EXTRACTION_CONTRACT = CONTRACT_DIR / "relationship_extraction.v1.schema.json"

PACKAGE_SHA_PLACEHOLDER = "0" * 64

#: A7 binding shape: a ruling ref is <ruling_id>@sha256:<sha256 of the bytes>.
RIGHTS_RULING_ID = re.compile(r"^GMI-REL-[A-Z0-9-]{3,80}$")


def _warn(title: str, message: str) -> None:
    print(f"::warning title={title}::{message}", flush=True)


def _canonical_json_bytes(obj) -> bytes:
    text = json.dumps(obj, sort_keys=True, indent=1, ensure_ascii=False)
    return (text + "\n").encode("utf-8")


def _canonical_instant(value: str):
    """Canonical ...Z instant, or None for naive/unparseable input."""
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        return None
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _input_path(path: Path) -> str:
    """Repo-relative path for in-repo inputs, absolute otherwise."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_rows(path: Path, label: str | None = None):
    rows = []
    prefix = f"{label}: " if label else ""
    with path.open("rb") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line.decode("utf-8"))
            except ValueError as error:
                _warn(
                    "relationship-row-invalid",
                    f"{prefix}line {number}: not JSON ({error}); skipped",
                )
                continue
            if not isinstance(row, dict):
                _warn("relationship-row-invalid", f"{prefix}line {number}: not an object")
                continue
            rows.append(row)
    return rows


def _resolve_rights(ruling_path):
    """(binding, error) from the optional --rights-ruling JSON file (A7).

    ``binding`` is None when the flag is absent or when ANY required condition
    fails — a ruling never partially grants.  On success the binding carries
    the three display fields, the ``ruling_ref`` and the ``input_ref`` entry
    for the ruling file itself.
    """
    if ruling_path is None:
        return None, None
    path = Path(ruling_path)
    try:
        raw = path.read_bytes()
        ruling = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as error:
        return None, f"{path}: unreadable or not JSON ({error})"

    def _refuse(reason):
        return None, f"{path}: {reason}"

    if not isinstance(ruling, dict):
        return _refuse("ruling is not a JSON object")
    if ruling.get("schema") != "company_intelligence.source_purpose_ruling/v1":
        return _refuse("schema is not company_intelligence.source_purpose_ruling/v1")
    if ruling.get("evidence_kind") != "direct_chairman_source_rights_confirmation":
        return _refuse(
            "evidence_kind is not direct_chairman_source_rights_confirmation"
        )
    if ruling.get("decision_owner") != "Chairman Chris":
        return _refuse("decision_owner is not Chairman Chris")
    ruling_id = ruling.get("ruling_id")
    if not isinstance(ruling_id, str) or not RIGHTS_RULING_ID.match(ruling_id):
        return _refuse(
            f"ruling_id {ruling_id!r} does not match {RIGHTS_RULING_ID.pattern}"
        )
    source = ruling.get("source")
    if not isinstance(source, dict) or source.get("source_class") != "SEC_PUBLIC_ACCESS":
        return _refuse("source.source_class is not SEC_PUBLIC_ACCESS")
    use = ruling.get("permitted_use")
    if not isinstance(use, dict):
        return _refuse("permitted_use is not an object")
    if use.get("citation_required") is not True:
        return _refuse("permitted_use.citation_required is not true")
    derived = use.get("derived_fact_public_display")
    if not isinstance(derived, bool):
        return _refuse("permitted_use.derived_fact_public_display is not a bool")
    magnitude = use.get("magnitude_display")
    if not isinstance(magnitude, bool):
        return _refuse("permitted_use.magnitude_display is not a bool")
    excerpt = use.get("verbatim_excerpt_display")
    if excerpt not in ("entitled_only", "public"):
        return _refuse(
            "permitted_use.verbatim_excerpt_display is not entitled_only|public"
        )
    max_bytes = use.get("excerpt_max_raw_bytes")
    if (
        not isinstance(max_bytes, int)
        or isinstance(max_bytes, bool)
        or max_bytes > 2048
    ):
        return _refuse("permitted_use.excerpt_max_raw_bytes is not an int <= 2048")
    binding = {
        "public_display": "derived_facts_permitted" if derived else "entitled_only",
        "excerpt_display": "public_permitted" if excerpt == "public" else "entitled_only",
        "magnitude_display": "permitted" if magnitude else "entitled_only",
        "ruling_ref": f"{ruling_id}@sha256:{hashlib.sha256(raw).hexdigest()}",
        "input_ref": {
            "path": _input_path(path),
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
    }
    return binding, None


def _has_clock(row: dict) -> bool:
    return bool(row.get("published_at") or row.get("ingested_at"))


def _cross_field_problems(row: dict):
    """Producer-enforced rules the extraction schema cannot express cheaply."""
    problems = []
    if row.get("row_kind") == "observation":
        object_party = row.get("object") or {}
        issuer = object_party.get("issuer_id")
        reason = object_party.get("non_edge_reason")
        if (issuer is None) == (reason is None):
            problems.append(
                "exactly one of object.issuer_id / object.non_edge_reason must be set"
            )
        species = row.get("species")
        subject_role = row.get("subject_role")
        if subject_role is not None and species in SPECIES_ROLES:
            from_role, to_role = SPECIES_ROLES[species][0], SPECIES_ROLES[species][1]
            if subject_role not in (from_role, to_role):
                problems.append(
                    f"subject_role {subject_role!r} is not a role of {species}"
                )
        source = row.get("source_ref") or {}
        if isinstance(source.get("byte_start"), int) and isinstance(
            source.get("byte_end"), int
        ):
            if source["byte_end"] <= source["byte_start"]:
                problems.append("source_ref byte_end must exceed byte_start")
        for magnitude in row.get("magnitudes") or []:
            if "value_high" in magnitude and magnitude.get("precision") != "range":
                problems.append(
                    f"magnitude {magnitude.get('kind')} carries value_high without "
                    "precision range"
                )
    elif row.get("row_kind") == "document_assessment":
        source = row.get("source_ref") or {}
        if isinstance(source.get("byte_start"), int) and isinstance(
            source.get("byte_end"), int
        ):
            if source["byte_end"] <= source["byte_start"]:
                problems.append("source_ref byte_end must exceed byte_start")
    return problems


def _validate_row(row: dict, extraction_validator):
    try:
        extraction_validator.validate(row)
    except jsonschema.ValidationError as error:
        return [error.message]
    return _cross_field_problems(row)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the relationship observation package v2 + edges record "
            "(off-render, fail-open)."
        )
    )
    parser.add_argument(
        "--as-of",
        required=True,
        help="point-in-time instant, ISO with offset or Z (naive instants are refused)",
    )
    parser.add_argument("--extraction", default=str(DEFAULT_EXTRACTION))
    parser.add_argument("--sources", default=str(DEFAULT_SOURCES))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument(
        "--rights-ruling",
        default=None,
        help=(
            "optional path to a Chairman rights-ruling JSON (A7); absent keeps "
            "every edge unknown with a null ruling_ref, and a ruling that fails "
            "any binding condition grants nothing"
        ),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "exit nonzero if any warning was emitted (2 when the A24 clock rule "
            "or a rights ruling refused a row, else 1)"
        ),
    )
    args = parser.parse_args(argv)

    as_of = _canonical_instant(args.as_of)
    if as_of is None:
        print(
            f"relationship_observations: --as-of must be an ISO instant with an "
            f"offset or Z (got naive or unparseable {args.as_of!r}); exit 2"
        )
        return 2

    # --extraction accepts one .jsonl file OR a directory of them (M2 will feed
    # many extraction files): a directory means every **/*.jsonl under it,
    # sorted by POSIX relative path.
    extraction_input = Path(args.extraction)
    if extraction_input.is_dir():
        extraction_files = sorted(
            (p for p in extraction_input.rglob("*.jsonl") if p.is_file()),
            key=lambda p: p.relative_to(extraction_input).as_posix(),
        )
        if not extraction_files:
            _warn(
                "relationship-input-missing",
                f"extraction directory {extraction_input} holds no *.jsonl; "
                "nothing written",
            )
            return 0
    elif extraction_input.is_file():
        extraction_files = [extraction_input]
    else:
        _warn(
            "relationship-input-missing",
            f"extraction file {extraction_input} is missing; nothing written",
        )
        return 0
    manifest_path = Path(args.manifest)
    if not manifest_path.is_file():
        _warn(
            "relationship-input-missing",
            f"universe manifest {manifest_path} is missing; nothing written",
        )
        return 0

    # --sources is searched recursively for <accession>.json.  Two copies of one
    # accession with identical bytes are one source; differing bytes make that
    # accession source_corrupt for every row citing it.
    sources_input = Path(args.sources)
    source_candidates: dict = {}
    if sources_input.is_dir():
        for path in sorted(sources_input.rglob("*.json")):
            if path.is_file():
                source_candidates.setdefault(path.stem, []).append(path)

    rows = []
    for extraction_file in extraction_files:
        label = (
            extraction_file.relative_to(extraction_input).as_posix()
            if extraction_input.is_dir()
            else None
        )
        rows.extend(_load_rows(extraction_file, label))

    # Refused-species rows bypass the extraction contract (its enum excludes them
    # by design) and are passed to the derivation, which records the refusal.
    rows_kept = []
    referenced = set()
    for row in rows:
        if (
            row.get("row_kind") == "observation"
            and row.get("species") not in SPECIES_ROLES
        ):
            rows_kept.append(row)
            source = row.get("source_ref") or {}
            if isinstance(source.get("accession"), str):
                referenced.add(source["accession"])
            continue
        problems = _validate_row(row, _extraction_validator())
        if problems:
            identifier = row.get(
                "observation_id", row.get("assessment_id", row.get("issuer_id", "?"))
            )
            _warn(
                "relationship-row-invalid",
                f"row {identifier}: {'; '.join(problems)}; skipped",
            )
            continue
        rows_kept.append(row)
        source = row.get("source_ref") or {}
        if isinstance(source.get("accession"), str):
            referenced.add(source["accession"])

    excerpts = {}
    source_inputs: dict = {}
    for accession in sorted(referenced):
        candidates = source_candidates.get(accession) or []
        if not candidates:
            excerpts[accession] = None
            continue  # an absent excerpt is a source state, not an input
        payload = {path: path.read_bytes() for path in candidates}
        if len(set(payload.values())) > 1:
            excerpts[accession] = "corrupt"
            source_inputs[accession] = sorted(
                payload, key=lambda p: _input_path(p)
            )
            _warn(
                "SOURCE_DUPLICATE_CONFLICT",
                f"accession {accession}: {len(candidates)} copies with differing "
                "bytes under the sources root; it is source_corrupt for every "
                "row citing it",
            )
            continue
        source_inputs[accession] = [candidates[0]]  # identical copies are one source
        try:
            excerpts[accession] = json.loads(
                payload[candidates[0]].decode("utf-8")
            )
        except ValueError:
            excerpts[accession] = "corrupt"

    manifest_version, issuers = load_manifest_issuers(manifest_path)
    inputs = [
        {"path": _input_path(path), "sha256": _sha_file(path)}
        for path in extraction_files
    ]
    for accession in sorted(source_inputs):
        for path in source_inputs[accession]:
            inputs.append({"path": _input_path(path), "sha256": _sha_file(path)})
    inputs.append({"path": _input_path(manifest_path), "sha256": _sha_file(manifest_path)})

    rights, rights_error = _resolve_rights(args.rights_ruling)
    if rights_error is not None:
        _warn("RIGHTS_RULING_INVALID", rights_error)  # nothing granted, all unknown
    elif rights is not None:
        inputs.append(rights["input_ref"])

    package, edges_doc = build_package(
        rows_kept,
        excerpts,
        issuers,
        as_of,
        manifest_version,
        inputs,
        enforce_clock=True,
        rights=rights,
    )

    package_validator = _validator(PACKAGE_CONTRACT)
    edges_validator = _validator(EDGES_CONTRACT)
    package_problems = _conformance_problems(package_validator, package)
    edges_problems = _conformance_problems(edges_validator, edges_doc)
    if package_problems or edges_problems:
        for problem in package_problems[:5]:
            _warn("relationship-package-invalid", problem)
        for problem in edges_problems[:5]:
            _warn("relationship-edges-invalid", problem)
        _warn(
            "relationship-output-invalid",
            "derived outputs do not conform to their contracts; nothing written",
        )
        return 0

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    package_bytes = _canonical_json_bytes(package)
    package_path = out_dir / "observation_package.v2.json"
    package_path.write_bytes(package_bytes)
    edges_doc["package_sha256"] = hashlib.sha256(package_bytes).hexdigest()
    edges_path = out_dir / "relationship_edges.json"
    edges_path.write_bytes(_canonical_json_bytes(edges_doc))

    for warning in package["warnings"]:
        _warn(warning["title"], warning["message"])

    counts = package["counts"]
    print(
        f"relationship_observations: as_of={as_of} edges={counts['edges']} "
        f"non_edges={counts['non_edges']} revisions={counts['revisions']} "
        f"warnings={counts['warnings']} package={package['package_id']}"
    )
    if args.strict:
        law_refused = rights_error is not None or any(
            warning["title"] == "CLOCK_MISMATCH" for warning in package["warnings"]
        )
        if law_refused:
            return 2
        return 1 if counts["warnings"] else 0
    return 0


_EXTRACTION_VALIDATOR = None


def _extraction_validator():
    global _EXTRACTION_VALIDATOR
    if _EXTRACTION_VALIDATOR is None:
        _EXTRACTION_VALIDATOR = _validator(EXTRACTION_CONTRACT)
    return _EXTRACTION_VALIDATOR


def _validator(contract_path: Path):
    schema = json.loads(contract_path.read_text(encoding="utf-8"))
    return jsonschema.validators.validator_for(schema)(schema)


def _conformance_problems(validator, document):
    problems = []
    for error in sorted(validator.iter_errors(document), key=lambda e: list(e.path)):
        location = "/".join(str(part) for part in error.path) or "<root>"
        problems.append(f"{location}: {error.message}")
    return problems


if __name__ == "__main__":
    sys.exit(main())
