---
workstream: "WS:GMI-THEME-GRAPH"
session: claude/ssd-gmi-robotics-reland-hold-17c9f82c
model: opus
ended_because: blocked
mission: >
  Principal (Fable Meta-CEO seat) record for operation
  gmi-robotics-fable-ceo-e2e-20260923-chairman-001: deliver the first production-proven
  granular Robotics theme-intelligence vertical (Precision Motion + Perception) inside the
  existing Theme Tracker / basket/robotics_automation.html workflow by CONSUMING the shared
  GMI foundation on #7870, building only the Robotics-specific composition, evidence
  qualification, facets, non-regression and real-path acceptance. Canonical packet: #7773 at
  325be052aa5892f21a399ec0eebc1bd5c65b995a, file
  agentos/handoffs/GMI-ROBOTICS-MASTER-FABLE-CEO-HANDOFF-2026-09-23.md.
state_before: >
  This operation had NO durable record on main. Its working checkpoint,
  agentos/handoffs/GMI-THEME-GRAPH-2026-09-24-robotics-implementation.md, was one of the 35
  paths the revert #8013 removed, so the knowledge record was collateral damage of a revert
  aimed at code. A successor reading main found nothing: not the revert's cause, not the
  no-split-re-land ruling, not the merge-order dependency on #7870. Everything below lived
  only in account-local session memory, which is explicitly not company memory. Implementation
  carrier #7908 merged 2026-09-25T07:27:34Z (70b3c9f1f8f0) and was reverted the same day by
  #8013 (e5512ef66a74). #7870, the shared foundation the re-land waits on, is still an open
  draft.
changed:
  - path: "agentos/handoffs/GMI-THEME-GRAPH-2026-09-27-robotics-reland-hold.md"
    what: "This record. Restores the operation's durable org memory after the revert removed its predecessor, updated to post-revert truth rather than re-adding a superseded document: the twelve architecture rulings, the corrected gate taxonomy (Gate C is a compound predicate - neither a bare exit code nor the script's own marker line), the re-land runbook with its two amendments, the cross-sector triage rule, the held lanes, and the reason MISSION_COMPLETE is not claimable. Documentation only - zero code paths, no partial re-land."
