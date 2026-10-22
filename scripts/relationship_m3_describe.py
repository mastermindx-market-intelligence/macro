#!/usr/bin/env python3
"""GMI ORCH-REL M3 describe CLI: descriptive renderer + correction demo.

``describe``        renders the committed relationship edges as plain-language
                    entries built only from the frozen premise templates plus
                    the filings' own verbatim words (sha-re-derived).
``correction-demo`` rebuilds one relationship at several point-in-time as-ofs
                    with the producer and demonstrates that a later filing
                    corrects or confirms an earlier figure while the earlier
                    view stays reproducible.

Read-only renderer: never a producer of record, never a store, never a gate,
never a site page.  No network; the only subprocess is the repo's own
producer script.  Output dirs under data/ or site/ are refused (OUT_REFUSED).
Exit codes: 0 success, 2 for any refusal.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.company_intelligence.relationships import describe  # noqa: E402

DATA_REL = "data/company_intelligence/relationships"
EDGES_REL = f"{DATA_REL}/relationship_edges.json"
PACKAGE_REL = f"{DATA_REL}/observation_package.v2.json"
SOURCES_REL = "research/theme_graph/gmi_relationships_20261021/sources"
EXTRACTION_REL = "research/theme_graph/gmi_relationships_20261021/extraction"
RESOLVER_REL = (
    "research/theme_graph/gmi_relationships_20261021/"
    "m2_inputs/resolver_us_issuers_v1.json"
)
PRODUCER_REL = "scripts/build_relationship_observations.py"
DESCRIBE_JSON = "describe_report.json"
DESCRIBE_TXT = "describe_report.txt"
DEMO_JSON = "correction_demo.json"
DEMO_TXT = "correction_demo.txt"


def _fail(code: str, message: str) -> int:
    print(f"relationship_m3_describe: {code}: {message}")
    return 2


def _out_refused(repo: Path, out: Path) -> bool:
    """True when the output dir is under the repo's data/ or site/ trees."""
    resolved = out.resolve()
    for guard in ("data", "site"):
        boundary = (repo / guard).resolve()
        if resolved == boundary or boundary in resolved.parents:
            return True
    return False


def _read_json(path: Path):
    return json.loads(path.read_bytes().decode("utf-8"))


