"""Tests for engine.policy_intent_desk — deterministic parts (LLM call injected)."""
from __future__ import annotations

import json

from engine import policy_intent_desk as pid

_REPLY = json.dumps({
    "regime_context": "Low-yield engineering + re-industrialization; revealed > narrative.",
    "confidence": "medium",
    "theses": [
        {"actor": "admin", "subject": "XLE", "lean": "overweight", "conviction": "medium",
         "horizon_d": 40, "thesis": "Energy theater + Iran fragility", "evidence": ["energy theater"],
         "dissent": "ceasefire holds, oil fades", "falsifier_text": "XLE lags SPY by 5%"},
        {"actor": "fed", "subject": "TLT", "lean": "avoid", "conviction": "low",
         "horizon_d": 60, "thesis": "Yield suppression but term-premium risk", "evidence": ["dollar theater"],
         "dissent": "growth scare bid", "falsifier_text": "TLT beats SPY by 5%"},
        {"actor": "admin", "subject": "NOTATICKER", "lean": "overweight"},   # dropped: bad subject
        {"actor": "admin", "subject": "XLF", "lean": "sideways"},            # dropped: bad lean
    ],
})


def _fake_call(system, user, cfg):
    return _REPLY, None


_REPLY_BILINGUAL = json.dumps({
    "regime_context": "Low-yield engineering + re-industrialization.",
    "regime_context_zh": "压低收益率 + 再工业化。",
    "confidence": "medium",
    "theses": [
        {"actor": "admin", "subject": "XLE", "lean": "overweight", "conviction": "medium",
         "horizon_d": 40, "thesis": "Energy theater", "thesis_zh": "能源战区",
         "evidence": ["energy theater"], "dissent": "ceasefire holds", "dissent_zh": "停火维持",
         "falsifier_text": "XLE lags SPY by 5%", "falsifier_text_zh": "XLE 跑输 SPY 5%"},
    ],
})


def _fake_call_bilingual(system, user, cfg):
    return _REPLY_BILINGUAL, None


def test_derive_check_rel_return():
    ov = pid._derive_check("XLE", "overweight", 40, pid._cfg())
    assert ov["kind"] == "rel_return" and ov["op"] == "<" and ov["threshold"] == -0.05 and ov["vs"] == "SPY"
    av = pid._derive_check("TLT", "avoid", 60, pid._cfg())
    assert av["op"] == ">" and av["threshold"] == 0.05
    # ITA (defense, no local series) is now GRADEABLE via a correlated surrogate (XLI)
    corr = pid._derive_check("ITA", "overweight", 40, pid._cfg())
    assert corr["kind"] == "rel_return" and corr["via"] == "correlated"
    assert corr["subject_ticker"] == "XLI" and corr["surrogate_of"] == "ITA"
    assert corr["threshold"] < -0.05            # wider threshold than a direct proxy (×1.6)
    # a cash/dollar soft (no equity surrogate) stays soft
    soft = pid._derive_check("UUP", "overweight", 40, pid._cfg())
    assert soft["kind"] == "soft" and soft["via"] == "soft"


def test_synthesize_builds_and_validates_theses():
    state = {"as_of": "2026-06-18", "allowed_subjects": sorted(pid._ALLOWED)}
    brief = pid.synthesize(state, pid._cfg(), call=_fake_call)
    assert brief["schema"] == pid.SCHEMA and brief["is_context_only"] is True
    subs = [t["subject"] for t in brief["theses"]]
    assert subs == ["XLE", "TLT"]                       # bad subject + bad lean dropped
    xle = brief["theses"][0]
    assert xle["falsifier"]["check"]["kind"] == "rel_return"
    assert xle["check_by"] and xle["actor"] == "admin"
    assert brief["confidence"] == "medium"


def test_synthesize_captures_bilingual_fields():
    state = {"as_of": "2026-06-18", "allowed_subjects": sorted(pid._ALLOWED)}
    brief = pid.synthesize(state, pid._cfg(), call=_fake_call_bilingual)
    assert brief["regime_context_zh"] == "压低收益率 + 再工业化。"
    assert brief["disclaimer_zh"] and "意图台" in brief["disclaimer_zh"]   # static zh disclaimer
    th = brief["theses"][0]
    assert th["thesis_zh"] == "能源战区" and th["dissent_zh"] == "停火维持"
    assert th["falsifier"]["text_zh"] == "XLE 跑输 SPY 5%"


