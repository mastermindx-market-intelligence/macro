# Q06 comparable-revenue Gate-S repair — 2026-09-29

**Operation:** `prophet-economic-evidence-research-20260926-sol-001`  
**Carrier:** existing Macro PR #8069 / `claude/prophet-economic-evidence-research-20260926-sol-001`  
**Reviewed head:** `a3bee6f04a26caac30af4d49452690cd2d8a5dea`  
**Disposition:** **Gate S repaired, pending parent acceptance. Gate E remains NOT_REGISTERED / UNCOMPUTED.**

This is the bounded repair requested after the completed independent GLM-5.3 source-method review. It changes no Earnings adapter, ranker, B4 gate, model plan, portfolio, paper design, protected outcome, source rights or collector.

## 1. M1 — fetched envelope identity is not an issuer-body revision

The old v0.1 record called ten distinct `source_sha256` values "source-body revisions." That wording is withdrawn.

The ten hashes in the existing chain receipt are now classified only as **distinct supplied/fetched envelope identities** unless exact bytes have been normalized and compared. The selected economic value/text hashes stayed stable, but that fact does not prove that every envelope change was an issuer-authored correction.

A deterministic, deliberately narrow normalization rule is now frozen for the exact AAPL FY2026 Q3 Exhibit 99.1 source:

```text
rule id: sec_suffix_delivery_script_v1
scope: this exact Q06 AAPL Exhibit 99.1 source construction only

remove at most one final:
<script type="text/javascript"  src="/_[A-Za-z0-9/_-]+"></script>
when it is immediately before </body>.

Always retain:
- raw fetched-envelope SHA-256;
- removed-wrapper SHA-256 and bytes;
- normalized-body SHA-256;
- rule id.

If the pattern does not match exactly once, do not normalize.
If normalized bytes change, classify the body as changed and require source-method review.
Never infer an issuer revision from an envelope hash alone.
```

A fresh bounded read on 2026-09-29 independently reproduced this behavior:

| Item | Exact result |
|---|---|
| Frozen fixture | 173,484 bytes / `070abd6a9cdb7070e546d24ffcbc41c65450d939c6f88f189cb18ec711cf5fdb` |
| Current fetched envelope | 173,602 bytes / `be6971e00004345bacedaccd598f89e76e7f6480707ecab88c64a5c4ae31d257` |
| One terminal wrapper | 118 bytes / `21b6e01b8d5e0b138e3f0e46762ca1d0407b7b428237a3fa4a1972ee8a9ed1d3` |
| Normalized result | exact frozen 173,484 bytes / `070abd6a…` |
| Current value position | byte 19,519 |
| Prior value position | byte 20,003 |

Two consecutive live reads returned the same raw/current witness. This is evidence for the exact normalization rule above, not a declaration that every historical envelope can be normalized without its raw bytes.

The independent review's September 27 witness remains separately preserved: 173,604-byte live envelope `6595b242…`, reported 120-byte delivery wrapper, normalized to the same frozen body. Because those wrapper bytes are not stored here, it remains a review witness rather than the reproducible primary normalization fixture.

The nine non-baseline historical hashes in `q06_aapl_revision_chain_receipt.v1.json` are therefore **UNEXPLAINED_SUPPLIED_ENVELOPE_IDENTITY** until their raw bytes are available for the versioned rule. This is fail-closed and intentionally less ambitious than the old wording.

## 2. M2 — economic value and field provenance are separately versioned

The v0.2 contract now carries two independent identities.

**Economic identity**

`econ:50d783276670de14acd15a92317b93649d877c01f7d48961d1c56e5e7c87a656`

It binds issuer, fiscal period, metric, current/prior periods, values, units, currency, accounting basis, formula and computed 16.356501765281383% result.

**Field-provenance identity**

`fpv:36091b7aff3681e59ab527eb3ebeac61a20324195a9f43f4478c4ccbcff1566a`

It separately binds:

- exact SEC document identity / CIK / accession / form / Exhibit 99.1;
- frozen-envelope and normalized-body hashes;
- normalization rule;
- exact statement title **“CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS (Unaudited)”**;
- the **Three Months Ended** column role;
- both UTF-8 byte spans and text hashes;
- explicit GAAP mapping rationale;
- source-available clock;
- admissibility decision; and
- the pinned source-rights record path, blob and allowed-with-limits state.

