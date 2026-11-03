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
* Strict alias search (W-R2 M3) - an alias matches only facts in its own
  taxonomy.  When the alias concept is filed in the slot's accessions only
  under another taxonomy, the cell is ``absent_other_taxonomy_only``; when the
  metric has a us-gaap alias and the slot's accessions carry ifrs-full facts
  but no us-gaap fact, it is ``absent_ifrs_taxonomy``.
* Slot dates (W-R2 m6) - a present slot whose report or filing date is not an
  ISO calendar date is never evaluated: the cell is ``failed_extraction`` with
  reason ``invalid_slot_date``.
* D2 (seat ruling 2026-10-19; W-R2 M4) - when the cached companyfacts carry no
  fact from the slot's own accession in any taxonomy (dei included), a direct
  metric's ``absent_no_alias_fact`` is not evidence of absence: the cell is
  ``stale`` with reason ``companyfacts_missing_accession``.  Limitation: D2
  cannot tell a genuinely stale cache from an accession that companyfacts
  never carried; the writer reads no cache fetch time and never compares one
  with the filing date.
* D1 (seat ruling 2026-10-19) - see ``COVER_DATE_POLICY``.  The dei cover-page
  share count filed in the slot's own accession, dated after the period end
  and on or before the filing date, is written as a present cell qualified
  ``cover_date_as_of`` with its own ``as_of`` date.  It is never relabelled as
  a period-end count, and no formula consumes it.  The policy is visible only
  at a rule clock on or after its ``available_at`` (W-R2 m7), applies only to
  forms exactly ``10-K`` or ``10-Q``, and more than one distinct value at the
  selected date (a multi-class cover page) is the typed absence
  ``cover_date_multi_class``, never one present value and never a sum (W-R2 M2).
* NP (A36) - behind ``--np-linkbases DIR`` the census applies the governed
  not-presented rules the served query path applies, from linkbases captured
  for the slot's own accession (``fif.np_linkbases/v1``; the sha256 of each
  file's uncompressed bytes is verified).  A strict metric whose only verdict
  is ``absent_no_alias_fact`` may become ``not_applicable`` with
  ``na_basis: not_presented_item`` and the verdict's ``np_*`` evidence, and a
  governed formula follows the served not-presented operand policy
  (``total_debt``'s qualified sum; ``net_debt`` / ``cash_to_total_debt``
  inherit).  Every failure - missing or sha-mismatched linkbases, an amended
  slot, mixed durations, conflicting values, no visible rule at the clock -
  keeps the absent cell.  So do the two served-precondition gates (review
  2026-11-02): an alias fact of the metric carried by any accession outside
  the slot's own at the report date (``np_alias_fact_other_accession``), and,
  for a duration metric, a census-requested span (``duration_for_slot`` over
  the issuer's governed duration universe) that is not exactly the slot
  accession's own single span (``np_span_not_requested``).  Without the flag
  the writer's output is byte for byte the pre-NP writer's.

Issuer rollups (W-R2 M1): ``present_cells``, ``core_pass`` and ``deep_pass``
are any-basis and count qualified present cells; ``present_cells_strict``,
``core_pass_strict`` and ``deep_pass_strict`` count only present cells that
carry no qualifier and no derivation.  The deep tier (A36) additionally follows
the prover's component rule: ``deep_pass`` also requires every deep component
cell — per deep period each required package role and statement, plus the
wildcard-period specialist packs, packet and journey — to be present (a
``not_applicable`` specialist pack still passes), and ``deep_pass_strict``
additionally fails on any component cell the prover counts as labelled.
Both strict passes also mirror the prover's scope-label rule (A36 deep fix,
2026-11-02): a ``not_applicable`` metric cell inside the tier's metric window
whose ``na_basis`` is neither absent nor ``kernel`` fails that tier's strict
pass while every any-basis output is untouched.
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import gzip
import hashlib
import json
import sys
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.fundamental_forensics.metric_registry import load_core_metric_registry  # noqa: E402

# NP (A36): the census reuses the served path's own helpers and constants; it
# never re-types their strings.  ``_evidence_fields`` / ``split_kernel_reason``
# are the same objects ``coverage_manifest.map_metric_cell`` applies to a
# served NOT_APPLICABLE cell, so a key collision raises exactly as served.
# ``duration_for_slot`` (with the family constants it switches on) is the
# census's own span choice, imported and called, never re-typed here.
from engine.fundamental_forensics.coverage_manifest import (  # noqa: E402
    _FAMILY_ANNUAL,
    _FAMILY_INTERIM,
    NA_BASIS_KERNEL,
    _evidence_fields,
    duration_for_slot,
    split_kernel_reason,
)
from engine.fundamental_forensics.not_presented import (  # noqa: E402
    NA_BASIS_NOT_PRESENTED_ITEM,
    NOT_PRESENTED_REASON,
    NotPresentedError,
    NotPresentedEvidence,
    NotPresentedPack,
    evaluate_not_presented_package,
    load_not_presented_pack,
)
from engine.fundamental_forensics.query import (  # noqa: E402
    FORMULA_NOT_PRESENTED_PREFIX,
    FORMULA_NOT_PRESENTED_WITHHELD_PREFIX,
    FORMULA_QUALIFIED_WITHHELD_PREFIX,
    QUALIFIED_NOT_PRESENTED_EXPORT_PREFIX,
)

WRITER_SCHEMA = "fif.coverage_writer/v1"

COVER_DATE_POLICY: dict[str, str] = {
    "policy_id": "fif.coverage_writer.cover_date_as_of",
    "version": "1.0.0",
    "available_at": "2026-10-19T00:00:00Z",
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
COVER_DATE_FORMS = frozenset({"10-K", "10-Q"})
QUALIFIER_KEYS = ("qualifier", "as_of", "qualifier_policy")
# A present cell carrying a non-null value under either key is labelled, never strict.
LABEL_KEYS = ("qualifier", "derivation")
# Keys a re-evaluated cell drops before it takes its fresh result.
REEVALUATED_KEYS = (*QUALIFIER_KEYS, "derivation")
ROLLUP_BASIS: dict[str, str] = {
    "present_cells": "any_basis",
    "core_pass": "any_basis",
    "deep_pass": "any_basis",
    "present_cells_strict": "strict",
    "core_pass_strict": "strict",
    "deep_pass_strict": "strict",
}

CORE_WINDOW_SLOTS = ("A1", "I1")
DEEP_WINDOW_SLOTS = ("A1", "A2", "I1", "I2")
PACKAGE_ROLES = ("primary", "schema", "presentation", "calculation", "definition", "label")

# FIF A36 deep components: ``tiers.deep`` of the frozen thresholds config
# (config/fundamental_forensics/coverage/c2_thresholds_v1.json), restated as
# constants so the writer's import graph is unchanged; pinned field by field
# against the config by test_deep_pass_mirrors_prover_component_specs.
WILDCARD_PERIOD = "*"
LEGACY_PACKAGE_ALIAS_PREFIX = "package."
DEEP_PACKAGE_ROLES = ("primary", "schema", "presentation", "calculation", "definition", "label")
DEEP_STATEMENTS = ("income_statement", "balance_sheet", "cash_flow")
DEEP_SPECIALIST_PACKS = tuple(f"PK{pack:02d}" for pack in range(1, 13))
DEEP_REQUIRE_PACKET = True
DEEP_REQUIRE_JOURNEY = True
# The prover's present-label pairs (coverage_proof._PRESENT_LABELS): a deep
# component cell carrying a non-null value under any of these keys is labelled
# and keeps its issuer out of deep_pass_strict.
COMPONENT_LABEL_KEYS = ("qualifier", "qualifier_policy", "derivation", "derivation_policy")

COMPANYFACTS_URL_PREFIX = "https://data.sec.gov/api/xbrl/companyfacts/CIK"


def qualifier_policy_ref() -> str:
    return f"{COVER_DATE_POLICY['policy_id']}/{COVER_DATE_POLICY['version']}"


def _bump(counters: dict[str, int] | None, key: str, amount: int = 1) -> None:
    if counters is not None:
        counters[key] = counters.get(key, 0) + amount


def _utc_instant(value: str) -> _dt.datetime:
    """A timezone-aware instant; a naive timestamp raises ValueError."""
    parsed = _dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"rule clock must carry a timezone: {value!r}")
    return parsed


