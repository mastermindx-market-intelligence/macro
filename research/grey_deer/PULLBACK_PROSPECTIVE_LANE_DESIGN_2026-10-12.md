# Pullback prospective lane — design (2026-10-12)

Status: design only. No writer, no grader, no row, no price series.
Program: `WS:GREY-DEER-RISK-INTELLIGENCE` / MAS-258 · operation `risk-radar-pullback-20261009`.
Frozen recipe: prereg v1 `research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md`, blob `49a68b5e9c6543d662044b0aa391c4b6e6e6052e` (`git rev-parse HEAD:<path>` on this branch).
Manifest v1.0.0 is not edited. Prereg v1.1 (the 14-ticker panel) is not frozen and is not specified here.

Prospective N under §13 is 0. W3 stage-1 (`research/grey_deer/PULLBACK_STAGE1_RESULTS_2026-10-11.md` and the r1 rerun) left every P-all claim `underpowered/blocked claim` and every P-active claim blocked `OBSERVER_NOT_ON_MAIN`. This note does not restate that run's statistics and does not recompute them.

This file is the issuing-lane design §13 asks for. It does not issue.

## 1. GENUINELY_ISSUED

A row is GENUINELY_ISSUED only when the nightly lane writes it, before the next session open, from inputs available at the asof close, with the code sha of that checkout recorded on the row.

The following are not issued, whatever their other fields say:

- a backfill (any asof older than the latest closed session in the input store the process actually read);
- a rerun (a second write of an existing key, including a research replay);
- an intraday, closing-bell, render, or engine-render write;
- a row whose `issued_at` is outside the window below;
- a row introduced by a git commit that is not the nightly ledger commit.

### 1.1 Field check

A reader admits a row only when every field below holds. One failure excludes the row. The exclusion is typed `NOT_ISSUED` plus the first failing reason. The line may remain on disk; it does not enter a prospective count.

| Check | Required value |
|---|---|
| `evidence_class` | the literal `GENUINELY_ISSUED` |
| `writer_lane` | the literal `nightly` |
| `collect_lane_env` | the literal `nightly` |
| `writer_identity` | the literal pinned before the first issue, `daily.yml:engine` |
| `backfill`, `rerun`, `intraday` | all false |
| `code_sha` | 40-hex, equal to the checkout `HEAD` the writer computed itself |
| `prereg_blob` | 40-hex blob of the frozen prereg the row claims |
| `inputs_digest` | 64-hex sha256 of the canonical input payload |
| `issued_at` | UTC timestamp inside the window in §1.3 |
| `asof` | a NYSE session, and the latest closed session in the store that run read |
| grading fields on this row | all null (`realized_A`, `Y`, `graded_at`, `grader_sha`) |

`US_LANE=nightly` does not arm this ledger. The house helper `ledger_lane_armed` treats that variable as a legacy alias. This lane does not. `COLLECT_LANE` must be exactly `nightly`. If `US_LANE` is set to anything else, the writer refuses.

The booleans are not trusted by themselves. The asof check is what makes `backfill=false` true: the writer may append only for the latest closed session it just read. A loop over history fails that check even if a caller sets the boolean.

### 1.2 Writer-identity check

The writer computes the identity. It does not accept these as arguments: `issued_at`, `code_sha`, `writer_lane`, `evidence_class`, `collect_lane_env`.

