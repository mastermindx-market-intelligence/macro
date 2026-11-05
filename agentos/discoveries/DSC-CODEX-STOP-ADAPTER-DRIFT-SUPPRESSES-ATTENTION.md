---
key: CODEX-STOP-ADAPTER-DRIFT-SUPPRESSES-ATTENTION
claim: >
  An installed Codex Fabric Stop definition can remain trusted while adapter-source
  drift makes the return guard refuse before reading results and emit an empty
  callback response, leaving native return attention unavailable.
falsifier: >
  Inspect the exact configured definition and guard, then run the reviewed
  fabric_stop_preflight command against the intended hooks.json. Matching adapter
  bytes remove this drift condition; native original-parent return proof is still
  needed to establish delivery.
so_what: >
  Check actual source bindings before relying on long-project returns and after
  adapter changes. Review the intended adapter release before repinning it, retain
  native trust controls and prove original-parent delivery separately.
kind: landmine
verified_at: 2026-10-21
verified_by: >
  Mastermind PR 1664 at b740b9afce945d15884076a14bbc6f9471716a46;
  python3 -B -m integrations.session_bridge.fabric_stop_preflight --hooks-file
  /Users/chriswong/.codex/hooks.json returned exit 78 with adapter_source_changed
  for both inspected definitions; the existing guard was read at d010b161.
scope: [mastermind, "WS:ORCHESTRATOR-PROJECT-CONTINUITY"]
confidence: verified
---

## Detail

The 2026-10-21 authorized M2 census found two configured Fabric Stop definitions:
one historical fixed-run binding and one subscribed binding. Their pinned adapter
digests differed from the inspected adapter. The guard's source comparison raises
its unavailable condition before adapter status/result reads; its top-level
handler emits an empty JSON object for that condition.

This establishes a configured failure mechanism. The census did not observe a
native callback firing or prove that this mechanism explains every reported
Astra continuity failure. It also did not establish native loading, delivery or
result consumption.

The preflight is deliberately read-only. Its static success is not a review
attestation for the installed adapter and is not a reason to change trust fields.
The private installed adapter differs from the closest inspected protected source;
automatic approval review denied disclosing that private diff in the connected
session. That exact source-disclosure action remains held pending explicit
permission. No pin was changed and no old operation was retired.

Evidence: [Mastermind PR 1664](https://github.com/mastermindx-market-intelligence/Mastermind/pull/1664)
and the matching source/test commit. The durable project checkpoint carries the
current publication, installation and native-proof state.
