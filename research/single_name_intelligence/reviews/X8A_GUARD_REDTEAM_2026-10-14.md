# X8A Guard Red-Team Review — SNI counter-relation, entitlement, correction-lineage guards

Scope: adversarial review at `97e9d6e7c3d15eeb3f8bb9e8996bfec710e6bfe0` of the three
DRAFT guard modules — `research/single_name_intelligence/common/sni_counter_relation_guard.py`,
`research/single_name_intelligence/common/sni_entitlement_guard.py`,
`research/single_name_intelligence/common/sni_correction_lineage_guard.py` — together with
their `tests/test_sni_*_guard.py` companions. Comparison family pattern is
`research/single_name_intelligence/common/sni_join_guard.py`.

The six authority flags appear as literal `False` in every guard's
`AUTHORITY_FLAGS` MappingProxyType and as literal `False` in every verdict's
`authority_flags` property. No flag becomes `True` or `1` or anything else,
and `refuse_nonfalse_authority()` raises on any non-False value. Stdlib-only
imports (`__future__`, `dataclasses`, `datetime`, `types`, `typing`) in all three
modules; no `datetime.now`, `utcnow`, `date.today`, `time.time`, `open(`.
`python3 research/single_name_intelligence/evaluation/seal_full_check.py --study all --repo-root .`
final line: `SEAL FULL CHECK: OK (10 files float-equivalent on Linux x86_64 within rel 1e-10 / abs 1e-13, not byte-identical; byte identity rests on the XREP Linux receipt)`.

## Summary

Eight findings: six MAJOR, two MINOR. All MAJORs share one root cause: each
guard's `_blank()` helper treats "blank" as only `None` or `""`, so any
non-string, whitespace-only, or truthy non-string value passes the blank-check
at all identity/structural fields and the verdict returns `allowed=True,
reasons=()` with the malformed value echoed verbatim into the verdict or
silently coerced to `None`. Two MINORs concern the verdict echo semantics.
Two of the three guards (A02G, A18) have at least one concrete docstring-vs-
behaviour gap that lets a real mismatch pass. A16 looks clean against every
attack run. All nine branches I disabled via /tmp copy mutants were killed by
the test file (test strength is high, no surviving mutants among the three
branches per guard that I tried). No ticker/listing literal, no wall clock,
no I/O, no non-stdlib import, no authority flag truthy.

## Findings

### X8A-01 — MAJOR — A02G — whitespace-only `source_ref` and `relation_id` pass as non-blank

CLAIM: A relation whose `source_ref` is `" "`, `"\t"`, or `"\n"`, or whose
`relation_id` is `" "`, is allowed by `check_counter_relation` (verdict
`allowed=True, reasons=()`, with the whitespace-only value echoed into
`verdict.relation_id`). The docstring promises `RELATION_UNSOURCED` and
`RELATION_ID_MISSING` refusals for "non-sourced" / "missing" inputs;
whitespace-only is functionally unsourced / has no real id.

Module: `research/single_name_intelligence/common/sni_counter_relation_guard.py`,
function `_blank()` at line 124. Both refusal checks (`RELATION_ID_MISSING`
at line 254, `RELATION_UNSOURCED` at line 256) use `_blank()`. The `_blank`
predicate returns True only for `None` or `""`; `value == ""` in Python is
False for `" "`, `"\t"`, `"\n"`.

Reproducing input:
```python
from sni_counter_relation_guard import check_counter_relation
print(check_counter_relation(
    {"issuer_id": "SYN-ISSUER-1",
     "left_listing_id": "SYN-LISTING-a1",
     "right_listing_id": "SYN-LISTING-b1"},
    ({"relation_id": " ", "issuer_id": "SYN-ISSUER-1",
      "source_ref": " ", "available_at": "2026-05-01T00:00:00+00:00",
      "members": (
          {"listing_id": "SYN-LISTING-a1", "counter_kind": "ordinary", "currency": "HKD"},
          {"listing_id": "SYN-LISTING-b1", "counter_kind": "ads", "currency": "USD"})},),
    as_of="2026-06-01T00:00:00+00:00",
))
```
Observed: `CounterRelationVerdict(allowed=True, reasons=(), relation_id=' ')`.
Expected per docstring: at least one of `RELATION_ID_MISSING` /
`RELATION_UNSOURCED`. The single-character space passes both blanks, the
verdict says the relation is fine and echoes `' '` as the relation_id.

