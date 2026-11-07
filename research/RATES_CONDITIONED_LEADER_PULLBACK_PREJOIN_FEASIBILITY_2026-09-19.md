# Rates-Conditioned Leader-Pullback — Pre-Join Feasibility Receipt

**Operation:** `rates-conditioned-leader-pullback-prereg-20260919-sol-001`  
**Purpose:** verify substrate identity and marginal sample feasibility **without joining rate state to episode outcomes**.  
**Research cutoff:** last stored C2r/C4 episode date = **2026-08-10**.  
**Authority:** research evidence only; no TrialLedger registration, outcome execution, rank/gate/size/trade authority, or production change.

## 1. What was and was not opened

Two separate censuses were run after the protocol thresholds/population/hurdles had been frozen:

1. **Episode-only census:** construction/date/addon/leader-field availability and whether the already-stored primary outcome is non-null. No rates were loaded into that computation.
2. **Rate-only census:** prevalence of the frozen rate states across the research era. No episode dates, tickers, leader labels, or outcomes were joined into that computation.

No rate×episode cell, treatment outcome, effect size, p-value, interval, or verdict was opened.

No treatment threshold, leader threshold, primary outcome definition, multiple-testing budget, date/quarter floor, or result hurdle was changed in response to these marginal counts.

## 2. Episode substrate identity

Path: `research/prophet_us_audit/early_admission_bakeoff_episodes.parquet`

- Git blob on #7400 freeze base: `86142b0f567044b4a3d2e307ca87a41029e83afa`
- Local read-only data-host Git blob: same.
- SHA256 bytes: `a55f3e3ecaef13efc6dc0a407375ee3d87e66b6dfb70eacb0c1d3b7249c6feb4`
- Stored rows reported by the original results package: 39,877.
- C2r base rows: 3,630.
- C4 base rows: 11,111.
- Decision era across base C2r/C4: 2014-12-04 through 2026-08-10; 48 calendar quarters.

Required columns were present: `ticker,date,construction,addon,false_bounce,f_above200,f_rs63,survive_a,mfe_42,reached_2r,fwd21`.

### Episode-only feasibility

| construction | base rows | leader-like rows | leader-like dates | leader-like + non-null false_bounce rows | primary pre-rate dates | quarters | pre-2020-07-01 dates | post-2020-07-01 dates |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| C2r | 3,630 | 971 | 425 | 967 | 421 | 48 | 194 | 227 |
| C4 | 11,111 | 2,998 | 1,131 | 2,972 | 1,121 | 48 | 503 | 618 |

These are **not performance results**. The census never reads false-bounce values beyond null/non-null eligibility.

## 3. Rate substrate identity

Canonical source paths:
- `data/fred/DGS2.parquet`
- `data/fred/DGS10.parquet`
- `data/fred/DFII10.parquet`
- `data/fred/T10YIE.parquet`

The read-only Mini checkout had older full-file tails than #7400's freeze base. Therefore full-file equality is intentionally **not** the historical-input identity. The histories were compared through the last episode date, 2026-08-10, and were exactly equal on index and values.

### Frozen prefix-digest algorithm

For each source:
1. keep rows with source date <= 2026-08-10;
2. sort by source date;
3. encode each row as `(YYYY-MM-DD, float(value).hex())` (null would encode as null);
4. compact JSON encode the ordered row list;
5. SHA256 the bytes.

Frozen prefix identities:

| source | rows through cutoff | prefix SHA256 |
|---|---:|---|
| DGS2 | 12,544 | `a9b2615177ad46e359bbd368a5d8e280b397c818e840e875091d36bf7ff85cfe` |
| DGS10 | 16,136 | `4e0ca7ac1542f9ff6ab7a93d323f71d85cd342028e1c89b6a09baef1e5db5e87` |
| DFII10 | 5,905 | `835a01fd88d029a4fb2fbbff1517a22e4d8e0c2138c00cda5c41cf03e1d6f57e` |
| T10YIE | 5,905 | `cc6f9e6ecca3a8a512d2c7a4baa30d4646add347f628a838af798efc69ce90c6` |

A future appended tail is allowed. A prefix-digest mismatch is a **material input invalidator** and the runner must refuse before TrialLedger/result computation.

## 4. Rate-only state feasibility

Using the already-frozen state definitions on source observations over the episode era, without loading any episode row:

| rate state | observed dates | quarters | pre-2020-07-01 dates / quarters | post-2020-07-01 dates / quarters |
|---|---:|---:|---:|---:|
| EASING_AFTER_PRESSURE | 419 | 47 | 198 / 22 | 221 / 25 |
| POLICY_CONFIRMED_RELIEF | 310 | 47 | 145 / 22 | 165 / 25 |
| REACCELERATION | 817 | 46 | 321 / 21 | 496 / 25 |
| pressure but not easing | 1,082 | 47 | 423 / 22 | 659 / 25 |

Common finite DGS10/DFII10 observation dates in the era: 2,918 across 48 quarters (2014-12-08 through 2026-08-07).

These counts establish only that the frozen rate states are not trivially empty. They **do not establish** how many leader episodes fall into each arm; opening that joint population is reserved until TrialLedger registration.

## 5. Execution gate carried forward

Before the first rate×episode join:
- verify the episode Git/blob identity or exact SHA256 above;
- verify all four frozen rate prefix digests;
- verify the prereg markdown and JSON companion identities;
- declare budget 7 in existing TrialLedger family `rates_conditioned_leader_pullback_v1`;
- then execute once without threshold/population/horizon changes.

Any failure routes to a refusal or a new prereg, never an in-place threshold repair after outcomes.
