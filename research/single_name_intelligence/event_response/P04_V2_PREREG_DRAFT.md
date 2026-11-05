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
price/return inputs are vintage-pinned per episode, whose split identity
includes that vintage, and whose labels distinguish a thin-but-clustered
descriptive family from an abstention. P04 remains the results family on
the US counting clock. This draft is the prereg text the seat can register
after review. It is not itself a registration, a seal, or a result.

## What retired v1 TUNE

Facts only, from the v1 run receipt and trial-ledger retirement row, cited
to the S0 register §7 Retirement Log (origin/claude/sni-s2-ship-20261012
@ 050a5637515a; pending merge of PR #8893).

- Protocol P04 v1, split TUNE, contamination class `information_leak`.
- Composite split digest
  `a3b15693e32d9d2f44e5e4a78f90bdfb3ac2afece84b5691be12e03685804ed6`
  (v1 construction: sha256 of the joined per-horizon TUNE membership
  hashes for h in 5, 21, 63). The citation digest equals this value.
- Detected at 2026-10-11T21:59:47+00:00.
- Offending series: `close` and `close_price`.
- First offending dates: Alibaba ADR 2026-06-11 (1 step above tolerance),
  SPY 2026-06-18 (2 steps above tolerance).
- v1 still loaded and printed TUNE windows after detection, labelled
  non-confirmatory. The successor named in that receipt was "P04 v2 — not
  drafted; owner = seat/S0". This file is that draft.
- Per Split and Contamination Law §8 step 5, a successor of a retired TUNE
  does not refill TUNE. v2 TUNE is empty. v1 TUNE members stay retired and
  are never reused. v2 is declared UNTUNED. TRAIN is never retired.
- Registration still requires a v2 membership seal row in REG §6 (not
  minted by this draft).

## Vintage rule

Every episode reads its price/return inputs from the vintage pinned at
that episode's own D(s) (`vintage_rule.per_episode_pin`). `as_of_utc` is
the structured rule `{per_episode: true, format: "ISO-8601 UTC with Z
suffix", equals: "D(s) decision time", invariant: "input_vintage_utc <=
as_of_utc"}`. A loader check `check_episode_as_of` refuses a missing or
non-ISO value, a non-Z offset, an as_of that differs from D(s), or a
vintage after as_of.

A vintage step is any revision of a value already used by an earlier
decision. On a `close`/`close_price` pair the adjustment factor is
`q_t = close_t / close_price_t`, and a step is the dimensionless relative
move `|q_t / q_{t-1} - 1|`. Tolerance is `STEP_TOLERANCE = 1e-6`.

A step inside the split window with absolute size above that tolerance
retires the split automatically, class `information_leak`, **before any
outcome is read**. Independently, `cross_vintage_detector` compares every
bar USED by any episode (any split, TRAIN included) across every available
vintage up to the evaluation vintage. `|relative difference| > 1e-6`
marks that episode `VINTAGE_UNVERIFIABLE` and excludes it (listed with
reason, never silently dropped). `train_read_ceiling`: a TRAIN read from
a vintage dated after the last TRAIN D(s) is REFUSED. TRAIN is never
retired as a split; TRAIN episodes are still excluded per the
cross-vintage detector.

Facts known only after `as_of_utc` are never treated as known at that
instant. A residual or stress statistic computed after a clean vintage
check is descriptive. It is not causal. Series with no `close`/`close_price`
pair are `VINTAGE_UNVERIFIABLE`: disclosed, not retired.

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

Four labels, first match wins. `min_episodes` is 153 (one-sided significance
level 0.05, power 0.80, hit rate 0.60 vs 0.50; REG common-rules power formula). That sample-N abstention is SEPARATE from trial N
(`declared_budget_floor` 6). Family N is honest-N after IL §3 collapse and
after clock abstention (episodes on non-graded clocks or
`VINTAGE_UNVERIFIABLE` are not counted).

`label_order` lists all four labels in evaluation order.
`abstention_ladder` lists only the ABSTAIN_* tokens.

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
(`ABSTAIN_NO_EPISODES` or `ABSTAIN_INSUFFICIENT_CLUSTERS`). Baseline and
challenger "NOT ESTIMABLE" map to `ABSTAIN_INSUFFICIENT_CLUSTERS`. There is
no fifth family label. A family never fills with a 0.5 default (A25).
`TESTED` requires `min_clusters` 2.

## Horizons and graded legs

Horizons are the v1 set: 5, 21, 63 trading sessions.

The graded leg is a caller-supplied opaque id with role "Alibaba ADR leg,
MARKET_US", bound at seal from Stock Identity (cite REG §6 line 192). The
Tencent issuer group and the HK legs of both issuer groups are census-only:
counted and abstained, never graded. This draft does not mint canonical
issuer or security identifiers from a ticker, name, code, or CIK.

Frozen baselines stay the v1 trio (always-long; sign of trailing-63 excess
at D(s); pooled TRAIN prior) plus the unregistered challenger column.
Challenger and inestimable pooled-prior cells map to
`ABSTAIN_INSUFFICIENT_CLUSTERS`. Proper score remains NOT SUPPORTED.

Tuning mode is UNTUNED. All 12 cells (P04 × h∈{5,21,63} × baselines i..iii
+ challenger row) are reported under the family-wise budget haircut.
`selectors` is empty. TEST-conditional selection is REFUSED.

Declared budget floor is 6, sourced from SEAL_AND_BUDGET.json
`declared_budget` (P04) on origin/claude/sni-s2-ship-20261012. The itemized
grid is 12 configs (4 baselines × 3 horizons). Budget is a floor, never a
cap. Trial N is SEPARATE from the 153-episode sample abstention.

## What is NOT claimed

- v2 is NOT registered.
- v2 has NO outcome. `outcome_free` is true. No trial is run from this
  draft. No window return, hit rate, or interval is produced here.
- All six authority flags stay false. A caller that sets any of them true
  is refused (raise). This draft does not feed a ranker, gate, sizer,
  signal, escalation path, or trade path.
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
3. A v2 membership seal row in REG §6 (not minted by this draft).
4. Seal via `sni_seal`, binding per-episode `as_of_utc`, sorted
   `member_episode_ids`, and the vintage manifest (path → sha256).
5. An immutable budget row before any trial, with declared budget at least
   6 (SEAL_AND_BUDGET.json declared_budget for P04).

Until those are done, P04 v2 remains a draft: not registered, unsealed,
and without an outcome.
