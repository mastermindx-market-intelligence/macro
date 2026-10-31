# T13 frozen-sample metadata result — 18 October 2026

**Accept the bounded metadata diagnostic. Refuse the 21-session matched lane for lack of established event/control support. No model, probability or policy is admitted at any horizon.**

This is a post-observation feasibility result in the existing Grey Deer programme. The original sample's shortfalls were already known before this diagnostic; confirmation of those weaknesses is not a new predictive discovery. The original sample, labels, draft hypotheses and trial budgets are preserved. The [independent post-execution review](POST_EXECUTION_REVIEW_2026-10-18.md) found no identity, record-coverage or arithmetic errors and accepts only this bounded artifact and its support/refusal findings.

## Freeze and one execution

Sol adopted the [sample-use contract](T13_SAMPLE_USE_CONTRACT_2026-10-18.md) after [independent pre-execution review](T13_SAMPLE_USE_CONTRACT_REVIEW_2026-10-18.md), then committed it and [diagnostic source](t13_sample_metadata_admission.py) at **9102e6954db145b92dd3d1c32e113405104ce212**. Root separately read the committed Git objects and verified contract, source, sample and freeze-receipt bytes against the working files before execution. The source logic is identical to the independently reviewed proposal; only its module docstring changed.

One invocation started **2026-10-18T02:07:24.626119Z** and completed at **02:07:24.693074Z**, exit0. The [execution receipt](T13_SAMPLE_METADATA_ADMISSION_RECEIPT_2026-10-18.json) binds command, hashes, environment and timestamps. [The complete metadata output](T13_SAMPLE_METADATA_ADMISSION_2026-10-18.json) is **1,248,719 bytes**, SHA256 **91a45bc0f4ecb650db01bdeb5e9ec6834a09249ed4057d5a5d54a4d5cd6841e5**. No source module, builder, price file, feature, model or trial ledger was invoked by this diagnostic.

## Support remaining after the frozen warm-up and maturity rules

| Horizon | Original controls / requested | Supported pairs | Events with any supported pair | Events with three individually supported pairs | Disposition |
|---|---:|---:|---:|---:|---|
| 5 sessions | 10 / 18 | 9 | 4 / 6 | 2 / 6 | Necessary structural support only; power and fitting unadmitted |
| 10 sessions | 3 / 21 | 2 | 2 / 7 | 0 / 7 | Necessary structural support only; power and fitting unadmitted |
| 21 sessions | 1 / 24 | 0 | 0 / 8 | 0 / 8 | REFUSE_NO_ESTABLISHED_MATCHED_SUPPORT |

Role-supported and common-offset-supported pair counts happen to agree in this output. They remain distinct definitions and fields. Three supported pairs means three comparisons attached to the same event, each with its own surviving offsets; it is not three independent events or one offset set shared by all controls.

The sole originally matched 21-session episode has four positive origins at indices41–44. All fail the required index63 warm-up. Three later padded-window origins survive, but contain no positive origin. Its control has26 mature origins and20 immature origins; those facts do not repair the absent positive event support. At5 sessions, the entirely pre-warm-up control is retained and excluded; the tail control retains partial mature support. At10 sessions, one of the three controls loses all40 origins to warm-up.

## Denominator, missing dates and dependence

The output preserves **2,138 window-origin records in35 original windows**, not2,138 independently scored market decisions. It keeps110 pre-warm-up records and24 immature records with explicit reasons. There are2,004 metadata-eligible window-origin records, but **zero admitted scored origins**. These counts include the distinct appearances of dates in different horizons/windows.

Only237 origin records have dates directly bound by the permitted metadata; the other1,901 dates remain null. The diagnostic neither invents a calendar nor aligns FRED's348 missing origins to an assumed index range. Every per-origin label and feature-availability value remains null. All39 cross-horizon window intersections retain both original roles and identities. **Independent episode count remains null.**

The matched5/10-session event support remains confined to2022. Incomplete controls, concentration in one market era and overlapping horizons do not provide general out-of-sample validation. The retrospective case/control mixture cannot be used as a daily event probability or as evidence that the live21-day22% number is calibrated.

## Resulting programme decision

Retain the original21-session matched-sample failure as an explicit refusal under this freeze; do not manufacture controls, relax warm-up, shorten windows or silently replace the sample. The5/10-session lanes have some necessary pair support, with no established independent N, chronological evaluation, power or predictive value. Their model admission remains **NOT_ADMITTED**.

Retained-FRED fitting/evaluation and probability-publication purposes remain **UNKNOWN / operational HOLD**. An exact calendar, original daily outcome vector, purpose-qualified point-in-time feature availability, chronological evaluation, same-support baselines, counted fits and power/utility rules must be admitted before scoring. A materially changed history or sampler is a declared development revision, with this failure retained; it cannot be called an untouched continuation of this freeze. No T13/T14/T19 fit or trial was spent.

The next useful work remains real delivery integrity and qualification of a defensible research denominator through existing owners. Risk Radar's numerical allocation/execution authority stays false; Portfolio/Prophet retain their validated policy boundaries. This result accepts a diagnostic artifact, not the programme or a trading decision.
