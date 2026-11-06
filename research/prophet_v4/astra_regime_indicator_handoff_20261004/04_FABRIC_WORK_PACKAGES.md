# 04 — Fabric work packages (wave 1)

**Operation:** `prophet-astra-ceo-fable-20261004-001` · seat session `f273dd7d-5dfb-4725-b26d-3de277637b11` · plan: `03_RESEARCH_AND_PRODUCT_MASTERPLAN.md` (frozen).
**Routing law applied:** route eligibility and budgets were VERIFIED on 2026-10-04, not inferred from names (`ext/pool_status.py`: grok 0/6 active, cursor 0/3, bailian 0/9; acceptance floors from the ROUTING LAW table: MiniMax DEMOTE 0.00 n=208 → not used; GLM PASS). No ChatGPT-native subagent is spawned at any level. Native Claude children are used only as (a) `orchestrator` suborchestrators (Opus + `fable-mode`, or Fable with a FABLE-WHY) that shepherd external lanes and (b) `reviewer` (Opus, `ROUTE: review` + `ROUTE: AUDIT`, `MODE: READ_ONLY`). Labor runs on external GLM lanes through the B-kit launcher; the seat (Fable) adjudicates and is the only committer.

## 1. Lane matrix

| Lane | Spec | Tier / model | Task class | Host · cwd | Writes only | Inputs | Depends on | Budget |
|---|---|---|---|---|---|---|---|---|
| A1 baseline/clock census | `packets/A1.spec.txt` | leaf-labor · `glm-5.3-flash` | `census` | mini2 · `~/lanes/repos/macro` | `results/A1/` | engine/*, data stores, git log | — | 120 turns, ≤ 2 h |
| C1 rotation state | `packets/C1.spec.txt` | frontier-labor · `glm-5.3` (escalated: PIT-safety invariants) | `mechanical` | mini2 | `results/C1/` | yahoo SPDRs/SPY/RSP, DFII10, regime_v2_pit | — | 120 turns, ≤ 2 h |
| B1 phase/memory panel | `packets/B1.spec.txt` | frontier-labor · `glm-5.3` (escalated: pre-registered inference code, canon identity) | `mechanical` | mini2 | `results/B1/` | baskets/ohlcv, SPY, canon/bar_derive | A1 parity read (advisory) | 120 turns, ≤ 3 h |
| C2 interaction | `packets/C2.spec.txt` | frontier-labor · `glm-5.3` (escalated: paired bootstrap, verdict rule) | `mechanical` | mini2 | `results/C2/` | B1 + C1 outputs on host | B1 ACCEPT, C1 ACCEPT | 120 turns, ≤ 2 h |
| F1 hazard decomposition | `packets/F1.spec.txt` | frontier-labor · `glm-5.3` (escalated: purged OOS, IRLS by hand) | `mechanical` | mini2 | `results/F1/` | retro_grades, prophet ledger, C1 output | C1 DELIVERED (covariates optional) | 120 turns, ≤ 2 h |
| R-<lane> review | §4 template | native `reviewer` (Opus, READ_ONLY) | — | seat host, local worktree | nothing (scratchpad only) | rsync'd `results/<LANE>/` + full local data | lane DELIVERED | 1 return |

mini2 admits two concurrent lanes (`max_active=2`; rc 75 = clean refusal, retry after a 5-minute wait). Sequencing: [A1 ∥ C1] → [B1 ∥ F1] → [C2]. Repairs re-enter the same slot discipline. m1 is degraded (EINTR on git/ls in the lane checkout) and mb has no data; neither hosts a lane this wave.

Packet = `LANE_LAW_RESEARCH.txt` + `<LANE>.spec.txt` (+ a numbered `REPAIR ROUND n` block on rounds ≥ 1), concatenated into the seat scratchpad and transported by the launcher (`remote_sub.sh` scp's the packet; the packet is never argv). The lane checkout on mini2 is `main` at `052e02d085`; the results directory is listed in its `.git/info/exclude` so a no-git lane ends with a clean `git status` and the repository Stop hook allows it (dry-run receipt 2026-10-04: `ship_loop_guard.py` Stop payload on that checkout → rc 0).

## 2. Launch recipe (suborchestrator; verbatim)

```
K=~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/handoff_kits/meta-ceo-b-2026-09-08
W=/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/astra-ceo-handoff-4a36a0
P=$W/research/prophet_v4/astra_regime_indicator_handoff_20261004/packets
S=<scratchpad>/pkts; O=<scratchpad>/out; mkdir -p $S $O
cat $P/LANE_LAW_RESEARCH.txt $P/<LANE>.spec.txt [repair block] > $S/<LANE>_r<n>.txt
POOL_ORCHESTRATOR_ID=prophet-astra-ceo-fable-20261004-001 POOL_PARENT_RUN_ID=<LANE>-r<n> \
POOL_TASK_CLASS=<census|mechanical> [POOL_ESCALATION_REASON='<≥12 chars>'] \
nohup /bin/bash "$K/ext/remote_sub.sh" mini2 glm $S/<LANE>_r<n>.txt '~/lanes/repos/macro' <model> \
  --out $O/<LANE>_r<n>.out > $O/<LANE>_r<n>.launch.log 2>&1 &
echo $! > $O/<LANE>_r<n>.pid
```
Watch (one watcher per lane, ≤ 9 min per call, repeat until found or the lane budget elapses):
```
perl -e 'alarm 540; exec @ARGV' /bin/bash -c 'until grep -qE "^(DONE rc=|<LANE>_RETURN:)" '"$O/<LANE>_r<n>.out $O/<LANE>_r<n>.launch.log"' 2>/dev/null; do sleep 60; done; echo FOUND'
```
Refusal (`rc=75` in the launch log) → wait 5 min (`perl -e 'alarm 300; exec @ARGV' /bin/bash -c 'until false; do sleep 60; done'`) and relaunch the SAME packet with the same `POOL_PARENT_RUN_ID` (a refusal started nothing, so a relaunch is not a duplicate). Any other non-zero rc with no `<LANE>_RETURN:` → classify DEAD and report; never relaunch blindly.
Collect:
```
rsync -az --exclude '__pycache__' mini2:~/lanes/repos/macro/research/prophet_v4/astra_regime_indicator_handoff_20261004/results/<LANE>/ \
  $W/research/prophet_v4/astra_regime_indicator_handoff_20261004/results/<LANE>/
```
Then verify by artifact (RESULT.md, result.json parse, pytest summary line, hashes.txt, the parquet files named in the spec, total size) and return the structured packet. Parquet panels are NOT committed (`results/.gitignore`); their sha256 in `hashes.txt` and `result.json` is.

DO NOT (suborchestrators and lanes): run git write commands on mini2; write under `data/`; install packages; cancel or re-dispatch any GitHub workflow; post to any carrier; arm/ready/merge any PR; read credential files; spawn Sonnet/Haiku/general-purpose children; use MiniMax (DEMOTE 0.00); poll faster than 60 s.

## 3. Repair protocol

A review returns exactly one of ACCEPT · REQUEST_REPAIR (numbered defects + exact re-check each) · REJECT · ESCALATE. REQUEST_REPAIR relaunches the lane with the repair block appended ("REPAIR ROUND n — the previous results in RESULTS_DIR exist; fix the numbered defects, regenerate every affected output, re-run tests, re-emit the packet"). At most two repair rounds per lane; a third identical defect list → ESCALATE to the seat (change tier/owner/split, never a third identical attempt). The seat re-adjudicates every ESCALATE by opening the artifact.

## 4. Review commission template (native Opus `reviewer`)

```
ROUTE: review
ROUTE: AUDIT
MODE: READ_ONLY
WHY OPUS: adversarial statistical review of a pre-registered research artifact (PIT safety, cluster bootstrap validity, grain/memory confound, verdict-rule compliance) — fails the draft-and-review test at lower tiers.
MISSION: refute lane <LANE>'s result packet against its frozen spec.
ARTIFACT TO ATTACK: <local results dir> (RESULT.md, result.json, code/, hashes.txt, parquet outputs); spec = packets/<LANE>.spec.txt; law = packets/LANE_LAW_RESEARCH.txt; plan = 03 §5.x.
REVIEW STANDARD: every NOT DONE UNLESS item verified by opening the artifact (run the tests yourself from the local worktree, which has the full data; re-execute code/run.py into the scratchpad if under 20 min; recompute at least two reported numbers independently); look-ahead/PIT leaks; post-hoc selection; bootstrap clustering; honest-N; verdict rule applied mechanically; survivorship statement present; hashes match files.
SCOPE: this lane only. OUT OF SCOPE: redesigning the experiment, editing repo files, any git write.
NOT DONE UNLESS: a verdict ACCEPT|REQUEST_REPAIR|REJECT|ESCALATE with numbered defects (each with the exact re-check), the two independently recomputed numbers with their values, and the list of NOT DONE UNLESS items with PASS/FAIL.
EVIDENCE REQUIRED: commands run and their output lines; file paths; line numbers for code defects.
RETURN: STATUS / RESULT / EVIDENCE / GAPS / DEVIATIONS.
```

## 5. Suborchestrator commissions (Workflow stages)

- `SO-A` (Opus + `fable-mode`): shepherd A1 and C1 in parallel → return per-lane packets. `ROUTE: orchestration`; MISSION/WHY/SCOPE/OUT OF SCOPE/NOT DONE UNLESS/RETURN inline; schema-validated return.
- `SO-BC` (Fable, `FABLE-WHY: orchestration: multi-round statistical repair adjudication on the program's critical path (B1 → C2), where a wrong accept propagates into the decisive C2 verdict and cannot be undone by a later review` — script-level line in the Workflow): shepherd B1, then C2 after B1 and C1 ACCEPT.
- `SO-F` (Opus + `fable-mode`): shepherd F1 after C1 DELIVERED.
- Reviews: one `reviewer` stage per DELIVERED lane (template §4); repair ≤ 2 rounds (§3).
- Synthesis (C2 verdict, §7 implication, Agent OS records, ship chain) stays in the seat's main loop.

The Workflow script is persisted by the harness under the session directory at launch and its path is recorded in `05_ACCEPTANCE_AND_CONTINUATION.md`.
