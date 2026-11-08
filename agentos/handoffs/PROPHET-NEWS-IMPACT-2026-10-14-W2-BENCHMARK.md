---
workstream: "WS:PROPHET-NEWS-IMPACT"
session: "claude/ssd-prophet-ni-w2-results-487c8342859554a9"
model: opus
ended_because: ci_handoff
decisions: ["DEC:NEWS-IMPACT-W2-BENCHMARK-SCORING", "DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE"]
discoveries: ["DSC:NEWS-IMPACT-T1-PER-SHARE-DIVIDEND-CONTRACT-GAP", "DSC:NEWS-IMPACT-TWO-FAMILY-AGREEMENT-PREDICTS-CORRECTNESS", "DSC:NEWS-IMPACT-MINIMAX-NO-USAGE-RECEIPTS"]
prs: [9290]
mission: >
  Wave w2 of the Prophet news-to-business-impact masterplan (commission D): label the drawn
  benchmark with inexpensive model families, add a small stronger-model audit, and return the
  error taxonomy, recall against cost, actual token cost, calibration and burst/defer behavior.
  Labor ran on seat-launched external lanes (ext/remote_sub.sh); no native Claude children.
state_before: >
  PR #9290 (squash c0a9d097) had landed the tape draw, the EDGAR body frame and the frozen
  draws: 157 body-available cases out of the 600 the masterplan asks for, short cells printed.
  No case had been labeled or scored.
changed:
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/summary.json
    what: >
      Scored results for 157 cases and 293 critical slots: slot taxonomy, agreement with Wilson
      intervals, the audit block, observed fam_b token cost, recall against cost, calibration by
      proxy cell, burst/defer, span replay, and case status (all 157 routed_pending_third).
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/critical_slots.jsonl
    what: One row per critical slot with both families' normalised values and the class; no filing text.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/eval_receipt_fam_a.json
    what: eval_receipt for fam_a (MiniMax-M3) with cost null and reason USAGE_RECEIPT_MISSING.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/eval_receipt_fam_b.json
    what: eval_receipt for fam_b (qwen3.7-plus) with observed codex_native_session token counts.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/sample.json
    what: The 40-slot audit sample (20 agree_present, 10 present_value_differs, 10 present_vs_absent), seed 20261014.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/audit.json
    what: The seat's 40 audit verdicts; two why strings paraphrased so no filing text is stored.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/
    what: >
      The scorer, the canon pass (C1-C4), the audit sampler, the span filler, the label checker,
      the lane builder and both lane prompts (v1.0 and v1.1). Every committed output reproduces
      from these tools.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/README.md
    what: How the wave ran, what each file holds, the prompt-version split and the honest limits.
  - path: agentos/decisions/DEC-NEWS-IMPACT-W2-BENCHMARK-SCORING.md
    what: Seat ruling on gold, slot unit, canon, Q1, evidence, spans, audit verdicts, lanes and prompt versions.
  - path: agentos/discoveries/DSC-NEWS-IMPACT-T1-PER-SHARE-DIVIDEND-CONTRACT-GAP.md
    what: The frozen contract cannot encode a per-share dividend in T1; the guide leaves "increase up to $X" open.
  - path: agentos/discoveries/DSC-NEWS-IMPACT-TWO-FAMILY-AGREEMENT-PREDICTS-CORRECTNESS.md
    what: Agreed present values were right in every decided audit slot; disputed values were mostly wrong on both sides.
  - path: agentos/discoveries/DSC-NEWS-IMPACT-MINIMAX-NO-USAGE-RECEIPTS.md
    what: The MiniMax lane mode writes no usage receipt, so fam_a cost is unmeasured.
  - path: agentos/workstreams/WS-PROPHET-NEWS-IMPACT.md
    what: Wave w2 next_action and the top-level next_action now point at the third family, the contract-gap ruling and the 600-case continuation.
