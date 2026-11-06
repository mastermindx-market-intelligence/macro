# ROR-1 — Qualified country Radar existed in forward records, not in the held warning adapter's source

**15 October 2026 · Research only · No release or financial authority.**
Macro main source observation: `9b255a5377385a6b0dab23850e6a6ff67714a5f1`.
Held global warning writer: [Macro #8132](https://github.com/mastermindx-market-intelligence/macro/pull/8132), unchanged Draft/HOLD at `639aaed06ce7754110d3bd6e94a0b704bb6c7760`.

## Original forward-ledger provenance (not customer delivery)

The existing `engine/risk_radar_intl.py` source blob `4ed9bdebf6e76cbf529115203ae5d8820ba07f13` emits the full **`risk_radar_intl.v1`** contract, with `schema`, `market`, native `asof`, `state`, `top_score` and source-native alert evidence. Its `snapshot(profile)` computes read-only when asked; the existing market builders `scripts/build_china.py` (blob `7a1b401f40e9db94eaec0a8d95ad683ce1799fa8`) and `scripts/build_hk.py` (blob `cfc6fc429707fadb6d0ea01666608177f82d0dfe`) call that native producer and invoke the original first-writer `risk_radar_intl_audit` ledger lane only where it is armed.

The exact committed forward ledgers all pass strict JSONL and unique increasing `asof` / native-market checks:

| Ledger | Git blob | Records | Graded older records | Latest source session |
|---|---|---:|---:|---|
| CN | `facaaeb830b2e7fb4139e10a2e998408f72de44a` | 42 | 24 | Oct 15 |
| HK | `6ce8ea457097265b5f559cdf38aa0562a128a427` | 47 | 29 | Oct 15 |
| CA | `045a9b352ccc4cc35c9d9c21299771ec4926de31` | 51 | 37 | Oct 08 |
| US | `67332ea3cf70841f0e8398fa8da2054587a2f029` | 67 | 49 | Oct 14 |

The recent source observations, including recorded time (UTC), are:

| Radar | Source session | `logged_at` UTC | Native state | Score | Engine `alert` |
|---|---|---|---|---:|---|
| China | Oct 13 | 2026-10-13 15:53:13 | **Risk-off** | 98 | true |
| Hong Kong | Oct 13 | 2026-10-13 16:23:07 | **Elevated** | 90 | true |
| China | Oct 14 | 2026-10-14 15:17:16 | **Risk-off** | 97 | true |
| Hong Kong | Oct 14 | 2026-10-14 15:50:01 | Caution | 83 | false |
| China | Oct 15 | 2026-10-15 11:55:52 | **Risk-off** | 97 | true |
| Hong Kong | Oct 15 | 2026-10-15 12:28:08 | Caution | 81 | false |
| United States | Oct 14 | 2026-10-15 05:02:39 | Caution | 87.9 | false |

The U.S. October 14 forward row also records **`state_ungated=risk-off`**, but the published native state and alert remain Caution/false. Older graded records do not prove the future utility of these most recent ungraded observations. Recorded `logged_at` is a ledger issue/recording instant, NOT proof the evidence was available earlier in a customer product or that the alert was pushed.

## Proven disconnection, without creating a second pipeline

The actual China and Hong Kong engines demonstrably produced native observations and the existing nightly ledger recorded them. The separate `data/china_market_state/latest.json` and `data/hk_market_state/latest.json` intentionally preserve reduced board `radar` projections, with **China 24/RISK_OFF** and **Hong Kong 32/RISK_OFF** as the local Oct15 measured Market States; Hong Kong's native Radar simultaneously said **Caution/81**. This is a correct difference between measured country state and Radar hazard, not a contradiction to coerce away.

However, the currently held #8132 `risk_warning_source_adapter.py` reads `data/china_regime/latest.json:risk_radar` and `data/hk_regime/latest.json:risk_radar`. Both are the **wrong source envelopes** for the native observation: the former has no such key; the latter lacks it and is not strict JSON due to a bare NaN in an unrelated field. The adapter is correct to reject them. It cannot expose these *actual* native source readings to a customer from its declared paths.

The existing `scripts/build_feeds.py` already describes those radars as render-inline and creates a supplementary `site/feeds/intl_spillover.json` by recomputing the native snapshots from committed stores. That output is **not present in the pinned Git tree**. It may be served through a different existing R2/VPS publication route; do not infer it is absent in production, or replace it with a new duplicated schedule.

**Best source-owner implementation decision to evaluate:** bind #8132's existing warning projection to the authoritative native source or an already accepted durable producer artifact, preserving native `schema`, `market`, `asof`, calendar `expected_session`, source/input-health receipts and data hash. Do not read the first-writer outcome ledger as a live operational warning endpoint, loosen JSON standards, manufacture a `risk_radar_intl.v1` wrapper around reduced board Radar, or revive unauthorized `can_force` trade authority.

## Already-issued evidence versus user-facing product

The October 13 CN Risk-off and HK Elevated source rows were **logged the day before** the U.S. October 14 selloff. This is a valid historical timestamp comparison, *not* evidence of a real-time user-visible early warning, independent forecasting success, causal China→U.S. transmission or a validated liquidation signal. The observed U.S. mixed backdrop and Asian risk-off states should remain separately scoped and dated.

The correct user-facing test is: the original market's as-issued native source is selected **once** by the owner, qualified at a legal market session/knowledge cutoff, published at the existing transport boundary, consumed by an entitled user, visible on glance tier and tied to one verifiable incident/notification lifecycle. Record source issue, producer publish, origin serve, edge serve, browser render and outbound notification/ack clocks separately.

[Machine-readable native forward ledger receipt](COUNTRY_NATIVE_ISSUED_LEDGER_RECEIPT_20261015.json) is based on unchanged Git blobs, not a newly executed financial model or live renderer. Existing Grey Deer #8132 REQUEST_CHANGES / release hold, Macro #9428 CSS design-governance red, Terminal #894 production-data transport investigation, and all refusal/effect boundaries remain intact.

**STATUS:** native producer and ledger observation confirmed; adapter-to-publication-to-entitled-user path **NOT PROVEN**.