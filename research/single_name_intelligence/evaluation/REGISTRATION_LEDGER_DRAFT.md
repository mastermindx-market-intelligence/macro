# SNI evaluation registration ledger (R1-gated draft)

## Purpose

This is the SNI-local DRAFT contract for the immutable evaluation loop
commissioned under Single-Name Intelligence (SNI, commission 8659). It
specifies an append-only, hash-chained JSONL ledger that records
count-once family registration (A26), immutable published probabilities
with reproducible replay (A27), distinct pending / unpriceable /
censored / matured outcome states (A28), proper scoring only against
caller-supplied frozen baselines (A29), and NO-GO persistence for a
failed family (A30).

The module `sni_eval_ledger.py` CONSUMES the qledger / Evaluation
owner's vocabulary. It does not replace qledger, does not mint issuer
or security identifiers, and does not originate any probability. Family
ids, forecast ids, and baseline ids are caller-supplied opaque strings
owned by Stock Identity / Data OS.

Authority flags stay false everywhere this draft writes them:
`rank_authority`, `gate_authority`, `size_authority`, `signal_authority`,
`escalation_authority`, `trade_authority`. A payload that carries any of
those keys is refused. Nothing in this ledger feeds a ranker, gate,
sizer, signal, escalation, or trade path.

## Row kinds and the chain

Row kinds, in the only order a family can grow:

1. `REGISTER` — count-once preregistration of a family key.
2. `BUDGET` — declared trial cap for a family_id.
3. `PUBLISH` — immutable probability for a forecast_id, or `ABSTAIN`
   with a named reason. Each counts as one trial against the budget.
4. `RESOLVE` — terminal outcome state for a published forecast.
5. `SCORE` — descriptive Brier mean against a frozen caller baseline.
6. `NOGO` — family is finished; later `PUBLISH` is refused.

Every JSONL row is:

```
{seq, kind, written_at_utc, payload, prev_hash, row_hash}
```

`row_hash` is sha256 of the canonical JSON of the row without
`row_hash`. `prev_hash` is the previous row's `row_hash`, or `null` on
the first row. `append` writes one line and fsyncs. `verify_chain`
recomputes every hash and prev link. A tampered middle line is a
violation.

Replay invariant (A27): `state()` rebuilt from scratch by folding every
row equals the incremental fold maintained on `append`, and equals
`replay(path)` on a freshly opened `EvalLedger`. That is the one
invariant replay must reproduce.

## Count-once (A26)

`REGISTER` payload: `{family_id, protocol, version, split, h, prereg_digest}`
with `prereg_digest` a 64-char lowercase hex sha256.

Key = `(family_id, protocol, version, split, h)`. A second `REGISTER`
of the same key raises `ALREADY_REGISTERED` and is not written.
`registered_count()` is the number of distinct keys. A changed protocol,
version, split, or `h` is a new key.

## Budgets precede trials

`BUDGET` payload: `{family_id, declared_trials}` with `declared_trials`
an integer `> 0`. It must precede any `PUBLISH` or `ABSTAIN` for that
family (`BUDGET_REQUIRED`). Each `PUBLISH` and each `ABSTAIN` consumes
one trial. The `(n+1)`th trial raises `BUDGET_EXCEEDED` and is not
written. A second budget for the same family raises `DUPLICATE_BUDGET`.

## Immutable publication and replay (A27)

`PUBLISH` payload: `{forecast_id, family_id, p, inputs_digest,
published_at_utc, horizon_end_utc}` with optional `declared_reason`.
`p` is a float in `(0, 1)`. The family must already be registered (any
key whose `family_id` matches).

A second `PUBLISH` with the same `forecast_id` raises
`IMMUTABLE_PUBLICATION` whether or not `p` differs. Outcome arrival is
a later `RESOLVE` row; it never rewrites the published `p`.

`p` exactly `0.5` with no non-empty `declared_reason` raises
`DEFAULT_PROBABILITY_REFUSED` (A25: no silent 50/50). The same `p`
with a named `declared_reason` is accepted.

`ABSTAIN` payload: `{forecast_id, family_id, reason}` with non-empty
reason. A forecast_id may not be both abstained and published
(`ALREADY_ABSTAINED` / `ALREADY_PUBLISHED`).

## Four outcome states and their transitions (A28)

A published forecast starts `PENDING`. `RESOLVE` moves it to exactly
one terminal state. There is no reverse edge and no edge between
terminals.

```
                    PUBLISH
                       |
                       v
                   PENDING
                  /   |    \
                 /    |     \
                v     v      v
        UNPRICEABLE  CENSORED  MATURED
        outcome=null outcome=null outcome in {0,1}
                         observed_at_utc >= horizon_end_utc
```

- `MATURED` requires `outcome` in `{0, 1}` and `observed_at_utc >=
  horizon_end_utc` (`MATURED_OUTCOME_REQUIRED`, `HORIZON_NOT_REACHED`).
- `CENSORED` and `UNPRICEABLE` require `outcome` `null`
  (`OUTCOME_FORBIDDEN`).
- A second `RESOLVE` of the same forecast_id raises `ALREADY_RESOLVED`.
- `RESOLVE` is accepted only from `PENDING` (`NOT_PENDING`,
  `UNKNOWN_FORECAST`, `INVALID_RESOLVE_STATE`).

`state()` exposes the four states distinctly: unresolved publications
remain in `published` and out of `resolved` (`PENDING`); resolved ids
map to `UNPRICEABLE` | `CENSORED` | `MATURED`.

## Proper scoring vs frozen baselines (A29)

`brier(ledger, family_id)` is the mean of `(p - outcome)^2` over
`MATURED` forecasts of that family only. It is a DESCRIPTIVE residual
statistic, never causal, never "news impact".