verified:
  - claim: "The operation's prior handoff is absent from main, and the revert #8013 is what removed it."
    command: "gh api repos/{o}/{r}/contents/agentos/handoffs/GMI-THEME-GRAPH-2026-09-24-robotics-implementation.md?ref=main >/dev/null 2>&1 (exit-code test, with agentos/README.md as positive control and a nonsense path as negative control); gh api repos/{o}/{r}/pulls/8013/files --paginate --jq 'select(.filename|test(\"agentos\"))'"
    result: "Subject ABSENT (non-zero exit); positive control PRESENT 11115B; negative control correctly absent. #8013's own file list carries `removed agentos/handoffs/GMI-THEME-GRAPH-2026-09-24-robotics-implementation.md`. Zero robotics handoffs among the 524 on main."
  - claim: "All 35 paths the revert removed are retrievable at the pre-revert commit and none has been re-added to main."
    command: "gh api repos/{o}/{r}/pulls/8013/files --paginate --jq '.[] | select(.status==\"removed\") | .filename' then, for each, gh api contents/<path>?ref=36efe9c92b96 and contents/<path>?ref=main by EXIT CODE"
    result: "35 removed paths; retrievable_at_36efe9c92b96=35, not_retrievable=0, present_on_main=0. Instrument positively controlled at the same ref. Read-only retrieval, so the no-split-re-land ruling is untouched."
  - claim: "The revert's sole parent is the pre-revert tree, so one commit id recovers the whole carrier."
    command: "gh pr view 7908 --json state,mergedAt,mergeCommit; gh api repos/{o}/{r}/commits/e5512ef66a74 --jq .parents"
    result: "#7908 MERGED 2026-09-25T07:27:34Z, mergeCommit 70b3c9f1f8f0. Revert e5512ef66a74 has exactly one parent, 36efe9c92b96, subject 'Revert \"Merge #7908: Robotics Theme Intelligence implementation carrier\" (#8013)'."
  - claim: "#7870 is caught up and textually mergeable; DRAFT status is the only remaining blocker, and it is the shell owner's call."
    command: "gh pr view 7870 --json state,isDraft,mergeable,mergeStateStatus,headRefOid,updatedAt"
    result: "state=OPEN draft=true mergeable=MERGEABLE mergeStateStatus=UNSTABLE head=a0d7b054ff23 (behind_by 0 when last compared). UNKNOWN mergeability means recomputing and is never a verdict - re-poll. An earlier record of this carrier as '323 behind' and CONFLICTING is superseded."
  - claim: "No single signal from the contracts script is a sound Gate C. A bare exit code is hollow without --strict, AND the script's own marker line is unreachable on a materialised store, so gating on either one is unsound in opposite directions."
    command: "gh api contents/scripts/check_theme_graph_contracts.py?ref=a0d7b054ff23 | base64 -d, then an ast.parse walk building a parent chain per notices.append/breaches.append call site, plus sed -n on the selftest; gh api contents/data/theme_graph/identity_resolution.parquet --jq .size at a0d7b054ff23 and main with a nonexistent sibling as negative control; gh api contents/docs/HOUSE_LAW_CI_GUARD_SUITE.md?ref=main | grep -n check_theme_graph_contracts"
    result: "87600B at this head. Line 1099 prints 'theme graph contracts OK ...' only when `not breaches` (1097) AND `not notices` (1098); 1101 returns 0; 1102 prints '::warning title=theme graph contract breach::'; 1109 returns `1 if strict else 0`; 1582 documents 'default is advisory rc 0'. The advisory default is DESIGNED: the house-law guard-suite row gives the reason (display-tier, must not take the collect lane down) and states '--strict is what CI runs', so CI's rc is load-bearing and only a local non-strict run is hollow - which is what this seat had been doing. The marker line is NOT the fix: the `[identity resolution census]` notice at 1044 is guarded only by `if idres is not None` (856) under `if idres_path.exists()` (850), with no content condition, and data/theme_graph/identity_resolution.parquet is committed (203378B at a0d7b054ff23, 204044B at main; negative control absent). So on any materialised store notices is non-empty, 1098 is False and the marker never prints, clean or not. The script's own selftest says so at 1229-1232 ('a designed, always-on notice ... printed every run, never an incident') and asserts it at 1334. Notices mix designed output with real incidents and must be triaged by printed class title. Confirmed empirically by the shell owner's own run on materialised data: 1168 identity_resolution rows violating the state-to-ids biconditional - a breach (960) - exit 0 anyway. Controls: 21 'def ' hits, 0 nonsense-token hits; the blobs at 1e38d5c955dc and a0d7b054ff23 are byte-identical, so reading both is ONE observation."
  - claim: "#7870's head carries a lazy-import refactor of the shared assertion module, and the Robotics-side fix that depends on it is unaffected."
    command: "gh api contents/engine/theme_graph/curation_assertion.py?ref=<head> --jq .size at 1e38d5c955dc and a0d7b054ff23; direct file diff of the three dependency files across heads"
    result: "27838B -> 28610B. Module-level `import jsonschema` plus an eager Draft202012Validator became a `_validator()` accessor with a deferred import, because the module sits in the shared app.main import closure and a hard import made an unprovisioned app import raise ModuleNotFoundError instead of degrading. Robotics symbols survive at shifted lines (_revision_of, validate_assertion, curation_revision_mismatch, source_ref_for); the dependent Robotics commit imports symbols, not line numbers, so it is unaffected. A `gh api compare/A...B` over this range is void for absence claims - it returned ahead_by 608 with commits capped at 250 AND files_listed capped at 300."
  - claim: "Robotics is neither DECLARED nor ENROLLED in the shared registry at #7870's head; only the semiconductor vertical is."
    command: "gh api contents/engine/market_ontology/theme_research_mounts.py?ref=a0d7b054ff23 | base64 -d | grep -n 'anchor_theme_id=\"'; same for theme_research_registry.py | grep -n '_MOUNTS\\['"
    result: "DECLARED: mounts.py:135 anchor_theme_id=\"ai_semiconductors\" - the only literal. ENROLLED: registry.py:169 _MOUNTS[\"ai_semiconductors\"] - the only enrolment. The registry's own line 172 is `anchor_theme_id=_SEMICONDUCTOR_MOUNT.anchor_theme_id`, an ATTRIBUTE reference, which is why an `anchor_theme_id=\"...\"` pattern finds nothing there and a naive grep reads as 'no anchors registered'. Track DECLARED and ENROLLED separately or the instrument lies."
  - claim: "Both Robotics modules are free of third-party imports entirely, not merely at top level; and each carries TWO first-party imports that execute at import time, one of which is wrapped in a module-level try and is therefore invisible to a column-anchored grep."
    command: "gh api contents/<path>?ref=36efe9c92b96 | base64 -d, then ast.parse and classify every Import/ImportFrom by whether its parent chain contains a FunctionDef/AsyncFunctionDef/ClassDef (deferred) or not (executes at import time), recording enclosing Try/If nodes; the column-anchored `grep -c '^from \\|^import '` reproduced as a control on the same bytes"
    result: "Re-measured 2026-09-27 by AST, correcting a 2026-09-26 undercount. Composer (60749B): import-time = 8 stdlib/__future__ plus TWO first-party - engine.theme_graph.curation_assertion at :45 AND engine.market_ontology.semiconductor_theme_research at :123 inside a module-level try at :122; deferred = engine.theme_graph.identity at :68. Owner bundle (12407B): import-time = 3 stdlib plus TWO first-party - engine.market_ontology.robotics_theme_research at :156 AND engine.market_ontology.theme_research_binding at :162 inside a module-level try at :161; deferred = engine.theme_graph.rights at :197 'lazy by design'. THIRD-PARTY anywhere in either file, deferred sites included: zero. The earlier entry reported ONE first-party import per file because its instrument was `grep -c '^from \\|^import '`, which anchors at column 0 and cannot see an indented import inside a top-level try; reproduced on the same bytes it still returns 9 and 4, the exact figures that were published. A try/except does not exempt an import from the repo's static sweep, and BOTH missed sites are named in #8013's own body among the four absences that broke main. Fixing the awk-stops-at-^def blind spot while keeping the column-0 blind spot is why a positive control proves only that a scan found something, never that it found everything."
  - claim: "The two outbound executive-contract comments on this operation carry their intended content, not a file path."
    command: "gh api repos/{o}/{r}/issues/comments/<id> then compare in-process: json.load(...)['body'] == open(src, encoding='utf-8').read()"
    result: "5852920768 (2877B) and 5853205639 (3235B), both on #7780, both byte-identical to source, trailing newline included. Both were first posted with the body `@/private/tmp/...` because `gh api -f body=@file` sends a static string - file reading is -F, or build JSON and pipe to --input -. An earlier note of a '1-byte trailing-newline delta' was a command-substitution artifact; there is no delta."
