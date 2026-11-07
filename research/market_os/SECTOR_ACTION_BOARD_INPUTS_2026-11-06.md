# Captured action-board inputs and shared legacy adapters

## Qualified source scope

Base: Macro `4eddd4ad83f761d4178e1faa73173dccd71ed419`, original operation
`macro-always-on-shared-shell-20261105-c3`. The original board algorithms are unchanged
from the literal `b168ff4a498999251e70dc6a0076e422d2689738` source captured in the fixture.

This slice makes the existing Sector action-board calculation available over explicit
values. It does not acquire stock/sector analyses, complete the Sector producer, mount
a reader, transfer writers, deploy beta, or prove provider freshness.

## One calculation owner

`engine/sector_action_board.py` owns the existing narrative-basket reducer, Sector
lane reducer, display-field attachment and exact-basket-byte envelope. The original
`action_board`, `_action_board_stat_chip` and `_basket_as_of` source bodies are
byte-identical to the literal original fixture. The basket reducer changes only its
artifact acquisition/logging boundary; its routing and ranking remain the same.

The calculation preserves:

- Six counted lanes; narrative rows precede Sector rows; existing caps and more counts.
- Clean-entry and conflicted-theme routing, equal-weight risk overrides and disclosures.
- Caution lane hints and exact-tag fallback, including WAIT demotions.
- Stock urgency, alpha/conviction/factor ordering, company/ticker deduplication,
  soft Sector diversity and the 60-row standout cap.
- Existing setup/dual-read attachment, including the deliberately different malformed
  input policies of the broad and focused legacy builders.

`assemble_action_board_from_inputs` deep-copies the supplied timing, notable, basket,
allocation and setup values before invoking those owners. It performs no acquisition,
store access, page generation, signal-cache use, or publication. The isolation test
preloads incumbent constant/ranking modules before forbidding acquisition; it is not
a cold-import isolation claim.

`action_board_envelope` binds the board to the exact supplied basket bytes and their
matching top-level/theme dates. It rejects empty/notable-only boards, unusable source
bytes and contradictory source dates. It preserves the incumbent effective-total and
date-validation behavior; the final generation admission remains stricter. The basket
hash does not establish common provenance for every upstream board input.

The pure envelope deliberately detaches its board. Published JSON values match the
original writer; Python object identity is not claimed to match.

## Legacy compatibility

Both `scripts/build_site.py` and `scripts/build_sector_action_board.py` delegate to
the same owner. Existing acquisition and publication stay with those builders.

The focused builder preserves its `canonical=` injection and call order:
alpha, insider, sector pages, sector setup, basket items, action board. Its non-dictionary
result error remains. `write_action_board` retains its signature, validates the board
before reading, captures the basket bytes once, re-exports the same exception class,
and uses the unchanged atomic writer. Existing tests continue to prove preservation of
the prior artifact on invalid input.

The standing alert/action-board separation test now guards the actual engine module
as well as the legacy wrapper. No separate alert producer or interpretation was added.

## Verification and evidence

The first affected run returned **308 passed, 4 skipped, 6 failed**. One new isolation
test incorrectly targeted a nonexistent `store.load`; it now targets the real
`store.read`. One unchanged existing lane-hint test iterated every board value and
therefore tried to iterate the already-existing integer total. Its exact published
test source was byte-compared and executed against the literal original reducer,
reproducing `TypeError: 'int' object is not iterable`. The repair retains every
routing/duplicate assertion, iterates all row-bearing lanes, and additionally checks
the published total.

The other four failures are unchanged missing generated-site preconditions in the
sparse source checkout, previously reproduced against exact published source. Their
assertions are not changed. The final focused run explicitly deselects only:

- `test_redirect_stub_rendered` (two parameter cases);
- `test_generated_forming_narratives_matches_deferred_init_contract`;
- `test_scoped_publication_directories_are_real_and_owned_by_the_build`.

**Final result: 310 passed, 4 skipped, 4 deselected; exit 0.** These include literal
original basket/board/envelope parity, genuine legacy writer/fixture comparison,
pre-read rejection, detached composition, acquisition prohibitions, the existing
writer/semantic/canonical-injection tests, board coherence, hover, basket, standout,
and action-board ownership checks. These counts overlap the first run.

Tracked-source diff-check exited 0. All seven changed Python files parsed and had no
trailing whitespace. Exact source fingerprints and log digests are recorded in
[the source review](SECTOR_ACTION_BOARD_SOURCE_REVIEW_2026-11-06.json).

| Evidence | SHA256 |
| --- | --- |
| Literal original board/writer fixture | `67ef85e6b7cceb8c2add17bb71cf2ba46d0f386944c9426c2db519643708032a` |
| First affected log | `0628228f831f412b2c3f965798dcd98ee6cbf523f06896947b0a5aedea690140` |
| Original-test baseline diagnosis | `e7bb16b1dad4fb29ffe64928e5d5ed004f8a1466e152dea869e98d193d975e80` |
| Final affected log | `1dce99a281684cf8990aa5f14359cf671eb58beac68430c4c52c6abc59584f22` |

## Next executable work

Prepare current timing/notable/setup values without calling the page builder. Close
genuine thematic OHLCV acquisition and ThemeScore signal/texture calibration inputs,
plus separately required amalgam/holdings/context capture. Assemble and admit the five
final Sector documents with one captured dependency set and the original publisher CAS.

Source-updater recovery/drain, CI capability-owner resolution, required release checks,
API mounting, native Terminal repair and authenticated beta fault/advancement proof
remain open. Protected queue entries and all live writers retain their existing owners.
