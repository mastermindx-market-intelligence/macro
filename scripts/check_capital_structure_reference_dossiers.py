#!/usr/bin/env python3
"""Operand-traceability check for the six Capital Structure reference dossiers.

A0-0 (SPEC_A0 §2 + §7 row A0-0). The six dossiers under
``research/capital_structure/e2e_20261013/reference/`` fix the expected answers
A0 accepts a reference vertical against. This script proves each expectation
traces to exact permitted evidence: every operand resolves either to a served
``EvidenceRef`` in the state bundle's ``evidence_index`` (key
``<manifest_id>/<span_id>``) or to a qualified span of the reference pack
(label + sha256). It never fetches, never writes, and exits non-zero when an
expectation is untraceable, so the harness can never prove the engine agrees
with itself.

Dossier file shape (fixed here and in the dossiers; exactly one fenced YAML
block per file, then the fixed markdown sections):

    ```yaml
    schema: capital_structure.reference_dossier.v1
    ticker: AIR                          # pack archetype key
    issuer_id: sec:cik:0000001750
    cik: "0000001750"
    registry_name: AAR CORP
    binding_status: qualified            # identity_for(pack, ticker).qualification
    verdict_hint: accept                 # accept | withhold | reject
    gap_ids: []                          # reference-pack gap ids named by this dossier
    j5_cutoff: "2026-10-17"              # then-known cutoff date for J5
    expectations:
      - path_id: qncx:baby_shelf_offerable_total
        family: registration
        rule_id: sec_cdi.116.23          # active rule-applicability pack rule id
        rule_example_id: cdi_116_23_concurrent_continuous_offerings
        rule_class: staff_interpretation # the rule source's reference-pack class
        unit: usd                        # non-empty when expected is set
        expected: "7500000"              # Decimal STRING; null rows carry `gap:`
        gap: null                        # reason when no admissible expected value
        arithmetic: one_third_limit_usd - sold_to_date_usd
        operands:                        # every operand carries exactly one locator
          - name: one_third_limit_usd
            pack_span: cdi_securities_act_forms_q116_23
            text_sha256: a85fb5d9d3a8132b7782e84e59c8906d2cefda0fcff357e34137218940b28cdb
          - name: sold_to_date_usd
            ref: manifest:cs:<64hex>/root:<64hex>
            text_sha256: <64hex>         # optional cross-check against the bundle entry
    negatives:                           # at least two per dossier
      - name: route_without_rule_pack_witness
        expect: unknown                  # a typed state member OR "detail: ..." text
        state: ROUTE_STATUSES            # which frozen tuple `expect` is drawn from
        rule_id: form_f3.I.B.5           # optional
        reason: ...
    ```

Exit codes: 0 = every expectation traceable · 1 = at least one UNTRACEABLE
line printed · 2 = a dossier is missing or malformed · 3 = the real state
bundle is absent on this tree (printed verbatim). ``--json`` wraps the same
result in one JSON object; the exit-3 message stays verbatim in its
``message`` field.

Engine import note: the reference-pack loader and the state contracts are
imported through the real ``engine.capital_structure`` package. A host whose
package initializer refuses is the wrong interpreter; the error propagates.
"""
from __future__ import annotations

