---
workstream: WS:CHINA-ALPHA-INTELLIGENCE
session: claude/china-rotation-member-weekly-20260908-sol-001
model: sol
ended_because: blocked
mission: >
  Restore already-computed recent stock movement through the existing China rotation
  detail journey with honest observation dates, without changing group or Prophet
  ranking, entry authority, monthly member ordering or the common identity plane.
state_before: >
  At Macro0b30e044b6456a96f1d6e1a9885987691a2b46dc, the September8 THS basket
  source had3522 member occurrences with3522 non-null ret_5d values, but the China
  rotation adapter hardcoded displayed1W values to null. Its real detail consumer
  displayed only1M. The existing source-continuity successor and LENS repair have
  separate active owners and must not be duplicated.
changed:
  - path: tests/test_baskets_region.py
    what: >
      Confirmed local-only regression additions for current versus stale/gapped
      observations, six-session-window validity, invalid numeric types, immutable
      inputs and unchanged existing trailing-return values. No production edit.
  - path: tests/test_subsector_rotation.py
    what: >
      Confirmed local-only regression additions for weekly percent units, real zero
      and negative values, observation-date agreement, null preservation, unchanged
      monthly sample/group order, the actual CN detail builder, and unchanged default
      shared-template behavior for other regions. No result from these new tests yet.
  - path: agentos/handoffs/CHINA-ALPHA-INTELLIGENCE-2026-09-08-rotation-member-weekly.md
    what: >
      Adds this handoff to the existing records carrier6990; it does not publish or
      replace the interrupted source branch, and does not claim feature completion.
verified:
  - claim: The existing source computes weekly returns but the China adapter drops them.
    command: >
      git show 0b30e044b6456a96f1d6e1a9885987691a2b46dc:engine/baskets_region.py;
      git show 0b30e044b6456a96f1d6e1a9885987691a2b46dc:engine/subsector_rotation_china.py;
      parse site/chinabasketdata/baskets_ths.json at the same immutable commit.
    result: >
      Producer emits ret_1d/ret_5d/ret_10d/ret_20d. Adapter _members writes1W=None.
      Snapshotas_of2026-09-08 contains3522 member occurrences and every one hasret_5d.
      This is not a unique-stock count, a live-site capture or a return forecast.
  - claim: The new source worktree was created from a fresh remote main without competing path edits.
    command: >
      Complete four-page GitHub open-PR path census plus immutable Git resolution of
      truncated file listings; targeted git status over263 registered worktrees;
      git fetch origin main; git worktree add --no-checkout on the unique claude branch.
    result: >
      154 open PRs, no overlapping source path and no unresolved truncated listing.
      Local target deltas were absent sparse-proof files, not source modifications.
      Fresh source base909b9ffe81314fa0d5763f436a5386024168f86c matched remote main;
      the declared six paths were unchanged from prior323d63c5. Worktree was clean.
  - claim: Unchanged four-module baseline completed on the already-installed Python3.14 environment.
    command: >
      PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q --tb=short -p no:cacheprovider
      tests/test_baskets_region.py tests/test_baskets_china.py
      tests/test_baskets_china_ths.py tests/test_subsector_rotation.py
    result: >
      35passed, exit0, native process61387. An earlier sparse baseline lacked the
      collectors directory; materializing it exposed a separate missing-lxml failure
      underPython3.12:34passed/1failed. No installation, shim or exclusion hid it.
  - claim: New test-source writes were acknowledged before Studio transport stopped responding.
    command: Remote Desktop Commander write_file append calls to the two exact owned test paths.
    result: >
      The app acknowledged all appended test blocks. No engine, builder or template
      implementation file was edited, and no feature commit, push or PR was created.
  - claim: The current host failure was reported to its existing maintenance owner.
    command: GitHub add_comment_to_issue on Mastermind507 after reading owner adoption5592487889.
    result: >
      Comment5592825960 records this caller, the unresolved test receipt and the same
      Studio device. It creates no installer/wake assignment or drain certificate.
unverified:
  - claim: Outcome and side effects of the first new-regression run.
    what_would_verify: >
      Same-device recovery of the exact red.log, process/session state and working-tree
      diff. The start_process returned no PID or exit; do not infer either completion
      or no execution from the timeout, and do not replay it before reconciliation.
  - claim: Weekly-member production implementation, passing new tests and rendered capability.
    what_would_verify: >
      After recovering the existing source carrier, implement only the admitted six
      paths, run discriminating regressions, compare unchanged fields and render the
      actual CN detail builder with complete/partial/null inputs in both themes and
      languages on desktop1440/mobile390. None of this completion is claimed now.
  - claim: Current full Agent OS validation of this new handoff.
    what_would_verify: >
      Run the existing scripts/agentos.py validator at the correct record basename
      against the current store. Frontmatter was checked against the current schema;
      the official record or whole-store validator has not executed for this addition.
unresolved:
  - Studio file/process/ping calls timed out; the cloud online label is not execution proof.
  - The red test run has no received PID/result. Source custody and its possible process stay sticky.
  - Existing Macro6992/6996 remain held; Source Continuity346 has an active saturated-foreign-PR successor.
  - Existing LENS6860 owns mobile gesture work; no shared-JS implementation belongs to this slice.