unverified:
  - claim: "The re-land of the 35 reverted paths will pass its gates against a main that has #7870 merged."
    what_would_verify: "After #7870 merges: cherry-pick or re-apply 36efe9c92b96's Robotics paths onto real main, then gates A/B/C/D green on that tree with Gate C proven by the compound predicate in DEC:THEME-GRAPH-CONTRACTS-GATE-IS-A-COMPOUND-PREDICATE on materialised data, plus an in-flight CI result on the carrier PR rather than a local proof."
  - claim: "The shared owner's Q1 can be satisfied by the R1 corpus."
    what_would_verify: "Their own adjudication. Measured fact they need: all 21 R1 fixtures are `synthetic: true` (every one checked 2026-09-26), so if Q1 requires real retained evidence the re-land will never deliver it - that is the held R5 lane, not the re-land."
  - claim: "The gate A / B / D counts quoted in this record (136, 623, and 20 passed with 116 xfailed) still hold."
    what_would_verify: "A run on the re-landed tree. These are the pre-revert local figures from the #7908 build, carried here as the target to re-establish; no command in this record measures them, and the reverted code is not on main to re-measure. Treat them as the expected shape, not as a verified result."
  - claim: "Any Robotics live path exists."
    what_would_verify: "R4 nonce proof by the store owner, real assertions admitted through the shared admission path into the private key space, entitled API returning them, anonymous negative, deployed browser proof. None of this is built."
