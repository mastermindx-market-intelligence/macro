# Sector fixed-five calculation composition

Status: source-qualified, not activated. Governing issue: [Macro #10779](https://github.com/mastermindx-market-intelligence/macro/issues/10779). Convergence: [PR #10780](https://github.com/mastermindx-market-intelligence/macro/pull/10780). Base: `cec642221e01dfc5a496d99f866e9b6fe313cfbb`. Protected Mastermind law: `49c2e1d93e5e080b1671c98087a845e5beb09dd5`.

## One calculation, existing owners

`engine.sector_basket_documents.compose_sector_documents` accepts the already established BasketInputs, ThemeScoreInputs, NarrativeAllocationInputs, SectorCyclesInputs and SectorTimingInputs plus SectorDocumentContext and explicit evaluation/build clocks. It invokes the existing real calculation owners and returns exactly the five members admitted by the existing Sector generation factory:

- `sectordata/sector_central.json`
- `sectordata/sector_cycles.json`
- `basketdata/baskets.json`
- `basketdata/si_handoff.json`
- `basketdata/action_board.json`

The existing basket, theme and allocation engines run first. The cycles engine uses its original bounded panel and captured cycle context. Existing rotation alignment decorates the cycle output. The established basket document owner adds bottoming, Pulse, ThemeContext and the compact handoff. The timing/setup owner and action-board reducer then compute the board. Finally Central consumes the actual computed cycle spine and allocation; the captured pre-append grader and existing document-completion owner add their fields.

No precomputed Central, cycles or board output can be supplied in place of these calculations. Prepared theme rows/enrichments remain accepted explicit inputs: their binding to the actual thematic resolution is the capture adapter's responsibility. Narrative retains its separately owned primary-plus-extras projection. The prior selected Central is input only to theme scoring, through its established prior-sector-text field.

## Coherence and clocks

Core source session, basket baseline session, cycle evaluation date, outer evaluation date and aware publication/build timestamp are separate facts. A source session cannot exceed evaluation; baseline cannot exceed core; build UTC date cannot precede evaluation. The captured cycle evaluation may equal the observed source day while the outer evaluation occurs later. The original cycle as-of semantics remain intact.

The original cycle bounding operation runs before consumers diverge. Central and the grader receive exactly that effective Yahoo panel, including explicit-ceiling and benchmark-tail trimming. Shared setup and timing ETF observations must equal the corresponding effective Yahoo observations. Comparison ignores outer-index null padding but does not excuse changed values/history. The full basket specification passed to cycles must equal the BasketInputs membership. Theme and narrative price-basis differences are not collapsed into an assumed universal panel.

Setup requires captured SPY and every configured setup sector, actual US reference-session containment and no price after the core source date. Timing and cycles must share identical captured cycle calculation settings and reference indexes. The frozen grader history must have a unique, ascending, daily, timezone-naive DatetimeIndex without NaT and with no observation beyond the admitted core date.

These guards establish internal composition consistency. They do not prove an external private-input manifest, provider entitlement, corporate-action basis, source completeness or holdings vintage. Those remain required at capture admission.

## Byte and effect ownership

The final enriched basket document is serialized once. The same bytes determine the board's basket digest, Central's secondary-source digest and the eventual publisher request. Other members are serialized as finite JSON; no NaN or Infinity can enter a successful result. The compact handoff and board keep the basket baseline as their observation date; build time is never substituted for market observation.

The function performs no acquisition, writes, publication, selection or ledger advancement. It returns deferred theme effects as values. Grading reads one supplied frozen frame for both levels and membership, consumes the captured pre-append call log, and does not append today's calls or freeze basket prices. This can legitimately differ from a later nightly ledger run.

Central explicitly records that legacy flows HTML and premium artifact writes did not occur. Native research handoffs remain disclosed as unbound pending the actual shared-shell receiver integration. The existing native projector does not turn raw legacy handoff metadata into a new receiver.

The existing `prepare_sector_generation_request` / `preflight_sector_bundle`, private publisher, selected-generation reader and authorization gates remain the admission/publication/read authorities. This composer does not create a competing serializer protocol, manifest verifier, scheduler, cache or publication identity.

## Verification

The initial focused suite passed **19 tests** and the first six affected suites passed **261 tests**. After the real publication bridge and split-baseline proofs were added, the final seven-suite run passed **328 tests**, with 64 existing FastAPI/Starlette deprecation warnings and no skips or deselections. Counts overlap. Exact commands, source hashes and log hashes are in [the source proof](SECTOR_DOCUMENT_COMPOSITION_SOURCE_REVIEW_2026-11-06.json).

The real integration fixture uses 320 observed US sessions ending 2026-11-05, actual synthetic five-field member values, the distinct thematic and narrative preparation paths, genuine member candles, timing/setup and all five real document engines. It passes both preview and entitled native-bundle preflights. It proves calculation and native projection compatibility; its 320 sessions intentionally do not claim the private Yahoo transport's separate 1,000-observation source floor.

An ambient-effect observer forbids configuration/store reads, provider calls, wall clocks and writes during calculation. The test preserves dateutil's original datetime type namespace only to keep pandas DateOffset type checks operational under the existing observer; no production clock is relaxed. Two initial failures were this test-observer compatibility, not successful production behavior, and were repaired before qualification.

Adversarial cases refuse incompatible source/evaluation clocks, changed shared cycle settings, changed setup/timing values, divergent membership, missing benchmark, future setup prices and malformed/future frozen history. Explicit-as-of trimming and a later ETF-only row both prove byte-identical output to the bounded baseline; the actual grader receives the same truncated panel. Inputs remain detached.

## Existing publication and API path now exercised

`Orchestrator.publish_sector_documents` checks the fixed-five byte set, its composition hashes/lengths, core/baseline identity and actual emitted build stamps before staging. It reuses the existing private-root exclusion, ephemeral private staging, request factory, lock and CAS publisher. It returns the original publisher effect result and applies no deferred effects.

The domain request factory now validates an optional aware computation clock against the actual target publication receipt, including the original receipt on retained-byte reuse. The new bridge always supplies this clock. Existing callers that omit it keep their established behavior.

The real-engine fixture now runs through private publication, one selected-generation read and the actual router/wire with controlled identity and entitlement lookups, for both audiences. No full application lifespan is started. A one-session older basket/theme/allocation baseline remains visibly `declared_older_baseline`; an expired baseline is refused for new selection. Omitting the older baseline refuses before staging. An attempt delayed until the source is stale cannot replace or reuse the previous accepted selection. A future computation clock, changed bytes, changed identity and changed build evidence are refused. All tests use isolated temporary private roots and synthetic input data; no live-account or VPS data-currentness claim follows.

## Remaining implementation and acceptance

The next source integration must complete capture of all real required inputs through the existing owners, bind thematic preparation/enrichment and narrative projections, carry original auxiliary vintages and bind the previous selected Central. Amalgams, sponsor holdings, calibrations, archives and grading history must be either correctly admitted or explicitly unavailable under existing semantics; no synthetic currentness or undocumented default can stand in for source evidence.

A private captured-input canary requires an independently admitted immutable execution closure and the existing publisher's private target, or completion of the source updater barrier before mutable-VPS activation. It must not start another provider loop or ledger writer. The API mount, native whole-generation BFF/consumer, sole-writer transfer, CI registration/protected merge, authenticated two-generation open-tab refresh, fault drills and other estate families remain unfinished.

The CI capability denial remains binding. The original holdings commission still lacks a qualified no-effect/return reconciliation and remains protected. A distinct Terminal managed-workspace acquisition for the generation consumer returned REFUSED / NOT_APPLIED / REPOSITORY_SOURCE_UNAVAILABLE; the one bounded diagnostic found no mmx-workspace executable in the current shell PATH. This is a workspace-source admission failure, not evidence of a credential failure or an executed mutation. No rehome or unchanged retry occurred.
