# T04a content review R1 — MINING_DOMAIN_DEFINITIONS_M1_2026-09-24.md (PR #7922)

ROUTE: review · MODE: READ_ONLY · 2026-09-24 · adversarial, read-only.

ARTIFACT: `refs/remotes/pr/7922:research/mining/m1_integration_program/domain/MINING_DOMAIN_DEFINITIONS_M1_2026-09-24.md`
Artifact line numbers below = `git show refs/remotes/pr/7922:<path> | cat -n`.
Sources ref `R` = `origin/sol/mining-principal-research-20260923`; source line numbers = `git show "${R}:<path>" | cat -n`.

## VERDICT

**VERDICT: ACCEPT-WITH-FIXES** — 2 BLOCKER, 5 MAJOR, 4 MINOR. Repairs are surgical (delete one metric block, retype four field values, re-point two locators, add one metric); the file does not need re-derivation. Do not merge until F1–F7 are closed.

## What I tried to falsify and could NOT break (no finding — recorded so the seat does not re-litigate)

- **R-MIN-03 (no live figures): CLEAN.** Full-file scan found no tonnage, dollar amount, percentage, price, cost/lb or ownership %. The only numerals are the two CIKs (artifact:16, :142 — identity, sanctioned by the commission) and the five provenance blob SHAs. Every quantitative relation is carried in words ("already proportionately consolidated", "positive adjusted EBITDA can coexist with a GAAP loss"). This is the ruling most likely to force a REJECT and the file passes it.
- **`magnetics_precursor_revenue` is NOT a substituted line.** I suspected the artifact had swapped the frozen "Magnetics revenue" for a narrower sub-line, breaking the disclosed reconciliation. Falsified: `MINING_BATTERY_RARE_EARTH_ECONOMICS_2026-09-23.md:67@R` — "MP's Q2 release identifies $16.524 million of Magnetics revenue as magnetic precursor products". Same row, same literal as `MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md:62@R`. The artifact's label is more accurate than the qualification's; the segment reconciliation at artifact:191 still holds. **No finding on the value.** (The *label string* is a separate defect — see F5.)
- **Nine-key completeness: CLEAN.** All 15 `required_metrics` entries (artifact:30–83, :159–239) carry exactly `key, label, basis, period_kind, sign_convention, exclusions_or_definition_notes, source_family, selection_label, research_locator`.
- **Antamina section computes nothing: CLEAN.** artifact:280–282 carries no silver interest, payability, threshold, step-down or purchase-price figure, and states "No entitlement value is computed here" — correct against `MINING_COPPER_PRECIOUS_ASSET_DOSSIERS_2026-09-23.md:75,83@R` (§4 "Dossier 3 — Antamina's silver", "### Conditional entitlement arithmetic"), which is exactly the section whose arithmetic must not travel.
- **Provenance table: CLEAN.** All five blobs re-derived with `git rev-parse "${R}:<file>"` and matched byte-for-byte: `34548e6b…`, `a2fca1c5…`, `053a59e2…`, `52ac589b…`, `1bef33fc…`.
- **Morenci double-application, output≠sales, PPA≠revenue, GAAP≠adjusted, half-year≠quarter:** all present and correctly worded (artifact:71, :117, :119, :227, :262, :266, :267).

## FINDINGS

### F1 — BLOCKER — Grasberg entry contradicts the only source that supports it

- **Artifact:80** — "A dated recovery expectation is not new capacity, a discovery, or **a next-period outlook**."
- **Contradicted by:** `research/mining/MINING_COPPER_PRECIOUS_ASSET_DOSSIERS_2026-09-23.md:37@R` — "In April, Freeport lowered its expected **second-half 2026** Grasberg Block Cave operating level from the earlier approximately 85% to approximately 65%".
- The selected figure **is** a next-period (H2 2026) outlook, issued in April. The artifact's definitional note asserts the exact opposite of its cited source, and a code task told these YAML blocks "may be copied verbatim" (artifact:3) will encode the inversion.
- **Compounding, same entry:** `basis: reported` (artifact:77) is wrong — a lowered management expectation is an issuer estimate, not a reported outcome; `period_kind: point_in_time` (artifact:78) is wrong for an H2-2026 forward level and is the only non-`quarter` value in the file with no enum support anywhere in the plan or addendum; and the April vintage sits on the *estimate* side of the very Apr-vs-Jul comparison W-C exists to run, so admitting it as a `reported` measure re-opens the period mixing IR-02 forbids (`docs/superpowers/plans/2026-09-24-mining-integration-plan-addendum.md:61@R`).
- **Exact replacement:** delete artifact:75–83 (the whole `grasberg_block_cave_operating_level_estimate` entry) and delete `- Grasberg Block Cave operating recovery` at artifact:21. Grasberg is absent from the frozen W-C selection (`MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md:33–38@R` lists copper sales, unit net cash cost, production, idle/restoration, Morenci and nothing else), so M1 loses no frozen input. If the seat wants the mechanism retained, retain it as prose only in §A, wording: "A dated change to an expected future operating level is an expectation revision with its own vintage, not a reported outcome, new capacity, or a discovery."

