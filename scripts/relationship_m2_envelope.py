#!/usr/bin/env python3
"""GMI ORCH-REL M2 relationship envelope CLI: measure.

Prints the §8.2 envelope of measures from the committed relationship
artifacts (M0, E1-E8), plus the D1/D2 record counts by species.  This is
MEASUREMENT ONLY: no new producer, store, ranking, score, prediction or
gate.  A measure that cannot be computed is printed as OWED or ABSENT with
its reason — never estimated, never hidden.

Discipline (mirrors scripts/gmi_coverage_proof.py, never imports it): no
network, no clock call — every instant comes from the artifacts, two runs on
identical inputs are byte-identical, and an output directory under data/ or
site/ is refused (rc 2).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.company_intelligence.relationships import envelope as env  # noqa: E402

DEFAULT_INPUTS = "research/theme_graph/gmi_relationships_20261021"
PACKAGE_PATH = "data/company_intelligence/relationships/observation_package.v2.json"
EDGES_PATH = "data/company_intelligence/relationships/relationship_edges.json"
REFUSED_OUT_ROOTS = ("data", "site")

EXIT_REFUSED = 2


def _read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def _sha_file(path: Path) -> str:
    return env.sha256_hex(_read_bytes(path))


def _refuse_out(out_path: Path) -> None:
    """Refuse writing under data/ or site/ (rc 2, OUT_REFUSED)."""
    resolved = Path(str(out_path))
    if not resolved.is_absolute():
        resolved = Path(str(REPO_ROOT)) / resolved
    try:
        relative = resolved.resolve().relative_to(REPO_ROOT.resolve())
    except ValueError:
        return
    parts = relative.parts
    if parts and parts[0] in REFUSED_OUT_ROOTS:
        raise env.OutRefused(
            f"OUT_REFUSED: refusing to write under {parts[0]}/: {out_path}"
        )


def _fail(code: str, message: str) -> int:
    print(f"relationship_m2_envelope: {code}: {message}", file=sys.stderr)
    return EXIT_REFUSED


def _join_items(mapping: dict) -> str:
    return ", ".join(f"{key}={value}" for key, value in mapping.items())


def _species_line(title: str, mapping: dict) -> str:
    parts = [f"{species}={mapping.get(species, 0)}" for species in env.SPECIES_ORDER]
    extra = [
        f"{key}={value}" for key, value in sorted(mapping.items())
        if key not in env.SPECIES_ORDER
    ]
    return title + " " + " ".join(parts + extra)


def cmd_measure(args) -> int:
    try:
        _refuse_out(Path(args.out))
    except env.OutRefused as error:
        return _fail("OUT_REFUSED", str(error).replace("OUT_REFUSED: ", ""))

    inputs_dir = REPO_ROOT / args.inputs
    package_path = REPO_ROOT / PACKAGE_PATH
    edges_path = REPO_ROOT / EDGES_PATH
    leaves_path = inputs_dir / "m2_inputs" / "leaves_v1.json"
    panel_path = inputs_dir / "m2_inputs" / "envelope_panel_v1.json"
    resolver_path = inputs_dir / "m2_inputs" / "resolver_us_issuers_v1.json"
    extraction_dir = inputs_dir / "extraction"
    judging_root = inputs_dir / "m2" / "judging"

    missing = [
        label for label, path in (
            ("observation package", package_path),
            ("relationship edges", edges_path),
            ("leaves", leaves_path),
        ) if not path.is_file()
    ]
    if missing:
        return _fail(
            "INPUT_MISSING",
            "required input(s) absent: " + ", ".join(missing),
        )

    inputs: dict = {}
    inputs[PACKAGE_PATH] = _sha_file(package_path)
    inputs[EDGES_PATH] = _sha_file(edges_path)
    leaves_bytes = _read_bytes(leaves_path)
    inputs[str(leaves_path.relative_to(REPO_ROOT))] = env.sha256_hex(leaves_bytes)

    if not panel_path.is_file():
        return _fail("PANEL_DRIFT", "the predeclared panel file is absent")
    panel_bytes = _read_bytes(panel_path)
    try:
        env.verify_panel(panel_bytes, env.PANEL_SHA256,
                         env.sha256_hex(leaves_bytes))
    except env.PanelDrift as error:
        return _fail("PANEL_DRIFT", str(error))
    panel = json.loads(panel_bytes.decode("utf-8"))
    panel_rel = str(panel_path.relative_to(REPO_ROOT))
    inputs[panel_rel] = env.sha256_hex(panel_bytes)

    resolver_rows = []
    resolver_index: dict = {}
    if resolver_path.is_file():
        resolver_doc = json.loads(_read_bytes(resolver_path).decode("utf-8"))
        resolver_rows = resolver_doc.get("rows", [])
        resolver_index = env.resolver_index_of(resolver_rows)
        inputs[str(resolver_path.relative_to(REPO_ROOT))] = _sha_file(resolver_path)

    extraction_rows = []
    if extraction_dir.is_dir():
        for path in sorted(extraction_dir.rglob("*.jsonl")):
            for line in _read_bytes(path).decode("utf-8").splitlines():
                if line.strip():
                    extraction_rows.append(json.loads(line))
            inputs[str(path.relative_to(REPO_ROOT))] = _sha_file(path)

    judging_dirs = sorted(judging_root.iterdir()) if judging_root.is_dir() else []
    judging_dirs = [d for d in judging_dirs if d.is_dir()]

    package = json.loads(_read_bytes(package_path).decode("utf-8"))
    edges_doc = json.loads(_read_bytes(edges_path).decode("utf-8"))
    leaves = json.loads(leaves_bytes.decode("utf-8"))
    as_of = package.get("as_of")

    lines: list = []
    add = lines.append
    add("GMI ORCH-REL M2 relationship envelope — §8.2 measures (measurement only)")
    add(f"as_of: {as_of}")
    add(f"panel_sha256: {env.PANEL_SHA256}")
    add("")

    # --- M0 ---------------------------------------------------------------
    m0 = env.m0_counts(package, edges_doc, extraction_rows, leaves)
    add("M0 record counts by species (the M2 NOT-DONE line)")
    add(
        f"  join: index_rows={m0['join']['index_rows']} "
        f"extraction_rows={m0['join']['extraction_rows']} "
        f"joined={m0['join']['joined']} "
        f"extraction_only={m0['join']['extraction_only']}"
    )
    if m0["join"]["join_missing"]:
        add(
            "  join_missing (index ids with no extraction row): "
            + ",".join(m0["join"]["join_missing"])
        )
    for bucket in ("observations", "edges", "non_edges"):
        for domain in ("D1", "D2", "ALL"):
            add(_species_line(f"  {bucket} {domain}:", m0[bucket][domain]))
    add(f"  excluded dispositions: {_join_items(m0['excluded_dispositions']) or 'none'}")
    for domain in ("D1", "D2", "ALL"):
        states = m0["coverage"][domain]
        add(f"  coverage {domain}: {_join_items(dict(sorted(states.items()))) or 'none'}")
    add("")

    # --- E1 ---------------------------------------------------------------
    e1 = env.e1_coverage(package, leaves)
    add("E1 issuer relation coverage (every eligible issuer accounted)")
    for domain in ("D1", "D2"):
        block = e1["domains"][domain]
        add(
            f"  {domain}: total={block['total']} states="
            + _join_items({k: v for k, v in block["states"].items() if v})
        )
        add(
            f"  {domain}: §8.2 reading "
            + _join_items({k: v for k, v in block["reading"].items() if v})
            + f"  (sum={sum(block['states'].values())} == {block['total']})"
        )
    add("")

    # --- E2 ---------------------------------------------------------------
    e2 = env.e2_cells(package, edges_doc, extraction_rows, leaves, e1)
    add("E2 role/species coverage cells (ELIGIBLE x species x from/to role)")
    for domain in ("D1", "D2"):
        add(f"  {domain}:")
        for species, roles in e2["per_domain"].get(domain, {}).items():
            for role, states in roles.items():
                non_zero = {
                    state: counts["total"]
                    for state, counts in states.items() if counts["total"]
                }
                known = ""
                if non_zero.get("known_fresh") or non_zero.get("known_stale"):
                    known = (
                        " [own={own_filing} counterparty={counterparty_filing}]"
                    ).format(**states.get("known_fresh")
                             or states.get("known_stale"))
                add(
                    f"    {species}/{role}: "
                    + (_join_items(non_zero) if non_zero else "all not_assessed")
                    + known
                )
    add(f"  cells_total={e2['cells_total']}")
    add(f"  caveat: {e2['caveat']}")
    add("")

    # --- E3 ---------------------------------------------------------------
    ledger_rows, materialize_reports, judging_files = env.read_judging(judging_dirs)
    e3 = env.e3_sources(
        package, leaves, judging_dirs,
        inputs_dir=inputs_dir,
        ledger_rows=ledger_rows, materialize_reports=materialize_reports,
    )
    for path in judging_files:
        try:
            inputs[str(path.relative_to(REPO_ROOT))] = _sha_file(path)
        except ValueError:
            pass
    add("E3 source processing (§8.2 vocabulary)")
    add(f"  judging ledger: {e3['judging_state']}")
    for domain in ("D1", "D2", "OTHER"):
        block = e3["per_domain"][domain]
        states = {k: v for k, v in block["issuers"].items() if v} \
            if block["issuers"] else {}
        add(f"  {domain}: issuers " + (_join_items(states) or "none"))
        if block["issuers"]:
            add(f"  {domain}: m1_pinned_documents={block['m1_pinned_documents']}")
        add(
            f"  {domain}: filings_by_state "
            + (_join_items(block["filings_by_state"]) or "none")
        )
        add(
            f"  {domain}: documents_by_state "
            + (_join_items(block["documents_by_state"]) or "none")
        )
        if block["documents_failed"] or block["documents_skipped"]:
            add(
                f"  {domain}: documents failed={block['documents_failed']} "
                f"skipped={block['documents_skipped']}"
            )
        add(
            f"  {domain}: parse_outcomes "
            + (_join_items(block["parse_outcomes"]) if block["parse_outcomes"]
               else "ABSENT")
        )
    add("")

    # --- E4 ---------------------------------------------------------------
    e4 = env.e4_recall()
    add("E4 extraction recall")
    add(f"  value={e4['value']} state={e4['state']}")
    add(f"  reason: {e4['reason']}")
    add("")

    # --- E5 ---------------------------------------------------------------
    e5 = env.e5_precision(args.precision_dir)
    for path in e5.pop("files_read", []) or []:
        try:
            inputs[str(Path(path).relative_to(REPO_ROOT))] = _sha_file(Path(path))
        except ValueError:
            inputs[str(path)] = _sha_file(Path(path))
    add("E5 positive precision")
    if e5["state"] == "SCORED":
        overall = e5["overall_unweighted"] or {}
        add(
            f"  overall accepted={overall.get('accepted')}"
            f"/{overall.get('reviewed')} precision={overall.get('precision')}"
        )
        add(f"  overall wilson95={overall.get('wilson95')}")
        for stratum, block in sorted((e5["strata"] or {}).items()):
            add(
                f"  stratum {stratum}: reviewed={block.get('reviewed')} "
                f"accepted={block.get('accepted')} precision={block.get('precision')} "
                f"wilson95={block.get('wilson95')}"
            )
        weighted = e5.get("overall_weighted") or {}
        add(
            f"  overall_weighted precision={weighted.get('precision')} "
            f"ci={weighted.get('ci')}"
        )
        decoys = e5.get("decoys") or {}
        add(
            f"  decoys reviewed={decoys.get('reviewed')} "
            f"accepted={decoys.get('accepted')} "
            f"acceptance_rate={decoys.get('acceptance_rate')}"
        )
        add(f"  reviewer_reliable={e5.get('reviewer_reliable')}")
    elif e5["state"] == "PREPARED_NOT_REVIEWED":
        add(
            f"  state={e5['state']} n_items={e5['n_items']} "
            f"n_real={e5['n_real']} n_decoys={e5['n_decoys']}"
        )
        add(f"  strata={_join_items(e5['strata'] or {})}")
    else:
        add(f"  state={e5['state']}")
        add(f"  reason: {e5.get('reason')}")
    add("")

    # --- E6 ---------------------------------------------------------------
    e6 = env.e6_latency(package, extraction_rows, leaves)
    judge_latency = {}
    for directory, report in sorted(materialize_reports.items()):
        direct = report.get("latency")
        if isinstance(direct, dict):
            judge_latency[str(directory)] = direct
            continue
        counters = report.get("counters")
        if isinstance(counters, dict):
            picked = {
                key: value for key, value in counters.items()
                if "latency" in key or "duration" in key
            }
            if picked:
                judge_latency[str(directory)] = picked
    if judge_latency:
        e6["judge_lane_latency"] = judge_latency
    add("E6 natural operations latency (hours, ingested - published, UTC)")
    for domain in ("D1", "D2", "ALL"):
        block = e6["per_domain"][domain]
        add(
            f"  {domain}: n={block['n']} p50={block['p50']} p90={block['p90']} "
            f"max={block['max']} clock_violations={block['clock_violations']}"
        )
    if e6.get("missing_timestamps"):
        add(f"  missing_timestamps={e6['missing_timestamps']}")
    add(
        f"  package_lag: state={e6['package_lag']['state']} "
        f"reason: {e6['package_lag']['reason']}"
    )
    if "judge_lane_latency" in e6:
        for directory, values in sorted(e6["judge_lane_latency"].items()):
            add(f"  judge_lane_latency {directory}: {_join_items(values)}")
    add("")

    # --- E7 ---------------------------------------------------------------
    e7 = env.e7_answerability(package, edges_doc, extraction_rows,
                              leaves, panel, e1, resolver_index)
    add("E7 investor usefulness — machine answerability of the predeclared panel")
    for cell in e7["cells"]:
        line = (
            f"  {cell['domain']} {cell['issuer']} ({cell['issuer_name']}) "
            f"{cell['question']} {cell['status']}"
        )
        add(line)
        add(f"    en: {cell['en']}")
        add(f"    zh: {cell['zh']}")
        if cell["cite"]:
            add(f"    cite: {cell['cite']}")
    for domain in ("D1", "D2"):
        block = e7["per_domain"][domain]
        add(f"  {domain}: answered {block['answered']}/{block['of']}")
    add(f"  {e7['note']}")
    add("")

    # --- E8 ---------------------------------------------------------------
    e8 = env.e8_evidence(package, edges_doc, extraction_rows, leaves,
                         resolver_index)
    add("E8 release evidence (preregistered hash-min selection; ABSENT is a result)")
    for row in e8["kinds"]:
        if row["state"] == "FOUND":
            add(
                f"  {row['domain']} {row['kind']}: candidates={row['candidates']} "
                f"selected={row['selected']}"
            )
            add(f"    {row['line']}")
        else:
            add(
                f"  {row['domain']} {row['kind']}: ABSENT (candidates=0)"
            )
    add(f"  selection: {e8['selection']}")
    add("")

    report = {
        "schema": env.REPORT_SCHEMA,
        "as_of": as_of,
        "inputs": dict(sorted(inputs.items())),
        "panel_sha256": env.PANEL_SHA256,
        "M0": m0,
        "E1": e1,
        "E2": e2,
        "E3": e3,
        "E4": e4,
        "E5": e5,
        "E6": e6,
        "E7": e7,
        "E8": e8,
    }

    text = "\n".join(lines) + "\n"
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = Path(str(REPO_ROOT)) / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "envelope_report.json").write_bytes(env.canon_bytes(report))
    (out_dir / "envelope_report.txt").write_bytes(text.encode("utf-8"))
    sys.stdout.write(text)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    measure = sub.add_parser(
        "measure", help="print the §8.2 envelope measures"
    )
    measure.add_argument("--out", required=True,
                         help="output directory (refused under data/ or site/)")
    measure.add_argument("--inputs", default=DEFAULT_INPUTS,
                         help="research inputs directory")
    measure.add_argument("--precision-dir", default=None,
                         help="optional M2 precision sample directory")
    measure.set_defaults(func=cmd_measure)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except env.PanelDrift as error:
        return _fail("PANEL_DRIFT", str(error))
    except env.InputMissing as error:
        return _fail("INPUT_MISSING", str(error))
    except env.OutRefused as error:
        return _fail("OUT_REFUSED", str(error))


if __name__ == "__main__":
    sys.exit(main())