verified:
  - claim: The committed outputs reproduce from the committed tools.
    command: PYTHONPATH=. python3 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/score_benchmark.py (with the canon returns and the committed audit.json), then cmp against the committed files
    result: summary.json, critical_slots.jsonl and both eval receipts byte-identical.
  - claim: The audit sample reproduces from its seed.
    command: PYTHONPATH=. python3 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/build_audit.py with seed 20261014
    result: audit/sample.json sha256 868ce66e2b8877a7ad38f3c1d9a592a32b1e46ea29d48176347f0f12bd9e72b9.
  - claim: The committed results carry no filing text.
    command: grep -rnE "aggregate principal amount|share repurchase authorization|narrowing our revenue forecast|Consideration Shares" results_w2/; grep -rn "«" results_w2/
    result: no phrase match; the only guillemet is the card formatter in tools/build_audit.py.
  - claim: Agent OS records are schema-valid.
    command: python3 scripts/agentos.py validate
    result: exit 0 (0 errors).
  - claim: PR #9290 merged and landed.
    command: git log origin/main --oneline --grep="#9290"
    result: c0a9d097 feat(prophet) news-impact W2 benchmark is on origin/main.
unverified:
  - claim: The CI run on this results pull request.
    what_would_verify: gh pr checks concluding green, then a per-path blob comparison against a freshly fetched origin/main after the squash.
  - claim: The two-family agreement result holds for agreed absences.
    what_would_verify: An audit of agree_absent slots (129 in w2), which this wave did not sample.
unresolved:
  - "157 of 600 cases were drawn (body available). The 443-case shortfall is printed, never padded; the continuation needs more tape and more 8-K bodies."
  - "No case can pass the case gate with two families. All 157 cases are routed_pending_third until a third family labels the disputed slots."
  - "T1 per-share dividends have no lawful encoding in the frozen contract (DSC:NEWS-IMPACT-T1-PER-SHARE-DIVIDEND-CONTRACT-GAP). A contract or guide change needs an owner ruling; the contract stays frozen until then."
  - "fam_a (MiniMax-M3) cost is null because its lane mode wrote no usage receipt."
next_actions:
  - Merge this results PR on concluded green with gh pr merge --squash --match-head-commit, then verify landing per path against a freshly fetched origin/main.
  - "Third family: label the disputed slots (42% of critical slots) with GLM once its quota resets after 2026-10-19 05:16Z, using tools/build_label_lanes.py with LABEL_TEMPLATE=tools/label_batch.template.v1.1.txt."
  - Get an owner ruling on the T1 per-share dividend gap and the "increase up to $X" guide gap before the 600-case continuation.
  - Add a usage capture to the MiniMax lane mode, or join a provider usage export, before the next labeling wave.
  - Audit a sample of agree_absent slots.
  - After w2 closes, wave 3 wires the measured packet producer to the event ledger, context_only, behind the benchmark gate.
do_not_redo:
  - The 157-case two-family labeling (fam_a lanes 01, 02r, 03-10; fam_b lanes 01-10) is ACCEPTED; do not relabel it. Add a third family on top.
  - The 40-slot audit (seed 20261014) is ACCEPTED; extend it with new strata, never redraw it.
  - fam_c (cursor) refused on economic policy in all 10 lanes. Do not retry it through another tool, account or model.
  - DEC:NEWS-IMPACT-W2-BENCHMARK-SCORING settles the scoring rules; do not report per-family accuracy against agreed labels.
danger_areas:
  - "Label returns, 8-K bodies and the audit card batches exist only in the seat's /private/tmp scratch and are lost when it is cleaned. The committed tools and outputs reproduce the scores but not the raw returns."
  - "The audit card batches (batch_*.txt) quote filing text. Never commit them (DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE)."
  - "GLM is exhausted until 2026-10-19 05:16Z; Grok and Codex are exhausted; cursor refuses this task. MiniMax and qwen are the only live labeler families."
  - The frozen news_impact_event.v1 contract (sha256 prefix 3edc7139) and the A4 case JSON files are byte-frozen.
  - PRs #6514, #8697 and #8698 belong to other owners; never touch them.
---

# PROPHET-NEWS-IMPACT handoff 2026-10-14 (w2 benchmark results)

Two inexpensive families labeled the 157 drawn cases. Their slots agree 57.7% of the time
(Wilson 95% 0.520-0.632) and dispute 42.3%. A 40-slot audit by the seat found agreed present
values right in every decided slot, while most disputed values were wrong on both sides. No
case can pass the gate without a third family, so all 157 wait for one. fam_b used about 300k
tokens per case, mostly cached input; fam_a's cost is unmeasured. Three of the twenty disputed
audit slots are contract gaps (T1 per-share dividends), which need an owner ruling.
