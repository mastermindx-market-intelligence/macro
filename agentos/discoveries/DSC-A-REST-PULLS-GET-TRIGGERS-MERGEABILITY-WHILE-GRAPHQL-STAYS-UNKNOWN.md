---
key: A-REST-PULLS-GET-TRIGGERS-MERGEABILITY-WHILE-GRAPHQL-STAYS-UNKNOWN
claim: "`gh pr view --json mergeable` can answer UNKNOWN for minutes on a hot main (two reads 150 s apart on #8287), while one REST `gh api repos/{owner}/{repo}/pulls/N` returns mergeable=true immediately because the GET schedules the computation."
falsifier: "`gh api repos/mastermindx-market-intelligence/macro/pulls/<n> --jq .mergeable` returning null on a second read 60 s after the first."
so_what: "A merge precondition that reads GraphQL mergeable can refuse forever; read REST pulls/N before refusing, and put the state read and the --match-head-commit merge in ONE invocation."
kind: runtime
verified_at: 2026-10-02
verified_by: "#8287 19:3xZ: GraphQL UNKNOWN x2; REST pulls/8287 mergeable=true mergeable_state=unstable; merge succeeded on the same invocation"
scope:
  - "macro"
  - "WS:MARKET-OS"
  - "scripts/merge_on_green.py"
confidence: verified
---

The REST and GraphQL pools are separate and the REST GET has the side effect of triggering GitHub's mergeability computation. `$S/merge_pr.sh` reads REST first for this reason.
