# Stock-level entry transparency — existing producer to existing detail page

## Capability and release boundary

This continuation of Macro #7669 adds a usable stock-by-stock explanation path,
not another historical study, ranking policy, candidate registry or execution plane.
The primary theme assessment now links directly to the existing stock-entry
section. Its disclosure explains every member, preserving the distinction between
an unqualified entry and unavailable assessment. The real per-stock page remains
the destination for each ticker. No score, price target, allocation, trade, or
new entry permission is created.

Protected procedure was freshly loaded from
`Mastermind@0471cea4f891da1ec0c9fbeff10a9391f9cdd90f` (Skillpack 1.0.1/bootstrap 1).
The same source carrier remains `claude/theme-recommendation-reasons-20260921-sol`.
Original feature head before this unit: `4e01f20e2dc5ee66634ed51ec127ba8b8630b860`.
No other PR's source writer was replaced. Direct-work reason: PRINCIPAL_JUDGMENT /
LOWER_TOTAL_OVERHEAD for the canonical stock admission and its actual user claim.

## Actual defect and implementation

`engine/basket_score.py::act_now_stocks` already decides whether a member stock
qualifies. Its old empty result nevertheless attributed the entire roster to
extension/mid-trend conditions and requested a pullback. That was not established
by its rejection logic: a stock might be cycle-blocked, below the conviction floor,
waiting for a signal, or unrated. The fast-turn projection could even copy a
positive entry headline as the explanation for a stock rejected by the score floor.

`_stock_entry_check` now contains that same existing eligibility decision, paired
with its deciding condition. The buy list and watch explanation consume it instead
of implementing separate, potentially contradictory decisions. Source status,
qualified buy records/order/cap and uncovered names are unchanged. An already
qualified legacy member is no longer duplicated as a non-actionable fast-turn watch.
The legacy entry fallback is explicitly described as legacy, not a newly confirmed
entry signal.

The additive `entry_checks` and `entry_summary` fields remain inside the existing
`act_now_stocks` payload. All member rows are described even when the original
12-row buy presentation cap applies. Summary arithmetic is validated at render;
invalid reasons/counts fail to a neutral unavailable message. Strings are escaped.
No browser-side eligibility scoring or new recommendation logic exists.

`templates/basket_detail.html.j2` consumes these fields in its existing entry
section. A top-level 'Check individual stocks' link opens and focuses the native
'Review stock entries' disclosure. Both targets are at least 40px high. The existing
UI-state helper preserves its open state and keyboard focus across normal renders;
there is no second persisted state owner. Existing button/table/material tokens are
reused. Both English and Chinese explanations are supplied by the producer.

All previously existing basket-score functions other than `act_now_stocks` are
source-hash frozen in a test-only fixture, including clean_entry and the risk
textures. The 0.75/0.85 research results and their artifacts remain bound to their
original source commits. Do not silently rerun a frozen whole-module-hash study
against this new module and claim identical source: use its original frozen head.

## Proof and checks

`tests/test_basket_entry_explanations.py` exercises the native producer and real
JavaScript consumer, including theme veto, cycle restriction, score threshold,
unavailable coverage, older records, complete-roster/capped-display semantics,
translation, escaping and contradictory diagnostics. A 2,160-case comparison uses
a test-only copy of the original function and requires identical status, buy list
and uncovered coverage. No assertions or old admission controls are removed.

`prove_stock_entries.py` reads immutable, already-published detail-page inputs and
recomputes the existing native stock projection. It binds each source page and
requires original status/buys/coverage parity. Results are stored in
`stock-entry-proof.json`; absent data is never filled with synthetic stock claims.

The existing `browser_proof.py` now invokes the real stock producer, tests the
hero-to-stock-check keyboard action, every reason and stock link, and open/focus
persistence across a render. It retains the original-template comparisons and
all dark/light, English/Chinese, desktop/mobile cells. The screenshot/proof files
remain under the existing browser evidence directory. They are local stored-input
proof, not an authenticated or deployed production claim.

## Exact external gates, not more implementation prerequisites

At this continuation's release reconciliation:
- #7650 had independent approval and successful exact-head CI at
  `e0e996381af1494e3c201078fddb472ad75b8061`; it remains OPEN, not deployed.
- Shared main-baseline failure still blocks the real publication path. Existing
  repair #7693 at `9e74c33d3f6c22b1e41f4dc7f100baf32a050734` owns that lane.
  Its latest completed run was red in packs 3/7/9, with exact source-owner
  diagnoses in comments 5774384105 and 5774440956. No competing repair,
  gate waiver, test skip, or source takeover was attempted.
- #7669 still needs independent review and release. The formally requested
  reviewer remains `mastermindx-3`. A bounded native reviewer invocation through
  the existing Opus reviewer agent was attempted once; the platform blocked it
  before any process receipt. It is NOT a started/completed review. The command
  was not retried or rerouted through another actor, account or provider.
- #7478 is accepted historical work and was not redone. No Vercel operation,
  deployment, trade, new watcher or alternate pipeline was created.

Current result: BUILT_NOT_PROVEN / MISSION_COMPLETE: false. Source release,
normal producer publication and current-input deployed-browser proof remain
separate obligations. The exact commit, final test results and hosted run
identities are recorded in the same PR's cumulative read-back checkpoint.
