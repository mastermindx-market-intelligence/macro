"""FIF A1: deterministic offline per-issuer journey + refusal ledger.

Turns (a) one production publish report JSON, (b) one LOCAL replay
production-dataset store directory and (c) the coverage contract into a
per-issuer journey ledger (JSON + Markdown).  It proves, issuer by issuer,
that the locally replayed generation bytes are the production bytes
(content-addressed generation ids), and records source fidelity, statements,
lineage, kernel query journeys and refusals.

Laws this harness obeys:

* It never reads R2, never uses the network and never computes a financial
  value outside the kernel's own query path: every metric value comes from
  ``BitemporalMetricQueryEngine.query_matrix`` over payloads rebuilt by
  ``load_query_dataset_payloads`` — the same engine and payloads
  ``ProductionFinancialQueryProvider.resolve`` builds for the production
  request path (engine/fundamental_forensics/production_provider.py:112-142,
  engine/fundamental_forensics/query_service.py:648-666).
* It never re-implements a reader: store/generation/statement/lineage access
  goes through the frozen readers in
  engine/fundamental_forensics/production_datasets.py; lineage refusal causes
  go through scripts/fif_a1_lineage_causes.py, which calls only the kernel's
  own guard functions.
* Determinism: outputs are byte-identical for identical inputs — sorted keys,
  2-space indent, trailing newline, no wall clock, no absolute paths.  Each
  input file is recorded by basename + sha256 of its bytes; the store (and the
  optional archive root) by basename only.

Exit codes (an uncaught traceback is never the exit path):

* 0 — every check passed;
* 1 — the ledger was written and at least one check failed (both outputs are
  still written); a per-issuer read or internal error is a FAIL row for that
  issuer (``statement_trees_unreadable``, ``lineage_evidence_unreadable``,
  ``issuer_internal_error``) and the other issuers are still ledgered; an
  issuer that stopped at an internal error keeps exactly that one check row;
* 2 — unusable arguments/inputs: one typed stderr line plus a FAIL ledger
  carrying the ``harness_input`` check row, written to both out paths (stale
  out files are unlinked first, so no previous run's bytes survive).  Two out
  paths naming the same file are refused before any delete or input read,
  with the stderr line only (one file cannot hold the pair).  An output that
  cannot be written leaves neither output and no temp file;
* 3 — internal error: one typed stderr line plus a FAIL ledger carrying the
  ``harness_internal_error`` check row, written to both out paths.  When
  every contract issuer stopped at an internal error, the full ledger keeps
  its ``issuer_internal_error`` rows and adds that run-level row.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from functools import partial
from pathlib import Path
from typing import Any, Mapping, Sequence

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.fundamental_forensics.fif_member_capture import (  # noqa: E402
    read_retained_fif_packages,
)
from engine.fundamental_forensics.admitted_filing_package import (  # noqa: E402
    admit_retained_filing_package,
)
from engine.fundamental_forensics.issuer_sic import (  # noqa: E402
    IssuerSicResolver,
    resolve_issuer_sic,
)
from engine.fundamental_forensics.production_datasets import (  # noqa: E402
    PRODUCTION_DATASET_SCHEMA,
    ProductionDatasetError,
    build_production_dataset_store,
    lineage_from_role_payload,
    load_latest_generation,
    load_query_dataset_payloads,
    statement_trees_from_role_payload,
)
from engine.fundamental_forensics.production_lineage import (  # noqa: E402
    admitted_concept_namespace_uris,
)
from engine.fundamental_forensics.query import (  # noqa: E402
    BitemporalMetricQueryEngine,
    CellState,
    PeriodRequest,
    QueryBounds,
    QueryEntity,
    QueryPolicy,
)

# The lineage refusal cause classifier (section 4b).  Imported, never copied.
from scripts.fif_a1_lineage_causes import (  # noqa: E402
    CODE_CROSS_TAXONOMY,
    classify_refusal_causes,
)

LEDGER_SCHEMA = "fif.a1_journey_ledger/v1"

# Report/contract schemas owned by the frozen publisher
# (scripts/publish_fif_production_datasets.py:125-126).
PUBLISH_REPORT_SCHEMA = "fundamental_forensics.fif_production_publish_report/v1"
COVERAGE_CONTRACT_SCHEMA = "fundamental_forensics.coverage_contract/v1"

# The lawful (outcome, clock_basis) pairs the production publisher can emit,
# read from the publisher's own pairing invariant
# (scripts/publish_fif_production_datasets.py,
# ``_IssuerPlan._VALID_OUTCOME_CLOCK_BASIS``): "content" and
# "run_recorded_at" pair with outcome "published", "latest_unchanged" pairs
# with "unchanged".  Any other pair fails ``no_fixture_substitution``.
LAWFUL_OUTCOME_CLOCK_PAIRS = frozenset(
    {
        ("published", "content"),
        ("published", "run_recorded_at"),
        ("unchanged", "latest_unchanged"),
    }
)

# An EDGAR accession spelling (``0000320193-25-000079``) and a coverage
# contract CIK spelling (1-10 digits; the EDGAR index URL rules require int()).
_EDGAR_ACCESSION_RE = re.compile(r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
_CONTRACT_CIK_RE = re.compile(r"^[0-9]{1,10}$")

# Statement types the precomputed trees role carries per accession
# (engine/fundamental_forensics/statement_graph.py:2166,
# ``reconstruct_primary_statements``).
STATEMENT_TYPES = ("income_statement", "balance_sheet", "cash_flow")

# The journey metrics, resolved at runtime from the metric catalog snapshot
# the generation itself pins (the dataset's registry role is a snapshot of
# config/fundamental_forensics/metrics/v1/metric_catalog.yaml; see
# engine/fundamental_forensics/production_datasets.py:178-194).  Labels are
# matched exactly against the catalog's own ``label`` field — never guessed
# ids and never a ticker/CIK literal.
JOURNEY_METRIC_LABELS: tuple[tuple[str, str], ...] = (
    ("revenue", "Revenue"),
    ("net_income", "Net income or loss"),
    ("total_assets", "Total assets"),
    ("operating_cash_flow", "Net cash from operating activities"),
    ("diluted_eps", "Diluted earnings per share"),
)

# Browser linkage: the exact product URL paths a logged-in browser opens per
# issuer, derived ONLY from the site's existing fundamental-forensics routes.
#
# * The product page is ``fundamental_forensics.html``, rendered from
#   templates/fundamental_forensics.html.j2 by
#   scripts/build_fundamental_forensics.py:1490-1496 (wired into the site
#   build at scripts/build_site.py:8366-8372).  Its URL state schema —
#   ``symbol`` plus ``tab`` — is read by the page's own
#   templates/fundamental_forensics.js:1016-1058 (``readUrlParams``), with
#   tabs 'radar' (default), 'statements', 'timeline' (URL_TABS,
#   templates/fundamental_forensics.js:1023).
# * The authenticated API surface the page calls is registered in
#   app/forensics.py: ``/api/forensics/health`` (app/forensics.py:191, called
#   with an ``entity_id`` query parameter from
#   templates/fundamental_forensics.js:1244), ``/api/forensics/v1/financial/
#   query`` (app/forensics.py:1054), ``/api/forensics/v1/financial/revisions``
#   (app/forensics.py:1247) and ``/api/forensics/v1/financial/statements``
#   (app/forensics.py:1349).
BROWSER_LINKAGE_TEMPLATE = [
    {"path": "/fundamental_forensics.html?symbol={ticker}", "method": "GET"},
    {
        "path": "/fundamental_forensics.html?symbol={ticker}&tab=statements",
        "method": "GET",
    },
    {
        "path": "/fundamental_forensics.html?symbol={ticker}&tab=timeline",
        "method": "GET",
    },
    {"path": "/api/forensics/health?entity_id={issuer_id}", "method": "GET"},
    {"path": "/api/forensics/v1/financial/query", "method": "POST"},
    {"path": "/api/forensics/v1/financial/revisions", "method": "POST"},
    {"path": "/api/forensics/v1/financial/statements", "method": "POST"},
]

_HARD_MAX_PERIODS_PER_CALL = 32  # query.HARD_MAX_PERIODS (engine/fundamental_forensics/query.py:124)


class _UsageError(Exception):
    """Unusable arguments/inputs: printed as one typed line, exit 2."""


class _EmptyPeriodUniverse(Exception):
    """The governed ledger yields no queryable period.

    Raised before the kernel matrix runs so the whole-issuer kernel refusal
    is recorded as a failed ``kernel_query_engine`` check — never as the pass
    row ``0 matrix periods queried``, which would claim a query that never
    happened.
    """


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_json_file(path_text: str, *, kind: str) -> dict[str, Any]:
    path = Path(path_text)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise _UsageError(f"{kind} is unreadable: {path.name} ({exc.strerror})") from exc
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _UsageError(f"{kind} is not parseable JSON: {path.name}") from exc
    if not isinstance(document, dict):
        raise _UsageError(f"{kind} is not a JSON object: {path.name}")
    document["__input_basename__"] = path.name
    document["__input_sha256__"] = _sha256_bytes(raw)
    return document


def _issuer_rows(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _row_by_cik(rows: Sequence[Mapping[str, Any]], cik: str) -> Mapping[str, Any] | None:
    for row in rows:
        if str(row.get("cik") or "") == cik:
            return row
    return None


def edgar_index_url(cik: str, accession: str) -> str:
    """The canonical EDGAR filing-index URL for one accession.

    ``https://www.sec.gov/Archives/edgar/data/<int(cik)>/<accession without
    dashes>/<accession>-index.htm`` — derived from the issuer's CIK and the
    accession string only, never fetched.
    """
    numeric = int(cik)
    return (
        f"https://www.sec.gov/Archives/edgar/data/{numeric}/"
        f"{accession.replace('-', '')}/{accession}-index.htm"
    )


class _Checks:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def add(self, check_id: str, issuer: str | None, passed: bool, detail: str) -> None:
        self.rows.append(
            {
                "id": check_id,
                "issuer": issuer,
                "status": "pass" if passed else "fail",
                "detail": detail,
            }
        )

    @property
    def all_passed(self) -> bool:
        return all(row["status"] == "pass" for row in self.rows)


def _period_request_for_key(key: tuple[str, str, str]) -> PeriodRequest:
    kind, start, end = key
    if kind == "instant":
        return PeriodRequest.instant(end)
    return PeriodRequest.duration(start, end)


def _period_universe(ledger: Any, registry: Any) -> list[PeriodRequest]:
    """Distinct periods of governed ledger occurrences.

    Mirrors the kernel's own fact-period derivation
    (``_fact_period_index_key``, engine/fundamental_forensics/query.py:4227-
    4235: instant ``(instant, '', end)``, duration ``(duration, start, end)``)
    over occurrences whose concept is governed by the registry — the concept
    set the engine itself matches facts against
    (``f"{alias.taxonomy}:{alias.concept}"``,
    engine/fundamental_forensics/query.py:5278-5291).  The packet's cited
    helper (``_period_universe`` in tests/test_fif_g_pack_kernel.py) is absent
    from this tree at the lane BASE; the rule implemented is the one the
    packet text states.  No provider-side period enumeration exists on the
    production request path, so this ledger-derived universe is the universe.
    """
    governed = set()
    for contract in registry.contracts:
        for mapping in contract.mappings:
            for alias in mapping.taxonomy_concept_aliases:
                governed.add(f"{alias.taxonomy}:{alias.concept}")
    keys: dict[tuple[str, str, str], None] = {}
    for event in ledger.events:
        if event.concept_qname not in governed:
            continue
        context = event.context
        if context.instant is not None:
            keys.setdefault(("instant", "", context.instant.isoformat()))
        else:
            keys.setdefault(
                ("duration", context.start.isoformat(), context.end.isoformat())
            )
    return [_period_request_for_key(key) for key in sorted(keys)]


def _build_engine(
    payloads: Mapping[str, Any],
    ticker: str,
    source_entity_id: str,
    *,
    issuer_sic_resolver: IssuerSicResolver | None = None,
):
    """The same engine the production request path builds.

    ``execute_financial_query`` constructs
    ``BitemporalMetricQueryEngine(ledger=..., registry=...,
    entities=[QueryEntity(ticker=binding.ticker,
    entity_id=binding.source_entity_id,
    issuer_sic=sic_resolver(binding.source_entity_id))],
    filing_metadata=..., bounds=..., lineage_evidence=...)`` and calls
    ``query_matrix`` (engine/fundamental_forensics/query_service.py:653-684).
    Production exposes no engine builder function, so this harness mirrors
    that exact construction over ``load_query_dataset_payloads`` output —
    the issuer SIC reaches the kernel through ``QueryEntity`` only, and a
    class-restricted metric fails closed to ``issuer_class_unknown`` when no
    SIC resolves.

    Bounds: production admission caps one request at 8 periods / 400 cells
    (``_MAX_PERIODS`` / ``_MAX_CELLS``, query_service.py:46-48).  The harness
    queries the whole governed universe in 32-period chunks (``_query_cells``),
    so it uses the kernel's hard per-call period cap (32) and its cell cap
    covers 50 metrics x 32 periods (1600 <= 10_000).

    The default resolver is looked up at CALL time (never bound as a default
    argument), so the production default ``partial(resolve_issuer_sic)`` and
    any test substitution of that module name take effect per call.
    """
    sic_resolver = (
        issuer_sic_resolver
        if issuer_sic_resolver is not None
        else partial(resolve_issuer_sic)
    )
    return BitemporalMetricQueryEngine(
        ledger=payloads["ledger"],
        registry=payloads["registry"],
        entities=[
            QueryEntity(
                ticker=ticker,
                entity_id=source_entity_id,
                issuer_sic=sic_resolver(source_entity_id),
            )
        ],
        filing_metadata=payloads["filing_metadata"],
        bounds=QueryBounds(max_tickers=1, max_metrics=50, max_periods=32, max_cells=10_000),
        lineage_evidence=payloads["lineage_evidence"] or (),
    )


def _query_cells(
    engine: BitemporalMetricQueryEngine,
    *,
    ticker: str,
    metrics: Sequence[str],
    periods: Sequence[PeriodRequest],
    policy: QueryPolicy,
) -> list[Any]:
    """query_matrix over period chunks (the kernel caps periods per call)."""
    cells: list[Any] = []
    for index in range(0, len(periods), _HARD_MAX_PERIODS_PER_CALL):
        chunk = list(periods[index : index + _HARD_MAX_PERIODS_PER_CALL])
        matrix = engine.query_matrix(
            tickers=[ticker], metrics=list(metrics), periods=chunk, policy=policy
        )
        cells.extend(matrix.cells)
    return cells


def _statement_index(gen: Any) -> dict[str, dict[str, Any]]:
    """Accession -> decoded statement-packages-index row (manifest + members)."""
    document = json.loads(gen.role_payloads["statement_packages_index_json"])
    out: dict[str, dict[str, Any]] = {}
    for item in document.get("accessions") or []:
        if isinstance(item, dict) and isinstance(item.get("accession"), str):
            out[item["accession"]] = item
    return out


def _primary_document_row(index_row: Mapping[str, Any] | None) -> dict[str, Any]:
    """The primary document exactly as the generation records it.

    The statement-packages-index role records every package member with
    ``{name, state, role, content_sha256, byte_length}``
    (engine/fundamental_forensics/production_datasets.py:361-384); the primary
    document is the member whose ``role`` is ``primary``.  Nothing here hashes
    SEC bytes itself — when no such row is recorded the answer is
    ``{"status": "not_recorded"}``.
    """
    if index_row is None:
        return {"status": "not_recorded"}
    for row in index_row.get("members") or []:
        if isinstance(row, dict) and row.get("role") == "primary":
            name = row.get("name")
            digest = row.get("content_sha256")
            length = row.get("byte_length")
            if isinstance(name, str) and isinstance(digest, str) and isinstance(length, int):
                return {"name": name, "sha256": digest, "byte_length": length}
    return {"status": "not_recorded"}


def _journey_metric_ids(registry: Any) -> dict[str, str]:
    """Resolve the five journey metric ids from the pinned catalog snapshot.

    The generation's registry role is the publication-time snapshot of
    config/fundamental_forensics/metrics/v1/metric_catalog.yaml
    (engine/fundamental_forensics/production_datasets.py:178-194); ids are
    matched by the catalog's own ``label`` text so no id is guessed.
    """
    by_label: dict[str, str] = {}
    for contract in registry.contracts:
        by_label.setdefault(contract.label, contract.metric_id)
    resolved: dict[str, str] = {}
    for slot, label in JOURNEY_METRIC_LABELS:
        metric_id = by_label.get(label)
        if metric_id is None:
            raise _UsageError(
                f"journey metric label is not in the pinned catalog: {label!r}"
            )
        resolved[slot] = metric_id
    return resolved


def _filing_period_ends(statement_index: Mapping[str, Mapping[str, Any]]) -> tuple[set[str], set[str]]:
    """Annual and quarter period-of-report ends, keyed by the filing's form."""
    annual: set[str] = set()
    quarterly: set[str] = set()
    for row in statement_index.values():
        manifest = row.get("manifest") or {}
        form = str(manifest.get("form") or "")
        period = manifest.get("period_of_report")
        if not isinstance(period, str) or not period:
            continue
        if form.startswith("10-K"):
            annual.add(period)
        elif form.startswith("10-Q"):
            quarterly.add(period)
    return annual, quarterly


