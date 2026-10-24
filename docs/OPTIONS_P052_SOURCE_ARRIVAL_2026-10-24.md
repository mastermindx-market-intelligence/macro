# P052 original GEX source arrival

Source-only addition to B's existing fixed-file `OPTIONS_SCENARIO_PRODUCER_DIR` ingress. B owns application bindings, private retention, current principal/resource authorization and activation. This source milestone does not transfer a native payload, create a live producer directory, read credentials, call a bucket/provider, enable flags, perform per-user retention or apply an Investigation revision.

## Existing composition and exact gap

B source join `9a2610c13e362a6be41f17057c15ae6ed7c18122` already has `capture_built_scenario_sources`: fixed producer file reads, exact descriptor validation, source-Save/current-viewer/private-destination/retention checks and immutable private object retention. The descriptor pins source kind/root/session, hashes and byte lengths, source clock, model, lens/selection and basis digest. It sufficiently selects exact content. It does not attest one atomic nightly generation or independently verify scenario math; no new generation protocol is introduced.

The M1 source receipt identifies code `/Users/chriswong/optionshub-ops-wt` and physical output `/Users/chriswong/hub-ops-wt/data/live_flow_out/options_hub`. Its GEX/moves writes are separate mutable files. A public last-good Hub object need not match the local producer bytes, so it is never a delivery fallback. The API's retained 2026-10-24T06:34:18Z configuration receipt has a dedicated Research Vault destination, read/capture OFF and no configured producer directory. No authenticated private paid-byte transfer or destination qualification is established by those receipts.

Existing M2 `m1` SSH configuration and B's strict-known-host `macro_dashboard_deploy_v2` API receipt identify host access legs. Those references do not authorize or prove a payload copy, API target ACL or a working native-to-API mount. No SSH/SFTP operation was attempted here. B chose the existing producer-dir interface; the new helper closes the missing safe-arrival invariant rather than introducing a transport service or another store.

## Narrow source interface

`engine/options_scenario_source_arrival.py:arrive_gex_source(descriptor, raw, producer_out_dir=..., today=...)` accepts original descriptor-selected GEX bytes from an independently authorized private copy facility. It validates the existing native descriptor, exact size/digest/schema/root/session and projection observation clock before target IO. Raw bytes are retained unchanged; no JSON reserialization, derived source or source-availability clock is invented.

The existing absolute configured tree and its `gex` directory must already exist. Unsafe path components, symlinks, path escape and any existing target—including identical bytes—refuse. A complete bounded 0600 temporary leaf is fsynced inside the held directory; an atomic no-overwrite link exposes the final `{root}.json`. Failure cleans only the helper's own temporary leaf. An ambiguous/post-link outcome reports uncertainty and leaves the final target intact; the caller must inspect the same delivery, not overwrite/replay or claim rollback.

A successful source arrival is not a Save/retention/authorization receipt. Existing capture still revalidates original bytes under fresh current-user/resource/Save/retention checks and retains immutable exact objects before dependent canonical publication. It does not resolve source-grant, scenario-math or saved-revision acceptance.

## Optional moves and provenance

An explicitly GEX-only descriptor with `moves:null` is supported. Requested optional moves refuse before target IO; they are never stripped from a request or silently downgraded. Whole moves artifacts can include Levels learned multipliers and graded calibration. The producer reads `levels/track_record.json` and `levels/grades.parquet`; `scripts/refresh_index_bars.py` documents the separate Yahoo/yfinance adjusted index-grading route. The narrow Research Factory Yahoo attestation cannot be assumed to qualify that complete route. B's existing whole-moves refusal remains; GEX-only support does not claim missing moves were admitted.

## Exact next effect

After accepted source release, B/native owners must separately qualify the actual existing private copy facility, receiving service account/path and destination privacy, select the intentional exact original GEX reference, and admit one bounded copy into the existing configured producer tree. No account/ACL/configuration/transfer/activation permission is created by this document or helper. Then use the existing B capture/read/CAS path; verify retained exact bytes and the same saved revision after source/head changes. Do not enable source/capture flags merely because this source test passes, and do not use a public/latest replacement when the private source is absent or changed.
