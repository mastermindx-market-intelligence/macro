# Q09 PREREG — publication-vintage ATS / non-ATS venue concentration

Status: frozen by FREEZE.log before `evaluate.py` reads any outcome. Later changes go only
into PREREG_AMENDMENT.md. Author: Claude Opus 5.5 (`claude-opus-5-5`), research reference only.

## 0. What was known before freezing (data qualification, not outcomes)

The data qualification (brief work item 1) was done before this freeze. It reads structure
and metadata only; no concentration, HHI or forecast error was computed.

- `data/finra_ats/` has 22 week files. `20231106.parquet` is a truncated pre-repair remnant:
  19,978 rows, tier `NMS`, 3,572 empty mpid, 494 duplicate rows. It is **excluded**. The
  21 complete weeks run from 20260413 to 20260831, with tiers T1/T2/OTCE, no empty mpid and
  40–44 mpids. `notional` is present from 20260629.
- `data/finra_otc_nonats/` has 17 weeks, 20260511–20260831. `mpid` is empty on every row.
  Firm identity is in `venue_name`, which includes the FINRA aggregate `De Minimis Firms`
  (mass of unknown composition).
- No stored file carries a FINRA initial-publication or update timestamp. The incumbent
  collector (`collectors/finra_ats_transparency.py`) writes each week once, after both T1
  and T2 partitions exist. It records no publication time and keeps no earlier vintage.
- Git history of origin/main (read-only `git log --name-status`) shows every week file
  added (A) and never modified (M), so the store holds **exactly one vintage per week**.
  Only the ingest heartbeat files were modified.
- First-add commit times are an **upper bound on when our store held the week**. They are
  not FINRA release times. Weeks 20260413–20260713 (ATS) and 20260511–20260713 (non-ATS)
  share one bulk/shallow-boundary commit, so they carry no per-week identity.
- Week 20260629 has 2,727 tickers present in both T1 and T2 (a tier reclassification).
  (ticker, mpid) is not unique within a week across tiers.

Consequence, fixed before any outcome: 0 weeks have publisher release identity and 0 weeks
have ≥2 vintages. Publication-vintage and revision-stability claims are therefore
**INSUFFICIENT_DATA** under the brief's falsifier. This was decided by data structure,
not by an evaluation outcome.

## 1. Non-duplication (incumbent refresh + collision check)

Greps of `_base` (read-only snapshot at d252f919):
- No hits for `venue_concentration`, `venue_hhi` or `offexchange_venue`. Module
  `engine/offexchange_venue_concentration.py` is NEW.
- HHI/Herfindahl appears in `portfolio_brief`, `smart_money` (`ownership_hhi`),
  `group_flow`, `stock_personality`, `signal_lab`, `factor_exposure` and others. None of
  them reads FINRA ATS/non-ATS venue data.

Incumbents and the narrow relation:
- `collectors/finra_ats_transparency.py` is the source writer. Q09 reads its output and
  does not change it. Its completeness gate {T1,T2} does not cover OTCE. Its docstring
  makes an owner-intent claim that Q09 does not repeat.
- `scripts/build_darkpool_desk.py::_compute_ats_venue_table` is the incumbent baseline.
  It builds a market-wide ATS venue share table for the latest stored week, with wow_pp
  against the prior file. It keys on `mpid.str.len() > 0`, so empty-mpid mass leaves the
  denominator silently. It labels by reporting week, not availability.
- `engine/darkpool_context.py::_venue_block` is a display projection of that table
  (top-8 + biggest mover, VENUE_MOVE=1.0pp). Q09 adds nothing to the display.
- `engine/darkpool_signals.py::venue_split` is a per-ticker ATS-vs-non-ATS split with
  firm-role mix. Q09 does not redo the role classification.

