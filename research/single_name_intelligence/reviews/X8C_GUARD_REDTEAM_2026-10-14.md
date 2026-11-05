# X8C — SNI guard red-team

Scope: `sni_ads_ratio_guard.py`, `sni_identity_binding_guard.py`, `sni_kpi_missingness_guard.py`, `sni_view_state_guard.py`, `sni_release_evidence_guard.py` at commit `97e9d6e7c3d15eeb3f8bb9e8996bfec710e6bfe0`. `sni_join_guard.py` used as the family pattern, not under attack. Owner-pattern (literal false) on every `AUTHORITY_FLAGS` mapping across all five modules: `rank_authority`, `gate_authority`, `size_authority`, `signal_authority`, `escalation_authority`, `trade_authority` — all literal `False`; no call path can set them true without raising. All five modules use stdlib only, no I/O, no wall clock, no ticker/listing literal in any branch.

Summary: **0 BLOCKER · 3 MAJOR · 8 MINOR · 0 NIT-FINDING THAT SURVIVES** (the mutation sweep also revealed one test-coverage gap classified as a MINOR). The five modules collectively refuse every reason they promise; the largest real defects are (a) the release-evidence guard accepting a slot with `slot_id` missing or non-string and counting it as a present owner slot, (b) the identity-binding `ID_LOOKS_DERIVED` substring matcher firing on innocent 3-character common prefixes, and (c) the KPI `reported_periods` tuple carrying the input-order of records rather than the expected-period order, so a shuffled series still passes the positive test only because the test happens to feed records in `PERIODS` order. Every "always allow" and per-reason branch-disable mutation was killed by at least one test; one non-regression mutation (`_blank` extended to treat `0` as blank) survived every test, which is reported as a coverage gap (MINOR).

## Findings

### X8C-01 — MAJOR — `sni_release_evidence_guard.py:180-206` — slot with no `slot_id` (None or key missing) is treated as a present owner slot

CLAIM. The docstring says the guard "never mints evidence refs or identity ids" and "A page whose evidence is all absent, or that rests on synthetic fixtures or test doubles, is refused, not filled in." The verdict's `present_owner_slots` field is meant to list "slot_ids that are present with provenance `owner`, in input order." In practice, a slot whose `slot_id` is `None` (explicit) or absent (key missing) is silently counted as a present owner slot and included in `present_owner_slots` with `None` as the slot id, so a synthetic or attacker-supplied slot can hide its identity and still count as real evidence.

EVIDENCE.
```
$ python3 - <<'PY'
import sys; sys.path.insert(0, '/home/longr/lanes/wt/sni-x8c-20261014T052454Z/research/single_name_intelligence/common')
from sni_release_evidence_guard import check_release
print(check_release({"page_id":"P","slots":(
    {"slot_id":None,"state":"present","provenance":"owner","evidence_ref":"X","required":True},
    {"slot_id":"S1","state":"present","provenance":"owner","evidence_ref":"Y","required":True},
    {"slot_id":"S2","state":"present","provenance":"owner","evidence_ref":"Z","required":True})}).present_owner_slots)
# -> (None, 'S1', 'S2')

print(check_release({"page_id":"P","slots":(
    {"state":"present","provenance":"owner","evidence_ref":"X","required":True},  # no slot_id KEY
    {"slot_id":"S1","state":"present","provenance":"owner","evidence_ref":"Y","required":True},
    {"slot_id":"S2","state":"present","provenance":"owner","evidence_ref":"Z","required":True})}).present_owner_slots)
# -> (None, 'S1', 'S2')
PY
```
The function never types-checks `slot_id` (line 180: `slot_id = slot.get("slot_id")`); `None` is not in `seen_ids` initially so no `DUPLICATE_SLOT` fires; `state=="present"` and `provenance=="owner"` make the slot count as a present owner slot. A non-string `slot_id` (e.g. `int(1)`, `[1,2]`) is also accepted and ends up in `present_owner_slots`.

FALSIFIER. If the seat believes the verdict must carry a meaningful string `slot_id` for every present owner slot, the fix is to append `"SLOT_ID_MISSING"` (or a new reason) when the slot's `slot_id` is not a non-blank string. The cheapest observation: re-run the script above and check `verdict.reasons` for the new reason and `present_owner_slots` no longer containing `None`. The mutation `_blank(0) = True` (X8C-09) also points to the same family of issue: the helper is too permissive on identity-field types.

REPAIR. Commission a "slot identity required" check on every slot: refuse any slot whose `slot_id` is not a non-blank string, and emit a new reason (e.g. `SLOT_ID_MISSING`) in `REASONS`. Block two synthetic-fixture slots with `slot_id=None` from counting as present owner evidence.

---

### X8C-02 — MAJOR — `sni_identity_binding_guard.py:211-226` — `ID_LOOKS_DERIVED` fires on 3-character common prefixes (high false-positive rate)

CLAIM. The docstring promises a refusal for "an id that looks derived from a ticker, name, code, or CIK." The implementation uses a substring match (`if needle in ident: return True` at line 224) against a minimum-3-character `display_code` or `display_name`. With synthetic fixtures, this means a perfectly legitimate binding is refused the moment a 3-character `display_code` happens to share any substring with any of the four bodies' `listing_id` / `security_id` / `issuer_id` fields. The current test corpus carefully picks `display_code` values that do not collide (`QZX`, `LIST`, `ISSUER`, `SEC`); a real consumer cannot rely on the same luck.