### F2 — BLOCKER — `definition_status` is hardcoded to a degraded value the frozen source contradicts

- **Artifact:90 and :97** — `definition_status: definition_unqualified` on both the earlier estimate and the later actual; **artifact:99** — "an unqualified definition produces no beat, miss, improvement, or consensus badge" (stated unconditionally).
- **Contradicted by:** `MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md:35@R` — the Required-scope column for copper sales supplies "Million recoverable pounds; consolidated reporting; sales excluding purchases", i.e. unit, perimeter and reporting basis are **present**, which is precisely what would make the comparison qualified.
- **And by:** `docs/superpowers/plans/2026-09-24-mining-integration-plan-addendum.md:15@R` — "The helper **appends** `definition_unqualified:<field>` when both prior and actual lack a basis, currency, perimeter or definition." The status is a runtime emission of the shared helper, not a domain constant. `…addendum.md:57@R` additionally requires "test fully qualified compatible inputs **so the consumer does not suppress a genuine positive comparison**" — freezing the degraded value makes that suppression unconditional.
- **Exact replacement:** delete the `definition_status:` lines at artifact:90 and :97. Replace artifact:99 with: `comparison: The two separately sourced literals remain inspectable. When the shared helper emits definition_unqualified for any compared field, no beat, miss, improvement, or consensus badge may be produced; when all compared definitions are qualified and compatible, a genuine positive comparison must not be suppressed.`

### F3 — MAJOR — the investor question promises a unit-cost comparison the contract never wires

- **Artifact:17** — "…deliver copper sales **and unit cost** outcomes different from management's earlier estimate?"
- **Artifact:84–101** — `management_estimate_vs_actual` carries exactly one pair, `management_issued_copper_sales_estimate` → `consolidated_copper_sales`. No cost pair exists.
- **Frozen source requires both:** `MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md:36@R` — the "Copper unit net cash cost" row carries both an "Earlier issued Q2 estimate, C1" and a "Q2 actual, C2" column, identically to the sales row at :35. Dropping it silently narrows a frozen selection.
- **Exact replacement:** either (a) restate artifact:17 as "…deliver copper sales outcomes different from management's earlier estimate, with unit cost reported beside it?", or preferably (b) convert `management_estimate_vs_actual` to a list of two comparison objects and add the cost pair with `earlier_point_estimate.metric: management_issued_copper_unit_net_cash_cost_estimate`, `later_actual.metric: copper_unit_net_cash_cost`, `selection_label: Second-quarter copper unit net cash cost outlook` / `Second-quarter consolidated unit net cash cost`, `period_kind: quarter`, plus the carried note `changed by-product assumptions prevent an isolated productivity interpretation` (IR-02, `…addendum.md:61@R`).

### F4 — MAJOR — Morenci locator points at the dossier's live-figure section when the qualification is not silent

- **Artifact:74** — `research_locator: MINING_COPPER_PRECIOUS_ASSET_DOSSIERS_2026-09-23.md § Dossier 1 selected evidence`.
- **The qualification is NOT silent on Morenci:** `MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md:38@R` — "Its Morenci discussion specifies proportionate consolidation of a 72% interest… do not… multiply an already-proportionate number by ownership again." The review standard permits the dossier only where the qualification is silent.
- **Aggravating:** the section actually pointed to (`MINING_COPPER_PRECIOUS_ASSET_DOSSIERS_2026-09-23.md:19–25@R`) is the densest live-figure block in the corpus — 72%, 55.08%, 55.66%, 48.76%, 66%, 117/202/786/218/568/47 million pounds, 84.24 million, 28%. Sending an implementer there as the authoritative locator is the single highest R-MIN-03 exposure the file creates.
- **Exact replacement (artifact:74):** `    research_locator: MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md § W-C selected test inputs`

