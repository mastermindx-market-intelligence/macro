"""Section 11 report: one pure assembly of the quality/cost report from scratch inputs.

DEC:NEWS-IMPACT-SECTION11-REPORT clause 13 (freeze, then assemble). The assembler reads
the committed registration and one scratch inputs file (system rows, gold slots, group and
issuer maps, routing and transfer verdicts, cost receipts), grades every critical slot
through eval_grade, builds one combined eval_receipt plus one per template stratum, and
projects the section 11 view on top: per-template N and shortfall, auto-published versus
all-dispositions versus absence correctness, routing recall and reject-audit miss as
seat_only, the unsupported-transfer count with the undecidable note, six-way disposition
accounting per construction, group independence, correction replay null_printed, and cost
from the qwen receipts with the MiniMax gap printed. It never originates a value: every
number is a count or a rate over graded items, and labeled values stay in scratch.

Registration gate: schema, version, the endpoints sha256 and
section11_registration.require_registered_implementation, which refuses when the loaded
code differs from any registered component. Refusals carry a code and an id, a path or a
count, never a value.

  python -m engine.news_impact.section11_report --inputs <scratch json> --out <scratch path>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from engine.news_impact import eval_grade as eg
from engine.news_impact import eval_receipt as er
from engine.news_impact import section11_registration as s11

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "ni-section11-report.v1"
SECTION11_REPORT_VERSION = "ni-section11-report-1"
DECISION = "DEC:NEWS-IMPACT-SECTION11-REPORT"

TEMPLATE_SCHEMA: Mapping[str, str] = {
    "T1": "capital_allocation_event.v1",
    "T2": "demand_guidance_contract_event.v1",
    "T3": "strategic_product_partnership_event.v1",
}
PER_TEMPLATE_N = 200
ABLATION = "full"
SUT_CONSTRUCTIONS = ("cheap_extractor_no_frontier", "proposed_cascade", "frontier_only_audit")
ROUTING_CONSTRUCTIONS = SUT_CONSTRUCTIONS + ("current_news_stack",)
# Baselines that emit no packet: their critical rows (or every row) are null_printed by name.
NO_PACKET_NULL_REASON: Mapping[str, str] = {
    "current_news_stack": "baseline_emits_no_packet",
    "deterministic_materiality_price_factor": "no_licensed_pit_price_factor_source",
}
NOVELTY_INDEPENDENCE = "new_magnitude_timing_commitment_counterparty"
DISPOSITIONS = ("deferred", "rejected", "quarantined", "auto_published", "reviewed_published", "abstained")
PACKET_DISPOSITIONS = ("auto_published", "reviewed_published")
GOLD_STATUSES = ("agreed", "adjudicated", "null_printed")
GOLD_SCORED = ("agreed", "adjudicated")
GOLD_NULL_REASONS = ("no_third_value", "economic_refusal")
ROUTING_OUTCOMES: Mapping[str, tuple[str, ...]] = {
    "material_routing": ("hit", "miss"),
    "reject_audit": ("auto_published", "not_published"),
}
TRANSFER_OUTCOMES = ("yes", "no")
REPORTING_FLOOR_REASON = "n_below_reporting_floor"
CRITICAL_METRICS = (
    "critical_numeric_correctness_auto_published",
    "critical_numeric_correctness_all_dispositions",
    "absence_correctness",
)
VIEW_METRICS = CRITICAL_METRICS + (
    "material_event_routing_recall",
    "reject_audit_miss_rate",
    "unsupported_ticker_to_supplier_count",
    "root_source_independence_hold",
    "correction_replay_success",
    "disposition_accounting_complete",
)
REQUIRED_REGISTRATION_KEYS = (
    "a3_registration", "baselines", "code_versions", "disclosures", "draws", "gold",
    "populations", "routing_metrics", "schema", "registration_version",
)
CODES = (
    "BAD_REGISTRATION", "ENDPOINTS_SHA_MISMATCH", "UNKNOWN_CASE", "UNKNOWN_FIELD",
    "UNKNOWN_TEMPLATE", "UNKNOWN_CONSTRUCTION", "UNKNOWN_DISPOSITION", "UNKNOWN_ROUTING_SOURCE",
    "BAD_OUTCOME", "BAD_FOLD", "BAD_GOLD_STATUS", "BAD_COUNT", "BAD_ROW", "OFF_AUDIT_SUBSET",
    "DUPLICATE_ROW", "DUPLICATE_SLOT", "DUPLICATE_ROUTING", "DUPLICATE_TRANSFER", "DUPLICATE_COST",
    "GOLD_SLOT_MALFORMED", "CLUSTER_MISSING", "NO_SYSTEM_ROWS", "FORBIDDEN_KEY", "OUT_EXISTS",
)
_NULL_REASON_RE = re.compile(r"null_reason=([a-z_0-9.]+)")

SpanVerifier = Callable[[Any], bool]


class ReportError(Exception):
    """Coded refusal; the message carries a code and an id, path or count, never a value."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        super().__init__(f"{code}: {detail}" if detail else code)


