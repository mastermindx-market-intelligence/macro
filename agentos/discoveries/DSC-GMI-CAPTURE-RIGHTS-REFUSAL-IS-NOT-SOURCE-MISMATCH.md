---
key: GMI-CAPTURE-RIGHTS-REFUSAL-IS-NOT-SOURCE-MISMATCH
claim: At Terminal 048e019caf84fc8c2bc0e4180de313d6a02e7ca5, the selection-cohort reader collapses SOURCE_UNAVAILABLE:CAPTURE_RIGHTS_UNAVAILABLE
  into source, causing its card to claim source matching failed even though the typed refusal does not
  establish that cause.
falsifier: Run git show 048e019caf84fc8c2bc0e4180de313d6a02e7ca5:terminal/lib/selectionCohort.ts in the
  Terminal repository, then reproduce the exact pre-repair reader/card with the existing unavailable fixture
  and only the exact capture-rights reason substituted. Distinct capture-rights output or absence of the
  matching claim would refute this source finding. Reconcile future reader, card and lexicon changes before
  reusing the result.
so_what: 'Preserve a known exact refusal reason and use non-diagnostic copy for unknown source failures.
  Do not amend rights or turn a refused cohort into empty/zero-overlap data to repair presentation. Reuse
  Terminal #868, not another parser or new source family. Its local fixtures and source publication do
  not establish authenticated production parity, a capture right, D2E acceptance or W3B release.'
kind: landmine
verified_at: 2026-10-09
verified_by: 'https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/868 at e199c9e5357427a2da4722e5ef3e2da326a6d0bd;
  exact five-file remote/local byte parity; npm test -- lib/__tests__/selectionCohort.test.ts lib/__tests__/SelectionCohortCard.test.tsx:
  original baseline 28 pass, expanded old-code matrix 8 fail/46 pass, repaired matrix 54 pass; full tsc
  and focused ESLint pass. Native source/proof manifest: /Users/chriswong/agent-evidence/theme-fabric-e2e-20261008-sol-001/w3c-refusal-copy-20261009/candidate-manifest.json;
  cumulative patch SHA-256 a0eac49d0383f0ab0317340152bcc13935d184e824ff64e4265faa409621dabc.'
scope:
- mastermind-terminal
- terminal/lib/selectionCohort.ts
- terminal/components/prophet/SelectionCohortCard.tsx
- terminal/components/prophet/prophetStrings.ts
- WS:GMI-THEME-GRAPH
confidence: verified
---

# A capture-permission refusal is not evidence of a matching failure

The upstream purpose/rights boundary remains governed by
`DSC:W3C-COHORT-CAPTURE-IS-REFUSED-BY-THE-RIGHTS-GATE-BY-DESIGN`.
This discovery adds a distinct Terminal presentation finding; it supersedes no rights ruling.
The original committed Macro refusal has blob `533ad2e21f2154d49efda7196504dc64e88511b8`.
The pre-repair reader/card/lexicon blobs are respectively `0b8583796301223e6150d8231cfd8caf3fb977d9`,
`829e034fd1b3cd09d820ca2ebb5a96e6204a0067` and `79f712492d593e2d1be5d4053b555339952cefc0`.

The repair gives only the exact typed capture refusal its dedicated presentation reason.
Schema, the research ceiling and every one of the six false authority flags are checked first.
Unknown detail is not echoed. Ready/empty counts, source order, HTTP and fetch behavior are unchanged.
The prior signed-in screen is consistent with this path, but its authenticated payload was not
observed; the source reproduction is not a claim that current production was independently traced.

Terminal #868 is a draft source candidate, not an independent approval, merge or deployment.
The retained three mutations (removed branch, prefix match, wrong UI mapping) fail as expected;
the exact candidate was restored. Local browser cases use the incumbent loopback fixture seam,
not alternate credentials or a replacement for the original Cloud Browser handoff.