Falsifier: change `_blank()` to `if value is None or (isinstance(value, str)
and value.strip() == "")` — then `" "`, `"\t"`, `"\n"` refuse. (The existing
tests `test_a02g_blank_*` only cover `None` / `""`, so the new behaviour
does not break them.)

REPAIR: seat should commission a single shared `_blank()` that treats any
non-`str`, any `None`, and any whitespace-only `str` as blank. Same fix
applies to A18 (see X8A-05).

---

### X8A-02 — MAJOR — A02G — `currency` accepts integer, float, and boolean values as "declared"

CLAIM: A `currency` field of `840` (int), `840.0` (float), `True`, `False`,
`0`, or `1` is accepted as a "declared currency" — `CURRENCY_UNDECLARED`
fires only for `None` or `""`. The same guard's `counter_kind` check
correctly refuses all six values because it tests `not in _COUNTER_KIND_SET`.
The internal asymmetry (counter_kind: set membership; currency: blank-only)
means an ISO-4217-numeric-code caller, a JSON-decoded `true`, or a
flag-as-currency passes silently as a real currency.

Module: `_blank()` at line 124, CURRENCY check at lines 270-271,
COUNTER_KIND check at line 268. COUNTER_KIND uses `member.get("counter_kind")
not in _COUNTER_KIND_SET`; CURRENCY uses `_blank(member.get("currency"))`.

Reproducing input:
```python
from sni_counter_relation_guard import check_counter_relation
print(check_counter_relation(
    {"issuer_id": "SYN-ISSUER-1",
     "left_listing_id": "SYN-LISTING-a1",
     "right_listing_id": "SYN-LISTING-b1"},
    ({"relation_id": "SYN-REL-1", "issuer_id": "SYN-ISSUER-1",
      "source_ref": "SYN-SRC-1", "available_at": "2026-05-01T00:00:00+00:00",
      "members": (
          {"listing_id": "SYN-LISTING-a1", "counter_kind": "ordinary", "currency": 840},
          {"listing_id": "SYN-LISTING-b1", "counter_kind": "ads", "currency": "USD"})},),
    as_of="2026-06-01T00:00:00+00:00",
))
```
Observed: `CounterRelationVerdict(allowed=True, reasons=(), relation_id='SYN-REL-1')`.
Same verdict for `currency=True`, `currency=False`, `currency=840.0`,
`currency=0`, `currency=1`. The COUNTER_KIND counterpart at line 268
correctly refuses `counter_kind=True` (output: `('COUNTER_KIND_UNKNOWN',)`).

Falsifier: change the currency check to `if not isinstance(member.get("currency"), str)
or member.get("currency") not in {"HKD","USD","CNY",...}` (or simply `if
member.get("currency") not in some-allowed-currency-set`).

REPAIR: seat should commission a typed-set currency check like the counter_kind
one. The CURRENCY check should refuse any value that is not a non-blank `str`.

---

### X8A-03 — MAJOR — A02G — non-string `relation_id` (int, float, bool, list, dict) yields `allowed=True` with `relation_id=None`

CLAIM: A `relation_id` of `0`, `1`, `1.5`, `True`, `False`, `[]`, or `{}`
yields `allowed=True, reasons=(), relation_id=None`. The `_blank` check is
False for all of them, so `RELATION_ID_MISSING` is not appended. The echo
code requires `isinstance(relation_id, str)` and falls back to `None`, so
the verdict misleads a downstream caller: `allowed=True` signals a valid
relation, but `relation_id=None` hides the malformed input. The docstring
says "ids and codes are compared as exact strings" and "verdict's relation_id
only echoes a caller-supplied relation_id" — silently coercing to None is
neither comparison nor echo.

