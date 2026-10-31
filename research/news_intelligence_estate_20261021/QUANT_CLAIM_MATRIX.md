# Quant claim matrix — News Intelligence Estate (2026-10-31)

What can be claimed TODAY about the quantitative outcome of the News Intelligence Estate
(masterplan §11 and the Prophet News Impact benchmark), what cannot, and what evaluation
design the next step needs. Every number traces to a committed file at lane HEAD
`6135e2c3c64cd62258f176b234c6bb27960e3adb`, except the gated_v3 numbers, which are cited
to PR #10063 head `01f9e0a50f17879f5a13a5fe10eff14c52fb4cc2` (read-only `git show`, not on
this HEAD). No new measurement was made for this matrix.

Path shorthand: `P = research/prophet_v4/news_to_business_impact_20261006/benchmark`,
`E = research/news_intelligence_estate_20261021`, `R = P/results_w2`.

## Strict separation

600 registration cases / gated_v2 99 drawn of which 74 routed MATCH (scorable) /
gated_v3 135 drawn / 40 NEW cases routing-pending / 0 prospective. The 135 drawn are not
135 scored or gold cases. A shared group id does not transfer a label, a verdict or
independence across versions, assets, clocks or horizons. Cluster/group ids are never
evidence of independence.

## Population ladder

