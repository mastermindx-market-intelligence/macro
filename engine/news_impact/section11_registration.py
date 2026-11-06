"""Section 11 registration: the frozen inputs of the quality/cost report.

DEC:NEWS-IMPACT-SECTION11-REPORT clause 13 freezes, before any GLM output exists, the system
families and prompt version, the gold families, the third-family candidates, seeds 20261021
and 20261022, the population lists, and the operator-tap note for the cascade.v1 lanes that
need one. This module builds that registration as a pure function of committed inputs: it
pins every input by sha256, checks the population joins it depends on, draws the
frontier_only_audit subset, and runs eval_receipt.make_registration for the A3 pins.

The registration holds ids, enums, counts, shas and rules only, never labeled values
(DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE).

Historical metadata integrity does not establish current implementation eligibility.
The original v1 registration is immutable; current code must match every registered
component before this module can qualify or write it. A changed implementation needs
a separately admitted registration, never a rewrite of the original.

  python -m engine.news_impact.section11_registration --check-historical-v1
  python -m engine.news_impact.section11_registration --check        # also require current code
  python -m engine.news_impact.section11_registration --out <path>   # eligible code only; no overwrite
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from engine.news_impact import eval_receipt as er
from engine.news_impact import section11_draws as draws
from engine.news_impact.cascade import DEFAULT_SCHEMA_VERSION
from engine.news_impact.cluster import CLUSTERER_VERSION
from engine.news_impact.edgar_body import EDGAR_BODY_VERSION_2
from engine.news_impact.issuer import RESOLVER_VERSION
from engine.news_impact.observation import OBSERVATION_VERSION
from engine.news_impact.producer import PRODUCER_VERSION
from engine.news_impact.producer_facts import PRODUCER_FACTS_VERSION
from engine.news_impact.prophet_adapter import ADAPTER_VERSION
from engine.news_impact.routing_gates import GATES_VERSION as GATES_1_VERSION
from engine.news_impact.routing_gates_2 import GATES_VERSION as GATES_2_VERSION
from engine.news_impact.sampler import SAMPLER_VERSION
from engine.news_impact.tape_draw import TAPE_DRAW_VERSION

SECTION11_REGISTRATION_VERSION = "ni-section11-registration-1"
SCHEMA = "ni-section11-registration.v1"
DECISION = "DEC:NEWS-IMPACT-SECTION11-REPORT"

ROOT = Path(__file__).resolve().parents[2]
PROGRAM = "research/prophet_v4/news_to_business_impact_20261006"
BENCH = f"{PROGRAM}/benchmark"
DEFAULT_OUT = f"{BENCH}/section11/registration.json"

# The original registration's complete identity, not a selectable live-code profile.
# The builder reconstructs metadata from pinned inputs; it does not execute old code.
HISTORICAL_V1_SHA256 = "5637cbea2d44533db77d7c77051996cd27dad5e1bb16ba483fd5b1ffeb02a71a"
HISTORICAL_V1_CODE_VERSIONS: Mapping[str, str] = MappingProxyType({
    "cascade_schema": "news_impact_event.v1:3edc7139",
    "cluster": "ni-cluster-1",
    "edgar_body": "ni-edgar-body-2",
    "issuer": "ni-issuer-1",
    "observation": "ni-observation-1",
    "producer": "ni-producer-1",
    "producer_facts": "ni-producer-facts-1",
    "prophet_adapter": "ni-prophet-adapter-2",
    "routing_gates_1": "ni-routing-gates-1",
    "routing_gates_2": "ni-routing-gates-2",
    "sampler": "ni-sampler-1",
    "tape_draw": "ni-tape-draw-1",
    "section11_draws": "ni-section11-draws-1",
    "section11_registration": "ni-section11-registration-1",
})

T_PROSPECTIVE = "2026-10-15T00:00:00Z"
MODE = "confirm"
SUT_PROMPT_VERSION = "prompt-v1.2"
TAPE_SAMPLER_VERSION = "ni-sampler-1"
TAPE_SEED = 20261014
GLM_EARLIEST_UTC = "2026-10-19T05:16:00Z"
GATED_V3_EARLIEST_UTC_DATE = "2026-10-20"
PER_TEMPLATE_N = 200

PINNED_INPUTS: dict[str, str] = {
    "endpoints": "contracts/news_impact/endpoints.v1.json",
    "cascade": "contracts/news_impact/cascade.v1.json",
    "label_return_schema": "contracts/news_impact/label_return.v1.schema.json",
    "adjudication_record_schema": "contracts/news_impact/adjudication_record.v1.schema.json",
    "sut_prompt": f"{BENCH}/results_w2/tools/label_batch.template.v1.2.txt",
    "gated_v2_manifest": f"{BENCH}/gated_v2/manifest.json",
    "gated_v2_cases": f"{BENCH}/gated_v2/cases.jsonl",
    "v2_routing": f"{BENCH}/results_w2/audit/v2_routing.json",
    "w2_critical_slots": f"{BENCH}/results_w2/critical_slots.jsonl",
    "w2q_critical_slots": f"{BENCH}/results_w2/v2_queue/critical_slots.jsonl",
    "w2_summary": f"{BENCH}/results_w2/summary.json",
    "w2_receipt_fam_a": f"{BENCH}/results_w2/eval_receipt_fam_a.json",
    "w2_receipt_fam_b": f"{BENCH}/results_w2/eval_receipt_fam_b.json",
    "w2q_summary": f"{BENCH}/results_w2/v2_queue/summary.json",
    "seat_audit_present": f"{BENCH}/results_w2/audit/audit.json",
    "seat_audit_absent": f"{BENCH}/results_w2/audit/audit_absent.json",
    "seat_audit_malformed": f"{BENCH}/results_w2/audit/audit_malformed.json",
    "routing_verdicts": f"{BENCH}/results_w2/audit/routing_verdicts.json",
    "gates1_verdicts": f"{BENCH}/results_w2/audit/gate_verdicts.json",
    "gates2_verdicts": f"{BENCH}/results_w2/audit/gates2_verdicts.json",
    "v2_routing_verdicts": f"{BENCH}/results_w2/audit/v2_routing_verdicts.json",
    "gated_v3_rule": f"{BENCH}/issuer_fallback/README.md",
}

# Byte-frozen contracts and the frozen system prompt. A change to any of these is a new
# registration version, never a silent rebuild.
FROZEN_SHA256: dict[str, str] = {
    "endpoints": "061d1c21276475f470fb16355832aa7bc16b10c897d5afcde97df7176be5d4b9",
    "cascade": "f1ddcbdb6dbdaefb7e7418a8542b4f0a60d2a8c9907bb07d94f92f16de25ffc9",
    "label_return_schema": "874a115fd059c6c2f2e63c1a655f1fc63dc43dfe5745f3f4a1fb3b10a0a279be",
    "adjudication_record_schema": "300f6929f24226b08b22ce055ffb0fc2263ed8e7483b5b254c442758e031fc23",
    "sut_prompt": "d4f986382a9a724df707c49b33b7ae738672a49d8883178b8d733d1e37238cfe",
}

# Population facts the registration rests on (DEC:NEWS-IMPACT-CONTINUATION-ROUTING-GATES).
EXPECTED_MATCH_BY_TEMPLATE = {"T1": 34, "T2": 36, "T3": 4}
EXPECTED_QUEUE = 12
EXPECTED_CRITICAL_SLOTS = {
    "T1": {"executed_amount": 34, "incremental_amount": 34, "remaining_authorization": 34},
    "T2": {"stated_amount": 36},
    "T3": {"stated_quantity": 4},
}

THIRD_FAMILY_ORDER = (
    {"rank": 1, "model": "deepseek-v4.1-flash", "provider": "go", "task_class": "extract"},
    {"rank": 2, "model": "deepseek-v4-flash-0731", "provider": "bailian", "task_class": "extract"},
)


class RegistrationError(Exception):
    """Coded refusal; the message carries a code and a path or count, never a value."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        super().__init__(f"{code}: {detail}" if detail else code)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def pin_inputs(root: Path) -> dict[str, dict[str, str]]:
    pins: dict[str, dict[str, str]] = {}
    for role, rel in PINNED_INPUTS.items():
        path = root / rel
        if not path.is_file():
            raise RegistrationError("INPUT_MISSING", rel)
        pins[role] = {"path": rel, "sha256": _sha256(path)}
    for role, want in FROZEN_SHA256.items():
        if pins[role]["sha256"] != want:
            raise RegistrationError("FROZEN_INPUT_CHANGED", PINNED_INPUTS[role])
    return pins


