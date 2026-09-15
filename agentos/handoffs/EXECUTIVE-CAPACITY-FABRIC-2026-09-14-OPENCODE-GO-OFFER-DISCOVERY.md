---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: sol/opencode-go-subscription-usage
model: sol
ended_because: blocked
mission: >
  Add a public inventory and official-documentation offer-drift reader with bounded
  previews and change classification, while preserving existing ownership and granting
  no route or account authority.
state_before: >
  Quota parsing and simulated transport continuity existed, but there was no executable
  public inventory or offer-drift consumer.
changed:
  - path: agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-14-OPENCODE-GO-OFFER-DISCOVERY.md
    what: >
      Added the continuation record for public Go offer discovery and the exact runtime
      boundary.
  - path: research/OPENCODE_GO_DYNAMIC_OFFERS_AND_MODEL_DISCOVERY_2026-09-14.md
    what: >
      Documents the full architecture for the dynamic-offer and model-discovery source.
verified:
  - claim: >
      The public API returned 37 IDs, selected documentation contained 28 endpoint IDs
      and 36 rate variants, and the gap analysis identified nine unmatched listing IDs
      plus one missing privacy row.
    command: >
      Run the public API and selected official documentation through the new reader and
      compare its parsed inventory and offer rows.
    result: >
      The reader returned 37 API IDs and 28 endpoint IDs with 36 rate variants; nine
      listed IDs lacked offer rows and MiniMax M2.5 lacked a privacy row.
  - claim: >
      The new reader parses public model and documentation content, preserves unknowns
      and time, context, and promotion qualifiers, previews model-equivalent windows,
      and classifies changes without route authorization.
    command: >
      Inspect the reader implementation added by commit
      74eb5e946963f87e284ae37f3307eaeab0f93e7d.
    result: >
      The source implements the stated parsing and classification behavior as advisory,
      always-disarmed previews.
  - claim: >
      48 new tests and the earlier 84 checks passed together in 3.71 seconds, and new
      published Git blobs matched tested bytes.
    command: >
      Run the 48 new tests together with the earlier 84 checks on Linux using Python
      3.13.5 and compare published Git blobs with tested bytes.
    result: >
      132 tests passed in 3.71 seconds, and the new published Git blobs matched the
      tested bytes.
unverified:
  - claim: The default collector operates against real HTML.
    what_would_validate: >
      Validate the public reader against real API and HTML bytes on a permitted
      execution surface.
  - claim: The capability passes full repository CI and independent review.
    what_would_validate: Run full repository CI on the exact head and obtain independent
      review.
  - claim: Mac installation and live scheduling are proven.
    what_would_validate: Perform and verify Mac installation and live scheduling through
      the existing owner.
  - claim: The Models.dev importer is built.
    what_would_validate: Implement and separately review the importer under existing
      model-economics ownership.
  - claim: Browser research results are reproducible outside the recorded browser-tool run.
    what_would_validate: Reproduce the inspected public sources through a fresh permitted
      execution path.
unresolved:
  - >
    The new public reader has not been validated against real API and HTML bytes on a
    permitted execution surface.
  - >
    #622 remains at 097e1bac090be8f254013a2729e0f7ef69c94054 with
    parent-composition conflicts.
  - >
    One real supported-account coding task with a visible workspace result, streaming
    cancellation, fresh observations, and existing allocation proof is still required
    before activation.
next_actions:
  - >
    Validate the new public reader against real API and HTML bytes on a permitted
    execution surface.
  - >
    Connect the reader through the existing single-account streaming harness on #622
    and reconcile against landed enrollment, ACL, and binding owners without reviving
    stale parent code.
  - >
    Preserve #7103 and #594 ownership for plans and economics; do not duplicate their
    calculators or force a strict v1 capacity-schema extension.
do_not_redo:
  - >
    Do not create a new registry, timer, daemon, quota ledger, credential store,
    worker, or lifecycle.
  - >
    Do not auto-promote discovered models, reprice or reset existing observations after
    an offer update, or turn marketing request estimates into quota counters.
  - >
    Do not rerun prior platform-blocked native workspace or PR-description effects
    through another device or encoding.
danger_areas:
  - >
    Global listing is not account eligibility, and authenticated usage does not provide
    absolute balances or enrollment identity.
  - >
    Models.dev metadata must not override the actual Go offer or existing
    model-economics ownership.
  - >
    A fetch failure must not erase a valid prior snapshot or renew its age; promotion
    and conditional-retention expiry must remain explicit.