# ---------------------------------------------------------------- registration

def load_registration(path: Path | None = None) -> dict[str, Any]:
    p = Path(path) if path is not None else ROOT / s11.DEFAULT_OUT
    if not p.is_file():
        raise ReportError("BAD_REGISTRATION", s11.DEFAULT_OUT if path is None else str(p))
    return json.loads(p.read_text(encoding="utf-8"))


def check_registration(reg: Mapping[str, Any], registry: Any) -> None:
    """Schema, version, every required block, the implementation guard, the endpoints sha."""
    if reg.get("schema") != s11.SCHEMA:
        raise ReportError("BAD_REGISTRATION", "schema")
    if reg.get("registration_version") != s11.SECTION11_REGISTRATION_VERSION:
        raise ReportError("BAD_REGISTRATION", "registration_version")
    missing = [k for k in REQUIRED_REGISTRATION_KEYS if k not in reg]
    if missing:
        raise ReportError("BAD_REGISTRATION", ",".join(missing))
    # Refuses when the loaded code differs from any registered component (RegistrationError).
    s11.require_registered_implementation(reg)
    if reg["a3_registration"].get("endpoints_sha256") != registry.sha256:
        raise ReportError("ENDPOINTS_SHA_MISMATCH", str(reg["a3_registration"].get("endpoints_sha256", ""))[:12])


def _population(reg: Mapping[str, Any]) -> tuple[dict[str, dict[str, str]], frozenset[str]]:
    block = reg["populations"]["v2_match"]
    fields = list(block["row_fields"])
    cases: dict[str, dict[str, str]] = {}
    for row in block["rows"]:
        d = dict(zip(fields, row))
        cases[d["case_id"]] = d
    audit = frozenset(reg["draws"]["frontier_only_audit"]["v2_match_case_ids"])
    return cases, audit


def _template_fields(template: str) -> tuple[str, ...]:
    return tuple(eg.CRITICAL_NUMERIC_FIELDS[TEMPLATE_SCHEMA[template]])


def _registered_slots(cases: Mapping[str, Mapping[str, str]]) -> set[tuple[str, str]]:
    return {(cid, f) for cid, c in cases.items() for f in _template_fields(c["template"])}


# ---------------------------------------------------------------- inputs

def _int(obj: Mapping[str, Any], key: str, where: str) -> int:
    v = obj.get(key, 0)
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise ReportError("BAD_COUNT", f"{where}:{key}")
    return v


def _gold(inputs: Mapping[str, Any], cases: Mapping[str, Mapping[str, str]]) -> tuple[dict, dict]:
    registered = _registered_slots(cases)
    gold: dict[tuple[str, str], Mapping[str, Any]] = {}
    for slot in inputs.get("gold_slots", ()):
        cid, field, status = slot.get("case_id"), slot.get("field"), slot.get("status")
        if cid not in cases:
            raise ReportError("UNKNOWN_CASE", str(cid))
        if (cid, field) not in registered:
            raise ReportError("UNKNOWN_FIELD", f"{cid}/{field}")
        if (cid, field) in gold:
            raise ReportError("DUPLICATE_SLOT", f"{cid}/{field}")
        if status not in GOLD_STATUSES:
            raise ReportError("BAD_GOLD_STATUS", f"{cid}/{field}")
        if status == "null_printed" and slot.get("null_reason") not in GOLD_NULL_REASONS:
            raise ReportError("BAD_GOLD_STATUS", f"{cid}/{field}:null_reason")
        gold[(cid, field)] = slot
    by_status = Counter(s["status"] for s in gold.values())
    null_by_reason = Counter(s["null_reason"] for s in gold.values() if s["status"] == "null_printed")
    counts = {
        "registered": len(registered),
        "provided": len(gold),
        "by_status": {k: by_status.get(k, 0) for k in GOLD_STATUSES},
        "null_by_reason": {k: null_by_reason.get(k, 0) for k in GOLD_NULL_REASONS},
        "gold_missing": len(registered) - len(gold),
    }
    return gold, counts