def match_rows(routing: Mapping[str, Any], cases: Iterable[Mapping[str, Any]]) -> list[dict[str, str]]:
    """Join the v2 MATCH ids to their gated_v2 case rows; refuse any join failure."""
    by_id = {str(c["item_id"]): c for c in cases}
    rmap = routing["routing_map"]
    match = [str(cid) for cid in routing["scorable_match"]]
    if len(set(match)) != len(match):
        raise RegistrationError("DUPLICATE_MATCH_ID", str(len(match)))
    rows: list[dict[str, str]] = []
    for cid in sorted(match):
        case = by_id.get(cid)
        if case is None:
            raise RegistrationError("MATCH_ID_NOT_IN_CASES", cid)
        if str(rmap[cid]["template"]) != str(case["template"]):
            raise RegistrationError("TEMPLATE_DISAGREES", cid)
        fold = str(case["fold"])
        if fold not in er.HISTORICAL_FOLDS:
            raise RegistrationError("NON_HISTORICAL_FOLD", f"{cid}:{fold}")
        rows.append(
            {
                "case_id": cid,
                "template": str(case["template"]),
                "proxy_cell": str(case["proxy_cell"]),
                "fold": fold,
            }
        )
    return rows


def _check_counts(rows: list[dict[str, str]], queue: list[str]) -> None:
    got = Counter(r["template"] for r in rows)
    if dict(got) != EXPECTED_MATCH_BY_TEMPLATE:
        raise RegistrationError("MATCH_COUNTS_CHANGED", str(sorted(got.items())))
    ids = {r["case_id"] for r in rows}
    if len(queue) != EXPECTED_QUEUE or len(set(queue)) != EXPECTED_QUEUE:
        raise RegistrationError("QUEUE_COUNT_CHANGED", str(len(queue)))
    if not set(queue) <= ids:
        raise RegistrationError("QUEUE_NOT_IN_MATCH", str(len(set(queue) - ids)))


