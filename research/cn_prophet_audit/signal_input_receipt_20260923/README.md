# Native China daily-input receipt preservation

MISSION_COMPLETE: false. BUILT_NOT_PROVEN. Same Chairman-authorized China leadership mission; this slice restores existing evidence across serialization, not a new entry policy.

Authority: Mastermind protected master `4c1b3d389286df2a4b5b98a4d4491f2c8a1263f2`, compatible Skillpack 1.0.1. Original branch `claude/cn-signal-input-receipt-20260923`, diagnostic head `8016d09418d25eed5d171247254dd33444c4dee4`, source base `88a3f1cfd18f391d2802e9086dc00f6fe5545607`.

## Capability

The China library already stamps `input_asof` from its daily close. Both signal_gate serializers discarded it; the existing China consumer requires that date independently of the analytical three-day `asof` bucket. The repair passes the explicit canonical YYYY-MM-DD receipt through compact and buy_signal. Missing stays absent; explicit null, invalid dates and unsupported types stay unknown. No clock, bucket, exchange calendar or validity window is substituted.

The same existing serializers feed native per-stock JSON and board enrichment. The consumer can now distinguish same-session data from stale/future/missing receipts after JSON serialization. This is not proof that every prior in-memory board was stale, a performance claim, a new recommendation, or the complete native-China Theme EntryContext adapter.

## Scope and compatibility

Only `engine/signal_gate.py`, two already-registered test suites and this evidence folder change. Existing field sets remain byte-for-byte equivalent for inputs without the new explicit receipt. is_buyable and tier/rank/size logic are unchanged. No new store, calendar, queue, publication path, or U.S.-receipt relabel.

Current main `f84d9c882b7fabf87835e6c630ad9b4ab1f69fca` added #7825 validity_block after pickup. That appended next-session block is not edited or replaced. Current integration proof must preserve it. #6992 retains the native library source and #7664/#7669 retain theme entry/recommendation integration.

## Validation and continuation

Original 12 failing / 7 passing reproduction remains dated. Initial repaired suites: 70 passed. Expanded five-owner regression: 200 passed, including canonical date/type failures, missing/null behavior, correction independence, eligibility invariance, and actual serializer -> JSON -> China enrichment/freshness behavior. No browser claim is owed by this backend-only slice; authentic publish/readback is still required for live proof.

Implementation proceeded directly because the bounded repair was smaller than worker framing and review overhead. An independent read-only source review is required before release. Published #7567 cards and #7753 context are not reimplemented here. Remaining parent work includes native entry joins, emerging/ENTER continuation, CPU/memory coverage and production acceptance.

The earlier metadata-write timeout was reconciled on the same carrier: no matching process and unchanged metadata, followed by a verified same-carrier update. No source effect is uncertain. Do not reset/recreate the branch or reapply the historical prospective patch over the already-present tests.
