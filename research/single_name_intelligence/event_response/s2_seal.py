"""S2 seal constants and the frozen preregistration spec (P04/P05/P06 only).

HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned,
non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN
(A07); conditional post-event co-movement description, never an attribution.

This module carries ONLY frozen constants and content-derived digests. It never
reads a price, never computes a return and never holds an outcome. The seal
builder (build_seal.py) and the evidence runner (run_s2.py) both import it, so
both sides see one definition of every frozen rule.

S0 sources (blob ids frozen at BASE 5ef7a7f39f99232bf9b574c7603da1011ee3af66):
- REG research/single_name_intelligence/protocols/S0_PROTOCOL_REGISTER.md
- IL  research/single_name_intelligence/protocols/S0_INDEPENDENCE_LAW.md
- SL  research/single_name_intelligence/protocols/S0_SPLIT_AND_CONTAMINATION_LAW.md
Where this packet and S0 differ, S0 wins; every observed difference is recorded
in SEAL_AND_BUDGET.md under DEVIATIONS.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date

# ---------------------------------------------------------------------------
# Identity of this lane
# ---------------------------------------------------------------------------
LANE = "s2_event_response"
BASE_COMMIT = "5ef7a7f39f99232bf9b574c7603da1011ee3af66"
BRANCH = "claude/sni-s2-event-response-20261011"
PROTOCOL_VERSION = "v1"

# The three S0 law blobs, pinned at BASE.
S0_BLOB_IDS = {
    "REG": {
        "path": "research/single_name_intelligence/protocols/S0_PROTOCOL_REGISTER.md",
        "blob": "1b891b3c60a54bc5eba94cb7fafa8fec6ffb6ea6",
    },
    "IL": {
        "path": "research/single_name_intelligence/protocols/S0_INDEPENDENCE_LAW.md",
        "blob": "6ec4b097ce3fd24261da12061b3418fde945efaf",
    },
    "SL": {
        "path": "research/single_name_intelligence/protocols/S0_SPLIT_AND_CONTAMINATION_LAW.md",
        "blob": "c06a91beee22626eab1912aaa8a3baa6856913a2",
    },
}

# ---------------------------------------------------------------------------
# E1 labels (every output file and every report block carries these)
# ---------------------------------------------------------------------------
LABEL_HISTORICAL = (
    "HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, "
    "non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN "
    "(A07), identity_resolved_as_of = security_master ingested_at; conditional "
    "post-event co-movement description, not an attribution"
)
IDENTITY_VIEW = "RETROSPECTIVE_JOIN"
AUTHORITY_FLAGS = {
    "rank_authority": False,
    "gate_authority": False,
    "size_authority": False,
    "signal_authority": False,
    "escalation_authority": False,
    "trade_authority": False,
}

# A07 identity resolution instants (security_master ingested_at, as stored).
IDENTITY_RESOLVED_AS_OF = {
    "SEC:US-XNYS-BABA": "2026-08-21T10:17:27",
    "SEC:HK-XHKG-09988": "2026-08-20T18:50:35",
    "SEC:HK-XHKG-00700": "2026-08-20T18:50:35",
}

# ---------------------------------------------------------------------------
# E2 families and the frozen classification table (category vocabulary seen in
# data/hk_filings/events.parquet at BASE -> one of the three IL §1 families or
# UNCLASSIFIED). A sentence-level text classifier is out of scope.
# ---------------------------------------------------------------------------
FAMILIES = ("results", "capital_action", "regulatory_material")
PROTOCOLS = ("P04", "P05", "P06")
PROTOCOL_FAMILY = {"P04": "results", "P05": "capital_action", "P06": "regulatory_material"}
PROTOCOL_TITLE = {
    "P04": "EVT-RESULTS (REG P04)",
    "P05": "EVT-CAPITAL (REG P05)",
    "P06": "EVT-REGULATORY (REG P06)",
}
NOT_SUPPORTED_PROTOCOLS = ("P07", "P08", "P11")
NOT_SUPPORTED_LINE = "NOT SUPPORTED in S2 (not commissioned)"

# category (exact vocabulary value) -> family | UNCLASSIFIED
CLASSIFICATION_TABLE = {
    "final_results": "results",
    "interim_results": "results",
    "quarterly_results": "results",
    "buyback": "capital_action",
    "general_mandate": "capital_action",
    "shareholder": "UNCLASSIFIED",
}
FAMILY_PRECEDENCE = {"results": 3, "capital_action": 2, "regulatory_material": 1}

# ---------------------------------------------------------------------------
# Issuer groups and counters (coverage profiles are READ only; profile-local
# keys are labels, never identity ids)
# ---------------------------------------------------------------------------
ISSUERS = ("alibaba", "tencent")
GRADED_ISSUER = "alibaba"          # the only graded issuer group (US ADS leg)
GRADED_LEG = {
    "alibaba": "adr_baba",
    "tencent": None,                # census only (V0 row 14)
}
GRADED_LEG_LABEL = {
    "alibaba": "adr_baba (SEC:US-XNYS-BABA, MARKET_US)",
    "tencent": "NONE — census only (V0 row 14)",
}
COUNTER_LOCAL_CODE = {
    "alibaba": {"hkd_9988": "09988"},
    "tencent": {"hkd_0700": "00700"},
}
COUNTER_SECURITY_ID = {
    "alibaba": {"hkd_9988": "SEC:HK-XHKG-09988", "adr_baba": "SEC:US-XNYS-BABA"},
    "tencent": {"hkd_0700": "SEC:HK-XHKG-00700"},
}

# ---------------------------------------------------------------------------
# E4 clock: counting clock is MARKET_US for every graded leg (REG P04/P05/P06
# US legs; HK legs are NOT SUPPORTED, V0 row 14). Both s clocks are computed
# for every event regardless.
# ---------------------------------------------------------------------------
COUNTING_CLOCK = "US"
GRADE_HORIZONS = (5, 21, 63)

# ---------------------------------------------------------------------------
# E6 splits (SL §2, immutable) and purge
# ---------------------------------------------------------------------------
SPLIT_TUNEE_START = date(2024, 1, 1)
SPLIT_QUARANTINE_START = date(2026, 10, 1)
SPLITS = ("TRAIN", "TUNE", "QUARANTINE")

# ---------------------------------------------------------------------------
# E7 baselines, challenger, pooling, proper score
# ---------------------------------------------------------------------------
BASELINE_ALWAYS_LONG = "always_long"
BASELINE_TRAILING63 = "trailing_63_excess_sign"
BASELINE_POOLED_PRIOR = "pooled_train_prior"
CHALLENGER = "challenger_hierarchy"
BASELINES = (BASELINE_ALWAYS_LONG, BASELINE_TRAILING63, BASELINE_POOLED_PRIOR)
BASELINE_LABELS = {
    BASELINE_ALWAYS_LONG: "baseline (i) always-long (+1)",
    BASELINE_TRAILING63: "baseline (ii) sign of the trailing-63-session excess at D(s)",
    BASELINE_POOLED_PRIOR: "baseline (iii) direction of the all-events pooled TRAIN prior",
    CHALLENGER: "challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name)",
}
MIN_TRAIN_CLUSTERS_POOLED_PRIOR = 2
POOLING_WEIGHT_TOKEN = "NOT ESTIMABLE"
PROPER_SCORE_LINE = "NOT SUPPORTED (REG P04: hit and excess are not a proper score)"
TRAILING63_SESSIONS = 63

# ---------------------------------------------------------------------------
# E8 statistics, minimum evidence, abstention ladder, kill/hold
# ---------------------------------------------------------------------------
ALPHA = 0.05
MIN_EPISODES = 153  # one-sided alpha 0.05, power 0.80, hit rate 0.60 vs 0.50
ABSTAIN_NO_EPISODES = "ABSTAIN_NO_EPISODES"
ABSTAIN_INSUFFICIENT_CLUSTERS = "ABSTAIN_INSUFFICIENT_CLUSTERS"
DESCRIPTIVE_ONLY = "DESCRIPTIVE_ONLY"
TESTED = "TESTED"
KILL_LINE = (
    "Kill/continue per REG P01: a failed criterion prints KILL or HOLD-AS-RESEARCH "
    "and is never rescued by changing target, cohort or horizon after seeing results."
)

# ---------------------------------------------------------------------------
# E10 A23 INFO-LEAK predicate
# ---------------------------------------------------------------------------
INFO_LEAK_STEP_TOLERANCE = 1e-6
INFO_LEAK_CLASS = "information_leak"
RETIREMENT_SOURCE = "sni_s0_holdout_retirement"
INFO_LEAK_INVARIANCE_NOTE = (
    "a window return is invariant to a multiplicative adjustment constant across "
    "the window; the leak is the vintage, not necessarily the value"
)
HK_VINTAGE_LINE = "VINTAGE_UNVERIFIABLE (disclosed; HK series carry no adjustment-factor pair; not retired)"
TRAIN_NEVER_RETIRED = "TRAIN is never retired (SL §8 step 6)"

# ---------------------------------------------------------------------------
# E11 trial ledger (seat-amended rule)
# ---------------------------------------------------------------------------
TRIAL_LEDGER_REL_PATH = "research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl"
TRIAL_LEDGER_SOURCE = "sni_s2_historical_descriptive"
FAMILY_BUDGET = 6  # REG §8: floors, not caps
FAMILY_BUDGET_REASON = (
    "floor per REG §8 (L205); itemized grid per family = 3 frozen baselines x 3 horizons"
    " = 9 configs, plus the challenger column x 3 horizons = 3 (logged even when NOT"
    " ESTIMABLE) = 12 itemized configs"
)
REG_CANONICAL_FAMILY = {
    "P04": "sni.s0.P04",
    "P05": "sni.s0.P05",
    "P06": "sni.s0.P06",
}


def ledger_family(pid: str) -> str:
    """S2 run-local ledger family for a protocol (never writes sni.s0.* rows)."""
    return f"sni.s2_event_response.{pid}"


def itemized_grid(pid: str) -> list[dict]:
    """The frozen itemized grid for one family: 12 configs."""
    rows = []
    for h in GRADE_HORIZONS:
        for b in BASELINES:
            rows.append({"protocol_id": pid, "version": PROTOCOL_VERSION,
                         "baseline": b, "horizon": h})
    for h in GRADE_HORIZONS:
        rows.append({"protocol_id": pid, "version": PROTOCOL_VERSION,
                     "baseline": CHALLENGER, "horizon": h})
    return rows


# ---------------------------------------------------------------------------
# E13 pinned inputs (path -> blob at BASE)
# ---------------------------------------------------------------------------
INPUT_MANIFEST = {
    "data/yahoo/BABA.parquet": "2c627eecb86b92f20c969498fed2d127e032b3b6",
    "data/yahoo/SPY.parquet": "9b306b50884279e4155030298627faa26e5c6d9a",
    "data/hk_stocks/9988.HK.parquet": "2792f4bc5685cd13ceabcdac25acf37a43acb199",
    "data/hk_stocks/0700.HK.parquet": "b439ba667ff8bfcdd35d854b7d461ff624a48df9",
    "data/hk_filings/events.parquet": "be30a5bc5ecbb8d007c248f0a26d51010c5027ab",
    "data/earnings/earnings.parquet": "8f0575464ba0a1abed7cee7799e90b8fab7bd6fc",
    "data/reference/security_master.parquet": "85ef75104840b6b5be3aceeac21f1dbfabad6472",
    "config/single_name_intelligence/coverage_profiles/alibaba.yml": "0914dd8bdf9330a77c442cf5015315235a7878e7",
    "config/single_name_intelligence/coverage_profiles/tencent.yml": "d5f952887b82a254a6ec3cf3d816ba22ca366f97",
    "research/single_name_intelligence/evidence/Alibaba/E1_COVERAGE_REPORT_2026-10-11.json": "11170a7406abcb70386a8827d5acf5e8b5a5ca0b",
    "research/single_name_intelligence/evidence/Tencent/E2_COVERAGE_REPORT_2026-10-11.json": "5c29370884099389454f336ed1dd794b97ce7901",
    "research/single_name_intelligence/evidence/Alibaba/E1_EVIDENCE_PACK_2026-10-11.md": "fde534f8fb912738fde8e2d9b3ebd03881b5ffa4",
    "research/single_name_intelligence/evidence/Alibaba/E1_ADVERSARIAL_CASES_2026-10-11.md": "49225d3e71ea3d141aef837dc6f351ac1cbb7544",
    "research/single_name_intelligence/evidence/Tencent/E2_EVIDENCE_PACK_2026-10-11.md": "47ec0d812c7fd5d160b6658b69858ed3f298ad81",
    "research/single_name_intelligence/evidence/Tencent/E2_ADVERSARIAL_CASES_2026-10-11.md": "817f8eefda838cb17300beac98f43133041d6631",
}

# Metadata columns the seal phase may request (never a price or a volume column).
EVENTS_METADATA_COLUMNS = ("news_id", "stock_code", "ticker", "category",
                           "announced_at", "date", "title", "subcats")
EARNINGS_METADATA_COLUMNS = ("ticker", "next_date", "next_time", "as_of",
                             "surprises_as_of")
SECURITY_MASTER_ID_COLUMNS = ("security_id", "issuer_id", "issuer_state",
                              "ingested_at")
# Outcome-phase columns (runner only; volume is never read).
PRICE_COLUMNS = ("Date", "close", "close_price")

COVERAGE_REPORTS = {
    "alibaba": {
        "path": "research/single_name_intelligence/evidence/Alibaba/E1_COVERAGE_REPORT_2026-10-11.json",
        "task": "E1",
    },
    "tencent": {
        "path": "research/single_name_intelligence/evidence/Tencent/E2_COVERAGE_REPORT_2026-10-11.json",
        "task": "E2",
    },
}

# The one event-source cell per issuer (E3(c)): hk_filings announcements.
EVENT_SOURCE_CELL = {
    "alibaba": "filings_announcements.hkd_9988",
    "tencent": "filings_announcements.hkd_0700",
}

# ---------------------------------------------------------------------------
# E3(c) dispositions for coverage cells
# ---------------------------------------------------------------------------
DISPOSITION_EVENT_SOURCE = "event source used (data/hk_filings/events.parquet, exact local_code token match)"
DISPOSITION_NOT_SOURCE = "not an S2 event source (state {state})"


def canonical_json(obj) -> str:
    """The one canonical JSON encoding used for digests and manifest lines."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def prereg_digest(spec: dict) -> str:
    return sha256_hex(canonical_json(spec))