def critical_slot_counts(
    rows: list[dict[str, str]],
    queue: list[str],
    w2_slots: Iterable[Mapping[str, Any]],
    w2q_slots: Iterable[Mapping[str, Any]],
) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, int]]]:
    """Critical slots of the MATCH cases: W2 rows for the 62 reused cases, W2Q rows for the
    12 queue cases. Returns slot counts per template and field, and slot counts per source
    and prompt_version. Counts only; the rows' labeled values are never read."""
    ids = {r["case_id"] for r in rows}
    queued = set(queue)
    counts: dict[str, Counter] = {}
    versions: dict[str, Counter] = {"w2": Counter(), "w2q": Counter()}
    seen: set[tuple[str, str]] = set()

    def add(slot: Mapping[str, Any], source: str) -> None:
        key = (str(slot["case_id"]), str(slot["field"]))
        if key in seen:
            raise RegistrationError("DUPLICATE_SLOT", f"{key[0]}/{key[1]}")
        if key[1] not in er.CRITICAL_NUMERIC_FIELDS:
            raise RegistrationError("NOT_A_CRITICAL_FIELD", key[1])
        seen.add(key)
        counts.setdefault(str(slot["template"]), Counter())[key[1]] += 1
        versions[source][str(slot["prompt_version"])] += 1

    for slot in w2_slots:
        cid = str(slot["case_id"])
        if cid in ids and cid not in queued:
            add(slot, "w2")
    for slot in w2q_slots:
        cid = str(slot["case_id"])
        if cid in ids:
            if cid not in queued:
                raise RegistrationError("W2Q_SLOT_OUTSIDE_QUEUE", cid)
            add(slot, "w2q")
    covered = {cid for cid, _ in seen}
    if covered != ids:
        raise RegistrationError("MATCH_CASE_WITHOUT_SLOTS", str(len(ids - covered)))
    out = {t: dict(sorted(c.items())) for t, c in sorted(counts.items())}
    if out != EXPECTED_CRITICAL_SLOTS:
        raise RegistrationError("CRITICAL_SLOT_COUNTS_CHANGED", str(sorted((t, sum(c.values())) for t, c in out.items())))
    return out, {s: dict(sorted(c.items())) for s, c in versions.items()}


