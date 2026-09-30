ROUTE: review
OPERATION: cn-input-receipt-compact-audit-20260924
RECEIVER_MODE: DIRECT_TARGETED. This live delivery assigns this bounded review only.
AUTHORITY: Chairman continuation; Sol owns source/release. Mastermind294b4c00ed668b497edb834be8108f14bc1bee8a compatible Skillpack1.0.1. No other source owner is displaced.
WHY: Existing Opus reviewer profile supplies independent adversarial code judgment; no Fable principal is needed.
ARTIFACT TO ATTACK: Macro PR7860 exact semantic head722910e0028a982956769cc779673b12e7936e59. The full authored code/test diff and existing consumer are embedded below.
REVIEW STANDARD: Can the added helper and serializer return paths preserve only explicitly supplied canonical daily dates, keep absent keys absent, reject invalid types/dates, avoid substituting bucket/clock freshness, and leave legacy eligibility/ranking unchanged? Find concrete bugs, not generic redesign opportunities. Do not audit unrelated upstream validity rules, mutate source, research trading performance, or claim this completes native Theme EntryContext.
METHOD: Review the embedded immutable artifact only. No repository exploration, tools, shell, network, tests, credentials, delegation or watchers are assigned. Return one completed report in this invocation. Independent execution and Git identity verification are explicitly outside this review; parent verifies hashes separately.
EVIDENCE: Parent executed221 integrated passes plus594 cross-market passes/16HK data-dependent skips. Hosted CI35941146078 and fences35941145859 succeeded at this exact head. These are supplied receipts, not reviewer-executed tests.
CONTEXT: Earlier separate review childca9da29e was terminally stopped after repeated max-turn returns; its stop file has now been read and also contains error_max_turns. No usable report or acknowledgement exists. No source writer or watcher was assigned there. This is a newly commissioned smaller review, not a resume, replacement source writer or provider switch.
RETURN: Include pickup and start acknowledgement, then STATUS, RESULT, EVIDENCE, GAPS, DEVIATIONS. PASS is permitted for a correct bounded source repair with explicit production gaps. Return any blocker/major with precise diff/function evidence. Await only the parent's exact-session terminal STOP; do not create unattended continuation.