### F5 — MAJOR — two `selection_label` values cannot resolve to a single real row

- **Artifact:37** — `selection_label: Consolidated sales outlook **or** operating summary copper sales row` — a disjunction, not a header. **Artifact:175** — `selection_label: Magnetics revenue magnetic precursor products` — a concatenation of a table row label with body-text characterization; no such single label exists (`MINING_BATTERY_RARE_EARTH_ECONOMICS_2026-09-23.md:67@R` shows "Magnetics revenue" is the row and "magnetic precursor products" is the release's prose gloss).
- **Contradicted by:** `MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md:83@R` — "The literal path masks markup attributes and **refuses multiple matches within its window**. Numeric text appearing in both a quarter and half-year table is therefore a selector problem"; and `…addendum.md:61@R` — "A correct numeric span **without its label/header** cannot prove the selected measure." A label that matches zero or many rows is an unresolvable selector.
- **Exact replacement:** artifact:37 → `    selection_label: Consolidated copper sales row`; artifact:175 → `    selection_label: Magnetics revenue`, and move the precursor characterization into `exclusions_or_definition_notes` at artifact:173, which already carries it.

### F6 — MAJOR — `source_family: issuer_release` is invented; nothing in the frozen selections uses it

- **Artifact:81** — `source_family: issuer_release`, the only non-`sec_edgar_8k_exhibit` value in the file.
- **Contradicted by:** `MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md:25–27@R` (C1/C2/C3) and `:52–53@R` (R1/R2) — every frozen candidate is an 8-K exhibit or a 10-Q; and `…addendum.md:77@R` discusses the `sec_edgar` registry disposition as the governing family. The dossier's [A03] Grasberg observation is the April release = C1 = the same 8-K exhibit.
- **Exact replacement:** moot if F1 is applied (entry deleted). If the seat overrules F1 and retains Grasberg, set artifact:81 → `    source_family: sec_edgar_8k_exhibit`.

### F7 — MAJOR — `research_locator` for nine W-R metrics names a heading that does not exist

- **Artifact:167, :185, :194, :203, :212, :221, :230, :239** — `§ W-R selected measurements`.
- **Actual heading:** `MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md:57@R` — `### Selected Q2 measurements, USD thousands unless stated`. The dropped "Q2" and the dropped units clause are load-bearing: the whole quarter-vs-half-year hazard (`…qualification:71@R`, `…addendum.md:61@R`) lives in that heading, and a locator that omits the period invites the H1 column.
- **Exact replacement (all eight lines):** `    research_locator: MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md § W-R Selected Q2 measurements`

### F8 — MINOR — idle/restoration `basis` fights its own `sign_convention`

- **Artifact:50** `basis: company_adjusted` vs **artifact:52** "Charges retain their **reported** charge direction." The disclosed charge amount is a reported figure; what is company-defined is its *exclusion* from the non-GAAP unit cost.
- **Exact replacement (artifact:50, :52):** `    basis: reported` / `    sign_convention: Charges retain their reported charge direction.` and extend artifact:53 with `; this is a reported charge whose exclusion from unit cost is the issuer's non-GAAP definition.`

### F9 — MINOR — one `counter_thesis` entry names no metric or reference

- **Artifact:107** — "A later compatible operating or cash observation that reverses the direction contradicts an assertion of durable improvement." No metric key, no source reference; unfalsifiable as written. The other three W-C entries and all four W-R entries do name theirs.
- **Source of the correct phrasing:** `MINING_COPPER_PRECIOUS_ASSET_DOSSIERS_2026-09-23.md:43@R` — "**Discriminating evidence:** successive mine-specific throughput/recovery/sales observations, exact cost definitions, capital spending, and a matching forecast vintage."
- **Exact replacement (artifact:107):** `  - A later consolidated_copper_sales or copper_unit_net_cash_cost observation on a matching definition and forecast vintage that reverses the direction contradicts an assertion of durable improvement.`

### F10 — MINOR — `management_estimate_vs_actual` has two incompatible shapes across the two slices

- **Artifact:84–101** (keys `earlier_point_estimate`/`later_actual`/`comparison`/`is_range`/`is_consensus`) vs **artifact:240–243** (keys `observation`/`is_range`/`is_consensus`). A block declared "the later code task's complete content contract… may be copied verbatim" (artifact:3) cannot present one field name in one slice and a different one in the other.
- **Exact replacement (artifact:240–243):** keep `is_range: false` / `is_consensus: false`, and express the absence in the shared shape — `  earlier_point_estimate: null` / `  later_actual: null` / `  comparison: W-R has no selected management estimate-versus-actual comparison in M1; separately qualified quarter observations are reported without inventing one.`

### F11 — MINOR — the stream vocabulary sits on the slice with no stream, and the stream case carries none

- **Artifact:252** puts `stream_threshold_unknown` in the MP `limitations_vocabulary`, while the actual stream case (Antamina, artifact:278–282) is prose with no vocabulary attached. MP's instrument is a price-protection agreement with a benchmark and a capacity condition (`MINING_BATTERY_RARE_EARTH_ECONOMICS_2026-09-23.md:68@R`), not a metal stream.
- **Not a rule violation:** `docs/superpowers/plans/2026-09-24-mining-economic-dossier-implementation.md:199@R` (`assert "stream_threshold_unknown" in result["limitations"]`, task T04) and `:317@R` (MGD-18 `test_missing_threshold_keeps_contract_explanation`) sanction the term under T04, so **do not remove it**.
- **Exact replacement (add after artifact:249):** a one-line note in §B prose — "The `stream_threshold_unknown` limitation is used here for any unverified contractual threshold balance, including a price-protection benchmark or capacity condition; it does not assert a metal-stream instrument."

## REPAIR PACKET (hand to a fix lane verbatim)

```
File: research/mining/m1_integration_program/domain/MINING_DOMAIN_DEFINITIONS_M1_2026-09-24.md (PR #7922). Content-only; add no numbers.
1. DELETE lines 75-83 (grasberg_block_cave_operating_level_estimate) and line 21 ("- Grasberg Block Cave operating recovery"). [F1,F6]
2. DELETE lines 90 and 97 (definition_status:); REPLACE line 99 comparison: per F2 (badge suppressed only when the helper emits definition_unqualified; qualified inputs must not be suppressed).
3. ADD a second comparison pair for copper unit net cash cost per F3 (estimate + actual, period_kind quarter, carry the by-product caveat); OR narrow line 17 to sales only.
4. Line 74 research_locator -> "MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md § W-C selected test inputs". [F4]
5. Line 37 selection_label -> "Consolidated copper sales row"; line 175 -> "Magnetics revenue". [F5]
6. Lines 167,185,194,203,212,221,230,239 -> "... § W-R Selected Q2 measurements". [F7]
7. Line 50 basis -> reported; extend line 53 note per F8. Line 107 counter_thesis -> named-metric form per F9. Lines 240-243 -> shared null-shape per F10. Add the stream_threshold_unknown scope note per F11.
DO NOT: introduce any figure, percentage, price or tonnage; re-point any locator into MINING_COPPER_PRECIOUS_ASSET_DOSSIERS §2 "Selected evidence" or § "Recovery, expansion..."; remove stream_threshold_unknown.
```

## Evidence log

- Research sections spot-checked: **6** — qualification §2 "Candidate source sequence" (:21@R) ✓; qualification §2 "Selected test inputs" (:31@R) ✓; qualification §3 "Selected Q2 measurements, USD thousands unless stated" (:57@R) ✓ heading text differs (F7); copper dossier §2 "Dossier 1 — Freeport" / "Selected evidence" (:17,:19@R) ✓ exists but wrongly cited (F4); copper dossier "Recovery, expansion and new capacity are different economic mechanisms" (:35@R) ✓ exists and contradicts the artifact (F1); RE dossier "B04 — MP Materials: precursor sales, customer qualification and price protection" (:65@R) ✓ exists and vindicates the artifact.
- Provenance blobs: 5/5 re-derived and matched.
- Tool calls used at time of writing: **7**.
- No file in the worktree was read, created, edited or checked out; all source reads via `git show`. Zero `gh` calls.
