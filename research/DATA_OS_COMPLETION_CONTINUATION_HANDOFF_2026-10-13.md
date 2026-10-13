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
| 1 identity+time | G01 (route proof, no repo files), I01 (adopt #8637 by `cherry-pick -x`), I02 (reference snapshots), I03 (continuity refusal matrix), T01 (`lib/dataos/read_contract.py`: ReadMode / ReadRequest / ViewContract / `qualify`), T02 (read coherence tests) | `claude/dataos-i01-2026-10-13`, `claude/dataos-t01-2026-10-13` | orchestrator RUNNING |
| 1 math+registry | Q00 (baseline + discriminators), R00 (three consumer rows in `config/dataset_registry.yml`), K01 (rights/leakage matrix), P01 (`qualify_action_input`), P02 (`lib/dataos/price_views.py` action projection, exact `Fraction`), P03 (`sadj_view`), P04 (declared-policy `TOTAL_RETURN`) | `claude/dataos-q00-…`, `claude/dataos-r00-…` (+P01), `claude/dataos-k01-…`, `claude/dataos-p02-…` (+P03/P04) | orchestrator RUNNING |
| 2 consumers | P05 (`RetainedView`), C01 (`engine/price_ladder.py` opt-in canonical read; legacy bytes unchanged; S10 labelled `legacy_defect:S10`), C02 (`CoverageResult`), C03 (`inspect_agreement`), U01 (Terminal ingest consumes the serialized ViewContract), U02 (dataCache view identity + ChartFrameBar origin readout, dark + light evidence), U03 (DataWorkspace ReadRequest fields; 131072 bound and `statv1:` token unchanged), U04 (basket read binding), M01 (support matrix) | `claude/dataos-p05c01-…`, `claude/dataos-c02c03-…`, `claude/dataos-u03-…`, `-u04-…`, `-m01-…`; Terminal `claude/dataos-u01u02-2026-10-13` | not started (after wave 1 lands) |
| 3 verification + acceptance | Q01 (independent oracle), Q02 (adversarial access at the real handler boundary), Q03 (frozen matched workload), F01 (§14 cross-consumer journey), A01 (end-to-end vertical), A02 (corrections, SYNTHETIC-labelled), A03 (interrupted publish / rollback / idempotent recovery), R01 (read-only source review), R02/R03 prep (plans only) | `claude/dataos-verify-2026-10-13`, `claude/dataos-accept-2026-10-13` | not started (after wave 2 lands) |
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
  `lib/dataos/__init__.py` edit outside the identity+time orchestrator's wiring, and
  anything touching PR #8637 / #7299 / #9121 / #8076 or Terminal #955.
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

- 2026-10-13 11:13Z — D00 MERGED + LANDED `52af4108676b`. Identity+time and
  math+registry orchestrators RUNNING since 10:54Z; no return yet. Records PR (this
  file, the workstream and the D00 decision) opened from `claude/dataos-records-2026-10-13`.

## 5. Next seat act

Consume the two orchestrator returns, judge every DRAFT PR by artifact, mark ready,
merge on concluded green, verify each landing, wire the `price_views` exports into
`lib/dataos/__init__.py` through the identity+time orchestrator, then commission the
consumer wave with the landed wave-1 PR numbers and shas in its packet. Update §4 and the
workstream `next_action` at every wave boundary.
