---
workstream: WS:MARKET-OS
session: |
  harness session d640f3ef-1305-4b6c-aa5d-2d6d5e3dc515 (Claude 5 runtime, Fable), holder of the
  Meta-CEO B seat since 2026-09-08 21:1xZ; bound on macro#6819 with issuecomment-5592587864 (the
  ACK issuecomment-5557271957 and the Wave 1 comment issuecomment-5577816742 are never repeated).
  The Wave 2 comment on macro#6819 is issuecomment-5626381233 and the Wave 3 comment is
  issuecomment-5630979484 (posted 2026-09-11 07:3xZ, naming the Wave 3 record that merged as
  ca1b51ac); neither is ever repeated. This wave's single Wave 4 comment on macro#6819 is posted
  by the seat when this record merges and its id is pasted into this field then; it is never
  repeated either.
model: fable
ended_because: complete
mission: >
  Wave 4 checkpoint for Meta-CEO B (Chairman override of 2026-09-05/06; charter
  research/MARKET_ONTOLOGY_META_CEO_CHARTER_2026_09_06.md). Half B is F06 F07 F08 F09 F11 F12
  F13 plus the Supabase migration namespace, the identity/tenant contracts and the A-spare
  packets. This record covers 2026-09-11 07:15Z to 12:19Z - the hardening, hygiene and
  plain-language tail of the settings-and-teams cascade landing on Terminal master, the two reds
  that had to be attributed before anything could move, the laws the wave minted about launching
  and waiting, and the state of every open half-B pull request at the boundary. It is written so
  a cold successor on any account can resume from GitHub plus this file plus the durable kit.
state_before: >
  The Wave 3 record (agentos/handoffs/MARKET-ONTOLOGY-META-CEO-B-2026-09-11.md) closed at
  2026-09-11 07:15Z one minute after Terminal #568, the applied flip for migrations 0019 to 0021,
  merged as 2b7d3485. At that boundary Terminal master carried the whole settings-and-teams
  cascade, the three migrations were applied in production and the ledger was flipped, and two
  ratified carriers were still open: #567, the hover hardening, behind master, and #569, the
  evidence guard that deepens its fetch, dirty against master. On macro nothing of this seat's
  had merged: #7032 was armed and approved with its packs churning behind a three-runner pool,
  #6920 was armed, and the Wave 3 record itself was about to be opened as #7071. The operating
  split set by the Chairman at 22:16Z on 2026-09-10 was in force: Fable keeps rulings,
  ratifications, merges, production DDL and records, and every mechanical step goes to a one-shot
  Opus orchestrator with a full brief.
changed:
  - path: agentos/handoffs/MARKET-ONTOLOGY-META-CEO-B-2026-09-11T12.md
    what: "This Wave 4 checkpoint record, the second record of 2026-09-11 and so carrying the hour suffix. Records only; no source or product effect."
