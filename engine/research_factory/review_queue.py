"""engine.research_factory.review_queue — cross-domain review queue builder (W5, RF-5/RF-9/RF-12/RF-16).

Builds the human-review packet list from candidates in `human_review` status
(plus paper candidates flagged for decay review by monitor rows when present,
plus candidates in `awaiting_data` status — blocked on data/label/grader
availability — surfaced as a separate Blocked section,
absent-safe).

Each packet:
  - hypothesis, mechanism
  - candidate_type, domain, track
  - frozen-gate metrics (aggregate, from artifact)
  - mechanical probe flags
  - reviewer blockers, best_counterargument, human_review_question (from challenge file)
  - search_width_at_scan (REQUIRED for oracle candidates — from artifacts;
    loudly 'MISSING' if absent, never silently omitted)
  - crowds_with (per-candidate list: other non-terminal candidates sharing
    entry-rule column-set overlap or same alpha cluster — CONTEXT ONLY;
    RF-16 forbids any composite/fused ranking)
  - allowed_decisions [paper, deferred, rejected, scoped_build]
  - decision_question (the exact question the human must answer)

Queue ordering: category bins (oracle_compound, cortex_hypothesis,
alpha_family, species, external_idea) then created_at. NEVER by a numeric score.

Authority: every artifact row carries "authority": "display_only".

Pure stdlib: no pandas, no yaml, no third-party imports (lazy in-function only).

Charter: research/RESEARCH_FACTORY_MASTERPLAN_BY_FABLE.md §6 W5,
rulings RF-5, RF-9, RF-10, RF-12, RF-16.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_RF_DIR = Path("data") / "research_factory"

# Allowed human decisions from human_review (§4 state machine)
ALLOWED_DECISIONS = ["paper", "deferred", "rejected", "scoped_build"]

# Paper-decay candidates surface for visibility but cannot be decided by decide.py
# until the W6 paper-to-human_review monitor re-transitions them.
# The legal exits from 'paper' per §4 matrix are: promote_eligible, human_review, retired.
# None of those are human decisions accepted by decide.py today (which only accepts
# candidates in human_review).  Mark them clearly so operators don't run a command
# that will always return rc=1.
_PAPER_DECAY_ALLOWED_DECISIONS: list[str] = []  # empty — no runnable decide path yet

# awaiting_data (blocked) candidates surface for operator awareness only.
# No auto-transition is possible until the blocking condition resolves.
# Empty allowed_decisions mirrors paper-decay shape — no runnable decide path.
_AWAITING_DATA_ALLOWED_DECISIONS: list[str] = []  # empty — blocked, no decide action

# Terminal states — excluded from crowds_with candidates pool
_TERMINAL_STATES = frozenset({
    "schema_rejected", "deduped", "numeric_rejected",
    "scoped_build", "rejected", "retired",
})

# Candidate type ordering for queue bins (RF-16 — no numeric composite)
_TYPE_ORDER = [
    "oracle_compound",
    "cortex_hypothesis",
    "alpha_family",
    "species",
    "external_idea",
]


def _type_bin(candidate_type: str | None) -> int:
    """Return the bin index for sorting by category."""
    try:
        return _TYPE_ORDER.index(candidate_type or "")
    except ValueError:
        return len(_TYPE_ORDER)  # unknown types go last


# ---------------------------------------------------------------------------
# I/O helpers (absent-safe, pure stdlib)
# ---------------------------------------------------------------------------


def _load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file absent-safely."""
    if not path.exists():
        return []
    rows: list[dict] = []
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except OSError:
        return []
    return rows