def test_synthesize_zh_fields_degrade_to_none_when_absent():
    # English-only reply (no *_zh keys) → zh fields are None; the template falls back to en.
    state = {"as_of": "2026-06-18", "allowed_subjects": sorted(pid._ALLOWED)}
    brief = pid.synthesize(state, pid._cfg(), call=_fake_call)
    assert brief["regime_context_zh"] is None
    assert brief["disclaimer_zh"]                                          # static, always present
    assert brief["theses"][0]["thesis_zh"] is None
    assert brief["theses"][0]["falsifier"]["text_zh"] is None


def test_synthesize_degrades_without_key():
    brief = pid.synthesize({"as_of": "2026-06-18"}, pid._cfg(), call=lambda s, u, c: (None, "no_client_or_key"))
    assert brief["theses"] == [] and brief["degraded_reason"] == "no_client_or_key"


def test_build_thesis_rejects_bad():
    assert pid._build_thesis({"subject": "ZZZ", "lean": "overweight"}, 0, "2026-06-18", pid._cfg()) is None
    assert pid._build_thesis({"subject": "XLE", "lean": "nope"}, 0, "2026-06-18", pid._cfg()) is None
    ok = pid._build_thesis({"subject": "xle", "lean": "OverWeight"}, 0, "2026-06-18", pid._cfg())
    assert ok and ok["subject"] == "XLE" and ok["lean"] == "overweight"


def test_gather_state_reads_intel(tmp_path):
    (tmp_path / "data" / "policy").mkdir(parents=True)
    (tmp_path / "data" / "regime").mkdir(parents=True)
    (tmp_path / "data" / "policy" / "intel.json").write_text(json.dumps({
        "as_of": "2026-06-18", "thesis": {"en": "T"},
        "administration": {"theaters": [{"title_en": "China", "basis": "FACT", "capital_en": "x"}]},
        "rotation": {"targeted": [{"theme_en": "Defense", "proxies": ["ITA"], "basis": "FACT"}]},
        "predictions": [{"text_en": "P open", "status": "open"}, {"text_en": "P hit", "status": "hit"}],
    }))
    (tmp_path / "data" / "regime" / "latest.json").write_text(json.dumps({"quad_name": "Goldilocks"}))
    st = pid.gather_state(root=tmp_path)
    assert st["thesis"] == "T" and st["market"]["quad"] == "Goldilocks"
    assert len(st["theaters"]) == 1 and st["open_predictions"] == ["P open"]
    assert "XLE" in st["scorable_subjects"]


def test_gather_state_none_without_intel(tmp_path):
    assert pid.gather_state(root=tmp_path) is None


def test_run_persists_and_appends(tmp_path):
    (tmp_path / "data" / "policy").mkdir(parents=True)
    (tmp_path / "data" / "regime").mkdir(parents=True)
    (tmp_path / "site").mkdir()
    (tmp_path / "data" / "policy" / "intel.json").write_text(json.dumps({"as_of": "2026-06-18", "thesis": {"en": "T"}}))
    brief = pid.run(persist=True, root=tmp_path, force=True, call=_fake_call)
    assert brief and len(brief["theses"]) == 2
    assert (tmp_path / "site" / "policy_intent.json").exists()
    rows = (tmp_path / "data" / "policy_intent" / "theses.jsonl").read_text().strip().splitlines()
    assert len(rows) == 2
    r0 = json.loads(rows[0])
    assert r0["status"] == "open" and r0["subject"] == "XLE" and r0["falsifier"]["check"]["kind"] == "rel_return"
    # public copy drops raw_text
    pub = json.loads((tmp_path / "site" / "policy_intent.json").read_text())
    assert "raw_text" not in pub


def test_gld_aliases_to_scorable_gold_futures():
    tk, vs, kind, via = pid._resolve_subject("GLD")
    assert (tk, vs, kind, via) == ("GC_F", "SPY", "rel_return", "direct")
    chk = pid._derive_check("GLD", "overweight", 40, pid._cfg())
    assert chk["kind"] == "rel_return" and chk["subject_ticker"] == "GC_F"


