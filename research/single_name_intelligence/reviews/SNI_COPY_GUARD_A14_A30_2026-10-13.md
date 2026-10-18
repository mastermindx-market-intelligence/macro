# SNI copy guard A14 / A30 — 2026-10-13

SNI-local DRAFT contract review. This is a lexical copy check over
markdown under `research/single_name_intelligence/`. It consumes
owner-supplied document text. It does not mint issuer or security
identifiers; unknown identity stays UNRESOLVED / null (Stock Identity /
Data OS owns those opaque strings). It does not re-implement Data OS
identity, Company Event/Earnings, FIF, Capital Structure, Stock
Identity, Options, Research Vault, or qledger/Evaluation.

rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay false. Nothing here feeds
a ranker, gate, sizer, signal, escalation, or trade path. This review
is descriptive copy about a lexical scanner. It is not a forecast, not
a signal, and not a validation.

## Summary

Acceptance rows A14 and A30 now have a deterministic sentence-level
checker, `research/single_name_intelligence/acceptance/sni_copy_guard.py`,
driven by `tests/test_sni_copy_guard.py`.

A14 title (quoted from the matrix): "Holdings and options OI are not live flow or intent".
The scanner flags a sentence that contains both a holdings-family subject
term and a live-flow or intent term.

A30 title (quoted from the matrix): "Failed model stays NO-GO; UI does not imply forecast success".
The scanner flags a sentence that contains both a failed-state term and
a forecast-success term.

Quoted spans, backtick spans, and ban-stating negators (listed below)
suppress a match. An exact-match allowlist is present and is empty at
this pin. Sealed S1 residual report dump lines that still collocate a
failed-state token with a success token are pinned as `KNOWN_FINDINGS`
in the test module so a new collocation still fails the tests.

## Rules and vocabularies

Verbatim lists. One term per fence so the lists themselves do not
collocate a subject with an intent term, or a failed-state token with a
success token.

A14 subject terms:

```
holdings
southbound
northbound
stock connect
short interest
short-interest
CCASS
open interest
options OI
OI
13F
shareholding
```

A14 intent terms:

```
smart money
accumulating
accumulation
net buying
net selling
inflow
inflows
outflow
outflows
betting on
bets on
positioning for
positioned for
signals intent
conviction
whale
whales
loading up
dumping
```

A30 failed-state terms:

```
NO-GO
failed
retired
RETIRED-CONTAMINATED
contaminated
NON-CONFIRMATORY
BLOCKED-AS-EVIDENCE
NOT SUPPORTED
DESCRIPTIVE_ONLY
```

A30 success terms:

```
predicts
predictive
predicted correctly
outperform
outperforms
outperformed
beats
beat the
proven
edge
alpha
winning
works
profitable
forecast skill
```

Every vocabulary match uses word boundaries, case-insensitive.
Multi-word phrases match with intervening whitespace. The bare token
listed as `works` does not match inside `workspace`. The intent phrase
listed as `positioning for` does not match the family label
`positioning` on its own.

## Masking and negation

Applied before matching, per sentence.

1. Double quotes `"..."`, curly quotes `“...”`, and backtick spans are
   QUOTED. The span is replaced with spaces. A review that quotes banned
   copy in order to reject it does not fire. Unclosed openers are left
   as-is (the rest of the sentence stays visible).
