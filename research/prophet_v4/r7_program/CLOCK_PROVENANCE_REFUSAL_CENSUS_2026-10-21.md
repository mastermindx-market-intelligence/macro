# Clock-provenance refusal census — 2026-10-21

Read-only census. BASE `e5dd30c6344e4b62a0beba054ac4da97e00bab36`. True failure count
at BASE: **38** (matches the packet's 38; `intake.validation_failed` = 38 and
`intake.validation_failures` has 38 entries, all `stage: "clock_provenance"`, each with
exactly one error string). Every failure is one pattern in three date-cohorts; every row
is classified **LEGITIMATE** (0 source defects, 0 missing-evidence rows at the run).
One artifact contradiction is reported below (§4): the site board at BASE is a
superseded generation and does not contain BRO's buy row; the run's actual input board
is the frozen, hash-verified snapshot committed at BASE under
`data/prophet/origination_sources/`.

---

## 1. Where the error comes from (engine chain, file:line)

All 38 error strings are produced at one site:

- `engine/prophet_bridge.py:1045-1049` — inside `_resolve_candidate_signal_dates`
  (defined at `engine/prophet_bridge.py:957`), for fired tiers only
  (`if tier in ("T1", "T2")`, line 1035):
  `formation_date {formation_date!r} postdates tier_event_date {event_date!r}`.
- The two compared values both come from the board row:
  - `formation_date` = `hold.anchor` if present else the board `as_of` —
    `engine/prophet_bridge.py:4371-4373` (`anchor = hold.get("anchor")`), documented at
    `engine/prophet_bridge.py:60-61` ("ID STABILITY … formation_date = hold.anchor").
  - `tier_event_date` = row `signal.tier_event_date` — read at
    `engine/prophet_bridge.py:1009`, passed in via the candidate mapping at 4506-4510.
- The refusal is recorded as `stage: "clock_provenance"` at
  `engine/prophet_bridge.py:4515-4522`, under the comment (4513-4514): *"Clock
  provenance is a validation gate, never an invitation to guess the prior Friday."*
  Errors from `_resolve_origination_clocks` (`engine/prophet_bridge.py:853`, wrapper
  price/publication clocks) would join the same record; **none appear in this run** —
  every one of the 38 carries only the formation-vs-event string.

Producers of the two board fields (the pairing this gate polices):

| Field | Producer (file:line) | Contract |
|---|---|---|
| `hold.anchor`, `anchor_src` | `scripts/build_stock_library.py:4286-4291` picks `_anchor = last §7 buy/rebuy marker date` (else `None`); `engine/hold.py:119-136` resolves it (`anchor_src="take"`) or falls back to the last 3D cross (`anchor_src="cross"`, `engine/hold.py:124-134`); returned at `engine/hold.py:203-213` | W6-C HOLD tracker — "Additive + graceful … display-only" (`scripts/build_stock_library.py:282-285` comment). The anchor follows the **newest** §7 take, by design. |
| `signal.tier_event_date`, `tier_observed_date` | `engine/confluence_tiers.py:370-391` `_tier_dates` (event = the confirmed T2 2D-cross close / T1 knowability close; observed = the session whose close produced the verdict); copied verbatim by `engine/signal_gate.py:516-533` into the verdict block | `engine/confluence_tiers.py:19-20`: *"tier_event_date is the immutable close that fired T1/T2"* — the event date **never moves** when a later take fires. |

So the two clocks are owned by different contracts with no invariant between them:
`hold.anchor` moves forward with every new §7 buy take; `tier_event_date` is frozen at
the cross that admitted the row. Whenever a name takes a marker **after** its T2 cross
fired, the pair (anchor > event) becomes causally unpairable for a plan, and the bridge
refuses it. That is exactly what happened on the week of 2026-10-12 (§3).

## 2. The 38 rows

