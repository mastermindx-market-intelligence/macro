# Rotation Core — hold-out access ruling v1

**Recorded:** 2026-11-11, before Stage D was run, and before any candidate or baseline outcome was computed.
**Ruling by:** Prophet programme CEO (parent of Rotation Core), Phase 1 adjudication, decision 3.
**Recorded by:** Rotation Core research lead.
**Applies to:** `protocol_header_v1.json` (sha256 `af2a09886132bb784535e21134b63c2c86c579e186c248b20bb617fc77580f32`).
The header is unchanged. This ruling narrows access only: it changes no threshold, parameter, window, family or test count.

## Rule

1. The hold-out H (returns dated 2020-01-02 … 2026-11-06; J4 formations 2016-02 … 2022-05) is **sealed**.
2. `scripts/run_rotation_core_v1.py --stage H` refuses to run unless **both** of these hold:
   - `research/rotation_core/results_stage_D.json` is committed (tracked, clean, matching the working tree).
   - `research/rotation_core/HOLDOUT_RELEASE_v1.json` is committed (tracked, clean). It names exactly which configuration ids may be computed on H.
3. With both present, Stage H computes **only** the configurations listed in `HOLDOUT_RELEASE_v1.json`, plus the baselines and exposure-matched references their contrasts require. It computes no other configuration on H.
4. **The Rotation Core lead never writes `HOLDOUT_RELEASE_v1.json`.** The parent CEO writes it after adjudicating Stage D.
5. Stage D never computes, prints or stores any statistic of a return dated on or after 2020-01-02 (J4: any formation after 2015-12). Simulations run as one continuous causal path, but metric code receives only D-dated rows.

## Parent's stated default, recorded before any outcome

H opens only for candidates that clear G1, G2, G3 and G5 on D. It also opens for J5-A, J5-B and J2-E, built from J1* and J2*, if and only if those components cleared. If nothing clears, H stays sealed for a later v2 header.

## Consequence for the header

The header's two-stage design (Stage H runs right after Stage D is committed) is narrowed by this ruling. It is recorded in `results_stage_D.json` `deviations[]` as a pre-outcome access restriction.

## Parent ruling on Stage D (2026-11-11 09:50Z): v1 closed at L0, Stage H never run

The Prophet programme CEO read `RESULTS_STAGE_D.md` at commit `9aec219537` and accepted it. No v1 candidate cleared G1, G2, G3 and G5 on D. Under the default stated above before any outcome, the parent will not write `HOLDOUT_RELEASE_v1.json`. Stage H of protocol v1 is therefore never run, and v1 closes at L0 descriptive. The 2020-01-02 onward window stays unseen for this question and is reserved as a confirmation sample for protocol v2. Recorded by the Rotation Core lead at the commit that adds this paragraph.
