#!/usr/bin/env python3
"""GMI ORCH-REL M2 precision CLI: blind stratified samples and their scoring.

``sample`` renders committed observation rows into blind review packs: one
plain-English claim next to its verbatim excerpt per item, plus deliberately
wrong decoy claims that measure the reviewer.  ``score`` recomputes the sample
from the current inputs, checks the verdicts against the review rules, and
writes the precision report (per-stratum Wilson intervals, a stratified-normal
weighted overall, field error counts, and the decoy acceptance rate that decides
``reviewer_reliable``) — and only then the per-item answer key.

It measures whether the rows say what the filings say.  Nothing here scores,
ranks, sizes or predicts companies, and no sample, verdict or report is
committed by this lane: everything lands under the caller's --out-dir.

Exit codes: 0 success, 2 for any refusal (bad salt, empty/dirty out dir, an
extraction row that violates its contract, input drift, salt mismatch, a
recomputed sample that no longer matches the reviewed packs, missing verdicts
without --allow-missing).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import jsonschema  # noqa: E402

from engine.company_intelligence.relationships import precision as prec  # noqa: E402
from engine.company_intelligence.relationships import replay  # noqa: E402
from scripts.build_relationship_observations import (  # noqa: E402
    _validate_row,
    _extraction_validator,
)

DEFAULT_EXTRACTION = (
    REPO_ROOT / "research/theme_graph/gmi_relationships_20261021/extraction"
)
DEFAULT_SOURCES = (
    REPO_ROOT / "research/theme_graph/gmi_relationships_20261021/sources"
)
DEFAULT_LEAVES = (
    REPO_ROOT
    / "research/theme_graph/gmi_relationships_20261021/m2_inputs/leaves_v1.json"
)
DEFAULT_SEED = "gmi-rel-m2-precision-v1"
GUIDE_NAME = "GUIDE.md"
MANIFEST_NAME = "manifest.json"
KEY_NAME = "sample_key.jsonl"
REPORT_NAME = "precision_report.json"
REVIEW_DIR = "review"

CODE_SCHEMA_INVALID = "VERDICT_SCHEMA_INVALID"
CODE_DUPLICATE = "VERDICT_DUPLICATE"
CODE_UNKNOWN_ITEM = "VERDICT_UNKNOWN_ITEM"
CODE_QUOTE_NOT_FOUND = "QUOTE_NOT_FOUND"
CODE_QUOTE_MISSING = "QUOTE_MISSING"
CODE_MISSING_VERDICTS = "MISSING_VERDICTS"


def _fail(message: str) -> int:
    print(f"relationship_m2_precision: {message}")
    return 2


def _canon_line(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _pretty_bytes(obj) -> bytes:
    text = json.dumps(obj, sort_keys=True, indent=1, ensure_ascii=False)
    return (text + "\n").encode("utf-8")


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _input_path(path: Path) -> str:
    """Repo-relative POSIX path for in-repo inputs, absolute otherwise."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def _resolve_input(text: str) -> Path:
    path = Path(text)
    return path if path.is_absolute() else REPO_ROOT / path


def _load_salt(text: str):
    path = Path(text)
    try:
        salt = path.read_bytes()
    except OSError as error:
        return None, _fail(f"--salt-file {path} is unreadable ({error})")
    if len(salt) < 16:
        return None, _fail(
            f"--salt-file {path} is {len(salt)} bytes; at least 16 are required"
        )
    return salt, None


def _key_fn(salt: bytes, seed: str):
    return lambda x: prec.key(salt, seed, x)


def _extraction_files(extraction_dir: Path):
    return sorted(
        (path for path in extraction_dir.rglob("*.jsonl") if path.is_file()),
        key=lambda path: path.relative_to(extraction_dir).as_posix(),
    )


def _load_file_rows(extraction_dir: Path):
    """[(relpath, lineno, row)] for observation rows, in visit order.

    Any observation-kind line that fails its contract is a hard refusal naming
    file:line and the first problem — a sample built over an invalid row would
    not be reproducible.
    """
    validator = _extraction_validator()
    file_rows = []
    for path in _extraction_files(extraction_dir):
        relpath = path.relative_to(extraction_dir).as_posix()
        with path.open("rb") as handle:
            for lineno, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line.decode("utf-8"))
                except ValueError as error:
                    return None, _fail(f"{relpath}:{lineno}: not JSON ({error})")
                if not isinstance(row, dict):
                    return None, _fail(f"{relpath}:{lineno}: not a JSON object")
                if row.get("row_kind") != "observation":
                    continue
                problems = _validate_row(row, validator)
                if problems:
                    return None, _fail(f"{relpath}:{lineno}: {problems[0]}")
                file_rows.append((relpath, lineno, row))
    return file_rows, None


