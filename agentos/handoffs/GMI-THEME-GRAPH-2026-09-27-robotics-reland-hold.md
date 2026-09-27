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
    what: "This record. Restores the operation's durable org memory after the revert removed its predecessor, updated to post-revert truth rather than re-adding a superseded document: the twelve architecture rulings, the corrected gate taxonomy (Gate C is a marker line, not an exit code), the re-land runbook with its two amendments, the cross-sector triage rule, the held lanes, and the reason MISSION_COMPLETE is not claimable. Documentation only - zero code paths, no partial re-land."
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
  - claim: "Gate C cannot be an exit code: the contracts script returns 0 on a breach unless --strict, and returns 0 with notices while suppressing its own OK line. The marker line is the only proof."
    command: "gh api contents/scripts/check_theme_graph_contracts.py?ref=a0d7b054ff23 | base64 -d then grep -n 'theme graph contracts OK' and grep -n 'return 1 if strict'"
    result: "87600B at this head. Line 1099 prints 'theme graph contracts OK ...' only when `not breaches` (1097) AND `not notices` (1098); line 1101 returns 0; line 1109 returns `1 if strict else 0`; line 1582 documents 'default is advisory rc 0'. Confirmed empirically by the shell owner's own run on materialised data: 1168 identity_resolution rows violating the state-to-ids biconditional, exit 0 anyway. Controls: 21 'def ' hits, 0 nonsense-token hits."
  - claim: "#7870's head carries a lazy-import refactor of the shared assertion module, and the Robotics-side fix that depends on it is unaffected."
    command: "gh api contents/engine/theme_graph/curation_assertion.py?ref=<head> --jq .size at 1e38d5c955dc and a0d7b054ff23; direct file diff of the three dependency files across heads"
    result: "27838B -> 28610B. Module-level `import jsonschema` plus an eager Draft202012Validator became a `_validator()` accessor with a deferred import, because the module sits in the shared app.main import closure and a hard import made an unprovisioned app import raise ModuleNotFoundError instead of degrading. Robotics symbols survive at shifted lines (_revision_of, validate_assertion, curation_revision_mismatch, source_ref_for); the dependent Robotics commit imports symbols, not line numbers, so it is unaffected. A `gh api compare/A...B` over this range is void for absence claims - it returned ahead_by 608 with commits capped at 250 AND files_listed capped at 300."
  - claim: "Robotics is neither DECLARED nor ENROLLED in the shared registry at #7870's head; only the semiconductor vertical is."
    command: "gh api contents/engine/market_ontology/theme_research_mounts.py?ref=a0d7b054ff23 | base64 -d | grep -n 'anchor_theme_id=\"'; same for theme_research_registry.py | grep -n '_MOUNTS\\['"
    result: "DECLARED: mounts.py:135 anchor_theme_id=\"ai_semiconductors\" - the only literal. ENROLLED: registry.py:169 _MOUNTS[\"ai_semiconductors\"] - the only enrolment. The registry's own line 172 is `anchor_theme_id=_SEMICONDUCTOR_MOUNT.anchor_theme_id`, an ATTRIBUTE reference, which is why an `anchor_theme_id=\"...\"` pattern finds nothing there and a naive grep reads as 'no anchors registered'. Track DECLARED and ENROLLED separately or the instrument lies."
  - claim: "Both Robotics modules are free of third-party top-level imports, which is a hard requirement for the post-merge registration commit."
    command: "sed -n on the import blocks of engine/market_ontology/robotics_theme_research.py and robotics_owner_bundle.py at 36efe9c92b96, with a grep -c positive control"
    result: "Measured 2026-09-26. Composer (60749B): stdlib copy/hashlib/json/math/dataclasses/datetime/typing plus ONE first-party import at :45 from engine.theme_graph.curation_assertion. Zero third-party. Owner bundle (12407B): __future__ :147, collections.abc :149, typing :150, robotics_theme_research :156; engine.theme_graph.rights deferred at :197 'lazy by design'. Zero third-party. An awk scan that stops at the first ^def|^class reported ZERO imports for the bundle - defeated by a 145-line docstring containing a line starting with def; the grep -c control returned 4."
  - claim: "The two outbound executive-contract comments on this operation carry their intended content, not a file path."
    command: "gh api repos/{o}/{r}/issues/comments/<id> then compare in-process: json.load(...)['body'] == open(src, encoding='utf-8').read()"
    result: "5852920768 (2877B) and 5853205639 (3235B) both byte-identical to source, trailing newline included. Both were first posted with the body `@/private/tmp/...` because `gh api -f body=@file` sends a static string - file reading is -F, or build JSON and pipe to --input -. An earlier note of a '1-byte trailing-newline delta' was a command-substitution artifact; there is no delta."
