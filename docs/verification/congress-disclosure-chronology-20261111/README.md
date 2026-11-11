# Congress disclosure chronology repair

Operation: `terminal-estate-congress-chronology-20261111-c3`
Protected Mastermind law: `bb2c2e4437e6ee250f9d4ee9b6b420abdfbbc178`
Macro source base: `dce366adcf109daa9a2f0bf99ed68120da6b7957`
Terminal acceptance carrier: [issue #1466](https://github.com/mastermindx-market-intelligence/mastermind-terminal/issues/1466)
Original failure: [Macro #1224 diagnostic](https://github.com/mastermindx-market-intelligence/macro/pull/1224#issuecomment-6793793709)

## Change

The existing member engine owns one shared chronology qualifier. Both the
watchlist builder and the independent full-history member reader require valid
transaction <= report <= cutoff dates before any ranking or member statistic.
The watchlist retains its inclusive 182-day transaction window and original
transaction-age decay. Member reliability retains its full-history cohort and
30-day maturity rule.

The raw feed keeps every previously retained source row. Missing dates are
unknown, malformed/inverted dates are invalid, and later dates are excluded;
the bilingual page shows that status and retains malformed date values.
The latest eligible filing date and processing cutoff are separate. No eligible
filing means unavailable, without substituting the build date. Zero
ExcessReturn remains a valid non-hit. The source Parquet and input DataFrames
are unchanged.

This necessary date condition does not establish point-in-time outcome,
observation or vintage availability. No trading authority is added.

## Executed qualification

- The original 82 score tests passed unchanged at the exact base.
- The 13-case admission matrix reproduced **7 failures / 6 passes** before
  source edits: four future-date cases, two unavailable report dates and one
  inverted chronology.
- The repaired focused suite passes **103 tests**: the 82 unchanged tests plus
  21 regressions, including the full 13-case date matrix.
- One regression executes all **five native consumer fixtures** through real
  synthetic Parquet, builder, member engine, aggregate/scoring, complete native
  Jinja templates and captured snapshot handoff. Every contaminated fixture
  exactly preserves the valid control's full items, member leaderboard and
  snapshot arguments. Their baseline cluster/composite remain 41.3/8.7.
- Additional regressions cover raw retention/status, independent member
  full-history qualification, older valid member observations, zero returns,
  absent date columns, UTC timestamps, invalid numeric dates, and the
  unavailable page date.
- Affected design-system and UI-evidence diff gates pass. No CSS, runtime
  styling or JS changes are included. The whole-tree runtime-style guard
  explicitly refused this sparse checkout because `site/` is unmaterialized;
  it is not claimed as a local pass, and its hosted gate remains required.
- Source diff whitespace check passes. The original score-test file is
  byte-identical to the base.

Native runtime: Python 3.14.7, pandas 3.0.5, pytest 9.1.1, Jinja2 3.1.6.
The source requirement is pandas >=2.2, which supports the shared parser.

## Reproduce

Run `python3 -m pytest -q tests/test_congress_chronology.py tests/test_congress_score.py`
from the repository root. Synthetic fixture directories, frozen UTC time,
local page output, and intercepted desk-grader writes are test boundaries.
Collectors, real ledgers, deployed source and authenticated production users
are not exercised. The fail-soft builder returning 0 is insufficient by itself:
the tests require the generated page and actual consumer payloads.

The raw logs and reviewed diffs are losslessly gzip-wrapped for publication.
`manifest.json` binds compressed and decompressed bytes and final source blobs.
No failed result is rewritten into a pass. Author self-check is the review
performed here; no formal approval or merge is claimed by these local results.
