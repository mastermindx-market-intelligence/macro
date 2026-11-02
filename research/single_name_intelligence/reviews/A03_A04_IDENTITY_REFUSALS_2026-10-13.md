# A03 / A04 identity refusals — 2026-10-13

SNI-local DRAFT contract review. Identity ids are caller-supplied opaque
strings owned by Stock Identity / Data OS; this lane never mints them.
rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay literal false. Fixtures in
the accompanying tests are synthetic. Refuse-probe values use the
placeholder `MINTED-FAKE-1`.

## Summary

Acceptance rows A03 ("Null HK issuer stays null; ID operations refuse")
and A04 ("Ticker aliases and venue mismatches cannot cross-bind") are
backed by `tests/test_sni_identity_refusals.py`. The tests walk committed
SNI JSON/YAML identity keys, pin the Tencent coverage-profile issuer
fields, drive `check_profile` key-spelling variants, load synthetic
alias profiles through `load_profiles`, assert coverage-profile
currency/venue pairs, and AST-scan SNI Python for identity-id minting
helpers. Four missing refusals are recorded as strict xfails IDR-F1..F4.
No identity resolver is implemented here.

| check | test | result |
|---|---|---|
| Committed JSON/YAML identity keys | `test_idr_01_committed_artifacts_hold_no_minted_id` | pass |
| Tencent issuer-level fields | `test_idr_02_tencent_issuer_stays_null` | pass |
| Key spelling / `issuer_link` variants | `test_idr_03_key_variants_refused` | pass |
| Unicode lookalike `іssuer_id` | `test_idr_03_unicode_lookalike_refused` | XFAIL IDR-F1 |
| Alias load pin | `test_idr_04_alias_cannot_cross_bind` | pass (actual behaviour pinned) |
| 0700 / 700 / ` 0700.HK` refusal | `test_idr_04_leading_zero_aliases_refused` | XFAIL IDR-F2 |
| TME + company Tencent | `test_idr_04_tme_tencent_refused` | XFAIL IDR-F3 |
| TCEHY + admitted-issuer claim | `test_idr_04_tcehy_admitted_issuer_refused` | XFAIL IDR-F4 |
| Currency / venue pairs | `test_idr_05_currency_venue_mismatch` | pass |
| AST no-minting + positive control | `test_idr_06_no_id_minting_helpers` | pass |
| Pure path (subprocess/socket raise) | `test_idr_07_pure` | pass |

Rows A03 and A04 stay PARTIAL: no C1/C4 owner test exists, and identity
resolution belongs to Data OS / Stock Identity.

## Existing coverage (INV, the coverage-profile test)

`tests/test_sni_program_invariants.py` (`test_inv_02_identity_ids_owner_supplied`)
walks `research/single_name_intelligence/**` and
`contracts/single_name_intelligence/**` for `*.json` / `*.yml` / `*.yaml`
/ `*.py`. Identity keys are matched with `key.casefold()` (no `strip()`).
Allowed values are `None`, `"UNRESOLVED"`, or a string present in
`data/reference/security_master.parquet`. When the parquet is absent the
identity check is skipped. INV does not scan
`config/single_name_intelligence/`.

`tests/test_single_name_coverage_profiles.py`
(`test_identity_ids_are_existing_owner_shapes_never_minted`) loads the
Alibaba and Tencent coverage profiles with PyYAML and requires each
`canonical_issuer_id` / counter `issuer_link` / counter `security_id` to
be `"UNRESOLVED"` or to match `ISS:[A-Z]{2}-[A-Z]{4}-[A-Z0-9.]+` /
`SEC:[A-Z]{2}-[A-Z]{4}-[A-Z0-9.]+`, and to fail the tickerish regex
(bare ticker, HK local code, CIK). `issuer_key` must not start with
`ISS:` or `SEC:`.

This lane does not copy INV's parquet-backed research/contracts/.py walk.
`test_idr_01` walks JSON/YAML under both `research/single_name_intelligence/`
and `config/single_name_intelligence/` with `key.strip().casefold()`,
independent of `data/`. Allowed values are JSON/YAML null, the string
`UNRESOLVED`, and owner-shaped `ISS:` / `SEC:` strings matching the
coverage-profile regexes (recorded Data OS values already present in
committed files). No other null-like sentinel appears.

