# S0 register amendment A01 — DRAFT

This is an SNI-local DRAFT contract. It consumes owner-supplied values from
Data OS identity, Company Event/Earnings, FIF, Capital Structure, Stock
Identity, Options, Research Vault, and qledger/Evaluation. It does not
re-implement those owners. Identity ids are caller-supplied opaque strings;
unknown identity stays UNRESOLVED / null.

**status:** DRAFT

**applied:** false

**amends:** `research/single_name_intelligence/protocols/S0_PROTOCOL_REGISTER.md`

**amends_blob:** `5cea5c88335133e7684200b694f0d170ca4ae5b2` (register blob of the tree that carries this draft — the INT1 integration branch)

This pin becomes the origin/main register blob when INT1 merges.

**drafted_by:** grok-4.6 lane S0D under seat 508c3757

**drafted_at:** 2026-10-13T03:11:37Z

A01 changes no status, budget, split, horizon, null or retirement rule of the frozen register; it only declares successor pointers and records UNRESOLVED identity facts. It takes effect only when the seat accepts it under register §2.

## 2. Successor table

One row per retirement or freeze of `(protocol_id, version, split)`. Successor
pointers live only here. The frozen register §7 cells that still read
"— (none declared)" are left untouched.

| protocol_id | retired_version | split | retirement_source | successor_pointer | successor_status | budget_floor_carried | owner |
|---|---|---|---|---|---|---|---|
| P01 | v1 | TUNE | research/single_name_intelligence/protocols/S0_PROTOCOL_REGISTER.md:322 (origin/main §7; information_leak) | P01 v2 — NOT DRAFTED; owner seat/S0 | NOT DRAFTED | 6 | seat/S0 |
| P02 | v1 | n/a (freeze, not a §7 retirement) | research/single_name_intelligence/protocols/S0_PROTOCOL_REGISTER.md:336 (origin/main §8 budget freeze: "frozen before the bridge, so a bridged successor cannot claim a fresh budget"); also §9 P02 L395 | bridged successor — BRIDGE-FROZEN; inherits the carried budget floor 4 per register §8 'Successors'; NOT DRAFTED | BRIDGE-FROZEN | 4 | seat/S0 |
| P03 | v1 | TUNE | research/single_name_intelligence/protocols/S0_PROTOCOL_REGISTER.md:323 (origin/main §7; information_leak) | P03 v2 — NOT DRAFTED; owner seat/S0; still BRIDGE REQUIRED | NOT DRAFTED | 4 | seat/S0 |
| P04 | v1 | TUNE | research/single_name_intelligence/protocols/S0_PROTOCOL_REGISTER.md:324 (origin/main §7; information_leak) | P04 v2 — DRAFT at research/single_name_intelligence/event_response/P04_V2_PREREG_DRAFT.md (not registered; no outcome) | DRAFT | 6 | seat/S0 |

Budget floors are the declared n values in register §8 (origin/main L335–L338).
A01 does not raise, lower, or refill them.

## 3. Successor rule (SL §8)

Restated by citation only (Split and Contamination Law
`research/single_name_intelligence/protocols/S0_SPLIT_AND_CONTAMINATION_LAW.md` §8):

- A successor is a **new version** (SL §8 step 5, L189).
- Nothing is refilled (SL §8 L144: never repaired, refilled or dropped; step 5 L189: never refills retired members).
- A successor's budget is at least the carried count (SL §8 step 5 L192; register §8 **Successors** L331).
- Retired rows are never deleted (SL §8 step 3 L185; register §7 L318).

P04 v2 exists as a DRAFT at
`research/single_name_intelligence/event_response/P04_V2_PREREG_DRAFT.md`
(sibling branch head `a2d33b153a0eb99bbd525ea506c78f0577e1ede1`; status DRAFT,
`registered` false, no outcome). Pointing at that path does not register it
and does not edit register §7.

## 4. US/Mag-7 residual-transfer pointer

Family `sni.us_transfer.RESID-DIR-US`.

**status:** DRAFT — pointer only

**path:** `research/single_name_intelligence/us_transfer/A8_US_RESIDUAL_TRANSFER_PREREG_DRAFT.md`

A01 points at this path only. Whether or not the file is present, A01 does not register it and does not claim it is registered.

**NOT P07** (P07 = EVT-RESPONSE-WINDOW, intraday, procurement-gated).

**cohort:** hindsight-selected cohort: stress of method mechanics only, never transfer evidence.

This pointer is not a protocol retirement row and carries no budget change.

## 5. TCEHY identity and admission (UNRESOLVED)

Identity/admission row, not a protocol. `TCEHY` is a display label only.
No SNI lane may mint, derive or normalise an issuer or security id for this
instrument from its ticker, name, CIK, FIGI or ISIN.

| field | value |
|---|---|
| label | TCEHY |
| canonical_issuer_id | null |
| security_id | null |
| issuer_link | UNRESOLVED |
| admission | NOT ADMITTED |

### Facts (each with source)

1. A yahoo price file is present at `data/yahoo/TCEHY.parquet` (origin/main
   blob `0c03b5f83178ddf2ed9c25f39ef7688139ed24be`, `git rev-parse` metadata
   only). Presence is not admission.
2. TCEHY is absent from `data/reference/security_master.parquet` (origin/main
   blob `85ef75104840b6b5be3aceeac21f1dbfabad6472`, `git rev-parse` metadata
   only; this lane did not open the parquet). U0 reuse map L15 and L20:
   "UNRESOLVED (absent from security_master)".
