# P04 v2 pre-registration draft (SNI S2 conditional event-response)

This is an SNI-local DRAFT contract. It consumes owner-supplied values from
Data OS identity, Company Event/Earnings, FIF, Capital Structure, Stock
Identity, Options, Research Vault, and qledger/Evaluation. It does not
re-implement those owners. Identity ids are caller-supplied opaque strings;
unknown identity stays UNRESOLVED / null.

**v2 is NOT registered and has NO outcome.** Status is DRAFT.
`registered` is false. The S0 protocol register is not edited. Nothing is
sealed.

Owner: seat/S0. Drafted by grok-4.6 lane A3 under seat 508c3757 at
2026-10-12T04:49:00Z.

## Purpose

Replace the retired P04 v1 TUNE split with a successor version whose
price/return inputs are vintage-pinned, whose split identity includes that
vintage, and whose labels distinguish a thin-but-clustered descriptive family
from an abstention. P04 remains the results family on the US counting clock.
This draft is the prereg text the seat can register after review. It is not
itself a registration, a seal, or a result.

## What retired v1 TUNE

Facts only, from the v1 run receipt and trial-ledger retirement row.

- Protocol P04 v1, split TUNE, contamination class `information_leak`.
- Composite split digest
  `a3b15693e32d9d2f44e5e4a78f90bdfb3ac2afece84b5691be12e03685804ed6`
  (v1 construction: sha256 of the joined per-horizon TUNE membership
  hashes for h in 5, 21, 63).
- Detected at 2026-10-11T21:59:47+00:00.
- Offending series: `close` and `close_price`.
- First offending dates: BABA 2026-06-11 (1 step above tolerance), SPY
  2026-06-18 (2 steps above tolerance).
- v1 still loaded and printed TUNE windows after detection, labelled
  non-confirmatory. The successor named in that receipt was "P04 v2 — not
  drafted; owner = seat/S0". This file is that draft.
- Per Split and Contamination Law §8 step 5, a successor of a retired TUNE
  does not refill TUNE. v2 TUNE is empty. v1 TUNE members stay retired and
  are never reused. v2 is declared untuned. TRAIN is never retired.

## Vintage rule

Every price/return input to a split is read from a vintage pinned at or
before the split's decision timestamp (`as_of_utc`). A vintage step is any
revision of a value already used by an earlier decision. On a
`close`/`close_price` pair the adjustment factor is `q_t = close_t /
close_price_t`, and a step is the dimensionless relative move `|q_t /
q_{t-1} - 1|`. Tolerance is `STEP_TOLERANCE = 1e-6`, inherited from
`s1_infoleak.vintage_series` / `detect`.

A step inside the split window with absolute size above that tolerance
retires the split automatically, class `information_leak`, **before any
outcome is read**. The detector runs before outcomes are loaded: detection
clock precedes outcome clock.

Facts known only after `as_of_utc` are never treated as known at that
instant. A residual or stress statistic computed after a clean vintage check
is descriptive. It is not causal. Series with no `close`/`close_price` pair
are `VINTAGE_UNVERIFIABLE`: disclosed, not retired.

## Split identity

The v2 composite split digest is sha256 of the canonical JSON object

`{protocol, version, split_name, member_episode_ids (sorted), as_of_utc,
vintage_manifest (sorted path → sha256)}`.

Canonical JSON means `sort_keys=True`, separators `(',', ':')`, UTF-8.
`member_episode_ids` are caller-supplied opaque ids. `vintage_manifest` is
the pinned input blobs at `as_of_utc`. Membership is immutable once sealed
(A23). Any change mints a new digest and a new version; a sealed digest is
never rewritten.

No v2 digest is minted in this draft. The seat binds `as_of_utc`, membership,
and the vintage manifest at seal. The v1 digest above identifies only the
retired TUNE split.

## Label semantics

Four labels, first match wins. `min_episodes` is 153, carried from v1
`minimum_evidence.episodes`.

| Condition | Label |
|---|---|
| episodes = 0 | `ABSTAIN_NO_EPISODES` |
| episodes > 0 and date clusters < 2 | `ABSTAIN_INSUFFICIENT_CLUSTERS` |
| date clusters ≥ 2 and episodes < 153 | `DESCRIPTIVE_ONLY` |
| date clusters ≥ 2 and episodes ≥ 153 | `TESTED` |

`DESCRIPTIVE_ONLY` is not an abstain. The v1 wording "CI NOT ESTIMABLE
(cluster-N < 2)" is wrong for that case: cluster-N is already at least 2, so
an interval may be printed as a descriptive statistic. It does not make the
family `TESTED`. An unestimable family abstains with a named reason
(`ABSTAIN_NO_EPISODES` or `ABSTAIN_INSUFFICIENT_CLUSTERS`). It never fills
with a 0.5 default (A25).

## Horizons and graded legs

Horizons are the v1 set: 5, 21, 63 trading sessions.

Graded legs are copied from v1: only the Alibaba ADR leg
`adr_baba (SEC:US-XNYS-BABA, MARKET_US)` is graded. The Tencent issuer group
and both HK legs (9988, 0700) are census-only: counted and abstained, never
graded. Those identifiers are owner-supplied strings copied from the v1
prereg; this draft does not mint them.

Frozen baselines stay the v1 trio (always-long; sign of trailing-63 excess
at D(s); pooled TRAIN prior) plus the unregistered challenger column, which
stays NOT ESTIMABLE until hierarchy legs above own-name are registered.
Proper score remains NOT SUPPORTED.

Declared budget floor is 13 (carried v1 `literal_n`). The itemized grid is
12 configs (4 baselines × 3 horizons). Budget is a floor, never a cap.

## What is NOT claimed

- v2 is NOT registered.
- v2 has NO outcome. `outcome_free` is true. No trial is run from this
  draft. No window return, hit rate, or interval is produced here.
- All six authority flags stay false. A caller that sets any of them true
  is refused (raise). This draft does not feed a ranker, gate, sizer,
  escalation path, or trade path.
- The S0 register is not edited. REG §6 has no v2 row. Nothing is sealed
  via `sni_seal`.
- v2 TUNE is empty. This draft does not restore, refill, or re-rank the
  retired v1 TUNE members.
- Identifiers are not derived from a ticker, name, code, or CIK.
- Nothing here is confirmatory evidence.

## Registration checklist

The registration gate is not met. Registration requires, in order:

1. Seat review of this draft.
2. An S0 register §6 row for P04 v2 (written by the seat, not by this lane).
3. Seal via `sni_seal`, binding `as_of_utc`, sorted `member_episode_ids`,
   and the vintage manifest (path → sha256).
4. An immutable budget row before any trial, with declared budget at least
   the carried v1 `literal_n` of 13.

Until those four are done, P04 v2 remains a draft: not registered, unsealed,
and without an outcome.