verified:
  - claim: "Six Terminal pull requests merged in this window, each on its own green at a head the seat had ratified: #567 0245e920 at 07:56:25Z, #569 525157b1 at 08:46:54Z, #570 908540b7 at 09:30:59Z, #571 bb7df1ca at 10:14:09Z, #572 d812eba5 at 11:16:28Z and #573 a4be9a3f at 12:08Z."
    command: "the Terminal sweep and armed watchers reported every merge; terminal_reviews/_post_merge.sh <pr> then read the merge commit and the served build"
    result: "Master moved 2b7d3485 to 0245e920 to 525157b1 to 908540b7 to bb7df1ca to d812eba5 to a4be9a3f. Heads merged: #567 at the merge-only refresh 03e6baee, #569 at the bot-made refresh 578ceb79, #570 at 656924ed, #571 at the merge-only refresh 27956bc5, #572 at d382df9a and #573 at f9eac720. Ratification of record: #571 issuecomment-5632423854 at 8fa81b50, #573 issuecomment-5633800099 at f9eac720, #570 issuecomment-5632166255 at 656924ed. #567 and #569 were ratified in Wave 3 and their ratifications were extended by the merge-only law."
  - claim: "Every merge in this window was proved live: the served build identifier equals the merge commit each time, and the counter of consecutive on-master deploys reached fifteen."
    command: "terminal_reviews/_post_merge.sh <pr>, which builds on the box and reads the served build identifier"
    result: "Seven deploy proofs ran inside the window - 2b7d3485 for #568 at 07:22Z closing the Wave 3 chain, then 0245e920, 525157b1, 908540b7, bb7df1ca, d812eba5 and a4be9a3f, the ninth through the fifteenth consecutive on-master deploy. No deploy lag was seen on any of them and no build had to be re-run."
  - claim: "#571's only red belonged to #571, and the fix was proved red before it was proved green."
    command: "read the failing unit job 103212658983 at head 2488b05d, then reproduce and fix in the lane worktree with single-worker vitest"
    result: "The b-f12-7 webhooks evidence packet counts the files its discovery pattern finds and pins the count at fifteen; #571's new ledger-contract suite is named so that the pattern finds it, so the true count became sixteen. The earlier head's run had been cancelled by the amendment push, so the red was seen only at 2488b05d. The seat ruled the count guard moves with a truthful comment and never a rename to dodge the pattern; the fix 2488b05d to 8fa81b50 touched one file, reproduced the red first, then passed four files and twenty-eight tests, with the type check clean. The file is not a pinned row in that packet, so no hash moved and no crop was recaptured."
  - claim: "macro #7032's pack-8 red was not caused by #7032: the same test fails on the pack's own base commit with no part of the change present."
    command: "git archive of master b958ef17 into a scratch directory, then python3 -m pytest tests/test_macro_monetary_hub.py -q -p no:cacheprovider there; the commissioning checkout was never mutated"
    result: "Identical failure and identical shape at the base, one failed and twenty-one passed. The mechanism is a window bug in the test: the template puts the class the test asserts on the line before the workspace marker the test slices from, so the slice structurally excludes the class. It has been latent since #6873 and was flipped red by the daily regime data; bisecting the data against unchanged code pinned the flip to the 2026-09-09 update, not the 09-10 one. The heal is one test file, six lines added and one removed, folded into #7032 as a second heal at 7caf9505: red first with one failed and twenty-one passed, then one hundred and twelve passed over the two named files."
  - claim: "The plain-language sweep converted every customer-facing string of the formal second-person form on Terminal master and left the house-style guards intact."
    command: "re-run of the inventory at branch time, then the named tests and the full Terminal vitest suite in the lane worktree, plus next typegen and tsc --noEmit"
    result: "Twenty-five occurrences over twenty-three lines in five sources became 你: the shared translation table, the shared-workflow library, the teams library, one forecast component and one invitations route. The re-run found forty-five lines rather than the twenty-nine the spec catalogued; the extra ones are ten guard test files whose only use of the old form is a negative assertion or a title, so converting them would have inverted the repository's only standing tripwire. They were left alone under the seat's ruling. Six evidence rows were restamped hash-only with header disclosures and no crop was recaptured, because no captured surface renders a converted key. Twenty-one named files gave four hundred and sixty-five passed; the full suite gave three hundred and twenty-four files and five thousand three hundred and eighty-two passed with four to do; the type check was clean."
  - claim: "The account-completeness crops now pin the rail that frames them and depict the rail master actually renders."
    command: "Terminal #570 in a lane worktree at master 525157b1: add the panel and provider pins to the capture script and the evidence test, recapture the eight crops, then the packet test single-worker, tsc --noEmit and the full-tree lock screen"
    result: "The crops had been captured when the settings rail had seven rows and master renders eleven; the packet pinned no file that changes when the rail gains a row, so nothing ever fired. The pins are in and the eight crops were recaptured at 525157b1 with the eleven-row rail. Packet test five passed, type check clean, lock screen zero asserted problems. Merged as 908540b7."
  - claim: "The ownership-transfer evidence pointer is healthy on master and the freshness law is closed for it."
    command: "read-only worktree at master a4be9a3f: read both pointer lines in the packet's evidence file, git merge-base --is-ancestor, the packet test single-worker, then the full-tree lock screen"
    result: "Both the header line and the data line name d812eba5, which is master's immediate parent and the squash of #572; the ancestor check exits clean; the packet test gives five passed; the lock screen reports twenty-four packets, zero problems and fourteen historical non-asserted rows. The pointer had been orphaned minutes earlier when #572 squashed, which the post-merge chain caught in the same run and repaired as #573."
  - claim: "Every refresh of an armed head in this window was proved merge-only before it was accepted, and every full-tree lock screen came back with nothing asserted stale."
    command: "md5 of the sorted plus and minus lines of the three-dot diff against master on both heads, equal file counts, git merge-base --is-ancestor; then the scratchpad lock screen over every packet"
    result: "#567 d8946ff6 to 03e6baee, one file, fact comment issuecomment-5630961665; #569 dcbd7fca to 578ceb79 after the merge bot refreshed it itself, one file, fact comment issuecomment-5631457301; #571 8fa81b50 to 27956bc5, fourteen files, fact comment issuecomment-5632560461. Zero asserted mismatches at every head screened; the same fourteen non-asserted historical rows in six packets appeared throughout and are now reported as one line per packet rather than as problems."
  - claim: "The Wave 3 record is on macro main."
    command: "the per-PR watcher on #7071 reported all checks concluded with no binding red; the seat then hand-merged by squash at the ratified head, never with an override"
    result: "#7071 was opened at 07:25Z, ratified at ac26a7cc with issuecomment-5630990312, sat with two packs queued from 07:34Z, concluded green at 12:18Z and was squashed at 12:19:10Z as ca1b51ac. The Wave 3 comment on macro#6819 is issuecomment-5630979484 and is never posted again."
  - claim: "No production DDL was applied in this wave and no ledger flip was owed by any of its merges."
    command: "the squash-law and ledger-flip checks in each post-merge chain: read the squash diff for migration files, reservation rows and pointer lines"
    result: "None of #567, #569, #570, #571, #572 or #573 carried a migration. #571 touched three migration files only to correct a one-line header comment each, with no change to any statement body, and moved two lines in the reservations file - a key order and a sentence that had become false - with no state, merge or applied value flipped. The chain 0014 through 0021 stays complete and applied; 0022 and 0023 stay on master and unapplied until the seat runs them in ledger order."