unresolved:
  - "BLOCKER (owner's call, not this seat's): #7870 is OPEN, MERGEABLE, mergeStateStatus UNSTABLE, and DRAFT. Draft status is the only thing left blocking it. The Robotics re-land is sequenced entirely behind it. The draft/blocking-dependency topic is already well covered on that thread, including a receipt and its own correction, so re-raising it would spend the owner's attention on what their merge box already shows."
  - "STANDING JOINT OBLIGATION (v1.1): object.subject_role in {acquirer, seller, party} plus a JOINT DEFINITION_VERSION bump, owed with #7870's owner. Confirmed live and unbuilt on both sides - V1_1 is PROPOSED_NOT_BUILT and the registry still imports the unbumped _SEMICONDUCTOR_DEFINITION_VERSION. Shared-contract compatibility is a principal decision, not a lane decision."
  - "RULED, no split re-land (ruling 10): the carrier re-lands whole, behind #7870, or not at all. Read-only retrieval of the reverted paths for measurement does not violate this; adding any subset of them to main does."
  - "RULED, registration is POST-MERGE (ruling 6): the shared registry imports a vertical's composer eagerly at registry-import time, so the Robotics registry entry cannot land before the carrier's modules are on main. Corroborated by four independent sources including the shell owner's own statement that the registry resolves to ['ai_semiconductors']."
  - "RULED, merge is not acceptance (ruling 7): a green main is not acceptance either. This is why MISSION_COMPLETE is not claimable on a merge, and why the completion criterion is the real-path law in the master packet section 3."
  - "RULED, retention is by design (ruling 11): RBV-18 is a designed retention contract, not a defect. The design-vs-defect test that settled it: is there a contract statement (docstring or comment) AND a pin whose name states it? Contract plus pin = design. Neither = defect."
  - "CONFIRMED DEFECT (ruling 12): the cross-scope _correction_lineage walk. Distinct from ruling 11 by the same test - no contract statement, no pin."
  - "RULED, the Robotics mount partial is RETIRED (ruling 5); scope.canonical_theme_id carries theme:<slug> (ruling 8); ruling 9 is VOID and any law derived from it is withdrawn."
  - "NOT THIS OPERATION'S WORK - three sector dependency clarifications adjudicated out of scope (Materials #7773 comment 5809093547, Communications #7870 comment 5846455819, Semiconductor B to Communications #7870 comment 5852703250), each addressed to the shared owner with no receiver assigned. 5852703250 is authored by the same GitHub login this seat writes under, which is shared across operations on this account - Semiconductor B is a different operation, so common authorship is not common ownership. Reusable triage rule so a successor need not re-adjudicate: not mine when (a) the addressee is the shared or incumbent owner or another sector's operation, (b) it names no Robotics coordinate - Robotics is a canonical THEME with slice_keys, while sector dossiers, rosters and issuer sets are a different coordinate, and (c) any fact this lane could contribute is already on that thread from its owner."
  - "OPEN OFFER, no reply: the #8011 seat owns the CI baseline. No word received."
