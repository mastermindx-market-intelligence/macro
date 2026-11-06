# X9 — SNI guard red-team after the FAMILY TEXT RULE v2 rewrites (INT7)

Scope: all 15 modules matching `research/single_name_intelligence/common/sni_*_guard.py`
at commit `9a2682e4a5f1f9794acf168f512d96d819476b05`. The earlier X8A/X8B/X8C rounds
predate the INT7 rewrites; the X9 round checks the post-rewrite state of every guard.
Excluded topics (parallel repair lanes own them; we do not file on them):
`sni_kpi_missingness_guard` `period_id` / `expected_periods` handling;
`sni_then_known_guard` `fact_id` / `supersedes` handling; the form of the
`_text_present` body in `sni_identity_binding_guard` and `sni_release_evidence_guard`.
Everything else in those four modules is in scope.

Every `AUTHORITY_FLAGS` mapping is literal false across the 15 modules
(`rank_authority`, `gate_authority`, `size_authority`, `signal_authority`,
`escalation_authority`, `trade_authority`); the existing
`refuse_nonfalse_authority` idiom refuses any non-False value. Every module
imports only `__future__`, `dataclasses`, `datetime`, `math` (where used),
`types`, `typing`, `collections.abc`, `zoneinfo`, `functools`. No `open(`,
no `datetime.now`, no `utcnow`, no `date.today`, no `time.time`, no ticker
or listing literal in any branch.

`python3 research/single_name_intelligence/evaluation/seal_full_check.py --study all --repo-root .`
final line: `SEAL FULL CHECK: OK (10 files float-equivalent on Linux x86_64 within rel 1e-10 / abs 1e-13, not byte-identical; byte identity rests on the XREP Linux receipt)`.

## Summary

Six findings: 4 MAJOR, 1 MINOR, 1 INFO. The four MAJORs span two distinct root
causes: (a) direct Python `==` / `!=` on identity fields that the FAMILY
TEXT RULE v2 mandates must be present-as-str first (three modules:
identity_binding currency, ads_ratio `rec.issuer_id` vs `request.issuer_id`,
counter_relation `relation.issuer_id` vs `request.issuer_id`); and (b) the
sole remaining `in <set>` membership test on a caller-supplied value that is
NOT gated by `_text_present` first, so an unhashable `level` raises
TypeError out of `validate_fact`. The MINOR is the documented-but-still-
violating `_blank` on a closed-set / family-rule-applicable field in
class_duplicate_guard's `_pair_shape_ok`. The INFO is the well-known
dead-helper pair `_blank` and `_present` in view_state_guard called out
explicitly in the X9 brief.

## Scope and exclusions

- `sni_kpi_missingness_guard` `period_id` / `expected_periods` handling — out of scope.
- `sni_then_known_guard` `fact_id` / `supersedes` handling — out of scope.
- The form of the `_text_present` body in `sni_identity_binding_guard` and
  `sni_release_evidence_guard` — out of scope. We DO attack every OTHER
  defect in those two modules.
- `sni_inference.py` (matches `sni_*.py` but not `sni_*_guard.py`) — out of
  scope for X9 (not a refusal contract). Future round may differ.

## Findings

### X9-01 — MAJOR — `sni_identity_binding_guard.py:340` — currency `!=` uses bare Python equality, not `_text_present`-gated equality

CLAIM. The guard's `bind_identity` checks
`if request.get("currency") != listing.get("currency"): reasons.append("CURRENCY_MISMATCH")`
at line 340 of `research/single_name_intelligence/common/sni_identity_binding_guard.py`.
That comparison uses Python `!=` with no `_text_present` gate on either
side. The FAMILY TEXT RULE v2 reads: "Equality is checked only between two
present values." Two ABSENT (None, "", whitespace, non-str) currencies
"match" silently and Python bool/int collisions (`True == 1`, `True == 1.0`)
are accepted as the same currency.

