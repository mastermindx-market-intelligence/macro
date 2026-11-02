---
key: READY-FOR-REVIEW-TRIGGERS-NO-CI
claim: "Flipping a PR from draft to ready (`gh pr ready`) schedules no ci.yml run on this repository; the levers that produce a run are a push or a re-run."
falsifier: "`gh pr ready <n>` on a PR with no in-flight run followed by `gh run list --branch <br> --json event` showing a new ci.yml run with event ready_for_review."
so_what: "Make a PR ready only after its checks have concluded on the exact head (the flip buys nothing); if a head has never run, push or `gh run rerun` \u2014 never wait for the flip to start CI."
kind: runtime
verified_at: 2026-10-02
verified_by: "measured 2026-10-02 on the F01 chip lanes: draft->ready flips produced no new run; `gh run list --branch <br>` unchanged"
scope:
  - "macro"
  - "WS:MARKET-OS"
  - ".github/workflows/ci.yml"
confidence: verified
---

ci.yml's pull_request trigger types do not include ready_for_review here. The seat's merge discipline (ready -> state read -> `--match-head-commit`) therefore reads checks that already exist; it never creates them.
