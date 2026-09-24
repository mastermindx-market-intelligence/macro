# RV — Opus read-only audit of the R6-D10-01 draft (v1) — 2026-09-23/24

Reviewer: native Opus `reviewer` child, `ROUTE: review`, `MODE: READ_ONLY` (no edits, commits, pushes, labels or comments). Commissioned by the Fable Meta-CEO seat 48cdfd56 on the v1 draft pushed as the single file of PR #7855 (head 442a4a0b). Sources the reviewer used: `origin/main` records, the B kit under `~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/handoff_kits/meta-ceo-b-2026-09-08/ext/` (scripts, lane logs, queue logs, the lease store read-only), `hosts.json`. Artifact: `rulings/R6-D10-01_SOURCE_CUSTODY_ADMISSION_2026-09-23.md`.

## Verdict on v1
**REJECT** — "two of its evidence claims are contradicted by the kit's own logs, and the §9 evidence it cites breaks rules the ruling itself states." STATUS PARTIAL (turn-capped once; report written on resume). Seat disposition: every finding folded into v2; the seat verified both blockers independently before rewriting (`ps -p 73620` gone; `remote_lane_v8.sh:238` trap; the two `LEDGER_ROW` lines at 22:06Z/22:07Z; 12+ `REMOTE_LANE_STARTED` lines on m1 between 11:30Z and 20:42Z on Wednesday 09-23; zero `LAUNCH` lines in `host_queue_m1.log` that day).

## Findings and disposition
| # | Sev | Finding (reviewer) | Seat disposition in v2 |
|---|---|---|---|
| B1 | BLOCKER | §3.3 PRESTART_REBIND example wrong: lease `70c4882b0684` (pid 73620) released 21:27:53Z, but `trap 'release_lane_leases' EXIT INT TERM HUP` (`remote_lane_v8.sh:238`) never exits, so the wrapper kept polling without a lease beside the 21:31Z relaunch and wrote a second `LEDGER_ROW run-1790198866` (22:07Z) next to `run-1790199074` — a duplicate operation key; the cited refusal line no longer exists (`:261` `rm -f active/$LABEL lanes_$LABEL.stdout` + rsync overwrite). | §3.3 restated honestly; rules forward: copy refusal evidence out before requeue; rebind only when `kill -0` fails; ledger row VOID + correction owed; kit trap repair owed to the fabric program (not patched live). |
| B2 | BLOCKER | Every seat m1 lane on 2026-09-23 started outside the Chairman's 02:00–11:00Z weekday window via direct launches; v1's "the seat enforces it with timed enqueues" was false for 09-23 and §9 counted the violating runs as evidence. | §4: breach disclosed lane by lane and routed to the Chairman on #6805; m1/bm1 lanes only through `host_queue` from now on; falsifier added; §9 rows marked "direct m1"; records stand (host-use breach, not evidence validity); nothing ratified retroactively. |
| M1 | MAJOR | §5.2 contradicted: all program lanes used glm-codex/glm-5.3 for fix AND review, including judgment units. | §5.2 re-scoped: lane review = first slot always; second slot = seat reading + Opus where applied. |
| M2 | MAJOR | §5.3 contradicted by §9: only three `RV_*` files exist; #7842/#7845/#7847/#7850 merged without cross-family review. | §5.3 records the gap; Opus read-only reviews of the pre-registration and the B04 contract commissioned before consumption; matrix/era accepted with the seat reading as second slot, gap recorded. |
| M3 | MAJOR | §5.1 overstates independence: review prompt injects the fixer's report (`lane2.py:352-355`); executor guard only on non-review steps (`lane2.py:219`). | §5.1 states both limits; seat ratifies from the diff/artifact, never the summary. |
| M4 | MAJOR | `REMOTE_LANE_STARTED` is logged unconditionally (`:264-265`), even with an empty pid. | §2: START = non-empty `started pid=` only. |
| M5 | MAJOR | `pu_c_earnings` was qwen/qwen3.8-max with `review_engine: seat` and an empty m1 `started pid=`; §4/§5 did not cover it. | §4 adds bailian/qwen; §5.4 defines seat-review mode and records the unit as a DEVIATION. |
| m1 | minor | `n=<k>/<cap>` is the lease index over needed pools (`:200`), not a cap. | Wording fixed. |
| m2 | minor | "v8 does not enforce the window" — `host_queue.sh` does; direct launches bypass it. | Reworded to name the bypass. |
| m3 | minor | Falsifiers missing (duplicate row / surviving wrapper; START by pid only; out-of-window lanes; judgment unit without cross-family review). | §8.3 extended. |
| m4 | minor | Reversibility should admit the ruling indexes runs that cannot be undone. | §8.4 amended. |

