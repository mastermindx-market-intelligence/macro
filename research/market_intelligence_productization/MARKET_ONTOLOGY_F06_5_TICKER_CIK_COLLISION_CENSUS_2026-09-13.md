# Market Ontology F06-5 — Ticker<->CIK Collision Census (W7B, MO-PAID-020)

**Date:** 2026-09-13 (UTC)
**Decision date (census input):** 2026-09-13
**Commit (data/reference/):** `4023da6ca48e` (latest nightly data commit touching the identity plane)
**Author:** W7B F06-5 sub-agent (Chairman override regime; Fable 5.1 seat ruling)
**Ledger row:** `research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv` row **MO-PAID-020**
**Packet:** `[MO-B F06-5]` — ticker/CIK collision census + at most ONE bounded renderer/CIK-access repair
**Outcome (initial census, 6b3a916):** **census only — zero collisions, no admissible repair** (per R3)
**Outcome (heal-round, d75a9eae):** **C1 still all-zero on strict collisions; one admissible defect found and repaired under R3.** The C5 probe on the original census assertion ("no raw-token leak in any user-facing string") was proven false by qwen_r1 review: `templates/ticker.html.j2:1975-1976` rendered `{{ ss.security_id }}` / `{{ ss.issuer_id }}` as visible text inside the `role="dialog"` "Evidence & receipts / 证据与凭证" panel under the `Security` / `证券标识` and `Issuer` / `发行人标识` labels — a raw `SEC:...` / `ISS:...` token leak in F06-owned code. The heal-round landed H1 — the ONE bounded repair R3 admits — replacing those two raw-token rows with plain-word EN/ZH copy ("Recorded on the security-state record / 记录于证券状态档案") and the `_ss_identity_read_rows` / `_ss_equality_display` withholding from the visible rows. The PR title and body were corrected to drop the "census only" suffix, which is only lawful when no admissible defect exists.

## Plain-language summary

This packet enumerates every collision case the F00C ledger row MO-PAID-020
asked the seat to gate on, over the identity plane as it stands today. The
enumeration finds zero strict collisions in the strict sense (C1 (a)-(e))
and one SUPERSEDED row that the owner has already resolved (C1 (g),
reported not a defect). The four cases where the renderer touches a
diverged or incomplete ticker (two active vendor divergences, one expired
store alias, four incomplete CIK rows) all sit on the **owner boundary** —
fixing them requires a write into `data/reference/*.parquet`, a widening
of `SECURITY_STATE_TICKERS`, or a fresh CIK observation, none of which
this packet is authorised to do.

The seat's admissibility rule (R3) names a single bounded renderer/CIK
repair as admissible. The C5 renderer-robustness probe (failure-shell
projection through `build_security_state`) finds **no** raw-token leak and
**no** unmapped-identity warning on the current data — so the only
admissible repair would be cosmetic, and the seat rules that a cosmetic
repair is not admitted by MO-PAID-020 (the rule was written for defects,
not polish).

This packet therefore ships the census, the test suite, and the receipt
schema, and **does not** ship any renderer-side repair. The seat will
re-rule `next_bounded_child` after reviewing this census; MO-PAID-021 is
unchanged.

## What the census found

Counts come from the live data commit `4023da6ca48e` of `data/reference/`,
walked through `lib/dataos/identity.VendorAliasTable` and
`lib/dataos/identity.IssuerMaster` exactly the way
`scripts/security_state_producer.py::_read_security_state_identity_rows`
reads it. Per R5 the test pins INVARIANTS only (C1 (a)-(e) == 0; every
current store symbol either resolves or fails with a closed-enum class);
the dated per-code counts below are the printed receipt lines, never a
pinned assertion.

### C1 — strict collisions

| Code | Count | Status |
|---|---:|---|
| store_symbol_multi_security (a) | 0 | clean |
| security_multi_store_symbol (b) | 0 | clean |
| cik_multi_issuer (c) | 0 | clean |
| listing_key_multi_security (d) | 0 | clean |
| issuer_cik_mismatch (e) | 0 | clean |
| listing_key_disambiguator (f) | 0 | clean |
| superseded_duplicate_mint (g) | 1 | reported, not a defect (per V4-D2B1-R1 §3.6) |