FULL AUTHORED DIFF
diff --git a/engine/signal_gate.py b/engine/signal_gate.py
index cccf77910f87..f3bee2833f5f 100644
--- a/engine/signal_gate.py
+++ b/engine/signal_gate.py
@@ -668,12 +668,33 @@ def blend_sorted(items: list, base_of, verdict_of, reverse: bool = True, bonus_o
     return sorted(items, key=_score, reverse=reverse)


+def _with_input_receipt(out: dict, verdict: dict) -> dict:
+    """Retain an explicit daily-input date without assigning freshness or validity.
+
+    Legacy receipts keep their key set. Invalid/non-date values stay unknown;
+    the consumer owns exchange-session checks. The analytical bucket is not a
+    fallback, and serialization must never stamp today's date onto old input.
+    """
+    from datetime import date
+
+    if "input_asof" in verdict:
+        value = verdict["input_asof"]
+        out["input_asof"] = None
+        if isinstance(value, str) and len(value) == 10:
+            try:
+                if date.fromisoformat(value).isoformat() == value:
+                    out["input_asof"] = value
+            except ValueError:
+                pass
+    return out
+
+
 def compact(v: dict | None) -> dict:
     """The display-safe verdict subset to attach to a grid card row (drops "result")."""
     if not v:
         return {"eligible": False, "tier": None, "sub": None, "reason": "no signal",
                 "reasons": ["no signal"]}
-    return {k: v.get(k) for k in _VERDICT_KEYS}
+    return _with_input_receipt({k: v.get(k) for k in _VERDICT_KEYS}, v)


 # the SLIM, fully JSON-safe verdict for the "what to buy" boards (Top-setups strip on
@@ -693,7 +714,7 @@ def buy_signal(v: dict | None) -> dict:
         return {"eligible": False, "tier_cascade": None, "htf_s1": False, "htf_s2": False,
                 "young_history": False, "anchor_era": confluence_tiers.ANCHOR_ERA,
                 "sq_anchor_era": signal_quality.ANCHOR_ERA}
-    return {k: v.get(k) for k in _BUY_KEYS}
+    return _with_input_receipt({k: v.get(k) for k in _BUY_KEYS}, v)


 def validity_block(as_of: str | None, emitted_at: str, pair_id: str) -> dict:
diff --git a/tests/test_china_board_rank.py b/tests/test_china_board_rank.py
index c2c32fec1d1f..3fc0e6cf2b06 100644
--- a/tests/test_china_board_rank.py
+++ b/tests/test_china_board_rank.py
@@ -604,3 +604,31 @@ def test_partition_is_disjoint_lossless_and_input_order_invariant():
     assert len({row["ticker"] for row in all_rows}) == len(rows)
     assert all(row["lane"] in names for row in all_rows)
     assert all(row["score_rank"] >= 1 and row["display_rank"] >= 1 for row in all_rows)
+
+
+@pytest.mark.parametrize('serializer_name', ['compact', 'buy_signal'])
+@pytest.mark.parametrize('daily,expected', [(ASOF, True), ('2026-07-28', False),
+                                          ('2026-07-30', False), (None, False)])
+def test_native_signal_daily_receipt_survives_json_to_existing_cn_consumer(serializer_name, daily, expected):
+    import json
+    from engine import signal_gate
+    original = _verdict(asof='2026-07-27', input_asof=daily)
+    signal = json.loads(json.dumps(getattr(signal_gate, serializer_name)(original), allow_nan=False))
+    enriched, = china_board_rank.enrich_and_score_rows(
+        [{**_row('600001.SS'), 'signal': signal}], board_asof=ASOF)
+    assert china_board_rank._signal_is_fresh(enriched) is expected
+    assert enriched['_signal_research'].get('input_asof') == daily
+    assert enriched['signal']['eligible'] == original['eligible']
+    assert enriched['signal']['tier_cascade'] == original['tier_cascade']
+
+
+@pytest.mark.parametrize('serializer_name', ['compact', 'buy_signal'])
+def test_cn_consumer_does_not_treat_bucket_only_receipt_as_current(serializer_name):
+    import json
+    from engine import signal_gate
+    original = _verdict()
+    original.pop('input_asof')
+    signal = json.loads(json.dumps(getattr(signal_gate, serializer_name)(original)))
+    enriched, = china_board_rank.enrich_and_score_rows(
+        [{**_row('600001.SS'), 'signal': signal}], board_asof=ASOF)
+    assert china_board_rank._signal_is_fresh(enriched) is False
diff --git a/tests/test_signal_gate.py b/tests/test_signal_gate.py
index 57757b87af0b..5da80d285f22 100644
--- a/tests/test_signal_gate.py
+++ b/tests/test_signal_gate.py
@@ -391,3 +391,79 @@ class TestEngineErrorIsDistinguishableFromThinHistory:
         v = sg.gate("TEST", self._thin_tape())
         assert v["reason"] == "insufficient history"
         assert v["eligible"] is False
+
+
+@pytest.mark.parametrize('serializer_name', ['compact', 'buy_signal'])
+@pytest.mark.parametrize('input_asof', ['2026-09-22', '2026-09-21', None])
+def test_signal_serialization_preserves_explicit_daily_input_receipt(serializer_name, input_asof):
+    from copy import deepcopy
+    from engine import signal_gate as sg
+    full = {'eligible': True, 'tier_cascade': 'T2', 'ticks': 1,
+            'asof': '2026-09-18', 'input_asof': input_asof}
+    before = deepcopy(full)
+    out = getattr(sg, serializer_name)(full)
+    assert 'input_asof' in out
+    assert out['input_asof'] == input_asof
+    assert json.loads(json.dumps(out, allow_nan=False))['input_asof'] == input_asof
+    assert sg.is_buyable(out) == sg.is_buyable(full)
+    assert full == before
+    if serializer_name == 'compact':
+        assert out['asof'] == '2026-09-18'  # analytical bucket remains independent
+
+
+@pytest.mark.parametrize('serializer_name', ['compact', 'buy_signal'])
+def test_signal_serializer_does_not_invent_a_daily_receipt_from_the_bucket(serializer_name):
+    from engine import signal_gate as sg
+    out = getattr(sg, serializer_name)({'eligible': True, 'tier_cascade': 'T2',
+                                      'asof': '2026-09-22'})
+    assert 'input_asof' not in out  # preserve legacy shape as well as honest absence
+    assert 'input_asof' not in getattr(sg, serializer_name)(None)
+
+
+@pytest.mark.parametrize('serializer_name', ['compact', 'buy_signal'])
+@pytest.mark.parametrize('invalid', [True, 20260922, float('nan'), {}, ['2026-09-22']])
+def test_signal_daily_receipt_is_json_safe_without_coercing_unknown_types(serializer_name, invalid):
+    from engine import signal_gate as sg
+    out = getattr(sg, serializer_name)({'eligible': False, 'tier_cascade': None,
+                                      'input_asof': invalid})
+    assert out['input_asof'] is None
+    assert sg.is_buyable(out) is False
+    json.dumps(out, allow_nan=False)
+
+
+@pytest.mark.parametrize('serializer_name', ['compact', 'buy_signal'])
+def test_receipt_preservation_never_changes_the_signal_eligibility_decision(serializer_name):
+    from engine import signal_gate as sg
+    serializer = getattr(sg, serializer_name)
+    for eligible in (False, True):
+        for tier in (None, 'T1', 'T2', 'T3', 'T4'):
+            legacy = {'eligible': eligible, 'tier_cascade': tier, 'ticks': 1}
+            enriched = {**legacy, 'input_asof': '2026-09-22'}
+            before, after = serializer(legacy), serializer(enriched)
+            assert after.pop('input_asof') == '2026-09-22'
+            assert after == before
+            assert sg.is_buyable(serializer(enriched)) == sg.is_buyable(legacy)
+
+
+@pytest.mark.parametrize('serializer_name', ['compact', 'buy_signal'])
+@pytest.mark.parametrize('invalid', ['', '2026-09-31', '20260922', '2026-W39-2',
+                                      '2026-09-22T00:00:00Z', '2026-9-22'])
+def test_daily_input_receipt_rejects_noncanonical_dates(serializer_name, invalid):
+    from engine import signal_gate as sg
+    out = getattr(sg, serializer_name)({'input_asof': invalid, 'eligible': False})
+    assert out['input_asof'] is None
+    json.dumps(out, allow_nan=False)
+
+
+@pytest.mark.parametrize('serializer_name', ['compact', 'buy_signal'])
+def test_daily_input_correction_is_not_hidden_by_bucket_identity(serializer_name):
+    from engine import signal_gate as sg
+    serializer = getattr(sg, serializer_name)
+    original = {'asof': '2026-09-18', 'input_asof': '2026-09-21',
+                'eligible': True, 'tier_cascade': 'T2'}
+    before = serializer(original)
+    corrected = serializer({**original, 'input_asof': '2026-09-22'})
+    assert before['input_asof'] == '2026-09-21'
+    assert corrected['input_asof'] == '2026-09-22'
+    assert before.get('asof') == corrected.get('asof')
+    assert sg.is_buyable(before) == sg.is_buyable(corrected)

EXISTING CONSUMER
def _as_date(value: Any) -> str | None:
    """Normalise common date values without making the ranking depend on pandas."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text[:10] if len(text) >= 10 else (text or None)

def _signal_is_fresh(row: Mapping[str, Any]) -> bool:
    """Require the confluence verdict to come from the board's stock session."""
    research = row.get("_signal_research")
    if not isinstance(research, Mapping):
        return False
    return (
        bool(row.get("_board_asof"))
        and _as_date(research.get("input_asof")) == row.get("_board_asof")
    )
