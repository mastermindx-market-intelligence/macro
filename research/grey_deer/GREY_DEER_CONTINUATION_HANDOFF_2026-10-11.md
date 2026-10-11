# Grey Deer — continuation handoff 2026-10-11 (Fable seat, pullback operation)

**Program:** `WS:GREY-DEER-RISK-INTELLIGENCE` / MAS-258 · **Sub-operation:** `risk-radar-pullback-20261009`
· **Carrier key:** `grey-deer-fable-orchestration-20261003-001` · **Seat:** Claude Code Fable 5.1
principal (session `da1ad7ad-6fbb-45a4-8a6a-46cee9cadc62`, Macro worktree
`claude/14851c4656838a3b/grey-deer-fable-continuation-32b5d5`).

This is the resumption file (fable-mode L.1). A cold successor reads this file, the latest
`agentos/handoffs/GREY-DEER-RISK-INTELLIGENCE-*.md`, and the Slack thread from the last consumed
counterpart edge, then resumes in one cycle. It is updated at wave boundaries; it is not a session log.

## 0. Read this first

1. **Authority.** Chairman-directed handoff of the whole program to Fable orchestration (package
   `START_HERE_FABLE.md`, 2026-10-11; Sol's documentation PR #8772). Chairman Chris is final authority;
   Sol holds the release HOLDs; this seat holds in-scope delegated decisions and does not re-ask Sol for them.
2. **Ladder for the operation key:** `ACK` (Slack `1791707775.860299`) → `START` (Slack, same thread,
   posted once before the first repository effect) → `RUNNING`. Never re-ACK, never re-START.
3. **Incumbents (never write):** PR #8721 (US OOS baseline, live writer `mastermindxryan`, head
   `f28759c84e2e`); PR #8188 (China pullback view, semantic v6, HOLD-FOR-SOL, custody
   `cn-pullback-lifecycle-20260929-sol-001`, three evidence-receipt conflicts). Held frontier: #6989 /
   #7029 / #7592 / #7875 / #8132 / #8648 / Terminal #849 / #852 — holds bind every merge path.
4. **Capability truth (this session):** Executive ingress BLOCKED at enrollment/OAuth (fabric dispatch
   impossible from here); native Opus children only as bounded orchestrator or READ_ONLY auditor; no
   `ext/sub.sh` lanes in the kit. Under L.7 the seat performs bounded principal work itself.
