# Sector Intelligence build-out — execution frontier

**Program:** Macro #7646 / WS:SECTOR-INTELLIGENCE-COMPLETION. **Plan:** PR #10915 (`FINAL_FABLE_T3_PACKET_2026-11-09.md`).
**Assignment:** Chairman, 2026-11-09, to the T3 COO thread `2f136a11-91f9-4bca-bf10-8a1d8b7f4e5d` (Fable).
**Coordination branch (Macro):** `claude/ssd-t3-7e7aa529-223284e0aaec51f6` — plan documents, the lane charter and this frontier only.
**Lane rules:** [`EXECUTION_CHARTER_2026-11-09.md`](EXECUTION_CHARTER_2026-11-09.md).

This file records what was started and what has returned. A row marked STARTED means a worker thread was launched;
it is not a delivered, tested, merged or served result. Update the row only from the lane's returned evidence.

## Source frontier re-read at start (2026-11-09)

Macro main `cae8e01be6ad`. Terminal master `2fe2f02f07d1` (the packet was written at `57ab4281`).
Donor heads unchanged from the packet: Terminal #1339 `7ded5375`, #1249 `abe704f1`; Macro #10780 `91add961`,
#10839 `3894ea1b`, #10777 `99968fd0` (CONFLICTING, `merge-on-green` + `merge-blocked`), #10703 `9fc460ff` (Draft/HOLD),
#10707 `74930f69` (Draft/HOLD), #10676 `b3cb43f3` (Draft), #9124 `2b72dc1c` (Draft/HOLD).

Donor PRs are reused by SHA into new lane branches. No donor carrier is pushed to, relabelled, merged or closed.

## Wave 1 (launched 2026-11-09)

| Lane | Brief | Repo | Branch (intended) | Model | State |
|---|---|---|---|---|---|
| 1 Macro sector generation | 1 | Macro | `claude/si-macro-generation-20261109` | GLM 5.3 | STARTED |
| 2 Paper design completion (five missing groups) | 2 | Paper R4 + Macro docs | `claude/si-design-r5-20261109` | Opus 5.5 | STARTED |
| 3 Terminal native workspace + integration writer | 3 | Terminal | lane branch from `master` | GLM 5.3 | STARTED |
| 4 Terminal full Cycles | 4 | Terminal | lane branch from `master` | GLM 5.3 | STARTED |
| 5 Research v2 + industry evidence | 5 | Macro | `claude/si-research-v2-20261109` | GLM 5.3 | STARTED |
| 6 Durable investigations and actions | 6 | Terminal | lane branch from `master` | GLM 5.3 | STARTED |

Terminal shared files (`SectorIntelligenceWorkspace.tsx`, `sectorIntelligenceLex.ts`, `sectorIntelligence.ts`,
`app/api/sector-intelligence/route.ts`) have one writer: lane 3. Lanes 4 and 6 return mount hunks.

## Wave 2 (not started — each waits on a named input)

| Lane | Brief | Waits on |
|---|---|---|
| 7 Retained native depth and compatibility (calls, Bottoming Watch, flows, four universes, legacy destinations) | 7 | Lane 3 workspace slots; lane 2 frames for groups 1–3 |
| 8 Analytics and history (definitions, turn knowledge, B12 scientific disposition) | 8 | Lane 1 landing `engine/sector_central.py` (shared file) |
| Terminal integration pass (mount lanes 4 and 6, lane 5 research consumer) | 3 | Lanes 3, 4, 5, 6 returns |
| 9 Integrated candidate proof, release, served and natural-update evidence | 9 | An integrated candidate in both repos |

## Open decisions held by the COO

- Macro static-site Cycles composition (#10777 / #10703 / #10707): the native Terminal controller re-implements the
  capture/apply behaviour (lane 4). Whether the Macro template side is also completed, or retired after parity,
  is decided after lanes 3 and 4 return (packet §8.5).
- Installed `valid_investigation_manifest_v2` shape (0042 versus 0043) was not read in planning; lane 6 writes a
  preimage-asserting migration source only. Applying it is a separate operator act.
- Release: Terminal #1339's upstream integration/release hold and Mastermind #1202 conditions are unchanged. No
  deployment has been attempted.
