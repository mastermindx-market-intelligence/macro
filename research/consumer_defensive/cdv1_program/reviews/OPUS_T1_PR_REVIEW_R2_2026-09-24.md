# Opus T1 PR #7905 re-review round 2 — head bc33493b511e879a9a2b38c7b371e535274d57b3
Bound to SEAT_RULING_T1_PR_R1 R1–R6. MODE READ_ONLY.

## R1 — scope-derived vocabulary
F1 [BLOCKER] engine/company_intelligence/pg_profile.py:355 — heading is `f"Fourth Quarter {current_year} Results"`: the ruling's named example ("a fixed 'Fourth Quarter 2026'") survives with only the year parameterised. Quarter ordinal is never derived from fiscal_scope; `current_year = current_end.year` (:320) is the CALENDAR year, wrong for PG fiscal Q1/Q2 (FY ends June). No "Three Months Ended <Month DD, YYYY>" form, no fiscal-year-only annual form refused anywhere. — falsifier: any non-Q4 scope binds an EPS fact (probe P4 below).
F2 [BLOCKER] pg_profile.py:325-346,373,398,412,242,279,322-323 — fixture-only vocabulary remains in the extractor: row labels "Prior Diluted EPS"/"Prior Core EPS"; column headers are ISO dates (`current_end.isoformat()`), a form no PG release uses; driver headers "Reported sales growth percent" … "Other contribution percent"; headings "Volume Conventions", "Segments", "Core Reconciliation"; convention literals "Neutral convention"/"dash means zero"; reconciliation located by the terms ("core eps","incremental charge","dilution") = the words of the fixture sentence tests/earnings_economic_fixtures.py:113. Every one of these strings appears in the fixture (_html :44-113) and nowhere in a PG release convention. Standard: fixture-only vocabulary = REJECT.
F3 [MAJOR] tests/test_pg_economic_observations.py:248-261 — the FY2027 test is tautological: pg_workspace_case regenerates the BODY from the scope year (fixtures :166-167, `_html(period=2027)` rewrites heading, ISO headers and prior column), so extractor and fixture vocabulary move in lock-step. It never presents a body where a 2026 column must be refused as current, and does not assert "nothing else binds". It cannot fail for the defect R1 targets.
Probe P5 (R1): fiscal Q1 FY2027 scope (2026-07-01..09-30), fixture-shaped body with "First Quarter 2027 Results" + Q1 ISO headers -> EPS bound: [] (6 EPS-family absences). Probe P6: Q4 scope, heading "Three Months Ended June 30, 2026" (the PG convention the ruling names) -> EPS bound: []. Suite 33/33 green.
R1: NOT HELD.

## R2 — replay must compare (value AND period)
Value/text compare at economic_observations.py:214-221 is real. Mutant M1 (`if False:` at :220) -> the three tamper tests (:135,:144,:156) FAIL (3 failed) -> pinned.
F4 [BLOCKER] economic_observations.py:168-174,214-221 — the ruled "and, for period-bearing spans, to the stored period" is not implemented: the stored period is checked only against the METRIC (prior_* -> prior_end, else current_end); nothing ties the replayed span to the column whose header is that period. Probe P3: swap pg_diluted_eps <-> pg_prior_diluted_eps spans AND values -> ACCEPTED (current fact now carries the prior-year 1.37 under period 2026-06-30). Probe P1: pg_diluted_eps retargeted to the Diluted EPS PRIOR-YEAR cell "$1.31", value 1.31 -> ACCEPTED. Probe P2: pg_core_eps retargeted to the GAAP Diluted EPS cell "$1.25" -> ACCEPTED (non-GAAP metric proven by a GAAP cell). Replay proves "some bytes parse to this number", not "this metric/period's cell". — falsifier: any of P1–P3 refused.
F5 [MAJOR] tests/test_pg_economic_observations.py:144-153 — "span pair" test swaps present_rows[:2] = pg_reported_sales_growth_pct (3.0) and pg_organic_sales_growth_pct (1.0), NOT a current/prior pair; it passes only because the values differ. The named current/prior tamper is untested (and passes, P3).
F6 [MAJOR] economic_observations.py:216-217 — any replayed dash becomes 0.0 with no check of the neutral-zero convention the extractor requires (pg_profile.py:240-244). Probe P9 (blank_dash): forge pg_organic_volume_growth_pct=0.0 pointing at its dash cell (row convention "0.0", not "dash means zero"; extractor emitted an absence) -> ACCEPTED. Validator semantics diverge from extractor semantics.
R2: NOT HELD (value half held and pinned; period half absent).

