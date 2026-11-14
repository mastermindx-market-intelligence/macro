# Historical X post and publisher defects — 2026-11-14 UTC

## Evidence boundary

Source snapshot: `mastermindx-market-intelligence/macro` at
`9b3759e` (`marketing-publish: outbox run 2026-11-14T06:01Z`). This is a
**committed** replay, not an online crawl of X. Read
`data/marketing/outbox/items.jsonl` as immutable emitted versions and
`data/marketing/outbox/status_ledger.jsonl` as append-only state changes; fold
the **last** transition per ID. `posted` means the publisher recorded a Buffer
acceptance/booking receipt. It is **not** independently observed X visibility.

- 6,530 item rows; 6,515 distinct item IDs; 6,458 IDs with a terminal/latest
  ledger transition.
- Latest ledger state: 2,457 `posted`, 3,923 `quarantined`, 60 `failed`,
  18 `approved` (other IDs have no transition here).
- Historical quarantine reasons include 1,302 approval-desk, 508 vintage voice
  law, 485 expired-session-language, 460 clock, 340 expired-stale-wire. These
  are **causes**, not proof that the blocking guard is wrong: expiry and
  unsupported factual assertions are reasons to hold posts.

## Reproduced defects and repair status

### 1. Hot Tape models copy the sign of a negative data value into a decline verb

180 `posted`-status texts contain a direct decline verb followed by a negative
number, e.g. `ob-2026-11-10-71b90ef5b7`: `GE Vernova $GEV falls -5.35% ...`.
175 are Hot Tape posts with `source.llm.mode` `llm`/`llm_repair`; the numeric
validator dropped the sign when checking grounded magnitudes. The *actual
model prompt* included three archived winning examples that taught this form.

Historical replay of 401 Buffer-accepted Hot Tape rows carrying a FactPacket,
using `hot_tape_wire.llm_packet` and the revised language check: 177 flagged;
175 for redundant signed declines, another two for missing percent symbols on
named peer moves. No posts were mutated or resent for this audit.

**Repaired in this source change:** keep the raw corpus as archival evidence,
use human-sounding examples in the live prompt, safely strip only redundant
minus signs following a decline verb, require percentage units for source-typed
daily/median/peer moves and reject a daily directional assertion that conflicts
with the FactPacket. Preserve numeric and source provenance checks and the
deterministic fallback. No synthetic prices or opinions are introduced.

### 2. The per-kind editorial gate was treated as globally disarmed

`config/marketing.yml` arms `value_gate.enforce: true` for enumerated post
kinds, including `breaking`. However both `outbox.stamp_value_gate` (audit
metadata) and the admin Intelligence Desk approval path called
`_value_gate_enforced(cfg)` **without the kind**. That function intentionally
returns `False` for a kind-less query when `enforce_kinds` is configured.
Consequences:

- Every stamped `source.value_gate.enforced` incorrectly read `false`, even for
  a checked kind.
- Admin Intelligence approval could enqueue a value-gate-`abstain` breaking
  post, because its final refusal branch was never armed under production-style
  per-kind configuration.

**Repaired in this source change:** bind the actual `kind` to both checks.
Negative-control tests show unarmed kinds still receive nonblocking verdicts.

## Confirmed follow-up defects; not yet claimed fixed

### 3. The nightly plan loses inspectable fact evidence

The committed 2026-11-13 plan has 39 queued planned rows. 38 contain numeric
copy but **none** persist `facts`, `source_facts` or `numbers_whitelist` on the
post row. Separately, 423 latest quarantines begin
`approval-desk: number_sanity: decisive posture`, and sampled rows have only
plan IDs, ticker, angle and a chart ID in `source`, not a fact packet.
Examples: `ob-2026-11-13-b0d600e779` (GDPNow and median CPI) and
`ob-2026-11-13-3ce44540ad` (an insider purchase). The guard was correct to
hold claims for which it received no source evidence; disabling it or allowing
unverified price levels would be a regression. Next code lane: retain the
verified producer fact snapshot through plan serialization into the canonical
outbox, with source timestamp and typed units, and replay these 423 examples
before altering the guard. The separate armed/held editorial-compiler carriers
must be respected.

### 4. A short press relay can pass as reader value

`ob-2026-11-13-ba8928382c` was queued/recorded `posted` as a 13-word Bitcoin
headline with no image, analysis or source citation visible in the copy. Its
`source.value_gate.verdict` was `pass` because the rubric counted a dollar
number and an underlying source URL as enough. The gate tests structural proof,
not the depth of insight. Also
`ob-2026-11-13-295a9f32f6` relayed an unconfirmed Nvidia succession report;
its own source class was `hearsay`. These are editorial-risk examples, **not**
independent findings that those market/news claims are false. Next lane: ground
source authority, firsthand versus hearsay status and specific incremental
analysis before press publication; distinguish attributed reported claims from
confirmed events. Do not invent catalysts or recommendations.

### 5. Unresolved context briefs spend work before the dependency gate

62 items end `quarantined` because their source alert was unresolved
(`orphaned context brief`). The sample
`ob-2026-11-13-58228ea972` had already used DeepSeek phrasing and a chart
asset before the publisher's quarantine. Move **existing** alert-resolution
preflight ahead of optional model/media creation where the producer can observe
the necessary authoritative state. Keep the publisher's final guard as the
race-safe backstop; no duplicate alert owner or retry queue.

## Safe next acceptance

1. Bind a new fact-bearing content-plan-to-outbox fixture to the original
   numbers and timestamps; prove unsupported claims remain held.
2. Backtest the press value bar against actual published/held samples, with
   quality judgments and false-positive counts before changing enforcement.
3. Prove a **new** chart/media item after the governed merge and deployment;
   neither this audit nor a green CI job proves production X delivery.
