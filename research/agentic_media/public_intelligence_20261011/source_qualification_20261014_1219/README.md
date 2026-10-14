# 12:19 continuation evidence

This directory records adjacent work while #9209 awaits controller-admitted CI refresh.
It does not authorize release or publication.

- `release_snapshot.json` and `controller_decision.json`: one release read and the
  already-completed full controller decision. Green CI is stale for landing.
- `prospective_merge_tree.json`, `prospective_acceptance.json`,
  `shared_dependency_diff.txt`, and `check_definition_delta.txt`: exact Git preflight;
  no release branch mutation or silent manifest rebind.
- `verify_shared_dependency.py`: reproduces exact protected source extraction into
  an isolated temporary fixture on this same SSD, checks unchanged inputs, and runs
  the two Node commands recorded in `shared_dependency_checks.json`.
- `shared_dependency_checks_1_initial_spec_reporter.txt`: initial54tests passed;
  wrapper format detection failed. Explicit TAP corrected the wrapper, not tests.
- `shared_dependency_review.json`: parent acceptance limited to these prospective
  shared dependency bytes.67checks pass; installation/browser acceptance still due.
- `source_screen.json`, `fed_notes_feed.json`, `fed_press_feed.json`: bounded public
  source review. Feeds were read without invoking a producer. No article or issuer
  admission, provider generation, staging, publication, or first-party receipt.

Verification command from this worktree:

```sh
python3 research/agentic_media/public_intelligence_20261011/source_qualification_20261014_1219/verify_shared_dependency.py
```

Next release action: consume the existing controller's admitted refresh and new
exact-head CI, then protected merge and actual-merge-SHA normal-updater acceptance.
Only afterward integrate that landed main into the same reviewed Press follow-on.

Diff text files are review displays with trailing whitespace removed; exact raw
output hashes and normalization are in `diff_display_receipt.json`. Source bytes
and test inputs are unmodified and remain bound to their named Git objects.
