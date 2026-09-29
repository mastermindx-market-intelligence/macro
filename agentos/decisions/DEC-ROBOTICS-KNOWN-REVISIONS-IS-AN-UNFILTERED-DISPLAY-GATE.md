---
key: ROBOTICS-KNOWN-REVISIONS-IS-AN-UNFILTERED-DISPLAY-GATE
question: "In the Robotics composer, `known_revisions` gates both a limitations count and whether an interpretation block's prose is served. Another seat withdrew its earlier acceptance that it is count-only. Is the behaviour a designed retention contract, as RBV-18 was, or a defect - and if a defect, what exactly is defective?"
answer: >
  SPLIT RULING, and the split is the point. The WITHHOLDING is DESIGNED and
  stays. Its INPUT SET is a CONFIRMED DEFECT with three distinct symptoms.
  RULING 14, in two halves.
  (14a) `_inputs_known` returning false withholds the whole block rather than
  labelling it through, and counts it once as `interpretation_inputs_absent:<n>`
  without naming anything. That passes the ruling-11 design test on both legs:
  a contract is STATED at robotics_theme_research.py:531-536, citing its own
  authority (#7780 comment 5814333887 §4) and drawing the boundary against the
  visible `[stale interpretation]` case; and a PIN NAMES THE BEHAVIOUR -
  tests/test_robotics_research_temporal.py:302 is
  `test_interpretation_with_an_input_absent_from_the_bundle_is_withheld`. So an
  input the bundle does not carry is correct behaviour, not a bug. Do not
  "fix" it.
  (14b) What IS defective is how the set is BUILT. At :400-402 `known_revisions`
  is a comprehension over `bundle.assertions` with NO scope, NO rights and NO
  time filter, and it is then used as a DISPLAY gate at :530, not merely as a
  counter at :404. Nothing in the contract covers the construction and no pin
  names it. Three consequences, all CONFIRMED DEFECTS:
  (i) POINT-IN-TIME VIOLATION, the severe one. A record recorded AFTER a
  replay's cutoff still populates `known_revisions`, so `_inputs_known` passes
  and the block reaches the `system_replay` branch at :532 where only the
  BLOCK's own `reviewed_at` is compared to the cutoff. A replay's served text
  therefore depends on whether a post-cutoff record happens to sit in the
  bundle. Two different outputs for one cutoff is precisely what a replay
  exists to prevent, and the house law is explicit that the decision boundary
  binds and live-vs-replay must be declared.
  (ii) MISATTRIBUTED CAUSE. The count at :404 runs over every block with no
  `time_mode` awareness, so a block excluded for a TIME reason is reported as
  `interpretation_inputs_absent`. The served set is right; the limitations line
  names the wrong reason, which is worse than silence because a reader acts on
  the named cause.
  (iii) CROSS-SCOPE DISPLAY EFFECT, the same family as ruling 12. A block
  citing another slice's record is marked stale rather than scoped out or
  declared. Conditional on the bundle being slice-scoped, which is exactly
  where the missing filter belongs.
  REMEDY, and deliberately not a new one: adopt the shape of the Energy seat's
  R-ENE-31 at 3c775ea592a6 - build the set over records that pass scope,
  cohort, rights and time BEFORE review, and gate both the count and the served
  list through ONE helper keyed on the block's review time. Robotics cannot
  take it as a hotfix because #8013 removed the composer from `main`, so 14b is
  a RE-LAND OBLIGATION on the Robotics carrier, not a separate PR. Do not fork
  a Robotics-local variant of a shared helper to get there sooner.
rationale: >
  Three things made this worth a record rather than a comment.

  First, it is the third time in this operation that a COUNT was mistaken for
  the whole effect. The earlier instance was mine: I counted six
  `notices.append` sites in the theme-graph guard and called that the notice
  taxonomy, missing four `notices +=` merges and a seventh designed class. Here
  another seat read `known_revisions` as feeding only the `absent` count at :404
  and missed that the same predicate gates prose at :530. The general lesson is
  the same both times - enumerate a symbol's READ SITES, not its most obvious
  one - and it is why 14a and 14b had to be separated before either could be
  judged.

  Second, the ruling-11 test earns its keep here. Ruling 11 held that RBV-18
  retention is a designed contract; ruling 12 held that a cross-scope
  `_correction_lineage` walk is a defect; the test that separated them was
  "contract stated in a docstring or comment AND a pin whose NAME states the
  behaviour". Applied here it cleanly splits one mechanism into a designed half
  and a defective half, which is a stronger result than either a blanket
  "designed" or a blanket "defect" - and it is why this record refuses to
  ratify the whole mechanism just because part of it is pinned. A pin on the
  withholding is not a pin on the input set.

  Third, symptom (i) is not a display nit. A replay whose text depends on a
  record created after its own cutoff is unfalsifiable as evidence: you cannot
  tell from the output whether you are seeing the state at the cutoff or the
  state as later amended. Every other symptom here degrades a label; this one
  degrades the guarantee the replay mode exists to provide.

  On provenance: the Energy seat found and reported the mechanism (#7870
  comment 5866433049 item 4) and withdrew its own earlier "count-only"
  acceptance. I reproduced the call sites on a composer whose sha256 I verified
  byte-identical at two refs, confirmed its correction, and then ruled on the
  part it explicitly left to this seat. Its R-ENE-31 is adopted as the reference
  shape rather than replaced, because a second remedy for one defect in a shared
  pattern is how two verticals drift apart.
alternatives:
  - option: "Rule the whole mechanism DESIGNED, since the withholding is contracted and pinned."
    why_not: >
      This is the failure the record exists to avoid. The pin
      (`test_interpretation_with_an_input_absent_from_the_bundle_is_withheld`)
      names what happens WHEN an input is unknown; it says nothing about which
      records make an input known. The contract comment at :531-536 is likewise
      about the refusal, not the set. Ratifying the construction on the
      strength of a pin covering the consequence is how a defect acquires a
      certificate.
  - option: "Rule the whole mechanism a DEFECT and remove the withholding."
    why_not: >
      Refuted by the stated contract and its named pin, and it would regress a
      rights guarantee: an input the bundle does not carry is what an upstream
      rights drop looks like from inside the composer, and labelling such a
      block through would publish prose whose evidence was withdrawn. The
      `[stale interpretation]` path exists for inputs that are present but not
      live; conflating the two loses the distinction the comment draws.
  - option: "Hotfix 14b on `main` now, ahead of the re-land."
    why_not: >
      Not possible and not desirable. #8013 removed
      engine/market_ontology/robotics_theme_research.py from `main`, so there is
      no file on `main` to patch; and ruling 10 forbids landing any subset of
      the reverted paths ahead of the whole carrier. A hotfix would be a split
      re-land wearing a bug-fix label.
  - option: "Write a Robotics-local replacement for the shared `_le` helper and the review-time filter."
    why_not: >
      Rejected on the same ground as the Robotics-only framework prohibition. A
      second implementation of one shared predicate is how two verticals answer
      the same question differently; and the base defect in `_le` belongs to the
      shared owner. Robotics guards its own call site and adopts R-ENE-31's
      shape.
  - option: "Defer the whole question until #7870 merges and the composer is back on main."
    why_not: >
      The measurement does not need the file on `main` - it needs a blob, and
      the blob is readable at two refs and verified byte-identical between them.
      Deferring would have let the re-land carrier ship without the obligation,
      which is the same mistake as re-landing 35 paths with no CI wiring.
evidence:
  - "engine/market_ontology/robotics_theme_research.py fetched at BOTH a1c8968f8e2f and 36efe9c92b96 via gh api contents | base64 -d: 60749 B at each, sha256 7dcdbee913af67d7... identical at both refs, so the reading is ref-independent. grep -n known_revisions returns EXACTLY two lines - :400 (the comprehension over bundle.assertions) and :549 (the membership test inside _inputs_known) - and grep -n _inputs_known returns three - the def at :547 and the two callers at :404 and :530. So the predicate is read by a counter AND by a display path, which is the correction this record confirms."
  - "sed -n 400,410p: `self.known_revisions = {item.get(\"curation_revision\") for item in bundle.assertions if isinstance(item, Mapping)}` - no scope, rights, cohort or time predicate appears in the comprehension - immediately followed by `absent = sum(1 for block in bundle.interpretation_blocks if not self._inputs_known(block))` and `if absent: self.limitations.add(f\"interpretation_inputs_absent:{absent}\")`. The count runs over every block with no reference to self.query.time_mode, which is symptom (ii) read directly off the source."
  - "sed -n 526,556p: inside interpretation_blocks(), `if not self._inputs_known(block): continue` at :530-543 carries the contract comment citing 'Sol #7780 5814333887 §4: refusal includes dependent prose', stating the block is WITHHELD and 'counted once in limitations', never labelled through, and that 'Inputs that are present but not live stay the visible [stale interpretation] case'. The `system_replay` branch that follows at :532-535 tests ONLY `block.get(\"reviewed_at\")` against self.query.recorded_cutoff - never the revision's own recording time - which is symptom (i)."
  - "tests/test_robotics_research_temporal.py at a1c8968f8e2f, 20345 B: the pin at :302 is named test_interpretation_with_an_input_absent_from_the_bundle_is_withheld and its comment cites the same authority packet (#7780 5814333887 §4). The test immediately above it asserts the CONTRASTING case at :295-297 - item[\"stale\"] is True, text startswith '[stale interpretation] ', 'interpretation_stale' in limitations - so both sides of the contract's boundary are pinned. Both legs of the ruling-11 design test are therefore satisfied for 14a and neither is satisfied for 14b."
  - "Provenance and independence: the mechanism was reported by another seat on #7870 comment 5866433049 (2026-09-28T08:37:33Z), item 4, which also WITHDREW that seat's own earlier count-only acceptance and named tests/test_robotics_research_temporal.py:302 and the reference fix R-ENE-31 at 3c775ea592a6. This seat reproduced every call site independently before ruling, and ruled only on the part that comment explicitly left to the Robotics owner. Answered on the same carrier as #7870 comment 5866989985, read back byte-identical."
affects:
  - "WS:GMI-THEME-GRAPH"
  - "engine/market_ontology/robotics_theme_research.py"
  - "tests/test_robotics_research_temporal.py"
confidence: high
reversibility: easy
decided_by: "session 17c9f82c-8981-43d5-bf95-307691cb27cd (principal seat, operation gmi-robotics-fable-ceo-e2e-20260923-chairman-001)"
decided_at: 2026-09-28
---

# What a successor must not re-derive

`known_revisions` has exactly two read sites and one of them is a display gate. Any future
reading that treats it as a counter is wrong, and the reason it is easy to get wrong is that the
count at `:404` sits eleven lines from the comprehension while the display gate at `:530` sits a
hundred and thirty lines away. Enumerate read sites.

# The falsifier

14a is falsified if the contract comment at `:531-536` or the pin at
`tests/test_robotics_research_temporal.py:302` is removed or renamed such that the withholding is
no longer stated and named - at which point the behaviour loses its ruling-11 warrant and must be
re-judged, not grandfathered.

14b is discharged when, at the Robotics re-land head, `known_revisions` is built from records that
have passed scope, cohort, rights and time, and one helper keyed on the block's review time gates
both the `interpretation_inputs_absent` count and the served list - with a pin that fails when a
record recorded after a replay's cutoff changes that replay's served text. It would be REFUTED as
a defect only by a contract statement, somewhere in the composer or its pins, that a replay's text
is *intended* to reflect records recorded after its own cutoff. No such statement exists at
`a1c8968f8e2f`.

**WITHDRAWN, 2026-09-28, from an earlier version of this paragraph: the second half of that
sentence claimed "the route's own comment at `app/theme_research.py:384-388` points the other
way". It does not, and it was cited at a ref where the file does not exist.** Measured, with
`agentos/README.md` at 11115 B as a positive control that resolved at every ref: `app/theme_research.py`
exists ONLY at `a0d7b054ff23`, #7870's head, at 34786 B / 761 lines, and returns 404 at `main`
`05b242506be7`, at the revert parent `36efe9c92b96`, at `a1c8968f8e2f` and at the revert
`e5512ef66a74`. At the one ref where it does exist, `:384-388` reads: "A row this transport cannot
read is WITHHELD, never fatal. Before this, ``assertion.get(...)`` raised AttributeError, the
route's catch-all turned it into a 503, and one malformed row from the owner took down the entire
request instead of dropping itself. Withholding is the fail-closed answer; 503 is not." That is a
statement about withholding an unreadable row instead of returning 503 -- it is evidence for
**14a**, the designed half of this split, and it says nothing about replay cutoffs. The file's
`recorded_cutoff` / `system_replay` mentions sit at `:157` `:161` `:196` `:198` `:219`, nowhere near
the cited range. The pillar is withdrawn rather than re-aimed.

**14b's classification is unaffected, and this is why the withdrawal is safe to state plainly.**
It rests on ruling 11's test applied to the pins directly: `known_revisions` is built with no
scope, rights or time filter, and the pin that exists names the *consequence* (a withheld block)
rather than the *input set*. A pin on the consequence is not a pin on the input set, so the
unfiltered construction is unpinned and therefore not designed. The route comment was offered as
corroboration and was never load-bearing; removing it leaves the ruling standing on the
measurement that actually supports it.

One generalisation earned by this correction, because it explains all five bad anchors found in
this packet on 2026-09-28: **#7870 introduces the entire shared route / registry / restart
surface.** `app/theme_research.py`, the `engine/market_ontology/` group of the deploy restart ERE,
`theme_research_mounts.py` and `theme_research_registry.py` all exist at `a0d7b054ff23` and at no
other ref probed. Any anchor into that surface resolves only at #7870's head, so cite that ref
explicitly or the citation is unresolvable -- and locate by symbol or string, never by line.

Symptom (iii) carries one extra precondition worth stating: it is a defect only if the bundle is
slice-scoped. If a bundle deliberately carries every slice's assertions, then citing another
slice's record is not a scope escape and (iii) collapses into (i). Measure the bundle's scope
before acting on (iii).

## Refinement 2026-09-28: the remedy is smaller and the ruling is stronger

This record named R-ENE-31 (`3c775ea592a6`, another vertical, another carrier) as "the reference
fix". That understated the finding and pointed the implementer out of the class. Measured in
`engine/market_ontology/robotics_theme_research.py` at `36efe9c92b96` -- locate by string, line
numbers are revision-stamped hints:

* `self.known_revisions = {` (`:400`) comprehends **`bundle.assertions`**, the raw bundle, with no
  scope, rights, cohort or time predicate -- and it sits **two lines after**
  `self.assertions.sort(...)` (`:397`). The admitted set already exists when the comprehension
  runs; the comprehension steps around it.
* `def _now_of_query` (`:436`) already resolves the query's effective time, under an explicit
  contract comment: *the replay cutoff when present, else the newest review stamp inside the
  selection -- never the wall clock, so a composition is reproducible.*
* `def _review_excluded` (`:443`) consumes it and raises `review_expired_present`.
* `def _inputs_known` (`:547`) tests `ref in self.known_revisions`, so the set gates served prose.

Disjointness control: `_now_of_query`, `_review_excluded` and `review_due_at` occur **0 times** in
the shared `app/theme_research.py` and **0 times** in
`engine/market_ontology/semiconductor_theme_research.py` at `a0d7b054ff23`, and **twice each** in
the Robotics composer. The gate is the vertical's own, not inherited -- so this is not a base
defect and it is not semiconductor's.

**What changes.** Apply ruling 11's test to the two paths side by side: the time-aware path carries
a contract statement in a comment, the unfiltered path carries neither a comment nor a pin naming
its input set. So 14b is not a missing capability that needs a filter imported from a sibling
vertical -- it is **one of two consumers in the same class bypassing a documented mechanism 36
lines below it**. The remedy: build the set from the admitted selection and resolve any time
predicate through `_now_of_query()`, never a second notion of "now". Ordering permits it.

**What does not change.** 14b remains a **CONFIRMED DEFECT**. Only its strength and the size of its
remedy move, both toward less work. R-ENE-31 remains a valid cross-check on the shape and is no
longer the reference.

Falsifier: a ref where `_now_of_query` is absent from the Robotics composer, or where the
`known_revisions` comprehension already references it. So-what: without this, an implementer
rebuilds a mechanism the class already documents, which the Executive contract forbids.
