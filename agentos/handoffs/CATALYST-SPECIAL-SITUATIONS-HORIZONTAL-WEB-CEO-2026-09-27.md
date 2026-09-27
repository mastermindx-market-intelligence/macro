---
workstream: "WS:MARKET-OS"
session: sol/special-situations-horizontal-catalyst-r2-20260927
model: sol
ended_because: ci_handoff
mission: >
  Recover and advance the existing Special Situations system as a horizontal Catalyst Intelligence input:
  audit current source and consumers, perform primary research, identify a real transaction-to-affected-security
  failure, freeze transaction/relationship/lifecycle/economic semantics, provide executable reference tests and
  dependency-ordered implementation slices, and preserve a self-contained Codex continuation without changing
  production recommendation authority or creating a replacement event/identity/lifecycle/publication plane.
state_before: >
  Macro main had a mature Special Situations collector/classifier/render path, historical validation work, an
  existing context handshake into Alt-Data and an old Draft F09 cash-deal repair. The web commission itself was
  only a source packet. Current lifecycle still grouped by issuer/category with issuer-wide terminal signals,
  mastermind_emit kept only the newest event per ticker, cross-source merge used ticker/category rather than
  transaction identity, partial EFTS enrichment could drop a discovered 8-K, and the user-facing page remained
  technical-setup-first. No current horizontal Catalyst research packet or real event-to-affected-security
  regression existed on current Macro main.
changed:
  - path: research/SPECIAL_SITUATIONS_HORIZONTAL_CATALYST_R2_2026-09-27.md
    what: >
      Added current-source R2 research/architecture, primary-source MGLD/USCF vertical, event-family economics,
      transaction/affected-security/source-origin rulings, evaluation contract, product direction and separate
      research/forecast/production readiness boundaries.
  - path: research/SPECIAL_SITUATIONS_HORIZONTAL_CATALYST_IMPLEMENTATION_PLAN_2026-09-27.md
    what: >
      Added dependency-ordered RED-to-GREEN implementation slices for relation identity, transaction lifecycle,
      partial-enrichment coverage, multi-event security projection, Alt-Data deduplication, economic invalidation,
      F09 reconciliation, evaluation and eventual native Paper/product work.
  - path: research/special_situations_horizontal_reference.py
    what: >
      Added pure research-only reference semantics for direct versus indirectly affected securities, one
      source-origin transaction, transaction-scoped lifecycle, discovery/enrichment unknowns and scoped case
      invalidation. It performs no IO, scoring, ranking, publication or production action.
  - path: tests/test_special_situations_horizontal_reference.py
    what: >
      Added six reference-contract tests covering the MGLD/USCF relation, source-origin deduplication, unrelated
      deal closure, partial enrichment, observed negative enrichment and dependency-scoped invalidation.
  - path: agentos/handoffs/CATALYST-SPECIAL-SITUATIONS-HORIZONTAL-WEB-CEO-2026-09-27.md
    what: >
      Added this self-contained continuation with exact protected/source pins, real-path evidence, Paper block,
      DO_NOT_REDO boundaries and the next Codex Astra CEO actions.
