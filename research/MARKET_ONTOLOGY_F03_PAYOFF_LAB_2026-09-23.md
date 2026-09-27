# Options payoff lab — store-host producer (W2-5a)

**Packet:** A-F03-W2-5a
**Date:** 2026-09-23
**Decision:** `DEC:F03-W2-5-PAYOFF-LAB-CHARTERED-AFTER-C0-FREEZE`

The payoff engine in `engine/options_payoff.py` had no consumer. The rows that
pointed at it were waiting on a program that is now closed and starts no
build. This packet is the producer. It does not add a page. The page is
W2-5b, and it waits until this file is actually being published.

## What the artifact is

`data/options_payoff_lab/latest.json` is one session of four index ETFs.
The schema is `mastermind.options_payoff_lab/v1`. The source is `thetadata`.
Each root carries the spot the skew ledger already records, the expiration
the skew tenor rule already picks, and four structures. Every number comes
from `engine/options_payoff.py`. This file does not price, and it does not
invent a second spot or a second expiry rule.

The file is display only. It has no rank, score, size, or trade instruction.
A missing input is a named state. It is not turned into zero.

`latest.json` is replaced each session. `history/<asof>.json` is kept.
R2 is the copy render hosts read. The directory is not part of the nightly
publish list. Only the store-host runner publishes it, with
`--dirs options_payoff_lab`.

## Frozen catalog

Roots: SPY, QQQ, IWM, DIA. One expiration per root, the listed expiration
`engine.options_skew._nearest_expiry` picks (about 30 calendar days, same
rule as the skew ledger). The contract multiplier is 100. That number is a
caller input. The chain does not carry it.

| Name | Legs |
|---|---|
| `atm_straddle` | Buy 1 call and buy 1 put at the strike nearest spot. |
| `rr25` | Buy 1 call whose delta is nearest +0.25, and sell 1 put whose delta is nearest -0.25. If a whole side has no delta, use the strike nearest 1.05 times spot for the call and 0.95 times spot for the put. The file records which rule fired. |
| `put_spread_95_90` | Buy 1 put nearest 0.95 times spot, sell 1 put nearest 0.90 times spot. |
| `call_spread_105_110` | Buy 1 call nearest 1.05 times spot, sell 1 call nearest 1.10 times spot. |

There is no collar. The engine does not support an underlying leg.

For each structure the file stores the engine's own summary, the expiry
payoff at 41 spots from 80% of spot to 120% of spot, three scenario grids
(0, 7, and 21 days forward; spot shocks -10%, -5%, 0, +5%, +10%; no vol
shock), the greeks drift at those same three days, the assumption block,
and the evidence recipe.

## Store-host receipt

Read-only run against `/Users/chriswong/theta-ops-wt/data/thetadata_eod`.
Nothing was written under `/Users/chriswong/skew-ops-wt` or
`/Users/chriswong/skew-ops-state`, and `publish_r2` was not called.

Session date: **2026-09-21**. Counts: 4 roots priced, 16 structures built,
0 structures withheld. `latest.json` is 407,756 bytes.

| Root | Spot | Expiration | Tenor (days) |
|---|---:|---|---:|
| SPY | 773.50 | 2026-10-23 | 32.0 |
| QQQ | 741.47 | 2026-10-23 | 32.0 |
| IWM | 285.58 | 2026-10-23 | 32.0 |
| DIA | 519.78 | 2026-10-23 | 32.0 |

The 25-delta rule fired on the delta for every risk-reversal leg. No side
had to fall back to moneyness. Strikes below are the ones the rules picked.

| Root | Structure | Max loss | Max gain | Breakevens |
|---|---|---:|---|---|
| SPY | atm_straddle | -2291.5 | UNBOUNDED | 750.085, 795.915 |
| SPY | rr25 | -75387.0 | UNBOUNDED | 753.87 |
| SPY | put_spread_95_90 | -155.5 | 3844.5000000000005 | 733.445 |
| SPY | call_spread_105_110 | -88.0 | 3712.0 | 812.88 |
| QQQ | atm_straddle | -3151.0 | UNBOUNDED | 709.49, 772.51 |
| QQQ | rr25 | -71447.5 | UNBOUNDED | 714.475 |
| QQQ | put_spread_95_90 | -301.0 | 3599.0 | 700.99 |
| QQQ | call_spread_105_110 | -275.0 | 3225.0 | 782.75 |
| IWM | atm_straddle | -1150.5 | UNBOUNDED | 274.495, 297.505 |
| IWM | rr25 | -27559.5 | UNBOUNDED | 275.595 |
| IWM | put_spread_95_90 | -99.0 | 1301.0000000000073 | 270.01 |
| IWM | call_spread_105_110 | -97.00000000000001 | 1303.0 | 300.97 |
| DIA | atm_straddle | -1570.0 | UNBOUNDED | 504.3, 535.7 |
| DIA | rr25 | -50648.5 | UNBOUNDED | 506.485 |
| DIA | put_spread_95_90 | -107.50000000000003 | 2392.5 | 493.925 |
| DIA | call_spread_105_110 | -92.99999999999999 | 2507.0 | 546.93 |

