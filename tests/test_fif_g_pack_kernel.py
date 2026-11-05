"""G-pack kernel data gate: the incumbent kernel over staged admitted packages.

Every pack under ``tests/fixtures/fundamental_forensics/g_pack/*/`` is run
through the incumbent production query path — D1 admission of the staged
package bytes, strict parse, iXBRL ledger conversion, then
``BitemporalMetricQueryEngine.query_matrix`` over the core registry — entirely
in-process, with no network, no store, and no credential. Issuer identity,
admitted accessions, expected cells and known defects come from the pack data
(``pack_manifest.json`` + ``gold_cells.jsonl``); nothing about any issuer is
typed here.

Comparison contract (kernel cells vs gold cells, keyed by
``view / source_accession / metric_id / period_key``):

* value rows compare ``value_exact`` as Decimals under the R-G1 contract, and
  for the ``latest_known_as_of`` view the selected vintage's accession must
  equal the gold row's ``source_accession``;
* typed absences compare their code under the kernel <-> catalog vocabulary
  table below (both vocabularies are defined by the repo, never by this file);
* a metric the registry does not govern produces no kernel cell; its gold row
  is equivalent to that only when it is the typed ``unsupported_metric``
  absence the packet builder itself emits for such metrics
  (engine/fundamental_forensics/financial_intelligence_packet.py:893); any
  other gold row for an ungoverned metric is a failed comparison.

Each ``pack_manifest.json`` ``defects[]`` entry — ``{id, row_keys,
comparison}`` with ``comparison`` one of ``value`` / ``code`` — turns exactly
the comparisons it names into an expected failure: a named comparison that
still fails is reported as the defect (strict expected-failure semantics), an
entry that no longer reproduces fails the suite, and every unnamed comparison
must match. Row-presence mismatches (a row on one side only) are treated as a
failed comparison of the kind the entry names for that row. Each entry's
``record.gold`` must still equal the current gold cell (value, code, source
accession), so a gold edit on a defect row cannot hide behind the defect.

Byte-level work needs the staged SEC bytes, so the gate skips unless
``FIF_GSRC_STAGE_ROOT`` names the stage root.
"""
from __future__ import annotations

import json
import os
import re
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = REPO_ROOT / "tests" / "fixtures" / "fundamental_forensics" / "g_pack"
G_SRC_ROOT = REPO_ROOT / "tests" / "fixtures" / "fundamental_forensics" / "g_src"

VIEW_A = "as_filed"
VIEW_B = "latest_known_as_of"

# Kernel reason prefix -> catalog absence code. Kernel side: CellState and the
# reason strings the query path emits (engine/fundamental_forensics/query.py:
# CellState :210-223; missing_standard_fact :5887/:5899/:5940/:5993;
# outside_period_constraint :2346; missing_dependency :3253/:6676;
# incompatible_dependencies :6657; disallowed_dimension :2841; division_by_zero
# :3285; not_applicable_for_issuer_class :2822). Gold side: the per-metric
# catalog ``no_result.codes`` (config/fundamental_forensics/metrics/v1/
# metric_catalog.yaml:61-63 direct, :69-71 derived) plus ``NOT_APPLICABLE`` for
# the issuer-class basis (CellState.NOT_APPLICABLE query.py:223).
KERNEL_CODE_MAP = {
    "missing_standard_fact": "missing_standard_fact",
    "outside_period_constraint": "outside_period_constraint",
    "missing_dependency": "missing_dependency",
    "incompatible_dependencies": "incompatible_dependencies",
    "disallowed_dimension": "disallowed_dimension",
    "division_by_zero": "division_by_zero",
    "not_applicable_for_issuer_class": "NOT_APPLICABLE",
    # Runtime refusal (query.py:5981) for raw facts with no minted lineage. The
    # mint-time cause differs per cell, so each defect records it in
    # kernel_observation.typed_cause; this code stays general.
    "unlinked source vintages require an explicit typed revision lineage": "unlinked_source_vintages",
}

VALUE_CATEGORIES = frozenset(
    {"value_mismatch", "value_vs_absence", "absence_vs_value"}
)
CODE_CATEGORIES = frozenset({"code_mismatch"})
PRESENCE_CATEGORIES = frozenset(
    {"gold_row_without_kernel_row", "kernel_row_without_gold_row"}
)


