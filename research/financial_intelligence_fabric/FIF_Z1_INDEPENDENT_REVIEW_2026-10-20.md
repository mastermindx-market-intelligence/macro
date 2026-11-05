# FIF Z1 independent review — 2026-10-20 (r1)

- Lane: `fif-z1rev-20261020-r1` (Subagent Fabric, host ubuntu2, glm-5.3, task class review)
- Reviewed head: `830adc10d7098502bc659442dd53ab164a1461c8` (PR #9891, `claude/fif-z0-records-20261020`)
- Artifacts attacked: `FIF_Z0_CLOSURE_MATRIX.json` (54 rows) and the A54 export ruling
- Lane verdict: **FAIL**; **A54: RATIFY**
- The seat's adjudication of each finding is below; the lane output follows verbatim.
  The seat's adjudication is not an independent review; only the lane's findings are.

| Finding | Lane claim | Seat adjudication | Matrix effect |
| --- | --- | --- | --- |
| F1 | A43 cited tests prove corpus hygiene only; no tablet cell in REQUIRED_CELLS; focus restore / disabled text unasserted | CONFIRMED (0 "tablet" in both cited files) | A43 CLOSED -> PARTIAL, test_gap obligation |
| F2 | A22 cited tests check headers only; body scan lives in uncited `_assert_error`; no caplog test | CONFIRMED | A22 CLOSED -> PARTIAL, evidence amended, test_gap obligation |
| F3 | A19 `.mjs` suite executed only by a disabled job (`if: ${{ false }}`) | REBUTTED: legacy-pack jobs MUST declare `if: ${{ false }}` (scripts/run_ci_pack.py:83 DISABLED_IF, :1580-1583) so GitHub allocates no duplicate runner; ci-pack-0 ("validate and run legacy CI pack") still executes them, scoped by gate/scope/paths; fif-kernel-guards (.github/ci/legacy-jobs.yml:8902, gate code, scope exclusive, explicit paths) ran on ci.yml run 39461860948 (cov-wire @59eb8978, "Selected jobs: fif-kernel-guards", success) | A19 stays CLOSED, adjudication noted |
| F4 | A03 inconsistent leg asserted only by an uncited test | CONFIRMED | evidence amended, stays CLOSED |
| F5 | every CLOSED row is CI-dark (suites only in legacy-jobs.yml) | REBUTTED, same evidence as F3 | adjudication noted on A51 |
| A54 | RATIFY the synchronous stateless re-issue ruling | accepted | A54 PARTIAL -> CLOSED |
| NOTE | A37 obligation kind mislabelled | accepted | implementation_gap -> dependency_admission |
| NOTE | A54 note carried an off-topic #9884 sentence | accepted | moved to A36 |
| NOTE | masterplan path absent from HEAD; guard checks names only | accepted, no change (pinned commit readable; guard scope is recorded in the handoff danger_areas) | none |

Next: one fabric build lane repairs the A43/A22 test gaps; the re-review covers only that diff.

---

## Lane output (verbatim)

All evidence is in. Consolidating the final adjudication — every packet received, my own A54/A19/A20/CI-wiring checks complete.

---

STATUS: DONE

RESULT:
**VERDICT: FAIL** (Z1 independent acceptance — four F-rows are defects; the matrix's own no-premature-finalization discipline held, `claimable:false` / "Z1 pending" is honest)
**A54: RATIFY** (below)

F-rows:
- **F1 — A43 CLOSED → LOWER_TO PARTIAL.** Cited tests prove corpus hygiene, not the behavior. `tests/test_check_ui_visual_evidence.py:1140-1141` (`all_findings.extend(guard.validate_manifest_evidence(record, guard.REPO_ROOT))` / `assert all_findings == []`) checks structure only (receipt shape, PNG sha256, dims, theme/locale); `REQUIRED_CELLS` (:31-36) covers desktop/mobile × en/zh × dark/light — **no tablet**, the exact 820px band the note says #9879 fixed; the capture tool disclaims judgment (`test_fif_p2_evidence_capture.py:397` "measures and screenshots; judges nothing"); `test_manifest_postprocess_populated` runs on a synthetic 3-row fake manifest (:411-464). Focus restore (keyboard set captures only containment: tab_keys/drawer_trap `escaped==0`), disabled/unavailable text, and readability are asserted by **no cited test**; the linter also skips on every sparse checkout (:1119 `needs_full_checkout("mockups")`; locally: "1 passed, 1 skipped"). The corpus itself is real (135 entries, 8/8/8/48/36 incl. 36 keyboard states, recaptured through #9882) — evidence adjacent.
- **F2 — A22 CLOSED → LOWER_TO PARTIAL.** The clause "no secret/source body in error or logging" is unproven: both cited tests check headers only (`financial_query_api.py:67-69` `_assert_private_headers` header loop); the body-leak scan lives in the uncited `_assert_error` (:397-400, forbidden-strings); **no cited test captures logs at all**. Deny-before-open is proven (:1095-1097 constructions all zero; :204-206 resolve_calls == []).
- **F3 — A19 CLOSED → LOWER_TO PARTIAL.** 8/14 cited items are `tests/fundamental_forensics_a19_hostile.test.mjs`, executed only by disabled job `fif-kernel-guards` (`.github/ci/legacy-jobs.yml:8902-8903` `if: ${{ false }}`; step :10002-10003 `node --test … a19_hostile.test.mjs … a44_span.test.mjs`); no enabled workflow mirrors it (grep over `.github/workflows/`). The .mjs assertions are substantive (static sink/esc/safeUrl pins + vm-rendered hostile payloads — verified by read), but no enabled automation keeps them true; the note's "mutation-checked" is an unverifiable run claim.
- **F4 — A03 CLOSED → amend evidence or LOWER_TO PARTIAL.** The "inconsistent" leg of "distinguish exact/consistent/inconsistent" is asserted only by an **uncited** test (`multi_filing_lineage.py:340-341` `assert classification.state == CHAIN_STATE_CONTRADICTORY` / `edge_refusals == (None, "changed_value")`); cited tests cover exact/rounded/ambiguous + no-transitive-rescue.
- **F5 — systemic (all 31 CLOSED rows).** Sampled cited suites (`query_exports`, `admitted_filing_package`, `a18_publish_fault_drill`, `cross_filing_lineage` .py + both .mjs) appear in **no enabled `run:` step** — only inside `if: false` legacy jobs; the repo's own census rule (`ci.yml:3082-3092` "an unnamed suite is genuinely never executed") makes the closure evidence enforcement-dark. Wire the closure-evidence corpus into an enabled job or record a `ci_proof` obligation. (Verified by sample, not exhaustively.)

54-row table (CLOSED → PROVEN|ADJACENT|TAUTOLOGICAL|MISSING; others echo verdict + HONEST|LOWER_TO):
| row | verdict | adjudication |
|---|---|---|
| A01 | CLOSED | PROVEN — all 18 keys forged independently, both gates refuse (cross:834-883) |
| A02 | CLOSED | PROVEN — byte-identity pins + A3 not_evaluable refusal retained |
| A03 | CLOSED | ADJACENT — F4 (inconsistent leg uncited) |
| A04 | CLOSED | PROVEN — untyped never picked; only typed AMENDMENT satisfies restated |
| A05 | CLOSED | PROVEN — v1 guard preserved; forks/skips/mixed versions refused |
| A06 | CLOSED | PROVEN (NOTE: kernel-layer non-USD refusal proven via inventory+release/cohort layers; fiscal/calendar label pin only) |
| A07 | CLOSED | PROVEN |
| A08 | CLOSED | PROVEN — never invented zero; reason asserted |
| A09 | CLOSED | PROVEN |
| A10 | PARTIAL | HONEST — Chairman dependency admission, specific |
| A11 | CLOSED | PROVEN — guessed-approved namespace needs the source map |
| A12 | PARTIAL | HONEST — #9761 pending-merge, specific clock test named |
| A13 | CLOSED | PROVEN — reconstruction + attestation refused both layers |
| A14 | CLOSED | PROVEN — real Data OS chain (`statement_service.py:217` `cik = issuer_master.cik_of_issuer(entity_id)`; build script excludes unbound/disagreeing CIKs) |
| A15 | CLOSED | PROVEN (NOTE: invalid-mode POST-path legs carried by uncited tests; health-GET cited) |
| A16 | CLOSED | PROVEN — 400/413, provider never opened, leak-scan + network tripwires |
| A17 | CLOSED | PROVEN — collision/read-back/stale all fail closed, no pointer advance |
| A18 | CLOSED | PROVEN — drill subclasses real store, drives real publish producer; S1-S4 as named |
| A19 | CLOSED | ADJACENT — F3 (CI-dark .mjs evidence) |
| A20 | CLOSED | PROVEN — one pacer across collectors/paths, 0.5s floors, workflow flags pinned (NOTE: strongest anti-multiplication tests — private-pacer comparison, 8-worker ≤2/s aggregate — are in-file but uncited; cross-process sharing unproven, single-host deployment bounds it) |
| A21 | PENDING_LIVE | HONEST — natural-schedule proof, observable artifact named |
| A22 | CLOSED | ADJACENT — F2 (error/log leak clause unproven) |
| A23 | PARTIAL | HONEST |
| A24 | PARTIAL | HONEST |
| A25 | CLOSED | PROVEN — refusal codes, closed shape, packet immutability |
| A26 | CLOSED | PROVEN — amount/base exposed; no score/risk key |
| A27 | CLOSED | PROVEN — language gate trips "fraud", spares "Alphabet" |
| A28 | CLOSED | PROVEN — three distinct typed outcomes |
| A29 | CLOSED | PROVEN |
| A30 | CLOSED | PROVEN (NOTE: FCF clause vacuous — no FCF detector ships) |
| A31 | CLOSED | PROVEN (NOTE: inventory/cash-flow double-count covered by the registry-wide consolidated_only fence, not per-statement) |
| A32 | CLOSED | PROVEN |
| A33 | PARTIAL | HONEST — admits replays skip without FIF_GSRC_STAGE_ROOT |
| A34 | PARTIAL | HONEST — 12 packs specified only |
| A35 | CLOSED | PROVEN |
| A36 | PENDING_LIVE | HONEST — 32,267/50,000 deep (0/250), 63,202/100,000 core (0/1,000), blockers match record exactly |
| A37 | PARTIAL | HONEST — 12/12 qualified abstain, no pass claim, labeler-owned; record consistent |
| A38 | PARTIAL | HONEST |
| A39 | HUMAN_GATE | HONEST — real named gate (Accessibility/Screen Recording, refused 10-19), no re-probe |
| A40 | CLOSED | PROVEN (NOTE: vintage roundtrip implicit in column-map completeness) |
| A41 | PARTIAL | HONEST — flags OFF, owner named |
| A42 | HUMAN_GATE | HONEST |
| A43 | CLOSED | ADJACENT — F1 |
| A44 | PARTIAL | HONEST (its 4 .mjs citations share F3's CI-darkness; verdict already PARTIAL) |
| A45 | HUMAN_GATE | HONEST |
| A46 | HUMAN_GATE | HONEST |
| A47 | PARTIAL | HONEST |
| A48 | PENDING_LIVE | HONEST |
| A49 | PARTIAL | HONEST |
| A50 | PARTIAL | HONEST |
| A51 | CLOSED | PROVEN — the guard structurally enforces the discipline; "Z1 pending" honest |
| A52 | PARTIAL | HONEST — hold mechanism not built, correctly not CLOSED |
| A53 | PARTIAL | HONEST |
| A54 | PARTIAL | HONEST + ruling below |

**A54 — RATIFY.** The handler is stateless (`app/forensics.py:1260-1300`: admit body → provider → execute → export; no job store; `Depends(require_site_full_user)` per call; no job/queue machinery anywhere in the file). Scenario 1 (connection lost mid-export, new generation published): re-issue of the identical canonical bytes returns 200 bound to the NEW receipt (`test_a54_reissue_after_a_new_generation_binds_the_new_receipt`: `new_receipt != old_receipt`; `new_exports[path].headers["x-fif-receipt-sha256"] == new_receipt`); the client's recorded sidecar digest no longer matches and `export_with_sidecar` refuses on mismatch — the change is detected, never silent; nothing strands server-side. What re-issue cannot do — re-deliver the superseded generation's bytes (no generation pin in the request) — is precisely the second lifecycle the required_behavior forbids minting; "use existing job/export owner" is conditional and none exists, so the stateless reading is the only one satisfying all three clauses (immutable input refs = client-held canonical request + content-addressed receipt naming `dataset_generation_id`). Scenario 2 (entitlement lapsed between re-issues): re-issue → 401 with private headers, provider factory never called (`factory_calls == [1]` in `test_a54_reissue_without_auth_is_401_and_skips_provider`); entitlement restored → 200 byte-identical including headers (`test_a54_identical_csv/parquet_posts_are_byte_identical`). Fully satisfied. The design_ruling obligation is discharged by this ratification; the seat may close A54 by recording it.

**Guard**: would NOT catch adjacent/tautological evidence — `_test_exists` (tests/test_fif_z0_closure_matrix.py:23-31) checks only that the file exists and the name appears (regex `def name(` for .py; bare substring for .mjs); it never reads assertions, skips, or CI wiring.

EVIDENCE:
- pytest: `python3 -m pytest -q -p no:cacheprovider tests/test_fif_z0_closure_matrix.py` → **"4 passed in 0.62s"**
- `git -c gc.auto=0 diff --stat 69288ad8d58… BASE` → 5 files: `agentos/handoffs/FINANCIAL-INTELLIGENCE-FABRIC-2026-10-20-fif-z0-closure-wave.md` (+91), `agentos/workstreams/WS-FINANCIAL-INTELLIGENCE-FABRIC.md` (28 ±), `FIF_A36_COVERAGE_REMEASURE_2026-10-20.md` (+33), `FIF_A37_HELD_OUT_QUALIFIED_ABSTAIN_2026-10-20.md` (+76), `FIF_Z0_CLOSURE_MATRIX.json` (141 ±) — **5 files changed, 292 insertions(+), 77 deletions(-)** (records-only wave; no code delta).
- Matrix↔acceptance drift: none — all 54 condition/required_behavior/tasks identical to the pinned masterplan (44e3c09b).

NOTES (not F-rows): A37 obligation kind `implementation_gap` mislabels an external-labeler dependency; the matrix's masterplan `path` no longer exists in HEAD's tree (readable only at the pinned commit — the guard never checks it); A54's note carries an off-topic PR #9884 cov-wire sentence; A04's weakest cited test is classification-only; F5's fix (wiring `fif-kernel-guards` content into an enabled job) also cures A44's citations.

GAPS: cited tests were read, not executed (except the guard; the S1-qualification subset and A32 trio passed live; the A43 pair passed/skipped per sparse checkout) — HEAD greenness rests on static reading; CI-darkness verified by sample (4 .py + 2 .mjs of ~40 cited), not exhaustively; PR numbers/main SHAs in notes (#9863/#9869/#9870/#9871/#9879/#9882/#9884) not verified against origin (no network); A43 screenshots not viewed (binary; and no cited test adjudicates them visually either — that is F1).

DEVIATIONS: none — read-only throughout, no commit/edit/push/label/PR, `git -c gc.auto=0` on every git command; two subagents hit turn limits and were resumed solely to emit their final packets; one ran the two A43 test files as commissioned.
