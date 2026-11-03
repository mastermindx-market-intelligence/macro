# D07 dossier and planner advisory diagnostics

These are current-source baseline witnesses for the D07 calendar, article and return contract. The two witnesses cover the requested-call mismatch at a current-event dossier and date-change ambiguity when the planner's period is unknown.

## Run

Use Node 24.22.1 with its standard-library modules.

```sh
# From the D07 package directory
cd checks/diagnostics/dossier-return
node probe.mjs sources/company-intelligence-dossier.js sources/watchlistEventPlanner.ts
```

For a byte-for-byte comparison with the recorded output, run the same command through `diff`.

```sh
set -o pipefail
node probe.mjs sources/company-intelligence-dossier.js sources/watchlistEventPlanner.ts | diff -u results.json -
```

The probe checks the Git blob of each full source copy before selecting the original functions. A successful run prints `SOURCE_BOUNDARIES_REPRODUCED`. Assertions intentionally require the inspected baseline. The recorded result is deterministic. Node's experimental TypeScript-erasure notice goes to stderr.

## Included evidence

| File | Purpose |
| --- | --- |
| `probe.mjs` | Runnable witness using original selected function bodies |
| `sources/company-intelligence-dossier.js` | Unchanged full Macro consumer at `fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9` |
| `sources/watchlistEventPlanner.ts` | Unchanged full Terminal model at `3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9` |
| `results.json` | Recorded stdout from the successful run |
| `source-manifest.json` | Immutable source URLs, full source Git blobs/SHA-256 and diagnostic artifact SHA-256 |

## Witnesses

1. The dossier receives an incoming `tx=2026Q3` and a source-shaped current Q4 response. V1 `showPayload` delivers Q4 to a substituted `renderEvent` recorder. Its positive control uses valid `tx=2026Q4` and the same public `latest_event` shape. V2 `renderV2` writes the Q4 event attribute and creates a Q4 transcript link plus the current Company analysis link. Both unmatched-query variants retain the incoming Q3 URL.
2. Original `eventIdentity` and `noteReschedule` retain `earnings:AAPL:next` across a date change with null period. The result records an earlier day without identifying whether one issuer event moved or the next event replaced it.

## Execution boundary

The VM executes the original `showPayload` and `renderV2` functions and their selected original identity/URL helpers. V1 presentation is a callback recorder. V2 runs through a minimal DOM adapter with display helpers stubbed. The request lifecycle, real DOM rendering, auth, browser history, serving caches and production incidence remain outside this execution.

The planner functions run after TypeScript type erasure. The input events are controlled fixtures using the source's supported null-period state. The probe exercises selected function boundaries. Full planner-component and normal-entry-point verification remain pending.

Browser acceptance, implementation repair and formal review remain pending. The existing six member-hydration witnesses are separate. This bundle is internal advisory evidence under the current D07 owner.

[Macro consumer source](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/site/assets/js/company-intelligence-dossier.js) · [Terminal planner source](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/watchlistEventPlanner.ts)

The matching-call control clears its callback recorder before invocation and requires exactly one newly recorded matching callback. Its result records `callbackCount=1`, so an earlier mismatch response cannot satisfy this control.
