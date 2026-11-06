"""A3 metrics/receipt layer: eval_receipt.v1 assembly from graded items.

Implements design packet A3_eval sections 4.8-4.14 (endpoint families,
baselines/ablations as declarative records, PROPOSED-OWNER-FREEZES thresholds,
leakage audit, receipt assembly) under Phase 0 freeze (contract sha256 prefix
``3edc7139``) and MASTERPLAN.md section 11 (no confidence/probability/price-
target/score field anywhere; nulls printed, never hidden; no promotion from
this receipt in v1).

Graded-item contract with the parallel eval_grade lane (NOT imported here by
seat ruling): each :class:`GradedItem` is one unit of analysis. ``field`` is
the graded slot token; ``outcome`` is the closed grade string. Populations are
discriminated by the exact ``notes`` token (``population=all_dispositions``,
``population=gold_absent``; the default empty-notes population is the
auto-published one, per A3 section 7 default 4: reviewed_published items are
excluded from the 98 percent denominator).

Cluster bootstrap (A3 section 4.7 / assumption A4): random.Random(20261012),
9999 replicates, percentile interval at coverage 0.95, resampling CLUSTER
group ids (all rows of a resampled group travel together) — never items.
A zero denominator yields value null plus a null_reason string carried in
``display_text`` (the schema's metric_row is additionalProperties false and
admits no null_reason key); never 0 and never an exception.

Design-vs-schema notes (schema wins per W3-R1; see
R/out/W3_E3_receipt/proposed/eval_receipt_v1_design_schema_conflicts.md):
``threshold_crossing="disputed_dependence"`` (A3_eval.md:341) is not in the
schema crossing enum — the dispute is carried by ``dependence_dispute``; the
two-way CGM "second governing method" (A3_eval.md:340) has no receipt slot —
exposed as :func:`two_way_cgm_interval` only; the registry's string bar
``"success_on_subset"`` (endpoints.v1.json:188) is not representable
(number|boolean|null, eval_receipt.v1.schema.json:271) — emitted as null.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "CODES",
    "EvalReceiptError",
    "GradedItem",
    "AccountingInput",
    "CostRecord",
    "BaselineSpec",
    "AblationSwitch",
    "RegistryMetric",
    "EndpointRegistry",
    "EndpointSpec",
    "BOOTSTRAP_SEED",
    "BOOTSTRAP_REPS",
    "INTERVAL_COVERAGE",
    "FOLD_ALLOWLIST",
    "canonical_json",
    "default_registry_path",
    "load_registry",
    "ablation_id_from_switches",
    "cluster_bootstrap_interval",
    "clopper_pearson_interval",
    "wilson_interval",
    "two_way_cgm_interval",
    "strip_forbidden_keys",
    "lint_display_text",
    "audit_leakage",
    "evaluate_threshold",
    "make_registration",
    "build_receipt",
]

# ---------------------------------------------------------------- constants

BOOTSTRAP_SEED = 20261012
BOOTSTRAP_REPS = 9999
INTERVAL_COVERAGE = 0.95
FOLD_ALLOWLIST: tuple[str, ...] = ("f1", "f2", "f3", "f4", "f5")
HISTORICAL_FOLDS: frozenset[str] = frozenset(FOLD_ALLOWLIST)
FOLD_SLICES: tuple[str, ...] = ("all_historical",) + FOLD_ALLOWLIST
MIN_N_FOR_INTERVAL = 30            # A3 assumption A5
MIN_CLUSTERS_FOR_INTERVAL = 10     # A3 assumption A5
CONTRACT_SHA256_PREFIX = "3edc7139"
Z_BY_COVERAGE: dict[float, float] = {0.95: 1.959963984540054}
UNDECIDABLE_ZERO_BARS: frozenset[str] = frozenset(
    {"unsupported_ticker_to_supplier_count", "root_source_independence_hold"}
)
_FORBIDDEN_KEY_RE = re.compile(
    r"confidence|probability|score|target|fair.?value|rating|sentiment|contagion",
    re.IGNORECASE,
)
_DISPLAY_FORBIDDEN_RE = re.compile(r"\b(proves?|falsifies?|guarantees?|will)\b", re.IGNORECASE)
CRITICAL_NUMERIC_FIELDS: frozenset[str] = frozenset(
    {
        "incremental_amount",
        "remaining_authorization",
        "executed_amount",
        "stated_amount",
        "stated_quantity",
    }
)
POP_ALL_DISPOSITIONS = "population=all_dispositions"
POP_GOLD_ABSENT = "population=gold_absent"
NULL_REASON_ZERO_DENOMINATOR = "zero_denominator"

CODES: frozenset[str] = frozenset(
    {
        "PROSPECTIVE_FOLD_REFUSED",
        "SEALED_FOLD_REFUSED",
        "ENDPOINTS_SHA_MISMATCH",
        "CLUSTER_ID_MISSING",
        "UNKNOWN_FOLD_SLICE",
        "UNKNOWN_BASELINE",
        "DUPLICATE_GRADED_ITEM",
        "BAD_REGISTRY",
        "BAD_REGISTRATION",
        "BAD_COVERAGE",
        "BAD_METRIC_VALUE",
        "DISPLAY_FORBIDDEN_WORD",
    }
)


class EvalReceiptError(Exception):
    """Module error carrying a closed code string (see :data:`CODES`)."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# ------------------------------------------------------------ value objects


@dataclass(frozen=True)
class GradedItem:
    """One graded unit of analysis (slot / case / pair / group / observation).

    Exactly the eight fields fixed by lane ruling; ``eval_grade`` is a parallel
    lane and is deliberately not imported.
    """

    case_id: str
    fold: str
    template: str
    field: str
    outcome: str
    gold_value: Any = None
    candidate_value: Any = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "fold": self.fold,
            "template": self.template,
            "field": self.field,
            "outcome": self.outcome,
            "gold_value": self.gold_value,
            "candidate_value": self.candidate_value,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class AccountingInput:
    """Disposition accounting block (schema key order), injected as data."""

    manifest_n: int
    discovered: int = 0
    unique_groups: int = 0
    extracted_packets: int = 0
    issuer_impacts: int = 0
    deferred: int = 0
    rejected: int = 0
    quarantined: int = 0
    auto_published: int = 0
    reviewed_published: int = 0
    abstained: int = 0
    evaluated: int = 0
    unresolved_identity: int = 0
    body_unavailable: int = 0
    short_cells: int = 0
    rights_blocked: int = 0
    manifest_case_ids: tuple[str, ...] = ()
    output_case_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, int]:
        keys = (
            "manifest_n discovered unique_groups extracted_packets issuer_impacts "
            "deferred rejected quarantined auto_published reviewed_published "
            "abstained evaluated unresolved_identity body_unavailable "
            "short_cells rights_blocked"
        ).split()
        return {k: int(getattr(self, k)) for k in keys}

    def six_way_sum(self) -> int:
        return int(
            self.deferred
            + self.rejected
            + self.quarantined
            + self.auto_published
            + self.reviewed_published
            + self.abstained
        )

    def complete(self) -> bool:
        """A3 4.8 F1: 1 iff every manifest case has exactly one output and the
        six-way counts sum to manifest_n."""
        if self.six_way_sum() != self.manifest_n:
            return False
        if self.manifest_case_ids or self.output_case_ids:
            return sorted(self.manifest_case_ids) == sorted(self.output_case_ids)
        return True