EXCLUSIONS incumbents (EXCLUSIONS_AND_DEPENDENCIES.md, off-exchange row): Q03 first, Q09
independent, Q10 then Q11. Venue analysis never enters frozen PSS-AF1 (DNR:HOLD-PSS-AF1-FINRA).
There is no crowding coupling (DNR:HOLD-PSS-CD1-CROWDING). It is not a fused composite
(DNR:KILL-FUSED-COMPOSITE) and not positioning fusion (DNR:KILL-POSITIONING-FUSION). It is
also not a live dark-pool print feed, a retail/institution classifier or a PSS-AF1
extension. No language model originates anything (DNR:KILL-LLM-ORIGINATION).

## 2. Estimand

- **Primary (descriptive stability)**: the relative reduction in holdout mean squared error
  for per-symbol weekly ATS venue HHI. The candidate is a multi-week, shrunk per-symbol
  training mean. The baseline is the incumbent-style single latest-observed-week snapshot.
  `R = mean_w(L_B,w − L_C,w) / mean_w(L_B,w)`, where `L_·,w` is the mean squared error
  across eligible symbols in holdout week w.
- **Vintage/revision estimand** (brief): the stability of concentration across publisher
  revisions. It is not estimable here (§0), and that part is reported as INSUFFICIENT_DATA.

## 3. Unit, clocks, cohort

- Unit of analysis is the symbol-week. The **honest-N unit is the holdout week.**
- Venue identity: ATS = `mpid`.
- Universe: ATS rows with tier ∈ {T1, T2}. OTCE is excluded because it is a different
  coverage universe and the collector's completeness gate does not cover it.
- A (week, ticker) present in more than one tier is **dropped as tier-ambiguous** and
  counted as attrition.
- Symbol-week eligibility: total T1/T2 ATS shares ≥ 100,000 in that week. This threshold is
  fixed a priori and is not tuned.
- Target: HHI over mpid shares of that symbol-week.
- Weeks: the 21 complete ATS weeks in file order. **Train = first 14 weeks; holdout = last
  7 weeks.**
- Input clock: the store-first-seen upper bound (§7 JSON). Every training week was first
  seen in the store at or before the bulk commit. Every holdout week was first seen
  strictly after it. The forecast origin is the bulk commit time, and the split therefore
  respects the availability clock. The reporting week is never used as availability.
- Output clock: results are labelled `as_of` = the latest store-first-seen among the
  inputs, as an upper bound and not a FINRA time.
- Cohort: tickers with ≥ 8 eligible training weeks. Holdout evaluation uses eligible
  holdout symbol-weeks of cohort tickers. Attrition and support are reported: cohort size,
  eligible holdout rows per week, and dropped tier-ambiguous rows.

## 4. Hypotheses, competitors, trial family

- H1: the candidate C has lower holdout MSE than the baseline B (R > 0).
- H0: R ≤ 0.
- Candidate C: `λ·mean_train(symbol) + (1−λ)·pooled`, where pooled = the mean of the
  cohort's training symbol means. λ ∈ {0, 0.25, 0.5, 0.75, 1.0} is chosen **inside
  training only**, by an inner chronological split: fit on training weeks 1–10 (inner
  cohort ≥ 6 eligible weeks), validate on weeks 11–14, and choose the λ with the minimum
  mean-over-weeks MSE (ties go to the larger λ). The model is then refit on all 14
  training weeks.
- Baseline B (incumbent analog): the symbol's HHI in its most recent eligible training week.
- Descriptive competitor P: the pooled mean. It is reported and not tested.
- Trial family: **exactly one** confirmatory comparison (C vs B on the holdout). No other
  holdout test, and no repeated holdout search.

## 5. Effect bar, uncertainty, decision

- Uncertainty: a moving-block bootstrap over the 7 holdout weeks with block length 2,
  10,000 replicates and seed 909. The numerator and denominator of R are resampled with
  the same week indices. Resampling whole weeks preserves cross-sectional dependence;
  blocks preserve serial dependence. Honest N = 7 weeks (≈4 blocks), which is very small
  and is stated as such.
