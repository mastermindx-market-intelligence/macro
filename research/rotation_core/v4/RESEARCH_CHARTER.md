# Rotation and Pivot Research — charter for the Research Director

Principal: Prophet programme CEO. Written 2026-11-12 01:23Z. This replaces the v3 single-test plan.
The v3 header was never frozen and never run; it is withdrawn. Its breadth tests become hypothesis cards.

## 1. The question
Which observable combinations of market, sector, technical, macro and positioning factors give statistically
defensible information about (a) an upcoming sector or asset rotation and (b) a risk-on / risk-off pivot:
its probability, its timing, its size, and whether acting on it beats SPY, RSP (equal weight) and cash after
costs. Do not assume the signal exists. Not knife-catching: a call needs early evidence of the turn.
The Chairman's rulings bind: the modern regime (2020 onward) is the test bed; change in breadth matters more
than its level; history is reconstructed from historical data, point-in-time is not a precondition.

## 2. Why the plan changed
v2 and v3 spent the whole modern window on one pre-declared test, so nothing could be discovered in the
regime that matters, and my rulings went on ticker-level detail. The desk now discovers on modern data and
confirms on a block it has not touched.

## 3. Data governance (mine; nobody else changes it)
- **Discovery block D: 2020-01-02 to 2023-12-29.** Opens only when the file
  `/home/ubuntu2/tmp/rotation-core/v4/RELEASE_D.md` exists (I write it). Until then keep R42: no
  signal-against-forward-return number on 2020 onward.
- **Sealed block S: 2024-01-02 onward.** Features may be computed on S by code. Nobody joins any candidate
  signal to any forward return, hit rate or P&L on S, in any form, until I write a confirmation release.
  The Sector Intelligence CEO witnesses that read.
- **Before 2020:** secondary. Use it to check a finding does not reverse, never to select.
- **Trial ledger:** `v4/trials.jsonl`, append-only. One row per evaluated configuration, written BEFORE its
  result is read (id, card, features, label, model class, grid size, utc). Every report states the count.
  Selection is corrected for it (deflated Sharpe, probability of backtest overfitting, Holm on the final family).
- **Confirmation:** I freeze at most five candidates with declared statistic, sign and pass line. One read of S.
  Then the forward record carries them.
- **Prior looks:** the July 2026 "rotation time machine" reports and Prophet's own tuning touched 2024–2026.
  Sector Intelligence is running a census; any candidate close to one is disclosed with it.
- The French post-2019 files stay sealed. Raw vendor prices are never committed. No worker writes a release.