3. KWEB is a proxy and never a Tencent quote (register P13 L645:
   `engine/hk_adr_bridge.py` pairs 0700.HK with KWEB as `"proxy"` (L85);
   "KWEB is never a Tencent quote"). Independence Law L80 lists KWEB as a
   proxy exclusion. M0 L133–L134: the bridge pairs 0700.HK→KWEB (pair kind
   `proxy`); "KWEB is an ETF and is never a Tencent quote." KWEB price file
   `data/yahoo/KWEB.parquet` origin/main blob
   `d42bd75db56f8ad5c2530ee415262a0c68b913bd` (metadata only).
4. Tencent coverage profile (paraphrase of
   `config/single_name_intelligence/coverage_profiles/tencent.yml` L499–L507):
   no same-issuer ADR counter in Data OS; KWEB is an ETF proxy; the yahoo
   TCEHY price file exists (4,216 rows 2010-01-05..2026-10-08) and the
   profile records the `adr_h_basis.hkd_0700` cell as UNRESOLVED.
   L511: a proxy is not a basis; a TCEHY basis would need Data OS admission
   of the OTC ADR plus a carried ADS ratio.
5. U0 / M0 / E0 / IL / V0 status lines:
   - U0 reuse map L20: Tencent ADR `TCEHY` security_id UNRESOLVED (absent
     from security_master); canonical_issuer_id UNRESOLVED; yahoo file is
     price only.
   - U0 reference journey L36: 0700.HK J7 shows only the KWEB proxy,
     because TCEHY, 80700 and 89988 are absent from the masters.
   - M0 L135: yahoo TCEHY file (4,216 rows) exists and the cell is
     UNRESOLVED; presence is not admission.
   - E0 L155: yahoo TCEHY file now exists (4,216 rows) and Data OS
     security remains UNRESOLVED; presence is not admission.
   - IL L81: TCEHY is a Step 0 exclusion (source tencent.yml L499–L500).
   - V0 matrix L31: `data/yahoo/` holds `TCEHY.parquet`; that listing is
     path presence, and presence is not admission.
   - `data/reference/issuer_master.parquet` origin/main blob
     `6643e7eae37940d800659f7b4589f242ec70ef45`
     (`git rev-parse` metadata only).

### exit_conditions (ordered)

1. Data OS admits the security (owner: Data OS identity / security master).
2. An ADS-ratio owner exists (owner: Capital Structure / corporate actions;
   register P13 L653 cites M0 gap 3, M0 L205).
3. FX leg/clock receives Data OS market-data admission (owner: Data OS
   market data; M0 gap 5, M0 L207).
4. Then the seat may draft a Tencent leg for a P13-style DIAGNOSTIC only
   (owner: seat/S0).

Until every prior step is done by its owner, the row stays UNRESOLVED and
NOT ADMITTED. A01 does not perform any of those steps.

## 6. Owner follow-on: stale hk_adr_bridge comment

`engine/hk_adr_bridge.py` L83 still says TCEHY is "explicitly excluded:
thin/illiquid, not in yahoo store." L26 still routes 0700.HK to a group ETF
proxy and names OTC TCEHY as thin/illiquid. The yahoo TCEHY file is present
(fact 1). E0 L155 and L190, and U0 reuse map L31, already record the comment
as stale. This is an **OWNER FOLLOW-ON** (owner: the hk_adr_bridge module
owner). A01 does not edit `engine/`.

## 7. Authority

First-stage authority is false on all six flags. Nothing in A01 requests,
implies, or reserves authority. Nothing here is a rank, gate, size, signal,
escalation, or trade input.

| rank_authority | gate_authority | size_authority | signal_authority | escalation_authority | trade_authority |
|---|---|---|---|---|---|
| false | false | false | false | false | false |

A caller that tries to set any of these true is refused.

## 8. Language

This draft uses the S0 frozen vocabulary only. Exception phrases in use are
`UNRESOLVED`, `NOT ADMITTED`, and `is not admission`. A01 does not change a
status, budget, split, horizon, null, or retirement rule of the frozen
register.

## 9. Register errata

One erratum, **A01-E1**.

The summary sentence at `S0_PROTOCOL_REGISTER.md:129` (P01; P03) states counts
that no longer match the Status column of the same frozen register.

**register blob:** `5cea5c88335133e7684200b694f0d170ca4ae5b2`

**cited line:** `S0_PROTOCOL_REGISTER.md:129` (P01)

**status rows:** L115–L127

| class | stated at line 129 | derived from the Status column | protocols |
|---|---|---|---|
| RETIRED-CONTAMINATED | 0 | 3 | P01, P03, P04 |
| REGISTERED-GATED | 4 | 2 | P05, P06 |
| NOT SUPPORTED — BRIDGE REQUIRED | 6 | 5 | P02, P09, P10, P11, P12 |
| NOT SUPPORTED — PROCUREMENT-GATED | 2 | 2 | P07, P08 |
| DIAGNOSTIC | 1 | 1 | P13 |

The mismatch is consistent with the three Status cells (P01, P03, P04) having
been changed to RETIRED-CONTAMINATED and line 129 left stating the prior
counts.

A01 reads the Status column (rows L115–L127) as the register's statement.
This erratum changes no status, budget, split, horizon, null or retirement
rule. The register is not edited. Correcting line 129 is an OWNER FOLLOW-ON
for the register owner under the register's own amendment rule.