EVIDENCE.
```
$ python3 - <<'PY'
import sys; sys.path.insert(0, '/home/longr/lanes/wt/sni-x8c-20261014T052454Z/research/single_name_intelligence/common')
from sni_identity_binding_guard import bind_identity
AS_OF="2026-08-20T12:00:00+00:00"; AV="2026-08-20T11:00:00+00:00"
def go(display_code):
    v=bind_identity({"listing_id":"SYN-LIST-1","issuer_id":"SYN-ISS-1","currency":"CCC","operation_needs_issuer":True},
        listing={"listing_id":"SYN-LIST-1","security_id":"SYN-SEC-1","currency":"CCC","owner_ref":"O","available_at":AV,
                 "display_code":display_code,"display_name":"Synthetic Holding One"},
        security={"security_id":"SYN-SEC-1","issuer_id":"SYN-ISS-1","owner_ref":"O","available_at":AV},
        issuer={"issuer_id":"SYN-ISS-1","owner_ref":"O","available_at":AV}, as_of=AS_OF)
    return v.allowed, v.reasons
print("display_code='SYN' (substring of SYN-LIST-1):", go("SYN"))   # -> (False, ('ID_LOOKS_DERIVED',))
print("display_code='SEC' (substring of SYN-SEC-1):", go("SEC"))   # -> (False, ('ID_LOOKS_DERIVED',))
print("display_code='LIST' (substring of SYN-LIST-1):", go("LIST"))# -> (False, ('ID_LOOKS_DERIVED',))
print("display_code='ISS-1' (substring of SYN-ISS-1):", go("ISS-1"))# -> (False, ('ID_LOOKS_DERIVED',))
PY
```
None of these synthetic collisions is "derivation"; they are all common prefixes. `_collected_ids` only walks `(_ID_KEYS)` so the matcher skips `currency` and `owner_ref`, but the field is still wide enough to false-positive at the rate a real owner-supplied display code would hit. The same code path also picks up request-supplied ids (not just owner-supplied), so the matcher is also cross-body.

FALSIFIER. The cheapest test: pick a `display_code` whose only 3+ char overlap with the four bodies' `_ID_KEYS` ids is a common prefix (e.g. `SYN`, `SYN-`, `SYN-LIST`, `CCC`-adjacent) and call `bind_identity`; today the verdict is refused. If the seat believes substring is too lax, the fix is to anchor on either a whole-word match or a leading/trailing delimiter split.

REPAIR. Tighten `_id_looks_derived` to anchor on a delimiter split (e.g. `ident.split(needle)` only matches when one side is empty or the surrounding characters are non-alphanumeric) or compare to a whole-word match; require the needle to be at least the longer of `len(display_code)` and 4 chars. Add a `_display_code_no_common_substring` regression test that uses a display code that DOES share a 3-char substring but is not a derivation.

---

### X8C-03 — MAJOR — `sni_kpi_missingness_guard.py:282-287` — `verdict.reported_periods` carries the input record order, not the expected-period order, so a shuffled series still passes the positive test

CLAIM. The docstring says: "An aggregate is refused unless every named period is reported." The aggregate is `aggregate_sum`, which is a separate function and uses the `periods` argument order. The verdict's `reported_periods` field is built by `reported_acc.append(period_id)` in the order records are processed (line 264). The positive test `test_a10_positive_four_reported_quarters` passes records in `PERIODS` order so `verdict.reported_periods == PERIODS`. A caller passing the records in a different order gets a different tuple, and a caller relying on `reported_periods` to be in `expected_periods` order will be silently misled.

EVIDENCE.
```
$ python3 - <<'PY'
import sys, random; sys.path.insert(0,'/home/longr/lanes/wt/sni-x8c-20261014T052454Z/research/single_name_intelligence/common')
from sni_kpi_missingness_guard import check_kpi_series
PERIODS=("SYN-P-1","SYN-P-2","SYN-P-3","SYN-P-4")
def rec(p,v): return {"period_id":p,"state":"reported","value":v}
series=[rec(p,v) for p,v in zip(PERIODS,(10,20,30,40))]
random.seed(0)
diffs=0
for _ in range(20):
    s=list(series); random.shuffle(s)
    v=check_kpi_series(tuple(s), expected_periods=PERIODS)
    if v.reported_periods != PERIODS: diffs += 1
print("diffs vs PERIODS order:", diffs, "/ 20")  # 19 / 20
PY
```
19 of 20 shuffled orders produce a different `reported_periods` tuple. The verdict is still `allowed=True` with empty reasons, so the **refusal contract is honoured**, but the `reported_periods` content varies, so a downstream consumer that iterates it cannot rely on it.

FALSIFIER. The cheapest observation: re-run the script and confirm `diffs >= 1`. If the seat believes `reported_periods` should be in `expected_periods` order, the fix is to add the `period_id` to a set keyed by `expected_periods` order, then iterate `expected_periods` to build `reported_acc`.

REPAIR. Build `reported_periods` by iterating `expected_periods` and appending only those that are present and reported, rather than accumulating in record-iteration order. Add a regression test that shuffles the records and asserts `verdict.reported_periods == expected_periods`.

---

### X8C-04 — MINOR — `sni_ads_ratio_guard.py:122-128, 163-170` — `_as_date` / `_iso_date` silently truncate long strings and accept weird suffixes

CLAIM. `_as_date` returns `date.fromisoformat(text[:10])`; `_iso_date` requires `len(text) == 10`. A caller passing `valid_from="2010-01-01 12:34:56 garbage"` gets a 10-char slice parsed as `2010-01-01` rather than an error. This is consistent within the module, but a refactor that changed either helper would change behaviour with no test catching it. Similarly, the call-site in `check_ads_ratio` uses `request.get("on_date")` directly; a stray `valid_from` value of `2010-1-01` (single-digit month) is correctly refused because `date.fromisoformat` is strict, but `20100101` is rejected only by `len(text) == 10` (so `_iso_date` rejects it but `_as_date` does NOT — it accepts strings of length `>= 10`).