def build_prereg_spec(classification_counts: dict, vocabulary: list[str],
                      membership_table: list[dict]) -> dict:
    """The frozen pre-registration spec. Every field is a rule, a count of
    metadata rows, or a pinned identifier — never an outcome."""
    return {
        "lane": LANE,
        "version": PROTOCOL_VERSION,
        "base_commit": BASE_COMMIT,
        "branch": BRANCH,
        "labels": {
            "status": LABEL_HISTORICAL,
            "identity_view": IDENTITY_VIEW,
            "authority_flags": dict(AUTHORITY_FLAGS),
        },
        "scope": {
            "protocols": list(PROTOCOLS),
            "not_supported_in_s2": [{"protocol_id": p, "line": NOT_SUPPORTED_LINE}
                                    for p in NOT_SUPPORTED_PROTOCOLS],
            "graded_issuer_group": GRADED_ISSUER,
            "graded_leg": GRADED_LEG_LABEL[GRADED_ISSUER],
            "census_only": ["tencent issuer group", "HK legs (9988, 0700)"],
        },
        "s0_sources": {k: dict(v) for k, v in S0_BLOB_IDS.items()},
        "families": [
            {
                "protocol_id": pid,
                "family": PROTOCOL_FAMILY[pid],
                "counting_clock": COUNTING_CLOCK,
                "ledger_family": ledger_family(pid),
                "reg_canonical_family": REG_CANONICAL_FAMILY[pid],
                "declared_budget": FAMILY_BUDGET,
                "budget_basis": "FLOOR (REG §8 L205)",
                "itemized_grid_size": len(itemized_grid(pid)),
                "itemized_grid": itemized_grid(pid),
            }
            for pid in PROTOCOLS
        ],
        "classification_table": {
            "source": "data/hk_filings/events.parquet category vocabulary (metadata only)",
            "mapping": dict(CLASSIFICATION_TABLE),
            "vocabulary_seen": list(vocabulary),
            "count_per_category": dict(classification_counts),
            "unclassified_rule": "a category the table does not map is UNCLASSIFIED: listed, never counted",
        },
        "event_sources": [
            {
                "id": "a",
                "path": "data/hk_filings/events.parquet",
                "selection": "rows whose exact '<br/>'-split stock_code token equals a profile counter local_code (09988 alibaba hkd_9988; 00700 tencent hkd_0700)",
                "t_avail": "announced_at (publisher-stated HKT, converted to UTC)",
                "timestamp_quality": "PUBLISHER_STATED",
            },
            {
                "id": "b",
                "path": "data/earnings/earnings.parquet",
                "selection": "rows for BABA",
                "timestamp_quality": "EVENT_DATE",
                "disposition": "excluded-and-listed (IL §1), never an anchor",
            },
            {
                "id": "c",
                "path": "E1/E2 coverage reports (census only)",
                "selection": "every coverage cell listed with its state and disposition",
            },
        ],
        "clock_rules": {
            "s_c": "first session on clock c whose REGULAR OPEN is strictly after t_avail (pre-open -> same day; in-session, HK midday break or after close -> next session; DISCLOSURE_DATE -> first session strictly after the date)",
            "graded_clock": "MARKET_US only (BABA leg)",
            "window": "entry_anchor = calendar day before s_US; resolve_horizon_window(entry_anchor, h, HORIZON_UNIT_TRADING, MARKET_US); assert fill_date == s_US else ABSTAIN_FILL_MISMATCH; None -> ABSTAIN_RESOLVER_NONE",
            "leg_return": "close(coverage_date)/close(fill_date) - 1 on the adjusted total-return close; both endpoint bars present on exactly those sessions else ABSTAIN_MISSING_ENDPOINT",
            "excess": "BABA return - SPY return",
            "decision_time": "D(s) = last NYSE session before s_US; every decision-time quantity uses bars <= D(s); the day-s move is excluded and disclosed",
            "W_h": "sessions s .. s+h inclusive (IL §1); the overlap window used by IL §3",
        },
        "collapse_rules": {
            "order": "IL §3 steps 0..N run IN FULL before anything is counted (A22)",
            "duplicate_reports": "repeated reports of one occurrence -> one event, earliest admissible t_avail",
            "programme": "one programme -> one event; execution returns are evidence rows",
            "cross_counter": "BABA and 9988 rows of one occurrence -> ONE alibaba episode; leg outcomes are columns of one episode, never extra N (IL §6)",
            "overlap": "overlapping windows within an issuer group at the same h handled per IL §3 step 4 (absorb / confounded flags), never silently merged, never double-counted",
            "clusters": "same-day shocks across issuer groups share a cluster key (trade date of s) and are counted in cluster-N, never merged into one episode (IL §8)",
            "exclusion_order": "excluded-and-listed rows are removed before episode formation; the exclusion is listed with its ids",
            "programme_rule": "among the selected rows of one issuer group, the capital_action rows whose category is general_mandate and whose title carries PLACING form ONE programme (proposal, pricing, completion = evidence rows); the frozen coverage exclusion then removes that programme for REG P05 with its ids listed (E0 gap 10: HK placement coverage misses general-mandate placings)",
        },
        "splits": {
            "TRAIN": "s < 2024-01-01",
            "TUNE": "2024-01-01 <= s < 2026-10-01",
            "QUARANTINE": "s >= 2026-10-01 (listed, counted, never evaluated)",
            "TEST": "prospective claims only; REG §2 registration gate not met, so S2 has no TEST",
            "purge": "TRAIN episode with coverage_date >= 2024-01-01, or TUNE episode with coverage_date >= 2026-10-01 -> PURGED (counted visibly, never moved)",
            "episode_key": "sha256('{issuer_key}|{opener_family}|{opener_t_avail_utc_iso8601}|{opener_evidence_pointer}') (SL §1)",
            "manifest_rule": "runs/s2_event_response/manifests/<Pxx>_h<h>.jsonl, sorted by (horizon, episode_key), canonical json lines; membership_sha256 per (protocol, h, split) = sha256 of that split's lines in order",
        },
        "baselines": {
            "i": "always-long (+1)",
            "ii": "sign of the trailing-63-session excess at D(s): (BABA(D)/BABA(D63) - 1) - (SPY(D)/SPY(D63) - 1), exact bars on D and D63 for both legs, else direction 0",
            "iii": "direction of the all-events pooled prior = sign of the mean excess of all counted TRAIN episodes across the three families at that h (PRIMARY set), computed from TRAIN only; TRAIN cluster-N < 2 -> NOT ESTIMABLE (abstain, never 0.5, never +1 by default)",
            "challenger": "NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N printed beside)",
            "pooling_weight": "NOT ESTIMABLE whenever baseline (iii) is not estimable or own-name cluster-N < 2; the token is printed, never a number by default",
            "proper_score": PROPER_SCORE_LINE,
            "hit_rule": "hit = sign(excess) == direction; excess == 0 exactly -> non-hit, listed as a tie; direction 0 -> ABSTAIN",
        },
        "statistics": {
            "h0": "post-event hit rate = 0.50 per horizon",
            "test": "exact one-sided binomial (greater) via math.comb",
            "alpha": ALPHA,
            "hit_rate_ci": "wilson_ci (3 dp)",
            "mean_excess_ci": "mirror-trick block_bootstrap_ci: dates=concat(k,k), vals=concat(x,-x), mask=concat([True]*n,[False]*n), stat='mean', default draws/seed; block = one episode window W_h; cluster variable = cluster key (trade date of s)",
            "forbidden": "block_bootstrap_scalar_ci is not permitted",
        },
        "minimum_evidence": {
            "episodes": MIN_EPISODES,
            "derivation": "one-sided alpha 0.05, power 0.80, hit rate 0.60 vs 0.50",
            "below_minimum": "DESCRIPTIVE ONLY — below the 153-episode minimum",
        },
        "abstention_ladder": [
            "ABSTAIN_NO_EPISODES (honest-N 0)",
            "ABSTAIN_INSUFFICIENT_CLUSTERS (cluster-N < 2: no test, no CI, per-episode rows printed descriptively)",
            "DESCRIPTIVE_ONLY (< 153)",
            "TESTED",
            "first match wins; never a 0.5 fill (A25)",
        ],
        "kill_hold_rule": KILL_LINE,
        "info_leak_predicate": {
            "series": "q_t = close_t / close_price_t for BABA and SPY",
            "rule": "any |q_t/q_{t-1} - 1| > 1e-6 on a date >= the earliest TUNE anchor and <= the last input bar",
            "class": INFO_LEAK_CLASS,
            "effect": "TUNE RETIRED for P04/P05/P06 (per family with a non-empty TUNE); TUNE still computed and printed, labelled NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)",
            "ledger_row": "log_trial(config={event: holdout_retired, protocol_id, version, split: TUNE, membership_sha256, contamination_class, detected_at (BASE commit date, deterministic), evidence}, family=sni.s2_event_response.<Pxx>, source=sni_s0_holdout_retirement) inside the register_trials block after the budget row",
            "manifest_row": "a retirement row in runs/s2_event_response/LANE_MANIFEST.json with successor '<Pxx> v2 — not drafted; owner = seat/S0'",
            "invariance_note": INFO_LEAK_INVARIANCE_NOTE,
            "hk_series": HK_VINTAGE_LINE,
            "train": TRAIN_NEVER_RETIRED,
            "empty_split": "EMPTY — retirement not applicable",
            "membership_sha256_construction": "sha256 of '|'.join(per-(protocol,h,TUNE) membership_sha256 for h in (5,21,63))",
        },
        "trial_ledger": {
            "path": TRIAL_LEDGER_REL_PATH,
            "required_arg": "--trial-ledger-path is REQUIRED with NO default; the runner refuses (exit 2) any path resolving inside <repo>/data/",
            "budgets": {pid: FAMILY_BUDGET for pid in PROTOCOLS},
            "effective_n": "TrialLedger.effective_n = max(base, declared, 1); printed, never hidden; labelled effective N (trials) — never a sample N (IL §1)",
        },
        "report_order": "REG §5 order: (1) plain-word null; (2) analysis set; (3) honest-N; (4) cluster-N; (5) literal row count; (6) visible exclusions; (7) test; (8) CI; (9) trial count; (10) receipt — then the commission family row",
        "determinism": {
            "command": "python3 research/single_name_intelligence/event_response/run_s2.py --input-ref "
                       + BASE_COMMIT + " --out-dir <dir> --trial-ledger-path <dir>/trial_ledger.jsonl",
            "check": "--check reruns into a temp dir and byte-compares every output against runs/s2_event_response/ (ledger compared after dropping ts); exit 0 iff identical",
            "seal_verification": "the runner first recomputes every membership_sha256 and the prereg digest and exits non-zero on any mismatch with the seal",
        },
        "membership_table": [dict(row) for row in membership_table],
    }