next_actions:
  - "WAIT on #7870. Do not re-land, do not split, do not register. Two watchers are the attention path; they are session-local and die with the session, so a successor re-arms rather than inherits."
  - "WHEN #7870 MERGES: re-land the 35 paths whole from 36efe9c92b96 onto real main, in one carrier. Then gates A (136) / B (623) / C (the compound predicate) / D (20 passed, 116 xfailed), with A, B and D re-established rather than assumed - see unverified. The Gate C step MUST pass --strict on a materialised data/ and require all three of: exit 0; no '::warning title=theme graph contract breach::' line in stdout; and every '::notice title=theme graph - <class>::' enumerated and triaged, where 'identity resolution census' and 'licensing snapshots - designed' are designed and non-blocking while 'theme graph indeterminate', either 'side-car MISSING - half-finished build' and 'capability promoted itself' block. Do NOT gate on the literal 'theme graph contracts OK': the committed identity-resolution sidecar makes that line unreachable on any materialised store, clean or not. Unmaterialised data/ is INDETERMINATE, never pass."
  - "THEN, as a separate post-merge additive commit: the Robotics registry entry. It MUST use the lazy loader wrapper pattern (a module-level function that defers `from engine.market_ontology.robotics_owner_bundle import ...` inside its body, with a noqa PLC0415 and a stated reason), never a top-level import - the registry sits in the shared app.main import closure and the shell owner already took 4-of-7 pack failures from exactly one hard top-level import there. The composer must also stay third-party-free at top level, because the registry imports it eagerly."
  - "Before any substantive reciprocal write: fresh-read the exact bound carrier in the same turn, and include an abort guard comparing the latest comment id. Class-M default interval is 60 minutes, hard floor 15."
  - "DONE in this same change: the two highest-consequence ruling clusters are now DEC records - DEC:GMI-ROBOTICS-RELAND-ORDERING-AND-REGISTRATION (rulings 5, 6, 7, 10 plus the lazy-wrapper requirement) and DEC:THEME-GRAPH-CONTRACTS-GATE-IS-A-COMPOUND-PREDICATE (the withdrawn exit-code gate, and why the script's own success line is not its replacement). The convention in this program is one DEC per coherent cluster, not one per ruling, following DEC:IND-FIRST-VERTICAL-CARRIER-AND-ORDERING. Rulings 8, 11 and 12 remain prose in this record; ruling 9 is void and needs none. Promote 11 and 12 together if a later lane re-opens the design-versus-defect question, since the test that separates them is the reusable part."
  - "Held lanes, in dependency order once the re-land clears: R5 real evidence qualification through the shared admission and private adapter (also the likely content of the shared owner's Q1); R5 rights seam; R6 remaining halves (registration post-merge, served API is the shell owner's file); live admission; browser and production acceptance."
do_not_redo:
  - "The 35 reverted paths are NOT lost and do NOT need rebuilding. Every one is retrievable at 36efe9c92b96, verified by exit-code test with a positive control. Re-authoring any of them is duplicated work."
  - "Do not re-adjudicate the three sector dependency clarifications listed in unresolved - the triage rule there settles them."
  - "Do not re-measure the R1 corpus for synthetic status: all 21 fixtures are synthetic: true, every one checked. tests/robotics_research_helpers.py states the contract and refuses any value whose synthetic flag is not explicitly True."
  - "Do not rebuild the source-rights qualification matrix. research/theme_graph/thematic_research_20260924/ROBOTICS_SOURCE_RIGHTS_QUALIFICATION_2026-09-24.md (56508B) exists at 36efe9c92b96: one row per publisher host by source class, terms actually inspected with timestamps, READ versus INFERRED per clause, a minimum positive witness, refusal behaviour, and gaps G1/G2/G4."
  - "Do not create another Theme Graph, a global Robotics product master, another evidence or correction system, another identity system, another private publication plane, another scheduler, queue or watcher, or another theme-detail dashboard. Do not create /api/themes/v1/robotics as a parallel route without an explicit architecture ruling. Do not create a Robotics-specific database, bucket, private store, publisher, evidence ledger or scheduler."
  - "Do not edit #7870, #7462 or #7669 paths from a Robotics carrier WHILE THOSE CARRIERS ARE IN FLIGHT. This stops applying to a given path the moment that carrier's modules are on main: the post-merge registry entry in next_actions edits theme_research_registry.py, which is a #7870 path today and a main path afterwards."
  - "Do not alter Robotics basket membership or weights, ThemeState, Theme Tracker recommendation/lane/stage, Prophet or member ranking, entry gates, sizing, alerts, or trading. Research coverage carries zero automatic decision authority."
