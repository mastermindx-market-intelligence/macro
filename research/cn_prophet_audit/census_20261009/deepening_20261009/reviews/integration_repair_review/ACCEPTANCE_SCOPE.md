# Independent acceptance scope for the integration repair

This scope is recorded after sealing the original seven-finding review and before inspecting the completed repair. The original review manifest is `78fcfa3c271d214c751a40220dc92e44cec67409eb49fbe7421b9c22a32698b6`. It remains unchanged. The repair is owned separately under `repairs/integration_contract`; this review does not edit it.

Acceptance must bind the exact repaired code, fixture, source dependencies and result hashes. A passing producer battery is evidence to inspect, not a substitute for independent hostile execution.

## Required adversarial outcomes

| Original finding | Independent acceptance condition |
|---|---|
| F1: whole-key spool omission | Removing all evidence for any previously consumed target-session key, including a spool containing only close snapshots, must be refused or explicitly unavailable before writing. |
| F2: equal-time conflicting closes | Conflicting membership under the same observation time and generation must not be selected by object-key ordering. Repeat with the original inert-nonce variants. Equivalent close evidence needs an explicit coalescing rule and retained source object identities. |
| F3: false quote adjustment provenance | Missing, adjusted and bare raw declarations must not acquire unsupported raw provenance. Inspect and exercise the repaired source-contract binding; a positive explicit synthetic contract must preserve exact source and price evidence. |
| F4: duplicate Parquet history loss | Conflicting existing daily keys must be refused in either row order before a writer runs. Original file bytes must remain unchanged. |
| F5: score domain | Standalone score values below 0 and above 100 must be refused; 0 and 100 remain valid measured values. |
| F6: huge JSON integer | A 401-digit positive price must take the intended typed or per-name refusal path, not an unhandled overflow. |
| F7: copied immutable fields | A conflicting stored first price under the original event ID must be refused rather than silently kept or healed. Check at least one other immutable first-observation field. |

## Compatibility and authority controls

- Reproduce the intended positive synthetic flow through the pinned native functions and the existing daily-key/native-writer path.
- Preserve the prior armed generation after current-key rollover. Keep settlement gate verdict and canonical membership receipt distinct.
- Replay complete evidence idempotently after persisted representation normalization.
- Carry a valid noncolliding older legacy row unchanged, without inventing research provenance. Target-session unbound collisions remain explicit migration conflicts.
- Allow a legitimate later repeat observation to update last-observation/count fields while preserving the first record.
- Preserve the original lab and original review hashes throughout acceptance.

The repaired artifact remains offline research. No synthetic test certifies natural vendor-basis accuracy, object-store permissions/retention, deployment, market execution, fills, returns, or a completed scheduled production roundtrip.