- Practical bar: the descriptive-stability sub-result is **KEEP** iff R ≥ 0.10 AND the
  bootstrap 95% CI lower bound of R > 0. Otherwise it is **REJECT**.
- Overall verdict rule:
  - If `n_with_publisher_release_identity == 0` or `n_with_multiple_vintages == 0`, the
    overall verdict is **INSUFFICIENT_DATA**. The missing input is named as: FINRA
    weekly-summary initial-publication/update metadata per (week, tier) and retained
    multi-vintage snapshots.
  - The sub-result is reported but cannot upgrade the overall verdict.
  - Nothing is promoted under any outcome.

## 6. Descriptive (non-trial) outputs and baseline reproduction

- Reproduce the incumbent `_compute_ats_venue_table` logic on the latest two ATS weeks
  (the mpid filter, share_of_total_pct and wow_pp), and log the sha256 of its output.
- Apply the incumbent mpid filter to the matching non-ATS week, and report the fraction of
  mass it would drop.
- Market-wide latest-week ATS venue HHI (over mpid), with conserved shares.
- Non-ATS HHI over `venue_name` with `De Minimis Firms` as unknown mass. Two upper bounds
  are reported: a separate-venue bound and an overlap bound.
- Exact HHI change decomposition, latest vs prior week (within-common / entry / exit).
- Every emitted string passes the forbidden-interpretation guard (no accumulation, net
  buying, live print or short interest).

## 7. Source vintages (licensed local data, vintage cdab6268, read-only)

Root: `/Users/chriswong/Documents/Cluade/macro-main/data/`. evaluate.py recomputes each
sha256 and refuses to run on a mismatch.

