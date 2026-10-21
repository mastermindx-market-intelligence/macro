---
key: A-PATH-ONLY-REVIEW-COMMISSION-BUYS-DISCOVERY-NOT-JUDGMENT
claim: >
  Commissioning an adversarial review by naming the artifact's PATH turns it into a
  discovery task with a review attached, and a routed worker's turn budget (~24 turns)
  is consumed before any judgment is produced. Measured on one 1,129-line module: three
  commissions produced ONE verdict - two workers exhausted their budgets reading toward
  the artifact and returned no findings at all, one of them emitting three sentences all
  of the form "now I will read X". A truncated reviewer cannot be resumed, because
  SendMessage is unavailable in this session type, so a wasted commission is a wasted
  round, not a pause.
falsifier: >
  A review commissioned with the artifact named only by path that returns a receipted
  verdict with reproductions inside its turn budget. Equivalently: `ToolSearch
  select:SendMessage` resolving in an ordinary seat session, which would make a truncated
  reviewer resumable and reduce this from a lost round to a delay.
so_what: >
  Commission judgment-only. Paste the code excerpt, the measured probe output, and a
  numbered list of candidate defects INTO the prompt, and ask the worker to adjudicate
  those candidates and name anything it adds - spend the seat's turns on discovery, since
  the seat can run probes cheaply and its context survives. Say explicitly that a partial
  report carrying rulings beats a complete exploration carrying none. Then expect to run
  the decisive probes yourself and budget the seat's own time for them: on the artifact
  measured here the seat's probes found two of six blockers directly and the seventh
  outright. Do not spawn a third worker on an artifact where two have already truncated -
  that is the banned no-delta third attempt; change tactic and take the work.
kind: constraint
verified_at: 2026-09-26
verified_by: >
  GMI Industrials first vertical T04 (PR #8062, engine/fundamental_forensics/
  industrials_result_cash.py, 1,129 lines). Three `reviewer` (opus, ROUTE review,
  MODE READ_ONLY) commissions against head
  365c2666b88a8e0afdae5f294aef3f9553e44ea0: two stopped at the ~24-turn limit having
  returned no verdict - the surviving output of one was "Test suite: `48 passed`. Now the
  frozen plan's paired-remeasurement text, plus the big adversarial probe." - and the
  third, commissioned on receipt/test causality with the mechanism described inline,
  returned a complete receipted verdict (13 mutations, 8 survivors, all in one plane).
  Resume was probed and is unavailable: `ToolSearch select:SendMessage` returned "No
  matching deferred tools found". Adjudication record, including which findings came from
  the worker and which from the seat:
  research/industrials/first_vertical_program/reviews/OPUS_T04_REDTEAM_2026-09-26.md
  (PR #8070).
scope: [macro, agent-commissions, gmi-industrials]
confidence: verified
---

## Detail

The mechanism is ordinary and easy to miss when writing the commission. "Attack
`engine/<pkg>/<module>.py` against the frozen spec" reads like a complete instruction,
but the worker must first find the spec, read the module, read the suite, read the
helpers the suite imports, and only then form a hypothesis - and each of those is a turn
that produces no ruling. A 1,100-line module with a 800-line suite and a frozen plan in
another branch does not fit in the budget that remains. The commission that worked named
its plane narrowly (receipt construction and test causality) and carried the mechanism in
the prompt, so the worker's first turn was already adjudication.

Two adjacent traps sit next to this one and are worth naming in the same record, because
they turn a recoverable waste into an unrecoverable one:

- **Worktree isolation.** A seat that has entered a worktree isolates its already-running
  subagents too. A reviewer commissioned against an artifact in a *different* worktree
  then burns its budget on tooling refusals rather than on reading. Spawn before entering,
  or hand the worker a tested wrapper.
- **No resume.** With `SendMessage` absent, the only responses to a truncated worker are
  replace or take over. Replacing twice on the same artifact is the banned third identical
  attempt; taking over is what the execution-continuation law requires, and it is what
  actually closed this task.

The corollary for the seat's own accounting: the independent adversarial pass is the real
closure gate
(DSC:A-LANE-SELF-VERDICT-IS-NOT-A-CLOSURE-GATE), so a commission that returns nothing
does not merely cost tokens - it leaves the gate unmanned while a dependent task waits to
branch. Price the commission accordingly and write it to be cheap to answer.
