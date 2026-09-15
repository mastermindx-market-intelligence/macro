# Prophet: shared downside, entry-path value and decision-time qualification

Date: 2026-09-11 UTC. Author: Sol. Existing research operation:
`prophet-absolute-downside-research-20260910-sol-001`, Macro PR #7043.

**Disposition:** a research-design recommendation and finite qualification boundary,
not an activated strategy, new prediction service, completed data qualification,
new formal preregistration, or a claim of improved returns. The completed archive
pilot remains `NO_INCREMENTAL_SUPPORT` and its consumed test period remains consumed.

## 1. What advanced in this continuation

The retained closed-read regression is now an independently retrievable, five-file
capsule at commit `381dea6000f56bbc76446b27f4cd74b76319dcf4`, under
`research/grey_deer/closed_read_capsule/`. It preserves the original selector,
unapplied candidate, 28-case harness, proposed bilingual explanation and remaining
consumer work. The prior six research files are unchanged by that commit.

A non-author method-review request was delivered to the existing placement owner
on a new, child-specific Slack root. It concerns only the original six-file pilot
at `50a5bc1881aa29a51b2971cd241c0443f65e4d6c`. At the last full read there was no
receiver, PICKUP_ACK or START. Delivery is not review execution. GitHub comment
5628785855 contains the complete bounded review; the exact transport root and
current disposition belong in the accompanying Agent OS handoff.

The existing Cockpit owner received a finite adoption/custody request in issue
#6817/comment5628945643. That asks for a disposition from already-held evidence,
not a fresh current-source investigation or a competing writer. No acceptance,
source repair, deployment or browser improvement is inferred from sending it.

This continuation did not run another market-data experiment. The additional
arithmetic below uses the exact retained aggregate result, and the joint-loss
example is mathematical, not an estimate of Prophet probabilities.

## 2. The unit of the customer's problem is not only an individual stock

Twelve individually plausible entries can still fail together. A per-stock win
probability or a relative rank does not determine the probability that almost the
whole board loses at once.

A synthetic counterexample makes this precise. Consider twelve securities, each
with marginal loss probability 20%. If the losses were independent, the chance
that all twelve lose would be 0.2^12 = 0.000000004096. In a perfectly shared-loss
world, all twelve lose together with probability 20%. Both worlds have the same
individual loss probabilities and the same expected losing fraction. Their joint
tail risk is radically different. These are deliberately extreme illustrative
worlds, not fitted models or a claim about the actual screenshot.

**Research consequence:** preserve individual setup/entry evaluation, but also
measure shared downside on the actual frozen candidate population. Do not count
stocks exposed to the same market episode as independent demonstrations that a
market-warning model works. Keep market-wide and candidate-conditioned results
separate: a candidate board is a selected sample, not an unbiased breadth index.

A future research comparison should distinguish:

- the probability/distribution of broad absolute deterioration in a declared market
  universe;
- the joint adverse-path distribution within the actual candidate opportunity set;
- which candidate adds useful absolute entry value conditional on that environment;
- whether a permitted entry-deferral policy improves results after charging missed
  moves, later fills, costs and common exposure.

This is a measurement requirement for existing Grey Deer/Conditional Fusion and
Evaluation OS owners, not permission to create a fused buy-veto service. Portfolio
sizing remains with its owner; no automatic shorting, hedging or exit is proposed.

## 3. The retained experiment gives a concrete reason to grade the path

The exact original result JSON has SHA256
`2cde9ca7aa7166b952028e394ded55fed5ca9a7df690c4cd2e3453b0b464ebb9`.
Both pilot endpoints use the same 373 test observations and report no invalid
OHLC rows. With low <= close, a bar closing at least 1% below its open necessarily
also has a low at least 1% below its open. The reported counts are 30 terminal
loss events and 71 low-touch events. Therefore 41 of those 71 low-touch events,
57.75%, did not still meet the terminal-loss threshold at the close.