`SCORE` payload: `{family_id, baseline_id, baseline_digest,
scored_forecast_ids, brier, baseline_brier, n, descriptive_only}`.
`descriptive_only` must be `true`. `scored_forecast_ids` is the sorted
list of every matured forecast_id for the family. The module recomputes
Brier and refuses `BRIER_MISMATCH` unless the payload `brier` matches
within `1e-12`. A scored id that is not `MATURED` raises `NOT_MATURED`.
`n` must equal the matured count (`N_MISMATCH`, `NO_MATURED_FORECASTS`,
`SCORED_IDS_UNSORTED`, `DESCRIPTIVE_ONLY_REQUIRED`).

The baseline is caller-supplied (`baseline_id`, `baseline_digest`,
`baseline_brier`). This module never constructs a baseline.

Hit/return grading is not probabilistic forecast support until an accepted bridge exists.

## NO-GO (A30)

`NOGO` payload: `{family_id, reason}`. Once written, any later
`PUBLISH` (or `ABSTAIN`) for that family raises `FAMILY_NOGO`. There is
no un-NOGO row kind. A failed model stays NO-GO; only a new
`family_id` can proceed (`ALREADY_NOGO` on a second NOGO of the same
family).

## Refusal code table

Codes raised by `LedgerRefused.code`. A-cases are the commission
acceptance cases.

| Code | A-case | When |
|---|---|---|
| `ALREADY_REGISTERED` | A26 | Second `REGISTER` of the same key; row is not written. |
| `BUDGET_REQUIRED` | — | `PUBLISH` or `ABSTAIN` before `BUDGET`. |
| `BUDGET_EXCEEDED` | — | Trial count would exceed `declared_trials`. |
| `DUPLICATE_BUDGET` | — | Second `BUDGET` for the same family_id. |
| `IMMUTABLE_PUBLICATION` | A27 | Second `PUBLISH` of the same forecast_id. |
| `REPLAY_MISMATCH` | A27 | Incremental `state` differs from a from-scratch rebuild. |
| `DEFAULT_PROBABILITY_REFUSED` | A25 | `p == 0.5` with no non-empty `declared_reason`. |
| `ALREADY_RESOLVED` | A28 | Second `RESOLVE` of the same forecast_id. |
| `MATURED_OUTCOME_REQUIRED` | A28 | `MATURED` without outcome in `{0, 1}`. |
| `OUTCOME_FORBIDDEN` | A28 | `CENSORED` / `UNPRICEABLE` with a non-null outcome. |
| `HORIZON_NOT_REACHED` | A28 | `MATURED` with `observed_at_utc` before `horizon_end_utc`. |
| `NOT_PENDING` | A28 | `RESOLVE` of a forecast that is not pending. |
| `UNKNOWN_FORECAST` | A28 | `RESOLVE` of a forecast_id that was never published. |
| `INVALID_RESOLVE_STATE` | A28 | `state` not in `{UNPRICEABLE, CENSORED, MATURED}`. |
| `BRIER_MISMATCH` | A29 | Payload `brier` differs from the recomputed mean by `> 1e-12`. |
| `NOT_MATURED` | A29 | A scored forecast_id is not `MATURED` for the family. |
| `DESCRIPTIVE_ONLY_REQUIRED` | A29 | `SCORE` without `descriptive_only: true`. |
| `SCORED_IDS_UNSORTED` | A29 | `scored_forecast_ids` is not sorted. |
| `N_MISMATCH` | A29 | `n` or the scored id list is not exactly the matured set. |
| `NO_MATURED_FORECASTS` | A29 | `SCORE` / `brier` with no matured forecasts. |
| `FAMILY_NOGO` | A30 | `PUBLISH` or `ABSTAIN` after `NOGO` for that family. |
| `ALREADY_NOGO` | A30 | Second `NOGO` for the same family_id. |
| `AUTHORITY_FLAG_REFUSED` | — | An authority key is present in the payload. |
| `FAMILY_NOT_REGISTERED` | — | Family_id has no `REGISTER` key. |
| `ALREADY_PUBLISHED` | — | `ABSTAIN` of a forecast_id that was published. |
| `ALREADY_ABSTAINED` | — | `PUBLISH` of a forecast_id that was abstained. |
| `UNKNOWN_KIND` | — | `append` kind is not a row kind. |
| `INVALID_PAYLOAD` | — | Missing or ill-typed required field. |
| `INVALID_PREREG_DIGEST` | — | `prereg_digest` is not 64 lowercase hex. |
| `INVALID_INPUTS_DIGEST` | — | `inputs_digest` is not 64 lowercase hex. |
| `INVALID_BASELINE_DIGEST` | — | `baseline_digest` is not 64 lowercase hex. |
| `INVALID_P` | — | `p` is not a finite float in `(0, 1)`. |
| `INVALID_DECLARED_TRIALS` | — | `declared_trials` is not an integer `> 0`. |
| `EMPTY_REASON` | — | Empty `reason` on `ABSTAIN` or `NOGO`. |

## What this is not

- This is an R1-gated draft on a lane branch. It is not a pull request
  and it is not accepted Evaluation OS.
- It is SNI-local. It consumes qledger vocabulary; it does not replace
  qledger, the Evaluation owner, or any owner named in the commission
  (Data OS identity, Company Event/Earnings, FIF, Capital Structure,
  Stock Identity, Options, Research Vault).
- No forecasts exist. This ledger stores caller-supplied synthetic
  fixtures in tests. It does not generate, mint, or guess a probability
  or a canonical identifier.
- It does not claim that hit/return grading is probabilistic forecast
  support. That bridge is out of scope until an accepted bridge exists.
- Residual and stress statistics recorded here are descriptive. They
  are never written as causal effects or as news impact (A24).
