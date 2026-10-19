# R-IND — T06 closed financial-dossier contract and thin shared adapter: binding rulings

**Task:** T06 of the frozen Industrials nine-task plan, operation
`gmi-industrials-fable-ceo-e2e-20260924-chairman-001`.
**Workstream:** `WS:GMI-INDUSTRIALS-FIRST-VERTICAL`.

**The task itself is NOT DISPATCHABLE.** T06 consumes T01–T05. T01 and T04 are on main
(#7924, #8062); T02 is blocked on a shared seam this program does not own
(`issuer_profiles.py`, `event_workspace.py`, `refresh_event_workspaces.py`, serialized behind
#7870 and #7905), T03 consumes T02, and T05 consumes T03. The whole product chain is
serialized behind that seam — see the T05 rulings file's R8 for why an early dispatch
fabricates rather than refuses.

**Supersession inside this file.** R7 narrows R3 with the T04 as-built surface; R8 carries the
same four consumption rules the T05 ruling carries.

**R7–R8 were verified at PR #8062's cured head `0e3344a9071f` while that PR was still open.**
A dispatching seat re-verifies the exported names and the head sha in its own C0 gate rather
than trusting these lines.

**Binding on this task specifically:** the dossier stores derivation **refs plus values**, and
pins no `receipt_id` literal, receipt snapshot, or golden receipt file — the B2/M2 digest
widening changed every `receipt_id` value, and the B6 cure changed them again. Re-derive
receipts through `engine.fundamental_forensics.industrials_result_cash`; never cache one.

**Why this lives in the repo rather than a session scratchpad.** These rulings bind a future
lane's behaviour and would otherwise die with the session that wrote them. Context:
`agentos/handoffs/GMI-INDUSTRIALS-2026-09-24-first-vertical-implementation.md`,
`research/industrials/first_vertical_program/reviews/OPUS_T04_REDTEAM_2026-09-26.md`,
`DSC:A-LANE-SELF-VERDICT-IS-NOT-A-CLOSURE-GATE`.

---

R1 (R-IND-17; audit F9/F10/F11). Semiconductor B's `contracts/market_ontology/semiconductor_theme_research.v1.schema.json` is const-pinned (`schema` const `semiconductor_theme_research.v1`, `definition_version` const, `additionalProperties: false`, `required` includes `industrial_views`) — Industrials can NEVER emit into it. Mint Industrials' OWN `industrials_theme_research.v1` contract + module on the accepted per-sector precedent (#7891 Technology: `technology_economic_change.v1`). `industrial_views` / `_industrial_row` / `_CAPACITY_OWNER_FIELDS` are SEMICONDUCTOR vocabulary meaning wafer/capacity physical views — your view key is `operating_views`. The "thin adapter into the accepted shared component" is legal only for the future transport/route discriminator (not built here).
R2 (R-IND-18; audit F12). The optional `management_history` section consumes `assess_dossier_comparison('management_sequence', …)` from T05 exactly as it returns (`unavailable`/`projector_unbound`/`management_sequence_missing` all leave `profit`/`cash`/`source_editions` ready). Do not import `guidance_history` here.
R3 (R-IND-16). Every derivation ref in `dependencies` is a `derive_result_cash` result (`formula`, `formula_version`, `operand_refs`, `receipt_ref`) — the dossier stores refs + values, never recomputes; `sections.*.status` mirrors the derivation `status` (`ready`/`limited`/`refused`), and a `limited` comparison never becomes a beat/miss badge in `narrative` (A14-04).
R4 (R-IND-19; audit F13). `.github/ci/legacy-jobs.yml`: touch ONLY the `industrials-result-cash` job block (append paths, extend the single run line, add `jsonschema` to its pip line only if the suite imports it — measure in a clean venv); never reorder sibling blocks; `CURATED_EXCLUSIVE` untouched.
R5 (contract registration). Find the checker that enumerates `contracts/market_ontology/*.schema.json` and `contracts/company_intelligence/*` (`grep -rn "contracts/market_ontology\|contracts/company_intelligence" scripts/*.py tests/*.py | head`); register both new contracts the way the newest sibling contract is registered (quote the diff); if `contracts/company_intelligence/` has no registry today, say so and register only the market_ontology one, recording the gap.
R6 (audit F1). First action after `git fetch`: `git checkout -b claude/ind-t06-financial-dossier origin/main`; quote `git rev-parse origin/main`; C0 proves T01–T05 on main else STATUS BLOCKED. Pin #7870's head sha at the time of your run under EVIDENCE (`git ls-remote origin refs/heads/claude/ssd-semiconductor-theme-intelligence-b-impl-988406e131fd90b9`) — consume nothing from it.
R7 (T04 AS-BUILT — narrows R3; provisional until PR #8062 merges, re-verify in C0). `engine.fundamental_forensics.industrials_result_cash` exports EXACTLY `FORMULA_VERSION` (= `"v1"`), `ALLOWED_FORMULAS`, `qualify_operands`, `derive_result_cash`, `build_comparison_receipt` — nothing else is importable, so a `from ... import` of any other name is an immediate FIX_REQUIRED. Signatures: `build_comparison_receipt(purpose, cells, *, checked=None, unknowns=(), transformations=())`, `qualify_operands(purpose, cells, *, comparison_receipt, formula=None)`, `derive_result_cash(formula, cells, *, comparison_receipt)`. `ALLOWED_FORMULAS` is the closed seven-name vocabulary `growth_pct`, `margin_pct`, `paired_remeasurement`, `cash_after_capital_payments`, `cash_rollforward`, `segment_change_bridge`, `final_vs_preview`; an unknown name RETURNS a refusal carrying `unknown_formula` rather than raising, so the dossier contract branches on status, never on an exception. The dossier contract carries `formula_version` through from the derivation receipt and never re-derives, re-rounds, re-signs or re-labels a number T04 already produced: a closed-contract field either quotes T04's value verbatim or reports the refusal T04 returned.
R8 (T04 round-2 CONSUMPTION RULES — verified at cured head `0e3344a9071f`, binding on T06). Same four rules the T05 ruling carries: always pass `formula=` to `qualify_operands` (otherwise a formula's own operand-requirement guard is inert); an omitted `checked` certifies nothing (all gates default False, `None` == `{}`), so declare what you verified; the `checked` block is disclosure, not authority (currency/scale refuse on operand inspection regardless, duration/perimeter/definition-class gates consult the receipt); and `receipt_id` values CHANGED when its digest widened to cover unknowns + transformations, so the dossier contract must pin no `receipt_id` literal or golden receipt. A closed-contract field quotes T04's value or reports T04's refusal — it never re-derives, re-rounds or re-labels.