def _journey_periods(
    metric_id: str,
    registry: Any,
    universe: Sequence[PeriodRequest],
    annual_ends: set[str],
    quarterly_ends: set[str],
) -> dict[str, PeriodRequest | None]:
    """Latest annual + latest quarterly period for one journey metric.

    Both scopes take the LATEST end date; annual then picks the LONGEST
    duration ending there (a fiscal year, not a quarter that happens to share
    its end date), quarterly the shortest (today's key).  Instants carry no
    start, so they rank by end date only.
    """
    contract = registry.metric(metric_id)
    kind = str(contract.period_constraints.kind)
    out: dict[str, PeriodRequest | None] = {"annual": None, "quarterly": None}

    def _pick(candidates: list[PeriodRequest], *, annual: bool) -> PeriodRequest | None:
        if not candidates:
            return None
        if annual:
            return max(
                candidates,
                key=lambda period: (
                    str(period.end),
                    -(period.start.toordinal() if period.start is not None else 0),
                ),
            )
        return max(candidates, key=lambda period: (str(period.end), str(period.start or "")))

    if annual_ends or quarterly_ends:
        for scope, ends in (("annual", annual_ends), ("quarterly", quarterly_ends)):
            candidates = [
                period
                for period in universe
                if str(period.kind.value) == kind and str(period.end) in ends
            ]
            out[scope] = _pick(candidates, annual=scope == "annual")
        return out
    # No statement packages: fall back to duration length.  A year is at least
    # 300 days; a quarter is 60..150 days.  Instants key off those durations'
    # end dates.
    durations = [
        period
        for period in universe
        if str(period.kind.value) == "duration" and period.start is not None
    ]
    fallback_annual_ends = {
        str(period.end) for period in durations if (period.end - period.start).days >= 300
    }
    fallback_quarterly_ends = {
        str(period.end)
        for period in durations
        if 60 <= (period.end - period.start).days <= 150
    }
    for scope, ends in (("annual", fallback_annual_ends), ("quarterly", fallback_quarterly_ends)):
        candidates = [
            period for period in universe if str(period.kind.value) == kind and str(period.end) in ends
        ]
        out[scope] = _pick(candidates, annual=scope == "annual")
    return out


