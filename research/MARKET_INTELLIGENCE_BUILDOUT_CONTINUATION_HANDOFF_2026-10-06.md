# Market-Intelligence Institutional Buildout — continuation handoff (2026-10-06)

**Program file for `WS:MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT`.** Written by the Fable
Meta-CEO seat (session `fd47d431`) at the wave-3 boundary. A cold stranger resuming from this
file should lose at most one cycle. Verify every PR state against GitHub and every artifact
against `origin/main` before acting; nothing here is a substitute for the carrier.

## 0. Identity and mandate

- **Carrier:** Mastermind PR #1258 (head `d1a8e672464d9a90dfe5b3608e071f8a730f3c95`, OPEN /
  DRAFT, base `master`, protected base `7eac3ec2…`) = owner-preserving integration overlay of
  umbrella Mastermind #1202 (op `market-intelligence-institutional-buildout-20261004`, plan PR
  #1203). Package text: `research/product_intelligence_local_delivery_20261005/03_WORK_PACKAGES.md`
  at `d1a8e672` in the Mastermind repo.
- **Chairman directive (2026-10-05, verbatim-critical):** act as Meta-CEO; finish end to end;
  save limitations/blockers for the Chairman LAST; no stalling, loops, or bureaucratic dwelling;
  continuity, anti-drift, anti-token-burn; **no Claude-native subagents**; use the subagent
  fabric (multi-level frontier sub-orchestrators allowed); tier order GLM Flash 5.3 → GLM 5.3 →
  Grok/Cursor → Opus 5.5 last resort only. Post-compaction: "Contiue working on the program.
  you're responsible to get it finished end to end".
- **ACK exists once** on #1202 (comment 6009097528, 04:05Z). Never re-ACK, never re-START.
- **Packages:** P (program), N (ticker/news change view), E (expectations/evidence dossier),
  F (fundamental forensics, C19-gated), R (Research Vault, other owner), L (leadership/theme
  context), V (verdict preservation), I (integrated answer), S (intraday strength).
  Phases: A reconcile → B parallel fronts N/E/R/L (+C19 F) → C integrated answer → D
  production/prospective evidence.