@dataclass(frozen=True)
class CostRecord:
    """Measured resource use for one construction (a cost, never a quality signal)."""

    baseline_id: str
    ablation_id: str
    tokens_in: int
    tokens_out: int

    def total_tokens(self) -> int:
        return int(self.tokens_in) + int(self.tokens_out)


@dataclass(frozen=True)
class BaselineSpec:
    baseline_id: str
    consumes: tuple[str, ...]
    emits_packet: bool
    population: str


@dataclass(frozen=True)
class AblationSwitch:
    switch: str
    removes: str


@dataclass(frozen=True)
class RegistryMetric:
    metric_id: str
    family: str
    predictive_weight: str
    proposed_bar: Any
    unit_of_analysis: str = ""
    formula: str = ""


@dataclass(frozen=True)
class EndpointRegistry:
    baselines: tuple[BaselineSpec, ...]
    ablations: tuple[AblationSwitch, ...]
    metrics: tuple[RegistryMetric, ...]
    bootstrap_seed: int
    bootstrap_reps: int
    interval_coverage: float
    undecidable_metric_id: str
    undecidable_n_groups_needed: int
    undecidable_n_cases: Mapping[str, Any]
    sha256: str


# ------------------------------------------------- endpoint spec table (declarative)


@dataclass(frozen=True)
class EndpointSpec:
    """How one endpoint is computed from graded items, or why it is not."""

    metric_id: str
    family: str
    predictive_weight: str
    kind: str                       # rate | mean | count | accounting | cost
    item_field: str | None = None   # None -> computed from injected inputs
    critical_fields: bool = False   # selector matches CRITICAL_NUMERIC_FIELDS
    population_note: str = ""       # exact notes token ("" = default population)
    positive: tuple[str, ...] = ()
    total: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    extra_input: str = ""           # accounting | costs | registry_undecidable
    qa_only_flag: bool = True


def _rate(
    metric_id: str,
    family: str,
    item_field: str,
    positive: tuple[str, ...],
    total: tuple[str, ...],
    **kw: Any,
) -> EndpointSpec:
    return EndpointSpec(
        metric_id=metric_id, family=family, predictive_weight="qa_only",
        kind="rate", item_field=item_field, positive=positive, total=total, **kw,
    )


def _prospective(
    metric_id: str,
    family: str,
    item_field: str,
    positive: tuple[str, ...],
    total: tuple[str, ...],
    missing: tuple[str, ...] = (),
    **kw: Any,
) -> EndpointSpec:
    return EndpointSpec(
        metric_id=metric_id, family=family, predictive_weight="prospective_primary",
        kind="rate", item_field=item_field, positive=positive, total=total,
        missing=missing, **kw,
    )


ENDPOINT_SPECS: tuple[EndpointSpec, ...] = (
    # F1 fact_integrity (A3 4.8)
    EndpointSpec(
        metric_id="critical_numeric_correctness_auto_published",
        family="fact_integrity", predictive_weight="qa_only", kind="rate",
        critical_fields=True, population_note="",
        positive=("correct",),
        total=("correct", "wrong_value", "wrong_absence", "unevidenced"),
    ),
    EndpointSpec(
        metric_id="critical_numeric_correctness_all_dispositions",
        family="fact_integrity", predictive_weight="qa_only", kind="rate",
        critical_fields=True, population_note=POP_ALL_DISPOSITIONS,
        positive=("correct",),
        total=("correct", "wrong_value", "wrong_absence", "unevidenced"),
    ),
    EndpointSpec(
        metric_id="absence_correctness",
        family="fact_integrity", predictive_weight="qa_only", kind="rate",
        critical_fields=True, population_note=POP_GOLD_ABSENT,
        positive=("correct",), total=("correct", "wrong_absence"),
    ),
    _rate("span_replay_pass_rate", "fact_integrity", "span_replay",
          ("pass",), ("pass", "fail")),
    _rate("correction_replay_success", "fact_integrity", "correction_replay",
          ("success",), ("success", "failure")),
    EndpointSpec(
        metric_id="disposition_accounting_complete",
        family="fact_integrity", predictive_weight="not_a_rate", kind="accounting",
        item_field=None, extra_input="accounting", qa_only_flag=False,
    ),
    # F2 clustering_integrity
    _rate("pair_precision", "clustering_integrity", "pair_joined",
          ("same_gold_group",), ("same_gold_group", "different_gold_group")),
    _rate("pair_recall", "clustering_integrity", "gold_pair",
          ("system_joined",), ("system_joined", "system_split")),
    _rate("false_event_merge_rate", "clustering_integrity", "system_cluster",
          ("mixed",), ("mixed", "pure")),
    _rate("missed_novel_term_rate", "clustering_integrity", "novelty_term",
          ("missed",), ("missed", "caught")),
    _rate("root_source_independence_hold", "clustering_integrity",
          "group_independence", ("hold",), ("hold", "violation")),
    # F3 routing_quality
    _rate("material_event_routing_recall", "routing_quality", "material_routing",
          ("hit",), ("hit", "miss")),
    EndpointSpec(
        metric_id="cost_at_fixed_recall", family="routing_quality",
        predictive_weight="not_a_rate", kind="cost", item_field=None,
        extra_input="costs",
    ),
    _rate("strategic_nonnumeric_coverage", "routing_quality",
          "strategic_nonnumeric", ("published",), ("published", "dropped")),
    _rate("reject_audit_miss_rate", "routing_quality", "reject_audit",
          ("auto_published",), ("auto_published", "not_published")),
    _rate("defer_disposition_match", "routing_quality", "defer_match",
          ("matched",), ("matched", "not_matched")),
    # F4 economic_reasoning
    _rate("mechanism_follows_from_source", "economic_reasoning",
          "mechanism_follows", ("allowed",), ("allowed", "not_allowed")),
    _rate("negative_channel_represented", "economic_reasoning",
          "negative_channel", ("represented",), ("represented", "missing")),
    _rate("contrary_quote_present_when_required", "economic_reasoning",
          "contrary_quote", ("present",), ("present", "missing")),
    # F5 business_outcomes (missing outcomes remain missing: A3 4.8)
    _prospective("period_matched_revision_hit", "business_outcomes",
                 "revision_hit", ("agree",), ("agree", "disagree"),
                 missing=("unmatured",)),
    _prospective("reported_operating_change_agree", "business_outcomes",
                 "operating_change", ("agree",), ("agree", "disagree"),
                 missing=("unmatured",)),
    _prospective("actual_buyback_execution", "business_outcomes",
                 "buyback_execution", ("agree",), ("agree", "disagree"),
                 missing=("unmatured",)),
    _prospective("preregistered_strategic_milestone", "business_outcomes",
                 "milestone_observed", ("observed",), ("observed", "not_observed"),
                 missing=("unmatured",)),
    # F6 market_outcomes (means of candidate_value; missing printed)
    EndpointSpec(
        metric_id="net_return_horizon", family="market_outcomes",
        predictive_weight="prospective_primary", kind="mean",
        item_field="net_return", positive=("observed",),
        missing=("missing",),
    ),
    EndpointSpec(
        metric_id="group_relative_return", family="market_outcomes",
        predictive_weight="prospective_primary", kind="mean",
        item_field="group_relative_return", positive=("observed",),
        missing=("missing",),
    ),
    EndpointSpec(
        metric_id="drawdown_window", family="market_outcomes",
        predictive_weight="prospective_primary", kind="mean",
        item_field="drawdown", positive=("observed",),
        missing=("missing",),
    ),
    _prospective("coverage_rate", "market_outcomes", "return_coverage",
                 ("computed",), ("computed", "not_computed")),
    # The A3 4.11 zero bar lives outside families[] (endpoints.v1.json
    # undecidable_at_600); family assignment routing_quality is this lane's,
    # recorded in the return packet.
    EndpointSpec(
        metric_id="unsupported_ticker_to_supplier_count",
        family="routing_quality", predictive_weight="qa_only", kind="count",
        item_field="unsupported_transfer", positive=("yes",),
        total=("yes", "no"), extra_input="registry_undecidable",
    ),
)
SPECS_BY_ID: dict[str, EndpointSpec] = {s.metric_id: s for s in ENDPOINT_SPECS}