danger_areas:
  - "A local gate proof is never a substitute for an in-flight CI result - it is what tempts you not to wait for one. This operation's revert exists because a carrier was merged 2m22s after the correct CI run started against the correct base (run created 07:25:12Z, merge 07:27:34Z), and that run went red only AFTERWARDS - the first failure 9m47s post-merge and the import defect 27m35s post-merge, on a pack that had passed at the previous head. The window is not four minutes; it is long enough that waiting feels unreasonable, which is the whole trap. Check `gh pr checks` for anything PENDING, not merely for anything red."
  - "Importable is not served. A static import guard, a linter, a collection sweep and a coverage run all touch files nothing serves, so 'nothing uses it at runtime' is not 'nothing reads it'."
  - "Testimony is not observation, including an API's testimony about your own write. `gh api -f body=@file` posts the literal path (-f is a static string; file reading is -F, or build JSON and pipe to --input -), returns a normal id and exits 0. Read every outbound write back and compare in-process; keep the shell out of the comparison, because command substitution strips trailing newlines and jq appends one, and both manufacture phantom deltas on correct content."
  - "GitHub instruments under-report SILENTLY, so every absence claim from them needs a positive control: trees truncate, `gh pr diff --name-only` 406s over 300 files, `gh api compare` caps at 250 commits AND 300 files, issue comments paginate to page 1 only, and `gh api` prints a 404 body to STDOUT so presence must be tested by EXIT CODE. `?since=` on issue comments filters on updated_at, so it catches EDITS that a comment-id high-water mark misses, and a re-emitted id is correct behaviour rather than a duplicate bug."
  - "Full-fidelity real Robotics assertion bodies must never enter a public carrier, evidence.parquet, site/ or public R2. The repo is public; fixtures stay synthetic with example.invalid or already-public vendor pages."
  - "Builder is not reviewer, and this is mandatory. In-flight worker returns are not truth until reviewed and integrated."
prs: [7773, 7780, 7870, 7908, 8013]
decisions:
  - "DEC:GMI-ROBOTICS-RELAND-ORDERING-AND-REGISTRATION"
  - "DEC:THEME-GRAPH-CONTRACTS-GATE-IS-A-COMPOUND-PREDICATE"
---

# GMI Robotics - re-land hold, post-revert (2026-09-27)

This record exists because the revert that correctly removed this operation's *code* from main
also removed its *knowledge record*. A revert aimed at an import blocker is not a decision to
forget why the work existed, what was ruled, or what a successor must not redo. Nothing here
restores code.

## Where the operation actually stands

Implementation carrier #7908 merged and was reverted the same day. The cause was narrow and is
fully understood: modules living only in the unmerged #7870 became unresolvable first-party
imports on a main that does not have them, and the repo's static import sweep is not softened by
a try/except, because its own guard synthesises a try-wrapped import specifically to catch that.
The heal was a plain revert of the merge commit. The re-land waits on #7870 and nothing else.

The shared foundation #7870 has moved for the first time in this hold: its head went
6cd958e92b2 to 1e38d5c955dc to a0d7b054ff23, and its state went CONFLICTING to MERGEABLE with
behind_by 0. Draft status is now the only blocker, and that is its owner's decision.