A provenance change therefore cannot silently remain "the same field" merely because 109,417 and 94,036 stay unchanged. Conversely, a wrapper or span-location change cannot be mislabeled an economic revenue revision when the economic identity is unchanged.

## 3. M3 — source construction and model experiment are now different gates

The phrase **“first preregisterable construction”** in v0.1 is superseded.

The repaired record is a **source-field contract candidate** only.

**Gate S — source construction**

Current state: `REPAIRED_PENDING_PARENT_ACCEPTANCE`.

This gate asks whether the exact field can be used as prospective factual evidence. It requires source identity, rights, clocks, fiscal comparability, spans, normalization and correction/provenance semantics. It does **not** need a matured trading result.

**Gate E — empirical claim**

Current state: `NOT_REGISTERED_PREPARATORY_ONLY`.

Before any protected outcome access or trial start, the Evaluation owner still must freeze at least:

- directional estimand and exact target;
- denominator states, including no-entry, unpriced, delisted, FPI and duplicate issuer/date;
- comparator arms;
- origin and first lawful fill/mark;
- endpoint arithmetic;
- chronological train/calibration/test partitions and label-support exclusion;
- market and sector benchmarks;
- costs and execution assumptions;
- multiplicity owner and trial budget;
- numeric worthwhile-gain and harm criteria; and
- fixed look / maturity rule.

The broad H42/H21/H63 section in v0.1 remains useful **research questions**, not a registered experiment.

No outcome is read or computed by this repair.

## 4. Minor review findings closed

**m1 — clock:** `2026-07-30T16:30:00Z` is now explicitly classified as malformed timezone/truncation fixture metadata relative to the verified SEC acceptance clock. It is not a competing decision-time clock. Source authority remains `2026-07-30T20:30:28Z`.

**m2 — accounting label:** the exact source statement title and period heading are bound in the field-provenance identity; GAAP is a source-method mapping from that reported financial statement, not inferred merely from a lowercase manifest token.

**m3 — reproducibility:** the committed verifier
`verify_q06_sec_comparable_revenue_source_contract.py`
checks the frozen fixture, rights blob, economic/provenance ids, spans/text hashes, exact source arithmetic, normalized-wrapper witness, envelope classification, all-false authority and separate Gate-S/Gate-E states. `tests/test_q06_sec_comparable_revenue_source_contract.py` makes that check CI-addressable.

## 5. Reconciled downstream reality

An important orphan/staleness correction is preserved here:

- the Earnings D5 adapter shell is **already implemented in current Macro source** at `engine/prophet_lab/intelligence_vector.py::build_earnings_intelligence_vector`;
- the existing read-only Prophet Lab route calls it;
- it already projects current revenue and guidance with all financial authority false;
- it does **not** currently materialize this same-table comparable prior as the accepted Q06 field.

Therefore the post-Gate-S engineering job is **not “build D5 from scratch.”** It is:

> extend the existing owner-native Earnings event/workspace → existing D5 family path with this exact accepted comparable-revenue field and its field-provenance identity, while retaining correction-safe PIT reads and all-false rank/entry authority.

The 2026-09-23 readiness census also found current coverage is narrow and many episodes truthfully return NOT_COVERED. Do not widen coverage or substitute the separate EquityDesk earnings plane merely to make the feature look common.

## 6. What this repair does not authorize

All remain false / held:

- rank or Fusion vote;
- candidate promotion;
- B4/entry permission;
- model sizing;
- portfolio action;
- plan rewrite;
- trial registration/start;
- protected return access;
- Packet4/D5 production edit from this record alone;
- collector or source-rights expansion;
- replacement U.S. price feed purchase.

Gate S parent acceptance is the next decision. After that acceptance, the existing Earnings/D5 owner may implement the factual field. Gate E remains separately owned by Evaluation and must be complete before outcome access.

## Exact acceptance evidence

The machine-readable controlling record is:
`q06_sec_comparable_revenue_source_contract.v0_2.json`.

The deterministic verifier is:
`verify_q06_sec_comparable_revenue_source_contract.py`.

The original v0.1 and independent review remain immutable historical evidence; this file supersedes only their incorrect or incomplete source-method claims.
