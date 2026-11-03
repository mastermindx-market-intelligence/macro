# D02 verification and acceptance cases

## What was actually checked in Phase 2A

- Same-pin assignment/common/index/shell/checklist and protected procedure were read; current source/dependency pins are recorded.
- All 26 canonical assignment rows are accounted for. All25 exact document paths received beta read requests:23 HTTP200 shell/loading-only responses and2 observed404s. Browser interaction attempts failed at CDP; no populated beta, keyboard or modal proof is asserted.
- Three public-host responses were retrieved separately: Macro overview, Macro Command and Macro Context. Their response titles/copy are preserved; public www evidence does not qualify beta.
- Five exact assigned Paper pages were re-read:26 listed artboards. Nine representative screenshots were visually inspected and captured. Remaining variants are identity-censused, not all visually approved.
- All fourteen complete source workspace JSON snapshots had their documented canonical digest recomputed independently:14/14 matched. Required/closed top-level keys also matched14/14. This is an integrity/shape check, not full nested-schema, source-quality or model validation.
- Full existing Python JSON-schema validation was attempted but jsonschema was absent in both available Python runtimes. It was not executed successfully and no package/production change was made. [Exact scoped result](evidence/workspace-validation.json).
- The artifact-level consistency results are recorded in evidence/package-checks.json. The enclosing source commit and Draft PR #10646 identify publication; remote readback is reported on that carrier. Future product tests below have not been run.

## Future test matrix

These are discriminating acceptance requirements for later authorized implementation and real-host verification. Every row is **NOT_EXECUTED_FUTURE_ACCEPTANCE_CASE**. They are not unit tests added to production or evidence that a proposed UI exists. The [risk appendix](appendix/RISK_FED_CONTRACT_JUDGMENT.md) adds30 focused source-truth cases; overlapping cases refine the same obligations, not extra completed gates.