This is a derivation from the already-consumed report, not a second holdout look
used to choose a model. It does NOT establish that those 41 bars closed positive,
that a stop could execute at its stated price, that a target preceded a stop, or
that the bars describe regular-session auctions. The pilot's raw archive and
session/availability limits remain controlling.

**Decision implication:** endpoint return, downside along the path, and executable
trade payoff must remain different measurements. A single close-to-close label
cannot certify the user's ability to hold the recommended entry.

A useful future path model can represent mutually exclusive first outcomes:
objective first, invalidation first, and no first event before the owner-defined
expiry. An unexplained pair of independent probabilities that can sum above one
is not a coherent competing-outcome forecast. An ambiguous bar touching both
boundaries needs finer lawful evidence or an explicit interval/conservative
convention; it must not be forced into the more flattering outcome.

For a research-only discrete-time construction, conditional hazards for objective
and invalidation must sum to at most one at each step. Survival to step k is the
product of the preceding no-event probabilities; each cumulative first-event
probability sums its hazard weighted by survival. This elementary construction is
an option for the EXISTING multi-head research owner, not a new operational grader.
The existing outcome owner must settle censoring, expiry, price basis and fills
before a model consumes those labels.

## 4. Waiting is a policy to test, not a virtue to assume

The repository's August 12 Prophet evaluation specification already cites an
adverse result for entering at later confirmation ticks and explicitly preserves
`FRESH_TICKS=2`. The exact dated finding concerns that construction, not all forms
of conditional waiting. It is a strong reason not to turn this incident into
'add more confirmation everywhere.' [R1]

The next decision-level study should compare the SAME initial opportunities under
an unchanged incumbent policy and, if separately admitted, one precisely specified
conditional deferral. A waiting arm must include opportunities that never trigger.
Dropping those names and evaluating only eventual entries would select on future
information and conceal missed winners.

Use two clearly separated views of the outcome: a common opportunity-time horizon
that captures missed or delayed exposure, and the strategy owner's own post-entry
ruler. Do not silently compare a three-day-late entry over a fresh full horizon
against an earlier entry over a shorter remaining window. A price-taking historical
counterfactual must disclose its fill/impact assumptions; it is not a realized
customer trade.

Known no-entry under a fully observed policy may carry the declared cash/benchmark
return. An unobserved or invalid decision path is unavailable, not an invented zero.
New-entry permission is distinct from management of an already-held position.
Re-entry after deterioration must be charged for false starts and missed recovery,
not graded only on the losses it avoided.

The existing Prophet Arena and owner graders are the natural comparison homes,
subject to their actual current contracts. The August specification describes
prospective policy comparison on the same nightly artifact; that dated description
does not prove all required current fields or producers are installed today. [R1]

## 5. Source qualification: event time is not knowledge time

Official documentation now gives an exact source-method boundary. It is NOT a
qualification of the current Mastermind production route.

| Source | Documented clock/basis | What it does not establish |
|---|---|---|
| Final daily flat file | Finalization around 11 a.m. ET on the following day | Availability the prior evening or next pre-open. [S1] |
| REST custom aggregates | `t` is aggregate-window start in Unix milliseconds; `adjusted` means split adjustment | The observer's historical receipt time, dividend-total-return basis, or an executable auction fill. [S2] |
| WebSocket minute aggregates | `s`/`e` are window start/end in Unix milliseconds; eligible-trade bars span pre/regular/post sessions | First receipt, immutable finality, or confirmation that an absent minute is an outage. No eligible trades can mean no emitted bar. [S3] |
| Dated ticker reference | A date-filtered ticker listing and explicit active/inactive semantics are documented | First-captured history, historical index membership, or the past membership of today's curated AI cohort. [S4] |

A backtest cannot assign a 09:34 aggregate to a 09:35 decision simply because its
window ends before the decision: a version first received at 09:36 was unavailable
at 09:35. Later corrected bars must not rewrite the earlier information set. These
are logical admissibility rules, not observed current production defects.