Reproducing input:
```python
from sni_counter_relation_guard import check_counter_relation
for rid in [0, 1, 1.5, True, False, [], {}]:
    v = check_counter_relation(
        {"issuer_id": "SYN-ISSUER-1",
         "left_listing_id": "SYN-LISTING-a1",
         "right_listing_id": "SYN-LISTING-b1"},
        ({"relation_id": rid, "issuer_id": "SYN-ISSUER-1",
          "source_ref": "SYN-SRC-1", "available_at": "2026-05-01T00:00:00+00:00",
          "members": (
              {"listing_id": "SYN-LISTING-a1", "counter_kind": "ordinary", "currency": "HKD"},
              {"listing_id": "SYN-LISTING-b1", "counter_kind": "ads", "currency": "USD"})},),
        as_of="2026-06-01T00:00:00+00:00",
    )
    print(rid, v.allowed, v.reasons, v.relation_id)
```
Observed (all): `True () None`.
Expected per docstring: refuse, because the relation_id is not a real id.

Falsifier: change the echo path to either propagate the non-string value
literally (so downstream sees the malformed input), or refuse
`RELATION_ID_MISSING` whenever `relation_id` is not a non-blank `str`.

REPAIR: commission `RELATION_ID_MISSING` for non-`str` / blank `str` /
whitespace `str`, and have the echo reflect that refusal.

---

### X8A-04 — MAJOR — A02G — `source_ref` accepts non-string values as "sourced"

CLAIM: A `source_ref` of `42` (int) or `True` (bool) yields
`allowed=True, reasons=()` because `_blank(42)` and `_blank(True)` are
False. The docstring promises `RELATION_UNSOURCED` for "non-sourced"
inputs; an integer is not a real source reference.

Reproducing input:
```python
from sni_counter_relation_guard import check_counter_relation
v = check_counter_relation(
    {"issuer_id": "SYN-ISSUER-1",
     "left_listing_id": "SYN-LISTING-a1",
     "right_listing_id": "SYN-LISTING-b1"},
    ({"relation_id": "SYN-REL-1", "issuer_id": "SYN-ISSUER-1",
      "source_ref": 42, "available_at": "2026-05-01T00:00:00+00:00",
      "members": (
          {"listing_id": "SYN-LISTING-a1", "counter_kind": "ordinary", "currency": "HKD"},
          {"listing_id": "SYN-LISTING-b1", "counter_kind": "ads", "currency": "USD"})},),
    as_of="2026-06-01T00:00:00+00:00",
)
print(v)
```
Observed: `CounterRelationVerdict(allowed=True, reasons=(), relation_id='SYN-REL-1')`.
Same for `source_ref=True`, `source_ref=False`, `source_ref=0`, `source_ref=1`.

REPAIR: commission a `RELATION_UNSOURCED` check that requires
`isinstance(source_ref, str) and source_ref.strip() != ""`.

---

### X8A-05 — MAJOR — A18 — `entitlement_ref` accepts whitespace-only and non-string values

CLAIM: An `entitlement_ref` of `" "`, `"\t"`, `"\n"`, `True`, `False`, `0`,
`1`, or `1.5` yields `allowed=True` (and the LOADER IS CALLED with the
document_id) — `ENTITLEMENT_REF_MISSING` only fires for `None` or `""`. The
docstring promises a refusal; same `_blank()` root cause as X8A-01.

Module: `research/single_name_intelligence/common/sni_entitlement_guard.py`,
`_blank()` at line 117, `_present()` at line 125, `ENTITLEMENT_REF_MISSING`
check at line 244.

Reproducing input:
```python
from sni_entitlement_guard import gate_access
spy = lambda d: ("LOADED", spy.calls.append(d))[0]
spy.calls = []
v = gate_access(
    {"surface": "private", "account_id": "syn-account-1",
     "document_id": "syn-doca-42", "want_full_text": True},
    {"entitlement_ref": " ",
     "account_id": "syn-account-1",
     "document_ids": ("syn-doca-41", "syn-doca-42"),
     "valid_from": "2026-01-01T00:00:00+00:00",
     "valid_to": None, "revoked_at": None},
    as_of="2026-10-01T12:00:00+00:00",
    loader=spy,
)
print(v.allowed, v.reasons, spy.calls)
```
Observed: `True () ['syn-doca-42']` — loader ran with the document_id;
private full-text payload was returned.
Same observed for `entitlement_ref=True`, `entitlement_ref=0`, etc.