def _journey_row(metric_slot: str, metric_id: str, scope: str, cell: Any | None, period: PeriodRequest | None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "metric": metric_slot,
        "metric_id": metric_id,
        "scope": scope,
    }
    if period is not None:
        row["period"] = {
            "kind": str(period.kind.value),
            "start": str(period.start) if period.start else None,
            "end": str(period.end),
        }
    else:
        row["period"] = None
    if cell is None:
        row["status"] = "refused"
        row["code"] = "period_unavailable"
        return row
    if cell.state is CellState.VALUE:
        provenance = cell.provenance
        occurrence_ids = list(provenance.source_occurrence_ids or ())
        row["status"] = "served"
        row["value"] = str(cell.value) if cell.value is not None else None
        row["unit"] = cell.unit
        row["concept"] = provenance.concept_qname
        row["fact_id"] = occurrence_ids[0] if occurrence_ids else None
        row["accession"] = provenance.accession
        row["source_url"] = provenance.source_url
        return row
    row["status"] = "refused"
    row["code"] = cell.reason
    return row


def _histogram_flat(histogram: Mapping[str, Any]) -> str:
    parts: list[str] = []
    cross = histogram.get(CODE_CROSS_TAXONOMY) or {}
    total_cross = sum(cross.values()) if isinstance(cross, Mapping) else 0
    for code in sorted(histogram):
        if code == CODE_CROSS_TAXONOMY:
            continue
        parts.append(f"{code} {histogram[code]}")
    detail = ", ".join(f"{k} {v}" for k, v in sorted(cross.items()))
    parts.append(f"{CODE_CROSS_TAXONOMY} {total_cross} ({detail})")
    return ", ".join(parts)


def _render_markdown(document: Mapping[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# FIF A1 journey ledger")
    lines.append("")
    inputs = document["inputs"]
    if inputs:
        lines.append(
            f"Production report: `{inputs['production_report']['basename']}` "
            f"(sha256 `{inputs['production_report']['sha256'][:16]}…`), "
            f"store: `{inputs['store_dir']['basename']}`, "
            f"contract: `{inputs['coverage_contract']['basename']}`."
        )
    else:
        # A harness failure ledger carries no inputs: the run refused before
        # reading them, and the markdown says so instead of raising.
        lines.append("Inputs: none (the harness refused before reading its inputs).")
    lines.append("")
    lines.append("## Coverage")
    lines.append("")
    header = [
        "ticker",
        "contract",
        "captured",
        "admitted",
        "served",
        "statements served",
        "statement refusals",
        "lineage receipts",
        "lineage refusals",
        "bridge",
    ]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")
    for row in document["coverage_table"]:
        cross = row["lineage_refusal_codes"]
        total = row["lineage_refusals"]
        detail = ", ".join(f"{code} {count}" for code, count in sorted(cross.items()))
        refusal_text = f"{total}" + (f" ({detail})" if detail else "")
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["ticker"]),
                    str(row["contract"]),
                    str(row["captured"]),
                    str(row["admitted"]),
                    str(row["served"]),
                    str(row["statements_served"]),
                    str(row["statement_refusals"]),
                    str(row["lineage_receipts"]),
                    refusal_text,
                    str(row["bridge"]),
                ]
            )
            + " |"
        )
    lines.append("")
    for issuer in document["issuers"]:
        lines.append(f"## {issuer['ticker']}")
        lines.append("")
        bridge = issuer["bridge"]
        lines.append(
            f"- bridge: **{bridge['status'] or 'dropped'}** "
            f"(production generation `{bridge['production_generation_id']}`, "
            f"local generation `{bridge['local_generation_id']}`)"
        )
        if bridge["status"] == "not_published":
            lines.append(
                f"- exclusion reason: `{bridge['exclusion_reason']}`"
            )
        basis = issuer.get("basis")
        if basis:
            lines.append(f"- basis: `{basis}`")
        journeys = issuer.get("query_journeys") or []
        if journeys:
            lines.append("")
            lines.append("### Query journeys")
            lines.append("")
            lines.append("| metric | scope | period | status | value | unit | concept | accession |")
            lines.append("|---|---|---|---|---|---|---|---|")
            for journey in journeys:
                period = journey.get("period") or {}
                period_text = (
                    f"{period.get('kind')}"
                    + (f" {period.get('start')}.." if period.get("start") else " ")
                    + f"{period.get('end')}"
                    if period
                    else ""
                )
                # An unresolved id (the registry itself could not load) renders
                # the slot name — the literal None never reaches the column.
                metric_cell = (
                    str(journey["metric_id"])
                    if journey.get("metric_id") is not None
                    else str(journey["metric"])
                )
                if journey["status"] == "served":
                    lines.append(
                        "| "
                        + " | ".join(
                            [
                                metric_cell,
                                str(journey["scope"]),
                                period_text,
                                "served",
                                str(journey.get("value")),
                                str(journey.get("unit")),
                                str(journey.get("concept")),
                                str(journey.get("accession")),
                            ]
                        )
                        + " |"
                    )
                else:
                    lines.append(
                        "| "
                        + " | ".join(
                            [
                                metric_cell,
                                str(journey["scope"]),
                                period_text,
                                "refused",
                                f"`{journey.get('code')}`",
                                "",
                                "",
                                "",
                            ]
                        )
                        + " |"
                    )
        causes = ((issuer.get("lineage") or {}).get("refusal_causes")) or None
        if causes:
            lines.append("")
            lines.append("### Lineage refusal ledger")
            lines.append("")
            if "histogram" in causes:
                lines.append(f"- basis: `{causes['basis']}`")
                lines.append(f"- histogram: {_histogram_flat(causes['histogram'])}")
            else:
                lines.append(f"- status: `unavailable` ({causes.get('reason')})")
        lines.append("")
    lines.append("## Checks")
    lines.append("")
    lines.append("| id | issuer | status | detail |")
    lines.append("|---|---|---|---|")
    for check in document["checks"]:
        lines.append(
            f"| {check['id']} | {check['issuer'] or '-'} | {check['status']} | {check['detail']} |"
        )
    lines.append("")
    lines.append(f"all_checks_passed: **{str(document['all_checks_passed']).lower()}**")
    lines.append("")
    return "\n".join(lines)