Max loss and max gain are the engine's expiry bounds for that structure.
`UNBOUNDED` means the payoff does not level off. A short put's bound at a
spot of zero is large; that is the engine's number, not a position limit.

Null states: **WIDE_SPREAD, 2 legs.** DIA put at 470 (bid 0.54, ask 0.75)
and DIA call at 572 (bid 0.04, ask 0.15). Both are printed on the leg.
No other null code appears. No root was skipped.

The emit leg, reading only that data file, wrote
`site/options_payoff_lab/latest.json` with `ledger_asof` 2026-09-21,
`accrual_state` `ledger_only`, and `n` 16. `ledger_only` is correct here
because this second command did not accrue. A run that accrues and emits
in one process records `accrued_today`. A missing data file records
`absent` and `n` 0.

## The two legs

`python -m scripts.build_options_payoff_lab --accrue` runs on the store
host. It takes the latest session date the same way the skew ledger does.
It writes the data files above. If the store does not resolve, it prints
`::warning title=options-payoff-lab-source::` and exits 0. It does not
write an empty file over a previous good one.

`python -m scripts.build_options_payoff_lab --emit` runs on render hosts.
It reads `data/options_payoff_lab/latest.json` and does not open the store.
No flag runs both legs.

## Install runbook

The seat does this on the store host, after merge. The job stays off until
then. It is a sibling of the skew lane. It uses the same checkout
`/Users/chriswong/skew-ops-wt` and the same state directory
`/Users/chriswong/skew-ops-state`. It does not edit the skew runner or the
skew plist.

It starts at 08:00 local on weekdays. The skew lane starts at 05:30 local
and may wait up to two hours for a fresh store. 08:00 is two and a half
hours after 05:30, so this lane starts after that wait instead of resetting
the shared checkout while the skew runner is still in it. If the skew
runner is still alive, this runner sleeps 300 seconds up to six times and
then stops.

```sh
cp ops/launchd/com.macro.payofflab.plist ~/Library/LaunchAgents/
mkdir -p /Users/chriswong/skew-ops-state/logs
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.macro.payofflab.plist
```

Dry run, through the env wrapper, with no publish:

```sh
PAYOFF_DRY_RUN=1 \
  /Users/chriswong/skew-ops-wt/ops/launchd/run_with_env.sh \
  /Users/chriswong/skew-ops-wt/.env \
  /Users/chriswong/skew-ops-wt/ops/launchd/run_options_payoff_lab.sh
```

Logs:

```sh
tail -f /Users/chriswong/skew-ops-state/logs/payofflab.stdout.log \
        /Users/chriswong/skew-ops-state/logs/payofflab.stderr.log
```

The first hydrate finds no objects in R2. That is not a failure. The runner
logs it and continues, then publishes. Later runs restore the previous file
before accruing.

To remove it:

```sh
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.macro.payofflab.plist
rm ~/Library/LaunchAgents/com.macro.payofflab.plist
```

## What W2-5b reads

W2-5b reads `site/options_payoff_lab/latest.json` after a render host has
run `--emit`. It does not open the ThetaData store.

Top of the file:

- `schema`: `mastermind.options_payoff_lab/v1`
- `asof`: the session date the store host computed
- `generated_utc`
- `source`: `thetadata`
- `roots[]`: `root`, `spot`, `expiration`, `tenor_days`, `structures[]`, `states[]`
- `counts`: `roots_priced`, `structures_built`, `structures_null`
- `states`: root-level nulls, also listed on each root

Emit adds `ledger_asof` (equal to `asof`), `accrual_state`
(`accrued_today`, `ledger_only`, or `absent`), and `n` (structures built,
or 0 when the file is absent).

Each structure has `name`, `selection_rule` (which rule picked each strike),
`summary`, `expiry_payoff`, `scenario_grids` keyed by `"0"`, `"7"`, and
`"21"`, `greeks_drift`, `assumptions`, `evidence_recipe`, and `states`.

Root-level codes this producer can print: `CHAIN_EMPTY`, `SPOT_UNAVAILABLE`,
`NO_USABLE_TENOR`. An absent file uses `ABSENT` and `accrual_state`
`absent`. Leg and structure codes are the engine's own states, copied, not
rewritten.

The page must say what it shows in a plain English sentence and a plain
Chinese sentence. The codes above stay codes. They are not a sentence, and
they are not a trade instruction.
