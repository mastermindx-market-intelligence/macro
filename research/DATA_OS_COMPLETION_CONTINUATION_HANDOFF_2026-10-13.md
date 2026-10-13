# Data OS completion — continuation handoff (2026-10-13)

Programme home: `WS:DATA-OS-COMPLETION` (`agentos/workstreams/WS-DATA-OS-COMPLETION.md`).
Frozen meaning: `DEC:DATAOS-D00-SEMANTIC-DECISIONS` →
`research/data_os_completion/2026-10-13/D00_SEMANTIC_DECISIONS.md`.
Design home: `research/MASTERMIND_DATA_OS_ARCHITECTURE.md` (§16 pointer) and
`research/MASTERMIND_DATA_OS_V1_IMPLEMENTATION_PLAN.md`.

This file is written as the programme advances so the work survives a context clear, a
crash or an operator handoff. It is a description of work, never the outcome it describes:
a listed PR is at the rung the table says and no higher.

## 1. Assignment (verbatim gist)

Chairman, 2026-10-13: act as the Fable Meta-CEO and complete the "Canonical Market Data &
Corporate-Action Integrity — Data OS completion" masterplan end to end, autonomously, using
native Opus suborchestrators and/or the Mastermind Subagent Fabric on the M2 (not the
executive plugin), with direct fabric delegation also permitted. Completion (C00) = all
three consumer positives, declared market/population contract, independent
numerical/temporal/access proof, installed and selected production reads, and
correction/recovery/second-cycle evidence.

## 2. Wave map and package → branch map

