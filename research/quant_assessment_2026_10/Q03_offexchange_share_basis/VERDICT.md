# Q03 VERDICT — KEEP (research reference only; not wired, not promoted)

**Verdict: KEEP.** This verdict comes from the single preregistered primary run. All four §10 gates passed on the chronological holdout.

KEEP means one thing only. Converting both sides of off-exchange participation to one share basis, using an explicit vintage-stamped factor record, removes the mechanical split artefact. It does so without disturbing nonsplit names.

KEEP does not mean any of the following:
- a signal
- a promotion
- a wiring request
- a claim about buying or selling

A corrected participation ratio is never institutional buying. FINRA short volume is not short interest or net buying. ATS/non-ATS is a venue category, not owner intent.

## Frozen protocol

| item | value |
|---|---|
| PREREG.md sha256 | `ca5e84bd6dc3fe074bcfc777707b55889e3dcb7f90da64d862c7ac6a8f1443f9` |
| frozen at | `Fri Oct  9 09:38:13 UTC 2026` (`date -u`, FREEZE.log), before any outcome was read |
| amendment | PREREG_AMENDMENT.md. Amendment 1 was written before the first evaluate run and adds a descriptive comparator and implementation clarifications only; no gate changed. Amendment 2 is a post-run provenance note: module bytes restored, evaluate.py hash trail, gate (c) relabelled. It changes no gate and no parameter |
| runs | exactly one `--stage baseline` and one `--stage primary` (RUNS.log, both exit 0); no rerun and no holdout re-search |

## Result (holdout = last 60% of eligible events by date)

| quantity | value |
|---|---|
| eligible events (all) | 11 events / 11 tickers / 7 quarter blocks |
| training (first floor(0.4·11)=4) | HUT 1:5 reverse, NVDA 10:1, AVGO 10:1, SMCI 10:1 |
| holdout | LRCX 10, ANET 4, PANW 2, TSCO 5, ORLY 15, NOW 5, POWL 3 — **7 events / 7 tickers / 4 blocks** (2024Q4, 2025Q2, 2025Q4, 2026Q2) |
| training A1 diagnostic | median E_raw 2.223 vs median log r 2.303 → within ±log 1.25 (vendor volume is split-adjusted as assumed) |
| holdout per-event \|E_corr\| (primary support) | **all 7 within the ±log 1.25 = 0.2231 bar; max \|E_corr\| = 0.1018 (TSCO); all 7 positive, range +0.0013 to +0.1018**. Raw basis: min \|E_raw\| = 0.740, so all 7 are outside the bar |
| holdout median E_corr (secondary) | +0.0382 log, quarter-block bootstrap 95% CI [+0.0013, +0.0468] (10,000 reps, seed 3003; only 4 blocks, so the CI is coarse) |
| holdout median E_raw (incumbent-basis) | +1.648 log, CI [+1.106, +2.709] |
| share \|E_corr\| ≤ log 1.25 | 7/7 = 1.00 (raw basis: 0/7) |
| gate (a) CI ⊂ ±0.2231 | PASS |
| gate (b) ≥80% within bar | PASS |
| gate (c) controls corrected == raw, bitwise | PASS (390 control names). **This is a construction invariant, not an empirical test** (Amendment A2.4): with no actions, corrected = num·1.0/den = raw, so the gate cannot fail |
| gate (d) panel/panel_deep sha unchanged; short columns never read | PASS (sha before == after; loader reads only date/ticker/total_vol) |

E is the event's level shift in median log participation (post 40 vs pre 40 valid rows), minus the median level shift of same-date nonsplit controls. Controls per event: 63–68.

### Incumbent comparator (descriptive; amendment A1.1)

`share_break_index` is applied to each event's 80-row window.
- **Raw basis:** a break fired inside the post window on 11/11 events. `usable_history` discarded 68–69 of the window's rows.
- **Corrected basis:** 0/11 fired.
- **Literal ±3-row fire rate:** 0 on both bases. This is expected: the incumbent returns the LAST crossing index, about 40 rows after the break (A1.1).
- **Median |trailing_z| over the first 20 post rows:** 7–163 on the raw basis, against 0.37–1.21 corrected and 0.65–0.81 for the control median.

The incumbent's truncation is therefore correct as damage control. Correction restores the comparable history it throws away; for AVGO it keeps all 801 rows instead of the 533 left after the break at index 268.

### Retained baseline case (results/baseline.json)

| case | basis | value |
|---|---|---|
| fixture: true 0.2, 10:1 | mismatched | 0.02 |
| | restored | 0.2 |
| | incumbent break fires | raw only |
| AVGO 2024-07-15 10:1 (training) | pre-split median, raw | 0.0364 |
| | pre-split median, corrected | 0.3637 |
| | post median | 0.3579 |
| | D_raw | +2.287 |
| | D_corr | −0.016 |

## Honest reading and limitations