EVIDENCE. From `/tmp/x9a_currency.py` (ran against this commit):
```
currency=None & currency=None: True ()         # no CURRENCY_MISMATCH
currency=True & currency=1: True ()             # Python: True == 1
```
The companion path through `_id_pair_equal` (lines 222-233) is properly
gated; the `currency` check at line 340 is the only identity comparison
left in the module that uses bare Python equality.

REPRODUCING INPUT:
```python
from sni_identity_binding_guard import bind_identity
AS_OF = "2026-08-20T12:00:00+00:00"; AV = "2026-08-20T11:00:00+00:00"
v = bind_identity(
    {"listing_id": "SYN-LIST-1", "issuer_id": "SYN-ISS-1",
     "currency": None, "operation_needs_issuer": True},
    listing={"listing_id": "SYN-LIST-1", "security_id": "SYN-SEC-1",
             "currency": None, "owner_ref": "O", "available_at": AV,
             "display_code": "D", "display_name": "Name"},
    security={"security_id": "SYN-SEC-1", "issuer_id": "SYN-ISS-1",
              "owner_ref": "O", "available_at": AV},
    issuer={"issuer_id": "SYN-ISS-1", "owner_ref": "O", "available_at": AV},
    as_of=AS_OF,
)
print(v.allowed, v.reasons)  # -> (True, ())
```

EXPECTED per family rule: refuses with `CURRENCY_MISMATCH`. The family
rule mandates "Equality is checked only between two present values", so
two absent currencies are not a match and must refuse.

PIN: `test_x9_01_identity_binding_currency_untext_equal`.

---

### X9-02 — MAJOR — `sni_join_guard.py:289` — `level not in _LEVELS` raises TypeError on unhashable `level`

CLAIM. `validate_fact` line 289 of
`research/single_name_intelligence/common/sni_join_guard.py`:
```python
level = fact.get("level")
if _blank(level) or level not in _LEVELS:
    found.append("LEVEL_UNKNOWN")
```
`_blank(level)` only catches `None` and `""`. An unhashable `level`
(list, dict, set, anything `__hash__`-less) falls through to the
`level not in _LEVELS` membership test and raises `TypeError: unhashable
type: 'list'` (or equivalent). The other identity-or-text fields in the
same module route through `_text_absent(fact.get(...))` which always
returns True for non-str and never reaches a set membership test.

EVIDENCE. From `/tmp/x9c_join_level.py`:
```
level=list RAISED: unhashable type: 'list'
```
The X9 brief states the family rule: "Unhashable input never raises;
only `refuse_nonfalse_authority` or a documented top-level TypeError
may raise." This is neither, and the module docstring of `sni_join_guard`
is silent on the possibility.

REPRODUCING INPUT:
```python
from sni_join_guard import validate_fact
print(validate_fact({..., "level": ["issuer"]}))   # raises TypeError
```

EXPECTED: return `('LEVEL_UNKNOWN',)` (or any refusal), never raise.

PIN: `test_x9_02_join_guard_level_unhashable_raises`.

---

### X9-03 — MAJOR — `sni_ads_ratio_guard.py:392, 406, 426, 445` — `rec.issuer_id` vs `request_issuer` uses bare Python equality; int/bool collisions match silently

CLAIM. Four sites in
`research/single_name_intelligence/common/sni_ads_ratio_guard.py` use
direct Python `==`/`!=` on `rec.get("issuer_id")` and `request_issuer`:
```python
if rec.get("issuer_id") != request_issuer:        # line 392 (loop)
for rec in rec_list
    if rec.get("issuer_id") == request_issuer and _interval_usable(rec)  # line 406
def _covers_day(rec, issuer_id, day):              # line 257
    if rec.get("issuer_id") != issuer_id: return False
cover_on = [rec for rec in rec_list if _covers_day(rec, request_issuer, on_date)]  # line 426
cover_win = [rec for rec in rec_list if _covers_day(rec, request_issuer, window_date)]  # line 445
```
None of these gates `request_issuer` (or the record-side value) on
`_text_present`. With both sides equal under Python (e.g. `1 == 1`,
`True == 1`, `None == None`), the family rule's "Equality is checked
only between two present values" is violated.