def _population_block(rows: list[dict[str, str]], queue: list[str], families: Mapping[str, Any]) -> dict[str, Any]:
    by_template = Counter(r["template"] for r in rows)
    per_template = {}
    for t in sorted(EXPECTED_MATCH_BY_TEMPLATE):
        fam = families.get(t, {})
        per_template[t] = {
            "drawn": int(fam.get("drawn", 0)),
            "scorable_match": by_template.get(t, 0),
            "shortfall_vs_200": PER_TEMPLATE_N - by_template.get(t, 0),
        }
    return {
        "v2_match": {
            "source": "v2_routing.scorable_match joined to gated_v2 cases.jsonl by item_id",
            "n": len(rows),
            "per_template": per_template,
            "per_cell": dict(sorted(Counter(f"{r['template']}-{r['proxy_cell']}" for r in rows).items())),
            "per_fold": dict(sorted(Counter(r["fold"] for r in rows).items())),
            "rows": [[r["case_id"], r["template"], r["proxy_cell"], r["fold"]] for r in rows],
            "row_fields": ["case_id", "template", "proxy_cell", "fold"],
        },
        "label_queue": {
            "source": "v2_routing.label_queue, a subset of v2_match",
            "n": len(queue),
            "case_ids": sorted(queue),
        },
        "gated_v3": {
            "rule": "issuer_fallback/README.md exactly as frozen, run on or after the date below",
            "earliest_utc_date": GATED_V3_EARLIEST_UTC_DATE,
            "joins_report_as": "its own MATCH cases after the seat routing verdicts, in a separate table from v2_match",
        },
        "w2_extraction_only": {
            "source": "results_w2 summary and receipts",
            "rule": "W2 stays extraction-only in its own table and is never pooled with v2_match or gated_v3",
        },
        "unscorable": {
            "rule": "v2 routing classes other than MATCH are printed as counts with their class and never enter critical-numeric denominators",
        },
    }


def current_code_versions() -> dict[str, str]:
    """Describe the loaded implementation, independently of historical metadata."""
    return {
        "cascade_schema": DEFAULT_SCHEMA_VERSION,
        "cluster": CLUSTERER_VERSION,
        "edgar_body": EDGAR_BODY_VERSION_2,
        "issuer": RESOLVER_VERSION,
        "observation": OBSERVATION_VERSION,
        "producer": PRODUCER_VERSION,
        "producer_facts": PRODUCER_FACTS_VERSION,
        "prophet_adapter": ADAPTER_VERSION,
        "routing_gates_1": GATES_1_VERSION,
        "routing_gates_2": GATES_2_VERSION,
        "sampler": SAMPLER_VERSION,
        "tape_draw": TAPE_DRAW_VERSION,
        "section11_draws": draws.SECTION11_DRAWS_VERSION,
        "section11_registration": SECTION11_REGISTRATION_VERSION,
    }


