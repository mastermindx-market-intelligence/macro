"""s1_prereg.py — the frozen PREREG_SPEC for the S1 residual lane (C1 seal).

Single source of truth for every frozen choice (D1-D15). build_seal.py writes
PREREG_SPEC.json and its digest; run_s1.py recomputes the digest and refuses
to run on any mismatch. Nothing in this file may change without a new protocol
version (SL §6, DEC:PREREG-DESIGN-CHANGE-SUPERSEDES).
"""
from __future__ import annotations

import hashlib
import json

BASE = "5ef7a7f39f99232bf9b574c7603da1011ee3af66"
BRANCH = "claude/sni-s1-residual-20261011"
LANE = "s1_residual"
VERSION = "v1"
RUNS_REL = "research/single_name_intelligence/runs/s1_residual"

S0_BLOBS = {
    "REG": ("research/single_name_intelligence/protocols/S0_PROTOCOL_REGISTER.md",
            "1b891b3c60a54bc5eba94cb7fafa8fec6ffb6ea6"),
    "IL": ("research/single_name_intelligence/protocols/S0_INDEPENDENCE_LAW.md",
           "6ec4b097ce3fd24261da12061b3418fde945efaf"),
    "SL": ("research/single_name_intelligence/protocols/S0_SPLIT_AND_CONTAMINATION_LAW.md",
           "c06a91beee22626eab1912aaa8a3baa6856913a2"),
}

INPUT_PINS = {
    "data/yahoo/BABA.parquet": "2c627eecb86b92f20c969498fed2d127e032b3b6",
    "data/yahoo/SPY.parquet": "9b306b50884279e4155030298627faa26e5c6d9a",
    "data/yahoo/KWEB.parquet": "d42bd75db56f8ad5c2530ee415262a0c68b913bd",
    "data/hk_stocks/9988.HK.parquet": "2792f4bc5685cd13ceabcdac25acf37a43acb199",
    "data/hk_stocks/0700.HK.parquet": "b439ba667ff8bfcdd35d854b7d461ff624a48df9",
    "data/hk/2800.HK.parquet": "07c65f47d1b2a62f8163774d13237ed53127270c",
    "data/hk/3033.HK.parquet": "be48af26ae803eaaf4481c259a625d77d66a704f",
    "data/reference/security_master.parquet": "85ef75104840b6b5be3aceeac21f1dbfabad6472",
    "config/single_name_intelligence/coverage_profiles/alibaba.yml":
        "0914dd8bdf9330a77c442cf5015315235a7878e7",
    "config/single_name_intelligence/coverage_profiles/tencent.yml":
        "d5f952887b82a254a6ec3cf3d816ba22ca366f97",
}

ENGINE_CITATIONS = {
    "engine/qledger.py": {
        "GRADE_HORIZONS": 114, "HORIZON_UNIT_TRADING": 141, "MARKET_US": 180,
        "MARKET_HK": 182, "CLOCK_CALENDARS": 190, "HorizonWindow": 255,
        "resolve_horizon_window": 352, "_leg_ret_in_window": 2540,
        "grade_claim": 2698, "register_FORBIDDEN_here": 2026,
    },
    "engine/grading_stats.py": {
        "BOOT_DRAWS": 43, "BOOT_SEED": 44, "wilson_ci": 56,
        "block_bootstrap_ci": 121, "block_bootstrap_scalar_ci_NOT_PERMITTED": 193,
    },
    "engine/trial_ledger.py": {
        "DEFAULT_PATH_never_used_here": 49, "TrialLedger": 66, "log_trial": 146,
        "log_declared_budget": 202, "literal_n": 253, "effective_n": 257,
        "declared_budget": 287, "register_trials": 296,
    },
}