prs: [7143]
---

# Executive Capacity Fabric - Go offer discovery continuation

Parent: WS:EXECUTIVE-CAPACITY-FABRIC. Owner: Sol. Same source carrier: Macro #7143, sol/opencode-go-subscription-usage. Operation: opencode-go-offer-discovery-20260914-sol-001. State: BUILT_NOT_PROVEN for metadata reader/preview; PARTIAL for live Go routing.

## Outcome and exact source

Chris explicitly continued the program and requested the Go limits and automatic handling of changing models/limits. Procedure was loaded atomically from protected Mastermind 935f8d05d7f855f810c5f14c005ab845305f235f, Skillpack 1.0.1/bootstrap 1.

Before: quota parsing and simulated transport continuity existed, but there was no executable public inventory/offer drift consumer. After: the new reader parses the public model list and selected official documentation, preserves unknowns and time/context/promotion qualifiers, previews model-equivalent windows, and classifies changes without authorizing routes or changing any account usage.

Implementation commit: 74eb5e946963f87e284ae37f3307eaeab0f93e7d, parent d8127bded3a9a35bc501e786d27fa32f0ecdd923. Existing usage parser unchanged. Full architecture: research/OPENCODE_GO_DYNAMIC_OFFERS_AND_MODEL_DISCOVERY_2026-09-14.md, documentation commit 8257ac2b1f317527601fd6b2751ac0ac29a3846f.

## Evidence and discoveries

The public API returned 37 IDs, while the selected docs had 28 endpoint IDs and 36 rate variants. Nine listed IDs have no matching offer row; MiniMax M2.5 lacks a matching privacy row. Listing is global discovery, not account eligibility. The listing's created value is response-generation time, not model release identity. Authenticated usage remains percentage/status/reset evidence, not absolute balances or enrollment identity.

Models.dev supplies additional model/provider metadata, but the inspected Go DeepSeek record contains a flat cost without subscription limits or peak/promotion semantics. Use it for enrichment and cross-checking under existing model-economics ownership, not to override Go's actual offer. The Models.dev importer is not built here.

48 new tests and the earlier 84 checks passed together: 132 passed in 3.71 seconds in Linux/Python 3.13.5. New published Git blobs matched tested bytes. Fixtures are explicitly factual transcriptions, not raw HTTP capture; HTML tests are synthetic. Browser-tool research succeeded; sandbox native HTTP acquisition failed. Therefore default collector operation against real HTML, full repository CI, independent review, Mac installation and live scheduling remain unproven.

## Rulings retained

The three account windows are shared, with model-specific equivalent consumption; no independent per-model wallet or universal fixed twelve-dollar budget. Future quote C uses estimated quota points 100*C/(L*f). Existing provider observations are never repriced or reset after an offer update. Marketing request estimates do not become quota counters.

New models are discovered, not auto-promoted. Removals hold new requests; rates require new quote and usage observation; protocol changes require harness proof; privacy changes require policy validation. A fetch failure does not erase a valid prior snapshot or renew its age. Promotion and conditional retention expiry must be explicit, not perpetual flags. No model swap or ambiguous inference replay is implied.

No new registry, timer, daemon, quota ledger, credential store, worker or lifecycle was created. The source emits advisory change records and always disarmed previews. Any future polling/publication uses the existing Provider Control owner. Runtime enrollment/claim/policy gates remain unchanged; registration is not proof of those gates.

## Exact next action

Validate the new public reader against real API and HTML bytes on a permitted execution surface, then connect it through the existing single-account streaming harness on #622. #583 has now merged as 7868e2c2727a8871f64f387de9ce00dc6a67cff9; #622 remains 097e1bac090be8f254013a2729e0f7ef69c94054 with parent-composition conflicts. Reconcile against the landed enrollment/ACL/binding owners without reviving stale parent code. #7103 and #594 retain plan and economic ownership; do not duplicate their calculators or force a strict v1 capacity-schema extension.

One real supported-account coding task, with visible workspace result, streaming cancellation, fresh observations and existing allocation proof, is still required before activation. No Fable assignment or watcher is outstanding. Do not rerun prior platform-blocked native workspace/PR-description effects through another device or encoding. No such effect was retried in this increment.
