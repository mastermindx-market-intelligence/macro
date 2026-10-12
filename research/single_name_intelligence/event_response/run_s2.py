"""S2 evidence runner — C2/C3. HISTORICAL-DESCRIPTIVE (non-confirmatory).

One command reproduces the evidence from a clean checkout:

  python3 research/single_name_intelligence/event_response/run_s2.py \
      --input-ref 5ef7a7f39f99232bf9b574c7603da1011ee3af66 \
      --out-dir <dir> --trial-ledger-path <dir>/trial_ledger.jsonl

plus `--check`, which reruns into a temp dir and byte-compares every output
against the committed seal directory (the ledger compared after dropping
"ts"); exit 0 iff identical. The runner FIRST recomputes every
membership_sha256 and the prereg digest and exits non-zero on any mismatch
with the seal.

`--trial-ledger-path` is REQUIRED with NO default; any path resolving inside
<repo>/data/ is refused (exit 2). Every family evaluates inside
register_trials(budget=6, ledger=...) — the declared_budget row is written
BEFORE any outcome row of that family. Ledger outcome rows are logged one per
itemized config (3 baselines + challenger) x 3 horizons = 12 per family,
including not-estimable ones.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2]))

from engine.trial_ledger import TrialLedger, register_trials  # noqa: E402

from s2_loaders import GitBlobLoader, verify_pinned_blobs  # noqa: E402
from s2_outcomes import OutcomeEngine  # noqa: E402
from s2_seal import (ABSTAIN_INSUFFICIENT_CLUSTERS, ABSTAIN_NO_EPISODES,
                     BASE_COMMIT, BASELINE_ALWAYS_LONG, BASELINE_LABELS,
                     BASELINE_POOLED_PRIOR, BASELINE_TRAILING63, BRANCH,
                     CHALLENGER, DESCRIPTIVE_ONLY, FAMILY_BUDGET,
                     FAMILY_BUDGET_REASON, GRADE_HORIZONS, GRADED_ISSUER,
                     IDENTITY_VIEW, INFO_LEAK_CLASS, INFO_LEAK_INVARIANCE_NOTE,
                     LABEL_HISTORICAL, LANE, MIN_EPISODES,
                     MIN_TRAIN_CLUSTERS_POOLED_PRIOR, NOT_SUPPORTED_LINE,
                     NOT_SUPPORTED_PROTOCOLS, POOLING_WEIGHT_TOKEN,
                     PROPER_SCORE_LINE, PROTOCOLS, PROTOCOL_FAMILY,
                     PROTOCOL_TITLE, PROTOCOL_VERSION, REG_CANONICAL_FAMILY,
                     RETIREMENT_SOURCE, TESTED, TRIAL_LEDGER_REL_PATH,
                     TRIAL_LEDGER_SOURCE, itemized_grid, ledger_family,
                     prereg_digest)  # noqa: E402
from s2_splits import purge_flag, split_label, window_last_session  # noqa: E402
from s2_state import compute_state  # noqa: E402
from s2_stats import (MIRROR_BLOCK_NAME, MIRROR_CLUSTER_VARIABLE,
                      hit_rate_test, mirror_trick_ci, sign_exact)  # noqa: E402

SPLITS = ("TRAIN", "TUNE", "QUARANTINE")
AUTHORITY_FLAGS_FALSE = {
    "rank_authority": False, "gate_authority": False, "size_authority": False,
    "signal_authority": False, "escalation_authority": False,
    "trade_authority": False,
}


def base_commit_detected_at(input_ref: str, repo_root: Path) -> str:
    """The BASE commit's committer instant in UTC — deterministic per input."""
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "show", "-s", "--format=%cI", input_ref],
        capture_output=True, text=True)
    iso = proc.stdout.strip()
    parsed = dt.datetime.fromisoformat(iso).astimezone(dt.timezone.utc)
    return parsed.isoformat()


def refuse_data_path(repo_root: Path, ledger_path: Path) -> None:
    repo_data = (repo_root / "data").resolve()
    try:
        resolved = ledger_path.resolve()
    except OSError:
        resolved = ledger_path.absolute()
    if resolved == repo_data or repo_data in resolved.parents:
        print("REFUSED: --trial-ledger-path resolves inside <repo>/data/ "
              f"({resolved}); the run-local ledger never touches data/",
              file=sys.stderr)
        raise SystemExit(2)


# ---------------------------------------------------------------------------
# episode helpers
# ---------------------------------------------------------------------------

def episode_identity(ep) -> str:
    from s2_splits import episode_key as mk
    return mk(ep.opener.issuer_key, ep.opener.family, ep.opener.t_avail_utc,
              ep.opener.evidence_pointer)


def episode_purged(ep, h: int) -> bool:
    split = split_label(dt.date.fromisoformat(ep.opener.s_us))
    coverage = window_last_session(dt.date.fromisoformat(ep.opener.s_us), h)
    return purge_flag(split, coverage)


def compute_outcomes(engine: OutcomeEngine, state: dict) -> dict:
    """Graded outcomes keyed (episode_key, h); census-only episodes never get
    one (V0 row 14). Decision-time trailing direction keyed episode_key."""
    outcomes: dict[tuple, dict] = {}
    trailing: dict[str, int] = {}
    seen_trailing: set[str] = set()
    for pid in PROTOCOLS:
        for h in GRADE_HORIZONS:
            for ep in state["membership"][pid]["counted"].get(h, []):
                key = episode_identity(ep)
                if (key, h) in outcomes:
                    continue
                outcomes[(key, h)] = engine.episode_excess(
                    dt.date.fromisoformat(ep.opener.s_us), h)
                if key not in seen_trailing:
                    seen_trailing.add(key)
                    trailing[key] = engine.trailing63_direction(
                        dt.date.fromisoformat(ep.opener.s_us))
    return {"outcomes": outcomes, "trailing": trailing}


