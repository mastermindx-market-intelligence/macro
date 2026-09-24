# GMI Industrials — first-vertical implementation checkpoint (Fable Meta-CEO seat)

Operation: `gmi-industrials-fable-ceo-e2e-20260924-chairman-001` (research operation `gmi-industrials-sector-research-20260923-sol-001`, research carrier #7789 — HOLD, never product code).
Seat: Fable 5.1, Claude Code session `c6467452-92b1-436b-9999-ee2ae3d2b14b` (account claude8), worktree `Macro Dashboard/.claude/worktrees/gmi-industrials-fable-handoff-0cb6a4` (SPARSE), seat branch `claude/gmi-industrials-seat-program` off `origin/main` `10c0d79e2992`.
Delivery: deliberate Chairman delivery 2026-09-24 ~08:05Z of `GMI_INDUSTRIALS_FABLE_HANDOFF_2026-09-24.zip` (member SHA-256s verified; `verify_wave14.py` 14/14, `verify_wave13.py` 16/16). PICKUP_ACK: #7789 comment 5810419863 (08:13Z) — never re-ACK.
Frozen inputs (verified on `origin/sol/industrials-sector-research-20260923` @ `40d91e50a38c`): plan blob `a5462dc7f36aea08c57ce43a8a230ef00ebae802`, addendum blob `a2416836ad973a9224c4823ae0b6ae4d1272a011`, traceability `c727e109ff84e1318c6a3bb50214ad74a56e6b21`, specs r1 `40fd1e37…` / r2 `9c98e106…` / W12 `b343cbd7…`. Read them with `git show origin/sol/industrials-sector-research-20260923:<path>`.
Procedure: Mastermind protected `docs/sol_skills/INDEX.md` re-read at `origin/master` `ed678f27` (skillpack 1.0.1, bootstrap 1; no delta vs the packet pin `294b4c00`).

## 1. State table (update at wave boundaries)

| Item | State | Evidence |
|---|---|---|
| ACK | DONE 08:13Z | #7789 comment 5810419863 |
| START | pending — after seam rulings + T01 admission | #7789 thread |
| Implementation carrier | task PRs off fresh `origin/main`, merged in dependency order; continuity = this file on `main` (CDV-1 precedent, PR #7880 model) | see §4 |
| G1 shared consumption | HELD for T07/T08 (B's route/mount not built); OPEN for T01–T06 synthetic + incumbent-owner work | #7870 head `70fde3c79956` has no `app/theme_research.py`, no `_basket_intelligence_mounts.html.j2` |
| G2 real inputs | HELD — real EXPO/PNR identity, source receipts, clocks not yet bound | T02/T03 real admission |
| G3 private role/rights | HELD — R4 mechanism selected, unproven; `sec_edgar` scope per A14-06 | T07 |
| G4 shared page | HELD — B owns the aggregator seam | T08 |
| G5 acceptance | HELD | T09 |

## 2. Rulings

Astra/Chairman ruling 2026-09-24 ~07:50Z (relayed): Semiconductor B (#7870) owns the shared base; sector verticals extend incumbent owners and integrate later. Consumed here as R-IND-00: Industrials mints NO shell, evidence, rights, route or mount vocabulary; T01–T06 extend Company Intelligence / Fundamental Forensics / Earnings owners only; T07–T09 wait for B's route family and aggregator on `main`.

Seam rulings R-IND-01.. are recorded in `research/industrials/first_vertical_program/rulings/R-IND-2026-09-24-wave1.md` after the Opus READ_ONLY seam audit (`research/industrials/first_vertical_program/reviews/OPUS_PLAN_SEAM_AUDIT_2026-09-24.md`).

## 3. Fabric and hosts (as of 08:15Z)

Labor = external lanes via the B-kit (`$K=~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/handoff_kits/meta-ceo-b-2026-09-08`): `$K/ext/remote_lane_v8.sh <host> <label>` reading `$K/ext/args_<label>.json`, dispatched through the seat scratchpad copy of `admission_wait_dispatch.sh <host> <label> 2` (marker-count admission, 300 s ticks). Hosts: `m1` (m1studio, GLM+MiniMax keys, window 02–11Z weekdays), `mb` (MacBook, GLM+MiniMax, usually full with sibling lanes), `mini2` (GLM via shim only, no MiniMax key). Packets live in the seat scratchpad `packets/` with the shared `LAW.md` appended. Opus/Fable children: sub-orchestrators and READ_ONLY auditors only. The `mastermind-executive` MCP connector is unauthenticated in this non-interactive session; lane placement follows the accepted fleet practice above (no parallel queue minted).

## 4. Wave plan

| Wave | Tasks | Branch / lane | Gate |
|---|---|---|---|
| W1 | T01 helpers + fixtures + `validate_delivery_inputs` + new gate:code job `industrials-result-cash` | `claude/ind-t01-dependency-binding` / `ind_t01_binding` | G1-synthetic |
| W2 | T02 issuer profiles ∥ T04 pure result-to-cash module (path-disjoint) | `claude/ind-t02-issuer-enrollment`, `claude/ind-t04-result-cash` | T01 merged |
| W3 | T03 case extractors ∥ T05 editions/comparisons | `claude/ind-t03-source-facts`, `claude/ind-t05-source-history` | T02, T04 merged |
| W4 | T06 closed dossier contract + adapter | `claude/ind-t06-financial-dossier` | T03, T05 merged; B's profile pattern |
| W5 | T07 private role, T08 typed view, T09 proofs | after B's route family + aggregator land on `main` | G1/G3/G4 |

Each task PR: Opus `reviewer` READ_ONLY red-team before dependents branch; seat merges on concluded green; a merged slice is a checkpoint, never a completion claim (all 56 requirements stay NOT_EXECUTED until T09's real proofs).

## 5. DO_NOT_REDO

Waves 1–14 research, the nine-task plan, the 56-requirement traceability, R14-01..R14-05, the R4 private-mechanism choice, the #7669 aggregator choice, and the `sec_edgar` rationale scoping. Do not reopen the GET-route or direct-mount designs. Do not put product code on #7789. Do not edit #7870's branch.

## 6. Danger areas

Sparse tree (never write `data/`/`site/`); `issuer_profiles.py`/`event_workspace.py`/`refresh_event_workspaces.py` are shared with #7870 (B) and #7905 (CDV-1 T1) — serialize; a new test wired into a `run:` line needs its `paths:` entry or contract-delta reds every PR; a copied gate:code recipe carries the donor's pip deps; GLM lanes can degenerate — commit-per-step law in every packet.