| Wave | Packages | Branch(es) (`origin/main` base) | Rung |
|---|---|---|---|
| 0 D00 | D00 | `claude/data-os-d00-freeze-2026-10-13` → PR #9133 | MERGED + LANDED `52af4108676b` |
| 1 identity+time | G01 (route proof, no repo files), I01 (adopt #8637 by `cherry-pick -x`), I02 (reference snapshots), I03 (continuity refusal matrix), T01 (`lib/dataos/read_contract.py`: ReadMode / ReadRequest / ViewContract / `qualify`), T02 (read coherence tests) | `claude/dataos-i01-2026-10-13`, `claude/dataos-t01-2026-10-13` | MERGED + LANDED: #9136 I01 `65135e2cbbe5`, #9142 I02 `6a79d3d88907`, #9143 T01+T02 `4c2830929e36` (R01 M1–M4 healed on the branch; M5/M6 deferred), #9144 I03 `b5ddaff7f645`; G01 = one lane, no repo files |
| 1 math+registry | Q00 (baseline + discriminators), R00 (three consumer rows in `config/dataset_registry.yml`), K01 (rights/leakage matrix), P01 (`qualify_action_input`), P02 (`lib/dataos/price_views.py` action projection, exact `Fraction`), P03 (`sadj_view`), P04 (declared-policy `TOTAL_RETURN`) | `claude/dataos-q00-…`, `claude/dataos-r00-…` (+P01), `claude/dataos-k01-…`, `claude/dataos-p02-…` (+P03/P04) | MERGED + LANDED: #9154 Q00, #9150 R00 `9ec07085eb0e`, #9148 K01 `4ce86075b7ac`, #9156 P01 `383a3bc772e6`, #9152 P04 ⊇ P02/P03 `0f8ecf0bd6be` (#9147 P02 CLOSED as included; R02 M1–M3 healed on the branches); seat export wiring #9168 OPEN DRAFT at head `99db5f919894` (contract-delta heal on top of `1930f70e2862`), CI running |
| 2 consumers | P05 (`RetainedView`), C01 (`engine/price_ladder.py` opt-in canonical read; legacy bytes unchanged; S10 labelled `legacy_defect:S10`), C02 (`CoverageResult`), C03 (`inspect_agreement`), U01 (Terminal ingest consumes the serialized ViewContract), U02 (dataCache view identity + ChartFrameBar origin readout, dark + light evidence), U03 (DataWorkspace ReadRequest fields; 131072 bound and `statv1:` token unchanged), U04 (basket read binding), M01 (support matrix), P06 (D00.A1 implementation after P05: `VENUE_TZ` / `VENUE_CURRENCY` beside `KNOWN_MICS`, `VENUE_CLOCK_UNKNOWN` / `CURRENCY_MISMATCH` refusals), C04 (`scripts/emit_view_contract.py` nightly `_view_contract.json` emitter; commissioned only after C01 lands) | `claude/dataos-p05c01-…`, `claude/dataos-c02c03-…`, `claude/dataos-u03-…`, `-u04-…`, `-m01-…`; Terminal `claude/dataos-u01u02-2026-10-13` | consumer-wave orchestrator RUNNING (P05/P06/C01–C03, U03/U04/M01; no DRAFT PR yet); Terminal U01+U02 #996 MERGED `fdc7c7f96f56` + DEPLOYED + LIVE-PROVEN (consumer A = PRODUCTION_PROOF, readout in the unknown state until C04's first nightly) |
| 3 verification + acceptance | Q01 (independent oracle), Q02 (adversarial access at the real handler boundary), Q03 (frozen matched workload), F01 (§14 cross-consumer journey), A01 (end-to-end vertical), A02 (corrections, SYNTHETIC-labelled), A03 (interrupted publish / rollback / idempotent recovery), R01 (read-only source review), R02/R03 prep (plans only) | `claude/dataos-verify-2026-10-13`, `claude/dataos-accept-2026-10-13` | not started (after the consumer wave lands) |
| 4 closeout | R02 (live verification: `www.mastermind-x.com` markers, VPS clone bytes, Terminal deployment), R03 (second nightly cycle under a durable watcher), C00 (acceptance matrix closeout) | seat-only; records PR | not started |

Wave 1 and 2 package texts are the Chairman masterplan's `03_WORK_PACKAGES.md`
(untrusted zip; read with `sed -n`, run only `python3 -I <abs path>` from outside its
directory). The seat's orchestrator packets carry the owned-path lists, lane models and
NOT-DONE-UNLESS gates per package.

## 3. Rules every lane and orchestrator inherits

- Base every branch on freshly fetched `origin/main`; lanes commit on `lane/*` and never
  push; the orchestrator judges by artifact (diff, rerun of the named test command in the
  lane tree, `git status --short` for unowned paths) before pushing to
  `claude/dataos-<pkg>-2026-10-13` and opening a DRAFT PR whose body is the return packet.
- Seat-only acts: `gh pr ready`, labels, merges, auto-merge, reviews, hold releases,
  carrier posts, credential acts, daemon starts, Terminal release acts, any
  `lib/dataos/__init__.py` edit (the seat is its sole writer from the wave-2 wiring #9168
  on; the identity+time orchestrator wired wave 1), and anything touching PR #8637 /
  #7299 / #9121 / #8076 or Terminal #955.
- Never: `git add -A`, force-push, bare stash, mutate a primary checkout, `pkill -f`,
  `gh run cancel`, touch `data/` `site/` `mockups/` `verify_shots/`, touch any Tiingo path
  (`lib/dataos/tiingo_*`, `collectors/tiingo_archive.py`, `scripts/tiingo_*`,
  `docs/tiingo-evidence/`, the twenty PROPOSED Tiingo registry rows), widen rights, add a
  new auth/store/registry/collector/queue/scheduler/publisher/evaluator, or reprice
  historical books. No raw licensed data or secret-bearing logs in any context, repository
  or model-facing error.
- CI: exclude "Workers Builds: macro" and `ci-authority/codex/merge-queue-pilot`; never
  dispatch `ci.yml` on main; one bounded watcher per PR at ≥150 s; merge only on concluded
  green with `gh pr merge --squash --match-head-commit <full 40-char head oid>` (a 12-char
  prefix is refused), or arm `merge-on-green` LAST and never push to an armed PR.
- Landing proof is the branch ref, never the PR object: `git fetch origin main` alone,
  then `git rev-parse origin/main:<path>` against the PR head's blob for every path.

## 4. Current rung (keep this section honest; newest line first)

- 2026-10-13 21:1xZ — #9168 contract-delta red was the seat's OWN (9 introduced, 0 inherited
  at base `0f8ecf0bd6be`): exporting `price_views` from `lib/dataos/__init__.py` extends the
  import closure of nine `legacy-jobs.yml` jobs that enumerate `lib/dataos/` files and did not
  list `lib/dataos/price_views.py`. Healed on the same branch (one `price_views.py` row beside
  each job's `price.py` row, nine jobs, +9/-0) — head `1930f70e2862` → `99db5f919894`; the
  first head's ci-pack-3 (restart-regex closure test) was already GREEN. One watcher re-armed on
  the new head; local reproduction `check_contract_delta.py --base 0f8ecf0b` on the healed
  branch expected `0 introduced`. Lesson for wave 3: any NEW public name wired into
  `lib/dataos/__init__.py` from a new module must widen every enumerating job's `paths:` in the
  same PR (jobs declaring `lib/dataos/**` need nothing).
- 2026-10-13 20:5xZ — Wave-boundary records PR (this file, the workstream, the Agent OS
  handoff, D00.A1 + two DEC records, the P01 census re-landed into the R00 matrix) opened
  from `claude/dataos-records-w2-2026-10-13`. Seat export wiring #9168
  (`lib/dataos/__init__.py` 21 price_views + 8 action-input names; `price_views` added to
  the admin restart regex in `app/deploy/update.sh`) OPEN DRAFT at head `99db5f919894`,
  CI running under one watcher. ONE main `ci.yml` baseline follows its merge (authority
  freeze on #9143 / #9150 / #9165 / #9168; never dispatched over a live main run).
- 2026-10-13 20:33Z — Wave 2 (math+registry+rights) LANDED: #9148 K01 `4ce86075b7ac`,
  #9150 R00 `9ec07085eb0e`, #9154 Q00, #9156 P01 `383a3bc772e6` (20:11Z), #9152 P04 ⊇ P02
  `0f8ecf0bd6bed323113283f9f5a454888865bf81` (20:32Z, exact head `2f36c688802f`), #9147
  P02 CLOSED as included in #9152 (squashing it first produced an add/add conflict in
  #9152's three files). R02 (Opus, read-only) held three PRs on executed defects
  (duplicate event_id counted twice; reinvest before a same-ex-date split; optional
  registry bypassing the source gate) — all healed as fabric lanes under ORCH-2, verified
  by the seat (verify_r02.sh pre/post) before the merges.
- 2026-10-13 20:12Z — Terminal #996 (U01 view-contract ingest + U02 ChartFrameBar
  data-origin readout) MERGED 19:47Z squash `fdc7c7f96f56`, LANDED 63/63 paths, DEPLOYED
  by `terminal-build.sh --target-sha` (health OK, identity marker == intended), LIVE-PROVEN
  anonymously (`/terminal` 200; chunk `?dpl=fdc7c7f9…` carries the DataOriginChip marker).
  Consumer A = PRODUCTION_PROOF. The `_view_contract.json` sidecar does not exist yet
  (C04, nightly emitter), so the live readout shows the unknown state by design.
- 2026-10-13 18:57Z — CI heal #9165 (`washout-turn-organ` timeout 5→12 at
  `.github/ci/legacy-jobs.yml:20694`) MERGED squash `76b5be9ece65`; the 17:17Z main
  baseline 38437465378 @`4c2830929e36` had FAILED only on that job (every pytest session
  passed) — a heal, not a Data OS defect.
