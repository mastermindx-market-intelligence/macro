---
workstream: "WS:PROPHET-REGIME-TIMEFRAME-RESEARCH"
session: >
  claude/prophet-astra-regime-w1-results-20261004 (Fable seat session f273dd7d, worktree
  astra-ceo-handoff-4a36a0; wave-1 results PR from branch claude/prophet-astra-regime-w1-results-20261004 (number assigned at creation; this record ships inside it)). Successor to the Astra→Fable takeover
  record PROPHET-REGIME-INDICATOR-2026-10-04-ASTRA-CEO.md (PR #8375).
model: fable
ended_because: blocked
mission: >
  Wave 1 of the Chairman's Prophet regime / indicator / timeframe / theme program: run the
  pre-registered lanes A1, B1, C1, C2, D, E, F1 on the pinned checkout 052e02d085b0, review
  every delivered round by artifact, and land the accepted records with their verdicts so
  Mastermind and Prophet can consume true results — one Prophet platform with separately
  evaluated strategies, never a universal regime score.
state_before: >
  PR #8375 landed the Fable-authored masterplan (03), fabric packages (04), acceptance ledger
  (05), lane packets and the results/.gitignore; lanes were running on the MiniMax host mini2.
  During wave 1 both MiniMax hosts were lost (mini2 ssh denied fleet-wide ~05:30Z, mb offline
  mid-transfer 07:11Z) and the Chairman ruled "no more using Opus" (~05:30Z); every remaining
  build and every review moved to grok-4.6 lanes on the seat's own pinned checkout host2.
changed:
  - path: research/prophet_v4/astra_regime_indicator_handoff_20261004/results/A1/
    what: A1 round 1 record (ACCEPTED) — Pine RSI-MACD ≡ engine.canon.rsi_macd (max abs diff ~1e-13, 415/415 crosses matched), 3-session bars ≡ pos//3 on open-date labels, and the served indicator ≠ canon (DSC:CANON-RSI-MACD-IS-NOT-THE-SERVED-INDICATOR).
  - path: research/prophet_v4/astra_regime_indicator_handoff_20261004/results/B1/
    what: B1 round 4 record — events panel 209e2246… (296,637 1D rows) + confirmation pairs d20cd405…; grain_effect_3d / grain_effect_2d / memory_effect_3 all NOT SUPPORTED — pooled Δ(3D.p* − 1D.M3) H10 net +7.0e-05 [−2.9e-04, +4.2e-04]; panel 209e2246… / pairs d20cd405… frozen since round 3 (0 rows changed in round 4); r4 result.json e480d73a….
  - path: research/prophet_v4/astra_regime_indicator_handoff_20261004/results/C1/
    what: C1 round 4 record (seat ACCEPT 07:50Z on grok review; r4 result.json 142de0f2…) — rotation_state_daily.parquet 9361dbf0… frozen since round 2; controls BROKEN (calibrated control FAIL, p95 null lag-21 +0.0498 vs positive control +0.2533).
  - path: research/prophet_v4/astra_regime_indicator_handoff_20261004/results/C2/
    what: C2 round 2 record — verdict INSUFFICIENT SUPPORT (3D and 2D; counterfactual NOT SUPPORTED) under the frozen rule (C1 controls BROKEN ⇒ INSUFFICIENT SUPPORT), descriptive pooled 3D H10 DiD beside it.
  - path: research/prophet_v4/astra_regime_indicator_handoff_20261004/results/D0/
    what: D0 round 3 record — PIT_PARTIAL (honest window 2026-07-05 → host-vintage end; minimum per-date coverage 25.43% = 660/2595 < 50%); lane D parked as a forward study (DEC:D-LANE-PARKED-AS-FORWARD-STUDY).
  - path: research/prophet_v4/astra_regime_indicator_handoff_20261004/results/E/
    what: E round 1 record — SCOPED_NULL (no family×partition meets the winner rule; 10/12 tests above floor; strongest raw p 0.068 = structure×P2_stress, I −0.0069).
  - path: research/prophet_v4/astra_regime_indicator_handoff_20261004/results/F1/
    what: F1 round 4 record — verdict MIXED (purged OOS AUC 0.6227 [0.5715, 0.6738]; deteriorated share 0.1484; immediate-failure share 0.6813; honest-N 1,669 episodes); round 4 closed the production-comparator purge tests, the record checker and the generated §12 with the science keys byte-identical to round 3; embargo 21 NYSE sessions (DEC:F1-EMBARGO-IS-21-NYSE-SESSIONS).
  - path: research/prophet_v4/astra_regime_indicator_handoff_20261004/05_ACCEPTANCE_AND_CONTINUATION.md
    what: §1 gates graded, §3 lane matrix at wave-1 close, ledger folded in, §7 next action rewritten.
  - path: research/prophet_v4/astra_regime_indicator_handoff_20261004/06_PHASE22_CONTINUITY_NOTE.md
    what: Phase-22 conditioner continuity note (same-cut confirmed 2D StochRSI turn).
  - path: research/prophet_v4/astra_regime_indicator_handoff_20261004/07_PRODUCT_CONDITIONING_TABLE_SPEC.md
    what: Product conditioning-table spec consumed by the §7 implication map.
  - path: research/prophet_v4/astra_regime_indicator_handoff_20261004/08_HOST_FAULT_REPORT_2026-10-04.md
    what: Host-fault report — mini2 loss, mb loss, host2/grok fallback, D0 r3 rerun rule.
  - path: agentos/decisions/DEC-B1-MEMORY-FACTOR-DIRECTION.md
    what: B1 memory-factor direction ruling.
  - path: agentos/decisions/DEC-C1-AR1-GATE-UNCALIBRATED-SERIES-FAILS-CALIBRATED.md
    what: C1 AR(1) gate — an uncalibrated series fails the calibrated control.
  - path: agentos/decisions/DEC-D-LANE-PARKED-AS-FORWARD-STUDY.md
    what: Lane D parked as a forward study.
  - path: agentos/decisions/DEC-F1-EMBARGO-IS-21-NYSE-SESSIONS.md
    what: F1 purge/embargo fixed at 21 NYSE sessions.
  - path: agentos/discoveries/DSC-CANON-RSI-MACD-IS-NOT-THE-SERVED-INDICATOR.md
    what: engine/canon.py rsi_macd is not the indicator the product serves.
verified:
  - claim: Every accepted record's inputs are pinned at 052e02d085b0 and its hashes.txt verifies on the pinned checkout.
    command: "cd <host2> && for L in A1 B1 C1 C2 D0 E F1; do shasum -a 256 -c research/prophet_v4/astra_regime_indicator_handoff_20261004/results/$L/hashes.txt | grep -vc ': OK$'; done"
    result: "from the repo root of the seat worktree (origin/main 9201f160 vintage data): A1 0 non-OK of 2,861; B1 1 of 22 (data/yahoo/SPY.parquet — input vintage, the seat tree is newer than host2's 052e02d085b0); C1 14 of 23 (all data/yahoo/*.parquet inputs — same vintage reason); E 1 of 13 (results/B1/RESULT.md — the stated E→B1 round-3 pin, never rebuilt); F1 1 of 10 (data/prophet/ledger.jsonl — vintage). Zero mismatches on any lane's OWN outputs; B1's two panel parquets verify but are not committed (49 MB + 7.8 MB; reproduced from pinned inputs and named by sha256 in the record)"
  - claim: C1 round 4 changed no number — parquets byte-identical to rounds 2/3.
    command: shasum -a 256 results/C1/rotation_state_daily.parquet results/C1/rotation_cuts_daily.parquet
    result: 9361dbf08018f0c2… / 484492539ae42cb3…
  - claim: E round 1 consumed the B1 round-3 panel at load and at write-out.
    command: python3 -c "import json;r=json.load(open('results/E/result.json'))['inputs'];print(r['panel_sha256_load']==r['panel_sha256_write']==r['panel_sha256'])"
    result: True (209e2246…)
  - claim: "Every delivered round was reviewed by an independent grok-4.6 lane on host2 and ruled by the seat from the review artifact: C1 r4 ACCEPT (07:44Z); E r1 ACCEPT (07:54Z); B1 r4 REQUEST_REPAIR on two record defects (08:20Z) → seat-executed round 5 → ACCEPTED; F1 r4 ACCEPT (08:29Z); C2 r2 and D0 r3 DELIVERED on host2 (08:44Z / 09:14Z; result.json sha256 be4e04d4… / b16f444a… observed by seat watchers) but NOT REVIEWED and NOT SHIPPED here — the host volume became unreadable at 08:24Z before either record was copied; both ship with their reviews in a follow-up PR"
    command: grep -A3 "^## RESULT" $S/review/{C1_r4,E_r1,B1_r4,F1_r4,C2_r2,D0_r3}/REVIEW.md (seat scratchpad; reviews are not shipped — their rulings are restated in 09_WAVE1_SYNTHESIS_AND_PRODUCT_IMPLICATION.md)
    result: ACCEPT ×4 as delivered (C1 r4, E r1, F1 r4, and B1 after the seat's round-5 record repair); C2 r2 and D0 r3 DELIVERED on host2 (08:44Z / 09:14Z; result.json sha256 be4e04d4… / b16f444a… observed by seat watchers) but NOT REVIEWED and NOT SHIPPED here — the host volume became unreadable at 08:24Z before either record was copied; both ship with their reviews in a follow-up PR
  - claim: agentos records validate.
    command: python3 scripts/agentos.py validate
    result: exit  at commit time (python3 scripts/agentos.py validate)
unverified:
  - claim: D0 round 3's mini2 artifacts (rs_20261004T051657Z_81412, lease b6face03ca9a) reproduce the host2 record.
    what_would_verify: a mini2 ssh session pulling results/D0/ from that run and a leaf diff against the host2 record (cross-host check only; host2 is the record).
  - claim: The SCOPED_NULL in E closes only the construction tested (one feature per family, whole-sample terciles, binary P1/P2 partitions, month-cluster bootstrap, Holm over 12).
    what_would_verify: a wave-2 pre-registration on a different construction (e.g. within-era terciles, continuous partitions) — not a re-run of E.
unresolved:
  - "C2 r2 and D0 r3: delivered, unreviewed, unshipped — blocked on the host2 volume (`/Volumes/Mastermind`, every directory read hangs or returns EINTR since 2026-10-04 08:24Z; device enumerates, df answers from cache). Operator-owned recovery (physical re-seat / power-cycle); the seat never remounts a shared fleet volume. On readability: copy results/C2 and results/D0 off host2, verify the two shas, launch one grok-4.6 review each, then open the follow-up PR."
  - "B1 round 5 was seat-executed (record-only; L8 note + B1_RETURN.md) while host2 was unreadable; its full 34-test suite re-run on host2 is still owed (seat copy: 29 passed, 2 env-failed on missing basket data, 3 env-skipped). E's hashes.txt pins B1 round-3 RESULT.md (fe0460d8…), which rounds 4–5 rewrote; E is never rebuilt for it."
  - E's hashes.txt pins B1 round 3's RESULT.md; B1 round 4 (record-only) rewrote that file, so that one line no longer verifies against the shipped B1 record while both parquets do. Documented in 05 §3; E is not rebuilt for it.
next_actions:
  - "W3 owner handoff (05 §7): deliver the wave-1 evidence to the V4 owners on #6805 as EVIDENCE with the rung stated honestly (≤ MERGED, never PRODUCTION_PROOF or ACCEPTANCE); W2 is a new pre-registration (different E construction; B1/C1 are closed as delivered), never a re-run"
  - Keep lane D as a forward study; its next evaluation date is in DEC:D-LANE-PARKED-AS-FORWARD-STUDY.
  - Any new conditioning claim for Prophet enters through 07_PRODUCT_CONDITIONING_TABLE_SPEC.md, display-tier first (gauntlet is a promotion gate, never a build gate).
do_not_redo:
  - Never re-run or re-pre-register A1/B1/C1/C2/E/F1 as delivered; a repair round only ever changed tests/record/provenance after the numbers froze (B1 r3 panel, C1 r2 parquet, F1 r3 hazards, C2 rule inputs).
  - Never substitute mini2's D0 r3 artifacts for the host2 record; never retry the blocked ChatGPT chapter-03 upload.
  - "Pickup ACK/START on carrier #8363 was posted once (comment 5975009284); wave RESULT not yet posted at the time of this record — it is posted ONCE after the results PR merges."
  - No Opus/Sonnet/Haiku subagents anywhere in this program (Chairman 10-04); grok-4.6 external lanes and the Fable main loop only.
danger_areas:
  - results/<LANE>/ directories are untracked on the seat worktree via .git/info/exclude lines; they must be un-excluded only for the results PR and never carry parquet, DONE sentinels or caches.
  - host2 (/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/astra-host2-052e02d-690b56cac98b57f7) is DETACHED at 052e02d085b0 and shared by build and review lanes — never checkout/pull/commit there; only one producer per results/<LANE>/ at a time.
  - The grok pool is fleet-shared with max_active 2; a third lane is refused, so builds and reviews must be slot-managed (out_g/max), never launched blind.
---

# Wave 1 — Prophet regime / timeframe research (Fable seat, 2026-10-04)

See `05_ACCEPTANCE_AND_CONTINUATION.md` for the graded gates, the lane matrix at wave-1 close
and the §7 next action. This record is the cold-stranger resumption point: every verified claim
above names its command; every unresolved item names its owner.