unverified:
  - claim: "macro #7032 concludes green on its restarted twelve-pack cycle and the seat hand-merges it at 7caf9505, after which the update-branch round turns the twelve pull requests behind it green."
    what_would_verify: "the per-PR watcher reporting all checks concluded with no binding red, the hand merge at the ratified head, then a refreshed head on each of the twelve with the suite-labels and hub reds gone."
  - claim: "macro #6920 merges at 8ad66422 and #7007 can then be refreshed onto main, re-checked over its thirteen files, marked ready and armed."
    what_would_verify: "the #6920 watcher reporting the merge, then a three-dot diff on #7007 against main showing the same thirteen files."
  - claim: "This record merges on its own green and the seat posts exactly one Wave 4 comment on macro#6819 naming it."
    what_would_verify: "the per-PR watcher on this record's pull request reporting all checks concluded, the hand merge at the ratified head, and the comment id pasted into this file's session field."
unresolved:
  - "macro #7032 carries two heals now and restarted its twelve packs at 11:49Z; nothing of this seat's has merged on macro all day except the Wave 3 record, and the three-runner pool is still the reason. The twelve pull requests waiting on the update-branch round are #7020, #7003, #6905, #6958, #6909, #7012, #7021, #7010, #7006, #7008, #7011 and #7014."
  - "macro #7008's pack-6 red is infrastructure, not code: every group passed and then the runner received a shutdown signal. It rides the post-#7032 refresh round and is not re-run. The rollup's completion time for that pack is more than an hour earlier than the last line of its own log, which is unexplained."
  - "macro #6920 is armed and #7007 waits on it; until they land the change-card lane specified in records_queue/specs/F06-ZH-CARD-1_change_card_state_token.md cannot start, and the dead defensive branch found in the ticker page builder during that review rides in with #6920 rather than existing on main today."
  - "Fourteen non-asserted evidence rows in six packets are stale on master. The seat ruled option A: the lock screen now tags packets whose evidence test no longer exists in the tree as historical and prints one count line instead of fourteen row lines, and the repository is untouched, so the rows stay as records. Options B and C are closed."
  - "Three end-to-end proof images and the crops of packets that frame the settings rail age with the surface and no lock fires on them. The seat ruled proof images are artefacts rather than evidence, so the one regenerated during the sweep was a deliberate no-op; the general rail-crop law is in the kit but the other rail-framing packets have not been re-checked since #550's recapture."
  - "Terminal #496 is foreign and on hold, dirty against master, untouched all wave."
  - "The second plain-language sweep, records_queue/specs/T-PL-LOCK-1_i18n_lock_rows.md, is still specified and not started."
  - "Records still owed and not started: the over-specified label recorded on #7032 rather than healed, the single-banner follow-on on #7008, and the change-card lane above."