prs: []
verified:
  - claim: "The branch was created from current Macro main and contained exactly five additive files before this schema-format repair."
    command: >
      GitHub compare base 170456b0013bf833a952498daf6a44a2153d70c6 against
      sol/special-situations-horizontal-catalyst-r2-20260927, then GitHub immutable file readback.
    result: >
      status ahead, ahead_by 5, behind_by 0; five added paths only. Readback blobs were research
      81d933f38f334bd412e49b597e948ebe17deb9a7, implementation plan
      208981ba25ecc834c9c12676102d3ffd65240a14, reference
      6d78c2ec1acdf7753c5944954bfd0a604fe6829e and pre-repair handoff
      5a2d716d1fc44c3494c8dd11bece04a5d56a3c48.
  - claim: "The research-only horizontal reference passes its exact repository-style test import."
    command: >
      In an isolated archive of the branch: python3 -m unittest -v
      tests/test_special_situations_horizontal_reference.py
    result: "6 tests passed, 0 failures."
  - claim: "The reference tests were RED before the reference implementation existed."
    command: >
      In a clean research scratch directory, run python3 -m unittest -v
      test_special_situations_horizontal_reference.py before creating
      special_situations_horizontal_reference.py.
    result: >
      ImportError / ModuleNotFoundError for special_situations_horizontal_reference; RED receipt SHA256
      44c7c1c516e4d357ce187a4b1c105c6aee3e22bfaae5d7ec7ad6ee53536d2d4c.
  - claim: "The first Agent OS validation attempt correctly rejected this handoff before this repair."
    command: >
      Fetch the branch, archive agentos + scripts/agentos.py + the reference/test files, then run
      python3 scripts/agentos.py validate.
    result: >
      Exit 1 with exactly one error attributable to this new handoff: no YAML frontmatter block.
      The same run reported 1305 records and 739 warnings; the warnings were not attributed as new
      errors. This commit repairs that exact schema defect and requires a fresh validation before acceptance.
  - claim: "The first real horizontal specimen is one TMC/MGLD take-private with multiple USCF funds affected through the control/general-partner chain."
    command: >
      Primary SEC reads of USL accession 0002071876-26-000222 and UGA accession
      0002071876-26-000220, plus bounded M2 reads of data/special_situations/events.parquet,
      classify_cache, site/allocationdata/special_situations.json,
      data/special_situations/context/latest.json and data/altdata/by_ticker.json.
    result: >
      SEC source says TMC entered the all-cash transaction and would become private/delist; TMC owns
      USCF Investments, which owns the relevant GP/sponsor chain. M2 projections independently tagged
      UNL, USL, BNO, CPER, UGA, UNG and USO as Going-Private and each received a special_situation
      Alt-Data channel at 0.20. The research ruling preserves the affected relationship but refuses to
      treat the funds as direct take-private targets or seven independent confirmations.
  - claim: "The repaired handoff and reference tests validate together on the exact remote branch archive."
    command: >
      git fetch origin sol/special-situations-horizontal-catalyst-r2-20260927; git archive FETCH_HEAD
      agentos scripts/agentos.py research/special_situations_horizontal_reference.py
      tests/test_special_situations_horizontal_reference.py; then run python3 -m unittest -v
      tests/test_special_situations_horizontal_reference.py and python3 scripts/agentos.py validate.
    result: >
      Reference tests: 6 passed, 0 failed. Agent OS: 1306 records (75 workstreams, 368 decisions,
      339 discoveries, 524 handoffs), 0 errors, 739 warnings; process exit 0. The warnings are the
      validator's existing warning census, not errors introduced by this handoff.
unverified:
  - claim: "The current canonical Company/Event/GMI owner can already express the exact controller/general-partner affected relationship required by the MGLD/USCF vertical."
    what_would_verify: >
      Fresh-read the owner-native event/entity/relationship interface at implementation head and obtain one
      canonical MGLD event receipt plus accepted typed relations to USCF Investments, United States Commodity
      Funds LLC and representative fund securities. A missing search hit is not absence proof.
  - claim: "The R2 semantics have passed a production Special Situations regression suite and real served user journey."
    what_would_verify: >
      Implement the admitted slices RED-first on a current branch, run the exact Special Situations/Alt-Data/
      brain/Catalyst consumer suites, then build and browser-verify the served route with real projection data.
  - claim: "The local design reference is visually accepted or native in Paper."
    what_would_verify: >
      Restore the guarded Paper runtime with an accepted catalog/write schema, reserve the actual lane artboard
      under the existing design owner, apply the design, then inspect desktop/mobile dark/light screenshots and
      cold-reader behavior. Local static HTML is supporting evidence only.
  - claim: "Any new event-family probability or investment ranking is qualified for live use."
    what_would_verify: >
      Point-in-time prospective shadow evidence under the incumbent evaluation owner, family/role/stage
      calibration, after-cost outcome analysis, independent method review and separate recommendation/publication
      admission. Current holds remain.
