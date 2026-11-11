# Rotation Core v2 — hold-out release ruling R13 (staged release)

- **Ruled by:** Prophet programme CEO, 2026-11-11 12:42Z (real UTC). Recorded by the Rotation Core lead.
- **Frozen header:** `protocol_header_v2.json`, sha256 `ca5af27429b54df534e959bde8a3db037c95f7fe5c7c430fe7e6bb5b03d01728` (freeze commit `ac68f2e72a`).
- **When written:** after the selection result on 1998–2019 (`1ca5228b3c`: selected h = 3, b = 25; H1 −2.29 %/yr against its matched mix, H3 +1.33 %/yr; neither informative), and before any v2 number on pre-1998 or 2020–2025 exists.
- **Scope:** R13 changes no rule, threshold, window, yardstick or pass condition in the frozen header. It fixes only the order in which the two confirmation windows are read, which the header leaves to the parent's release file.

## The two confirmation windows are not equally clean

- **Pre-1998 (Ken French industries, 1928–1997)** was already examined for this question by Pro run B's ten rules on the French 49 industries 1926–2019. Those 10 trials are counted in the ledger. This window is not clean.
- **2020-01-02 → 2025-12-31** is the only window no test of this programme has read. It contains about two stress episodes. It can be opened once.

## Rule

**Stage 1.** The parent releases `pre1998_1928_1997` only. One run computes, for the selected setting:
- H1, the price-only control (for H2), H3 and the cash ablation;
- all four yardsticks (the French market in place of SPY, the stated equal-weight proxy in place of RSP, equal-weight industries, and the binding exposure-matched mix);
- each era (1928–1945, 1946–1997) and the full window, at 10 bp and at 2× costs;
- drawdown against the mix, turnover, and false DEFEND calls per calm year.

No pooled Holm p is computed at this stage, because it needs both windows. No date after 1997-12-31 is read in Stage 1.

**Stage 2.** 2020-01-02 → 2025-12-31 opens once, by a second release the parent writes, **only if** at least one of H1 and H3 has a positive point estimate over its matched mix in **both** pre-1998 eras. The runner checks this against the committed Stage 1 result file, not against anyone's word. If the window opens, it opens for every configuration in the header at once, including the tradable-funds check and the named mapping. The pooled Holm test (m = 3, all three hypotheses, as frozen) is computed then. A hypothesis that already failed its pre-1998 leg stays FAIL; its 2020–2025 numbers are reported, not scored.

**If neither H1 nor H3 clears the pre-1998 leg:**
- the historical tier closes as FAIL for all three hypotheses;
- 2020–2025 and the sealed French post-2019 files stay sealed and are recorded as unspent;
- the forward tier is unaffected.

## Why this ordering cannot raise the false-positive rate

The frozen pass condition is a conjunction. One of its necessary parts is "point estimate > 0 in both pre-1998 eras" on the primary contrast. A hypothesis with a non-positive estimate in either era fails the frozen test, whatever 2020–2025 shows.

R13 only ever skips reading 2020–2025 in that case. It never adds a way to pass, never changes a statistic, and never lets Stage 1 numbers alter anything computed in Stage 2. Every pass under R13 is therefore also a pass under the frozen header read in one go, and the false-positive rate cannot rise. For H1 and H3 the stop costs nothing, because the stopped case is already a fail.

**The lead's caveat, recorded before any number (one place where the stop is not costless).** H2's primary contrast is its own paired difference, H1 minus the price-only control, and its sign leg is on that difference. Suppose H1 and H3 both fail their pre-1998 eras while H2's paired difference is positive in both. Then R13 keeps 2020–2025 shut, and H2 never receives the test it could otherwise pass.

That is a loss of power for H2, not a route to a false positive, so it is not a stop under R13's own test. The parent may name H2 in the Stage 2 release's opening-condition list if the parent wants H2 to be able to open the window. The runner reads that list from the release file.

## Guards (implemented in `scripts/run_rotation_core_v2.py`)

- **Stage 1** requires a committed, clean `HOLDOUT_RELEASE_v2.json` whose `windows_released` is exactly `["pre1998_1928_1997"]`. It reads only the truncated `le2019` French copies, refuses any date after 1997-12-31 and any sealed path, and runs once.
- **Stage 2** requires a second committed release, `HOLDOUT_RELEASE_v2_stage2.json`, with `windows_released` `["2020-01-02..2025-12-31"]`. It also requires a committed Stage 1 result file that satisfies the opening condition named in that release. It runs once.
- **Order of work still open:** Sector Intelligence's reviewer findings on the engine. Stage 1 does not run until the parent forwards them or says there are none.

---

## Amendment 1 to R13 (parent 12:48Z and 12:51Z; recorded before any pre-1998 or 2020–2025 v2 number exists)