# ---------------------------------------------------------------- helpers


def canonical_json(obj: Any) -> str:
    """Canonical JSON (A3 / W3-R2): sorted keys, compact, unicode-preserving."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def default_registry_path() -> Path:
    """Frozen endpoints registry location (final repository layout)."""
    return (
        Path(__file__).resolve().parents[2]
        / "contracts"
        / "news_impact"
        / "endpoints.v1.json"
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_registry(path: str | Path | None = None) -> EndpointRegistry:
    """Parse the frozen endpoints registry (lazy read; no module-level I/O)."""
    p = Path(path) if path is not None else default_registry_path()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvalReceiptError("BAD_REGISTRY", str(exc)) from exc
    try:
        baselines = tuple(
            BaselineSpec(
                baseline_id=str(b["baseline_id"]),
                consumes=tuple(str(c) for c in b.get("consumes", ())),
                emits_packet=bool(b.get("emits_packet", False)),
                population=str(b.get("population", "")),
            )
            for b in raw["baselines"]
        )
        ablations = tuple(
            AblationSwitch(switch=str(a["switch"]), removes=str(a.get("removes", "")))
            for a in raw["ablations"]
        )
        metrics: list[RegistryMetric] = []
        for fam in raw["families"]:
            for m in fam["metrics"]:
                metrics.append(
                    RegistryMetric(
                        metric_id=str(m["metric_id"]),
                        family=str(fam["family"]),
                        predictive_weight=str(fam["predictive_weight"]),
                        proposed_bar=m.get("proposed_bar"),
                        unit_of_analysis=str(m.get("unit_of_analysis", "")),
                        formula=str(m.get("formula", "")),
                    )
                )
        und = raw["undecidable_at_600"]
        registry = EndpointRegistry(
            baselines=baselines,
            ablations=ablations,
            metrics=tuple(metrics),
            bootstrap_seed=int(raw["bootstrap_seed"]),
            bootstrap_reps=int(raw["bootstrap_reps"]),
            interval_coverage=float(raw["interval_coverage"]),
            undecidable_metric_id=str(und["metric_id"]),
            undecidable_n_groups_needed=int(und["n_independent_groups_needed"]),
            undecidable_n_cases=dict(und.get("n_cases_after_deff", {})),
            sha256=_sha256_file(p),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise EvalReceiptError("BAD_REGISTRY", str(exc)) from exc
    spec_ids = set(SPECS_BY_ID)
    reg_ids = {m.metric_id for m in registry.metrics} | {registry.undecidable_metric_id}
    if spec_ids != reg_ids:
        raise EvalReceiptError(
            "BAD_REGISTRY",
            f"spec table does not match registry: only_specs={sorted(spec_ids - reg_ids)} "
            f"only_registry={sorted(reg_ids - spec_ids)}",
        )
    if registry.bootstrap_seed != BOOTSTRAP_SEED or registry.bootstrap_reps != BOOTSTRAP_REPS:
        raise EvalReceiptError("BAD_REGISTRY", "seed/reps drifted from frozen values")
    return registry


def ablation_id_from_switches(removed: Iterable[str]) -> str:
    """A3 4.10: ``full`` or sorted ``+``-joined minus-prefixed removed switches."""
    r = sorted(set(removed))
    return "full" if not r else "+".join(f"minus_{s}" for s in r)


def strip_forbidden_keys(tree: Any) -> tuple[Any, list[str]]:
    """W3-R3: recursively drop keys matching the forbidden pattern; return
    (clean tree, stripped key paths)."""
    if isinstance(tree, dict):
        out: dict[str, Any] = {}
        stripped: list[str] = []
        for k in sorted(tree, key=str):
            if _FORBIDDEN_KEY_RE.search(str(k)):
                stripped.append(str(k))
                continue
            v, s = strip_forbidden_keys(tree[k])
            out[str(k)] = v
            stripped.extend(f"{k}.{p}" for p in s)
        return out, stripped
    if isinstance(tree, list):
        out_l: list[Any] = []
        stripped_l: list[str] = []
        for i, v in enumerate(tree):
            cv, s = strip_forbidden_keys(v)
            out_l.append(cv)
            stripped_l.extend(f"[{i}].{p}" for p in s)
        return out_l, stripped_l
    return tree, []


def lint_display_text(text: str) -> str:
    """A3 4.14: windows and counts, never proves/falsifies/guarantee/will."""
    if _DISPLAY_FORBIDDEN_RE.search(text):
        raise EvalReceiptError("DISPLAY_FORBIDDEN_WORD", text[:120])
    return text


# ----------------------------------------------------------- statistics


def _betacf(a: float, b: float, x: float) -> float:
    max_it, eps, fpmin = 300, 3e-12, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, max_it + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _reg_inc_beta(x: float, a: float, b: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln_bt = (
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log1p(-x)
    )
    bt = math.exp(ln_bt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _beta_quantile(p: float, a: float, b: float) -> float:
    lo, hi = 0.0, 1.0
    for _ in range(200):  # fixed iterations: deterministic
        mid = (lo + hi) / 2.0
        if _reg_inc_beta(mid, a, b) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _interval(low: float | None, high: float | None, method: str, coverage: float) -> dict[str, Any]:
    return {"low": low, "high": high, "method": method, "coverage": coverage}


def clopper_pearson_interval(k: int, n: int, coverage: float = INTERVAL_COVERAGE) -> dict[str, Any] | None:
    """Naive i.i.d. diagnostic (A3 4.7); None on zero denominator."""
    if n <= 0:
        return None
    alpha = 1.0 - coverage
    low = 0.0 if k == 0 else _beta_quantile(alpha / 2.0, float(k), float(n - k + 1))
    high = 1.0 if k == n else _beta_quantile(1.0 - alpha / 2.0, float(k + 1), float(n - k))
    return _interval(low, high, "clopper_pearson_diagnostic", coverage)


def wilson_interval(k: int, n: int, coverage: float = INTERVAL_COVERAGE) -> dict[str, Any] | None:
    """Naive i.i.d. diagnostic (A3 4.7); None on zero denominator."""
    if n <= 0:
        return None
    if coverage not in Z_BY_COVERAGE:
        raise EvalReceiptError("BAD_COVERAGE", f"z not tabulated for coverage {coverage}")
    z = Z_BY_COVERAGE[coverage]
    phat = k / n
    z2 = z * z
    den = 1.0 + z2 / n
    centre = (phat + z2 / (2.0 * n)) / den
    half = z * math.sqrt(phat * (1.0 - phat) / n + z2 / (4.0 * n * n)) / den
    return _interval(centre - half, centre + half, "wilson_diagnostic", coverage)


def cluster_bootstrap_interval(
    values: Sequence[float],
    cluster_ids: Sequence[str],
    *,
    seed: int = BOOTSTRAP_SEED,
    reps: int = BOOTSTRAP_REPS,
    coverage: float = INTERVAL_COVERAGE,
) -> dict[str, Any]:
    """Governing interval: percentile bootstrap resampling CLUSTER group ids
    with replacement (A3 4.7). Reporting floor A5: n<30 or clusters<10 ->
    method not_estimable."""
    if len(values) != len(cluster_ids):
        raise EvalReceiptError("CLUSTER_ID_MISSING", "values/cluster_ids length mismatch")
    n = len(values)
    by_cluster: dict[str, list[float]] = {}
    for cid, v in zip(cluster_ids, values):
        by_cluster.setdefault(cid, []).append(float(v))
    ordered = sorted(by_cluster)
    n_clusters = len(ordered)
    if n < MIN_N_FOR_INTERVAL or n_clusters < MIN_CLUSTERS_FOR_INTERVAL:
        return _interval(None, None, "not_estimable", coverage)
    sums = [math.fsum(by_cluster[c]) for c in ordered]
    lens = [len(by_cluster[c]) for c in ordered]
    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(reps):
        s_tot = 0.0
        l_tot = 0
        for _ in range(n_clusters):
            j = rng.randrange(n_clusters)
            s_tot += sums[j]
            l_tot += lens[j]
        means.append(s_tot / l_tot)
    means.sort()
    alpha = (1.0 - coverage) / 2.0
    lo = means[int(alpha * reps)]
    hi = means[min(reps - 1, int((1.0 - alpha) * reps))]
    return _interval(lo, hi, "cluster_bootstrap_percentile", coverage)


def two_way_cgm_interval(
    values: Sequence[float],
    group_ids: Sequence[str],
    issuer_ids: Sequence[str],
    coverage: float = INTERVAL_COVERAGE,
) -> dict[str, Any] | None:
    """Cameron-Gelbach-Miller two-way (group x issuer) sandwich CI for the mean.

    A3 4.7 names this a second governing method when n_issuers >= 20; the
    receipt schema has no second-governing slot, so it is exposed here only.
    """
    n = len(values)
    if n == 0 or coverage not in Z_BY_COVERAGE:
        return None
    mean = math.fsum(float(v) for v in values) / n
    resid = [float(v) - mean for v in values]
    sg: dict[str, float] = {}
    sc: dict[str, float] = {}
    sgc: dict[tuple[str, str], float] = {}
    for g, c, e in zip(group_ids, issuer_ids, resid):
        sg[g] = sg.get(g, 0.0) + e
        sc[c] = sc.get(c, 0.0) + e
        sgc[(g, c)] = sgc.get((g, c), 0.0) + e
    G, C, GC = len(sg), len(sc), len(sgc)
    if G < 2 or C < 2 or GC < 2:
        return None
    var = (
        G / (G - 1) * math.fsum(v * v for v in sg.values())
        + C / (C - 1) * math.fsum(v * v for v in sc.values())
        - GC / (GC - 1) * math.fsum(v * v for v in sgc.values())
    ) / (n * n)
    half = Z_BY_COVERAGE[coverage] * math.sqrt(max(var, 0.0))
    return _interval(mean - half, mean + half, "two_way_cluster_cgm", coverage)


# ------------------------------------------------------- threshold machinery


def evaluate_threshold(
    bar: float | bool | None,
    observed: float | bool | None,
    governing: Mapping[str, Any] | None,
    naive_cp: Mapping[str, Any] | None,
    *,
    undecidable: bool = False,
) -> dict[str, Any]:
    """crossing + dependence_dispute. Schema crossing enum wins over the
    design's ``disputed_dependence`` token (see module docstring)."""
    if undecidable or bar is None or observed is None:
        return {"crossing": "not_evaluable", "dependence_dispute": False}
    if isinstance(bar, bool):
        ok = observed is True
        return {"crossing": "meets" if ok else "below", "dependence_dispute": False}
    obs = float(observed)  # type: ignore[arg-type]
    gov = governing if governing is not None and governing.get("method") != "not_estimable" else None
    if gov is None or gov.get("low") is None:
        return {"crossing": "not_evaluable", "dependence_dispute": False}
    low, high = float(gov["low"]), float(gov["high"])
    if low >= bar:
        crossing = "meets"
    elif high < bar:
        crossing = "below"
    else:
        crossing = "straddles"
    gov_clears = low >= bar
    naive_clears = (
        naive_cp is not None and naive_cp.get("low") is not None
        and float(naive_cp["low"]) >= bar
    )
    dispute = gov_clears != naive_clears
    return {"crossing": crossing, "dependence_dispute": dispute}