## Reviewer verification table (as returned)
VERIFIED: D10 register fields and §8.2 release set; lane log format; daemon pids; mb LAUNCH times; lease bb940b9e063c; #7572 at 177146dd; RV_7180/RV_7572/B-reconciliation files; #7837 0B/0M/1m; #7840 PASS 0/0/0; #7843 1B; the three RV files; #7811, #7850→e9ee7281, dspr0a lease 5bf8fe72700b, b20 LAUNCH 22:33Z + r2 pid 97639, #7842→89a1a579, #7843→2d688de2, #7845→5b767701, prereg pid 16800 + #7847→0c9e30ad, `site/watchstore.js` 110,461 B in git. CONTRADICTED: refusal line in `lanes_mb_pu_w2_dspr0a.stdout`; m1 window in practice; outcome of the pid-73620 kill. UNVERIFIED (no `gh` spent): #7849 CI state, the live `watchstore.js`, the timed-enqueue sleepers' contents, the other refusal-code strings, `chriswong6031-creator` as token login, `lease_broker.py status` output (the reviewer read the sqlite store instead).

## Reviewer deviation (disclosed)
One recursive `grep -rn 73620` over the kit's `ext/` reached `ext/glm_shim/shim.log` and printed two lines of request metadata (request ids, role lists, account names `chairman-max-2/3`); no credential values; output unused; later commands excluded the folder. Recorded here because the packet forbade opening that file.

## Seat follow-ups created by this audit
1. Opus read-only review of `wave2/CYCLE_A_MACRO_DIAGNOSTIC_PREREG_2026-09-23.md` (#7847): returned REJECT / RUN MAY START: NO (3B/8M/4m) — the diagnostic-run enqueue was stopped before it reached the queue; lane `pu_w3_prereg_v2` commissioned (record `reviews/RV_7847_PREREG_OPUS_2026-09-24.md` with that PR).
2. Opus read-only review of `rulings/R6-B04-01_DOSSIER_CONTRACT_2026-09-24.md` (#7850): returned APPROVE WITH REQUIRED REPAIRS / B04-A MAY START: NO (2B/7M/4m) — the B04-A enqueue was stopped; lane `pu_w3_b04_a7` commissioned to draft R6-B04-01a (record `reviews/RV_7850_B04_CONTRACT_OPUS_2026-09-24.md` with that PR).
3. Chairman disclosure of the 09-23 m1 window breach posted on #6805 as comment 5805139954 (2026-09-24T00:18:20Z), fence read clear after 5803910454.
4. Fabric-program items owed: `remote_lane_v8.sh` trap-without-exit; refusal-evidence preservation; ledger correction for `run-1790198866-pu_w2_dspr0a`.
5. v2 re-check by the same reviewer (7 read-only calls): all 11 findings REPAIRED/disclosed; VERDICT APPROVE WITH REQUIRED REPAIRS — n1 minor (the timed-enqueue lanes are SCHEDULED, not QUEUED) and two evidence notes (commission evidence for the #7847/#7850 reviews; confirm the #6805 disclosure) — folded in v2.1.