next_actions:
  - "Ratify this record's pull request, hand-merge it on concluded green at the ratified head, post exactly ONE Wave 4 comment on macro#6819 naming it, and paste that comment id into this file's session field. Never re-ACK; never repeat the Wave 1, Wave 2 or Wave 3 comment."
  - "When macro #7032 concludes green, hand-merge it by squash at 7caf9505, then run the update-branch round on the twelve pull requests behind it and prove each refreshed head merge-only before accepting it."
  - "When macro #6920 merges, refresh #7007 onto main, re-check its thirteen files, mark it ready and arm it; then open the change-card lane."
  - "Keep the ownership-transfer pointer fresh: whenever a carrier re-hashes one of its pinned files, move the pointer to the new squash in the same post-merge run, and if no pinned file changes for roughly fifty master merges, file a hygiene refresh before the guard's single deepening stops reaching it."
  - "Launch stream runs only with a watcher event in hand, and rotate the armed watcher to the short interval whenever a carrier with live checks is armed."
  - "Write the Wave 5 record at the next boundary."
do_not_redo:
  - "Do not re-review any head named in a ratification comment. Ratified or extended this wave: Terminal #567 03e6baee, #569 dcbd7fca and 578ceb79, #570 656924ed, #571 8fa81b50 and 27956bc5, #572 d382df9a, #573 f9eac720; macro #7071 ac26a7cc and #7032 7caf9505."
  - "Do not re-apply 0019, 0020 or 0021, and do not treat #571 as a ledger flip: it corrected header comments and dropped a false sentence, and flipped no state."
  - "Do not attribute a red to a pull request before the same test has been run against the pull request's own base with none of its diff present. The hub window bug looked like a fault in #7032 and was master-side, latent for days and flipped by daily data."
  - "Do not open a sibling heal pull request when a carrier is already in a pack cycle: the sibling still forces the carrier to refresh and restart its packs. One heal carrier per cycle."
  - "Do not rename a file to dodge a count-based discovery guard. Bump the count with a comment that says why it moved."
  - "Do not convert the house-style guard files in a plain-language sweep: their only use of the forbidden form is a negative assertion, and converting them would invert the repository's only standing tripwire."
  - "Do not launch a stream run merely to sit on watcher files. A run that fits inside the watcher's poll gap is structurally blind and returns with nothing, which is what happened to stream T run 19."
  - "Do not end an orchestrator turn while waiting. Wait in a foreground blocking loop; a run that returns before handling its event is a failed run, and a run that goes silent gets stopped, as stream M run 10 was."
  - "Do not suffix a comment-posting command with a JSON filter: it is rejected and the failure is silent. Verify the post through the comments listing instead."
  - "Do not re-ACK or re-bind on macro#6819, and do not post a second Wave 1, Wave 2 or Wave 3 comment."
danger_areas:
  - "A squash merge orphans any evidence pointer that names a branch commit, and the checkout depth hides the cause: the whole open queue fails one test at once. This wave it happened again, was caught by the post-merge chain in the same run, and was repaired as #573 within twenty minutes."
  - "A count-based guard that discovers files by pattern goes red the day an unrelated, correctly named file lands. The red looks like a fault in the new change and is really the guard doing its job."
  - "Daily data commits can flip a latent test bug red on main, and then every pull request whose pack contains that group is red for a reason none of them caused. A later data update can mask it again."
  - "A byte lock over a packet's own files is blind to the container the crops frame. Nothing fires while the picture stops matching the product."
  - "A watcher whose required-check filter names a job that no longer exists reports merges correctly and never reports a red. Prove the filter against a live check list at arming."
  - "A one-shot run launched into a nine-hundred-second poll gap sees nothing and costs a full window. Launch on events, not on hope."
  - "The macro runner pool is three machines: packs queue for hours, a pack can die to a runner shutdown, and a red on such a run says nothing about the code."
prs:
  - 6819
  - 6920
  - 7007
  - 7008
  - 7032
  - 7071
  - 496
  - 567
  - 569
  - 570
  - 571
  - 572
  - 573
