---
schema: mastermind.macro_regime_intelligence.implementation_packet.v1
operation_key: macro-regime-intelligence-architecture-20260912-sol-001
workstream: WS:RATES-INFLATION-COMMAND
owner: ceo-sol
status: READY_FOR_INDEPENDENT_DESIGN_REVIEW_NOT_EXECUTION_ADMISSION
capability_state: SPEC_ONLY
source_pin: 1850547c80e92191e6b195acce446c912de7f5e3
procedure_pin: 57a2672af5b9dcea282e4bae01d1a0b9d10bb1cd
---

# R1: a usable comparison of possible real-rate paths

This is the bounded implementation packet subordinate to
`PROGRAM_ARCHITECTURE_2026-09-12.md`, not another program charter. It resolves
additional source and ordering questions found while preparing that architecture.
No implementation, worker assignment, native execution, test pass or production
claim is made here.

## Mission and why it matters

Let a researcher answer: **is real-rate pressure durably easing, or are we seeing a
pause, growth deterioration, renewed inflation pressure or a long-end premium
shock?** Show the actual evidence, contrary evidence and missing evidence behind
those alternatives on the existing `transmission.html` surface. Preserve the full
program's subsequent forecasting, history and portfolio scope; R1 does not claim
to complete them.

The first useful output is a coherent investigation, not numerical probabilities
made from condition counts. It must add understanding beyond listing indicators.

## Authority and current state

Current live Chairman direction to Sol authorizes completing the original program.
Protected procedure and actual current runtime/source permissions remain required.
The design extends `DEC:RIC-CANONICAL-COMPOSITION-BOUNDARIES`; it does not supersede
that decision. Existing RIC and Market Ontology source owners keep their paths.

At authoring: Executive state calls returned an MCP tunnel404; MacBook configuration
access failed and a read-only shell request was safety-blocked; Studio advertised a
new session but its ping timed out. Do not repeat or delegate the denied shell
preflight, infer native source access from GitHub access, or transplant an existing
writer's source. An eligible native worker must use its own already authorized
execution path and establish task/source permission before work. No worker is bound
by this record and no numbered account is selected.

PR7015's recorded-history reader and PR7024's briefing consumer are existing
unmerged capabilities, not tasks to recreate. PR7024 additionally has incumbent
applied local changes described in comment5647959939; a clean remote branch does
not release its writer. Shared Lens6860, Risk Radar7040 and policy-pre-turn6788
retain their own carriers. RIC workstream status correction remains on6593.

## 1. Exact recovered input map

All paths and observations below were read at Macro commit
`1850547c80e92191e6b195acce446c912de7f5e3`. These are source evidence, not a claim of
live-service verification. Re-pin current compatible source at placement, but do
not restart a general census.

| Evidence | Existing input and field | Use and limit |
|---|---|---|
| Nominal/real curve, inflation and expectations | `data/transmission/latest.json`; `state.rates`, `state.inflation`, `state.expectations`, `yield_curve` | Reuse the existing transmission and curve contracts, including their dates, units and authority. RIC already consumes this file. |
| Yield technicals | Same transmission artifact, `yield_momentum.series`; existing `engine/yield_momentum.py` | Existing 2/5/10/20/30-year,5/22/63-session reads. Do not relabel nominal-yield turns as measured real-yield technicals. |
| Dollar | Same transmission artifact, `dollar_channel`, produced by `engine/transmission_context.py::compose_dollar_channel`; underlying `data/forex/latest.json` | This is the existing dollar join. Preserve the source's actual field semantics and dated envelope; never use RIC `compact_state.usd_dir`, which currently points to the policy-row object. |
| Market-implied policy path | `data/bonds/bond_health.json#fed_path`, projected to `rates_command.board.rate_path_row` | Use the existing m1/m3/m6/m12 path, gap and repricing. Not a real-world probability distribution or a prediction that the Fed must follow. |
| Labor | `data/regime/latest.json#labor_nowcast`, owner `engine.regime.labor_nowcast`; current workspace projection references `claims_z`, `indeed_chg_3m_pct`, `withheld_tax_yoy_pct` | Read the upstream owner, not a downstream Monetary Policy workspace. A z-score is not automatically a direction of change; preserve the measure's meaning. Per-field vintage dates are not supplied by this owner, so do not invent them. |
| Economic versus market regime | Existing `data/regime/regime_one.json` decomposition | Preserve tape/economy disagreement. Filtered current membership is not a future-date forecast. Historical-issued claims depend on accepted7015 semantics. |
| Credit/financial conditions | Existing regime/market-state owner and reviewed conditions-vintage fields; RIC already reads `data/market_state/latest.json` | Consume the underlying credit measures and actual clocks, not a new average of workspace axis scores. Exact required fields must be pinned from that owner's contract before coding. |
| Inflation release context | `data/release_forecast/latest.json#upcoming`, existing RIC inflation-row projection | Preserve actual versus forecast release, target period, release time and epoch. Do not promote an experimental release forecast by placing it beside measured data. |
| Oil | `data/commodity/latest.json#assets.oil`, `data/commodity/shock_state.json#oil`, `data/commodity/complex_latest.json#growth_dir` | Preserve owner classification and staleness. Price direction alone is not a supply/demand cause. No extra shock classifier. |
| Policy | `data/policy/intel.json`, `site/policy_lever.json` and existing policy-event owners | Keep source `as_of`, known-at and effective dates. Old narrative may appear as dated background, never current confirmation. |