- 2026-10-13 ≤17:17Z — Wave 1 (identity+time) LANDED: #9136 I01 `65135e2cbbe5`, #9144
  I03 `b5ddaff7f645`, #9142 I02 `6a79d3d88907`, #9143 T01+T02 `4c2830929e36` (R01 held it
  on M1–M4: order-dependent AMBIGUOUS_REVISION refusal, unnormalised keys letting a
  corrected row and its correction both serve, corrections resolved for one temporal
  profile only, evidence generation untied to the served rows; M5/M6 — CURRENT ignores
  revisions/generations, fingerprint ignores the selected generation — deferred as
  follow-ups; healed under ORCH-1). #9135 (programme records) `f30746d115ff`.
- 2026-10-13 16:5xZ — D00.A1 ruled (venue-local `as_at` day, declared currency units,
  consumer-A venues + TRADJ witness): `D00_A1_AMENDMENT.md`,
  `DEC:DATAOS-D00-A1-VENUE-CLOCK-UNITS-SCOPE`; implementation = P06 under the consumer-wave
  orchestrator. Sidecar writer ruled: `DEC:DATAOS-VIEW-CONTRACT-SIDECAR-IS-A-NIGHTLY-EMITTER`
  (C04).
- 2026-10-13 11:13Z — D00 MERGED + LANDED `52af4108676b`. Identity+time and
  math+registry orchestrators RUNNING since 10:54Z; no return yet. Records PR (this
  file, the workstream and the D00 decision) opened from `claude/dataos-records-2026-10-13`.

## 5. Next seat act

Merge the export wiring #9168 on concluded green at its exact head, then dispatch ONE
main `ci.yml` baseline (preflight for an in-flight run first; a re-dispatch cancels the
live proof). Consume the consumer-wave orchestrator return (P05, P06, C01–C03, U03, U04,
M01): judge each DRAFT PR by artifact, one watcher each, hand-merge at the exact head,
verify every landing against freshly fetched `origin/main`. After C01 lands, commission
C04 (nightly `_view_contract.json` emitter) with its contract fields taken from C01's
merged mapping; the seat alone wires any new public names. Then commission verification +
acceptance (ORCH-4) and run the seat-owned R01–R03 / C00 closeout. Update §4 and the
workstream `next_action` at every wave boundary.