## Artifacts inspected (count + roots)

| root | files | notes |
|---|---|---|
| `research/single_name_intelligence/` | 85 (`*.json` 78, `*.yml` 7) | INV already identity-scans this root; this walk adds `strip()` and a parquet-independent allowed set |
| `config/single_name_intelligence/` | 2 (`alibaba.yml`, `tencent.yml`) | INV misses this root |

Live counts are printed by `test_idr_01`: **87 files**, **257 identity
keys**. Every non-null identity value is an owner-shaped `ISS:` or `SEC:`
string. Tickerish values and `MINTED-FAKE-1` do not appear as identity-key
values.

`data/` is out of scope (absent in sparse/CI checkouts). Markdown, Python,
and `*.jsonl` are outside the JSON/YAML walk. Python minting is covered
separately by `test_idr_06` (31 `*.py` files under
`research/single_name_intelligence/`).

## Variant table

`check_profile` / `_walk_refuse` compares keys with `key.strip().casefold()`.
Identity keys with any non-`None` value raise `ValueError`. `issuer_link`
must be `None` or the literal `"UNRESOLVED"`. Nested at depth 1, depth 3
(`layer1.layer2.<key>`), and inside a list (`bucket: [{<key>: ...}]`).

| key | value | refused? | expected |
|---|---|---|---|
| ` issuer_id ` | `MINTED-FAKE-1` | yes | refuse (strip + casefold) |
| `Issuer_ID` | `MINTED-FAKE-1` | yes | refuse |
| `ISSUER_ID` | `MINTED-FAKE-1` | yes | refuse |
| `issuer_id\t` | `MINTED-FAKE-1` | yes | refuse |
| `canonical_Security_Id` | `MINTED-FAKE-1` | yes | refuse |
| `CIK` | `MINTED-FAKE-1` | yes | refuse |
| `Isin` | `MINTED-FAKE-1` | yes | refuse |
| ` figi` | `MINTED-FAKE-1` | yes | refuse |
| each identity variant above | `None` | no | pass |
| `issuer_link` | `HK-0700` | yes | refuse |
| `issuer_link` | `tencent` | yes | refuse |
| `issuer_link` | `0700.HK` | yes | refuse |
| `issuer_link` | `""` (empty string) | yes | refuse (`""` is not `None` and not `"UNRESOLVED"`) |
| `issuer_link` | `None` | no | pass |
| `issuer_link` | `UNRESOLVED` | no | pass (documented allowed token) |
| `іssuer_id` (Cyrillic `і`) | `MINTED-FAKE-1` | no | IDR-F1: not casefold-equal; unrefused |

## Alias table

`load_profiles` parses YAML in a temp directory and keys the result by
filename stem. `check_profile` is applied per file. There is no ticker
normalisation, alias table, or company-name cross-check.

| probe | actual | refused? | expected |
|---|---|---|---|
| tickers `0700`, `700`, ` 0700.HK` in three files | three stems load (`syn0700`, `syn700`, `syn0700hk`) | no | IDR-F2 |
| ticker `TME`, `display_name` Tencent Holdings Ltd, identity null | stem `tme` loads | no | IDR-F3 |
| ticker `TCEHY`, `identity_state: ADMITTED`, identity null | stem `tcehy` loads | no | IDR-F4 |

TME is Tencent Music, a different issuer (U0 reuse map). TCEHY is an
unresolved ADR (absent from security_master; U0). This lane does not add
those refusals.

## Tencent issuer fields (A03)

Quoted from `config/single_name_intelligence/coverage_profiles/tencent.yml`:

| field | value |
|---|---|
| `canonical_issuer_id` | `UNRESOLVED` |
| `issuer_key` | `tencent` (profile-local file key, never an identity id) |
| `counters.hkd_0700.issuer_link` | `UNRESOLVED` |
| `counters.rmb_80700.issuer_link` | `UNRESOLVED` |
| `counters.hkd_0700.security_id` | owner-shaped `SEC:` listing id recorded by Data OS; `issuer_link` stays `UNRESOLVED` |
| `counters.rmb_80700.security_id` | `UNRESOLVED` |