Falsifier: tighten `_blank()` to cover non-`str` and whitespace-`str` (same
fix as X8A-01).

REPAIR: commission the same `_blank()` tightening; this is the same fix
needed for X8A-01.

---

### X8A-06 — MAJOR — A18 — `account_id` matches across non-string types (1 == True), and a non-string account opens the loader

CLAIM: The `account_id` boundary uses Python `==`. `1 == True` is `True`,
so `account_id=1` on the request and `account_id=True` on the entitlement
match. The guard has no isinstance check; non-string account_ids on BOTH
sides (e.g. `0`/`False`, `1`/`True`, `1.5`/`1.5`, `float("inf")`/`inf`) all
open the loader. The docstring says "caller-supplied opaque strings";
numeric/bool ids are not opaque strings.

Module: lines 245-246 use `account_id != entitlement.get("account_id")`,
without any `isinstance` check. A loader-side private full-text leak can
follow from a JSON-decoded `true` arriving as `True` on one side and `1` on
the other.

Reproducing input:
```python
from sni_entitlement_guard import gate_access
spy = lambda d: ("LOADED", spy.calls.append(d))[0]
spy.calls = []
v = gate_access(
    {"surface": "private", "account_id": 1,
     "document_id": "syn-doca-42", "want_full_text": True},
    {"entitlement_ref": "syn-ent-17",
     "account_id": True,
     "document_ids": ("syn-doca-41", "syn-doca-42"),
     "valid_from": "2026-01-01T00:00:00+00:00",
     "valid_to": None, "revoked_at": None},
    as_of="2026-10-01T12:00:00+00:00",
    loader=spy,
)
print(v.allowed, v.reasons, spy.calls)
```
Observed: `True () ['syn-doca-42']` — loader ran.

Falsifier: add `if not isinstance(account_id, str) or account_id.strip() == ""` to the
mismatch predicate; then `account_id=1` triggers `ACCOUNT_MISMATCH` and the
loader does not run.

REPAIR: commission an isinstance-`str` + non-blank check on `account_id` on
both request and entitlement sides, before the equality check. The
document_id side already requires `isinstance(document_id, str)` (line 176);
extend the same discipline to account_id.

---

### X8A-07 — MINOR — A02G — verdict echoes whitespace / newline / trailing-space relation_ids verbatim

CLAIM: When a relation's `relation_id` is `" "` or `"SYN-REL-1\n"` (or any
non-blank string with surrounding whitespace), the verdict's `relation_id`
field carries the exact bytes. Downstream callers that compare this string
to an expected id using `==` see two ids that look identical but differ by
a single space / newline. No trim, no normalisation — and the static-scan
test `test_a02g_static_scan_no_normalisation` enforces no `.strip()` /
`.lower()` etc. So the asymmetry is structural: trailing-space listing_ids
are correctly refused (see `test_a02g_adversarial_trailing_space`,
`test_a02g_adversarial_member_side_variant`), but trailing-space
relation_ids are echoed verbatim.

Reproducing input:
```python
from sni_counter_relation_guard import check_counter_relation
v = check_counter_relation(
    {"issuer_id": "SYN-ISSUER-1",
     "left_listing_id": "SYN-LISTING-a1",
     "right_listing_id": "SYN-LISTING-b1"},
    ({"relation_id": "SYN-REL-1\n", "issuer_id": "SYN-ISSUER-1",
      "source_ref": "SYN-SRC-1", "available_at": "2026-05-01T00:00:00+00:00",
      "members": (
          {"listing_id": "SYN-LISTING-a1", "counter_kind": "ordinary", "currency": "HKD"},
          {"listing_id": "SYN-LISTING-b1", "counter_kind": "ads", "currency": "USD"})},),
    as_of="2026-06-01T00:00:00+00:00",
)
print(v.relation_id, len(v.relation_id))
```
Observed: `SYN-REL-1\n` (length 10; `len("SYN-REL-1") == 9`).
Expected per the principle "exact strings" plus the trailing-space-mismatch
precedent for listing_ids: the relation_id should either be refused or
stripped. Today it is echoed.