## R3 — drivers by column header
pg_profile.py:150-166 locates header cell -> column index -> row; tests :22-43 assert all 8 driver VALUES on annual_first AND columns_reordered; fixture :62-65 permutes header and both value rows together. Held mechanically.
F7 [MINOR] pg_profile.py:372-386 — the two volume drivers are read from the "Volume Conventions" table while the Sales Drivers table also carries volume columns; disagreement between the two is never checked. (Vocabulary itself is F2.)
R3: HELD (mechanics); vocabulary defect carried by F2.

## R4 — unit-aware parsing
Probe P7: '$1.25'->1.25, '(1.25)'->-1.25, '1.25%'(usd)->None, '$1.25'(pct)->None, '(+2)%'->-2.0; test_unit_shape_mismatch (:241) yields a typed absence. Held for ruled shapes.
F8 [MINOR] pg_profile.py:112 — percent pattern accepts UNBALANCED parens: '(1.25%' -> -1.25, '1.25%)' -> 1.25 (coerced, not refused). '-2%' and '$(1.25)' -> None (absence, acceptable).
Deviation `missing_units` vs ruled `unit_mismatch`: documents.py:72-84 ABSENCE_REASONS is a closed frozenset; `missing_units` asserts the units are ABSENT, which is false here (units present, wrong shape) — a mislabel in a vocabulary whose purpose is countable reasons. Recommendation: do NOT ratify; add `unit_mismatch` to ABSENCE_REASONS (one line, same registry) and use it at pg_profile.py:254 + test :245. If the seat wants zero shared-vocab edits in T1, ratify explicitly in a DEC with the future rename named — not silently.
R4: HELD (with F8 minor).

## R5 — quarter, combined-only, fixture 1.48
F9 [BLOCKER] economic_observations.py:80 — expected_quarter = (month+2)//3 is the CALENDAR quarter; PG fiscal Q4 (June 30) => 2. The fixture was bent to match: pg_workspace_case builds FiscalPeriod(quarter=(month+2)//3) (fixtures :176) while its own FISCAL_PERIOD constant says quarter=4 (fixtures :22, unused). Result: the P&G fiscal-Q4 event is minted as `evt_cik0000080424_2026q2_results` (probe P10 output) and a correctly labelled fiscal-Q4 workspace is REFUSED (probe P4: "workspace quarter does not match fiscal_scope"). Mutant M2 (quarter check -> `if False:`) -> 33/33 still pass: the check has no negative test. The hard-coded Q4 rule was moved, not dropped: extraction still binds only "Fourth Quarter" (F1/P5).
F10 [MAJOR] tests/earnings_economic_fixtures.py:67-77,110 + test :213-226 — "combined_volume_only" is NOT combined-only: the Sales Drivers table still carries split "Mix contribution percent"/"Total volume growth percent" columns; probe P8: pg_mix_contribution_pp binds 0.5 in the combined case. Test asserts only the two volume metrics, never mix; absence subject/detail do not name the combined presentation (subject==metric is forced by :148 — ruling R5 vs R6 tension the lane resolved silently; detail is the generic "No unique heading…" string). Absence arises only because fixture-only labels are missing, not from any combined-line recognition.
1.48 removed (grep: no 1.48/1.63/4-digit figures in fixture). Held.
R5: NOT HELD (quarter derivation wrong + untested; combined-only property untested for mix).

