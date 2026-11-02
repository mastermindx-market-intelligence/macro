#!/usr/bin/env python3
"""Acceptance-report generator for the Prophet B23 latency lab (BU5).

Turns lab capture manifests (``scripts/capture_page_evidence.py``, schema
``mastermind.p0_evidence.v2``, whose per-state ``timing`` block carries
``lcp_ms`` / ``cls`` / ``inp_proxy_ms`` / ``resource_count`` /
``transfer_bytes`` / ``server_timing`` under a manifest-wide
``timing_basis: "lab"``) plus lab-server request journals
(``scripts/prophet_journey_lab_serve.py``) into ``b23_latency_report.json`` and
a markdown summary, against the declarative matrix in
``config/prophet_journey_latency.yml``. Nothing consumes the PASS/FAIL until
decision D11 accepts the shape; this tool computes and never decides.

Contract
--------
1. **Lab basis is named, never implied.** Every metric block carries
   ``basis: "lab"`` and its sample count ``n``; the labels are ``lab_p75_*``
   and are never called field. Field metrics have no wire yet: the report says
   ``field: "BLOCKED_ON_D11"`` rather than omitting or imputing them. A
   manifest whose ``timing_basis`` is not ``"lab"`` is refused outright.
2. **Insufficient is reported, never smoothed over.** A cell metric with fewer
   samples than the spec requires reports ``INSUFFICIENT_SAMPLES`` with the
   observed ``n`` and ``null_count`` — never a p75. A null timing value is
   excluded and counted, never treated as 0.
3. **p75 is nearest-rank** — ``rank = ceil(0.75 * n)``, 1-based, on the
   ascending sorted samples — and the report says so. No interpolation, no
   averaging across cells.
4. **Gaps stay gaps.** A cell recorded as a gap (a manifest axis gap, a route
   no manifest carries, or a cell with no captured load) is verdict ``GAP`` and
   is never ``PASS``. Failure classes are counted against a budget of zero and
   never averaged away: a 5xx anywhere fails the run's failure tally even when
   every percentile passes.
5. **A load that did not complete is a failure, not a sample.** Only captured
   states (``force_state`` null — forced shots are presentation evidence, and
   rest-cell statistics are the design's cold loads) contribute samples. A
   not-captured state counts in the capture-fidelity failure class; timing
   harvested from it stays in the manifest, out of the distribution.
6. **Deterministic bytes.** The JSON is ``json.dumps(..., sort_keys=True)`` of
   a dict that contains no wall-clock read anywhere: run time is an explicit
   ``--run-time`` argument, inputs are ordered by path, and the same inputs
   produce byte-identical output.
7. **No budget is invented.** ``resource_count`` / ``transfer_bytes`` report
   per-load values plus max and no verdict — the first run is the baseline,
   later runs diff it. Server-held time is a distribution flagged
   ``EDGE_TIMEOUT_RISK`` past the incumbent tool timeout; no number is minted.

Usage::

    python3 scripts/prophet_journey_latency_report.py \\
        --spec config/prophet_journey_latency.yml \\
        --manifest run1/p0_evidence_manifest.json --manifest run2/... \\
        --journal run1/journal.jsonl \\
        --run-time 2026-10-21T09:00:00Z \\
        --out-report run/b23_latency_report.json \\
        --out-summary run/b23_latency_report.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

MODULE_REF = "scripts/prophet_journey_latency_report.py"
TOOL_VERSION = "1.0.0"
REPORT_SCHEMA = "mastermind.b23_latency_report.v1"
SPEC_SCHEMA = "mastermind.prophet_journey_latency_spec.v1"
MANIFEST_SCHEMA = "mastermind.p0_evidence.v2"

BASIS_LAB = "lab"
FIELD_STATUS = "BLOCKED_ON_D11"
TIMING_BASIS_KEY = "timing_basis"

VERDICT_PASS = "PASS"
VERDICT_FAIL = "FAIL"
VERDICT_INSUFFICIENT = "INSUFFICIENT_SAMPLES"
VERDICT_GAP = "GAP"
# Closed verdict set, worst first.
VERDICT_ORDER: tuple[str, ...] = (
    VERDICT_FAIL,
    VERDICT_INSUFFICIENT,
    VERDICT_GAP,
    VERDICT_PASS,
)

BUDGETED_STATISTICS: tuple[str, ...] = ("lcp", "cls", "inp")
UNBUDGETED_STATISTICS: tuple[str, ...] = ("resource_count", "transfer_bytes")
ALL_STATISTICS: tuple[str, ...] = BUDGETED_STATISTICS + UNBUDGETED_STATISTICS
BUDGET_KEY: Mapping[str, str] = {
    "lcp": "p75_max_ms",
    "cls": "p75_max",
    "inp": "p75_max_ms",
}

EXIT_OK = 0
EXIT_USAGE = 2

# The frozen journal line shape of scripts/prophet_journey_lab_serve.py.
JOURNAL_KEYS: tuple[str, ...] = (
    "bytes",
    "elapsed_ms",
    "method",
    "path",
    "seq",
    "sha256",
    "status",
)


class SpecError(ValueError):
    """The spec, a manifest, or a journal does not match what this tool consumes."""


# ---------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------


def nearest_rank_percentile(sorted_values: Sequence[float], q: float) -> float:
    """Nearest-rank percentile: rank = ceil(q * n), 1-based, on sorted values."""

    n = len(sorted_values)
    if n == 0:
        raise ValueError("nearest_rank_percentile of an empty sample")
    rank = min(max(1, math.ceil(q * n)), n)
    return sorted_values[rank - 1]


def p75_nearest_rank(values: Sequence[float]) -> float:
    """p75 by nearest rank — the one method the report names and tests."""

    return nearest_rank_percentile(sorted(values), 0.75)


# ---------------------------------------------------------------------------
# input loading
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_str_list(values: object) -> bool:
    return isinstance(values, Sequence) and not isinstance(values, (str, bytes)) and len(values) > 0


def load_spec(path: Path | str) -> dict[str, Any]:
    """Load and check the declarative journey/matrix spec."""

    spec_path = Path(path)
    try:
        raw = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SpecError(f"spec not found: {spec_path}") from exc
    except yaml.YAMLError as exc:
        raise SpecError(f"spec is not parseable YAML: {spec_path}: {exc}") from exc
    if not isinstance(raw, Mapping):
        raise SpecError(f"spec must be a mapping: {spec_path}")
    if raw.get("schema") != SPEC_SCHEMA:
        raise SpecError(f"spec schema {raw.get('schema')!r} != {SPEC_SCHEMA!r}")

    matrix = raw.get("matrix")
    if not isinstance(matrix, Mapping):
        raise SpecError("spec.matrix missing")
    for axis in ("widths", "locales", "themes"):
        if not _is_str_list(matrix.get(axis)):
            raise SpecError(f"spec.matrix.{axis} must be a non-empty list")

    journeys = raw.get("journeys")
    if not _is_str_list(journeys):
        raise SpecError("spec.journeys must be a non-empty list")
    for journey in journeys:
        if not isinstance(journey, Mapping) or not journey.get("name"):
            raise SpecError("every journey needs a name")
        steps = journey.get("steps")
        if not _is_str_list(steps):
            raise SpecError(f"journey {journey.get('name')!r} needs a non-empty steps list")
        for step in steps:
            if not isinstance(step, Mapping) or not step.get("name") or not step.get("route"):
                raise SpecError(f"journey {journey.get('name')!r} step needs name + route")
            for interaction in step.get("interactions") or ():
                if not isinstance(interaction, Mapping) or not interaction.get("name"):
                    raise SpecError(f"step {step.get('name')!r} interaction needs a name")
                reps = interaction.get("reps")
                if not isinstance(reps, int) or isinstance(reps, bool) or reps < 1:
                    raise SpecError(
                        f"interaction {interaction.get('name')!r} reps must be a positive int"
                    )

    statistics = raw.get("statistics")
    if not isinstance(statistics, Mapping):
        raise SpecError("spec.statistics missing")
    for stat in BUDGETED_STATISTICS:
        entry = statistics.get(stat)
        if not isinstance(entry, Mapping):
            raise SpecError(f"spec.statistics.{stat} missing")
        if not isinstance(entry.get("manifest_key"), str):
            raise SpecError(f"spec.statistics.{stat}.manifest_key missing")
        required_n = entry.get("required_n")
        if not isinstance(required_n, int) or isinstance(required_n, bool) or required_n < 1:
            raise SpecError(f"spec.statistics.{stat}.required_n must be a positive int")
        budget = entry.get("budget")
        if not isinstance(budget, Mapping) or BUDGET_KEY[stat] not in budget:
            raise SpecError(f"spec.statistics.{stat}.budget.{BUDGET_KEY[stat]} missing")
        if not isinstance(entry.get("label"), str) or not entry["label"]:
            raise SpecError(f"spec.statistics.{stat}.label missing")
    for stat in UNBUDGETED_STATISTICS:
        entry = statistics.get(stat)
        if not isinstance(entry, Mapping) or not isinstance(entry.get("manifest_key"), str):
            raise SpecError(f"spec.statistics.{stat} missing manifest_key")
        if entry.get("budget") is not None:
            raise SpecError(
                f"spec.statistics.{stat} must declare no budget (null); "
                "the first run is the baseline"
            )

    timeout_s = raw.get("tool_timeout_s")
    if not isinstance(timeout_s, (int, float)) or isinstance(timeout_s, bool) or timeout_s <= 0:
        raise SpecError("spec.tool_timeout_s must be a positive number")
    if not isinstance(raw.get("tool_timeout_source"), str) or not raw["tool_timeout_source"]:
        raise SpecError("spec.tool_timeout_source missing (the timeout constant names its source)")

    return dict(raw)


def load_manifest(path: Path | str) -> dict[str, Any]:
    """Load one capture manifest and refuse anything that is not lab-basis v2."""

    manifest_path = Path(path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SpecError(f"manifest not found: {manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise SpecError(f"manifest is not parseable JSON: {manifest_path}: {exc}") from exc
    if not isinstance(manifest, Mapping):
        raise SpecError(f"manifest must be a mapping: {manifest_path}")
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise SpecError(
            f"manifest schema {manifest.get('schema')!r} != {MANIFEST_SCHEMA!r}: {manifest_path}"
        )
    if manifest.get(TIMING_BASIS_KEY) != BASIS_LAB:
        raise SpecError(
            f"manifest {TIMING_BASIS_KEY} is {manifest.get(TIMING_BASIS_KEY)!r}, not "
            f"{BASIS_LAB!r}: {manifest_path}"
        )
    return manifest


def load_journal(path: Path | str) -> list[dict[str, Any]]:
    """Load one lab-server jsonl journal; every line must carry the frozen keys."""

    journal_path = Path(path)
    try:
        text = journal_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SpecError(f"journal not found: {journal_path}") from exc
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SpecError(f"journal line {number} is not JSON: {journal_path}: {exc}") from exc
        missing = [key for key in JOURNAL_KEYS if key not in row]
        if missing:
            raise SpecError(f"journal line {number} lacks {missing}: {journal_path}")
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# cell collection
# ---------------------------------------------------------------------------


def _steps_by_route(spec: Mapping[str, Any]) -> dict[str, list[tuple[str, str]]]:
    """Route -> [(journey, step)]; two journeys may legitimately share a route."""

    steps: dict[str, list[tuple[str, str]]] = {}
    for journey in spec["journeys"]:
        for step in journey["steps"]:
            steps.setdefault(step["route"], []).append((journey["name"], step["name"]))
    return steps


def _declared_routes(spec: Mapping[str, Any]) -> set[str]:
    return {step["route"] for journey in spec["journeys"] for step in journey["steps"]}


class CellAccumulator:
    """Per-cell sample bookkeeping across every manifest, honestly."""

    def __init__(self, spec: Mapping[str, Any]) -> None:
        self.spec = spec
        self.matrix = spec["matrix"]
        self.statistics = spec["statistics"]
        self.samples: dict[tuple[Any, ...], dict[str, list[float]]] = {}
        self.null_counts: dict[tuple[Any, ...], dict[str, int]] = {}
        self.gap_reasons: dict[tuple[Any, ...], list[str]] = {}
        self.capture_failures: list[dict[str, Any]] = []
        self.out_of_matrix_loads = 0
        self.forced_state_loads_excluded = 0
        self.console_errors = 0
        self.failed_responses: list[dict[str, Any]] = []
        self.fidelity_gap_rows = 0

    @staticmethod
    def key(journey: str, step: str, width: int, locale: str, theme: str) -> tuple[Any, ...]:
        return (journey, step, int(width), locale, theme)

    def ensure(self, key: tuple[Any, ...]) -> None:
        if key not in self.samples:
            self.samples[key] = {stat: [] for stat in ALL_STATISTICS}
            self.null_counts[key] = {stat: 0 for stat in ALL_STATISTICS}
            self.gap_reasons[key] = []

    def record_gap(self, key: tuple[Any, ...], reason: str) -> None:
        self.ensure(key)
        if reason not in self.gap_reasons[key]:
            self.gap_reasons[key].append(reason)

    def add_manifest(self, manifest: Mapping[str, Any], manifest_path: Path) -> None:
        steps_by_route = _steps_by_route(self.spec)

        for page in manifest.get("pages") or []:
            route = str(page.get("route") or "")
            pairs = steps_by_route.get(route, ())
            self.console_errors += len(page.get("console_errors") or [])
            for failure in page.get("failed_responses") or []:
                self.failed_responses.append(
                    {
                        "route": route,
                        "url": str(failure.get("url") or ""),
                        "status": int(failure.get("status") or 0),
                        "manifest": manifest_path.name,
                    }
                )
            for gap in page.get("gaps") or []:
                if gap.get("dimension") in ("state_application", "force_state_application"):
                    self.fidelity_gap_rows += 1

            if not pairs:
                continue  # out-of-journey pages are reported at input level

            axis_gaps = [
                gap
                for gap in (page.get("gaps") or [])
                if gap.get("dimension") in ("locale", "theme")
            ]
            for state in page.get("states") or []:
                if state.get("force_state") is not None:
                    # Forced shots are presentation evidence, never cold loads.
                    self.forced_state_loads_excluded += 1
                    continue
                width = state.get("viewport_width")
                locale = state.get("locale")
                theme = state.get("theme")
                if (
                    width not in self.matrix["widths"]
                    or locale not in self.matrix["locales"]
                    or theme not in self.matrix["themes"]
                ):
                    self.out_of_matrix_loads += 1
                    for journey_name, step_name in pairs:
                        self.record_gap(
                            self.key(journey_name, step_name, width, locale, theme),
                            f"load outside the declared matrix: width={width!r} "
                            f"locale={locale!r} theme={theme!r}",
                        )
                    continue

                for journey_name, step_name in pairs:
                    key = self.key(journey_name, step_name, width, locale, theme)
                    self.ensure(key)
                    # A registry-declared axis exclusion covers the cell before
                    # any load is considered: the manifest says this page was
                    # never meant to be captured here, and a recorded gap stays
                    # a gap even if a contradictory load exists.
                    for gap in axis_gaps:
                        if gap.get("value") in (locale, theme):
                            self.record_gap(
                                key,
                                f"manifest axis gap ({gap.get('dimension')}={gap.get('value')}): "
                                f"{gap.get('reason')}",
                            )
                    if not state.get("captured"):
                        self.capture_failures.append(
                            {
                                "route": route,
                                "width": width,
                                "locale": locale,
                                "theme": theme,
                                "reason": str(state.get("reason") or "captured: false"),
                                "manifest": manifest_path.name,
                            }
                        )
                        continue
                    timing = state.get("timing") or {}
                    for stat in ALL_STATISTICS:
                        value = timing.get(self.statistics[stat]["manifest_key"])
                        if value is None:
                            self.null_counts[key][stat] += 1
                        else:
                            self.samples[key][stat].append(value)

    def finish_gaps(self) -> None:
        """Every declared cell with no captured load anywhere stays a gap."""

        for journey in self.spec["journeys"]:
            for step in journey["steps"]:
                for width in self.matrix["widths"]:
                    for locale in self.matrix["locales"]:
                        for theme in self.matrix["themes"]:
                            key = self.key(journey["name"], step["name"], width, locale, theme)
                            self.ensure(key)
                            if not any(self.samples[key].values()):
                                if not self.gap_reasons[key]:
                                    self.gap_reasons[key].append(
                                        f"no captured load for route {step['route']} at this "
                                        "cell in any manifest"
                                    )


# ---------------------------------------------------------------------------
# report assembly
# ---------------------------------------------------------------------------


def _metric_block(
    *,
    stat: str,
    samples: Sequence[float],
    null_count: int,
    required_n: int | None,
    budget: float | None,
    gap: bool,
) -> dict[str, Any]:
    block: dict[str, Any] = {
        "basis": BASIS_LAB,
        "n": len(samples),
        "null_count": null_count,
        "p75": None,
    }
    if stat not in BUDGETED_STATISTICS:
        # Unbudgeted: per-load values + max, no verdict, first run is baseline.
        block.update(
            {
                "required_n": None,
                "budget": None,
                "verdict": None,
                "values": list(samples),
                "max": max(samples) if samples else None,
            }
        )
        return block
    block["required_n"] = required_n
    block["budget"] = budget
    if gap:
        block["verdict"] = VERDICT_GAP
        return block
    if len(samples) < int(required_n or 0):
        block["verdict"] = VERDICT_INSUFFICIENT
        return block
    p75 = p75_nearest_rank(samples)
    block["p75"] = p75
    block["verdict"] = VERDICT_PASS if p75 <= float(budget) else VERDICT_FAIL
    return block


def _worst_verdict(verdicts: Sequence[str | None]) -> str:
    ranked = [VERDICT_ORDER.index(v) for v in verdicts if v is not None]
    return VERDICT_ORDER[min(ranked)] if ranked else VERDICT_PASS


def build_cells(
    accumulator: CellAccumulator, spec: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], int]:
    cells: list[dict[str, Any]] = []
    gap_cell_count = 0
    for journey in spec["journeys"]:
        for step in journey["steps"]:
            for width in spec["matrix"]["widths"]:
                for locale in spec["matrix"]["locales"]:
                    for theme in spec["matrix"]["themes"]:
                        key = accumulator.key(
                            journey["name"], step["name"], width, locale, theme
                        )
                        reasons = accumulator.gap_reasons.get(key) or []
                        captured_any = any(accumulator.samples[key].values())
                        gap = bool(reasons) or not captured_any
                        metrics: dict[str, Any] = {}
                        for stat in ALL_STATISTICS:
                            entry = spec["statistics"][stat]
                            metrics[entry["label"]] = _metric_block(
                                stat=stat,
                                samples=accumulator.samples[key][stat],
                                null_count=accumulator.null_counts[key][stat],
                                required_n=entry.get("required_n"),
                                budget=(
                                    entry["budget"].get(BUDGET_KEY[stat])
                                    if stat in BUDGETED_STATISTICS
                                    else None
                                ),
                                gap=gap,
                            )
                        cell: dict[str, Any] = {
                            "journey": journey["name"],
                            "step": step["name"],
                            "route": step["route"],
                            "width": int(width),
                            "locale": locale,
                            "theme": theme,
                            "basis": BASIS_LAB,
                            "verdict": _worst_verdict(
                                [m["verdict"] for m in metrics.values()]
                            ),
                            "metrics": metrics,
                        }
                        if gap:
                            gap_cell_count += 1
                            cell["gap_reasons"] = sorted(set(reasons))
                        cells.append(cell)
    cells.sort(
        key=lambda c: (c["journey"], c["step"], c["width"], c["locale"], c["theme"])
    )
    return cells, gap_cell_count


def _server_routes(
    journals: Sequence[Mapping[str, Any]], tool_timeout_s: float
) -> list[dict[str, Any]]:
    by_route: dict[str, list[Mapping[str, Any]]] = {}
    for journal in journals:
        for row in journal["rows"]:
            by_route.setdefault(str(row.get("path") or ""), []).append(row)
    timeout_ms = float(tool_timeout_s) * 1000.0
    routes: list[dict[str, Any]] = []
    for route in sorted(by_route):
        rows = by_route[route]
        elapsed = sorted(float(r.get("elapsed_ms") or 0.0) for r in rows)
        statuses: dict[str, int] = {}
        for row in rows:
            key = str(row.get("status"))
            statuses[key] = statuses.get(key, 0) + 1
        over = [value for value in elapsed if value > timeout_ms]
        routes.append(
            {
                "route": route,
                "n": len(rows),
                "elapsed_ms": {
                    "min": elapsed[0],
                    "p50": nearest_rank_percentile(elapsed, 0.50),
                    "p75": nearest_rank_percentile(elapsed, 0.75),
                    "max": elapsed[-1],
                },
                "statuses": statuses,
                "over_timeout_count": len(over),
                "status_5xx_count": sum(
                    1 for r in rows if int(r.get("status") or 0) >= 500
                ),
                "edge_timeout_risk": bool(over),
            }
        )
    return routes


def _failure_classes(
    *,
    spec: Mapping[str, Any],
    journals: Sequence[Mapping[str, Any]],
    server_routes: Sequence[Mapping[str, Any]],
    accumulator: CellAccumulator,
    gap_cell_count: int,
) -> list[dict[str, Any]]:
    journal_5xx = sum(route["status_5xx_count"] for route in server_routes)
    journal_over_timeout = sum(route["over_timeout_count"] for route in server_routes)
    manifest_5xx = sum(1 for f in accumulator.failed_responses if f["status"] >= 500)
    manifest_401_403 = sum(
        1 for f in accumulator.failed_responses if f["status"] in (401, 403)
    )
    gated = set(spec.get("gated_routes") or ())
    gated_200 = sum(
        1
        for journal in journals
        for row in journal["rows"]
        if str(row.get("path") or "") in gated and int(row.get("status") or 0) == 200
    )

    return [
        {
            "id": "server_error_or_over_timeout",
            "description": (
                "5xx responses, or a response whose server-held time exceeds the "
                "incumbent tool timeout"
            ),
            "budget": 0,
            "count": journal_5xx + journal_over_timeout + manifest_5xx,
            "breakdown": {
                "journal_status_5xx": journal_5xx,
                "journal_over_timeout": journal_over_timeout,
                "manifest_failed_responses_5xx": manifest_5xx,
            },
        },
        {
            "id": "auth_plane_leak_or_denial",
            "description": (
                "401/403 on an entitled route inside an authenticated run, or 200 on "
                "a gated plane inside an anonymous run"
            ),
            "budget": 0,
            "count": manifest_401_403 + gated_200,
            "breakdown": {
                "manifest_failed_responses_401_403": manifest_401_403,
                "journal_200_on_declared_gated_route": gated_200,
            },
            "note": (
                "no gated routes are declared in the spec; the anonymous static build "
                "serves no gated plane by construction"
                if not gated
                else "gated routes declared in the spec are checked against journal 200s"
            ),
        },
        {
            "id": "console_errors_or_failed_responses",
            "description": "console errors and failed (4xx/5xx) responses the pages observed",
            "budget": 0,
            "count": accumulator.console_errors + len(accumulator.failed_responses),
            "breakdown": {
                "console_errors": accumulator.console_errors,
                "failed_responses": len(accumulator.failed_responses),
            },
        },
        {
            "id": "interaction_never_settled",
            "description": "named interactions that never settle within the journey run",
            "budget": 0,
            "count": 0,
            "note": (
                "the B23 journey-runner unit owns this evidence; capture manifests "
                "carry no interaction-settle records, so the count is 0 from this "
                "source and never assumed"
            ),
        },
        {
            "id": "capture_fidelity_failures",
            "description": (
                "states that failed to capture, or captured a state other than the "
                "one requested"
            ),
            "budget": 0,
            "count": len(accumulator.capture_failures) + accumulator.fidelity_gap_rows,
            "breakdown": {
                "states_not_captured": len(accumulator.capture_failures),
                "state_application_gap_rows": accumulator.fidelity_gap_rows,
            },
        },
        {
            "id": "gated_asset_without_no_store",
            "description": "gated assets served without Cache-Control: no-store",
            "budget": 0,
            "count": 0,
            "note": (
                "no gated plane is served by the anonymous lab leg, and the lab "
                "server sets no-store on every response (asserted by "
                "tests/test_prophet_journey_lab_serve.py); per-response headers are "
                "not journaled, so this is a construction fact, not a measured zero"
            ),
        },
        {
            "id": "resource_envelope_exceeded",
            "description": "request count or transferred bytes beyond the declared envelope",
            "budget": 0,
            "count": 0,
            "note": (
                "no envelope is declared; the first run is the baseline and later "
                "runs diff the per-load resource_count/transfer_bytes values this "
                "report carries"
            ),
        },
        {
            "id": "recorded_gap_cells",
            "description": "cells recorded as gaps; a gap stays a gap and is never PASS",
            "budget": 0,
            "count": gap_cell_count,
        },
    ]


def build_report(
    *,
    spec: Mapping[str, Any],
    spec_path: Path,
    manifest_paths: Sequence[Path],
    journal_paths: Sequence[Path],
    run_time: str,
) -> dict[str, Any]:
    """Assemble the whole report dict. Pure: no clock, no network, no writes."""

    manifests = [(path, load_manifest(path)) for path in sorted(manifest_paths)]
    journals = [
        {"path": str(path), "sha256": _sha256_file(path), "rows": load_journal(path)}
        for path in sorted(journal_paths)
    ]

    accumulator = CellAccumulator(spec)
    out_of_journey: set[str] = set()
    declared_routes = _declared_routes(spec)
    for path, manifest in manifests:
        accumulator.add_manifest(manifest, path)
        for page in manifest.get("pages") or []:
            route = str(page.get("route") or "")
            if route not in declared_routes:
                out_of_journey.add(route)
    accumulator.finish_gaps()

    cells, gap_cell_count = build_cells(accumulator, spec)
    server_routes = _server_routes(journals, spec["tool_timeout_s"])
    failure_classes = _failure_classes(
        spec=spec,
        journals=journals,
        server_routes=server_routes,
        accumulator=accumulator,
        gap_cell_count=gap_cell_count,
    )

    by_verdict: dict[str, int] = {verdict: 0 for verdict in VERDICT_ORDER}
    for cell in cells:
        by_verdict[cell["verdict"]] += 1

    overall = VERDICT_PASS
    if any(entry["count"] > 0 for entry in failure_classes) or by_verdict[VERDICT_FAIL]:
        overall = VERDICT_FAIL
    elif by_verdict[VERDICT_INSUFFICIENT]:
        overall = VERDICT_INSUFFICIENT
    elif by_verdict[VERDICT_GAP]:
        overall = VERDICT_GAP

    return {
        "schema": REPORT_SCHEMA,
        "tool": {"module_ref": MODULE_REF, "version": TOOL_VERSION},
        "run_time": run_time,
        "basis": BASIS_LAB,
        "field": FIELD_STATUS,
        "method": {
            "percentile": "nearest_rank",
            "rank": "ceil(0.75 * n), 1-based, on ascending sorted samples",
            "labels": "every timing statistic is lab (lab_p75_*); no field value exists",
            "inp_proxy": (
                "inp_proxy_ms is the per-load max of the driver's scripted interactions; "
                "p75(max) <= budget implies every interaction's p75 <= budget, and "
                "per-interaction attribution arrives with the B23 journey-runner unit"
            ),
            "samples": (
                "only captured rest states (force_state null) are samples; a null timing "
                "value is excluded and counted, never 0"
            ),
        },
        "spec": {
            "path": str(spec_path),
            "sha256": _sha256_file(spec_path),
            "schema": spec["schema"],
            "budgets": {
                stat: spec["statistics"][stat]["budget"] for stat in BUDGETED_STATISTICS
            },
            "required_n": {
                stat: spec["statistics"][stat]["required_n"] for stat in BUDGETED_STATISTICS
            },
            "labels": {
                stat: spec["statistics"][stat]["label"] for stat in ALL_STATISTICS
            },
        },
        # matrix is echoed so the report is self-describing; mapping keys are
        # normalized to strings because YAML parses bare numerals as ints and
        # sorted-key JSON would otherwise order an int-keyed dict differently
        # than its own round trip (canonical bytes, FROZEN SPEC 5).
        "matrix": {
            **{k: v for k, v in spec["matrix"].items() if k != "viewport_keys"},
            "viewport_keys": {
                str(k): str(v)
                for k, v in (spec["matrix"].get("viewport_keys") or {}).items()
            },
        },
        "journeys": [
            {
                "name": journey["name"],
                "steps": [
                    {
                        "name": step["name"],
                        "route": step["route"],
                        "interactions": [
                            {"name": i["name"], "reps": i["reps"]}
                            for i in step.get("interactions") or ()
                        ],
                    }
                    for step in journey["steps"]
                ],
            }
            for journey in spec["journeys"]
        ],
        "inputs": {
            "manifests": [
                {
                    "path": str(path),
                    "sha256": _sha256_file(path),
                    TIMING_BASIS_KEY: BASIS_LAB,
                }
                for path, _ in manifests
            ],
            "journals": [
                {
                    "path": journal["path"],
                    "sha256": journal["sha256"],
                    "lines": len(journal["rows"]),
                }
                for journal in journals
            ],
            "out_of_journey_routes": sorted(out_of_journey),
            "out_of_matrix_loads": accumulator.out_of_matrix_loads,
            "forced_state_loads_excluded": accumulator.forced_state_loads_excluded,
        },
        "server": {
            "basis": BASIS_LAB,
            "tool_timeout_s": spec["tool_timeout_s"],
            "tool_timeout_source": spec["tool_timeout_source"],
            "routes": server_routes,
        },
        "failure_classes": failure_classes,
        "totals": {
            "cells": len(cells),
            "by_verdict": by_verdict,
            "manifests": len(manifests),
            "journal_lines": sum(len(j["rows"]) for j in journals),
        },
        "overall_verdict": overall,
        "cells": cells,
    }


def report_bytes(report: Mapping[str, Any]) -> bytes:
    """Deterministic serialization: sorted keys, no clock, trailing newline."""

    return (json.dumps(report, sort_keys=True, indent=2) + "\n").encode("utf-8")


# ---------------------------------------------------------------------------
# markdown summary
# ---------------------------------------------------------------------------


def _fmt_number(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _fmt_budget(budget: Mapping[str, Any]) -> str:
    if "p75_max_ms" in budget:
        return f"p75 <= {budget['p75_max_ms']} ms"
    return f"p75 <= {budget['p75_max']}"


def _cell_value(block: Mapping[str, Any]) -> str:
    if block.get("verdict") == VERDICT_GAP:
        return "GAP"
    if block.get("verdict") == VERDICT_INSUFFICIENT:
        return f"INSUFFICIENT (n={block.get('n')}, nulls={block.get('null_count')})"
    return _fmt_number(block.get("p75"))


def render_markdown(report: Mapping[str, Any]) -> str:
    """A summary of the report — the JSON is canonical, this is the readable face."""

    lines: list[str] = []
    lines.append("# Prophet B23 latency report (lab)")
    lines.append("")
    lines.append(f"- run time: {report['run_time']}")
    lines.append(f"- overall: **{report['overall_verdict']}** (budget verdicts per cell)")
    verdicts = report["totals"]["by_verdict"]
    lines.append(
        "- cells: {cells} — PASS {p} / FAIL {f} / INSUFFICIENT_SAMPLES {i} / GAP {g}".format(
            cells=report["totals"]["cells"],
            p=verdicts[VERDICT_PASS],
            f=verdicts[VERDICT_FAIL],
            i=verdicts[VERDICT_INSUFFICIENT],
            g=verdicts[VERDICT_GAP],
        )
    )
    lines.append(f"- basis: {report['basis']} (every statistic is lab; labels are lab_p75_*)")
    lines.append(f"- field: **{report['field']}** — no field wire exists; nothing is imputed")
    lines.append(f"- method: p75 by {report['method']['percentile']} ({report['method']['rank']})")
    lines.append(
        f"- inputs: {report['totals']['manifests']} manifests, "
        f"{report['totals']['journal_lines']} journal lines"
    )
    lines.append("")

    lines.append("## Budgets (per cell)")
    lines.append("")
    lines.append("| statistic | label | required N | budget |")
    lines.append("|---|---|---|---|")
    for stat in BUDGETED_STATISTICS:
        lines.append(
            f"| {stat} | {report['spec']['labels'][stat]} "
            f"| {report['spec']['required_n'][stat]} "
            f"| {_fmt_budget(report['spec']['budgets'][stat])} |"
        )
    lines.append("")

    labels = report["spec"]["labels"]
    lines.append("## Cells")
    lines.append("")
    lines.append(
        f"| journey / step | width | locale | theme | verdict | "
        f"{labels['lcp']} | {labels['cls']} | {labels['inp']} |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for cell in report["cells"]:
        metrics = cell["metrics"]
        lines.append(
            f"| {cell['journey']} / {cell['step']} | {cell['width']} | {cell['locale']} | "
            f"{cell['theme']} | {cell['verdict']} "
            f"| {_cell_value(metrics[labels['lcp']])} "
            f"| {_cell_value(metrics[labels['cls']])} "
            f"| {_cell_value(metrics[labels['inp']])} |"
        )
    lines.append("")

    lines.append("## Resources (no budget: first run is the baseline)")
    lines.append("")
    lines.append(
        f"| journey / step | width | locale | theme | {labels['resource_count']} max | "
        f"{labels['transfer_bytes']} max |"
    )
    lines.append("|---|---|---|---|---|---|")
    for cell in report["cells"]:
        rc = cell["metrics"][labels["resource_count"]]
        tb = cell["metrics"][labels["transfer_bytes"]]
        lines.append(
            f"| {cell['journey']} / {cell['step']} | {cell['width']} | {cell['locale']} | "
            f"{cell['theme']} | {_fmt_number(rc.get('max'))} | {_fmt_number(tb.get('max'))} |"
        )
    lines.append("")

    server = report["server"]
    lines.append(
        f"## Server-held time (no budget; EDGE_TIMEOUT_RISK beyond {server['tool_timeout_s']} s)"
    )
    lines.append("")
    if server["routes"]:
        lines.append("| route | n | min ms | p50 ms | p75 ms | max ms | EDGE_TIMEOUT_RISK |")
        lines.append("|---|---|---|---|---|---|---|")
        for route in server["routes"]:
            elapsed = route["elapsed_ms"]
            lines.append(
                f"| {route['route']} | {route['n']} | {_fmt_number(elapsed['min'])} | "
                f"{_fmt_number(elapsed['p50'])} | {_fmt_number(elapsed['p75'])} | "
                f"{_fmt_number(elapsed['max'])} | {route['edge_timeout_risk']} |"
            )
    else:
        lines.append("_No journal was supplied; server-held time is unreported, not zero._")
    lines.append("")

    lines.append("## Failure classes (budget zero on every class)")
    lines.append("")
    lines.append("| class | count |")
    lines.append("|---|---|")
    for entry in report["failure_classes"]:
        lines.append(f"| {entry['id']} | {entry['count']} |")
    lines.append("")

    lines.append(
        "_The JSON report is canonical. INSUFFICIENT_SAMPLES and GAP are reported, "
        "never smoothed into a percentile; a gap cell is never PASS._"
    )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--spec", required=True, help="journey/matrix spec yml")
    parser.add_argument(
        "--manifest",
        action="append",
        required=True,
        dest="manifests",
        help="capture manifest (repeatable; one cold-load run each)",
    )
    parser.add_argument(
        "--journal",
        action="append",
        default=[],
        dest="journals",
        help="lab-server jsonl journal (repeatable, optional)",
    )
    parser.add_argument(
        "--run-time",
        required=True,
        help="explicit run time stamp for the report (no wall clock is read)",
    )
    parser.add_argument("--out-report", required=True, help="output path for the JSON report")
    parser.add_argument(
        "--out-summary", required=True, help="output path for the markdown summary"
    )
    args = parser.parse_args(argv)

    try:
        spec = load_spec(args.spec)
        report = build_report(
            spec=spec,
            spec_path=Path(args.spec),
            manifest_paths=[Path(p) for p in args.manifests],
            journal_paths=[Path(p) for p in args.journals],
            run_time=args.run_time,
        )
    except SpecError as exc:
        print(f"latency report: {exc}", file=sys.stderr)
        return EXIT_USAGE

    report_path = Path(args.out_report)
    summary_path = Path(args.out_summary)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(report_bytes(report))
    summary_path.write_text(render_markdown(report), encoding="utf-8")

    verdicts = report["totals"]["by_verdict"]
    print(
        "latency report: {overall} — cells {cells} "
        "(PASS {p} / FAIL {f} / INSUFFICIENT {i} / GAP {g}); "
        "wrote {report} + {summary}".format(
            overall=report["overall_verdict"],
            cells=report["totals"]["cells"],
            p=verdicts[VERDICT_PASS],
            f=verdicts[VERDICT_FAIL],
            i=verdicts[VERDICT_INSUFFICIENT],
            g=verdicts[VERDICT_GAP],
            report=report_path,
            summary=summary_path,
        )
    )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
