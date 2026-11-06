---
key: MERGE-ON-GREEN-RELEASE-IS-HOLD-RELEASED-NEWEST-HUMAN-COMMENT
claim: >
  The merge-on-green sweeper lifts a recorded hold only when a NEW issue comment
  begins a candidate line with the literal token HOLD-RELEASED, is the newest
  non-Bot comment, and is dated after every hold-carrying comment (or the marker
  is edited out of the body); any other release sentence leaves the hold binding.
falsifier: >
  Read scripts/merge_on_green.py HOLD_RELEASE_RE (~:5196, r"\bHOLD-RELEASED\b")
  and the dated-comment release rule (~:5412-5438); or post "RELEASE HOLD — ..."
  on an armed PR carrying a body hold and watch the hold-guard refuse the merge.
so_what: >
  A seat that holds its own PR must release it with a comment whose own line
  starts "HOLD-RELEASED", then remove the body marker in ONE edit after checks
  conclude; a prose release ("hold lifted", "RELEASE HOLD") is not a release and
  the PR sits refused by the hold-guard while every read looks green.
kind: constraint
verified_at: 2026-10-02
verified_by: >
  PR #8265: seat comment "RELEASE HOLD — R3 ACCEPTED" (11:46Z) never matched;
  hold-guard refusals 13:28Z/13:36Z ("matched marker: HOLD —"); HOLD-RELEASED
  comment 5953835766 + one body edit cleared it and the PR merged 36d83f1330ff.
  scripts/merge_on_green.py:5180 hold regex, :5196 HOLD_RELEASE_RE.
scope:
  - macro
  - scripts/merge_on_green.py
  - .github/workflows/merge-on-green.yml
  - WS:MARKET-OS
confidence: verified
---

The hold regex (`\bHOLD-FOR-[A-Z0-9_-]+|\bHELD[- ]FOR[- ][A-Z0-9_-]+|\bHOLD\s*[—:-]|\bDO\s+NOT\s+MERGE\b`)
binds only when the marker BEGINS a candidate line in the body or a comment; inline-code
mentions and quoted `>` lines never count. A body hold is cleared only by a release that is
the newest non-Bot comment, or by editing the marker out of the body.
