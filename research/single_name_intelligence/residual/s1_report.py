"""s1_report.py — REG §5 null-disclosure blocks, in the frozen order (D12).

Every block carries exactly these ten fields, in this order (a test pins the
order in both REPORT.md and results/<Pxx>.json):

  1 null             plain-word null
  2 analysis_set     PRIMARY = SENS-A = SENS-B for rolling anchors (IL §4)
  3 honest_n         distinct units after the IL §3 collapse — the only sample N
  4 cluster_n        distinct cluster keys (= trade date of the anchor s)
  5 literal_rows     input manifest rows for the (protocol, subject, h); never
                     a sample size
  6 exclusions       excluded-listed / confounded / absorbed / purged / QUARANTINE
  7 test             name, sidedness, alpha
  8 ci               with block length and cluster variable named
  9 trial_accounting literal_n, effective_n, declared_budget (read back from
                     the run-local trial ledger)
  10 receipt         code tree sha, prereg digest, seal row, ledger path,
                     prior looks (none for v1)

Every block names its split (in the block key and in analysis_set).
"""
from __future__ import annotations

from collections import Counter

from s1_prereg import POWER_FLOOR_N

FIELD_ORDER = ["null", "analysis_set", "honest_n", "cluster_n", "literal_rows",
               "exclusions", "test", "ci", "trial_accounting", "receipt"]

ANALYSIS_SET_ROLLING = ("PRIMARY = SENS-A = SENS-B (no event bundling for "
                        "rolling anchors, IL §4); split={split}")

LABEL_BLOCKED = "vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1)"
LABEL_HK_VINTAGE = ("VINTAGE_UNVERIFIABLE (HK series, no raw column) — "
                    "disclosed, NOT retired")
TCEHY_EXEMPLAR = ("UNRESOLVED — not an admitted security (M0 qualification); "
                  "no protocol row registered; owner = seat/S0")
V1_BASE = "c5a79a69826eaa6c34b8d7a59ead6506c5f8888d"
V1_RUNS = "research/single_name_intelligence/runs/s1_residual"
PREREG_DIGEST = "c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab"
FINDING_WORDS = ("criterion met", "beats", "rejects")


def make_block(*, null: str, split: str, honest_n: int, cluster_n: int,
               literal_rows: int, exclusions: dict, test: dict, ci: dict,
               trial_accounting: dict, receipt: dict) -> dict:
    block = {
        "null": null,
        "analysis_set": ANALYSIS_SET_ROLLING.format(split=split),
        "honest_n": honest_n,
        "cluster_n": cluster_n,
        "literal_rows": literal_rows,
        "exclusions": exclusions,
        "test": test,
        "ci": ci,
        "trial_accounting": trial_accounting,
        "receipt": receipt,
    }
    assert list(block.keys()) == FIELD_ORDER
    return block


def block_key(protocol_id: str, subject: str, h: int, split: str, config: str) -> str:
    return f"{protocol_id}|{subject}|h={h}|{split}|{config}"


def empty_exclusions() -> dict:
    return {"excluded_listed": 0, "confounded": 0, "absorbed": 0,
            "purged": 0, "quarantine": 0, "detail": {}}


def parse_block_key(key: str) -> dict:
    parts = key.split("|")
    pid, subject, hpart, split = parts[0], parts[1], parts[2], parts[3]
    h = int(hpart.split("=", 1)[1])
    if split.startswith("TUNE"):
        split_base = "TUNE"
    elif split.startswith("TRAIN"):
        split_base = "TRAIN"
    else:
        split_base = split
    return {"protocol": pid, "subject": subject, "h": h,
            "split": split_base, "split_raw": split,
            "config": "|".join(parts[4:])}


def is_retired_block(block: dict) -> bool:
    return "TUNE RETIRED" in (block.get("analysis_set") or "")


def s0_criterion_holds(block: dict) -> bool:
    """Computed S0 incremental-explanation decision from stored numbers."""
    t = block.get("test") or {}
    stat = t.get("statistic") or {}
    ci = block.get("ci") or {}
    delta = stat.get("delta_R2")
    if delta is None:
        delta = ci.get("delta_R2")
    bounds = ci.get("ci95")
    if delta is None or not bounds:
        return False
    return delta > 0 and bounds[0] > 0