5. **DO_NOT_REDO:** GD-3 production acceptance (2026-08-27); GD-UI-RADAR-1 (#7467); the phase-only
   remaining-downside diagnostic (RESEARCH_REJECTED_FOR_PUBLICATION); `pullback_causal_features.py`
   (NOT FITTED); the #8188 semantic v6 contract; the 2026-10-11 frontier census in #8772.

## 1. Wave plan and exit gates (written before each wave starts)

| Wave | Content | Exit gate (observable) | State |
|---|---|---|---|
| W0 Reconcile + admit | carrier edges, incumbents, capability matrix, records | ACK + START posted once; records PR MERGED; `python3 scripts/agentos.py validate` 0 errors | DONE (PR #8785 merged `2dd5f5078cba`) |
| W1 Foundations | O1/T02 source-clock-basis-rights qualification; O7/T03 publication-health note; O8/T22 preregistration | three docs MERGED; every pullback feed has a rights disposition (`recorded` / `source_unavailable`); prereg frozen with sha256 before any outcome inspection; GH001 + heartbeat repairs routed to owners on their carriers | RUNNING (O1/T02 written) |
| W2 Observed-move primitives | PIT, basis-correct 5/10/21-session local-move primitives + tests, off the render path | MERGED, CI green, no `data/`/`site/` writes from the render budget, nulls printed | after W1 |
| W3 Consumer qualification | evaluate under the frozen prereg; #8721 consumed read-only through CI | results doc with honest episode N, blocked OOS + purge, abstention rate, negative results preserved; Opus READ_ONLY red-team before presenting | after W2 |
| W4 Integration + acceptance | warning-delivery dependency (#8132 lineage) only after publication continuity is proven; HOLDs intact | production proof on the live surface (authenticated HTTP 200, four authority booleans false); Sol/Chairman checkpoints per the wave matrix §6 | after W3 |

Pre-mortem tripwires (O.15): (a) a lane writes into #8721/#8188 paths → freeze, one owner; (b) Yahoo
closes leak back in as a product source → T02 fails the feed to `source_unavailable`; (c) the proxy
`510300.SS` total-return drawdown is read as nominal damage → label or re-source, never silently mix;
(d) the nightly keeps failing GH001 silently (`continue-on-error`) while W3 claims a prospective proof
→ W3 gate requires a post-repair `daily.yml` run with the publication step green; (e) a Stop-hook block
during CI is answered with a poll → one-line hold note only; (f) a second session on the shared Slack
seat posts for this key → search the key before every once-per-operation act.

## 2. Lane matrix

| Lane | Owner | Artifact(s) | Watcher | State |
|---|---|---|---|---|
| W0 records | this seat (principal) | `agentos/handoffs/…-2026-10-11-FABLE-W0.md`, WS `next_action`, this file, `research/grey_deer/README.md` | records PR + one `gh` watcher ≥60 s / sweeper | MERGED (PR #8785, `2dd5f5078cba`) |
| O1/T02 qualification | this seat (principal; data-source owner for rights determinations) | `research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_2026-10-11.md` | PR | written (manifest v1.0.0); PR in flight |
| O7/T03 publication health | this seat (note); QLedger owner (GH001 repair); CI/heartbeat owner (`stalled_since`) | note under `research/grey_deer/incidents/`; routing comments on #8128 / #8042 lineage | PR | next |
| O8/T22 preregistration | this seat (design); Opus READ_ONLY audit before freeze | `research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md` + sha256 in the WS record | PR | next |
| Fabric dispatch | Executive OS | — | — | BLOCKED (enrollment gate; named, not routed around) |

## 3. Ledger

**DECIDED**
- D1 Seat = this session; organizational `owner: coo-fable` is not a lease; ACK posted once (1791707775.860299).
- D2 No writes to #8721 / #8188; both consumed read-only. #8188 custody recovery is the canonical placement owner's act.
- D3 Fabric unavailable ⇒ L.7 bounded principal work; no second queue, no raw socket, no credential request to the user.
- D4 Records-first: W0 ships as a docs-only PR before any research lane opens.
- D5 US observed-price basis for pullback work moves to Massive (`close_raw` nominal; split basis via recorded `adjustment_asof`); Yahoo closes are not a source for model use or user redistribution.
- D6 CN headline (`000001.SS`, `399001.SZ`): keep the existing observer and record the invariance proof; `510300.SS` proxy is total-return and must be labelled (EN/ZH) or re-sourced raw before any user-facing use; user-facing CN publication is gated on a rights determination.

**FACTS (verified this seat, 2026-10-11)**
- F1 `origin/main` at branch time `ea7fa5bbb44b`; agentos baseline 1608 records / 0 errors / 145 warnings.
- F2 QLedger publication: the 10-08 GH001 failure (run 37716729584, `daily`, head `a7220102c116`, blob 103,393,347 B) was NOT durable - `data/qledger/claims.jsonl` landed on main on 10-09 (`9eabe65cf44f`) and 10-10 (`f71defd249e4`). But no size partition exists (one `claims.jsonl` in `data/qledger/`) and the blob at `ea7fa5bbb44b` is 104,468,672 B = 388,928 B under GitHub's 104,857,600 B limit; measured growth 1,016,105 B (10-08->09) and 56,955 B (10-09->10). Recurrence is a days-scale certainty; the 10-10/10-11 `daily.yml` successes (`38017284947`, `38103820170`) are run colour, not publication proof (`continue-on-error`, comment 6072401693).
- F3 Heartbeat state file last committed 2026-10-09 (`1a2212fbb53c`); the 10-08 commit `e65335239332` is where the risk_radar `stalled_since` was erased (comment 6072401693).
- F4 Massive entitlement RECORDED for display / redistribution / non-display / derived / AI-ML / retention (operator 2026-08-09); Yahoo rows in the Prophet US rights register read "not a source" for model use and redistribution; `config/dataset_registry.yml` labels them `vendor_terms_personal_use`.
- F5 `collectors/china_prices.py:126` stores `auto_adjust=True` closes; `lib/china_pullback_view.py@ff27a268` observes stored `close`; 5y join (comment 6104906486): `000001.SS` 1212 rows / 0 differing, `399001.SZ` 0 differing, `510300.SS` 1038 of 1211 differing (ratio 0.9047–1.0, 5 distributions).
- F6 No China index-price rights record exists under `research/licenses/`.
- F7 #8132 is OPEN / DRAFT on `claude/grey-deer-warning-delivery-20260927-sol-c1` (stale Astra pickup; held).

**OPEN**
- O-a #8188 join custody (owner inert since 10-02; questions 6105079256 unanswered) — canonical placement owner.
- O-b QLedger GH001 size partition — QLedger owner (#8042 → #8669 lineage).
- O-c Heartbeat `stalled_since` preservation — CI/heartbeat owner.
- O-d CN rights determination + `510300.SS` labelling decision — data-source owner (this seat drafts the disposition in T02; the determination is recorded, never assumed).
- O-e Executive ingress enrollment — user-only OAuth step; lane blocker, not a mission stop.

**NEXT (in order)**
1. ~~Post START on the carrier (once), then open the W0 records PR and own it to MERGED.~~ DONE: START `1791709498.229729`; PR #8785 merged `2dd5f5078cba`; MERGED edge `1791710983.487829`.
2. O1/T02 qualification doc → PR → merge. Doc written (manifest v1.0.0); ship chain in flight.
3. O7/T03 publication-health note + owner routing comments → PR → merge.
4. O8/T22 preregistration → Opus READ_ONLY audit → freeze (sha256) → PR → merge.
5. W2 primitives only after 2–4 are MERGED.

## 4. Preserved denial / DO_NOT_RETRY register

- Executive ingress (`mastermind-executive`, `linear-server`, `figma`): OAuth only the user can start; `mmx-cimd-probe` transport refused. No tokens/codes/callback URLs are requested; no alternate carrier is used.
- #8188 publication precheck refusal (owner op `gd-issued-warning-artifact-audit-20261008`): not rerouted.
- HOLDs #8188 / #7029 / #8132 / #7875 / #7592: Sol releases; nobody else arms, marks ready or merges.
- Production runs (`daily`, `render`, watchdogs): never cancelled or re-dispatched by this seat.

## 5. Pointers

- Packet of record: `research/grey_deer/GREY_DEER_FABLE_HANDOFF_2026-10-11.md` (PR #8772) and `#8128` comment 5975760082.
- W0 receipt: `agentos/handoffs/GREY-DEER-RISK-INTELLIGENCE-2026-10-11-FABLE-W0.md`.
- Prior acceptance: `agentos/handoffs/GREY-DEER-RISK-INTELLIGENCE-2026-08-27-GD3-DONE.md`.
- Incident note (T03 creates it; path proposed in #8128 comment 6072335386, absent on main at `ea7fa5bbb44b`): `research/grey_deer/incidents/2026-10-08_QL_GH001_NIGHTLY_ISSUER_PUBLICATION.md`.
- Price-basis law: `lib/dataos/price.py` (`AdjustmentBasis`, `adjustment_asof`); `DNR:KILL-CN-ADJUSTED-TAPE-LEGAL-LIMIT`.