def _dedupe_rows(file_rows):
    """([(relpath, lineno, row)], error): identical observation rows collapse
    to their first occurrence; one observation_id with differing content is a
    refusal."""
    seen: dict = {}
    rows = []
    for relpath, lineno, row in file_rows:
        observation_id = row.get("observation_id")
        row_canon = _canon_line(row)
        held = seen.get(observation_id)
        if held is None:
            seen[observation_id] = (row_canon, relpath, lineno)
            rows.append((relpath, lineno, row))
            continue
        if held[0] != row_canon:
            return None, _fail(
                f"observation {observation_id} appears with differing content at "
                f"{held[1]}:{held[2]} and {relpath}:{lineno}; the population would "
                "be ambiguous"
            )
    return rows, None


def _index_sources(sources_dir: Path):
    """{(accession, span.raw_sha256): (excerpt doc, relpath)} over every *.json."""
    index: dict = {}
    if not sources_dir.is_dir():
        return index
    for path in sorted(
        (path for path in sources_dir.rglob("*.json") if path.is_file()),
        key=lambda path: path.relative_to(sources_dir).as_posix(),
    ):
        relpath = path.relative_to(sources_dir).as_posix()
        try:
            doc = json.loads(path.read_bytes().decode("utf-8"))
        except (OSError, ValueError):
            continue  # unkeyable; any row citing it reads as EXCERPT_MISSING
        span = doc.get("span") if isinstance(doc, dict) else None
        accession = doc.get("accession") if isinstance(doc, dict) else None
        span_sha = span.get("raw_sha256") if isinstance(span, dict) else None
        if isinstance(accession, str) and isinstance(span_sha, str):
            index[(accession, span_sha)] = (doc, relpath)
    return index


def _load_leaves(text: str):
    path = Path(text)
    try:
        doc = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, ValueError) as error:
        return None, _fail(f"leaves file {path} is unreadable ({error})")
    domain_of = doc.get("domain_of") if isinstance(doc, dict) else None
    if not isinstance(domain_of, dict):
        return None, _fail(f"leaves file {path} carries no domain_of object")
    return domain_of, None


def _used_excerpt_relpaths(file_rows, excerpt_index) -> set:
    used = set()
    for _relpath, _lineno, row in file_rows:
        source = row.get("source_ref") or {}
        held = excerpt_index.get(
            (source.get("accession"), source.get("span_sha256"))
        )
        if held is not None:
            used.add(held[1])
    return used


def _build_inputs(extraction_dir: Path, extraction_files, used_relpaths: set,
                  sources_dir: Path, leaves_path: Path) -> dict:
    inputs: dict = {}
    for path in extraction_files:
        inputs[_input_path(path)] = _sha_file(path)
    for relpath in sorted(used_relpaths):
        inputs[_input_path(sources_dir / relpath)] = _sha_file(sources_dir / relpath)
    inputs[_input_path(leaves_path)] = _sha_file(leaves_path)
    return inputs


def _excerpt_view(excerpt: dict) -> dict:
    span = excerpt.get("span") or {}
    return {
        "accession": excerpt.get("accession"),
        "form": excerpt.get("form"),
        "filed_at": excerpt.get("filed_at"),
        "url": excerpt.get("url"),
        "text": span.get("normalized"),
    }


