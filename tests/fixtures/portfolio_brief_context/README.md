# portfolio_brief_context fixtures

Shared, synthetic, adversarial fixtures for the Portfolio brief snapshot
witness contract (`portfolio_snapshot_witness.v1`).

**Every value here is invented.** There is no live account, no real holding, no
real owner id and no database behind any of it.

## `projection_cases.json`

One entry per adversarial case. Each entry carries three independently sourced
blocks and the verdict derived from them:

| block | what it is | where it came from |
|---|---|---|
| `row` | the raw captured `portfolio_positions` row | hand-written synthetic input |
| `terminal` | the Terminal's projection of that row | the Terminal's REAL `rowToPosition`, run from `terminal/lib/portfolio.ts` at commit `70ebc639e0a6795f8bc100008fa609406db72f3f` (read-only contract reference) |
| `composer` | the Python composer's reading of that row | the frozen `engine/portfolio_brief.py::_normalize_holdings`, cross-checked against that composer's OWN output weights |
| `compatible` | whether the two authorities agree about the row | derived from the two blocks above |
| `reject_reason` | why they disagree, when they do | derived from the two blocks above |

The point of the split is that the fixture is a contract between two
independent authorities, not a restatement of one implementation. A producer
that agrees with its own mirror but not with the Terminal fails this fixture.

### Fields

- `terminal` is `null` when Terminal's `rowToPosition` DROPS the row (no usable
  id, or a ticker it refuses). Otherwise it carries `id`, `ticker`, `shares`,
  `entryPrice`, `entryCurrency`, `entryDate`, `notes`, `status`, `createdAt`.
- `composer.shares` / `composer.entry_price` / `composer.cost` are the frozen
  composer's own numeric reading. `composer.non_finite` names the columns whose
  reading is `Infinity`/`NaN`; strict JSON has no literal for those, so they
  are encoded as `null` plus the name.
- `composer_input` is the row as the producer hands it to the composer:
  `ticker`, `shares` and `entry_price` VERBATIM, never coerced.

### Scope

The producer's compatibility gate covers the OPEN rows — the rows the composer
is called with. A closed row never reaches the composer, so the two readers
cannot disagree about it; it is carried in the witness verbatim and is not
gated.

### Reuse

A Terminal-side consumer can read this file directly to check its own
projection against the same authorities, and to learn which raw values it must
refuse rather than normalise. The file is strict JSON: `JSON.parse` and
`json.loads` both accept it unchanged.

Regenerating the expectations requires the Terminal source and the frozen
composer; it is NOT a hand-maintained file. See
`docs/verification/portfolio-brief-snapshot-20261102/` for the generation
receipt.
