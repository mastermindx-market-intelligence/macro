# Prophet news-to-business-impact — continuation handoff (2026-10-11)

Program file for `WS:PROPHET-NEWS-IMPACT`. Written as the work happens so a cold
successor loses at most one cycle. Masterplan:
`research/prophet_v4/news_to_business_impact_20261006/package/MASTERPLAN.md`
(sha256 prefix `90411a99cfaa88d9`, 309 lines; §3 fact packet, §4 channels, §5 clusters,
§11 benchmark thresholds, §12 phases, §13 scope limit, §14 holds).

## 0. Identity and custody

- Seat: Fable Meta-CEO, Chairman assignment 2026-10-10/11 ("take over this Prophet
  project … deliver autonomously end to end … ultracode with native subagents mixed with
  the subagent fabric").
- Branch `claude/prophet-project-takeover-7fd52d` (pushed), base `origin/main` at
  `cd06b9ae010c` on 2026-10-11; first commit `9f40dc978021` = cherry-pick -x of Sol's
  masterplan packet (#8533 head `cde0219b1040`, 8 files).
- #8533 stays OPEN/DRAFT until the Phase 0 PR merges, then closes with one comment
  naming the superseding PR. Never merge, rebase or push to #8533.
- Not ours: #8697 (Sol, tiingo news quality, DRAFT/HOLD), #8698, #6514 (K3-D,
  HOLD-FOR-SOL — commission C never repairs or merges it).

## 1. DECIDED

- D1. Orchestration hierarchy: Fable seat (judgment, freezes, carrier acts) → one
  native Opus `orchestrator` per wave (`ROUTE: orchestration`, `WHY OPUS`, fable-mode
  load line, fabric-only training block) → read-only or build fabric lanes launched
  through the kit launcher `ext/sub.sh` on LOCAL m2 pools (glm-5.3-flash for census,
  glm-5.3 for architecture-sensitive design and attack reviews) → orchestrator-written
  synthesis → seat adjudication. Native `reviewer` (opus, MODE: READ_ONLY) only for the
  final adversarial pass before a freeze.
- D2. Critical path: commission A (three event templates + acceptance labels + closed
  schemas, seat freeze) → wave 1 (benchmark sampler + validator with hostile fixtures)
  → wave 2 (commission D, 600 graded cases) → wave 3 (Phase 1 measured packet producer,
  `context_only`, behind the benchmark gate). Commissions B and C are research lanes
  that run beside wave 1; neither gates the freeze.
- D3. New code only in the LEAF namespace `engine/news_impact/` +
  `contracts/news_impact/`, consuming existing owners (`engine/news_events.py`
  `classify_event`, `engine/news_event_ledger.py`, `engine/company_intelligence/
  {events,documents,resolution,economic_observations,contracts}.py`). No edits to
  those owners in Phase 0 or wave 1.
- D4. Frozen assumptions for every template (masterplan §3 + E0 contracts): issuer id
  `cik:` + 10 digits; every critical numeric field binds a `source_span.v1`
  (receipt_state ∈ byte_replayed | address_only | typed_absence); authority
  `context_only`; quantity = value + unit/currency + basis {total, incremental,
  run_rate, per_share, percent} + period + negation; typed absence {not_stated,
  stated_without_number, range_only, redacted_rights, parse_failed}; no model
  confidence, price target, fair value or score (DNR:KILL-LLM-CONFIDENCE,
  DNR:KILL-CAUSAL-DAG-ALPHA); bounded free text (maxLength); `additionalProperties:
  false` everywhere.

## 2. FACTS (verified this program)

- F1. `origin/main` carried nothing of this program on 2026-10-11 (grep of
  `news_impact`, `news_to_business_impact` across engine/, contracts/, research/,
  agentos/ on the fetched ref); no open PR other than #8533 touched the namespace.
- F2. The `Workflow` tool is platform-blocked in the seat session: two launches failed
  with "PreToolUse hook did not respond before its timeout (host client may be
  unreachable)". A direct `Agent` spawn of an Opus `orchestrator` launched on the first
  attempt. Do not try `Workflow` a third time in this session.
- F3. Fabric admission through the `mastermind-executive` connector is unauthenticated
  in the seat session; labor runs through the kit launcher (`ext/sub.sh`) instead.
  Pools on 2026-10-11: glm (claude -p harness, local m2; 5h window 840/28000),
  minimax 7/7 free, grok/cursor caps 11, mini2 at its 49.9 GB floor (no glm-codex),
  m2 358.9 GB free, ubuntu2 held, never m1, never mb.
- F4. Lane worktrees are sparse and blobless; the masterplan exists only on the seat
  branch, so lanes read it from the seat scratchpad copy and read tape
  (`data/qbus/items.parquet` 9.77 MB, `data/news/`) from the seat worktree's checked-out
  `data/` by absolute path.

## 3. OPEN

- O1. Commission A freeze — awaiting ORCH-W1's synthesis (nine lane artifacts + one
  recommendation). The seat adjudicates by artifact, not by the orchestrator's report.
- O2. Whether `SourceDocument`/`verify_span` admit non-filing news URLs as-is or need a
  LEAF adapter (C2 lane answers with executed probes).
- O3. (answered) `.github/workflows/ci.yml` triggers on every path; the selector,
  not the event filter, owns cost. The Phase 0 PR will carry pack checks and merges
  only on concluded green; `--admin` does not apply.

## 4. NEXT

- N1. Judge ORCH-W1 by artifact (`$S/census/C{1,2,3}_*.md`, `$S/design/D{1,2,3}_*`,
  `$S/design/SYNTHESIS_RECOMMENDATION.md`, kit record
  `orch/fabric/reviews/PROPHET_NI_W1_r1.md`); re-run the `additionalProperties` walk
  and the forbidden-name grep (confidence|score|target|fair_value) in the seat.
- N2. Write `PHASE0_FREEZE_2026-10-11.md` and `contracts/news_impact/*.schema.json`;
  one native opus `reviewer` attack pass; commit; `git fetch origin`; open the Phase 0
  PR; carry it to merged on concluded checks; verify against freshly fetched
  `origin/main`; close #8533 as superseded.
- N3. Wave 1 orchestrator: L3 sampler + L4 validator + hostile fixtures under the
  frozen schemas; B/C research lanes beside it.

## 5. Lane matrix

| lane | role | tier/pool | cwd | sentinel | budget | state |
|---|---|---|---|---|---|---|
| ORCH-W1 | native Opus orchestrator, Phase 0 judge panel | opus (native `orchestrator`) | seat scratchpad `$S` | task notification | one wave | RUNNING (spawned 2026-10-11) |
| C1_tape / C2_contracts / C3_owners | read-only census | glm-5.3-flash, local glm pool | shared RO worktree `prophet-ni-w1-ro` | `<LANE>: <VERDICT> <sha>` in `$S/out/<lane>.out` | ≤40 min each | owned by ORCH-W1 |
| D1_fact_integrity / D2_labeler_first / D3_consumer_first | design candidates (commission A) | glm-5.3, local glm pool | same RO worktree | same | ≤60 min each | owned by ORCH-W1 |
| R1 / R2 / R3 | attack reviews, different lane than author | glm-5.3 | same RO worktree | same | ≤45 min each | owned by ORCH-W1 |

`$S` = the seat session scratchpad (not in the repository); the durable copies of the
accepted artifacts land under `research/prophet_v4/news_to_business_impact_20261006/`
in the Phase 0 PR.

## 6. Ladder rung reached

Phase 0: RUNNING (orchestrator live; no artifact DELIVERED yet). Nothing MERGED.