SUBJECTS = {
    "P01": [{"counter": "adr_baba", "security_id": "SEC:US-XNYS-BABA",
             "issuer_key": "alibaba", "market": "US", "data_path": "data/yahoo/BABA.parquet",
             "canonical_issuer_id": "ISS:US-XNYS-BABA",
             "identity_state": "RESOLVED",
             "identity_resolved_as_of": "2026-08-21 10:17:27"}],
    "P02": [
        {"counter": "hkd_9988", "security_id": "SEC:HK-XHKG-09988",
         "issuer_key": "alibaba", "market": "HK", "data_path": "data/hk_stocks/9988.HK.parquet",
         "canonical_issuer_id": "UNRESOLVED",
         "identity_state": "NO_ISSUER_EVIDENCE",
         "identity_resolved_as_of": "2026-08-20 18:50:35"},
        {"counter": "hkd_0700", "security_id": "SEC:HK-XHKG-00700",
         "issuer_key": "tencent", "market": "HK", "data_path": "data/hk_stocks/0700.HK.parquet",
         "canonical_issuer_id": "UNRESOLVED",
         "identity_state": "NO_ISSUER_EVIDENCE",
         "identity_resolved_as_of": "2026-08-20 18:50:35"},
    ],
}

BENCHES = {
    "P01": {"counter": "SPY", "data_path": "data/yahoo/SPY.parquet",
            "market": "US", "role": "US market factor / bench, adjusted TR close"},
    "P02": {"counter": "2800.HK", "data_path": "data/hk/2800.HK.parquet",
            "market": "HK", "role": "HK market factor / bench, FIXED at the seal for v1; "
            "3033.HK is not a P02 bench"},
}

HORIZONS = [5, 21, 63]

D1_LABELS = [
    "HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; nothing here is a "
    "forecast, a signal, or authority",
    "vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1)",
    "identity = RETROSPECTIVE JOIN (A07), identity_resolved_as_of = security_master ingested_at",
]
AUTHORITY_FLAGS = {"rank": False, "gate": False, "size": False, "signal": False,
                   "escalation": False, "trade": False}