decisions:
  - "DEC:SUPABASE-MIGRATION-NAMESPACE-TERMINAL-LEDGER-2026-09-06"
  - "DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06"
discoveries:
  - "DSC:PR-CI-ONLY-RUNS-AGAINST-MAIN-BASE"
  - "DSC:SHARED-CLONE-PACK-STORM-STALLS-THE-FLEET"
---

# Meta-CEO B — Wave 4 checkpoint (2026-09-11 07:15Z to 12:19Z)

Seat: harness session d640f3ef, model Fable, sole owner of half B for the whole window.

Authority: the Chairman override of 2026-09-05/06 and the operating split set at 22:16Z on
2026-09-10 — Fable turns are for rulings, ratifications, merges, production DDL and records, and
every mechanical step around a decision goes to a one-shot Opus orchestrator with a full brief,
because a brief cannot be amended once the agent is running. Watchers report events only; nothing
polls GitHub on a short cycle.

Wave 3 was the cascade landing. Wave 4 is the tail it left behind: the hover hardening, the
evidence guard, the crops that had quietly stopped matching the product, the ledger pins that
existed on one side of the repository and not the other, the plain-language sweep that had been
specified for a day, and the pointer repair the last of those made necessary. Six Terminal pull
requests merged in five hours and the half-B packet queue on Terminal is now empty. On macro the
only thing that merged was the Wave 3 record itself; everything else is still behind a
three-runner pool.

## What landed

Terminal, on master, in order:

- **#567** the hover hardening from Wave 3's flake verdict, test-only — merged **0245e920** at
  07:56:25Z at the merge-only refresh 03e6baee.
- **#569** the ownership-transfer pointer plus the guard that deepens its fetch once before it
  gives up — merged **525157b1** at 08:46:54Z. Its refresh took master's evidence file whole,
  keeping only the test change; then the merge bot refreshed it again and the resulting run sat
  held for approval while the pull request read blocked with every present check green, which is
  the shape the kit's bot-refresh law describes. The seat approved the run and it merged.
- **#570** the rail pins and the eight recaptured crops for the account-completeness packet —
  opened 09:07:35Z, ratified issuecomment-5632166255, merged **908540b7** at 09:30:59Z.
- **#571** ledger pin parity: a contract test for every migration prefix that had none, the key
  order of one row normalised, three header comments corrected to the ledger, and the capture
  script now deriving its ledger line from the row instead of printing a stale one — merged
  **bb7df1ca** at 10:14:09Z, ratified issuecomment-5632423854 at 8fa81b50 and extended to the
  merge-only refresh 27956bc5.
- **#572** the plain-language sweep: twenty-five customer-facing occurrences of the formal
  second-person form became 你 — merged **d812eba5** at 11:16:28Z at d382df9a.
- **#573** the pointer move the squash of #572 made necessary — merged **a4be9a3f** at 12:08Z at
  f9eac720, ratified issuecomment-5633800099, which is this record's boundary.

Every one of them was proved live in the same chain that caught it: the served build identifier
equalled the merge commit each time. With the Wave 3 chain for #568 closing at 07:22Z, seven
deploy proofs ran inside this window and the counter stands at fifteen consecutive on-master
deploys. The build-service checks still read failure on every pull request, are still the
free-tier build rate limit rather than code, and are still not required.

macro merged one thing of this seat's: **#7071**, the Wave 3 record, opened at 07:25Z, ratified at
ac26a7cc, held for four and a half hours by two queued packs, concluded green at 12:18Z and
hand-merged by squash at 12:19:10Z as **ca1b51ac**. The heal carrier #7032 was amended in place
from 807ca8ba to **7caf9505** and re-ratified as issuecomment-5633995741; its twelve packs
restarted. The only other macro merge the sweep saw was foreign: #7033, a Macro Command cleanup,
at 08:13:32Z.

## Production DDL

None this wave. No pull request that merged in this window carried a migration, so no readback
was prepared and no receipt was written. The chain 0014 through 0021 is complete and applied from
Wave 3; 0022 and 0023 remain on master and unapplied until the seat runs them in ledger order.

The ledger-flip law is explicitly not engaged by #571, #572 or #573. #571 looks like ledger work
and is not: it added contract tests, corrected three one-line header comments to the ledger's own
truth, normalised one key order and deleted one sentence that had become false. No state value, no
merge commit field and no applied field moved, and no migration statement body changed by a
character. #572 and #573 touch no migration file at all.