# ---------------------------------------------------------------------------
# family evaluation (graded cohort only; census-only episodes never count)
# ---------------------------------------------------------------------------

def evaluate_family(pid: str, state: dict, occ: dict, h: int, split: str,
                    baseline: str, pooled_prior_dir: int | None) -> dict:
    eps = [ep for ep in state["membership"][pid]["counted"].get(h, [])
           if split_label(dt.date.fromisoformat(ep.opener.s_us)) == split]
    rows = []
    for ep in eps:
        key = episode_identity(ep)
        out = occ["outcomes"].get((key, h),
                                  {"state": "ABSTAIN_MISSING_ENDPOINT",
                                   "window": None})
        excess = out.get("excess")
        if baseline == BASELINE_ALWAYS_LONG:
            direction = 1
        elif baseline == BASELINE_TRAILING63:
            direction = occ["trailing"].get(key, 0)
        elif baseline == BASELINE_POOLED_PRIOR:
            direction = pooled_prior_dir
        else:  # challenger: hierarchy legs above own-name are unregistered
            direction = None
        hit = None
        if excess is not None and direction is not None:
            if direction == 0:
                hit = None  # direction 0 -> ABSTAIN (listed)
            else:
                hit = 1 if (sign_exact(excess) == direction) else 0
        rows.append({
            "episode_key": key,
            "issuer_key": ep.opener.issuer_key,
            "opener_family": ep.opener.family,
            "s_us": ep.opener.s_us,
            "cluster_key": ep.opener.s_us,
            "outcome_state": out["state"],
            "window": out.get("window"),
            "excess": excess,
            "subject_ret": out.get("subject_ret"),
            "bench_ret": out.get("bench_ret"),
            "baseline": baseline,
            "direction": direction,
            "hit": hit,
            "tie": bool(excess is not None and excess == 0),
            "purged": episode_purged(ep, h),
            "confounded": bool(getattr(ep, "confounded", False)),
            "absorbed_count": getattr(ep, "absorbed_count", 0),
        })
    primary_idx = [i for i, r in enumerate(rows) if not r["confounded"]]
    sensb_idx = [i for i in primary_idx if rows[i]["absorbed_count"] == 0]
    sets = {"PRIMARY": primary_idx, "SENS_A": list(range(len(rows))),
            "SENS_B": sensb_idx}
    summary = {}
    for name, idxs in sets.items():
        sub = [rows[i] for i in idxs if not rows[i]["purged"]]
        summary[name] = {
            "honest_n": len(sub),
            "cluster_n": len({r["cluster_key"] for r in sub}),
            "cluster_keys": sorted({r["cluster_key"] for r in sub}),
            "episodes": sub,
        }
    return {"rows": rows, "summary": summary}


def abstention_state(primary: dict) -> str:
    n = primary["honest_n"]
    if n == 0:
        return ABSTAIN_NO_EPISODES
    if primary["cluster_n"] < 2:
        return ABSTAIN_INSUFFICIENT_CLUSTERS
    if n < MIN_EPISODES:
        return DESCRIPTIVE_ONLY
    return TESTED


PLAIN_NULL_TESTED = (
    "Across the counted episodes the post-event directional agreement with "
    "each frozen baseline cannot be distinguished from a coin flip at this "
    "sample size; the rows describe conditional post-event co-movement over "
    "fixed windows and are not forecasts, signals or attribution.")
_PLAIN_NULL_TAIL = ("The rows describe conditional post-event co-movement over "
                    "fixed windows and are not forecasts, signals or attribution.")
PLAIN_NULL_NOT_TESTED = {
    ABSTAIN_NO_EPISODES: (
        "This family abstains: no episode was counted in this block, so no "
        "agreement rate, no interval and no test against the frozen baselines "
        "is estimable. " + _PLAIN_NULL_TAIL),
    ABSTAIN_INSUFFICIENT_CLUSTERS: (
        "This family abstains: fewer than two independent clusters, so no "
        "agreement rate, no interval and no test against the frozen baselines "
        "is estimable. " + _PLAIN_NULL_TAIL),
    DESCRIPTIVE_ONLY: (
        "This family is descriptive only: the counted episodes are below the "
        f"pre-registered minimum of {MIN_EPISODES} for a test, so no agreement "
        "rate test and no interval is reported. " + _PLAIN_NULL_TAIL),
}


def plain_word_null(state_token: str) -> str:
    """REG §5 item 1. The coin-flip sentence only when a test exists (TESTED);
    every other state gets its own plain-word line (A25: abstain, never fill).
    An unknown token raises KeyError (fail closed)."""
    if state_token == TESTED:
        return PLAIN_NULL_TESTED
    return PLAIN_NULL_NOT_TESTED[state_token]