Board bytes quoted from the run's actual input board — the frozen snapshot
`data/prophet/origination_sources/b16040c9b350b1a7dc00485ffb8cf094818e14699facad6453d442fa7539d363.json.gz`
(gzip decompresses to 2,814,843 bytes, sha256 `b16040c9…` re-verified byte-for-byte;
bound to this run by `data/prophet/origination_receipts/39420247928-1-b16040c9b350b1a7.json`,
`recorded_utc 2026-10-20T18:30:08Z`, 30 `originated_plan_ids`, `source.sha256` = the
same hash, `source.board_asof 2026-10-19`). Error strings are quoted verbatim from
`site/prophet/index.json` → `intake.validation_failures`. `entry_signal` and `prophet`
blocks exist and are shape-uniform across all 38 (one keyset each); the gate reads
neither, so they are not quoted per row. Every row: `signal.tier_observed_date` =
`2026-10-19` = the run's price basis; `tier_observation_provisional` = `false`;
`signal.asof` = `2026-10-16`; `signal.last.confirmed_date` = `null`.

| # | Ticker | Plan id | Error (verbatim) | hold.anchor (frozen board) | tier/sub | tier_event_date | tier_observed | last marker |
|---|---|---|---|---|---|---|---|---|
| 1 | NUE | NUE-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-13' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-13 | 2026-10-19 | 2026-10-16 buy |
| 2 | OMC | OMC-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-13' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-13 | 2026-10-19 | 2026-10-16 buy |
| 3 | YETI | YETI-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |
| 4 | OGS | OGS-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-13' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-13 | 2026-10-19 | 2026-10-16 buy |
| 5 | NHC | NHC-BULL-20261015 | formation_date '2026-10-15' postdates tier_event_date '2026-10-13' | 2026-10-15 (src=cross, basing=2d, intact) | T2/deep | 2026-10-13 | 2026-10-19 | 2026-07-31 sell |
| 6 | MCO | MCO-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |
| 7 | CELH | CELH-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, launched) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |
| 8 | DRI | DRI-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |
| 9 | UGI | UGI-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-13' | 2026-10-16 (src=take, basing=1d, intact) | T2/shallow | 2026-10-13 | 2026-10-19 | 2026-10-16 buy |
| 10 | FRPT | FRPT-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-13' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-13 | 2026-10-19 | 2026-10-16 buy |
| 11 | CCK | CCK-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |
| 12 | SCI | SCI-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |
| 13 | SIGI | SIGI-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |
| 14 | SHW | SHW-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |
| 15 | LEA | LEA-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |
| 16 | CMC | CMC-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-13' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-13 | 2026-10-19 | 2026-10-16 buy |
| 17 | CUBE | CUBE-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-13' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-13 | 2026-10-19 | 2026-10-16 buy |
| 18 | HIG | HIG-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-13' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-13 | 2026-10-19 | 2026-10-16 buy |
| 19 | CDW | CDW-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-13' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-13 | 2026-10-19 | 2026-10-16 buy |
| 20 | AVY | AVY-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |
| 21 | ICE | ICE-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |
| 22 | LYB | LYB-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |
| 23 | BRO | BRO-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |
| 24 | PEP | PEP-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |
| 25 | EXE | EXE-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-13' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-13 | 2026-10-19 | 2026-10-16 buy |
| 26 | FUL | FUL-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-13' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-13 | 2026-10-19 | 2026-10-16 buy |
| 27 | AR | AR-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-13' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-13 | 2026-10-19 | 2026-10-16 buy |
| 28 | AGYS | AGYS-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-13' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-13 | 2026-10-19 | 2026-10-16 buy |
| 29 | PPG | PPG-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |
| 30 | LULU | LULU-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |
| 31 | ENOV | ENOV-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-13' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-13 | 2026-10-19 | 2026-10-16 buy |
| 32 | HRL | HRL-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |
| 33 | HSY | HSY-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |
| 34 | AXP | AXP-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-13' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-13 | 2026-10-19 | 2026-10-16 buy |
| 35 | NXST | NXST-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |
| 36 | TXT | TXT-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |
| 37 | WU | WU-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |
| 38 | CHWY | CHWY-BULL-20261016 | formation_date '2026-10-16' postdates tier_event_date '2026-10-15' | 2026-10-16 (src=take, basing=1d, intact) | T2/deep | 2026-10-15 | 2026-10-19 | 2026-10-16 buy |

