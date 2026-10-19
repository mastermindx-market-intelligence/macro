#!/usr/bin/env python3
"""Offline FIF coverage-manifest writer.

Re-evaluates the ``metric:*`` cells of an existing coverage manifest from
cached SEC companyfacts JSON, using the repository's governed metric registry
at an explicit rule clock (``recorded_at``), and writes a deterministic
manifest.  Nothing is fetched: the cache is an input, and a missing cache file
leaves the issuer's cells exactly as the base manifest wrote them.

Field rules (ported from the census writer):

* R-PERIOD - a fact counts only for the slot's own period: its end equals the
  slot report date; an annual slot's duration fact spans 52 or 53 fiscal weeks
  (inclusive day count, nearest whole week); an interim slot keeps the
  1..400-day duration bound.  A slot-accession fact that fails only the period
  test leaves ``absent_period_mismatch``.
* Formula metrics are present only when every operand is present; a formula
  operand is evaluated through its own operands, and a dependency cycle is a
  missing operand (``absent_dependency``).  Operands are always strict.
* D2 (seat ruling 2026-10-19) - when the cached companyfacts carry no us-gaap
  fact from the slot's own accession, a direct metric's ``absent_no_alias_fact``
  is not evidence of absence: the cell is ``stale`` with reason
  ``companyfacts_missing_accession``.
* D1 (seat ruling 2026-10-19) - see ``COVER_DATE_POLICY``.  The dei cover-page
  share count filed in the slot's own accession, dated after the period end
  and on or before the filing date, is written as a present cell qualified
  ``cover_date_as_of`` with its own ``as_of`` date.  It is never relabelled as
  a period-end count, and no formula consumes it.
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import gzip
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.fundamental_forensics.metric_registry import load_core_metric_registry  # noqa: E402

WRITER_SCHEMA = "fif.coverage_writer/v1"

COVER_DATE_POLICY: dict[str, str] = {
    "policy_id": "fif.coverage_writer.cover_date_as_of",
    "version": "1.0.0",
    "metric_id": "common_shares_outstanding",
    "taxonomy": "dei",
    "concept": "EntityCommonStockSharesOutstanding",
    "qualifier": "cover_date_as_of",
    "reason": (
        "Form 10-K and Form 10-Q cover pages state the number of shares outstanding of each class "
        "of common stock as of the latest practicable date. This cell carries that cover-page count "
        "with its own as_of date; it is not a period-end count and is never relabelled as one."
    ),
}
COVER_DATE_FORMS = ("10-K", "10-Q")
QUALIFIER_KEYS = ("qualifier", "as_of", "qualifier_policy")

CORE_WINDOW_SLOTS = ("A1", "I1")
DEEP_WINDOW_SLOTS = ("A1", "A2", "I1", "I2")
PACKAGE_ROLES = ("primary", "schema", "presentation", "calculation", "definition", "label")

COMPANYFACTS_URL_PREFIX = "https://data.sec.gov/api/xbrl/companyfacts/CIK"


def qualifier_policy_ref() -> str:
    return f"{COVER_DATE_POLICY['policy_id']}/{COVER_DATE_POLICY['version']}"


def _bump(counters: dict[str, int] | None, key: str, amount: int = 1) -> None:
    if counters is not None:
        counters[key] = counters.get(key, 0) + amount


# --- Registry view ---------------------------------------------------------


def metric_specs_at(repo_root: str | Path, recorded_at: str) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Metric specs visible at ``recorded_at`` from the governed registry.

    Every mapping entry of a metric contributes its aliases (merged, never
    replaced), sorted by (priority, taxonomy, concept).  The rule clock is the
    registry's own ``governance_bundle_at``.
    """
    registry = load_core_metric_registry(repo_root)
    bundle = registry.governance_bundle_at(recorded_at)
    if bundle.catalog is None or bundle.mapping_pack is None:
        raise ValueError(f"metric catalog or mapping pack is not visible at {recorded_at}")
    specs: dict[str, dict[str, Any]] = {}
    rule_ids: set[str] = set()
    for contract in sorted(bundle.contracts, key=lambda item: item.metric_id):
        aliases: list[tuple[int, str, str]] = []
        for mapping in bundle.mappings_for(contract.metric_id):
            rule_ids.add(mapping.rule.rule_id)
            for alias in mapping.taxonomy_concept_aliases:
                aliases.append((int(alias.priority), alias.taxonomy, alias.concept))
        specs[contract.metric_id] = {
            "metric_id": contract.metric_id,
            "kind": contract.period_constraints.kind,
            "units": tuple(contract.units),
            "formula_dependencies": tuple(contract.declared_formula_dependencies),
            "aliases": sorted(aliases),
        }
    provenance = {
        "mapping_rule_ids": sorted(rule_ids),
        "catalog_version": registry.catalog_version,
        "mapping_pack_version": registry.mapping_pack_version,
    }
    return specs, provenance


