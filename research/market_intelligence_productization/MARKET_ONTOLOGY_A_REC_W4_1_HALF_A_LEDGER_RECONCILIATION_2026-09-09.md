# F00C ledger reconciled against the merged half-A wave

Packet A-REC-W4-1, recorded 2026-09-09 by the Meta-CEO B seat under the Chairman's
2026-09-09 throughput directive. Records only: no product code, no new capability, no
promotion of any authority ceiling. Stacked on B-REC-B5-1
(`claude/mo-b-rec-b5-1-ledger-reconciliation`).

## Why this record exists

Nine half-A ledger rows still read `SPEC_ONLY` or `PARTIAL` after seven pull requests
that meet their acceptance sentences had already merged to `origin/main`. The Charter's
DONE test is computed off this ledger, so those nine rows were counting the program as
further behind than the merged tree. This packet re-reads each merged difference against
the ledger's own acceptance sentence and writes down what it found.

The rule applied to every row was the same and was applied literally: the acceptance
sentence already written in the ledger is the test, not a paraphrase of it and not the
pull request's title. All nine sentences were met. None of the seven merged differences
contains a production readback (a live URL check, a two-user session log, a monitoring
receipt), so none of the nine rows qualifies for `PROVEN_LIVE`. `PROVEN_LIVE` needs a
production readback the seat performs separately.

Two rows carry a caveat a reviewer should weigh before accepting the verdict as-is. Both
are recorded here rather than silently resolved.

## What the state words mean here

`BUILT_NOT_PROVEN` means the capability is merged to `origin/main` and the producer path
named in the row exists in that tree. It does not mean anyone has used it in production.
No row in this packet moves to `PROVEN_LIVE`.

## The nine rows that moved

- `MO-DELTA-032` — a jurisdiction-scoped policy item advances through deterministic
  lifecycle states on a real store, rendered. Merged macro#6900 as
  `ad021359a0f3da97f53eebde550b8c7cf422815e`. Producers:
  `engine/policy_intent_desk.py`, `config/policy_lifecycle_seed.json`,
  `templates/policy_watch.html.j2`. The merge ships `LIFECYCLE_STAGES`, `fold_lifecycle`
  and `lifecycle_view` over an operator-authored seed, rendered as a four-stop stage
  meter. Literal match.

- `MO-PAID-007` — policy_watch renders a lifecycle stage, not just a thread tag. Same
  merge, macro#6900 / `ad021359a0f3da97f53eebde550b8c7cf422815e`. Same three producers.
  The absorption into `MO-DELTA-032` is discharged; `next_bounded_child` is emptied
  rather than restated. Literal match.

- `MO-PAID-023` — a second country's political desk ships under the same contract and is
  rendered. Merged macro#6928 as `4b2f97f196d5666e29e3bb8991d4f18e65a0b584`. Producers:
  `engine/uk_policy_brain.py`, `scripts/build_policy_watch.py`,
  `templates/policy_watch.html.j2`. United Kingdom / GOV.UK desk under the
  `whitehouse_brain.py` contract, rendered across six typed states. Literal match.

- `MO-PAID-034` — one non-China region gets an equivalent PIT event-bus module on the
  qbus join surface. Merged macro#6931 as `91f114ad4b7338cf82529f9ef2f11845f6589104`.
  Producers: `engine/europe_news_intel.py`, `scripts/collect.py`. EC Presscorner + Bank
  of England on the existing qbus join. Does not close UNRESOLVED-3/3a/4/6. Literal
  match.

- `MO-DELTA-001` — MO-PAID-017 interface confirmed to serve (or explicitly not serve) a
  Market-Feed surface. Merged macro#6897 as `31ac6bf3ffb658c0d2b63d31fac33fa35f6a64a3`.
  Producers: `engine/chronicle/market_feed_alias.py`, `engine/chronicle/__init__.py`.
  Measured answer: NOT_SERVED. The acceptance sentence is closed both ways. Literal
  match.

- `MO-DELTA-004` — a surface maps a shock node through GMI edges to company exposure.
  Merged macro#6929 as `585d9d3a0f9b023f54aa003f821d249964107e3e`. Producers:
  `engine/market_ontology/exposure_map.py`, `engine/market_ontology/__init__.py`.
  `compose_exposure_map(ShockSpec, asof)` walks GMI edges from a caller-declared shock
  through theme to company, rights-filtered, typed-null on every gap, ordered by node id
  only. Census reading: SATISFIED → `BUILT_NOT_PROVEN`. Caveat below.

- `MO-DELTA-015` — one additional family implemented, callable, tested. Merged macro#6901
  as `413e1f930fc3cfd5deece8eff1485f9f466d68e1`. Producer: `engine/local_projections.py`.
  Local Projections (Jordà 2005) is the third of eleven econometric families. Literal
  match. The remaining eight families are future ledger rows, not children of this one.