## The twelve rulings, by number

Rulings 1 to 4 are carried in the packet and the predecessor record. The ones a successor is
most likely to trip over:

- **5** - the Robotics mount partial is RETIRED. Robotics mounts by REGISTERING in the shared
  shell, not by shipping its own partial.
- **6** - mount registration is POST-MERGE, because the shared registry imports a vertical's
  composer eagerly at registry-import time. Corroborated four independent ways.
- **7** - merge is not acceptance, and a green main is not acceptance.
- **8** - scope.canonical_theme_id carries `theme:<slug>`.
- **9** - VOID. Any law derived from it is withdrawn.
- **10** - no split re-land.
- **11** - RBV-18 retention is a designed contract, not a defect.
- **12** - the cross-scope `_correction_lineage` walk is a CONFIRMED defect.

Rulings 11 and 12 look like the same shape and resolve opposite ways. The test that separates
them: is there a contract statement in a docstring or comment, AND a pin whose *name* states the
behaviour? Contract plus pin is design. Neither is a defect.

## Gate taxonomy, with Gate C corrected

Gate A is 136, Gate B is 623, Gate D is 20 passed and 116 xfailed - those three are the
pre-revert local figures to re-establish, not results this record verifies. **Gate C was hollow
and the earlier definition is WITHDRAWN.** It was recorded as `check_theme_graph_contracts.py`
exiting 0, and that script returns 0 on a real breach unless `--strict` is passed. The shell
owner's run confirmed it empirically: 1168 biconditional violations, exit 0.

The first replacement written here was also wrong, and an independent audit caught it before it
landed. Gating on the script's own success line looks airtight - it prints on exactly one path -
but that path requires `notices` to be empty too, and the identity-resolution census at line 1044
is an unconditional notice whenever `data/theme_graph/identity_resolution.parquet` merely exists.
That file is committed. So the success line never prints on a materialised store, clean or not,
and a gate built on it is permanently red and indistinguishable from a real breach. So:

> Gate C := `--strict`, on a materialised `data/`, AND exit 0 AND no
> `::warning title=theme graph contract breach::` line AND every
> `::notice title=theme graph - <class>::` enumerated and triaged by class.

Designed and non-blocking: `identity resolution census`, `licensing snapshots - designed`.
Blocking: `theme graph indeterminate` (store incomplete), either
`side-car MISSING - half-finished build`, `capability promoted itself`. The script's own comment
at 1090 states why the titles differ - so a designed notice cannot visually mask a half-finished
build - which is what makes triage by title sound. Unmaterialised `data/` is INDETERMINATE.

One correction to the framing that earlier drafts of this gate carried: the advisory exit code is
DESIGNED, and documented. The house-law guard-suite row explains it (display-tier, a breach must
not take the nightly collect lane down) and records that `--strict` is what CI runs. So CI's exit
code was never the hollow one. The hollow gate was this seat's own local non-strict run.

## DECLARED versus ENROLLED

Ruling 6 turns on a distinction that is easy to measure wrongly.
`theme_research_mounts.py` **declares** a mount with a literal
`anchor_theme_id="<id>"`. `theme_research_registry.py` **enrols** it with
`_MOUNTS["<id>"]`, and its own `anchor_theme_id=` line is an attribute reference, not a literal.
A grep for the literal pattern therefore returns nothing against the registry and reads exactly
like "no anchors are registered." Track the two sites separately, and control the instrument with
a positive, a negative and a teeth case before believing any answer it gives.

## Why MISSION_COMPLETE is not claimable

Ruling 7. The completion criterion is the real-path law in the master packet section 3: a
fixture-green composer, a 200 from the shared API, or a rendered shell is not the vertical. A
merge of the re-land would not be acceptance either. The target classification is
PROVEN_OUTCOME, and the honest current classification is BLOCKED, with the block outside this
seat's authority to clear.
