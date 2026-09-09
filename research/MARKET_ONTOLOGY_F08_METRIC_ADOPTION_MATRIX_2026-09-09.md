# F08 §1 metric adoption matrix (amendment, 2026-09-09)

This file is the V2 entry gate named by
`research/MARKET_ONTOLOGY_F08_ARCHITECTURE_FREEZE_2026-09-05.md` §1: metric →
owning module → definition / benchmark / horizon / annualization / version, or
the literal token `NO-OWNER`. It is an **amendment**. The freeze text itself is
not rewritten.

**Ceiling:** `decision_support_only`. The Portfolio Constructor remains
research-proposal-only and is visibly separate from any live book surface.
`engine/portfolio.py` stays HOUSE-only and is never forked.

**Route boundary (restated from the freeze so this gate carries it).** Every
holdings-coupled surface lives in the Terminal shell; macro `site/` gains no new
authenticated portfolio surface and no third header family, and macro-side F08
work is engines/receipts/delivery/prefs only —
`research/MARKET_ONTOLOGY_F08_ARCHITECTURE_FREEZE_2026-09-05.md:83`. Ratifying an
owner here does not create a macro route for it.

**How this matrix was read.** Macro contains no `terminal/` tree. The four
owned rows rest on B-REC-B5-1 / macro#7003's reading of terminal#524 (merged
`efcd98aa`) at Terminal master `db69d072`. That pin is checked in at
`tests/fixtures/b_rec_b5_x_consolidated_manifest.json`. Later drift on the
Terminal repository is invisible to this suite by design. This matrix does not
restate or fork a formula: it names the module that already computes the
readout, or it says `NO-OWNER`.

A builder may neither fork nor invent a formula before the matrix is ratified —
that freeze sentence still stands in the 2026-09-05 document. Ratifying an
invented owner here would be the same violation wearing the gate's uniform.

`MO-DELTA-014` stays open. Its acceptance sentence names Sharpe, Sortino, beta
and concentration; only concentration shipped. This matrix leaves that row
open.

| Metric | Owning module | Definition (governance-internal) | Benchmark | Horizon | Annualization | Version (governance-internal) | May not be used for |
|---|---|---|---|---|---|---|---|
| concentration | terminal/lib/portfolioRisk.ts | The per-user holdings concentration readout shipped by terminal#524 over A1A positions. This matrix names the owning module; it does not restate or fork the formula in that file. | none — descriptive of the user's own book, not a peer or index comparison | point-in-time over current holdings | none | terminal#524 merge efcd98aa | Must not become execution or sizing authority. F08 freeze: research Portfolio Constructor output never becomes execution/sizing authority. |
| industry weight | terminal/lib/portfolioRisk.ts | The per-user industry-weight factor readout shipped by terminal#524 over A1A positions. This matrix names the owning module; it does not restate or fork the formula in that file. | none — descriptive of the user's own book, not a peer or index comparison | point-in-time over current holdings | none | terminal#524 merge efcd98aa | Must not become execution or sizing authority. F08 freeze: research weights must not become execution/sizing authority. |
| company-size weight | terminal/lib/portfolioRisk.ts | The per-user company-size-weight factor readout shipped by terminal#524 over A1A positions. This matrix names the owning module; it does not restate or fork the formula in that file. | none — descriptive of the user's own book, not a peer or index comparison | point-in-time over current holdings | none | terminal#524 merge efcd98aa | Must not become execution or sizing authority. F08 freeze: research weights must not become execution/sizing authority. |
| liquidity thickness | terminal/lib/portfolioRisk.ts | The per-user liquidity-thickness readout shipped by terminal#524 over A1A positions. This matrix names the owning module; it does not restate or fork the formula in that file. | none — descriptive of the user's own book, not a peer or index comparison | point-in-time over current holdings | none | terminal#524 merge efcd98aa | Must not become execution or sizing authority. |
| Sharpe | NO-OWNER | NO-OWNER | NO-OWNER | NO-OWNER | NO-OWNER | NO-OWNER | No builder may compute or display Sharpe over a user's holdings until an owner is ratified. The freeze forbids forking or inventing a formula. terminal#524 does not compute it over A1A positions. |
| Sortino | NO-OWNER | NO-OWNER | NO-OWNER | NO-OWNER | NO-OWNER | NO-OWNER | No builder may compute or display Sortino over a user's holdings until an owner is ratified. The freeze forbids forking or inventing a formula. terminal#524 does not compute it over A1A positions. |
| beta | NO-OWNER | NO-OWNER | NO-OWNER | NO-OWNER | NO-OWNER | NO-OWNER | No builder may compute or display beta over a user's holdings until an owner is ratified. The freeze forbids forking or inventing a formula. terminal#524 does not compute it over A1A positions. |

**The Definition and Version cells are governance-internal, not display
strings.** They carry machine text on purpose: a cross-repo pull-request number
and a commit sha (`terminal#524 merge efcd98aa`), the internal position code
`A1A`, and meta about this matrix's own scope. No surface may render either cell
as written. Before any surface shows a metric's definition or version to a user,
that cell must first be rewritten in plain language as a bilingual EN/中文 pair
in the shipped `t('…', '…')` form — the pattern
`templates/capital_structure.html.j2:72` uses for `Policy watch / 政策关注`.
A commit sha, a pull-request number or a code like `A1A` never reaches a paying
user. This requirement binds the V2 builder that this gate admits; it is not
discharged by ratification.

Paired decision: `DEC:F08-METRIC-ADOPTION-MATRIX-2026-09-09`.