def pooled_prior(state: dict, occ: dict, h: int) -> tuple[int | None, str]:
    """Baseline (iii): sign of the mean excess of all counted TRAIN episodes
    across the three families at h (PRIMARY), TRAIN only."""
    excesses: list[float] = []
    clusters: list[str] = []
    for other in PROTOCOLS:
        ev = evaluate_family(other, state, occ, h, "TRAIN", BASELINE_ALWAYS_LONG,
                             pooled_prior_dir=None)
        for r in ev["summary"]["PRIMARY"]["episodes"]:
            if r["excess"] is not None:
                excesses.append(r["excess"])
                clusters.append(r["cluster_key"])
    if len(set(clusters)) < MIN_TRAIN_CLUSTERS_POOLED_PRIOR:
        return None, ("NOT ESTIMABLE (TRAIN cluster-N < %d; TRAIN episodes=%d)"
                      % (MIN_TRAIN_CLUSTERS_POOLED_PRIOR, len(excesses)))
    mean_ex = sum(excesses) / len(excesses)
    d = sign_exact(mean_ex)
    return d, f"direction {d:+d} (mean TRAIN excess {mean_ex:+.6f})"


def exclusion_index_by_family(state: dict) -> dict:
    idx: dict[str, list[str]] = {}
    for e in state["collapse"]["counts"]["excluded_and_listed"]:
        scope = e.get("family_scope")
        if scope:
            idx.setdefault(scope, []).append(e["id"])
    return idx


# ---------------------------------------------------------------------------
# REG §5 block
# ---------------------------------------------------------------------------

def build_block(pid: str, state: dict, occ: dict, h: int, split: str,
                ledger_counts: dict, exclusions: list[str],
                info_leak_ctx: dict) -> dict:
    evals = {b: evaluate_family(pid, state, occ, h, split, b,
                                pooled_prior_dir=None)
             for b in (BASELINE_ALWAYS_LONG, BASELINE_TRAILING63)}
    primary = evals[BASELINE_ALWAYS_LONG]["summary"]["PRIMARY"]
    state_token = abstention_state(primary)

    pooled_dir, pooled_token = pooled_prior(state, occ, h)
    pooled_eval = evaluate_family(pid, state, occ, h, split,
                                  BASELINE_POOLED_PRIOR, pooled_prior_dir=pooled_dir)
    challenger_token = ("NOT ESTIMABLE (hierarchy legs above own-name "
                        f"unregistered; own-name honest-N={primary['honest_n']})")

    split_eps = [ep for ep in state["membership"][pid]["counted"].get(h, [])
                 if split_label(dt.date.fromisoformat(ep.opener.s_us)) == split]
    absorbed_n = sum(getattr(ep, "absorbed_count", 0) for ep in split_eps)
    confounded_n = sum(1 for ep in split_eps
                       if getattr(ep, "confounded", False))
    purged_n = sum(1 for ep in split_eps if episode_purged(ep, h))
    quarantine_n = sum(1 for ep in
                       state["membership"][pid]["counted"].get(h, [])
                       if split_label(dt.date.fromisoformat(ep.opener.s_us))
                       == "QUARANTINE")

    if state_token == TESTED:
        hits = [r["hit"] or 0 for r in primary["episodes"] if r["hit"] is not None]
        test_block = hit_rate_test(hits)
        ci = mirror_trick_ci([r["cluster_key"] for r in primary["episodes"]],
                             [r["excess"] for r in primary["episodes"]])
        ci_block = ({"statistic": "mean excess", "ci": ci,
                     "block": MIRROR_BLOCK_NAME,
                     "cluster_variable": MIRROR_CLUSTER_VARIABLE}
                    if ci is not None else "CI NOT ESTIMABLE (cluster-N < 2)")
    else:
        test_block = state_token
        ci_block = "CI NOT ESTIMABLE (cluster-N < 2)"

    pooling = POOLING_WEIGHT_TOKEN  # printed, never a number by default (E7)

    block = {
        "plain_word_null": plain_word_null(state_token),
        "analysis_set": {
            "PRIMARY": "all counted episodes, minus those flagged confounded (IL §4)",
            "SENS_A": {"honest_n": evals[BASELINE_ALWAYS_LONG]["summary"]["SENS_A"]["honest_n"],
                       "cluster_n": evals[BASELINE_ALWAYS_LONG]["summary"]["SENS_A"]["cluster_n"]},
            "SENS_B": {"honest_n": evals[BASELINE_ALWAYS_LONG]["summary"]["SENS_B"]["honest_n"],
                       "cluster_n": evals[BASELINE_ALWAYS_LONG]["summary"]["SENS_B"]["cluster_n"]},
        },
        "honest_n": {
            "PRIMARY": primary["honest_n"],
            "SENS_A": evals[BASELINE_ALWAYS_LONG]["summary"]["SENS_A"]["honest_n"],
            "SENS_B": evals[BASELINE_ALWAYS_LONG]["summary"]["SENS_B"]["honest_n"]},
        "cluster_n": {
            "PRIMARY": primary["cluster_n"],
            "SENS_A": evals[BASELINE_ALWAYS_LONG]["summary"]["SENS_A"]["cluster_n"],
            "SENS_B": evals[BASELINE_ALWAYS_LONG]["summary"]["SENS_B"]["cluster_n"]},
        "literal_row_count": state["collapse"]["counts"]["literal_row_count_pre_step0"],
        "visible_exclusions": {
            "excluded_and_listed": exclusions,
            "excluded_and_listed_count": len(exclusions),
            "confounded": confounded_n,
            "absorbed": absorbed_n,
            "purged": purged_n,
            "quarantine": quarantine_n,
        },
        "test": test_block,
        "ci": ci_block,
        "trials": {
            "literal_n": ledger_counts["literal_n"],
            "effective_n": ledger_counts["effective_n"],
            "declared_budget": ledger_counts["declared_budget"],
            "effective_n_label": ("effective N (trials; TrialLedger.effective_n "
                                  "— never a sample N, IL §1)"),
        },
        "receipt": {
            "code_commit_sha": ("inputs pinned at " + BASE_COMMIT +
                                " (see seal INPUT_MANIFEST blob ids; the branch"
                                " head is never stamped so byte-compares stay stable)"),
            "prereg_digest_sha256": state["prereg_digest_sha256"],
            "seal_row": ("research/single_name_intelligence/runs/s2_event_response/"
                         "SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the "
                         "seat integrates)"),
            "trial_ledger_path": TRIAL_LEDGER_REL_PATH,
            "prior_looks": "none for v1",
        },
        "family_row": {
            "event_count": len(split_eps),
            "distinct_calendar_clusters": primary["cluster_n"],
            "honest_n": primary["honest_n"],
            "honest_n_sens_a": evals[BASELINE_ALWAYS_LONG]["summary"]["SENS_A"]["honest_n"],
            "honest_n_sens_b": evals[BASELINE_ALWAYS_LONG]["summary"]["SENS_B"]["honest_n"],
            "effective_n": ledger_counts["effective_n"],
            "pooling_weight": pooling,
            "uncertainty": ci_block if isinstance(ci_block, str) else ci_block["ci"],
            "abstention_state": state_token,
        },
        "baselines": {
            BASELINE_ALWAYS_LONG: {
                "label": BASELINE_LABELS[BASELINE_ALWAYS_LONG],
                "episodes": evals[BASELINE_ALWAYS_LONG]["summary"]["PRIMARY"]["episodes"]},
            BASELINE_TRAILING63: {
                "label": BASELINE_LABELS[BASELINE_TRAILING63],
                "episodes": evals[BASELINE_TRAILING63]["summary"]["PRIMARY"]["episodes"]},
            BASELINE_POOLED_PRIOR: {
                "label": BASELINE_LABELS[BASELINE_POOLED_PRIOR],
                "state": pooled_token,
                "episodes": pooled_eval["summary"]["PRIMARY"]["episodes"]},
            CHALLENGER: {
                "label": BASELINE_LABELS[CHALLENGER],
                "state": challenger_token,
                "episodes": []},
        },
        "proper_score": PROPER_SCORE_LINE,
        "labels": {"status": LABEL_HISTORICAL, "identity_view": IDENTITY_VIEW},
    }
    if split == "TUNE" and info_leak_ctx.get("retired"):
        block["tune_retirement"] = info_leak_ctx["record"]
    return block


