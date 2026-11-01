---
key: ITP-SEAT-RELEASES-ADMINISTRATIVE-BLOCKS-UNDER-CHAIRMAN-2026-10-06
question: >
  When the Information-to-Price program's own pull requests sit behind Sol HOLD-FOR-SOL holds,
  stale CHANGES_REQUESTED reviews whose blockers main has already closed, or a CI red that
  provably belongs to an unrelated sibling test, does the Fable Program-CEO seat wait for Sol /
  the Chairman, or release and merge itself?
answer: >
  The seat releases and merges itself, under the Chairman's explicit 2026-10-06 ruling that these
  are administrative blocks ("they are all really administrative blocks and not hard blocks, so u
  should just overrule them and get us past them rather than making me go fix them using chatgpt
  web sessions"), using the lawful release form every time: a release comment on the PR naming the
  Chairman authority and the exact head, ONE title/body edit turning HOLD-FOR-SOL into
  HOLD-RELEASED 2026-10-06, gh pr ready, a state read on CONCLUDED checks, and a squash merge
  pinned with --match-head-commit, followed by a fetch of main alone and a per-path blob compare.
  Stale reviews are dismissed through the review-dismissal API with a message naming the evidence
  that their blocker is closed on main. A red that is provably inherited (same assertion red on
  two identical attempts, green on main's own baseline, owner test untouched by the PR, owner job
  of the PR executed and green) is classified inherited and the merge proceeds on the exact head
  with that red named in the release comment. Gates that are NOT administrative stay with their
  owners and are reported to the Chairman last: capital/rank/size/trade authority, vendor
  procurement, source-owner rights receipts, EVAL-1 held-outcome custody, EFFECT_UNKNOWN acts,
  typed git precheck refusals, and fabric capacity limits.
rationale: >
  DEC:SOL-HOLD-IS-A-MERGE-BARRIER makes a recorded hold bind every merge path until its holding
  authority releases it. The Chairman is the final authority above Sol and, on 2026-10-06,
  delegated release of exactly this class of block to the program seat; an explicit Chairman
  delegation overrides the default role assumptions inside its stated scope. Waiting on Sol for
  blocks the Chairman had already classified as administrative was the measured failure mode of
  the previous day (nine PRs DRAFT + HOLD with accepted content and green checks, zero merges).
  The lawful release form keeps the carrier truthful: each PR carries the authority, the exact
  head, and the evidence, and each merge is independently reversible by git revert. The
  inherited-red rule exists because a pack is one check and a third identical rerun changes
  nothing (two equivalent no-delta cycles ban a third).
alternatives:
  - option: Keep every held PR PARKED until Sol posts HOLD-RELEASED
    why_not: >
      Sol was not acting on the holds and the Chairman explicitly ruled them administrative;
      parking contradicts the delegation and stalls the program with accepted, green content.
  - option: Open replacement PRs without holds
    why_not: >
      Forbidden by the program's do_not_redo law (never replace an occupied carrier); it would
      also strip the review and acceptance history from the artifacts.
  - option: Merge with --admin or arm merge-on-green on the held PRs
    why_not: >
      merge-on-green on a held PR is forbidden fleet law, and --admin outruns CI; the release
      form merges only on concluded checks with the head pinned.
  - option: Keep rerunning #8422's CI until ci-pack-6 greens
    why_not: >
      Two identical attempts failed the same unrelated assertion on the same plan; a third is a
      no-delta cycle, and the owner job of the PR had already executed green.
evidence:
  - "Chairman ruling 2026-10-06 (verbatim quoted in the answer), applied as seat ledger entries D34, D38, D42, D49."
  - "Release comments: #8312 6011558025, #8505 6011669970, #8514 6011673427, #8394 6011777769, #8467 6011782121, #8504 6012034313, #8521 6012032293, #8522 6012094323, #8461 6012568839, #8463 6012679845, #8422 6012779228."
  - "Dismissed reviews: 5404446368 (#8394), 5411174554 (#8467), 5408914930 (#8422); each via PUT repos/{owner}/{repo}/pulls/{n}/reviews/{id}/dismissals, state DISMISSED."
  - "Squashes on origin/main: 0f575e51 (#8312), 999e43f1 (#8505), 1bd2813b (#8514), 96422cf6 (#8394), ab63a77e (#8467), cab92332 (#8504), f8ce27bf (#8521), 8c3d0f60 (#8522), 42107c53 (#8525), 77fc9b1c (#8461), fbd63e4f (#8463), d0ede600 (#8422)."
  - "#8422 inherited red: ci.yml run 37433544726 attempts 1 and 2 red only on tests/test_brain_history_widget.py::test_composer_controls_keep_touch_targets_and_reflow[1-zh-320]/[2-zh-320] (#8473's test); main baseline run 37432781824 ci-pack-6 green; options-skew-engine executed in ci-pack-4, 60 passed in 20.74s."
  - "research/INFORMATION_TO_PRICE_CONTINUATION_HANDOFF_2026-10-06.md sections 18-19."
affects:
  - "WS:ALPHA-INTELLIGENCE-INTEGRATION"
  - ".github/ci/legacy-jobs.yml"
  - "engine/price_pressure/**"
  - "engine/k3e*/**"
confidence: high
reversibility: easy
decided_by: "seat: fable program-ceo session 2fc05761, under Chairman ruling 2026-10-06"
decided_at: 2026-10-06
review_by: 2026-10-20
---

# Seat releases administrative blocks under explicit Chairman authority (Information-to-Price, 2026-10-06)

Scope. This decision is a Chairman-delegated exception for the Information-to-Price program's own
pull requests on 2026-10-06. It does not supersede `DEC:SOL-HOLD-IS-A-MERGE-BARRIER`: a hold placed
by Sol still binds every seat that has not received an explicit Chairman delegation covering it,
and conditional authority granted for one program never transfers to another.

What "administrative" means here. A block is administrative when the artifact's content is
accepted or unchanged, the binding checks have concluded, and the only thing standing between the
PR and main is a label, a hold marker, a review whose stated blocker main has since closed, or a
red that provably belongs to an unrelated sibling test. A block is not administrative when it
protects capital, rights, custody, or an unobservable effect; those are reported, never overruled.

Reversibility. Every merge taken under this decision is a squash with its hash recorded in the
continuation file; `git revert <squash>` undoes it without touching any other artifact.
