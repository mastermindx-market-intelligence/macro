# Synthetic `systematic_research.v1` fixtures

**Every file in this directory is synthetic test data.** The numbers are invented
for the UI tests. None of them is a measured result, and none of them describes
any real strategy, instrument, account or market.

They exist to exercise one rendering path: `scripts/render_systematic_strategies.py`
→ `templates/systematic_strategies.html.j2`.

| File | State it exercises |
|---|---|
| `research_available.json` | `status=research_available`, two candidates, full historical metrics, data health `ready`, current against the reference clock |
| `inputs_blocked.json` | `status=inputs_blocked`, named data-health reasons, both candidates blocked with `historical.state=unavailable` — absent metrics must never read as zero |
| `data_stale.json` | one candidate, an information cutoff two weeks behind the reference clock — the record stays readable but is labelled historic, never current |

The unavailable-metrics case is carried by `inputs_blocked.json` (both
candidates `historical.state=unavailable`) and is mutated in place by
`tests/test_systematic_strategies_ui.py`; it is not a separate committed file.

**Rates are decimal fractions.** `net_cagr` and `max_drawdown` are fractions in
this contract: `0.032` is 3.20% and `-0.114` is -11.40%. The renderer scales them
into the unit its own label names. A fixture carrying `3.2` under a "%" label
means 320%, and is the defect this convention exists to prevent.

Each file also carries an `_fixture_note` key. That key is **not** part of the
`systematic_research.v1` contract; it is here to make the file self-identifying
if it is ever read out of context, and it doubles as the allowlist fixture —
the renderer must ignore it (and every other unknown key) and never print it.

Corrupt, hostile and edge-case artifacts are built in
`tests/test_systematic_strategies_ui.py` rather than committed here, so the
directory holds only well-formed examples.