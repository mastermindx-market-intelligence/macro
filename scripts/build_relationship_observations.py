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
    CORRUPT,
    SPECIES_ROLES,
    build_package,
    canon,
    load_manifest_issuers,
)

DEFAULT_EXTRACTION = (
    REPO_ROOT / "research/theme_graph/gmi_relationships_20261021/extraction"
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

#: A33 source layout: an accession is 10 digits, dash, 2, dash, 6.
ACCESSION_RE = re.compile(r"^\d{10}-\d{2}-\d{6}$")


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

    # --sources is searched recursively (A33).  Two on-disk layouts are
    # recognized, keyed by (accession, span.raw_sha256) so one filing can carry
    # several relationship spans:
    #   FLAT    <any dirs>/<accession>.json          (the stem is the accession)
    #   NESTED  <any dirs>/<accession>/<sha20>.json  (the parent dir is the
    #                                                 accession; sha20 =
    #                                                 span.raw_sha256[:20])
    # File order is the string order of the POSIX relative path — NOT Path
    # order — so a flat file sorts before nested files of the same accession
    # ('.' < '/').  Anything else under the root is skipped with a warning.
    sources_input = Path(args.sources)
    source_files: list = []  # (accession, path, nested) in deterministic order
    if sources_input.is_dir():
        for path in sorted(
            (p for p in sources_input.rglob("*.json") if p.is_file()),
            key=lambda p: p.relative_to(sources_input).as_posix(),
        ):
            if ACCESSION_RE.match(path.stem):
                source_files.append((path.stem, path, False))
            elif ACCESSION_RE.match(path.parent.name):
                source_files.append((path.parent.name, path, True))
            else:
                _warn(
                    "SOURCE_PATH_UNRECOGNIZED",
                    f"{path.relative_to(sources_input).as_posix()}: neither "
                    "<accession>.json nor <accession>/<sha20>.json; skipped",
                )

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
    for row in rows:
        if (
            row.get("row_kind") == "observation"
            and row.get("species") not in SPECIES_ROLES
        ):
            rows_kept.append(row)
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

    # Row dedupe: the same row may arrive from several extraction files.  Rows
    # sharing an observation_id / assessment_id collapse to their first row in
    # load order when canonically identical; a group with differing rows is
    # dropped ENTIRELY — the package never silently prefers one variant.
    # Coverage rows carry no content identity and pass through untouched.
    def _dedupe_id(row: dict):
        if row.get("row_kind") == "observation":
            return row.get("observation_id")
        if row.get("row_kind") == "document_assessment":
            return row.get("assessment_id")
        return None

    groups: dict = {}  # identifier -> [kind, row count, {canon(row)}]
    for row in rows_kept:
        identifier = _dedupe_id(row)
        if not isinstance(identifier, str):
            continue
        held = groups.get(identifier)
        if held is None:
            groups[identifier] = [row.get("row_kind"), 1, {canon(row)}]
        else:
            held[1] += 1
            held[2].add(canon(row))
    dropped = set()
    for identifier, (kind, count, prints) in groups.items():
        if len(prints) > 1:
            dropped.add(identifier)
            _warn(
                "OBSERVATION_DUPLICATE_CONFLICT"
                if kind == "observation"
                else "ASSESSMENT_DUPLICATE_CONFLICT",
                f"{identifier}: {count} rows with differing content; the whole "
                "group is dropped",
            )
    deduped = []
    seen_ids = set()
    for row in rows_kept:
        identifier = _dedupe_id(row)
        if not isinstance(identifier, str):
            deduped.append(row)  # coverage / id-less rows pass through
            continue
        if identifier in dropped or identifier in seen_ids:
            continue  # a conflicted group drops whole; an identical copy collapses
        seen_ids.add(identifier)
        deduped.append(row)
    rows_kept = deduped

    referenced = set()
    for row in rows_kept:
        source = row.get("source_ref") or {}
        if isinstance(source.get("accession"), str):
            referenced.add(source["accession"])

    # Excerpts and their inputs, keyed by (accession, span.raw_sha256) with the
    # M1 plain-accession view preserved for single-excerpt accessions (A33):
    #   excerpts[accession]               = CORRUPT when the accession is
    #     poisoned; else its single key's value (dict or CORRUPT); else absent.
    #   excerpts[(accession, raw_sha256)] = the parsed excerpt dict, or CORRUPT
    #     for a key with differing bytes on disk.
    excerpts = {}
    excerpt_paths = {}
    source_inputs: dict = {}
    for accession in sorted(referenced):
        entries = [entry for entry in source_files if entry[0] == accession]
        if not entries:
            excerpts[accession] = None
            continue  # an absent excerpt is a source state, not an input
        # Every recognized file of the accession is read and parsed; any bad
        # one poisons the whole accession for every row citing it.
        parsed = []
        poisoned = False
        for _accession, path, nested in entries:
            rel = path.relative_to(sources_input).as_posix()
            try:
                payload = path.read_bytes()
                doc = json.loads(payload.decode("utf-8"))
            except (OSError, ValueError) as error:
                poisoned = True
                _warn(
                    "SOURCE_FILE_POISONED",
                    f"{rel}: unreadable or not JSON ({error}); accession "
                    f"{accession} is source_corrupt for every row citing it",
                )
                continue
            span = doc.get("span") if isinstance(doc, dict) else None
            span_sha = span.get("raw_sha256") if isinstance(span, dict) else None
            if (
                not isinstance(doc, dict)
                or not isinstance(doc.get("accession"), str)
                or not isinstance(span_sha, str)
            ):
                poisoned = True
                _warn(
                    "SOURCE_FILE_POISONED",
                    f"{rel}: excerpt lacks a string accession or "
                    f"span.raw_sha256; accession {accession} is source_corrupt "
                    "for every row citing it",
                )
                continue
            if doc["accession"] != accession:
                poisoned = True
                _warn(
                    "SOURCE_FILE_POISONED",
                    f"{rel}: excerpt accession {doc['accession']!r} does not "
                    f"match its path accession {accession!r}; the accession is "
                    "source_corrupt for every row citing it",
                )
                continue
            if nested and path.stem != span_sha[:20]:
                poisoned = True
                _warn(
                    "SOURCE_PATH_MISMATCH",
                    f"{rel}: nested stem {path.stem!r} does not equal "
                    f"span.raw_sha256[:20] ({span_sha[:20]!r}); accession "
                    f"{accession} is source_corrupt for every row citing it",
                )
                continue
            parsed.append((path, nested, payload, doc))
        if poisoned:
            excerpts[accession] = CORRUPT
            source_inputs[accession] = [entry[1] for entry in entries]
            continue
        # Healthy files group by (accession, raw_sha256); byte-identical copies
        # are one source (the first file in order wins and is the input).
        key_groups: dict = {}
        for path, nested, payload, doc in parsed:
            key_groups.setdefault(doc["span"]["raw_sha256"], []).append(
                (path, nested, payload, doc)
            )
        cited_spans = {
            (row.get("source_ref") or {}).get("span_sha256")
            for row in rows_kept
            if (row.get("source_ref") or {}).get("accession") == accession
        }
        keyed: dict = {}
        for raw_sha in sorted(key_groups):
            members = key_groups[raw_sha]
            wanted = len(key_groups) == 1 or raw_sha in cited_spans
            if len({payload for _p, _n, payload, _d in members}) > 1:
                keyed[raw_sha] = CORRUPT
                if wanted:  # a conflicted key contributes all its files
                    source_inputs.setdefault(accession, []).extend(
                        path for path, _nested, _payload, _doc in members
                    )
                _warn(
                    "SOURCE_DUPLICATE_CONFLICT",
                    f"accession {accession} span {raw_sha[:20]}: {len(members)} "
                    "copies with differing bytes under the sources root; the "
                    "span is source_corrupt for every row citing it",
                )
                continue
            path, nested, _payload, doc = members[0]
            keyed[raw_sha] = doc
            if nested:
                excerpt_paths[(accession, raw_sha)] = _input_path(path)
            if wanted:
                source_inputs.setdefault(accession, []).append(path)
        for raw_sha, value in keyed.items():
            excerpts[(accession, raw_sha)] = value
        if len(keyed) == 1:
            excerpts[accession] = next(iter(keyed.values()))

    manifest_version, issuers = load_manifest_issuers(manifest_path)
    inputs = [
        {"path": _input_path(path), "sha256": _sha_file(path)}
        for path in extraction_files
    ]
    seen_paths = set(extraction_files)  # dedupe inputs by path
    for accession in sorted(source_inputs):
        for path in source_inputs[accession]:
            if path in seen_paths:
                continue
            seen_paths.add(path)
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
        excerpt_paths=excerpt_paths or None,
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
