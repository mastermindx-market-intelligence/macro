---
workstream: WS:TREND-PERSISTENCE
session: claude/ssd-tp-wave-c-close-records-ec2cc69e85d5182d
model: fable
ended_because: complete
prs: [8418, 8459]
decisions: [DEC:TREND-PERSISTENCE-STOPS-AT-WAVE-C, DEC:TREND-PERSISTENCE-STOPS-AT-WAVE-B]
mission: >
  Wave C-2 to close. Land the Wave C instrument in Mastermind, make the ONE pre-registered C1
  development run from a committed clean tree against the pinned inputs, apply the C1 document's
  section 8 decision rule, commit the attempt and result files with the public attempt record,
  and flip the macro Agent OS records so that the workstream's end state is readable by a
  stranger. Operator orders in force for the whole wave: no Opus, Sonnet or Haiku workers
  (everything in the Fable main loop), do not use the Mastermind Executive, both repositories
  usable, never switch the macro-main checkout off main.
state_before: >
  Waves A, B, B2, C-0 and C-1 done. The C1 pre-registration research/TREND_PERSISTENCE_PREREG_C1.md
  merged in Mastermind as PR 1226 (master 521720b09be2, freeze date 2026-10-04 UTC, sha256
  f22b0cee218c381dd3fd078d67301c985eb9415faa0e75ffdc57d520374bf4cc). The macro records PR 8418
  (merged 59a0789c0e5f) had flipped C-1 to done and left C-2 in_progress and C-3 todo. The
  instrument research/trend_persistence_group.py plus 18 tests were built on Mastermind PR 1230
  but not yet merged; the C1 run had not been made. The sector substrate
  data/breadth/sp1500_pit_sectors.parquet (sha256 cba7fc07...0de3, label_asof 2026-10-04,
  era_correct False on every row) sat in the squash-merged C-1 worktree on the SSD.
changed:
  - path: "Mastermind research/trend_persistence_group.py (PR 1230, master 1644ace945a8)"
    what: "Wave C instrument. Reads the C1 document and refuses to run if any section 11 pin (prereg, B2 result, V2 rev 2, protocol, readout, sector snapshot) drifts; reproduces both B2 means to 1e-9 before scoring; one-run guard via the public attempt record; writes attempt + result files; applies the section 8 rule mechanically and prints its wording verbatim. An exp-underflow guard that happened to spell an identity literal (745) was removed because the d8 identity scanner reads research/data/*.json and non-test code; behaviour unchanged."
  - path: "Mastermind tests/test_trend_persistence_group.py (PR 1230)"
    what: "18 tests pinning the instrument's pins, the one-run guard, the decision rule branches and the output schema."
  - path: "Mastermind research/data/trend_persistence_c1_attempt.json (PR 1252)"
    what: "The public attempt record of the single C1 development run: started 2026-10-05T00:06:21Z, git_head 1644ace945a8, code/prereg/B2/sector pins, retry_reason null. 521 bytes, sha256 22137f608a01cf2d19801b8398d68557d6a5d822c505197d9bbb5e35e7fb949f."
  - path: "Mastermind research/data/trend_persistence_c1_result.json (PR 1252)"
    what: "The committed result: decision.outcome C1-NULL, carried [], power.n_read null; three selection cells with all five carry conditions printed; horizons 5/20/60 with blocks, brackets, LOSO folds, embargo counts; coverage 1690 labelled / 343 unlabelled of 2033 names; redundancy drop of grp_hit_20 (rho 0.82 with grp_participation_50); reproduction block. 347,099 bytes, sha256 bcc1e259b83e319e39714f9cc84abc29cfbc43be10a8cd0ea90242a1f1533ccc."
  - path: agentos/workstreams/WS-TREND-PERSISTENCE.md
    what: "status done; C-2 done (PRs 1230 + 1252 named in the title); C-3 dropped with the reason; decision, artifacts, landmine (dates scored three times), two do_not_redo entries and next_action updated."
  - path: agentos/decisions/DEC-TREND-PERSISTENCE-STOPS-AT-WAVE-C.md
    what: "New decision record: the family stops at Wave C under C1-NULL; alternatives rejected and evidence listed."
  - path: research/DO_NOT_REBUILD.md
    what: "New section 2 row DNR:KILL-TREND-PERSISTENCE-SECTOR-GROUP-PERSISTENCE (eleven-sector group persistence constructions of the C1 document closed; other constructions untested); compiled blocklists regenerated with scripts/check_blocklist_drift.py --fix."
  - path: agentos/handoffs/TREND-PERSISTENCE-2026-10-05.md
    what: This record.