## The reds this wave and how they were attributed

Two reds mattered, and they are attributed in opposite directions.

**#571's own.** The webhooks evidence packet counts the files its discovery pattern finds and pins
the count. #571's new ledger-contract suite is named so that the pattern finds it, so the true
count went from fifteen to sixteen and the guard fired. The earlier head's run had been cancelled
by the amendment push, so the red appeared only once. The seat ruled that a count guard of this
kind legitimately moves when a matching file lands: bump the number with a comment that says why,
never rename a file to dodge the pattern. The fix reproduced the red first, then passed; the file
is not a pinned row in that packet, so no hash moved and no crop was touched.

**macro #7032's pack-8.** This one looked identical in shape and was the reverse. The failing test
was not the one #7032 heals and its subject is not in #7032's diff, so before attributing anything
the orchestrator exported the pack's own base commit read-only and ran the test there with none of
the change present. It failed identically. The mechanism is a window bug in the test: the template
puts the class the assertion looks for on the line before the marker the test slices from, so the
slice structurally excludes the class it asserts. The product is correct; the test has been wrong
since it was written, and daily regime data flipped it red by leaving a different workspace last
in the list. Bisecting the data directories against unchanged code pinned the flip to the
2026-09-09 update rather than the 09-10 one, which also means main has been carrying this red for
every pull request whose pack contains that group, and that a later data update could mask it
again.

The ruling was to fold the one-file fix into #7032 rather than open a sibling: a sibling would
still have forced the carrier to refresh and restart its twelve packs, so one carrier per pack
cycle is cheaper and truthful. The carrier now ships two heals and says so in its body.

A third red needed no heal. macro #7008's pack-6 shows every group passing and then the runner
receiving a shutdown signal — infrastructure, not a test failure. It is not re-run; it rides the
refresh round that follows #7032.

## Rulings this wave

- **Tests never pin known-false statements.** The ledger-pin lane had written assertions that
  froze three stale header sentences as they stood. The seat ruled the sentences corrected to the
  ledger's truth and the pins rewritten to assert agreement between the header line and the row,
  so the test now fails if either drifts. The one false clause in the reservation row went with
  them.
- **Count guards move, names do not.** As above: a discovery-count pin is bumped with a truthful
  comment when a legitimately matching file lands.
- **Guard files are excluded from a plain-language sweep.** Ten test files use the forbidden form
  only in negative assertions and titles. Converting them would have inverted every guard into one
  forbidding the house form. They keep the old character and are the standing tripwire.
- **The sweep's inventory extends to anything in the check rollup.** Three end-to-end assertions
  and four rows of a user-experience specification still asserted the pre-sweep text. Because the
  end-to-end shards are part of the rollup that decides the merge, they were folded into #572
  rather than deferred to a follow-on, and no evidence row pins any of those files, so nothing was
  restamped.
- **Proof images are artefacts, not evidence.** One proof image regenerated itself during the
  sweep. It is produced by the specification that reads it, is pinned by no lock, and the
  regeneration is a deliberate no-op rather than a recapture.
- **The pointer lives on the branch while the branch lives, then moves on master.** #572 used the
  two-commit branch form the kit prescribes; the moment it squashed, the pointer named a commit
  master's history does not contain, and #573 moved it to the squash with every pinned hash
  unchanged and no crop recaptured. The freshness law is closed for that packet, proved on master
  after #573 landed.
- **Option A for the fourteen historical lock rows.** The rows belong to packets whose evidence
  test no longer exists, so they assert nothing. The screening tool now tags those packets as
  historical and prints one count line; the repository is untouched and the rows stay as records.
- **No re-run for an infrastructure red that a refresh will cover.** #7008's pack-6 waits for the
  round rather than burning a machine on a re-run.
- **Rotate the watcher on every arming.** A watcher baselined before a carrier was armed cannot
  report on that carrier; the seat stops it and starts a replacement with a clean baseline, one
  per endpoint, every time.

## Open half-B state at 12:19Z 2026-09-11