def block_lead(key: str, block: dict) -> str:
    n = block["honest_n"]
    if n < POWER_FLOOR_N:
        return (f"ABSTAIN — honest_n {n} < {POWER_FLOOR_N} "
                "(REG power floor); not a test result")
    if is_retired_block(block):
        v1 = (block.get("test") or {}).get("verdict") or block.get("null") or ""
        desc = (v1.replace("S0 criterion met; ", "")
                .replace("S0 criterion met", "")
                .replace("criterion met", ""))
        return (f"criterion not assessable — TUNE RETIRED (A23 INFO-LEAK); "
                f"descriptive comparison: {desc}")
    return ""


def family_effective_n(protocols: dict, pid: str) -> int:
    p = protocols[pid]
    for key in p["block_order"]:
        acc = p["blocks"][key].get("trial_accounting") or {}
        if "effective_n" in acc:
            return int(acc["effective_n"])
    return 0


def family_alpha(effective_n: int) -> float:
    return 0.05 / effective_n if effective_n else float("inf")


def cells_with_unadjusted_p(protocols: dict) -> list[tuple[str, float, int, str, int]]:
    """(key, p, honest_n, protocol, effective_n) for every cell that has a p_value."""
    out = []
    for pid in ("P01", "P02", "P03"):
        p = protocols.get(pid) or {}
        eff = family_effective_n(protocols, pid) if pid in protocols else 0
        for key, b in (p.get("blocks") or {}).items():
            pv = (b.get("test") or {}).get("p_value")
            if pv is None:
                continue
            out.append((key, float(pv), int(b["honest_n"]), pid, eff))
    return out


def family_wise_clearing(protocols: dict, pid: str) -> list[str]:
    """Cells whose unadjusted p clears family-wise α AND honest_n >= POWER_FLOOR_N."""
    if pid not in protocols:
        return []
    eff = family_effective_n(protocols, pid)
    a = family_alpha(eff)
    hit = []
    for key, b in protocols[pid]["blocks"].items():
        pv = (b.get("test") or {}).get("p_value")
        if pv is None:
            continue
        if pv < a and b["honest_n"] >= POWER_FLOOR_N:
            hit.append(key)
    return hit


def appendix_cells(protocols: dict) -> list[tuple[str, float, float, str]]:
    """Cells with unadjusted p < 0.05 that fail the family-wise haircut."""
    rows = []
    for key, pv, _n, pid, eff in cells_with_unadjusted_p(protocols):
        a = family_alpha(eff)
        if pv < 0.05 and pv >= a:
            rows.append((key, pv, a, pid))
    return rows


def criterion_met_rows(protocols: dict) -> list[dict]:
    rows = []
    for pid in ("P01", "P02", "P03"):
        p = protocols.get(pid) or {}
        for key, b in (p.get("blocks") or {}).items():
            if not s0_criterion_holds(b):
                continue
            meta = parse_block_key(key)
            rows.append({
                "key": key,
                "protocol": pid,
                "subject": meta["subject"],
                "split": meta["split"],
                "horizon": meta["h"],
                "honest_n": b["honest_n"],
                "retired": is_retired_block(b),
            })
    return rows


def verdict_bucket(key: str, block: dict) -> str:
    n = block["honest_n"]
    if n < POWER_FLOOR_N:
        return "below_floor_abstain"
    if is_retired_block(block):
        return "tune_retired"
    v = ((block.get("test") or {}).get("verdict") or block.get("null") or "")
    if s0_criterion_holds(block):
        return "s0_criterion_holds"
    if "KILL/HOLD" in v:
        return "kill_hold"
    if "departs" in v:
        return "departs"
    if "indistinguishable" in v or "not met" in v or "NOT ESTIMABLE" in v:
        return "null_held"
    return "other"


def exemplar_table(protocols: dict) -> list[dict]:
    names = [
        ("BABA (ADS)", "adr_baba"),
        ("9988.HK", "hkd_9988"),
        ("0700.HK", "hkd_0700"),
    ]
    rows = []
    for label, needle in names:
        per = {}
        for pid in ("P01", "P02", "P03"):
            blocks = (protocols.get(pid) or {}).get("blocks") or {}
            keys = [k for k in blocks if needle in k]
            dist = Counter(verdict_bucket(k, blocks[k]) for k in keys)
            per[pid] = {"n": len(keys), "dist": dict(sorted(dist.items()))}
        rows.append({"exemplar": label, "subject": needle, "protocols": per})
    rows.append({"exemplar": "TCEHY", "subject": None, "text": TCEHY_EXEMPLAR})
    return rows