next_actions:
  - >
    On the same Studio, read the retained red.log and reconcile the pending test
    process plus actual local diff before any source command or rerun. Recover the
    existing branch/worktree; do not mint another one or overwrite unique tests.
  - >
    Verify intended new failures against the unchanged production source. Correct
    any test-harness defect honestly before implementing the six-path vertical.
  - >
    Add price_asof/ret_5d_asof metadata to the current producer without changing old
    values; restore current-only weekly values in the China adapter; opt only the
    CN detail builder into the existing shared component's1W/1M/date/sample view.
  - >
    Prove null/zero/negative/date/unit behavior, exact non-weekly parity, the actual
    producer-to-renderer path and dark/light EN/ZH desktop/mobile results. Publish
    one normal same-branch DraftHOLD source PR, obtain current independent review,
    applicable completed CI/continuity and natural publication/served-user proof.
do_not_redo:
  - Do not restart or duplicate terminal Mastermind544/545; their merges are ca833b63 and7afc6641.
  - Do not create a competing saturated-foreign-PR adapter; existing START is Mastermind346/comment5592292126.
  - Do not replace Macro6992 input repair, Macro6996 instruction repair, existing China6871 or Entry Truth6805.
  - Do not use635cbf9a as6996 source; the verified source is30da44be695d5b7b249d0180f3af6d21ed5bad09.
  - Do not claim weekly data is absent upstream or create another price collector/store.
  - Do not change the monthly top-eight selection or promote these display returns into trading authority.
  - Do not infer a complete constituent roster from the displayed eight-member sample.
  - Do not relabel the35-pass unchanged baseline as a pass of the new regression tests.
danger_areas:
  - The common producer also feeds Hong Kong and Canada; additive metadata must not alter their values or default UI.
  - Five non-null observations across a gap are not five complete input sessions; do not compress missingness silently.
  - Snapshot/observation dates are not knowledge-time or a point-in-time replay guarantee.
  - No test result or file contents may be fabricated because remote transport failed.
  - No pending source operation may be moved to another Mac or carrier without effect/custody reconciliation.
prs: [6990, 6992, 6996, 6860, 7000]
discoveries: [DSC:CN-PROPHET-V4-ORDER-DISABLED-BY-INCOMPLETE-INTELLIGENCE-COVERAGE]
---

# Exact continuation: existing weekly-member source, not a replacement plan

Current live Chairman direction authorizes continuing the four-market recovery.
Source admission is Macro6990/comment5592658253. This handoff is organizational
continuity under the existing records branch; it grants no source transfer or
release merely because another session retrieves it.

Source worktree:
`/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/china-rotation-member-weekly-20260908-sol-001`

Source branch: `claude/china-rotation-member-weekly-20260908-sol-001`.
Original source base: `909b9ffe81314fa0d5763f436a5386024168f86c`.
Protected procedure at admission: Mastermind
`ca833b63c3ac5b2c0c1dc0d670d11e3f1f24a5b4`, same-pin compatible Skillpack1.0.1/bootstrap1.

Evidence folder:
`/Users/chriswong/Documents/Cluade/exec-prestage-receipts/china-rotation-member-weekly-20260908-sol-001`.
Confirmed files include the four PR-census pages, scope-census.json and
implementation-plan.md. The intended `red.log` write and its completeness are
unverified because both start_process and the subsequent exact-file read timed
out. Cloud listing retained an online label with Studio last_seen22:23:39Z while
other devices reported22:28–30. Subsequent Studio ping also timed out.

## Six-path contract retained

1. `engine/baskets_region.py`: additive observation/window dates; existing numeric
   return and basket methods unchanged.
2. `engine/subsector_rotation_china.py`: map existing ret_5d fractions to1W percent
   only with matching valid dates; retain1M order and top-eight sample.
3. `scripts/build_subsector_rotation_china_pages.py`: pass the explicit China-only
   weekly-display option and snapshot date through the real builder.
4. `templates/subsector_rotation_detail.html.j2`: render1W/1M, sample count and
   honest observation freshness only for that opt-in; default other-region view
   unchanged, existing tokens/components/navigation retained.
5. `tests/test_baskets_region.py`: producer date/window/value tests already begun.
6. `tests/test_subsector_rotation.py`: China mapping plus actual builder/default
   renderer regressions already begun. There is no existing separate
   tests/test_subsector_rotation_china.py to invent as a registered owning test.

Data behavior: current six valid positive finite daily input observations permit
weekly display; stale or gapped data remains unavailable for that snapshot.
Real zero and negative returns remain numbers. Neither this evidence date nor
existing historical return computation is promoted into a correction-safe
historical research feed. No stock/group score or strategy permission changes.

Dark retains the existing quiet bordered instrument cards. Light retains the
existing white-panel/hairline structure. Added returns use existing directional
ink tokens and a compact stack, with explicit tests for long names and390px
width. Both languages/themes require actual browser inspection before acceptance;
no successful new visual proof exists at this checkpoint.

## Integration coordination completed in this continuation

Macro6860/comment5592352098 directs the real nested China chip/Terminal gesture
acceptance case to the already-existing LENS owner without duplicating its source.
Macro7000/comment5592403706's active portfolio-context incident is retained as a
separate P0-C evidence owner, not confused with the legacy reader or absorbed into
this source slice. The R0 safety carrier was freshly read beyond its last consumed
September8 edge and returned no newer reply; no worker return or completion was
invented and no new R0 worker was created.

The product capability remains NOT_BUILT for this new weekly-display slice;
test preparation and a35-case unchanged baseline do not make it live. The broader
China/US/HK/Canada recovery remains open. The next useful action is same-carrier
result recovery followed by the bounded producer-to-user implementation.