For the next study, the existing owners need one qualified composition that binds:
security/identity epoch; candidate and generation; strategy and horizon; observation
window and session; provider availability where established; the system's actual
receipt; source revision and price basis; decision publication; and the first
permitted execution observation. Reuse existing identifiers and corrections.
Unknown clocks do not become the build time, and a newer wrapper does not refresh
an older input. Rights for one vendor/source do not qualify another feed.

**Current status:** the ordinary archive pilot did not establish this composition.
The later attempt to inspect the current live-source file/header/template metadata
was safety-refused. It has not been retried, subdivided, or delegated. This paper
therefore marks current runtime source qualification UNKNOWN. The table is an
external-method requirements analysis, not a new claim of actual route access.

## 6. Adaptive confidence: useful research, not a transferable guarantee

The retained pilot already showed that one fixed calibration mapping worsened its
later-period scores. That supports investigating reliability change; it does not
validate an adaptive replacement or identify the cause of every forecast error.

Three primary-source distinctions materially affect the design:

**Temporal reliability is not just whole-history average coverage.** Bhatnagar,
Wang, Xiong and Bai study strongly adaptive online conformal prediction, motivated
by failures hidden by full-horizon performance. Their prediction-set and regret
results depend on the paper's protocol and assumptions; they do not certify a
profitable trade, tomorrow's conditional crash probability, or an arbitrary risk
model. A trivial very-wide interval can cover outcomes while being useless. [S5]

**A trajectory guarantee has a sampling contract.** Zhou, Lindemann and Sesia's
CAFHT method studies simultaneous path coverage under exchangeable trajectories,
while allowing dependence within a trajectory. Its main setting adapts one-step
forecasts after observing prior trajectory values. A correlated set of stocks
from one selloff is not automatically an exchangeable sample of independent market
episodes, and adaptive path coverage is not the same promise as a single fixed
entry-time forecast. The paper also distinguishes marginal protection from
performance on harder subpopulations. [S6]

**Feedback arrives later than the forecast.** Hallberg Szabadvary's multi-step
online ACI work explicitly studies multiple forecast horizons. It motivates
separate horizon-specific updates; its published abstract is the reviewed source
here, not a reproduced method. A five-session result cannot update the calibrator
on day one. Faster observations may inform a detector, but cannot stand in for
an unmatured target. [S7]

Recommended research order: retain a frozen baseline; specify one delayed-feedback
adaptive comparator and its numerical bounds BEFORE new outcomes; evaluate both
probability error and the cost/informativeness of uncertainty; report crisis and
recovery windows as predeclared subperiods without discarding the full cohort.
No adaptive method may lower deterministic data/entry requirements or acquire live
rank, gate, size or execution authority without its existing promotion process.

## 7. Proposed next study: finite qualification before model execution

This is deliberately a qualification design, NOT a completed preregistration.
No new outcome has been inspected to select its thresholds or new model. Each
item below needs a concrete accepted existing-owner answer before a runnable
new policy study is admitted:

1. **Opportunity identity and source.** One existing, immutable candidate generation
   and its declared strategy/horizon, including withheld and unavailable cases.
   Historical board revisions must not be reconstructed from today's membership.
2. **As-known inputs.** At least one real, lawfully accessible decision-to-observation
   composition with receipt and correction semantics. Final archives alone are
   insufficient. A permission refusal remains a refusal, not a request to another
   account to retrieve the same object.
3. **Outcome and comparison contract.** The existing grader supplies fill convention,
   target/invalidation/expiry definitions, ambiguous-path treatment, censored states,
   benchmark/matched-control policy, and a common initial opportunity denominator.
   The historical Path Survival questions are a checklist, not answers or current
   proof that those gaps remain unresolved. [R2]
4. **Information timing.** Define the before-session decision and a separately graded
   intraday update, with realistic source delay and only matured calibration updates.
   Do not give an after-open detection credit for a prior-evening prediction.