EVIDENCE. From `/tmp/x9b_ads_issuer.py`:
```
issuer_id=1 (int) both sides:  True ()            # allowed, no ISSUER_MISMATCH
issuer_id=str both sides:      True ()            # control: still allowed
issuer_id=True vs 1:           True ()            # Python True == 1
```
The first case is the defect — neither value is present under FAMILY
TEXT RULE v2.

REPRODUCING INPUT:
```python
from sni_ads_ratio_guard import check_ads_ratio
print(check_ads_ratio(
    {"issuer_id": 1, "on_date": "2015-01-15"},
    [{"ratio_record_id": "rr-1", "issuer_id": 1,
      "ordinary_per_ads": 8, "valid_from": "2010-01-01",
      "valid_to": None, "source_ref": "src",
      "available_at": "2019-07-10T00:00:00+00:00"}],
    as_of="2021-06-01T00:00:00+00:00",
).reasons)  # -> ()
```

EXPECTED: refuses with `ISSUER_MISMATCH` because neither side is text-present.

PIN: `test_x9_03_ads_ratio_issuer_id_untext_equal`.

---

### X9-04 — MAJOR — `sni_counter_relation_guard.py:272-273` — `relation.issuer_id` vs `request.issuer_id` uses bare Python equality; `True`/`1`/None collisions match silently

CLAIM. Line 273 of
`research/single_name_intelligence/common/sni_counter_relation_guard.py`:
```python
if relation.get("issuer_id") != request.get("issuer_id"):
    reasons.append("ISSUER_MISMATCH")
```
This is direct Python `!=` without `_text_present` gating on either
side. Same root cause as X9-03. The pre-rewrite X8A-04 finding fixed
non-str `source_ref`/`currency`/`relation_id` at the same module via
`_text_present`; the `issuer_id` site was missed.

EVIDENCE. From `/tmp/x9d_cr_issuer.py`:
```
True vs 1:      True ()    # Python: True == 1; no ISSUER_MISMATCH
None vs None:   True ()    # both ABSENT silently match
```
For `True vs 1`, `x8a_attacks/counter_relation` produces no
`ISSUER_MISMATCH` reason. The verdict returns `allowed=True` despite
both sides being non-str.

REPRODUCING INPUT:
```python
from sni_counter_relation_guard import check_counter_relation
v = check_counter_relation(
    {"issuer_id": True, "left_listing_id": "SYN-LISTING-a1",
     "right_listing_id": "SYN-LISTING-b1"},
    ({"relation_id": "SYN-REL-1", "issuer_id": 1,
      "source_ref": "SYN-SRC-1", "available_at": "2026-05-01T00:00:00+00:00",
      "members": (
          {"listing_id": "SYN-LISTING-a1", "counter_kind": "ordinary", "currency": "HKD"},
          {"listing_id": "SYN-LISTING-b1", "counter_kind": "ads", "currency": "USD"})},),
    as_of="2026-06-01T00:00:00+00:00",
)
print(v.allowed, v.reasons)  # -> (True, ())
```

EXPECTED: refuses with `ISSUER_MISMATCH`.

PIN: `test_x9_04_counter_relation_issuer_id_untext_equal`.

---

### X9-05 — MINOR — `sni_class_duplicate_guard.py:154-157` — `_pair_shape_ok` accepts whitespace-only `security_ids` via `_blank`