def m2_over_m1_sentence(protocols: dict) -> str | None:
    p03 = (protocols.get("P03") or {}).get("blocks") or {}
    baba = p03.get("P03|adr_baba|h=5|TRAIN|M2_vs_M1")
    if baba is None or not s0_criterion_holds(baba):
        return None
    hk_keys = [k for k in p03 if k.endswith("|M2_vs_M1")
               and ("hkd_9988" in k or "hkd_0700" in k)]
    if not hk_keys:
        return None
    for k in hk_keys:
        b = p03[k]
        if s0_criterion_holds(b):
            return None
        v = (b.get("test") or {}).get("verdict") or ""
        # below-floor cells keep the computed KILL/HOLD in statistic/ci; the
        # printed verdict may be the power-floor ABSTAIN.
        if "KILL/HOLD" not in v and not (b["honest_n"] < POWER_FLOOR_N):
            return None
    return ("The M2-over-M1 result is BABA-ADS h=5 TRAIN descriptive only and "
            "is KILL/HOLD on every 9988/0700 M2_vs_M1 cell.")


def below_floor_count(protocols: dict) -> int:
    n = 0
    for pid in protocols:
        for b in protocols[pid]["blocks"].values():
            if b["honest_n"] < POWER_FLOOR_N:
                n += 1
    return n


def lead_change_counts(protocols: dict) -> dict:
    below = below_floor_count(protocols)
    hk_tune_not_retired = 0
    retired_no_criterion = 0
    train_blocked = 0
    for pid in protocols:
        for key, b in protocols[pid]["blocks"].items():
            meta = parse_block_key(key)
            aset = b.get("analysis_set") or ""
            if meta["subject"].startswith("hkd_") and meta["split"] == "TUNE" \
                    and pid == "P03":
                if "TUNE RETIRED" not in aset:
                    hk_tune_not_retired += 1
            if is_retired_block(b) and "criterion met" not in str(b):
                retired_no_criterion += 1
            if meta["split"] == "TRAIN" and "BLOCKED-AS-EVIDENCE" in aset:
                train_blocked += 1
    return {
        "below_floor_abstain_leads": below,
        "p03_hk_tune_unretired": hk_tune_not_retired,
        "retired_blocks_without_criterion_met": retired_no_criterion,
        "train_blocks_blocked_as_evidence": train_blocked,
    }


def version_record_obj(lane: dict, protocols: dict, membership_equal: bool) -> dict:
    digest = lane.get("prereg_digest_sha256") or PREREG_DIGEST
    return {
        "version": "v1.1",
        "supersedes": {
            "version": "v1",
            "base_commit": V1_BASE,
            "runs_dir": V1_RUNS,
        },
        "reason": "defect repair (X1-01..X1-10, A6-F1..F3)",
        "defects": {
            "X1-01": "coverage and current regime section; retired TUNE never prints criterion met",
            "X1-02": "exemplar table for BABA ADS / 9988.HK / 0700.HK / TCEHY UNRESOLVED",
            "X1-03": "P03 TUNE retirement scoped to adr_baba (P03-BABA); HK TUNE not retired",
            "X1-04": "0700 COVERAGE HOLE printed per block and in the exemplar row",
            "X1-05": "honest_n < 153 cells lead with ABSTAIN (REG power floor)",
            "X1-06": "family-wise α = 0.05 / effective_n per family; unadjusted p in appendix",
            "X1-07": "committed-evidence tests read runs/s1_residual_v1_1/",
            "X1-08": "every TRAIN block carries BLOCKED-AS-EVIDENCE",
            "X1-09": "IPCA challenger universe disclosure; cannot support a coverage claim",
            "X1-10": "assert_authority_false on AUTHORITY_FLAGS, seal write, and verify_seal",
            "A6-F1": "spec_hash docstring: factor order is significant by design",
            "A6-F2": "mirror_mean_ci docstring: 4-dp rounding of bounds vs printed mean",
            "A6-F3": "beta_window_dates raises on non-strictly-increasing subject_dates",
        },
        "prereg_digest_v1": PREREG_DIGEST,
        "prereg_digest_v1_1": digest,
        "prereg_digest_unchanged": digest == PREREG_DIGEST,
        "membership_table_unchanged": bool(membership_equal),
        "configuration_added_removed_or_changed": False,
        "lead_changes": lead_change_counts(protocols),
        "voided": [
            "v1 P03 HK TUNE TUNE RETIRED labels were outside the prereg scope and are void",
            "v1 leads that presented p-values or S0 verdicts at honest_n < 153 are void as leads",
        ],
        "authority_flags": {"rank": False, "gate": False, "size": False,
                            "signal": False, "escalation": False, "trade": False},
        "descriptive_only": True,
    }