1. **Small N.** 7 holdout events in 4 blocks just clears the preregistered INSUFFICIENT_DATA floor (6 events, 4 blocks). A 4-block bootstrap is coarse, and the CI understates block-level uncertainty. The primary support is therefore per-event, not the CI: every one of the 7 holdout events has |E_corr| ≤ 0.102, under half the 0.223 bar, while every raw-basis |E_raw| is ≥ 0.740. Under a null in which each event independently falls outside the bar with probability ≥ 0.5, seven of seven inside has probability ≤ 1/128. The median residual is about 6× smaller than the bar, and the raw artefact is about 40× larger than the residual. The 7 corrected residuals are also all positive (see 2).
2. **Small positive residual.** The +0.038 residual is distinguishable from zero (the CI excludes 0) but well inside the practical bar. It may be real post-split participation change (retail access, index or option effects) or vendor-volume noise. It is not interpreted, and it is never a buying claim.
3. **Ex-post vintage.** The factor store (`share_quality_reference.json`, fetched stamps 2026-07/09) postdates every event. This is a correction of history, not a point-in-time reproduction. Revision behaviour is covered by the adapter contract (req3), not by observed revisions: no owner-published revision vintages exist locally.
4. **Coverage is selection-biased.** The store attests 1,323 names; 404 of 1,642 panel tickers joined with yahoo and were attested. 19 unattested names still show an incumbent break, among them BKNG, MSTR, WMT, AZO, FAST and several sector ETFs. For these the adapter returns BASIS_INCOMPATIBLE / NONCOMPARABLE and does not repair them. This is the brief's falsifier branch: qualified coverage plus explicit noncomparability.
5. **Attrition.**
   - CRWD 2026-07-02 4:1: post support 6 rows (beyond the attestation horizon).
   - GE 2024-04-02 ratio 1.253: AMBIGUOUS (spin-off adjustment) → a segment boundary, never a factor.
   - KLAC 2026-06-12 10:1: only 1 control attested through the window.
6. **Assumption A1.** Vendor volume is split-adjusted as of the file's last row. Training was consistent with this; it is not proven per file.
7. The frozen PSS-AF1 construction is untouched. short_vol/total_vol is within-FINRA and basis-invariant, and the module does not compute, accept or emit it.
8. **Beyond-horizon rows keep row class VALID.** When `denominator_as_of` is past the vintage's `attested_through`, rows stay `VALID`. Only the read-level `level_status` drops to `RELATIVE_WITHIN_SEGMENT`, so a consumer filtering on `row_class` alone would treat those rows as fully comparable. This evaluation was not exposed to that, because `window_vals` clips post rows at the horizon H itself. A consumer must read `level_status`, or a future module revision must add a distinct per-row class. That would be a module logic change, outside this frozen evaluation; see the independent-audit gap in PR_BODY.md.

## Corrected-read proposal (versioned; no in-place ledger rewrite)

A future owner may consume `normalize_participation(..., denominator_convention=ADJUSTED_AS_OF, denominator_as_of=<vendor vintage>)` with factors from the corporate-action owner (#8680 S1 / #8677 basis where applicable). Each read carries a `result_id` bound to the factor-vintage hash, and `append_read` keeps earlier vintages.

This deliverable does not wire, register, schedule or gate anything.

Sequencing per brief: Q03 → Q10 → Q11, one activity owner integrating. Venue analysis never enters PSS-AF1.

DNR keys respected:
- KILL-OUTCOME-AUDITION (no forward-return search)
- KILL-LLM-ORIGINATION
- KILL-FUSED-COMPOSITE
- KILL-POSITIONING-FUSION
- KILL-REGIME-SCORECARD
- KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR
- KILL-CAUSAL-DAG-ALPHA
- HOLD-PSS-AF1-FINRA
- HOLD-PSS-CD1-CROWDING

## Module sha note

Both runs used module sha256 `193c006ceba46274a20cab03d74a831801af96189300e6f6865a3e7a0d52d6ca`, the freeze-time module. After the primary run, the author edited the module's `__doc__` string to embed this verdict, which produced sha256 `0b36697890a16af2999471b61be026b85a1083b381aa87d046a7d693a6e9c729`. The finisher restored the evaluated bytes (PREREG_AMENDMENT.md A2.1). **The shipped module sha256 is `193c006c…d6ca`, identical to the frozen and evaluated module.** The verdict numbers live only in this file.

The shipped evaluate.py, `48dea05f…56d5`, is byte-identical to the version both runs used. Its post-freeze, pre-run edit trail is in A2.2. Its refusal checks only the PREREG hash. A future rerun must also match the module hash recorded in FREEZE.log (A2.3); evaluate.py does not enforce that in code.

## Freeze-refusal demonstration

A scratch copy of evaluate.py was run against a tampered PREREG copy, outside the deliverable tree. It exited 2 with the message `REFUSED: sha256(PREREG.md)=ec8fdc7a… != FREEZE.log ca5e84bd…` and logged that refusal to the scratch RUNS.log.