CLAIM. `_pair_shape_ok` in
`research/single_name_intelligence/common/sni_class_duplicate_guard.py`:
```python
def _pair_shape_ok(sids: object) -> bool:
    if not isinstance(sids, (tuple, list)): return False
    if len(sids) != 2: return False
    for sid in sids:
        if not isinstance(sid, str) or _blank(sid): return False
    return sids[0] != sids[1]
```
The helper's docstring promises "exactly two distinct **non-blank**
strings", but the loop uses `_blank` which only catches `None` and `""`.
A whitespace-only `sid` (`" "`, `"\t"`, NBSP, em space, ideographic
space, …) is `isinstance(sid, str)` and `_blank(sid)` returns False, so
the loop continues. A pair whose `security_ids` is `(" ", "X")` passes
the shape check and is treated as a structurally valid pair.

The end-to-end impact is benign (the pack's real `security_id`s flow
through `_text_present` and never carry whitespace, so
`frozenset(group) == frozenset(sids)` never matches), but the helper's
own contract is violated at the type-check layer.

EVIDENCE. Static analysis: `_pair_shape_ok` at line 154-157; the
docstring says "exactly two distinct non-blank strings"; `_blank` at
line 135-140 only returns True for `None` or `""`.

REPRODUCING INPUT:
```python
from sni_class_duplicate_guard import check_class_duplicates, _pair_shape_ok
print(_pair_shape_ok((" ", "X")))  # -> True (should be False per docstring)
```

EXPECTED: `False` per the docstring's "exactly two distinct non-blank
strings" promise.

PIN: `test_x9_05_pair_shape_ok_accepts_whitespace`.

---

### X9-06 — INFO — `sni_view_state_guard.py:154-163` — `_blank` and `_present` are dead helpers