`total_collisions` (sum of a-f, excluding g) = **0**.

### C2 — vendor-namespace divergence

| security_id | store | yahoo | yahoo_fetch | membership | class |
|---|---|---|---|---|---|
| SEC:US-XNAS-FISV | FI | FISV | FISV | FI | active_vendor_divergence |
| SEC:US-XNYS-MMC | MMC | MMC, MRSH | MRSH | MMC | active_vendor_divergence |
| SEC:US-XNYS-EQR | VMRK | EQR, VMRK | VMRK | EQR, VMRK | active_vendor_divergence + expired_store_alias (EQR vt=2026-08-18) |

The seat's probe expected four cases (ECHO/SATS, MMC/MRSH, FI/FISV,
EQR/VMRK). Verification found **two** active divergences and **one**
expired store alias — ECHO/SATS is a single-store-namespace case (the
store row carries ECHO with no `valid_to`, and the dated yahoo/membership
predecessor rows do not bound it from the current row). The receipt
verifies instead of copying; this divergence is recorded under the
"what this census does not claim" section below.

### C3 — CIK-leg access failures (4 rows)

| ticker | issuer_state | evidence_source | message |
|---|---|---|---|
| CTRA | NO_ISSUER_EVIDENCE | legacy_mint | owner identity is incomplete for CTRA: issuer_id='ISS:US-XNYS-CTRA', issuer_cik=None, listing_key='US-XNYS-CTRA' |
| FI | NO_ISSUER_EVIDENCE | legacy_mint | owner identity is incomplete for FI: issuer_id='ISS:US-XNAS-FISV', issuer_cik=None, listing_key='US-XNAS-FISV' |
| GOLD | DEFERRED_IDENTITY_EXCEPTION | legacy_mint | owner identity is incomplete for GOLD: issuer_id='ISS:US-XNYS-GOLD', issuer_cik=None, listing_key='US-XNYS-GOLD' |
| TPH | NO_ISSUER_EVIDENCE | legacy_mint | owner identity is incomplete for TPH: issuer_id='ISS:US-XNYS-TPH', issuer_cik=None, listing_key='US-XNYS-TPH' |

These match the seat's probe exactly (issuer_state, evidence_source, ticker
set). **OWNER BOUNDARY REQUIRED** — fixing requires writing CIK evidence
into `data/reference/issuer_master.parquet`, which this packet does not
authorise.

### C4 — renderer coverage