unresolved:
  - "Which existing owner-native relationship interface should carry controller/general-partner impact if the current Company/Event/GMI projection cannot express it without extension."
  - "How the old Draft #6793 source-bound F09 cash-deal work should be selectively reconciled against current main; wholesale branch revival is ruled out."
  - "Exact fund-level economic consequences of the MGLD transaction: change-of-control consent, adviser/GP continuity, fee structure, product support and strategy changes require owner-bound evidence."
  - "Native Paper write admission: server 0.5.12 was observed but catalog 8cd27488a3adfc19c6c36d4349b75feebc71c159253c47f8a0f8d50c27043deb was not accepted against expected ca90a537ee97f3e371ac945a8a3b9a928ba7fac9ffaeb67e31491075a0790570; a later catalog call returned UPSTREAM_UNAVAILABLE with retry disallowed."
next_actions:
  - "Fresh-read current protected procedure and Macro head, then reconcile active owners/branches before any implementation write."
  - "Run python3 scripts/agentos.py validate on this repaired handoff; do not open/claim a clean PR until it returns 0 errors attributable to this branch."
  - "Start the admitted MGLD/USCF RED regression under the existing event/entity owner: direct target MGLD, indirect affected funds, one source-origin transaction and no copied merger-arb economics."
  - "Resolve or minimally extend the incumbent relationship projection, then implement transaction-specific lifecycle before changing downstream ranking or UI."
  - "Trace the corrected projection through Special Situations context, Alt-Data, Company/Catalyst read models and recommendation review; invalidate only dependent investment cases and preserve prior snapshots."
  - "Revisit native Paper only after a relevant runtime/catalog change or an existing owner returns admission; do not retry the unchanged no-retry state or switch carrier to bypass it."
do_not_redo:
  - "Do not recreate Special Situations, rerun its generic competitor census or blindly replay SPECIAL_SITUATIONS_ROADMAP_V2."
  - "Do not create another event store, identity map, lifecycle service, queue, publication path, ranker or generic Catalyst score."
  - "Do not revive PR #6793 wholesale or create a third premium/spread producer; reconcile bounded source-bound semantics through its incumbent owner."
  - "Do not treat USO/USL/UNG/UGA/BNO/CPER/UNL as direct MGLD take-private targets, and do not multiply their repeated upstream disclosure into independent conviction."
  - "Do not infer fund-level value, fees, adviser continuity or shareholder-right changes solely from the parent transaction; unresolved economics stay unavailable."
  - "Do not coerce a missing probability/return/identity/enrichment field to zero or a negative finding."
  - "Do not mutate Paper through Desktop Commander/RDC or another host to evade the guarded catalog refusal."
  - "Do not call the local HTML prototype native Paper, visual acceptance, live recommendation or served product proof."
danger_areas:
  - "Current lifecycle terminalizes at issuer/category granularity, so an unrelated Item 2.01, Form 15 or Deal Termination can contaminate another transaction."
  - "Current mastermind_emit latest-per-ticker behavior can erase simultaneous material events."
  - "Current snapshot ticker/category merge can call related evidence confirmation without proving transaction identity."
  - "The current technical setup score/grade/tier language can look like investment authority even while the artifact says context-only; the redesign must separate technical state, event state, research maturity and accepted recommendation."
  - "Repeated registrant filings are valuable affected-coverage evidence but highly correlated; counting them as independent alpha evidence creates false certainty."
  - "Source time, first-known time, effective date, analysis cutoff and market-price time are different clocks; historical evaluation fails if they are collapsed."
---