def _build_registration(root: Path, code_versions: Mapping[str, str]) -> dict[str, Any]:
    pins = pin_inputs(root)
    registry = er.load_registry(root / PINNED_INPUTS["endpoints"])
    if registry.sha256 != pins["endpoints"]["sha256"]:
        raise RegistrationError("ENDPOINTS_SHA_MISMATCH", PINNED_INPUTS["endpoints"])
    manifest = _read_json(root / PINNED_INPUTS["gated_v2_manifest"])
    if manifest.get("sampler_version") != TAPE_SAMPLER_VERSION or int(manifest.get("seed", -1)) != TAPE_SEED:
        raise RegistrationError("TAPE_MANIFEST_CHANGED", PINNED_INPUTS["gated_v2_manifest"])
    tape_sha = str(manifest["tape_sha256"])
    routing = _read_json(root / PINNED_INPUTS["v2_routing"])
    cases = _read_jsonl(root / PINNED_INPUTS["gated_v2_cases"])
    rows = match_rows(routing, cases)
    queue = [str(q) for q in routing["label_queue"]]
    _check_counts(rows, queue)
    slots, slot_versions = critical_slot_counts(
        rows,
        queue,
        _read_jsonl(root / PINNED_INPUTS["w2_critical_slots"]),
        _read_jsonl(root / PINNED_INPUTS["w2q_critical_slots"]),
    )
    frontier_draw = draws.frontier_only_audit_draw(rows)
    cascade = _read_json(root / PINNED_INPUTS["cascade"])

    a3 = er.make_registration(
        tape_sha256=tape_sha,
        sampler_version=TAPE_SAMPLER_VERSION,
        sampling_seed=TAPE_SEED,
        t_prospective=T_PROSPECTIVE,
        mode=MODE,
        prompt_corpus_sha256=pins["sut_prompt"]["sha256"],
        endpoints_sha256=pins["endpoints"]["sha256"],
    )
    reg: dict[str, Any] = {
        "schema": SCHEMA,
        "registration_version": SECTION11_REGISTRATION_VERSION,
        "decision": DECISION,
        "authority": "context_only",
        "a3_registration": a3,
        "inputs": pins,
        "populations": _population_block(rows, queue, routing["families"]),
        "system_under_test": {
            "family": "qwen",
            "prompt_version": SUT_PROMPT_VERSION,
            "prompt_sha256": pins["sut_prompt"]["sha256"],
            "cheap_extractor_no_frontier": {
                "model": "qwen3.7-plus",
                "provider": "bailian",
                "route": "prompt-v1.2 label_return.v1, then producer stage one in shadow mode, then validate_event",
            },
            "proposed_cascade": {
                "cheap_model": "qwen3.7-plus",
                "frontier_model": "qwen3.8-max",
                "frontier_on": ["deferred", "quarantined", "classify_event_disagreement"],
                "quarantined_means": "producer outcome rejected with a code beginning validation:",
                "frontier_calls": "every call counted and printed; off-peak only; within cascade.v1 measurement_run_slot_caps",
            },
            "run": "one fresh run on every v2_match case and, later, every gated_v3 MATCH case",
            "not_system_output": "the W2 fam_b returns (mixed prompt-v1.0 and v1.1) are labels and are never reused as system output",
            "model_vintage": "vintage_unknown",
        },
        "baselines": {
            "current_news_stack": {
                "calls": ["engine.news_common.is_low_value", "engine.news_events.classify_event"],
                "inputs": "tape title and domain; author empty; body not supplied",
                "critical_slots": "null_printed with reason baseline_emits_no_packet",
                "routing": "graded on material-event routing against the same seat verdicts as the system",
            },
            "deterministic_materiality_price_factor": {
                "rule": "market model on SPY: OLS over the 120 regular sessions ending t-1; sigma is the standard deviation of the last 60 residuals; material when the absolute residual on t is at least 2.0 sigma; t is the first regular session on or after seendate",
                "threshold_sigma": 2.0,
                "estimation_sessions": 120,
                "sigma_sessions": 60,
                "frozen_before": "any return is read",
                "without_licensed_source": "every row null_printed with reason no_licensed_pit_price_factor_source",
                "critical_slots": "null_printed with reason baseline_emits_no_packet",
            },
            "cheap_extractor_no_frontier": {"see": "system_under_test.cheap_extractor_no_frontier"},
            "proposed_cascade": {"see": "system_under_test.proposed_cascade"},
            "frontier_only_audit": {
                "model": "qwen3.8-max",
                "provider": "bailian",
                "v2_match_draw": frontier_draw,
                "gated_v3_draw": "the same function and seed on gated_v3 MATCH rows, drawn once after its seat routing verdicts and before any system output",
                "off_subset": "null_printed with reason not_in_audit_subset",
                "widening": "never",
            },
            "population": "every baseline runs on the same case_id set, or each row is null_printed with a reason; silent skip is refused",
        },
        "gold": {
            "families": ["MiniMax-M3", "GLM"],
            "minimax": {
                "v2_match_reused": "accepted W2 fam_a drafts for the 62 v2_match cases outside the label queue, prompt_version recorded per draft",
                "label_queue_reused": "accepted W2Q fam_a drafts for the 12 queue cases at prompt-v1.2",
                "gated_v3": "a fresh MiniMax draft at prompt-v1.2 for each MATCH case",
            },
            "glm": {
                "model_requested": "glm-5.3",
                "task_class": "extract",
                "earliest_utc": GLM_EARLIEST_UTC,
                "scope": "every critical slot of every v2_match and gated_v3 MATCH case",
                "prompt_version": SUT_PROMPT_VERSION,
                "model_recorded": "the granted model is recorded per draft; drafts from different granted models are never mixed in one table",
            },
            "critical_slots_v2_match": slots,
            "critical_slots_v2_match_total": sum(sum(c.values()) for c in slots.values()),
            "critical_slots_v2_match_by_prompt_version": slot_versions,
            "disagreement": "a slot where MiniMax and GLM disagree goes to the third family, then to seat adjudication under adjudication_record.v1 with exactly three labeler values",
            "no_third_value": "the slot is null_printed, leaves the denominator, and the count of such slots is printed",
            "vendor_disjoint": "no qwen family output enters gold for any case",
        },
        "third_family": {
            "order": list(THIRD_FAMILY_ORDER),
            "rule": "the first candidate that returns labels every disputed slot; the next is used only on non-return; family and model are recorded per slot",
            "economic_refusal": "final; the affected slots are null_printed and counted",
            "excluded": ["qwen (system under test)", "MiniMax (gold)", "GLM (gold)", "MiMo (provider block in W2)"],
            "named_before": "any third-family output is read",
        },
        "draws": {
            "draws_version": draws.SECTION11_DRAWS_VERSION,
            "frontier_only_audit": {
                "seed": draws.FRONTIER_AUDIT_SEED,
                "rate": draws.FRONTIER_AUDIT_RATE,
                "strata": "template-proxy_cell",
                "v2_match_case_ids": frontier_draw["case_ids"],
            },
            "gold_agreed_audit": {
                "seed": draws.GOLD_AUDIT_SEED,
                "size": draws.GOLD_AUDIT_SIZE,
                "strata": "template-agreement_kind",
                "agreement_kinds": list(draws.AGREEMENT_KINDS),
                "drawn": "once both gold families have returned, before any system output is graded",
            },
        },
        "reporting": {
            "critical_numeric_denominator": "MATCH cases only; null and n_below_reporting_floor printed per A3",
            "gold_error_rate": "from the W2 seat audits plus the gold_agreed_audit draw, printed beside every gold-graded rate",
            "unsupported_ticker_to_supplier_count": "observed count printed with its undecidable_at_600 note, never a certified zero",
            "too_small_at_600": "null interval with reason n_below_reporting_floor",
            "per_template": "N and shortfall_vs_200; T3 at zero stays zero",
            "interval": "bootstrap per a3_registration seed and reps",
            "producer_on_gold": "stage one in adjudicated mode on gold and stage two on its events measure pipeline fidelity only, never extraction accuracy",
            "outputs_with_values": "scratch only",
        },
        "routing_metrics": {
            "material_event_routing_recall": "seat routing verdict files only",
            "reject_audit_miss_rate": "seat routing verdict files only",
            "sources": ["routing_verdicts", "gates1_verdicts", "gates2_verdicts", "v2_routing_verdicts", "gated_v3 verdicts when they exist"],
            "label": "seat_only until the second auditor of DEC:NEWS-IMPACT-ROUTING-GATES-2-MISS-PATH item 7 has run; the coverage limit is printed",
        },
        "mirror_and_correction": {
            "root_source_independence_hold": "stage-two rule novelty on system output",
            "correction_replay_success": "null_printed with reason no_gold_correction_case until a gold case carries a corrected fact",
        },
        "cost": {
            "system": "qwen usage receipts per call, frontier calls counted separately",
            "gold_labeling": "printed as a gap where MiniMax usage receipts are missing (DSC:NEWS-IMPACT-MINIMAX-NO-USAGE-RECEIPTS)",
        },
        "operator_tap": {
            "lanes": list(cascade["lanes_require_operator_tap"]),
            "note": "these cascade.v1 lanes run in production only after an operator tap; the runs registered here are measurement runs on frozen historical cases and enable no lane",
            "measurement_run_slot_caps": dict(cascade["measurement_run_slot_caps"]),
        },
        "code_versions": dict(code_versions),
        "disclosures": [
            "Historical folds f1 to f5 are QA only; no prospective case exists in v2_match.",
            "Model vintage is unknown for every family and is printed as vintage_unknown.",
            "600 cases are too few for the too_small_at_600 endpoints; their intervals print null.",
            "The v2_match population falls short of 200 per template; the shortfall is printed per template.",
        ],
    }
    self_check(reg)
    return reg


