# Terminal saved-workflow contribution

Source-only contribution for the incumbent [Terminal #778](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/778), not a new Terminal writer or release. Root publishes this review packet through Macro #9066 and may post one canonical #778 contribution/custody question after review. No receiving owner, delivery acknowledgment or custody transfer is claimed.

`terminal-contribution.patch` extends existing saved-view and immutable Thesis owners with a closed Government Revenue declaration. `source-manifest.json` binds exact original Git blobs and proposed bytes. `checks.mjs` refuses source drift before importing those bytes. All source inputs are now qualified against #778 head `122694a1249cc15f563f139aa6ee5e36c7862f12`. Fresh pinned reads show its Thesis/SQL validator and `rmsViews`/`analysisSymbol` leaves byte-identical to current protected `master` at `abea23b1f75231aa7ae8f3a971c44094ff4f9726`. The same patch applies to an exact #778 artifact copy and reproduces every tested proposed hash. This closes the earlier mixed-source uncertainty; it does not qualify source custody, native Terminal CI or release.

## Correct v2 consumer shape

The outer contract is `mastermind.saved_view.v2`; the discriminated definition is version **1** and its declaration property is **`monitor`**:

```js
const originalRequest = {
  action: "create",
  contract: "mastermind.saved_view.v2",
  scope: "user",
  id: originalRequestId,
  name: "Government Revenue — LMT",
  definition: { version: 1, kind: "government_revenue", monitor: verifiedDeclaration },
};
```

Use the existing authenticated `/api/thesis-saved-views` original-request create/readback path. The server binds owner identity. Preserve that exact request during uncertain outcomes; do not replace it with a fresh ID or adopt another principal's state. Versioned GET can filter `kind=government_revenue`. Existing saved-view definitions, legacy reads and retirement/recovery remain with #778.

The typed declaration carries canonical subject, enabled flag, mode/truth/query/agency/ticker/issuer selection, observation window, knowledge cutoff, immutable input references and bounded baseline events. No free URLs, private sidecars or narrative bodies are admitted. Atlas-only identity context does not establish procurement monitor eligibility; `gria1` references and `companies` mode are unsupported by this declaration.

Saving a view alone does not subscribe to the monitor. Subscription requires an explicit same-subject immutable Thesis revision through existing `applyThesisVersion`, with optimistic `expectedVersion` and original `clientRequestId`. Its TypeScript content property is **`governmentRevenueMonitor`**; its wire property is **`government_revenue_monitor`**. Foreign-subject declarations fail before RPC. Existing immutable content lineage and fingerprint ownership stay intact.

The separate Macro contribution lets the existing monitor consume that wire member and the governed published workspace. It distinguishes new facts, corrections, no change and outage in bounded dry plans. It does not reconstruct unavailable historical source bytes or enqueue/send Government Revenue notifications. No new registry, table, scheduler or outbox owner is introduced.

## Portable source checks

On a lawful review tree containing the proposed Terminal bytes:

```sh
node --experimental-strip-types checks.mjs --root /path/to/terminal-review-tree
```

The root must contain `terminal/lib/`, `terminal/app/api/thesis-saved-views/route.ts` and `supabase/migrations/0012_thesis_objects.sql`. Local Node 26.5.0 qualification passed 12 cases; the runner requires Node with built-in TypeScript stripping. The runner copies reviewed modules into a temporary harness and rewrites TypeScript alias specifiers. Stub disclosures: `rmsViews`, `analysisSymbol` and type-only `watchlists` leaves; synthetic in-memory DB and RPC; fetch forbidden. These checks cover parser/wire/persistence-double behavior and static API/SQL source fences. They do not replace native Terminal typecheck/Vitest, actual database or browser tests. Exact proposed Macro bytes separately passed all 71 local pytest cases: 43 incumbent plus 28 actual-workspace cases.

The SQL file diff is a validator-source proposal, not migration installation or authority to modify deployed migration history. Any installed validator change requires the incumbent migration ledger, review and approved release path. No SQL was applied.

## Custody and release holds

Fresh #778 remains OPEN/DRAFT at the head above. Latest discussion still includes unresolved fixed-group original-selection context. Current inspected live Terminal sessions own other carriers; an active #778 writer has not been identified. Historical account labels and absent local worktrees do not transfer custody. The root's one canonical question should ask the incumbent to identify its current receiving session/path and accept review or explicitly defer this contribution under the existing hold.

All #778 obligations remain: atomic cap-50 enforcement in the existing database owner; old/new binary deletion, retirement and rollback proof; mounted-client recovery after 401/403; fixed-group original-selection context disposition; independent exact-head review and current CI; authenticated ThemeAtlas/integration acceptance; approved non-Vercel release/deployment; actual production and two-account proof. The original held PostgreSQL harness effect is not retried. Migration prefixes must follow the existing reservation ledger; no prefix is claimed by this artifact.

Notification and drain enablement remain a separate gate requiring independent privacy/risk assessment and evidence of current installation. Source receipts and historical RLS/migration proof cannot establish that gate. The original unresolved local saved-workflow Fabric operation remains on its original carrier without replay.

## Source materialization correction

The initial fetched-source Add File serializer split content ending in LF and emitted an extra empty plus-line, appending one LF to each of seven source files. The original artifacts remain retained. Removing exactly that introduced byte reproduces every original advertised Git blob. This packet uses the reconstructed exact bytes and fresh checks; its manifest records the cause and original corrupted hashes. No logic, fixture, upstream fix or incumbent source was rewritten to resolve the mismatch.

## Receiving frontier qualification — October 13

The root published this packet at Macro commit `75da11947eb007cefb01125533df08a4703866d2` and posted exactly one [canonical #778 handoff](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/778#issuecomment-6141933267). No owner ACK follows in the inspected discussion.

The precise original source frontier is [issue770 comment5889320517](https://github.com/mastermindx-market-intelligence/mastermind-terminal/issues/770#issuecomment-5889320517), operation `heatmap-recovery-20260929-sol`, last updated October3. It records an in-turn Sol receiver, no worker/watcher/background execution, and unresolved original source-writer custody. It also retains an unlanded R16 Atlas/SavedViewClient candidate. Four GovRev target TypeScript source files in that candidate match #778 exactly; the R16 overlays are adjacent and must be preserved during any eventual integration. The candidate's absence of a SQL file is not database or installation evidence.

Current inspected native sessions do not qualify a #778 receiving owner: Intelligence Workspace 2.0 retains #804; Complete Finviz Theme/Subtheme Clust is a separate mission without a current #778 custody declaration. The existing handoff requests the receiving session or an explicit lawful custody disposition. The next source integration edge remains that original-writer consumption or custody handoff on #770/#778; no duplicate message, worker, source carrier or held-effect retry follows from this source qualification.
