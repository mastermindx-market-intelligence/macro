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


def _load_rows(path: Path):
    rows = []
    with path.open("rb") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line.decode("utf-8"))
            except ValueError as error:
                _warn(
                    "relationship-row-invalid",
                    f"line {number}: not JSON ({error}); skipped",
                )
                continue
            if not isinstance(row, dict):
                _warn("relationship-row-invalid", f"line {number}: not an object")
                continue
            rows.append(row)
    return rows


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
        "--strict",
        action="store_true",
        help="exit 1 if any warning was emitted",
    )
    args = parser.parse_args(argv)

    as_of = _canonical_instant(args.as_of)
    if as_of is None:
        print(
            f"relationship_observations: --as-of must be an ISO instant with an "
            f"offset or Z (got naive or unparseable {args.as_of!r}); exit 2"
        )
        return 2

    extraction_path = Path(args.extraction)
    if not extraction_path.is_file():
        _warn(
            "relationship-input-missing",
            f"extraction file {extraction_path} is missing; nothing written",
        )
        return 0
    manifest_path = Path(args.manifest)
    if not manifest_path.is_file():
        _warn(
            "relationship-input-missing",
            f"universe manifest {manifest_path} is missing; nothing written",
        )
        return 0
    sources_dir = Path(args.sources)

    rows = _load_rows(extraction_path)

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
    for accession in sorted(referenced):
        excerpt_path = sources_dir / f"{accession}.json"
        if not excerpt_path.is_file():
            excerpts[accession] = None
            continue
        try:
            excerpts[accession] = json.loads(
                excerpt_path.read_bytes().decode("utf-8")
            )
        except ValueError:
            excerpts[accession] = "corrupt"

    manifest_version, issuers = load_manifest_issuers(manifest_path)
    inputs = [{"path": _input_path(extraction_path), "sha256": _sha_file(extraction_path)}]
    for accession in sorted(excerpts):
        if excerpts[accession] is None:
            continue  # an absent excerpt is a source state, not an input
        inputs.append(
            {
                "path": _input_path(sources_dir / f"{accession}.json"),
                "sha256": _sha_file(sources_dir / f"{accession}.json"),
            }
        )
    inputs.append({"path": _input_path(manifest_path), "sha256": _sha_file(manifest_path)})

    package, edges_doc = build_package(
        rows_kept, excerpts, issuers, as_of, manifest_version, inputs
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
    if args.strict and counts["warnings"]:
        return 1
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