# ---------------------------------------------------------------------------
# outputs
# ---------------------------------------------------------------------------

def maybe_log_retirement(ledger: TrialLedger, pid: str, engine: OutcomeEngine,
                         state: dict, tune_anchor: dt.date | None,
                         detected_at: str) -> dict:
    """E10: when the family's TUNE is non-empty and the INFO-LEAK predicate
    fires, log exactly one holdout_retired row (source
    sni_s0_holdout_retirement) and return the LANE_MANIFEST record. An empty
    TUNE returns 'EMPTY — retirement not applicable'; TRAIN is never retired."""
    scan = engine.info_leak_scan(tune_anchor)
    if tune_anchor is not None and scan["leak"]:
        mem = state["membership"][pid]
        tune_shas = [mem["sha_table"][str(h)]["TUNE"] for h in GRADE_HORIZONS]
        membership_sha = hashlib.sha256(
            "|".join(tune_shas).encode("utf-8")).hexdigest()
        first_off = sorted({v["first_offending_date"]
                            for v in scan["series"].values()
                            if v["first_offending_date"]})
        steps = {k: v["steps_above_tolerance"] for k, v in scan["series"].items()}
        maxes = {k: v["max_abs_step"] for k, v in scan["series"].items()}
        cfg = {
            "event": "holdout_retired",
            "protocol_id": pid,
            "version": PROTOCOL_VERSION,
            "split": "TUNE",
            "membership_sha256": membership_sha,
            "contamination_class": INFO_LEAK_CLASS,
            "detected_at": detected_at,
            "evidence": (f"series=close/close_price; "
                         f"first_offending_date={','.join(first_off)}; "
                         f"steps_above_tolerance={steps}; "
                         f"max_abs_step={maxes}"),
        }
        ledger.log_trial(cfg, family=ledger_family(pid),
                         info_cutoff=engine.last_bar_date.isoformat(),
                         source=RETIREMENT_SOURCE,
                         note=("A23 INFO-LEAK: TUNE RETIRED; " +
                               INFO_LEAK_INVARIANCE_NOTE))
        return {
            "protocol_id": pid,
            "split": "TUNE",
            "contamination_class": INFO_LEAK_CLASS,
            "detected_at": detected_at,
            "evidence": cfg["evidence"],
            "successor": f"{pid} v2 — not drafted; owner = seat/S0",
            "membership_sha256": membership_sha,
        }
    return {
        "protocol_id": pid,
        "split": "TUNE",
        "state": ("EMPTY — retirement not applicable"
                  if tune_anchor is None else
                  "scanned; no adjustment-factor step above tolerance; "
                  "TUNE not retired"),
        "first_tune_anchor": tune_anchor.isoformat() if tune_anchor else None,
    }