E2 pack: `issuer_of_security` returns `None` (NO_ISSUER_EVIDENCE). No
security in the Tencent profile binds `issuer_link` to an issuer id.
`test_idr_02` walks every issuer-level identity key (`canonical_issuer_id`,
`issuer_id`, `cik`, `lei`, `permid`, `perm_id`) and requires null /
`UNRESOLVED`.

## Currency / venue (A04 listing pairs)

Coverage-profile counters carry `currency` and `venue_mic`. Committed
pairs:

| counter | fields | pair |
|---|---|---|
| Alibaba `hkd_9988` | `currency`, `venue_mic` | `HKD` / `XHKG` (HKEX) |
| Alibaba `adr_baba` | `currency`, `venue_mic` | `USD` / `XNYS` (NYSE) |
| Tencent `hkd_0700` | `currency`, `venue_mic` | `HKD` / `XHKG` (HKEX) |

US/Mag-7 stress profiles carry `venue_mic: XNAS` and `currency: USD` only
(no BABA / 9988.HK pair). The pairing surface for BABA vs 9988.HK is the
coverage profile.

## Findings (IDR-F*)

| id | finding | suggested owner |
|---|---|---|
| IDR-F1 | Cyrillic `іssuer_id` with a non-null value passes `check_profile`, because `strip().casefold()` is not confusable-equal to `issuer_id`. | SNI us_stress draft (`_walk_refuse`); Data OS / Stock Identity own real identity keys. |
| IDR-F2 | `load_profiles` keys by filename stem. Tickers that differ by leading zeros, whitespace, or a `.HK` suffix load as distinct companies. | SNI us_stress draft loader (consumer of caller tickers); alias identity belongs to Data OS / Stock Identity. |
| IDR-F3 | A synthetic profile with ticker `TME` and company Tencent Holdings Ltd loads. TME is Tencent Music. | Data OS / Stock Identity (issuer axis). SNI must keep consuming UNRESOLVED / caller-supplied ids. |
| IDR-F4 | A synthetic profile with ticker `TCEHY` and `identity_state: ADMITTED` loads. TCEHY is an unresolved ADR. | Data OS / Stock Identity (OTC ADR admission). SNI must not treat TCEHY as an admitted issuer. |

No finding row mints or suggests a canonical issuer or security id.

## What this does NOT prove

No C1/C4 owner test exists, so rows A03 and A04 stay PARTIAL. Identity
resolution belongs to the Data OS / Stock Identity owners; this lane
builds none of it. The tests prove that committed SNI JSON/YAML identity
keys are null, `UNRESOLVED`, or owner-shaped recorded values; that
`check_profile` refuses the listed spelling variants and non-null
`issuer_link` tokens; that Tencent's issuer-level fields stay
`UNRESOLVED`; that coverage-profile currency/venue pairs are internally
consistent; and that SNI Python does not assign f-string or concatenation
values to identity-key names. They do not prove that a future owner
resolver would reject TME/Tencent or TCEHY, that Markdown prose cannot
name an id, or that a homoglyph other than Cyrillic `і` is refused.

## Gaps

- Alias and lookalike refusals are absent from `load_profiles` /
  `_walk_refuse` (IDR-F1..F4). This lane records them and does not add
  the refusals.
- INV's parquet membership check is skipped when `data/` is absent; this
  walk covers that hole for JSON/YAML identity keys only, via owner-shape
  regex plus null / `UNRESOLVED`.
- `*.jsonl`, Markdown, and `contracts/single_name_intelligence/` are
  outside `test_idr_01`. INV already scans contracts/.
- Empty-string `issuer_link` is refused by today's `_walk_refuse`. That
  is pinned; a future change that treated `""` as null would be a
  behaviour change.
- Mutation proofs m1/m2 are session evidence (reverted before commit).
  They are not additional committed tests.
