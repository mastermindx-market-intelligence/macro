# MarketOntology — CEO B (F06–F13) continuation handoff — 2026-10-10 (seat transfer to the Claude3 account)

Supersedes `research/MARKETONTOLOGY_CEO_B_CONTINUATION_HANDOFF_2026-10-02.md` for seat state; its rulings R-B-01…R-B-08 still bind.
Written by the outgoing seat (Fable session `3add8c61`, Claude Code, worktree `ceo-b-marketontology-handoff-6ec639`) at 2026-10-10 ~22:00Z against macro `origin/main` `9bcdbb4d887f` and Terminal `master` `34d52545ac04`.
Cold-stranger test: a successor on a DIFFERENT Claude account, with no access to this account's memory, must be able to take the seat from this file plus the carrier (macro issue #6819) alone.

## 0. Read this first — the Chairman directive and who you are

- Chairman/operator, 2026-10-10: **"checkpoint and hand off to Claude3 account. Need to tell it to run on full throttle to get as much done as possible."**
- You are the successor **CEO B** seat: MarketOntology families **F06–F13** (79 of the 130 F00C ledger rows) plus the joint **J1** proof with CEO A. Carrier = macro issue **#6819**. Commissioning record = the Astra Pro Mode CEO handoff (#6819 comment 5946057251) with the Sol operating addendum (5946604516). Do not re-ACK either.
- **Full throttle means:** continuous waves of *verified* capability on F06–F13 rows; several path-disjoint lanes in flight at once through the Mastermind Executive/Subagent Fabric (external lanes), the seat adjudicating in its own main loop; never idle while an authorized lane exists; every opened change carried to MERGED + PRODUCTION_PROOF in the same seat; one #6819 receipt per closed lane.
- **Full throttle never means:** fabricated or restamped proof, self-enabling dormant flags, any credential act, touching held or other-seat PRs, native Opus/Sonnet/Haiku labor subagents, rerun storms, or merging mid-flight. §2 is the boundary; speed is bought inside it, never through it.

## 1. Seat identity and carrier discipline

- Predecessor = this account's Fable session `3add8c61`. **Announce your OWN session id on #6819 once** (one transition acknowledgement, naming this file); never self-identify as `3add8c61`; never re-ACK or re-START anything already acknowledged on the carrier.
- Carrier edges at transfer: predecessor's own last substantive edge **6072879900** (10-09 02:1xZ, F08-851 PRODUCTION_PROOF) plus the transition note that links this file; counterpart traffic consumed through **6102601319** (CEO A's own transfer notice, 2026-10-10T21:57:01Z). Everything after 6073882128 is adjudicated in §5 — do not re-adjudicate it.
- **CEO A's seat moves to the Claude3 account at the same time** (#6819 6102601319; records PR #8751 with D95–D97; A resumes from §7 of `research/MARKET_ONTOLOGY_CEO_A_CONTINUATION_HANDOFF_2026-10-02.md`). Authority is unchanged: A owns F01–F05 and is the sole F00C writer, B verifies. **One seat per session:** the B successor must be a distinct session from the A successor even though both run on one account; never answer the carrier as A, never write F00C.
- Read the carrier forward from the last **counterpart** edge you consumed, never from your own last post. One `gh api …/issues/6819/comments?since=<iso>` per cycle; consume-then-act; answer ordinary CEO A questions directly; accept/counter interface proposals; never wait for an ACK-of-ACK.
- Slack thread `C0BTG1BMY8K / 1790918549.460609` was unreadable from this account (Slack MCP unauthenticated). If your account can read it, bind it once and say so on #6819; otherwise #6819 remains the only carrier you can prove.
- **Shared GitHub identity:** every fleet session authors as `mastermindxryan` / `chriswong6031-creator`. `--author` never identifies your PRs. B's PRs are identified by #6819 receipts and branch names (`claude/mo-b-*`, `claude/ceo-b-*`, `claude/f08-*`). Terminal **#896–#913** (`test(evidence): recapture …`) are another program's lanes under the same author — never touch.
- Gate every post on a fresh fence read (newest comment id > last consumed); never run the fence read and the post in one unconditional command.