# ---------------------------------------------------------- leakage audit


def audit_leakage(
    items: Iterable[GradedItem],
    *,
    mode: str,
    registration: Mapping[str, Any],
    registry_sha256: str | None = None,
    prospective_labels_loaded: bool = False,
    prospective_outputs_in_tune: bool = False,
    prompt_corpus_hit: bool = False,
    outcome_conditioned_selection: bool = False,
) -> dict[str, Any]:
    """A3 4.13. Prospective and sealed folds are refused with coded errors
    (lane ruling: folds f1..f5 only)."""
    if registry_sha256 is None:
        registry_sha256 = load_registry().sha256
    findings: list[str] = []
    for it in items:
        if it.fold == "prospective":
            raise EvalReceiptError("PROSPECTIVE_FOLD_REFUSED", it.case_id)
        if it.fold not in HISTORICAL_FOLDS:
            raise EvalReceiptError("SEALED_FOLD_REFUSED", f"{it.case_id}:{it.fold}")
    reg_sha = registration.get("endpoints_sha256")
    if reg_sha != registry_sha256:
        raise EvalReceiptError("ENDPOINTS_SHA_MISMATCH", f"registration={reg_sha}")
    if mode in ("tune", "select") and prospective_labels_loaded:
        findings.append(f"prospective_label_loaded_in_{mode}")
    if prospective_outputs_in_tune:
        findings.append("prospective_output_present")
    if prompt_corpus_hit:
        findings.append("prompt_corpus_contains_prospective_identifier")
    if outcome_conditioned_selection:
        findings.append("outcome_conditioned_selection")
    return {
        "passed": not findings,
        "mode": mode,
        "t_prospective": registration["t_prospective"],
        "endpoints_sha256": registry_sha256,
        "prompt_corpus_sha256": registration.get("prompt_corpus_sha256"),
        "prospective_labels_loaded": bool(prospective_labels_loaded),
        "prospective_outputs_in_tune": bool(prospective_outputs_in_tune),
        "prompt_corpus_hit": bool(prompt_corpus_hit),
        "outcome_conditioned_selection": bool(outcome_conditioned_selection),
        "findings": sorted(findings),
    }


