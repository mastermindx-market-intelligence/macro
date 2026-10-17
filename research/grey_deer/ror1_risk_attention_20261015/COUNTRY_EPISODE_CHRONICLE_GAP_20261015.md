# ROR-1 — Existing Chronicle cannot yet de-duplicate China/Hong Kong Radar warning runs

**October 15, 2026 · Original-owner implementation dependency, not an implemented alert system.**
Source read pin `mastermindx-market-intelligence/macro@9b255a5377385a6b0dab23850e6a6ff67714a5f1`.
Original Grey Deer risk owner #8132 remains Draft/HOLD. The parent program's frozen decision `DEC:RISK-EPISODES-USE-CHRONICLE-AND-REFLEXES` is unchanged.

## Native source warning persistence

The actual first-writer market Radar logs reveal persistent warnings, not unique daily incidents. Source-bounded counts are captured in [the source-alert persistence receipt](COUNTRY_SOURCE_ALERT_FATIGUE_RECEIPT_20261015.json).

- **CN:** 26/42 recorded source rows have `alert=true`. The latest 9/9 source observations since Sep23 have `alert=true`; the longest contiguous **recorded row** run is 18 from source session Sep09 through Oct15, with gaps in calendar days.
- **HK:** 14/47 `alert=true`; since Sep23, 11/14 source observations have `alert=true`. Longest contiguous **recorded row** run: 11 from Sep24 through Oct13; later Oct14/15 native Radar Caution/alert false while local measured Market State remains Risk-off.
- **CA:** 0/51 native model alerts, latest source observation Oct08; absence of alert is not fresh all-clear.
- **US:** 0/67 native model alerts; latest Oct14 emitted gated Caution while ungated Risk-off, indicating a separate model threshold and market state.

These are only the **recorded** forward-log observations (not all due exchange sessions), and their `alert` flags are not accepted customer deliveries or independently graded outcomes. They do show why a naïve daily push would produce chronic red-notification fatigue.

## Canonical Chronicle source boundary — concrete code finding

1. The frozen architecture `agentos/decisions/DEC-RISK-EPISODES-USE-CHRONICLE-AND-REFLEXES.md`, blob `33df7dddcab2c851c2e381b2ba4dcd838adeb2bf`, assigns **settled market risk episode transitions to Chronicle**, **bounded firing evidence to the existing Reflex Registry**, and **realized grading to QLedger/Evaluation OS**. No new generic episode database, intraday forward-log writer or second notification queue.
2. Current `engine/chronicle/adapters.py` blob `93589d594fd78889222a1a6234a9683f8e6a9451`, `adapt_risk_band()` reads ONLY `data/risk_radar/forward_log.jsonl` (the U.S. Radar log); it emits `risk_band` events only on a changed **U.S.** `state`, source refs `risk_radar_forward_log#<date>`. It does NOT observe country Radar logs and does NOT currently supply CN/HK episode identities.
3. `engine/chronicle/spine.py` blob `c47ffb69f27200a30ef8e33baaf7934ec9f16237` registers only `risk_band` (and `regime_flip`) for this domain, and `REBUILD_SOURCES` lists the U.S. Radar forward file, **not** `data/risk_radar_intl/cn_forward_log.jsonl`, `hk_forward_log.jsonl`, or `ca_forward_log.jsonl`. The module explicitly requires the tuple be extended whenever an adapter's immutable source set grows, else byte-identity rebuild proofs become invalid.
4. `engine/chronicle/state_log.py` blob `d04d53909481095e644cc6b390614b98460d11ca` captures an aggregate `intl_risk.em_stress_state` for context, but expressly states that risk-band transitions are derived from the U.S. Radar log, not this state-log field. A generic international stress string is not a substitute for source-native CN/HK Radar episode transitions.
5. `engine/chronicle/schema.py` blob `53cf81e96a73a91ce47c3d6ab3c09aa199361a0d` restricts `SOURCES` and `KINDS`; any new country-episode adapter or extension requires an explicit owner-reviewed schema/identity decision. Do not sneak an unregistered `risk_band_intl` into the event stream or alter existing U.S. event IDs.

**Finding:** the durable owner **exists and is operational for U.S. risk-band flips**; **country Radar episode derivation is not yet implemented**. Architecture freeze is a target ownership assignment, not a receipt that cross-country episodes are already shipping.

## Exactly scoped native owner follow-on, not a competing event store

A Chronicle source-owner extension, subject to registered sources/review, should:

- Observe **settled**, correct-market, increasing native country Radar source sessions and retain their original `logged_at` as evidence separate from event/effective time. Do not advance the original first-writer ledgers or synthesize new historical issue times.
- Decide whether the existing `risk_band` event type can be extended with a market-scoped `source_ref` (e.g., namespace of market and original session) without changing existing U.S. identities, or whether a specifically registered new source is needed.
- Bind immutable country forward-log **source hashes** and include all added source files in `spine.REBUILD_SOURCES` and the manifest; preserve deterministic fully regenerable event ID and changed-vintage tests. False/missing/stale data must not generate calm/resolved event.
- Separate **onset, material worsening, persistence, first qualifying source availability, unknown-data interruption, recovery candidate and independently qualified resolution**. Multiple consecutive `alert=true` rows during one active condition do not authorize separate pushes. Exact per-market thresholds/hysteresis/recipient policy require preregistration, not a global 2-of-N rule.
- Preserve mixed regional semantics: Hong Kong's measured RISK_OFF can coexist with native Radar CAUTION. Neither China Radar risk-off nor Hong Kong elevated automatically means U.S. transmitted stress.
- Gate actual notifications through the **existing** Reflex/Alerts delivery and subscription/entitlement owner. Count accepted issuer publication, transport delivery and user acknowledgment separately. Financial risk sizing/selection remains disabled.

## Product acceptance before any "early warning" claim

Reconstruct the **October 13** CN/HK native source issue, actual publisher availability, existing source/Chronicle episode state, the correct region-specific expected session, alert materiality and original subscriber channel. Show when a user *could have* been warned vs when any message **actually** reached a connected user; no post-hoc click or inferred delivery is accepted. Include ordinary pullbacks, sustained warning windows and recovery/stale-source negative controls.

**No code/ledger edits or retrospective fitting here.** This memo is a research audit of existing immutable records/registered code and an owner-bound scope definition. It does not implement Chronicle country events, clear #8132's review hold or satisfy customer-facing production acceptance.