- `MO-PAID-003` — vendor rights recorded and depth-parity assessment written. Merged
  macro#6908 as `dd1dbfb90310344fba0b9fee85ee6578c83645cc`. Producer:
  `research/market_intelligence_productization/F01_FX_COMMODITY_SOURCE_RIGHTS_AND_DEPTH_2026-09.md`.
  FX vendor rights and a depth-parity assessment are on disk. No engine, template or
  product code changed. Literal match.

- `MO-PAID-004` — the producing engine module chain is named per page. Same merge,
  macro#6908 / `dd1dbfb90310344fba0b9fee85ee6578c83645cc`. Same doc, §3.1, 3/3 pages
  (`commodities.html`, `commodity_strategies.html`, `spr.html`) named at module and
  function granularity. Literal match. Collision flag below.

## Caveat: `MO-DELTA-004` — "surface" is doing real work in this sentence

`engine/market_ontology/exposure_map.py`'s `compose_exposure_map(ShockSpec, asof)`
literally walks a caller-declared shock through GMI edges
(`engine.theme_graph.store.read_edges`) to company exposure, typed-null on every gap,
rights-filtered, ordered by node id only. That is the literal action the acceptance
sentence names. But PR #6929's own body draws a line this packet should not paper over:
"Ledger rows closed: MO-DELTA-004 (data tier only; A-F04-W2-2 owns the rendered surface)."
The row's own pre-existing `real_consumer` cell already said the gap was "no product
surface" — and after #6929, `real_consumer` is still internal-only (`adapters/theme.py`,
`projection.py:41`); no template, route, or nav entry consumes the composer. A-F04-W2-2
(the PR the author names as the owner of "the rendered surface") was not found merged in
this repo as of this research.

This packet follows the census's generous reading (a callable, tested, rights-enforced
composer is a real software surface, and the sentence never says "rendered" or "on a
page") but records the PR author's own narrower self-description so a reviewer applying
the stricter "product/rendered surface" reading has the exact quote to dispute it against.
If a reviewer overturns this row, the correct `next_bounded_child` is not empty but
"A-F04-W2-2 — the rendered/product surface over this composer (not confirmed merged)",
not a restatement of the discharged `next_bounded_child` that already produced #6929.

## Caveat: `MO-PAID-004` — a file-level collision with open #6957, not a row edit

`research/market_intelligence_productization/F01_FX_COMMODITY_SOURCE_RIGHTS_AND_DEPTH_2026-09.md`
§3.1 names a verified engine-module-and-function chain for all three commodity pages
(`commodities.html`, `commodity_strategies.html`, `spr.html`); its own §7 line states
"producer chain named per page at both module AND function granularity, 3/3 pages ...
acceptance_test ... satisfied." That is a literal match and is independently corroborated
by the still-open macro **#6957** ("[MO-BA-spare] B-A-F01-2: F01 credit and commodity
data-plane wiring trace"), whose own acceptance-evidence section says of the identical
three pages: "All three: YES verified."

The reason this needs a flag rather than a quiet close: **#6957 is OPEN (not merged, base
`main`, head `claude/mo-b-a-spare-b-a-f01-2`) and its file list includes the exact same
CSV**. This round re-read that pull request's live hunk rather than only its file list
(`gh api repos/mastermindx-market-intelligence/macro/pulls/6957/files`): the CSV change is
`+1/-1`, and the only cell it moves is `MO-DELTA-008`'s `missing_contract_or_proof`
(from "broad HY/IG aggregate credit surface (current instance single-issuer only)" to a
sentence naming the shipped aggregate spread-gauge card). **#6957 does not touch
`MO-PAID-004`.** The earlier reading of this caveat — that the two packets collide on the
`MO-PAID-004` row — was drawn from the file list alone and is withdrawn. The collision is
real but file-level: two open records packets edit one CSV, so whichever merges second must
rebase past the other's edit, not force it. This packet applies the §2 edit.

Scope of the close: this row closes the **commodities half only**. The credit half of
the same F01 wiring trace sits inside the still-open macro#6957 as `MO-DELTA-008` and is
not closed by this row or by this packet; `MO-PAID-004` stays `BUILT_NOT_PROVEN`.

## What this record deliberately does not do

- It does not touch `real_consumer` on any row.
- It does not claim any production proof. See the state-word section above.
- It writes no disposition into any row outside the nine, and it changes no authority
  ceiling, no source-rights entry and no family assignment.
- It does not import `engine/uk_policy_brain.py` or `engine/market_ontology/` into this
  stacked tree. Those files exist on `origin/main` at the named merge commits (#6928,
  #6929) but are not ancestors of this stacked HEAD. Adding them here would widen the
  diff past the named files.

## Where the evidence lives

`tests/fixtures/f00c_half_a_reconciliation_manifest.json` carries the machine-readable
version: each of the nine rows with the pull request it names, that pull request's merge
commit, the producer paths, and the ledger's own acceptance sentence. The suite
`tests/test_f00c_half_a_reconciliation.py` asserts the manifest and the ledger agree.
The suite reads the manifest and the CSV; it does not call `gh` or git.