## R6 — minors
- Absence rows: authority pinned `context_only` (:146), subject==metric (:148), event bound (:150), exact key set rejects extra keys (:131), TypedAbsence closed-vocab reason re-validated (:136). Test :317. HELD.
F11 [MINOR] economic_observations.py:152 — absence (and present-span, :181-183) document_id is bound to the CALLER's source_texts keys, not to the workspace's own document. Probe P11: absence pointed at "doc_other" with an extra caller text -> ACCEPTED.
F12 [BLOCKER] pg_profile.py:201,217 + economic_observations.py:121-122 — fact_id is `fact_{metric}`; the ruled derivation from (event, metric, period, basis) is not implemented, while the error text at :122 claims it is. Probe P10: `fact_pg_diluted_eps` for event evt_cik0000080424_2026q2_results — every PG event mints the same fact_id per metric (cross-event collision). Duplicate refusal (:117) HELD.
F13 [MAJOR] engine/company_intelligence/qa_exchange.py:26 vs pg_profile.py:26 — `RIGHTS_PROFILES` is registered but read by NOTHING (git grep: sole occurrence is its definition); the operative token is a second literal `PG_PRIVATE_RIGHTS_PROFILE = "rp_internal_private_v1"` in pg_profile.py, and the validator (:179) compares to that literal, not to the registry. Two declarations, registry decorative: deleting the registry entry breaks nothing. Fix: import from qa_exchange (or assert membership) so the registry is load-bearing.
- rights_profile must equal private (:179), test :348 HELD. None fiscal_period -> EconomicObservationError (:76-77), test :307 HELD (extractor path pg_profile.py:317 still AttributeErrors on None — MINOR, F14).
- Dash span at dash cell: test :357 HELD. F14-orig: `headers` param gone; single 24 cap (:91) HELD.
R6: NOT HELD (fact_id identity; registry not load-bearing).

## Fixture / registry / CI
- Fixture-literal grep of pg_profile.py: FAIL — see F2 (≥15 fixture-only literals).
F15 [BLOCKER] tests/earnings_economic_fixtures.py:45 — `$1.37` (asserted as pg_prior_diluted_eps at test :30,:259) is P&G's REPORTED Q4 FY2023 diluted EPS ("Diluted net earnings per share were $1.37", P&G 8-K exhibit 99.1, 2023-07-28). Ruling R5 required re-checking the fixture for live-looking numbers after 1.48; this one survived. 1.48/1.63/4-digit sales: absent. Fix: replace with an obviously synthetic value (e.g. 1.07).
- CI job earnings-economic-dossier (.github/ci/legacy-jobs.yml:13436-13478): gate code, exclusive, paths cover the new files + fixtures, `pip install pytest pyyaml`, runs the 33-test file; `if: ${{ false }}` is the file-wide convention (229 jobs). No finding.

## VERDICT
REJECT — R1, R2 (period half), R5 (quarter), R6 (fact_id) are not real; R3, R4 held. Counts: BLOCKER 6 (F1,F2,F4,F9,F12,F15) · MAJOR 5 (F3,F5,F6,F10,F13) · MINOR 3 (F7,F8,F11) + extractor None-period note.
Minimal repair set (re-lane, same seams):
1. pg_profile: derive quarter ordinal + FISCAL year from fiscal_scope with PG's June FYE; accept "<Ordinal> Quarter Fiscal <FY>" / "Three Months Ended <Month D, YYYY>" headings and period column headers; refuse fiscal-year-only annual headers for a quarterly scope; drop ISO-date headers, "Prior … EPS" rows, "Volume Conventions"/"Neutral convention"/"dash means zero", and the sentence-word reconciliation locator. Rebuild the fixture in those conventions; FY2027 test must use a body NOT regenerated from the scope and assert the full bound set.
2. Validator: bind span -> period (and row) — e.g. carry the column header/row label bytes in the receipt or re-locate the cell's column header from source and compare to the stored period; add the current/prior EPS swap (span+value) and core<-GAAP retarget tests; dash-replay must require the row's neutral-zero convention.
3. Quarter: fiscal quarter = ((month - FYE_month - 1) % 12)//3 + 1; fixture uses quarter=4 for June; add a negative mismatch test.
4. fact_id = hash/compose(event_id, metric, period, basis); validator recomputes.
5. Registry: pg_profile imports the token from qa_exchange (or asserts ∈ RIGHTS_PROFILES) and validator checks membership.
6. Replace $1.37; combined-only fixture drops split volume/mix columns from the drivers table and the test asserts mix absence + a detail naming the combined line.
7. `unit_mismatch` into ABSENCE_REASONS (recommended over ratifying missing_units).