## 2. Boundary (verbatim; in force for the successor exactly as for the predecessor)

- #761's signed-in Playwright storage state is a bundle of the user's live auth session cookies/tokens. Harvesting it is a prohibited credential action even with full authority, AND it is the project's human-only gate by design. Must NOT pursue by any route.
- Never mint or handle credentials, create accounts, sign in, or fabricate storage state.
- **#761 = EXACT_HUMAN_GATE.** "Do not create accounts, credentials or synthetic 'live' proof."
- BUILT_NOT_PROVEN ceiling: never manufacture a due date or manual run and call it natural-cadence proof.
- Never read secret VALUES on hosts or the VPS; only key names and counts. Redact log output.
- Never trigger, dispatch or manually run the nightly or worker. This covers the terminal-data cron, `daily.yml`, `weekly.yml`, `debt-maturity-drip.yml` and the webhook worker.
- Never self-enable `RECURRING_BRIEFS_ENABLE`. Never mount or unmount the hung m1 volume. Never touch the Terminal host cron or `.env.local`.
- Production DDL apply is a credential act and is never performed.
- Lane M: the caller JWT never enters prompts, logs or tests.
- Terminal live check: **"Do NOT sign in."** Anonymous status reads only.
- Forbidden: empty commits, rerun storms, force merges, fabricated proof, weakened tests, and evidence restamping for changes that need recapture.
- Local e2e uses the fixture seam on localhost (`TERMINAL_E2E_FIXTURE=1`). It is NOT production signed-in proof.
- F13 readback boundaries: never trigger, dispatch, or manually run the nightly, terminal-data, or the worker; never read secret values (key names/counts only, redact output); never mint/refresh credentials, never sign in, never create accounts, never touch #761 (EXACT_HUMAN_GATE) or #7100 (HOLD-FOR-SOL). No Opus/Sonnet/Haiku subagents for labor.
- The authority grant "you have full authority to act on my behalf" covers seat judgment inside this boundary. It does not cure a credential gate, a data-availability gap, or another owner's custody.

## 3. Standing fences (never touch; adjudicate only where it says so)

| Fence | State | Rule |
|---|---|---|
| Terminal **#761** `[MO-B F11-10c]` | DRAFT, head `aacecaf476a2` | EXACT_HUMAN_GATE. Never dispatch, ready, merge, or harvest. One operator export (`npx playwright codegen --save-storage=…` by the authorized principal) unlocks #761 Phases B/C, MO-PAID-039/051/058 and every signed-in panel proof; until then those rows sit at BUILT_NOT_PROVEN and you report that ceiling, never work around it. |
| macro **#7100** `[MO-BW6] B-F11-6` | DRAFT / HOLD-FOR-SOL, r7 head green, readback 5978034479 | Never arm, mark ready, or merge. Resumes only on a same-carrier Sol `CONTINUE` / `REQUEST_REPAIR`. |
| macro **#7357 / #7358** `[MO-B-REC]` | OPEN, Sol HOLD | Never close, never arm. |
| macro **#7117** `[MO-B HEAL-AUDIT] B-F07-1` | OPEN since 2026-09-13, head `fda23c11bddf`, labels `merge-on-green` + `merge-blocked`, last sweeper refusal 2026-09-22 (semantic proof unusable) | Pre-handoff seat artifact that was NOT in the 10-01 inventory and that the predecessor never touched. **Successor adjudicates custody first:** `git diff --stat origin/main <head> -- <its files>`; if superseded/landed → close with a comment naming your session; if still wanted → disarm visibly (comment + `merge-blocked` stays), rebuild on a fresh branch off `origin/main`, re-review. Never force-merge. |
| Sol placement **5989578037** | pending | Add Symbol (C4 5988227669 / C2 5988426602) and the Watchlist findings (C4 5993627763, C2 5994757193, C4 6041866838) are consumed evidence with **no B custody** until Sol places them. |
| SearchModal | unassigned under F00; C3 holds the bounded ArrowDown zero-row repair (6083693499) | Not a B lane. |
| F09 | owner-gated: `DEC:MARKET-ONTOLOGY-POST-TIMEOUT-COMPLETION-ARCHITECTURE-2026-09-02` §6; `WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2` owner `coo-fable` | macro #8673 (C2 issuer-state repair, DRAFT) and covenant-headroom wiring (MO-DELTA-021) are not B lanes; B takes no custody. |
| MO-PAID-085 digest send path | "SEND PATH IS OFF" | External effect (emails to users) → reserved Sol/Chairman decision before any lane. |
| Other seats' PRs | — | Terminal #808, #813, #801–#804, #776, #774, #827, #829, #814, #757, #755, #731–#733, #582, #896–#913; macro #8673. |
| VPS `146.190.142.17` | — | **Audit20** (root `01a10f92`) owns Terminal releases under the macro-update lock: before any Terminal deploy read #6819 and `/var/lib/mastermind-terminal/release-preflight/` for an in-flight canonical release and never start a second builder. `ingest/gen_slices_all.py` and the git-pack maintenance python are other owners' processes. Quiet window for deploys: weekdays ≥22:07Z or <13:00Z. |

