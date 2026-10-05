---
key: OPTIONS-ALPHA-EXACT-OPTION-OUTCOME-RULER
question: >
  What exact executable-quote outcome may Options Alpha claim for an independently selected
  option expression, without substituting underlying returns, midpoint marks, benchmark-specific
  cohort semantics, or hindsight-selected contracts?
answer: >
  Register OA-3 v1 as a zero-authority, long-single-leg, one-contract H+60 quote-ruler.
  The exact contract must be selected by a separately governed immutable expression receipt
  before any outcome is observed. Entry eligibility begins at that expression's actual
  available_at clock, never the earlier source event, campaign formed_at, candidate decision,
  or a backdated trigger. Select the first valid firm OPRA ask for the exact standard-deliverable
  contract whose quote event falls in [entry_boundary, entry_boundary+60s]. The holding clock
  begins at that admitted entry quote event. The exit target is exactly 60 minutes later and
  uses the first valid firm OPRA bid whose quote event falls in [exit_target, exit_target+60s].
  Both observations must remain inside the same NYSE RTH session; same-day-expiry, adjusted
  deliverable, package, short-premium and non-standard-multiplier expressions are outside v1.
  Price one contract with multiplier 100 and the already-frozen same-basis research fee
  convention of $0.65 per side. Ask-in/bid-out is a conservative quote-ruler estimate, not a
  fill claim. Missing required quotes remain unavailable and stay in the denominator. No mid,
  last, EOD, intrinsic, Black-Scholes, neighboring strike, underlying return or later best print
  may substitute. Reuse the current exact-contract/firm-quote parsing and net-return mechanics
  from engine/options_nbbo_cohort.py by version/digest where possible, but do not reuse its
  MomoEdge benchmark cohort identity, benchmark digest, producer registry, 600-second live-capture
  availability fence, or comparison-session coverage semantics. Outcome retrieval may happen
  after maturity; its later source/computed clocks are recorded honestly. The existing
  episode/campaign outcome owner remains canonical; no second outcome ledger is created.
rationale: >
  OA-0 and the current Options recovery explicitly separate stock success from option success and
  require exact-option NBBO outcomes before option-return claims. Current
  options.signal_episode_outcome/v1 intentionally leaves the option leg unavailable with
  reason no_executable_nbbo_quote_path. The existing private prospective NBBO cohort already
  implements exact OCC validation, first firm ask/bid selection, retained source-response
  receipts and a one-contract ask-in/bid-out fee formula, but it is governed by a MomoEdge
  same-basis benchmark and can select from an immutable trigger boundary before event availability.
  Importing that cohort wholesale would backdate OA entry semantics and couple OA to a competitor
  benchmark. This ruling reuses only its generic quote mechanics and freezes a causal OA-specific
  decision-time ruler before any OA exact-option outcomes are inspected.
alternatives:
  - option: Reuse options_nbbo_cohort.py benchmark events and snapshots unchanged as OA-3.
    why_not: >
      Their cohort_rule_id, benchmark digest, producer/capture registries, session-coverage gates
      and trigger-boundary semantics belong to the frozen MomoEdge benchmark, not the OA candidate
      outcome population. Reuse of mechanics is lawful; reuse of benchmark identity is not.
  - option: Use the current option mark/midpoint or underlying H+60 outcome as option P&L.
    why_not: >
      Neither is an executable exact-contract ask-in/bid-out return. OA-0 explicitly forbids
      stock/midpoint substitution when exact option quotes are missing.
  - option: Evaluate every campaign contract and report the best one.
    why_not: >
      That is hindsight expression selection and would turn OA-3 into outcome audition. Contract
      selection must be frozen upstream before the return path is observed.
evidence:
  - "Parent carrier mastermind-terminal#599 / operation options-alpha-product-integration-20260917-sol-001."
  - "Current Chairman instruction: take over the parent and continue moving the project forward."
  - "Protected procedure Mastermind@ac6180d0ca9107daae54f9eea6bd4b8aef92d630, Skillpack 1.0.1/bootstrap1."
  - "Macro base 6ac3817e063ded1d5bc71662bff184151756d868."
  - "Packet K in research/options_estate/OPTIONS_INTELLIGENCE_INTEGRATION_AMENDMENT_2026-09-16/CONDITIONAL_CHILD_PACKETS.md."
  - "engine/options_nbbo_cohort.py blob b84426de82c9d55caa26e9dd95092460be6dda1b."
  - "research/momoedge/MOMOEDGE_COMPLETION_BENCHMARK_PREREG_2026-08-11.md blob fe340fa06e886cf395c863e4c7498fd483a7445f."
  - "engine/options_signal_episode.py blob c8bfdb823770821a9adfe26d76ebe2709b7139a4."
  - "OA architecture docs/superpowers/specs/2026-08-27-options-alpha-intelligence-recovery-design.md."
affects:
  - "WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY / OA-3"
  - "existing options episode/campaign outcome owner"
  - "engine/options_nbbo_cohort.py quote mechanics as a reusable implementation reference"
  - "future exact-expression selection receipt owner"
confidence: high
reversibility: costly
decided_by: ceo-sol
decided_at: 2026-09-19
authority: >
  Current Chairman instruction assigns active parent continuation to Sol. This records-only
  decision stays inside the existing Options Alpha architecture/statistical scope and grants
  no model fit, source acquisition, outcome write, merge, deployment, issue, sizing or trade authority.
---

## Scope and preservation

This decision registers the first OA-3 exact-option outcome ruler. It does not activate the
ruler, select an option, create an outcome row, or make an option-return claim.

It preserves:

- existing event/episode/campaign identities and the existing outcome owner;
- the distinction between underlying-plan return, option-contract return and allocation-weighted
  portfolio return;
- explicit unavailable/censored/invalid states and original denominators;
- the MomoEdge benchmark as its own independent same-basis cohort;
- zero authority for candidate/outcome records;
- separate package-economics registration after qualified package structure exists.

Detailed machine and human contracts are frozen in:

- `research/options_estate/OPTIONS_ALPHA_EXACT_OPTION_OUTCOME_PREREG_2026-09-19.md`
- `research/options_estate/options_alpha_exact_option_outcome_policy_v1.json`
- `contracts/options/options.alpha_exact_option_outcome_policy.v1.schema.json`

A later implementation must reuse the existing outcome owner and current lawful quote source.
No second ledger/store/publisher is authorized by this decision.