def test_correlated_surrogates_are_scorable_and_resolve():
    """Every soft→surrogate mapping must point at a SCORABLE ticker (else the surrogate
    grade silently expires too) and resolve to a 'correlated' rel_return check."""
    for soft, surrogate in pid._SOFT_PROXY.items():
        assert surrogate in pid._SCORABLE, f"{soft} -> {surrogate}: surrogate not scorable"
        tk, vs, kind, via = pid._resolve_subject(soft)
        assert kind == "rel_return" and via == "correlated" and tk == surrogate


def test_every_scorable_subject_has_a_price_series():
    """Regression guard for the GLD class of bug: a SCORABLE subject MUST resolve to a
    ticker that actually has a data/yahoo price series, else it scores 'expired', never graded."""
    from lib import config
    ydir = config.ROOT / "data" / "yahoo"
    for s in pid._SCORABLE:
        tk, vs, kind, via = pid._resolve_subject(s)
        assert kind == "rel_return", f"{s} should be scorable"
        assert (ydir / f"{tk}.parquet").exists(), f"{s} -> {tk}: no price series (would never score)"


def test_run_thesis_ids_carry_run_token(tmp_path):
    (tmp_path / "data" / "policy").mkdir(parents=True)
    (tmp_path / "data" / "regime").mkdir(parents=True)
    (tmp_path / "site").mkdir()
    (tmp_path / "data" / "policy" / "intel.json").write_text(json.dumps({"as_of": "2026-06-18", "thesis": {"en": "T"}}))
    brief = pid.run(persist=True, root=tmp_path, force=True, call=_fake_call)
    ids = [t["id"] for t in brief["theses"]]
    # ids are run-token-stamped (date-token-seq), so same-day re-runs can't collide
    assert all(len(i.split("-")) >= 3 for i in ids), ids
    assert len(set(ids)) == len(ids)


# Exact source vintage is raw provenance, not a freshness qualification.
from unittest.mock import patch

def _provenance_fail(*args):
    raise AssertionError('unexpected model call')

def _provenance_brief(state=None, call=_fake_call):
    state = {'as_of': '2026-11-08', 'intel_asof': '2026-07-13'} if state is None else state
    with patch.object(pid, '_now_iso', return_value='2026-11-08T09:00:00+00:00'):
        return pid.synthesize(state, pid._cfg(), call=call)

def test_intel_asof_source_clock_is_retained_without_replacing_run_clock(tmp_path):
    brief = _provenance_brief()
    assert 'intel_asof' in brief
    assert brief['intel_asof'] == '2026-07-13'
    assert brief['state_asof'] == '2026-11-08'
    assert brief['schema'] == 'policy_intent_desk.v1'

def test_intel_asof_all_synthesis_return_paths_retain_provenance(tmp_path):
    for reply, reason in [(None, 'no_client_or_key'), ('not JSON', None), (_REPLY, 'partial')]:
        brief = _provenance_brief(call=lambda *args: (reply, reason))
        assert 'intel_asof' in brief
        assert brief['intel_asof'] == '2026-07-13'

def test_intel_asof_missing_and_null_are_unknown(tmp_path):
    state = {'as_of': '2026-11-08', 'intel_asof': '2026-07-13'}
    for state in [{'as_of': '2026-11-08'}, {'as_of': '2026-11-08', 'intel_asof': None}]:
        brief = _provenance_brief(state)
        assert 'intel_asof' in brief
        assert brief['intel_asof'] is None

def test_intel_asof_raw_json_provenance_is_not_normalized(tmp_path):
    state = {'as_of': '2026-11-08', 'intel_asof': '2026-07-13'}
    for value in [' 2026-07-13 ', 'not-a-date', '', 0, False, ['unknown'], {'raw': 'date'}]:
        brief = _provenance_brief({**state, 'intel_asof': value})
        assert 'intel_asof' in brief
        assert brief['intel_asof'] == value
        assert type(brief['intel_asof']) is type(value)