### Workspace manifest is a coverage reference, not a new truth source

The actual manifest is `site/macrodata/workspaces/manifest.json`, blob
`a9945a9f73a21d66b4c880e860fa7a70e15254fc`. Its paths are relative to `site/macrodata/`:
`workspaces/<workspace>/US/latest.json`.

The September12 07:40:49Z manifest reports labor/growth/financial conditions CURRENT,
inflation LATE_WITHIN_TOLERANCE, central-bank liquidity STALE_SOURCE and rates_curves
SOURCE_FAILED. Do not treat every input as unusable because of one aggregate status,
or treat every component as current because of a fresh build timestamp.

The rates body, blob `b97cf98c8a1c5f4ebd72038a425017cda6647788`, identifies the specific
problem: `availability.degraded=[iorb]`; that component has source_asof September14,
statusPARTIAL and freshnessSOURCE_FAILED. The nominal and5/10-year real nodes are
individually PRESENT/CURRENT dated September10; breakevens are dated September11;
term premium is dated September4 under its own cadence. This is **not evidence that
the entire Treasury curve feed is down**. R1 must retain valid independent curve
reads and withhold only conclusions requiring the unavailable reserve-rate leg.
The actual upstream cause of the future-dated IORB value has not been established;
never clamp its date to today or relabel it observed to make the page green.

The labor body, blob `60858f251db1264780230ea9d4f2b517c7fc7a4f`, explicitly says its
components share calculation_as_of because the owner does not publish per-field
vintages. Its observed raw receipts are claims_z approximately-1.419, Indeed3m change
approximately+1.850%, and withheld-tax YoY approximately+3.364%. These are useful
context with limited time provenance, **not** proof that all three underlying
observations arrived September11. Do not present the negative claims z-score as
proof that claims are falling.

A workspace's20-year node comes from DGS20 in `_RATES_FRED_COLUMNS`, whereas the
canonical yield-momentum owner explicitly protects its own `us20y` source. Same
short key is not evidence of interchangeable series. R1 reuses yield-momentum's
own result; it does not silently swap or concatenate the two histories.

## 2. Acyclic build and publication boundary

A naive return path would recreate exactly the stale-generation problem the new
capability is supposed to solve:

- `scripts/build_transmission.py` currently computes transmission and curve inputs,
  builds the dollar channel, renders the page, and writes
  `data/transmission/latest.json`.
- `scripts/build_rates_command.py` then needs that transmission artifact to build
  its board. It is the existing sole writer of `data/rates_command/latest.json`.
- `engine/market_os/macro_workspaces/build.py` reads Rates Command for the Monetary
  Policy workspace. Feeding the whole suite back into RIC would introduce a
  dependency cycle or quietly read the previous generation.

**Ruling for R1:** the analytical dependency remains one-way. Consume upstream
labor/credit/regime owners directly; do not consume the Monetary Policy workspace,
the suite hub, or a generic whole-suite fusion in the RIC producer. A manifest may
be inspected for diagnostics, but it does not become an analytical prerequisite.

For `transmission.html`, add a **render-only path in the existing transmission
builder**, used after the RIC artifact is published. It reads the prepared
transmission contract and the matching RIC research projection and writes the
existing page only. It must not recompute features, fit a model, refresh a collector,
write a canonical data artifact, or append any ledger. Preserve the current
standalone builder's default behavior and the existing publication owner.

The implementation must bind this final render to the actual current DAG after
`build_rates_command`; do not merely hope an unrelated render will run later. A
small dependency/entrypoint change in the existing `config/dag.yml` is in scope if
required, with its generated/projection rules respected. This is not permission to
create a new workflow, scheduler, retry loop or publication service.

The final UI shows the same `regime_outlook` semantic content and input-generation
references as the machine consumer. If the saved RIC projection does not match the
transmission generation it describes, show the previous dated research separately
or an explicit unavailable state; never silently combine them into a current read.
Fingerprint/reference semantics should reuse the existing owner contract. Do not
mint another generic source-identity registry.

Required discriminating proof: change a transmission input, run the existing producer
and RIC sequence, then the render-only stage. Both consumers must show the new
condition. Repeating render-only must leave every canonical data/ledger hash
unchanged. A mismatched prior RIC generation must not pass as current. An upstream
failure must still leave a useful partial page without fabricating a successful
refresh.

## 3. Research projection and readable comparison

Add `regime_outlook` to `rates_command.v1`. Keep every existing field and capital
behavior unchanged. A small pure helper under the RIC owner is permissible; it is
not a second registered regime/shock engine.

