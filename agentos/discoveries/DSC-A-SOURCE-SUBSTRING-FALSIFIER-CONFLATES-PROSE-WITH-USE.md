---
key: A-SOURCE-SUBSTRING-FALSIFIER-CONFLATES-PROSE-WITH-USE
claim: >
  A falsifier that asserts a forbidden token is ABSENT from a function's raw source text cannot
  distinguish a USE of that token from prose ABOUT it, so it fires on the comment that documents why
  the forbidden path is not taken - and therefore penalises exactly the worker who explained
  themselves. Measured 2026-09-25 on Mastermind IAC-P1 C-A. The reviewer's instrument asserted
  `"EFFECT_UNKNOWN" not in ast.get_source_segment(SOURCE, _dispatch_read)`. The repaired code was
  correct: both uncertain read legs assign the string `"CARRIER_RECONCILIATION_REQUIRED"` and neither
  assigns `EFFECT_UNKNOWN`. The only occurrence was the comment `... instead of leaking an exception
  through the gateway as EFFECT_UNKNOWN.` The falsifier stayed red at the repaired head, and taken at
  face value it would have been published as "C-A-4 not fixed" - a false defect report against
  correct work. The same class of bug sat in the reviewer's own gate script, whose new-test counter
  matched `^+def test_` but not `^+async def test_`; in an async-heavy suite it reported 2 new tests
  where there were 8, which would have turned an exact count reconciliation (1969 + 8 + 0 = 1977)
  into a phantom six-test discrepancy.
falsifier: >
  Run the source-text falsifier against a head where the forbidden construct is genuinely absent but
  is NAMED in a comment or docstring. If it still fails, it is measuring prose. Convert it to an AST
  walk over `ast.Constant` / `ast.Name` / `ast.Attribute` nodes - comments and their text are absent
  from the AST, which is the property that makes the check sound - then re-control at two points: the
  rewritten falsifier must still FAIL at the unrepaired parent and PASS at the repaired head. A
  rewrite that passes at the parent has been neutered, not fixed. For a diff-line counter, positive
  control it against a known-count change that uses every declaration form the language allows.
  Historical targets: integrations/company_consultation_dispatch.py and instrument_p1c.py; the comment-match and async-def counter corrections are recorded in https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5828478882.
so_what: >
  Static instruments are themselves code under test, and a red falsifier is not self-validating
  evidence of a defect. Before reporting any structural finding, confirm the instrument discriminates
  the thing it claims to measure - otherwise a reviewer's tooling produces confident false accusations
  that cost a worker a whole repair round. Text-level absence checks are the wrong shape for any
  language with comments; assert over the parsed tree. And any instrument figure that feeds an
  arithmetic reconciliation must be positive-controlled first, because a miscount there does not look
  like a broken instrument - it looks like a broken worker.
kind: landmine
verified_at: 2026-09-25
verified_by: >
  Historical author-recorded verification dated 2026-09-25; supporting receipt: https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5828478882.
  The C-A receipt records an EFFECT_UNKNOWN source search matching a comment and a counter omitting async def declarations, reporting two new tests instead of eight.
scope:
  - "Mastermind historical IAC-P1 C-A donor evidence (2026-09-25)"
  - "integrations/company_consultation_dispatch.py"
  - "historical instrument_p1c.py"
confidence: verified
---

## Historical provenance — 2026-09-25

The measurements, confidence and verification date above describe the original September 25 observation. The November 6 record repair validates document structure and preserves source references; it does not rerun the historical experiment or establish current runtime behavior. The supporting [original receipt](https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5828478882) records the historical evidence.

The [later canonical lineage ruling](https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5841164702) designated claude/iac1-p1-packet-carriage-20260925 as **DONOR_TEST_EVIDENCE / DO_NOT_PUBLISH_AS_P1**, with [Mastermind #986](https://github.com/mastermindx-market-intelligence/Mastermind/pull/986) the canonical P1 carrier. Its held C-D child remained STOP / DO_NOT_PUBLISH. These knowledge records grant no transplantation, installation, live-packet or replay authority; all original refused or uncertain effects retain their original target and reconciliation boundary.
