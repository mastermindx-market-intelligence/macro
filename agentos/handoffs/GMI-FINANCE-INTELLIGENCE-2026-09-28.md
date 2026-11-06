---
workstream: "WS:GMI-FINANCE-INTELLIGENCE"
session: "seat 938d17d6 (worktree .claude/worktrees/finance-intelligence-e2e-7c27cd); #8146 on claude/finance-limitations-known-evidence; #8159 on claude/ssd-finance-container-totality-4b0eb49fead48723; #8165 on claude/finance-container-review-answers; #8167 on claude/ssd-finance-observation-date-d8a6f2ab6d5eaf80; records on claude/ssd-finance-records-0928-36936d43f225abf5"
model: opus
ended_because: complete
mission: >
  Seat 938d17d6 holds gmi-finance-fable-ceo-e2e-20260924-chairman-001 end to end. T4-T7 stay
  HELD behind #7870, so this wave closed the composer items the 09-27 handoff left open:
  - #8146: the registration limitations read theme evidence through the composer's own gate,
    so owner_input_absent:theme_evidence is named when the cutoff withholds every assertion
    (the #8138 round-3 NIT).
  - #8159: an owner input reads the same whatever container holds its rows. Six containers
    changed what the document said (R1-R6: generators, a nested generator, a deque, a set, a
    mapping keyed by a number and by text). Owner inputs are now read once at entry, receipts
    come from the gate's own tally, and the digest hashes content, not containers.
  - #8165: the answers to #8159's independent review, which returned FIX_REQUIRED with no
    blocker or major finding. The sweeper merged #8159 on concluded checks before the answers
    were pushed, so they shipped as a follow-up: two crashes #8159 introduced (F1, F2), pins
    for the two mutants that survived every suite, and the stated bounds.
  - #8167: an observation has one date, and every reader reads it through one helper (D1-D8);
    the operating plane's ranking rule is stated and pinned
    (DEC:FINANCE-AN-OBSERVATION-HAS-ONE-DATE). A read-only Opus review of round 1 returned
    FIX_REQUIRED with three MINOR findings; round 2 answered all three and pinned three published
    clocks the parser fix moved (D8).
state_before: >
  At the 2026-09-27 checkpoint (handoff GMI-FINANCE-INTELLIGENCE-2026-09-27; its records PR
  #8145 MERGED bbcdc58d8add), T1-T3, T8-T11 and the composer follow-ups #8113, #8121, #8130,
  #8134, #8135 and #8138 were merged. The page stayed NOT CONNECTED (FI_READ_URL = "") and
  T4-T7 stayed HELD. Open: the two #8138 round-3 NITs, the container-totality lane, and the
  optional date rule for the operating and price planes.
changed:
  - path: engine/sector_intelligence/finance_research_registration.py
    what: "#8146 (MERGED 3b9a451f7085): _build_limitations names owner_input_absent:theme_evidence from _known_assertions, the rows the composer's cutoff gate kept, not from the raw inputs."
  - path: engine/sector_intelligence/finance_projection.py
    what: "#8159 (MERGED a4236bb07f88): _drained_inputs reads every one-shot iterator once at entry, recursing through mappings, lists and tuples; a container is rebuilt only if it held an iterator. _known_rows counts the rows it read and kept (_RowCount), and a receipt reads DEGRADED when the gate read rows and kept none; _known_at_cutoff returns (known, withheld). _digest_form hashes content: a set sorted by its members' JSON, a mapping whose keys are not all text as [key, value] pairs, any other iterable as a list, anything else as str(). #8165 (MERGED e2fb0a011661): _digest_form hashes an iterable whose iter() raises TypeError as its str() (F1), and _drained asks Mapping before Iterator (F2); both docstrings state their bounds. #8167 (MERGED 867b6b87bd4b): _observation_date (as_of, else observed_at) and _observation_day are the only readers of an observation's date: the plane clock, the valuation anchor, the operating, price and consensus rankings, the consensus and guidance history, the slice's freshness and common_as_of. The operating plane publishes the freshest dated observation; an undated one counts as the oldest; on one date the slice-tagged one outranks an untagged one; a full tie keeps the owner's order. The valuation anchor stays dated-only. _parse_iso_date falls back to datetime.fromisoformat and keeps the date a timestamp was written in (never moved into UTC), so a timestamp parted by a space dates its row, the gate's day read and three published clocks (a plane clock's published_at and effective_at, a material change's effective_at)."
  - path: tests/test_finance_research_registration.py
    what: "#8146: a test whose cutoff withholds every assertion requires owner_input_absent:theme_evidence."
  - path: tests/test_finance_intelligence_projection.py
    what: "#8159: 29 cases over the six containers (generator, nested generator, deque, set, mixed keys), receipts and digest identity. #8165: 11 cases: emptied row lists read READ (3), rows held in tuples compose the list document (6), F1, F2. #8167: eight new tests and two new rows in the knowledge-cutoff clock table, 52 cases (the suite collects 231 against main's 179): the operating ranking (undated, observed_at-only, the tag rule on one date, a fresher untagged over an older tagged), the price and consensus rankings by observed_at, a row dated by observed_at reads as the same row dated by as_of in every reader, a row reads as the date written in its clock however written (30 cases), and a published clock reads a timestamp as the date written however parted (3 cases)."
  - path: agentos/decisions/DEC-FINANCE-AN-OBSERVATION-HAS-ONE-DATE.md, agentos/handoffs/GMI-FINANCE-INTELLIGENCE-2026-09-28.md, agentos/workstreams/WS-GMI-FINANCE-INTELLIGENCE.md
    what: "This records PR: the one-date decision, this handoff, and the workstream's next_action."
verified:
  - claim: "#8146 merged and holds on main."
    command: "gh pr view 8146 --json state,mergedAt,mergeCommit; gh run list --workflow ci.yml --commit d7901433127d252ada4218a61e6ff5ca5b7786b2; the eight Finance suites on main's bytes at a4236bb07f88's parent chain"
    result: "MERGED 2026-09-29T01:31:10Z -> 3b9a451f7085 (ci.yml 36506727223 success on d7901433127d). On its own lane: 412 passed, 1 skipped, 1 xfailed (main 411); mutants M1 (the builder reads the raw inputs) and M2 (compose passes the raw assertions) each killed by the new test only."
  - claim: "#8159 merged and holds on main."
    command: "gh pr view 8159 --json mergedAt,mergeCommit,headRefOid; gh run list --workflow ci.yml --commit 5376cc222047d156e883a8916e0b315af93278b7; git show cfbd16e8d979:<file> blob-compared with the lane's two files; the eight Finance suites on main's bytes cfbd16e8d979"
    result: "MERGED 2026-09-29T02:02:27Z -> a4236bb07f88 by the sweeper at 5376cc222047 (its update-branch of the round-1 head d922bb81ec87 with main 8cf49d5bb338; ci.yml 36509072012 success). Eight suites on main cfbd16e8d979: 441 passed, 1 skipped, 1 xfailed."
  - claim: "#8165 answers #8159's review: F1 and F2 crash on main and compose here; every mutant is killed."
    command: "python3 scratchpad/r2_repro.py on main cfbd16e8d979 and on the lane; scratchpad/ct2_checks.py with BASE=main7_bytes (the eight suites, the red proof, 11 mutants, fixture identity, record -k selections)"
    result: "Eight suites 452 passed, 1 skipped, 1 xfailed (main 441). Red proof: 2 failed (F1, F2), 9 passed (the pins for rules main already follows). 11 mutants killed, including the review's two survivors (3 and 6 failures). Identity 12/12. Selections 59/14/8/9/0/0 unchanged. MERGED 2026-09-29T03:01:01Z -> e2fb0a011661 at 8d39cde62fc1 (the sweeper's update-branch of the answers head d304a0248718 with main 9487ec33b322; ci.yml 36513427899 success, ci-gate SUCCESS); main's blobs for both files equal the PR head's."
  - claim: "#8167: D1-D8 reproduce on main and are fixed; every mutant is killed; the documents are unchanged."
    command: "BASE=main7_bytes python3 scratchpad/pe3_checks.py e2fb0a011661 d10b114b3a7d (the eight suites, the red proof on main's and round 1's composers, 23 mutants, fixture identity, record -k selections); scratchpad/pe3_extra.log (the new test functions, the DSC falsifier with main's test, agentos validate)"
    result: "Eight suites 504 passed, 1 skipped, 1 xfailed (main e2fb0a011661: 452). Red proof: 31 cases fail on main's composer, in seven of the eight new tests and the knowledge-cutoff test; the eighth new test pins a rule main already honours (the date outranks the slice tag) and kills M-i. On round 1's composer the new and changed tests fail 16 cases. 23 mutants each killed (round 2's M-a to M-f, the review's three predicted survivors and a variant, the anchor's own rule M-v, N1-N12). Identity 12/12. Only DSC:A-KNOWLEDGE-CUTOFF-BINDS-ONLY-THE-READERS-THAT-APPLY-IT's selection moves (59 -> 63); its falsifier on #8135's composer: 51 failed, 12 passed (49 failed, 10 passed with main's test). agentos validate: 0 errors. MERGED 2026-09-29T04:34:58Z -> 867b6b87bd4b at head 3712eeddd926 (ci.yml 36520392031 success); main's blobs for the three files equal the head's, and the eight Finance suites on main 867b6b87's bytes: 504 passed, 1 skipped, 1 xfailed. The sweeper update-branched the pushed head d10b114b3a7d once, to 3712eeddd926, a clean merge of main that changed none of the three files; the seat merged that head with --match-head-commit on a passing fence."
  - claim: "A malformed owner container crashes the composer at 70 of 184 shapes on the default fixture, each failing closed."
    command: "python3 scratchpad/container_probe.py <main cfbd16e8d979 bytes> default (every owner container replaced in turn by a mapping, list, text, number or None; outcome = crash, contract refusal, or contract acceptance)"
    result: "184 shapes: 70 crash, 14 refused by the contract, 100 accepted. The crashes group by the composer function that raised: _slice_inputs_for 21, _company_row_for_issuer 12, _extract_source_record_extras 10, a slice-catalog generator expression 6, _operating_reading 4, and 17 across seven smaller sites (_hash_inputs, _outer_dossier_ref, _conflicts_for, _company_rows, _source_records_block, _coerce_rights_state, _basket_state_for). 42 of the 70 replace a whole input field; the other 28 replace a container inside owner records (a source record, an identity binding, a catalog entry, a packet's cells, a slice's rows or basket)."
unverified:
  - claim: "The connected page renders a real owner document end to end."
    what_would_verify: "A production read route (T7, HELD) and FI_READ_URL set; then the 1440/390 x dark/light x EN/ZH + keyboard proof on live data."
unresolved:
  - "T4-T7 stay HELD by the Chairman directive until #7870 (the Semiconductors shared base) merges; #7870 is still DRAFT/HOLD (head a0d7b054ff23 at 2026-09-29T02:5xZ)."
  - "The Financials launch partial stays DORMANT until #7669 (basket_detail owner) merges; #7669 is DRAFT and CONFLICTING (head 2e6bea89cb32)."
  - "A malformed owner CONTAINER still crashes the composer (70 of 184 shapes on the default fixture). Every crash fails closed, but one bad packet takes the whole document down. The integration adapter is the owner (next_actions)."
  - "Bounds of #8159, stated in #8165 and the docstrings: a structure nested deeper than the recursion limit raises RecursionError; a one-shot iterable that is not an Iterator, or a generator inside a deque or a set, is not read at entry; content hashing makes distinct Python inputs hash alike ({1: x} and [[1, x]]; a set and its sorted list); a cyclic structure raises; macro_context=iter(()) now composes with macro_rates_credit DEGRADED."
  - "On a full tie (one date, filed the same way) the price and consensus rankings publish the first-listed row (max), while the operating plane and the valuation anchor publish the last-listed (sort, take last). Not decided."
  - "A knowledge_cutoff padded with whitespace is read by the gate, which strips it, and refused by the contract, which does not. The document is refused, so nothing leaks (#8138 round-3 NIT)."
  - "Carried from 09-27 and still true: the T10 adapter does not adopt #7870's owner-bundle wire grammar; T10 _try_resolve_assertion swallows any resolver failure; the 390 px phone card omits basis, retained risk and evidence date; the composer validates nothing at emit beyond its key walks; an untagged observation reaches every slice from whichever packet it sits in; a plane's evidence_refs is its slice's union; generation.rights_profile lists every family by name, internal_only included."
next_actions:
  - "When #7870 merges, open the integration wave: the adapter onto source_record.v1 / evidence_claim.v1 / sector_intelligence_packet.v1, then the T7 serving route once accepted, then FI_READ_URL, then a connected browser proof on live data. The T6 publish step MUST run validate_contract on the composed document before serving."
  - "In that adapter, refuse a malformed owner container per record, as a named omission, before compose. The composer crashes on 70 of 184 malformed container shapes (default fixture); the adapter is where one bad packet can be dropped without dropping the document. Re-run scratchpad-style container_probe over the adapter's output to prove zero crashes."
  - "When #7669 merges, wire the Financials launch include as a one-line guarded include."
  - "Carry the deferred review MINORs and the T10 gaps into the integration wave (the 09-24 and 09-27 handoff lists)."
  - "In that adapter, write a source record's own clocks (source.observed_at, source.published_at) as dates. The composer copies them as the owner wrote them, and the contract refuses any timestamp there, however it is parted (#8167 probe, space_clock_probe.py)."
do_not_redo:
  - "Every do_not_redo entry of GMI-FINANCE-INTELLIGENCE-2026-09-27 still binds."
  - "Read owner inputs once, at entry (_drained_inputs). Never let a reader, the cutoff gate or the digest iterate an owner container on its own: a generator read twice is empty the second time."
  - "Derive receipts from the gate's tally (_RowCount), never from len() of an owner container."
  - "The digest hashes content through _digest_form. Never json.dumps(default=str) an owner structure into the digest: it hashes a generator's address, a deque's repr and a set's iteration order."
  - "Date an observation only through _observation_date / _observation_day. Never read as_of or observed_at directly in a new reader (DEC:FINANCE-AN-OBSERVATION-HAS-ONE-DATE)."
  - "The valuation anchor is dated-only and the operating plane counts an undated observation as the oldest. The difference is deliberate: an anchor needs an information clock, and the operating plane must not withdraw a slice's only reading. Do not unify them."
  - "#8159's review is answered in full by #8165. Do not re-open or revert #8159 for it."
danger_areas:
  - "Every danger_areas entry of GMI-FINANCE-INTELLIGENCE-2026-09-27 still applies."
  - "_drained asks Mapping before Iterator. A new container check placed before the Mapping check drains a mapping that is also an iterator into its keys (F2)."
  - "_digest_form hashes an iterable whose iter() raises TypeError as its str() (a 0-d array). Removing that fallback crashes the digest (F1)."
  - "Content hashing collides distinct Python inputs. A reader that treats a set differently from a list, or a numeric-keyed mapping differently from its pairs, could compose different documents under one input digest."
  - "Two rules of #8159 were right on main but unpinned, and only a mutant run showed it. Mutation-test a new composer rule over the projection suite before calling it pinned."
  - "The merge sweeper merges an armed PR on concluded checks whether or not a self-commissioned review is still running. A verdict that lands after the merge ships as a follow-up PR (#8165 for #8159)."
  - "gh fails from the scratchpad (not a git repository) before any API call; run gh from a checkout."
  - "_parse_iso_date keeps the date a timestamp was written in. Reading it as its UTC date (M-c) moves a row across the knowledge-cutoff day; do not normalize to UTC."
  - "_coerce_date is the only date parser. A new published clock read any other way publishes null for a timestamp parted by a space (D8); the published-clock test pins the three that exist."
  - "A mutant's anchor can match more than one site: the operating plane and the valuation anchor share their sort lines. Assert every anchor is unique before a mutation run (the round-2 harness died on one)."
---

# Finance Intelligence — wave checkpoint 2026-09-28 (seat 938d17d6)

The composer items the 09-27 handoff left open are closed: #8146 (limitations read the gate),
#8159 with its review answers in #8165 (containers), and #8167 (one date per observation). What
remains is gated on other owners: #7870 for the integration wave (T4-T7) and #7669 for the
Financials launch include. The page stays NOT CONNECTED by design.

## Merges

| PR | lane | merged | main SHA | binding CI | proof rung |
|---|---|---|---|---|---|
| #8145 | records: 09-27 checkpoint | 2026-09-28T10:15:10Z | bbcdc58d8add | ci.yml 36407574488 | MERGED (records only) |
| #8146 | limitations read theme evidence through the gate | 2026-09-29T01:31:10Z | 3b9a451f7085 | ci.yml 36506727223 | MERGED + verified on main (no production reader) |
| #8159 | an owner input reads the same whatever container holds its rows | 2026-09-29T02:02:27Z | a4236bb07f88 | ci.yml 36509072012 | MERGED + verified on main (no production reader) |
| #8165 | #8159's review answers | 2026-09-29T03:01:01Z | e2fb0a011661 | ci.yml 36513427899 | MERGED + verified on main (no production reader) |
| #8167 | one date per observation | 2026-09-29T04:34:58Z | 867b6b87bd4b | ci.yml 36520392031 | MERGED + verified on main (no production reader) |

## #8146: limitations read the gate

#8138's round-3 review left a NIT: when the cutoff withheld every theme-evidence row, the
registration envelope's limitations omitted `owner_input_absent:theme_evidence`, because
`_build_limitations` read the raw inputs. It now reads `_known_assertions`, the rows the
composer's own gate kept. The fix was the reviewer's own proposal and touches three lines, so
no second review ran; one red test and two mutants (the builder reads the raw inputs; compose
passes the raw assertions), each killed by the new test only, are the check.

## #8159 and #8165: containers

Six owner containers changed what the document said (R1-R6). R1-R4 were #8138's deferred
round-2 findings: a receipt read READ over a generator whose every row the cutoff withheld
(fail-open), a generator of theme evidence hashed like empty evidence, a nested generator hashed
by its address, and a deque hashed unlike the same rows in a list. R5 (a set hashed by the hash
seed) and R6 (a mapping keyed by a number and by text crashed) are the same class, so #8159 took
them too and said so. The fix reads owner inputs once at entry, takes receipts from the gate's
own tally and hashes content, not containers; every input a JSON adapter can produce hashes as
before (12/12 fixture digests unchanged). One of its seven mutants (pair keys written as text)
survived the first draft, because its test compared pairs with an object; the test now compares
two pair-form mappings.

The independent Opus review of #8159's round-1 head `d922bb81ec87` returned FIX_REQUIRED with no
blocker or major finding. It found two crashes #8159 itself introduced (F1: an owner value that
declares iteration and refuses it, as a 0-d array does; F2: identity bindings in a mapping that
is also an iterator, drained into its keys), two mutants that survived all eight suites (a
receipt DEGRADED whenever the gate kept nothing; a drain over lists only), a depth bound, a
one-shot iterable the drain cannot detect, an over-broad claim that distinct inputs never newly
collide, and one unstated change (`macro_context=iter(())` now composes instead of raising). The sweeper merged #8159 on concluded checks while the answers were being
written, so they shipped as #8165: F1 and F2 fixed and red-proven, both survivors pinned, and
every bound stated in the PR and the docstrings.

## #8167: one date per observation

The composer dated one observation two ways: the plane clock and the valuation anchor read
`as_of`, else `observed_at`, and every other reader read `as_of` alone. A row dated only by
`observed_at` was therefore dated in its clock and undated everywhere else: a stale row was
published over a fresher one (D2, D4), and a consensus history copied a null or timestamp
`as_of`, so the contract refused the whole document (D5). The operating plane also ranked an
undated observation as `date.max`, above every dated one (D1), and broke a same-date tie by
owner order rather than by the slice tag (D3). A timestamp parted by a space was an instant to
the knowledge gate but undated to every reader (D7), and a published clock written that way
was null in the document (D8). Now one helper dates every reader
(DEC:FINANCE-AN-OBSERVATION-HAS-ONE-DATE). The 09-27 handoff suggested the anchor's dated-only
rule for the operating plane; the seat chose undated-as-oldest instead, because dated-only would
withdraw a slice's only operating reading. Every fixture composes byte-identically.

A read-only Opus review of round 1 (`741a5000`) returned FIX_REQUIRED with three MINOR findings
and no blocker or major: the docstring overstated the undated rule (F1), the gate read a
space-parted timestamp the date parser could not (F2), and the body's behaviour-change paragraph
was false and too narrow (F3). Round 2 answered each: the parser falls back to
`datetime.fromisoformat` and keeps the date a timestamp was written in, the docstring and the
body are corrected, and the three mutants the review predicted would survive are killed. The
parser fix also moved three published clocks (D8), which the seat measured and pinned with a
new test before pushing. No second review ran: the round-2 delta is one parser fallback, a
docstring and tests; all 23 mutants are killed; and the composer still has no production caller.

## The container probe

The 09-27 handoff recorded that the composer is not total over a malformed container. A probe
over main's bytes measured it on the default fixture: of 184 container shapes (every owner
container replaced in turn by a mapping, list, text, number or None), 70 crash, 14 are refused by
the contract and 100 compose documents the contract accepts. Every crash fails closed (nothing
is served), but one bad packet takes the whole document down. 42 of the 70 replace a whole input
field, which the integration adapter builds; the other 28 sit inside owner records. The seat
routed this to the integration adapter, which can drop one malformed record as a named omission
before compose, instead of making the composer total over shapes the shared base's contracts
will refuse at ingestion.
