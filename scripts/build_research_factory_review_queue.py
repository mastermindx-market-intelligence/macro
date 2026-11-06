"""scripts/build_research_factory_review_queue.py — W5 queue builder CLI.

Emits:
  data/research_factory/review/queue.json   — machine-readable packet list
  data/research_factory/review/queue.md     — human-readable, one section per
                                              candidate, decision block template
                                              at the end of each section

Display-only wording throughout. Never emits the word 'validated' in any text.

Forward-ledger law (RF-8):
  Default: --dry-run (print without writing).
  Use --write to emit to disk.

Charter: research/RESEARCH_FACTORY_MASTERPLAN_BY_FABLE.md §6 W5,
rulings RF-5, RF-9, RF-12, RF-16.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.research_factory.review_queue import build_queue, DEFAULT_RF_DIR

# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

_DECISION_BLOCK_TEMPLATE = """\
### Decision block

**Candidate:** `{candidate_id}`
**Allowed decisions:** paper | deferred | rejected | scoped_build

**Decision question:**
> {decision_question}

**To record a decision, run:**
```
python scripts/research_factory_decide.py \\
  --candidate {candidate_id} \\
  --decision <paper|deferred|rejected|scoped_build> \\
  --actor <fable|operator> \\
  --actor-ref <session/PR ref> \\
  [--expected-half-life-d <N>]        # required for paper \\
  [--come-back-on YYYY-MM-DD]         # required for deferred \\
  [--kill-class <class>]              # required for rejected/retired \\
  [--program-doc research/<NAME>_BY_FABLE.md]  # required for scoped_build
```
"""


def _render_metric_line(k: str, v: object) -> str:
    if isinstance(v, float):
        return f"  - **{k}**: {v:.4f}"
    return f"  - **{k}**: {v}"


def _render_blocker(b: dict) -> str:
    sev = b.get("severity", "?")
    cat = b.get("category", "?")
    finding = b.get("finding", "")
    return f"  - [{sev}/{cat}] {finding}"


def render_markdown(packets: list[dict], generated_at: str, *,
                    private_source_references=None, source_repository=None) -> str:
    """Render the full queue.md document.

    Sections:
      1. Active Queue — human_review and paper-decay candidates (decidable or near-decidable)
      2. Blocked — awaiting_data candidates (blocked on data/label/grader availability)
    """
    if private_source_references is not None:
        if type(private_source_references) is not list or type(packets) is not list:
            raise ValueError("PRIVATE_SOURCE_REFERENCE_REFUSED")
        if len(private_source_references) != len(packets):
            raise ValueError("PRIVATE_SOURCE_REFERENCE_REFUSED")
        if not all(type(packet) is dict and packet.get("is_research_diagnostic") is True
                   for packet in packets):
            raise ValueError("PRIVATE_SOURCE_REFERENCE_REFUSED")
    elif source_repository is not None:
        raise ValueError("PRIVATE_SOURCE_REFERENCE_REQUIRED")
    # Split packets into active and blocked
    active_packets = [p for p in packets if not p.get("is_awaiting_data") and not p.get("is_research_diagnostic")]
    blocked_packets = [p for p in packets if p.get("is_awaiting_data")]
    diagnostic_packets = [p for p in packets if p.get("is_research_diagnostic")]

    lines: list[str] = []
    lines.append("# Research Factory — Human Review Queue")
    lines.append("")
    lines.append(f"*Generated: {generated_at}*")
    lines.append(f"*Candidates awaiting decision: {len(active_packets)}*")
    lines.append(f"*Blocked (awaiting_data): {len(blocked_packets)}*")
    lines.append("")
    lines.append(
        "> **Display-only context.** All metrics are aggregate, frozen-gate outputs "
        "from the domain evaluator. This queue provides context for the human decision "
        "only; it does not score, rank by merit, or originate any signal."
    )
    lines.append("")

    if not packets:
        lines.append("*No candidates currently in human_review, flagged for decay review, or blocked.*")
        lines.append("")
        return "\n".join(lines)

    # ---- Active Queue section ----
    lines.append("## Active Queue")
    lines.append("")
    if not active_packets:
        lines.append("*No candidates currently in human_review or flagged for decay review.*")
        lines.append("")
    else:
        for i, pkt in enumerate(active_packets, 1):
            _render_packet(lines, i, pkt)

    # ---- Blocked section ----
    lines.append("---")
    lines.append("")
    lines.append("## Blocked")
    lines.append("")
    lines.append(
        "> **Blocked candidates** are in `awaiting_data` state — blocked on data, label, or "
        "grader availability. No decide command is runnable. Each entry shows its "
        "`come_back_on` clock."
    )
    lines.append("")
    if not blocked_packets:
        lines.append("*No candidates currently blocked.*")
        lines.append("")
    else:
        for i, pkt in enumerate(blocked_packets, 1):
            _render_blocked_packet(lines, i, pkt)

    if diagnostic_packets:
        lines.extend(["", "## Synthetic research diagnostics", ""])
        for i, pkt in enumerate(diagnostic_packets, 1):
            if private_source_references is None:
                _render_packet(lines, i, pkt)
            else:
                _render_packet(lines, i, pkt, private_source_reference=private_source_references[i - 1],
                               source_repository=source_repository)
    return "\n".join(lines)


def _render_packet(lines: list[str], i: int, pkt: dict, *, private_source_reference=None,
                   source_repository=None) -> None:
    """Render one active-queue packet into lines (mutates lines in place)."""
    if private_source_reference is not None:
        # Direct helper calls must pass through the same checks as render_markdown.
        from engine.research_factory.review_queue import diagnostic_review_packet
        if type(pkt) is not dict or pkt.get("is_research_diagnostic") is not True or pkt.get("allowed_decisions") != []:
            raise ValueError("PRIVATE_SOURCE_REFERENCE_REFUSED")
        attached = pkt.get("engineering_evidence", {})
        keys = ("schema", "identity", "accounting", "attempts", "controls")
        if type(attached) is not dict or set(attached) != set(keys) | {"authority", "scope", "physical_acceptance", "scientific_acceptance"}:
            raise ValueError("PRIVATE_SOURCE_REFERENCE_REFUSED")
        checked = diagnostic_review_packet(pkt["diagnostic"],
            engineering_evidence={key: attached[key] for key in keys},
            private_source_reference=private_source_reference, source_repository=source_repository)
        if (pkt.get("private_source_context") != checked["private_source_context"]
                or attached != checked["engineering_evidence"]
                or any(pkt.get(key) != checked[key] for key in ("diagnostic_id", "candidate_id",
                    "created_at", "authority", "current_status", "candidate_type", "domain", "frozen_gate_metrics"))):
            raise ValueError("PRIVATE_SOURCE_REFERENCE_REFUSED")
        pkt = checked
    elif source_repository is not None:
        raise ValueError("PRIVATE_SOURCE_REFERENCE_REQUIRED")
    if pkt.get("is_research_diagnostic"):
        # These are owner-bound attachments, never decide.py candidates.
        from engine.research_codegen.bridge import PUBLIC_AGGREGATE_KEYS
        lines.extend([f"### {i}. {pkt['diagnostic_id']}", "", pkt["note"], ""])
        metrics = pkt["frozen_gate_metrics"]
        lines.extend(_render_metric_line(k, metrics[k]) for k in PUBLIC_AGGREGATE_KEYS)
        if "engineering_evidence" in pkt:
            # Recompile before rendering caller-owned packet data. The exact
            # compiled shape rejects extra fields and altered authority flags.
            from engine.research_factory.review_queue import diagnostic_review_packet
            attached = pkt["engineering_evidence"]
            keys = ("schema", "identity", "accounting", "attempts", "controls")
            flags = {"authority": "display_only", "scope": "SYNTHETIC_ENGINEERING_ONLY",
                     "physical_acceptance": False, "scientific_acceptance": "UNQUALIFIED"}
            if (type(attached) is not dict or len(attached) != len(keys) + len(flags)
                    or not all(type(key) is str for key in attached)
                    or set(attached) != set(keys) | set(flags)
                    or any(type(attached[key]) is not type(value) or attached[key] != value
                           for key, value in flags.items())):
                raise ValueError("INVALID_DIAGNOSTIC_ENGINEERING_EVIDENCE")
            checked = diagnostic_review_packet(pkt["diagnostic"],
                engineering_evidence={key: attached[key] for key in keys})["engineering_evidence"]
            lines.extend(["", "**Engineering controls — synthetic receipts only**", "",
                          "| Control | Observation | Evidence SHA-256 |",
                          "| --- | --- | --- |"])
            for control in checked["controls"]:
                evidence = control["evidence_sha256"] or "none"
                lines.append(f"| {control['id']} | {control['status']} | {evidence} |")
            lines.extend(["", f"Retained attempts: {len(checked['attempts'])}.",
                          "Physical acceptance: unqualified. Scientific acceptance: unqualified."])
        if private_source_reference is not None:
            context = pkt["private_source_context"]
            lines.extend(["", "**PRIVATE local source inspection — advisory only**",
                f"Verified source: {context['source_link']}",
                f"Source bytes: {context['source_bytes']}",
                "Economic mechanism: UNAVAILABLE", "Parent diff: UNAVAILABLE",
                "Local Git bytes match; no candidate execution or scientific acceptance."])
            lines.extend(f"- {key}: {value}" for key, value in context["binding"].items())
        lines.append("")
        return
    cid = pkt.get("candidate_id", "?")
    ctype = pkt.get("candidate_type", "?")
    domain = pkt.get("domain", "?")
    status = pkt.get("current_status", "?")
    source = pkt.get("source", "?")
    track = pkt.get("track") or "—"

    lines.append(f"---")
    lines.append("")
    lines.append(f"## {i}. {cid}")
    lines.append("")
    lines.append(f"**Type:** {ctype} | **Domain:** {domain} | "
                 f"**Status:** {status} | **Source:** {source} | **Track:** {track}")
    lines.append("")

    # Hypothesis + mechanism
    hyp = pkt.get("hypothesis") or "—"
    mech = pkt.get("mechanism") or "—"
    lines.append("### Hypothesis")
    lines.append(f"> {hyp}")
    lines.append("")
    lines.append("### Mechanism")
    lines.append(f"> {mech}")
    lines.append("")

    # Frozen-gate metrics
    metrics = pkt.get("frozen_gate_metrics") or {}
    if metrics:
        lines.append("### Frozen-gate metrics (display only)")
        for k, v in metrics.items():
            lines.append(_render_metric_line(k, v))
        lines.append("")

    # search_width_at_scan (oracle only — REQUIRED)
    sw = pkt.get("search_width_at_scan")
    if sw is not None:
        if sw == "MISSING":
            lines.append("### Search width at scan")
            lines.append("**WARNING: search_width_at_scan is MISSING — "
                          "required for oracle candidates (charter §6 W3/W5)**")
            lines.append("")
        else:
            lines.append("### Search width at scan")
            lines.append(f"  {sw}")
            lines.append("")

    # Probe flags
    flags = pkt.get("probe_flags") or {}
    if flags:
        lines.append("### Mechanical probe flags")
        for k, v in flags.items():
            lines.append(f"  - **{k}**: {v}")
        lines.append("")

    # Reviewer blockers
    blockers = pkt.get("reviewer_blockers") or []
    if blockers:
        lines.append("### Reviewer blockers (advisory only)")
        for b in blockers:
            lines.append(_render_blocker(b))
        lines.append("")

    # Best counterargument
    bca = pkt.get("best_counterargument")
    if bca:
        lines.append("### Best counterargument (advisory)")
        lines.append(f"> {bca}")
        lines.append("")

    # Crowding context (RF-16 — context only, no composite)
    crowds = pkt.get("crowds_with") or []
    if crowds:
        lines.append("### Crowding context (display only — not a rank)")
        lines.append(
            "*Other non-terminal candidates sharing entry-rule column overlap "
            "or same alpha cluster. Context only; RF-16 forbids composite ranking.*"
        )
        for c in crowds:
            other_id = c.get("candidate_id", "?")
            other_status = c.get("status", "?")
            overlap = c.get("overlap_columns") or []
            cluster_match = c.get("same_alpha_cluster", False)
            overlap_str = ", ".join(overlap) if overlap else "—"
            cluster_str = " (same alpha cluster)" if cluster_match else ""
            lines.append(
                f"  - `{other_id}` (status={other_status}) "
                f"overlap_cols=[{overlap_str}]{cluster_str}"
            )
        lines.append("")

    # Human review question
    hrq = pkt.get("human_review_question")
    if hrq:
        lines.append("### Human review question")
        lines.append(f"> {hrq}")
        lines.append("")

    # Decision block template
    dec_q = pkt.get("decision_question") or "See human_review_question above."
    lines.append(
        _DECISION_BLOCK_TEMPLATE.format(
            candidate_id=cid,
            decision_question=dec_q,
        )
    )
    lines.append("")


def _render_blocked_packet(lines: list[str], i: int, pkt: dict) -> None:
    """Render one blocked (awaiting_data) packet into lines (mutates lines in place)."""
    cid = pkt.get("candidate_id", "?")
    ctype = pkt.get("candidate_type", "?")
    domain = pkt.get("domain", "?")
    source = pkt.get("source", "?")
    come_back_on = pkt.get("come_back_on") or "not set"

    lines.append(f"---")
    lines.append("")
    lines.append(f"### B{i}. {cid}")
    lines.append("")
    lines.append(
        f"**Type:** {ctype} | **Domain:** {domain} | **Source:** {source} | "
        f"**Status:** awaiting_data | **come_back_on:** {come_back_on}"
    )
    lines.append("")

    hyp = pkt.get("hypothesis") or "—"
    mech = pkt.get("mechanism") or "—"
    lines.append("#### Hypothesis")
    lines.append(f"> {hyp}")
    lines.append("")
    lines.append("#### Mechanism")
    lines.append(f"> {mech}")
    lines.append("")

    note = pkt.get("note") or ""
    lines.append(f"*{note}*")
    lines.append("")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--rf-dir", type=Path, default=None,
        help="Override data/research_factory/ dir (default: data/research_factory/)",
    )
    ap.add_argument(
        "--write", action="store_true", default=False,
        help="Write queue.json + queue.md to disk (default: dry-run only)",
    )
    ap.add_argument(
        "--dry-run", action="store_true", default=False,
        help="Print summary without writing (default behaviour; explicit flag for clarity)",
    )
    ap.add_argument("--retain-diagnostics", action="store_true", help="Preserve the existing compiled display projection when publishing a refreshed queue.")
    ap.add_argument("--retire-diagnostics", action="store_true", help="Explicitly retire the existing compiled diagnostic projection.")
    ap.add_argument("--private-source-review", action="store_true", help="PRIVATE stdout-only immutable-source inspection; never publishes.")
    ap.add_argument("--private-packets", type=Path)
    ap.add_argument("--private-source-links", type=Path)
    ap.add_argument("--source-repository", type=Path)
    return ap


def _private_source_review(args):
    """Retained packets only; never reaches build_queue or the normal publisher."""
    import hashlib
    from engine.research_codegen.bridge import _pairs
    def _nonfinite(_):
        raise ValueError("PRIVATE_NONFINITE_INPUT")
    from engine.research_factory.review_queue import diagnostic_review_packet
    def read(path):
        with path.open("rb") as stream:
            raw = stream.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise ValueError("PRIVATE_INPUT_LIMIT")
        return raw
    raw = read(args.private_packets)
    packets = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_nonfinite)
    links = json.loads(read(args.private_source_links).decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_nonfinite)
    import re
    if (type(links) is not dict or set(links) != {"scope", "source_commit", "packet_sha256", "rows",
                "swapped_source_matches", "declared_economic_mechanism", "parent_diff", "candidate_execution"}
            or type(links.get("source_commit")) is not str
            or re.fullmatch(r"[0-9a-f]{40}", links["source_commit"]) is None
            or type(links.get("swapped_source_matches")) is not int or links["swapped_source_matches"] != 0
            or links.get("scope") != "Private local inspection of retained engineering controls"
            or links.get("packet_sha256") != hashlib.sha256(raw).hexdigest()
            or links.get("declared_economic_mechanism") != "UNAVAILABLE"
            or links.get("parent_diff") != "UNAVAILABLE" or links.get("candidate_execution") is not False
            or type(packets) is not list or not 0 < len(packets) <= 256
            or type(links.get("rows")) is not list or len(links["rows"]) != len(packets)):
        raise ValueError("PRIVATE_PACKET_BINDING_REFUSED")
    verified, refs = [], []
    seen = set()
    for packet, reference in zip(packets, links["rows"]):
        if (type(packet) is not dict or type(reference) is not dict
                or type(reference.get("source_link")) is not str
                or not reference["source_link"].startswith("https://github.com/mastermindx-market-intelligence/macro/blob/" + links["source_commit"] + "/")):
            raise ValueError("PRIVATE_PACKET_BINDING_REFUSED")
        if (packet.get("allowed_decisions") != [] or packet.get("is_research_diagnostic") is not True
                or packet.get("diagnostic_id") in seen):
            raise ValueError("PRIVATE_PACKET_BINDING_REFUSED")
        seen.add(packet["diagnostic_id"])
        evidence = packet["engineering_evidence"]
        keys = ("schema", "identity", "accounting", "attempts", "controls")
        checked = diagnostic_review_packet(packet["diagnostic"],
            engineering_evidence={key: evidence[key] for key in keys},
            private_source_reference=reference, source_repository=args.source_repository)
        # Original packets can have a receipt-composition note; render only the rebuilt packet.
        if (evidence != checked["engineering_evidence"]
                or any(packet.get(key) != checked[key] for key in ("diagnostic_id", "candidate_id",
                    "created_at", "authority", "current_status", "candidate_type", "domain", "frozen_gate_metrics"))):
            raise ValueError("PRIVATE_PACKET_BINDING_REFUSED")
        verified.append(checked); refs.append(reference)
    text = render_markdown(verified, "PRIVATE local inspection", private_source_references=refs,
                           source_repository=args.source_repository)
    print(text)
    return 0


def main(*, trusted_codegen_artifacts: tuple = (), synthetic_commission=None) -> int:
    ap = _build_parser()
    args = ap.parse_args()
    if args.private_source_review:
        if args.write or args.retain_diagnostics or args.retire_diagnostics or args.rf_dir is not None:
            ap.error("PRIVATE source review is stdout-only; publishing options refused")
        if not all((args.private_packets, args.private_source_links, args.source_repository)):
            ap.error("PRIVATE source review needs packets, source links, and local source repository")
        try:
            return _private_source_review(args)
        except (OSError, ValueError, KeyError, TypeError, RecursionError):
            print("PRIVATE source review refused: source or packet binding could not be verified.", file=sys.stderr)
            return 2
    if any((args.private_packets, args.private_source_links, args.source_repository)):
        ap.error("private inputs require --private-source-review")
    dry_run = not args.write

    rf_dir = args.rf_dir or DEFAULT_RF_DIR

    packets = build_queue(rf_dir=rf_dir, trusted_codegen_artifacts=trusted_codegen_artifacts,
                          synthetic_commission=synthetic_commission)

    generated_at = datetime.now(timezone.utc).isoformat()

    active_packets = [p for p in packets if not p.get("is_awaiting_data") and not p.get("is_research_diagnostic")]
    blocked_packets = [p for p in packets if p.get("is_awaiting_data")]
    diagnostic_rows = [p["diagnostic"] for p in packets if p.get("is_research_diagnostic")]
    diagnostic_state = "AVAILABLE" if diagnostic_rows else "DISABLED"
    if args.retain_diagnostics and args.retire_diagnostics:
        ap.error("choose one diagnostic retention disposition")
    if args.write and not trusted_codegen_artifacts:
        prior = rf_dir / "review" / "queue.json"
        if prior.exists():
            from engine.research_codegen.bridge import MAX_ARTIFACT_BYTES, decode_published_diagnostics
            try:
                with prior.open("rb") as stream:
                    retained, prior_state = decode_published_diagnostics(stream.read(MAX_ARTIFACT_BYTES + 1))
            except (OSError, ValueError):
                print("Existing queue cannot be qualified; publication refused.")
                return 2
            if retained or prior_state == "UNAVAILABLE":
                if not args.retain_diagnostics and not args.retire_diagnostics:
                    print("Existing diagnostic publication needs --retain-diagnostics or --retire-diagnostics.")
                    return 2
                if args.retain_diagnostics:
                    diagnostic_rows, diagnostic_state = list(retained), prior_state
                    from engine.research_factory.review_queue import diagnostic_review_packet
                    packets.extend(diagnostic_review_packet(row) for row in sorted(retained, key=lambda r: (r["created_at"], r["diagnostic_id"])))

    # Build JSON payload
    queue_json: dict = {
        "schema": "research_factory.review_queue.v1",
        "authority": "display_only",
        "generated_at": generated_at,
        "n_candidates": len(active_packets),
        "n_research_diagnostics": len(diagnostic_rows),
        "research_diagnostics": diagnostic_rows,
        "research_diagnostics_state": diagnostic_state,
        "n_blocked": len(blocked_packets),
        "candidates": packets,
        "note": (
            "Cross-domain review queue. Active = human_review + paper-decay; "
            "Blocked = awaiting_data (blocked on data/label/grader). "
            "Ordered by candidate_type bin then created_at. "
            "RF-16: crowds_with is context only — no composite ranking. "
            "All metrics are display-only."
        ),
    }

    # Build Markdown
    queue_md = render_markdown(packets, generated_at)

    # Print summary
    print(f"Review queue: {len(active_packets)} active, {len(blocked_packets)} blocked")
    for p in active_packets:
        sw = p.get("search_width_at_scan")
        sw_str = f" [search_width={sw}]" if sw is not None else ""
        print(
            f"  [active] {p.get('candidate_id','?')} "
            f"({p.get('candidate_type','?')}/{p.get('domain','?')}, "
            f"status={p.get('current_status','?')})"
            f"{sw_str}"
        )
    for p in blocked_packets:
        cbo = p.get("come_back_on") or "not set"
        print(
            f"  [blocked] {p.get('candidate_id','?')} "
            f"({p.get('candidate_type','?')}/{p.get('domain','?')}) "
            f"come_back_on={cbo}"
        )

    if dry_run:
        print(f"\n[DRY-RUN] Generated {len(active_packets)} active + "
              f"{len(blocked_packets)} blocked packet(s). Use --write to emit to disk.")
        return 0

    # Write outputs
    review_dir = rf_dir / "review"
    review_dir.mkdir(parents=True, exist_ok=True)

    json_path = review_dir / "queue.json"
    md_path = review_dir / "queue.md"

    json_path.write_text(
        json.dumps(queue_json, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    md_path.write_text(queue_md, encoding="utf-8")

    print(f"\nWrote: {json_path}")
    print(f"Wrote: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