def _load_json(path: Path) -> dict | list | None:
    """Load a JSON file absent-safely."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_challenge(challenges_dir: Path, candidate_id: str) -> dict | None:
    """Load a challenge packet for a candidate_id, absent-safe."""
    path = challenges_dir / f"{candidate_id}.json"
    result = _load_json(path)
    if isinstance(result, dict):
        return result
    return None


def _load_paper_monitor(pm_path: Path, candidate_id: str) -> dict | None:
    """Return the most-recent paper_monitor row for candidate_id, absent-safe."""
    rows = _load_jsonl(pm_path)
    # Most recent = last written per keep-first semantics
    matched = [r for r in rows if r.get("candidate_id") == candidate_id]
    return matched[-1] if matched else None


# ---------------------------------------------------------------------------
# Latest-status resolver
# ---------------------------------------------------------------------------


def _resolve_candidates(candidates_jsonl: list[dict],
                        transitions_jsonl: list[dict]) -> dict[str, dict]:
    """Return latest-state candidates keyed by candidate_id.

    Status is derived from the last transition destination (ground truth).
    """
    # Build latest candidate row (first occurrence wins for initial data)
    by_id: dict[str, dict] = {}
    for row in candidates_jsonl:
        cid = row.get("candidate_id")
        if cid and cid not in by_id:
            by_id[cid] = dict(row)

    # Override status from last transition destination
    last_to: dict[str, str] = {}
    for t in transitions_jsonl:
        cid = t.get("candidate_id")
        if cid:
            last_to[cid] = t.get("to", "")
    for cid, row in by_id.items():
        if cid in last_to:
            row["status"] = last_to[cid]

    return by_id


# ---------------------------------------------------------------------------
# crowds_with computation (RF-16 — context only, no composite)
# ---------------------------------------------------------------------------


def _extract_entry_rule_columns(candidate: dict) -> frozenset[str]:
    """Extract column names from a candidate's entry rule / spec for overlap detection.

    Sources checked (in order, absent-safe):
      1. evaluation_plan.entry_rule_columns  (explicit list)
      2. artifacts.search_columns / screen_columns
      3. hypothesis text (simple word-level extraction, fallback)

    Returns a frozenset of column strings (possibly empty).
    """
    cols: set[str] = set()

    # 1. Explicit columns list in evaluation_plan
    ep = candidate.get("evaluation_plan") or {}
    if isinstance(ep, dict):
        rc = ep.get("entry_rule_columns")
        if isinstance(rc, list):
            cols.update(str(c) for c in rc if c)

    # 2. Artifacts
    arts = candidate.get("artifacts") or {}
    if isinstance(arts, dict):
        for key in ("search_columns", "screen_columns", "columns"):
            v = arts.get(key)
            if isinstance(v, list):
                cols.update(str(c) for c in v if c)

    # 3. trial_accounting family as a weak proxy (alpha grammar domain)
    ta = candidate.get("trial_accounting") or {}
    if isinstance(ta, dict) and ta.get("family"):
        cols.add(ta["family"])

    return frozenset(cols)


def _extract_alpha_cluster(candidate: dict) -> str | None:
    """Extract alpha cluster identifier for alpha_family candidates."""
    arts = candidate.get("artifacts") or {}
    if isinstance(arts, dict):
        return arts.get("cluster") or arts.get("alpha_cluster")
    return None


def _compute_crowds_with(
    candidate_id: str,
    this_candidate: dict,
    all_candidates: dict[str, dict],
) -> list[dict]:
    """Return context list of other non-terminal candidates that share column overlap.

    RF-16: this list is CONTEXT ONLY. It is never used as a composite rank.
    Overlap criterion:
      - entry-rule column-set overlap (any shared column), OR
      - same alpha cluster (for alpha_family candidates)
    """
    this_cols = _extract_entry_rule_columns(this_candidate)
    this_cluster = _extract_alpha_cluster(this_candidate)

    results: list[dict] = []
    for other_id, other in all_candidates.items():
        if other_id == candidate_id:
            continue
        if other.get("status") in _TERMINAL_STATES:
            continue

        shared_cols: set[str] = set()
        if this_cols:
            other_cols = _extract_entry_rule_columns(other)
            shared_cols = set(this_cols) & set(other_cols)

        cluster_match = False
        if this_cluster and this_cluster == _extract_alpha_cluster(other):
            cluster_match = True

        if shared_cols or cluster_match:
            results.append({
                "candidate_id": other_id,
                "candidate_type": other.get("candidate_type"),
                "domain": other.get("domain"),
                "status": other.get("status"),
                "overlap_columns": sorted(shared_cols) if shared_cols else [],
                "same_alpha_cluster": cluster_match,
                "context_note": (
                    "display-only crowding context (RF-16 — no composite ranking)"
                ),
            })

    return results


# ---------------------------------------------------------------------------
# Artifact metric extraction (frozen-gate, aggregate)
# ---------------------------------------------------------------------------


def _extract_frozen_metrics(candidate: dict) -> dict:
    """Extract aggregate frozen-gate metrics from a candidate's artifacts.

    Returns a dict of metric-name → value pairs.  Display-only.
    Never includes individual per-fire outcomes.
    """
    metrics: dict[str, Any] = {}

    arts = candidate.get("artifacts") or {}
    if not isinstance(arts, dict):
        return metrics

    # Reversion track: n, wr, asym, ret_exit, gauntlet
    if "wr" in arts:
        for key in ("n", "wr", "asym", "ret_exit", "gauntlet"):
            if arts.get(key) is not None:
                metrics[key] = arts[key]

    # Screen result (63d or generic)
    sr = arts.get("screen_result") or {}
    if isinstance(sr, dict):
        for key in ("n", "sharpe", "deflated_sharpe", "win_rate", "mean_ret",
                    "fdr_reject", "verdict", "legs"):
            if sr.get(key) is not None:
                metrics[key] = sr[key]

    # evaluation_plan declared metrics (read-back, display)
    ep = candidate.get("evaluation_plan") or {}
    if isinstance(ep, dict):
        for key in ("primary_metric", "horizon_d", "min_n", "expected_half_life_d"):
            if ep.get(key) is not None:
                metrics[f"plan_{key}"] = ep[key]

    # Any top-level artifact metric keys
    for key in ("ic", "rank_ic", "hit_rate", "alpha", "t_stat", "p_value",
                "n_fires", "mfe_mae", "entry_quality_score"):
        if arts.get(key) is not None:
            metrics[key] = arts[key]

    return metrics


# ---------------------------------------------------------------------------
# Probe flags extractor
# ---------------------------------------------------------------------------


def _extract_probe_flags(candidate: dict, challenge: dict | None) -> dict:
    """Extract mechanical probe flags from the candidate flags list and challenge packet.

    Sources: candidate.flags list + challenge.mechanical_probes
    """
    flags: dict[str, Any] = {}

    # From candidate.flags list (strings)
    candidate_flags = candidate.get("flags") or []
    if isinstance(candidate_flags, list):
        for f in candidate_flags:
            if isinstance(f, str):
                flags[f] = True

    # From challenge mechanical_probes
    if challenge and isinstance(challenge, dict):
        probes = challenge.get("mechanical_probes") or {}
        if isinstance(probes, dict):
            for k, v in probes.items():
                flags[k] = v

    return flags


# ---------------------------------------------------------------------------
# search_width_at_scan extraction (REQUIRED for oracle, loud MISSING if absent)
# ---------------------------------------------------------------------------


def _extract_search_width(candidate: dict) -> Any:
    """Extract search_width_at_scan for oracle candidates.

    Returns the value if found, or the string 'MISSING' (loudly) if absent
    for oracle candidates.  Non-oracle candidates return None (not required).
    """
    domain = candidate.get("domain") or ""
    candidate_type = candidate.get("candidate_type") or ""
    is_oracle = domain == "oracle" or candidate_type == "oracle_compound"

    arts = candidate.get("artifacts") or {}
    if isinstance(arts, dict):
        sw = arts.get("search_width_at_scan")
        if sw is not None:
            return sw
        # Check nested artifact structures
        for key in ("pq_entry", "artifact"):
            nested = arts.get(key) or {}
            if isinstance(nested, dict):
                sw = nested.get("search_width_at_scan")
                if sw is not None:
                    return sw

    if is_oracle:
        log.warning(
            "review_queue: search_width_at_scan MISSING for oracle candidate %s — "
            "this is REQUIRED per charter §6 W3/W5",
            candidate.get("candidate_id", "?"),
        )
        return "MISSING"

    return None  # not required for non-oracle candidates


# ---------------------------------------------------------------------------
# Reviewer fields from challenge
# ---------------------------------------------------------------------------


def _extract_reviewer_fields(challenge: dict | None) -> dict:
    """Extract reviewer blockers, best_counterargument, human_review_question."""
    if not challenge or not isinstance(challenge, dict):
        return {
            "reviewer_blockers": [],
            "best_counterargument": None,
            "human_review_question": None,
        }
    reviewer = challenge.get("reviewer") or {}
    return {
        "reviewer_blockers": reviewer.get("blockers") or [],
        "best_counterargument": reviewer.get("best_counterargument"),
        "human_review_question": reviewer.get("human_review_question"),
    }


# ---------------------------------------------------------------------------
# Decision question builder
# ---------------------------------------------------------------------------


def _build_decision_question(candidate: dict, challenge: dict | None) -> str:
    """Build the exact decision question for the human reviewer.

    Pulls human_review_question from the challenge packet if present;
    otherwise synthesises a domain-appropriate question.
    """
    # Prefer the challenger-authored question
    reviewer_q = None
    if challenge and isinstance(challenge, dict):
        reviewer = challenge.get("reviewer") or {}
        reviewer_q = reviewer.get("human_review_question")
    if reviewer_q:
        return reviewer_q

    # Synthesise from domain / type
    ctype = candidate.get("candidate_type") or "candidate"
    domain = candidate.get("domain") or "unknown"
    cid = candidate.get("candidate_id", "?")
    hyp_short = (candidate.get("hypothesis") or "")[:120]
    return (
        f"Decision required for {ctype} ({domain}) candidate {cid}: "
        f"\"{hyp_short}\". "
        f"Choose: paper (begin accrual with expected_half_life_d), "
        f"deferred (come_back_on date required), "
        f"rejected (kill_class + kill_evidence required), or "
        f"scoped_build (program_doc_ref required)."
    )


# ---------------------------------------------------------------------------
# Paper-monitor decay check (absent-safe)
# ---------------------------------------------------------------------------


def _is_flagged_for_decay_review(pm_row: dict | None) -> bool:
    """Return True if this paper candidate is flagged for human decay review."""
    if not pm_row:
        return False
    action = pm_row.get("action")
    paper_status = pm_row.get("paper_status")
    return action in ("review", "retire_recommended") or paper_status in ("review", "retire_recommended")


# ---------------------------------------------------------------------------
# come_back_on extractor for awaiting_data transitions
# ---------------------------------------------------------------------------


def _extract_come_back_on(transitions_jsonl: list[dict], candidate_id: str) -> str | None:
    """Return the come_back_on date from the most-recent awaiting_data transition.

    Absent-safe: returns None if no awaiting_data transition found.
    """
    matched = [
        t for t in transitions_jsonl
        if t.get("candidate_id") == candidate_id and t.get("to") == "awaiting_data"
    ]
    if not matched:
        return None
    # Most recent = last in the append-only log
    last = matched[-1]
    return last.get("come_back_on")


# ---------------------------------------------------------------------------
# Core queue builder
# ---------------------------------------------------------------------------


def build_queue(
    rf_dir: Path | None = None,
    *, trusted_codegen_artifacts: tuple = (), synthetic_commission=None,
) -> list[dict]:
    """Build the cross-domain review queue.

    Parameters
    ----------
    rf_dir : Optional override for data/research_factory/ directory.

    Returns
    -------
    list[dict]
        List of review packet dicts, one per candidate.  Each packet carries
        "authority": "display_only".  Queue is ordered by category bin then
        created_at (RF-16 — never by a numeric score).
    """
    # Explicit owner attachment only. Default path performs no diagnostic I/O.
    if type(trusted_codegen_artifacts) is not tuple:
        raise ValueError("immutable diagnostic bindings required")
    diagnostics = ()
    if trusted_codegen_artifacts:
        from engine.research_codegen.bridge import load_diagnostics, public_diagnostic
        diagnostics = load_diagnostics(trusted_codegen_artifacts, commission=synthetic_commission)
    _dir = Path(rf_dir) if rf_dir else DEFAULT_RF_DIR
    candidates_path = _dir / "candidates.jsonl"
    transitions_path = _dir / "transitions.jsonl"
    challenges_dir = _dir / "challenges"
    pm_path = _dir / "paper_monitor.jsonl"

    # Load raw data (all absent-safe)
    candidates_jsonl = _load_jsonl(candidates_path)
    transitions_jsonl = _load_jsonl(transitions_path)

    # Resolve latest status per candidate
    all_candidates = _resolve_candidates(candidates_jsonl, transitions_jsonl)

    # Collect candidates eligible for the queue:
    #   1. status == 'human_review'  → full decide.py path
    #   2. status == 'paper' AND monitor flags decay review
    #      → visibility-only; decide.py cannot act until W6 re-transitions to human_review
    #   3. status == 'awaiting_data'
    #      → blocked bucket; surfaced for operator awareness with come_back_on clock;
    #        no decide path until the blocking condition resolves
    # Tuple: (candidate_id, is_paper_decay, is_awaiting_data)
    queue_ids: list[tuple[str, bool, bool]] = []
    for cid, cand in all_candidates.items():
        status = cand.get("status")
        if status == "human_review":
            queue_ids.append((cid, False, False))
        elif status == "paper":
            pm_row = _load_paper_monitor(pm_path, cid)
            if _is_flagged_for_decay_review(pm_row):
                queue_ids.append((cid, True, False))
        elif status == "awaiting_data":
            queue_ids.append((cid, False, True))

    # Build packets
    packets: list[dict] = []
    for cid, is_paper_decay, is_awaiting_data in queue_ids:
        cand = all_candidates[cid]
        challenge = _load_challenge(challenges_dir, cid)

        frozen_metrics = _extract_frozen_metrics(cand)
        probe_flags = _extract_probe_flags(cand, challenge)
        reviewer_fields = _extract_reviewer_fields(challenge)
        search_width = _extract_search_width(cand)
        crowds_with = _compute_crowds_with(cid, cand, all_candidates)
        decision_question = _build_decision_question(cand, challenge)

        if is_paper_decay:
            # Paper-decay candidates surface for operator awareness only.
            # decide.py refuses any candidate not in human_review, so emitting
            # the standard allowed_decisions list would produce a command that always
            # exits rc=1.  The W6 paper-monitor step (not yet built) will re-transition
            # these to human_review when decay is confirmed.
            packet_allowed_decisions = _PAPER_DECAY_ALLOWED_DECISIONS
            packet_note = (
                "decay_review_pending — current_status is 'paper'; decide.py cannot act "
                "until W6 paper-monitor re-transitions this candidate to human_review. "
                "No runnable decide command exists yet. "
                "RF-16 forbids any composite/fused ranking — crowds_with is context only."
            )
        elif is_awaiting_data:
            # awaiting_data candidates are blocked on data/label/grader availability.
            # No decide command is runnable until the blocking condition resolves and
            # the candidate re-enters a decidable state.
            packet_allowed_decisions = _AWAITING_DATA_ALLOWED_DECISIONS
            # Extract come_back_on from the most recent awaiting_data transition
            come_back_on = _extract_come_back_on(transitions_jsonl, cid)
            packet_note = (
                f"awaiting_data — blocked on data/label/grader availability; "
                f"come_back_on={come_back_on or 'not set'}. "
                "No decide command is runnable until the blocking condition resolves. "
                "RF-16 forbids any composite/fused ranking — crowds_with is context only."
            )
        else:
            packet_allowed_decisions = ALLOWED_DECISIONS
            packet_note = (
                "display-only review context; RF-16 forbids any composite/fused "
                "ranking — crowds_with is context only, not a score"
            )

        packet: dict = {
            "authority": "display_only",
            "schema": "research_factory.review_packet.v1",
            "candidate_id": cid,
            "created_at": cand.get("created_at"),
            "current_status": cand.get("status"),
            "is_awaiting_data": is_awaiting_data,
            "come_back_on": (_extract_come_back_on(transitions_jsonl, cid)
                             if is_awaiting_data else None),
            "candidate_type": cand.get("candidate_type"),
            "domain": cand.get("domain"),
            "track": (cand.get("artifacts") or {}).get("track"),
            "source": cand.get("source"),
            "hypothesis": cand.get("hypothesis"),
            "mechanism": cand.get("mechanism"),
            "frozen_gate_metrics": frozen_metrics,
            "probe_flags": probe_flags,
            "reviewer_blockers": reviewer_fields["reviewer_blockers"],
            "best_counterargument": reviewer_fields["best_counterargument"],
            "human_review_question": reviewer_fields["human_review_question"],
            "search_width_at_scan": search_width,
            "crowds_with": crowds_with,
            "allowed_decisions": packet_allowed_decisions,
            "decision_question": decision_question,
            "note": packet_note,
        }
        packets.append(packet)

    for diagnostic in diagnostics:
        packets.append(diagnostic_review_packet(public_diagnostic(diagnostic)))

    # Order: category bins then created_at (RF-16 — never by numeric score)
    packets.sort(
        key=lambda p: (
            _type_bin(p.get("candidate_type")),
            str(p.get("created_at") or ""),
        )
    )

    return packets


def diagnostic_review_packet(public: dict, *, engineering_evidence=None,
                             engineering_receipts=None) -> dict:
    """Closed compiled display attachment; never a canonical candidate row."""
    from engine.research_codegen.bridge import validate_public_projection
    public = validate_public_projection(public)
    if engineering_receipts is not None:
        if engineering_evidence is not None:
            raise ValueError("AMBIGUOUS_DIAGNOSTIC_ENGINEERING_INPUT")
        engineering_evidence = _compose_diagnostic_receipts(public, engineering_receipts)
    packet = {
        "schema": "research_factory.review_packet.v1", "authority": "display_only",
        "is_research_diagnostic": True, "diagnostic_id": public["diagnostic_id"],
        "candidate_id": public["candidate_id"], "created_at": public["created_at"],
        "current_status": "unregistered_synthetic_diagnostic", "candidate_type": None,
        "domain": "research_engineering", "allowed_decisions": [],
        "frozen_gate_metrics": public["aggregates"], "diagnostic": public,
        "note": "Synthetic engineering only; no candidate lifecycle or promotion authority. "
                "Equal-date 25-session single-entry adverse excursion, including four post-exit sessions. "
                "INFERENCE_UNQUALIFIED / NO_QUALIFIED_PROCEDURE.",
    }
    if engineering_evidence is not None:
        packet["engineering_evidence"] = _diagnostic_engineering_evidence(
            public, engineering_evidence)
    if engineering_receipts is not None:
        packet["note"] += (" Synthetic/scripted source plumbing; receipt types and digests "
                           "do not authenticate a producer or establish temporal-bias "
                           "detection, a numerical oracle or a physical boundary.")
    return packet


def _compose_diagnostic_receipts(public, receipts):
    """Pure typed receipt join into the incumbent advisory display schema.

    These are structural provenance inputs, never authenticated owner evidence.
    No original expectation descriptor binds a good/bad control to a variant in
    the current generation contract, so output-control adjudication stays NOT_RUN.
    """
    import hashlib
    import json
    from dataclasses import replace
    from engine.research_codegen import accounting_contract as accounting
    from engine.research_codegen import bridge, prefix_driver, staging_accounting

    def require(ok):
        if not ok:
            raise ValueError("INVALID_DIAGNOSTIC_ENGINEERING_RECEIPTS")

    require(type(receipts) is dict and set(receipts) == {
        "run", "commission", "source", "staged", "outcome"})
    run, commission, source, staged, outcome = (receipts[key] for key in
        ("run", "commission", "source", "staged", "outcome"))
    require(type(run) is bridge.SyntheticRun
            and type(staged) is staging_accounting.StagedAccountingReadback
            and type(outcome) is prefix_driver.PrefixDriverOutcome)
    prepared = bridge.prepare_synthetic_inputs(run, commission=commission)
    staging_accounting._bound(source, "source")
    require(source.sha256 == public["source_sha256"]
            and source.size <= prefix_driver.MAX_SOURCE_BYTES)
    require(type(prepared.identity) is bridge.PreparedIdentity
            and type(outcome.identity) is bridge.PreparedIdentity
            and outcome.identity == prepared.identity)
    for key in bridge._IDENTITY:
        require(getattr(prepared.identity, key) == public[key])
    require(outcome.source_sha256 == public["source_sha256"]
            and outcome.config_sha256 == public["config_sha256"])

    # Existing bounded, duplicate-key rejecting reader validates exact bytes.
    expected, trial, writer, durable = (
        staging_accounting._load_bound_json(getattr(staged, key), key)
        for key in ("expected_generation", "trial_readback", "writer_observation",
                    "durable_readback_observation"))
    staging_accounting._bound(staged.raw_snapshot, "snapshot")
    require(run.expected_generation == staged.expected_generation
            and run.trial_readback == staged.trial_readback)
    require(accounting.assess_accounting_references(
        expected, trial_readback=trial)["status"] == "STRUCTURALLY_COMPLETE_DISABLED")
    require(expected["original_root_id"] == public["original_root_id"]
            and expected["protocol_sha256"] == public["protocol_sha256"])
    selected = [v for v in expected["variants"]
                if v["source_sha256"] == outcome.source_sha256
                and v["config_sha256"] == outcome.config_sha256]
    require(len(selected) == 1)
    require(trial["snapshot_sha256"] == staged.raw_snapshot.sha256
            and trial["snapshot_bytes"] == staged.raw_snapshot.size
            and trial["writer_receipt_sha256"] == staged.writer_observation.sha256
            and trial["durable_readback_receipt_sha256"] == staged.durable_readback_observation.sha256)
    for observation in (writer, durable):
        require(observation.get("original_root_id") == expected["original_root_id"]
                and observation.get("family") == expected["family"]
                and observation.get("scope") == "SYNTHETIC_ENGINEERING_ONLY"
                and observation.get("authority") == "display_only"
                and observation.get("uncertainty") == "none")
    require(writer.get("run_id") == durable.get("run_id")
            and writer.get("sha256_after") == staged.raw_snapshot.sha256
            and durable.get("snapshot_sha256") == staged.raw_snapshot.sha256)

    require(type(prepared.decisions) is tuple and len(prepared.decisions) <= 4096
            and type(outcome.attempts) is tuple and len(outcome.attempts) <= len(prepared.decisions)
            and type(outcome.completed) is bool and type(outcome.refusal_reasons) is tuple)
    keys = ("operation_id", "plan_sha256", "input_sha256", "output_sha256", "output_bytes",
            "state", "workload_confirmed", "workload_returncode", "execution_uncertain",
            "reconciliation_required", "cleanup_confirmed")
    attempts, adopted = [], []
    for attempt, task in zip(outcome.attempts, prepared.decisions):
        require(type(attempt) is prefix_driver.PrefixAttempt
                and type(task) is bridge.PreparedDecisionInput)
        staging_accounting._bound(task.input_bytes, "input")
        argv, _, carrier = prefix_driver.build_carrier(source.raw, task.input_bytes.raw)
        require((attempt.fold_id, attempt.entity_id, attempt.decision_id, attempt.input_sha256)
                == (task.fold_id, task.entity_id, task.decision_id, task.input_bytes.sha256))
        plan, raw = attempt.transport_plan, attempt.transport_attempt
        require(type(plan) is prefix_driver.transport_module.TransportPlan
                and type(raw) is prefix_driver.transport_module.TransportAttempt
                and type(raw.state) is prefix_driver.transport_module.AttemptState
                and type(raw.workload_output) is bytes
                and len(raw.workload_output) <= plan.output_cap_bytes)
        require(attempt.operation_id == plan.operation_id == raw.operation_id
                == prefix_driver.decision_operation_id(prepared, task, carrier)
                and plan.argv == argv
                and attempt.plan_sha256 == raw.plan_sha256
                == prefix_driver.transport_module.plan_identity(plan)
                and attempt.container_id == raw.container_id
                and attempt.state == raw.state.value)
        for key in ("workload_confirmed", "workload_returncode", "execution_uncertain",
                    "reconciliation_required", "cleanup_confirmed"):
            require(getattr(attempt, key) == getattr(raw, key)
                    and type(getattr(attempt, key)) is type(getattr(raw, key)))
        require(attempt.output_bytes == len(raw.workload_output)
                and attempt.output_sha256 == (hashlib.sha256(raw.workload_output).hexdigest()
                                             if raw.workload_output else None))
        row = {key: getattr(attempt, key) for key in keys}
        row["state"] = row["state"].upper()
        attempts.append(row)
        try:
            adopted.append((task, prefix_driver._adopt(
                raw, plan, prepared.identity, task, plan.output_cap_bytes)))
        except prefix_driver.PrefixDriverRefused:
            require(not outcome.completed and len(attempts) == len(outcome.attempts))
    if outcome.completed:
        require(bool(attempts) and len(attempts) == len(prepared.decisions)
                and not outcome.refusal_reasons
                and all(row["state"] == "CLEANED_SUCCESS" for row in attempts)
                and public["status"] == "DIAGNOSTIC_ONLY")
        require(type(outcome.outputs) is tuple and len(outcome.outputs) == len(prepared.schedules))
        for group, output in zip(prepared.schedules, outcome.outputs):
            staging_accounting._bound(output, "output")
            expected_output = {"schema": prefix_driver.OUTPUT_SCHEMA,
                "candidate_id": prepared.identity.candidate_id,
                "fold_id": group.fold_id, "entity_id": group.entity_id,
                "input_policy_sha256": prepared.identity.input_policy_sha256,
                "rows": [row for task, row in adopted
                         if (task.fold_id, task.entity_id) == (group.fold_id, group.entity_id)]}
            require(output.raw == prefix_driver._canonical(expected_output))
        diagnostic = prefix_driver.connect_prepared_outputs(run, outcome, commission=commission)
    else:
        require(public["status"] == "REFUSED" and outcome.outputs == ())
        # An incomplete attempt cannot borrow pre-existing successful outputs.
        require(run.outputs == ())
        diagnostic = bridge.compute_synthetic_diagnostic(run, commission=commission)
    binding = replace(run.identity, artifact_sha256=hashlib.sha256(diagnostic).hexdigest(),
                      artifact_bytes=len(diagnostic))
    derived = bridge.public_diagnostic(bridge.decode_bound_artifact(
        diagnostic, expected=binding, commission=commission))
    require(derived == public)
    encoded = json.dumps(attempts, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    controls = [{"id": "accounting_declaration", "status": "MATCHED_EXPECTATION",
                 "evidence_sha256": staged.trial_readback.sha256},
                {"id": "prefix_schedule", "status": "MATCHED_EXPECTATION" if outcome.completed else "NOT_RUN",
                 "evidence_sha256": hashlib.sha256(encoded).hexdigest() if outcome.completed else None}]
    controls.extend({"id": key, "status": "NOT_RUN", "evidence_sha256": None}
                    for key in ("output_contract", "physical_boundary", "resource_overload"))
    return {"schema": "research_codegen.engineering_evidence.v1",
            "identity": {key: public[key] for key in (*bridge._IDENTITY, "artifact_sha256")},
            "accounting": {"expected_generation_sha256": staged.expected_generation.sha256,
                           "trial_readback_sha256": staged.trial_readback.sha256,
                           "durable_observation_sha256": staged.durable_readback_observation.sha256},
            "attempts": attempts, "controls": controls}


def _diagnostic_engineering_evidence(public, evidence):
    """Copy a closed, bounded fixture-owner projection for advisory inspection.

    Digests correlate receipts; they do not authenticate a caller or prove that
    any control ran. Only synthetic engineering evidence is admitted here.
    Real boundary and resource acceptance require their separate actual owner.
    No raw commands, output, paths, labels or free-form errors are copied.
    """
    import re

    def require(ok):
        if not ok:
            raise ValueError("INVALID_DIAGNOSTIC_ENGINEERING_EVIDENCE")

    def closed(value, names):
        require(type(value) is dict and len(value) == len(names)
                and all(type(key) is str for key in value)
                and set(value) == set(names))

    def sha(value):
        return (type(value) is str and len(value) == 64
                and re.fullmatch(r"[0-9a-f]{64}", value) is not None)

    def identifier(value):
        return (type(value) is str and 1 <= len(value) <= 128
                and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value) is not None)

    closed(evidence, ("schema", "identity", "accounting", "attempts", "controls"))
    require(type(evidence["schema"]) is str
            and evidence["schema"] == "research_codegen.engineering_evidence.v1")
    identity_keys = ("diagnostic_id", "original_root_id", "candidate_id", "source_sha256",
                     "config_sha256", "protocol_sha256", "input_policy_sha256",
                     "runtime_sha256", "evaluator_sha256", "artifact_sha256")
    identity = evidence["identity"]
    closed(identity, identity_keys)
    for key in identity_keys:
        require((sha(identity[key]) if key.endswith("sha256") else identifier(identity[key]))
                and identity[key] == public[key])
    accounting = evidence["accounting"]
    closed(accounting, ("expected_generation_sha256", "trial_readback_sha256",
                        "durable_observation_sha256"))
    require(all(sha(value) for value in accounting.values()))
    rows = evidence["attempts"]
    require(type(rows) is list and len(rows) <= 4096)
    attempts, seen = [], set()
    attempt_keys = ("operation_id", "plan_sha256", "input_sha256", "output_sha256",
                    "output_bytes", "state", "workload_confirmed", "workload_returncode",
                    "execution_uncertain", "reconciliation_required", "cleanup_confirmed")
    states = ("PLANNED", "CREATE_UNCERTAIN", "CLEANED_SUCCESS", "CLEANED_FAILURE",
              "CLEANUP_UNCERTAIN")
    for row in rows:
        closed(row, attempt_keys)
        require(identifier(row["operation_id"]) and row["operation_id"] not in seen)
        seen.add(row["operation_id"])
        require(sha(row["plan_sha256"]) and sha(row["input_sha256"]))
        require(row["output_sha256"] is None or sha(row["output_sha256"]))
        require(type(row["output_bytes"]) is int and 0 <= row["output_bytes"] <= 65536)
        require(row["output_sha256"] is not None or row["output_bytes"] == 0)
        require(type(row["state"]) is str and row["state"] in states)
        require(all(type(row[key]) is bool for key in ("workload_confirmed",
            "execution_uncertain", "reconciliation_required", "cleanup_confirmed")))
        code = row["workload_returncode"]
        require(code is None or type(code) is int and -255 <= code <= 255)
        require(not row["workload_confirmed"] or code is not None)
        if row["state"] == "CLEANED_SUCCESS":
            require(row["workload_confirmed"] and code == 0 and row["cleanup_confirmed"]
                    and not row["execution_uncertain"] and not row["reconciliation_required"])
        elif row["state"] == "CLEANED_FAILURE":
            require(row["cleanup_confirmed"] and not row["workload_confirmed"])
        elif row["state"] in ("CREATE_UNCERTAIN", "CLEANUP_UNCERTAIN"):
            require(not row["cleanup_confirmed"] and row["reconciliation_required"])
        else:
            require(not row["workload_confirmed"] and code is None
                    and row["output_bytes"] == 0 and row["output_sha256"] is None
                    and not row["cleanup_confirmed"])
        attempts.append(dict(row))
    controls = evidence["controls"]
    expected_controls = ("accounting_declaration", "prefix_schedule", "output_contract",
                         "physical_boundary", "resource_overload")
    require(type(controls) is list and len(controls) == len(expected_controls))
    copied_controls = []
    for row, expected in zip(controls, expected_controls):
        closed(row, ("id", "status", "evidence_sha256"))
        require(type(row["id"]) is str and row["id"] == expected)
        require(type(row["status"]) is str
                and row["status"] in ("MATCHED_EXPECTATION", "DID_NOT_MATCH", "NOT_RUN"))
        if row["status"] == "NOT_RUN":
            require(row["evidence_sha256"] is None)
        else:
            require(sha(row["evidence_sha256"]))
        if expected in ("physical_boundary", "resource_overload"):
            require(row["status"] == "NOT_RUN")
        copied_controls.append(dict(row))
    return {"schema": evidence["schema"], "identity": dict(identity),
            "accounting": dict(accounting), "attempts": attempts,
            "controls": copied_controls, "authority": "display_only",
            "scope": "SYNTHETIC_ENGINEERING_ONLY", "physical_acceptance": False,
            "scientific_acceptance": "UNQUALIFIED"}