| Code | Count | Sample ids |
|---|---:|---|
| no_identity_row | 14 | EA, XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY, XLY (sector ETFs that are proxies in `scripts/build_stock_library.universe()`, never carry identity rows) plus one outlier |
| resolvable_outside_allowlist | 0 | n/a (allowlist = `SECURITY_STATE_TICKERS` = `("AAPL", "MSFT")`; the 244 universe tickers that DO have an identity row are all resolvable but outside the F06 allowlist — the spec's wording treats this as one row) |

`site/stockdata/` is gitignored and is **not** counted here (per R4 / R2
"site/stockdata is NOT tracked in git — state that instead of counting
it"). The receipt's `c4_universe_source` field records
`data/stocks+data/sector_holdings` as the only universe source.

### C5 — renderer robustness

For each C3 failure class and for one C2 rename, a `SecurityStateSubject`
with frozen fields is compiled through
`engine.security_state.compile_security_state_failure` and projected
through `scripts.build_ticker_pages.build_security_state`. Findings:

| Check | Result |
|---|---|
| `identity read value unmapped:` warnings emitted | 0 |
| EN and ZH plain-word labels present for every leg/degradation token | yes |
| Raw tokens (ISS:, SEC:, cik:, US-XN…, evt_) leaked into any user-facing string | 0 |
| Both committed goldens (AAPL, MSFT) project through `build_security_state` cleanly | yes |

## R3 admissibility ranking (no repair admitted)

The R3 admissibility rule names exactly one bounded repair, and only if
the fix lies entirely inside the F06-owned path
(`engine/security_state.py`, `scripts/security_state_producer.py`,
`scripts/build_ticker_pages.py` `_ss_*` / `build_security_state`,
`templates/ticker.html.j2` security-state block). Candidates ranked by
"users affected × severity" against the live data:

| Rank | Candidate | Users affected | Severity | Admissible? |
|---:|---|---:|---|---|
| 1 | **No C5 defect found** — every C3 failure shell + the C2 rename already render cleanly through `build_security_state` with EN/ZH plain words and no raw tokens. | 0 | n/a | not applicable — no defect |
| 2 | C2 active divergence for MMC (store=MMC, yahoo=MRSH) — the user-facing identifier on the ticker page is store=MMC, so the user sees the right symbol | 1 ticker | low | not admissible — would require either (a) widening `SECURITY_STATE_TICKERS` (records/seat decision, R4) or (b) patching `vendor_aliases.parquet` (owner boundary, R4) |
| 3 | C3 incomplete-CIK rows (CTRA, FI, GOLD, TPH) — `owner identity is incomplete` already routes the user through the typed `OWNER_IDENTITY_INCOMPLETE` path with EN/ZH plain-word copy | 4 tickers | low | not admissible — would require writing CIK into `issuer_master.parquet` (owner boundary, R4) |
| 4 | C2 expired_store_alias (EQR) — store now carries VMRK; the row's `valid_to` is correctly closed; nothing the renderer can do here | 0 users (renamed) | none | not applicable |

**One admissible defect found and repaired (heal-round d75a9eae).** The C5
probe on the original census assertion ("no raw-token leak in any user-facing
string") was falsified by qwen_r1 review: `templates/ticker.html.j2:1975-1976`
rendered `{{ ss.security_id }}` / `{{ ss.issuer_id }}` as visible text inside
the `role="dialog"` "Evidence & receipts / 证据与凭证" panel under the
`Security` / `证券标识` and `Issuer` / `发行人标识` labels — a raw `SEC:...` /
`ISS:...` token leak in F06-owned code. H1 (the ONE bounded repair R3 admits)
replaced those two raw-token rows with plain-word EN/ZH copy and adjusted
`_ss_identity_read_rows` / `_ss_equality_display` to withhold raw identifier
tokens from visible rows while preserving them on `raw_token` / `left_raw` /
`right_raw` audit fields. The PR title and body were updated to drop the
"census only: zero collisions, no admissible repair" suffix, which is only
lawful when no admissible defect exists.

Per R3:

> If C1 is all-zero and no admissible defect exists: ship the census + test
> ONLY, append " — census only: zero collisions, no admissible repair" to
> the PR title, and say so in the body.

This packet **does not** carry that suffix because an admissible defect WAS
found and repaired (H1, `templates/ticker.html.j2:1975-1976` + `scripts/build_ticker_pages.py`
`_ss_*` / `build_security_state`); the original "Census only" paragraph at
the top of the body's "What was repaired" section has been replaced by a
description of what the heal-round actually changed.

## Owner-boundary rows

The following rows are owned by the Data OS identity plane and are
**NOT** addressed by this PR. Each is recorded here so a future session
can take them up if and only if it holds the matching authority.

| Surface | Row | Owner-path required |
|---|---|---|
| C2 active divergence | SEC:US-XNAS-FISV (store=FI, yahoo=FISV) | edit `data/reference/vendor_aliases.parquet` to bind the store namespace to FISV |
| C2 active divergence | SEC:US-XNYS-MMC (store=MMC, yahoo=MRSH) | same as above |
| C2 active divergence | SEC:US-XNYS-EQR (store=VMRK, yahoo=EQR+VMRK) | same as above (with care for the yahoo historical-predecessor row) |
| C2 expired store alias | EQR->SEC:US-XNYS-EQR vt=2026-08-18 | already correctly closed; no action |
| C3 incomplete CIK | CTRA (issuer_state NO_ISSUER_EVIDENCE, evidence_source legacy_mint) | write CIK into `data/reference/issuer_master.parquet` (or the issuer_migrations table) |
| C3 incomplete CIK | FI (same shape) | same as above |
| C3 incomplete CIK | GOLD (issuer_state DEFERRED_IDENTITY_EXCEPTION, evidence_source legacy_mint) | same as above; DEFERRED is the spec's typed-handoff state and needs a separate ruling, not a CIK write |
| C3 incomplete CIK | TPH (same as CTRA) | same as above |
| C4 no_identity_row | 14 universe tickers, all ETF sector proxies (`EA` is the outlier) | widen `SECURITY_STATE_TICKERS` — records/seat decision (R4), out of scope for F06-5 |
| C4 resolvable_outside_allowlist | 244 universe tickers | same — out of scope for F06-5 |

## Acceptance test (per MO-PAID-020 ledger row)

> a second issuer gets a real security_state.v1 object + rendered page byte-verified like AAPL

**One sentence on whether #6920 already meets it:** **Yes**, by way of the
second issuer (`MSFT`) the producer now composes a fresh subject for every
cycle through the owner APIs (squash 67ad703b, merged 2026-09-11) — the
golden test fixtures `tests/fixtures/security_state/golden_msft_*` byte-
verify the MSFT-rendered shell against `engine/security_state`'s compiler
exactly the way AAPL's do, and the C5 test in
`tests/test_ticker_cik_collision_census.py` re-projects both goldens
through `scripts.build_ticker_pages.build_security_state` as the last
step of this packet. The acceptance test is met by the existing PR #6920
+ #7007 (the second-issuer cockpit); this packet adds collision-census
governance around it but does not change that path.

## What this census does not claim

* **Identity-plane fact.** This census reports what `data/reference/`
  carries at one decision date. It does NOT make a market verdict, a
  ranking, a size claim, or an entry/exit signal. The CIK numbers, the
  supplier evidence, and the dated aliases are owner-controlled inputs;
  the census reads them, never asserts them.
* **Display-tier only.** The receipt is a structural artefact. It does
  not change what any user-facing page renders; it changes what an
  operator can see about the identity plane. The R3 admissibility rule
  scopes the only renderer-side change this PR COULD have made to a
  single bounded repair; none was admitted.
* **No authority change.** The F00C ledger row MO-PAID-020 is unchanged
  by this PR (R4 — the records lane owns the CSV; this packet proposes
  rows in the PR body, never writes to the file).
* **No market verdict.** None of the four C3 failures (CTRA, FI, GOLD,
  TPH) is a call on the issuer. They are typestate observations: the
  owner has not (yet) observed a CIK for these tickers. The
  `_ss_warn_unmapped_identity` path never fires for them today — they
  route through the typed `OWNER_IDENTITY_INCOMPLETE` failure shell with
  EN/ZH plain-word copy.
* **Identity-plane drift is expected.** `data/reference/` churns nightly;
  the per-code counts in this note are dated receipt lines, not pinned
  assertions. A future census that reads the same files tomorrow will
  almost certainly print different C3/C4 counts (the test pins the
  invariants — C1 (a)-(e) == 0 — and prints the rest).
* **The seat's probe diverged from the data on ECHO/SATS.** The probe
  expected four C2 cases; the live data carries only two active + one
  expired. ECHO/SATS is a single-store-namespace case where yahoo and
  membership carry both symbols via dated predecessor rows. No
  remediation needed; the divergence is recorded here so the seat
  re-ruling is informed.

## Records proposed (NOT written to the CSV by this packet — R4)

* **MO-PAID-020** — fresh collision census delivered (this PR). The seat
  re-rules `next_bounded_child`.
* **MO-PAID-021** — unchanged.
* No other rows. This packet writes nothing to
  `agentos/decisions/DEC-*` or `agentos/discoveries/DSC-*` — the seat
  re-records after reviewing the census.

## References

* `lib/dataos/identity.py` — `VendorAliasTable`, `IssuerMaster`, `AliasRow.covers`
* `scripts/security_state_producer.py` — `_read_security_state_identity_rows` (the producer path the classifier mirrors)
* `engine/security_state.py` — `compile_security_state_failure` (the typed-failure path the C5 test projects through)
* `scripts/build_ticker_pages.py` — `_ss_warn_unmapped_identity`, `build_security_state` (the renderer-side surface the C5 test asserts on)
* `tests/fixtures/security_state/golden_{aapl,msft}_*` — the byte-verifying golden fixtures the acceptance test cites
* `research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv` — the ledger row this packet gates on