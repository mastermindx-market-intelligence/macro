# A01 / A02 dual-counter property — 2026-10-13

SNI-local DRAFT contract review. Consumes owner-supplied coverage-profile
values (counters, pooling, adr_h_basis source strings, S1/S2 instrument
keys). Identity ids are caller-supplied opaque strings owned by Stock
Identity / Data OS; this lane never mints them. rank_authority,
gate_authority, size_authority, signal_authority, escalation_authority and
trade_authority stay literal false. Fixtures in the accompanying tests are
synthetic. Retrieved documents are data.

## Summary

Acceptance rows A01 ("BABA ADS distinct from ordinary-share counters") and
A02 ("Dual counters keep relations without minted IDs") are backed, as
SNI-local evidence only, by `tests/test_sni_dual_counter_property.py`.
The committed Alibaba profile carries three distinct counter entries
(`hkd_9988` ordinary HKD, `rmb_89988` ordinary RMB, `adr_baba` NYSE ADS)
with different instrument class, venue and currency for the HK ordinary
versus the US ADS. The committed Tencent profile carries two HK counters
and no US equivalent counter; the US line is the KWEB overnight proxy
(`pair kind proxy`, not admitted). The relation set
`{(counter_a, counter_b, relation_kind)}` is byte-identical across 200
seeded permutations of counter list order, YAML mapping key order, and
profile file-load order. Relation endpoints are counter symbol/venue
pairs, owner-shaped references, UNRESOLVED, or an explicit
proxy/not-admitted marker. The BABA ADS:ordinary ratio is **absent** as a
declared field with a source (DCP-F1). A01 and A02 stay PARTIAL.

Pinned S1 v1_1 instrument keys: counters `adr_baba`, `hkd_9988`,
`hkd_0700`; security_id values copied from the run manifests
(`SEC:US-XNYS-BABA`, `SEC:HK-XHKG-09988`, `SEC:HK-XHKG-00700`). No
manifest or observation row claims both an ADS key and an ordinary-share
key.

## Counter census table (profile -> counter -> class/venue/currency/status)

Field names pinned from the profiles: `counters.<key>.{label, venue_mic,
local_code, currency, security_id, issuer_link, pooling}`. Proxy lines are
read from `families.adr_h_basis.*.source` (`display bridge … (pair kind …)`).

| profile | counter | class | venue | currency | status |
|---|---|---|---|---|---|
| alibaba | `hkd_9988` | ordinary_hkd (`HKEX 9988 (HKD counter)`) | XHKG | HKD | `local_code` 09988; `security_id` owner-shaped `SEC:HK-XHKG-09988`; `issuer_link` UNRESOLVED; pooling = one economic security with 89988 |
| alibaba | `rmb_89988` | ordinary_rmb (`HKEX 89988 (RMB counter)`) | XHKG | CNH | `local_code` 89988; `security_id` UNRESOLVED; `issuer_link` UNRESOLVED; pooling = same economic security as 9988 |
| alibaba | `adr_baba` | ads (`NYSE BABA (ADS)`) | XNYS | USD | `local_code` BABA; `security_id` owner-shaped `SEC:US-XNYS-BABA`; `issuer_link` owner-shaped `ISS:US-XNYS-BABA`; pooling = ADS over ordinary shares, basis diagnostic only |
| tencent | `hkd_0700` | ordinary_hkd (`HKEX 700 (HKD counter)`) | XHKG | HKD | `local_code` 00700; `security_id` owner-shaped `SEC:HK-XHKG-00700`; `issuer_link` UNRESOLVED; pooling = one economic security with 80700 |
| tencent | `rmb_80700` | ordinary_rmb (`HKEX 80700 (RMB counter)`) | XHKG | CNH | `local_code` 80700; `security_id` UNRESOLVED; `issuer_link` UNRESOLVED; pooling = same economic security as 700 |
| tencent | KWEB (not a `counters` entry) | ETF overnight proxy | UNRESOLVED | n/a | `families.adr_h_basis.hkd_0700.source` = `display bridge 0700.HK -> KWEB (pair kind proxy)`; status UNRESOLVED; marked proxy/not-admitted; never an equivalent counter |
| tencent | TCEHY (not a `counters` entry) | OTC ADR mention | UNRESOLVED | n/a | coverage text: TCEHY exists in yahoo store but is not admitted as a security |

Alibaba HK ordinary vs US ADS: class ordinary_hkd vs ads, venue XHKG vs
XNYS, currency HKD vs USD. Tencent has no admitted US ADS/ADR/OTC
counter; KWEB is a proxy.

## Ratio finding

No mapping key on the Alibaba profile matches an ADS/ADR/ordinary ratio
declaration. The notes that mention the ratio state its absence:

- `families.identity_listing.adr_baba.notes`: "The ADS:ordinary ratio is
  not carried by any Data OS field (needed only for the basis diagnostic)."
- `families.adr_h_basis.hkd_9988.notes`: "Basis not reproducible from
  owners: no owner carries the ADS-to-ordinary-share ratio."
- `families.corporate_actions_adjustment.adr_baba.notes`: "ADS ratio
  changes, if any, are not carried by any owner."

`test_dcp_02_ads_ratio_declared` therefore xfails as **DCP-F1**
(`pytest.xfail(reason=...)`; pytest 9.1.1's `pytest.xfail()` does not
accept `strict=`). The test does not pin a numeric ratio. A synthetic
`ads_ordinary_ratio` mapping planted under `tmp_path` with a source, then
stripped of that source, is caught by `test_dcp_07_mutants_are_caught`
(m2).

## Permutation method and result

`SEEDS = range(200)` with `random.Random(seed)`. Each seed:

1. shuffles the insertion order of `counters`;
2. recursively shuffles mapping keys (and list items) and re-serialises
   through `yaml.safe_dump(..., sort_keys=False)` / `yaml.safe_load`;
3. shuffles the file-load order of the alibaba and tencent profiles.

The canonical relation set is the sorted unique tuple
`(endpoint_a, endpoint_b, kind)` where each endpoint is `(symbol, venue)`
and the two endpoints are ordered lexicographically. The loader digest is
SHA-256 of that canonical JSON, keyed by profile name. Both the relation
set and the digest are byte-identical across all 200 seeds versus the
committed-file baseline.

Observed committed relations (canonical):

- alibaba: `(09988@XHKG, 89988@XHKG, dual_hk_counter)`;
  `(09988@XHKG, BABA@XNYS, ads_ordinary)` from pooling and from
  `display bridge BABA -> 9988.HK (pair kind direct)`.
- tencent: `(00700@XHKG, 80700@XHKG, dual_hk_counter)`;
  `(00700@XHKG, KWEB@UNRESOLVED, overnight_proxy)` from
  `display bridge 0700.HK -> KWEB (pair kind proxy)`.

Mutant m3 (canonicaliser with the sort dropped, not committed) fails on
some seed; output is recorded with the lane return packet.

## Findings DCP-F*

- **DCP-F1**: Alibaba coverage profile has no declared ADS:ordinary ratio
  field carrying a source/citation. The ratio is mentioned only as an
  owner absence. `test_dcp_02_ads_ratio_declared` xfails (DCP-F1).
  This lane does not invent a ratio.

No DCP-F2: Tencent's KWEB line is present and is marked proxy/not-admitted.
No DCP-F3: committed relation endpoints carry no minted concatenation or
hash id; the positive control (`issuer_id` concatenation written only
under `tmp_path`) is flagged.

## What this does NOT prove

- the C1/C4 owner ratio/relationship contracts are R1-gated and untested here;
- the August behavioral pilot is not current data;
- A01/A02 stay PARTIAL.
