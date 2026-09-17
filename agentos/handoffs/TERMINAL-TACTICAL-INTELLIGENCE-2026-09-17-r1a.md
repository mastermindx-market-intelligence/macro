---
workstream: WS:TERMINAL-TACTICAL-INTELLIGENCE
session: claude/terminal-tactical-r1-20260917-sol-004
model: sol
ended_because: ci_handoff
mission: >
  Advance the approved Terminal Tactical Intelligence program from data qualification into the first registered
  price-first experiment, preserve all negative/tiny-N outcomes, and select the next research frontier without
  promoting an unproven signal.
state_before: >
  D0 qualification existed on Terminal #601 and R1-A design existed on Macro #7270, but the 84-cell study had not
  been registered, implemented or run because earlier modification calls had returned no effect.
changed:
- path: data/trial_ledger.jsonl
  what: Added exactly 84 R1-A comparison cells to the existing entry_radar TrialLedger after prereg/config freeze; prior ledger prefix preserved.
- path: engine/entry_radar/tactical_research.py
  what: Added pure causal research primitives for segment geometry, frozen arm selection, ambiguous first-touch and censored fixed outcomes; no live emission or I/O.
- path: scripts/research/terminal_tactical_r1_study.py
  what: Added the offline exact-input consumer producing the 84-cell aggregate result with causal session/date handling.
- path: research/species/TTI_R1A_REPORT.md
  what: Published the aggregate R1-A result and no-promotion adjudication; raw licensed panel/outcome rows remain private.
- path: agentos/decisions/DEC-TERMINAL-TACTICAL-R1A-DISPOSITION.md
  what: Recorded no-promotion and the independent exhaustion/reclaim-versus-continuation continuation ruling.
verified:
- claim: The full R1-A grid was registered before outcomes without truncating the existing TrialLedger.
  command: 'Compare c621a35:data/trial_ledger.jsonl with 0109877:data/trial_ledger.jsonl and read research/species/tti_r1/REGISTRATION_RECEIPT.json.'
  result: '1674 -> 1758 lines; exactly 84 study rows; prefix_preserved=true; grid SHA256 86b9e84faec43882e4ccc0975b2193a2ee489e618cd13adcbe784ea7dab53b46.'
- claim: Canonical corrected-history execution is reproducible on the preserved inputs after causal repairs.
  command: 'Run scripts/research/terminal_tactical_r1_study.py on the D0 input directory/manifest and Terminal c0f36cb; compare run-002 and run-003 bytes.'
  result: 'Both runs: 2464 candidate rows, 1810 comparable rows, 58308 outcomes; feature panel, outcomes and result byte-identical; aggregate SHA256 5c75a38d3f5acc61ad5e79fcec2f26af37a6f62da0ed449c4b1533b5cc35ff0b.'
- claim: The tactical causal code and relevant owners pass the available sparse-worktree test slice.
  command: 'python3 -m pytest -q tests/test_tactical_research.py tests/test_tactical_research_cli.py tests/test_trial_ledger.py tests/test_entry_radar_events.py tests/test_entry_radar_w5_gates.py tests/test_entry_radar_w5_data.py'
  result: '265 passed, 2 skipped. Focused post-merge tactical subset separately returned 41 passed; compileall and git diff --check passed.'
- claim: No R1-A arm clears the program evidence bar.
  command: 'Read research/species/TTI_R1A_REPORT.md and tti_r1/RESULT.json at Macro #7270.'
  result: 'PERSISTENT N=12/10 dates with negative primary incremental delta; WEAKNESS_PERSISTENT N=1; WEAKNESS_RECLAIM primary delta near zero; PERSISTENT_OPEN_ACCEPT N=3/2 development dates. No promotion.'
unverified:
- claim: Macro #7270 is independently reviewed, hosted-CI accepted or merged.
  what_would_verify: 'Current-head independent review plus concluded applicable hosted checks and lawful merge evidence.'
- claim: The next exhaustion/reclaim species has a real edge.
  what_would_verify: 'A separate frozen R1-B preregistration, complete trial accounting, causal execution, negative controls and prospective/held-out evidence.'
- claim: Current live/finer-grain data is fit for production shadow scanning.
  what_would_verify: 'Existing #595 data-owner repair plus qualified finer-grain availability/freshness and real shadow-path proof.'
decisions:
- DEC:TERMINAL-TACTICAL-PRICE-FIRST-APPROVAL
- DEC:TERMINAL-TACTICAL-R1A-DISPOSITION
discoveries:
- DSC:TERMINAL-TACTICAL-R1A-EXTENDED-SESSION-RESULT
- DSC:TERMINAL-INTRADAY-REFRESH-FAILURE-MASKING
unresolved:
- Macro #7270 remains draft pending current-head review/CI; do not turn a research result into production authority.
- Terminal #595 repair and #601 independent release review remain separate existing-owner gates.
- Historical live knowledge-time, NBBO fill quality and INTC motivating-session reproduction remain unproven.
next_actions:
- 'Consume #7270 current-head review/CI; repair only exact findings and keep R1-A thresholds/results frozen.'
- 'After R1-A source acceptance, start a separate R1-B long-side exhaustion/reclaim-versus-continuation carrier from current main.'
- 'When #595/#601 move materially, consume their evidence without taking over their source carriers.'
do_not_redo:
- 'Do not rerun or retune the unchanged R1-A 84-cell grid as a new discovery search; canonical run-003 is preserved.'
- 'Do not promote PERSISTENT_OPEN_ACCEPT from 2 dates or infer a broad persistence failure from this one construction.'
- 'Do not rebuild D0, recensus unchanged input hashes, or retry the held live INTC operation through another carrier.'
- 'Do not make unfinished Executive a prerequisite for independent TTI research.'
danger_areas:
- 'Corrected-history bars are not historical knowledge-time receipts; a good retrospective cell is not a live fill proof.'
- 'The six-value chart projection discarded exact vendor VWAP/transaction-count fields; bar-VWAP proxy is not order-flow intent.'
- 'Run-001 numerical output happened to match later corrected runs on these bytes, but its causal defects were real and it remains rejected as proof.'
prs: [7270, 7262]
---

## §0 State — what is true right now
R1-A has a frozen registration, working causal research consumer and reproducible corrected-history result. The result is useful chiefly because it rejects promotion: strict persistence did not add primary short-horizon value and the only positive opening-acceptance cell is tiny and development-only.

## §1 What is LEFT — in order
Review and source-adjudicate #7270, then start R1-B as a new bounded carrier. Current-history repair and D0 release review continue on #595/#601 under their incumbent owners.

## §2 What will bite you
Do not turn same-date enrichment into causal treatment, corrected bars into historical live observability, or tiny-N opening acceptance into a calibrated probability. The next experiment must remain distinct from post-hoc R1-A threshold tuning.

## §3 What was decided and found
DEC:TERMINAL-TACTICAL-R1A-DISPOSITION records no promotion and the next independent experiment. DSC:TERMINAL-TACTICAL-R1A-EXTENDED-SESSION-RESULT records the exact dated result and falsifier.

## §4 Not in scope — do not adopt
No production scanner, new event/replay store, option expression, order routing, paid provider, threshold rescue, or live capital authority. Existing Radar, Setup Species, Evaluation, data-refresh and Terminal consumer owners remain controlling.