| ID / area | Fixture or action | Expected result | Responsible owner |
| --- | --- | --- | --- |
| SC01 — Assigned route set | Compare exact immutable D02 rows to candidate crosswalk | All 26 IDs retained; 25 documents plus qualified historical fragment family; no added public route | D02/F03 |
| SC02 — Internal access | Anonymous and entitled requests to crossasset and macro_signals | Both preserve existing internal404 boundary; no payload leakage or public-nav admission | Access owner/F01 |
| SC03 — Shared template | Render macro and stocks before/after scoped change | Macro behavior changes only as approved; D03 body.page-stocks and full S&P1500 board preserved | D02/D03 |
| SC04 — Existing Signals candidate | Compare intended evidence implementation with #10485 exact head and live writer | Reuse/reconcile existing owner; no parallel popup rewrite | D02/#10485 |
| SC05 — Fragment family | Run existing exporter over exact eleven fragments | Excluded as html_fragment; not standalone pages or synthesized redirects | F03 |
| SC06 — Fragment fetch | HTTP error, wrong content type, missing marker and timeout | Typed fallback/working deep workspace; no blank infinite loading or false zero | D02 |
| SC07 — Delayed fragment with subtab | Open #growth/business and #credit/funding before fetch resolves | Selected subtab and link bases survive insertion; same source/refusal as host | D02 |
| SC08 — No JavaScript | Open suite and Command with JS unavailable | Server-rendered answer/data and reachable deep links remain useful | D02/F01 |
| DA01 — Snapshot integrity | Alter a metric without updating digest; use wrong schema/version or extra top key | Fail closed; retain verified prior or typed failure; never certify current | Producer/D02 |
| DA02 — Manifest mismatch | Manifest generation differs from snapshot/fragment generation | No mixed new headline/old drivers; explicit incompatibility or compatible bundle | Producer/F01/D02 |
| DA03 — Same content new build | Only built_at/code_version changes | Content digest and analytical change remain stable under documented contract | Workspace owner |
| DA04 — Prior publication | Same-date rebuild then later publication | Compare against last strictly earlier publication; no double-counted daily change | Workspace owner |
| DA05 — Method change | Same metric ID with different method_version | No numerical delta unless explicitly comparable; preserve prior identity | Workspace owner |
| DA06 — Mixed cadence | Daily close on weekend plus weekly/monthly sources | Own dates/cadences preserved; weekend alone does not imply stale; build time never freshens source | D02/source owners |
| DA07 — True zero and false | Rate=0, p_up=0, return=0, false gate; separate null/NaN/missing | Each valid zero/false retained; absent values not defaulted to another source or50% | D02 |
| DA08 — Missing sort | Ascending and descending with negative, zero, positive and null values | Null last both directions; visible missing state; numeric order correct | D02 |
| DA09 — Unknown/future source time | Missing evidence timestamp or observation/publication/availability later than the permitted calculation cutoff; separately test legitimate future target dates | Unknown/mismatch for inadmissible evidence; legitimate future targets retained; never substitute today or truncate silently | D02/producer |
| DA10 — Rights/region | RIGHTS_BLOCKED or unsupported CN request to US suite | No hidden premium prefetch or US relabeling; truthful supported destination | Access owner/F01/D19 |
| DA11 — Coverage contradiction | coverage_ratio=1 with PARTIAL discovery; CURRENT plus contradiction | Both source meanings retained; ratio/current stamp cannot erase incompleteness/disagreement | D02 |
| DA12 — Series gaps | Null series point or changed universe/adjustment basis | Visible discontinuity/qualification; no fabricated interpolation or comparable-history claim | Producer/D02 |
| RK01 — Canonical confidence | Current0.22 and separate HMM posterior0.6774 | Heuristic agreement wording; no22% regime probability; quantities remain separate | D02 |
| RK02 — Regime confirmation | Raw differs from confirmed; pending0/7 vs actual non-null pending | Correct producer state; TRANSITIONING alone is not confirmation countdown | Regime owner/D02 |
| RK03 — Risk context cap | caution + ungated risk-off + gate false | Explain absent broad-tape confirmation; no all-clear or UI recalculation | RiskRadar/D02 |
| RK04 — Unavailable scare | raw100, reading_state UNAVAILABLE, display_score null | Unavailable in dashboard and Context; never100/current or calm0 | D02 |
| RK05 — Model estimate / reconstructed cell | 22% h21; state-only16%; matching n66/events16 interval4.99–45.45 | Conjunction estimate distinct; interval described as reconstructed observed-rate uncertainty, not predictive interval | RiskRadar/D02 |
| RK06 — Forward cohort | Four issued/zero graded, validation false, publication timing false | Evidence accruing; no validated/precision/publication badge | Model owner/D02 |
| RK07 — Changed model evidence | Old calibration cell with different config/surface/hash | Evidence unmatched; oldN not inherited; current estimate qualified/refused per producer | Model owner |
| RK08 — Different drawdown events | Path rises then falls but never5% below issue close | RiskRadar issue-close target and slow63-day peak-to-trough target may differ; labels explain | Model owner/D02 |
| RK09 — HMM history | Full-sample-smoothed retrospective sequence with future input | No claim it predicted historical turns; fit cutoff/description visible | HMM owner/D02 |
| RK10 — Pullback arithmetic | Current loss, worst loss, rebound, further loss and total-depth fixture | Consistent episode peak; further loss not added as an identical percent basis; range not path/floor | Model owner/D02 |
| RK11 — China forecast absent | Observed local drawdown with no qualified remaining-depth model | Observed facts retained, estimate unavailable; no US calibration transplant | D19/D02 |
| RK12 — Breadth fixture/universe | 128 highs67 lows and stated ratio; NYSE versus S&P1500 | 65.64 if that formula/window; otherwise explicit producer definition; no mixed denominator | Breadth owner/D02/D03 |
| FD01 — Level versus change | Path+58bp from current but20-session change−22.2bp | Can display both qualified meanings; no contradictory cut/hike shorthand | Rates owner/D15/D02 |
| FD02 — Basis refusal | not_comparable/reference_end mismatch plus legacy numeric gap | Gap/takeaway withheld in every visible/accessible branch; valid independent observations retained | Rates owner/D02 |
| FD03 — Incomplete board | board_generation.complete=false and d1_missing | Current stance refusal preserved; a legacy path cannot silently override it | Rates owner/D02 |
| FD04 — SEP alignment | Same current-year dot in policy and Fed details | Actual target date/dated row; not arbitrary6m versus12m placement | D15/D02 |
| FD05 — Rate index change | SOFR fallback where EFFR was expected | Visible basis change or refusal; no falsely unified curve | Rates owner |
| FD06 — Prediction-market price | Outcome price and settlement condition | Market-implied benchmark copy; no percentage-of-traders survey claim | D02 |
| UX01 — Primary journey | Regime→indicator history→sector/asset→exact company/chart→return | Identity, source cutoff, route/hash, scroll and focus preserved | D02/destination owners |
| UX02 — Risk journey | Risk alert→changed axis→partial/calibration evidence→D23 condition seam | Useful reading first; source-qualified condition; no fake save when service unavailable | D02/D23 |
| UX03 — Phone first fold | 320/390 with long EN/ZH labels and material caveat | Answer and path remain useful; metadata/gauge does not displace all time-series context | D02/F01-F02 |
| UX04 — Inspector return | Open from scrolled table; change detail/horizon; close | Return to original surviving trigger/scroll; else relevant heading with change explanation | F01-F02/D02 |
| UX05 — Overlay arbitration | Open risk evidence while global search/Brain layer exists | One active blocking layer under F01 policy; no nested unreachable modal or duplicated Brain | F01 |
| UX06 — Dock/overlay boundary | Resize with evidence open and expanded/compact rail | Same evidence identity; proper modal/nonmodal roles; no hidden focused duplicate | F01-F02 |
| UX07 — Keyboard/focus set | Tab/ShiftTab/Escape with buttons, links, inputs, selects and summaries | Complete reachable controls, visible focus and correct return; existing limited trap expanded if needed | F01-F02/D02 |
| UX08 — Deep anchor and history | Direct suite hidden-panel anchor; Command tab; browser Back/Forward | Reveal right panel; retain existing history semantics and sticky offset; no double scroll | D02/F01 |
| UX09 — Odds invalid ticker | Unknown ?t= plus valid fallback asset | Explicit substitution notice; no false requested-asset label | D02 |
| UX10 — Locale/navigation effects | ?lang=zh/en, theme/context switch, opening inspector | Follow approved local/persisted preference policy; no watchlist/portfolio/alert mutation | F01/D25/D23 |
| UX11 — Save acknowledgment | D23 pending then authoritative object readback | Saved only after confirmed identity; activation separate | D23 |
| UX12 — Uncertain save | Timeout/session expiry after submission; potential duplicate retry | Preserve original operation and reconcile before resend; do not assert definitive failure/success | D23 |
| UX13 — Laboratory definitions | Odds next-open returns; Anticipation5/42/189 windows; cycle FRAME | Exact definitions and evidence limitations visible; no universal probability styling | D02/model owners |
| UX14 — Queue empty versus failed | Impulse no_data/no_scored versus0 eligible; Radar fetch fail; Demand empty cohort | Distinct reason and recovery; empty output not market conclusion | D02 |
| AC01 — Zoom/reflow | 400% zoom and320CSS width with inspector open | Host permits zoom; page reflows; necessary2D overflow contained; close/actions reachable | F01-F02/D02 |
| AC02 — Target and contrast | Important mobile controls, light/dark, all states | 44px house target; actual WCAG24px/spacing assessment; measured contrast/focus/non-color cues | F02/QA01 |
| AC03 — Chart alternatives | Keyboard-only/screen reader on path, rates and cone | Same value/target/date/qualification in summary and data view; no hover-only warning | D02/F02 |
| AC04 — Reduced motion | Reduced-motion/forced-color settings | No decorative draw/pulse requirement; selected state/focus/meaning preserved | F02 |
| AC05 — Chinese financial semantics | Long labels; price direction versus health/risk/positioning | Signs/text/legends consistent; language does not invert unrelated semantics | F02/D02/D19 |
| PE01 — Real content widths | 320, 390, 768, 1024, 1280, 1440, 1600 plus fractional breakpoint edges | Measure actual shell content C and local chrome; dock only when released rule permits | F01-F02/D02 |
| PE02 — Lazy mounting | Initial overview then one selected Command section/inspector | No eager all-route/all-matrix/hidden-chart loads; no duplicate listeners/subscriptions | Builder |
| PE03 — Output integrity | Nonfatal builder exception returning0 | Missing/stale output detected by artifact/readback check; no successful-publication claim | Builder |
| PE04 — Performance | Accepted deployed release, mobile/desktop p75 | LCP≤2.5s, INP≤200ms, CLS≤0.1; actual measurements recorded separately | Release/QA01 |
| PE05 — Rollback | Introduce route, data-guard or modal regression in authorized staging | Revert same carrier to known-good compatible release; verify served identity and access | Release owner |