## 4. State at transfer (ladder rung = highest fact with evidence)

| Lane | Rung | Evidence |
|---|---|---|
| F08-851 — C2's Terminal #851 (`eventImpact.ts` `calendar_unreadable` for a bad ticker map/row; B held F08 integration accountability) | **PRODUCTION_PROOF (app layer)** | squash `505edf78` (tree == head `f9eea521`); live deploy `a70cf2ad` (Audit20's canonical release) carries it; anonymous: `/terminal` 200, `data-dpl-id`, server chunk contains "bad ticker row", `/api/event-impact` 401 anonymous. #6819 receipt 6072879900. Signed-in panel = #761 gate. |
| F08-RAIL — Terminal #830 | PRODUCTION_PROOF (app) | squash `1c78e496`, anon dpl-id; C4 round-2 PASS 5997982150; receipt 5998643387. |
| F08-REARM — Terminal #823 | PRODUCTION_PROOF (app) | squash `8885866c`; r2 repaired C4 5991393156; receipt 5993360086. |
| F08 heal — Terminal #805 | PRODUCTION_PROOF | squash `a885200f` 2026-10-04 (identity + health verified; anon read). **C2 later proposed a Settings-targets GET-retry on top of it — see §5 item 1.** |
| F08 portfolio mutation chain — Terminal #807 | MERGED | squash `5dcaf15f` 2026-10-05T05:56Z. |
| F08 producer-contract repair — macro #8434 | MERGED | `31061d29df70` (unknown private holdings fail closed — never an empty-book brief). |
| F12 — Terminal #806 (`8bab5556`), #816 F12-PERSIST (`df7a4da3`), #818 F12-CLIPBOARD (`ab460b26`) | PRODUCTION_PROOF (app) | deployed + anon dpl-id each; receipts on #6819 (5989945305 and following). |
| F11-11b-pre-2 — Terminal #762 (Alerts cockpit thesis summary) | MERGED + deployed | squash `a7447db0` 2026-10-04T08:59Z. |
| F11-6 recompose Lane T — Terminal #798 | PRODUCTION_PROOF | squash `1c708450`. Lane M = macro #7100 (held, see §3). |
| F13 / MO-DELTA-007 personal-accuracy scoring | **PRODUCTION_PROOF (natural cadence)** with a BUILT_NOT_PROVEN residual | nightly 2026-10-05 22:38:47Z ran `score_personal_accuracy` (`settled 0, undetermined 0, skipped 0`, no Node-20 WebSocket throw); the settle path is unexercised because nothing was due — proving it needs a naturally due authorized claim, which only the #761 operator act can create. Never manufacture one. |
| Census F06–F09 / F10–F13 | MERGED (macro #8423 `596aa45af820`, #8426 `1b9bdfd2620e`, #8429 `ad9fbf0eebf6`, #8431 `5ea8b012106c`) | the two docs in §6; CEO A's F00 writer consumed them (W14 records #8496 `543e6513`). |
| J1 joint proof with CEO A | context contract SETTLED (R2(b)); live joint proof still gated | transmission return href rule R-B-02; anonymous phase proven on Terminal #744; signed-in phases = #761 gate. |
| Open B PRs / lanes / watchers at transfer | **none** | no open B Terminal PR; no B macro PR besides this handoff and the held/stale set in §3; no fabric lane running; no watcher armed. |

## 5. Carrier traffic adjudicated at transfer (everything after 6073882128; do not re-adjudicate)

1. **C2 6076995179 (10-09 08:05Z)** — tested Settings-targets GET-retry proposal (+ revision-2 owner-generation repair) posted on Terminal **#805** comments 6076991008 / 6077827461; "consume through the existing F08 source owner; no new branch or reassignment". #805 is B's own F08 heal and is already MERGED, so the only lawful adoption is a **new B Terminal PR** against current `master` (verify the patch still applies on `34d52545ac04` or later). **Disposition: ACCEPTED as backlog lane `B-F08-SETTINGS-RETRY`** (successor wave-1 candidate). Not done unless: EN/ZH 390/1440 browser evidence recaptured for real, scoped fixture typecheck green, hosted CI green, anonymous live read after deploy.
2. **C4 6083598726 (15:06Z)** — SearchModal empty-to-populated keyboard case, source-only, no ownership transfer requested. No B action.
3. **C3 6083693499 (15:12Z)** — C3 takes the bounded SearchModal ArrowDown zero-row repair. No B action; fence recorded in §3.
4. **C2 6089317076 (21:10Z)** — stock-library (`templates/stockdata.js` + `site/stockdata.js` + native test + a narrow CI manifest/registry overlay) recovery implemented locally, **publication HELD** pending the user's retry approval; no branch, commit, or PR exists (proposed branch `sol/c2-stockdata-index-recovery-20261009` absent). F08/Market OS integration ownership stays with B. **Disposition: no B act until a source carrier exists;** when C2 publishes, B reviews and carries it through the macro ship chain as F08 owner (paired template/site copy law applies: `python -m scripts.check_template_site_sync --fix`).
5. **C4 6091394282 (10-10 00:05Z)** — "acknowledged DELETE can be undone on screen by an older inventory read" (SPEC_ONLY; AlertsView blob `93d5d375`, API blob `b5c7be3a`, Terminal master `b7a3357b`). Returned to B for disposition. **Disposition: ACCEPTED as F08-Alerts defect lane `B-F08-ALERTS-DELETE-FLOOR`** — component-local per-ID acknowledged-delete read floor + the eight regression groups in the comment; re-verify the blobs against current master first.
6. **C4 6091529927 (00:20Z)** — "delayed create success clears a newer alert draft" (SPEC_ONLY, same AlertsView blob). **Disposition: ACCEPTED as `B-F08-ALERTS-DRAFT-REV`** — component-local monotonic draft revision ref guarding ONLY `setVal("")`, ten regression groups per the comment. Items 5 and 6 touch the same file: **one lane owns `AlertsView.tsx`** (one PR with two reviewed commits, or two strictly serialized PRs) — never two writers.

7. **CEO A 6102601319 (21:57Z)** — A's seat-transfer notice (not a re-ACK), D95 readback through 6091529927 (no F01–F05 act), and **D96:** the 10-10 natural `weekly.yml` run 38074714177 was cancelled at step 9 (19:46:16Z, 95 min into a 300-min cap, group `cancel-in-progress: false`), so the recurring-briefs producer step was skipped — **MO-PAID-032 stays BUILT_NOT_PROVEN with no observation this week; next natural read 2026-10-17 at or after 22:30Z.** Who cancelled the lane is the lane owner's/operator's question. **Disposition: consumed; B dispatches, cancels, and re-runs nothing** (boundary §2); the transition note answers it.

Earlier adjudications that still stand: C2 6073882128 (#8673, F09, coo-fable — no custody); C4 6041866838 (Watchlist read-failure typing — Sol placement pending); CEO A 6006069622 accepted (reply 6006318924).

## 6. Backlog — where capability is still owed (verify every cell against current source before launching a lane)

- **Row evidence (canonical, on `origin/main`):** `research/market_intelligence_productization/CEO_B_CENSUS_F06_F09_ROW_EVIDENCE_2026-10-02.md` (44 rows: PROVEN_LIVE 9 · BUILT_NOT_PROVEN 7 · PARTIAL 10 · NOT_BUILT 18) and `research/market_intelligence_productization/CEO_B_CENSUS_F10_F13_ROW_EVIDENCE_2026-10-02.md` (35 rows; its RESULT table carries the split). Both carry §CORRECTION blocks — read them.
- **Stale-cell lesson (happened twice, 10-04):** census NOT_BUILT cells for MO-DELTA-018/MO-PAID-059 (debt-maturity) and MO-PAID-032 (recurring briefs producer) were already BUILT on main. Before any build lane: `git grep` the row's named paths on fresh `origin/main`, check `docs/ACTIVE_BUILD_MAP.md`, `research/DO_NOT_REBUILD.md`, open PRs on the owned files, and the live page. "Do not rebuild from stale NOT_BUILT cells."
- **Already settled, do not redo:** 018/059 PROVEN_LIVE (#6921 producer + `debt-maturity-drip.yml` natural runs + served `#debt-maturity` panel); 032 producer present and DORMANT behind the operator-held `RECURRING_BRIEFS_ENABLE` (ceiling BUILT_NOT_PROVEN; never self-enable; the 10-10 weekly observation was lost to a cancel — D96 — next natural read 2026-10-17 ≥22:30Z, never dispatched by B); 054 custody CLEAR (Terminal #577 merged) → the residual chat↔thesis context binding is a legitimate build candidate; 021 covenant headroom owner-gated (§3); 085 reserved (§3); 039/051/058 human-gated (§3).
- **Known pre-existing defect, unfixed:** F11 research-views surface renders the ZH status "有效" red where EN "Active" renders green (seen in #763 crops). Bounded Terminal fix candidate; design law = `docs/DESIGN_DOCTRINE.md` + the theme art-direction rule (dark and light judged separately, EN/ZH × 1440/390 evidence).
- **Terminal-side census of F08/F11/F12 rows was DEFERRED on 10-02** (census lanes could not mount the Terminal tree). A read-only census lane against `~/Documents/Cluade/charting-app` (or a fresh clone of `mastermindx-market-intelligence/mastermind-terminal`) is cheap and will sharpen the backlog.
- **Full-throttle wave 1 (path-disjoint, all buildable now, none gated):** (a) `B-F08-ALERTS-DELETE-FLOOR` + `B-F08-ALERTS-DRAFT-REV` — one Terminal lane on `terminal/components/AlertsView.tsx` (+ tests); (b) `B-F08-SETTINGS-RETRY` — Terminal lane on the Settings targets loader (C2's two-file patch); (c) MO-PAID-054 residual — Terminal lane on the thesis workspace/chat binding; (d) F11 ZH status colour defect — Terminal lane on the research-views surface; (e) read-only Terminal census of the F08/F11/F12 rows; (f) macro: the 18 F06–F09 NOT_BUILT rows, each re-verified first, ordered by the census "next_bounded_child" column, DNR-checked, off the render path (budget law). Trees (a)–(d) are disjoint from each other and from (f).

## 7. How to run at full throttle (operating model)

- Run the seat loop every cycle, in order: read the carrier from the last counterpart edge → reconcile watchers once from their log files → judge every delivered return by its artifact (diff/tests/crops, never the report) → write the ledger → commission from the critical path → launch + arm exactly one watcher per lane → bounded principal work only when no worker started, you hold custody, no other owner is on the artifact, and nothing is EFFECT_UNKNOWN → checkpoint and go quiet.
- **Labor goes to the fabric:** the B-kit external lanes (`ext/sub.sh` / `remote_lane_v8.sh`: GLM first, MiniMax for mechanical/read-only, Cursor fallback; m1 admission gate load1 ≤ 7; mini2 read-only). Per Chairman 2026-10-06, Opus 5.5 **orchestrators** may administrate fabric lanes (cap 2 concurrent, no native children under them). Native Sonnet/Opus/Haiku labor subagents remain banned (Chairman 2026-10-04). If no lane can be admitted and the four conditions above hold, the seat executes the bounded lane itself — a dead delegation surface is not a reason to stop.
- **Parallelism:** keep 3–5 lanes in flight on disjoint trees (Terminal component lanes ∥ macro row lanes ∥ a read-only census lane). One owner per artifact; two lanes needing one file are merged or serialized.
- **Review before ready:** an Opus read-only review of the diff (orchestrator or main loop) plus the peer reviews that arrive on #6819 from C2/C4. A late review outranks an early approval (F08-REARM was reopened once for a missed C4 review — do not repeat).
- **DONE per PR** = merged on CONCLUDED checks + PRODUCTION_PROOF (anonymous evidence on the served host) + one #6819 receipt. Then the next lane in the same turn. A merged wave is a checkpoint, not a session end.
- **Two no-delta cycles → change lane/tier/owner.** Hold notes against the Stop ladder are few words and no tool calls.
- **Record as you go:** your own program file (account memory) + this repo's `research/` continuation docs at wave boundaries; the predecessor's local ledgers (§9) are read-only reference.

## 8. Mechanics the successor needs

**Terminal (`mastermindx-market-intelligence/mastermind-terminal`, default `master`, strict protection; required contexts `Quote Hub tests`, `Terminal typecheck + tests`, `Ingest + signal-layer tests`; Vercel checks non-binding, R-B-07).** Branch off fresh `origin/master`; PR; arm with `gh pr merge N --auto --squash --match-head-commit <full-head>`; when BEHIND: `gh api -X PUT repos/…/pulls/N/update-branch -f expected_head_sha=<full>` then re-pin; on MERGED: `git fetch origin master` alone, `git log origin/master --grep '(#N)'`, compare `<squash>^{tree}` with `refs/pull/N/head^{tree}`. Deploy detached (python `subprocess.Popen(..., start_new_session=True)`): `ssh -o BatchMode=yes -o ConnectTimeout=20 -i ~/.ssh/macro_dashboard_deploy_v2 root@146.190.142.17 "bash /opt/terminal/terminal-build.sh --target-sha <full>"` — the script fails closed pre-swap and restores the live generation; a Turbopack/PostCSS timeout under VPS load ~6 is environmental (happened 10-09; Audit20 released the same commit later). Anonymous proof: `curl -sL https://app.mastermind-x.com/terminal` → 200, `<title>Mastermind Terminal</title>`, `data-dpl-id` == squash SHA, and a grep of the served chunk for a string only your change introduced. Never sign in.

**Macro (`mastermindx-market-intelligence/macro`, default `main`).** Session start: `git fetch origin && git merge --ff-only origin/main` in `/Users/chriswong/Documents/Cluade/macro-main` (if the ff fails, stop and tell the operator); work in a fresh worktree on a `claude/<task>` branch; commit → push → PR → `gh pr edit N --add-label merge-on-green` **LAST** (never push into an armed PR) → one watcher → on MERGED `git fetch origin main` alone and blob-compare each path against `origin/main`. Paired template/site assets ship together; `scripts/check_template_site_sync.py` refuses on a sparse tree (`python3 scripts/worktree_sparse.py full` first).

**Watchers / quota.** One watcher per endpoint, ≥150 s cadence, rate preflight `gh api rate_limit --jq '.resources.core.remaining'`; start detached and wait on the pid in the background; never foreground `gh run watch`/`--watch`, never `sleep`+poll in the principal turn (the CI wait guard denies it), never a `for … gh …` loop without ≥90 s sleep (the quota guard denies it), never re-read the same PR state inside 300 s (the guard fences it). Job logs: `gh api --allow-escape-sequences … | perl -pe 's/\e\[[0-9;]*[A-Za-z]//g'`.

**Posts.** Commit trailers and PR footers follow the harness reminder of the day. #6819 posts: gated fence read first, then one post; never re-ACK.

**Hourly reciprocal-attention check — recreate on YOUR account (replace the session id):**

> CEO B hourly reciprocal-attention check (MarketOntology F06–F13, seat session <YOUR-SESSION-ID>). Do exactly this, quietly: (1) read the Slack thread C0BTG1BMY8K / 1790918549.460609 forward from the last edge you consumed and macro #6819 comments newer than your last consumed comment id (one gh api call with ?since=); (2) for each NEW peer/Sol/Chairman message, adjudicate it per the seat loop (S.1): answer ordinary CEO A questions directly in the thread, accept/counter interface proposals, never re-ACK/re-START, never wait for an ACK-of-ACK; (3) reconcile armed lane watchers ONCE from their log files (no gh polling, no tailing between ticks); (4) update LANES.md / the program memory file if anything changed. If nothing is new, do nothing and post nothing.

## 9. Transfer receipts and local reference (this Mac, unix user `chriswong`; read-only for the successor)

- This file ships in the handoff PR named in the #6819 transition note; that note is the predecessor's final own edge.
- Predecessor cron 36402219 (hourly check) and 7d134317 (F13 readback) belong to the `3add8c61` account and are retired at transfer; if the scheduled-tasks tool stayed unreachable during transfer the operator retires them — the note on #6819 says which happened.
- Kit `~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/handoff_kits/meta-ceo-b-2026-09-08` (`ext/` lane launchers, `orch/ceo_b_2026_10/LANES.md` lane ledger, `WAVE2_PLAN.md` with the 10-04 corrections, `records/`, `packets/`, watcher scripts).
- Predecessor program memory: `~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/memory/marketontology-ceo-b-f06-f13-program.md` (542 lines of checkpoints, 10-01 → 10-09).
- Terminal checkout `~/Documents/Cluade/charting-app` (remote `mastermind-terminal`); macro primary root `/Users/chriswong/Documents/Cluade/macro-main` (linked worktree — never open `…/Macro Dashboard` as a workspace, never delete it).
- `agentos/`: no dedicated MarketOntology `WS-*` exists; F09 state lives under `WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2`. Mint records only for durable facts (`DSC-*`) or choices (`DEC-*`), never session logs.

## 10. First-hour checklist for the successor

1. `cd /Users/chriswong/Documents/Cluade/macro-main && git fetch origin && git merge --ff-only origin/main`; mint a fresh sparse worktree on a `claude/ceo-b-*` branch.
2. Read this file, the two census docs (§6), `research/MARKETONTOLOGY_CEO_B_CONTINUATION_HANDOFF_2026-10-02.md` §2 (rulings), and the #6819 comments from 6072879900 onward.
3. Fence read #6819; post ONE transition acknowledgement with your session id, this file's path, and the edges you take over (own = the predecessor's transition note; counterpart consumed through 6102601319 plus anything newer you just read and adjudicated).
4. Recreate the hourly check (§8) on your account.
5. Adjudicate macro #7117 custody (§3) — one bounded act, then move on.
6. Launch wave 1 (§6): the AlertsView lane first (two accepted C4 findings, one owner), then Settings retry, 054 residual, the ZH colour defect, the read-only Terminal census — on disjoint trees, one watcher each — and carry each to MERGED + PRODUCTION_PROOF + receipt. Keep going.
7. End every substantial turn on a state (`SESSION END: <STATE>`); `MORE_WORK_EXISTS` is never a stopping state.
