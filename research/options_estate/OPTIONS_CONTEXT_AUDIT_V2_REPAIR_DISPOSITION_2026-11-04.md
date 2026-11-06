# Context Audit charter repair disposition — 2026-11-04

Source proposal, not independent acceptance. The original Oct22 review remains unchanged. The charter retains every v1 cap, service limit and production hold. No corpus remeasurement, benchmark, registration, implementation or runtime change occurred.

The original Fabric worker `options-context-v2-charter-repair-20261103` (GLM5.3Flash/ubuntu0) returned rc0 and two artifacts through its original manifest-bound export. Parent verdict on the raw candidate: **REPAIR_REQUIRED**, not accepted. Retained stdout SHA256 `e9229a62c9cba937b57fca4302bf55c96b66c39bf259cb1b8cb27ee16208d18e`; raw charter `98b6b7888bdf13238e0ab492292d132277ddbca6184d68c65f42f9bc325877de`; raw disposition `8146c8d4cb9fd0ffd9e60c4179dfece196856d3d7765263ba98a8844dfc25cd9`.

Parent corrections address five remaining contradictions in that candidate:

1. Stable semantic bytes cannot include the digest of variable attempt evidence. Independent hashes now meet only in an outer envelope. Envelope/HEAD byte lengths are checked outside those objects to avoid a hash/length cycle.
2. Missing HEAD is not proof of absent publication. Partial/unknown writes preserve originals and wait for authoritative same-operation settlement or exclusion; no automatic delete, replay or replacement. Temporary-file cleanup is separately bounded to settled local work.
3. An acceptance role is not an absent named conversation. The current delegated receiver can record the applicable authority and exact-byte decision after independent review; neither authorship nor this proposal is acceptance or a new cap grant.
4. Registration and Git merge cannot install or select a validator. Qualified selection and effect settlement are separate required evidence; the prospective cohort starts after all three clocks, while v1 bytes stay pinned.
5. Manifest mutation and derivation lag are not a complete age policy. Missing source-age/skew/calendar parameters remain explicit preregistration prerequisites, without invented thresholds.

## Original finding disposition

| Findings | Proposed source repair | Still required |
|---|---|---|
| 1–2 | Explicit recoverable acceptance role; exact reviewed bytes; no in-place v1 cap changes or seat-decision loophole | Independent review and recorded acceptance under the current assignment |
| 3,6 | Fixture scale is not a grant; no feasibility claim or new numeric operating limit | Real service-class benchmark including context-store and cgroup accounting |
| 4 | Acyclic semantic/attempt/envelope separation; canonical output independent of partition; source reorder still refuses | Review and later reproducibility/crash tests |
| 5 | Positive complete-population success at qualified scale; universal refusal cannot pass | Actual admitted fixture benchmark and separately reported live defects |
| 7 | Frozen campaign slicing explicitly classified; complete manifest/checkpoint and current receiver own contract investigation | Current snapshot census and lawful campaign resolution, no invented coverage |
| 8 | Every incremental HEAD represents full population using authenticated prefix evidence | Full-scan parity and negative fixture proofs |
| 9,11 | Registration, protected source, acknowledged selection and forward-session eligibility distinguished; missing age parameters explicit | Accepted registration and clock contract; later installed selection proof |
| 10 | All five incumbent caps and fixed service envelope retained | Byte parity on any future implementation |
| 12–13 | No independent verdict or acceptance claimed; exact revision required | Independent changed-risk review, exact commit/blob decision |
| 14,16 | Historical censuses remain dated; no fresh host proof or growth forecast; wave publication does not equal acceptance | Dated journal and current snapshot provenance; task remains open |
| 15 | Sole writable path, no privilege changes, cgroup accounting, settled-local cleanup only | Actual bounded benchmark and cleanup/unknown-effect tests |

This is the original charter repair, not a replacement implementation carrier. PR #7728 stays held. Acceptance of this document cannot reopen source-use reviews, data rights, production-records refusals or uncertain effects elsewhere in Options.
