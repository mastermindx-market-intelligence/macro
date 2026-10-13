# Listing transitions behind the eleven lost reference rows

Workstream: `WS:LIVE-ENTRY-RADAR` — RS Pullback Launch source admission.

**Status: research evidence only; no transition has been applied.** Phase 1 remains `NOT_ADMITTED`, H1/H2/H3 remain `NOT_TESTED`, and every research/trading authority flag remains false. This packet explains the eleven missing listing matches that blocked the original prospective reference attempt. It neither revises that attempt nor turns a public filing into an admitted historical identity observation.

## Outcome and next bounded implementation

The eleven rows describe several different events. Two are same-venue name/ticker changes; three involve exchange transfers; four involve the conversion of an old common security in a completed transaction; one is an exchange suspension with contemplated OTC trading; one is withdrawal of an ADS listing while the ADR program continues. They cannot all be repaired by marking securities extinct or adding ticker aliases.

The smallest implementation candidate is **DOMO → HUCK and YYGH → YFOR**, after an explicit security-class, listing and observation-time contract is accepted in the existing identity owner. This is a proposed sequence, not implemented behavior. The existing rename table alone does not provide a complete or point-in-time-safe repair. Exchange transfers, security exits, suspension and continuing ADRs remain separate cases. The three original ETF reference refusals also remain separate.

The parent commission and original negative source verdict remain authoritative:

- [Implementation handoff](../../../agentos/handoffs/RS_PULLBACK_LAUNCH_SOL_IMPLEMENTATION_HANDOFF_2026-10-06.md).
- [Phase-1 admission](PHASE1_ADMISSION_2026-10-07.json), SHA-256 `a4e00a5c191917dc8c64fb74ca3348827ab9bd47d9ad8a03a1130a50fde36e9f`.
- [Native reference delivery, Macro #8607](https://github.com/mastermindx-market-intelligence/macro/pull/8607): accepted candidate `6d14f398564dce1d0f68daf956315cf7e9d19520`, actual squash `7a1f9ad0a28973cdc9b261e80bfdf61f4eae9575`.

## Observation boundary and retained inputs

Two bounded primary-source research passes were conducted on **2026-10-07**, followed by root verification of decisive documents. The first pass retrieved ATAI, DOMO, KHC, ET and YYGH sources during 10:45:08–10:50:36 UTC. The second pass retrieved the other six cases during 10:45:41–10:54:20 UTC. Root subsequently verified the closing/transition evidence for every case; supplemental DOMO and Cosan inspection occurred later in the same session.

Those intervals describe research-tool retrieval. They are **not** exact raw HTTP receipt times, provider publication times, sealed input artifacts or evidence that an earlier Radar decision had access to the documents. A document's filing, event or displayed page date must not become the identity owner's `known_at`. A future intake must preserve its actual acquisition and owner-read clocks separately.

The owner census was pinned to `macro@6d14f398564dce1d0f68daf956315cf7e9d19520`. It found the eleven old rows still present in the master, with null `security_state` and earlier resolved issuer evidence. It found no matching accepted rename, supersession, exit-ledger, migration or graph-break repair for these cases. Relevant immutable source:

- [Master builder](https://github.com/mastermindx-market-intelligence/macro/blob/6d14f398564dce1d0f68daf956315cf7e9d19520/scripts/build_security_master.py), blob `4a042933f37f32d112bd4d77a704f233bbd7d4a9`.
- [Identity reader](https://github.com/mastermindx-market-intelligence/macro/blob/6d14f398564dce1d0f68daf956315cf7e9d19520/lib/dataos/identity.py), blob `ea8485596e57fd1e686bfdb9d75708a3a3845fda`.
- [Existing exit-ledger reader](https://github.com/mastermindx-market-intelligence/macro/blob/6d14f398564dce1d0f68daf956315cf7e9d19520/lib/delisted_symbols.py), blob `8d5f1dd5d19c642deab84f0c823591378eb1d3f6`.
- [Existing exit ledger](https://github.com/mastermindx-market-intelligence/macro/blob/6d14f398564dce1d0f68daf956315cf7e9d19520/config/delisted_symbols.yml), blob `3a68f4476be8374cdcbcff8b1315f67084f4f8f6`.

Retained directory and CIK input identities are:

| Input | SHA-256 |
|---|---|
| Directory, 2026-10-07 | `7c4e48fb0b9de67487c0cc87c2b3362ce7ce438960050907a35503426e0f9c13` |
| Directory, 2026-10-06 | `28310239fc262b2f7b8dc293bc2b524197e96d949053054eaae1bcda8101cd54` |
| Directory, 2026-10-05 | `6dcc85d3f84abf9476d9db4ee0083d2e528e86bf4cb14d434e5e39a61558a9a8` |
| CIK input, 2026-10-05 | `5b817069fbee57a6616095e58b3b2ba759f55eb3f1cbf866fc62e0f0f55230b9` |

The reference receipt's `snapshot_date=2026-10-05` describes the CIK input; it does not date the newer directory input. Neither retained input is itself an eligible `listing_sec_identity_binding` document.

The original four-probe evidence and its decisions stay immutable. Its owner read completed at **`1791354276802797000` ns**, and its canonical prospective-reference block hashes to `0e07e498d7a6983c8752a53d719281b07c30d334895c0b418edbbcc160145856`. MU is bound; SPY, QQQ and SMH retain their original refusals. The installed proof in #8607 reads those retained bytes with a new actual read clock; it does not change their historical availability.

## Primary-source findings by security

### Same-venue ticker changes

| Old row | What the primary evidence establishes | Dates and unresolved limits |
|---|---|---|
| **DOMO → HUCK** | The company changed its name to Huckleberry.ai. Its **Class B common stock** continues on Nasdaq; the issuer says its CUSIP and security-holder rights are unchanged. The asset sale to Progress does not make the old common stock the same security as Progress stock. [Issuer 8-K, Items 2.01/5.03](https://www.sec.gov/Archives/edgar/data/1505952/000110465926109635/tm2625825d1_8k.htm); [Nasdaq corporate-action notice](https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-672). | Legal name/asset-sale events: **September 22**. Nasdaq ticker event: **September 24**. The exchange notice identifies unchanged CUSIP `257554105`. These are distinct from the October 7 research observation and any future owner intake. |
| **YYGH → YFOR** | The issuer reports that its **Class A ordinary shares** began trading on Nasdaq as YFOR, with unchanged ISIN. This supports continuity of the named class, subject to the existing identity owner's evidence contract. [Issuer 6-K](https://www.sec.gov/Archives/edgar/data/1985337/000118518526003874/yfor6k090726.htm); [BVI amendment exhibit](https://www.sec.gov/Archives/edgar/data/1985337/000118518526003874/yforex99-1.htm). | New ticker trading: **September 2**. The issuer reports filing the corporate amendment on **August 31**; the 6-K was filed **September 8**. Exact certification/publication clocks remain unestablished. |

The retained directories contain HUCK Class B and YFOR Class A on Nasdaq on October 5, 6 and 7. The October 5 CIK input includes DOMO and HUCK under CIK 1505952, and YFOR under CIK 1985337. No HUCK/YFOR master inception or alias row exists at the frozen owner pin. Thus, these cases are not adequately described as vanished issuer evidence. The remaining defect includes current listing lookup and observation-time semantics.

### Exchange transfers

| Old row | What the primary evidence establishes | Dates and unresolved limits |
|---|---|---|
| **KHC** | Common stock transferred from Nasdaq to NYSE under the same ticker. A contemporaneous exchange-operations notice confirms the completed change used for openings. The issuer's filing distinguishes common stock from separately listed notes. [MIAX operational notice](https://www.miaxglobal.com/alert/2026/09/14/miax-options-exchanges-change-market-underlying-security-used-openings); [issuer 8-K](https://www.sec.gov/Archives/edgar/data/1637459/000163745926000057/khc-20260824.htm). | Market transfer: **September 14**. [Form 25](https://www.sec.gov/Archives/edgar/data/1637459/000163745926000062/khc-form25gdcdraftx6001812.htm) is dated September 8; it is not the trading-transfer date. Preserve canonical security continuity across changing listing keys. |
| **ET** | Energy Transfer's **common partnership units** moved from NYSE to TXSE with ticker ET. TXSE reports completion and identifies its MIC as `TXSE`, SIP code `F`. Preferred-unit treatment must remain class-specific. [TXSE completion notice](https://www.txse.com/press/texas-stock-exchange-celebrates-move-of-energy-transfer-partnership-s-primary-listings); [TXSE codes](https://www.txse.com/regulations/id-codes); [issuer 8-K](https://www.sec.gov/Archives/edgar/data/1276187/000127618726000044/et-20260903.htm). | Completed transfer: **October 5**. Retained directory venue codes are N/F/F on October 5/6/7. Preserve this lag/contradiction; do not rewrite the October 5 input. The builder lacks the required F/TXSE mapping at the frozen pin. |
| **PSKY → SKYD** | The closing 8-K reports the company's **Class B common stock** changing symbol from PSKY to SKYD and listing from Nasdaq to NYSE. The named class continues through the transfer; the acquisition context does not justify treating WBD as the same canonical security. [Closing 8-K, Explanatory Note, PDF page 2](https://ir.paramount.com/static-files/6af929e3-2b7a-43d0-a097-faf343b093df); [Form 8-A](https://ir.paramount.com/node/73446/html). | Closing and reported transfer: **October 6**. SKYD appears in the retained October 7 directory with NYSE code N. The October 5 CIK input still contains PSKY under CIK 2041610, not SKYD. |

ET also exposes disagreement between two public directory documents: a [Nasdaq data notice](https://www.nasdaqtrader.com/TraderNews.aspx?id=DTN2026-10) adds code F but contains a year inconsistency, while the [symbol-directory definition page](https://www.nasdaqtrader.com/Trader.aspx?id=SymbolDirDefs) omits F in its displayed table. TXSE's own code table supplies affirmative evidence. The inconsistent documents remain part of the provenance assessment rather than being silently harmonized.

### Completed conversions of old common securities

| Old row | What the primary evidence establishes | Dates and unresolved limits |
|---|---|---|
| **ATAI** | The Lilly transaction closed and the old common shares converted under the merger terms. The acquired entity's continued existence as a subsidiary does not preserve the old public common security or establish an ATAI→LLY same-security alias. [Closing 8-K](https://www.sec.gov/Archives/edgar/data/2081043/000114036126036283/ef20081247_8k.htm); [Nasdaq notice](https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-633). | Closing: **September 11**. Nasdaq records last trading September 10 and suspension September 14. The notice's displayed original date and later updated transaction text differ; the update's publication clock is unknown. Final Form 25 effectiveness was not established. |
| **QRVO** | The two-step transaction completed; the old common stock converted into cash and SWKS-share consideration. That is a conversion event, not a QRVO→SWKS ticker rename. [Closing 8-K, including Item 3.01](https://ir.qorvo.com/static-files/97184275-c23b-40b6-8c00-fab7ad1c2258); [Form 25](https://www.sec.gov/Archives/edgar/data/1604778/000135445726000942/xslF25X02/primary_doc.xml). | Closing: **October 5**; the filing reports a halt before that day's market open. QRVO's continued appearance in October 5/6 retained directories conflicts with the transaction evidence and must be preserved. |
| **DBRG** | The completed transaction converted the old **Class A common stock** into cash consideration. Preferred securities and the surviving subsidiary are distinct from that old common security. [Closing 8-K, Items 2.01/3.01/3.03](https://ir.digitalbridge.com/node/15466/html); [SoftBank completion release](https://group.softbank/en/news/press/20260930). | Closing: **September 30**; the issuer describes removal before the open and filing of Form 25. A future ledger entry still needs the exact supported last session and the owner's observation law. |
| **WBS** | The holding-company transactions completed and old common holders received cash and Santander ADS consideration. The old WBS security is not simply renamed SAN. [Closing 8-K](https://www.sec.gov/Archives/edgar/data/801337/000119312526357758/d919931d8k.htm); [Santander completion release](https://www.santander.com/en/press-room/press-releases/2026/08/santander-expands-us-presence-with-completion-of-webster-acquisition). | Closing: **August 20**, with filing-reported transaction times of 00:01, 00:02 and 00:04 **Eastern**. Withdrawal was requested before the open. Actual Form 25 effectiveness and an independently qualified last-session field remain unresolved. |

These four cases are candidates for the existing security-exit owner once its required fields and time law are satisfied. A closing date must not automatically become `last_session`, and consideration in another issuer's security must not become a same-security alias.

### Suspension and continuing ADR program

| Old row | What the primary evidence establishes | Dates and unresolved limits |
|---|---|---|
| **GWH** | NYSE immediately suspended trading and commenced delisting proceedings. The common shares continue to exist. The issuer contemplated OTC trading as GWHT, subject to the stated conditions. This is insufficient evidence of security extinction. [Issuer 8-K, Item 3.01](https://www.sec.gov/Archives/edgar/data/1819438/000181943826000088/wk-20261002.htm); [issuer release distributed by Business Wire](https://www.businesswire.com/news/home/20261005134678/en/). | Suspension: **October 2**. October 5 OTC commencement was qualified/anticipated in the recovered evidence. Final delisting, appeal disposition and exact first OTC trade were not proved. Direct retrieval of the SEC page was inconsistent; root recovered the relevant SEC text through official-domain search. |
| **CSAN → CSANY (continuing ADS program)** | Cosan announced voluntary withdrawal of the NYSE ADS listing while maintaining a Level I ADR program. Its current issuer table identifies OTC symbol CSANY, ADS ISIN `US22113B1035`, CUSIP `22113B103` and ratio 4:1. This does not extinguish the ADS or identify it with the underlying B3 ordinary share. [Issuer 6-K](https://www.sec.gov/Archives/edgar/data/1430162/000155485526001981/MainDocument.htm); [Form 25](https://www.sec.gov/Archives/edgar/data/1430162/000095010326013642/dp252967_25.htm); [current issuer securities page](https://www.cosan.com.br/relacoes-com-investidores/outras-informacoes-para-investidores/nossas-acoes/). | The September 8 filing planned the last NYSE day for **September 18**. Exact first OTC trading and its availability clock remain unproved. The undated current issuer page also retains stale NYSE/Level II prose, so its internal inconsistency and unknown publication time remain explicit. |

GWHT and CSANY are absent from the retained directory snapshots. That absence cannot establish that an OTC security did not exist or trade. The CIK input does contain CSANY under CIK 1430162 and GWH under CIK 1819438; neither fact alone supplies an admitted listing/class binding.

## Why the existing owners need a bounded extension

The following findings were verified by the frozen source census and isolated read-only probes (processes 99833, 9970, 9103 and 14969; all exited zero). They are implementation facts, not new authority rules.

1. **The rename table is incomplete as a current-symbol resolver.** `RenameEvent` stores old/new symbols, a date, vendor scope and evidence, but no actual observation clock or explicit MIC/class binding. `_inception_code` walks backward and `_current_symbol` walks forward; `resolve_universe` still looks up the fetch/key symbol rather than the curated current tip. Adding DOMO→HUCK alone therefore leaves DOMO unresolved. A repair must preserve the existing fetch/store namespace unless separately migrated.

2. **Exchange changes can accidentally mint a second security.** A KHC listing-key change from XNAS to XNYS must preserve the old canonical security identity. ET additionally needs the missing F/TXSE mapping. PSKY combines venue and symbol changes. `SECURITY_SUPERSESSIONS` is a duplicate-mint repair mechanism; it must not be reinterpreted as a generic acquisition, venue-transfer or suspension ledger.

3. **Suspension is not a supported master-state insertion.** At the frozen pin, the meaningful non-null master state is `SUPERSEDED_DUPLICATE_MINT`, and consumers exclude any non-null state. Adding `SUSPENDED` would silently remove a continuing security from consumers. GWH cannot be repaired through that shortcut.

4. **The exit ledger has real downstream effects and no enforced observation clock.** Its contract concerns a security whose public tape/security existence ended and requires company, last session, delisting date, reason and sources. Existing Yahoo collection and stock-library code consume it. Inserting GWH or continuing CSAN ADSs would assert the wrong event and can change collection/authority behavior. The four converted old-common cases still require exact supported fields before use.

5. **Existing namespace visibility is uneven.** Native polygon aliases have explicit known-at/seal gating. A bounded probe showed that a future `known_at` on a membership alias can nevertheless resolve at an earlier decision in the legacy namespace. `IssuerMaster` is current-only. A rename implementation therefore cannot inherit a historical point-in-time guarantee merely by attaching a clock field.

6. **The original Native attempt is immutable.** `_load_reference_input` admits one immutable prospective attempt and refuses changed revisions. Its intake guard also protects existing master, alias, issuer and migration rows. Applying transition repairs and creating a later reference attempt require separate, explicit operations through the existing owners. Editing the old REFUSED entries to BOUND would erase what was known at the original cutoff.

7. **Artifact publication must preserve history.** Lawful alias refinements, removed-row receipts, seal conflicts and the global lost-row check already have owner-specific behavior. The direct master builder writes files sequentially; the nightly wrapper supplies rollback. A new path cannot assume a direct invocation has atomic multi-file publication merely because its individual outputs are valid.

## Acceptance requirements for the proposed first wave

Before implementing the two same-MIC renames, define and review the extension against the existing builder and reader. It must preserve the following conditions:

- Identify the exact continued class and listing, the old and new symbols, effective market date, actual source acquisition, actual owner-read time and immutable evidence identity. Unknown clocks remain unknown; CIK is supporting issuer provenance rather than a substitute listing binding.
- Resolve the current listing tip while retaining inception-based canonical security IDs. Do not silently rename legacy Yahoo fetch keys or on-disk symbol stores.
- Apply observation-time visibility before consulting later event semantics. A cutoff before the new evidence was actually read must yield the original state/refusal; a later corrected document must not change that earlier answer.
- Preserve the original Native block, MU binding and SPY/QQQ/SMH refusals byte-for-byte. Keep exchange-transfer, security-exit, suspension and continuing-ADR cases refused unless their own semantics are implemented and independently proved.
- Retain every preexisting master/alias/issuer/migration record and historical resolution generation except for an explicitly lawful, receipted refinement under the existing owner. Unknown conflicts refuse rather than selecting a convenient identifier.
- Verify the real consumer, including reverse symbol lookup, class/venue mismatch, missing/naive clocks, historical cutoffs, later correction, exact-date boundaries and recovery. A current builder success alone cannot prove historical reader visibility.

A later Native acquisition attempt additionally needs a versioned extension of the **existing receipt owner**: immutable attempt identity, predecessor/input/dependency seals, actual monotone owner-read clocks, preserved provider clocks, idempotence of an identical attempt, refusal of same-attempt mutation, bounded capacity and atomic publication/history behavior. That extension is not implemented by this research packet. `temporal.py` publication/ingestion coalescing and an externally supplied Radar identity receipt are not substitutes for validating native revision history.

## Remaining program boundary

Stable listing identity is one source dependency. Raw one-minute capture, adjustment and split-factor applicability, complete RTH interval behavior, daily leader/pullback availability, faithful incumbent assessment and a complete pilot population still require their own admitted receipts. A source-retention proof does not establish any H1, H2 or H3 effect, and no outcome tuning is authorized by this packet.

A future implementation should start from the two explicitly bounded renames and reassess the next owner dependency after its accepted delivery. Do not repeat the broad transition research merely because source branches move; refresh only changed or unresolved evidence. Preserve the eleven-case taxonomy and all named unknowns when the next source census runs.
