# Synthetic `systematic_research.v1` fixtures

**Every file in this directory is synthetic test data.** The numbers are invented
for the UI tests. None of them is a measured result, and none of them describes
any real strategy, instrument, account or market.

They exist to exercise one rendering path: `scripts/render_systematic_strategies.py`
→ `templates/systematic_strategies.html.j2`.

| File | State it exercises |
|---|---|
| `research_available.json` | `status=research_available`, two candidates, full historical metrics, data health `ready` |
| `inputs_blocked.json` | `status=inputs_blocked`, named data-health reasons, one candidate blocked — the useful empty state |
| `historical_unavailable.json` | one candidate with `historical.state=unavailable` and `null` metrics — absent must never read as zero |

Each file also carries an `_fixture_note` key. That key is **not** part of the
`systematic_research.v1` contract; it is here to make the file self-identifying
if it is ever read out of context, and it doubles as the allowlist fixture —
the renderer must ignore it (and every other unknown key) and never print it.

Corrupt, hostile and edge-case artifacts are built in
`tests/test_systematic_strategies_ui.py` rather than committed here, so the
directory holds only well-formed examples.