# F02 observation identity and Company clock correction v1

**Prepared source overlay; no native effect claimed.** This bounded correction follows the native contract audit. It preserves every existing `fixture-coherence-v1/effective-spaced/` packet and native candidate file. Only six source steps change: two Macro identity fields and four Company fault-copy steps. No board, step, entity, numeric-input or evidence-action identity changes.

## Exact corrections

| Board / step | Correct content |
| --- | --- |
| `macro-dark / evidence-field-0` | `f02.fixture.v3/macro/sector/communication_services/share_above_50d/2026-10-30` |
| `macro-light / evidence-field-0` | The same complete selected observation identity |
| `fault-compositions / empty-table-context` | Fiscal basis FY 2025–2026; USD; fixture publication 30 Oct 2026, 20:02 UTC; retrieval 30 Oct 2026, 20:03 UTC |
| `fault-compositions / retained-table-context` | The same fiscal/publication basis, with **last successful retrieval** labeled explicitly |
| `fault-compositions / tabs-empty-panel` | Annual statement request, fiscal basis FY 2025–2026, fixture publication 20:02 UTC and retrieval 20:03 UTC |
| `fault-compositions / retained-table-error` | Retained EXM view keeps its **original fiscal periods and publication clock**, replacing ambiguous “original source date” wording |

The authoritative [Company fixture](../../../fixtures/company-history.json) describes fiscal periods rather than a calendar observation timestamp. Its publication is `2026-10-30T20:02:00Z`; retrieval is `2026-10-30T20:03:00Z`. This correction removes the Macro settled-session clock accidentally copied into the three completed/retained Company contexts. It does not manufacture a Company observation timestamp.

**Preserved exactly:** unavailable Company source/table copy, loading-tab copy, all raw Company rows, every Macro 20:00 observation, Macro history/publication/coverage/save state, all quantities, component geometry and action semantics. The full Macro identity now agrees with the existing 1280 dock, Chinese evidence journey, 768/1024/1600 width evidence and fault inspector.

## Files and precedence

1. Existing base: `fixture-coherence-v1/effective-spaced/`.
2. Apply [source-overrides.v1.json](source-overrides.v1.json), guarded by each exact base HTML hash, or use the two complete cumulative packets in [effective/consumer-boards.json](effective/consumer-boards.json) and [effective/fault-composition-inputs.json](effective/fault-composition-inputs.json).
3. Preserve and independently compose the latest Company annual-growth v2 row/caveat overlays. These cumulative packets do not absorb or supersede those separate Company improvements.

Use the complete cumulative fault packet for affected **unapplied** steps. If any affected step already exists, the sole writer must bind its actual current native IDs and exact old copy. This package does not invent IDs for the pending fault board or replay an existing step.

For the two existing Macro text nodes, use **one** of these routes:

- [minimal-native-identity-patch.v1.json](minimal-native-identity-patch.v1.json): just the two guarded text updates; preferred when all other repair progress is already tracked.
- [native-patch-candidates.cumulative.v2.json](native-patch-candidates.cumulative.v2.json): the previous cumulative native candidate with only these two groups corrected. All other groups retain their prior candidate content and must be reconciled with actual writer progress before use.

Never apply both representations of the same logical change. Dark text node **`4XH-0`** belongs to step **`4XF-0`** on board **`4PO-0`**. Light text node **`4Z5-0`** belongs to step **`4Z4-0`** on board **`4YD-0`**. These identities come from the existing retained native bindings; the writer still needs a fresh read of each exact target.

Each minimal update accepts only the observed old label `macro / communication-services` or the exact incomplete v3 prefix `f02.fixture.v3/macro/sector/communication_services`. If the full metric/date identity is already present, record the condition satisfied and do not replay. Any different text or identity requires reconciliation. Preserve source-key wrapping and read back the complete value after the effect.

## Validation

[validation.json](validation.json) records the authoritative Company fixture hash, six changed steps, **311 unchanged steps**, preserved input/native-candidate hashes and exact cumulative output hashes. Checks establish:

- Fiscal period, publication and retrieval semantics match `company-history.json`.
- The three corrected Company timestamp contexts contain 20:02/20:03 and no 20:00 clock.
- Loading/unavailable Company copy and all specified Macro 20:00 clocks are byte-identical.
- Complete Macro identities match all five existing narrower/width source steps and the fault inspector.
- Board/step/parent keys, HTML tag topology and all other native repair groups remain unchanged.

These are authoring/source checks, not independent product/taste review, native readback, browser proof or a RIG receipt. The sole writer must inspect any increased wrapping in the Company context lines and long source key, persist actual captures/exports and bind the final freeze. No Paper, browser, GitHub or external-message operation was performed by this preparation.