```json
{
  "files": {
    "finra_ats/20260413.parquet": "27f384e472ce266a7aedd3041581ef6aa321acc13a699275f13f3234660d9243",
    "finra_ats/20260420.parquet": "c61a7810c125d38349b275a277fd829249286d3a0d17e501827b910c7fbb1d92",
    "finra_ats/20260427.parquet": "e8da438ccd366b3b608b32f15e4b18be7117cd378b2037f73fc7d13e4a3ffb4e",
    "finra_ats/20260504.parquet": "67c1341d3deaa2fc1af0f2223af3948005cc1460d1e6d04607727959b6ede495",
    "finra_ats/20260511.parquet": "cb82202dad2e368e3d1eac5ceb3ef50a38f9d52659d3d4b975f002f452db44e7",
    "finra_ats/20260518.parquet": "2f76fa55fa84b6ca1d57fd8e417693a0dc83060cc64923e9540326e64963579c",
    "finra_ats/20260525.parquet": "8ab283f3eb97ef61a7fbb07c73629853dbbcf0e28b83bab345bdd30b87cba833",
    "finra_ats/20260601.parquet": "76ea3cea920d739ad69d247c958929c065805977cc31514fe09c0dbb5b5901df",
    "finra_ats/20260608.parquet": "1159f68765a2d98f88893dedae051f72a7f1fba6b1ee5e406fef6cabe880a407",
    "finra_ats/20260615.parquet": "08514206f1451753177ad582cf050974414d309abcf7dfb9dfba4620d40dd215",
    "finra_ats/20260622.parquet": "93b3792f496963742278eecaf53798fba85f85705cb2634da1b822f491504648",
    "finra_ats/20260629.parquet": "60ac91f7d32dc4fda553abd78f6106e63f525252eb85cecf1aee178a2ad0efcd",
    "finra_ats/20260706.parquet": "8649f28e0fa938916cd52763bff3059f90fe81ec31b2ee919cedee6b38164a09",
    "finra_ats/20260713.parquet": "33bc982bb031409532e2054b2d9eafa057731bed34d7b7ecadf7a76e32ec44d1",
    "finra_ats/20260720.parquet": "477b283e93cac2d1df21ffcaedb7f8a54a86f448bdddc9d568d255ed830d931a",
    "finra_ats/20260727.parquet": "c50cb6a732f8729a5aaec77cceb71e19439095343481a87c5d1c24193e83a191",
    "finra_ats/20260803.parquet": "5ec10d79bbfe91ed53c4f3524c9a75e5fa5b3bfd4c1022f8d18855998601a058",
    "finra_ats/20260810.parquet": "3c6aa61468539bb3353732bc7ee5031cfaf2703f0d1bce4965e8c988b114f908",
    "finra_ats/20260817.parquet": "a42749e9bd504c705b511d872312c9b3c97d761a391d131db709b45f9cb8cde9",
    "finra_ats/20260824.parquet": "78986bf586288f99dbf2d0859ff7c7e6cdb87a2056548d91e50cc70c6c359a57",
    "finra_ats/20260831.parquet": "93a48afb3320e63728503feb8dc0442594e8420f18a7c853b40d4b7a08f34272",
    "finra_otc_nonats/20260824.parquet": "c0e334aa068fcd9ec2d9bcf23d5d7d6868755164dff22ae0cb4308fe74852d40",
    "finra_otc_nonats/20260831.parquet": "9c507c341c9c725b2a5c36115d71762392ca0990d6faf73d7caf136fff935b09"
  },
  "excluded": {
    "finra_ats/20231106.parquet": "cf2e9dfdc6ba989b3a4d495303345a9e9623d7d7c679e1f4d77d8d60d5ab232e"
  },
  "store_first_seen_upper_bound": {
    "bulk_commit": "69268b06502cdbfb9cdf9ae24e6e64663b17c8ed",
    "bulk_commit_time": "2026-08-23T22:55:42Z",
    "bulk_weeks": ["20260413","20260420","20260427","20260504","20260511","20260518","20260525","20260601","20260608","20260615","20260622","20260629","20260706","20260713"],
    "per_week": {
      "20260720": ["b63e336e82295a842fe8addd5e7d1587a1e2a1b7", "2026-08-25T01:33:25Z"],
      "20260727": ["1a81abce4e1633a5d0b81877ca669735872ebfd6", "2026-09-01T03:51:21Z"],
      "20260803": ["a4bfb29e460fbbd27984438b314d9200daf48f84", "2026-09-09T03:37:46Z"],
      "20260810": ["95d24fa1d6ab859d99cbccc1c7218f49fd30af97", "2026-09-15T03:55:44Z"],
      "20260817": ["7c75130b797a62b874a85054dcd55e64017d53a9", "2026-09-22T04:07:43Z"],
      "20260824": ["df166dd0cdfc9c3c6197c68de503158152eb1803", "2026-10-01T11:28:48Z"],
      "20260831": ["ad2e466898473301f4c7a6402f3c1858c64b9fa4", "2026-10-06T04:40:36Z"]
    },
    "publisher_release_identity": "none stored",
    "vintages_per_week": 1
  },
  "params": {
    "tiers": ["T1", "T2"], "min_week_shares": 100000, "n_train": 14,
    "min_train_weeks": 8, "inner_fit_weeks": 10, "inner_min_weeks": 6,
    "lambda_grid": [0.0, 0.25, 0.5, 0.75, 1.0], "block_len": 2, "n_boot": 10000,
    "seed": 909, "effect_bar": 0.10
  }
}
```

Non-ATS weeks beyond the two used for descriptive output (20260511–20260817) are qualified
in §0 but are not inputs to any computation.

## 8. Falsifier and stop rule

- Falsifier (brief): if release vintages or common denominators are unavailable, output is
  limited to currently released descriptive concentration, and historical predictive
  claims are withheld. Release vintages are unavailable here (§0), so this falsifier binds.
- Stop rule: the holdout comparison runs once. Re-runs must reproduce identical numbers
  (deterministic seed). No parameter in §7 changes after the freeze; any change goes to
  PREREG_AMENDMENT.md, labelled post-hoc, and cannot alter the verdict.
- Restrictions: ATS/non-ATS is a venue/reporting category, not owner intent. FINRA weekly
  volume is not short interest or net buying. Nothing is wired, gated or promoted.