# --- Field logic -------------------------------------------------------------


def slot_accessions(slot: Mapping[str, Any]) -> set[str]:
    """The slot's own accession plus its amendments."""
    out: set[str] = set()
    if slot.get("accession"):
        out.add(slot["accession"])
        for item in (slot.get("amendments") or "").split(","):
            if item:
                out.add(item)
    return out


def _unit_matches(catalog_units: Iterable[str], unit_name: str) -> bool:
    for unit in catalog_units:
        if unit == "USD" and unit_name == "USD":
            return True
        if unit == "USD/shares" and unit_name in ("USD/shares", "USDPerShare"):
            return True
        if unit == "shares" and unit_name in ("shares",):
            return True
    return False


def _slot_period_ok(kind: str, slot_period: tuple[str, str] | None, start: Any, end: Any) -> bool:
    if not slot_period:
        return False
    report_date, slot_kind = slot_period
    if not report_date or end != report_date:
        return False
    if kind == "instant":
        return True
    if str(slot_kind).startswith("A"):
        try:
            inclusive_days = (_dt.date.fromisoformat(end[:10]) - _dt.date.fromisoformat(start[:10])).days + 1
        except Exception:
            return False
        return (inclusive_days + 3) // 7 in (52, 53)
    return True


def check_metric_against_facts(
    spec: Mapping[str, Any],
    facts: Mapping[str, Any],
    accessions: set[str],
    slot_period: tuple[str, str] | None = None,
) -> tuple[bool, str, str, str, int | None]:
    """Strict alias pass: (present, reason_code, concept, unit, priority)."""
    aliases = spec.get("aliases") or []
    if not aliases:
        return False, "absent_no_alias_fact", "", "", None
    catalog_units = spec["units"]
    kind = spec["kind"]
    period_rejected = False
    for priority, taxonomy, concept in aliases:
        facts_for_concept = None
        if taxonomy in facts:
            facts_for_concept = facts.get(taxonomy, {}).get(concept)
        # Ported unchanged from the census writer: when the alias taxonomy
        # carries no such concept, the concept name is searched in every
        # taxonomy (a known gap, kept for equivalence).
        if not facts_for_concept:
            for _taxonomy, payload in facts.items():
                if isinstance(payload, dict):
                    candidate = payload.get(concept)
                    if candidate and isinstance(candidate, dict):
                        facts_for_concept = candidate
                        break
        if not facts_for_concept:
            continue
        units = facts_for_concept.get("units", {}) or {}
        for unit_name, fact_list in units.items():
            if not isinstance(fact_list, list):
                continue
            if not _unit_matches(catalog_units, unit_name):
                continue
            for fact in fact_list:
                if fact.get("accn", "") not in accessions:
                    continue
                start = fact.get("start")
                end = fact.get("end")
                if kind == "instant":
                    if start:
                        continue
                else:
                    if not start:
                        continue
                    try:
                        begin = _dt.datetime.fromisoformat(start.replace("Z", "+00:00"))
                        finish = _dt.datetime.fromisoformat(end.replace("Z", "+00:00"))
                        days = (finish - begin).days
                        if days < 1 or days > 400:
                            continue
                    except Exception:
                        continue
                if not _slot_period_ok(kind, slot_period, start, end):
                    period_rejected = True
                    continue
                return True, "present", concept, unit_name, priority
    if period_rejected:
        return False, "absent_period_mismatch", "", "", None
    if "ifrs-full" in facts and not any(t in facts for t in ("us-gaap", "gaap", "dei")):
        return False, "absent_ifrs_taxonomy", "", "", None
    return False, "absent_no_alias_fact", "", "", None