import argparse
from decimal import Decimal  # exact arithmetic only; never a binary approximation
import importlib
import json
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
DOSSIER_DIR = Path("research") / "capital_structure" / "e2e_20261013" / "reference"
DOSSIER_TICKERS = ("AIR", "CLNN", "QNCX", "WHK", "LPTH", "EDBL")
BUNDLE_RELPATH = Path("data") / "capital_structure" / "state_bundle.json"
RULE_PACK_RELPATH = Path("config") / "capital_structure_rule_applicability_pack.v1.json"
REFERENCE_PACK_RELPATH = Path("config") / "capital_structure_reference_pack.v1.json"
BUNDLE_ABSENT_MESSAGE = "a0: real bundles absent on this tree"
YAML_FENCE = re.compile(r"^```yaml\s*$", re.MULTILINE)
SECTIONS = (
    "## Identity",
    "## Source packet",
    "## Mandatory numerical path",
    "## Negatives",
    "## J5 cutoff",
    "## Findings",
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _engine_module(name: str):
    """Import ``engine.capital_structure.<name>`` through the real package.

    There is no fallback: a host whose package initializer refuses (for
    example the document-term authority seal) is the wrong interpreter for
    this checker, and the refusal propagates instead of loading a submodule
    under a stub parent.
    """
    return importlib.import_module(f"engine.capital_structure.{name}")


def parse_dossier(text: str, ticker: str) -> dict:
    """Parse one dossier: exactly one fenced YAML block, all sections present."""
    fences = YAML_FENCE.findall(text)
    if len(fences) != 1:
        raise ValueError(f"{ticker}: expected exactly one ```yaml block, found {len(fences)}")
    body = text.split("```yaml", 1)[1].split("```", 1)[0]
    missing = [section for section in SECTIONS if section not in text]
    if missing:
        raise ValueError(f"{ticker}: missing sections: {', '.join(missing)}")
    import yaml  # PyYAML; safe_load only

    spec = yaml.safe_load(body)
    if not isinstance(spec, dict):
        raise ValueError(f"{ticker}: the fenced YAML block must be a mapping")
    if spec.get("schema") != "capital_structure.reference_dossier.v1":
        raise ValueError(f"{ticker}: unexpected dossier schema {spec.get('schema')!r}")
    if spec.get("ticker") != ticker:
        raise ValueError(f"{ticker}: dossier ticker field disagrees with the file name")
    for field in ("issuer_id", "cik", "registry_name", "binding_status", "verdict_hint",
                  "j5_cutoff", "expectations", "negatives"):
        if field not in spec:
            raise ValueError(f"{ticker}: YAML block is missing {field!r}")
    return spec


def load_dossiers(root: Path) -> dict[str, dict]:
    dossiers: dict[str, dict] = {}
    for ticker in DOSSIER_TICKERS:
        path = root / DOSSIER_DIR / f"{ticker}.md"
        if not path.is_file():
            raise ValueError(f"dossier not found: {path}")
        dossiers[ticker] = parse_dossier(path.read_text(encoding="utf-8"), ticker)
    return dossiers


def _load_rule_pack_ids(root: Path) -> tuple[dict, dict]:
    """Active rule ids + pinned span digests from the rule-applicability pack.

    Read directly from the frozen config JSON (this checker re-derives no
    rule logic; it only checks membership).
    """
    path = root / RULE_PACK_RELPATH
    if not path.is_file():
        return {}, {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    rules = raw.get("rules") or []
    rule_ids = {str(rule.get("rule_id")) for rule in rules if rule.get("rule_id")}
    pinned_spans = dict((raw.get("reference_pack") or {}).get("pinned_spans") or {})
    return rule_ids, pinned_spans


def _pack_span_index(pack) -> dict[str, str]:
    """span label -> sha256 across every qualified reference-pack source."""
    index: dict[str, str] = {}
    for source in pack.sources:
        for span in source.spans:
            index[span.label] = span.sha256
    return index


def _operand_problem(operand, bundle_index: dict, pack_span_index: dict,
                     pinned_spans: dict) -> str | None:
    """Return the missing locator text, or None when the operand resolves."""
    if not isinstance(operand, dict) or not operand.get("name"):
        return "operand without a name"
    ref = operand.get("ref")
    pack_span = operand.get("pack_span")
    if bool(ref) == bool(pack_span):
        return f"{operand.get('name')}: exactly one of ref/pack_span is required"
    if ref is not None:
        entry = bundle_index.get(str(ref))
        if entry is None:
            return f"{operand.get('name')}: ref {ref} not in the served evidence index"
        claimed = operand.get("text_sha256")
        if claimed is not None:
            served = entry.get("text_sha256") or entry.get("ledger_text_sha256")
            if served is not None and str(served) != str(claimed):
                return (f"{operand.get('name')}: text_sha256 {claimed} does not match "
                        f"the served entry digest {served}")
        return None
    label = str(pack_span)
    digest = pack_span_index.get(label)
    if digest is None:
        return f"{operand.get('name')}: pack span {label!r} is not in the reference pack"
    claimed = operand.get("text_sha256")
    if claimed is not None and str(claimed) != digest:
        return (f"{operand.get('name')}: text_sha256 {claimed} does not match the "
                f"reference-pack span digest {digest}")
    if claimed is None and label in pinned_spans:
        # The rule-applicability pack pinned this span; the dossier must carry it.
        if str(pinned_spans[label]) not in (digest,):
            return (f"{operand.get('name')}: pinned span {label!r} digest disagrees "
                    f"with the reference pack")
    return None


def _rule_problem(expectation, rule_ids: set, example_ids: set) -> str | None:
    rule_id = expectation.get("rule_id")
    example_id = expectation.get("rule_example_id")
    if rule_id in rule_ids:
        return None
    if example_id in example_ids:
        return None
    return (f"rule {rule_id!r} is in neither the active rule-applicability pack "
            f"nor the reference pack's rule examples")


def evaluate_expectations(dossiers: dict[str, dict], pack, bundle: dict,
                          rule_ids: set | None = None,
                          pinned_spans: dict | None = None) -> list[dict]:
    """One result record per dossier expectation row (never raises on content)."""
    bundle_index = bundle.get("evidence_index") or {}
    if rule_ids is None or pinned_spans is None:
        loaded_ids, loaded_spans = _load_rule_pack_ids(REPO_ROOT)
        rule_ids = loaded_ids if rule_ids is None else rule_ids
        pinned_spans = loaded_spans if pinned_spans is None else pinned_spans
    example_ids = {example.example_id for example in pack.rule_examples}
    pack_span_index = _pack_span_index(pack)
    results: list[dict] = []
    for ticker, spec in sorted(dossiers.items()):
        for row in spec.get("expectations") or []:
            path_id = str(row.get("path_id") or "")
            expected = row.get("expected")
            if expected is None:
                results.append({
                    "ticker": ticker, "path_id": path_id, "kind": "gap",
                    "detail": str(row.get("gap") or "gap without a reason").strip(),
                })
                continue
            problem = _rule_problem(row, rule_ids, example_ids)
            if problem is None:
                for operand in row.get("operands") or ():
                    problem = _operand_problem(operand, bundle_index, pack_span_index,
                                               pinned_spans)
                    if problem is not None:
                        break
            if problem is None and not row.get("operands"):
                problem = "expectation carries no operands"
            if problem is None:
                try:
                    Decimal(str(expected))  # exact base-10 only; never a binary approximation
                except Exception:  # noqa: BLE001 — a malformed expected must not crash
                    problem = f"expected {expected!r} is not a Decimal string"
            results.append({
                "ticker": ticker, "path_id": path_id,
                "kind": "traceable" if problem is None else "untraceable",
                "detail": problem or "",
            })
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--pack", type=Path, default=None,
                        help="override the reference pack path")
    parser.add_argument("--json", action="store_true", help="machine summary")
    args = parser.parse_args(argv)
    root = args.root

    try:
        dossiers = load_dossiers(root)
    except ValueError as exc:
        print(str(exc))
        return 2

    bundle_path = root / BUNDLE_RELPATH
    if not bundle_path.is_file():
        if args.json:
            print(json.dumps({
                "status": "bundle_absent",
                "message": BUNDLE_ABSENT_MESSAGE,
                "dossiers_parsed": sorted(dossiers),
            }, sort_keys=True))
        else:
            print(BUNDLE_ABSENT_MESSAGE)
        return 3

    rq = _engine_module("reference_qualification")
    pack = rq.load_reference_pack(args.pack or (root / REFERENCE_PACK_RELPATH))
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    results = evaluate_expectations(dossiers, pack, bundle)
    traceable = [row for row in results if row["kind"] == "traceable"]
    untraceable = [row for row in results if row["kind"] == "untraceable"]
    gaps = [row for row in results if row["kind"] == "gap"]
    if args.json:
        print(json.dumps({
            "status": "ok",
            "traceable": len(traceable),
            "untraceable": len(untraceable),
            "gaps": len(gaps),
            "results": results,
        }, sort_keys=True))
    else:
        for row in results:
            if row["kind"] == "traceable":
                print(f"TRACEABLE {row['ticker']} {row['path_id']}")
            elif row["kind"] == "untraceable":
                print(f"UNTRACEABLE {row['ticker']} {row['path_id']} {row['detail']}")
            else:
                print(f"GAP {row['ticker']} {row['path_id']} {row['detail']}")
    return 1 if untraceable else 0


if __name__ == "__main__":
    raise SystemExit(main())