The pure function receives already-loaded, type-checked owner objects and an explicit
analysis cutoff. Its output includes:

- current evidence receipts and each receipt's actual clock type/precision;
- the five fixed path identities defined in the program architecture;
- per-path conditions with `supporting`, `contrary` or `unknown` evidence, plus
  assumptions that have not occurred;
- a short deterministic explanation of the principal difference between the
  alternatives, including the strongest available disagreement;
- what observable development would distinguish the alternatives next;
- links/references to existing transmission mechanisms and relevant source details;
- typed absence of numerical forecasts or historical distributions not yet supplied
  by their accepted owners;
- unchanged display/research-only authority.

Never use a raw count, weighted tally or LLM opinion to rank the paths or derive
probabilities. The five paths can overlap, so they are not an exhaustive partition.
A path can have supporting and contrary evidence simultaneously. Missing inputs
are unknown, not negative votes. Preserve contradictory evidence rather than
choosing whichever reading makes a smooth story.

Reuse owner-reviewed directions/thresholds with their actual definitions. Any new
research-only condition must disclose its rule, units and rationale in the receipt;
its wording cannot claim a measured forecast edge. In particular, raw rate level,
change, acceleration and historical percentile must not be exchanged for one another.

The user sees **Possible paths / Why this fits / What does not fit / What we are
watching**, in plain English and Chinese. Technical definitions and internal verdicts
belong in details. No front-facing falsifier/refutation jargon. Each card should
explain a conditional asset mechanism through an existing TXI/read owner where
available; no new numerical return forecast, beneficiary rank or portfolio order.

## 4. Time and correction tests

Distinguish `known_at` from a future policy `effective_from`. A genuinely announced
future-effective decision can be legitimate **scheduled policy evidence** if its
source proves it was known before the analysis cutoff. It is not an observed future
rate, and must not be used in current curve arithmetic. An unexplained future source
stamp is not equivalent to such evidence.

Required cases: valid negative/zero yields; booleans masquerading as numbers;
NaN/infinity; malformed mappings; stale policy beside fresh markets; missing labor;
calculation date without observation vintage; incompatible curve dates; future-dated
observations; known future-effective policy distinguished from observations; source
corrections; mixed-generation publication; all-input absence; one invalid component
with other usable components. Use real current artifact shapes, not only idealized
fixtures.

Do not run production helpers under an assumed read-only flag without inspecting
side effects. Ordinary render-only execution must never append the original RIC
`forward_log.jsonl`, regime histories, research outcomes or other owner ledgers.
Nightly remains the only admitted advancer, and R1 adds no new forecast ledger.

## 5. Owned scope and implementation order

Proposed implementation paths, subject to exact current ownership reconciliation:
`engine/rates_inflation_command.py`, one optional RIC-owned pure helper,
`scripts/build_rates_command.py`, `scripts/build_transmission.py`,
`templates/transmission.html.j2`, an appropriate governed existing CSS path,
focused tests, the necessary existing DAG/CI entrypoints, and the normal generated
page/evidence outputs. Do not edit `master_brain.py`, shared Lens/theme semantics,
Risk Radar, the existing forecast issuers or either incumbent7015/7024 worktree.

1. Consume the independent architecture verdict; bind one eligible worker and exact
   source ownership through the current execution path. Stop on a collision rather
   than taking another worker's tree.
2. Pin the remaining credit/dollar per-field receipt mapping and actual current DAG
   seam. Use the existing consumers; do not re-research the entire estate.
3. Implement the pure projection and producer integration with discriminating tests.
4. Implement the matching-generation render-only integration and readable comparison.
5. Run the real artifact bundle through the actual build sequence, then verify the
   machine reader and full page together. The existing Brain RIC reader is the
   preferred eventual machine projection; extend its current small receipt boundary
   only under its owner, never add another global intelligence route. Before claiming
   R1 complete, name and demonstrate the actual consuming reader rather than merely
   pointing to the newly written JSON.
6. Independent intent/code/design review, required concluded checks, ordinary merge,
   existing production deployment, browser and machine readback, durable closeout.

**Design acceptance:** current design doctrine and specimen, dark and light as two
intentional material treatments, EN/ZH,1440/390 widths, touch/keyboard/reduced-motion,
readable missing/partial states, no required hover, no horizontal overflow or console
errors. A generated mockup is not the final implementation; a screenshot is not proof
of data provenance.

**Stop condition:** return a concrete source/permission collision or failed gate,
or the real production-proven R1 journey. Do not return merely a schema, a model
notebook, green unit tests, or a branch that is not consumed. Sol then advances the
next program dependency immediately; R1 is not the whole-program completion marker.

**Continuation handoff:** exact head/base and ownership; changed paths; input and
output generation references; commands and results; independent review; current
checks; publication identity; live browser/machine evidence; open effects; actual
capability state; one exact next action. Preserve all pre-existing source effects.