# CATALYST — Special Situations Horizontal Integration — Web CEO R2

## Exact source and scope

Protected Mastermind procedure was read at
`429bf720788f8c68e76a576b7b3fedd8f8ad423a`, with INDEX blob
`94d1af402598894372858793a5b1931019c5fa77` and compatible Skillpack 1.0.1/bootstrap 1.
The research branch began from Macro main `170456b0013bf833a952498daf6a44a2153d70c6`.

This is the existing Special Situations horizontal lane under `WS:MARKET-OS`. It does not create a
new workstream or replace the shared Catalyst owners.

## First real vertical

The key real-path specimen is the September 25, 2026 Marygold / Madison Dearborn take-private.
USCF fund filings explicitly say TMC is the party becoming private and that the fund is affected through
USCF's ownership/general-partner chain. Current local generated artifacts nonetheless project at least
UNL, USL, BNO, CPER, UGA, UNG and USO as separate Going-Private rows and give each a
`special_situation` Alt-Data channel.

The frozen semantic correction is: **one canonical transaction, one direct target, many typed affected
relationships, one source-origin independence group**. The affected fund evidence remains useful and
visible; target merger-arb economics do not migrate to the funds.

## Architecture

The required path is:

```
source change
 -> incumbent source/event owner
 -> canonical transaction + source-origin lineage
 -> typed direct parties and affected relationships
 -> transaction-specific lifecycle
 -> affected asset/program/security cases
 -> bounded specialist research
 -> incumbent financial/economic translation
 -> accepted recommendation review
 -> coherent publication snapshot
 -> prospective evaluation
```

A later event revision invalidates only dependent cases. Independent scientific, procurement, project
or commodity models remain unchanged unless their own dependency changed. Old recommendations and
known-at-time evidence remain immutable.

## Reference proof

`research/special_situations_horizontal_reference.py` is deliberately pure research reference code.
Its six tests pin:

- direct MGLD target versus indirect fund role;
- seven affected registrants without seven independent source origins;
- transaction-specific terminal state;
- partial enrichment as unknown rather than negative;
- observed nonqualifying enrichment as droppable;
- dependency-scoped invalidation.

It is not a production model and is never imported into a scoring/ranking path by this branch.

## Product direction

The existing page is setup-first. The target view is investment-impact-first:

1. security and exact event role;
2. prepared judgment or explicit Researching/Review pending;
3. catalyst and next decision/window;
4. conditional economic consequence;
5. principal risk/unknown;
6. affected structures and source-origin independence;
7. deeper timeline, evidence, economics, expectations and decision history.

The fallback local HTML prototype is a conversation artifact, SHA256
`c349ea16175088d34f19afeb2fcaf09821e04d5452fcc80d47e2056ef40f6521`.
Eight static semantic/responsive/theme checks passed. Two bounded Chromium screenshot attempts hung and
were stopped by timeout, so no screenshot or browser acceptance is claimed.

## Paper boundary

The central Paper file was observed as `01M2WGNCX9475G79JRKJTCM08P`; BioCatalyst page `p-K-0`
exists. The guarded write catalog was not admitted and a later unchanged catalog attempt reported
UPSTREAM_UNAVAILABLE with retry disallowed. No Paper edit was dispatched, so there is no uncertain
Paper effect to reconcile. Wait for a relevant runtime/catalog/owner change before another admission
check.

## Next implementation boundary

Use `research/SPECIAL_SITUATIONS_HORIZONTAL_CATALYST_IMPLEMENTATION_PLAN_2026-09-27.md`.
The first production implementation must be the real MGLD/USCF relation correction under incumbent
identity/event ownership, RED-first, followed by transaction-specific lifecycle and consumer
deduplication. Forecast/live recommendation authority remains held until prospective evaluation and
independent method review.

Research/design remains a checkpointed continuation rather than a completion claim; forecast promotion
is not qualified and production acceptance is unchanged.