2. Fenced code blocks (lines opening with ``` or ~~~) are skipped
   entirely, including the fence lines. Inline code is not skipped: a
   table cell that contains `engine/options_*.py` remains a sentence so
   an allowlist on that cell can stay live.
3. Ban-stating negators, matched on word boundaries, inside the same
   sentence, before the intent term (A14) or before the success term
   (A30):

```
not
never
no
cannot
must not
does not
do not
is not
are not
without
forbid
forbidden
banned
ban
```

The token `no` does not match the `NO-` prefix of `NO-GO`. The token
`not` does not match the `NOT` of `NOT SUPPORTED`. Those two compound
failed-state labels would otherwise hide every A30 sentence that uses
them. Positive controls show that a plain claim still fires:
"The NO-GO model still predicts returns." is a finding.

Known blind spots of this simple negation rule:

- A ban-stating negator anywhere earlier in a long sentence hides a
  later plain claim in that same sentence.
- Paraphrase outside the vocabulary is invisible. A sentence can state
  live flow or forecast success in other words and the scanner will
  stay silent.
- Single quotes are not a quoting mask. Python-dict dump lines that use
  single quotes stay visible.
- Periods inside numbers (`0.025`) do not split a sentence. A long
  dump line is one sentence.
- Numbered-list markers of the form `7. rest` split on the period, so
  the finding excerpt starts at `rest`.

## Scan result

Counted by glob of `*.md` under `research/single_name_intelligence/`
after this review file is added.

| quantity | value |
|---|---|
| markdown files scanned | 44 (43 at BASE plus this review) |
| raw A14 findings | 0 |
| raw A30 findings | 21 |
| allowlisted findings | 0 |
| KNOWN_FINDINGS (un-allowlisted, pinned) | 21, all A30 |

The pre-scan candidate at
`SNI_U0_COMPANY_INTELLIGENCE_REUSE_MAP.md` line 81, table cell
"Options / positioning", is not a finding. The intent vocabulary
requires `positioning for`. The family label without `for` is out of
scope.

## Allowlist table

No entries. `ALLOWLIST` is an empty tuple. Every future entry must name
an existing file, carry a non-empty justification sentence, and still
match exactly one current finding (path, line, rule, and substring in
the excerpt). A stale entry fails `test_cg_04`.

| path:line | rule | excerpt | justification |
|---|---|---|---|
| — | — | — | none at this pin |

## Bounds

- The charting-app repository (the actual product UI) is not covered.
- Rendered `site/` pages are not covered.
- Non-markdown files (JSON, Python string literals, YAML drafts) are
  not covered.
- The guard is lexical, not semantic. It does not read meaning, only
  word-boundary collocation inside a sentence.
- A14/A30 product-surface copy still needs a guard in the product repo,
  as an owner follow-on.
- `scan_paths` refuses a path outside `research/single_name_intelligence/`
  and refuses a non-markdown path. The helper reads only the files it
  is handed.

## Gaps

A14 on this tree is clean at the vocabulary: zero raw findings.

A30 fires on 21 sealed S1 residual REPORT dump lines. This lane does
not edit those reports. They are not allowlisted. `tests/test_sni_copy_guard.py`
pins them as `KNOWN_FINDINGS` so a new collocation still fails and a
repair of a listed line forces the tuple to shrink.

The dump lines are the S0 incremental-explanation test dict printed as
one numbered item. After the `7.` list split, the remainder is a single
sentence. That sentence carries the hyphenated non-confirmatory label
(a failed-state term). The same sentence also carries the Type-I field
name from the success list and the S0 criterion verb from the success
list. The 160-character excerpt is the shared prefix of those dump
lines and does not itself contain the matched tokens; the tokens sit
later on the line.

Pinned rows (path:line, all rule A30):

| path:line |
|---|
| research/single_name_intelligence/runs/s1_residual/REPORT.md:962 |
| research/single_name_intelligence/runs/s1_residual/REPORT.md:975 |
| research/single_name_intelligence/runs/s1_residual/REPORT.md:988 |
| research/single_name_intelligence/runs/s1_residual/REPORT.md:1001 |
| research/single_name_intelligence/runs/s1_residual/REPORT.md:1066 |
| research/single_name_intelligence/runs/s1_residual/REPORT.md:1079 |
| research/single_name_intelligence/runs/s1_residual/REPORT.md:1144 |
| research/single_name_intelligence/runs/s1_residual/REPORT.md:1196 |
| research/single_name_intelligence/runs/s1_residual/REPORT.md:1209 |
| research/single_name_intelligence/runs/s1_residual/REPORT.md:1248 |
| research/single_name_intelligence/runs/s1_residual/REPORT.md:1261 |
| research/single_name_intelligence/runs/s1_residual/REPORT.md:1300 |
| research/single_name_intelligence/runs/s1_residual/REPORT.md:1352 |
| research/single_name_intelligence/runs/s1_residual/REPORT.md:1365 |
| research/single_name_intelligence/runs/s1_residual/REPORT.md:1404 |
| research/single_name_intelligence/runs/s1_residual/REPORT.md:1417 |
| research/single_name_intelligence/runs/s1_residual/REPORT.md:1456 |
| research/single_name_intelligence/runs/s1_residual/REPORT.md:1469 |
| research/single_name_intelligence/runs/s1_residual_v1_1/REPORT.md:1186 |
| research/single_name_intelligence/runs/s1_residual_v1_1/REPORT.md:1214 |
| research/single_name_intelligence/runs/s1_residual_v1_1/REPORT.md:1631 |

STATUS of this lane for A14/A30 product copy in SNI markdown: PARTIAL.
A14 has a live regression test and a clean tree. A30 has a live
regression test and 21 pinned dump-line collocations on sealed reports.

The product UI and the rendered site remain unguarded (owner follow-on).
JSON protocol files and Python string literals remain unguarded.