CLAIM. The module defines `_blank` (lines 154-159) and `_present`
(lines 162-163). The only call to `_blank` in the module is its own
implementation site inside `_present` (line 163); `_present` itself is
never invoked anywhere in the module. No test file imports either
helper (`tests/test_sni_view_state_guard.py` and
`tests/test_sni_mut7_f.py` only import `check_view_transition`,
`persist_across`, `REASONS`, `AXES`, `LANGS`, `VIEWPORTS`,
`AUTHORITY_FLAGS`, `ViewTransitionVerdict`, `refuse_nonfalse_authority`).
The X9 brief explicitly calls these out as the canonical dead-helper
pair ("e.g. sni_view_state_guard `_blank` (~L154) and `_present`
(~L162)"). The presence of `_present` next to `_text_present`-only
checks in the same module is a future-misroute smell: a future edit
that calls `_present(before, "issuer_id")` instead of
`_text_present(before.get("issuer_id"))` would silently restore the
pre-INT7 permissive non-str acceptance.

EVIDENCE. Static scan: `grep -nE "_blank|_present"
research/single_name_intelligence/common/sni_view_state_guard.py`
yields only the definitions at lines 154/162 and the one internal use
at line 163; no other call site in the module, and no test import.

PIN: not applicable — an INFO finding about a code smell, not a
behaviour defect. Documenting in the review so the seat knows the
dead pair is exactly the hint the X9 brief named.

## Probes that held

Twenty-five probes below were run and matched the docs; no new finding
filed. Bounds described per probe.

1. **A09 join_guard `validate_fact`** — `level=1` (int): `('LEVEL_UNKNOWN',)`.
   `level=""` (str): `('LEVEL_UNKNOWN',)`. `level="issuer"`: empty.
   `level="ISSUER"` (case): `('LEVEL_UNKNOWN',)`. `level=None`:
   `('LEVEL_UNKNOWN',)`. `level=True` (bool): `('LEVEL_UNKNOWN',)`.
2. **A09 join_guard `check_join` with `join_kind="garbage"`** — returns
   `('JOIN_KIND_UNKNOWN',)` and `REFUSED`. `join_kind="same_fact"` /
   `"ratio"` / `"time_series"` all walk the rest of the rules.
3. **A09 join_guard `check_join` LEFT/RIGHT swap invariance** — for every
   fact pair I tried (mismatched `metric`, mismatched `basis`, both
   `period_end` blank/missing, mismatched `currency`, mismatched
   `share_denominator`), the bare (prefix-stripped) reason set is
   invariant under a swap. The docstring promise is kept.
4. **A36 class_duplicate `pair_shape_ok`** — non-list (str, dict) → False;
   non-2 length → False; both sids equal → False; one non-str sid → False;
   sid=`None` → False. Five shape negatives tested.
5. **A36 class_duplicate `check_class_duplicates` dead-pair case** — pack with
   no duplicate issuers + no pairs → `allowed=True`, `reasons=()`,
   `counted_security_ids` is the input order, `duplicate_issuers=()`.
6. **A13 comparison `_finite_positive_real`** — rejects `True`, `False`,
   `None`, `0`, `-1`, `NaN`, `+inf`, `-inf`; admits `1`, `1.5`, `1e300`.
7. **A13 comparison `check_comparison`** with `surface="public"` and
   `want_full_text=False` → no public-full-text refusal, FX may still
   refuse. Loader not called on public.
8. **A11 denominator `_finite_positive`** — rejects bool, zero, NaN, inf,
   -inf, negative floats; admits `1` and `1e300`. Identical semantics to
   the ADS guard's helper.
9. **A11 denominator `_correction_version_value`** — `1.0` (float) → None
   (CORRECTION_VERSION_MISSING); `True` → None; `None` → None;
   negative int → None.
10. **A11 denominator `_owner_authority_nonfalse`** — observation with
    `authority={"is_context_only": True, "rank_authority": True}` →
    refuses. observation with `is_context_only=False` → not refused.
    observation without `authority` key → not refused.
11. **A18 entitlement `_document_entitled`** — `document_id=1` (int) →
    refuses via `DOCUMENT_NOT_ENTITLED`. `document_ids` as `list`,
    `tuple`, `set`, `frozenset` all admitted; `None`, `dict`,
    `frozenset()` empty all refused correctly.
12. **A18 entitlement `gate_access`** — `surface="public"` with
    `want_full_text=1`, `"yes"`, `True`, `None`, missing all refuse
    `PUBLIC_FULL_TEXT_FORBIDDEN`; `want_full_text=False` allows. Loader
    not called on any refusal (`test_a18_every_refusal_never_loads`).
13. **A02 counter-relation `left_listing_id` as a list** — does NOT raise;
    refuses as `RELATION_SET_MISSING` since list vs `SYN-LISTING-a1`
    differs on `==`.
14. **A02 counter-relation `_covers_day` dual-listing-id collision
    matrix** — `left=1, right=True` → `SAME_LISTING` fires (Python `==`).
15. **A31 view-state `_changed_axes`** — returns `()` when both sides are
    non-text-present for the same axis. `before={"issuer_id":1}`,
    `after={"issuer_id":True}` → `(('issuer_id',),)` (Python `1 == True`
    makes them "equal" in the text-present test, so no change).
16. **A31 view-state `change="as_of"` but only `lang` actually changed**
    → `ALLOWED` with `reasons=()` and `changed_axes=('lang',)`. This is
    the documented intent-as-permitted behaviour (`test_a31_positive_zero_change_declared_lang`).
17. **A31 view-state `_field_missing`** — missing axis on either side
    triggers `FIELD_MISSING`; trailing-space `issuer_id` triggers it via
    `_text_present`. Per-axis check works on every AXES element.
18. **A16 correction-lineage `_valid_record`** — `version="2"` (str) →
    False (`_version_number` requires real `int`); `version=2.0` → False;
    `version=0` → False; `recorded_at="2026-01-01"` (date-only) → False;
    `content_sha256="z"*64` → False; missing any RECORD_FIELDS key → False.
19. **A16 correction-lineage `check_lineage`** with empty `prior` and one
    valid `proposed` record → `allowed=True`, `appended=('v-1',)`.
20. **A16 correction-lineage `check_lineage`** with `proposed=()` →
    `proposed_valid=False` → `RECORD_FIELD_INVALID`; otherwise empty.
21. **A07 then-known `_fact_id_absent`** — accepts padding
    (`"SYN-FACT-1 "`, `" SYN-FACT-1"` stays PRESENT per the pinning test
    `test_a07g_duplicate_exact_only_no_folding`); rejects `None`, `""`,
    `" "`, `1`, `True`, `[1]`. **Recorded here, not a finding, because
    the fact_id path is excluded from X9 scope.**
22. **A33 release-evidence `_id_or_ref_present`** — non-str None, "" →
    False; non-str `1`, `[1]`, `{}` → False; `" "` (whitespace) and
    `"X "` (trailing space) → True. The permissive variant is the
    documented seat ruling (line 134-138); the form is excluded from X9
    so recorded here, not a finding.
23. **A33 release-evidence `check_release` slot with `slot_id=None`,
    `state="present"`** — emits `SLOT_STATE_UNKNOWN` (reusing the
    existing code), excludes the slot from `present_owner_slots`.
    The X8C-01 fix (reusing `SLOT_STATE_UNKNOWN`) is in force.
24. **A10 kpi-missingness `reported_periods` is now in
    `expected_periods` order** — 20 random shuffles of 4 records all
    yield the same `reported_periods` tuple (in `PERIODS` order).
    X8C-03 fix confirmed in force. **Recorded here, not a finding,
    because period handling is excluded.**
25. **A10 kpi-missingness `_finite_number`** — rejects `True`, `None`,
    `"10"`, NaN, inf, -inf; admits `0`, `-0.0`, `1e300`, `10**400`.
26. **All 15 modules — `AUTHORITY_FLAGS` literal False** — every flag in
    every MappingProxyType is `False`. `refuse_nonfalse_authority` raises
    `ValueError` for any non-False value supplied to it; the post-init
    hook enforces this on every verdict dataclass.
27. **All 15 modules — stdlib-only, no wall clock, no I/O, no ticker
    literals** — static scan: only `__future__`, `dataclasses`,
    `datetime`, `zoneinfo`, `functools` (A12 only), `types`, `typing`,
    `collections.abc`, `math`; no `pandas`, `numpy`, `re` (except the
    three-clock helper), `requests`, `urllib`. No `datetime.now`,
    `utcnow`, `date.today`, `time.time`, `monotonic`, `perf_counter`
    substring anywhere. No ticker / listing literal (`BABA`, `TCEHY`,
    `AAPL`, `MSFT`, `NVDA`, `GOOGL`, `AMZN`, `META`, `TSLA`,
    `\b\d{4,5}\.HK\b`, `0700`, `9988`, `3690`) anywhere.
28. **Seal check** —
    `python3 research/single_name_intelligence/evaluation/seal_full_check.py --study all --repo-root .`
    final line: `SEAL FULL CHECK: OK (10 files float-equivalent on Linux x86_64 within rel 1e-10 / abs 1e-13, not byte-identical; byte identity rests on the XREP Linux receipt)`.

## What this review does NOT prove

- The guards are DRAFT, not wired into any owner, pipeline, page, or
  job. Behaviour may differ when an owner caller supplies real records.
- A pinned xfail test guards the DESIRED behaviour (the family-rule-
  required refusal). Today's behaviour is the actual, unfixed state.
- The seal-check OK does not prove the four MAJORs above are correct;
  the guard modules are not in the seal study set.
- We did not exhaustively mutate every branch in the 15 modules; only
  the four MAJOR sites and the four INFO/MINOR sites were probed.
- We did not test concurrent calls; all 15 modules are pure functions.
- The same `level not in _LEVELS` site is also subject to a TypeError
  on a set/dict input; we documented the list case as the probe.