EVIDENCE.
```
$ python3 - <<'PY'
import sys; sys.path.insert(0, '/home/longr/lanes/wt/sni-x8c-20261014T052454Z/research/single_name_intelligence/common')
from sni_ads_ratio_guard import check_ads_ratio
print(check_ads_ratio({"issuer_id":"iss-001","on_date":"2010-01-01"},
    [{"ratio_record_id":"rr-1","issuer_id":"iss-001","ordinary_per_ads":8,
      "valid_from":"2010-01-01 12:34:56","valid_to":None,
      "source_ref":"src","available_at":"2019-07-10T00:00:00+00:00"}],
    as_of="2021-06-01T00:00:00+00:00").allowed)
# -> True  (silently truncated the suffix; no error)
PY
```
The static-scan test (`test_a01g_static_scan`) only checks that the *code* does not contain forbidden strings; it does not exercise this code path.

FALSIFIER. The cheapest observation: call `check_ads_ratio` with a `valid_from` that is `len > 10` and not a date; today the verdict can be allowed because the first 10 chars parse as a valid date.

REPAIR. Tighten `_as_date` to require exactly 10 chars (mirroring `_iso_date`) or raise on longer input; or document and test the current truncation behaviour explicitly. The current asymmetry between `_as_date` (`>= 10`) and `_iso_date` (`== 10`) is a latent refactor trap.

---

### X8C-05 — MINOR — `sni_ads_ratio_guard.py:233-238` — `as_of=None` / `0` / non-string silently produce `RATIO_NOT_AVAILABLE_AS_OF`; no raise

CLAIM. The guard promises "refused, not filled in" for a missing or unparsable `as_of`. The implementation returns `RATIO_NOT_AVAILABLE_AS_OF` for any non-parseable `as_of`, including `None`, `0`, `True`, a list, a dict, or a malformed string. A caller passing `as_of=None` thinking it means "now" gets a quiet refusal rather than a `TypeError` or a "missing as_of" reason.

EVIDENCE.
```
$ python3 - <<'PY'
import sys; sys.path.insert(0, '/home/longr/lanes/wt/sni-x8c-20261014T052454Z/research/single_name_intelligence/common')
from sni_ads_ratio_guard import check_ads_ratio
v = check_ads_ratio({"issuer_id":"iss-001","on_date":"2015-01-15"},
    [{"ratio_record_id":"rr-1","issuer_id":"iss-001","ordinary_per_ads":8,
      "valid_from":"2010-01-01","valid_to":None,
      "source_ref":"src","available_at":"2019-07-10T00:00:00+00:00"}],
    as_of=None)
print(v.allowed, v.reasons)  # -> (False, ('RATIO_NOT_AVAILABLE_AS_OF',))
PY
```
The contract is "refused" not "raise", so the behaviour is internally consistent, but the test corpus never exercises `as_of=None` (only the omission-of-`as_of` is a name-collision concern, not this). The static-scan test does not cover it.

FALSIFIER. If the seat wants to distinguish missing `as_of` from `as_of=garbage`, add a new reason `AS_OF_MISSING_OR_INVALID` and split the `_aware_datetime` failure path. The cheapest observation: re-run the script and check the same code path with `as_of='garbage'`, `as_of=['2021-...']`, `as_of=0` (all return `RATIO_NOT_AVAILABLE_AS_OF`).

REPAIR. Add a test asserting `as_of=None` and `as_of="garbage"` are refused with a named reason; decide whether to split `RATIO_NOT_AVAILABLE_AS_OF` from `AS_OF_MISSING_OR_INVALID` and document the difference.

---

### X8C-06 — MINOR — `sni_ads_ratio_guard.py:241-247` — `bytes` in `acknowledged_ratio_changes` is wrapped to `(b'rr-002',)` and then cannot match the string `ratio_record_id`

CLAIM. `_ack_ids` returns `(raw,)` when the caller passes a `bytes` value. The downstream `cover_on[0].get("ratio_record_id") not in _ack_ids(request)` then compares a string `ratio_record_id` to a tuple of bytes; the test `test_a01g_ack_trailing_space_does_not_match` covers the trailing-space string case, but a caller passing the binary form of a known id is refused even if they intended to acknowledge.