def test_intel_asof_gather_persist_and_new_ledger_rows_retain_source(tmp_path):
    (tmp_path / 'data/policy').mkdir(parents=True)
    (tmp_path / 'site').mkdir()
    (tmp_path / 'data/policy/intel.json').write_text(json.dumps({'as_of': '2026-07-13', 'thesis': {'en': 'synthetic'}}))
    with patch.dict('os.environ', {'COLLECT_LANE': 'nightly', 'US_LANE': ''}):
        brief = pid.run(persist=True, root=tmp_path, force=True, call=_fake_call)
    assert brief['intel_asof'] == '2026-07-13'
    for path in ['data/regime/policy_intent.json', 'site/policy_intent.json']:
        obj = json.loads((tmp_path / path).read_text())
        assert obj['intel_asof'] == '2026-07-13'
    assert 'raw_text' not in json.loads((tmp_path / 'site/policy_intent.json').read_text())
    rows = [json.loads(line) for line in (tmp_path / 'data/policy_intent/theses.jsonl').read_text().splitlines()]
    assert len(rows) == 2
    assert all((row['intel_asof'] == '2026-07-13' for row in rows))

def test_intel_asof_direct_legacy_brief_appends_unknown_without_backfill(tmp_path):
    brief = _provenance_brief()
    brief.pop('intel_asof', None)
    with patch.dict('os.environ', {'COLLECT_LANE': 'nightly', 'US_LANE': ''}):
        pid._append_ledger(brief, tmp_path)
    rows = [json.loads(line) for line in (tmp_path / 'data/policy_intent/theses.jsonl').read_text().splitlines()]
    assert len(rows) == 2
    for row in rows:
        assert 'intel_asof' in row
        assert row['intel_asof'] is None

def test_intel_asof_legacy_bytes_and_duplicate_id_are_preserved(tmp_path):
    brief = _provenance_brief()
    ledger = tmp_path / 'data/policy_intent/theses.jsonl'
    ledger.parent.mkdir(parents=True)
    old = (json.dumps({'id': brief['theses'][0]['id'], 'legacy': True}, separators=(',', ':')) + '\n').encode()
    ledger.write_bytes(old)
    with patch.dict('os.environ', {'COLLECT_LANE': 'nightly', 'US_LANE': ''}):
        pid._append_ledger(brief, tmp_path)
        first = ledger.read_bytes()
        pid._append_ledger(brief, tmp_path)
    assert first.startswith(old)
    assert ledger.read_bytes() == first
    rows = [json.loads(line) for line in first.splitlines()]
    assert len(rows) == 2
    assert 'intel_asof' not in rows[0]
    assert rows[1]['intel_asof'] == '2026-07-13'

def test_intel_asof_off_lane_gate_precedes_argument_access(tmp_path):

    class Trip:

        def get(self, *args):
            raise AssertionError('off-lane brief accessed')

        def __fspath__(self):
            raise AssertionError('off-lane root accessed')
    with patch.dict('os.environ', {'COLLECT_LANE': '', 'US_LANE': ''}):
        pid._append_ledger(Trip(), Trip())

def test_intel_asof_cached_legacy_brief_is_not_backfilled_or_resynthesized(tmp_path):
    cfg = {**pid._cfg(), 'enabled': True, 'interval_days': 3}
    prior = {'generated_at': '2026-11-08T09:00:00+00:00', 'state_asof': '2026-11-08', 'theses': []}
    path = tmp_path / 'data/regime/policy_intent.json'
    path.parent.mkdir(parents=True)
    original = json.dumps(prior, separators=(',', ':')).encode()
    path.write_bytes(original)
    with patch.object(pid, '_cfg', return_value=cfg), patch.object(pid, '_brief_age_days', return_value=0), patch.object(pid, 'gather_state', side_effect=AssertionError('cached input gathered')):
        result = pid.run(root=tmp_path, call=lambda *a: _provenance_fail('model called'))
    assert result == prior
    assert 'intel_asof' not in result
    assert path.read_bytes() == original

def test_intel_asof_persist_false_writes_nothing(tmp_path):
    state = {'as_of': '2026-11-08', 'intel_asof': '2026-07-13'}
    with patch.object(pid, 'gather_state', return_value=state):
        result = pid.run(root=tmp_path, force=True, persist=False, call=_fake_call)
    assert result['intel_asof'] == '2026-07-13'
    assert list(tmp_path.iterdir()) == []