def _archive_taxonomy_uris(
    *,
    archive_root: Path,
    cik: str,
    admitted_accessions: Sequence[str],
    statement_index: Mapping[str, Mapping[str, Any]],
    ticker: str,
    checks: _Checks,
) -> tuple[dict[tuple[str, str], str], bool]:
    """Recover original concept namespace URIs from the retained archive.

    Uses the SAME loader the publisher uses for ``--archive-root``
    (``read_retained_fif_packages``,
    engine/fundamental_forensics/fif_member_capture.py:1170, called at
    scripts/publish_fif_production_datasets.py:1355) plus the publisher's own
    admission step (``admit_retained_filing_package``,
    scripts/publish_fif_production_datasets.py:1408).  Before any URI is
    used, each retained package's primary-document sha256 must equal the value
    the generation records for that accession — else failed check
    ``archive_package_mismatch`` and the elimination basis for this issuer.
    An empty admitted set refuses before any archive read: there is nothing
    to verify against, and a match over zero packages would be vacuous.
    """
    if not admitted_accessions:
        checks.add(
            "archive_package_mismatch",
            ticker,
            False,
            "no admitted accession to verify against the retained archive",
        )
        return {}, False
    uris: dict[tuple[str, str], str] = {}
    try:
        retained = read_retained_fif_packages(
            archive_root, cik=cik, accessions=list(admitted_accessions)
        )
    except Exception as exc:  # noqa: BLE001 - typed, never a crash
        checks.add(
            "archive_package_mismatch",
            ticker,
            False,
            f"retained archive read refused ({type(exc).__name__})",
        )
        return {}, False
    verified = []
    for package in retained:
        accession = str(package.manifest.get("accession") or "")
        primary = package.manifest.get("primary_document")
        recorded = _primary_document_row(statement_index.get(accession))
        member = package.members.get(primary) if isinstance(primary, str) else None
        if "sha256" not in recorded or member is None:
            checks.add(
                "archive_package_mismatch",
                ticker,
                False,
                f"archive package for {accession} has no comparable primary bytes",
            )
            return {}, False
        if _sha256_bytes(member) != recorded.get("sha256"):
            checks.add(
                "archive_package_mismatch",
                ticker,
                False,
                f"archive primary sha256 differs from the generation for {accession}",
            )
            return {}, False
        try:
            verified.append(
                admit_retained_filing_package(
                    index_bytes=package.index_bytes,
                    manifest=dict(package.manifest),
                    members=dict(package.members),
                    witness_bytes=package.witness_bytes,
                    capture_recorded_at=package.capture_recorded_at,
                )
            )
        except Exception as exc:  # noqa: BLE001 - typed, never a crash
            checks.add(
                "archive_package_mismatch",
                ticker,
                False,
                f"archive package admission refused for {accession} ({type(exc).__name__})",
            )
            return {}, False
    if len(verified) != len(set(admitted_accessions)):
        checks.add(
            "archive_package_mismatch",
            ticker,
            False,
            "retained archive is missing an admitted accession",
        )
        return {}, False
    try:
        uris = admitted_concept_namespace_uris(tuple(verified))
    except Exception as exc:  # noqa: BLE001 - typed, never a crash
        checks.add(
            "archive_package_mismatch",
            ticker,
            False,
            f"namespace URI recovery refused ({type(exc).__name__})",
        )
        return {}, False
    return uris, True


def _fixture_locator_hits(gen: Any) -> list[str]:
    if gen is None:
        return []
    hits: list[str] = []
    needle = b"tests/fixtures/"
    for role in sorted(gen.role_payloads):
        if needle in gen.role_payloads[role]:
            hits.append(f"role {role}")
    if needle in json.dumps(gen.manifest).encode("utf-8"):
        hits.append("manifest")
    return hits


_REPORT_ROW_SECTIONS = (
    "published",
    "excluded",
    "coverage",
    "statement_refusals",
    "not_attempted",
)


def _row_cik_text(row: Mapping[str, Any]) -> str:
    """A report row's cik as display text; no cik is ``"(missing)"``."""
    return str(row.get("cik") or "") or "(missing)"


def _failed_row(report: Mapping[str, Any]) -> Mapping[str, Any] | None:
    failed = report.get("failed")
    return failed if isinstance(failed, Mapping) else None


def _report_fixture_hits_for_cik(report: Mapping[str, Any], cik: str) -> list[str]:
    """Fixture locators in ONE contract issuer's own report rows.

    Scans the row sections a report attributes to issuers (``published``,
    ``excluded``, ``coverage``, ``statement_refusals``, ``not_attempted``,
    plus the ``failed`` object) and keeps only rows whose ``cik`` is this
    issuer's — a locator in another issuer's rows belongs to that issuer's
    verdict, and an unattributed row to ``production_report_shape``.
    """
    needle = "tests/fixtures/"
    hits: list[str] = []
    for section in _REPORT_ROW_SECTIONS:
        rows = _issuer_rows(report.get(section))
        for index, row in enumerate(rows):
            if str(row.get("cik") or "") != cik:
                continue
            if needle in json.dumps(row, sort_keys=True):
                hits.append(f"report {section}[{index}]")
    failed = _failed_row(report)
    if failed is not None and str(failed.get("cik") or "") == cik:
        if needle in json.dumps(failed, sort_keys=True):
            hits.append("report failed")
    return hits


def _unattributed_fixture_hits(
    report: Mapping[str, Any], contract_ciks: set[str]
) -> list[str]:
    """Fixture locators in report rows NO contract issuer owns."""
    needle = "tests/fixtures/"
    hits: list[str] = []
    for section in _REPORT_ROW_SECTIONS:
        rows = _issuer_rows(report.get(section))
        for index, row in enumerate(rows):
            if str(row.get("cik") or "") in contract_ciks:
                continue
            if needle in json.dumps(row, sort_keys=True):
                hits.append(f"report {section}[{index}]")
    failed = _failed_row(report)
    if failed is not None and str(failed.get("cik") or "") not in contract_ciks:
        if needle in json.dumps(failed, sort_keys=True):
            hits.append("report failed")
    return hits