def _sut_rows(
    inputs: Mapping[str, Any], cases: Mapping[str, Mapping[str, str]], audit: frozenset[str]
) -> dict[tuple[str, str], dict[str, Any]]:
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for row in inputs.get("sut_rows", ()):
        cid, con, disp = row.get("case_id"), row.get("construction"), row.get("disposition")
        if cid not in cases:
            raise ReportError("UNKNOWN_CASE", str(cid))
        if con not in SUT_CONSTRUCTIONS:
            raise ReportError("UNKNOWN_CONSTRUCTION", f"{cid}/{con}")
        if disp not in DISPOSITIONS:
            raise ReportError("UNKNOWN_DISPOSITION", f"{cid}/{con}")
        if con == "frontier_only_audit" and cid not in audit:
            raise ReportError("OFF_AUDIT_SUBSET", cid)
        if (cid, con) in rows:
            raise ReportError("DUPLICATE_ROW", f"{cid}/{con}")
        qty = row.get("quantities") or {}
        if not isinstance(qty, Mapping):
            raise ReportError("BAD_ROW", f"{cid}/{con}:quantities")
        allowed = _template_fields(cases[cid]["template"])
        for field in qty:
            if field not in allowed:
                raise ReportError("UNKNOWN_FIELD", f"{cid}/{field}")
        rows[(cid, con)] = {
            "case_id": cid,
            "construction": con,
            "disposition": disp,
            "novelty": row.get("novelty"),
            "quantities": dict(qty),
        }
    if not rows:
        raise ReportError("NO_SYSTEM_ROWS", "sut_rows")
    return rows


def _routing_items(
    inputs: Mapping[str, Any], sources: frozenset[str]
) -> tuple[dict[str, list[er.GradedItem]], dict[str, Counter]]:
    items: dict[str, list[er.GradedItem]] = defaultdict(list)
    coverage: dict[str, Counter] = defaultdict(Counter)
    seen: set[tuple[str, str, str]] = set()
    for it in inputs.get("routing_items", ()):
        cid, con, metric = str(it.get("case_id")), it.get("construction"), it.get("metric")
        if con not in ROUTING_CONSTRUCTIONS:
            raise ReportError("UNKNOWN_CONSTRUCTION", f"{cid}/{con}")
        if metric not in ROUTING_OUTCOMES or it.get("outcome") not in ROUTING_OUTCOMES[metric]:
            raise ReportError("BAD_OUTCOME", f"{cid}/{metric}")
        if it.get("fold") not in er.HISTORICAL_FOLDS:
            raise ReportError("BAD_FOLD", f"{cid}/{metric}")
        if it.get("template") not in TEMPLATE_SCHEMA:
            raise ReportError("UNKNOWN_TEMPLATE", f"{cid}/{metric}")
        source = str(it.get("source") or "").split()[:1]
        source_id = source[0] if source else ""
        if source_id not in sources:
            raise ReportError("UNKNOWN_ROUTING_SOURCE", f"{cid}/{metric}")
        key = (cid, con, metric)
        if key in seen:
            raise ReportError("DUPLICATE_ROUTING", f"{cid}/{con}/{metric}")
        seen.add(key)
        items[con].append(
            er.GradedItem(cid, it["fold"], TEMPLATE_SCHEMA[it["template"]], metric, it["outcome"])
        )
        coverage[con][source_id] += 1
    return items, coverage