| Repo | PR | Head | State | Next act |
|---|---|---|---|---|
| terminal | #573 pointer move | MERGED a4be9a3f 12:08Z | freshness proved on master: pointer is master's parent, packet test green, lock screen clean | nothing owed |
| terminal | #496 | f664ba3d | foreign, dirty, on hold | not this seat's; leave alone |
| macro | #7032 heal carrier | 7caf9505 | ratified, approved, labelled for merge on green; twelve packs restarted at 11:49Z; no native auto-merge on this repo | hand-merge by squash on concluded green, then the update-branch round |
| macro | #7020 #7003 #6905 #6958 #6909 #7012 #7021 #7010 #7006 #7008 #7011 #7014 | see each PR | ratified; their pack reds are the pair #7032 heals plus the hub window bug, and #7008's is infrastructure | update-branch after #7032, prove each refresh merge-only, merge on green |
| macro | #6920 F06 ticker identity panel | 8ad66422 | ratified, armed | merge on green |
| macro | #7007 | b2a3eb17 | ratified, draft on #6920's branch | after #6920: refresh, retarget to main, re-check thirteen files, ready, arm |
| macro | #7071 Wave 3 record | MERGED ca1b51ac 12:19:10Z | hand-merged at the ratified head after both packs concluded | Wave 4 record is this file |

Records owed at the boundary: the change-card lane once #6920 and #7007 land, the single-banner
follow-on on #7008, the over-specified label recorded on #7032 rather than healed, the dead
defensive branch in the ticker page builder that rides in with #6920, the note on ageing proof
images, and the Wave 5 record at the next boundary.

## Laws this wave minted

- **Launch on an event, never to wait.** A stream run is launched with a watcher event already in
  hand. Stream T run 19 sat entirely inside a nine-hundred-second poll gap, saw nothing and
  returned empty; that is structural, not a stall. The waiting rule still governs every wait
  inside a run that is handling an event.
- **A watcher takes its interval as an argument.** Three hundred seconds while an armed carrier
  has live checks, nine hundred when the queue is idle, never below a hundred and fifty.
- **A watcher's filter must be proved against a live check list at arming.** The armed watcher had
  been filtering on a job name that no longer exists, so its required-check field was always empty
  and its red exit could never fire; merges were still caught, which is why it went unnoticed. A
  watcher whose required-check field prints empty on its baseline is defective.
- **A packet that frames a shared rail must pin the rail's sources.** Otherwise a later packet adds
  a row and the crops rot with no lock going red. When a pinned rail source changes, the owning
  packet recaptures at the merge commit.
- **A pointer is valid only while it is reachable at the checkout depth CI uses.** On landing, the
  pointer names a commit in master's history; the guard deepens once before failing; and a packet
  whose pinned files sit still for many merges eventually needs a hygiene refresh anyway.
- **Attribute a red on the base before you attribute it to the change**, and put at most one heal
  in a carrier's pack cycle. Pack numbers are per-pull-request and are not comparable across them.
- **Never suffix a comment-posting command with a JSON filter.** It is rejected and the failure is
  silent; the comment simply does not appear.

## Operating pattern at the end of the wave

Eleven orchestrator runs and six lanes carried this wave. Stream T ran runs 15 through 22: the
post-merge chains and deploy proofs for #568, #567, #569, #570, #571, #572 and #573, the
merge-only verifications on three heads, the report of the held run that needed the seat's
approval, the freshness proofs on master, and the pointer repair that became #573. Run 19 is the
one that returned with nothing and produced the launch law. Stream M ran runs 9 through 12:
classification of a known pack red, one run that went silent and was stopped, the attribution of
the hub window bug to master with the flip date bisected, and the fold-in of the second heal.
Six lanes produced the work itself: the rail pins and recapture, the ledger pins, the amendment
that corrected the header sentences, the count-guard fix, the plain-language sweep with an
adversarial review round, and the sweep's inventory extension. The Wave 3 record agent returned at
07:27Z and its pull request was hand-merged at the close of this window.

Every one of them returned facts and left the decisions to the seat, which is the pattern the
Chairman set. The seat ratified eight heads in five hours, applied no migration because none was
owed, and never merged past a real red.

Plain language stays a program law: no machine text in anything a customer reads, and Chinese copy
uses 你 and never the formal second person. With this wave's sweep landed, the Terminal sources
carry none of the formal form in customer-facing strings; the remaining lane is the one over the
evidence lock rows, still specified and still waiting.
