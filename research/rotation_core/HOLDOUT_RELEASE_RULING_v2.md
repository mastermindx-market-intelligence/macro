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