def companyfacts_missing_accession(facts: Mapping[str, Any], accession: str) -> bool:
    """D2: no us-gaap fact in ``facts`` carries the slot's own accession.

    Amendments are not consulted: an amendment's facts do not show that the
    original filing is in the cache.  An empty accession is never missing.
    """
    if not accession:
        return False
    for concept in (facts.get("us-gaap") or {}).values():
        for unit_facts in (concept.get("units") or {}).values():
            for fact in unit_facts:
                if fact.get("accn") == accession:
                    return False
    return True


def cover_date_as_of(
    spec: Mapping[str, Any],
    facts: Mapping[str, Any],
    slot: Mapping[str, Any],
    counters: dict[str, int] | None = None,
) -> str | None:
    """D1: the single qualifying cover-page instant, or None."""
    policy = COVER_DATE_POLICY
    if spec.get("metric_id") != policy["metric_id"]:
        return None
    if slot.get("slot_status") != "present":
        return None
    if not any(t == policy["taxonomy"] and c == policy["concept"] for _p, t, c in spec.get("aliases") or []):
        _bump(counters, "cover_fallback_alias_not_visible")
        return None
    if not str(slot.get("form") or "").startswith(COVER_DATE_FORMS):
        _bump(counters, "cover_fallback_form_not_covered")
        return None
    accession = slot.get("accession") or ""
    report_date = slot.get("report_date") or ""
    filing_date = slot.get("filing_date") or ""
    if not (accession and report_date and filing_date):
        return None
    concept = (facts.get(policy["taxonomy"]) or {}).get(policy["concept"]) or {}
    fact_list = (concept.get("units") or {}).get("shares") or []
    instants: dict[str, int] = {}
    for fact in fact_list:
        if not isinstance(fact, dict) or fact.get("start"):
            continue
        if fact.get("accn") != accession:
            continue
        end = fact.get("end") or ""
        if report_date < end <= filing_date:
            instants[end] = instants.get(end, 0) + 1
    if not instants:
        return None
    if len(instants) > 1:
        _bump(counters, "cover_window_ambiguous")
        return None
    ((as_of, count),) = instants.items()
    if count > 1:
        _bump(counters, "cover_multi_value")
    return as_of


def _formula_operands_present(
    spec: Mapping[str, Any],
    specs: Mapping[str, Mapping[str, Any]],
    facts: Mapping[str, Any],
    slot: Mapping[str, Any],
    visiting: frozenset[str],
    allow_qualified: bool,
) -> bool:
    accessions = slot_accessions(slot)
    slot_period = (slot.get("report_date", ""), slot.get("slot_id", ""))
    for dep in spec["formula_dependencies"]:
        dep_spec = specs.get(dep)
        if not dep_spec:
            return False
        if dep_spec["formula_dependencies"]:
            if dep in visiting:
                return False
            if not _formula_operands_present(dep_spec, specs, facts, slot, visiting | {dep}, allow_qualified):
                return False
            continue
        present, _reason, _concept, _unit, _priority = check_metric_against_facts(
            dep_spec, facts, accessions, slot_period=slot_period
        )
        if not present and allow_qualified:
            present = cover_date_as_of(dep_spec, facts, slot, None) is not None
        if not present:
            return False
    return True


