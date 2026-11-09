# PBG-01 — Preserve and qualify policy source clocks

**Status: PROPOSED_UNLAUNCHED.** Incorporates the [shared handoff contract](../PB_G_IMPLEMENTATION_HANDOFF_INDEX.md). Separate implementation authorization is required.

## Capability, owner and scope

A Policy Watch reader and downstream context consumer can distinguish when the underlying evidence was checked, the vintage of each supporting observation, and when a model synthesized the view. A new model run cannot make unrefreshed inputs appear current.

Existing owner: Policy Intent. Candidate paths are [engine/policy_intent_desk.py](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/policy_intent_desk.py), [engine/policy_watch_current.py](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/policy_watch_current.py), [scripts/build_policy_watch.py](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/scripts/build_policy_watch.py), with a bounded consumer compatibility check in [engine/intel_hub.py](https://github.com/mastermindx-market-intelligence/macro/blob/c6c0ab36cdbf31f74a20f5ebf9304dd3fd920b05/engine/intel_hub.py). Data OS temporal logic is a dependency to reuse, not rewrite. Read-only inputs include the existing policy substrate, White House/Federal Register/Fed/Treasury/current-country receipts, lifecycle and RIC artifacts. The future owner must verify exact output-contract tests at pickup.

The inspected producer already puts `intel_asof` into `gather_state`. `synthesize` and `_append_ledger` omit it; refresh age is based on the generated brief. The page already has separate evidence/analysis labels. Correct the producer's lost provenance and carry qualification through those labels; do not create another freshness dashboard.

## Inputs and output semantics

Retain source-family identity, original observation/event references and content/version digest; observed/effective/publication times with precision; most recent successful coverage check; coverage extent/completeness; owner-native failure status; synthesis time/model/config and input manifest/cutoff. Map these concepts to the smallest owner-approved contract extension. Do not fabricate precise timestamps from date-only fields.

Freshness concerns the relevant source family's coverage, not simply the age of an operative decision. An old policy remains operative after a successful current check. A successful empty check is distinct from no coverage, source outage, invalid newest item or stale observation. Reuse source-specific budgets already owned by the source; do not invent one universal TTL. A failed optional family limits only conclusions requiring it. A missing required input withholds the current affected conclusion and exposes a dated prior view only as prior context.

## Failure, correction and model role

Qualify evidence before model synthesis and before appending a new eligible thesis row. A cached/latest brief must also be requalified at read time, so avoiding a new model call cannot preserve a misleading current label. The LLM may explain qualified observations and alternatives; it cannot supply missing source clocks, grant factual lifecycle state or bypass a deterministic refusal.

Keep existing nightly ledger gates and append-FIRST/accountability semantics. Add future rows with input provenance under an admitted version. Preserve old rows unchanged; absent historical provenance remains unknown. A later corrected source creates a linked new version; it cannot rewrite earlier information sets. Do not replace missing owner receipts by the current wall clock.

## Discriminating tests and real-path proof

Demonstrate a freshly generated synthesis over stale/missing source coverage remains visibly limited; the same old operative decision with a successful current check is qualified. Test successful empty coverage versus outage, missing required versus optional family, future/malformed timestamps, late ingestion, correction, legacy rows without provenance and a fresh output without a source manifest. Verify policy still cannot enter Intel Hub scored votes.

Use retained real official-source artifacts through normal producer and page build. Identify source family, observation/manifest digest, output bytes, ledger behavior and served consumer evidence. Show existing evidence/analysis labels and the dated-prior/withheld case in the actual page. No new production writes are authorized until this later commission's ordinary release gates are met.

## Non-goals and stop

No new collector, store, clock service, lifecycle, policy-intent score, TTL policy or full page redesign. Automatic White House/FR facts → lifecycle admission is not already proven and must stay within the existing lifecycle owner's explicit reviewed admission.

Stop when the exact existing-source → brief/ledger → current page/context route preserves and explains provenance under both successful and failure cases, with authority unchanged. PBG-02 starts only after this contract is accepted.