def _stage_root() -> Path | None:
    value = os.environ.get("FIF_GSRC_STAGE_ROOT")
    return Path(value).expanduser() if value else None


def _pack_dirs() -> list[Path]:
    if not PACK_ROOT.is_dir():
        return []
    return sorted(
        p for p in PACK_ROOT.iterdir()
        if p.is_dir() and (p / "pack_manifest.json").is_file()
    )


def _load_pack(pack_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = json.loads(
        (pack_dir / "pack_manifest.json").read_text(encoding="utf-8")
    )
    gold_rows = [
        json.loads(line)
        for line in (pack_dir / "gold_cells.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return manifest, gold_rows


def _resolve_sic(cik10: str) -> str | None:
    from engine.fundamental_forensics.issuer_sic import resolve_issuer_sic

    return resolve_issuer_sic(cik10, repo_root=REPO_ROOT)


def _convert_package(cik10: str, accession: str, stage: Path):
    """The step-2 recipe for one staged admitted package (no source edits)."""
    from collectors.sec_filing_parser import parse_sec_filing_document
    from engine.fundamental_forensics.admitted_filing_package import (
        admit_retained_filing_package,
    )
    from engine.fundamental_forensics.ixbrl_raw_ledger import convert_parsed_filing

    manifest = json.loads(
        (G_SRC_ROOT / cik10 / accession / "package_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    package_dir = stage / cik10 / accession
    members = {
        item["name"]: (package_dir / "members" / item["name"]).read_bytes()
        for item in manifest["members"]
        if item.get("state") == "stored"
    }
    admitted = admit_retained_filing_package(
        index_bytes=(package_dir / "index.json").read_bytes(),
        manifest=manifest,
        members=members,
        witness_bytes=(package_dir / "sec_submissions_witness.json").read_bytes(),
        capture_recorded_at=manifest["fixture_recorded_at"],
        capture_basis="reconstruction",
    )
    primary = admitted.manifest["primary_document"]
    parsed = parse_sec_filing_document(
        admitted.members[primary], document_name=primary
    )
    occurrences, metadata, _receipt = convert_parsed_filing(
        parsed=parsed, package=admitted
    )
    return occurrences, metadata, admitted


def _period_universe(occurrences: Sequence[Any], governed: frozenset[str]):
    from engine.fundamental_forensics.query import PeriodRequest

    seen: dict[tuple[str, str, str], PeriodRequest] = {}
    for occ in occurrences:
        if occ.concept_qname not in governed:
            continue
        ctx = occ.context
        if ctx.instant is not None:
            key = ("instant", "", ctx.instant.isoformat())
            request = PeriodRequest.instant(ctx.instant)
        else:
            key = (
                "duration",
                ctx.start.isoformat() if ctx.start else "",
                ctx.end.isoformat(),
            )
            request = PeriodRequest.duration(ctx.start, ctx.end)
        seen.setdefault(key, request)
    return [seen[key] for key in sorted(seen)]


def _governed_concepts(registry, clock: str) -> frozenset[str]:
    """Aliases from the clock-scoped governance view the kernel itself applies.

    The kernel reads governance through
    ``MetricRegistry.governance_bundle_at(recorded_at)`` — a mapping is
    visible only when ``mapping.rule.available_at <= cutoff``
    (engine/fundamental_forensics/metric_registry.py:493-530) — so the period
    grid here is derived from that same view: an alias whose rule clock is
    after the run clock cannot contribute a period the frozen gold never had.
    The bundle exposes the visible contracts as ``contracts`` with only their
    visible mappings attached under ``contract.mappings``.
    """
    governed = set()
    for contract in registry.governance_bundle_at(clock).contracts:
        for mapping in contract.mappings:
            for alias in mapping.taxonomy_concept_aliases:
                governed.add(f"{alias.taxonomy}:{alias.concept}")
    return frozenset(governed)


def _run_clock(
    cik10: str, gold_rows: Sequence[Mapping[str, Any]], admitted: Sequence[str]
) -> str:
    """A cutoff after every acceptance, governance clock and staged capture
    clock, all read from data (the recorded cutoff gates the retained packages'
    fixture_recorded_at clocks too)."""
    from engine.fundamental_forensics.lineage_evidence import (
        CONFIRMATION_CHAIN_RULE_AVAILABLE_AT,
        CONFIRMATION_RULE_AVAILABLE_AT,
    )

    registry = _registry()
    stamps = [str(row["knowledge_time"]) for row in gold_rows if row.get("knowledge_time")]
    stamps.extend(
        contract.available_at.isoformat() for contract in registry.contracts
    )
    # The lineage mint's rule clocks are governance clocks too: the cutoff must
    # sit at or above both floors for the receipts to be mintable and visible.
    stamps.extend(
        (
            CONFIRMATION_RULE_AVAILABLE_AT.isoformat(),
            CONFIRMATION_CHAIN_RULE_AVAILABLE_AT.isoformat(),
        )
    )
    for accession in admitted:
        manifest = json.loads(
            (G_SRC_ROOT / cik10 / accession / "package_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        stamps.append(str(manifest["fixture_recorded_at"]))
    return max(stamps)


_REGISTRY_CACHE: Any = None


def _registry():
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is None:
        from engine.fundamental_forensics.financial_intelligence_packet import (
            load_core_registry,
        )

        _REGISTRY_CACHE = load_core_registry(REPO_ROOT)
    return _REGISTRY_CACHE


_KERNEL_CACHE: dict[tuple[str, str], tuple[Any, Any, Any]] = {}
_ROWS_CACHE: dict[tuple[str, tuple[str, ...], str], list[dict[str, Any]]] = {}


def _kernel_rows(cik10: str, admitted: Sequence[str], stage: Path, clock: str) -> list[dict[str, Any]]:
    cached = _ROWS_CACHE.get((cik10, tuple(admitted), clock))
    if cached is not None:
        return cached

    from engine.fundamental_forensics.production_lineage import (
        mint_production_lineage_evidence,
    )
    from engine.fundamental_forensics.query import (
        BitemporalMetricQueryEngine,
        QueryEntity,
        QueryPolicy,
    )
    from engine.fundamental_forensics.raw_ledger import RawFactLedger, parse_utc

    registry = _registry()
    governed = _governed_concepts(registry, clock)
    entity = QueryEntity(
        ticker=_pack_ticker(cik10),
        entity_id=cik10,
        issuer_sic=_resolve_sic(cik10),
    )
    metrics = tuple(sorted(contract.metric_id for contract in registry.contracts))

    packages: dict[str, tuple[Any, Any, list[Any]]] = {}
    admitted_packages: list[Any] = []
    for accession in admitted:
        converted = _KERNEL_CACHE.get((cik10, accession))
        if converted is None:
            converted = _convert_package(cik10, accession, stage)
            _KERNEL_CACHE[(cik10, accession)] = converted
        occurrences, metadata, package = converted
        admitted_packages.append(package)
        packages[accession] = (
            occurrences,
            metadata,
            _period_universe(occurrences, governed),
        )

    rows: list[dict[str, Any]] = []

    def _cells(occurrences, metadata, periods, selection, lineage_evidence=()):
        engine = BitemporalMetricQueryEngine(
            RawFactLedger(occurrences),
            registry,
            entities=(entity,),
            filing_metadata=metadata,
            lineage_evidence=lineage_evidence,
        )
        policy = QueryPolicy(
            source_snapshot_at=clock, recorded_at=clock, selection=selection
        )
        matrix = engine.query_matrix(
            tickers=(entity,), metrics=metrics, periods=tuple(periods), policy=policy
        )
        return matrix.cells

    for accession in admitted:
        occurrences, metadata, periods = packages[accession]
        cells = _cells(occurrences, {accession: metadata}, periods, "latest_known_as_of")
        rows.extend(_cell_rows(VIEW_A, cells, accession))

    union: list[Any] = []
    seen: set[tuple[str, str, str]] = set()
    all_occurrences: list[Any] = []
    all_metadata: dict[str, Any] = {}
    for accession in admitted:
        occurrences, metadata, periods = packages[accession]
        all_occurrences.extend(occurrences)
        for occ in occurrences:
            all_metadata[occ.occurrence_id] = metadata
        for period in periods:
            key = _period_key(period)
            if key not in seen:
                seen.add(key)
                union.append(period)
    # The union view runs the way production serves it: receipts minted by the
    # one lawful mint (R-S2P-1) over the admitted ledger, handed to the engine
    # as lineage_evidence.  A LineageEvidenceError propagates; there is never a
    # fallback to an empty bundle.  The per-accession views above stay exactly
    # as they are: one accession, no receipts.
    ledger = RawFactLedger(all_occurrences)
    receipts = mint_production_lineage_evidence(
        ledger,
        admitted_packages,
        system_available_at=parse_utc(clock, field_name="run_clock"),
    )
    cells = _cells(
        all_occurrences, all_metadata, union, "latest_known_as_of", receipts
    )
    rows.extend(_cell_rows(VIEW_B, cells, None))
    _ROWS_CACHE[(cik10, tuple(admitted), clock)] = rows
    return rows


_TICKER_CACHE: dict[str, str] = {}


def _pack_ticker(cik10: str) -> str:
    """A display ticker for the query entity, from the coverage contract."""
    cached = _TICKER_CACHE.get(cik10)
    if cached is not None:
        return cached
    coverage_dir = REPO_ROOT / "config" / "fundamental_forensics" / "coverage"
    ticker = None
    for path in sorted(coverage_dir.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        for row in document.get("issuers", ()):  # type: ignore[union-attr]
            if str(row.get("cik")) == cik10:
                ticker = str(row.get("ticker"))
                break
        if ticker:
            break
    if not ticker:
        raise AssertionError(f"no coverage-contract ticker for {cik10}")
    _TICKER_CACHE[cik10] = ticker
    return ticker


def _period_key(period) -> tuple[str, ...]:
    """Gold-shape period key: (kind, end) for instants, (kind, start, end)."""
    normalized = period.normalized
    kind = normalized.kind.value if hasattr(normalized.kind, "value") else str(normalized.kind)
    if kind == "instant":
        return (kind, normalized.end.isoformat())
    return (kind, normalized.start.isoformat() if normalized.start else "", normalized.end.isoformat())


def _cell_rows(view: str, cells, accession: str | None) -> list[dict[str, Any]]:
    rows = []
    for cell in cells:
        provenance = cell.provenance
        reason = cell.reason or ""
        code = None
        if cell.status.value != "value":
            for prefix, mapped in KERNEL_CODE_MAP.items():
                if reason == prefix or reason.startswith(prefix + ":"):
                    code = mapped
                    break
            else:
                code = "UNMAPPED_KERNEL_REASON:" + reason[:160]
        rows.append(
            {
                "view": view,
                "source_accession": accession,
                "provenance_accession": provenance.accession,
                "metric_id": cell.metric_id,
                "period_key": list(_period_key(cell.period)),
                "state": cell.status.value,
                "value_exact": None if cell.value is None else str(cell.value),
                "kernel_code": code,
            }
        )
    return rows


def _gold_key(row: Mapping[str, Any]) -> tuple[str, str, str, Any]:
    period = row["period_key"]
    if row["view"] == VIEW_B:
        return (VIEW_B, "", row["metric_id"], tuple(period))
    return (row["view"], row.get("source_accession") or "", row["metric_id"], tuple(period))


def _kernel_key(row: Mapping[str, Any]) -> tuple[str, str, str, Any]:
    if row["view"] == VIEW_B:
        return (VIEW_B, "", row["metric_id"], tuple(row["period_key"]))
    return (row["view"], row["source_accession"] or "", row["metric_id"], tuple(row["period_key"]))


def _compare_group(
    kernel_rows: Sequence[Mapping[str, Any]],
    gold_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    kernel_by_key = {_kernel_key(row): row for row in kernel_rows}
    gold_by_key = {_gold_key(row): row for row in gold_rows}
    results: list[dict[str, Any]] = []
    for key in sorted(set(kernel_by_key) | set(gold_by_key), key=repr):
        kernel_row = kernel_by_key.get(key)
        gold_row = gold_by_key.get(key)
        if kernel_row is None:
            results.append(
                {"key": key, "category": "gold_row_without_kernel_row", "gold": gold_row}
            )
            continue
        if gold_row is None:
            results.append(
                {"key": key, "category": "kernel_row_without_gold_row", "kernel": kernel_row}
            )
            continue
        gold_value = gold_row.get("value_exact")
        if kernel_row["value_exact"] is not None and gold_value is not None:
            same = Decimal(kernel_row["value_exact"]) == Decimal(gold_value)
            # r2 View B formula rows carry no single source_accession (the
            # draft records dep_source_accessions instead), so the vintage
            # accession is compared only where gold states one.
            accession_ok = (
                gold_row["view"] == VIEW_A
                or gold_row.get("source_accession") is None
                or (kernel_row.get("provenance_accession") or "")
                == (gold_row.get("source_accession") or "")
            )
            if gold_row["view"] == VIEW_B and not accession_ok:
                results.append(
                    {"key": key, "category": "value_mismatch", "gold": gold_row,
                     "kernel": kernel_row, "detail": "view B vintage accession differs"}
                )
            elif same:
                results.append({"key": key, "category": "match"})
            else:
                results.append(
                    {"key": key, "category": "value_mismatch", "gold": gold_row,
                     "kernel": kernel_row}
                )
        elif kernel_row["value_exact"] is None and gold_value is None:
            if kernel_row["kernel_code"] == gold_row.get("code"):
                results.append({"key": key, "category": "match"})
            else:
                results.append(
                    {"key": key, "category": "code_mismatch", "gold": gold_row,
                     "kernel": kernel_row}
                )
        elif kernel_row["value_exact"] is not None:
            results.append(
                {"key": key, "category": "absence_vs_value", "gold": gold_row,
                 "kernel": kernel_row}
            )
        else:
            results.append(
                {"key": key, "category": "value_vs_absence", "gold": gold_row,
                 "kernel": kernel_row}
            )
    return [r for r in results if r["category"] != "match"]


def _defect_kind(category: str) -> str | None:
    if category in VALUE_CATEGORIES:
        return "value"
    if category in CODE_CATEGORIES:
        return "code"
    if category in PRESENCE_CATEGORIES:
        return None  # either kind covers a row-presence failure
    return "unknown"


def _group_params() -> list[pytest.ParameterSet]:
    params = []
    for pack_dir in _pack_dirs():
        manifest, _gold = _load_pack(pack_dir)
        cik10 = str(manifest["cik10"])
        for accession in manifest["admitted_accessions"]:
            params.append(
                pytest.param(
                    pack_dir.name, cik10, VIEW_A, str(accession),
                    id=f"{pack_dir.name}-as_filed-{accession}",
                )
            )
        params.append(
            pytest.param(
                pack_dir.name, cik10, VIEW_B, "",
                id=f"{pack_dir.name}-latest_known_as_of-union",
            )
        )
    return params


@pytest.mark.data_gate
@pytest.mark.parametrize(
    "pack_name,cik10,view,accession", _group_params()
)
def test_kernel_cells_match_gold_cells(pack_name, cik10, view, accession) -> None:
    stage = _stage_root()
    if stage is None:
        pytest.skip("FIF_GSRC_STAGE_ROOT is not set; staged bytes are not present")
    pack_dir = PACK_ROOT / pack_name
    manifest, gold_rows = _load_pack(pack_dir)
    admitted = [str(item) for item in manifest["admitted_accessions"]]

    kernel_rows = _kernel_rows(cik10, admitted, stage, _run_clock(cik10, gold_rows, admitted))
    group_kernel = [
        row for row in kernel_rows
        if row["view"] == view and (view == VIEW_B or row["source_accession"] == accession)
    ]
    group_gold = [
        row for row in gold_rows
        if row["view"] == view
        and (view == VIEW_B or (row.get("source_accession") or "") == accession)
    ]

    defects = [
        entry for entry in manifest.get("defects", ())
        if _defect_in_group(entry, view, accession)
    ]
    governed_metrics = frozenset(
        contract.metric_id for contract in _registry().contracts
    )
    mismatches = [
        mismatch for mismatch in _compare_group(group_kernel, group_gold)
        if not _ungoverned_typed_absence(mismatch, governed_metrics)
    ]

    unexpected = []
    fired: set[str] = set()
    for mismatch in mismatches:
        kind = _defect_kind(mismatch["category"])
        entry = _defect_covering(defects, mismatch["key"], kind)
        if entry is None:
            unexpected.append(mismatch)
        else:
            fired.add(str(entry["id"]))
    # strict semantics: every defect that claims a comparison in this group
    # must have fired (an entry whose rows all pass, or that names no real
    # row, can never fire and fails here).
    stale = sorted(
        {str(entry["id"]) for entry in defects} - fired
    )
    assert not unexpected, (
        f"{pack_name} {view} {accession or 'union'}: {len(unexpected)} "
        "comparisons differ from gold outside the pack's defects: "
        + json.dumps(unexpected[:20], default=str)
    )
    assert not stale, (
        f"{pack_name} {view} {accession or 'union'}: defects no longer "
        f"reproducing (strict): {stale}"
    )
    if fired:
        pytest.xfail(
            "pack defects: " + ", ".join(sorted(fired))
        )


def _ungoverned_typed_absence(
    mismatch: Mapping[str, Any], governed_metrics: frozenset[str]
) -> bool:
    """Gold-only row for an ungoverned metric, typed as unsupported_metric."""
    if mismatch["category"] != "gold_row_without_kernel_row":
        return False
    gold = mismatch["gold"]
    return (
        gold["metric_id"] not in governed_metrics
        and gold.get("value_exact") is None
        and gold.get("code") == "unsupported_metric"
    )


def test_ungoverned_metric_rule_is_narrow() -> None:
    """Only a typed unsupported_metric absence of an ungoverned metric passes."""
    governed = frozenset({"governed_metric"})

    def gold_only(metric_id, value, code):
        return {
            "category": "gold_row_without_kernel_row",
            "gold": {"metric_id": metric_id, "value_exact": value, "code": code},
        }

    assert _ungoverned_typed_absence(gold_only("other_metric", None, "unsupported_metric"), governed)
    assert not _ungoverned_typed_absence(gold_only("other_metric", "1", None), governed)
    assert not _ungoverned_typed_absence(gold_only("other_metric", None, "missing_standard_fact"), governed)
    assert not _ungoverned_typed_absence(gold_only("governed_metric", None, "unsupported_metric"), governed)
    assert not _ungoverned_typed_absence(
        {"category": "kernel_row_without_gold_row", "kernel": {}}, governed
    )


def test_governed_concepts_scope_to_the_run_clock() -> None:
    """An alias whose rule clock is after the run clock adds no concept.

    The kernel applies governance through ``governance_bundle_at``; this pins
    the harness to the same clock-scoped view — a mapping visible only after
    the clock must not contribute its alias (and so no period) to the grid.
    The amended registry re-dates one contract's mappings to a single rule
    past the clock (same governed aliases, new immutable rule), so both
    bundles stay inside the governed vocabularies.
    """
    from dataclasses import replace
    from datetime import datetime

    from engine.fundamental_forensics.metric_registry import (
        ImmutableRule,
        MappingRule,
    )

    registry = _registry()
    mapped = [c for c in registry.contracts if c.mappings]
    target, other = mapped[0], mapped[1]
    real = target.mappings[0]
    future = "2031-01-01T00:00:00+00:00"
    amended = replace(
        registry,
        contracts=tuple(
            replace(
                target,
                mappings=(
                    MappingRule(
                        metric_id=target.metric_id,
                        rule=ImmutableRule(
                            rule_id="a33-future-alias-rule/v1",
                            version="1.0.0",
                            available_at=datetime.fromisoformat(future),
                            confidence=real.rule.confidence,
                        ),
                        taxonomy_concept_aliases=real.taxonomy_concept_aliases,
                    ),
                ),
            )
            if current is target
            else current
            for current in registry.contracts
        ),
    )
    first_alias = real.taxonomy_concept_aliases[0]
    target_key = f"{first_alias.taxonomy}:{first_alias.concept}"
    other_alias = other.mappings[0].taxonomy_concept_aliases[0]
    other_key = f"{other_alias.taxonomy}:{other_alias.concept}"
    before = max(
        m.rule.available_at
        for contract in registry.contracts
        for m in contract.mappings
    ).isoformat()
    # The view is live at ``before`` (an untouched contract's alias is
    # governed there) but the re-dated contract's alias is not; it becomes
    # governed at/after its own rule clock.
    assert other_key in _governed_concepts(amended, before)
    assert target_key not in _governed_concepts(amended, before)
    assert target_key in _governed_concepts(amended, future)


def _defect_in_group(entry: Mapping[str, Any], view: str, accession: str) -> bool:
    for row_key in entry.get("row_keys", ()):
        if str(row_key.get("view")) != view:
            continue
        if view == VIEW_A and str(row_key.get("source_accession")) != accession:
            continue
        return True
    return False


def _defect_key(row_key: Mapping[str, Any]) -> tuple[str, str, str, Any]:
    period = list(row_key.get("period_key") or [])
    view = str(row_key.get("view"))
    if view == VIEW_B:
        return (VIEW_B, "", str(row_key.get("metric_id")), tuple(period))
    return (view, str(row_key.get("source_accession") or ""), str(row_key.get("metric_id")), tuple(period))


def _defect_covering(
    defects: Sequence[Mapping[str, Any]], key: tuple, kind: str | None
) -> Mapping[str, Any] | None:
    for entry in defects:
        comparison = str(entry.get("comparison"))
        if kind is not None and comparison != kind:
            continue
        if any(_defect_key(row_key) == key for row_key in entry.get("row_keys", ())):
            return entry
    return None


def test_pack_defects_name_real_rows() -> None:
    """Every defects[] row_key is structurally resolvable to one group."""
    packs = _pack_dirs()
    if not packs:
        pytest.skip("no g_pack fixtures committed yet")
    for pack_dir in packs:
        manifest, _gold_rows = _load_pack(pack_dir)
        admitted = {str(item) for item in manifest["admitted_accessions"]}
        for entry in manifest.get("defects", ()):
            assert str(entry.get("comparison")) in {"value", "code"}, entry
            assert entry.get("row_keys"), entry
            for row_key in entry.get("row_keys", ()):
                view = str(row_key.get("view"))
                assert view in {VIEW_A, VIEW_B}, row_key
                assert row_key.get("metric_id"), row_key
                period = list(row_key.get("period_key") or [])
                assert period and period[0] in {"instant", "duration"}, row_key
                assert len(period) == (2 if period[0] == "instant" else 3), row_key
                if view == VIEW_A:
                    assert str(row_key.get("source_accession")) in admitted, row_key


def _defect_gold_drift(
    entry: Mapping[str, Any], gold_by_key: Mapping[tuple, Mapping[str, Any]]
) -> list[str]:
    """Where a defect's recorded gold side no longer equals the gold cell.

    A defect turns a failed comparison into an expected failure, so a gold edit
    on a defect row would otherwise pass unseen; binding ``record.gold`` (value,
    code, source accession) to the current cell makes such an edit fail here.
    A row key with no gold cell is lawful only for a recorded all-null side.
    """
    record = entry.get("record")
    recorded = record.get("gold") if isinstance(record, Mapping) else None
    name = str(entry.get("id"))
    if not isinstance(recorded, Mapping):
        return [f"{name}: no record.gold"]
    problems = []
    for row_key in entry.get("row_keys", ()):
        gold = gold_by_key.get(_defect_key(row_key))
        if gold is None:
            if recorded.get("value_exact") is not None or recorded.get("code") is not None:
                problems.append(f"{name}: record.gold is set but no gold cell has its key")
            continue
        want, have = recorded.get("value_exact"), gold.get("value_exact")
        if (want is None) != (have is None) or (
            want is not None and Decimal(str(want)) != Decimal(str(have))
        ):
            problems.append(f"{name}: record.gold.value_exact={want!r}, gold cell {have!r}")
        if recorded.get("code") != gold.get("code"):
            problems.append(
                f"{name}: record.gold.code={recorded.get('code')!r}, gold cell {gold.get('code')!r}"
            )
        if recorded.get("source_accession") != gold.get("source_accession"):
            problems.append(f"{name}: record.gold.source_accession differs from the gold cell")
    return problems


def test_pack_defect_records_match_gold_cells() -> None:
    """Every defect's recorded gold side is the pack's current gold cell."""
    packs = _pack_dirs()
    if not packs:
        pytest.skip("no g_pack fixtures committed yet")
    for pack_dir in packs:
        manifest, gold_rows = _load_pack(pack_dir)
        gold_by_key = {_gold_key(row): row for row in gold_rows}
        problems = [
            problem
            for entry in manifest.get("defects", ())
            for problem in _defect_gold_drift(entry, gold_by_key)
        ]
        assert not problems, f"{pack_dir.name}: " + "; ".join(problems[:20])


def test_defect_gold_drift_negative() -> None:
    """A changed value, code or accession on a defect row is reported."""
    period = ["instant", "2024-01-31"]
    key = {"view": VIEW_A, "source_accession": "acc-1", "metric_id": "m", "period_key": period}
    cell = {**key, "value_exact": "100", "code": None}
    gold_by_key = {_gold_key(cell): cell}

    def entry(gold: Any) -> dict[str, Any]:
        return {"id": "D-1", "row_keys": [key], "comparison": "value", "record": {"gold": gold}}

    same = {"value_exact": "100.0", "code": None, "source_accession": "acc-1"}
    assert _defect_gold_drift(entry(same), gold_by_key) == []
    assert _defect_gold_drift(entry({**same, "value_exact": "101"}), gold_by_key)
    assert _defect_gold_drift(entry({**same, "value_exact": None}), gold_by_key)
    assert _defect_gold_drift(entry({**same, "code": "missing_standard_fact"}), gold_by_key)
    assert _defect_gold_drift(entry({**same, "source_accession": "acc-2"}), gold_by_key)
    assert _defect_gold_drift({"id": "D-2", "row_keys": [key]}, gold_by_key)
    assert _defect_gold_drift(entry(same), {})
    absent = {"value_exact": None, "code": None, "source_accession": None}
    assert _defect_gold_drift(entry(absent), {}) == []
    # a null accession is not an empty one
    view_b = {"view": VIEW_B, "source_accession": None, "metric_id": "m", "period_key": period}
    cell_b = {**view_b, "value_exact": "100", "code": None}
    by_key_b = {_gold_key(cell_b): cell_b}
    entry_b = {"id": "D-3", "row_keys": [view_b], "comparison": "value"}
    same_b = {"value_exact": "100", "code": None, "source_accession": None}
    assert _defect_gold_drift({**entry_b, "record": {"gold": same_b}}, by_key_b) == []
    assert _defect_gold_drift({**entry_b, "record": {"gold": {**same_b, "source_accession": ""}}}, by_key_b)
    # every row key is bound: a second key whose gold cell differs is reported
    other = {**key, "period_key": ["instant", "2024-04-30"]}
    other_cell = {**other, "value_exact": "7", "code": None}
    both = {**gold_by_key, _gold_key(other_cell): other_cell}
    two = {"id": "D-4", "row_keys": [key, other], "comparison": "value", "record": {"gold": same}}
    assert _defect_gold_drift(two, both)
    assert _defect_gold_drift({**two, "row_keys": [key]}, both) == []


def test_this_file_names_no_issuer() -> None:
    """No ticker, CIK, company name or accession is typed in this file."""
    source = Path(__file__).read_text(encoding="utf-8")
    forbidden: set[str] = set()
    coverage_dir = REPO_ROOT / "config" / "fundamental_forensics" / "coverage"
    for path in sorted(coverage_dir.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        for row in document.get("issuers", ()):  # type: ignore[union-attr]
            forbidden.update(
                str(row[field])
                for field in ("cik", "ticker", "legal_name")
                if row.get(field)
            )
            for accession_row in row.get("accessions", ()):  # type: ignore[union-attr]
                forbidden.add(str(accession_row.get("accession")))
    for pack_dir in _pack_dirs():
        manifest, gold_rows = _load_pack(pack_dir)
        for field in ("cik10", "entity_id", "legal_name"):
            if manifest.get(field):
                forbidden.add(str(manifest[field]))
        for key in ("security_ids", "listing_keys"):
            forbidden.update(str(item) for item in manifest.get(key, ()))
        forbidden.update(str(item) for item in manifest.get("admitted_accessions", ()))
        for row in gold_rows:
            if row.get("source_accession"):
                forbidden.add(str(row["source_accession"]))
    leaks = sorted(
        token for token in forbidden
        if len(token) >= 4 and token in source
    )
    assert not leaks, f"issuer literals typed in this file: {leaks}"
    assert not re.search(r"\b\d{10}-\d{2}-\d{6}\b", source), "accession literal typed"
    assert not re.search(r"\b\d{10}\b", source), "CIK-shaped literal typed"
    # The coverage-file tickers are short; catch them as whole words too.
    short = sorted(
        {t for t in forbidden if 2 <= len(t) < 4 and t.isalpha() and t.isupper()}
    )
    words = re.findall(r"[A-Za-z]+", source)
    assert not (set(words) & set(short)), "ticker word typed in this file"