### Additional concrete control cases

| ID / area | Fixture or action | Expected result | Responsible owner |
| --- | --- | --- | --- |
| UX15 — Odds controls/export | Lookback5y/10y/20y/max, tolerance exact/±1/±2, conditions, factor template/min-N/sector and CSV | Preserve selected query; no silent relaxation; unavailable conditions disabled; CSV exports full matched set beyond table truncation | D02/Odds owner |
| UX16 — Contextual analyst | Command/suite section with mounted/unmounted/no-JS Brain | Exact localized section/workspace to incumbent singleton; actual chat.html fallback; no duplicate Brain | D02/F01/Brain owner |
| UX17 — Cycle controls/layers | Groups, focus chips/cards/lines/hash, zoom presets/reset, fullscreen chart plus full sheet, Escape | Group filter differs from focus; frame lacks measured line; one Escape closes only top active layer; preserve chart/selection/scroll | D02/F01/cycle owner |

All three remain NOT_EXECUTED_FUTURE_ACCEPTANCE_CASE. Total main packet cases:65.

## Acceptance state and review protocol

Phase 2A's source/retention/specification outcome can be assessed from this packet. The overall D02 production-design reference is not ready for reference approval: joint F01/F02 release, final editable compositions, actual host interaction/responsive proof and independent review remain open. Data-truth defects identified here require revision before affected claims can qualify.

Formal RIG projection is draft, with no admitted approval receipt. Native principal advisers supplied technical/UX judgment; they are not the independent closed-input first-pass product/taste review. Do not relabel those notes as approval.

For that later review, freeze exact before/after artifacts, task/capability manifest, Paper IDs and source digests. First-pass reviewers receive only job, production-before, proposed-after and capability/task manifest. Record findings before revealing rationale/constraints. Carry inherited conditions explicitly through RESOLVED_BY_CHANGE, CARRIED_BLOCK, OVERRIDDEN or SUPERSEDED with required evidence/authority. CARRIED_BLOCK cannot coexist with approved.

Qualify families individually. A successful laboratory or component specimen does not qualify Macro overview, every region or the whole programme. Reference approval, implemented code, deployed release and served production proof remain separate facts.