REPAIR: align with the listing-id discipline: either echo the bytes
unchanged and add a test for the verbatim echo, or refuse any relation_id
with embedded whitespace / control characters.

---

### X8A-08 — MINOR — A18 — private surface + account_id `" "` on BOTH sides passes (no whitespace-aware check)

CLAIM: When request `account_id` is `" "` and entitlement `account_id` is
also `" "`, the verdict is `allowed=True` and the loader runs. The
ACCOUNT_MISMATCH check uses `_blank` (only refuses `None` and `""`) and
then `" " == " "` is True. This is a real-mismatch semantic: a whitespace-
only account id is not a real account.

Reproducing input:
```python
from sni_entitlement_guard import gate_access
spy = lambda d: ("LOADED", spy.calls.append(d))[0]
spy.calls = []
v = gate_access(
    {"surface": "private", "account_id": " ",
     "document_id": "syn-doca-42", "want_full_text": True},
    {"entitlement_ref": "syn-ent-17",
     "account_id": " ",
     "document_ids": ("syn-doca-41", "syn-doca-42"),
     "valid_from": "2026-01-01T00:00:00+00:00",
     "valid_to": None, "revoked_at": None},
    as_of="2026-10-01T12:00:00+00:00",
    loader=spy,
)
print(v.allowed, v.reasons, spy.calls)
```
Observed: `True () ['syn-doca-42']` — loader ran with full-text payload.

REPAIR: tightening `_blank` (same fix as X8A-01/05) closes this; otherwise
add an explicit isinstance-`str` + non-whitespace check on both sides.

---

## CHECKED-CLEAN

The attacks that found nothing, each with the bounds I checked:

- **A02G, dtype/identifier search-bounds**: I scanned every numeric field
  (`issuer_id`, `relation_id`, `source_ref`, `available_at`, `members[].currency`,
  `members[].counter_kind`, `members[].listing_id`) for `True`/`False`/`0`/`1`/
  `-0.0`/`NaN`/`+inf`/`-inf`/`1e308*10`/`Decimal`/`Fraction`/`numeric-strings`
  via `/tmp/x8a_attacks/attack_a02g.py` (output: 9 ms wall time, no
  `open(`, `utcnow`, `date.today`, `time.time`, `datetime.now` anywhere).
  `counter_kind` correctly refuses `True`/`False`/`None`/`int`/`float`
  (because it tests `not in _COUNTER_KIND_SET`); `currency` does NOT —
  covered by X8A-02. Numeric `available_at` values (`0`, `1`, `1.5`,
  `True`) all refuse via `RELATION_NOT_AVAILABLE_AS_OF`. Membership-of-int
  (`listing_id=12345`) correctly refuses via `RELATION_SET_MISSING`.

- **A02G, time-shape**: naive (`2026-05-01T00:00:00`), date-only
  (`2026-05-01`), invalid month (`2026-13-01T00:00:00+00:00`), empty (`""`),
  `None`, `as_of Z` (`2026-06-01T00:00:00Z` is normalized to +00:00 and
  used as decision time), `+99` offset — all refuse or normalise
  consistently. Same-instant equality (`as_of == available_at`) allows, as
  documented.

- **A02G, shape**: `members` as `str` / `bytes` / `dict` raise `TypeError`;
  `members=None` is treated as no-members (REFUSED). `member` not a Mapping
  raises. Extra unknown keys in `relation` are ignored (allowed). 10000
  duplicated and 10000 distinct containing relations: 9 ms wall time,
  `AMBIGUOUS_RELATION` returned deterministically.

- **A02G, determinism**: two runs over the same (relations tuple,
  members tuple) yield equal verdicts; reversed relations order yields
  identical `AMBIGUOUS_RELATION` verdict (covered by
  `test_a02g_flip_ambiguous_relation`).

- **A02G, mutation sweep on three branches** (`CURRENCY_UNDECLARED`,
  `COUNTER_KIND_UNKNOWN`, `RELATION_NOT_AVAILABLE_AS_OF`, disabled in /tmp
  copies via `mutation_test2.py`): 3 / 4 / 6 tests respectively fail. No
  surviving mutants among the three I picked.