def generate_outputs(repo_root: Path, input_ref: str, out_dir: Path,
                     ledger_path: Path, seal_dir: Path) -> dict:
    loader = GitBlobLoader(repo_root, input_ref)
    verify_pinned_blobs(repo_root, input_ref)
    state = compute_state(loader)
    state["prereg_digest_sha256"] = prereg_digest_of(state)

    # verify the seal BEFORE any outcome is computed
    verify_seal(seal_dir, state)

    engine = OutcomeEngine(loader)
    occ = compute_outcomes(engine, state)

    tune_anchors: dict[str, dt.date | None] = {}
    for pid in PROTOCOLS:
        anchors = [dt.date.fromisoformat(ep.opener.s_us)
                   for h in GRADE_HORIZONS
                   for ep in state["membership"][pid]["counted"].get(h, [])
                   if split_label(dt.date.fromisoformat(ep.opener.s_us)) == "TUNE"]
        tune_anchors[pid] = min(anchors) if anchors else None

    (out_dir / "results").mkdir(parents=True, exist_ok=True)
    (out_dir / "observations").mkdir(parents=True, exist_ok=True)

    detected_at = base_commit_detected_at(input_ref, repo_root)
    retirement_records: dict[str, dict] = {}
    results: dict[str, dict] = {}
    exclusions_by_family = exclusion_index_by_family(state)

    for pid in PROTOCOLS:
        fam = PROTOCOL_FAMILY[pid]
        ledger = TrialLedger(path=ledger_path)
        with register_trials(ledger_family(pid), budget=FAMILY_BUDGET,
                             reason=FAMILY_BUDGET_REASON, ledger=ledger):
            # E10 retirement row: logged after the budget row, inside the block
            retirement_records[pid] = maybe_log_retirement(
                ledger, pid, engine, state, tune_anchors[pid], detected_at)

        info_leak_ctx = {
            "retired": retirement_records[pid].get("contamination_class")
            == INFO_LEAK_CLASS,
            "record": retirement_records.get(pid, {}),
        }

        # ladder state per (h, split) — baseline-independent (reads honest-N
        # and cluster-N), so one pass serves all 12 config rows
        ladder_notes: dict[int, dict[str, str]] = {}
        for h in GRADE_HORIZONS:
            for split in SPLITS:
                prim = evaluate_family(pid, state, occ, h, split,
                                       BASELINE_ALWAYS_LONG,
                                       pooled_prior_dir=None)["summary"]["PRIMARY"]
                ladder_notes.setdefault(h, {})[split] = abstention_state(prim)

        # one log_trial per itemized config (including not-estimable ones)
        for h in GRADE_HORIZONS:
            for baseline in (BASELINE_ALWAYS_LONG, BASELINE_TRAILING63,
                             BASELINE_POOLED_PRIOR, CHALLENGER):
                note = ";".join(sorted(set(ladder_notes[h].values())))
                ledger.log_trial(
                    {"protocol_id": pid, "version": PROTOCOL_VERSION,
                     "baseline": baseline, "horizon": h},
                    family=ledger_family(pid),
                    info_cutoff=engine.last_bar_date.isoformat(),
                    source=TRIAL_LEDGER_SOURCE,
                    note=note)

        ledger_counts = {
            "literal_n": ledger.literal_n(family=ledger_family(pid)),
            "effective_n": ledger.effective_n(family=ledger_family(pid)),
            "declared_budget": ledger.declared_budget(family=ledger_family(pid)),
        }

        splits_obj: dict[str, dict] = {}
        for split in SPLITS:
            splits_obj[split] = {}
            for h in GRADE_HORIZONS:
                splits_obj[split][f"h{h}"] = build_block(
                    pid, state, occ, h, split, ledger_counts,
                    exclusions_by_family.get(PROTOCOL_FAMILY[pid], []),
                    info_leak_ctx)
        splits_obj["TEST"] = ("none (prospective only; REG §2 registration "
                              "gate not met)")

        results[pid] = {
            "label": LABEL_HISTORICAL,
            "protocol_id": pid,
            "title": PROTOCOL_TITLE[pid],
            "family": PROTOCOL_FAMILY[pid],
            "counting_clock": "MARKET_US",
            "identity_view": IDENTITY_VIEW,
            "authority_flags": dict(AUTHORITY_FLAGS_FALSE),
            "reg_canonical_family": REG_CANONICAL_FAMILY[pid],
            "honest_n_note": ("honest-N counts the graded cohort (alibaba) "
                              "only; census-only issuer episodes are listed "
                              "in the manifests and never counted (V0 row 14)"),
            "splits": splits_obj,
        }
        (out_dir / "results" / f"{pid}.json").write_text(
            json.dumps(results[pid], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")

    observations = render_observations(state, occ)
    (out_dir / "observations" / "episodes.jsonl").write_text(
        "".join(json.dumps(o, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False) + "\n" for o in observations),
        encoding="utf-8")

    lane_manifest = {
        "lane": LANE,
        "version": PROTOCOL_VERSION,
        "base_commit": BASE_COMMIT,
        "input_ref": input_ref,
        "branch": BRANCH,
        "labels": {"status": LABEL_HISTORICAL, "identity_view": IDENTITY_VIEW},
        "authority_flags": dict(AUTHORITY_FLAGS_FALSE),
        "families": list(PROTOCOLS),
        "declared_budgets": {pid: FAMILY_BUDGET for pid in PROTOCOLS},
        "itemized_grid_size": len(itemized_grid("P04")),
        "trial_ledger_path": TRIAL_LEDGER_REL_PATH,
        "prereg_digest_sha256": state["prereg_digest_sha256"],
        "info_leak": [retirement_records[pid] for pid in PROTOCOLS],
        "hk_series_vintage": "VINTAGE_UNVERIFIABLE (disclosed; not retired)",
        "train_retirement": "TRAIN is never retired (SL §8 step 6)",
        "census_only": [
            "tencent issuer group (00700) — counted, listed, abstained, never graded",
            "HK legs (9988, 0700) — never graded (V0 row 14)"],
        "not_supported_in_s2": {pid: NOT_SUPPORTED_LINE
                                for pid in NOT_SUPPORTED_PROTOCOLS},
        "evidence_command": (
            "python3 research/single_name_intelligence/event_response/run_s2.py "
            f"--input-ref {BASE_COMMIT} --out-dir "
            "research/single_name_intelligence/runs/s2_event_response "
            "--trial-ledger-path research/single_name_intelligence/runs/"
            "s2_event_response/trial_ledger.jsonl"),
    }
    (out_dir / "LANE_MANIFEST.json").write_text(
        json.dumps(lane_manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")

    report = render_report(results, retirement_records)
    (out_dir / "REPORT.md").write_text(report, encoding="utf-8")
    return {"results": results, "state": state, "occ": occ,
            "retirements": retirement_records, "engine": engine}


def prereg_digest_of(state: dict) -> str:
    return full_spec_digest(state)[1]


def full_spec_digest(state: dict) -> tuple[dict, str]:
    """The ONE spec construction shared with build_seal (same keys, same
    digest): the base spec plus the frozen programme grouping and the frozen
    event exclusions, then the content digest."""
    from s2_seal import build_prereg_spec
    spec = build_prereg_spec(state["class_summary"]["count_per_category"],
                             state["vocab"], state["prereg_membership_table"])
    spec["programmes_frozen"] = state["programmes"]
    spec["event_exclusions_frozen"] = state["event_exclusions"]
    return spec, prereg_digest(spec)


# ---------------------------------------------------------------------------
# REPORT.md (REG §5 order for every family x h x split block)
# ---------------------------------------------------------------------------

def _fmt(x):
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:+.6f}"
    return str(x)


def render_report(results: dict, retirement_records: dict) -> str:
    lines: list[str] = []
    a = lines.append
    a("# S2 conditional event-response study — P04 EVT-RESULTS, P05 EVT-CAPITAL, P06 EVT-REGULATORY")
    a("")
    a(f"**{LABEL_HISTORICAL}**")
    a("")
    a("The graded cohort is the Alibaba issuer group on its US ADS leg "
      "(BABA `SEC:US-XNYS-BABA` vs SPY total return, MARKET_US). HK legs "
      "(9988 `SEC:HK-XHKG-09988`, 0700 `SEC:HK-XHKG-00700`) and the whole "
      "Tencent issuer group are CENSUS-ONLY: counted, listed, abstained, never "
      "graded (V0 row 14). Every window return is a conditional post-event "
      "co-movement description over a fixed window; the day-s move is excluded "
      "and disclosed; nothing here is a forecast, a signal, an attribution or "
      "authority of any kind.")
    a("")
    for pid in NOT_SUPPORTED_PROTOCOLS:
        a(f"- **{pid}: {NOT_SUPPORTED_LINE}**")
    a("")
    a("## Abstention ladder (first match wins; never a 0.5 fill)")
    a("")
    a("`ABSTAIN_NO_EPISODES` (honest-N 0) → `ABSTAIN_INSUFFICIENT_CLUSTERS` "
      "(cluster-N < 2: no test, no CI, per-episode rows printed descriptively) "
      "→ `DESCRIPTIVE_ONLY` (< 153) → `TESTED`.")
    a("")
    a("## INFO-LEAK (A23) and vintage disclosure")
    a("")
    for pid in PROTOCOLS:
        rec = retirement_records[pid]
        if rec.get("contamination_class") == INFO_LEAK_CLASS:
            a(f"- **{pid} TUNE RETIRED** — contamination class "
              f"`{INFO_LEAK_CLASS}`; detected_at {rec['detected_at']}; "
              f"successor: {rec['successor']}. "
              f"{INFO_LEAK_INVARIANCE_NOTE}. The split is still computed and "
              "printed below, labelled NON-CONFIRMATORY — TUNE RETIRED.")
        else:
            a(f"- {pid}: {rec.get('state')}"
              + (f" (first TUNE anchor {rec.get('first_tune_anchor')})"
                 if rec.get("first_tune_anchor") else ""))
    a(f"- HK series (9988, 0700): VINTAGE_UNVERIFIABLE (disclosed; not retired).")
    a(f"- TRAIN is never retired (SL §8 step 6).")
    a("")
    for pid in PROTOCOLS:
        res = results[pid]
        a(f"## {res['title']}")
        a("")
        a(f"Ledger family `{ledger_family(pid)}` (budget {FAMILY_BUDGET}, "
          f"FLOOR); REG canonical family `{REG_CANONICAL_FAMILY[pid]}` is "
          "recorded for the later R1 step and is never written from S2.")
        a("")
        for split in ("TRAIN", "TUNE", "QUARANTINE"):
            obj = res["splits"][split]
            if isinstance(obj, str):
                a(f"### {split}: {obj}")
                a("")
                continue
            for h in GRADE_HORIZONS:
                blk = obj[f"h{h}"]
                fr = blk["family_row"]
                a(f"### {split} · h={h}")
                a("")
                a(f"**Label.** {blk['labels']['status']}")
                a("")
                a(f"{blk['plain_word_null']}")
                a("")
                a(f"1. **Null.** see the plain-word statement above.")
                a(f"2. **Analysis set.** PRIMARY leads; SENS-A honest-N "
                  f"{blk['analysis_set']['SENS_A']['honest_n']} / cluster-N "
                  f"{blk['analysis_set']['SENS_A']['cluster_n']}; SENS-B "
                  f"honest-N {blk['analysis_set']['SENS_B']['honest_n']} / "
                  f"cluster-N {blk['analysis_set']['SENS_B']['cluster_n']}.")
                a(f"3. **honest-N (PRIMARY).** {blk['honest_n']['PRIMARY']}")
                a(f"4. **cluster-N (PRIMARY).** {blk['cluster_n']['PRIMARY']}")
                a(f"5. **Literal row count.** {blk['literal_row_count']} "
                  "(pre step 0; transparency only, never a sample size)")
                ve = blk["visible_exclusions"]
                a(f"6. **Visible exclusions.** excluded-and-listed "
                  f"({ve['excluded_and_listed_count']}): "
                  f"{', '.join(ve['excluded_and_listed']) if ve['excluded_and_listed'] else 'none'}; "
                  f"confounded {ve['confounded']}; absorbed {ve['absorbed']}; "
                  f"purged {ve['purged']}; QUARANTINE {ve['quarantine']}.")
                t = blk["test"]
                if isinstance(t, str):
                    a(f"7. **Test.** {t}")
                else:
                    a(f"7. **Test.** {t['test']}; hits {t['hits']}/{t['n']}; "
                      f"p = {t['p_value']}; alpha {t['alpha']}; "
                      f"Wilson CI {t['wilson_ci']}.")
                c = blk["ci"]
                if isinstance(c, str):
                    a(f"8. **CI.** {c}")
                else:
                    a(f"8. **CI.** {c['statistic']} CI {c['ci']}; block: "
                      f"{c['block']}; cluster variable: {c['cluster_variable']}.")
                tr = blk["trials"]
                a(f"9. **Trial count.** literal_n {tr['literal_n']}; "
                  f"effective_n {tr['effective_n']}; declared_budget "
                  f"{tr['declared_budget']} — {tr['effective_n_label']}.")
                rc = blk["receipt"]
                a(f"10. **Receipt.** {rc['code_commit_sha']}; prereg digest "
                  f"`{rc['prereg_digest_sha256']}`; seal row {rc['seal_row']}; "
                  f"ledger {rc['trial_ledger_path']}; prior looks: "
                  f"{rc['prior_looks']}.")
                a("")
                a("**Commission family row.** "
                  f"event count {fr['event_count']}; distinct calendar "
                  f"clusters {fr['distinct_calendar_clusters']}; honest-N "
                  f"{fr['honest_n']} (SENS-A {fr['honest_n_sens_a']}, SENS-B "
                  f"{fr['honest_n_sens_b']}); effective N {fr['effective_n']} "
                  "(trials; never a sample N); pooling weight "
                  f"{fr['pooling_weight']}; uncertainty {fr['uncertainty']}; "
                  f"abstention state **{fr['abstention_state']}**.")
                a("")
                a("**Baselines.**")
                for bkey, bobj in blk["baselines"].items():
                    label = bobj["label"]
                    if "state" in bobj:
                        a(f"- {label}: {bobj['state']}")
                    eps = bobj["episodes"]
                    if not eps and "state" not in bobj:
                        a(f"- {label}: no counted episodes in this block")
                    for r in eps:
                        d = r["direction"]
                        ds = "ABSTAIN" if d is None else f"{d:+d}"
                        hit = r["hit"]
                        hs = ("—" if hit is None else
                              ("hit" if hit == 1 else
                               ("TIE (excess exactly 0)" if r["tie"] else "non-hit")))
                        a(f"- {label}: episode {r['episode_key'][:12]} s_us "
                          f"{r['s_us']} excess {r['excess'] if r['excess'] is not None else 'ABSTAIN (' + r['outcome_state'] + ')'} "
                          f"direction {ds} → {hs}")
                a("")
                a(f"**Proper score.** {blk['proper_score']}")
                if "tune_retirement" in blk:
                    rec = blk["tune_retirement"]
                    a("")
                    a(f"**NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK).** "
                      f"evidence: {rec['evidence']}; membership_sha256 "
                      f"`{rec['membership_sha256']}`; successor "
                      f"{rec['successor']}.")
                a("")
    a("## Census-only issuer group: tencent (00700)")
    a("")
    a("Counted and listed, never graded (V0 row 14): the interim-results "
      "announcement (news_id 12280990, 2026-08-12 16:31 HKT) forms one census "
      "episode per horizon (TUNE; at h=63 its window reaches past 2026-10-01 "
      "and the line carries the purged flag). It never enters any graded "
      "honest-N, test, CI or family row above.")
    a("")
    a("## Excluded-and-listed census (graded cohort)")
    a("")
    a("- `earnings.parquet#ticker=BABA` — TIMESTAMP_QUALITY EVENT_DATE is not "
      "an admissible t_avail (IL §1); listed, never an anchor (P04 scope).")
    a("- `12295308,12295380,12300619` — one general-mandate placing programme "
      "(ONE event under REG P05), excluded and listed: E0 gap 10 (HK placement "
      "coverage misses general-mandate placings).")
    a("- `12291963` — census-level near-token refusal (token `40700` is not "
      "`00700`); tencent census scope.")
    a("")
    a("## Reproduction")
    a("")
    a("```")
    a("python3 research/single_name_intelligence/event_response/run_s2.py \\")
    a(f"    --input-ref {BASE_COMMIT} \\")
    a("    --out-dir research/single_name_intelligence/runs/s2_event_response \\")
    a("    --trial-ledger-path research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl")
    a("```")
    a("")
    a("`--check` reruns into a temp dir and byte-compares every output "
      "(ledger after dropping `ts`); the runner first recomputes every "
      "membership_sha256 and the prereg digest and exits non-zero on any "
      "mismatch with the seal.")
    a("")
    return "\n".join(lines) + "\n"


def render_observations(state: dict, occ: dict) -> list[dict]:
    """One observation row per manifest line: graded outcomes for the graded
    cohort; census-only rows carry NOT COMPUTED — census only (V0 row 14)."""
    out = []
    for pid in PROTOCOLS:
        for h in GRADE_HORIZONS:
            for line in state["membership"][pid]["lines_by_h"].get(h, []):
                obj = json.loads(line)
                key = obj["episode_key"]
                if obj["flags"]["census_only"]:
                    outcome = {"state": "NOT COMPUTED — census only (V0 row 14)"}
                else:
                    outcome = occ["outcomes"].get(
                        (key, h), {"state": "ABSTAIN_MISSING_ENDPOINT",
                                   "window": None})
                out.append({
                    "protocol_id": pid,
                    "horizon": h,
                    "episode_key": key,
                    "issuer_key": obj["issuer_key"],
                    "split": obj["split"],
                    "purged": obj["flags"]["purged"],
                    "census_only": obj["flags"]["census_only"],
                    "cluster_key": obj["cluster_key"],
                    "outcome": outcome,
                })
    out.sort(key=lambda o: (o["protocol_id"], o["horizon"], o["episode_key"]))
    return out


# ---------------------------------------------------------------------------
# seal verification + --check
# ---------------------------------------------------------------------------

def verify_seal(seal_dir: Path, state: dict) -> None:
    seal_path = seal_dir / "SEAL_AND_BUDGET.json"
    if not seal_path.exists():
        raise SystemExit(f"seal not found: {seal_path}")
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    if seal.get("prereg_digest_sha256") != prereg_digest_of(state):
        raise SystemExit("SEAL MISMATCH: prereg digest differs from the seal")
    sealed_table = {(r["protocol_id"], str(r["horizon"]), r["split"]):
                    (r["count"], r["membership_sha256"])
                    for r in seal.get("membership_table", [])}
    for pid in PROTOCOLS:
        mem = state["membership"][pid]
        for h in GRADE_HORIZONS:
            committed = seal_dir / "manifests" / f"{pid}_h{h}.jsonl"
            rebuilt = "".join(mem["lines_by_h"].get(h, []))
            if not committed.exists():
                raise SystemExit(f"SEAL MISMATCH: missing manifest {committed}")
            if committed.read_text(encoding="utf-8") != rebuilt:
                raise SystemExit(
                    f"SEAL MISMATCH: manifest bytes differ for {pid} h{h}")
            for split in ("TRAIN", "TUNE", "QUARANTINE"):
                got = (mem["count_table"].get(str(h), {}).get(split, 0),
                       mem["sha_table"].get(str(h), {}).get(split))
                want = sealed_table.get((pid, str(h), split))
                if want is None or want != got:
                    raise SystemExit(
                        f"SEAL MISMATCH: membership table {pid} h{h} {split}: "
                        f"seal {want} vs rebuilt {got}")


def run_check(repo_root: Path, input_ref: str, seal_dir: Path) -> int:
    with tempfile.TemporaryDirectory(prefix="s2_check_") as td:
        tmp = Path(td)
        generate_outputs(repo_root, input_ref, tmp, tmp / "trial_ledger.jsonl",
                         seal_dir)
        problems: list[str] = []
        compared = ("REPORT.md", "LANE_MANIFEST.json",
                    "results/P04.json", "results/P05.json", "results/P06.json",
                    "observations/episodes.jsonl")
        for rel in compared:
            a = (tmp / rel).read_bytes()
            b = (seal_dir / rel).read_bytes()
            if a != b:
                problems.append(rel)
        la = [json.loads(l) for l in (tmp / "trial_ledger.jsonl")
              .read_text(encoding="utf-8").splitlines() if l.strip()]
        lb = [json.loads(l) for l in (seal_dir / "trial_ledger.jsonl")
              .read_text(encoding="utf-8").splitlines() if l.strip()]
        for row in la + lb:
            row.pop("ts", None)
        if json.dumps(la, sort_keys=True) != json.dumps(lb, sort_keys=True):
            problems.append("trial_ledger.jsonl (ts dropped)")
        if problems:
            print("--check FAILED; byte differences in: " + ", ".join(problems),
                  file=sys.stderr)
            return 1
        print("--check OK: every output byte-identical "
              "(ledger compared after dropping ts)")
        return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-ref", default=BASE_COMMIT)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--trial-ledger-path", required=True)  # NO default (E11)
    ap.add_argument("--seal-dir", default=None)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--repo-root", default=None)
    args = ap.parse_args()

    repo_root = Path(args.repo_root) if args.repo_root else None
    if repo_root is None:
        proc = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            print("not inside a git checkout; pass --repo-root", file=sys.stderr)
            return 2
        repo_root = Path(proc.stdout.strip())
    seal_dir = (Path(args.seal_dir) if args.seal_dir else
                repo_root / "research/single_name_intelligence/runs/s2_event_response")

    ledger_path = Path(args.trial_ledger_path)
    refuse_data_path(repo_root, ledger_path)

    if args.check:
        return run_check(repo_root, args.input_ref, seal_dir)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    generate_outputs(repo_root, args.input_ref, out_dir, ledger_path, seal_dir)
    print(f"S2 evidence written to {out_dir} (ledger {ledger_path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