def cover_policy_visible(recorded_at: str | None) -> bool:
    """D1 is visible only at a rule clock on or after its ``available_at``.

    No rule clock is fail-closed: strict only.
    """
    if recorded_at is None:
        return False
    return _utc_instant(recorded_at) >= _utc_instant(COVER_DATE_POLICY["available_at"])


def _iso_date(value: Any) -> bool:
    """True only for a string that round-trips as an ISO calendar date (YYYY-MM-DD)."""
    if not isinstance(value, str):
        return False
    try:
        return _dt.date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


# --- Registry view ---------------------------------------------------------


def metric_specs_at(repo_root: str | Path, recorded_at: str) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Metric specs visible at ``recorded_at`` from the governed registry.

    Every mapping entry of a metric contributes its aliases (merged, never
    replaced), sorted by (priority, taxonomy, concept).  The rule clock is the
    registry's own ``governance_bundle_at``.

    A formula metric also carries its governed not-presented operand policy
    (``np_formula_policy``) exactly as the bundle exposes it at the clock; a
    formula without one (or whose policy clock has not passed) carries None,
    which the NP branch reads as the served default ``withhold``.
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
        policy = (
            contract.formula.not_presented_policy
            if contract.formula is not None
            else None
        )
        specs[contract.metric_id] = {
            "metric_id": contract.metric_id,
            "kind": contract.period_constraints.kind,
            "units": tuple(contract.units),
            "formula_dependencies": tuple(contract.declared_formula_dependencies),
            "aliases": sorted(aliases),
            "np_formula_policy": (
                None
                if policy is None
                else {
                    "mode": policy.mode,
                    "qualified_operand": policy.qualified_operand,
                    "eligible_operands": tuple(policy.eligible_operands),
                    "all_not_presented": policy.all_not_presented,
                }
            ),
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
        payload = facts.get(taxonomy)
        facts_for_concept = payload.get(concept) if isinstance(payload, dict) else None
        if not facts_for_concept or not isinstance(facts_for_concept, dict):
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
    for _priority, taxonomy, concept in aliases:
        if _payload_has_accession(facts.get(taxonomy), accessions, concept):
            continue
        if any(
            other != taxonomy and _payload_has_accession(payload, accessions, concept)
            for other, payload in facts.items()
        ):
            return False, "absent_other_taxonomy_only", "", "", None
    if (
        any(taxonomy == "us-gaap" for _priority, taxonomy, _concept in aliases)
        and _payload_has_accession(facts.get("ifrs-full"), accessions)
        and not _payload_has_accession(facts.get("us-gaap"), accessions)
    ):
        return False, "absent_ifrs_taxonomy", "", "", None
    return False, "absent_no_alias_fact", "", "", None


def _payload_has_accession(payload: Any, accessions: set[str], concept: str | None = None) -> bool:
    """True when a fact in one taxonomy's payload carries an accession in ``accessions``.

    ``payload`` maps concept -> {"units": {unit: [fact, ...]}}; with ``concept``
    only that concept is searched.  Malformed levels are skipped.
    """
    if not isinstance(payload, dict) or not accessions:
        return False
    concepts = [payload.get(concept)] if concept is not None else list(payload.values())
    for entry in concepts:
        if not isinstance(entry, dict):
            continue
        units = entry.get("units")
        if not isinstance(units, dict):
            continue
        for fact_list in units.values():
            if not isinstance(fact_list, list):
                continue
            for fact in fact_list:
                if isinstance(fact, dict) and fact.get("accn") in accessions:
                    return True
    return False


def companyfacts_missing_accession(facts: Mapping[str, Any], accession: str) -> bool:
    """D2: no fact in any taxonomy of ``facts`` (dei included) carries the slot's own accession.

    Amendments are not consulted: an amendment's facts do not show that the
    original filing is in the cache.  An empty accession is never missing.
    Limitation: D2 cannot tell a genuinely stale cache from an accession that
    companyfacts never carried; the writer reads no cache fetch time and never
    compares one with the filing date.
    """
    if not accession:
        return False
    return not any(_payload_has_accession(payload, {accession}) for payload in facts.values())


def cover_date_outcome(
    spec: Mapping[str, Any],
    facts: Mapping[str, Any],
    slot: Mapping[str, Any],
    counters: dict[str, int] | None = None,
    *,
    recorded_at: str | None = None,
) -> dict[str, Any] | None:
    """D1: the qualified present cell, the typed multi-class absence, or None."""
    policy = COVER_DATE_POLICY
    if spec.get("metric_id") != policy["metric_id"]:
        return None
    if slot.get("slot_status") != "present":
        return None
    if not cover_policy_visible(recorded_at):
        _bump(counters, "cover_fallback_policy_not_visible")
        return None
    if not any(t == policy["taxonomy"] and c == policy["concept"] for _p, t, c in spec.get("aliases") or []):
        _bump(counters, "cover_fallback_alias_not_visible")
        return None
    if str(slot.get("form") or "") not in COVER_DATE_FORMS:
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
    values: dict[str, set[str]] = {}
    for fact in fact_list:
        if not isinstance(fact, dict) or fact.get("start"):
            continue
        if fact.get("accn") != accession:
            continue
        end = fact.get("end") or ""
        if report_date < end <= filing_date:
            instants[end] = instants.get(end, 0) + 1
            values.setdefault(end, set()).add(json.dumps(fact.get("val"), sort_keys=True))
    if not instants:
        return None
    if len(instants) > 1:
        _bump(counters, "cover_window_ambiguous")
        return None
    ((as_of, count),) = instants.items()
    if count > 1:
        _bump(counters, "cover_multi_value")
    if len(values[as_of]) > 1:
        _bump(counters, "cover_date_multi_class")
        return {"status": "absent", "reason_code": "cover_date_multi_class"}
    return {
        "status": "present",
        "reason_code": "present",
        "qualifier": policy["qualifier"],
        "as_of": as_of,
        "qualifier_policy": qualifier_policy_ref(),
    }


# --- NP (A36): the not-presented branch behind --np-linkbases -----------------
#
# The served query path (engine/fundamental_forensics/query.py) anchors a
# not-presented verdict to one filing, rebuilds that filing's exact slot
# context, and evaluates the governed pack against the filing's own
# calculation and presentation linkbases.  The census mirrors that decision
# from captured linkbase bytes; nothing here invents a verdict the served path
# would not print, and every doubt keeps the absent cell.

NP_LINKBASES_SCHEMA = "fif.np_linkbases/v1"
NP_COUNTERS_KEY = "not_presented"


class NPLinkbases:
    """Lazy, sha-verified view over one captured linkbase directory.

    ``index.json`` maps each accession (with dashes) to its calculation and
    presentation linkbase: relative gz paths plus the SHA-256 of each file's
    UNCOMPRESSED bytes.  An accession whose bytes do not reproduce the
    recorded digest is treated as having no linkbases at all (fail closed,
    never a guessed verdict); a malformed index refuses the whole run.
    """

    _FAIL_COUNTERS = {
        "entry": "np_no_linkbase_entry",
        "unreadable": "np_linkbase_unreadable",
        "sha": "np_linkbase_sha_mismatch",
    }

    def __init__(self, root: Path, entries: Mapping[str, Mapping[str, Any]]) -> None:
        self._root = root
        self._entries = dict(entries)
        self._cache: dict[str, tuple[str, tuple[bytes, bytes] | None]] = {}

    def for_accession(
        self, accession: str, counters: dict[str, int]
    ) -> tuple[bytes, bytes] | None:
        """The (calculation, presentation) bytes for one accession, or None.

        None means the census treats the accession as having no linkbases; the
        matching counter names why.  Results are memoized per accession; a
        memoized failure re-bumps its counter so the counts stay per attempt.
        """
        cached = self._cache.get(accession)
        if cached is None:
            cached = self._load(accession)
            self._cache[accession] = cached
        status, payload = cached
        if status != "ok":
            _bump(counters, self._FAIL_COUNTERS[status])
            return None
        return payload

    def _load(self, accession: str) -> tuple[str, tuple[bytes, bytes] | None]:
        entry = self._entries.get(accession)
        if not isinstance(entry, Mapping) or entry.get("status") != "ok":
            return "entry", None
        pair: list[bytes] = []
        for role in ("cal", "pre"):
            rel = entry.get(role)
            expected = entry.get(f"{role}_sha256")
            if not isinstance(rel, str) or not isinstance(expected, str):
                return "entry", None
            try:
                raw = gzip.decompress((self._root / rel).read_bytes())
            except Exception:
                return "unreadable", None
            if hashlib.sha256(raw).hexdigest() != expected:
                return "sha", None
            pair.append(raw)
        return "ok", (pair[0], pair[1])


def load_np_linkbases(directory: str | Path) -> NPLinkbases:
    """Load and validate one ``fif.np_linkbases/v1`` index; refuse drift.

    A missing index, a schema other than ``NP_LINKBASES_SCHEMA``, entries that
    are not an object, or a linkbase path that is absolute, contains ``..``,
    or resolves outside the directory raises ``ValueError`` (the CLI turns it
    into a non-zero exit with the message).
    """
    root = Path(directory)
    index_path = root / "index.json"
    try:
        document = json.loads(index_path.read_bytes())
    except OSError as exc:
        raise ValueError(f"np-linkbases index is unreadable: {index_path}") from exc
    except ValueError as exc:
        raise ValueError(f"np-linkbases index is not valid JSON: {index_path}") from exc
    if not isinstance(document, dict) or document.get("schema") != NP_LINKBASES_SCHEMA:
        raise ValueError(
            f"np-linkbases index schema must equal {NP_LINKBASES_SCHEMA}: {index_path}"
        )
    entries = document.get("entries")
    if not isinstance(entries, dict):
        raise ValueError(f"np-linkbases index entries must be an object: {index_path}")
    resolved_root = root.resolve()
    for accession, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        for role in ("cal", "pre"):
            rel = entry.get(role)
            if not isinstance(rel, str):
                continue
            candidate = PurePosixPath(rel)
            if candidate.is_absolute() or ".." in candidate.parts:
                raise ValueError(
                    f"np-linkbases entry {accession} {role} path must be relative and "
                    f"stay inside the directory: {rel!r}"
                )
            if not (root / candidate).resolve().is_relative_to(resolved_root):
                raise ValueError(
                    f"np-linkbases entry {accession} {role} path resolves outside the "
                    f"directory: {rel!r}"
                )
    return NPLinkbases(root, entries)


@dataclass
class NPContext:
    """Everything the census needs to mirror the served not-presented branch."""

    pack: NotPresentedPack
    linkbases: NPLinkbases
    recorded_at: _dt.datetime  # the rewrite rule clock, as visible_rule takes it
    counters: dict[str, int] = field(default_factory=dict)
    # Every alias qname the governed registry carries, unfiltered by a rule
    # clock - the set ``governed_duration_universe`` counts its spans from.
    # The CLI fills it from the registry; the empty default requests no
    # duration span at all, so every duration-period NP fails closed.
    governed_qnames: frozenset[str] = field(default_factory=frozenset)


# Sentinel for "no census span is bound to this evaluation" (an instant metric,
# or an NPContext built without the registry's alias set).  A bound span of
# None is a different fact: the census requests no duration at all for the
# slot, so no duration fact can sit on the requested span.
_NP_SPAN_UNBOUND = object()


def _governed_alias_qnames(repo_root: str | Path) -> frozenset[str]:
    """Every alias qname the governed registry carries, unfiltered by a clock.

    ``governed_duration_universe`` (coverage_manifest.py) walks
    ``registry.contracts`` without a rule clock, so the census's duration
    universe counts every governed alias; the writer's reconstruction of that
    universe must not be narrower than the same set.
    """
    registry = load_core_metric_registry(repo_root)
    return frozenset(
        f"{alias.taxonomy}:{alias.concept}"
        for contract in registry.contracts
        for mapping in contract.mappings
        for alias in mapping.taxonomy_concept_aliases
    )


def _np_alias_fact_other_accession(
    spec: Mapping[str, Any],
    facts: Mapping[str, Any],
    slot: Mapping[str, Any],
) -> bool:
    """Defect 1 (review 2026-11-02, broadened): True when ANY accession -
    including the slot's own - carries a fact, in ANY unit, for one of the
    metric's alias concepts with ``end == report_date``.

    The served precondition (query.py:7159-7167) attempts not-presented only
    when no alias fact is visible in ANY unit from ANY accession at the
    period, so such a fact makes served print VALUE, stay missing, or print
    NOT_EVALUABLE (an unexpected unit) where the writer would have printed
    ``not_applicable``.  The check is deliberately broader than served - it
    ignores the unit, the accession, the span and the duration class - so it
    can only turn a would-be ``not_applicable`` into the original absent
    result, never the reverse.  A USD fact in the slot's own accession that
    satisfies the strict pass never reaches this check (``evaluate_cell``
    already returned present), so admitting own accessions here cannot
    suppress a present cell.
    """
    aliases = spec.get("aliases") or []
    report_date = slot.get("report_date") or ""
    if not aliases or not report_date:
        return False
    wanted = {(taxonomy, concept) for _priority, taxonomy, concept in aliases}
    for taxonomy, payload in facts.items():
        if not isinstance(payload, dict):
            continue
        for concept, entry in payload.items():
            if (str(taxonomy), str(concept)) not in wanted or not isinstance(entry, dict):
                continue
            units = entry.get("units")
            if not isinstance(units, dict):
                continue
            for fact_list in units.values():
                if not isinstance(fact_list, list):
                    continue
                for fact in fact_list:
                    if not isinstance(fact, dict):
                        continue
                    if fact.get("end") == report_date:
                        return True
    return False


def _np_duration_universe(
    facts: Mapping[str, Any],
    governed_qnames: frozenset[str],
) -> list[tuple[str, str]]:
    """The issuer's distinct governed duration spans, as the census builds them.

    Mirrors ``governed_duration_universe`` (coverage_manifest.py) over the
    writer's fact source, companyfacts: every fact of a governed concept with
    a duration context (a start and an end) contributes its ``(start, end)``,
    whatever accession or unit filed it.  A divergence from the census's own
    ledger universe can only change which span ``duration_for_slot`` requests,
    and the NP gate in ``_np_facts_in_context`` fails closed on any such
    change.  Residual (review 2026-11-02): the universe is only as complete
    as the writer's ``--facts-cache`` - a governed duration fact the
    production ledger has but that cache lacks can make the writer choose a
    different span than served, so the ``--facts-cache`` must be the same
    companyfacts vintage the census used.
    """
    keys: dict[tuple[str, str], None] = {}
    for taxonomy, payload in facts.items():
        if not isinstance(payload, dict):
            continue
        for concept, entry in payload.items():
            if f"{taxonomy}:{concept}" not in governed_qnames or not isinstance(entry, dict):
                continue
            units = entry.get("units")
            if not isinstance(units, dict):
                continue
            for fact_list in units.values():
                if not isinstance(fact_list, list):
                    continue
                for fact in fact_list:
                    if not isinstance(fact, dict):
                        continue
                    start, end = fact.get("start"), fact.get("end")
                    if start and end:
                        keys.setdefault((str(start), str(end)))
    return sorted(keys)


def _np_slot_family(slot: Mapping[str, Any]) -> str | None:
    """The census slot family of a period id (``A*`` annual, ``I*`` interim)."""
    slot_id = str(slot.get("slot_id") or "")
    if slot_id.startswith("A"):
        return _FAMILY_ANNUAL
    if slot_id.startswith("I"):
        return _FAMILY_INTERIM
    return None


def _np_requested_span(
    facts: Mapping[str, Any],
    slot: Mapping[str, Any],
    governed_qnames: frozenset[str],
) -> tuple[str, str] | None:
    """The census's own duration request for this slot, or None.

    The census build (coverage_manifest.py ``_served_metric_cells``) chooses
    the slot's duration period with ``duration_for_slot(universe,
    period_of_report, family)`` over ``governed_duration_universe``; the
    writer reconstructs that universe from companyfacts and calls the same
    imported chooser, so the span here is the span the served query path
    matches contexts against (query.py ``_context_matches_period``).  A slot
    of no known family requests nothing.
    """
    family = _np_slot_family(slot)
    if family is None:
        return None
    return duration_for_slot(
        _np_duration_universe(facts, governed_qnames),
        str(slot.get("report_date") or ""),
        family,
    )


def _np_facts_in_context(
    facts: Mapping[str, Any],
    slot: Mapping[str, Any],
    counters: dict[str, int],
    requested_span: Any = _NP_SPAN_UNBOUND,
) -> dict[str, Decimal] | None:
    """The exact slot-context fact map for one NP evaluation, or None.

    Mirrors ``BitemporalMetricQueryEngine._not_presented_slot``'s fact walk
    (query.py:5937-5959): facts of the anchor accession only, consolidated
    USD only, the period matched to the slot, ``Decimal(str(value))`` with a
    non-finite or unparsable value failing the whole slot, and two different
    values for one concept failing the whole slot.  companyfacts carries no
    dimensions, so every fact it holds is already the consolidated,
    non-dimensional fact the served path's ``_np_consolidated_usd`` filter
    would keep; companyfacts has no withdrawal or nil marking either.  The
    anchor here is the slot's own accession (amended slots never reach NP).

    ``requested_span`` (defect 2, review 2026-11-02) binds a duration-period
    evaluation to the census's own duration request, exactly as served's
    ``_context_matches_period`` (query.py:5814-5820) admits only the requested
    span: when bound, the walk still applies the slot-class duration filter
    and the mixed-span fail-closed, and then every duration fact in the map
    must sit on exactly that span - none may sit anywhere else, one must sit
    on it, and a requested span of None (no governed span ends at the report
    date) admits none.  Any other outcome counts ``np_span_not_requested`` and
    fails the slot.  Unbound (an instant metric) keeps the plain walk.
    """
    accession = slot.get("accession") or ""
    report_date = slot.get("report_date") or ""
    slot_id = str(slot.get("slot_id") or "")
    out: dict[str, Decimal] = {}
    duration_spans: set[tuple[str, str]] = set()
    for taxonomy, payload in facts.items():
        if not isinstance(payload, dict):
            continue
        for concept, entry in payload.items():
            if not isinstance(entry, dict):
                continue
            units = entry.get("units")
            if not isinstance(units, dict):
                continue
            fact_list = units.get("USD")
            if not isinstance(fact_list, list):
                continue
            for fact in fact_list:
                if not isinstance(fact, dict) or fact.get("accn") != accession:
                    continue
                start = fact.get("start")
                end = fact.get("end")
                if end != report_date:
                    continue
                if start:
                    # Duration facts: the slot's own class only.  An annual
                    # slot (A*) keeps the fiscal-year rule _slot_period_ok
                    # applies (52/53 inclusive-day weeks); an interim slot
                    # (I*) keeps one fiscal quarter, 80..100 inclusive days.
                    # Any other slot id admits no duration at all.
                    if slot_id.startswith("A"):
                        if not _slot_period_ok("duration", (report_date, slot_id), start, end):
                            continue
                    elif slot_id.startswith("I"):
                        try:
                            inclusive_days = (
                                _dt.date.fromisoformat(end[:10]) - _dt.date.fromisoformat(start[:10])
                            ).days + 1
                        except Exception:
                            continue
                        if not 80 <= inclusive_days <= 100:
                            continue
                    else:
                        continue
                    span = (str(start), str(end))
                    duration_spans.add(span)
                    if len(duration_spans) > 1:
                        _bump(counters, "np_mixed_duration")
                        return None
                try:
                    value = Decimal(str(fact.get("val")))
                except (InvalidOperation, ValueError, TypeError):
                    _bump(counters, "np_bad_value")
                    return None
                if not value.is_finite():
                    _bump(counters, "np_bad_value")
                    return None
                qname = f"{taxonomy}:{concept}"
                prior = out.get(qname)
                if prior is not None and prior != value:
                    _bump(counters, "np_conflicting_value")
                    return None
                out[qname] = value
    if requested_span is not _NP_SPAN_UNBOUND and duration_spans != {requested_span}:
        # Defect 2: served's slot context holds duration facts only on the
        # census's requested span.  An empty set (no slot-accession fact on
        # the span, or no governed span ending at the report date at all) and
        # any other single span (the census requested a competing filing's
        # span) both fail closed; a mixed set already failed above.
        _bump(counters, "np_span_not_requested")
        return None
    return out


def _np_cell_outcome(
    spec: Mapping[str, Any],
    facts: Mapping[str, Any],
    slot: Mapping[str, Any],
    np_context: NPContext,
) -> dict[str, Any] | None:
    """The ``not_applicable`` cell for one strict metric, or None (keep absent).

    Only called when ``evaluate_cell`` would return
    ``{"status": "absent", "reason_code": "absent_no_alias_fact"}``.  A verdict
    that is not not-presented keeps the absent result and counts its outcome;
    the served cell for a not-presented verdict is exactly what
    ``coverage_manifest.map_metric_cell`` emits for a served NOT_APPLICABLE
    cell whose reason is ``NOT_PRESENTED_REASON`` and whose provenance carries
    ``na_basis == not_presented_item`` plus the evidence.
    """
    metric_id = spec["metric_id"]
    if _np_alias_fact_other_accession(spec, facts, slot):
        # Defect 1: served attempts NP only when no alias fact is visible from
        # any accession at the period; one filed by another accession makes
        # the served cell a VALUE (or missing), never a not-presented N/A.
        _bump(np_context.counters, "np_alias_fact_other_accession")
        return None
    rule = np_context.pack.visible_rule(metric_id, recorded_at=np_context.recorded_at)
    if rule is None:
        _bump(np_context.counters, "np_outcome:np_no_rule")
        return None
    if slot.get("amendments"):
        # The served path anchors NP to one revision basis; an amended slot has
        # two, so the census never evaluates NP for it.
        _bump(np_context.counters, "np_skipped_amended_slot")
        return None
    linkbases = np_context.linkbases.for_accession(
        slot.get("accession") or "", np_context.counters
    )
    if linkbases is None:
        return None
    requested_span: Any = _NP_SPAN_UNBOUND
    if spec.get("kind") == "duration":
        # Defect 2: a duration-period evaluation is bound to the census's own
        # requested span before any fact is admitted to the context.
        requested_span = _np_requested_span(facts, slot, np_context.governed_qnames)
    fact_map = _np_facts_in_context(facts, slot, np_context.counters, requested_span)
    if fact_map is None:
        return None
    try:
        verdict = evaluate_not_presented_package(
            np_context.pack,
            metric_id,
            calculation=linkbases[0],
            presentation=linkbases[1],
            facts_in_context=fact_map,
            recorded_at=np_context.recorded_at,
            accession=slot.get("accession") or "",
        )
    except NotPresentedError:
        # The served path swallows a NotPresentedError the same way and stays
        # absent (query.py:5992-5993).
        return None
    outcome = (
        verdict.outcome if verdict.is_not_presented else (verdict.reason or verdict.outcome)
    )
    _bump(np_context.counters, f"np_outcome:{outcome}")
    if not verdict.is_not_presented:
        return None
    cell: dict[str, Any] = {"status": "not_applicable"}
    reason_code, kernel_reason = split_kernel_reason(NOT_PRESENTED_REASON)
    cell["reason_code"] = reason_code
    cell["kernel_reason"] = kernel_reason
    cell.update(
        _evidence_fields(NotPresentedEvidence.from_verdict(verdict), cell)
    )
    cell["na_basis"] = NA_BASIS_NOT_PRESENTED_ITEM
    return cell


# Operand classes for the formula NP policy: PRESENT is the writer's strict or
# labelled (NP-qualified) present, NP is a not-presented verdict (an item's own
# or a dependent formula's), and OTHER is everything else.  A D1 cover-date
# qualified operand is deliberately OTHER: the served path has no such VALUE
# in-period and D1 itself says no formula consumes it, so treating it as
# PRESENT could emit a cell the served path would not.
_NP_OPERAND_PRESENT = "present"
_NP_OPERAND_QUALIFIED = "qualified"
_NP_OPERAND_NP = "np"
_NP_OPERAND_OTHER = "other"


def _np_absent_cell(reason: str) -> dict[str, Any]:
    reason_code, kernel_reason = split_kernel_reason(reason)
    cell: dict[str, Any] = {"status": "absent", "reason_code": reason_code}
    if kernel_reason:
        cell["kernel_reason"] = kernel_reason
    return cell


def _np_classify_operand(
    dep_id: str,
    specs: Mapping[str, Mapping[str, Any]],
    facts: Mapping[str, Any],
    slot: Mapping[str, Any],
    recorded_at: str | None,
    np_context: NPContext,
) -> tuple[str, dict[str, Any] | None, tuple[str, ...]]:
    """(kind, cell, np_ids) for one formula dependency, served classes only."""
    dep_spec = specs.get(dep_id)
    if dep_spec is None:
        return _NP_OPERAND_OTHER, None, ()
    if dep_spec["formula_dependencies"]:
        outcome = _formula_np_outcome(dep_spec, specs, facts, slot, recorded_at, np_context)
        if outcome is not None:
            cell, np_ids = outcome
            if cell["status"] == "present":
                return _NP_OPERAND_QUALIFIED, None, np_ids
            if cell["status"] == "not_applicable":
                return _NP_OPERAND_NP, None, ()
            return _NP_OPERAND_OTHER, None, ()
        if _formula_operands_present(
            dep_spec, specs, facts, slot, frozenset((dep_id,)), False, recorded_at
        ):
            return _NP_OPERAND_PRESENT, None, ()
        return _NP_OPERAND_OTHER, None, ()
    present, reason, *_rest = check_metric_against_facts(
        dep_spec,
        facts,
        slot_accessions(slot),
        slot_period=(slot.get("report_date", ""), slot.get("slot_id", "")),
    )
    if present:
        return _NP_OPERAND_PRESENT, None, ()
    outcome = cover_date_outcome(dep_spec, facts, slot, None, recorded_at=recorded_at)
    if outcome is not None:
        # A D1 qualified present or the multi-class absence: never NP input.
        return _NP_OPERAND_OTHER, None, ()
    if (
        reason == "absent_no_alias_fact"
        and slot.get("slot_status") == "present"
        and companyfacts_missing_accession(facts, slot.get("accession", ""))
    ):
        return _NP_OPERAND_OTHER, None, ()  # stale: not the NP precondition
    if reason == "absent_no_alias_fact":
        np_cell = _np_cell_outcome(dep_spec, facts, slot, np_context)
        if np_cell is not None:
            return _NP_OPERAND_NP, None, ()
    return _NP_OPERAND_OTHER, None, ()


def _formula_np_outcome(
    spec: Mapping[str, Any],
    specs: Mapping[str, Mapping[str, Any]],
    facts: Mapping[str, Any],
    slot: Mapping[str, Any],
    recorded_at: str | None,
    np_context: NPContext,
) -> tuple[dict[str, Any], tuple[str, ...]] | None:
    """The served formula not-presented policy on the writer's operands.

    Mirrors ``_formula_policy_outcome`` (query.py:3462-3582) over the writer's
    operand outcomes.  Any OTHER operand keeps the existing formula result; a
    governed ``not_presented`` policy then decides exactly as served: withhold
    (or no policy) is the absent ``not_presented_dependency`` cell,
    ``not_applicable`` is the ``formula_not_presented`` N/A cell whose
    ``na_basis`` is the kernel basis ``map_metric_cell`` stamps on it, and a
    ``qualified_sum`` with presented operands is the VALUE cell
    ``map_metric_cell`` writes with the ``qualified_not_presented`` qualifier
    and the pack's ``pack_id/pack_version`` policy.  The served order of the
    operand ids is the dependency order for N/A and withheld reasons and the
    sorted order for the qualifier, exactly as the kernel prints them.

    Revision basis (served: one shared accession across presented operands and
    every NP evidence accession equal to it): the census skips NP on any
    amended slot, so inside this branch every NP verdict is bound to the
    slot's own accession and every presented operand was matched against
    ``slot_accessions(slot)``, which for an unamended slot contains that
    accession alone - one shared revision basis by construction.  An amended
    slot never reaches an NP verdict here, so there is no divergent case to
    fail closed on; the gate itself is the fail-closed.
    """
    deps = spec["formula_dependencies"]
    outcomes = [
        _np_classify_operand(dep, specs, facts, slot, recorded_at, np_context)
        for dep in deps
    ]
    if any(kind == _NP_OPERAND_OTHER for kind, _cell, _ids in outcomes):
        return None
    np_ops = [dep for dep, (kind, *_rest) in zip(deps, outcomes) if kind == _NP_OPERAND_NP]
    qualified_ops = [
        (dep, ids)
        for dep, (kind, _cell, ids) in zip(deps, outcomes)
        if kind == _NP_OPERAND_QUALIFIED
    ]
    if not np_ops and not qualified_ops:
        return None
    policy = spec.get("np_formula_policy") or None
    mode = policy["mode"] if policy else "withhold"
    if np_ops and policy is not None and mode == "qualified_sum":
        eligible = tuple(policy.get("eligible_operands") or ())
        if any(item not in eligible for item in np_ops):
            mode = "withhold"
        elif len(np_ops) == len(deps):
            mode = policy.get("all_not_presented") or "withhold"
    if np_ops and mode == "withhold":
        _bump(np_context.counters, "np_formula_outcome:absent")
        return _np_absent_cell(
            FORMULA_NOT_PRESENTED_WITHHELD_PREFIX + ", ".join(np_ops)
        ), ()
    if np_ops and mode == "not_applicable":
        reason = FORMULA_NOT_PRESENTED_PREFIX + ", ".join(np_ops)
        reason_code, kernel_reason = split_kernel_reason(reason)
        _bump(np_context.counters, "np_formula_outcome:not_applicable")
        return (
            {
                "status": "not_applicable",
                "reason_code": reason_code,
                "kernel_reason": kernel_reason,
                "na_basis": NA_BASIS_KERNEL,
            },
            (),
        )
    if qualified_ops and (policy is None or policy.get("qualified_operand") == "withhold"):
        _bump(np_context.counters, "np_formula_outcome:absent")
        return (
            _np_absent_cell(
                FORMULA_QUALIFIED_WITHHELD_PREFIX
                + ", ".join(dep for dep, _ids in qualified_ops)
            ),
            (),
        )
    qualifiers = set(np_ops)
    for _dep, ids in qualified_ops:
        qualifiers.update(ids)
    ordered = tuple(sorted(qualifiers))
    _bump(np_context.counters, "np_formula_outcome:present")
    return (
        {
            "status": "present",
            "reason_code": "present",
            "qualifier": QUALIFIED_NOT_PRESENTED_EXPORT_PREFIX + ", ".join(ordered),
            "qualifier_policy": f"{np_context.pack.pack_id}/{np_context.pack.pack_version}",
        },
        ordered,
    )


def _formula_operands_present(
    spec: Mapping[str, Any],
    specs: Mapping[str, Mapping[str, Any]],
    facts: Mapping[str, Any],
    slot: Mapping[str, Any],
    visiting: frozenset[str],
    allow_qualified: bool,
    recorded_at: str | None = None,
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
            if not _formula_operands_present(
                dep_spec, specs, facts, slot, visiting | {dep}, allow_qualified, recorded_at
            ):
                return False
            continue
        present, _reason, _concept, _unit, _priority = check_metric_against_facts(
            dep_spec, facts, accessions, slot_period=slot_period
        )
        if not present and allow_qualified:
            outcome = cover_date_outcome(dep_spec, facts, slot, None, recorded_at=recorded_at)
            present = outcome is not None and outcome["status"] == "present"
        if not present:
            return False
    return True


def evaluate_cell(
    spec: Mapping[str, Any],
    specs: Mapping[str, Mapping[str, Any]],
    facts: Mapping[str, Any],
    slot: Mapping[str, Any],
    counters: dict[str, int] | None = None,
    *,
    recorded_at: str | None = None,
    np_context: NPContext | None = None,
) -> dict[str, Any]:
    """Status of one (slot, metric) cell: strict -> D1 fallback -> D2 relabel -> NP."""
    slot_status = slot.get("slot_status", "slot_absent")
    if slot_status in ("slot_absent", "fetch_failed"):
        return {"status": slot_status, "reason_code": slot_status}
    if slot_status and str(slot_status).startswith("not_applicable"):
        return {"status": slot_status, "reason_code": slot_status}
    if not (_iso_date(slot.get("report_date")) and _iso_date(slot.get("filing_date"))):
        _bump(counters, "invalid_slot_date")
        return {"status": "failed_extraction", "reason_code": "invalid_slot_date"}

    metric_id = spec["metric_id"]
    if spec["formula_dependencies"]:
        if np_context is not None:
            outcome = _formula_np_outcome(
                spec, specs, facts, slot, recorded_at, np_context
            )
            if outcome is not None:
                return outcome[0]
        if _formula_operands_present(spec, specs, facts, slot, frozenset((metric_id,)), False, recorded_at):
            return {"status": "present", "reason_code": "present"}
        if _formula_operands_present(spec, specs, facts, slot, frozenset((metric_id,)), True, recorded_at):
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
    outcome = cover_date_outcome(spec, facts, slot, counters, recorded_at=recorded_at)
    if outcome is not None:
        return outcome
    if (
        reason == "absent_no_alias_fact"
        and slot_status == "present"
        and companyfacts_missing_accession(facts, slot.get("accession", ""))
    ):
        return {"status": "stale", "reason_code": "companyfacts_missing_accession"}
    if reason == "absent_no_alias_fact" and np_context is not None:
        # NP (A36) is attempted only on the exact absence the served path may
        # upgrade: not stale, not a period mismatch, not another taxonomy, not
        # a cover-date outcome, not a slot-status outcome.
        np_cell = _np_cell_outcome(spec, facts, slot, np_context)
        if np_cell is not None:
            return np_cell
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


def _is_labelled(cell: Mapping[str, Any]) -> bool:
    """True when the cell carries a non-null value under any ``LABEL_KEYS`` key."""
    return any(cell.get(key) is not None for key in LABEL_KEYS)


def _strict_status(cell: Mapping[str, Any]) -> str:
    """The cell's status on the strict basis: a present cell carrying a non-null
    qualifier or derivation becomes the internal token ``present_labelled``,
    which no rollup counts as present.  The token is never written."""
    status = str(cell.get("status", ""))
    if status == "present" and _is_labelled(cell):
        return "present_labelled"
    return status


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


def _deep_component_specs():
    """The prover's deep component list, in its order (coverage_proof.py): for
    each deep period every required package role then statement, then the
    wildcard-period specialist packs, packet and journey.  Each entry is
    (period_id, field_id, allows_not_applicable); only a specialist pack may be
    ``not_applicable`` and still pass."""
    specs: list[tuple[str, str, bool]] = []
    for period_id in DEEP_WINDOW_SLOTS:
        for role in DEEP_PACKAGE_ROLES:
            specs.append((period_id, f"package:{role}", False))
        for kind in DEEP_STATEMENTS:
            specs.append((period_id, f"statement:{kind}", False))
    for pack in DEEP_SPECIALIST_PACKS:
        specs.append((WILDCARD_PERIOD, f"specialist:{pack}", True))
    if DEEP_REQUIRE_PACKET:
        specs.append((WILDCARD_PERIOD, "packet", False))
    if DEEP_REQUIRE_JOURNEY:
        specs.append((WILDCARD_PERIOD, "journey", False))
    return specs


DEEP_COMPONENT_SPECS = tuple(_deep_component_specs())
DEEP_COMPONENT_KEYS = frozenset(
    (period_id, field_id) for period_id, field_id, _allows_na in DEEP_COMPONENT_SPECS
)


def _canonical_deep_component_field(field_id: str) -> str:
    """The prover's declared legacy alias (seat ruling K-V1A-R1): a
    ``package.<role>`` cell whose role is one of the deep package roles is
    indexed as ``package:<role>``; every other spelling is returned unchanged
    and then simply matches no component spec."""
    if field_id.startswith(LEGACY_PACKAGE_ALIAS_PREFIX):
        role = field_id[len(LEGACY_PACKAGE_ALIAS_PREFIX):]
        if role and role in DEEP_PACKAGE_ROLES:
            return "package:" + role
    return field_id


def _component_status_by_key(cells):
    """Status by canonical (period_id, field_id) over one issuer's cells, built
    in cell order the way the prover indexes a manifest: a later duplicate key
    wins (the prover refuses a duplicate outright; the writer only reads, so it
    mirrors the index's last-write order)."""
    status_by_key: dict[tuple[str, str], str] = {}
    for period_id, field_id, status in cells:
        status_by_key[(period_id, _canonical_deep_component_field(field_id))] = status
    return status_by_key


def _component_is_labelled(cell: Mapping[str, Any]) -> bool:
    """The prover's component-labelled rule (seat ruling BLOCKER-1): the cell
    carries a non-null value under any present-label key, or an ``na_basis``
    that is neither absent nor the kernel's own."""
    if any(cell.get(key) is not None for key in COMPONENT_LABEL_KEYS):
        return True
    na_basis = cell.get("na_basis")
    return na_basis is not None and na_basis != NA_BASIS_KERNEL


def _labelled_deep_component_keys(cells) -> frozenset[tuple[str, str]]:
    """Canonical keys of one issuer's deep component cells the prover counts as
    labelled, decided on the cell the index order selects (a later duplicate
    spelling wins)."""
    selected: dict[tuple[str, str], Mapping[str, Any]] = {}
    for cell in cells:
        key = (
            str(cell.get("period_id", "")),
            _canonical_deep_component_field(str(cell.get("field_id", ""))),
        )
        if key in DEEP_COMPONENT_KEYS:
            selected[key] = cell
    return frozenset(
        key for key, cell in selected.items() if _component_is_labelled(cell)
    )


def _scope_cell_is_labelled_na(cell: Mapping[str, Any]) -> bool:
    """The prover's scope-label rule for a window metric cell (seat ruling
    BLOCKER-1): a ``not_applicable`` cell whose ``na_basis`` is neither absent
    nor the kernel's own — ``metric_scope`` counts it ``na_not_presented`` or
    ``na_class``, and ``scope_unlabelled`` then fails the tier's strict
    verdict while the any-basis pass is untouched."""
    if str(cell.get("status", "")) != "not_applicable":
        return False
    na_basis = cell.get("na_basis")
    return na_basis is not None and na_basis != NA_BASIS_KERNEL


def _scope_labelled_na_metric_keys(
    cells, periods: tuple[str, ...]
) -> frozenset[tuple[str, str]]:
    """Keys of one issuer's scope-labelled ``not_applicable`` metric cells
    inside one tier's metric window — exactly the cells the prover's
    ``metric_scope`` counts for that tier (core or deep periods times the
    metric ids).  A windowed (period, field) key is unique in a manifest the
    prover accepts; a later duplicate wins the way the component mirror
    decides."""
    window = frozenset(periods)
    selected: dict[tuple[str, str], Mapping[str, Any]] = {}
    for cell in cells:
        field_id = str(cell.get("field_id", ""))
        period_id = str(cell.get("period_id", ""))
        if field_id.startswith("metric:") and period_id in window:
            selected[(period_id, field_id)] = cell
    return frozenset(
        key for key, cell in selected.items() if _scope_cell_is_labelled_na(cell)
    )


def _deep_pass(cells, tier_assigned, metric_ids, labelled_components=None):
    """The prover's deep_pass rule (coverage_proof.py): a deep-tier issuer whose
    deep metric window passes and whose every deep component cell — per deep
    period each required package role and statement, then the wildcard-period
    specialist packs, packet and journey — is present; a ``not_applicable``
    specialist pack still passes, and a missing cell or any other status fails.
    A ``package.<role>`` cell is indexed as ``package:<role>`` exactly when the
    role is one of the deep package roles.  ``labelled_components`` (the strict
    basis) additionally fails the pass on every component cell the prover
    counts as labelled."""
    if tier_assigned != "deep":
        return False
    if not _window_pass(cells, tier_assigned, DEEP_WINDOW_SLOTS, metric_ids):
        return False
    status_by_key = _component_status_by_key(cells)
    for period_id, field_id, allows_not_applicable in DEEP_COMPONENT_SPECS:
        key = (period_id, field_id)
        if labelled_components is not None and key in labelled_components:
            return False
        status = status_by_key.get(key)
        if status == "present":
            continue
        if allows_not_applicable and status == "not_applicable":
            continue
        return False
    return True


# --- Manifest rewrite ----------------------------------------------------------


def rewrite_manifest(
    base_manifest: Mapping[str, Any],
    slot_rows: Iterable[Mapping[str, Any]],
    facts_for_cik: Callable[[str], Mapping[str, Any] | None],
    specs: Mapping[str, Mapping[str, Any]],
    recorded_at: str,
    provenance: Mapping[str, Any],
    np_context: NPContext | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Re-evaluate the metric cells of ``base_manifest``; return (manifest, counts).

    ``np_context`` (the ``--np-linkbases`` branch) is None on the plain path,
    whose output is byte for byte the pre-NP writer's.
    """
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
        result = evaluate_cell(
            spec, specs, loaded_facts, slot, counters, recorded_at=recorded_at,
            np_context=np_context,
        )
        for key in REEVALUATED_KEYS:
            new.pop(key, None)
        new.update(result)
        _bump(counters, "cells_rewritten")
        scopes = ("all", "core") if new.get("tier") == "core" else ("all",)
        key = f"{new['status']}/{new['reason_code']}"
        for scope in scopes:
            by_reason[scope][key] = by_reason[scope].get(key, 0) + 1
            if new["status"] == "present":
                if _is_labelled(new):
                    present_qualified[scope] += 1
                else:
                    present_strict[scope] += 1
        cells_out.append(new)

    triples_by_cik: dict[str, list[tuple[str, str, str]]] = {}
    strict_triples_by_cik: dict[str, list[tuple[str, str, str]]] = {}
    component_cells_by_cik: dict[str, list[Mapping[str, Any]]] = {}
    metric_cells_by_cik: dict[str, list[Mapping[str, Any]]] = {}
    for cell in cells_out:
        cik_key = str(cell.get("cik", ""))
        period_field = (str(cell.get("period_id", "")), str(cell.get("field_id", "")))
        triples_by_cik.setdefault(cik_key, []).append((*period_field, str(cell.get("status", ""))))
        strict_triples_by_cik.setdefault(cik_key, []).append((*period_field, _strict_status(cell)))
        if (period_field[0], _canonical_deep_component_field(period_field[1])) in DEEP_COMPONENT_KEYS:
            component_cells_by_cik.setdefault(cik_key, []).append(cell)
        if period_field[1].startswith("metric:"):
            metric_cells_by_cik.setdefault(cik_key, []).append(cell)
    labelled_components_by_cik = {
        cik_key: _labelled_deep_component_keys(issuer_cells)
        for cik_key, issuer_cells in component_cells_by_cik.items()
    }
    # The prover's scope-label rule per issuer and tier: a scope-labelled N/A
    # metric cell inside the tier's metric window fails that tier's strict
    # rollup (the core set for core_pass_strict, the deep set for
    # deep_pass_strict) without touching any-basis outputs.
    scope_labelled_by_cik = {
        cik_key: (
            _scope_labelled_na_metric_keys(issuer_cells, CORE_WINDOW_SLOTS),
            _scope_labelled_na_metric_keys(issuer_cells, DEEP_WINDOW_SLOTS),
        )
        for cik_key, issuer_cells in metric_cells_by_cik.items()
    }
    metric_ids = sorted(specs)
    issuers_out: list[dict[str, Any]] = []
    rollups = {
        "any_basis": {"core_pass": 0, "deep_pass": 0, "present_cells": 0},
        "strict": {"core_pass_strict": 0, "deep_pass_strict": 0, "present_cells_strict": 0},
    }
    for issuer in base_manifest.get("issuers", []):
        new_issuer = dict(issuer)
        tier_assigned = issuer.get("tier_assigned")
        cik_key = str(issuer.get("cik", ""))
        cells = triples_by_cik.get(cik_key, [])
        strict_cells = strict_triples_by_cik.get(cik_key, [])
        labelled_components = labelled_components_by_cik.get(cik_key, frozenset())
        core_scope_labelled, deep_scope_labelled = scope_labelled_by_cik.get(
            cik_key, (frozenset(), frozenset())
        )
        present_cells, absent_cells, na_cells = _count_rollup_cells(cells, tier_assigned)
        new_issuer.update(
            {
                "present_cells": present_cells,
                "absent_cells": absent_cells,
                "na_cells": na_cells,
                "core_pass": _window_pass(cells, tier_assigned, CORE_WINDOW_SLOTS, metric_ids),
                "deep_pass": _deep_pass(cells, tier_assigned, metric_ids),
                "present_cells_strict": _count_rollup_cells(strict_cells, tier_assigned)[0],
                "core_pass_strict": (
                    _window_pass(strict_cells, tier_assigned, CORE_WINDOW_SLOTS, metric_ids)
                    and not core_scope_labelled
                ),
                "deep_pass_strict": (
                    _deep_pass(
                        strict_cells, tier_assigned, metric_ids, labelled_components
                    )
                    and not deep_scope_labelled
                ),
            }
        )
        rollups["any_basis"]["core_pass"] += int(new_issuer["core_pass"])
        rollups["any_basis"]["deep_pass"] += int(new_issuer["deep_pass"])
        rollups["any_basis"]["present_cells"] += present_cells
        rollups["strict"]["core_pass_strict"] += int(new_issuer["core_pass_strict"])
        rollups["strict"]["deep_pass_strict"] += int(new_issuer["deep_pass_strict"])
        rollups["strict"]["present_cells_strict"] += new_issuer["present_cells_strict"]
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
        "rollup_basis": dict(ROLLUP_BASIS),
    }
    counters["facts_unavailable_issuers"] = len(unavailable)
    counts: dict[str, Any] = {
        "by_reason": by_reason,
        "present_strict": present_strict,
        "present_qualified": present_qualified,
        "issuer_rollups": rollups,
    }
    for name in (
        "cells_rewritten",
        "metric_not_visible",
        "slot_row_missing",
        "slot_accession_mismatch",
        "facts_unavailable_issuers",
        "invalid_slot_date",
        "cover_fallback_policy_not_visible",
        "cover_fallback_alias_not_visible",
        "cover_fallback_form_not_covered",
        "cover_window_ambiguous",
        "cover_multi_value",
        "cover_date_multi_class",
        "formula_blocked_by_qualified_operand",
    ):
        counts[name] = counters.get(name, 0)
    if np_context is not None:
        # NP counters ride under one new key and only when the flag is given;
        # every existing counter key keeps its name and meaning.
        counts[NP_COUNTERS_KEY] = dict(np_context.counters)
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
    rewrite.add_argument(
        "--np-linkbases",
        default=None,
        metavar="DIR",
        help=(
            "captured filing linkbases (fif.np_linkbases/v1) that enable the "
            "not-presented branch; without it the output is the plain census"
        ),
    )
    args = parser.parse_args(argv)

    np_context: NPContext | None = None
    if args.np_linkbases:
        try:
            np_context = NPContext(
                pack=load_not_presented_pack(),
                linkbases=load_np_linkbases(args.np_linkbases),
                recorded_at=_utc_instant(args.recorded_at),
                governed_qnames=_governed_alias_qnames(args.repo_root),
            )
        except ValueError as exc:
            print(f"--np-linkbases: {exc}", file=sys.stderr)
            return 2

    base_bytes = Path(args.base_manifest).read_bytes()
    base_manifest = json.loads(base_bytes)
    with open(args.slots, newline="") as handle:
        slot_rows = list(csv.DictReader(handle))
    specs, provenance = metric_specs_at(args.repo_root, args.recorded_at)
    provenance = dict(provenance, base_manifest_sha256=hashlib.sha256(base_bytes).hexdigest())
    manifest, counts = rewrite_manifest(
        base_manifest, slot_rows, cached_facts_loader(args.facts_cache), specs, args.recorded_at,
        provenance, np_context,
    )
    payload = dump_manifest(manifest)
    Path(args.out).write_bytes(payload)
    counts["out_sha256"] = hashlib.sha256(payload).hexdigest()
    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