def evaluate_cell(
    spec: Mapping[str, Any],
    specs: Mapping[str, Mapping[str, Any]],
    facts: Mapping[str, Any],
    slot: Mapping[str, Any],
    counters: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Status of one (slot, metric) cell: strict -> D1 fallback -> D2 relabel."""
    slot_status = slot.get("slot_status", "slot_absent")
    if slot_status in ("slot_absent", "fetch_failed"):
        return {"status": slot_status, "reason_code": slot_status}
    if slot_status and str(slot_status).startswith("not_applicable"):
        return {"status": slot_status, "reason_code": slot_status}

    metric_id = spec["metric_id"]
    if spec["formula_dependencies"]:
        if _formula_operands_present(spec, specs, facts, slot, frozenset((metric_id,)), False):
            return {"status": "present", "reason_code": "present"}
        if _formula_operands_present(spec, specs, facts, slot, frozenset((metric_id,)), True):
            _bump(counters, "formula_blocked_by_qualified_operand")
        return {"status": "absent", "reason_code": "absent_dependency"}

    present, reason, _concept, _unit, _priority = check_metric_against_facts(
        spec,
        facts,
        slot_accessions(slot),
        slot_period=(slot.get("report_date", ""), slot.get("slot_id", "")),
    )
    if present:
        return {"status": "present", "reason_code": "present"}
    as_of = cover_date_as_of(spec, facts, slot, counters)
    if as_of is not None:
        return {
            "status": "present",
            "reason_code": "present",
            "qualifier": COVER_DATE_POLICY["qualifier"],
            "as_of": as_of,
            "qualifier_policy": qualifier_policy_ref(),
        }
    if (
        reason == "absent_no_alias_fact"
        and slot_status == "present"
        and companyfacts_missing_accession(facts, slot.get("accession", ""))
    ):
        return {"status": "stale", "reason_code": "companyfacts_missing_accession"}
    return {"status": "absent", "reason_code": reason}


# --- Issuer rollups: the coverage prover's ruled contract --------------------


def _is_windowless_field(field_id: str) -> bool:
    """packet/journey/specialist cells carry no period window."""
    return field_id in ("packet", "journey") or field_id.startswith("specialist:")


def _is_deep_only_field(field_id: str) -> bool:
    """package/statement/specialist/packet/journey cells belong to the deep tier."""
    return (
        field_id.startswith("package:")
        or field_id.startswith("package.")
        or field_id.startswith("statement:")
        or _is_windowless_field(field_id)
    )


def _rollup_cells_for_issuer(cells, tier_assigned):
    """The issuer's cells the prover counts, after its orphan rules."""
    window = DEEP_WINDOW_SLOTS if tier_assigned == "deep" else CORE_WINDOW_SLOTS
    for period_id, field_id, status in cells:
        if not _is_windowless_field(field_id):
            if period_id == "*" or period_id not in window:
                continue
        if _is_deep_only_field(field_id) and tier_assigned != "deep":
            continue
        yield period_id, field_id, status


def _count_rollup_cells(cells, tier_assigned):
    """(present_cells, absent_cells, na_cells) under the prover's status map."""
    present = absent = na = 0
    for _period_id, _field_id, status in _rollup_cells_for_issuer(cells, tier_assigned):
        if status == "present":
            present += 1
        elif status in ("absent", "slot_absent"):
            absent += 1
        elif status == "not_applicable":
            na += 1
    return present, absent, na


def _window_pass(cells, tier_assigned, periods, metric_ids):
    """The prover's pass rule over one metric window (core or deep)."""
    window = DEEP_WINDOW_SLOTS if tier_assigned == "deep" else CORE_WINDOW_SLOTS
    status_by_key = {}
    for period_id, field_id, status in cells:
        if field_id.startswith("metric:") and period_id in periods and period_id in window:
            status_by_key[(period_id, field_id)] = status
    failed = False
    present = applicable = 0
    for period_id in periods:
        for metric_id in metric_ids:
            status = status_by_key.get((period_id, "metric:" + metric_id))
            if status == "present":
                present += 1
                applicable += 1
            elif status == "not_applicable":
                continue
            else:
                failed = True
                applicable += 1
    return (not failed) and applicable > 0 and present == applicable


def _deep_pass(cells, tier_assigned, metric_ids):
    """The prover's deep_pass rule; statements/specialist/packet/journey cells are
    not written by this census, so a deep pass is never reached from it."""
    if tier_assigned != "deep":
        return False
    if not _window_pass(cells, tier_assigned, DEEP_WINDOW_SLOTS, metric_ids):
        return False
    status_by_key = {}
    for period_id, field_id, status in cells:
        if field_id.startswith("package:") or field_id.startswith("package."):
            status_by_key[(period_id, field_id)] = status
    for period_id in DEEP_WINDOW_SLOTS:
        for role in PACKAGE_ROLES:
            if status_by_key.get((period_id, "package." + role)) != "present":
                return False
    return False


# --- Manifest rewrite ----------------------------------------------------------


def rewrite_manifest(
    base_manifest: Mapping[str, Any],
    slot_rows: Iterable[Mapping[str, Any]],
    facts_for_cik: Callable[[str], Mapping[str, Any] | None],
    specs: Mapping[str, Mapping[str, Any]],
    recorded_at: str,
    provenance: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Re-evaluate the metric cells of ``base_manifest``; return (manifest, counts)."""
    slots = {(str(row["cik"]), str(row["slot_id"])): dict(row) for row in slot_rows}
    counters: dict[str, int] = {}
    by_reason: dict[str, dict[str, int]] = {"all": {}, "core": {}}
    present_strict = {"all": 0, "core": 0}
    present_qualified = {"all": 0, "core": 0}
    unavailable: set[str] = set()
    loaded_cik: str | None = None
    loaded_facts: Mapping[str, Any] | None = None

    cells_out: list[dict[str, Any]] = []
    for cell in base_manifest.get("cells", []):
        new = dict(cell)
        field_id = str(cell.get("field_id", ""))
        if not field_id.startswith("metric:"):
            cells_out.append(new)
            continue
        cik = str(cell.get("cik", ""))
        spec = specs.get(field_id[len("metric:"):])
        if spec is None:
            _bump(counters, "metric_not_visible")
            cells_out.append(new)
            continue
        slot = slots.get((cik, str(cell.get("period_id", ""))))
        if slot is None:
            _bump(counters, "slot_row_missing")
            cells_out.append(new)
            continue
        if (slot.get("accession") or "") != (cell.get("accession") or ""):
            _bump(counters, "slot_accession_mismatch")
            cells_out.append(new)
            continue
        if cik != loaded_cik:
            loaded_cik, loaded_facts = cik, facts_for_cik(cik)
        if loaded_facts is None:
            unavailable.add(cik)
            cells_out.append(new)
            continue
        result = evaluate_cell(spec, specs, loaded_facts, slot, counters)
        for key in QUALIFIER_KEYS:
            new.pop(key, None)
        new.update(result)
        _bump(counters, "cells_rewritten")
        scopes = ("all", "core") if new.get("tier") == "core" else ("all",)
        key = f"{new['status']}/{new['reason_code']}"
        for scope in scopes:
            by_reason[scope][key] = by_reason[scope].get(key, 0) + 1
            if new["status"] == "present":
                if "qualifier" in new:
                    present_qualified[scope] += 1
                else:
                    present_strict[scope] += 1
        cells_out.append(new)

    triples_by_cik: dict[str, list[tuple[str, str, str]]] = {}
    for cell in cells_out:
        triples_by_cik.setdefault(str(cell.get("cik", "")), []).append(
            (str(cell.get("period_id", "")), str(cell.get("field_id", "")), str(cell.get("status", "")))
        )
    metric_ids = sorted(specs)
    issuers_out: list[dict[str, Any]] = []
    for issuer in base_manifest.get("issuers", []):
        new_issuer = dict(issuer)
        tier_assigned = issuer.get("tier_assigned")
        cells = triples_by_cik.get(str(issuer.get("cik", "")), [])
        present_cells, absent_cells, na_cells = _count_rollup_cells(cells, tier_assigned)
        new_issuer.update(
            {
                "present_cells": present_cells,
                "absent_cells": absent_cells,
                "na_cells": na_cells,
                "core_pass": _window_pass(cells, tier_assigned, CORE_WINDOW_SLOTS, metric_ids),
                "deep_pass": _deep_pass(cells, tier_assigned, metric_ids),
            }
        )
        issuers_out.append(new_issuer)

    manifest = dict(base_manifest)
    manifest["cells"] = cells_out
    manifest["issuers"] = issuers_out
    manifest["recorded_at"] = recorded_at
    manifest["writer"] = {
        "schema": WRITER_SCHEMA,
        "policy": dict(COVER_DATE_POLICY),
        "rules_recorded_at": recorded_at,
        "mapping_rule_ids": list(provenance.get("mapping_rule_ids", [])),
        "catalog_version": provenance.get("catalog_version", ""),
        "mapping_pack_version": provenance.get("mapping_pack_version", ""),
        "base_manifest_sha256": provenance.get("base_manifest_sha256", ""),
    }
    counters["facts_unavailable_issuers"] = len(unavailable)
    counts: dict[str, Any] = {
        "by_reason": by_reason,
        "present_strict": present_strict,
        "present_qualified": present_qualified,
    }
    for name in (
        "cells_rewritten",
        "metric_not_visible",
        "slot_row_missing",
        "slot_accession_mismatch",
        "facts_unavailable_issuers",
        "cover_fallback_alias_not_visible",
        "cover_fallback_form_not_covered",
        "cover_window_ambiguous",
        "cover_multi_value",
        "formula_blocked_by_qualified_operand",
    ):
        counts[name] = counters.get(name, 0)
    return manifest, counts


def dump_manifest(manifest: Mapping[str, Any]) -> bytes:
    return (json.dumps(manifest, sort_keys=True, indent=1) + "\n").encode("utf-8")


# --- CLI -------------------------------------------------------------------------


def companyfacts_cache_key(cik: str) -> str:
    """Cache file stem: sha256 of the public companyfacts URL for ``cik`` (never fetched)."""
    url = f"{COMPANYFACTS_URL_PREFIX}{int(cik):010d}.json"
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def cached_facts_loader(cache_dir: str | Path) -> Callable[[str], Mapping[str, Any] | None]:
    root = Path(cache_dir)

    def load(cik: str) -> Mapping[str, Any] | None:
        path = root / f"{companyfacts_cache_key(cik)}.gz"
        if not path.is_file():
            return None
        try:
            payload = json.loads(gzip.decompress(path.read_bytes()))
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        return payload.get("facts", {}) or {}

    return load


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    rewrite = sub.add_parser("rewrite", help="re-evaluate metric cells from cached companyfacts")
    rewrite.add_argument("--base-manifest", required=True)
    rewrite.add_argument("--slots", required=True)
    rewrite.add_argument("--facts-cache", required=True)
    rewrite.add_argument("--recorded-at", required=True)
    rewrite.add_argument("--out", required=True)
    rewrite.add_argument("--repo-root", default=str(ROOT))
    args = parser.parse_args(argv)

    base_bytes = Path(args.base_manifest).read_bytes()
    base_manifest = json.loads(base_bytes)
    with open(args.slots, newline="") as handle:
        slot_rows = list(csv.DictReader(handle))
    specs, provenance = metric_specs_at(args.repo_root, args.recorded_at)
    provenance = dict(provenance, base_manifest_sha256=hashlib.sha256(base_bytes).hexdigest())
    manifest, counts = rewrite_manifest(
        base_manifest, slot_rows, cached_facts_loader(args.facts_cache), specs, args.recorded_at, provenance
    )
    payload = dump_manifest(manifest)
    Path(args.out).write_bytes(payload)
    counts["out_sha256"] = hashlib.sha256(payload).hexdigest()
    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
