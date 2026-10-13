---
key: GRANULAR-REGIME-OUTLOOK-CONTRACT-V1
question: >
  What does the first Granular Regime Intelligence vertical publish, through which existing owner,
  and under what rules may a path reading or any later outcome study be made?
answer: >
  One additive projection, `regime_outlook`, inside the existing Rates & Inflation Command
  artifact, rendered as a section of `transmission.html` through the render-only path. It
  describes the current state family by family, what changed since the previous completed
  session, and nine overlapping path hypotheses. Each path is a short list of positive statements;
  each statement reads exactly one owner verdict through a versioned, display-tier table
  (`VERDICT_MAPPING_V1`) and yields `fits`, `does_not_fit`, `not_discriminating` or `unknown`. It
  publishes no probability, no cross-path count, rank or score, and no forecast. Any outcome study
  is a separate construction that must satisfy the contract's science rules and seen-history
  register before a new outcome is inspected. The contract is
  `research/macro_regime_intelligence/STATE_PATH_AND_SCIENCE_CONTRACT_2026-10-03.md`.
rationale: >
  The programme assignment (issue #8317) asks for a complete regime-intelligence system without a
  second regime engine, truth plane, history store or evaluator. Every state family already has
  an owner on main; what is missing is one honest composed description and a rule for what may be
  said from it. Three independent producer-code audits and three adversarial review rounds showed where a
  naive composition misleads: owner tokens that are the default for a missing input, verdicts that
  are a bare sign, snapshot dates presented as observation dates, and statement wording that
  silently counts an owner's middle state as agreement. The contract therefore admits owner
  tokens by class from producer code, guards every token a missing input can produce, fixes one
  row convention for the mapping, and keeps counts inside a single path's card. A descriptive
  vertical can ship on that basis now; predictive claims wait for qualified history and
  preregistration.
alternatives:
  - option: Build a new regime classifier that scores the paths and publishes a probability for each.
    why_not: >
      It would be a second regime engine beside Regime One and the Rates Command, and there is no
      point-in-time archive of the inputs on which to fit or test it. A hand-authored score would
      be a model with no evidence presented as one.
  - option: Publish a "supports / contradicts" tally per path and rank the paths by it.
    why_not: >
      Paths have different numbers and kinds of conditions, share evidence, and are not mutually
      exclusive, so a cross-path tally is a ranking with no meaning. The first review also showed
      a tally invites exactly the likelihood reading the surface must not give.
  - option: Wait for the historical qualification work (#7871, #8304, #8301) before shipping any surface.
    why_not: >
      The descriptive vertical needs no history beyond the previous session. Holding it would
      leave users without the composed current read while the slower data work runs; the
      contract instead separates the descriptive slices from the study slices.
  - option: Read every published owner token, including bare-sign trends and default tokens.
    why_not: >
      At the pin a missing core-PCE input reads `below target`, a missing change reads `stable`,
      and a zero change reads `falling`. Reading them would present absence as evidence.
evidence:
  - "macro issue #8317 — Chairman assignment and programme packet (workcards A–H)"
  - "macro PR #7088 — parent architecture and R1 implementation packet (head a6ccf23bfdee, unmerged)"
  - "macro research/macro_regime_intelligence/STATE_PATH_AND_SCIENCE_CONTRACT_2026-10-03.md — §15 (16 findings on revision 1), §16 (26 findings on Appendix A) and §17 (12 findings on the confirmation re-review), each with the change that answers it"
  - "producer rules at origin/main 5f20adbd6be6: engine/rate_inflation_transmission.py:223-261 and :356-388; engine/conditions.py:535-538, 622, 738-748, 973-974; engine/regime.py:183-202; engine/market_state.py:100-105, 317-321; engine/yield_momentum.py:159-182; engine/leadership_crack.py:319-323"
  - "config/dag.yml — build order of the cited artifacts before build_rates_command (nightly :1557, weekly :3262)"
affects:
  - WS:RATES-INFLATION-COMMAND
  - rates-inflation-command
  - engine/rates_inflation_command.py
  - engine/rate_inflation_transmission.py
  - engine/transmission_context.py
  - engine/neuralweb/market_packet.py
  - engine/neuralweb/world_state.py
  - templates/transmission.html.j2
  - research/macro_regime_intelligence/
confidence: medium
reversibility: easy
decided_by: "session 8fdb22b4-e16b-46d8-8948-ecfe95ec27fb (Fable programme lead, Chairman assignment in issue #8317)"
decided_at: 2026-10-03
---

## What is decided

The contract file is the working document for builders, reviewers and researchers. This record
fixes the choices in it that are expensive to revisit:

1. **One writer, one projection.** `regime_outlook` is a new key in the Rates & Inflation Command
   artifact. No new artifact, store, scheduler or reader family. Every existing field keeps its
   name, type and value.
2. **Readings are statements about wording.** `fits` means the owner's published token is the
   side the statement names. It is not a likelihood, a cause or a vote.
3. **Admission from producer code.** An owner token is read only if its class is banded or
   composite, and only when the numbers it was decided from are published beside it. Bare-sign
   verdicts, numbers without a token and prose are shown as evidence and read `unknown`.
4. **One row convention.** Positive statements only; the owner's middle token is
   `not_discriminating` in every row; rows that read the same field are identical or mirrors.
5. **No cross-path arithmetic.** Counts exist only inside one path's card, per evidence family.
   Families are groupings against double counting, not independent witnesses.
6. **The mapping is authored and says so.** It is display tier, versioned, never tested against
   outcomes, and changes only by a new version. Its one permitted look at the motivating episodes
   is a labelled hindsight coverage replay on four dates fixed in advance.
7. **Science before outcomes.** Any study that inspects an outcome is preregistered on
   `origin/main` first and appends to the seen-history register in the same pull request.

## What is not decided here

The repairs to the incumbent owners (slice E0), the page design (slice E2 needs a committed
mockup ratified by the operator), and every release decision on the held pull requests #8257,
#8301, #8304 and #8306. Those stay with their owners and gates.

## Reversal

Easy while nothing reads the projection. Once slice E1 ships, a change to the mapping is a new
mapping version reported in the projection's own change list; a change to the row convention or
the no-ranking rule needs a superseding decision record.