def build_spec() -> dict:
    return {
        "lane": LANE,
        "version": VERSION,
        "base": BASE,
        "branch": BRANCH,
        "status": "HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 registration gate NOT met",
        "labels": D1_LABELS,
        "authority_flags": AUTHORITY_FLAGS,
        "s0_blob_ids": {k: {"path": p, "blob": b} for k, (p, b) in S0_BLOBS.items()},
        "input_pins": dict(INPUT_PINS),
        "engine_citations": ENGINE_CITATIONS,
        "s0_line_drift_note": (
            "S0 cites trial_ledger L48/L126/L159/L210/L214/L242; at the BASE commit the "
            "same symbols sit at L49/L146/L202/L253/L257/L287. The drift is recorded, "
            "S0 is never edited."),
        "splits": {
            "law": "SL §2 (immutable, A23)",
            "train": "s < 2024-01-01",
            "tune": "2024-01-01 <= s < 2026-10-01",
            "quarantine": "s >= 2026-10-01 (listed and counted, never evaluated)",
            "purge": {
                "train": "coverage_date >= 2024-01-01 -> PURGED_TRAIN",
                "tune": "coverage_date >= 2026-10-01 -> PURGED_TUNE",
                "rule": "purged units are counted visibly and never moved to another split",
            },
        },
        "clock": {
            "law": "D3",
            "anchor": "session s on the subject's market calendar "
                      "(BABA MARKET_US; 9988/0700 MARKET_HK)",
            "window": "resolve_horizon_window(entry_anchor = calendar day before s, h, "
                      "HORIZON_UNIT_TRADING, market); assert fill_date == s",
            "abstain_resolver_none": "resolver returns None -> ABSTAIN_RESOLVER_NONE (listed)",
            "abstain_fill_mismatch": "fill_date != s -> ABSTAIN_FILL_MISMATCH (listed)",
            "leg_rule": "close(coverage)/close(fill) - 1 on the adjusted (TR) close; both "
                        "endpoint bars on EXACTLY those sessions else ABSTAIN_MISSING_ENDPOINT; "
                        "cites engine/qledger.py _leg_ret_in_window L2540",
            "decision_cutoff": "D(s) = last session before s on the same calendar; every "
                               "decision-cutoff quantity uses bars <= D(s) only",
            "disclosure": "the day-s move close(D(s)) -> close(s) is excluded from every "
                          "decision-cutoff input and this is disclosed",
        },
        "rolling_anchors": {
            "law": "IL §3 step 7; SL §1 non-event units (D4)",
            "first_anchor": "first session s on the subject's calendar with >= 252 subject "
                            "bars <= D(s)",
            "spacing": "next anchor = the session h+1 sessions after the previous anchor "
                       "(non-overlapping windows, no shared endpoints)",
            "episode_key": "sha256(\"{issuer_key}|rolling_anchor|{s.isoformat()}|{counter}\")",
            "cluster_key": "trade date of s; cluster-N == honest-N for rolling units (both printed)",
            "honest_n": "per (protocol, subject, h, split); NEVER summed across subjects, "
                        "counters, horizons or protocols (A22)",
            "no_pooling": "BABA and 9988 are the same issuer group: never pooled; different "
                          "protocols (P01 vs P02) or separate rows (P03)",
        },
        "manifests": {
            "law": "SL §5 (D5)",
            "built_before": "any outcome; outcome-free builder reads ONLY market calendars "
                            "and the subjects' index dates (never a price/volume column)",
            "row_schema": ["protocol_id", "version", "horizon", "episode_key", "issuer_key",
                           "counter", "security_id", "unit", "anchor_session_date",
                           "coverage_date", "split"],
            "split_vocab": ["TRAIN", "TUNE", "QUARANTINE", "PURGED_TRAIN", "PURGED_TUNE",
                            "ABSTAIN_RESOLVER_NONE", "ABSTAIN_FILL_MISMATCH"],
            "sort": "(horizon, episode_key)",
            "serialization": "json.dumps(sort_keys=True, separators=(\",\",\":\"), "
                             "ensure_ascii=False) + newline",
            "membership_sha256": "per (protocol, subject, h, split): sha256 of that split's "
                                 "lines in canonical order",
        },
        "protocols": {
            "P01": {
                "reg_block": "REG P01 (L236)",
                "subject": SUBJECTS["P01"],
                "bench": BENCHES["P01"],
                "market": "MARKET_US",
                "horizons": HORIZONS,
                "excess": "subject_ret - bench_ret, simple returns on the adjusted TR close "
                          "(grade_claim convention, qledger L2698/L2812); each leg reproduces "
                          "_leg_ret_in_window L2540",
                "baselines": {
                    "always_long": "direction +1",
                    "trail63": "sign of trailing-63-session excess at D(s): "
                               "(P_BABA(D)/P_BABA(D63)-1) - (P_SPY(D)/P_SPY(D63)-1), D63 = 63 "
                               "sessions before D(s) on the NYSE calendar; both series need "
                               "bars on D and D63 exactly else direction 0",
                },
                "hit_rule": "hit = (sign(excess) == direction); excess == 0 exactly -> "
                            "non-hit, listed as a tie; direction 0 -> ABSTAIN (listed, not a "
                            "hit, not a miss)",
                "tests": {
                    "H0_1": {"null": "hit rate = 0.50", "test": "exact one-sided binomial "
                             "(greater) via math.comb", "alpha": 0.05,
                             "interval": "wilson_ci on the hit rate"},
                    "H0_2": {"null": "median excess = 0", "test": "exact two-sided sign test",
                             "sidedness": "two-sided (frozen at this seal; REG did not fix "
                             "sidedness — recorded as a GAP)",
                             "interval": "mirror-trick block-bootstrap CI on mean excess (D9)"},
                },
                "configs": "2 baselines x 3 h = 6",
            },
            "P02": {
                "reg_block": "REG P02 (L271)",
                "subject": SUBJECTS["P02"],
                "bench": BENCHES["P02"],
                "market": "MARKET_HK",
                "horizons": HORIZONS,
                "excess": "as P01, vs 2800.HK adjusted TR",
                "exclusions": "RMB counters are never subjects; the two subjects are never pooled",
                "baselines": "as P01 (D63 on the HKEX calendar)",
                "hit_rule": "as P01",
                "tests": {
                    "H0_1": {"null": "hit rate = 0.50", "test": "exact one-sided binomial "
                             "(greater), alpha 0.05", "alpha": 0.05,
                             "interval": "wilson_ci on the hit rate"},
                    "H0_2": {"null": "median excess = 0", "test": "exact two-sided sign test",
                             "sidedness": "two-sided",
                             "interval": "mirror-trick CI on mean excess (D9)"},
                },
                "configs": "2 subjects x 2 baselines x 3 h = 12",
            },
            "P03": {
                "reg_block": "REG P03 (L303)",
                "nature": "contemporaneous decomposition, NEVER a pre-move forecast",
                "returns": "daily and window LOG returns on the adjusted close",
                "fit": "OLS with intercept of the subject's daily log return on factor daily "
                       "log return(s) over the last 252 subject bars <= D(s), inner-joined on "
                       "dates; require >= 200 joint observations else ABSTAIN_INSUFFICIENT_HISTORY",
                "models": {
                    "M0": "zero model (common = 0); sigma_hat = std(ddof=1) of in-window "
                          "subject daily log returns",
                    "M1": "market only: BABA SPY; HK 2800.HK",
                    "M2": "market + sector: BABA SPY + KWEB; HK 2800.HK + 3033.HK",
                    "disclosures": "BABA is a KWEB constituent — the sector factor carries "
                                   "the subject; KWEB is never a Tencent quote; the M2 "
                                   "circularity is disclosed and accepted at the seal",
                },
                "outcome": "r = log(close(coverage)/close(fill)); F = the same window log "
                           "return of each factor; common = sum(beta_k * F_k) (intercept "
                           "excluded, disclosed); resid = r - common; sigma_hat = std(ddof=1) "
                           "of the in-window daily OLS residuals; z = resid/(sigma_hat*sqrt(h))",
                "column_naming": "decision-cutoff quantities carry __dc (beta_*__dc, "
                                 "sigma_hat__dc, n_obs__dc); observation-cutoff quantities "
                                 "carry __oc (r__oc, F_*__oc, common__oc, resid__oc, z__oc)",
                "spec_hash": "sha256 of canonical JSON {model, subject_security_id, factors, "
                             "window:252, min_obs:200, h, return:'log', "
                             "intercept:'excluded_from_common'}",
                "abstention_states": ["OK", "ABSTAIN_INSUFFICIENT_HISTORY",
                                      "ABSTAIN_MISSING_ENDPOINT", "ABSTAIN_RESOLVER_NONE",
                                      "ABSTAIN_FILL_MISMATCH", "PURGED", "QUARANTINE"],
                "input_coverage_per_row": ["n_obs__dc", "beta_window_first__dc",
                                           "beta_window_last__dc",
                                           "subject_endpoint_fill__oc",
                                           "subject_endpoint_coverage__oc",
                                           "factor_endpoint_flags__oc"],
                "incremental_criterion": {
                    "null": "incremental explanation = 0 (P03 H0)",
                    "statistic": "for a pair (prev, next): d_i = (r - c_prev)^2 - "
                                 "(r - c_next)^2 over units where BOTH are OK; "
                                 "delta_R2 = sum(d)/sum(r^2)",
                    "uncertainty": "mirror-trick CI on mean(d) (D9)",
                    "decision": "next beats prev on a split iff delta_R2 > 0 AND CI lower "
                                "bound > 0 (approximately one-sided alpha 0.025); else print "
                                "KILL/HOLD-AS-RESEARCH — never retarget, re-horizon or swap "
                                "the cohort",
                },
                "calibration": "per model and split: coverage of |z| <= 1.96 vs nominal 0.95 "
                               "and |z| <= 1 vs 0.6827, wilson_ci; stability = TRAIN vs TUNE "
                               "coverage side by side plus mean/std of beta__dc per split",
                "cohort": "confirmatory-in-principle cohort = BABA only: M1 vs M0 and M2 vs "
                          "M1 at 3 h (6 configs); 9988/0700 decompositions print as "
                          "DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7): 12 configs, "
                          "logged as trials",
                "configs": "6 BABA + 3 challenger + 12 HK-descriptive = 21",
            },
        },
        "mirror_trick": {
            "law": "D9 — the ONLY permitted bootstrap use for a mean",
            "construction": "CI of mean(x): block_bootstrap_ci(dates=concat(k,k), "
                            "vals=concat(x,-x), mask=concat(1,0), stat='mean'), default "
                            "draws/seed (800/7)",
            "block": "one non-overlapping anchor unit (h+1 sessions >= h)",
            "cluster_variable": "cluster key = trade date of s",
            "none_case": "None -> print CI NOT ESTIMABLE (cluster-N < 2)",
            "test_properties": ["identity vs the hand gap computation",
                                "constant series c -> [c, c] to 4 dp",
                                "shift-equivariance CI(x+a) == CI(x)+a within 1e-4"],
        },
        "info_leak_predicate": {
            "law": "D10 (A23 sealed)",
            "series": ["BABA", "SPY", "KWEB"],
            "statistic": "q_t = close_t/close_price_t; offending step: "
                         "|q_t/q_{t-1} - 1| > 1e-6",
            "window": "date >= earliest TUNE anchor of any protocol using that series AND "
                      "<= the input vintage (last bar)",
            "action": "TUNE RETIRED for every protocol using that series (P01, P03-BABA); "
                      "TUNE still computed and printed, labelled NON-CONFIRMATORY — TUNE "
                      "RETIRED (A23 INFO-LEAK)",
            "ledger_row": "TrialLedger.log_trial inside the register_trials block, after the "
                          "budget row; family sni.s1_residual.<Pxx>; source "
                          "sni_s0_holdout_retirement; detected_at = BASE commit date "
                          "(deterministic)",
            "manifest_row": "one LANE_MANIFEST.json row with successor 'Pxx v2 — not drafted; "
                            "owner = seat/S0'",
            "honesty_note": "a window return is invariant to a multiplicative adjustment "
                            "constant across the window; the leak is the vintage, not "
                            "necessarily the value",
            "hk_series": "no raw column: VINTAGE_UNVERIFIABLE — disclosed, NOT retired",
            "train": "never retired; an empty split prints EMPTY — retirement not applicable",
        },
        "trial_ledger": {
            "law": "D11 (seat-amended rule, binding)",
            "families": {
                "P01": "sni.s1_residual.P01",
                "P02": "sni.s1_residual.P02",
                "P03": "sni.s1_residual.P03",
            },
            "reg_s8_canonical_mapping": {
                "sni.s1_residual.P01": "sni.s0.P01",
                "sni.s1_residual.P02": "sni.s0.P02",
                "sni.s1_residual.P03": "sni.s0.P03",
                "note": "recorded at the seal for the later R1 promotion step; this lane "
                        "never writes sni.s0.* rows",
            },
            "budgets": {"P01": 6, "P02": 4, "P03": 4},
            "budget_meaning": "REG L205: budgets are FLOORS; exceeding them raises "
                              "effective_n and is never hidden",
            "itemized_grids": {
                "P01": {"count": 6,
                        "grid": "baseline(always_long, trail63) x h(5,21,63) x subject(adr_baba)"},
                "P02": {"count": 12,
                        "grid": "subject(hkd_9988, hkd_0700) x baseline(always_long, trail63) "
                                "x h(5,21,63)"},
                "P03": {"count": 21,
                        "grid": "BABA cohort: (M1_vs_M0, M2_vs_M1) x h(5,21,63) = 6; "
                                "challenger: ipca_vs_M1 x h(5,21,63) = 3; HK descriptive: "
                                "(M1_vs_M0, M2_vs_M1) x h(5,21,63) x (hkd_9988, hkd_0700) = 12"},
            },
            "rules": [
                "register_trials(family=..., budget=..., reason=..., "
                "ledger=TrialLedger(path=<--trial-ledger-path>)) BEFORE any outcome",
                "--trial-ledger-path is REQUIRED with NO default; exit 2 on a path under "
                "data/",
                "one log_trial per config attempted (including not-estimable), "
                "source='sni_s1_historical_descriptive', info_cutoff = last input bar date",
                "committed evidence run writes "
                "research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl; "
                "tests use tmp_path",
                "a test asserts the declared_budget row precedes every outcome row",
                "REG §5 item 10 names the run-local ledger path for this lane (the seat "
                "rule overrides REG's data/trial_ledger.jsonl for the run-local copy)",
            ],
        },
        "report": {
            "law": "D12 (REG §5 ORDER)",
            "field_order": ["null", "analysis_set", "honest_n", "cluster_n", "literal_rows",
                            "exclusions", "test", "ci", "trial_accounting", "receipt"],
            "analysis_set_text": "PRIMARY = SENS-A = SENS-B (no event bundling for rolling "
                                 "anchors, IL §4)",
            "every_block_names_its_split": True,
            "twin": "runs/s1_residual/results/<Pxx>.json with the same ten fields in the "
                    "same order; a test asserts the field order",
        },
        "challenger": {
            "law": "D13 (bounded; IPCA family; frozen now)",
            "model": "beta_i(t) = z_i(t-1)' Gamma; z = [1, mom_12_1, vol_63, rev_21]",
            "characteristics": {
                "mom_12_1": "log(P[t-22]/P[t-253])",
                "vol_63": "std(ddof=1) of the last 63 daily log returns",
                "rev_21": "log(P[t-1]/P[t-22])",
                "basis": "adjusted close bars <= t-1",
                "standardisation": "cross-sectional rank to [-0.5, 0.5] per date across "
                                   "names with valid values; drop a date with < 30 valid names",
            },
            "factor": "f_t = SPY daily log return",
            "gamma": "4 numbers = pooled OLS, no intercept, of r_i,t on [f_t, mom*f_t, "
                     "vol*f_t, rev*f_t] over the TRAIN panel only (t < 2024-01-01)",
            "universe": {
                "iteration": "data/yahoo/*.parquet at BASE in ascending sha256(path) order",
                "skip": ["SPY", "KWEB", "BABA"],
                "admit_if": ["schema has the adjusted close column",
                             "first index date <= 2012-01-03",
                             "last index date >= 2026-09-30",
                             "bars on >= 95% of NYSE sessions in [2012-01-03, 2026-09-30] "
                             "(index dates only)"],
                "cap": 150,
                "record": "runs/s1_residual/CHALLENGER_UNIVERSE.json: admitted path + blob id, "
                          "files examined, rejected-by-reason counts",
                "disclosures": ["survivorship (today's file set)",
                                "ETFs mixed with single names",
                                "no point-in-time membership"],
            },
            "estimability": {
                "thresholds": {"min_admitted_names": 30, "n_characteristics": 3,
                               "min_train_months_with_valid_cross_section": 60},
                "otherwise": "print CHALLENGER NOT ESTIMABLE with those coverage counts and "
                             "log the 3 configs as not-estimable",
            },
            "application": "BABA's z at D(s) ranked against the panel cross-section at D(s); "
                           "common_IPCA = beta_BABA(s) * F_SPY(window)",
            "comparison": "vs M1 on the S0 criterion on TUNE (Gamma never sees TUNE), with "
                          "TRAIN printed and labelled IN-SAMPLE for Gamma; a failed criterion "
                          "prints KILL/HOLD-AS-RESEARCH",
            "configs": 3,
        },
        "determinism": {
            "law": "D14",
            "no_wall_clock_in_outputs": True,
            "ledger_ts_exception": "the ledger's 'ts' is the only wall-clock value",
            "reproduce_command": "python3 research/single_name_intelligence/residual/run_s1.py "
                                 f"--input-ref {BASE} --out-dir <dir> --trial-ledger-path "
                                 "<dir>/trial_ledger.jsonl",
            "check_flag": "--check runs into a temp dir and byte-compares every output file "
                          "against runs/s1_residual/ (the ledger compared after dropping "
                          "'ts'), exit 0 iff identical",
            "seal_verification": "the runner first recomputes every membership_sha256 and the "
                                 "prereg digest and exits non-zero on any mismatch with the seal",
        },
        "kill_hold_rule": "a failed pre-declared criterion prints KILL/HOLD-AS-RESEARCH; it is "
                          "never rescued by changing the target, cohort or horizon (REG §5 "
                          "quoting masterplan L268)",
        "out_of_scope_note": "nothing under data/ or research/single_name_intelligence/protocols/ "
                             "is created or modified; no qledger register call (L2026); no "
                             "forecast store, grader, registry, scheduler, queue, router or "
                             "agent definition",
    }


def canonical_json(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def prereg_digest(spec: dict | None = None) -> str:
    return hashlib.sha256(canonical_json(spec or build_spec()).encode("utf-8")).hexdigest()
