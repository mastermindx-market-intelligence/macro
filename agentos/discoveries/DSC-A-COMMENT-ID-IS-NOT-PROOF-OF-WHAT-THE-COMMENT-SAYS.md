---
key: A-COMMENT-ID-IS-NOT-PROOF-OF-WHAT-THE-COMMENT-SAYS
claim: >
  `gh issue comment --body "@/path/to/file.md"` posts the LITERAL STRING `@/path/to/file.md`
  as the comment body. Only `--body-file` reads a file; `@`-expansion belongs to `gh api -F`,
  not to `--body`. There is no error and no warning, `gh` prints a real comment URL, and the
  returned id is indistinguishable from a successful post - because the request genuinely did
  succeed, it just carried the wrong text. Measured on carrier #7789 on 2026-09-29: comment
  `5896637219` was recorded in a PR body, in program memory and in two session reports as the
  #8213 merge return; its actual body was 147 characters of filesystem path where a
  6,978-byte return carrying the candidate head, RED/GREEN evidence and the exact CI state
  should have been. The commissioning authority received a path for ~40 minutes while every
  local record said DELIVERED.
falsifier: >
  Post a comment with `gh issue comment <n> --body "@<some existing file>"` and read it back
  with `gh api repos/<owner>/<repo>/issues/comments/<id> --jq '.body'`. If the body is the
  file's CONTENTS rather than the literal string `@<file>`, `gh` has gained @-expansion on
  `--body` and this record is obsolete. Conversely, the bug this record describes is present
  whenever that read returns a single line beginning `@/`.
so_what: >
  A comment id proves a REQUEST succeeded; it proves nothing about what the comment says, so
  never treat the id as delivery evidence. After any carrier post, read the body back and
  diff it against the file you meant to send - a length check alone catches this class (147
  versus 6,978). Audit a whole thread for past occurrences with `gh api
  'repos/<owner>/<repo>/issues/<n>/comments?per_page=100' --jq '[.[] | select(.body |
  startswith("@/"))] | .[] | "\(.id) \(.created_at) len=\(.body|length)"'`. Repair shape:
  re-deliver as a NEW comment with `--body-file` (an edit to the old one may never notify a
  web counterpart, so an edit alone is not delivery), then PATCH the broken comment to point
  at the re-delivery so the thread carries no bare path - same carrier, no blind retry, per
  the EFFECT_UNKNOWN reconciliation rule. The general lesson generalizes past `gh`: when a
  success signal is a proxy that correlates with the outcome under normal conditions, verify
  the outcome itself, because the proxy decouples in exactly the failure case.
kind: landmine
verified_at: 2026-09-29
verified_by: >
  Measured on carrier #7789. `gh api repos/mastermindx-market-intelligence/macro/issues/
  comments/5896637219 --jq '.body'` returned one 147-character line
  (`@/private/tmp/.../carrier_return_8213_merged.md`) against a 6,978-byte intended file.
  An audit of all 100 comments on that thread for bodies starting `@/` returned exactly one
  row - that comment - so every other return on the carrier delivered real content. Repaired
  by re-posting with `--body-file` as `5896924077`, whose body was then read back and diffed
  against the source file (identical apart from jq's trailing newline), and by PATCHing
  `5896637219` to a 455-character pointer at the re-delivery.
scope:
  - WS:GMI-INDUSTRIALS-FIRST-VERTICAL
confidence: verified
---

The detection path is worth recording separately, because nothing in the ship loop was
looking for this. The standing carrier law requires a fresh re-read of the thread before any
new post, to catch a ruling that landed while you were working. That re-read prints each
recent comment's first ~110 characters - and that is what showed a body beginning
`@/private/tmp/…`. **A fence written to catch a stale premise caught a failed delivery
instead.** Without it the session would have ended reporting a merge return that was never
on the thread, and the next seat would have cited `5896637219` as the authority for what was
returned.

Two habits follow for any seat posting to a carrier. Put the return in a file and send it
with `--body-file`, so the shape that silently truncates is never typed. And treat "I posted
it" as a claim needing the same read-back discipline as "it merged": this repo already
insists that `MERGED` is a fact about a pull request and never about your bytes, verified by
reading `origin/main` itself. `DELIVERED` is the same kind of claim about a comment, and the
comment body is the only thing that can settle it.
