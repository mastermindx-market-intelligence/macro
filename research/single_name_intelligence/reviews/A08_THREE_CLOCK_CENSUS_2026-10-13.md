# A08 three-clock census — 2026-10-13

SNI-local DRAFT census of committed artifacts. It consumes owner-supplied
timestamps already stored on those artifacts. It does not mint, derive, or
guess canonical issuer or security identifiers (Stock Identity / Data OS
owns those). It does not re-implement Data OS identity, Company Event /
Earnings, FIF, Capital Structure, Stock Identity, Options, Research Vault,
or qledger/Evaluation. rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority and trade_authority stay literal
false; nothing here feeds a ranker, gate, sizer, signal, escalation, or
trade path.

Tests: `tests/test_sni_three_clock_census.py` (`test_tck_01` … `test_tck_07`).
Pin: worktree off `2c0422bfda93fce61445c308c01e46ee1449e6f4`.

## Summary

Acceptance row A08 ("Economic, owner-known, and publication times stay
distinct") is backed by a census of **73** INPUTS files and **23,185**
time-bearing key occurrences. Every observed time-bearing field is mapped
to exactly one of ECONOMIC / OWNER_KNOWN / PUBLICATION / SESSION_ANCHOR /
OTHER. No field name carries two clocks. The ordering law
(PUBLICATION >= ECONOMIC, OWNER_KNOWN >= PUBLICATION) has **zero committed
pairs to compare** on the same dict — S2 rows carry publication plus a
session-anchor, not an economic stamp; US-stress `then_known` rows carry
economic `valid_from` without a publication stamp. Copy-through of an
identical timestamp string across ECONOMIC and OWNER_KNOWN on one dict:
**0**. US-stress then-known: **0 verified / 28 total**, matching
`THEN_KNOWN_VERIFICATION.md`'s fail-closed rule.

A08 stays PARTIAL. The SNI three-clock VIEW is R1-gated and unbuilt. This
lane is the census that V1/C2 were waiting on from R1's absence: field
classification and co-location law, not a joinable three-clock table.

Census digest (field, clock, count), sha256
`875cec74faee84794b48eb52a6a637a34c5de3ef1cedd48a932011d8af633b83`.

## Clock definitions

Taken from the mission and from `event_response/s2_clocklaw.py` vocabulary.
SESSION_ANCHOR is the derived trading-session clock `s(c)` (first session
whose regular open is strictly after `t_avail`). Holiday/DST/session
placement is the CLK lane; this census does not re-test it.

| Clock | Meaning | Typical field names |
|---|---|---|
| ECONOMIC | When the fact was true in the world (fiscal period end, event date, listing/rename start) | `valid_from`, `valid_to`, `event_date`, `period_end`, `effective_at` |
| OWNER_KNOWN | When the owning system knew it | `as_of`, `ingested_at`, `known_at`, `identity_resolved_as_of`, `detected_at`, `observed_at_utc` |
| PUBLICATION | When it was published or filed | `opener_t_avail_utc`, `t_avail`, `filed_at`, `published_at`, `announced_at`, `disclosure_date` |
| SESSION_ANCHOR | Derived trading-session date `s(c)` | `anchor_session_date`, `coverage_date`, `s_date`, `s_hk`, `s_us`, `cluster_key` |
| OTHER | Matches the discovery regex but is not a clock | `coverage_1.0`, `coverage_1.96` (statistical coverage) |

Discovery: keys ending `_at` / `_date` / `_time` / `_as_of`, or named
`date` / `as_of` / `period_end` / `fiscal_*` / `anchor_*` / `coverage_*`,
plus extras that are timestamps without those suffixes
(`observed_at_utc`, `opener_t_avail_utc`, `s_hk`, `s_us`, `valid_from`,
`valid_to`, `cluster_key`). A later author who adds a new matching key
without classifying it fails `test_tck_01`.

## Census table

Walked **73** files (structured json/jsonl/yml plus evidence markdown,
`THEN_KNOWN_VERIFICATION.md`, and `s2_clocklaw.py`). Markdown and the
clock-law module contribute file counts and vocabulary; they do not add
structured key occurrences. Empty P05/P06 jsonl manifests are walked
(zero rows).

| Artifact family | files | field | clock | count |
|---|---:|---|---|---:|
| s1_residual_v1_1/manifests | 18 | `anchor_session_date` | SESSION_ANCHOR | 4336 |
| s1_residual_v1_1/manifests | 18 | `coverage_date` | SESSION_ANCHOR | 4336 |
| s1_residual_v1_1/observations | 18 | `anchor_session_date` | SESSION_ANCHOR | 7130 |
| s1_residual_v1_1/observations | 18 | `coverage_date` | SESSION_ANCHOR | 7130 |
| s1_residual_v1_1/results | 3 | `coverage_1.0` | OTHER | 60 |
| s1_residual_v1_1/results | 3 | `coverage_1.96` | OTHER | 60 |
| s1_residual_v1_1/root (`INPUT_MANIFEST*`, `VERSION_RECORD*`) | 2 | — | — | 0 |
| s2_event_response_v1_1/manifests | 9 | `opener_t_avail_utc` | PUBLICATION | 6 |
| s2_event_response_v1_1/manifests | 9 | `s_date` | SESSION_ANCHOR | 6 |
| s2_event_response_v1_1/manifests | 9 | `s_hk` | SESSION_ANCHOR | 6 |
| s2_event_response_v1_1/manifests | 9 | `s_us` | SESSION_ANCHOR | 6 |
| s2_event_response_v1_1/manifests | 9 | `cluster_key` | SESSION_ANCHOR | 6 |
| s2_event_response_v1_1/observations | 1 | `cluster_key` | SESSION_ANCHOR | 6 |
| s2_event_response_v1_1/results | 3 | `s_us` | SESSION_ANCHOR | 9 |
| s2_event_response_v1_1/results | 3 | `cluster_key` | SESSION_ANCHOR | 9 |
| s2_event_response_v1_1/results | 3 | `detected_at` | OWNER_KNOWN | 3 |
| s2_event_response_v1_1/root | 2 | — | — | 0 |
| evidence/Alibaba | 3 | `as_of` | OWNER_KNOWN | 1 |
| evidence/Tencent | 3 | `as_of` | OWNER_KNOWN | 1 |
| us_stress/profiles | 7 | `as_of` | OWNER_KNOWN | 7 |
| us_stress/profiles | 7 | `observed_at_utc` | OWNER_KNOWN | 7 |
| us_stress/profiles | 7 | `valid_from` | ECONOMIC | 28 |
| us_stress/profiles | 7 | `valid_to` | ECONOMIC | 28 |
| us_stress/THEN_KNOWN_VERIFICATION.md | 1 | — | — | 0 |
| coverage_profiles | 2 | `as_of` | OWNER_KNOWN | 2 |
| coverage_profiles | 2 | `observed_at_utc` | OWNER_KNOWN | 2 |
| event_response/s2_clocklaw.py | 1 | — | — | 0 |

Totals by field (sorted digest body):

| field | clock | count |
|---|---|---:|
| `anchor_session_date` | SESSION_ANCHOR | 11466 |
| `as_of` | OWNER_KNOWN | 11 |
| `cluster_key` | SESSION_ANCHOR | 21 |
| `coverage_1.0` | OTHER | 60 |
| `coverage_1.96` | OTHER | 60 |
| `coverage_date` | SESSION_ANCHOR | 11466 |
| `detected_at` | OWNER_KNOWN | 3 |
| `observed_at_utc` | OWNER_KNOWN | 9 |
| `opener_t_avail_utc` | PUBLICATION | 6 |
| `s_date` | SESSION_ANCHOR | 6 |
| `s_hk` | SESSION_ANCHOR | 6 |
| `s_us` | SESSION_ANCHOR | 15 |
| `valid_from` | ECONOMIC | 28 |
| `valid_to` | ECONOMIC | 28 |

14 distinct observed field names. `coverage_date` is null on **1476** S1
rows (horizon endpoint missing); the key is still classified
SESSION_ANCHOR. Alibaba/Tencent coverage-profile `observed_at_utc` is an
observation *window* (`2026-10-11T08:58Z..09:15Z`), not a single stamp;
ordering skips it.

## Ordering-law pairs and results

Comparable pairs, pinned, same dict (same fact row):

| Pair | Inequality | Where it could fire | Committed result |
|---|---|---|---|
| PUBLICATION vs ECONOMIC | PUBLICATION >= ECONOMIC | `opener_t_avail_utc` vs `event_date` / `valid_from` / `period_end` | **no co-located pair** (0 comparisons) |
| OWNER_KNOWN vs PUBLICATION | OWNER_KNOWN >= PUBLICATION | `detected_at` / `as_of` / `observed_at_utc` vs `opener_t_avail_utc` | **no co-located pair** (0 comparisons) |

S2 P04 manifest rows carry `opener_t_avail_utc` (PUBLICATION) next to
`s_date` / `s_hk` / `s_us` (SESSION_ANCHOR). That is the clock-law
placement `s(c)`, not PUBLICATION vs ECONOMIC. CLK owns the
open-strictly-after test; this census does not duplicate it.

US-stress `then_known` items carry `valid_from` (ECONOMIC) on the nested
dict; profile `as_of` (OWNER_KNOWN) sits on the parent. They are not the
pinned PUBLICATION/ECONOMIC pair. Then-known use-time is checked in
`test_tck_05`, not as an ordering-law xfail.

Mutant m2 (tmp_path copy of a P04 row, publication set to 2010-01-01,
`event_date` 2020-01-01) is the positive control that tck_03 fires.

## Findings TCK-F*

**TCK-F1.** No committed dict co-locates a PUBLICATION stamp with an
ECONOMIC stamp, or an OWNER_KNOWN stamp with a PUBLICATION stamp. The
ordering law is vacuously true on this tree. This is the A08 gap
("SNI three-clock view unbuilt"), not a row-level inversion.

**TCK-F2.** All 28 US/Mag-7 `then_known` entries have `verified: false`
and no `known_at` / `published_at` / `ingested_at`.
`THEN_KNOWN_VERIFICATION.md` states **0 verified / 28 total** and the
fail-closed rule: an unverified date must not be treated as a then-known
fact. `test_tck_05` cross-checks that rule. Unverified `valid_from`
values remain ECONOMIC claims in the census and are not promoted to
owner-known or publication time.

**TCK-F3.** `coverage_1.0` and `coverage_1.96` match the `coverage_*`
discovery rule (60 hits each on S1 P03 diagnostics) but are Wilson /
bootstrap *statistical* coverage, not a calendar clock. Classified OTHER.

**TCK-F4.** `coverage_date` is null on 1476 S1 rows. The field is still
SESSION_ANCHOR (horizon-end session when present). Nulls are not
ordering-law violations.

**TCK-F5.** Copy-through count (identical timestamp string on ECONOMIC
and OWNER_KNOWN of one dict) is **0**. No xfail.

No strict xfail is registered: there is no file:row inversion of the
ordering law on committed artifacts.

## What this does NOT prove

- the SNI three-clock VIEW is R1-gated and unbuilt;
- this is a census of committed artifacts only;
- current hindsight facts are not historical forecasts;
- A08 stays PARTIAL.

It does not prove that a future join of economic, owner-known, and
publication times on one evaluation row is look-ahead-safe. It does not
prove session placement, holiday, or DST behaviour (CLK /
`s2_clocklaw.py`). It does not verify Mag-7 `valid_from` dates against
an owner identity history (that history is absent; Data OS /
Stock Identity would supply it). It does not grade, forecast, or feed
any authority path. Cohort selection on the US stress profiles is
explicitly hindsight (`hindsight: true` as of 2026-10-12) and is not a
then-known claim.