**Class, all 38 rows: LEGITIMATE.**

## 3. Pattern groups and episodes

One error pattern exists in this run, in three date-cohorts (calendar: 2026-10-13 =
Tuesday, 10-15 = Thursday, 10-16 = Friday, 10-19 = Monday):

| Group | Error string (template) | Count | Cohort / episode | Class | Owning contract |
|---|---|---|---|---|---|
| P1 | `formation_date '2026-10-16' postdates tier_event_date '2026-10-13'` | 15 (incl. UGI, the one T2/shallow) | Tue 10-13 T2 cross fire → Fri 10-16 §7 take re-anchor, 3 sessions later | LEGITIMATE | pairing of `confluence_tiers._tier_dates` (immutable event) with the §7 take anchor, policed by `prophet_bridge._resolve_candidate_signal_dates:1045-1049` |
| P2 | `formation_date '2026-10-16' postdates tier_event_date '2026-10-15'` | 22 | Thu 10-15 T2 cross fire → Fri 10-16 §7 take re-anchor, 1 session later | LEGITIMATE | same |
| P3 | `formation_date '2026-10-15' postdates tier_event_date '2026-10-13'` | 1 (NHC) | No take (last §7 marker is a 2026-07-31 **sell**), so `hold.py` fell back to the last 3D cross-up (`anchor_src="cross"`, `engine/hold.py:124-134`) which landed 10-15, after the 10-13 event | LEGITIMATE | same; the cross-fallback path, not a take |

Episode history (same string, earlier checkpoints of `site/prophet/index.json`):
16 of 20 clock failures (checkpoint 2026-10-15), 20/31 and 19/31 (2026-10-16), 13-14/27
(2026-10-17), 13/27 (2026-10-18, where wrapper staleness errors dominated because the
board was stuck at `as_of 2026-10-14`), then **38/38 at BASE** — the flare is the
residue after the 10-17→10-19 board-staleness episode cleared (at BASE the wrapper
clocks are clean: board `as_of 2026-10-19`, `price_through 2026-10-19`,
`staleness.basis "panel_majority"`, `age_days 0`). House precedent for this exact
shape: the 2026-08-09 outage window's CCJ/SHEN/URG/UUUU class, filed as the engine's
own "chronology" refusals — `tests/test_prophet_outage_backfill_20260811.py:359-369`
quotes the identical error string for CCJ (`formation_date '2026-08-05' postdates
tier_event_date '2026-08-03'`).

Intended contract (tests): `tests/test_prophet_arena_clock_parity.py:249-330`
originates T1/T2 only with formation strictly before the event (T1 formation 2026-04-01
/ event 2026-04-28; T2 formation 2026-03-15 / event 2026-04-29) and pins
`signal_date_basis == "tier_event_date"`; `tests/test_prophet_bridge.py:572-620`
exercises the wrapper-clock fail-closed paths of the same stage. No test asserts that a
formation-after-event row should originate — the refusal is the contract.

## 4. Artifact contradiction found and how it was resolved

The packet says the board rows come from `site/factordata/us_standouts.json` at BASE.
That artifact is a **later re-render of the same `as_of 2026-10-19` stamp** and is NOT
the board the census run read:

- BASE site board sha256 `98eec0e2859aa8a0eab49be768876abce9caa06ee17b78a091fc02df6020ba44`,
  last committed 2026-10-20 11:10:29 -0700 ("engine-render: regime recompute +
  re-render 2026-10-20"). It has **no `.buy` row for BRO** (BRO appears only in
  `candidate_pool.rows` with null `hold`/`signal`).
- The failing run's receipt (`data/prophet/origination_receipts/39420247928-1-….json`,
  `recorded_utc 2026-10-20T18:30:08.605Z` = 11:30:08 -0700, 30 originated plans —
  matching `intake.originated: 30` and the 30 `plans` rows with `plan_asof
  "2026-10-20"`) freezes its input at sha256 `b16040c9…`, and that snapshot **does**
  contain the BRO buy row quoted in §2. The snapshot is committed at BASE and its bytes
  hash-verify against the receipt.