def _build_items(population, plan, decoys, key_fn, seed: str) -> tuple:
    """(items, identities) for the real selections and the decoys."""
    items: list = []
    identities: list = []
    for entry in plan["selected"]:
        claim = prec.claim_from_row(entry["row"])
        item_id = key_fn("item:" + entry["observation_id"] + ":real")[:16]
        items.append(
            {
                "schema": prec.ITEM_SCHEMA_NAME,
                "item_id": item_id,
                "claim_text": prec.render_claim(claim),
                "claim": claim,
                "excerpt": _excerpt_view(entry["excerpt"]),
            }
        )
        identities.append(
            {
                "item_id": item_id,
                "observation_id": entry["observation_id"],
                "stratum": entry["stratum"],
                "is_decoy": False,
                "decoy_kind": None,
            }
        )
    for decoy in decoys:
        entry = next(
            e for e in population if e["observation_id"] == decoy["observation_id"]
        )
        item_id = key_fn(
            "item:" + decoy["observation_id"] + ":decoy:" + decoy["kind"]
        )[:16]
        items.append(
            {
                "schema": prec.ITEM_SCHEMA_NAME,
                "item_id": item_id,
                "claim_text": prec.render_claim(decoy["claim"]),
                "claim": decoy["claim"],
                "excerpt": _excerpt_view(entry["excerpt"]),
            }
        )
        identities.append(
            {
                "item_id": item_id,
                "observation_id": decoy["observation_id"],
                "stratum": entry["stratum"],
                "is_decoy": True,
                "decoy_kind": decoy["kind"],
            }
        )
    items.sort(key=lambda item: item["item_id"])
    identities.sort(key=lambda row: row["item_id"])
    return items, identities


def _problems(validator, document) -> list:
    return [
        f"{'/'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(document), key=lambda e: list(e.path))
    ]


def _validator(schema: dict):
    return jsonschema.validators.validator_for(schema)(schema)


def cmd_sample(args) -> int:
    salt, error = _load_salt(args.salt_file)
    if error is not None:
        return error
    out_dir = Path(args.out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        return _fail(f"--out-dir {out_dir} exists and is not empty")
    domain_of, error = _load_leaves(args.leaves)
    if error is not None:
        return error

    extraction_dir = Path(args.extraction)
    if not extraction_dir.is_dir():
        return _fail(f"--extraction {extraction_dir} is not a directory")
    extraction_files = _extraction_files(extraction_dir)
    file_rows, error = _load_file_rows(extraction_dir)
    if error is not None:
        return error
    rows, error = _dedupe_rows(file_rows)
    if error is not None:
        return error

    sources_dir = Path(args.sources)
    excerpt_index = _index_sources(sources_dir)
    population, excluded = prec.build_population(
        rows,
        excerpt_index,
        domain_of,
        replay.verify_excerpt,
    )

    key_fn = _key_fn(salt, args.seed)
    plan = prec.select_sample(population, args.n, args.floor, key_fn)
    selected_ids = {entry["observation_id"] for entry in plan["selected"]}
    decoys, decoy_counters = prec.build_decoys(
        population, selected_ids, args.decoys, key_fn
    )
    items, identities = _build_items(population, plan, decoys, key_fn, args.seed)

    packs = [
        ("review/" + f"pack_{index:03d}.jsonl", items[start : start + args.pack_size])
        for index, start in enumerate(range(0, len(items), args.pack_size), start=1)
    ]
    manifest = {
        "schema": prec.MANIFEST_SCHEMA_NAME,
        "seed": args.seed,
        "salt_sha256": hashlib.sha256(salt).hexdigest(),
        "n_target": args.n,
        "n_effective": sum(plan["alloc"].values()),
        "floor": args.floor,
        "pack_size": args.pack_size,
        "decoys_requested": args.decoys,
        "decoys_made": len(decoys),
        "items_total": len(items),
        "packs": [{"pack": name, "items": len(pack_items)} for name, pack_items in packs],
        "population_below_target": plan["below_target"],
        "population_total": len(population),
        "population_by_stratum": {s: plan["sizes"][s] for s in sorted(plan["sizes"])},
        "allocation": {s: plan["alloc"][s] for s in sorted(plan["alloc"])},
        "excluded": {
            "EXCERPT_MISSING": excluded["EXCERPT_MISSING"],
            "EXCERPT_CORRUPT": excluded["EXCERPT_CORRUPT"],
        },
        "counters": dict(sorted(decoy_counters.items())),
        "inputs": _build_inputs(
            extraction_dir,
            extraction_files,
            _used_excerpt_relpaths(file_rows, excerpt_index),
            sources_dir,
            Path(args.leaves),
        ),
    }

    item_validator = _validator(prec.ITEM_SCHEMA)
    manifest_validator = _validator(prec.MANIFEST_SCHEMA)
    problems = []
    for item in items:
        problems += _problems(item_validator, item)
    problems += _problems(manifest_validator, manifest)
    if problems:
        for problem in problems[:5]:
            print(f"relationship_m2_precision: output-invalid: {problem}")
        return _fail("sample outputs do not conform to their contracts; nothing written")

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / REVIEW_DIR).mkdir(exist_ok=True)
    for name, pack_items in packs:
        (out_dir / name).write_text(
            "".join(_canon_line(item) + "\n" for item in pack_items),
            encoding="utf-8",
        )
    (out_dir / GUIDE_NAME).write_text(prec.REVIEW_GUIDE, encoding="utf-8")
    (out_dir / MANIFEST_NAME).write_bytes(_pretty_bytes(manifest))

    by_kind: dict = {}
    for decoy in decoys:
        by_kind[decoy["kind"]] = by_kind.get(decoy["kind"], 0) + 1
    print(
        "population_by_stratum: "
        + " ".join(f"{s}={plan['sizes'][s]}" for s in sorted(plan["sizes"]))
    )
    print(
        "allocation: "
        + " ".join(f"{s}={plan['alloc'][s]}" for s in sorted(plan["alloc"]))
    )
    print(
        f"n_effective={manifest['n_effective']} "
        f"population_total={manifest['population_total']} "
        f"population_below_target={manifest['population_below_target']} "
        f"items_total={len(items)}"
    )
    print(
        "decoys by kind: "
        + (
            " ".join(f"{kind}={by_kind[kind]}" for kind in sorted(by_kind))
            if by_kind
            else "(none)"
        )
    )
    short = args.decoys - len(decoys)
    print(f"decoys_short: {short}")
    print(
        f"excluded: EXCERPT_MISSING={len(excluded['EXCERPT_MISSING'])} "
        f"EXCERPT_CORRUPT={len(excluded['EXCERPT_CORRUPT'])}"
    )
    print(
        "excluded EXCERPT_MISSING ids: "
        + (", ".join(excluded["EXCERPT_MISSING"]) or "(none)")
    )
    print(
        "excluded EXCERPT_CORRUPT ids: "
        + (", ".join(excluded["EXCERPT_CORRUPT"]) or "(none)")
    )
    return 0