def _render_version_record_md(rec: dict) -> list[str]:
    L = ["## Version record", ""]
    L.append(f"v1.1 supersedes v1 at base commit {rec['supersedes']['base_commit']} "
             f"({rec['supersedes']['runs_dir']}).")
    L.append(f"reason = {rec['reason']}")
    for k, v in rec["defects"].items():
        L.append(f"- {k}: {v}")
    L.append(f"prereg digest v1 = {rec['prereg_digest_v1']}")
    L.append(f"prereg digest v1.1 = {rec['prereg_digest_v1_1']}")
    L.append(f"prereg digest unchanged = {rec['prereg_digest_unchanged']}")
    L.append(f"membership_table unchanged = {rec['membership_table_unchanged']}")
    L.append("no configuration added, removed, or changed")
    L.append("cells whose LEAD changed (relabel/abstain) by category:")
    for k, v in rec["lead_changes"].items():
        L.append(f"- {k}: {v}")
    for v in rec["voided"]:
        L.append(v)
    L.append(f"authority_flags all false; descriptive_only = {rec['descriptive_only']}")
    L.append("")
    return L


def _sanitize_finding_words(obj):
    if isinstance(obj, str):
        t = obj
        for w in FINDING_WORDS:
            t = t.replace(w, "")
        return t
    if isinstance(obj, dict):
        return {k: _sanitize_finding_words(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_finding_words(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_sanitize_finding_words(v) for v in obj)
    return obj


def _below_floor_receipt(block: dict) -> dict:
    t = block.get("test") or {}
    ci = block.get("ci") or {}
    stat = t.get("statistic") or {}
    rec = {
        "honest_n": block["honest_n"],
        "statistic": stat,
        "p_value": t.get("p_value"),
        "delta_R2": (stat.get("delta_R2") if "delta_R2" in stat else ci.get("delta_R2")),
        "ci95": ci.get("ci95"),
        "mean": ci.get("mean", ci.get("mean_d")),
    }
    return _sanitize_finding_words(rec)


def _coverage_section(protocols: dict, extra: dict) -> list[str]:
    L = ["## Coverage and current regime", ""]
    n_below = below_floor_count(protocols)
    L.append(f"below-floor cell count: {n_below} "
             f"(honest_n < {POWER_FLOOR_N} REG power floor)")
    L.append("")
    for pid in ("P01", "P02", "P03"):
        if pid not in protocols:
            continue
        eff = family_effective_n(protocols, pid)
        clearing = family_wise_clearing(protocols, pid)
        listed = ", ".join(clearing) if clearing else "none"
        L.append(f"{pid}: family-wise α = 0.05 / effective_n = {eff}; "
                 f"cells clearing α with honest_n >= {POWER_FLOOR_N}: {listed}")
    L.append("")
    rows = criterion_met_rows(protocols)
    L.append("cells that meet the S0 criterion (computed from results; "
             "retired status noted):")
    if not rows:
        L.append("- none")
    else:
        for r in rows:
            ret = "retired" if r["retired"] else "not-retired"
            L.append(f"- {r['protocol']}|{r['subject']}|h={r['horizon']}|{r['split']} "
                     f"honest_n={r['honest_n']} {ret}")
    L.append("")
    nonret_tune = [r for r in rows
                   if r["split"] == "TUNE" and not r["retired"]
                   and r["honest_n"] >= POWER_FLOOR_N]
    if nonret_tune:
        L.append("non-retired TUNE cells with honest_n >= 153 that meet the "
                 "S0 criterion:")
        for r in nonret_tune:
            L.append(f"- {r['key']}")
    else:
        L.append("ANY non-retired TUNE cell with honest_n >= 153 that meets the "
                 "S0 criterion: none")
        L.append("No S1 residual cell covering the 2024-01-01..2026-10-01 TUNE "
                 "window meets the S0 criterion as confirmatory evidence; the "
                 "criterion-met cells are pre-2024 TRAIN or TUNE-retired and "
                 "do not cover the 2026 regime.")
    L.append("")
    L.append("exemplar table (cell counts and verdict distribution, from results):")
    holes = extra.get("coverage_holes") or {}
    for row in exemplar_table(protocols):
        if row["exemplar"] == "TCEHY":
            L.append(f"- TCEHY: {row['text']}")
            continue
        bits = []
        for pid in ("P01", "P02", "P03"):
            info = row["protocols"][pid]
            bits.append(f"{pid} n={info['n']} {info['dist']}")
        extra_txt = ""
        if row["subject"] == "hkd_0700":
            hole_bits = [holes[h] for h in sorted(holes)]
            if hole_bits:
                extra_txt = "; " + "; ".join(hole_bits)
        L.append(f"- {row['exemplar']}: " + "; ".join(bits) + extra_txt)
    sent = m2_over_m1_sentence(protocols)
    if sent:
        L.append(sent)
    ch = extra.get("challenger_line")
    if ch:
        L.append(ch)
    L.append("")
    return L


def _appendix_section(protocols: dict) -> list[str]:
    rows = appendix_cells(protocols)
    L = ["## Multiple-looks appendix (unadjusted, non-confirmatory)", ""]
    L.append("Unadjusted p < 0.05 that do not clear family-wise α. "
             "These are not findings.")
    if not rows:
        L.append("- none")
    else:
        for key, pv, a, pid in rows:
            L.append(f"- {key}: unadjusted p={pv} ; family α={a} ({pid})")
    L.append("")
    return L


def render_report_md(lane: dict, protocols: dict, extra: dict | None = None) -> str:
    """Human-readable twin of results/<Pxx>.json, same per-block order."""
    extra = extra or {}
    membership_equal = extra.get("membership_table_unchanged", True)
    rec = version_record_obj(lane, protocols, membership_equal)
    lines: list[str] = []
    for lab in lane["labels"]:
        lines.append(f"> {lab}")
    lines.append("")
    lines.append(f"# {lane['title']}")
    lines.append("")
    lines.extend(_render_version_record_md(rec))
    lines.append(f"BASE: {lane['base']}  ")
    lines.append(f"branch: {lane['branch']}  ")
    seal_path = extra.get("seal_path") or (
        f"{lane.get('runs_rel', V1_RUNS)}/SEAL_AND_BUDGET.json")
    lines.append(f"seal: {seal_path} "
                 f"(prereg digest {lane['prereg_digest_sha256']})  ")
    lines.append("prior looks: none for v1  ")
    lines.append("")
    lines.extend(_coverage_section(protocols, extra))
    holes = extra.get("coverage_holes") or {}
    for pid in sorted(protocols):
        p = protocols[pid]
        lines.append(f"## {pid} — {p['family']}")
        lines.append("")
        for key in p["block_order"]:
            b = p["blocks"][key]
            meta = parse_block_key(key)
            lines.append(f"### {key}")
            lines.append("")
            lead = block_lead(key, b)
            if lead:
                lines.append(lead)
            if meta["subject"] == "hkd_0700" and meta["h"] in holes:
                lines.append(holes[meta["h"]])
            test_out = b["test"]
            receipt_out = b["receipt"]
            null_out = b["null"]
            if b["honest_n"] < POWER_FLOOR_N:
                test_out = _sanitize_finding_words(dict(b["test"]))
                null_out = (f"ABSTAIN — honest_n {b['honest_n']} < {POWER_FLOOR_N} "
                            "(REG power floor); not a test result")
                receipt_out = dict(b["receipt"])
                receipt_out["below_floor_receipt"] = _below_floor_receipt(b)
            lines.append(f"1. null: {null_out}")
            lines.append(f"2. analysis_set: {b['analysis_set']}")
            lines.append(f"3. honest_n: {b['honest_n']}")
            lines.append(f"4. cluster_n: {b['cluster_n']}")
            lines.append(f"5. literal_rows: {b['literal_rows']}")
            lines.append(f"6. exclusions: {b['exclusions']}")
            lines.append(f"7. test: {test_out}")
            lines.append(f"8. ci: {b['ci']}")
            lines.append(f"9. trial_accounting: {b['trial_accounting']}")
            lines.append(f"10. receipt: {receipt_out}")
            if b["honest_n"] < POWER_FLOOR_N:
                lines.append("below-floor receipt: "
                             f"{receipt_out['below_floor_receipt']}")
            lines.append("")
    lines.extend(_appendix_section(protocols))
    return "\n".join(lines) + "\n"