def build_ledger(
    *,
    report: Mapping[str, Any],
    contract: Mapping[str, Any],
    store_dir: Path,
    archive_root: Path | None,
) -> dict[str, Any]:
    checks = _Checks()
    report_basename = report["__input_basename__"]
    contract_basename = contract["__input_basename__"]

    published_rows = _issuer_rows(report.get("published"))
    excluded_rows = _issuer_rows(report.get("excluded"))
    coverage_rows = _issuer_rows(report.get("coverage"))
    statement_refusal_rows = _issuer_rows(report.get("statement_refusals"))

    store = build_production_dataset_store(store_dir)
    if store is None:
        raise _UsageError(f"store directory is unusable: {store_dir.name}")

    inputs: dict[str, Any] = {
        "production_report": {
            "basename": report_basename,
            "sha256": report["__input_sha256__"],
        },
        "coverage_contract": {
            "basename": contract_basename,
            "sha256": contract["__input_sha256__"],
        },
        "store_dir": {"basename": store_dir.name},
        "archive_root": {"basename": archive_root.name} if archive_root is not None else None,
    }

    issuers_out: list[dict[str, Any]] = []
    coverage_table: list[dict[str, Any]] = []

    contract_issuers = _issuer_rows(contract.get("issuers"))

    def _ledger_issuer(issuer_row: Mapping[str, Any]) -> None:
        """Ledger one contract issuer; appends its issuer entry and coverage row."""
        ticker = str(issuer_row.get("ticker") or "")
        cik = str(issuer_row.get("cik") or "")
        binding = issuer_row.get("security_master_binding") or {}
        issuer_id = str(binding.get("issuer_id") or "") if isinstance(binding, Mapping) else ""
        # A malformed contract row is a FAILED check and a skipped issuer, not
        # a whole-run refusal: the remaining issuers are still processed.
        malformed: list[str] = []
        if not ticker:
            malformed.append("ticker is missing")
        if not cik:
            malformed.append("cik is missing")
        elif not _CONTRACT_CIK_RE.fullmatch(cik):
            malformed.append(f"cik is not 1-10 digits: {cik!r}")
        if not issuer_id:
            malformed.append("security_master_binding.issuer_id is missing")
        if malformed:
            checks.add(
                "contract_issuer_malformed",
                ticker or None,
                False,
                f"coverage contract issuer row in {contract_basename}: " + "; ".join(malformed),
            )
            return
        pub_row = _row_by_cik(published_rows, cik)
        exc_row = _row_by_cik(excluded_rows, cik)
        cov_row = _row_by_cik(coverage_rows, cik)
        if pub_row is not None and cov_row is None:
            checks.add(
                "coverage_row_missing",
                ticker,
                False,
                "published issuer has no coverage[] row in the production report",
            )

        # ---- 1. bridge -------------------------------------------------
        try:
            generation = load_latest_generation(store, issuer_id)
        except Exception as exc:  # noqa: BLE001 - typed, never a crash
            checks.add(
                "store_generation_unreadable",
                ticker,
                False,
                f"latest generation for {issuer_id} cannot be verified ({type(exc).__name__})",
            )
            generation = None
        local_generation_id = generation.generation_id if generation is not None else None

        bridge: dict[str, Any] = {
            "status": None,
            "production_generation_id": None,
            "local_generation_id": local_generation_id,
            "production_outcome": None,
            "production_clock_basis": None,
            "manifest_key": None,
        }
        basis: str | None = None
        if pub_row is not None:
            checks.add(
                "coverage_served",
                ticker,
                True,
                "issuer published by the production run",
            )
            bridge["production_generation_id"] = pub_row.get("generation_id")
            bridge["production_outcome"] = pub_row.get("outcome")
            bridge["production_clock_basis"] = pub_row.get("clock_basis")
            bridge["manifest_key"] = pub_row.get("manifest_key")
            basis = "production_report"
            if generation is None:
                bridge["status"] = "mismatch"
                checks.add(
                    "bridge",
                    ticker,
                    False,
                    "report publishes a generation but the store holds none",
                )
            elif generation.generation_id != pub_row.get("generation_id"):
                bridge["status"] = "mismatch"
                checks.add(
                    "bridge",
                    ticker,
                    False,
                    "report generation id differs from the store's latest generation id",
                )
            else:
                bridge["status"] = "match"
                checks.add(
                    "bridge",
                    ticker,
                    True,
                    "report generation id equals the store's latest generation id",
                )
            if str(pub_row.get("entity_id") or "") != issuer_id:
                checks.add(
                    "entity_binding",
                    ticker,
                    False,
                    "report published row entity_id differs from the contract issuer_id",
                )
            else:
                checks.add(
                    "entity_binding",
                    ticker,
                    True,
                    "report published row entity_id equals the contract issuer_id",
                )
        elif exc_row is not None:
            bridge["status"] = "not_published"
            bridge["exclusion_reason"] = exc_row.get("reason")
            bridge["exclusion_detail"] = exc_row.get("detail")
            checks.add(
                "coverage_served",
                ticker,
                False,
                f"issuer excluded by the production publish: {exc_row.get('reason')}",
            )
            if generation is not None:
                basis = "local_replay_only"
        else:
            # In neither report section: name the precise terminal state the
            # report itself records for this issuer before calling it dropped.
            failed = _failed_row(report)
            if failed is not None and str(failed.get("cik") or "") == cik:
                checks.add(
                    "publish_commit_failed",
                    ticker,
                    False,
                    f"report failed[] records a commit failure with code {failed.get('code')!r}",
                )
            elif any(
                str(row.get("cik") or "") == cik
                for row in _issuer_rows(report.get("not_attempted"))
            ):
                checks.add(
                    "publish_not_attempted",
                    ticker,
                    False,
                    "report not_attempted[] lists the issuer without a publish outcome",
                )
            else:
                checks.add(
                    "issuer_dropped",
                    ticker,
                    False,
                    "contract issuer appears in neither published[] nor excluded[]",
                )

        issuer_out: dict[str, Any] = {
            "ticker": ticker,
            "cik": cik,
            "issuer_id": issuer_id,
            "bridge": bridge,
            "basis": basis,
        }

        statements_served = 0
        statement_refusals = 0
        lineage_receipts_total: int | str = 0
        refusal_causes: dict[str, Any] | None = None

        # ---- 2. accessions ---------------------------------------------
        contract_accessions = _issuer_rows(issuer_row.get("accessions"))
        cov_accessions = {
            str(row.get("accession") or ""): row
            for row in _issuer_rows((cov_row or {}).get("accessions"))
        }
        served_events: set[str] = set()
        for source in (pub_row or {}).get("admitted_event_accessions") or []:
            served_events.add(str(source))
        for source in (exc_row or {}).get("admitted_event_accessions") or []:
            served_events.add(str(source))
        statement_index: dict[str, dict[str, Any]] = {}
        if generation is not None:
            try:
                statement_index = _statement_index(generation)
            except Exception as exc:  # noqa: BLE001 - typed, never a crash
                statement_index = {}
                checks.add(
                    "statement_index_unreadable",
                    ticker,
                    False,
                    f"statement packages index cannot be decoded ({type(exc).__name__})",
                )

        served_accessions_report = {
            accession
            for accession, row in cov_accessions.items()
            if bool(row.get("served"))
        }
        outside = sorted(served_accessions_report - {str(a.get("accession") or "") for a in contract_accessions})
        if outside:
            checks.add(
                "served_outside_contract",
                ticker,
                False,
                "served accessions not in the contract: " + ", ".join(outside),
            )

        accession_rows: list[dict[str, Any]] = []
        for entry in contract_accessions:
            accession = str(entry.get("accession") or "")
            cov_acc = cov_accessions.get(accession) or {}
            captured = bool(cov_acc.get("captured"))
            admitted = bool(cov_acc.get("admitted"))
            served = bool(cov_acc.get("served"))
            not_served_reason: str | None = None
            if captured and not served:
                if accession in served_events:
                    not_served_reason = "event_filing_admitted_not_served"
                elif isinstance(cov_acc.get("served_withheld"), str):
                    not_served_reason = str(cov_acc.get("served_withheld"))
                elif (report.get("accession_all_refused") or {}).get(accession):
                    not_served_reason = "all_statements_refused"
                else:
                    not_served_reason = "not_served"
            accession_rows.append(
                {
                    "accession": accession,
                    "form": entry.get("form"),
                    "filing_date": entry.get("filing_date"),
                    "period_of_report": entry.get("period_of_report"),
                    "retention_state": entry.get("retention_state"),
                    "captured": captured,
                    "admitted": admitted,
                    "served": served,
                    "edgar_index_url": edgar_index_url(cik, accession),
                    "primary_document": _primary_document_row(
                        statement_index.get(accession)
                    ),
                    "not_served_reason": not_served_reason,
                    "missing_code": cov_acc.get("missing_code"),
                }
            )
        issuer_out["accessions"] = accession_rows

        if generation is not None:
            # ---- 3. statements ------------------------------------------
            gen_refusals: dict[tuple[str, str], str] = {}
            gen_served: set[tuple[str, str]] = set()
            served_accessions = (
                served_accessions_report
                if pub_row is not None
                else set(statement_index)
            )
            statement_rows: list[dict[str, Any]] = []
            unindexed_accessions: set[str] = set()
            unreadable_trees: set[str] = set()
            for accession in sorted(served_accessions):
                if accession not in statement_index:
                    unindexed_accessions.add(accession)
                    continue
                try:
                    trees = statement_trees_from_role_payload(
                        generation.role_payloads["statement_trees_json"], accession
                    )
                except Exception as exc:  # noqa: BLE001 - a per-issuer read error is a FAIL row, never a crash
                    unreadable_trees.add(f"{accession} ({type(exc).__name__})")
                    continue
                for statement in trees.get("statements") or []:
                    if not isinstance(statement, dict):
                        continue
                    statement_type = str(statement.get("statement_type") or "")
                    refusal = statement.get("refusal")
                    if isinstance(refusal, Mapping) and refusal.get("code"):
                        gen_refusals[(accession, statement_type)] = str(refusal["code"])
                    else:
                        gen_served.add((accession, statement_type))
            if unindexed_accessions:
                checks.add(
                    "served_accession_unindexed",
                    ticker,
                    False,
                    "served accessions absent from the statement packages index: "
                    + ", ".join(sorted(unindexed_accessions)),
                )
            if unreadable_trees:
                checks.add(
                    "statement_trees_unreadable",
                    ticker,
                    False,
                    "statement trees cannot be read from the generation: "
                    + ", ".join(sorted(unreadable_trees)),
                )
            # Every served accession must record its primary document — an
            # unrecorded primary is a silent hole in the generation, not a 0.
            missing_primary = sorted(
                accession
                for accession in served_accessions
                if "sha256" not in _primary_document_row(statement_index.get(accession))
            )
            if not served_accessions and pub_row is not None:
                checks.add(
                    "primary_document_recorded",
                    ticker,
                    False,
                    "published issuer has no served accession",
                )
            elif missing_primary:
                checks.add(
                    "primary_document_recorded",
                    ticker,
                    False,
                    "served accessions without a recorded primary document: "
                    + ", ".join(missing_primary),
                )
            else:
                checks.add(
                    "primary_document_recorded",
                    ticker,
                    True,
                    f"{len(served_accessions)} served accessions carry a recorded primary document",
                )
            report_refusals: dict[tuple[str, str], dict[str, Any]] = {}
            for row in statement_refusal_rows:
                if str(row.get("cik") or "") != cik:
                    continue
                key = (str(row.get("accession") or ""), str(row.get("statement_type") or ""))
                report_refusals[key] = {
                    "code": str(row.get("code") or ""),
                    "message": row.get("message"),
                }
            # Fail-closed census: every served accession x statement type is
            # either served, refused by the generation, or refused by the
            # report.  An unreadable tree or an unindexed accession leaves
            # types unaccounted, and that is a FAILED check.
            unaccounted = sorted(
                f"{accession} {statement_type}"
                for accession in served_accessions
                for statement_type in STATEMENT_TYPES
                if (accession, statement_type) not in gen_served
                and (accession, statement_type) not in gen_refusals
                and not (report_refusals.get((accession, statement_type)) or {}).get("code")
            )
            if unaccounted:
                checks.add(
                    "statement_types_accounted",
                    ticker,
                    False,
                    "statement types neither served nor refused: " + ", ".join(unaccounted),
                )
            else:
                checks.add(
                    "statement_types_accounted",
                    ticker,
                    True,
                    f"{len(served_accessions)} served accessions x "
                    f"{len(STATEMENT_TYPES)} statement types accounted",
                )
            disagreements: list[str] = []
            for key in sorted(set(gen_refusals) | set(report_refusals)):
                gen_code = gen_refusals.get(key)
                report_code = (report_refusals.get(key) or {}).get("code") or None
                if pub_row is not None and gen_code != report_code:
                    disagreements.append(
                        f"{key[0]} {key[1]}: generation {gen_code!r} vs report {report_code!r}"
                    )
            if disagreements:
                checks.add(
                    "statement_refusal_consistency",
                    ticker,
                    False,
                    "; ".join(disagreements),
                )
            elif pub_row is not None:
                checks.add(
                    "statement_refusal_consistency",
                    ticker,
                    True,
                    f"generation and report agree on {len(gen_refusals)} statement refusals",
                )
            for accession in sorted(
                {key[0] for key in set(gen_refusals) | set(report_refusals)}
            ):
                for statement_type in STATEMENT_TYPES:
                    key = (accession, statement_type)
                    if key not in gen_refusals and key not in report_refusals:
                        continue
                    report_entry = report_refusals.get(key) or {}
                    row: dict[str, Any] = {
                        "accession": accession,
                        "statement_type": statement_type,
                        "served": key in gen_served and key not in gen_refusals and key not in report_refusals,
                        "refusal": {
                            "generation_code": gen_refusals.get(key),
                            "report_code": report_entry.get("code") or None,
                            "report_message": report_entry.get("message"),
                        },
                    }
                    statement_rows.append(row)
            for key in sorted(gen_served):
                if key in gen_refusals or key in report_refusals:
                    continue
                statement_rows.append(
                    {
                        "accession": key[0],
                        "statement_type": key[1],
                        "served": True,
                        "refusal": None,
                    }
                )
            statement_rows.sort(key=lambda row: (row["accession"], row["statement_type"]))
            statements_served = sum(1 for row in statement_rows if row["served"])
            statement_refusals = sum(1 for row in statement_rows if not row["served"])
            issuer_out["statements"] = statement_rows
            issuer_out["statement_counts"] = {
                "served": statements_served,
                "refused": statement_refusals,
            }

            # ---- 4. lineage receipts + 4b causes -------------------------
            try:
                receipts = lineage_from_role_payload(
                    generation.role_payloads["lineage_evidence_json"]
                )
            except Exception as exc:  # noqa: BLE001 - a per-issuer read error is a FAIL row, never a crash
                receipts = None
                checks.add(
                    "lineage_evidence_unreadable",
                    ticker,
                    False,
                    f"lineage evidence cannot be read from the generation ({type(exc).__name__})",
                )
            by_version: dict[str, int] = {}
            if receipts is not None:
                for receipt in receipts:
                    version = str(getattr(receipt, "evidence_rule_version", ""))
                    by_version[version] = by_version.get(version, 0) + 1
                lineage_receipts_total = len(receipts)
            else:
                # Never a fake 0: a 0 would claim a census that never ran.
                lineage_receipts_total = "unavailable"
            reported_receipt_count = (
                pub_row.get("lineage_receipt_count") if pub_row is not None else None
            )
            if pub_row is not None:
                # The census is ALWAYS answered for a published issuer: a
                # missing or non-integer report count is a failed check, not
                # a skipped comparison.
                if receipts is None:
                    checks.add(
                        "lineage_count",
                        ticker,
                        False,
                        "generation lineage receipts are unreadable; "
                        "the report lineage_receipt_count cannot be compared",
                    )
                elif isinstance(reported_receipt_count, bool) or not isinstance(
                    reported_receipt_count, int
                ):
                    checks.add(
                        "lineage_count",
                        ticker,
                        False,
                        "report lineage_receipt_count is missing or not an integer",
                    )
                elif reported_receipt_count != lineage_receipts_total:
                    checks.add(
                        "lineage_count",
                        ticker,
                        False,
                        f"report lineage_receipt_count {reported_receipt_count} "
                        f"differs from the generation's {lineage_receipts_total} receipts",
                    )
                else:
                    checks.add(
                        "lineage_count",
                        ticker,
                        True,
                        f"report lineage_receipt_count equals the generation's {lineage_receipts_total} receipts",
                    )
            taxonomy_uris: dict[tuple[str, str], str] = {}
            archive_available = False
            if archive_root is not None:
                taxonomy_uris, archive_available = _archive_taxonomy_uris(
                    archive_root=archive_root,
                    cik=cik,
                    admitted_accessions=sorted(statement_index),
                    statement_index=statement_index,
                    ticker=ticker,
                    checks=checks,
                )
            if archive_available:
                checks.add(
                    "archive_package_mismatch",
                    ticker,
                    True,
                    "retained archive primary documents match the generation records",
                )

            # The kernel half: engine, matrix, causes, journeys.  A generation
            # whose own bytes cannot serve governed query (a typed engine
            # refusal) is a journey fact, never a crash — the refusal is
            # carried with its typed reason.
            kernel_error: str | None = None
            journey_ids: dict[str, str] = {}
            try:
                payloads = load_query_dataset_payloads(generation)
                registry = payloads["registry"]
                journey_ids = _journey_metric_ids(registry)
                ledger = payloads["ledger"]
                engine = _build_engine(
                    payloads, ticker, generation.binding.source_entity_id
                )
                # Query clock: the generation's own admitted_at — the dataset's
                # admission clock.  A12 (engine/fundamental_forensics/
                # query_service.py:229-256) refuses any recorded_at below it,
                # and a production report's recorded_at can precede a local
                # replay generation's admission, so admitted_at is the one
                # clock that is always lawful for these exact bytes.
                clock = generation.admitted_at
                policy = QueryPolicy(
                    selection="latest_known_as_of",
                    source_snapshot_at=clock,
                    recorded_at=clock,
                )
                universe = _period_universe(ledger, registry)
                if not universe:
                    # An empty universe is a kernel refusal, never the pass
                    # row "0 matrix periods queried": no matrix period was
                    # queried, so the engine proved nothing.
                    raise _EmptyPeriodUniverse(
                        "governed period universe is empty; no matrix period was queried"
                    )
                metrics = sorted(registry.metric_ids)
                cells = _query_cells(
                    engine,
                    ticker=ticker,
                    metrics=metrics,
                    periods=universe,
                    policy=policy,
                )
                event_by_id = {event.occurrence_id: event for event in ledger.events}
                events_by_logical_key: dict[str, list[Any]] = {}
                for event in ledger.events:
                    events_by_logical_key.setdefault(event.logical_key, []).append(event)
                refusal_causes = classify_refusal_causes(
                    cells=cells,
                    event_by_id=event_by_id,
                    events_by_logical_key=events_by_logical_key,
                    taxonomy_uris=taxonomy_uris,
                    archive_available=archive_available,
                )
                cross = refusal_causes["histogram"].get(CODE_CROSS_TAXONOMY) or {}
                refusal_causes["total_unlinked_cells"] = sum(
                    count
                    for code, count in refusal_causes["histogram"].items()
                    if code != CODE_CROSS_TAXONOMY
                ) + (sum(cross.values()) if isinstance(cross, Mapping) else 0)

                # ---- 5. query journeys ----------------------------------
                annual_ends, quarterly_ends = _filing_period_ends(statement_index)
                journey_periods: list[tuple[str, str, PeriodRequest | None]] = []
                for slot, metric_id in sorted(journey_ids.items()):
                    scopes = _journey_periods(
                        metric_id, registry, universe, annual_ends, quarterly_ends
                    )
                    journey_periods.append((slot, metric_id, scopes["annual"]))
                    journey_periods.append((slot, metric_id, scopes["quarterly"]))
                wanted = [
                    period for _slot, _mid, period in journey_periods if period is not None
                ]
                unique_periods = sorted(
                    {period.key: period for period in wanted}.values(),
                    key=lambda item: item.key,
                )
                journey_cells = _query_cells(
                    engine,
                    ticker=ticker,
                    metrics=sorted(set(journey_ids.values())),
                    periods=unique_periods,
                    policy=policy,
                )
                cell_by_key = {
                    (cell.metric_id, cell.period.key): cell for cell in journey_cells
                }
                journeys = []
                for index, (slot, metric_id, period) in enumerate(journey_periods):
                    scope = "annual" if index % 2 == 0 else "quarterly"
                    cell = (
                        cell_by_key.get((metric_id, period.key))
                        if period is not None
                        else None
                    )
                    journeys.append(_journey_row(slot, metric_id, scope, cell, period))
                issuer_out["query_journeys"] = journeys
                # A whole-issuer kernel failure is a FAILED check, not an
                # accepted journey; a per-cell refusal stays a carried fact.
                # <N> is the governed period universe the kernel matrix was
                # queried over.
                checks.add(
                    "kernel_query_engine",
                    ticker,
                    True,
                    f"production query engine built; {len(universe)} matrix periods queried",
                )
            except Exception as exc:  # noqa: BLE001 - a typed kernel refusal is carried
                kernel_error = f"{type(exc).__name__}: {exc}"
                checks.add("kernel_query_engine", ticker, False, kernel_error)
                issuer_out["query_journeys"] = [
                    {
                        "metric": slot,
                        "metric_id": journey_ids.get(slot),
                        "scope": scope,
                        "period": None,
                        "status": "refused",
                        "code": f"query_engine_unavailable ({kernel_error})",
                    }
                    for slot in sorted(dict(JOURNEY_METRIC_LABELS))
                    for scope in ("annual", "quarterly")
                ]
                refusal_causes = {
                    "status": "unavailable",
                    "reason": kernel_error,
                    "total_unlinked_cells": None,
                }
            issuer_out["lineage"] = {
                "receipts": (
                    {
                        "v1_pair": by_version.get("1", 0),
                        "v2_chain": by_version.get("2", 0),
                    }
                    if receipts is not None
                    else {"v1_pair": "unavailable", "v2_chain": "unavailable"}
                ),
                "receipt_count": lineage_receipts_total,
                "refusal_causes": refusal_causes,
            }

            # ---- 7. browser linkage -------------------------------------
            issuer_out["browser_linkage"] = [
                {
                    "path": template["path"].format(ticker=ticker, issuer_id=issuer_id),
                    "method": template["method"],
                    "receipt": "pending",
                }
                for template in BROWSER_LINKAGE_TEMPLATE
            ]

        # ---- 6. no_fixture_substitution (per contract issuer) -----------
        # Every contract issuer answers: fixture locators in its own
        # generation roles/manifest and report rows, EDGAR-shaped accessions,
        # the publisher's lawful outcome/clock_basis pair, and — when a local
        # generation exists — true production provider mode.
        issuer_fixture_problems: list[str] = []
        for hit in _fixture_locator_hits(generation):
            issuer_fixture_problems.append(f"fixture locator in generation {hit}")
        for hit in _report_fixture_hits_for_cik(report, cik):
            issuer_fixture_problems.append(f"fixture locator in {hit}")
        if pub_row is not None:
            bad_accessions = sorted(
                {
                    str(value)
                    for value in (pub_row.get("admitted_accessions") or [])
                    if not _EDGAR_ACCESSION_RE.fullmatch(str(value))
                }
                | {
                    accession
                    for accession in served_accessions_report
                    if not _EDGAR_ACCESSION_RE.fullmatch(accession)
                }
            )
            for value in bad_accessions:
                issuer_fixture_problems.append(
                    f"served accession is not an EDGAR accession: {value}"
                )
            outcome_clock = (str(pub_row.get("outcome")), str(pub_row.get("clock_basis")))
            if outcome_clock not in LAWFUL_OUTCOME_CLOCK_PAIRS:
                issuer_fixture_problems.append(
                    "report outcome/clock_basis pair is outside the publisher vocabulary: "
                    f"{outcome_clock[0]!r}/{outcome_clock[1]!r}"
                )
        if generation is not None:
            if generation.manifest.get("schema") != PRODUCTION_DATASET_SCHEMA:
                issuer_fixture_problems.append(
                    "generation manifest schema is not the production dataset schema: "
                    f"{generation.manifest.get('schema')!r}"
                )
            try:
                delivery = generation.delivery()
            except Exception as exc:  # noqa: BLE001 - a refused delivery is a typed problem
                issuer_fixture_problems.append(
                    f"production delivery refused ({type(exc).__name__})"
                )
            else:
                if delivery.get("kind") != "production_issuer_dataset":
                    issuer_fixture_problems.append(
                        "production delivery kind is not production_issuer_dataset: "
                        f"{delivery.get('kind')!r}"
                    )
                if delivery.get("production_issuer_service") is not True:
                    issuer_fixture_problems.append(
                        "production delivery is not flagged production_issuer_service"
                    )
                if delivery.get("dataset_generation_id") != generation.generation_id:
                    issuer_fixture_problems.append(
                        "production delivery dataset_generation_id differs from the generation"
                    )
        checks.add(
            "no_fixture_substitution",
            ticker,
            not issuer_fixture_problems,
            "; ".join(issuer_fixture_problems)
            or "no tests/fixtures locator; production provider mode and clock basis lawful",
        )

        generation_ran = generation is not None
        coverage_table.append(
            {
                "ticker": ticker,
                "contract": len(contract_accessions),
                "captured": _census_count(cov_row, "captured"),
                "admitted": _census_count(cov_row, "admitted"),
                "served": _census_count(cov_row, "served"),
                # A section that never ran is "unavailable": a fake 0 would
                # claim a census that never happened.
                "statements_served": statements_served if generation_ran else "unavailable",
                "statement_refusals": statement_refusals if generation_ran else "unavailable",
                "lineage_receipts": lineage_receipts_total if generation_ran else "unavailable",
                "lineage_refusals": _lineage_refusals_total(refusal_causes),
                "lineage_refusal_codes": _flat_refusal_codes(refusal_causes),
                "bridge": bridge["status"] or "dropped",
            }
        )
        issuers_out.append(issuer_out)

    issuer_internal_errors = 0
    for issuer_row in contract_issuers:
        issuers_mark = len(issuers_out)
        table_mark = len(coverage_table)
        checks_mark = len(checks.rows)
        try:
            _ledger_issuer(issuer_row)
        except Exception as exc:  # noqa: BLE001 - one issuer's internal error is a FAIL row
            # Every partial output of the failed issuer is cut back, check
            # rows included: a PASS row written before the error would claim
            # a result the issuer entry says is unavailable.
            del issuers_out[issuers_mark:]
            del coverage_table[table_mark:]
            del checks.rows[checks_mark:]
            issuer_internal_errors += 1
            failed_ticker = str(issuer_row.get("ticker") or "") or None
            checks.add(
                "issuer_internal_error",
                failed_ticker,
                False,
                f"issuer ledger stopped at an internal error ({type(exc).__name__}: {exc}); "
                "the remaining issuers were still processed",
            )
            coverage_table.append(
                {
                    "ticker": failed_ticker or "",
                    "contract": "unavailable",
                    "captured": "unavailable",
                    "admitted": "unavailable",
                    "served": "unavailable",
                    "statements_served": "unavailable",
                    "statement_refusals": "unavailable",
                    "lineage_receipts": "unavailable",
                    "lineage_refusals": "unavailable",
                    "lineage_refusal_codes": {},
                    "bridge": "unavailable",
                }
            )
            issuers_out.append(
                {
                    "ticker": failed_ticker or "",
                    "bridge": {
                        "status": "unavailable",
                        "production_generation_id": None,
                        "local_generation_id": None,
                        "production_outcome": None,
                        "production_clock_basis": None,
                        "manifest_key": None,
                    },
                    "basis": None,
                    "query_journeys": [],
                    "lineage": None,
                }
            )
    if contract_issuers and issuer_internal_errors == len(contract_issuers):
        # No issuer was ledgered at all: that is a harness defect, not an
        # ordinary check failure, so the run carries the run-level
        # harness_internal_error row (main exits 3) beside the issuer rows.
        checks.add(
            "harness_internal_error",
            None,
            False,
            f"every contract issuer stopped at an internal error "
            f"({issuer_internal_errors} of {len(contract_issuers)}); "
            "see the issuer_internal_error rows",
        )

    # ---- 6b. report issuers versus the coverage contract -----------------
    contract_ciks = {
        str(row.get("cik") or "")
        for row in contract_issuers
        if str(row.get("cik") or "")
    }
    # (a) one cik cannot be both published and excluded.
    published_ciks = {str(row.get("cik") or "") for row in published_rows}
    excluded_ciks = {str(row.get("cik") or "") for row in excluded_rows}
    for cik_text in sorted(published_ciks & excluded_ciks):
        contract_ticker = next(
            (
                str(row.get("ticker") or "") or None
                for row in contract_issuers
                if str(row.get("cik") or "") == cik_text
            ),
            None,
        )
        checks.add(
            "publish_exclusion_conflict",
            contract_ticker,
            False,
            f"report cik {cik_text} appears in both published[] and excluded[]",
        )
    # (b) every reported cik must be a contract cik; a row without a cik is
    # reported as "(missing)" — equally outside the contract.
    outside_ciks: dict[str, set[str]] = {}
    for section in _REPORT_ROW_SECTIONS:
        for row in _issuer_rows(report.get(section)):
            cik_text = _row_cik_text(row)
            if cik_text in contract_ciks:
                continue
            outside_ciks.setdefault(cik_text, set()).add(section)
    failed_row = _failed_row(report)
    if failed_row is not None:
        cik_text = _row_cik_text(failed_row)
        if cik_text not in contract_ciks:
            outside_ciks.setdefault(cik_text, set()).add("failed")
    for cik_text in sorted(outside_ciks):
        checks.add(
            "report_issuer_outside_contract",
            None,
            False,
            f"report cik {cik_text} in {', '.join(sorted(outside_ciks[cik_text]))} "
            "is outside the coverage contract",
        )

    # ---- 6c. report shape (issuer None) ----------------------------------
    shape_problems: list[str] = []
    if not isinstance(report.get("recorded_at"), str) or not report.get("recorded_at"):
        shape_problems.append("recorded_at is missing")
    if not isinstance(report.get("rule_clocks"), dict) or not report.get("rule_clocks"):
        shape_problems.append("rule_clocks is missing")
    for hit in _unattributed_fixture_hits(report, contract_ciks):
        shape_problems.append(f"fixture locator in {hit}")
    checks.add(
        "production_report_shape",
        None,
        not shape_problems,
        "; ".join(shape_problems)
        or "report recorded_at and rule_clocks present; no unattributed fixture locator",
    )

    document = {
        "schema": LEDGER_SCHEMA,
        "inputs": inputs,
        "checks": checks.rows,
        "issuers": issuers_out,
        "coverage_table": coverage_table,
        "all_checks_passed": checks.all_passed,
    }
    return document


