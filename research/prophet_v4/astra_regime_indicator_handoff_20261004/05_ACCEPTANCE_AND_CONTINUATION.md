# 05 — Acceptance ledger and continuation record

**Operation:** `prophet-astra-ceo-fable-20261004-001` · seat: Fable, Claude Code session `f273dd7d-5dfb-4725-b26d-3de277637b11` · carrier: PR #8363 (Astra's handoff DRAFT; one PICKUP_ACK/START comment) and the program PR(s) listed below · plan `03` (frozen) · packages `04`.
**Cold-stranger rule:** a resuming session reads this file LAST section first, then `03 §0` (exit gate), then the lane matrix. Nothing here is a control plane; execution state is in the lane out-files and the GitHub PRs.

## 1. Acceptance gates (per deliverable)

| Deliverable | Evidence level | Gate | State |
|---|---|---|---|
| 03/04/05 chapters | — | merged to `origin/main`; resumable from 05 | see ledger |
| A1 | 1 | review ACCEPT; parity numbers recorded; served definition with file:line receipts | pending |
| C1 | 1–2 | review ACCEPT; both positive controls reported; agreement tables; PIT tests pass | pending |
| B1 | 2 | review ACCEPT; cascade≡canon test; phase-0≡bar_derive test; look-ahead test; month-cluster test; verdict computed by rule | pending |
| C2 | 2 | review ACCEPT; join-leak test; paired-bootstrap test; cell support table; verdict by rule | pending |
| F1 | 2 (small-N) | review ACCEPT; purge test; AUC test; IRLS test; honest-N | pending |
| Seat synthesis | — | C2 verdict + §7 implication written; Agent OS DEC/DSC/handoff merged; `scripts/agentos.py validate` exit 0 | pending |
| Owner handoff (W3) | — | delivered to V4 owners (#6805) as evidence; rung stated honestly (≤ MERGED) | pending |

## 2. Program ledger (DECIDED / FACTS / OPEN / NEXT) — newest entry last

### 2026-10-04 00:30Z — wave 1 frozen (seat)
DECIDED: D1–D8 (03 §3); lane matrix (04 §1); GLM-only labor, MiniMax excluded (DEMOTE 0.00); A1 on flash/census, C1/B1/C2/F1 on glm-5.3 with escalation reasons; TOI W1/W2-0 out of scope (Sol #8332); #8303 pilots DO_NOT_REDO; one writer (seat); parquet outputs not committed; program PR stacks on #8363's head and supersedes it.
FACTS: Astra chapters 00/01/02/09 at `69846be73b62` (head of #8363, DRAFT, no hold, zero comments); mini2 lane checkout `main @ 052e02d085`, clean, full data, scipy 1.18, no sklearn/statsmodels, 4.9 GiB free; Stop-hook dry run on that checkout → rc 0 (no-git lanes end cleanly; results dir git-excluded); gh core remaining 4,677; pool: grok 0/6, cursor 0/3, bailian 0/9.
OPEN: none blocking wave-1 launch.
NEXT: commit 03/04/05 + packets → push → PR → ACK/START on #8363 → launch wave-1 Workflow.

## 3. Lane matrix state

| Lane | Round | Launched (UTC) | Host run id | Out file | State | Review | Notes |
|---|---|---|---|---|---|---|---|
| A1 | — | — | — | — | NOT STARTED | — | |
| C1 | — | — | — | — | NOT STARTED | — | |
| B1 | — | — | — | — | NOT STARTED | — | |
| C2 | — | — | — | — | NOT STARTED | — | |
| F1 | — | — | — | — | NOT STARTED | — | |

## 4. Holds and barriers (never crossed by this program)

HOLD-FOR-SOL PRs never armed/readied/merged: #8303, #8257, #8301, #8304, #8306. V4 incumbents never seized: #7581, #7180, #7572. TOI carriers #7107/#7094 untouched. Phase-22 population and outcomes never read. Production Prophet unchanged.

## 5. Do-not-redo (binding unless materially invalidated)

- #8303 ETF pilot (2,730 events) and kernel factorial (2,681 events) — consumed, not re-run.
- Broad family-by-regime main-effect study (57,642 signals) — scoped null, not re-run.
- RS .75–.85 threshold study; 1.5-ATR gate NO-GO — not re-run.
- The blocked `03` upload — not retried or rerouted; this `03` is the receiver's own authored plan.
- Pickup ACK/START on #8363 — posted once (search before any re-post).

## 6. Danger areas

- mini2 disk at 98%: lanes capped at 300 MB; never write under `data/` on the host.
- Lanes run on `main` in a shared checkout: no git writes, ever; the seat rsyncs and commits.
- Fleet git identity makes the seat's pushes look like a sibling's; verify by branch name, not author.
- A push to an armed PR can land after its merge — arm `merge-on-green` LAST.
- Do not run the full pytest suite in a sparse tree; the seat worktree is full-data for the lanes' local re-execution.

## 7. Next action for a resuming session

Read §2's last entry and §3; reconcile every lane's out file ONCE (RUNNING / DELIVERED / SILENT / DEAD / THRASHING); judge DELIVERED lanes by artifact through a `reviewer`; continue the wave from the lane matrix; never re-ACK on #8363; never re-launch a lane whose out file already carries `<LANE>_RETURN:`.