def _transfer_items(inputs: Mapping[str, Any]) -> dict[str, list[er.GradedItem]]:
    items: dict[str, list[er.GradedItem]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for it in inputs.get("transfer_items", ()):
        cid, con = str(it.get("case_id")), it.get("construction")
        if con not in SUT_CONSTRUCTIONS:
            raise ReportError("UNKNOWN_CONSTRUCTION", f"{cid}/{con}")
        if it.get("outcome") not in TRANSFER_OUTCOMES:
            raise ReportError("BAD_OUTCOME", f"{cid}/unsupported_transfer")
        if it.get("fold") not in er.HISTORICAL_FOLDS:
            raise ReportError("BAD_FOLD", f"{cid}/unsupported_transfer")
        if it.get("template") not in TEMPLATE_SCHEMA:
            raise ReportError("UNKNOWN_TEMPLATE", f"{cid}/unsupported_transfer")
        if (cid, con) in seen:
            raise ReportError("DUPLICATE_TRANSFER", f"{cid}/{con}")
        seen.add((cid, con))
        items[con].append(
            er.GradedItem(cid, it["fold"], TEMPLATE_SCHEMA[it["template"]], "unsupported_transfer", it["outcome"])
        )
    return items


def _costs(inputs: Mapping[str, Any]) -> tuple[list[er.CostRecord], dict[str, dict[str, int]]]:
    records: list[er.CostRecord] = []
    wrapper: dict[str, dict[str, int]] = {}
    for c in inputs.get("costs", ()):
        con = c.get("construction")
        if con not in SUT_CONSTRUCTIONS:
            raise ReportError("UNKNOWN_CONSTRUCTION", f"cost/{con}")
        if con in wrapper:
            raise ReportError("DUPLICATE_COST", str(con))
        ti, to = _int(c, "tokens_in", con), _int(c, "tokens_out", con)
        wrapper[con] = {
            "tokens_in": ti,
            "tokens_out": to,
            "total_tokens": ti + to,
            "calls": _int(c, "calls", con),
            "frontier_calls": _int(c, "frontier_calls", con),
        }
        records.append(er.CostRecord(con, ABLATION, ti, to))
    return records, wrapper


def _calibration(inputs: Mapping[str, Any]) -> dict[str, Any]:
    block = inputs.get("gold_calibration") or {}
    out: dict[str, Any] = {}
    for audit in ("w2_seat_audit", "gold_agreed_audit"):
        a = block.get(audit)
        if not a:
            out[audit] = {"status": "null_printed", "null_reason": "audit_not_run"}
            continue
        n, wrong = _int(a, "n", audit), _int(a, "gold_wrong", audit)
        if wrong > n:
            raise ReportError("BAD_COUNT", f"{audit}:gold_wrong")
        out[audit] = {
            "status": "measured" if n else "null_printed",
            "null_reason": None if n else "zero_denominator",
            "n": n,
            "gold_wrong": wrong,
            "gold_wrong_rate": (wrong / n) if n else None,
            "interval": er.clopper_pearson_interval(wrong, n) if n else None,
        }
    return out


def _w2(inputs: Mapping[str, Any]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for tpl, counts in (inputs.get("w2_extraction") or {}).items():
        if tpl not in TEMPLATE_SCHEMA:
            raise ReportError("UNKNOWN_TEMPLATE", f"w2/{tpl}")
        if not isinstance(counts, Mapping):
            raise ReportError("BAD_COUNT", f"w2/{tpl}")
        out[tpl] = {str(k): _int(counts, k, f"w2/{tpl}") for k in counts}
    return out


# ---------------------------------------------------------------- grading

def _gold_form(slot: Mapping[str, Any]) -> str | None:
    q = slot.get("quantity")
    return q.get("form") if isinstance(q, Mapping) else None


def _grade(
    rows: Mapping[tuple[str, str], Mapping[str, Any]],
    cases: Mapping[str, Mapping[str, str]],
    gold: Mapping[tuple[str, str], Mapping[str, Any]],
    span_verifier: SpanVerifier | None,
) -> tuple[dict[str, list[er.GradedItem]], dict[str, Counter], dict[str, set[str]]]:
    """Every system row x every registered slot with scored gold, through eval_grade.

    Three copies per graded slot: the auto-published population (only when the row is
    auto_published), the all-dispositions population, and the gold-absent population when
    the gold form is absent. The grader's notes are counted by prefix, never printed.
    """
    items: dict[str, list[er.GradedItem]] = defaultdict(list)
    note_counts: dict[str, Counter] = defaultdict(Counter)
    evaluated: dict[str, set[str]] = defaultdict(set)
    for (cid, con), row in sorted(rows.items()):
        case = cases[cid]
        schema = TEMPLATE_SCHEMA[case["template"]]
        for field in eg.CRITICAL_NUMERIC_FIELDS[schema]:
            slot = gold.get((cid, field))
            if slot is None or slot["status"] not in GOLD_SCORED:
                continue
            try:
                graded = eg.grade_critical_numeric_field(
                    case_id=cid,
                    fold=case["fold"],
                    template=schema,
                    field=field,
                    gold_quantity=slot.get("quantity"),
                    candidate_quantity=row["quantities"].get(field),
                    span_verifier=span_verifier,
                )
            except eg.EvalGradeError as exc:
                raise ReportError("GOLD_SLOT_MALFORMED", f"{cid}/{field}:{exc.code}") from None
            evaluated[con].add(cid)
            for note in getattr(graded, "notes", ()) or ():
                note_counts[con][str(note).split(":", 1)[0]] += 1
            base = dict(case_id=cid, fold=case["fold"], template=schema, field=field, outcome=graded.outcome)
            if row["disposition"] == "auto_published":
                items[con].append(er.GradedItem(**base))
            items[con].append(er.GradedItem(**base, notes=er.POP_ALL_DISPOSITIONS))
            if _gold_form(slot) == "absent":
                items[con].append(er.GradedItem(**base, notes=er.POP_GOLD_ABSENT))
    return items, note_counts, evaluated


def _group_items(
    rows: Mapping[tuple[str, str], Mapping[str, Any]],
    cases: Mapping[str, Mapping[str, str]],
    groups: Mapping[str, str],
) -> tuple[dict[str, list[er.GradedItem]], Counter]:
    """One group_independence item per (construction, group): violation when two or more
    auto-published members both carry the independence novelty, else hold."""
    items: dict[str, list[er.GradedItem]] = defaultdict(list)
    multi: Counter = Counter()
    by_con: dict[str, dict[str, list[Mapping[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for (cid, con), row in rows.items():
        by_con[con][groups[cid]].append(row)
    for con in sorted(by_con):
        for gid in sorted(by_con[con]):
            members = by_con[con][gid]
            if len(members) > 1:
                multi[con] += 1
            dup = sum(
                1 for m in members
                if m["disposition"] == "auto_published" and m["novelty"] == NOVELTY_INDEPENDENCE
            )
            lead = min(m["case_id"] for m in members)
            case = cases[lead]
            items[con].append(
                er.GradedItem(
                    lead, case["fold"], TEMPLATE_SCHEMA[case["template"]], "group_independence",
                    "violation" if dup >= 2 else "hold",
                )
            )
    return items, multi


# ---------------------------------------------------------------- accounting + receipts

def _accounting(
    rows: Mapping[tuple[str, str], Mapping[str, Any]],
    con: str,
    manifest: Iterable[str],
    groups: Mapping[str, str],
    issuers: Mapping[str, str],
    evaluated: Mapping[str, set[str]],
) -> er.AccountingInput:
    sel = [r for (_, c), r in rows.items() if c == con]
    disp = Counter(r["disposition"] for r in sel)
    packets = [r for r in sel if r["disposition"] in PACKET_DISPOSITIONS]
    manifest_ids = tuple(sorted(manifest))
    return er.AccountingInput(
        manifest_n=len(manifest_ids),
        discovered=len(sel),
        unique_groups=len({groups[r["case_id"]] for r in sel}),
        extracted_packets=len(packets),
        issuer_impacts=len({issuers[r["case_id"]] for r in packets}),
        deferred=disp["deferred"],
        rejected=disp["rejected"],
        quarantined=disp["quarantined"],
        auto_published=disp["auto_published"],
        reviewed_published=disp["reviewed_published"],
        abstained=disp["abstained"],
        evaluated=len({cid for cid in evaluated.get(con, ()) if (cid, con) in rows}),
        manifest_case_ids=manifest_ids,
        output_case_ids=tuple(sorted(r["case_id"] for r in sel)),
    )


def _accounting_block(acct: er.AccountingInput) -> dict[str, Any]:
    d = acct.to_dict()
    d["six_way_sum"] = acct.six_way_sum()
    d["complete"] = bool(acct.complete())
    return d


def _merge(*parts: Mapping[str, list[er.GradedItem]]) -> dict[str, list[er.GradedItem]]:
    out: dict[str, list[er.GradedItem]] = defaultdict(list)
    for part in parts:
        for con, items in part.items():
            out[con].extend(items)
    return out


def _receipt(
    graded: Mapping[str, list[er.GradedItem]],
    accounting: er.AccountingInput,
    reg: Mapping[str, Any],
    baseline_ids: list[str],
    groups: Mapping[str, str],
    issuers: Mapping[str, str],
    costs: list[er.CostRecord],
    span_injected: bool,
    registry_path: Path | None,
) -> dict[str, Any]:
    return er.build_receipt(
        graded_by_construction={(b, ABLATION): list(graded.get(b, [])) for b in baseline_ids},
        cluster_map=dict(groups),
        issuer_map=dict(issuers),
        accounting=accounting,
        registration=reg["a3_registration"],
        costs=costs,
        baselines_run=baseline_ids,
        ablations_run=[ABLATION],
        prospective_labels_loaded=False,
        prospective_outputs_in_tune=False,
        prompt_corpus_hit=False,
        outcome_conditioned_selection=False,
        registry_path=registry_path,
        notes="span_verification=" + ("injected" if span_injected else "not_injected"),
    )


def _too_small(registry_path: Path | None) -> tuple[frozenset[str], frozenset[str]]:
    """Plain metric ids in too_small_at_600, and the ids qualified 'on T3'."""
    path = Path(registry_path) if registry_path is not None else Path(er.default_registry_path())
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries = [str(e) for e in raw.get("too_small_at_600", [])]
    plain = frozenset(e for e in entries if " on " not in e)
    t3 = frozenset(e.split(" on ")[0] for e in entries if " on T3" in e)
    return plain, t3


# ---------------------------------------------------------------- section 11 view

def _null_reason(text: str | None) -> str | None:
    m = _NULL_REASON_RE.search(text or "")
    return m.group(1) if m else None


def _view(
    receipt: Mapping[str, Any],
    registry: Any,
    too_small: tuple[frozenset[str], frozenset[str]],
    stratum: str | None,
    accounting_rows: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    bars = {m.metric_id: m.proposed_bar for m in registry.metrics}
    thresholds = {
        (t["metric_id"], t["baseline_id"]): t
        for t in receipt["threshold_evaluations"]
        if t["fold_slice"] == "all_historical" and t["ablation_id"] == ABLATION
    }
    plain, t3 = too_small
    out: list[dict[str, Any]] = []
    for row in receipt["metrics"]:
        mid, con = row["metric_id"], row["baseline_id"]
        if mid not in VIEW_METRICS or row["fold_slice"] != "all_historical" or row["ablation_id"] != ABLATION:
            continue
        value, n, status = row.get("value"), row.get("n"), row.get("status")
        reason = _null_reason(row.get("display_text"))
        interval = row.get("interval")
        if con in NO_PACKET_NULL_REASON and (
            mid in CRITICAL_METRICS or con == "deterministic_materiality_price_factor"
        ):
            value, status, reason, interval = None, "null_printed", NO_PACKET_NULL_REASON[con], None
        if mid == "disposition_accounting_complete" and con in accounting_rows:
            acct = accounting_rows[con]
            value, n, status, reason = (1.0 if acct["complete"] else 0.0), acct["manifest_n"], "measured", None
        floored = (
            mid in plain
            or (stratum == "T3" and (mid in t3 or mid in CRITICAL_METRICS))
            or status not in ("measured",)
        )
        interval_null_reason: str | None = None
        if interval is None or floored:
            if interval is not None or status == "measured":
                interval_null_reason = REPORTING_FLOOR_REASON
            if mid == "disposition_accounting_complete":
                interval_null_reason = "not_a_rate"
            if status != "measured" and reason:
                interval_null_reason = reason
            interval = None
        thr = thresholds.get((mid, con), {})
        entry = {
            "metric_id": mid,
            "construction": con,
            "stratum": stratum or "all",
            "proposed_bar": thr.get("proposed_bar", bars.get(mid)),
            "value": value,
            "n": n,
            "n_clusters": row.get("n_clusters"),
            "status": status,
            "null_reason": reason if status != "measured" else None,
            "interval": interval,
            "interval_null_reason": interval_null_reason,
            "crossing": thr.get("crossing", "not_evaluable"),
        }
        if mid == "disposition_accounting_complete" and con in accounting_rows:
            entry["six_way_sum"] = accounting_rows[con]["six_way_sum"]
        out.append(entry)
    out.sort(key=lambda e: (e["metric_id"], e["construction"]))
    return out


# ---------------------------------------------------------------- assembly

def _strings(tree: Any) -> Iterable[str]:
    if isinstance(tree, Mapping):
        for k, v in tree.items():
            yield str(k)
            yield from _strings(v)
    elif isinstance(tree, (list, tuple)):
        for v in tree:
            yield from _strings(v)
    elif isinstance(tree, str):
        yield tree


def self_check(report: Mapping[str, Any]) -> None:
    _, stripped = er.strip_forbidden_keys(report)
    if stripped:
        raise ReportError("FORBIDDEN_KEY", ",".join(sorted(stripped)))
    for text in _strings(report):
        er.lint_display_text(text)


def assemble(
    inputs: Mapping[str, Any],
    registration: Mapping[str, Any],
    *,
    span_verifier: SpanVerifier | None = None,
    registry: Any = None,
    registry_path: Path | None = None,
    inputs_sha256: str | None = None,
) -> dict[str, Any]:
    """Pure: inputs + registration -> report. Raises ReportError, RegistrationError or
    EvalReceiptError with a code; never writes."""
    registry = registry if registry is not None else er.load_registry(registry_path)
    check_registration(registration, registry)
    reg = registration
    cases, audit = _population(reg)
    sources = frozenset(str(s).split()[0] for s in reg["routing_metrics"]["sources"])
    baseline_ids = sorted(b.baseline_id for b in registry.baselines)
    for con in ROUTING_CONSTRUCTIONS + tuple(NO_PACKET_NULL_REASON):
        if con not in baseline_ids:
            raise ReportError("UNKNOWN_CONSTRUCTION", f"registry/{con}")

    gold, gold_counts = _gold(inputs, cases)
    rows = _sut_rows(inputs, cases, audit)
    routing, coverage = _routing_items(inputs, sources)
    transfer = _transfer_items(inputs)
    costs, cost_wrapper = _costs(inputs)
    calibration = _calibration(inputs)
    w2 = _w2(inputs)

    touched = {cid for cid, _ in rows}
    for part in (routing, transfer):
        for items in part.values():
            touched.update(it.case_id for it in items)
    groups = inputs.get("case_groups") or {}
    issuers = inputs.get("case_issuers") or {}
    for cid in sorted(touched):
        if cid not in groups or cid not in issuers:
            raise ReportError("CLUSTER_MISSING", cid)

    graded, note_counts, evaluated = _grade(rows, cases, gold, span_verifier)
    group_items, multi = _group_items(rows, cases, groups)
    all_items = _merge(graded, group_items, routing, transfer)

    constructions_present = sorted({con for _, con in rows})
    manifests = {
        con: (audit if con == "frontier_only_audit" else frozenset(cases)) for con in SUT_CONSTRUCTIONS
    }
    accounting = {
        con: _accounting(rows, con, manifests[con], groups, issuers, evaluated) for con in SUT_CONSTRUCTIONS
    }
    accounting_rows = {con: _accounting_block(a) for con, a in accounting.items()}
    accounting_construction = next(
        (c for c in ("proposed_cascade", "cheap_extractor_no_frontier", "frontier_only_audit") if c in constructions_present),
        None,
    )
    if accounting_construction is None:
        raise ReportError("NO_SYSTEM_ROWS", "accounting")

    span_injected = span_verifier is not None
    too_small = _too_small(registry_path)
    receipt_all = _receipt(
        all_items, accounting[accounting_construction], reg, baseline_ids, groups, issuers, costs,
        span_injected, registry_path,
    )
    strata_receipts: dict[str, Any] = {}
    strata_views: dict[str, Any] = {}
    strata_accounting: dict[str, Any] = {}
    for tpl, schema in TEMPLATE_SCHEMA.items():
        sub_items = {con: [it for it in items if it.template == schema] for con, items in all_items.items()}
        sub_rows = {k: r for k, r in rows.items() if cases[k[0]]["template"] == tpl}
        sub_manifest = {
            con: frozenset(c for c in manifests[con] if cases[c]["template"] == tpl) for con in SUT_CONSTRUCTIONS
        }
        sub_acct = {
            con: _accounting(sub_rows, con, sub_manifest[con], groups, issuers, evaluated) for con in SUT_CONSTRUCTIONS
        }
        sub_rows_blocks = {con: _accounting_block(a) for con, a in sub_acct.items()}
        strata_accounting[tpl] = sub_rows_blocks
        strata_receipts[tpl] = _receipt(
            sub_items, sub_acct[accounting_construction], reg, baseline_ids, groups, issuers, (),
            span_injected, registry_path,
        )
        strata_views[tpl] = _view(strata_receipts[tpl], registry, too_small, tpl, sub_rows_blocks)

    per_template: dict[str, Any] = {}
    for tpl in TEMPLATE_SCHEMA:
        n = sum(1 for c in cases.values() if c["template"] == tpl)
        per_template[tpl] = {"n": n, "shortfall_vs_200": max(0, PER_TEMPLATE_N - n)}

    a3 = reg["a3_registration"]
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "report_version": SECTION11_REPORT_VERSION,
        "decision": DECISION,
        "authority": "context_only",
        "may_rank": False,
        "may_size": False,
        "may_gate": False,
        "inputs_sha256": inputs_sha256,
        "registration": {
            "schema": reg["schema"],
            "registration_version": reg["registration_version"],
            "endpoints_sha256": a3["endpoints_sha256"],
            "mode": a3["mode"],
            "t_prospective": a3["t_prospective"],
            "code_versions": dict(reg["code_versions"]),
        },
        "code_versions_current": s11.current_code_versions(),
        "span_verification": "injected" if span_injected else "not_injected",
        "populations": {
            "v2_match": {"n": len(cases), "per_template": per_template},
            "frontier_only_audit": {
                "n": len(audit),
                "rate": reg["draws"]["frontier_only_audit"]["rate"],
                "seed": reg["draws"]["frontier_only_audit"]["seed"],
            },
        },
        "gold": {
            "families": list(reg["gold"].get("families", [])),
            "slots": gold_counts,
            "calibration": calibration,
        },
        "system": {
            "accounting_construction": accounting_construction,
            "constructions": {
                con: {
                    "rows": sum(1 for _, c in rows if c == con),
                    "accounting": accounting_rows[con],
                    "note_prefix_counts": dict(sorted(note_counts.get(con, Counter()).items())),
                    "n_multi_case_groups": multi.get(con, 0),
                    "cost": cost_wrapper.get(con),
                }
                for con in SUT_CONSTRUCTIONS
            },
        },
        "routing": {
            "label": "seat_only",
            "basis": reg["routing_metrics"]["label"],
            "registered_sources": sorted(sources),
            "coverage_by_source": {con: dict(sorted(c.items())) for con, c in sorted(coverage.items())},
        },
        "transfer": {
            "metric_id": registry.undecidable_metric_id,
            "undecidable_n_groups_needed": registry.undecidable_n_groups_needed,
            "undecidable_n_cases": dict(registry.undecidable_n_cases),
            "note": "count printed; zero is never certified at this n",
        },
        "correction_replay": {"status": "null_printed", "null_reason": "no_gold_correction_case"},
        "cost": {
            "system": cost_wrapper,
            "gold_labeling": {
                "status": "null_printed",
                "null_reason": "no_usage_receipts",
                "discovery": "DSC:NEWS-IMPACT-MINIMAX-NO-USAGE-RECEIPTS",
            },
        },
        "w2_extraction": w2,
        "disclosures": list(reg["disclosures"]),
        "view": {"all": _view(receipt_all, registry, too_small, None, accounting_rows), "strata": strata_views},
        "strata_accounting": strata_accounting,
        "receipts": {"all": receipt_all, "strata": strata_receipts},
    }
    self_check(report)
    return report


def render(report: Mapping[str, Any]) -> str:
    return json.dumps(report, sort_keys=True, indent=1, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--inputs", required=True, help="scratch json with sut_rows, gold_slots, maps, verdicts, costs")
    ap.add_argument("--registration", default=None, help=f"default {s11.DEFAULT_OUT}")
    ap.add_argument("--out", required=True, help="scratch path; an existing file is never overwritten")
    args = ap.parse_args(argv)
    try:
        out = Path(args.out)
        if out.exists() or out.is_symlink():
            raise ReportError("OUT_EXISTS", str(out))
        raw = Path(args.inputs).read_bytes()
        inputs = json.loads(raw.decode("utf-8"))
        reg = load_registration(Path(args.registration) if args.registration else None)
        report = assemble(inputs, reg, inputs_sha256=hashlib.sha256(raw).hexdigest())
        out.write_text(render(report), encoding="utf-8")
    except (ReportError, s11.RegistrationError, er.EvalReceiptError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    sys_block = report["system"]["constructions"]
    print(
        "report ok: constructions="
        + ",".join(f"{c}:{b['rows']}" for c, b in sys_block.items())
        + f" gold_slots={report['gold']['slots']['provided']}/{report['gold']['slots']['registered']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