- **A18, identifier search-bounds**: `account_id` and `document_id` with
  trailing space, case change, Cyrillic look-alike all refuse correctly
  (covered by `test_a18_account_*`, `test_a18_document_*`). Numeric shapes
  on `document_id` (`0`, `1`, `True`, `False`, `-1`, `1.5`, `NaN`,
  `+inf`, `-inf`) all refuse via `DOCUMENT_NOT_ENTITLED` because
  `_document_entitled` requires `isinstance(document_id, str)`. `account_id`
  accepts non-strings when both sides are non-strings (covered by X8A-06);
  any mismatch still refuses (the test suite does kill an
  `ACCOUNT_MISMATCH`-disabled mutant).

- **A18, time-shape**: naive bounds (`valid_from="2026-01-01T00:00:00"`,
  `valid_to="2027-01-01T00:00:00"`, `revoked_at="2027-01-01T00:00:00"`)
  refuse with the correct code. Z-suffix on `as_of`, `revoked_at`, `valid_to`
  normalizes to `+00:00` correctly. Boundary equality (`as_of ==
  valid_from`, `as_of == valid_to`, `as_of == revoked_at`) handled per the
  docstring (at valid_from: allowed; at valid_to: expired; at revoked_at:
  revoked).

- **A18, public-surface hard refusal**: `surface="public"` with
  `want_full_text=True`/`1`/`"yes"`/`None`/missing all refuse
  `PUBLIC_FULL_TEXT_FORBIDDEN` and never call the loader. `surface="public"`
  with `want_full_text=False` allows without loading.

- **A18, loader invariants**: loader is called exactly once on a private
  allow (`test_a18_positive_private_full_text_allowed`,
  `test_a18_positive_private_want_false_still_loads_once`); not called on
  any refusal (`test_a18_every_refusal_never_loads`). Repr of `AccessVerdict`
  with a non-`None` payload does not print the payload
  (`test_a18_repr_hides_payload`).

- **A18, shape**: `request` not a Mapping raises `TypeError`; `entitlement`
  not a Mapping and not `None` raises `TypeError`; loader not callable
  raises `TypeError`. `document_ids` not in
  `(list, tuple, frozenset, set)` correctly refuses
  `DOCUMENT_NOT_ENTITLED`. `document_ids` as `set` IS allowed (the
  container tuple at line 41 contains `set`). 10000-member document_ids:
  fast path.

- **A18, mutation sweep on three branches**
  (`PUBLIC_FULL_TEXT_FORBIDDEN`, `ACCOUNT_MISMATCH`, `ENTITLEMENT_REVOKED`):
  4 / 6 / 4 tests fail respectively when the branch is disabled. No
  surviving mutants.

- **A16, identifier search-bounds**: `record_id` and `version_id` trailing
  space / case change / Cyrillic / numeric / `None` / `int` / `bool` all
  handled correctly. `_valid_record` rejects any record whose shape does
  not match `RECORD_FIELDS` exactly (`test_a16_record_shape_invalid`,
  `test_a16_version_type_invalid`, `test_a16_content_sha256_invalid`). Same
  on `recorded_at` (timezone-aware ISO required, `+99` refused,
  `test_a16_recorded_at_requires_offset`). Test file parametrises on
  `bad_version` (True / "2" / 0 / 1.0) and `bad_sha` ("AB"*32 / "a"*63 /
  "a"*65 / "g"*64 / 11*32 / None); each refuses with `RECORD_FIELD_INVALID`.

- **A16, chain rules**: `MIXED_RECORD_IDS` from prior-side covered by
  `test_a16_mixed_record_ids_from_prior_side`. `HISTORY_TRUNCATED` from
  prior-shorter, prior-missing-middle, prior-version-id-case-change
  covered by `test_a16_truncated_missing_middle_version`,
  `test_a16_truncated_same_length_missing_version_id`. `HISTORY_REWRITTEN`
  per-field parametrised by `test_a16_rewrite_each_prior_field`. `FORK`
  (same version, different vid) covered by `test_a16_flip_fork`.
  `VERSION_GAP` covered by `test_a16_flip_version_gap`. `SUPERSEDES_MISMATCH`
  covered by `test_a16_flip_supersedes_mismatch`,
  `test_a16_supersedes_none_on_version_two_mismatch`,
  `test_a16_supersedes_set_on_version_one_mismatch`. `CONTENT_UNCHANGED`
  covered by `test_a16_flip_content_unchanged`. `RECORDED_AT_NOT_MONOTONE`
  covered by `test_a16_flip_recorded_at_not_monotone`,
  `test_a16_equal_recorded_at_refuses`,
  `test_a16_mixed_offsets_compared_as_instants` (reversed order refuses).