**a. Failures stay failed.** A hypothesis whose point estimate is not positive in both pre-1998 eras is recorded FAILED before 2020–2025 opens, and nothing read later revives it. The Holm family at the pooled test is the full frozen family of three (H1, H2, H3), computed exactly as frozen, never the survivors.

**b. Pass sets and effect sizes.**
- **Identical-pass-set argument.** The lead flagged a flaw (12:48Z): it holds for H1 and H3, not H2. Sector Intelligence confirmed this, and the parent ruled (f) below. Read with (f), the frozen pass test (pooled Holm p plus the sign legs) is unchanged, and staging cannot raise its false-positive rate:
  - every outcome that passes under staging passes unstaged;
  - for H1 and H3 the pass sets are identical, because their stopped outcomes fail the frozen conjunction anyway;
  - for H2 the staged pass set is a subset.
- **Effect sizes.** Any pooled or all-eras point estimate reported after a gated opening is conditional on the gate and biased upward as an effect size. The 2020–2025 standalone estimate is reported as the out-of-sample effect size. Pooled figures are reported for the frozen test only, labelled "conditional on the pre-1998 gate, not an unbiased effect size".

**c. Gate definition.**
- **Statistic:** the sign of the point estimate of annualised mean daily excess of the book over its exposure-matched mix, net of costs at 10 bp per side, for H1 at the selected setting and for H3.
- **Eras by date:**
  - E1 = 1928-01-02 → 1945-12-31. 1928-01-02 is the first scored session: H1 and the price-only control first have a state on 1927-06-01 and H3 on 1926-12-31, so the frozen window start of 1928 governs.
  - E2 = 1946-01-02 (the first session of 1946) → 1997-12-31.
- **What the header says about the mix:** the frozen header builds the mix "at H1's average weights, rebuilt inside every bootstrap resample from that resample's own average weights". It is silent on era-level estimates. **Specification made before the read:** the mix for an era's point estimate is built on that era alone.
- **Release contents:** the release file carries the engine commit, the frozen header sha256 and the selected configuration. The runner refuses unless engine, scripts and tests at HEAD are byte-identical to the named engine commit and the tree is clean. A release commit necessarily sits on top of the engine commit, so "refuses any other commit" is enforced as "refuses any other engine code".
- **Engine fixes after a read:** any engine fix after a window has been read reruns every window read so far, including ones that passed, as a logged deviation.

**d. A closed gate.** 2020–2025 stays unread. Pre-1998 then counts as development data for any successor protocol, and a successor's trial count carries all 55 (v1's 36, v2's 9, run B's 10) plus its own.

**e. Funds.** The gate is on industry portfolios only, since no sector funds exist before 1998-12-22. The tradable-funds veto applies in full at 2020–2025 and cannot be waived or softened by a strong pre-1998 result.

**f. H2 under a closed gate.** H2's pass set is not inside the gate: H2 can be positive in both eras while H1 and H3 each miss one, so staging shrinks it. A closed gate records H2 as FAILED on the historical tier, not as untested. This is conservative, and it is disclosed as a consequence of staging.

**g. The gate is the same number the final conjunction uses.**
1. **Setting:** H1's gate setting is "the grid point selected at commit `1ca5228b3c`" (h = 3, b = 25). The runner reads it from the committed `results_v2_selection.json`, never from an argument, and refuses a release naming anything else.
2. **Costs, stricter reading:** "holds at 2× costs" applies to the whole conjunction. Significance and every sign leg must hold at 10 bp per side and again at 20 bp per side. The gate is evaluated at 10 bp only, so under this reading the gate is implied by the frozen pass condition and removes no passing outcome for H1 or H3. The header's wording also admits a narrower reading (2× applying to the effect alone); R13 takes the stricter one before any confirmation number exists.
3. **One function:** `engine.rotation_core_v2.window_excess` (mix on the window or era alone) computes the gate signs and the final conjunction's era signs. A test asserts it returns the identical value as the era point estimate of `matched_contrast`.

**h. No open choices while anyone knows a pre-1998 number.**
- **Seeds:** stage 1 20261113, stage 2 20261114, pooled test 20261115. Within a stage, books use fixed offsets written in the runner.
- **Bootstrap:** B = 10,000; mean block 21 sessions, 63 as sensitivity; the stationary bootstrap of the frozen header. The gate uses no bootstrap.
- **Pooled series across the 1997-12-31 / 2020-01-02 join.** The frozen header says only "the pooled pre-1998 + 2020-2025 primary contrast". The lead chose the conservative construction:
  - each window keeps its own daily excess series, with its own exposure-matched mix built on that window alone;
  - the bootstrap resamples each window separately, so no block spans the join (stratified);
  - the pooled statistic is the years-weighted mean of the two windows' annualised excesses;
  - the one-sided centred p is taken from that stratified distribution.

  **Why conservative:** a single mix across 1928–2025 would be one fixed reference over two eras of very different leg returns, which flatters a book whose average weights differ between windows. Separate mixes remove that. No block crosses a 22-year gap.
