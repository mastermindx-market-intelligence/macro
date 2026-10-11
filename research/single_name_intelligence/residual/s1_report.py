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

FIELD_ORDER = ["null", "analysis_set", "honest_n", "cluster_n", "literal_rows",
               "exclusions", "test", "ci", "trial_accounting", "receipt"]

ANALYSIS_SET_ROLLING = ("PRIMARY = SENS-A = SENS-B (no event bundling for "
                        "rolling anchors, IL §4); split={split}")


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


def render_report_md(lane: dict, protocols: dict) -> str:
    """Human-readable twin of results/<Pxx>.json, same per-block order."""
    lines: list[str] = []
    for lab in lane["labels"]:
        lines.append(f"> {lab}")
    lines.append("")
    lines.append(f"# {lane['title']}")
    lines.append("")
    lines.append(f"BASE: {lane['base']}  ")
    lines.append(f"branch: {lane['branch']}  ")
    lines.append(f"seal: research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json "
                 f"(prereg digest {lane['prereg_digest_sha256']})  ")
    lines.append(f"prior looks: none for v1  ")
    lines.append("")
    for pid in sorted(protocols):
        p = protocols[pid]
        lines.append(f"## {pid} — {p['family']}")
        lines.append("")
        for key in p["block_order"]:
            b = p["blocks"][key]
            lines.append(f"### {key}")
            lines.append("")
            lines.append(f"1. null: {b['null']}")
            lines.append(f"2. analysis_set: {b['analysis_set']}")
            lines.append(f"3. honest_n: {b['honest_n']}")
            lines.append(f"4. cluster_n: {b['cluster_n']}")
            lines.append(f"5. literal_rows: {b['literal_rows']}")
            lines.append(f"6. exclusions: {b['exclusions']}")
            lines.append(f"7. test: {b['test']}")
            lines.append(f"8. ci: {b['ci']}")
            lines.append(f"9. trial_accounting: {b['trial_accounting']}")
            lines.append(f"10. receipt: {b['receipt']}")
            lines.append("")
    return "\n".join(lines) + "\n"