| Step | Count | Source |
|---|---|---|
| Commission target (registered population) | 600 cases, 200 per template | `P/README.md` line 4 (MASTERPLAN §11 / `package/MASTERPLAN.md` line 215); `R/summary.json` `population.target` = 600 |
| Tape funnel above it (context) | 55,110 tape rows → 2,837 candidates | `P/README.md` "Funnel" |
| Graded (two-family labeled) | 157 of 600 — T1 68 / T2 66 / T3 23; shortfall 443 | `R/README.md` "What the numbers cover"; `R/summary.json` `population` {graded 157, by_template, shortfall 443} |
| gated_v2 drawn | 99 (T1 49 / T2 46 / T3 4); folds f1 21, f2 19, f3 20, f4 21, f5 18, prospective 0 | `P/gated_v2/manifest.json` `cells`, `folds` |
| routed MATCH, scorable | 74 (T1 34 / T2 36 / T3 4); non-MATCH 15 NO_EVENT / 9 OTHER_EVENT / 1 WRONG_ISSUER; label queue 12; shortfall vs 600 = 526 | `R/audit/v2_routing.json` `scorable_match` (74 ids), `routing_map_class_counts`, `label_queue`, `shortfall_total`; `P/section11/registration.json` `populations.v2_match` |
| gated_v3 drawn (not on this HEAD; PR #10063 head `01f9e0a5`) | 135 (T1 71 / T2 53 / T3 11) = 95 shared with gated_v2 + 40 NEW + 4 dropped; folds f1 28, f2 27, f3 27, f4 28, f5 25, prospective 0 | `#10063 head 01f9e0a5 gated_v3/CENSUS.md` §5, §6; `gated_v3/manifest.json` `cells`, `folds` |
| Prospective | 0 in every committed manifest | `P/gated_v2/manifest.json` `folds.prospective` = 0; `#10063 gated_v3/manifest.json` `folds.prospective` = 0 |

Arrows, with the rule that governs each: 600 → 157 is the body-available frame (most tape
rows have no 8-K behind them; `P/README.md` "The graded population is 157 of 600");
157-graded ≠ scorable — the 99-case gated_v2 draw is a continuation population, not a
regrade (`P/README.md` "The 99 drawn cases are a continuation population, not a regrade");
99 → 74 is seat routing verdicts, only MATCH scores
(`DEC:NEWS-IMPACT-ROUTING-GATES-2-MISS-PATH`, `R/README.md` v2 continuation routing census
addendum); 74 = 62 already graded + 12 queue cases (`R/audit/v2_routing.json`);
gated_v2 → gated_v3 shares 95 case ids, and a shared id transfers nothing — "A case
already in gated_v2 keeps its routing verdict and grade. A case new to gated_v3 needs a
routing verdict from a census card before it scores, and only MATCH scores."
(`#10063 gated_v3/CENSUS.md` §6, rule quoted from `issuer_fallback/README.md`).

## Claim matrix

| # | Claim | Status | Evidence (path + key/line) | Number(s) |
|---|---|---|---|---|
| 1 | 74 gated_v2 cases are routed MATCH and scorable | CLAIMABLE | `R/audit/v2_routing.json` `scorable_match` (74 ids), `scorable_total` 74, `routing_map_class_counts` {MATCH 74, NO_EVENT 15, OTHER_EVENT 9, WRONG_ISSUER 1}; `P/section11/registration.json` `populations.v2_match.per_template.scorable_match` | 74 of 99 drawn; T1 34 / T2 36 / T3 4; shortfall vs 200/template 166/164/196 |
| 2 | Two-family extraction agreement rates exist for the 157 graded cases / 293 critical slots | CLAIMABLE | `R/summary.json` `critical_slot_taxonomy` (field ALL); per-field rows; `all_field_agreement_by_prompt_version` (12 rows, `agreed_rate` by prompt pair × template) | Critical slots: agreement 0.5768 (README quotes 0.577), Wilson 95% [0.5196, 0.632], n=293; classes agree_absent 129 / agree_present 40 / present_value_differs 57 / present_vs_absent 50 / malformed_value 11 / absent_reason_differs 6. Per field: T1 executed 0.618, T1 incremental 0.412, T1 remaining_auth 0.941, T2 stated_amount 0.364, T3 stated_quantity 0.478. All-field (every contract field) by prompt pair: `agreed_rate` 0.125–0.361, n 24–396 (e.g. v1.0/v1.0 capital-allocation 0.361, n 252; v1.1/v1.1 capital-allocation 0.338, n 396) |
| 3 | Agreement is a lower bound, not ground truth | CLAIMABLE | `R/README.md` "What the numbers cover" bullet 3: "Two families agreeing is a lower bound, not ground truth" | worse-family error ≥ 0.2116 of slots (stored 0.21160409556313994; `R/summary.json` `critical_slot_taxonomy[0].worse_family_error_lower_bound`) |
| 4 | 25 of 40 sampled cases are off-event — the labels measure extraction from the attached filing, not the headline's event | CLAIMABLE | `R/README.md` "What the numbers cover" bullet 5 and routing check addendum "Result" | 25/40 = 0.625 off-event, Wilson 95% [0.470, 0.758]; MATCH 15/40 = 0.375 [0.242, 0.530]; ≈59 of 157 on-event (38–83 at interval ends) |
| 5 | Third-family gold adjudication: every case deferred | CLAIMABLE | `R/README.md` "The third family is unavailable … with two families every case is deferred"; `R/summary.json` `case_status.routed_pending_third` = 157, `burst_defer.defer.deferred_cases` = 157, `auto_published_cases` = 0 | 157 of 157 deferred; 0 auto-published |
| 6 | Section-11 gate is REGISTERED; a measured system score against v2_match exists | Registration CLAIMABLE; system score NOT CLAIMABLE | Registered: `P/section11/registration.json` (`authority` = "context_only", `registration_version` ni-section11-registration-1, 919-line freeze) + `P/section11/README.md` + `engine/news_impact/section11_registration.py` docstring ("holds ids, enums, counts, seeds and sha256 pins only … never labeled values"). Score: `git ls-files` shows `P/section11/` contains exactly `README.md` and `registration.json` — no eval receipt, no system score, no section-11 measurement output anywhere in the tree | v2_match n=74, critical slots 142, label queue 12; committed system scores: 0 |
| 7 | gated_v3 is a registered draw with a RECONSTRUCTION-labelled calendar; 40 NEW cases routing-pending | Draw facts CLAIMABLE; the 40 census routing verdicts exist at this HEAD under `authority: context_only` (`B4_V3_NEW_CASE_ROUTING.md`: 31 MATCH / 4 NO_EVENT / 3 OTHER_EVENT / 2 WRONG_ISSUER) — not gold, not scored; labels/grades PENDING the section-11 process | `#10063 head 01f9e0a5 gated_v3/CENSUS.md` §1 (sessions.json "RECONSTRUCTED, not RECOVERED"), §6 (95/40/4), §10 ("routing verdicts PENDING the seat — no gated_v3 card builder exists at BASE"); `gated_v3/manifest.json` | 135 drawn (T1 71 / T2 53 / T3 11); shared 95 / NEW 40 / dropped 4; calendar sha256 `c029035d…`, exchange_calendars cross-check null |
| 8 | Prospective cases: 0 | CLAIMABLE | `P/gated_v2/manifest.json` `folds.prospective` = 0; `#10063 gated_v3/manifest.json` `folds.prospective` = 0; `P/section11/registration.json` `disclosures[0]` "no prospective case exists in v2_match" | 0 (both manifests); `t_prospective` 2026-10-15T00:00:00Z not yet passed into any draw |
| 9 | Any quantitative influence of news on a trading/ranking/sizing decision | NOT CLAIMABLE | `P/section11/registration.json` `authority` = "context_only"; `R/README.md` line 8 "Authority is `context_only`. Nothing here ranks, sizes or gates anything"; `E/MASTERPLAN.md` line 495 (Promotion): the ≥98% critical-numeric and ≥95% routing-recall figures "are proposed task thresholds to reconcile/freeze with the owner, not measured achievements of this audit" | none — no measured number exists |
| 10 | Sentiment / LLM confidence as trading authority | NOT CLAIMABLE (and forbidden) | `R/README.md` §4 Calibration: "`DNR:KILL-LLM-CONFIDENCE` forbids using it"; `P/section11/registration.json` `authority` context_only | none |
| 11 | Labeler critical-numeric correctness (audit-sample estimates, labels not system output) | CLAIMABLE (bounded: from the 40-slot audit sample only) | `R/eval_receipt_fam_a.json`, `R/eval_receipt_fam_b.json`; table in `R/README.md` "Eval receipts" | fam_a 0.667 (n=33, [0.50, 0.818]); fam_b 0.750 (n=32, [0.594, 0.895]); auto_published not evaluable (n=0; proposed bar 0.98 — a proposal, not a measurement) |
| 12 | Span replay integrity of the W2 labels | CLAIMABLE | `R/summary.json` `span_replay` | fam_a 1,515/1,515 spans, 157/157 cases; fam_b 1,451/1,451, 157/157; Wilson lower bound 0.997 each |
| 13 | v2_queue + graded join: two-family agreement on the 74-case scorable view | CLAIMABLE (as agreement, not accuracy; no queue case adjudicated) | `R/README.md` v2 label queue addendum "Scorable view"; `R/v2_queue/summary.json` | 74 cases / 142 slots at 0.535 ([0.453, 0.615]); T1 0.598 (102 slots), T2 0.361 (36), T3 0.5 (4); all 12 queue cases `routed_pending_third` |
| 14 | Routing-gate validation outcomes (efficiency filters, not on-event guarantees) | CLAIMABLE | `R/README.md` gates validation + gates-2 validation addenda; `R/audit/gate_validation.json`, `R/audit/gates2_validation.json` | gates-1 gated-in 32/40 MATCH (0.80, [0.652, 0.895]) — MISS vs bar 34; gates-2 gated-in 31/40 (0.775, [0.625, 0.877]) — MISS; gates-2 real-event drop share 0.208 ([0.074, 0.439]) — MISS; ruling: neither set accepted as an on-event guarantee |
| 15 | v2 census MATCH share (information only) | CLAIMABLE (information-only by its own label) | `R/audit/v2_routing.json` `census.class_counts`, `census.class_rate_wilson95` | census 30 cases: MATCH 17 / NO_EVENT 7 / OTHER_EVENT 5 / WRONG_ISSUER 1; MATCH share 0.567 [0.392, 0.726]; `information_only`: "gates-2 frozen, no revision" |
| 16 | Estate docs A1/A5/B1/D1 add further measured news-outcome quantities | NOT CLAIMABLE — none exist | `grep -i "wilson\|precision\|recall\|coverage"` over `E/*.md`: hits are delivery/telemetry/configuration statements only — `E/A5_TRANSPORT_OBSERVABILITY_GAPS.md` line 179 ("a telemetry-coverage claim, not a liveness claim"), `E/D1_NEWS_INPUT_TRACE.md` T2.3 (sizing output "DISPLAY-ONLY"), `E/A1_SOURCE_DELIVERY_MATRIX.md` item 12 ("Premium reporting coverage unproved"), `E/B1_SCHEMA_INVENTORY.md` (`published_precision` is a column name) | 0 measured outcome quantities outside the benchmark tree |

## What cannot be claimed today and why

1. **Any system performance for news_impact packets behind the section-11 gate** (row 6).
   The gate is registered (`P/section11/registration.json`), but `git ls-files` shows the
   section-11 tree holds only the README and the registration. No system run against
   v2_match, no eval receipt under the section-11 gate, no system score — nothing to
   report. The qwen system under test has not been measured on this population.
2. **Any accuracy, precision or recall of news extraction as ground truth** (rows 2, 3,
   13). The committed rates are two-family agreement rates. Where the families agree both
   can still be wrong; the only third-family checks are samples (40 slots, 26 absent
   slots, 11 malformed slots) and none covers the population.
3. **That the labels describe the headline's event** (row 4). 25 of 40 sampled cases do
   not pair a material event with a filing that reports it. Every figure measures
   extraction from the attached 8-K, nothing more.
4. **Any adjudicated gold** (row 5). Every one of the 157 graded cases — and all 12 queue
   cases — is `routed_pending_third`; the third family was unavailable in W2. Zero cases
   carry registered gold.
5. **Any gate as an on-event guarantee** (row 14). Both gate validations MISSED their
   pre-fixed bars; the committed ruling keeps them as efficiency filters with per-case
   routing verdicts.
6. **Anything about the 40 NEW gated_v3 cases beyond their existence** (row 7). Their
   census routing verdicts exist at this HEAD (`B4_V3_NEW_CASE_ROUTING.md`, `authority:
   context_only`); none has a label or grade, only a MATCH case may later enter the labeling
   queue through the section-11 process, and no card builder exists at BASE. The 135 drawn are not 135 scored or gold cases.
7. **Any prospective performance** (row 8). Prospective count is 0 everywhere;
   `t_prospective` 2026-10-15 has produced no prospective case in any committed draw.
8. **Any quantitative news influence on trading/ranking/sizing, and any threshold as
   achieved** (rows 9, 10). Authority is `context_only` in every committed instrument;
   the ≥98% / ≥95% figures in the masterplan are explicitly labelled proposed thresholds,
   not measured achievements. Sentiment/LLM confidence as authority is forbidden
   (`DNR:KILL-LLM-CONFIDENCE`).

## Evaluation design the next step needs

Strictly from committed design — no threshold is invented here:

- **Run the section-11 registration as registered** (`P/section11/registration.json`,
  `P/section11/README.md`): GLM (`glm-5.3`, prompt-v1.2, task extract) drafts **every
  critical slot of every v2_match case** (`gold.glm.scope`); MiniMax-M3 gold reuses the
  accepted W2 fam_a drafts for the 62 non-queue cases and the W2Q fam_a drafts for the 12
  queue cases (`gold.minimax`), with a fresh MiniMax draft per gated_v3 MATCH case when
  that population arrives. 142 critical slots over 74 cases.
- **Third family only on MiniMax/GLM disagreement, in registered rank order**:
  deepseek-v4.1-flash via go, then deepseek-v4-flash-0731 via bailian; qwen, MiniMax,
  GLM and MiMo excluded; a slot with no third value is null_printed and counted
  (`third_family`); residual disputes go to seat adjudication under
  `adjudication_record.v1`.
- **Audit draws before any system score is read**: gold-agreed audit seed 20261022,
  size 40, strata template-agreement_kind, drawn once both gold families have returned
  (`draws.gold_agreed_audit`); frontier-only audit subset already frozen at 13 of 74
  cases, seed 20261021, never widened (`draws.frontier_only_audit`).
- **System under test stays disjoint from gold**: the qwen family
  (`cheap_extractor_no_frontier` = qwen3.7-plus on prompt-v1.2; `proposed_cascade` adds
  qwen3.8-max only on deferred/quarantined/classify_event-disagreement cases, within the
  registered slot caps); W2 fam_b returns are labels and are never reused as system
  output (`system_under_test`, `gold.vendor_disjoint`).
- **The 40 NEW gated_v3 cases enter only through routing verdicts then the labeling
  queue** — census cards first, only MATCH scores, reported as its own table separate
  from v2_match (`#10063 gated_v3/CENSUS.md` §6, §10; `P/section11/registration.json`
  `populations.gated_v3`). Before that run, the RECONSTRUCTED calendar and the missing
  card builder are the two named gaps.
- **Prospective cases only after `t_prospective` 2026-10-15T00:00:00Z, with no redraw**
  of the historical folds (`a3_registration.t_prospective`; both manifests show
  prospective 0 and `plan.prospective_from` null).
- **What a POSITIVE_BOUNDED claim would minimally require**: a committed system score
  against v2_match under the registered gate with the registered gold — i.e. a section-11
  eval receipt for the system under test on the 74 MATCH cases / 142 critical slots,
  reported with its bootstrap interval (9,999 reps, seed 20261012, coverage 0.95), its
  per-template N and shortfall_vs_200, its null_printed/deferred counts, and the
  gold-error-rate context from the seat audits plus the gold-agreed draw. Any promotion
  reading waits for the owner's threshold reconciliation; none is asserted here.

## Verdict

QUANT CLAIM VERDICT: DEFENSIBLE_NEGATIVE

- `P/section11/` at HEAD contains exactly `README.md` + `registration.json` (`git ls-files`): 0 committed system scores against v2_match under the registered gate.
- `R/summary.json` `critical_slot_taxonomy[0]`: two-family agreement 0.5768 (n=293 slots) — a lower bound, not accuracy (`R/README.md` "What the numbers cover").
- `R/README.md` routing check: 25/40 = 0.625 off-event, Wilson 95% [0.470, 0.758] — labels measure extraction from the attached filing only.
- `R/summary.json` `case_status.routed_pending_third` = 157 of 157 deferred, 0 auto-published — no adjudicated gold exists.
- `R/audit/v2_routing.json` `scorable_total` = 74 (T1 34/T2 36/T3 4), `shortfall_total` = 526 — the scorable population, nothing scored on it.
- `#10063 head 01f9e0a5 gated_v3/CENSUS.md` §6/§10: 40 NEW cases routing-PENDING; the 135 drawn are not 135 scored or gold cases.

## Evidence

Commands run at lane HEAD `6135e2c3c64cd62258f176b234c6bb27960e3adb`, branch
`lane/news-orch3-claim-r1`, clean tree (all STEP 0 assertions OK; scratch
`~/lanes/tmp/news-orch3-claim-r1/b4`):

- `git rev-parse HEAD` → `6135e2c3c64cd62258f176b234c6bb27960e3adb`; `git status --porcelain` → empty; `git branch --show-current` → `lane/news-orch3-claim-r1`.
- Read: `P/README.md`; `P/section11/README.md`; `P/section11/registration.json`; `R/README.md`; `R/summary.json`; `R/audit/v2_routing.json`; `P/gated_v2/manifest.json`; `engine/news_impact/section11_registration.py` (docstring, lines 1-21).
- `python3` JSON key reads on `R/audit/v2_routing.json` (`census.class_counts` = {MATCH 17, NO_EVENT 7, OTHER_EVENT 5, WRONG_ISSUER 1}; `scorable_match` len 74; `scorable_total` 74; `routing_map_class_counts` = {MATCH 74, NO_EVENT 15, OTHER_EVENT 9, WRONG_ISSUER 1}; `label_queue` len 12; `shortfall_total` 526) and on `P/gated_v2/manifest.json` (cells sum 99; folds f1 21/f2 19/f3 20/f4 21/f5 18/prospective 0).
- `grep -n "B4" E/MASTERPLAN.md` → lines 83, 164, 295, 349, 424, 548; `grep -n "74 MATCH"` → line 160; `grep -n "526"` → lines 160, 531, 542; `grep -n "Promotion"` / `"≥98%"` / `"≥95%"` → all line 495 (single Promotion paragraph: "proposed task thresholds … not measured achievements").
- `git ls-files P/section11 research/prophet_v4/news_to_business_impact_20261006 | grep -i -E 'eval_receipt|section11|score|result'` → 47 files; the only `section11/` entries are `README.md` and `registration.json`; every `eval_receipt`/`score`/`result` hit lives under `results_w2/` (W2 labeler receipts) or is the `phase1_designs/A3_eval/eval_receipt.v1.schema.json` schema. No section-11 measurement output is committed.
- `git fetch origin 01f9e0a50f17879f5a13a5fe10eff14c52fb4cc2`; `git rev-parse FETCH_HEAD` → `01f9e0a50f17879f5a13a5fe10eff14c52fb4cc2`; `git show FETCH_HEAD:P/gated_v3/CENSUS.md` and `:P/gated_v3/manifest.json` → `~/lanes/tmp/news-orch3-claim-r1/b4/` (read-only; 135 drawn T1 71/T2 53/T3 11; folds f1 28/f2 27/f3 27/f4 28/f5 25/prospective 0; §6 95 shared/40 NEW/4 dropped; §10 routing PENDING).
- `ls E/` → A1, A5, B1, D1, MASTERPLAN; `grep -l -i -E "wilson|precision|recall|coverage" E/*.md` → all five; `grep -n` per doc → no measured news-outcome quantity (telemetry/configuration/display-tier statements only; D1 T2.3 sizing DISPLAY-ONLY; A1 item 12 premium coverage unproved).