- **Choices the frozen header leaves silent** (each made without looking at data):
  1. **Era-level mix:** built on the era alone, for both the gate and the final conjunction.
  2. **Annualisation:** observed sessions per calendar year in the window or era, because pre-1952 French data includes Saturdays. Signs are unaffected.
  3. **Pooled construction:** as above.
  4. **First scored session:** 1928-01-02, taken from the frozen window, not from first state availability.
  5. **"Holds at 2× costs":** the stricter reading (g.2).
  6. **Drawdown condition:** "drawdown no worse than the matched mix" is assessed on the full pre-1998 window and on 2020–2025 separately, and both must hold.
  7. **H2 at stage 1:** its era signs are recorded in the gate file but do not open the window unless the parent names H2 in the stage-2 release.
- **Stage 1 is blind to magnitudes.**
  - **What the run prints:** only the four gate signs (H1 and H3, each era), the gate result, non-return integrity diagnostics, and the sha256 of the results file. The diagnostics are session counts per era, offence-member counts, deferred executions, days holding after a last close, dropped industry-days, state counts and episode count. H2's era signs are written to the gate file, not printed.
  - **Sealing:** every return, excess, interval, p-value, drawdown and cost figure goes to `/home/ubuntu2/tmp/rotation-core/data/sealed_stage1/results_v2_stage1_pre1998.json`, written mode 000. The committed `results_v2_stage1_gate.json` carries the signs, gate result, diagnostics, engine commit and that file's sha256.
  - **Gate open:** the sealed file stays unopened; the final run recomputes pre-1998, and `verify_reproduction` refuses to print anything unless the recomputation's sha equals the sealed sha.
  - **Gate closed:** the sealed file is readable through `open_sealed_stage1` and is reported in full; 2020–2025 stays unread.
  - **Tests:** stdout contains no decimal number (fixture run); the sealed file is unreadable without a stage-2 release or a recorded closed gate; the reproduction check fails on a one-byte difference; a fixture recomputation is byte-identical.
  - **Integrity under the blind:** nothing needed a magnitude. The integrity checks that matter (gaps, deferrals, dead positions, state counts, window dates) are all counts.

**i. Reporting rule.** The pooled minimum detectable effect is about 2.1–2.3 pp/yr, and about 7.6–8.3 for 2020–2025 alone, so a pooled p-value is set almost entirely by pre-1998, which the header discloses as previously examined. If the gate opens and the test passes, the result text gives the 2020–2025 standalone estimate with its interval. It says in words that significance comes from the examined window and that the unexamined window supplied a sign check, which a rule with no edge passes about half the time. The label stays "survives falsification on history"; nothing stronger is written anywhere, including the PR draft.

## Notes on the frozen header (power method)

- **MDE lines** (`power_statement_top`, `power.h1_actual_tilt`):
  - MDE = (z₁₋α/₃ + z₀.₈₀) × SE.
  - SE is the standard deviation of a stationary-bootstrap distribution (block 21, B = 4,000) of H1's matched-mix contrast on 1998–2019, scaled by √(D years ÷ window years).
  - **Method:** normal approximation, at the Bonferroni bound α/3 (Holm's first step, the worst case). It is not a simulation under Holm.
- **Joint-rule pass probabilities** (63 % at the MDE, 50–57 % at 2 pp/yr):
  - Monte Carlo of independent normal per-window estimates (E1 17.2 y, E2 52 y, 2020–2025 6 y) with D's per-year standard deviation;
  - pooled significance at the Bonferroni bound α/3, plus the four sign legs;
  - normal approximation, Bonferroni bound.
- **Post-freeze check, labelled as such** (`v2_power/power_holm_sim_D.*`):
  - **Method:** simulated under Holm (m = 3) with the D covariance of the three contrasts (variance and covariance only, centred series), H1 at the MDE and H2, H3 null.
  - **Results:**

    | True H1 edge | P(H1 rejected), Holm | P(H1 rejected), Bonferroni | Joint pass, Holm | Joint pass, Bonferroni |
    |---|---|---|---|---|
    | 2.18 pp/yr | 0.805 | 0.803 | 0.636 | 0.635 |
    | 2.0 pp/yr | 0.73 | 0.73 | 0.57 | 0.57 |
    | 1.0 pp/yr | 0.23 | 0.23 | 0.16 | 0.16 |

    The frozen figures are accurate approximations.
- **Bootstrap calibration** (`tests/test_rotation_core_si_findings.py`): under an AR(1) null (φ = 0.1, 3,000 sessions, 300 replications, B = 400, block 21), the measured one-sided size at nominal 5 % was **4.3 %** and the 95 % basic-interval coverage **94.7 %**. The tolerance, declared before running, was size in [2 %, 9 %] and coverage in [90 %, 99 %].