unverified:
  - claim: "The re-land of the 35 reverted paths will pass its gates against a main that has #7870 merged."
    what_would_verify: "After #7870 merges: cherry-pick or re-apply 36efe9c92b96's Robotics paths onto real main, then gates A/B/C/D green on that tree with Gate C proven by its marker line on materialised data, plus an in-flight CI result on the carrier PR rather than a local proof."
  - claim: "The shared owner's Q1 can be satisfied by the R1 corpus."
    what_would_verify: "Their own adjudication. Measured fact they need: all 21 R1 fixtures are `synthetic: true` (every one checked 2026-09-26), so if Q1 requires real retained evidence the re-land will never deliver it - that is the held R5 lane, not the re-land."
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
  - "NOT THIS OPERATION'S WORK - three sector dependency clarifications adjudicated out of scope (Materials 5809093547, Communications 5846455819, Semiconductor B to Communications 5852703250), each addressed to the shared owner with no receiver assigned. Reusable triage rule so a successor need not re-adjudicate: not mine when (a) the addressee is the shared or incumbent owner or another sector's operation, (b) it names no Robotics coordinate - Robotics is a canonical THEME with slice_keys, while sector dossiers, rosters and issuer sets are a different coordinate, and (c) any fact this lane could contribute is already on that thread from its owner."
  - "OPEN OFFER, no reply: the #8011 seat owns the CI baseline. No word received."
next_actions:
  - "WAIT on #7870. Do not re-land, do not split, do not register. Two watchers are the attention path; they are session-local and die with the session, so a successor re-arms rather than inherits."
  - "WHEN #7870 MERGES: re-land the 35 paths whole from 36efe9c92b96 onto real main, in one carrier. Then gates A (136) / B (623) / C (marker line) / D (20 passed, 116 xfailed). Gate C step MUST assert stdout contains the literal 'theme graph contracts OK' - exit 0 proves nothing in either direction - and data/ must be materialised or the honest verdict is INDETERMINATE. Adding --strict is worthwhile so a breach is also non-zero, but --strict plus rc 0 still does not clear notices."
  - "THEN, as a separate post-merge additive commit: the Robotics registry entry. It MUST use the lazy loader wrapper pattern (a module-level function that defers `from engine.market_ontology.robotics_owner_bundle import ...` inside its body, with a noqa PLC0415 and a stated reason), never a top-level import - the registry sits in the shared app.main import closure and the shell owner already took 4-of-7 pack failures from exactly one hard top-level import there. The composer must also stay third-party-free at top level, because the registry imports it eagerly."
  - "Before any substantive reciprocal write: fresh-read the exact bound carrier in the same turn, and include an abort guard comparing the latest comment id. Class-M default interval is 60 minutes, hard floor 15."
  - "Convert the twelve rulings into durable DEC records under agentos/decisions/, one per ruling with its falsifier, rather than leaving them as prose in a handoff. This record closes the immediate hazard; the DEC records are the proper home."
  - "Held lanes, in dependency order once the re-land clears: R5 real evidence qualification through the shared admission and private adapter (also the likely content of the shared owner's Q1); R5 rights seam; R6 remaining halves (registration post-merge, served API is the shell owner's file); live admission; browser and production acceptance."