def _census_count(row: Mapping[str, Any] | None, key: str) -> int | str:
    """One coverage census integer, or ``"unavailable"`` when not an integer.

    ``int(... or 0)`` turned a missing census into a claimed 0; a boolean
    (an int subclass) is equally not a census.
    """
    value = (row or {}).get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return "unavailable"
    return value


def _lineage_refusals_total(refusal_causes: Mapping[str, Any] | None) -> int | str:
    """The lineage-refusal census total, or ``"unavailable"`` when never computed.

    A computed histogram always carries ``total_unlinked_cells``.  The
    unavailable object (the kernel half refused) and a generation that never
    loaded carry none — a 0 there would claim a census that never ran.  The
    total must be a real int: ``None`` and ``True`` are both "unavailable".
    """
    if not isinstance(refusal_causes, Mapping) or "histogram" not in refusal_causes:
        return "unavailable"
    total = refusal_causes.get("total_unlinked_cells")
    if isinstance(total, bool) or not isinstance(total, int):
        return "unavailable"
    return total


def _flat_refusal_codes(refusal_causes: Mapping[str, Any] | None) -> dict[str, int]:
    if not refusal_causes:
        return {}
    histogram = refusal_causes.get("histogram") or {}
    out: dict[str, int] = {}
    for code, count in histogram.items():
        if isinstance(count, Mapping):
            for bucket, bucket_count in count.items():
                out[f"{code}.{bucket}"] = bucket_count
        else:
            out[code] = count
    return out


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="fif_a1_journey_ledger",
        description="Build the FIF A1 per-issuer journey + refusal ledger.",
    )
    parser.add_argument("--production-report", required=True)
    parser.add_argument("--store-dir", required=True)
    parser.add_argument("--coverage-file", required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    parser.add_argument("--archive-root")
    return parser.parse_args(list(argv))


def _failure_ledger(check_id: str, detail: str) -> dict[str, Any]:
    """The FAIL ledger a harness-level refusal writes to both out paths."""
    return {
        "schema": LEDGER_SCHEMA,
        "inputs": {},
        "checks": [
            {"id": check_id, "issuer": None, "status": "fail", "detail": detail}
        ],
        "issuers": [],
        "coverage_table": [],
        "all_checks_passed": False,
    }


def _write_outputs(
    args: argparse.Namespace, document: Mapping[str, Any], markdown: str
) -> int | None:
    """Write both out paths; the typed exit (2) when either cannot be written.

    ``None`` means both files were written — the caller owns the exit code.
    The two outputs are a pair: both are staged to same-directory temp files
    and renamed into place only after both writes succeed, and any failure
    removes every staged and already-renamed file, so a half pair never
    survives.  An unencodable payload (a lone surrogate is a
    ``UnicodeEncodeError``, a ``ValueError``) or an unserialisable document
    (``TypeError`` from ``json.dumps``) is the same typed exit, never a
    traceback that leaves a temp file behind.
    """
    staged: list[Path] = []
    published: list[Path] = []
    target = Path(args.out_json)
    try:
        pairs = [
            (
                target,
                json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            ),
            (Path(args.out_md), markdown),
        ]
        temps: list[tuple[Path, Path]] = []
        # Phase 1 (stage): write each payload next to its target.
        for target, payload in pairs:
            if target.parent and not target.parent.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
            temp = target.with_name(f".{target.name}.partial-{os.getpid()}")
            staged.append(temp)
            temp.write_text(payload, encoding="utf-8")
            temps.append((temp, target))
        # Phase 2 (publish): rename only after BOTH temps are written.
        for temp, target in temps:
            os.replace(temp, target)
            published.append(target)
    except (OSError, ValueError, TypeError) as exc:
        for leftover in (*staged, *published):
            try:
                leftover.unlink(missing_ok=True)
            except OSError:
                pass
        reason = getattr(exc, "strerror", None) or type(exc).__name__
        print(
            f"fif_a1_journey_ledger: output is unwritable: {target.name} ({reason})",
            file=sys.stderr,
            flush=True,
        )
        return 2
    return None


def _refuse_shared_out_path(out_json: str, out_md: str) -> None:
    """The typed usage refusal when both out paths name one file.

    One file cannot hold the pair: the staged write would publish one output
    and lose the other, and the stale-output unlink below would delete the
    only copy.  The same file is the same resolved path (``..`` segments and
    symlinks included) or, when both exist, the same inode (a hard link or a
    case-insensitive alias).
    """
    first, second = Path(out_json), Path(out_md)
    try:
        same = first.resolve() == second.resolve()
    except (OSError, RuntimeError):
        same = os.path.abspath(out_json) == os.path.abspath(out_md)
    if not same:
        try:
            same = os.path.samefile(first, second)
        except OSError:
            same = False
    if same:
        raise _UsageError(f"--out-json and --out-md name the same file: {second.name}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        _refuse_shared_out_path(args.out_json, args.out_md)
    except _UsageError as exc:
        # Refused before any delete or input read: no ledger is written (one
        # file cannot hold the pair) and the existing file is left untouched.
        print(f"fif_a1_journey_ledger: {exc}", file=sys.stderr, flush=True)
        return 2
    # Stale output never survives into this run: both out paths are unlinked
    # before any input is read, so a later refusal cannot leave the previous
    # run's bytes in place.
    for path_text in (args.out_json, args.out_md):
        try:
            Path(path_text).unlink(missing_ok=True)
        except OSError as exc:
            print(
                f"fif_a1_journey_ledger: output is unwritable: {Path(path_text).name} "
                f"({exc.strerror})",
                file=sys.stderr,
                flush=True,
            )
            return 2
    try:
        report = _read_json_file(args.production_report, kind="production report")
        if report.get("schema") != PUBLISH_REPORT_SCHEMA:
            raise _UsageError(
                f"production report schema is unsupported: {report.get('schema')!r}"
            )
        contract = _read_json_file(args.coverage_file, kind="coverage contract")
        if contract.get("schema") != COVERAGE_CONTRACT_SCHEMA:
            raise _UsageError(
                f"coverage contract schema is unsupported: {contract.get('schema')!r}"
            )
        if not isinstance(contract.get("issuers"), list) or not contract["issuers"]:
            raise _UsageError(f"coverage contract has no issuers: {contract['__input_basename__']}")
        store_dir = Path(args.store_dir)
        if not store_dir.is_dir():
            raise _UsageError(f"store directory does not exist: {store_dir.name}")
        archive_root = None
        if args.archive_root:
            archive_root = Path(args.archive_root)
            if not archive_root.is_dir():
                raise _UsageError(f"archive root does not exist: {archive_root.name}")
        document = build_ledger(
            report=report,
            contract=contract,
            store_dir=store_dir,
            archive_root=archive_root,
        )
        markdown = _render_markdown(document)
    except _UsageError as exc:
        # An input/usage error is still a ledger: the FAIL row names the
        # refused input, and both out paths carry it (exit 2).
        document = _failure_ledger("harness_input", str(exc))
        print(f"fif_a1_journey_ledger: {exc}", file=sys.stderr, flush=True)
        status = _write_outputs(args, document, _render_markdown(document))
        return 2 if status is None else status
    except Exception as exc:  # noqa: BLE001 - an internal error is a typed ledger, never a traceback
        detail = f"{type(exc).__name__}: {exc}"
        document = _failure_ledger("harness_internal_error", detail)
        print(
            f"fif_a1_journey_ledger: internal error: {detail}",
            file=sys.stderr,
            flush=True,
        )
        status = _write_outputs(args, document, _render_markdown(document))
        return 3 if status is None else status

    # Every contract issuer stopping at an internal error is a harness defect:
    # build_ledger then carries the run-level harness_internal_error row, and
    # the run exits 3 (never the ordinary check-failure exit 1).
    internal = next(
        (row for row in document["checks"] if row["id"] == "harness_internal_error"),
        None,
    )
    if internal is not None:
        print(
            f"fif_a1_journey_ledger: internal error: {internal['detail']}",
            file=sys.stderr,
            flush=True,
        )
    written = _write_outputs(args, document, markdown)
    if written is not None:
        return written
    if internal is not None:
        return 3
    return 0 if document["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