def _sha_file(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relpath(repo: Path, path: Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(repo.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def _instant(text: str):
    if not text:
        return None
    normalized = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        moment = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if moment.tzinfo is None:
        return None
    return moment.astimezone(timezone.utc)


def _load_resolver(path: Path):
    """(sec_names, resolver rows) or (None-reader, None) when absent."""
    if not path.is_file():
        return {}, None
    doc = _read_json(path)
    rows = doc.get("rows") if isinstance(doc, dict) else None
    return describe.sec_name_map(rows), rows


# --- describe ---------------------------------------------------------------------


def _selected_edges(edges: list, issuers) -> list:
    if not issuers:
        return edges
    wanted = set(issuers)
    return [
        edge
        for edge in edges
        if wanted
        & {
            (edge.get("direction") or {}).get("from_issuer_id"),
            (edge.get("direction") or {}).get("to_issuer_id"),
        }
    ]


def _needed_accessions(edges: list) -> set:
    accessions = set()
    for edge in edges:
        for source in edge.get("source_refs") or []:
            if source.get("accession"):
                accessions.add(source["accession"])
        for condition in edge.get("conditions") or []:
            if condition.get("accession"):
                accessions.add(condition["accession"])
        for row in edge.get("correction_lineage") or []:
            if row.get("accession"):
                accessions.add(row["accession"])
    return accessions


def cmd_describe(args) -> int:
    repo = Path(args.repo_root).resolve()
    out = Path(args.out)
    if _out_refused(repo, out):
        return _fail("OUT_REFUSED", f"{out} is under data/ or site/")
    try:
        premises = describe.load_premises_file(args.premises)
    except (describe.PremisesDrift, OSError, ValueError) as error:
        return _fail("PREMISES_DRIFT", str(error))

    edges_path = repo / args.edges if not Path(args.edges).is_absolute() else Path(args.edges)
    package_path = (
        repo / args.package if not Path(args.package).is_absolute() else Path(args.package)
    )
    if not edges_path.is_file() or not package_path.is_file():
        return _fail("INPUT_MISSING", f"{edges_path} / {package_path}")
    edges_doc = _read_json(edges_path)
    package_doc = _read_json(package_path)

    selected = _selected_edges(edges_doc.get("edges") or [], args.issuer)
    accessions = _needed_accessions(selected)
    sources_path = Path(args.sources) if Path(args.sources).is_absolute() else repo / args.sources
    excerpts, excerpt_inputs = describe.load_excerpt_map(
        sources_path, accessions, base=repo
    )
    resolver_path = (
        Path(args.resolver) if Path(args.resolver).is_absolute() else repo / args.resolver
    )
    sec_names, _rows = _load_resolver(resolver_path)

    entries, counters = describe.describe_edges(selected, excerpts, premises, sec_names)
    report = {
        "schema": describe.REPORT_SCHEMA,
        "as_of": package_doc.get("as_of"),
        "premises_sha256": describe.PREMISES_SHA256,
        "inputs": {
            _relpath(repo, edges_path): _sha_file(edges_path),
            _relpath(repo, package_path): _sha_file(package_path),
            _relpath(repo, Path(args.premises)): _sha_file(Path(args.premises)),
            **excerpt_inputs,
            **(
                {_relpath(repo, resolver_path): _sha_file(resolver_path)}
                if resolver_path.is_file()
                else {}
            ),
        },
        "entries": entries,
        "counters": counters,
    }
    return _write_report(out, DESCRIBE_JSON, DESCRIBE_TXT, report,
                         describe.report_text(entries))


def _write_report(out: Path, json_name: str, txt_name: str, document: dict,
                  text: str) -> int:
    out.mkdir(parents=True, exist_ok=True)
    (out / json_name).write_bytes(describe.canonical_json_bytes(document))
    (out / txt_name).write_bytes(text.encode("utf-8"))
    sys.stdout.write(text)
    sys.stdout.flush()
    return 0


# --- correction-demo ---------------------------------------------------------------


def _load_extraction_rows(extraction_dir: Path) -> list:
    rows = []
    if not extraction_dir.is_dir():
        return rows
    for path in sorted(extraction_dir.rglob("*.jsonl")):
        for line in path.read_text("utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _revision_row(rows: list, revision: dict):
    """The extraction observation row a revision came from (accession +
    known_at + the exact magnitude); None when no committed row matches."""
    source = revision.get("source_ref") or {}
    period_label = (revision.get("period") or {}).get("label")
    for row in rows:
        if row.get("row_kind") != "observation":
            continue
        if (row.get("source_ref") or {}).get("accession") != source.get("accession"):
            continue
        if (row.get("published_at") or row.get("ingested_at")) != revision.get("known_at"):
            continue
        for magnitude in row.get("magnitudes") or []:
            if (
                magnitude.get("kind") == revision.get("kind")
                and (magnitude.get("period") or {}).get("label") == period_label
                and magnitude.get("value") == revision.get("value")
            ):
                return row
    return None


def _latency(row) -> tuple:
    """(correction_latency_hours, backfill flag) from an extraction row."""
    ingested = _instant((row or {}).get("ingested_at"))
    published = _instant((row or {}).get("published_at"))
    if ingested is None or published is None:
        return None, False
    hours = round((ingested - published).total_seconds() / 3600, 2)
    return hours, ingested > published + timedelta(days=30)


def _run_producer(repo: Path, as_of: str, pit_dir: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(repo / PRODUCER_REL),
            "--as-of",
            as_of,
            "--out-dir",
            str(pit_dir),
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not (
        (pit_dir / "observation_package.v2.json").is_file()
        and (pit_dir / "relationship_edges.json").is_file()
    ):
        raise ProducerFailed(
            f"producer rc={result.returncode} for --as-of {as_of}: "
            f"{(result.stdout + result.stderr).strip()[-400:]}"
        )


class ProducerFailed(Exception):
    pass


def cmd_correction_demo(args) -> int:
    repo = Path(args.repo_root).resolve()
    out = Path(args.out)
    if _out_refused(repo, out):
        return _fail("OUT_REFUSED", f"{out} is under data/ or site/")
    try:
        premises = describe.load_premises_file(args.premises)
    except (describe.PremisesDrift, OSError, ValueError) as error:
        return _fail("PREMISES_DRIFT", str(error))
    as_ofs = sorted(set(args.as_of))
    key = args.relationship_key
    producer = repo / PRODUCER_REL
    if not producer.is_file():
        return _fail("PRODUCER_MISSING", str(producer))

    try:
        for as_of in as_ofs:
            _run_producer(repo, as_of, out / "pit" / as_of)
        rerun_as_of = as_ofs[0]
        _run_producer(repo, rerun_as_of, out / "pit" / f"{rerun_as_of}.rerun")
    except ProducerFailed as error:
        return _fail("PRODUCER_FAILED", str(error))
    reproducible = all(
        (out / "pit" / rerun_as_of / name).read_bytes()
        == (out / "pit" / f"{rerun_as_of}.rerun" / name).read_bytes()
        for name in ("observation_package.v2.json", "relationship_edges.json")
    )

    edges_path = repo / EDGES_REL
    package_path = repo / PACKAGE_REL
    if not edges_path.is_file() or not package_path.is_file():
        return _fail("INPUT_MISSING", f"{edges_path} / {package_path}")
    current_edges = _read_json(edges_path)
    current_package = _read_json(package_path)
    current_restatements = [
        {
            "relationship_key": revision["relationship_key"],
            "accession": (revision.get("source_ref") or {}).get("accession"),
            "revision_id": revision["revision_id"],
            "period_label": (revision.get("period") or {}).get("label"),
            "known_at": revision.get("known_at"),
        }
        for revision in current_package.get("magnitude_revisions") or []
        if revision.get("revision_kind") == "restatement"
    ]

    sources_path = repo / SOURCES_REL
    extraction_rows = _load_extraction_rows(repo / EXTRACTION_REL)
    resolver_path = repo / RESOLVER_REL
    sec_names, _rows = _load_resolver(resolver_path)

    # Excerpts for every view's relationship K, loaded once.
    pit_accessions = set()
    for as_of in as_ofs:
        pit_edges = _read_json(out / "pit" / as_of / "relationship_edges.json")
        pit_accessions |= _needed_accessions(
            [edge for edge in pit_edges.get("edges") or []
             if edge["relationship_key"] == key]
        )
    excerpts, excerpt_inputs = describe.load_excerpt_map(
        sources_path, pit_accessions, base=repo
    )

    heading = premises["corrections"]["as_known_at"]
    views = []
    seen_revisions: set = set()
    for as_of in as_ofs:
        pit_edges = _read_json(out / "pit" / as_of / "relationship_edges.json")
        pit_edge = next(
            (
                edge
                for edge in pit_edges.get("edges") or []
                if edge["relationship_key"] == key
            ),
            None,
        )
        if pit_edge is None:
            views.append(
                {
                    "as_of": as_of,
                    "package_id": pit_edges.get("package_id"),
                    "entry": None,
                    "correction_lineage": [],
                    "new_revisions": [],
                }
            )
            continue
        entries, _counters = describe.describe_edges(
            [pit_edge], excerpts, premises, sec_names
        )
        entry = entries[0]
        entry["lines"].insert(
            0,
            describe.line(
                "as_known_at",
                heading["en"].format(as_of=as_of),
                heading["zh"].format(as_of=as_of),
                None,
            ),
        )
        visible_ids = {
            revision["revision_id"]
            for revision in pit_edge.get("magnitude_history") or []
        }
        new_revisions = []
        for revision in sorted(
            pit_edge.get("magnitude_history") or [],
            key=lambda r: (
                r["kind"],
                (r.get("period") or {}).get("start") or "",
                (r.get("period") or {}).get("label") or "",
                r["revision_seq"],
            ),
        ):
            if revision["revision_id"] not in visible_ids - seen_revisions:
                continue
            row = _revision_row(extraction_rows, revision)
            hours, backfill = _latency(row)
            new_revisions.append(
                {
                    "revision_id": revision["revision_id"],
                    "kind": revision["kind"],
                    "period_label": (revision.get("period") or {}).get("label"),
                    "asserting_party": revision.get("asserting_party"),
                    "accession": (revision.get("source_ref") or {}).get("accession"),
                    "known_at": revision.get("known_at"),
                    "correction_latency_hours": hours,
                    "backfill": backfill,
                }
            )
        seen_revisions |= visible_ids
        views.append(
            {
                "as_of": as_of,
                "package_id": pit_edges.get("package_id"),
                "entry": entry,
                "correction_lineage": pit_edge.get("correction_lineage") or [],
                "new_revisions": new_revisions,
            }
        )

    inputs = {
        _relpath(repo, edges_path): _sha_file(edges_path),
        _relpath(repo, package_path): _sha_file(package_path),
        _relpath(repo, Path(args.premises)): _sha_file(Path(args.premises)),
        **excerpt_inputs,
    }
    if resolver_path.is_file():
        inputs[_relpath(repo, resolver_path)] = _sha_file(resolver_path)
    extraction_dir = repo / EXTRACTION_REL
    if extraction_dir.is_dir():
        for path in sorted(extraction_dir.rglob("*.jsonl")):
            inputs[_relpath(repo, path)] = _sha_file(path)

    demo = {
        "schema": describe.DEMO_SCHEMA,
        "premises_sha256": describe.PREMISES_SHA256,
        "relationship_key": key,
        "as_ofs": as_ofs,
        "reproducible": reproducible,
        "rerun_as_of": rerun_as_of,
        "views": views,
        "current_package_as_of": current_package.get("as_of"),
        "current_package_restatements": current_restatements,
        "inputs": inputs,
    }
    return _write_report(out, DEMO_JSON, DEMO_TXT, demo,
                         demo_text(demo, as_ofs, rerun_as_of, reproducible,
                                   current_restatements))


def demo_text(demo: dict, as_ofs: list, rerun_as_of: str, reproducible: bool,
              restatements: list) -> str:
    out = [
        f"correction demo for {demo['relationship_key']}",
        "as-of views (sorted): " + ", ".join(as_ofs),
        "",
    ]
    for view in demo["views"]:
        out.append(f"== as known at {view['as_of']} ==")
        if view["entry"] is None:
            out.append("relationship absent at this as-of")
        else:
            out.append(describe.report_text([view["entry"]]).rstrip("\n"))
        out.append(
            "correction_lineage visible at "
            f"{view['as_of']}: "
            + json.dumps(
                view["correction_lineage"], sort_keys=True, ensure_ascii=False
            )
        )
        out.append(f"revisions first appearing at {view['as_of']}:")
        if view["new_revisions"]:
            for revision in view["new_revisions"]:
                label = (
                    f"  {revision['revision_id']} "
                    f"({revision['kind']} {revision['period_label']}, "
                    f"{revision['accession']}): "
                    f"correction_latency_hours={revision['correction_latency_hours']}"
                )
                if revision["backfill"]:
                    label += " — backfill latency (not natural-operations latency)"
                out.append(label)
        else:
            out.append("  (none)")
        out.append("")
    out.append(
        f"== reproducible: {str(reproducible).lower()} — first as-of "
        f"{rerun_as_of} rebuilt into pit/{rerun_as_of}.rerun; package bytes "
        + ("identical" if reproducible else "DIFFER")
    )
    if restatements:
        out.append(
            "restatements in the current package "
            f"(as_of {demo['current_package_as_of']}): FOUND {len(restatements)}"
        )
        for row in restatements:
            out.append(
                f"  FOUND {row['relationship_key']} {row['accession']} "
                f"({row['revision_id']}, {row['period_label']})"
            )
    else:
        out.append(
            "restatements in the current package "
            f"(as_of {demo['current_package_as_of']}): ABSENT — none found; "
            "none synthesized"
        )
    return "\n".join(out) + "\n"


# --- CLI ----------------------------------------------------------------------


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def common(sub_parser):
        sub_parser.add_argument("--repo-root", default=str(REPO_ROOT))
        sub_parser.add_argument("--out", required=True)
        sub_parser.add_argument(
            "--premises",
            default=None,
            help="frozen premise table (default: the repo's m3 bytes)",
        )

    describe_parser = sub.add_parser(
        "describe", help="render descriptive entries for the committed edges"
    )
    common(describe_parser)
    describe_parser.add_argument("--issuer", nargs="*", default=None)
    describe_parser.add_argument("--edges", default=EDGES_REL)
    describe_parser.add_argument("--package", default=PACKAGE_REL)
    describe_parser.add_argument("--sources", default=SOURCES_REL)
    describe_parser.add_argument("--resolver", default=RESOLVER_REL)

    demo_parser = sub.add_parser(
        "correction-demo",
        help="rebuild one relationship at several as-ofs and demo corrections",
    )
    common(demo_parser)
    demo_parser.add_argument("--relationship-key", required=True)
    demo_parser.add_argument("--as-of", action="append", required=True)

    args = parser.parse_args(argv)
    if args.premises is None:
        args.premises = str(
            Path(args.repo_root) / describe.PREMISES_RELPATH
        )
    if args.command == "describe":
        return cmd_describe(args)
    return cmd_correction_demo(args)


if __name__ == "__main__":
    sys.exit(main())