- **Binding packet constraints (do not relitigate):** C19 sticky (recovery op
  `c19-program-recovery-20261004-01a108b6`, native parent `01a108b6-7f12-76a2-9123-2b49492f654c`,
  original request `req-4a8daf76317cfe92f436991444c58281`): never a fresh key, invented intent
  id, equivalent new root, carrier switch, or transfer to the new umbrella principal before
  original-target reconciliation. #1251's additive old-catalog compatibility repair is published
  at `1cfdf816924d2c2ab58110c9ec0a5d57b1758bb4` — do not duplicate. Respect active GMI children
  (#8324) and denied source lanes (Catalyst #6712, #8468). No all-account installation, provider
  enrollment, data purchase, production migration, source activation, portfolio behavior or
  live-capital change is authorized by the packet.

## 1. Wave plan and exit gates

| wave | content | exit gate | state (10-06 06:5xZ) |
|---|---|---|---|
| W1 | read-only censuses N0 / L0 / E0 (new macro branches, owned dir `research/product_intelligence_local_delivery/`) | three PRs MERGED + needle-verified on `origin/main` | L0 #8500 MERGED `2daaf9f1dc8f` (verified); N0 #8501, E0 #8502 READY · armed, sweeper owns |
| W2 | N1 Terminal news server child; E1 K3E qualification tests (stacked on #8337); V0 verdict-preservation census | N1: one owner; E1: accepted + RESULT to the E owner; V0: MERGED | N1 #832 CLOSED superseded by Terminal #831; E1 #8506 ACCEPTED, DRAFT HOLD-linked; V0 #8508 MERGED `0beebb3bd1f2` (verified) |
| W3 | I0 integrated-answer gate census; S0 intraday-estate census; L2 independent review of #8470's reader | PRs MERGED; L2 summary on #8470 | #8512, #8511, #8513 READY · armed; L2 summary posted (#8470 comment 6010401522) |
| W4 | records PR (this file + agentos WS/DEC/DSC/handoff); L3 display-spec freeze in the seat; one L3 build lane | records MERGED; L3 PR MERGED + live | records PR in flight; L3 freeze not started |
| W5 | I composition (owner-gated), S1 registration (owner-gated), F2 (C19-gated), R (other owner) | each gate opened by its owner | all gated — see §6 |

## 2. Lane matrix (every lane = cursor composer-2.5 via the B-kit `remote_lane_v8.sh`)

Recorded deviation on every packet: GLM tier fleet-unavailable (mini2 storage guard
`min_free_gb 50`, 49.56 GiB free; m1 `QUARANTINED_FROM_LANES`; kit refuses grok remotely;
local m2studio slots 2/2 held by other sessions).

| lane | host / branch | PR · head | verdict · seat acts |
|---|---|---|---|
| mi_l0_leadership_context_r1 | ubuntu1 / `claude/mi-l0-leadership-theme-context-20261006` | macro #8500 `5f76a128` → MERGED `2daaf9f1dc8f` 04:21Z | ACCEPT 6009218822; needle `RETAINED_LEDGER_UNMARKED` md=1, `1537636f` json=8 on origin/main |
| mi_n0_news_matrix_r1 | ubuntu1 / `claude/mi-n0-ticker-news-task-matrix-20261006` | macro #8501 `5657d3a3` → `03c37e142176` (sweeper update-branch) | ACCEPT 6009289761; armed; sweeper owns |
| mi_e0_exp_accept_r1 | ubuntu1 / `claude/mi-e0-expectations-acceptance-path-20261006` | macro #8502 `675ddd026c80` | ACCEPT 6009292494; armed; sweeper owns |
| mi_n1_terminal_news_server_r1 | ubuntu1 / Terminal `claude/mi-n1-ticker-news-server-20261006` | Terminal #832 `7d4fbf8c` | complete per spec (25 tests T01–T20) but COLLIDED with Astra's #831 → CLOSED SUPERSEDED (O.16); FYI on #831 6009862596; RESULT on #8454 6009862813; branch kept as cherry-pick reference |
| mi_e1_k3e_qualification_r1 | ubuntu2 / `claude/mi-e1-k3e-qualification-tests-20261006` (base = #8337 branch `claude/ssd-information-to-price-exp1-20261003-b4cff810e30514df` @ `13910854`) | macro #8506 `224a3fa85cd7` DRAFT | ACCEPTED (2 new test files, 19 tests: 10 pass + 9 strict xfail `GAP-E-{ALIAS,FAMILY-SEAM,CLOCK,RIGHTS,BASIS}`); HOLD-linked to #8337/#8312; RESULT on issue #8309 6009863135 (owner seat `2fc05761`, MAS-271). Never ready/label/merge from this seat |
| mi_v0_verdict_preservation_r1 | ubuntu2 / `claude/mi-v0-verdict-preservation-census-20261006` | macro #8508 `7815cebf` → MERGED `0beebb3bd1f2` 05:28Z | ACCEPT 6009861729; needle `DOCUMENT_ONLY` json=17, md=1 on origin/main |
| mi_i0_integrated_gate_census_r1 | ubuntu1 / `claude/mi-i0-integrated-answer-gate-census-20261006` | macro #8512 `779a99616893` | ACCEPTED (deps 7, workflows 6, tests 12 = 9 covered / 3 gap, freeze list 10; gate CLOSED: H01 ACCEPTED, H04/H06 BUILT_NOT_ACCEPTED, H05 ABSENT); armed |
| mi_s0_intraday_estate_census_r1 | ubuntu2 / `claude/mi-s0-intraday-estate-census-20261006` | macro #8511 `66652d0433dc` | ACCEPTED (estate 13, sessions 6, 6 strength modules all daily = not a rename, Trend Persistence DISTINCT under C1-NULL, gap CONFIRMED_GAP, 10 registration pins); armed |
| mi_l2_rotation_reader_review_r1 | GLM refused on mini2 05:40Z → ubuntu1 cursor 05:48Z / `claude/mi-l2-rotation-reader-review-20261006` | macro #8513 `07a0d426` → `62160a17cea0` (seat citation fixes via contents API: md `fb5d8269`, json `62160a17`) | ACCEPT_WITH_FOLLOWUPS: 12 probes executed, `18 passed, 23 deselected` on #8470 @ `1537636f`, 4 findings (2 MAJOR, 1 MINOR, 1 NOTE); ACCEPT 6010400652; armed LAST; review summary on #8470 = 6010401522 (seat-only, no approve/merge) |
| records (seat work) | session worktree / `claude/mi-records-wave3-20261006` (base `89f520972733`) | this PR | WS + DEC + DSC + handoff + this file |

## 3. DECIDED

- Wave 1 = three read-only census lanes in an owned directory with no collision on main;
  new-packet mode (`pr: null`, `task_class: execute`, `escalation_reason`), worker opens the
  DRAFT PR itself, `review_engine: seat`.
- All returns are judged by artifact: the seat re-shows every `path:line` claim on the pinned
  head before ACCEPT; a research PR is READY → one ACCEPT comment → `merge-on-green` armed
  LAST; no pushes into an armed PR.
- **Package N owner = Terminal #831** (`DEC:MI-BUILDOUT-N-PACKAGE-OWNER-IS-TERMINAL-831`).
  #832 closed superseded. No N2 from this seat; the Terminal news UI is Astra's.
- **E1 returns to the E owner** (issue #8309 seat `2fc05761`) as a RESULT, never as a
  ready/merge act; #8506 inherits #8337's and #8312's holds.
- **L2 citation drift (7 citations, 1–5 lines) was corrected by the seat on-branch** under L.7
  (bounded principal work, no worker started, seat held custody) rather than a repair round —
  substance was verified against #8470's bytes first.
- Kit `host_queue.sh` is inert on Linux (`DSC:KIT-HOST-QUEUE-GATE-IS-MACOS-ONLY`); Linux lanes
  launch directly via `remote_lane_v8.sh <host> <label>`.
- Workstream `program:` = `sector-rotation-intelligence` (nearest registered program key in
  `config/mastermind_programs.yml`; the buildout has no key of its own).

## 4. FACTS (verified this program; re-verify before relying on a moving one)

- Macro carriers: #8454 head `66ff33ac` (DRAFT / DO NOT MERGE; "Do not arm merge-on-green or
  auto-merge during implementation"); #8312 `69d8c407` Sol CONTINUE 5988970684; #8337
  `13910854` held on #8312; #8463 `014ffa83` HELD; #8470 `1537636f` green, independent-review
  condition now has L2 evidence; #8417 HOLD-RELEASED 10-06 still unmerged → #8486 → #8455.
- Terminal: census pin `e17622b1`, master 10-06 `1e31c8cc` (1-commit drift, test file only);
  incumbent CTE route `terminal/app/api/company-theme-context/[symbol]/route.ts` (nodejs /
  force-dynamic :14-15, Supabase getUser + E2E bypass :23-34, rate limit :45, `no-store` :17);
  Terminal #796 DRAFT `0dfb1d8f` (CTE card) — collision check before any L3 Terminal attach;
  Terminal #831 `sol/web-ticker-news-r1-20261004-astra-001` DRAFT "DO NOT MERGE yet", head
  `1ea7d2ff`, 22 files, pins Macro #8454 @ `66ff33ac`, dark-only.
- N0 contract: `app/ticker_news.py` routes `/api/ticker-news/stories/{story_id}` :286,
  `/{ticker}/changes` :310, `/{ticker}` :345, `/{ticker}/stream` :445; schema
  `ticker_news.snapshot.v1` :259; `engine/qbus_news_store.py` `NewsReadRights` :93,
  `NewsSnapshot` :137, `ChangePage` :161, `StoryDetail` :169; DO-NOT-CALL collectors
  `collectors/benzinga_news.py`, `collectors/massive_benzinga_news.py`, `scripts/run_qbus_news.py`.
- E0: no accepted Front-E publication on main; capture path
  `collectors/equity_revisions.py:425 accrue_expectation_observations` →
  `data/revisions/expectation_observations.parquet`; `engine/k3e_expectation_surface.py` exists
  only on #8337; lawful E1 seam = new test files under the `intelligence-registry` owner
  (`13910854:.github/ci/legacy-jobs.yml:4641-4680`); normalized baseline null (:389) = refusal,
  not zero; withdrawn/stale semantics UNKNOWN (owner ruling needed).
- L0 / L2: #8470 reader mode inference `engine/rotation_events.py:1419-1423` @ `1537636f`
  (`RECONSTRUCTED_REPLAY` only when `replayed is True`, else `RETAINED_LEDGER_UNMARKED`);
  consumers on main `engine/theme_context.py:589/:891`,
  `engine/company_theme_exposure/views.py:259 build_bundle` (`:32-65 _theme_state_receipt`),
  `engine/theme_graph/rights_use.py:140/:286`, `engine/us_board_rank.py:2208`; L3 attach points
  = CTE bundle receipt + `theme_context` leadership block (`templates/sector_central.html.j2:2110-2196`);
  constraints MLC-R1 consume-not-rebuild, MLC-R2 display-tier, V3.8 Action ≠ Trend Leadership.
  **L2 consumer display statement is binding for L3:** surface the ledger mode
  (`RECONSTRUCTED_REPLAY` vs `RETAINED_LEDGER_UNMARKED`) and the `ts`-after-`through` skew as
  display-tier receipts; never present replay-sourced rows as live observations.
- L2 findings (verbatim): MAJOR n1 "RECONSTRUCTED_REPLAY is inferred only from native
  `replayed is True`; replay-sourced rows without the flag classify as RETAINED_LEDGER_UNMARKED
  with no warning." MAJOR n2 "Write clock `ts` may be after `through` while observation_date is
  within `through`; reader returns OK with no coverage skew signal." MINOR n3 "Duplicate
  lifecycle lines inflate event_counts; coverage has no duplicate lifecycle count." NOTE n4
  "Leg membership as-of observation date is out of scope; consumer must join external
  GMI/cohort surfaces."
- Hosts: ubuntu1 (user longr) node 22 only at `~/lanes/tools/node-v22.12.0-linux-x64/bin`;
  Terminal `node_modules` cache seeded at `~/lanes/nm_cache/terminal/c8bd178646d6ee83`;
  ubuntu2 (user ubuntu2) no `~/lanes/venv`, python 3.12.3 without pandas (packets carry a
  lane-local venv step); only the macro mirror. Both `max_active 2`; pools cursor / go-codex /
  oc-free / grok; NOT glm-codex. Broker pool `cursor` admits ONE lane per host at a time.
- Collision lesson: search OPEN PRs in the target repo by owned path before freezing a spec;
  default-branch absence proves nothing (#832 cost one full lane).

## 5. Lane recipes (B-kit)

```
K=~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/handoff_kits/meta-ceo-b-2026-09-08
# write $K/ext/args_<label>.json (packet IS the prompt; new-packet mode pr:null + escalation_reason)
cd $K/ext && LANE_ORCH_ID=fd47d431-mi-meta-ceo bash remote_lane_v8.sh <ubuntu1|ubuntu2> <label>
# run as a background Bash task (timeout 7200000); the task exit IS the watcher.
# Admission = `LANE_LEASE pool=cursor n=1/1` + `started pid=`; `REMOTE_LANE_STARTED` is not admission; refusal rc=78.
```

Never read, print, or copy credentials (`~/.opencode-go`, `~/.glm`, `~/.minimax`, `~/.bailian`,
`~/.codex/auth*`, `ext/glm_shim/.token`, `ext/go_shim/.token`); never open `ext/glm_shim/shim.log`
or `usage.jsonl`. No `gh` inside shell loops (hook-denied) — one GraphQL query with aliases.
Merge verification = bare `git fetch origin main` then `git grep -c <needle> origin/main -- <path>`;
a deleted head SHA cannot be fetched and a diff against it passes vacuously.

## 6. OPEN — gates by owner (not this seat's to force)

| package | gate | owner | this seat's move |
|---|---|---|---|
| F2 / H02 | C19 original-request reconciliation `req-4a8daf76317cfe92f436991444c58281` | Chairman / Executive | EXACT_HUMAN_GATE — record only |
| I | H04/H06 BUILT_NOT_ACCEPTED, H05 ABSENT (I0) | Alpha Intelligence / event owners | optional read-only composition spec from I0's 10 freeze items; no warehouse, no thesis mutation |
| S | product owner accepts the distinct intraday-strength hypothesis | product owner | S1 registration packet only after acceptance; no outcome scan before registration |
| N | Terminal #831 DRAFT behind Macro #8454 DRAFT | Astra / #8454 owner | none; tracked |
| E | #8337 publication, #8312 release, withdrawn/stale semantics, `intelligence-registry` enrollment | Sol / issue #8309 seat `2fc05761` | none; E1 delivered |
| R | Vault custody + Mac13,1 ceremony | seat `0e657eec` (#8438) | record only |
| L | #8470 release (independent review condition now evidenced) | #8470 owner / Sol | L3 freeze + build may proceed display-tier against main's consumers |
| P | #1258 DRAFT on master merge queue; packet requests no release/auto-merge | Chairman | one checkpoint/RESULT at the wave boundary |

## 7. NEXT (critical path first)

1. Records PR: validate, push, READY, one comment, `merge-on-green` LAST; needle-verify after
   merge (`DEC-MI-BUILDOUT-N-PACKAGE-OWNER-IS-TERMINAL-831` in `agentos/decisions/`).
2. After each sweeper merge of #8501/#8502/#8511/#8512/#8513: bare fetch + needle verify; flip
   the wave rows in the WS record to `done` in the next records touch (not per merge).
3. L3 display-spec freeze in the seat (`docs/DESIGN_DOCTRINE.md` + frontend-design skill;
   dark AND light art directions; EN/ZH) against the attach points in §4; collision check vs
   Terminal #796, Macro #8412/#8470 and the GMI held PRs by owned path across OPEN PRs; then
   ONE cursor build lane (GLM if mini2 is freed).
4. Carrier checkpoint on #1258: merged + armed PRs, gates, blocker list pointer.
5. Deliver the Chairman blocker list LAST (§8).

## 8. Blocker list for the Chairman (deliver LAST, verbatim-safe)

- Executive MCP auth: `linear-server`, `mastermind-executive`, `figma` unauthenticated;
  `mmx-cimd-probe` ECONNREFUSED — fabric admission via connector unavailable to this seat.
- C19 original-request hold `req-4a8daf76…` (F2 / H02) — EXACT_HUMAN_GATE.
- Package I: H04/H05/H06 acceptance by their owners (gate CLOSED per I0).
- Package S: product-owner acceptance of the intraday-strength hypothesis before S1.
- Research Vault: R1 operator gate, R4 Mac13,1 ceremony (seat `0e657eec`).
- Source rights / paid-provider activation (Benzinga / Massive / Polygon intraday) — not
  authorized by the packet.
- Hosts: mb offline; m1 quarantined; mini2 49.56 GiB free < 50 GiB floor → GLM tier blocked
  (the Chairman's preferred tier was unusable for the whole program); kit refuses grok
  remotely; local slots fleet-shared; cursor pool serializes one lane per host.
- Sol holds: #8312, #8337, #8463, #8486/#8455/#8432/#8435; #8470 + #8412 independent review;
  #8454 DRAFT / DO NOT MERGE; Terminal #831 DRAFT / DO NOT MERGE.
- Kit defect: `host_queue.sh` Linux gate (`DSC:KIT-HOST-QUEUE-GATE-IS-MACOS-ONLY`).
- E owner rulings: withdrawn/stale expectation semantics; E1 `intelligence-registry` enrollment.
- Terminal news UI: zero implementation on master; owned by #831.
