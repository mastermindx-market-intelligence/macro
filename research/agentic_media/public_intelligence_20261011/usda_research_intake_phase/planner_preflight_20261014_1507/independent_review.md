STATUS: COMPLETE

**Verdict**
- NOT PASS. One narrow Research-only prompt correction is warranted. Brief and admitted earnings are unaffected by construction (see placement rationale).

**Grounding**
- The inline context is byte-faithful to `build_prompt` at accepted application `8eb4671` (`engine/press/writer.py:409`, `engine/press/writer.py:528`, `engine/press/writer.py:545`).
- Provenance flag for parent: installed tip `918fad1` exists in `lanes/repos/macro` but its `engine/press/writer.py` is the older variant — no VINTAGE LAW, and it emits `MINIMUM RECEIPTS: N distinct numbers drawn from SOURCE FACTS` (no `[first_party]`). `git merge-base --is-ancestor 8eb4671 918fad1` = NO. The selected slot was built from the application revision, not from `918fad1`'s writer. Not a re-run request; just confirm which revision the slot is stamped against.

**F1 — False Attribution (contract asserts our authorship of USDA figures)**
- Passage: "PRIMARY SOURCE — FIRST PARTY. This is our own measurement, so there is nothing to cite outward. Name the desk in words and carry the receipts inline…" + "desk: Mastermind Research: World Agricultural Supply and Demand Estimates, October 2026 (WASDE 676)".
- Six SOURCE FACTS are USDA projections ("USDA projects U.S. wheat ending stocks of 740 million bushels…"), tiered `[first_party]` because the tier covers our *coverage* (`engine/press/desk_planner.py:1341`, `engine/press/desk_planner.py:1345`). The prompt then states the opposite of that: "our own measurement", and disables the only outward-attribution channel (the EXTERNAL branch's "Name it IN FULL … and link this exact URL").
- Reinforcing passage: "Restating someone else's report is not coverage; our read of it, with our numbers, is." For this story "our numbers" resolves to USDA's, since those are the only numbers that can satisfy the floor and the 40% share.
- No deterministic backstop: `check_primary_source` returns pass unconditionally for first-party slots (`engine/press/validators.py:1094`), so "our corn ending stocks read 1.8 billion bushels" clears every gate.
- Mitigants that keep this from being certain failure: fact text carries "USDA projects/forecasts" and "(source: Mastermind Research coverage of U.S. Department of Agriculture)"; THE STORY carries `"institution": "U.S. Department of Agriculture"`, `"side": "independent"`; one fact states these "are not current spot prices or company earnings forecasts". Correct attribution is *available* in the data and *contradicted* by the contract.

**F2 — Unsupported Cross-Market Reasoning (agreement verdict is mandated, not optional)**
- Passages: "…then say what our own measurements make of it — where they agree, where they do not, and what would settle it." and "SHAPE: what the desk argued / what our data says / what would change the picture." (`engine/press/writer.py:412`, `engine/press/writer.py:418`).
- "Our own measurements" here are topic-blind engine telemetry injected by `engine_stat_facts` (`engine/press/desk_planner.py:1259` → `engine/press/desk_planner.py:1310`): market-state 50 of 100 MIXED plus four components, six index dealer-gamma lines, fear/greed 52, risk radar 73.9 / 0.19 (all 2026-10-13), and AI-vs-non-AI breadth 62.3% / 27.0% / 35.3 points (2026-10-08). None measures wheat, corn or soybean balances; `"tickers": []`.
- They arrive as SOURCE FACTS, not MARKET CONTEXT (that block is empty; only "context coverage: no events in window 2026-09-30..2026-10-14" prints), so the model reads them as usable receipts while SHAPE makes a verdict a required section.
- The existing guard does not reach this case: "Broad pre-event context cannot establish an issuer's reaction, exposure or causality. Do not pad unrelated measurements into a story to meet the receipt floor." It is keyed to *pre-event* context and an *issuer* — these facts are post-publication (Oct 13 > Oct 9) and there is no issuer; and the padding clause is a motive test tied to the floor, which the six USDA facts already satisfy alone. Nothing licenses "our indicators do not speak to this report."

**F3 — Minor, Same Root**
- "what the desk argued" is ambiguous inside a contract opening "YOU ARE: the Research Desk of Mastermind Research"; "the desk" reads as ours when the arguer is USDA. Fixed by the same clause at no extra cost.

**Adequate — Leave Unchanged**
- VINTAGE LAW satisfies constraint (5): "Attach every number to its own vintage in the prose…" and "A fact tagged (dated … after the RUN DATE above) must not be described as current or latest." Oct 9 forecast, Oct 13 telemetry and Oct 8 breadth are separately dated in every fact line.
- Receipt, similarity, word-count, cadence and release gates need no movement; the correction is prompt prose only.

**Smallest Warranted Correction (one, Research-only)**
- Placement: append to the Research contract string inside `if desk in ("research_desk", "research_note"):` (`engine/press/writer.py:409`). The FIRST PARTY line at `engine/press/writer.py:528` is shared by every desk, so editing it would change Brief and admitted earnings — which carry `"desk": "brief"` (`engine/press/earnings_adapter.py:207`) and take the else branch. The Research branch is desk-gated, and appending keeps both pinned strings green ("PRIMARY SOURCE — FIRST PARTY" at `tests/test_press_writer.py:49`; "Research Desk of Mastermind Research" at `tests/test_press_research_triage.py:1145`).
- Text: "ATTRIBUTION AND SCOPE OF OUR DATA: [first_party] is our RECEIPT tier for our own coverage of a report — it is never a claim that we produced the underlying figures. Where a SOURCE FACT names an institution, those numbers are that institution's estimates and projections: attribute them to it by name, in their own vintage, and never as Mastermind measurements. 'What our data says' covers only measurements of the same thing the report measures. Where we have none — broad equity, dealer-positioning, breadth or sentiment readings against a crop supply-and-demand balance — say so plainly, date those readings as their own, and assert no agreement, disagreement, confirmation, contradiction, exposure or causation. An empty ticker list means no issuer: do not infer one."
- Gate-safety: the floor of 4 distinct `[first_party]` numbers and the 40% share are satisfiable from USDA-coverage facts alone (740, 16.0, 1.8, 4.56, 315, $12.00, 181.2, 53.1), so declining the cross-market verdict creates no floor conflict. The clause contains no term from the rendered banned lexicons (checked against the phrase, word and pattern lists, including "the backdrop" and "positioning in").

**Suggested Test Cases**
1. Research slot with a named-institution report: assert the new clause is in the system prompt and the FIRST PARTY block is byte-identical to pre-change.
2. Desk isolation: same story as `desk="brief"`, plus an `earnings_adapter` slot (`desk="brief"`, `approved_claim_ids` set) — assert the clause is absent from both and CLAIM SCOPE text is unchanged.
3. Attribution lexicon (offline fixture, no provider): "our wheat ending stocks read 740 million bushels" / "we project" / "our forecast" on a USDA-institution slot must be flagged — currently waved through at `engine/press/validators.py:1094`. Recommend as follow-up validator, explicitly outside this prompt-only correction so gates stay unchanged.
4. Cross-market verdict: "the 50 of 100 composite confirms USDA's corn build" (and its "contradicts" twin) must fail; "our equity indicators do not measure crop balances; on 2026-10-13 the composite read 50 of 100" must pass.
5. Gate regression: an all-USDA-anchored draft with 4 distinct first-party numbers and zero equity numbers still passes `check_our_value` and `check_receipts`.
6. Vintage separation: Oct 9 / Oct 13 / Oct 8 dated separately passes; calling the Oct 13 composite "current" next to Oct 9 projections, or borrowing RUN DATE 2026-10-14 as a fact date, fails.
7. Lexicon collision on the clause text itself: assert no rendered `ai_tell_phrases` or imported lexicon term appears in the appended contract string.

**Non-Blocking Notes**
- The only allowed link is our own coverage page while the public report page is still absent; `check_link_allowlist` will pass the URL, so presence is a release-gate matter, not a prompt matter.
- No article generated, no provider call, no network, no source edit; all inspection was read-only against `lanes/repos/macro` blobs at `8eb4671` and `918fad1`.