5. **Frozen analysis and reporting.** Only after the first four are qualified, register
   exact dates, losses/utility, one challenger, costs, failure denominators, review
   checkpoints and sample requirements in the existing evaluation owner. The consumed
   2025-June2026 pilot test is not an untouched holdout for a retuned successor.

The finite preflight should return a qualified owner-issued packet or the single
highest-leverage missing field/source/permission with its owner. It must not keep
redesigning the whole company, create a duplicate store, or use a long-running
program as permission to cross an unresolved source boundary.

A first useful scientific comparison is not 'which large model wins?' It is whether
fresh, lawful participation/transition evidence changes the value of a defined
entry decision beyond simpler exposure and timing controls. More complex model
classes are considered only after that question has usable inputs and outcomes.
The existing Conditional Fusion framework already provides the home for earned
context-specific contribution; its early masterplan's historical champion statement
must not override later C1 adoption or current promotion rules. [R3]

## 8. Product acceptance and what the next session must do

The near-term product repair is truthful incomplete-read behavior, with real copy,
retained historical evidence and the proper source owner's production proof.
It need not wait for a successful prediction model, but it is not B4 completion.

The intelligence destination is broader: a user can discover a stock, understand
its market/sector exposure, distinguish a research thesis from a currently valid
entry, see what changed, and know what observable event would justify reconsidering
it. An exception such as a resilient stock must be identified from decision-time
features across held-out episodes, never added because it happened to win in the
motivating screenshot. Suppressed candidates remain visible and continue to be
graded under their original identities.

The machine-facing result must be the same owner-issued decision and evidence,
not a parallel LLM recommendation. LLM explanation can connect facts and conflicts;
it cannot invent numeric certainty or waive a deterministic blocker.

**Exact continuation:** consume the existing owner's disposition of the published
closed-read capsule, and adjudicate the bounded non-author pilot review when an
actual receiver returns. Until then, preserve WAITING_CAPACITY and the unapplied
repair. The next empirical model study stays behind the finite as-known-data and
outcome qualification above. No prior failed construction is silently promoted.

## Sources and scope

[R1] `research/MASTERMIND_PROPHET_EVAL_SPEC.md`, dated 2026-08-12; read at Macro
`43470274d542fdf0cfd59f77a938338f5778dea3`, blob
`1ad8dd54be4b32c3ab607917e2d6dab185a32fda`. Its old cohort counts are not current status.

[R2] `research/path_survival/F0_OPEN_QUESTIONS.md`, dated 2026-08-18; same Macro pin,
blob `d6c84f758aacb1291e77dcd6607ee4525bdab9a5`. Questions, not newly accepted law.

[R3] `research/PROPHET_CONDITIONAL_FUSION_MASTERPLAN_BY_FABLE.md`, dated 2026-08-14;
same Macro pin, blob `9f02020815cd51b6e4d9baa9d79ab3a1cf415cda`. Read relevant opening
architecture; later accepted decisions retain precedence. The proposed Evaluation
Standards at that pin were also read as methodological context, not unconditionally
promoted from their 'proposed policy' header to current law.

Primary external sources, read September11UTC; provider methods do not prove our
particular entitlement, installed route or historical receipt completeness:

[S1] https://massive.com/docs/flat-files/stocks/day-aggregates
[S2] https://massive.com/docs/rest/stocks/aggregates/custom-bars
[S3] https://massive.com/docs/websocket/stocks/aggregates-per-minute
[S4] https://massive.com/docs/rest/stocks/tickers/all-tickers
[S5] https://proceedings.mlr.press/v202/bhatnagar23a.html ; full paper reviewed at https://proceedings.mlr.press/v202/bhatnagar23a/bhatnagar23a.pdf
[S6] https://proceedings.mlr.press/v235/zhou24l.html ; full author paper reviewed at https://arxiv.org/pdf/2402.09623
[S7] https://proceedings.mlr.press/v230/hallberg-szabadvary24a.html

No raw licensed prices, credentials, private agreement or private host path is
contained here. This record modifies no market data, event owner, ranking,
permission, portfolio, source writer or production deployment.