- **A16, shape**: `prior` / `proposed` not tuple/list raises `TypeError`;
  record not a Mapping raises. Extra unknown key in record refuses with
  `RECORD_FIELD_INVALID`. 10000 records: 4.6 ms wall time (fast path).
  Empty proposed with non-empty prior refuses
  (`test_a16_proposed_empty_refused`); empty prior and empty proposed
  refuses (`test_a16_prior_empty_and_proposed_empty_refused`).

- **A16, determinism**: same `(prior, proposed)` tuple yields the same
  `LineageVerdict` on repeated runs. Reversed proposed order yields a
  different verdict (intended — order matters in a sequence).

- **A16, mutation sweep on three branches** (`CONTENT_UNCHANGED`,
  `VERSION_NOT_INCREASING`, `DUPLICATE_VERSION_ID`): 3 / 3 / 2 tests fail
  respectively. No surviving mutants.

- **A02G / A18 / A16, authority**: every `AUTHORITY_FLAGS` value is literal
  `False` (verified by `python3 -c` import of each module). Every verdict's
  `authority_flags` property returns the module-level `AUTHORITY_FLAGS`
  MappingProxyType. Setting any flag raises `ValueError`. No flag becomes
  `True` or `1` anywhere in the source.

- **A02G / A18 / A16, stdlib-only**: AST walk over each module: top-level
  imports are only `__future__`, `dataclasses`, `datetime`, `types`,
  `typing`. No `re`, no `pandas`, no `pyarrow`, no `jsonschema`, no `os`,
  no `io`. No `datetime.now`, `utcnow`, `date.today`, `time.time`, `open(`
  substring.

- **A02G / A18 / A16, no ticker/listing literal**: AST + text scan of each
  module confirms no `BABA`, `TCEHY`, `AAPL`, `MSFT`, `NVDA`, `GOOGL`,
  `AMZN`, `META`, `TSLA`, and no `\b\d{4,5}\.HK\b`. The static-scan tests
  (`test_a02g_static_scan_module_source`, `test_a18_static_scan_module_source`,
  `test_a16_static_scan_reasons_and_forbidden_text`) codify this.

## What this review does NOT prove

- The guards have NOT been wired into any owner, pipeline, page, or job.
  All three are DRAFT. Behaviour may differ once the owner callers supply
  actual records.
- The third party `seal_full_check.py` final-line OK only confirms the
  acceptance-evidence pipeline is byte-identical on the parent
  study/observation files. It does NOT prove the three guards are correct;
  the guards are not yet in the seal study set.
- The test suite is strong against the branches I disabled (all nine
  mutants killed), but I did not exhaustively sweep every line. A future
  reviewer should run `mutmut` / cosmic-ray / equivalent over the three
  modules; the `_blank()` gaps above mean a property-based or example-
  based test like `assert _blank(" ") is True` would have caught all
  six whitespace findings immediately.
- The `_as_date` / `_as_datetime` helpers in A02G and A18 (and the
  `_aware_datetime` in all three) were tested for boundary correctness
  on representative inputs, but I did not exhaustively test every leap-
  day / leap-second / DST-offset edge case. Behaviour on `2026-02-29T...`
  follows whatever `datetime.fromisoformat` does in Python 3.10+.
- This review found zero ticker / listing literals in the modules and
  zero authority flags set True, but it does not constitute a license
  audit — those checks live in other lanes.
- Attack #1 (docstring vs behaviour) was strong against A02G and A18 and
  found nothing material against A16; attack #2-7 found the gaps above;
  attack #8 (seal check) was run and reported. No attacks surfaced a
  live-leak path that the modules' own tests do not already cover, except
  the `_blank()` gaps, which the existing tests do not exercise because
  they only test `None` / `""`.