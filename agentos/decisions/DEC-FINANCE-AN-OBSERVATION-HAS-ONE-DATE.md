---
key: FINANCE-AN-OBSERVATION-HAS-ONE-DATE
question: >-
  An owner observation can carry two knowledge clocks, as_of and observed_at. The Finance
  composer's plane clock and valuation anchor dated a row by as_of, else observed_at, while
  its rankings, expectations history, freshness and common_as_of read as_of alone, and a
  timestamp whose date and time a space separates was an instant to the knowledge gate but no
  date to any reader. Which date does an observation have, and how does the operating plane
  rank an observation that has none?
answer: >-
  An observation has one date, and every reader in the composer reads it through
  _observation_date: as_of when it reads as a date, else observed_at. A clock reads as a date
  when _parse_iso_date reads it, a date or a timestamp whose date and time a T or a space
  separates, and a timestamp's date is the one it was written in, never moved into UTC; the
  knowledge gate withholds a row by that same date. The same reading dates the clocks the
  document publishes beside a row's date (a plane clock's published_at and effective_at, a
  material change's effective_at), so a space-parted timestamp publishes its date there, never
  null. The history publishes that date as the contract writes a date (_observation_day). The
  operating plane publishes the freshest dated observation with a direction filed under the
  slice. An undated one counts as the oldest, as on the price plane, so it is still published,
  without a clock, when no dated one with a direction is filed under the slice. The date decides
  first: on one date an observation tagged with the slice outranks an untagged one, as the
  valuation anchor rules, and a full tie keeps the owner's order. The valuation anchor stays
  dated-only: its date is the information clock the contract requires of an anchor. The
  conflicts follow the readings, because they read the reading each plane publishes. Source
  records keep their own date (source.observed_at, scoped by business_scope), and the
  knowledge-cutoff gate still reads every clock a row carries.
rationale: >-
  Two readers of one row that each pick a date disagree silently, and the contract accepts both
  documents. An observation dated only by observed_at was dated in its plane's clock and undated
  in the ranking that chose it, so a stale row was published over a fresher one (D2, D4), and a
  consensus row's history copied a null or timestamp as_of, so the contract refused the whole
  document (D5). The operating plane also ranked an undated observation as date.max, above every
  dated one, which erased the conflict a dated reading would draw (D1). And a timestamp written
  with a space left its row undated to every reader although the gate read its instant (D7), and
  a published clock written that way was null in the document although the same timestamp parted
  by a T published its date (D8). One helper for every reader closes the class, not the six
  sites; the plane clock's rule was the one already accepted, so it became the helper.
alternatives:
  - option: >-
      give the operating plane the anchor's dated-only rule (the 09-27 handoff's suggestion)
    why_not: >-
      it withdraws a reading the plane publishes today whenever that reading is the slice's
      only operating observation; undated-as-oldest removes the defect (an undated row never
      outranks a dated one) without withdrawing the sole reading
  - option: >-
      date every reader by as_of alone, the rankings' rule
    why_not: >-
      the plane clock and the anchor already read observed_at and their tests pin it (N11,
      N12); an observed_at-only row would lose its clock and its anchor, and a sole reading
      dated only by observed_at would publish no date
  - option: >-
      observed_at first, as_of as the fallback
    why_not: >-
      it moves the accepted plane clock for every row that carries both clocks, changing
      published dates across all fixtures; the defect was disagreement between readers, not
      the precedence
  - option: >-
      keep per-reader date rules and document them in a table
    why_not: >-
      six readers drifted from one rule once already; a table does not stop the next reader
      from reading as_of directly, and a single helper makes the rule the only path
evidence:
  - "PR #8167: D1-D8 each reproduce on origin/main e2fb0a011661; the head's projection tests on main's composer: 31 failed, 200 passed, in seven of the eight new tests and the knowledge-cutoff test, whose clock table gains two rows (the eighth new test pins a rule main already honours, the date outranking the slice tag); its new and changed tests on round 1's composer: 16 failed, 50 passed, 165 deselected"
  - "mutants over the projection suite, each killed: N1-N12, round 2's own M-a to M-f (M-d to M-f, one per published clock, each killed by the published-clock test alone), and the three the read-only Opus review of round 1 predicted would survive (tag before date, observed_at before as_of, a raw observed_at in the history)"
  - "whole-document identity: over the 12 fixture compositions, main and the change compose byte-identical documents"
  - "PR #8167 MERGED 2026-09-29T04:34:58Z -> 867b6b87bd4b at head 3712eeddd926 (ci.yml 36520392031 success); main's blobs for its three files equal the head's, and the eight Finance suites on main 867b6b87's bytes: 504 passed, 1 skipped, 1 xfailed"
  - "eight Finance suites on #8167's final head (main e2fb0a011661 plus the change): 504 passed, 1 skipped, 1 xfailed (main 452 passed, 1 skipped, 1 xfailed)"
  - "deciding inputs (seat probe f2_decide.py, synthetic): seven readable forms of one date in a consensus as_of, from a space timestamp to a date object, are each refused on main (the history copied them raw) and each composed here"
  - "published clocks (seat probe space_clock_probe.py, synthetic): a space-parted timestamp in a plane clock's published_at or effective_at, or a material change's effective_at, published null on main and its date here; a source record's own clocks are copied raw, so the contract refuses a timestamp there on both"
affects:
  - WS:GMI-FINANCE-INTELLIGENCE
  - engine/sector_intelligence/finance_projection.py
confidence: high
reversibility: easy
decided_by: "seat 938d17d6 (Finance Intelligence CEO seat, operation gmi-finance-fable-ceo-e2e-20260924-chairman-001)"
decided_at: 2026-09-28
---

The ruling covers the Finance composer's observation readers. It does not decide which row
wins a full tie on the price and consensus planes (they take the first-listed row, the
operating plane and the anchor the last-listed), and it does not change how source records
are dated. The shared base's evidence_claim.v1 (#7870) may carry its own clocks; the
integration wave maps them onto as_of and observed_at, and this helper stays the only reader.