def _recompute(salt: bytes, args, manifest: dict):
    """(state, error) — the recomputed sample over the CURRENT inputs."""
    extraction_dir = Path(args.extraction)
    sources_dir = Path(args.sources)
    leaves_path = Path(args.leaves)
    domain_of, error = _load_leaves(leaves_path)
    if error is not None:
        return None, error
    if not extraction_dir.is_dir():
        return None, _fail(f"--extraction {extraction_dir} is not a directory")
    extraction_files = _extraction_files(extraction_dir)
    file_rows, error = _load_file_rows(extraction_dir)
    if error is not None:
        return None, error
    rows, error = _dedupe_rows(file_rows)
    if error is not None:
        return None, error
    excerpt_index = _index_sources(sources_dir)
    population, excluded = prec.build_population(
        rows,
        excerpt_index,
        domain_of,
        replay.verify_excerpt,
    )
    key_fn = _key_fn(salt, manifest["seed"])
    plan = prec.select_sample(population, manifest["n_target"], manifest["floor"], key_fn)
    selected_ids = {entry["observation_id"] for entry in plan["selected"]}
    decoys, _counters = prec.build_decoys(
        population, selected_ids, manifest["decoys_requested"], key_fn
    )
    items, identities = _build_items(population, plan, decoys, key_fn, manifest["seed"])
    inputs = _build_inputs(
        extraction_dir,
        extraction_files,
        _used_excerpt_relpaths(file_rows, excerpt_index),
        sources_dir,
        leaves_path,
    )
    return {
        "items": items,
        "identities": identities,
        "population": population,
        "sizes": plan["sizes"],
        "excluded": excluded,
        "inputs": inputs,
    }, None