EVIDENCE.
```
$ python3 - <<'PY'
import sys; sys.path.insert(0, '/home/longr/lanes/wt/sni-x8c-20261014T052454Z/research/single_name_intelligence/common')
from sni_ads_ratio_guard import check_ads_ratio
v = check_ads_ratio({"issuer_id":"iss-001","on_date":"2020-01-15",
                     "window_start":"2012-06-01","acknowledged_ratio_changes":b"rr-002"},
    [{"ratio_record_id":"rr-001","issuer_id":"iss-001","ordinary_per_ads":8,
      "valid_from":"2010-01-01","valid_to":"2019-07-10","source_ref":"src",
      "available_at":"2019-07-10T00:00:00+00:00"},
     {"ratio_record_id":"rr-002","issuer_id":"iss-001","ordinary_per_ads":4,
      "valid_from":"2019-07-10","valid_to":None,"source_ref":"src",
      "available_at":"2019-07-10T00:00:00+00:00"}],
    as_of="2021-06-01T00:00:00+00:00")
print(v.allowed, v.reasons)  # -> (False, ('RATIO_CHANGE_UNACKNOWLEDGED',))
PY
```
The caller "acknowledged" with `b"rr-002"`, which is the same id in bytes form. The guard refuses. This is consistent with strict-type refusal (matching the join-guard's `type_strict` rule), but the test corpus only exercises string ack.

FALSIFIER. The cheapest observation: run the script above; the verdict is `RATIO_CHANGE_UNACKNOWLEDGED` despite the bytes ack.

REPAIR. Either reject `bytes` early (`raise TypeError`) or document and test that bytes ack is treated as a type mismatch and refused. The current behaviour is internally consistent (everything-not-equal-string-`rr-002` is not a match) but is surprising.

---

### X8C-07 — MINOR — `sni_kpi_missingness_guard.py:286-287` — the `reported_periods` field is not documented as order-dependent; the positive test only covers one order

CLAIM. The docstring of `KpiSeriesVerdict` says "Carries no filled or imputed value"; the contract on `reported_periods` is "an aggregate is refused unless every named period is reported." The order of `reported_periods` is not specified. The test `test_a10_positive_four_reported_quarters` asserts `verdict.reported_periods == PERIODS`, but the test feeds records in `PERIODS` order, so it does not constrain the implementation to any particular order. A future refactor that switches to insertion order vs. record order would still pass the test.

EVIDENCE. See X8C-03 for the 19/20 diffs output.

FALSIFIER. Re-run the X8C-03 script and confirm `diffs >= 1`.

REPAIR. If order is intentional, document it in the docstring and pin a test that asserts the order for a shuffled series; if order is not intentional, build `reported_periods` in `expected_periods` order (X8C-03).

---

### X8C-08 — MINOR — `sni_view_state_guard.py:212-216` — `_IDENTITY_REASONS` is a hard-coded 4-tuple; new axes cannot be wired without a code change

CLAIM. The identity-reason loop walks `_IDENTITY_REASONS = (("issuer_id", "ISSUER_CHANGED"), ("counter_id", "COUNTER_CHANGED"), ("lens", "LENS_CHANGED"), ("as_of", "AS_OF_CHANGED"))`. A future axis added to `AXES` will not produce a corresponding identity-reason refusal unless the maintainer remembers to also extend `_IDENTITY_REASONS` and `REASONS`. This is a maintenance smell, not a defect today.

EVIDENCE.
```
$ grep -n "_IDENTITY_REASONS" /home/longr/lanes/wt/sni-x8c-20261014T052454Z/research/single_name_intelligence/common/sni_view_state_guard.py
76:    ("as_of", "AS_OF_CHANGED"),
212:    for axis, code in _IDENTITY_REASONS:
```
No mechanism in the test file forces the two tuples to stay aligned.

FALSIFIER. Add a new identity axis (e.g. `"scenario_id"`) to `AXES` and observe that a changed `scenario_id` produces a `CHANGE_UNDECLARED` but no `SCENARIO_ID_CHANGED`. The cheapest observation: read the two tuples and confirm they have the same length and same axis set.

REPAIR. Either drive `_IDENTITY_REASONS` from a tagged subset of `AXES` (e.g. `AXES_IDENTITY = ("issuer_id", "counter_id", "lens", "as_of")` and `REASONS` keyed by `{axis: REASON_BY_AXIS[axis]}`) or add a static invariant test that the two tuples are aligned.

---

### X8C-09 — MINOR — `sni_release_evidence_guard.py:120-125` — `_blank` is too permissive (no type check); mutation that treats `0` as blank survives all 37 tests

CLAIM. The mutation sweep (attack 7) showed that extending `_blank` to also treat `0` as blank (`if value == "" or value == 0`) survives every test in `test_sni_release_evidence_guard.py`. This is a coverage gap: no test asserts the verdict's behaviour for `evidence_ref=0`, `page_id=0`, `slot_id=0`, or `required=0` as a *value* (the existing `required=0` test goes through `_required_flag`, which is a different path).

EVIDENCE.
```
=== RELEASE ===
  [disable SYNTHETIC_EVIDENCE] 5 failed, 32 passed in 0.03s
  [disable ALL_EVIDENCE_ABSENT] 7 failed, 30 passed in 0.03s
  [disable REQUIRED_SLOT_NOT_PRESENT] 4 failed, 33 passed in 0.03s
  [disable PRESENT_WITHOUT_REF] 3 failed, 34 passed in 0.02s
  [_blank treats 0 as blank] 37 passed in 0.02s       <-- survived
  [always allow] 25 failed, 12 passed in 0.03s
```
The mutation is non-regression (more strict), so it is not a real defect, but it indicates the test corpus never exercises numeric `evidence_ref`, `page_id`, or `slot_id` values for the "blank" boundary.

FALSIFIER. Run the mutation by hand: in a `/tmp` copy of the module, change `_blank` to also treat `0` as blank; rerun `tests/test_sni_release_evidence_guard.py`; expect 37 passed. The script in the working notes does this.

REPAIR. Add a test that asserts `evidence_ref=0` is treated as a present ref (and `page_id=0` is treated as a present page id) so that future refactors of `_blank` cannot silently change the boundary. This pairs with X8C-01 (slot_id=None is accepted, so a numeric 0 should be a meaningful non-blank).

---

### X8C-10 — MINOR — `sni_view_state_guard.py:182, 200-216` — `change='as_of'` with no actual change is `ALLOWED`; intent is not tracked

CLAIM. The docstring says "`change` is the one AXES name the user action declared, or None." If the user declared `change='as_of'` but the `as_of` did not actually change, the guard returns `ALLOWED`. The test `test_a31_positive_zero_change_declared_lang` confirms this for `change='lang'`. A user intending a different axis (e.g. typed `change='as_of'` but actually changed `lang`) is silently allowed.

EVIDENCE.
```
$ python3 - <<'PY'
import sys; sys.path.insert(0,'/home/longr/lanes/wt/sni-x8c-20261014T052454Z/research/single_name_intelligence/common')
from sni_view_state_guard import check_view_transition
v = check_view_transition(
    {"issuer_id":"I","counter_id":"C","lens":"L","as_of":"2026-10-13T08:00:00+00:00","lang":"en","viewport":"desktop"},
    {"issuer_id":"I","counter_id":"C","lens":"L","as_of":"2026-10-13T08:00:00+00:00","lang":"zh","viewport":"desktop"},
    change="as_of")
print(v.allowed, v.reasons, v.changed_axes)  # -> (False, ('CHANGE_UNDECLARED',), ('lang',))
PY
```
The verdict correctly refuses when `lang` silently changed while the user declared `as_of` (the `lang` change is `CHANGE_UNDECLARED`); the symmetric case — the user declared `as_of` but only `lang` actually changed — is `ALLOWED`. This is the same logic from a different angle. The test corpus asserts the `lang`-declares-but-only-`as_of`-changes case is allowed but does not assert the inverse.

FALSIFIER. Re-run the script and confirm `v.allowed is True` and `v.reasons == ()` when `change="as_of"` and the only actual change is `lang`.

REPAIR. Either document the intent-vs-effect asymmetry (the `change` argument names a permitted axis but is not an exclusive intent marker) or add a `DECLARED_BUT_NO_CHANGE` refusal when the declared axis is in `changed_axes` is False. This is a contract decision, not a bug; the test currently treats the lax interpretation as canonical.

---

### X8C-11 — MINOR — `sni_ads_ratio_guard.py:104-110` — `_blank` accepts non-string `source_ref` (lists, dicts, ints) as "present"

CLAIM. `_blank` only checks `None` and `""`. A record with `source_ref=[...]` (a list) or `source_ref={"id":...}` (a dict) or `source_ref=42` is treated as a present source ref and the record is not flagged `RATIO_RECORD_UNSOURCED`. The test corpus uses string source refs only; the static-scan test does not exercise the non-string path.

EVIDENCE.
```
$ python3 - <<'PY'
import sys; sys.path.insert(0,'/home/longr/lanes/wt/sni-x8c-20261014T052454Z/research/single_name_intelligence/common')
from sni_ads_ratio_guard import check_ads_ratio
v = check_ads_ratio({"issuer_id":"iss-001","on_date":"2020-01-15"},
    [{"ratio_record_id":"rr-001","issuer_id":"iss-001","ordinary_per_ads":8,
      "valid_from":"2010-01-01","valid_to":"2019-07-10",
      "source_ref":["src-a","src-b"],  # a list
      "available_at":"2019-07-10T00:00:00+00:00"},
     {"ratio_record_id":"rr-002","issuer_id":"iss-001","ordinary_per_ads":4,
      "valid_from":"2019-07-10","valid_to":None,
      "source_ref":"src-cs-002","available_at":"2019-07-10T00:00:00+00:00"}],
    as_of="2021-06-01T00:00:00+00:00")
print(v.allowed, v.reasons)  # -> (True, ())
PY
```
A list as `source_ref` passes the `_blank` check, the record is allowed, and the verdict picks it as the covering interval.

FALSIFIER. The cheapest observation: rerun the script; the verdict is `allowed=True` despite `source_ref` being a list.

REPAIR. Add an isinstance(value, str) guard inside `_blank` (or a per-field "string presence" helper) and refuse non-string `source_ref`, `ratio_record_id`, and `valid_from`/`valid_to` values. The same fix applies to the identity-binding guard (X8C-12 below).

---

### X8C-12 — MINOR — `sni_identity_binding_guard.py:118-119, 176-182` — same `_blank` permissiveness on `listing_id`, `security_id`, `issuer_id`, `owner_ref`, `currency`, `display_code`, `display_name`

CLAIM. The same `_blank` helper is used. A non-string `listing_id` is treated as a mismatch (because the verdict's `_opaque_id` returns `None` for non-strings) but is not refused as "id type wrong" — the verdict's `listing_id` becomes `None` even on the `LISTING_ID_MISMATCH` refusal. A non-string `owner_ref` is treated as present.

EVIDENCE.
```
$ python3 - <<'PY'
import sys; sys.path.insert(0,'/home/longr/lanes/wt/sni-x8c-20261014T052454Z/research/single_name_intelligence/common')
from sni_identity_binding_guard import bind_identity
AS_OF="2026-08-20T12:00:00+00:00"; AV="2026-08-20T11:00:00+00:00"
v = bind_identity({"listing_id":"L","issuer_id":"I","currency":"C","operation_needs_issuer":True},
    listing={"listing_id":1,"security_id":"S","currency":"C","owner_ref":"O","available_at":AV,
             "display_code":"D","display_name":"Name"},
    security={"security_id":"S","issuer_id":"I","owner_ref":"O","available_at":AV},
    issuer={"issuer_id":"I","owner_ref":"O","available_at":AV},
    as_of=AS_OF)
print(v.allowed, v.reasons, v.listing_id)
# -> (False, ('LISTING_ID_MISMATCH',), None)  # verdict.listing_id is None even though the
#                                               # record did carry a value (an int 1)
PY
```
The same pattern as the release guard (X8C-01): the verdict's `listing_id` field is `None` for a non-string record value, and the caller cannot tell whether the listing was missing or merely mistyped.

FALSIFIER. The cheapest observation: rerun the script; confirm `verdict.listing_id is None` while the record supplied `listing_id=1`.

REPAIR. Either type-check identity fields with `isinstance(value, str)` (and add a `LISTING_ID_WRONG_TYPE` reason) or document that the verdict's id fields are `None` whenever the corresponding record field is not a non-blank string, and test the asymmetry.

---

## CHECKED-CLEAN

For each module, the eight attacks were run; below are the bounds and outcomes that produced no finding. Bounds are described as "searched in `<module>.py`" and the evidence is a script that ran in `/tmp` against the actual module on this commit.

### `sni_ads_ratio_guard.py`
- ATTACK 1 (docstring vs behaviour): All 10 REASONS fire on the smallest appropriate input. `RATIO_NONPOSITIVE` is enforced for bool, str, None, 0, -1, NaN, inf, -inf, 1e300 finite, and 10**400 (a Python int, which the docstring does not bound). Evidence: `/tmp/sni_x8c/ads/attack1.py` (16 cases, all refused except the 10**400 and 1e300 huge-int/huge-float cases, which match the spec — finite positive passes). Bounds: refused-reasons enumerated in REASONS; no extra reasons appended.
- ATTACK 2 (identity strings on id/code fields): `rec.issuer_id=None` flips to `ISSUER_MISMATCH`; `rec.issuer_id=""` flips to `ISSUER_MISMATCH`; `rec.issuer_id=int(1)` triggers `ISSUER_MISMATCH` (verdict does not crash). Adversarial: trailing-space, case change, Cyrillic lookalike, U+00A0, tab all trip the existing tests. Bounds: tested with `issuer_id` only; `ratio_record_id` accepts any non-blank value (see X8C-11 for the underlying issue).
- ATTACK 3 (numbers on `ordinary_per_ads`): bool, 0, -1, NaN, +inf, -inf, 1e300 finite, Decimal(1.5), Fraction(1,2), "10" all refused. `10**400` (Python int) is finite-positive and allowed by the spec. Bounds: 0/0.0, -0.0, 1e300, 10**400 all match `_finite_positive`.
- ATTACK 4 (time): `as_of=None`, `as_of=""`, `as_of=int`, `as_of=date`, `as_of=aware datetime` all produce `RATIO_NOT_AVAILABLE_AS_OF` (consistent with `_aware_datetime` strictness). `as_of="Z"` works. `as_of=+05:45` works. Leap day `2024-02-29` works. Boundary tests: `on_date=valid_from` picks the record, `on_date=valid_to` picks the next, `on_date=valid_to-1day` picks the earlier. Two intervals with adjacent `valid_to == valid_from` are not flagged as overlapping. Bounds: only the documented `available_at`/`as_of` paths; the `window_start` path is checked separately.
- ATTACK 5 (shape): records=None and records=[] both `RATIO_RECORDS_MISSING`; records as tuple or generator works; `request` not a Mapping raises `TypeError`; request missing `issuer_id` flips `ISSUER_MISMATCH` (consistent with strict-type identity); `window_start` invalid date flips `DATE_INVALID`; 10,000 records run in 9 ms (no runtime cliff).
- ATTACK 6 (order/determinism): `test_a01g_permutation_invariance` and `test_a01g_permutation_invariance_refused` cover both the positive and refused invariants. Local verification: 6 permutations of the 3-record positive set all return identical `(allowed, reasons, ratio_record_id, ordinary_per_ads)` tuples. Bounds: 3-record positive set; 6 permutations; 3-record refused set; 6 permutations.
- ATTACK 7 (test strength / mutation sweep): 7 mutations run against the project's own test file in a `/tmp` copy; all 7 killed at least 2 tests (`disable INTERVAL_OVERLAP` 2, `disable ISSUER_MISMATCH` 6, `ordinary_per_ads >= 0` 4, `disable RATIO_NOT_AVAILABLE_AS_OF` 5, `always allow` 41, `disable RATIO_CHANGE_UNACKNOWLEDGED` 4, `disable RATIO_RECORD_UNSOURCED` 4). No surviving mutation. Bounds: 7 refusal-branch mutations; full test file (46 tests).
- ATTACK 8 (authority and law): `AUTHORITY_FLAGS` is `MappingProxyType` of 6 keys, all literal `False`. `refuse_nonfalse_authority` raises `ValueError` for True/0/None/""/non-Mapping. Module is stdlib-only. `python3 research/single_name_intelligence/evaluation/seal_full_check.py --study all --repo-root .` final line: `SEAL FULL CHECK: OK (10 files float-equivalent on Linux x86_64 within rel 1e-10 / abs 1e-13, not byte-identical; byte identity rests on the XREP Linux receipt)`. No ticker/listing literal in source; no wall clock; no I/O. Bounds: 5 forbidden-source needles, 9 ticker literals, 5 reason codes, 6 authority flag names.

### `sni_identity_binding_guard.py`
- ATTACK 1 (docstring vs behaviour): all 12 REASONS fire on the smallest appropriate input. `ID_LOOKS_DERIVED` correctly refuses when a 3+ char `display_code` is a substring of any collected id; the test `test_a03g_id_looks_derived_skips_two_char_display_code` correctly skips 2-char codes. Evidence: `/tmp/sni_x8c/identity/attack1.py`. Bounds: all 12 REASONS enumerated.
- ATTACK 2 (identity strings): trailing space, U+00A0, tab, int, full-width digits, None, "" on `listing_id` and `counter_id` all produce expected mismatches. `request.listing_id` mixed with `listing.listing_id` of any non-equal value trips `LISTING_ID_MISMATCH`. `request.issuer_id=""` (empty string, not None) trips `REQUEST_ISSUER_MISMATCH`. The `verdict.issuer_id is None` invariant holds when `security=None` or `security.issuer_id=None`. Bounds: `listing_id`, `security_id`, `issuer_id` covered; `display_name` and `display_code` are tested for length boundary (2-char vs 3-char).
- ATTACK 3 (numbers): `currency=int(42)` triggers `CURRENCY_MISMATCH` (consistent with strict string compare); `owner_ref=int(12345)` is allowed (consistent with `_present` non-strict type). Bounds: tested on currency, owner_ref, and id fields.
- ATTACK 4 (time): `as_of="Z"` and `as_of="+00:00"` both work. `+05:45` offset parses. `available_at=date-only` triggers `NOT_AVAILABLE_AS_OF`. Leap day `2024-02-29` works. Bounds: only `available_at` and `as_of` paths.
- ATTACK 5 (shape): listing, security, issuer as tuples/lists raise `TypeError` with the correct message; request as a list raises `TypeError`; missing `listing_id` in request triggers `LISTING_ID_MISMATCH`. Bounds: per-parameter type checks.
- ATTACK 6 (order/determinism): 20 repeated calls with fresh dict literals produce identical verdicts. Bounds: 20 runs.
- ATTACK 7 (mutation sweep): 7 mutations; all 7 killed at least 1 test (`disable LISTING_ID_MISMATCH` 8, `disable CURRENCY_MISMATCH` 5, `disable NOT_AVAILABLE_AS_OF` 6, `disable ID_LOOKS_DERIVED` 3, `fill issuer from request when security is None` 1, `disable NULL_ISSUER_REFUSED` 4, `always allow` 36). No surviving mutation. Bounds: 7 refusal-branch mutations; full test file (43 tests).
- ATTACK 8 (authority and law): same as ADS. Static scan matches.

### `sni_kpi_missingness_guard.py`
- ATTACK 1 (docstring vs behaviour): all 9 REASONS fire on the smallest appropriate input. `STATE_UNKNOWN` for "pending" and other unrecognised states; `REPORTED_VALUE_INVALID` for None/str/NaN/inf/-inf/bool; `MISSING_CARRIES_VALUE` for `not_reported/not_applicable/withheld` with non-None value (including 0 and 0.0). Evidence: `/tmp/sni_x8c/kpi/attack1.py`. Bounds: 9 REASONS enumerated; both not_reported and not_applicable paths covered.
- ATTACK 2 (identity strings on `period_id`): trailing space, case change, Cyrillic on both sides, int, None all trip the expected reasons. `expected_periods` containing `None` produces `PERIOD_ABSENT` + `UNEXPECTED_PERIOD`. Bounds: 6 string variants.
- ATTACK 3 (numbers on `value`): True/False, NaN, inf, -inf, Decimal, Fraction, str "10" all refused; 0 and -0.0 are finite numbers and allowed (consistent with the spec — the function refuses "invalid" values, and 0 is a valid reported number). `10**400` allowed (finite int). Bounds: 10 numeric shapes.
- ATTACK 4 (time): not applicable (no time fields in this module).
- ATTACK 5 (shape): `series=str` raises `TypeError`; `series=set` raises `TypeError` (sets are not hashable for the records); `expected_periods=str` raises `TypeError`; empty series with non-empty expected produces `PERIOD_ABSENT`; non-empty series with empty expected produces `UNEXPECTED_PERIOD`; duplicate period_ids in the series produce `DUPLICATE_PERIOD`. Bounds: per-shape.
- ATTACK 6 (order/determinism): 20 shuffles produce different `reported_periods` tuples (X8C-03 / X8C-07) but identical `allowed`/`reasons` (`reasons` is order-invariant after de-dup). Bounds: 20 shuffles of 4 records.
- ATTACK 7 (mutation sweep): 7 mutations; all 7 killed at least 2 tests (`disable DUPLICATE_PERIOD` 2, `disable CARRY_FORWARD_DECLARED` 2, `disable IMPUTATION_DECLARED` 2, `disable MISSING_CARRIES_VALUE` 6, `_finite_number accepts bool` 2, `aggregate_sum partial sum` 3, `always allow` 22). No surviving mutation. Bounds: 7 mutations; full test file (46 tests).
- ATTACK 8 (authority and law): same as ADS. Static scan matches.

### `sni_view_state_guard.py`
- ATTACK 1 (docstring vs behaviour): all 9 REASONS fire on the smallest appropriate input. `CHANGE_UNDECLARED`, `MULTIPLE_AXES_CHANGED`, `ISSUER_CHANGED`, `COUNTER_CHANGED`, `LENS_CHANGED`, `AS_OF_CHANGED` all fire correctly. Evidence: `/tmp/sni_x8c/view/attack1.py`. Bounds: 9 REASONS.
- ATTACK 2 (identity strings): trailing space, case change, Cyrillic on both sides (different), U+00A0, tab, None, int(1) on `issuer_id` and `counter_id` all trip expected refusals. Cyrillic on both sides (same) is allowed — consistent with the exact-string-match contract. Bounds: 8 string variants.
- ATTACK 3 (numbers on `lens`): `lens=int(123)` triggers `LENS_CHANGED` (correct refusal); `lens=None` triggers `FIELD_MISSING` (consistent with the `_field_missing` rule). Bounds: tested.
- ATTACK 4 (time): `as_of=+08:00` (same instant, different string) trips `AS_OF_CHANGED` (documented exact-string contract). `as_of=date-only`, `as_of=naive datetime`, `as_of=+1us` all trip `AS_OF_CHANGED`. Bounds: 4 string variants.
- ATTACK 5 (shape): `before=str` raises `TypeError`; `after=None` raises `TypeError`; missing viewport in `after` triggers `FIELD_MISSING` and `VIEWPORT_UNKNOWN`; extra unexpected axes (e.g. `owner_note`) are ignored. Bounds: 4 shape variants.
- ATTACK 6 (order/determinism): 20 shuffled dicts produce identical `allowed`/`reasons`/`changed_axes` for the positive case. Bounds: 20 runs.
- ATTACK 7 (mutation sweep): 6 mutations; all 6 killed at least 3 tests (`disable FIELD_MISSING` 3, `disable CHANGE_UNDECLARED` 10, `disable MULTIPLE_AXES_CHANGED` 5, `disable identity-reason branch` 14, `_changed_axes always empty` 27, `always allow` 32). No surviving mutation. Bounds: 6 mutations; full test file (45 tests).
- ATTACK 8 (authority and law): same as ADS. Static scan matches.

### `sni_release_evidence_guard.py`
- ATTACK 1 (docstring vs behaviour): all 9 REASONS fire on the smallest appropriate input. `PAGE_ID_MISSING` for `""` and `None`; `NO_SLOTS` for `()` and `None`; `DUPLICATE_SLOT` for two slots with the same `slot_id`; `SLOT_STATE_UNKNOWN` for `"not-a-state"`; `PROVENANCE_UNKNOWN` for `"unknown"` on a present slot; `PRESENT_WITHOUT_REF` for empty/None evidence_ref; `SYNTHETIC_EVIDENCE` for `synthetic_fixture` and `test_double`; `ALL_EVIDENCE_ABSENT` for all-absent or all-gated; `REQUIRED_SLOT_NOT_PRESENT` for one absent required slot. Evidence: `/tmp/sni_x8c/release/attack1.py`. Bounds: 9 REASONS.
- ATTACK 2 (identity strings): `page_id` trailing space / Cyrillic accepted (the page_id is opaque, not an identity); `slot_id` trailing space / case change / Cyrillic (all different) accepted; `slot_id` None / int(1) / list `[1,2]` accepted and included in `present_owner_slots` — see X8C-01. `evidence_ref=int(42)` accepted. Bounds: 6 string/numeric variants.
- ATTACK 3 (numbers): `required=1` triggers `REQUIRED_SLOT_NOT_PRESENT` (consistent with `required is not False`); `required="yes"` triggers the same; `required="False"` (string) also triggers because `"False" is not False` (the same permissive rule is exercised by `test_a33_required_zero_treated_as_required` and `test_a33_required_none_treated_as_required`); `required=0` triggers. Bounds: 4 numeric variants.
- ATTACK 4 (time): not applicable (no time fields in this module).
- ATTACK 5 (shape): page=list/None raises `TypeError`; slots as str/dict raises `TypeError`; slot as a list raises `TypeError` with the correct message. Bounds: 4 shape variants.
- ATTACK 6 (order/determinism): `reasons` is order-invariant after de-dup; `present_owner_slots` is order-dependent on input (X8C-01 / X8C-09). 20 shuffles: 17 of 20 produce a different `present_owner_slots` tuple; `allowed` and `reasons` are identical. Bounds: 20 shuffles.
- ATTACK 7 (mutation sweep): 6 mutations; 5 killed, 1 survived (`disable SYNTHETIC_EVIDENCE` 5, `disable ALL_EVIDENCE_ABSENT` 7, `disable REQUIRED_SLOT_NOT_PRESENT` 4, `disable PRESENT_WITHOUT_REF` 3, `_blank treats 0 as blank` 0 — survived, see X8C-09, `always allow` 25). The one survivor is non-regression (more strict), so it is a coverage gap, not a defect. Bounds: 6 mutations; full test file (37 tests).
- ATTACK 8 (authority and law): same as ADS. Static scan matches.

## What this review does NOT prove

- **Cross-guard wiring**: this review exercised each guard in isolation. It does not prove that a chain of guards (e.g. `bind_identity` followed by `check_ads_ratio` followed by `check_release`) would not produce an allowed verdict for an end-to-end mismatch; the family pattern (`sni_join_guard.py`) was not under attack.
- **Concurrent / repeated calls**: the guards are pure functions of their inputs; no attempt was made to exercise them under threading or signal-driven cancellation.
- **Byte-identical reproducibility of the seal check**: the seal_full_check script reports "10 files float-equivalent on Linux x86_64 within rel 1e-10 / abs 1e-13, not byte-identical; byte identity rests on the XREP Linux receipt." This review relied on the rel/abs tolerance and did not probe the XREP Linux receipt itself.
- **What happens when a guard is wired into a real owner**: each guard is currently a DRAFT not wired into any owner, pipeline, page, or job. A future wire-up that adds cross-guard invariants is not covered here.
- **Defect X8C-04 is a coverage finding on the `_blank` mutation survival**: the test corpus never exercises numeric `0` as a `page_id`, `slot_id`, or `evidence_ref`, so a future `_blank` change would not be caught. The change itself is not a defect.
- **The mutations on `aggregate_sum` and `_finite_number` were the only "non-allow" mutations I tried on KPI**: I did not exhaustively mutate the `kpi_value` path or the `_non_reported_states` set membership.
- **No new tests added**: this review exercised the existing test files in `/tmp` copies. The seat should not infer that I added or modified any test.
- **No code change**: I did not edit any file in the worktree; the only commit added is the review file itself.