def _strings(tree: Any) -> Iterable[str]:
    if isinstance(tree, str):
        yield tree
    elif isinstance(tree, Mapping):
        for k, v in tree.items():
            yield str(k)
            yield from _strings(v)
    elif isinstance(tree, (list, tuple)):
        for v in tree:
            yield from _strings(v)


def self_check(reg: Mapping[str, Any]) -> None:
    _, stripped = er.strip_forbidden_keys(reg)
    if stripped:
        raise RegistrationError("FORBIDDEN_KEY", ",".join(sorted(stripped)))
    for text in _strings(reg):
        er.lint_display_text(text)


def render(reg: Mapping[str, Any]) -> str:
    return json.dumps(reg, sort_keys=True, indent=1, ensure_ascii=False) + "\n"


def _require_historical_v1(registration: Mapping[str, Any]) -> None:
    """Bind this historical API to the original identity and complete metadata."""
    digest = hashlib.sha256(render(registration).encode("utf-8")).hexdigest()
    if digest != HISTORICAL_V1_SHA256:
        raise RegistrationError("HISTORICAL_REGISTRATION_CHANGED", SECTION11_REGISTRATION_VERSION)


def build_historical_registration_v1(root: Path = ROOT) -> dict[str, Any]:
    """Reconstruct the immutable v1 metadata; this does not qualify or execute code."""
    registration = _build_registration(root, HISTORICAL_V1_CODE_VERSIONS)
    _require_historical_v1(registration)
    return registration