- No board commit back to 2026-10-19 07:59 -0700 contains a BRO `.buy` row; the run's
  board generation was overwritten in the working tree before any commit captured it.

Consequence for classification: BRO's row is **not missing evidence** — its bytes are
recoverable and quoted (§2 row 23) from the run's own frozen source. But any census
performed against the BASE site board alone would mis-handle BRO; this census used the
frozen snapshot (a stronger, committed source standard). All other 37 rows exist
byte-identically in both generations for the fields quoted.

## 5. Classification ruling (why LEGITIMATE, not SOURCE DEFECT / MISSING EVIDENCE)

- **LEGITIMATE — 38/38.** For each row's *current* base formation (the 10-16 take; NHC's
  10-15 cross-fallback), no causal tier event exists at-or-after the formation: the only
  fired event on record is the immutable T2 cross close of 10-13/10-15
  (`engine/confluence_tiers.py:19-20`). The candidate genuinely lacks a causal signal
  clock for the formation it would be keyed on, and the engine correctly declines to
  substitute one (`engine/prophet_bridge.py:4513-4514`). Observation clocks are present
  and consistent (`tier_observed_date` = price basis `2026-10-19` on every row).
- **SOURCE DEFECT — 0/38.** The packet's example of an internally contradictory record
  ("formation date later than the claimed tier event") matches the *shape*, but no
  producer writes a false or impossible value: `scripts/build_stock_library.py:4290`
  writes the true latest §7 buy-marker date; `engine/hold.py:203-213` measures from it
  lawfully; `engine/confluence_tiers.py:388` writes the true cross close;
  `engine/signal_gate.py:531` copies it. The tension exists only **across two
  independently-lawful clocks** when the intake pairs them into one candidate. A real
  chronology defect on this board looked different: SYY-BULL-20260731
  (`data/prophet/ledger_corrections.jsonl`, `basis: "creation-vintage chronology
  audit"`, `market_session_lag: 3`, mixed-vintage board) — a ledger-corrected defect,
  after which the intake clocks were hardened into the current gate.
- **MISSING EVIDENCE — 0/38 at the run.** Every field the gate reads is present and
  well-formed in every row (tier T2, event date, observed date, anchor). The one
  evidence gap is at BASE for BRO only (§4), and it is closed by the committed frozen
  snapshot rather than guessed.

## 6. Denominator reconciliation (Q3)

`intake` counters at BASE: `considered 104` (= `.buy` rows), `admitted 81`
(refused earlier: `refused_band_low 19` + `refused_status {buy_soon 1, extended 1}` +
`refused_direction {down 2}` + `refused_tier {}`), pass-1 skips
`duplicate_id_blocked 7` + `reorigination_blocked 6` (keys DD/DOW/MDU/TDY/WDFC/YELP
`-BULL`), `eligible_after_skips 68`, `validation_failed 38`, `originated 30`
(68 − 38 = 30 ✓). Receipts: `passed 74`, `planned 30`, `declined 62`, `open_now 12`;
groups `plan_not_built 39 + already_open 12 + not_ready 1 + ran_too_far 9 +
conviction_low 11 + pointing_down 2 = 74` ✓.

