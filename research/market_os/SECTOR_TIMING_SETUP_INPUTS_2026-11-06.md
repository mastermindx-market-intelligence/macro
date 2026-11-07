# Captured Sector timing, standout stocks and setup calculation

Date: 2026-11-06. Base: `c18e840debddfb838074ac32e102f2cd53d89911`.
Carrier: Macro PR #10780; mission #10779. Source qualification only; runtime transfer remains open.

## Calculation ownership

`engine/sector_action_board.py` now owns the existing notable-stock projection,
fund timing/count summary, setup/base-rate/display projection and four shared display
helpers. `scripts/build_site.py` retains compatible entry points and acquisition/render
ownership. Its existing page loop calls the shared helpers at their original locations;
fundamentals, accumulation, alert preparation and page writes remain in the adapter.

The literal original builder/setup/helper bodies are retained in
`tests/fixtures/base_sector_timing_c18e840.py`, with an exact digest assertion. This is
an extraction of the existing calculation, not a change to signal meaning or ranking.
The setup caution-chip rule and action-board lane-hint rule retain their pre-existing
difference; reconciling those rules would be a separate behavior change.

## Explicit timing boundary

`SectorTimingInputs` contains the admitted source-session ceiling, ordered sponsor
fund list, ETF close frames, ordered top-ten holding frames, member close/optional-high
frames, effective liquidity/macro drag/per-fund macro beta, alpha/insider/factor/SUE
values, the existing `CycleCalculationInputs`, and auxiliary source evidence.
`sector_timing_and_notable_from_inputs` returns timing, notable rows and detached input
evidence. It reads no files, providers, configuration or clocks during the bound
calculation and performs no page, ledger, history or publication writes.

The caller must acquire and admit these inputs through their established owners.
This function does not declare an input cohort complete or publish a generation.
`engine.cycles` still has its incumbent cold-import configuration initialization;
this contract establishes bound calculation purity, not a new import lifecycle.

Qualification and calculation preserve the following distinctions:

- ETF analysis receives close only. Stock analysis receives the actual optional high
  field and the containing fund's effective beta. A stock held by two funds is analyzed
  twice in those contexts; there is no ticker-only signal cache.
- The legacy member floor is 300 **frame rows**, not 300 non-null closes. Missing or
  short frames and unavailable ladders retain their existing skip behavior. Counts
  measure successfully analyzed holdings. Notable urgency inclusion remains now,
  imminent and exit; soon is not newly included.
- Dates must lie within the captured US reference and not exceed the admitted source
  session. Evaluation cannot precede that session. Historical member observations
  may remain earlier; those holdings are not relabeled or discarded solely for age.
- Price evidence carries each supplied field's actual last observation,
  `close_observed_at`/`close_current`, and `current` only when every supplied calculation
  field reaches the source session. The compatibility `observed_at` remains the close
  observation. A current close does not make an older high observation current.
- Numeric and allocation qualification rejects malformed or non-finite captured
  values and bounds frames before copying. This does not clamp the legacy macro drag,
  substitute missing factor data, or infer source timestamps from build time.
- Alpha scoring, confirmation rules, 252-close high comparison, 66-close spark,
  punctuation normalization, holding order, title casing and formatting remain literal
  legacy behavior. Source auxiliary dates are retained unchanged.

## Setup boundary

`sector_setup_from_inputs(latest=..., closes=..., sectors=..., timing=...)` uses the
captured sector/SPY panel and the separate configured setup-sector list. It reuses the
existing sector signal board and calibration, including the calibration fallback,
tactical absolute-return formatting, seasonal-month choice and Markup types.

The source of the setup-sector list is the incumbent Yahoo sector configuration;
the timing fund list is the sponsor configuration. The composer must keep those two
ordered lists distinct. It must also supply an already-admitted setup close panel;
this legacy-compatible value helper does not create another source-session gate.
Missing SPY/no board or the original calculation-failure path returns `None`. Runtime
composition must identify this as unavailable and cannot silently call it a complete
setup surface.

## Proof and remaining integration

The source proof record beside this document contains exact file/log hashes, literal
baseline comparison and affected-suite results. Tests execute the old builder, new
legacy adapter and explicit timing path with the same inputs. They exercise the same
stock in two macro contexts, absent/short/no-ladder holdings, partial high history,
null-close rows, actual cycle analysis with ambient readers blocked, actual setup
calculation, measured/fallback/tactical base rates and production two-read chips.

This slice does not acquire live holdings or auxiliary datasets, assemble the final
five documents, mount the API, activate scheduling, transfer any data writer, deploy
Macro or prove authenticated beta refresh. Those remain on the existing master plan.
The separate bounded Terminal #1285 beta release has its own acceptance receipt and
must not be counted as generation-backed Sector acceptance.