1. Read `COLLECT_LANE`. Anything other than `nightly` refuses with reason `LANE` and writes no issued line.
2. Read `writer_identity` from the nightly job's own environment (`GREY_DEER_PULLBACK_WRITER_IDENTITY`). It must equal the pinned literal `daily.yml:engine`. Empty, missing, or different refuses with reason `IDENTITY`. The pin matches the house description of the risk-radar ledger's only advancing job (`daily.yml`'s engine job, `COLLECT_LANE=nightly`, in `engine/risk_radar_audit.py`). The writer pull request pins the literal to that job before the first issue. Changing the literal changes the recipe fingerprint (§6).
3. Set `code_sha` from `git rev-parse HEAD` inside the writer. A caller-supplied sha refuses with reason `SHA_MISMATCH`.
4. Set `issued_at` from the process clock in UTC, once, immediately before the append.
5. A later reader confirms the introducing commit of that jsonl line is a nightly ledger commit, the same class of check the risk-radar module documents with `git log` on its own forward log. A line whose introducing commit is a research lane, a hand edit, or a backfill script is `NOT_ISSUED` even when the fields above are present.

### 1.3 Window

Session membership comes from `lib.nyse_calendar.is_session`. That function counts a shortened session as a session. The module's own header says early closes are not modeled. This design does not invent a 13:00 table.

- `asof` must pass `is_session`. A Saturday, Sunday, or full-day holiday refuses with reason `NOT_A_SESSION`.
- Earliest legal `issued_at`: 17:00 America/New_York on `asof`. That is the regular-session close (16:00) plus the one-hour settle buffer the calendar module documents. A stamp earlier than that is before the writer can honestly claim the daily bar has settled, and it refuses with reason `CLOCK`.
- Latest legal `issued_at`: strictly before 09:30 America/New_York on the next date that passes `is_session` (walk forward with `sessions_between`). Friday's row may be written through the weekend. If Monday is not a session, the far edge is Tuesday's open.
- The next session's open is a design constant, `09:30 America/New_York`. `lib.nyse_calendar` does not export an open time.
- The writer does not move a late or early timestamp into the window. Outside the window, it writes no issued line.

Inputs are the asof close and features known at that close (prereg §6: embargo 0). The writer does not read a bar after `asof`. The input payload hashed into `inputs_digest` includes the ticker, the asof, the close used, the feature vector, the training-prefix end, and the store identity. A later night that sees a different close produces a different digest and does not rewrite the row (§6, data revision).

### 1.4 What the first nights are allowed to issue

Under prereg blob `49a68b5e9c6543d662044b0aa391c4b6e6e6052e` the only ticker is `SPY`. The 14-ticker panel is an unfrozen v1.1. This design stores a ticker field so that panel can use the same file later. It does not name those tickers and it does not issue them.

Issued configs, one row per (asof, ticker, horizon, config), horizons 5, 10 and 21:

| config_id | population | kind | gate |
|---|---|---|---|
| `B0`, `B1-20`, `B1-63`, `B2-21`, `B2-63` | P-all | binary | no (baseline; frozen) |
| `M3-ALL@C=1.0` | P-all | binary | yes |
| `M3-ALL@C=0.1` | P-all | binary | no (frozen sensitivity) |
| `Q0`, `Q1` | P-all | quantile | no (baseline; frozen) |
| `Q3-ALL` | P-all | quantile | yes |

P-active configs (`M3-ACT`, `Q3-ACT`, and the P-active baselines) are not issued while `close_path.v1` is off main. The writer records a refusal `OBSERVER_NOT_ON_MAIN` and does not copy PR #8188. Their prospective clock starts at the first nightly issue after that observer is on main with byte-identical rules. Those rows are not backfilled. A rules change on landing is a new prereg, per §12, and it is not this blob.

INC is not issued. It is CURRENT_VINTAGE and lives in its own table (prereg §6, manifest D8). The negative control is not issued. It is a retrospective label shift, not a forecast.

An abstention is issued. The row carries a null probability or null quantiles and a frozen `abstention_reason` (`FIT_NONCONVERGENCE`, `QUANTILE_CROSSING`, `TRAINING_FOLD_THIN`, and the other reasons the prereg names). Dropping abstentions would let a later run erase hard days.

Refits follow §13 and §7: expanding window, one fit per config per block of 126 sessions, purge `idx(t) + h ≤ idx(s0)`, embargo 0. The row records `fit_block_id` and `training_end_asof`. A new block writes new asofs only. It does not rewrite probabilities already issued.

## 2. Row schema

Two forecast-bearing files exist. The issued file is immutable. The graded file is a later append. Field names on the issued row that will hold outcomes stay null for the life of the row. A non-null grading field on an issued row means the row was edited, and the reader treats it as `NOT_ISSUED`.

JSONL, one object per line, UTF-8, `separators=(",", ":")`, `sort_keys=true` at write time so the line hash is stable.

### 2.1 Issued row (`grey_deer_pullback_forward_issue.v1`)

| Field | Type | Meaning |
|---|---|---|
| `schema` | string | `grey_deer_pullback_forward_issue.v1` |
| `evidence_class` | string | `GENUINELY_ISSUED` when §1 passes; otherwise the line is not written here |
| `asof` | string | Session date `YYYY-MM-DD` of the close the forecast is about |
| `ticker` | string | `SPY` under this blob |
| `horizon` | int | `5`, `10`, or `21` sessions |
| `config_id` | string | One id from §1.4 |
| `population` | string | `P-all` or, later, `P-active` |
| `kind` | string | `binary` or `quantile` |
| `is_gate` | bool | True only for `M3-ALL@C=1.0` and `Q3-ALL` (and the future P-active gated twins) |
| `probability` | float or null | Binary: predicted probability in `[0, 1]`, or null on abstention. Quantile rows: null |
| `quantile` | object or null | Quantile: `{"0.5": float, "0.8": float, "0.9": float}` after the frozen crossing-then-clip order. Null on abstention. Binary rows: null |
| `abstention_reason` | string or null | Frozen reason, or null when a number was issued |
| `inputs_digest` | string | sha256 of the canonical input payload (§1.3) |
| `code_sha` | string | 40-hex `HEAD` of the writing checkout |
| `recipe_fingerprint` | string | sha256 over the closed source list plus `prereg_blob` (§6) |
| `prereg_blob` | string | Git blob sha of the frozen prereg |
| `prereg_path` | string | `research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md` for this blob |
| `issued_at` | string | UTC ISO-8601 with seconds and offset. The first-write clock |
| `writer_lane` | string | `nightly` |
| `writer_identity` | string | `daily.yml:engine` |
| `collect_lane_env` | string | The `COLLECT_LANE` value actually read, which must be `nightly` |
| `backfill` | bool | false |
| `rerun` | bool | false |
| `intraday` | bool | false |
| `fit_block_id` | string | Expanding block id under the §7 rule of 126 sessions |
| `training_end_asof` | string | Last training origin whose label was knowable at this close |
| `issue_receipt` | object | House receipt: `contract` `grey_deer_pullback_forward_issue.v1`, `epoch` `grey_deer_pullback_prospective.v1`, `issued_at` (same timestamp), `ledger_lane` `nightly`, `first_writer_wins` true |
| `realized_A` | null | Stays null. The grade lives in the sibling |
| `Y` | null | Stays null |
| `graded_at` | null | Stays null |
| `grader_sha` | null | Stays null |

`epoch` is not the risk-radar epoch `2026-09-23-prospective-v1`. That epoch belongs to `data/risk_radar/forward_log.jsonl`.

### 2.2 Graded sibling row (`grey_deer_pullback_forward_grade.v1`)

Written only after horizon `h` has elapsed: the `t+h` close is in the store, and the label is mature in the §4 sense. An immature label is absent. It is never written as zero.

| Field | Type | Meaning |
|---|---|---|
| `schema` | string | `grey_deer_pullback_forward_grade.v1` |
| `asof`, `ticker`, `horizon`, `config_id` | as issued | Join key. Matches one issued row |
| `issue_line_sha256` | string | sha256 of the exact issued line, so the join does not depend on editing it |
| `prereg_blob` | string | Copied from the issued row. The grader refuses if its label rule disagrees with that blob |
| `realized_A` | float | `A(t, h)` from prereg §4. Not computed by this design |
| `Y` | int | `1` when `A ≥ 0.05`, else `0`. The §4 event |
| `graded_at` | string | UTC ISO-8601 of the grade append |
| `grader_sha` | string | 40-hex `HEAD` of the grading checkout |
| `grader_lane` | string | `nightly` |
| `grade_inputs_digest` | string | sha256 of the path the grader read |
| `revision_flag` | bool | True when the asof close in the grading store disagrees with the close inside the issue `inputs_digest` |
| `evidence_class` | string | `GRADE`. Never `GENUINELY_ISSUED` |

### 2.3 Refusal row (`grey_deer_pullback_forward_refusal.v1`)

A refused attempt is logged here so the issued file stays append-only. The refusal stores the key and the reason. It does not store the probability or the quantile. A refusal is not a forecast and is not gradeable.

| Field | Type | Meaning |
|---|---|---|
| `schema` | string | `grey_deer_pullback_forward_refusal.v1` |
| `refused_at` | string | UTC ISO-8601 |
| `reason` | string | `LANE`, `IDENTITY`, `CLOCK`, `BACKFILL_ASOF`, `NOT_A_SESSION`, `DUPLICATE_KEY`, `DIGEST_MISSING`, `SHA_MISMATCH`, `PREREG_MISMATCH`, `OBSERVER_NOT_ON_MAIN`, `UNFROZEN_PANEL` |
| `asof`, `ticker`, `horizon`, `config_id` | as attempted | The key that was refused. Null when the attempt had no key |
| `writer_lane` | string | Lane the attempt claimed, or `absent` |
| `attempt_digest` | string | sha256 of the attempt payload, not the payload |

## 3. Idempotence

The issued key is `(asof, ticker, horizon, config_id)`. Keep-first.

The writer appends with a single `O_APPEND` of one line. It may read the file to learn existing keys. It does not rewrite the file. A rewrite is the edit this rule forbids. The house risk-radar grader rewrites the whole file to set `graded` on the same row (`engine/risk_radar_audit.py` `grade_log`). This lane does not copy that step.

On a second write of an existing key:

1. The issued line stays byte-for-byte.
2. A refusal row with reason `DUPLICATE_KEY` is appended to the refusal sibling.
3. The function returns without changing the issued probability, the receipt, or the null grading fields.

The same keep-first rule applies to the graded sibling, on the same key. The first mature grade sticks, including a grade with `revision_flag=true`. A second grade is a refusal, not a correction.

Grading never updates the issued row. The nulls in §2.1 stay null after the horizon elapses. The realized `A`, `Y`, `graded_at`, and `grader_sha` exist only on the graded sibling.

The graded append is itself nightly-only. A grade computed off-lane would stick under keep-first, which is why `grade_log` in the risk-radar module no-ops unless the lane is armed. The same gate applies here.

## 4. Path and the nightly writer

| Role | Path | Who writes |
|---|---|---|
| Issued forecasts | `data/grey_deer_pullback/forward_log.jsonl` | Nightly only |
| Grades | `data/grey_deer_pullback/forward_log_graded.jsonl` | Nightly only, after maturity |
| Refusals | `data/grey_deer_pullback/forward_log_refusals.jsonl` | Nightly writer, on refuse |

`rg` on this branch finds no existing `data/grey_deer_pullback` path (§7). The refusal file is an enforcement sibling. It is not a second forecast ledger.

### 4.1 Reading of prereg §13

§13 says the issuing lane writes into the existing forward-ledger identity (issue receipt and `issued_at`), never a second ledger. This design reads that sentence as follows.

- One forecast ledger for this recipe. The issued path above is that ledger. Grades and refusals are sibling appends of later facts, not a second place where a prediction can be born.
- The identity written on each issued row is the house issue receipt: `issued_at` equal to the first-write clock, `ledger_lane=nightly`, `first_writer_wins=true`. That is the shape of `engine/risk_radar_audit._forward_issue_receipt`, with this recipe's contract and epoch.
- The file `data/risk_radar/forward_log.jsonl` is not this recipe. It records the live radar's own states. Manifest D8 keeps the evidence classes unpooled. §14 says this protocol writes nothing to PR #8721 or PR #8188. Appending pullback rows into the radar file would share a file this lane is forbidden to share.

If a later ruling reads §13 as "append into `data/risk_radar/forward_log.jsonl`", this design is wrong and the writer must not be built until the design is replaced. This note does not edit the prereg.

### 4.2 Nightly gate

House law (`CLAUDE.md`, Ledgers): nightly is the sole advancer of forward ledgers; intraday lanes discard `data/` writes.

The writer self-gates before any append, including the refusal append. An off-lane call returns without creating the directory. The gate is `COLLECT_LANE=nightly` plus the identity pin in §1.2. Render, closing-bell, and engine-render stay read-only for this path even if they have a `data/` tree.

A sparse research worktree does not create these files. The future writer runs in the nightly job, where `data/` exists. Tests of that writer, when a later lane builds them, use a temporary directory and synthetic bars. They do not download a price series and they do not write the repo `data/` tree.

Registration of the path in `scripts/audit_grading_closure.py`, `config/synapse.yml`, `config/dag.yml`, and the ledger heartbeat is work for the writer pull request. Those files are outside this design's owned set, and a registration with no writer would claim a ledger that does not exist.

This lane does not append issued nights to `data/trial_ledger.jsonl`. Stage-1 already registered family `grey_deer_pullback_v1`. Issuing a frozen config is not a new trial. A new config is a new revision and is out of scope.

## 5. Readiness floor

No prospective claim is computed until both bars hold, on one cohort. A cohort is one `(prereg_blob, recipe_fingerprint)`. Sessions, grades, events, non-events, and clusters are not pooled across fingerprints or across prereg blobs. A code change that rotates the fingerprint starts a new cohort at zero (§6).

The two bars are the 2026-09-24 readiness floor, quoted by prereg §13, and the §8 power floor (at least 10 episodes and at least 10 distinct event-months). Either bar alone does not open evaluation. The prospective clock starts at the first GENUINELY_ISSUED row. Evaluation stays not started until both bars hold. A computation that runs early has one legal verdict word: `underpowered/blocked claim`.

Counts are per horizon and per claim family (binary and quantile separately). Horizons mature at different lags. Pooling them would let horizon 5 carry horizon 21.

An issued session is a distinct `asof` with at least one GENUINELY_ISSUED row in that cohort. Ten configs at three horizons on one night are one session.

A graded row, for the floor, is a grade sibling whose issued partner is GENUINELY_ISSUED, whose `revision_flag` is false, and whose `config_id` is the gated config for that family (`M3-ALL@C=1.0` or `Q3-ALL`). Flagged grades are reported beside the floor and do not satisfy it.

Clusters use prereg §8 and no other definition. Event-positive origins in time order merge when the session-index gap is at most `h`. The index is the session index, not the position in the graded subset. Episodes are the §8 union of clusters whose episode windows overlap. The episode window runs from 21 sessions before the cluster's first event origin through `h` sessions after its last.

| Floor | Number | Why this number |
|---|---|---|
| Issued sessions | ≥ 252 | One US cash-equity year. The retrospective protocol starts its first test block at the 253rd warm origin (prereg §7), one trading year after warm-up. 252 is the 2026-09-24 round count of that year. The count is distinct sessions, so a night that emits many rows cannot manufacture a year. |
| Calendar span | ≥ 300 days | `last issued asof` minus `first issued asof`, in calendar days. 252 weekday sessions with no holidays span `252 × 7/5 = 352.8` calendar days, and holidays make the span longer, so a real year clears 300. The bar rejects a stamp run that places 252 asof labels inside a shorter calendar (backfill, non-session dates, or a clock that reuses a short window). 300 is under one seasonal year and over two quarters, so half a year of real nights does not open a claim. The number is the 2026-09-24 bar. It is not retuned here. |
| Graded rows | ≥ 200 per horizon | Prereg §9 builds calibration bins only when a bin holds at least 100 rows, and the calibration condition fails when those bins cover under half the comparison set. Under 200 graded rows, two such bins cannot exist. The count is per horizon because the horizons do not mature together. 200 is larger than 20 + 50, so the event floors and the row floor each have to hold on their own. |
| Events | ≥ 20 per horizon | Prereg §8's half-width is `1.645 · sqrt(0.25 / n)`. At 10 that is about 0.26, which §8 calls the coarsest floor for a cluster-level statement. At 20 the same bound is about 0.18. Event origins inside a cluster are not independent, so 20 is not a power proof. It stops a horizon that has many graded rows and almost no events, and it is stricter than the episode floor's own 10. The §8 floor of 10 episodes and 10 event-months still has to hold on top. |
| Non-events | ≥ 50 per horizon | False-alarm share (§9) and the abstention comparison (§11, the 5 percentage-point gap) need a non-event denominator. The same half-width at 50 is about 0.12. The non-event floor is higher than the event floor because non-events are the common class: a sample can reach 20 events while the other side is still a handful, and the abstention gap is then a one-row flip. 20 + 50 = 70, which does not satisfy the 200-row floor. |
| Clusters | ≥ 5 per horizon | §8 says the power floor of 10 episodes is twice the 2026-09-24 readiness floor of 5. Five uses the §8 cluster merge, so a streak of event origins is one cluster. Twenty events can be one drawdown. Five clusters means that streak is not the whole sample. Leave-one-cluster-out still has four clusters left, so the deletion is a check. Five clusters do not satisfy §8. Evaluation waits for both. |

The power floor is not replaced by this table. Ten episodes and ten distinct calendar months that contain an event origin remain required, measured with the §8 definitions, on the same cohort and the same horizon and family.

## 6. Owner and failure modes

Owner: `WS:GREY-DEER-RISK-INTELLIGENCE` (`agentos/workstreams/WS-GREY-DEER-RISK-INTELLIGENCE.md`). This design does not mint a second owner and does not edit the workstream record.

The nightly job is the only writer. An intraday lane, a research rerun, and a backfill script are not writers of these files. The future writer pull request belongs to this workstream. Until that job exists, prospective N stays 0.

The US nightly collection push has been blocked by QLedger GH001 (handoff `research/grey_deer/GREY_DEER_CONTINUATION_HANDOFF_2026-10-11.md`). While that stands, a grade that needs a published post-asof path cannot land on main. The handling is the missed-night row below. This design does not route around that owner and does not fetch a price series to grade offline.

`recipe_fingerprint` is sha256 of a canonical listing of `(relative path, blob sha)` for a closed source list, plus `prereg_blob`. The list is pinned in the writer pull request before the first issued row, and it covers the writer module, the prereg file, `lib/nyse_calendar.py`, and the feature and fit modules that produce B0, B1, B2, M3, Q0, Q1, and Q3. A byte change inside that list rotates the fingerprint. A nightly commit that does not touch the list changes `code_sha` and does not reset the cohort. `code_sha` is still stored on every row so the exact checkout can be audited.

| Failure | What happens | Handling |
|---|---|---|
| Missed night | The job does not run, or it runs and the collection push does not publish. That session has no issued row. | The gap stays empty. The next successful nightly issues only the new latest closed session. It does not write the missed asof. The gap is not an issued session. A claim census lists the missing sessions from `sessions_between` over the span. The span floor uses the issued asofs that exist, so a hole lengthens the calendar without adding sessions. |
| Duplicate night | The job runs twice, or a second process repeats the key. | Keep the first issued line. Append `DUPLICATE_KEY` to the refusal file. Do not rewrite the issued file and do not replace the probability. |
| Clock skew | `issued_at` falls outside §1.3, or a caller tries to supply a timestamp. | The writer reads UTC itself and refuses with `CLOCK` when the timestamp is outside the window. It does not clamp the timestamp into the window. A row later found outside the window is `NOT_ISSUED`. Skew that remains inside the window is stored as the clock read it. |
| Holiday | The calendar day is not a session, or the next open is not the next civil day. | `is_session` refuses a holiday asof (`NOT_A_SESSION`). The far edge of the window is 09:30 America/New_York on the next real session, so a Friday issue survives a weekend and a Monday holiday. No row is created for the holiday. Early closes stay sessions, and the 17:00 bound still applies, because the calendar module does not model a 13:00 close. Waiting until 17:00 on those days is inside the next-open edge. |
| Data revision | A vendor reprint changes the asof close or a feature after the row was issued. | The issued line and its `inputs_digest` stay. The grader writes one grade, sets `revision_flag` when the grading-time asof close disagrees with the digest, and does not recompute the issued probability. A flagged grade does not count toward the §5 floors. There is no second grade and no re-issue. |
| Code change mid-stream | The recipe bytes change between nights. | Later nights record the new `code_sha`. When the closed source list changes, they also record a new `recipe_fingerprint`, and that cohort starts at zero issued sessions. Earlier rows stay on the old fingerprint and are not rewritten, not re-labeled, and not pooled into the new cohort. A new prereg blob is a new clock under §12 and §13. |

## 7. Collision check

This lane writes nothing into PR #8721 or PR #8188 surfaces and does not share their files.

#8721 is the live US out-of-sample baseline (writer `mastermindxryan`, head `f28759c84e2e`, branch `sol/risk-radar-pullback-depth-20261009` in `docs/ACTIVE_BUILD_MAP.md`). Files named as living on that PR include `research/grey_deer/PULLBACK_CAUSAL_FEATURE_CONTRACT_2026-10-10.md` and `research/grey_deer/PULLBACK_OOS_BASELINE_RESULT_2026-10-09.md`. The build map also shows `.github/ci/legacy-jobs.yml` overlapping that PR. This design touches none of those paths.

#8188 is the held China pullback view (semantic v6, HOLD-FOR-SOL, custody `cn-pullback-lifecycle-20260929-sol-001`). `lib/pullback_observation.py` `close_path.v1` is on that draft and not on main (prereg §5). The handoff names shared template paths `china.html.j2`, `_risk_radar_card.html.j2`, and `_risk_radar_dlg.html.j2` across that PR and other held UI PRs. This design does not copy the observer and does not write those templates.

### 7.1 Commands and hits

Counts, run from this worktree:

```
rg -l -g '!*.png' '8721' | wc -l          # 174
rg -l -g '!*.png' '8188' | wc -l          # 173
rg -l -g '!*.png' 'risk_radar' | wc -l    # 482
rg -l -g '!*.png' 'forward_log' | wc -l   # 280
rg -n 'data/grey_deer_pullback'           # no hits
```

Most of the 174 and 173 file hits are the digit sequence inside research CSV and JSON artifacts. Those lines are not ledger names and are not pasted here, because they are not paths this design can write and many of them are market series. The PR-context hits that name a surface are pasted below.

Forward-log paths (`rg -o --no-filename -g '!*.png' -g '!*.jpg' 'data/[A-Za-z0-9_./-]*forward_log[A-Za-z0-9_./-]*' | sort -u`):

```
data/breadth_divergence/forward_log.parquet
data/china_sector_cycles/forward_log.parquet
data/china_sector_cycles/forward_log.pq
data/china_validation/allocation_forward_log.jsonl
data/china_validation/cycle_phase_forward_log.jsonl
data/china_validation/participation_forward_log.jsonl
data/china_validation/stock_lifecycle_forward_log.jsonl
data/china_validation/theme_rotation_forward_log.jsonl
data/cn_prophet_audit/forward_log.parquet
data/cn_prophet_audit/forward_log.parquet.
data/corp_bonds/forward_log.jsonl
data/country_cycles/forward_log.parquet
data/country_cycles/forward_log.tr_v0.parquet
data/cycle_flagships/forward_log.parquet
data/cycle_ontology/forward_log.parquet
data/deterioration_cascade/forward_log.jsonl
data/event_windows/forward_log.jsonl
data/forex/context_forward_log.jsonl
data/government_revenue/forward_log.jsonl
data/leadership_crack/forward_log.jsonl
data/market_state/forward_log.jsonl
data/opex_windows/forward_log.jsonl
data/prophet_miss_audit/forward_log.jsonl
data/prophet_scan_tier/forward_log.jsonl
data/rates_command/forward_log.jsonl
data/risk_radar/forward_log_contagion.jsonl
data/risk_radar/forward_log_crossasset.jsonl
data/risk_radar/forward_log.jsonl
data/risk_radar/forward_log.parquet
data/risk_radar_intl/au_forward_log.jsonl
data/risk_radar_intl/ca_forward_log.jsonl
data/risk_radar_intl/cn_forward_log.jsonl
data/risk_radar_intl/ez_forward_log.jsonl
data/risk_radar_intl/gb_forward_log.jsonl
data/risk_radar_intl/hk_forward_log.jsonl
data/risk_radar_intl/in_forward_log.jsonl
data/risk_radar_intl/jp_forward_log.jsonl
data/risk_radar_intl/kr_forward_log.jsonl
data/risk_radar_intl/tw_forward_log.jsonl
data/rotation_events/forward_log
data/sector_cycles/forward_log.parquet
data/sector_cycles/forward_log.tr_v0.parquet
data/us_sector_rotation/forward_log.jsonl
data/yield_momentum/forward_log.jsonl
```

A trailing dot on `data/cn_prophet_audit/forward_log.parquet.` is sentence punctuation the regex kept. It is not a second file.

Other ledger paths from the same class of sweep (`trial_ledger`, `forward_ledger`, `live_ledger`, `recovery_log`, `review_log`):

```
data/fundamental_forensics/forward_ledger.parquet
data/oracle/compounds/live_ledger.jsonl
data/oracle/compounds/trial_ledger.jsonl
data/oracle/forward_ledger.jsonl
data/oracle/gauntlet/p3_trial_ledger.json
data/oracle/gauntlet/p8_trial_ledger.json
data/release_forecast/forward_ledger.jsonl
data/risk_radar/recovery_log.jsonl
data/risk_radar/review_log.jsonl
data/seasonality/nw_forward_ledger.jsonl
data/stage_analysis/forward_ledger.jsonl
data/stage_analysis/forward_ledger_meta.json
data/stage_analysis/forward_ledger_quarantine.jsonl
data/stock_personality/forward_ledger.parquet
data/trial_ledger.jsonl
data/trial_ledger_d2_local.jsonl
```

`engine/contagion_links.py` and `scripts/heal_contagion_links_ledger.py` also build `data/risk_radar_intl/<mkt>_forward_log_contagion.jsonl`. Those paths are not pasted as a second inventory; they are the same radar family.

PR-context command:

```
rg -n -g '!reports/**' -g '!*.json' -g '!*.csv' -g '!*.tsv' -g '!*.svg' -g '!*.js' -g '!*.xml' -g '!*.log' -g '!docs/ACTIVE_BUILD_MAP.md' -g '!docs/AGENT_OS_STATE.md' '#8721|#8188|PR #8721|PR #8188|PR 8721|PR 8188' .
```

Hits (one manifest line is shortened; its numeric cells are a prior diagnostic and are omitted):

```
agentos/workstreams/WS-GREY-DEER-RISK-INTELLIGENCE.md:373: Consumer qualification under the frozen prereg (PR 8721 read-only)
agentos/workstreams/WS-GREY-DEER-RISK-INTELLIGENCE.md:389: P-active stays blocked until PR 8188 lands
agentos/workstreams/WS-GREY-DEER-RISK-INTELLIGENCE.md:394: incumbents PR 8721 (live writer) and PR 8188 (HOLD-FOR-SOL) are read-only
scripts/research/grey_deer_pullback_stage1.py:47: draft PR #8188, not main
scripts/research/grey_deer_pullback_stage1.py:661: close_path.v1 lives on draft PR #8188, not main
scripts/research/grey_deer_pullback_stage1.py:2018: P-active stays blocked until close_path.v1 (draft PR #8188) is on main
scripts/research/grey_deer_pullback_stage1.py:2750: BLOCKED / OBSERVER_NOT_ON_MAIN (stage 2; observer on draft PR #8188)
agentos/handoffs/GREY-DEER-RISK-INTELLIGENCE-2026-10-11-FABLE-W0.md:17-18: live US baseline PR #8721; held China pullback view PR #8188
agentos/handoffs/GREY-DEER-RISK-INTELLIGENCE-2026-10-11-FABLE-W0.md:41: PR #8721 has a live writer and is not this seat's to touch
agentos/handoffs/GREY-DEER-RISK-INTELLIGENCE-2026-10-11-FABLE-W0.md:43: head f28759c84e2e; the #8188 observer is not copied into it
agentos/handoffs/GREY-DEER-RISK-INTELLIGENCE-2026-10-11-FABLE-W0.md:44-45: PR #8188 hold intact
agentos/handoffs/GREY-DEER-RISK-INTELLIGENCE-2026-10-11-FABLE-W0.md:88: #8188 join custody, owner cn-pullback-lifecycle-20260929-sol-001
agentos/handoffs/GREY-DEER-RISK-INTELLIGENCE-2026-10-11-FABLE-W0.md:99: #8721 is consumed read-only through CI, never edited
agentos/handoffs/GREY-DEER-RISK-INTELLIGENCE-2026-10-11-FABLE-W0.md:104: #8188 semantic v6 contract — do not re-derive
agentos/handoffs/GREY-DEER-RISK-INTELLIGENCE-2026-10-11-FABLE-W0.md:109: writing into the #8721 or #8188 branches is a collision
agentos/handoffs/GREY-DEER-RISK-INTELLIGENCE-2026-10-11-FABLE-W0.md:110: china.html.j2, _risk_radar_card.html.j2, _risk_radar_dlg.html.j2 overlap #8188
agentos/handoffs/GREY-DEER-RISK-INTELLIGENCE-2026-10-11-FABLE-W0.md:135: #8721 head f28759c84e2e, read-only
agentos/handoffs/GREY-DEER-RISK-INTELLIGENCE-2026-10-11-FABLE-W0.md:139-140: #8721 live writer; #8188 held
agentos/handoffs/GREY-DEER-RISK-INTELLIGENCE-2026-10-11-FABLE-W0.md:181: #8188 publication precheck refusal
agentos/handoffs/GREY-DEER-RISK-INTELLIGENCE-2026-10-11-FABLE-W0.md:183: hold on #8188 binds every merge path
agentos/handoffs/GREY-DEER-RISK-INTELLIGENCE-2026-10-11-FABLE-W0.md:194: consumer qualification (#8721 read-only)
research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_2026-10-11.md:20: PULLBACK_CAUSAL_FEATURE_CONTRACT exists only on PR #8721
research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_2026-10-11.md:148: S07 OOS baseline is PR #8721 head (numeric cells omitted)
research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md:158-160: close_path.v1 is on draft PR #8188 (head ff27a268abaa), not main
research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md:464: this protocol writes nothing to PR #8721 or PR #8188
research/grey_deer/GREY_DEER_CONTINUATION_HANDOFF_2026-10-11.md:19-20: never write #8721 or #8188
research/grey_deer/GREY_DEER_CONTINUATION_HANDOFF_2026-10-11.md:28: #8188 semantic v6 contract is do-not-redo
research/grey_deer/GREY_DEER_CONTINUATION_HANDOFF_2026-10-11.md:37: W3 consumes #8721 read-only
research/grey_deer/GREY_DEER_CONTINUATION_HANDOFF_2026-10-11.md:40: a lane that writes #8721/#8188 paths freezes
research/grey_deer/GREY_DEER_CONTINUATION_HANDOFF_2026-10-11.md:62: no writes to #8721 / #8188
research/grey_deer/GREY_DEER_CONTINUATION_HANDOFF_2026-10-11.md:81: #8188 custody is the placement owner's act
research/grey_deer/GREY_DEER_CONTINUATION_HANDOFF_2026-10-11.md:98-99: #8188 precheck refusal and HOLD
research/grey_deer/README.md:48-49: PR #8721 read-only; PR #8188 HOLD-FOR-SOL
```

`docs/ACTIVE_BUILD_MAP.md:101` records `#8721` as `[MAS-258][DRAFT] Risk Radar pullback-depth research` on `sol/risk-radar-pullback-depth-20261009`. Later rows of that map are file-overlap counts, mostly `.github/ci/legacy-jobs.yml`. `docs/AGENT_OS_STATE.md` repeats the workstream sentence. Neither file is a ledger this design writes.

### 7.2 Closest names, and the non-share rule

The closest existing files are `data/risk_radar/forward_log.jsonl`, its parquet twin, `forward_log_contagion.jsonl`, `forward_log_crossasset.jsonl`, `recovery_log.jsonl`, `review_log.jsonl`, and `data/risk_radar_intl/*_forward_log.jsonl`. They are the live radar's ledgers. `data/trial_ledger.jsonl` holds the stage-1 family `grey_deer_pullback_v1` and is not extended by this lane.

None of the paths in §7.1 is `data/grey_deer_pullback/forward_log.jsonl`. The writer, when it exists, appends only to the three paths in §4. It does not open, append, or rewrite a #8721 file, a #8188 file, a risk-radar forward log, or `data/trial_ledger.jsonl`.

Idiom read for this rule, two modules:

- `engine/risk_radar_audit.py`: nightly gate, append to `data/risk_radar/forward_log.jsonl`, first-writer-wins on asof, issue receipt with `issued_at`. Its grader mutates `graded` on that same row. This design keeps the gate and the receipt, and puts the grade in the sibling instead.
- `engine/opex_risk.py` `log_window`: nightly gate, keep-first, `graded` null at stamp, no overwrite. `engine/credit_momentum.py` `_upsert_forward_log` adds the current-bar rule this lane uses for "latest closed session only". `engine/trial_ledger.py` is the append-only jsonl idiom for a different file, and this lane does not write it.

## 8. What this is not

- It is not customer-facing odds, severity, publication, or a capital change. Prereg §14 and manifest D4 stand. No sentence in a later writer may describe a retrospective stage-1 result as a forecast record.
- It is not a promotion to authority. The gauntlet is the promotion gate. This design does not promote, does not size, and does not change a displayed probability. Display of a null or of an unpromoted research state is a later decision under that gate, and it is not taken here.
- It is not a write to PR #8721, PR #8188, `site/`, `templates/`, `mockups/`, or `data/` by this design lane. This file is a research note.
- It is not a backfill of W3 scores into the forward log. Reconstruction is not issued history (§14). Prospective N stays 0 until a nightly row passes §1.
- It is not INC, and it is not the live risk-radar probability ledger.
- It is not a copy of the #8188 observer. P-active stays unissued until that observer is on main with byte-identical rules, on a later clock, without backfill.
- It is not prereg v1.1. The unfrozen 14-ticker panel does not issue under this blob.

No alternate confidence level, binning, block length, population, target, threshold, quantile level, cost ratio, power floor, or horizon is selected here. Those stay the frozen prereg's.