def cmd_score(args) -> int:
    sample_dir = Path(args.sample_dir)
    manifest_path = sample_dir / MANIFEST_NAME
    if not manifest_path.is_file():
        return _fail(f"{manifest_path} is missing; run `sample` first")
    try:
        manifest = json.loads(manifest_path.read_bytes().decode("utf-8"))
    except ValueError as error:
        return _fail(f"{manifest_path} is not JSON ({error})")

    salt, error = _load_salt(args.salt_file)
    if error is not None:
        return error
    if hashlib.sha256(salt).hexdigest() != manifest.get("salt_sha256"):
        return _fail("SALT_MISMATCH: the salt file does not hash to the sample's "
                     "recorded salt_sha256")

    # Input drift, part 1: every recorded input must still hash identically.
    for relpath, sha in sorted((manifest.get("inputs") or {}).items()):
        path = _resolve_input(relpath)
        if not path.is_file():
            return _fail(f"INPUT_DRIFT: recorded input {relpath} is missing")
        if _sha_file(path) != sha:
            return _fail(f"INPUT_DRIFT: recorded input {relpath} changed on disk")

    state, error = _recompute(salt, args, manifest)
    if error is not None:
        return error

    # Input drift, part 2: the recomputed input set must equal the recorded one
    # (a file added to or removed from an inputs root is drift too).
    recorded = manifest.get("inputs") or {}
    recomputed = state["inputs"]
    for relpath in sorted(set(recorded) | set(recomputed)):
        if recorded.get(relpath) != recomputed.get(relpath):
            return _fail(f"INPUT_DRIFT: {relpath} is not the recorded input set")

    review_dir = sample_dir / REVIEW_DIR
    reviewed_ids = set()
    for pack in sorted(review_dir.glob("pack_*.jsonl")):
        for line in pack.read_text("utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except ValueError as error:
                return _fail(f"{pack} holds a line that is not JSON ({error})")
            if isinstance(item, dict) and isinstance(item.get("item_id"), str):
                reviewed_ids.add(item["item_id"])
    recomputed_ids = {item["item_id"] for item in state["items"]}
    if reviewed_ids != recomputed_ids:
        return _fail(
            "SAMPLE_MISMATCH: the reviewed packs hold "
            f"{len(reviewed_ids)} items but the current inputs recompute "
            f"{len(recomputed_ids)}; re-run `sample` and review again"
        )

    # Verdicts.
    verdicts_dir = Path(args.verdicts)
    verdict_files = sorted(
        (path for path in verdicts_dir.rglob("*.jsonl") if path.is_file()),
        key=lambda path: path.relative_to(verdicts_dir).as_posix(),
    )
    validator = _validator(prec.VERDICT_SCHEMA)
    codes: dict = {}
    by_item: dict = {}
    for path in verdict_files:
        for line in path.read_text("utf-8").splitlines():
            if not line.strip():
                continue
            try:
                verdict = json.loads(line)
            except ValueError:
                codes[CODE_SCHEMA_INVALID] = codes.get(CODE_SCHEMA_INVALID, 0) + 1
                continue
            if _problems(validator, verdict):
                codes[CODE_SCHEMA_INVALID] = codes.get(CODE_SCHEMA_INVALID, 0) + 1
                continue
            by_item.setdefault(verdict["item_id"], []).append(verdict)
    valid: dict = {}
    for item_id, lines in sorted(by_item.items()):
        if len(lines) > 1:
            codes[CODE_DUPLICATE] = codes.get(CODE_DUPLICATE, 0) + 1
            continue  # all lines for a duplicated item are invalid
        verdict = lines[0]
        if verdict["item_id"] not in recomputed_ids:
            codes[CODE_UNKNOWN_ITEM] = codes.get(CODE_UNKNOWN_ITEM, 0) + 1
            continue
        valid[item_id] = verdict

    item_by_id = {item["item_id"]: item for item in state["items"]}
    identity_by_id = {row["item_id"]: row for row in state["identities"]}
    strata: dict = {}
    for stratum in sorted(state["sizes"]):
        strata[stratum] = {
            "population": state["sizes"][stratum],
            "reviewed": 0,
            "accepted": 0,
            "unclear": 0,
            "missing": 0,
        }
    field_errors = {"direction": 0, "counterparty": 0, "status": 0, "magnitude": 0}
    decoy_stats = {"reviewed": 0, "accepted": 0, "by_kind": {}}
    missing_ids: list = []
    for item_id in sorted(recomputed_ids):
        identity = identity_by_id[item_id]
        verdict = valid.get(item_id)
        if identity["is_decoy"]:
            bucket = decoy_stats["by_kind"].setdefault(
                identity["decoy_kind"], [0, 0]
            )
            if verdict is None:
                missing_ids.append(item_id)
                continue
            decoy_stats["reviewed"] += 1
            bucket[0] += 1
            claim = item_by_id[item_id]["claim"]
            if prec.verdict_accepts(verdict, item_by_id[item_id]["excerpt"]["text"],
                                    len(claim["magnitudes"])):
                decoy_stats["accepted"] += 1
                bucket[1] += 1
            continue
        block = strata[identity["stratum"]]
        if verdict is None:
            block["missing"] += 1
            missing_ids.append(item_id)
            continue
        block["reviewed"] += 1
        claim = item_by_id[item_id]["claim"]
        text = item_by_id[item_id]["excerpt"]["text"]
        problem = prec.quote_problem(verdict, text)
        if problem is not None:
            codes[problem] = codes.get(problem, 0) + 1
        for field in field_errors:
            if verdict[field] == "wrong":
                field_errors[field] += 1
        if prec.verdict_accepts(verdict, text, len(claim["magnitudes"])):
            block["accepted"] += 1
        elif prec.effective_relationship(verdict, text) == "unclear":
            block["unclear"] += 1

    if missing_ids and not args.allow_missing:
        return _fail(
            f"missing verdicts for {len(missing_ids)} items "
            f"(first: {missing_ids[0]}); pass --allow-missing to score anyway"
        )
    if missing_ids:
        codes[CODE_MISSING_VERDICTS] = len(missing_ids)

    # Report.
    for stratum, block in strata.items():
        block["precision"] = (
            block["accepted"] / block["reviewed"] if block["reviewed"] else None
        )
        block["wilson95"] = prec.wilson(block["accepted"], block["reviewed"])
    reviewed_total = sum(block["reviewed"] for block in strata.values())
    accepted_total = sum(block["accepted"] for block in strata.values())
    overall_unweighted = {
        "reviewed": reviewed_total,
        "accepted": accepted_total,
        "precision": (
            accepted_total / reviewed_total if reviewed_total else None
        ),
        "wilson95": prec.wilson(accepted_total, reviewed_total),
    }
    scored_strata = [
        (stratum, block)
        for stratum, block in sorted(strata.items())
        if block["reviewed"] > 0
    ]
    if scored_strata:
        weight_total = sum(block["population"] for _s, block in scored_strata)
        weights = {
            stratum: block["population"] / weight_total
            for stratum, block in scored_strata
        }
        estimate = sum(
            weights[stratum] * block["precision"]
            for stratum, block in scored_strata
        )
        variance = sum(
            weights[stratum] ** 2
            * block["precision"]
            * (1 - block["precision"])
            / block["reviewed"]
            for stratum, block in scored_strata
        )
        half = prec.WILSON_Z * variance ** 0.5
        overall_weighted = {
            "precision": round(estimate, 4),
            "ci": [
                round(max(0.0, estimate - half), 4),
                round(min(1.0, estimate + half), 4),
            ],
            "ci_method": "stratified_normal",
        }
    else:
        overall_weighted = {"precision": None, "ci": None,
                            "ci_method": "stratified_normal"}
    decoys_reviewed = decoy_stats["reviewed"]
    decoys_accepted = decoy_stats["accepted"]
    acceptance_rate = (
        decoys_accepted / decoys_reviewed if decoys_reviewed else None
    )
    report = {
        "schema": prec.REPORT_SCHEMA_NAME,
        "strata": {s: strata[s] for s in sorted(strata)},
        "overall_unweighted": overall_unweighted,
        "overall_weighted": overall_weighted,
        "field_errors": field_errors,
        "decoys": {
            "reviewed": decoys_reviewed,
            "accepted": decoys_accepted,
            "acceptance_rate": acceptance_rate,
            "wilson95": prec.wilson(decoys_accepted, decoys_reviewed),
            "by_kind": {kind: decoy_stats["by_kind"][kind]
                        for kind in sorted(decoy_stats["by_kind"])},
        },
        "reviewer_reliable": (
            decoys_reviewed >= prec.RELIABLE_MIN_DECOYS
            and acceptance_rate is not None
            and acceptance_rate <= prec.RELIABLE_MAX_ACCEPTANCE
        ),
        "codes": dict(sorted(codes.items())),
        "inputs": recomputed,
    }
    report_validator = _validator(prec.REPORT_SCHEMA)
    problems = _problems(report_validator, report)
    if problems:
        for problem in problems[:5]:
            print(f"relationship_m2_precision: report-invalid: {problem}")
        return _fail("report does not conform to its contract; nothing written")

    report_path = Path(args.report) if args.report else sample_dir / REPORT_NAME
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(_pretty_bytes(report))
    (sample_dir / KEY_NAME).write_text(
        "".join(_canon_line(row) + "\n" for row in state["identities"]),
        encoding="utf-8",
    )

    # Table.
    print(
        f"{'stratum':<32} {'pop':>5} {'rev':>5} {'acc':>5} {'unc':>5} "
        f"{'miss':>5} {'precision':>9}  wilson95"
    )
    for stratum, block in report["strata"].items():
        print(_stratum_row(stratum, block))
    print(_stratum_row("overall_unweighted", {
        "population": sum(block["population"] for block in strata.values()),
        "reviewed": reviewed_total,
        "accepted": accepted_total,
        "unclear": sum(block["unclear"] for block in strata.values()),
        "missing": sum(block["missing"] for block in strata.values()),
        "precision": overall_unweighted["precision"],
        "wilson95": overall_unweighted["wilson95"],
    }))
    print(
        f"overall_weighted: precision={overall_weighted['precision']} "
        f"ci={overall_weighted['ci']} ({overall_weighted['ci_method']})"
    )
    print(
        f"decoys: reviewed={decoys_reviewed} accepted={decoys_accepted} "
        f"acceptance_rate={acceptance_rate} wilson95={report['decoys']['wilson95']} "
        f"reviewer_reliable={report['reviewer_reliable']}"
    )
    for kind, counts in report["decoys"]["by_kind"].items():
        print(f"decoys by kind: {kind} reviewed={counts[0]} accepted={counts[1]}")
    print(f"codes: {report['codes']}")
    print(f"report: {report_path}")
    print(f"key: {sample_dir / KEY_NAME}")
    return 0


def _stratum_row(name: str, block: dict) -> str:
    precision = block["precision"]
    interval = block.get("wilson95")
    return (
        f"{name:<32} {block['population']:>5} {block['reviewed']:>5} "
        f"{block['accepted']:>5} {block['unclear']:>5} {block['missing']:>5} "
        f"{precision if precision is not None else '-':>9}  "
        f"{interval if interval is not None else '-'}"
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Blind stratified precision samples of relationship observation "
            "rows, and their scoring (GMI ORCH-REL M2)."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sample = subparsers.add_parser(
        "sample", help="render the blind review packs, guide and manifest"
    )
    sample.add_argument("--salt-file", required=True)
    sample.add_argument("--out-dir", required=True)
    sample.add_argument("--seed", default=DEFAULT_SEED)
    sample.add_argument("--n", type=int, default=100)
    sample.add_argument("--floor", type=int, default=8)
    sample.add_argument("--decoys", type=int, default=25)
    sample.add_argument("--pack-size", type=int, default=25)
    sample.add_argument("--extraction", default=str(DEFAULT_EXTRACTION))
    sample.add_argument("--sources", default=str(DEFAULT_SOURCES))
    sample.add_argument("--leaves", default=str(DEFAULT_LEAVES))
    sample.set_defaults(handler=cmd_sample)

    score = subparsers.add_parser(
        "score", help="score verdicts against a recomputed sample"
    )
    score.add_argument("--sample-dir", required=True)
    score.add_argument("--verdicts", required=True)
    score.add_argument("--salt-file", required=True)
    score.add_argument("--extraction", default=str(DEFAULT_EXTRACTION))
    score.add_argument("--sources", default=str(DEFAULT_SOURCES))
    score.add_argument("--leaves", default=str(DEFAULT_LEAVES))
    score.add_argument(
        "--allow-missing",
        action="store_true",
        help="score even when some items have no verdict (they count as missing)",
    )
    score.add_argument(
        "--report",
        default=None,
        help=f"report path (default <sample-dir>/{REPORT_NAME})",
    )
    score.set_defaults(handler=cmd_score)

    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