def require_registered_implementation(registration: Mapping[str, Any]) -> None:
    """Refuse if the loaded code differs from any component of the original v1.

    Run/report consumers must call this guard; a historical reconstruction is not
    an eligibility receipt. No caller-supplied version override is accepted.
    """
    _require_historical_v1(registration)
    registered = registration["code_versions"]
    current = current_code_versions()
    differences = [
        f"{key}: registered={registered.get(key, '<missing>')}, current={current.get(key, '<missing>')}"
        for key in sorted(set(registered) | set(current))
        if key not in registered or key not in current or registered[key] != current[key]
    ]
    if differences:
        raise RegistrationError("REGISTERED_IMPLEMENTATION_MISMATCH", "; ".join(differences))


def build_registration(root: Path = ROOT) -> dict[str, Any]:
    """Build v1 only when frozen inputs and the current implementation both match."""
    registration = build_historical_registration_v1(root)
    require_registered_implementation(registration)
    return registration


def _check_committed_historical_v1(payload: bytes, root: Path) -> None:
    path = root / DEFAULT_OUT
    if not path.is_file():
        raise RegistrationError("REGISTRATION_MISSING", DEFAULT_OUT)
    if path.read_bytes() != payload:
        raise RegistrationError("HISTORICAL_REGISTRATION_CHANGED", DEFAULT_OUT)


def _write_new_or_identical(out: Path, payload: bytes) -> bool:
    """Never truncate an existing file, including a symlink or hard-link alias."""
    if out.exists() or out.is_symlink():
        if out.is_file() and out.read_bytes() == payload:
            return False
        raise RegistrationError("REGISTRATION_OVERWRITE_REFUSED", str(out))
    out.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also refuses a file or symlink arriving after the check.
    try:
        with out.open("xb") as stream:
            stream.write(payload)
    except FileExistsError as exc:
        raise RegistrationError("REGISTRATION_OVERWRITE_REFUSED", str(out)) from exc
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--out", default=None, help="write an eligible registration to a new or identical file")
    mode.add_argument("--check", action="store_true", help="check the frozen file and current implementation")
    mode.add_argument("--check-historical-v1", action="store_true", help="check original v1 metadata only")
    args = ap.parse_args(argv)
    try:
        registration = build_historical_registration_v1()
        payload = render(registration).encode("utf-8")
        if args.check or args.check_historical_v1:
            _check_committed_historical_v1(payload, ROOT)
            if args.check:
                require_registered_implementation(registration)
                print(f"historical integrity and current implementation match: {DEFAULT_OUT}")
            else:
                print(f"historical v1 integrity ok; current eligibility not checked: {DEFAULT_OUT}")
            return 0
        require_registered_implementation(registration)
        out = Path(args.out) if args.out else ROOT / DEFAULT_OUT
        written = _write_new_or_identical(out, payload)
        print(f"{'wrote' if written else 'unchanged'} {out}")
        return 0
    except RegistrationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"REGISTRATION_IO_ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
