---
key: SOURCE-CONTINUITY-CENSUS-PASS-CRITERION-FOR-MACRO-CARRIERS-OVER-THE-490-CAP
claim: >
  While the Macro repository holds more than 490 open pull requests, the official read-only
  Source Continuity verifier (Mastermind scripts/source_continuity.py, last changed 6eb1989d
  2026-09-25 "scale Macro census to 490 (#982)", _MAX_COLLISION_PRS = 490 at :77, refusal branch
  at :1337) refuses `verify --kind remote-complete` for EVERY Macro carrier with the typed refusal
  {"code":"REMOTE_CENSUS_INCOMPLETE","message":"remote proof census is incomplete","ok":false,
  "schema":"mastermind.source_continuity_refusal/v1"}, and that refusal carries no cause: it is
  one static string (control_plane/source_continuity.py:171) emitted from several sites
  (scripts/source_continuity.py:2181, :2197, :2217, :2276, :2298, :2615, :2680 and
  control_plane/source_continuity.py:661-662), one of which (:2615) fires on
  `not files_complete or not collisions_complete` and is not roster-size specific. No
  REMOTE_COMPLETE_VERIFIED receipt is obtainable for any Macro carrier until the Mastermind #346
  census-envelope series lands or the roster falls to 490 or fewer. The seat's recorded pass
  criterion for a substitute (#7870 comments 6106134520 section 1 (i)-(v) and 6106495383
  sections 3 and 5) therefore has five legs, each checkable by command: (1) head identity,
  git ls-remote == local HEAD == pulls/N head and the GitHub commit tree == HEAD^{tree};
  (2) ownership, fully paginated pulls/N/files == git diff --name-only <merge-base>..<head>,
  with the count; (3) attribution, an open-PR count above 490 read immediately BEFORE and
  immediately AFTER the run plus the run's logical-call, byte and wall totals inside the #346
  envelope (1,152 logical HTTP calls, 128 MiB, 300 s), because the refusal text does not say
  which site fired; (4) fingerprint, sha256 of the exact posted census bytes, not of a
  paraphrase; (5) one substitute per carrier per head, re-recorded at every head move. The
  acc72f3f run on #7870 does not satisfy leg (3); #8250's substitute at 1db9cad1 (#8250 comment
  6106395498) satisfies legs (1), (2) and (5) and leg (4) by shape only, because the hashed
  ls-remote line is paraphrased and the pulls/8250 read is summarized there.
falsifier: >
  A non-seat ruling on #7870 or #8250 (the Chairman or Sol, by cited comment or message id)
  that accepts a substitute lacking one of the five legs, or that requires the
  REMOTE_COMPLETE_VERIFIED receipt itself and no substitute (option B); or a run of
  scripts/source_continuity.py (cap check in control_plane/source_continuity.py) on a Macro
  carrier that returns REMOTE_COMPLETE_VERIFIED while the open-PR roster is above 490.
so_what: >
  Gate (4) of the #7870 and #8250 release DECISIONs has one checkable definition, written before
  the release-head re-run so the run is specified before it runs: read the roster immediately
  before and after, record the call/byte/wall totals, post the exact census bytes the fingerprint
  hashes, and re-record at every new head (a base-sync merge supersedes the substitute:
  SOURCE_CONTINUITY: SUBSTITUTE_SUPERSEDED_NEEDS_NEW_AT_<head>). The seat requests the non-seat
  ruling on the substitute and never rules it; raising the 490 cap is a protected-source change
  owned by the Mastermind #346 series, not a constant a carrier seat may tweak.
kind: constraint
verified_at: 2026-10-11
verified_by: >
  Fable 5.1 Meta-CEO seat (#7870 worktree semiconductor-theme-intelligence-b-impl-988406e131fd90b9
  on the external SSD; Mastermind main checkout read-only at c7e47c859eb2925c5626931fd511800773ba09ac).
  `/opt/homebrew/bin/python3 scripts/source_continuity.py verify --kind remote-complete` for
  operation gmi-semiconductors-fable-ceo-e2e-20260923-chairman-001, PR 7870, base main pinned at
  363b4e6296b7598ad8980b6a1b8b9444e14cfd6b, the 102 changed paths as owned paths, external effect
  NONE / dependency NONE, exited 2 with the quoted refusal at acc72f3f. `gh api graphql -f
  query='{repository(owner:"mastermindx-market-intelligence",name:"macro"){pullRequests(states:OPEN)
  {totalCount}}}'` read 632 at 2026-10-11T05:12:45Z, 634 at 05:59:21Z and 633 at 06:17Z.
  `grep -n _MAX_COLLISION_PRS scripts/source_continuity.py` -> :77 = 490; `grep -rn
  REMOTE_CENSUS_INCOMPLETE scripts/source_continuity.py control_plane/source_continuity.py` ->
  the definition at control_plane :171 and the emission sites listed in the claim. The criterion
  text is #7870 comments 6106134520 and 6106495383 (2026-10-11T07:03:50Z); #8250's substitute is
  comment 6106395498 at 1db9cad104437dc0c9bb4b27cf45781040302fb2; the envelope figures are
  Mastermind issue #346 and docs/superpowers/plans/2026-09-24-source-continuity-macro-490-scale.md
  ("491+ remains outside this successor and must fail closed").
scope: [macro, mastermind]
confidence: verified
---

## Detail

The verifier is correct to refuse: the census it needs cannot complete inside the #346 envelope
when the roster is above the cap, and it fails closed by design. The practical failure mode is
not the refusal but an under-specified substitute: a session that posts "ls-remote matches, the
files match, the roster was 632" has recorded legs (1), (2) and a paraphrase of (3), and a later
reader cannot tell whether the refusal came from the roster-size site or from budget exhaustion
or from an ownership gap. Leg (3)'s before/after roster reads and the call/byte/wall totals are
what attribute the refusal to the roster; leg (4)'s exact bytes are what make the fingerprint
recomputable by someone other than the poster.

The criterion is the seat's recorded request, not a ruling. Until the Chairman or Sol accepts a
substitute by cited id, every Macro carrier's release stays RELEASE_BLOCKED_PENDING_NON_SEAT_RULING
on this gate, and a head move voids the substitute recorded for the previous head.