## 4. Workstreams (yours to staff and run)
- **W0 Panel, labels, features.** Finish the member price panel (the RC lead's R57 check and R58 share-class
  rule). Labels: forward relative return of each group at 3, 5, 10, 20 and 63 sessions; dated rotation events
  (leadership changes among groups); dated risk pivots (drawdown and volatility regime turns). Features:
  multi-timeframe relative strength and its velocity; breadth level and change (ours and Sector
  Intelligence's reconstruction); dispersion, correlation, volatility; credit, rates, liquidity and economic
  releases with their publication lag; positioning (options, futures) where we have access; the Risk Radar state.
- **W1 Ideation with ChatGPT Astra Pro.** Standing waves, five to six sessions at once. First wave:
  (1) research design and adversarial challenge of §3, including the D/S split and the multiple-testing plan;
  (2) regime and sector exhaustion; (3) reversal probability and timing (change-point, regime-switching,
  survival/hazard, calibrated learners against simple baselines); (4) confluence and interaction discovery
  with small samples; (5) macro, liquidity and positioning inputs and their real-time lags; (6) post-2020
  evidence on sector rotation and factor timing. Use Extra High (Sol 6) sessions for implementation plans and
  code reading. Every return is distilled into hypothesis cards: mechanism, exact features, label, expected
  sign, what refutes it, data needed.
- **W2 Baselines first.** 6- and 12-month momentum, 200-session trend, equal weight, SPY, RSP, cash. Every
  candidate reports against them.
- **W3 Model tracks, in parallel.** Hazard models for timing; regime and change-point models; calibrated
  boosted trees with monotone and interaction limits; a direct test of whether a combination beats its best
  single part. Purged, embargoed walk-forward inside D only.
- **W4 Independent falsification.** A separate lead on a different model family (gpt-6.1-sol) re-implements
  from the card and attacks every claimed finding: costs, lead time, false positives, calibration, tail
  losses, regimes, leakage. Nothing comes to me without its findings attached.

## 5. Staffing and routes
- You: Opus, orchestrate only. GLM 5.3 implementers; Deepseek for Pro operators and readers; Kimi as a
  second quant; gpt-6.1-sol for W4. Ask me for a Fable child only for one named, bounded design question.
- ChatGPT: Prophet uses the `chatgpt3` and `chatgpt4` profiles only. Start inside the "MastermindX"
  project, one-shot fill, send once, sends at least one minute apart, never resend after an uncertain send,
  stop and report on any limit or verification notice. The COO (operating deputy) owns making the route
  reliable and writes the operator runbook; use it, do not build another.
- The RC lead (Opus) now reports to you as panel lead. Its thread and the other ids are in §8.
- No spend, plan upgrade or paid credits without the Chairman. Vendor keys: paths only, never values.

## 6. What comes to me
1. The first hypothesis slate (one page, ranked, with what each costs to test). I approve it once.
2. Keep / kill at each milestone, with W4's findings.
3. The freeze list for the read of S.
4. Anything that touches S, spend, data rights or another team's custody.
One DIGEST per milestone, 15 lines at most. No routine status. State lives in `v4/STATE.md`.

## 7. First cycle
Pro wave 1 sent; panel, labels and baselines built (results on D only after RELEASE_D); slate v1 to me.

## 8. Pointers
- Workspace: `/home/ubuntu2/tmp/rotation-core/` (v3 drafts in `v3/`, vendor data under `data/`, memory of
  rulings R37–R58 in `v3/` and the lead's files). Macro checkout: `/home/ubuntu2/.t3/worktrees/Macro/rotation-core`.
- Never push to `fable/rotation-core-20261110` (permanent archive) or to pull request #11086.
- RC lead thread: `thread:delegated-task:command%3Amcp%3A66a7c19c-e0b7-4c19-8b77-338d8af5bb0c%3Adelegate-task%3A9bfadcdb-3cfe-4f0a-b258-a3c03bc8441f`
- Risk Radar leader (sibling, gpt-6.1-sol): `mcp:launch:e0c532a9d1ce00f71e4f0d5788cd1e4cb314ba7128039099fd56cdcce81d382f`
- COO thread: `thread:delegated-task:command%3Amcp%3A957e7c31-b086-4221-abbd-e5dcc233774a%3Adelegate-task%3Ae6a85b6d-2f6e-4bc7-9c84-d4068f4ee701`
- Environments: ubuntu2 `ed6c13bb-ffd8-42de-9874-a6d5254350e8`; m2studio `5f4cd5f0-e3df-407d-af02-1aa833637937`
  (its Terminal project `e93ac3f4-5a6b-41f1-9922-7cd236c45ed0`; a child there needs `target.projectId`).
- Pro prompts are published under Macro `research/rotation_core/pro_runs/`; returns are comments on Macro
  issue #11014 beginning `PRO-RUN`.
- Risk-intelligence limits that bind: no fused risk score in authority paths, no new risk-episode store, no
  Prophet rank mutation, no automatic exits. Model prose never sizes or executes trades.

## 3a. Amendments agreed with the Sector Intelligence CEO (2026-11-12 01:30Z) — these govern over §3 where they differ
- **Sealed-block eligibility is per candidate, decided by the prior-looks census.**
  (a) A candidate whose family was related to outcomes on any part of 2024 onward, or whose selection drew on
  the July 2026 mined list, is not eligible for a sealed-block confirmation. Its confirmation is the forward
  record from its freeze date; the stretch after 2026-07-02 is reported as a labelled short check, not a pass.
  Expect this to apply to breadth change on sector ETFs.
  (b) A candidate from an untouched family may use the sealed block for the one read. Its derivation from the
  discovery block alone is written down before the freeze.
  (c) Every sealed-block result states its touch status in the same sentence. A touched-family result is a
  "replication on a seen period", never a confirmation.
- **Discovery block start is not fixed at 2020.** If Sector Intelligence's reconstruction reaches earlier,
  those years join the discovery block, labelled with their basis. 2020–2023 remains the primary test bed.
- **Ledger records knowledge.** Each trial row also records whether its author (worker or model) had read the
  July rotation-time-machine reports. Do not point ideation prompts at those reports.
- **Handoff with Sector Intelligence is by committed artifact on Macro main with its basis sidecar**, plus a
  short thread message carrying only path and commit. State the basis in the same sentence as any result on
  their data (rule text: Macro `research/HISTORICAL_RECONSTRUCTION_PROTOCOL.md` once merged).
- **Sector Intelligence relates nothing to outcomes on any period.** It may enter candidate ideas into the
  trial ledger like any other author; the desk tests and counts them. Findings that should change what they
  display go to them as a file.
- **Before any confirmation read** the frozen candidate list, the trial-ledger hash and the census are
  committed on Macro; the Sector Intelligence CEO checks that, then witnesses.
- Sector Intelligence deputy (m2studio): `mcp:launch:713b5574fd4af9afb5a58b375c78e2f8b0eeae6c17c34b9ac70eeed31ecd59d6`.
