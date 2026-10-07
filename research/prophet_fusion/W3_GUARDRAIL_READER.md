# W3 post-floor statistical guardrail reader

*`WS:PROPHET-CONDITIONAL-FUSION` · source surface only. Frozen metric law:
[`W3_RACE_PREREG.md`](W3_RACE_PREREG.md). Capture/status owner:
`engine/us_prophet_w3.py`. This file documents the read-only CLI
`python -m scripts.report_us_prophet_w3_guardrail`.*

Software release of this reader is **separate from a scientific read**. Shipping
the source does not authorize a C1-vs-shadow comparison, a winner, a promotion,
a C2 fit, a reversion, or any AgentOS automated write.

---

## Invocation

`--root` is **required**. There is no live default. The process prints **stdout
JSON only** and writes no output file, no status rewrite, and no AgentOS record.

```bash
python -m scripts.report_us_prophet_w3_guardrail --root PATH
```

| Process exit | JSON `status` | Meaning |
|---|---|---|
| 0 | `FLOOR_UNMET` | Honest-N below 20 distinct matured H=10 paired sessions. Accrual only. |
| 0 | `READ` | Floor met, every selected stamp a lawful complete observation, stats printed. |
| 2 | `REFUSED` | Floor met (or claimed) but the whole read refused. No survivor drop. |

`--root` missing is argparse `SystemExit` (usage), not a guardrail `status`.

---

## Load order

The first call is `sessions_by_stamp`. Session **metadata** is inspected first.
Paired/family/coverage loaders, grain fingerprints, rank-IC, and HAC run **only
after** the honest-N floor is met. Below the floor the comparison surface stays
sealed: no IC, mean, p-value, interval, leader, tripwire, or hidden comparison
token on any structured field.

---

## Honest-N floor (N=20)

Grain is **distinct matured H=10 paired sessions**, identified by `stamp_date`.
Never rows, never fires, never a 60-name board counted as 60. Retries of one
`as_of` count as one session (keep-first).

Until that floor, JSON `status=FLOOR_UNMET`, process exit 0, and
`first_lawful_comparison_read` remains
`PENDING until 20 matured H=10 sessions`.

---

## Capture owner (frozen, exact persisted bytes)

The persisted paired output written by the capture owners is the registered
capture owner. This reader never reconstructs, requalifies, or re-runs the row
constructor.

A stamp is admitted only when:

1. every row carries exactly `source == candidates_store+grades_store`
2. every row carries exactly `benchmark == SPY` (missing/empty/null `source`,
   and a null `benchmark` backed by a legacy `bench` column, both refuse)
3. `grain_fingerprint(stored frame)` equals **both** the live observation
   record's `paired_fingerprint` **and** the session record's
   `paired_fingerprint`

Capture base SHA `dc4fd0766709188cba8d16a9fc16479c0e9c110f` and earlier status
SHA `53ab89afd507734189dd3dc2639e4377da11873e7b37165d490c602e7297a34d` are
**snapshots**, not current authority.

---

## Primary metric (controls investigation)

Per matured paired session, Spearman rank-IC of `(-published rank)` vs
`excess_spy` on the paired buy population:

- C1: `score_rank` under `board_definition=us_prophet_v3`
- shadow: `prophet_shadow_score_rank` under
  `prophet_shadow_definition=us_prophet_v2_shadow`

Sign: positive IC = ranker worked. Session delta ΔIC = IC_C1 − IC_shadow.

Inference: Newey-West HAC on the date-level ΔIC series, Bartlett kernel,
lag **L=9 (H−1)**. Interval is **Student-t** with df = N_sessions − 1. The
normal p-value is diagnostic only and never controls the primary.

**Investigation diagnostic only:** investigation opens iff the 95% two-sided
HAC-t CI for mean ΔIC has **upper bound strictly below 0** (`ci95_hi < 0`).
A point estimate below zero is not enough. An open investigation does not
un-adopt C1, does not trigger C2, and does not write AgentOS automatically.

---

## Secondary metric (cannot OR or cancel)

Top-30 mean `excess_spy`, same paired session, same grader, same SPY
benchmark. N=30. Names tied at the **published-rank** cutoff are included;
report the resulting n. Role: confirmatory safety only.

- cannot open an investigation by itself (`or_trigger=false`)
- cannot cancel a primary fire (`cancels_primary=false`)
- if primary fires and secondary disagrees, investigation still opens,
  labelled `rank-IC adverse, top-30 not confirmatory`

Current production rankers assign **unique ordinal ranks** after
`(stage_rank, -score, ticker)`. Equal raw scores do **not** become rank ties.
This reader adds **no new raw-score tie policy**. Inclusive-of-cutoff exists
for the published-rank column as stored.

---

## Authority (always false on this surface)

Every payload carries `authority=false` and the full zero-authority block:
no rank, gate, size, featured, plan, C2 trigger, automatic reversion,
promotion, or AgentOS write. An adverse primary tripwire is a diagnostic
label only.

---

## Current metadata snapshot (not a scientific read)

Root latest **read-only sessions metadata** snapshot (no outcomes read):

| Field | Value |
|---|---|
| sessions | 36 |
| `paired_accrued` | 1 |
| unmatured | 23 |
| degraded | 12 |
| latest stamp | 2026-09-30 |

This is **1/20, not ready**. No winner, promotion, fit, C2, reversion, or
AgentOS automated write follows from this snapshot.

---

## Lawful boundaries (this delivery)

- Assignment context is the Chairman share
  `https://chatgpt.com/s/t_6abf52c40940819186605acc3689fc54`. That is
  **not** a runtime grant and **not** a source grant beyond this reader.
- H1 incumbents remain held. No ownership transfer. Do not change held PRs
  `#8091` / `#8192` / `#8240`.
- Do not invent WS strategy or priority, a new `DEC`, a control plane, or a
  blanket permission.
- Do not read production paired/candidate/grade **outcomes** from this
  source-delivery wave.

---

## Cold-resume next steps (ordered)

1. Independent code review of this source, plus the required exclusive
   `gate:code` job (`prophet-w3-guardrail` in `.github/ci/legacy-jobs.yml`).
2. Source-only release of the reader. Software release ≠ scientific read.
3. Accrue metadata to **20** distinct matured H=10 paired sessions **before**
   any lawful comparison read.
4. Existing owners handle held H1 integration. This wave does not take that
   ownership.