verified:
  - claim: The C1 development run was made exactly once, from the committed clean tree at Mastermind master 1644ace945a8, and exited 0 with decision C1-NULL.
    command: "cd <Mastermind worktree> && git status --short | wc -l && git rev-parse HEAD && python3 research/trend_persistence_group.py run 2>&1 | tee $SP/c2/c1_run.log; tail -n 1 $SP/c2/c1_run.log; python3 -c \"import json;r=json.load(open('research/data/trend_persistence_c1_result.json'));print(r['decision']['outcome'], r['decision']['carried'], r['power']['n_read'], len(r['attempts']))\""
    result: "0 dirty; HEAD 1644ace945a83985ad45cd4bdec3edb155914a63; EXIT rc=0 after 80 s; C1-NULL [] None 1"
  - claim: The B2 reproduction gate passed before scoring.
    command: "python3 -c \"import json;r=json.load(open('research/data/trend_persistence_c1_result.json'));print(r['reproduction'])\""
    result: "both committed B2 means (0.49461154432499976 at h20, 0.5337496007208158 at h60) reproduced within 1e-9; gate passed"
  - claim: No selection cell met the five carry conditions.
    command: "python3 -c \"import json;r=json.load(open('research/data/trend_persistence_c1_result.json'));[print(k,v['carried'],round(v['mean'],6),round(v['p_one_sided'],3),v['blocks_positive'],'/',v['blocks_scored'],v['n']) for k,v in r['selection'].items()]\""
    result: "rel_spy_20:A-Bstar False -0.002391 0.674 1/5 192; rel_spy_20:I-A False -0.000913 0.909 1/5 192; rel_spy_60:A-Bstar False 0.001865 0.324 3/5 184"
  - claim: The instrument tests and the d8 identity-literal scanner pass on the results commit.
    command: "python3.12 -m pytest tests/test_trend_persistence_group.py tests/test_ceo_submit_armed_composition.py::test_d8_template_topology_and_protected_defaults -q  (at c553e5a23ef2)"
    result: "19 passed"
  - claim: Both result files are byte-identical on Mastermind origin/master after the queue merge of PR 1252.
    command: "git -C <Mastermind worktree> fetch origin master && for p in research/data/trend_persistence_c1_attempt.json research/data/trend_persistence_c1_result.json; do test \"$(git rev-parse origin/master:$p)\" = \"$(git rev-parse HEAD:$p)\" && echo OK $p; done"
    result: "OK both paths at origin/master 7eac3ec252475600147ec9a376b8ca16403ac4c5 (attempt blob 7e1f6870421b, result blob 02669072003c; squash is an ancestor of origin/master; PR 1252 mergedAt 2026-10-05T02:46:58Z)"
  - claim: The Agent OS records and the Do Not Rebuild registry validate.
    command: "python3 scripts/agentos.py validate && python3 scripts/check_blocklist_drift.py"
    result: "python3 scripts/agentos.py validate exit 0 (0 errors); python3 scripts/check_blocklist_drift.py OK no drift"
unverified:
  - claim: The SIC-derived labels on the 1,083 leavers are the sector each company had while it was a member.
    what_would_verify: A licensed historical GICS source; the artifact records era_correct False on every row and the C1 result pins that fact, so the null is a statement about as-of-now labels.
unresolved:
  - 343 of 2033 panel names carried no sector label and were scored in the unlabelled bracket only; the primary cells read the labelled universe, which is survivor-tilted (1506 current members of 1690 labelled).
  - Mastermind master is merged, not deployed; nothing in this wave runs in production, so no deploy is owed by this workstream.
next_actions:
  - Nothing is pending for this workstream; it is closed at Wave C (DEC:TREND-PERSISTENCE-STOPS-AT-WAVE-C, DNR:KILL-TREND-PERSISTENCE-SECTOR-GROUP-PERSISTENCE).
  - A successor who wants GICS industry-group or industry, basket or dynamic-theme group persistence writes a NEW pre-registration document in Mastermind research/ (new filename; never an edit of research/TREND_PERSISTENCE_PREREG_C1.md), with any gated read on formation dates after that document merges, and a new macro workstream or a reopening note on this one.
do_not_redo:
  - Do not run the C1 development pass again; the one-run guard reads research/data/trend_persistence_c1_attempt.json and the attempt record is public on Mastermind PR 1252.
  - Do not make a C2 confirmation read; under C1-NULL no cell carried, n_read is null and no constants block exists.
  - Do not edit research/TREND_PERSISTENCE_PREREG_C1.md, the committed C1 result or attempt files, or any pinned module; the instrument refuses to run on a drifted pin and a test fails if the committed result changes.
  - Do not relabel leavers by ticker string or re-run the sector collector expecting more coverage (2026-10-04 handoff).
  - Everything in the 2026-10-03 and 2026-10-04 handoffs' do_not_redo still binds (no V2/B2 re-run, no profile from the 29 tests, no Opus/Sonnet/Haiku workers for this program).
danger_areas:
  - "Mastermind master uses a merge queue: gh pr merge --squash --match-head-commit ENQUEUES and the squash lands later; QUEUED is not MERGED, verify the blob on origin/master after the queue reports the merge."
  - "The d8 identity-literal scanner (tests/test_ceo_submit_armed_composition.py) diffs merge-base..HEAD excluding tests/ and DOES scan research/data/*.json; it reads committed HEAD, so commit before running it. A harmless numeric literal that spells an identity fragment fails it."
  - "The Mastermind CI wait guard blocks a repeat gh pr view of the same PR inside 300 s; one 180 s watcher per PR is the lawful cadence."
  - "A write into data/ from a sparse macro worktree truncates committed artifacts; the C1 run read the sector parquet from the squash-merged C-1 worktree, which had opted into data/."
---

## Result in one paragraph

The pre-registered Wave C development pass returned C1-NULL. Measured against a member's own
trailing returns and volatility (the gating baseline B*), seven sector-level persistence features
add -0.0024 to the rank-linear fit of 20-session relative-to-SPY return (one-sided p 0.67) and
+0.0019 at 60 sessions (p 0.32); the interaction cell adds -0.0009 (p 0.91). Against zero the same
features read +0.0062 and +0.0249, so the group information they carry is already in each member's
own tape. No cell carried, so no C2 read exists and nothing is built. The family has now produced
three pre-registered nulls (Wave B, B2, C1) on formation dates 2022-07-06 to 2026-06-02, and those
dates carry no further claim. Industry-group or industry, basket and dynamic-theme constructions
are untested and not closed.