do_not_redo:
  - "The 35 reverted paths are NOT lost and do NOT need rebuilding. Every one is retrievable at 36efe9c92b96, verified by exit-code test with a positive control. Re-authoring any of them is duplicated work."
  - "Do not re-adjudicate the three sector dependency clarifications listed in unresolved - the triage rule there settles them."
  - "Do not re-measure the R1 corpus for synthetic status: all 21 fixtures are synthetic: true, every one checked. tests/robotics_research_helpers.py states the contract and refuses any value whose synthetic flag is not explicitly True."
  - "Do not rebuild the source-rights qualification matrix. research/theme_graph/thematic_research_20260924/ROBOTICS_SOURCE_RIGHTS_QUALIFICATION_2026-09-24.md (56508B) exists at 36efe9c92b96: one row per publisher host by source class, terms actually inspected with timestamps, READ versus INFERRED per clause, a minimum positive witness, refusal behaviour, and gaps G1/G2/G4."
  - "Do not create another Theme Graph, a global Robotics product master, another evidence or correction system, another identity system, another private publication plane, another scheduler, queue or watcher, or another theme-detail dashboard. Do not create /api/themes/v1/robotics as a parallel route without an explicit architecture ruling. Do not create a Robotics-specific database, bucket, private store, publisher, evidence ledger or scheduler."
  - "Do not edit #7870, #7462 or #7669 paths from a Robotics carrier."
  - "Do not alter Robotics basket membership or weights, ThemeState, Theme Tracker recommendation/lane/stage, Prophet or member ranking, entry gates, sizing, alerts, or trading. Research coverage carries zero automatic decision authority."
danger_areas:
  - "A local gate proof is never a substitute for an in-flight CI result - it is what tempts you not to wait for one. This operation's revert exists because a carrier was merged 2m22s after the correct CI run started against the correct base, and that run failed four minutes later on exactly the defect. Check `gh pr checks` for anything PENDING, not merely for anything red."
  - "Importable is not served. A static import guard, a linter, a collection sweep and a coverage run all touch files nothing serves, so 'nothing uses it at runtime' is not 'nothing reads it'."
  - "Testimony is not observation, including an API's testimony about your own write. `gh api -f body=@file` posts the literal path (-f is a static string; file reading is -F, or build JSON and pipe to --input -), returns a normal id and exits 0. Read every outbound write back and compare in-process; keep the shell out of the comparison, because command substitution strips trailing newlines and jq appends one, and both manufacture phantom deltas on correct content."
  - "GitHub instruments under-report SILENTLY, so every absence claim from them needs a positive control: trees truncate, `gh pr diff --name-only` 406s over 300 files, `gh api compare` caps at 250 commits AND 300 files, issue comments paginate to page 1 only, and `gh api` prints a 404 body to STDOUT so presence must be tested by EXIT CODE. `?since=` on issue comments filters on updated_at, so it catches EDITS that a comment-id high-water mark misses, and a re-emitted id is correct behaviour rather than a duplicate bug."
  - "Full-fidelity real Robotics assertion bodies must never enter a public carrier, evidence.parquet, site/ or public R2. The repo is public; fixtures stay synthetic with example.invalid or already-public vendor pages."
  - "Builder is not reviewer, and this is mandatory. In-flight worker returns are not truth until reviewed and integrated."
prs: [7773, 7870, 7908, 8013]
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

Gate A is 136, Gate B is 623, Gate D is 20 passed and 116 xfailed. **Gate C was hollow and the
earlier definition is WITHDRAWN.** It was recorded as `check_theme_graph_contracts.py` exiting 0.
That script returns 0 on a real breach unless `--strict` is passed, and returns 0 when breaches
are empty but notices are not - in which case it also suppresses its own success line. So:

> Gate C := stdout contains the literal `theme graph contracts OK`.

Adding `--strict` is still worth doing so a breach is also non-zero, but `--strict` plus rc 0 is
not sufficient, because it clears breaches and says nothing about notices. If `data/` is not
materialised the honest verdict is INDETERMINATE, not pass. Two independent holes were found in
this gate; the stronger one was this seat's own, and the shell owner's run later confirmed it
empirically - 1168 biconditional violations, exit 0.

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