- `validation_failed` (38) vs `plan_not_built` n=39: **all 38 failure tickers are
  members of the 39**; the artifact discloses only the top 14 names (cap
  `REFUSAL_NAMES_CAP = 14`, `engine/prophet_bridge.py:484`, applied at 1603 with the
  true count kept at 1602): `NUE,OMC,YETI,OGS,NHC,MCO,CELH,DRI,UGI,FRPT,CCK,SCI,SIGI,SHW`
  — every one a failure ticker. Proof of containment without the cap: the five other
  groups disclose their complete rosters (n ≤ 14 each) and contain no failure ticker,
  and an exact reproduction of `refusal_receipts` (engine function re-run read-only on
  the frozen board with the run's open-key and originated sets) returns n=39 with a
  byte-identical first-14 ordering and membership = the 38 + **AZN**.
- **The one name in `plan_not_built` but not in the failures: AZN.** Mechanism: AZN's
  frozen-board row carries `hold.anchor 2026-10-18` (src=take) → would-be id
  `AZN-BULL-20260818`, which already exists and is **closed** (`site/prophet/index.json`
  plans: `AZN-BULL-20260818, closed=true, phase=overtime, pulse "closed · timed out"`),
  so pass 1 suppressed it as a duplicate id (`engine/prophet_bridge.py:4388-4391`) —
  no validation failure is recorded for duplicate skips; its formation (08-18) does not
  postdate its event (10-15), so no clock error exists either. Counter cross-walk: the
  7 duplicate-id skips = AZN (closed id → `plan_not_built`) + 6 whose ids are open
  plans (→ `already_open`); the 12 `already_open` = those 6 + the 6 W1-blocked keys.
- Names in the failure set but not in any other receipt group: all 38 (they appear in
  `plan_not_built` only). The remaining 10 of the frozen board's 48 anchor>event rows
  never reached the clock gate: `LMT,KRG,RHP,EGP,HXL,KIM` (conviction_low), `COP,ALRM`
  (ran_too_far), `SSD` (not_ready), `YELP` (already_open / W1).

## 7. Ledger overlap (Q4) — none

- `data/prophet/ledger_corrections.jsonl` (9 rows at BASE): every row has
  `corrects_id: "SYY-BULL-20260731"` (fields entry_date, formation_date,
  integrity_reason, integrity_status, price_basis_date, recorded_at, signal_date_basis,
  signal_tier, source_marker_date; corrected_at 2026-08-08). **SYY is not among the 38** —
  no overlap.
- `data/prophet/ledger_quarantine.json` (`count: 11`, quarantined_on 2026-08-06):
  `KKR-BULL-20260318, FOXF-BULL-20260526, AEO-BULL-20260415, EXC-BULL-20260609,
  SYK-BULL-20260518, AMPH-BULL-20260604, CCS-BULL-20260601, U-BULL-20260327,
  KSS-BULL-20260522, SYY-BULL-20260731, REZI-BULL-20260703`. **No ticker overlap with
  the 38.**

## 8. Repair owners

1. **The refusal itself — `engine/prophet_bridge.py` clock-provenance gate**
   (`_resolve_candidate_signal_dates` 957-1094; error 1045-1049; recording 4515-4522).
   No defect found; the gate is correct accounting and preserves the old refusal
   history (failures are itemized in `intake.validation_failures`, `lossless: true`).
   No repair recommended. Backdating formation to the event is a substitute-clock guess
   and is out of scope by the packet and by the code's own comment.
2. **If the house wants these names originatable**, the decision belongs to one of the
   two clock owners, not to the intake:
   - `engine/confluence_tiers.py` `_tier_dates`/`cascade` (370-391; immutability
     contract at 19-20) with `engine/signal_gate.py:446-447, 516-533` — smallest
     producer-side change: register a fresh tier event when a §7 buy take fires after
     the cross (the take's emitted close already flows in as `take_event_date`). This
     changes the documented "immutable cross close" contract and would need its own
     acceptance lane.
   - `scripts/build_stock_library.py:4286-4291` + `engine/hold.py:119-136` — smallest
     anchor-side change: freeze the hold anchor at/below the tier event on fired-tier
     buy rows. This falsifies the W6-C display tracker's actual-base measurement and
     is not recommended.
   - `engine/prophet_bridge.py` `select_candidates` + `refusal_receipts` (1499-1604) —
     disclosure-vocabulary option only: a named board-level refusal code for "new base,
     event already fired" would move this cohort out of `validation_failures` into the
     receipts groups; changes no clock and no admission.
3. **No repair needed for accounting**: the cohort is chronic and self-churning
   (13-20/night the prior week; 38 at BASE after the staleness episode cleared). A name
   re-enters candidacy when a fresh cross fires on/after its current base, or it drops
   off the board; the refusal persists correctly in between.

## 9. Evidence index

- `site/prophet/index.json` @ BASE: `intake.validation_failed`, `intake.validation_failures`
  (38), `intake.receipts.{considered,passed,planned,declined,open_now,groups}`,
  `intake.{admitted,eligible_after_skips,duplicate_id_blocked,reorigination_blocked,
  reorigination_blocked_keys,originated}`, `plans` (656; 30 with `plan_asof 2026-10-20`),
  `source_board_asof`, `board_read_lineage`.
- `site/factordata/us_standouts.json` @ BASE: `as_of`, `.buy` (104 rows; 37 of the 38
  present, BRO absent), `candidate_pool.rows` (BRO stub), sha256 recorded in §4.
- `data/prophet/origination_sources/b16040c9….json.gz` @ BASE: the run's frozen input
  board (all 38 rows present; hash-reverified).
- `data/prophet/origination_receipts/39420247928-1-b16040c9b350b1a7.json` @ BASE: run
  binding (recorded_utc, 30 plan ids, source sha256, staleness block).
- `engine/prophet_bridge.py` @ BASE: 58-67, 853-954, 957-1094, 1499-1604, 4343-4408,
  4499-4522. `scripts/build_prophet.py` @ BASE: 115, 1641-1685, 2296-2323, 2460-2509,
  3156-3160. `scripts/build_stock_library.py` @ BASE: 4255-4295.
  `engine/hold.py` @ BASE: 95-213. `engine/signal_gate.py` @ BASE: 211-236, 440-533.
  `engine/confluence_tiers.py` @ BASE: 19-20, 370-391.
- `tests/test_prophet_arena_clock_parity.py` @ BASE: 249-330 (passing shapes), 32-56
  (`_tier_row` sets `hold.anchor = formation_date` by construction).
  `tests/test_prophet_bridge.py` @ BASE: 558-620. `tests/test_prophet_outage_backfill_20260811.py`
  @ BASE: 356-384 (chronology class precedent).
- `data/prophet/ledger_corrections.jsonl`, `data/prophet/ledger_quarantine.json` @ BASE
  (§7). Prior checkpoints of `site/prophet/index.json`: ad444311ef1, 474ddc123d5,
  53618566567, 45fa76f152e, 3c322c12d49, 5e0cddcff85, 859e5bb91c4 (episode history).
- Method note: the receipts reproduction re-ran `engine.prophet_bridge.refusal_receipts`
  read-only (in /tmp, no repo writes) on the frozen board with the run's pre-origination
  open-key set (published open plans minus the 30 originated that night) and the 30
  originated assets, with the 14-name display cap lifted for full membership only; it
  reproduced every published group count and the exact first-14 ordering.

## 10. Seat adjudication (Fable Meta-CEO seat 69eb9a1c, 2026-10-21 03:3xZ)

Ruling: **ACCEPTED — 38/38 LEGITIMATE, 0 source defects, 0 missing evidence.** The gate
compares two clocks that are each lawfully produced (`hold.anchor` advances with every §7
buy take; `signal.tier_event_date` is the immutable cross close) and correctly declines to
substitute a clock when the current base postdates the only fired event. Accounting is
correct (`intake.validation_failures` lossless, `plan_not_built` n=39 = 38 + AZN duplicate-id),
the old refusal and correction history is preserved, and no intake repair is authorized.

Consequences for the program:

1. **No clock repair.** Backdating formation to the event (option 8.2b) is a substitute-clock
   guess and is refused. Registering a fresh tier event on a post-cross take (option 8.2a)
   changes the documented immutable-cross-close contract and the point-in-time validity of
   the tier series; it is a Prophet science decision, not an accounting fix, and is held as
   **D-CLOCK-1 (reserved: incumbent Prophet owner + quant validation lane; not this wave)**.
2. **Disclosure refinement (option 8.2c) is adopted as a Stage 1 follow-on**, sequenced
   after PR #9921 (generic `validation_failed` receipt) merges: a named board-level receipt
   for "new base formed after the tier event fired" so the why-not surface states the actual
   reason instead of the generic "plan data didn't verify". No clock, admission or count
   changes; same owning contract (`engine/prophet_bridge.py` `refusal_receipts`) and the
   same test file as #9921. Lane id to mint: `pro-receipt-newbase-20261021-r1`.
3. **B-ledger**: the 38-refusal investigation obligation is dispositioned with evidence
   (this census, §§1–9); the positive origination count is not a target.