# ------------------------------------------------------------- registration


def make_registration(
    *,
    tape_sha256: str,
    sampler_version: str,
    sampling_seed: int,
    t_prospective: str,
    mode: str,
    prompt_corpus_sha256: str | None = None,
    endpoints_sha256: str | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    """Registration pin (A3 4.12): frozen endpoint sha, seeds, T_prospective."""
    sha = endpoints_sha256 if endpoints_sha256 is not None else load_registry(registry_path).sha256
    return {
        "endpoints_sha256": sha,
        "contract_sha256_prefix": CONTRACT_SHA256_PREFIX,
        "tape_sha256": tape_sha256,
        "sampler_version": sampler_version,
        "sampling_seed": int(sampling_seed),
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_reps": BOOTSTRAP_REPS,
        "interval_coverage": INTERVAL_COVERAGE,
        "t_prospective": t_prospective,
        "prompt_corpus_sha256": prompt_corpus_sha256,
        "owner_status": "PROPOSED-OWNER-FREEZES",
        "mode": mode,
    }


# ------------------------------------------------------------ metric core


def _select(items: Sequence[GradedItem], spec: EndpointSpec) -> list[GradedItem]:
    if spec.critical_fields:
        return [
            it for it in items
            if it.field in CRITICAL_NUMERIC_FIELDS and it.notes == spec.population_note
        ]
    assert spec.item_field is not None
    return [it for it in items if it.field == spec.item_field]


def _clusters_and_issuers(
    denom: Sequence[GradedItem],
    cluster_map: Mapping[str, str],
    issuer_map: Mapping[str, str],
) -> tuple[list[str], int]:
    cids: list[str] = []
    for it in denom:
        try:
            cids.append(cluster_map[it.case_id])
        except KeyError as exc:
            raise EvalReceiptError("CLUSTER_ID_MISSING", it.case_id) from exc
    issuers = {issuer_map[it.case_id] for it in denom if it.case_id in issuer_map}
    return cids, len(sorted(issuers))


def _check_duplicates(items: Sequence[GradedItem], spec: EndpointSpec) -> None:
    if spec.item_field is None and not spec.critical_fields:
        return  # accounting/cost specs consume injected inputs, not graded items
    seen: set[tuple[str, str]] = set()
    for it in _select(items, spec):
        key = (it.case_id, it.field)
        if key in seen:
            raise EvalReceiptError("DUPLICATE_GRADED_ITEM", f"{it.case_id}:{it.field}")
        seen.add(key)


def _fmt(x: float) -> str:
    return f"{x:.4f}"


def _rate_row(
    spec: EndpointSpec,
    items: Sequence[GradedItem],
    cluster_map: Mapping[str, str],
    issuer_map: Mapping[str, str],
    slice_label: str,
    registry: EndpointRegistry,
) -> dict[str, Any]:
    sel = _select(items, spec)
    denom = [it for it in sel if it.outcome in spec.total]
    pos = [it for it in denom if it.outcome in spec.positive]
    n_missing = sum(1 for it in sel if it.outcome in spec.missing)
    n = len(denom)
    coverage = registry.interval_coverage
    if n == 0:
        value: float | None = None
        interval = None
        cp = wilson = None
        status = "null_printed"
        n_clusters = 0
        n_issuers = 0
        display = lint_display_text(
            f"On the {slice_label} sample this metric has no denominator items "
            f"(null_reason={NULL_REASON_ZERO_DENOMINATOR}); value is null, n=0."
        )
    else:
        value = len(pos) / n
        cids, n_issuers = _clusters_and_issuers(denom, cluster_map, issuer_map)
        n_clusters = len(set(cids))
        interval = cluster_bootstrap_interval(
            [1.0 if it.outcome in spec.positive else 0.0 for it in denom],
            cids,
            seed=registry.bootstrap_seed,
            reps=registry.bootstrap_reps,
            coverage=coverage,
        )
        cp = clopper_pearson_interval(len(pos), n, coverage)
        wilson = wilson_interval(len(pos), n, coverage)
        if spec.predictive_weight == "prospective_primary" and slice_label != "prospective":
            status = "qa_only"
        elif interval["method"] == "not_estimable":
            status = "not_estimable"
        else:
            status = "measured"
        if interval["method"] == "not_estimable":
            iv_txt = "the dependence-aware interval is not estimable at this sample size"
        else:
            iv_txt = (
                f"the dependence-aware interval on this sample is "
                f"{_fmt(float(interval['low']))} to {_fmt(float(interval['high']))}"
            )
        display = lint_display_text(
            f"On the {slice_label} sample, {len(pos)} of {n} units met the rule "
            f"({_fmt(value)}). {iv_txt}. This describes the sample, not future packets."
        )
    return {
        "value": value,
        "n": n,
        "n_clusters": n_clusters,
        "n_issuers": n_issuers,
        "n_missing": n_missing,
        "interval": interval,
        "interval_diagnostic_cp": cp,
        "interval_diagnostic_wilson": wilson,
        "status": status,
        "display_text": display,
    }


def _mean_row(
    spec: EndpointSpec,
    items: Sequence[GradedItem],
    cluster_map: Mapping[str, str],
    issuer_map: Mapping[str, str],
    slice_label: str,
    registry: EndpointRegistry,
) -> dict[str, Any]:
    sel = _select(items, spec)
    observed: list[GradedItem] = [it for it in sel if it.outcome in spec.positive]
    n_missing = sum(1 for it in sel if it.outcome in spec.missing)
    coverage = registry.interval_coverage
    vals: list[float] = []
    for it in observed:
        if not isinstance(it.candidate_value, (int, float)) or isinstance(it.candidate_value, bool):
            raise EvalReceiptError("BAD_METRIC_VALUE", f"{it.case_id}:{it.field}")
        vals.append(float(it.candidate_value))
    n = len(vals)
    if n == 0:
        value = None
        interval = None
        status = "null_printed"
        n_clusters = n_issuers = 0
        display = lint_display_text(
            f"On the {slice_label} sample no outcome observation matured "
            f"(null_reason={NULL_REASON_ZERO_DENOMINATOR}); value is null, "
            f"n_missing={n_missing}."
        )
    else:
        value = math.fsum(vals) / n
        cids, n_issuers = _clusters_and_issuers(observed, cluster_map, issuer_map)
        n_clusters = len(set(cids))
        interval = cluster_bootstrap_interval(
            vals, cids, seed=registry.bootstrap_seed, reps=registry.bootstrap_reps, coverage=coverage
        )
        if slice_label != "prospective":
            status = "qa_only"
        elif interval["method"] == "not_estimable":
            status = "not_estimable"
        else:
            status = "measured"
        display = lint_display_text(
            f"On the {slice_label} sample the mean over {n} observed units is "
            f"{_fmt(value)} (n_missing={n_missing}). This describes the sample, "
            f"not future packets."
        )
    return {
        "value": value,
        "n": n,
        "n_clusters": n_clusters,
        "n_issuers": n_issuers,
        "n_missing": n_missing,
        "interval": interval,
        "interval_diagnostic_cp": None,
        "interval_diagnostic_wilson": None,
        "status": status,
        "display_text": display,
    }


def _count_row(
    spec: EndpointSpec,
    items: Sequence[GradedItem],
    cluster_map: Mapping[str, str],
    issuer_map: Mapping[str, str],
    slice_label: str,
    registry: EndpointRegistry,
) -> dict[str, Any]:
    sel = _select(items, spec)
    denom = [it for it in sel if it.outcome in spec.total]
    pos = [it for it in denom if it.outcome in spec.positive]
    n = len(denom)
    count = len(pos)
    rate = (count / n) if n else None
    n_groups = registry.undecidable_n_groups_needed
    lo, hi = (
        registry.undecidable_n_cases.get("low"),
        registry.undecidable_n_cases.get("high"),
    )
    rate_txt = "undefined" if rate is None else _fmt(rate)
    display = lint_display_text(
        f"On the {slice_label} sample, {count} of {n} accepted units carry an "
        f"unsupported ticker-to-supplier assertion (rate {rate_txt}). The zero bar "
        f"is undecidable_at_n: about {n_groups} independent groups are required "
        f"({lo} to {hi} cases after design-effect inflation). This describes the "
        f"sample, not future packets."
    )
    cids: list[str] = []
    if denom:
        cids, n_issuers = _clusters_and_issuers(denom, cluster_map, issuer_map)
    else:
        n_issuers = 0
    return {
        "value": float(count),
        "n": n,
        "n_clusters": len(set(cids)) if cids else 0,
        "n_issuers": n_issuers,
        "n_missing": 0,
        "interval": None,
        "interval_diagnostic_cp": None,
        "interval_diagnostic_wilson": None,
        "status": "measured",
        "display_text": display,
    }


def _accounting_row(accounting: AccountingInput, slice_label: str) -> dict[str, Any]:
    ok = accounting.complete()
    display = lint_display_text(
        f"On the {slice_label} sample the six-way disposition counts "
        f"{'sum to' if ok else 'do not sum to'} manifest_n={accounting.manifest_n}; "
        f"value {'1' if ok else '0'}, nulls are forbidden on this endpoint."
    )
    return {
        "value": 1.0 if ok else 0.0,
        "n": accounting.manifest_n,
        "n_clusters": 0,
        "n_issuers": 0,
        "n_missing": 0,
        "interval": None,
        "interval_diagnostic_cp": None,
        "interval_diagnostic_wilson": None,
        "status": "measured",
        "display_text": display,
    }


def _recall_f1_f4(items: Sequence[GradedItem]) -> float | None:
    denom = [it for it in items if it.field == "material_routing" and it.outcome in ("hit", "miss")]
    if not denom:
        return None
    return sum(1 for it in denom if it.outcome == "hit") / len(denom)


def _cost_rows(
    graded_by_construction: Mapping[tuple[str, str], Sequence[GradedItem]],
    costs: Mapping[tuple[str, str], CostRecord],
    constructions: Sequence[tuple[str, str]],
    slice_label: str,
) -> dict[tuple[str, str], dict[str, Any]]:
    """median tokens among constructions reaching recall >= 0.95 on f1-f4,
    evaluated on f5 (A3 4.8 F3); null when no run reaches the bar."""
    qualifying: list[tuple[str, str]] = []
    recall_by: dict[tuple[str, str], float | None] = {}
    for key in constructions:
        items = graded_by_construction.get(key, ())
        f14 = [it for it in items if it.fold in ("f1", "f2", "f3", "f4")]
        r = _recall_f1_f4(f14)
        recall_by[key] = r
        if r is not None and r >= 0.95:
            qualifying.append(key)
    tokens_list = sorted(
        costs[k].total_tokens() for k in qualifying if k in costs
    )
    median: float | None = None
    if tokens_list:
        m = len(tokens_list)
        median = (
            float(tokens_list[m // 2]) if m % 2
            else (tokens_list[m // 2 - 1] + tokens_list[m // 2]) / 2.0
        )
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for key in constructions:
        b, a = key
        if slice_label != "f5":
            value, reason, status, n = None, "f5_only_metric", "null_printed", 0
        elif not qualifying:
            value, reason, status, n = None, "no_run_reaches_recall_bar", "null_printed", 0
        elif key not in costs:
            value, reason, status, n = None, "cost_record_missing", "null_printed", len(qualifying)
        elif recall_by.get(key) is None or recall_by[key] < 0.95:  # type: ignore[operator]
            value, reason, status, n = None, "recall_below_0.95", "null_printed", len(qualifying)
        else:
            value, reason, status, n = median, "", "measured", len(qualifying)
        if value is None:
            display = lint_display_text(
                f"On the f5 slice, cost at fixed recall is null for {b}+{a} "
                f"(null_reason={reason})."
            )
        else:
            display = lint_display_text(
                f"On the f5 slice, median tokens in+out among the {n} constructions "
                f"reaching recall >= 0.95 on f1-f4 is {value:.0f}. This describes "
                f"the sample, not future packets."
            )
        rows[key] = {
            "value": value,
            "n": n,
            "n_clusters": 0,
            "n_issuers": 0,
            "n_missing": 0,
            "interval": None,
            "interval_diagnostic_cp": None,
            "interval_diagnostic_wilson": None,
            "status": status,
            "display_text": display,
        }
    return rows


# ---------------------------------------------------------- receipt assembly


def _metric_rows_for_construction(
    key: tuple[str, str],
    items: Sequence[GradedItem],
    accounting: AccountingInput,
    cluster_map: Mapping[str, str],
    issuer_map: Mapping[str, str],
    registry: EndpointRegistry,
    fold_slices: Sequence[str],
) -> list[dict[str, Any]]:
    baseline_id, ablation_id = key
    rows: list[dict[str, Any]] = []
    have_items = bool(items)
    for spec in ENDPOINT_SPECS:
        for slice_label in fold_slices:
            if spec.kind == "accounting":
                core = _accounting_row(accounting, slice_label)
            elif spec.kind == "cost":
                continue  # handled once per slice across constructions
            elif not have_items:
                reason = (
                    "not_in_audit_subset"
                    if baseline_id == "frontier_only_audit"
                    else "no_graded_items_for_construction"
                )
                core = {
                    "value": None, "n": 0, "n_clusters": 0, "n_issuers": 0,
                    "n_missing": 0, "interval": None,
                    "interval_diagnostic_cp": None,
                    "interval_diagnostic_wilson": None,
                    "status": "null_printed",
                    "display_text": lint_display_text(
                        f"On the {slice_label} sample, {spec.metric_id} is null for "
                        f"{baseline_id}+{ablation_id} (null_reason={reason})."
                    ),
                }
            else:
                sub = [
                    it for it in items
                    if it.fold in HISTORICAL_FOLDS
                    and (slice_label == "all_historical" or it.fold == slice_label)
                ]
                if spec.kind == "rate":
                    core = _rate_row(spec, sub, cluster_map, issuer_map, slice_label, registry)
                elif spec.kind == "mean":
                    core = _mean_row(spec, sub, cluster_map, issuer_map, slice_label, registry)
                else:
                    core = _count_row(spec, sub, cluster_map, issuer_map, slice_label, registry)
            rows.append(
                {
                    "metric_id": spec.metric_id,
                    "family": spec.family,
                    "baseline_id": baseline_id,
                    "ablation_id": ablation_id,
                    "fold_slice": slice_label,
                    **core,
                    "qa_only": spec.qa_only_flag,
                    "predictive_weight": spec.predictive_weight,
                }
            )
    return rows


def _threshold_rows(
    metric_rows: Sequence[Mapping[str, Any]],
    registry: EndpointRegistry,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Threshold rows only for metrics with a representable proposed bar
    (A3 4.11; registry string bars map to null and are skipped)."""
    bar_by_metric: dict[str, Any] = {}
    for m in registry.metrics:
        bar = m.proposed_bar
        if isinstance(bar, str):
            continue  # "success_on_subset" is not representable; schema wins
        if bar is not None:
            bar_by_metric[m.metric_id] = bar
    bar_by_metric[registry.undecidable_metric_id] = 0  # A3 4.11 zero bar
    rows: list[dict[str, Any]] = []
    kills: list[dict[str, Any]] = []
    by_key = {
        (r["metric_id"], r["baseline_id"], r["ablation_id"], r["fold_slice"]): r
        for r in metric_rows
    }
    for (mid, b, a, sl), r in sorted(by_key.items()):
        if mid not in bar_by_metric:
            continue
        bar = bar_by_metric[mid]
        undecidable = mid in UNDECIDABLE_ZERO_BARS
        observed: float | bool | None
        if mid == "disposition_accounting_complete":
            observed = r["value"] == 1.0
        else:
            observed = r["value"]
        verdict = evaluate_threshold(
            bar, observed, r["interval"], r["interval_diagnostic_cp"], undecidable=undecidable
        )
        rows.append(
            {
                "metric_id": mid,
                "baseline_id": b,
                "ablation_id": a,
                "fold_slice": sl,
                "proposed_bar": bar,
                "owner_status": "PROPOSED-OWNER-FREEZES",
                "observed": observed,
                "n": r["n"],
                "crossing": verdict["crossing"],
                "dependence_dispute": verdict["dependence_dispute"],
            }
        )
        if (
            mid == "span_replay_pass_rate"
            and r["value"] is not None
            and r["value"] < 1.0
        ):
            kills.append(
                {
                    "construction_id": f"{b}+{a}+{mid}",
                    "metric_id": mid,
                    "reason": (
                        "span replay failed on at least one auto-published present "
                        "quantity; this construction is closed, the remaining "
                        "constructions stay runnable"
                    ),
                    "search_space_still_open": True,
                }
            )
    rows.sort(key=lambda r: (r["metric_id"], r["baseline_id"], r["ablation_id"], r["fold_slice"]))
    # a kill closes the construction (baseline+ablation+metric), not a slice:
    # collapse duplicate kills across fold slices (A3 4.14 construction law)
    seen_kills: set[tuple[str, str]] = set()
    unique_kills: list[dict[str, Any]] = []
    for k in sorted(kills, key=lambda x: (x["construction_id"], x["metric_id"])):
        key = (k["construction_id"], k["metric_id"])
        if key not in seen_kills:
            seen_kills.add(key)
            unique_kills.append(k)
    return rows, unique_kills


def build_receipt(
    *,
    graded_by_construction: Mapping[tuple[str, str], Iterable[GradedItem]],
    cluster_map: Mapping[str, str],
    issuer_map: Mapping[str, str],
    accounting: AccountingInput,
    registration: Mapping[str, Any],
    costs: Iterable[CostRecord] = (),
    injection_findings: Iterable[Mapping[str, str]] = (),
    fold_slices: Sequence[str] = FOLD_SLICES,
    baselines_run: Sequence[str] | None = None,
    ablations_run: Sequence[str] | None = None,
    prospective_labels_loaded: bool = False,
    prospective_outputs_in_tune: bool = False,
    prompt_corpus_hit: bool = False,
    outcome_conditioned_selection: bool = False,
    registry_path: str | Path | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Assemble an eval_receipt.v1 dict. Pure: every ledger/manifest/cost input
    is injected as data (W3-R4); no clock, no network, no subprocess."""
    registry = load_registry(registry_path)
    if "endpoints_sha256" not in registration or "mode" not in registration or "t_prospective" not in registration:
        raise EvalReceiptError("BAD_REGISTRATION", "missing endpoints_sha256/mode/t_prospective")
    for sl in fold_slices:
        if sl == "prospective":
            raise EvalReceiptError("PROSPECTIVE_FOLD_REFUSED", "fold_slice=prospective")
        if sl not in FOLD_SLICES:
            raise EvalReceiptError("UNKNOWN_FOLD_SLICE", str(sl))

    cleaned: dict[tuple[str, str], list[GradedItem]] = {}
    for key, items in graded_by_construction.items():
        b, a = key
        if b not in {bs.baseline_id for bs in registry.baselines}:
            raise EvalReceiptError("UNKNOWN_BASELINE", b)
        cleaned[(b, a)] = sorted(items, key=lambda it: (it.case_id, it.field, it.outcome))
    all_items = [it for items in cleaned.values() for it in items]

    # Fold discipline first: refuse prospective/sealed before any scoring.
    leakage = audit_leakage(
        all_items,
        mode=str(registration["mode"]),
        registration=registration,
        registry_sha256=registry.sha256,
        prospective_labels_loaded=prospective_labels_loaded,
        prospective_outputs_in_tune=prospective_outputs_in_tune,
        prompt_corpus_hit=prompt_corpus_hit,
        outcome_conditioned_selection=outcome_conditioned_selection,
    )

    for spec in ENDPOINT_SPECS:
        for items in cleaned.values():
            _check_duplicates(items, spec)

    baselines = sorted(baselines_run if baselines_run is not None else {b for b, _ in cleaned})
    for b in baselines:
        if b not in {bs.baseline_id for bs in registry.baselines}:
            raise EvalReceiptError("UNKNOWN_BASELINE", b)
    ablations = sorted(ablations_run if ablations_run is not None else {a for _, a in cleaned})
    constructions = [(b, a) for b in baselines for a in ablations]

    metrics: list[dict[str, Any]] = []
    for key in constructions:
        metrics.extend(
            _metric_rows_for_construction(
                key,
                cleaned.get(key, []),
                accounting,
                cluster_map,
                issuer_map,
                registry,
                fold_slices,
            )
        )
    cost_map = {(c.baseline_id, c.ablation_id): c for c in costs}
    for sl in fold_slices:
        cost_rows = _cost_rows(cleaned, cost_map, constructions, sl)
        for key in constructions:
            b, a = key
            metrics.append(
                {
                    "metric_id": "cost_at_fixed_recall",
                    "family": "routing_quality",
                    "baseline_id": b,
                    "ablation_id": a,
                    "fold_slice": sl,
                    **cost_rows[key],
                    "qa_only": True,
                    "predictive_weight": "not_a_rate",
                }
            )
    metrics.sort(
        key=lambda r: (r["family"], r["metric_id"], r["baseline_id"], r["ablation_id"], r["fold_slice"])
    )

    thresholds, kills = _threshold_rows(metrics, registry)

    reg_clean, reg_stripped = strip_forbidden_keys(dict(registration))
    findings_clean, f_stripped = strip_forbidden_keys(
        [dict(f) for f in injection_findings]
    )
    stripped = [f"registration.{p}" for p in reg_stripped] + [
        f"injection_findings.{p}" for p in f_stripped
    ]
    final_notes = notes or ""
    if stripped:
        tail = "; stripped_fields=" + ",".join(sorted(stripped))
        final_notes = (final_notes + tail)[:2000]

    receipt: dict[str, Any] = {
        "schema": "eval_receipt.v1",
        "authority": "context_only",
        "prophet_flags": {
            "may_rank": False,
            "may_size": False,
            "may_gate": False,
            "prophet_authority": False,
        },
        "registration": reg_clean,
        "accounting": accounting.to_dict(),
        "metrics": metrics,
        "threshold_evaluations": thresholds,
        "kills": kills,
        "leakage_audit": leakage,
        "injection_findings": sorted(
            findings_clean, key=lambda f: (f.get("case_id", ""), f.get("quote", ""))
        ),
        "baselines_run": baselines,
        "ablations_run": ablations,
        "fold_slices_run": sorted(fold_slices),
        "notes": final_notes or None,
    }
    return receipt
