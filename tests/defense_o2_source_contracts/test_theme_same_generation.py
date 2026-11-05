"""Frozen build clocks and reviewed leaf isolation; no collection or writes."""
from pathlib import Path
import json
from copy import deepcopy
from scripts import build_government_revenue as builder
from engine.government_revenue import program_theme_context as t
from engine.government_revenue import program_theme_reviewed_builder as reviewed

NOW = '2026-10-13T08:53:36.399358+00:00'
FIXTURE = Path(__file__).parent / 'fixtures' / 'identity_atlas.json'

def test_budget_constructor_receives_the_frozen_generation_clock(tmp_path, monkeypatch):
    data = tmp_path / 'data/government_revenue'
    data.mkdir(parents=True)
    for filename in builder._BUDGET_SOURCE_FILENAMES:
        (data / filename).write_text('{}')
    monkeypatch.setattr(builder, 'DOD_BUDGET_PRODUCTION_ACTIVATION_ENABLED', True)
    monkeypatch.setattr(builder, '_read_jsonl_objects', lambda *a, **k: [])
    monkeypatch.setattr(builder, 'load_reviewed_edges', lambda *a: None)
    monkeypatch.setattr(builder, '_validate_budget_program_graph_payload', lambda p: p)
    monkeypatch.setattr(builder, '_validate_budget_program_award_bindings', lambda *a: None)
    observed = []
    def native_constructor(**kwargs):
        observed.append(kwargs['generated_at'])
        return {'generated_at': kwargs['generated_at']}
    monkeypatch.setattr(builder, 'build_budget_program_graph', native_constructor)
    first = builder._build_budget_program_graph_if_ready(tmp_path, as_of='2026-10-13', dossier={}, generated_at=NOW)
    second = builder._build_budget_program_graph_if_ready(tmp_path, as_of='2026-10-13', dossier={}, generated_at=NOW)
    assert first == second == {'generated_at': NOW}
    assert observed == [NOW, NOW]

def test_new_archetype_sibling_preserves_gd_leaf_but_legal_change_does_not():
    original = json.loads(FIXTURE.read_bytes())
    ref = {'owner_key':'atlas','pointer':'/issuers/4/entities/1','row_id':'legal:gd:electric-boat-corp'}
    def owner(payload):
        return t.OwnerSnapshot('identity_atlas',json.dumps(payload).encode(),NOW,'existing:reviewed-atlas','qualified_public_display')
    baseline = reviewed.reference_fingerprint(ref,'exposure',owner(original),NOW)
    changed = deepcopy(original)
    changed['issuers'][4]['archetype_context'] = {'state':'unavailable','gaps':['invalid_analysis_cutoff'],'listing_cases':[],'ownership_cases':[]}
    assert reviewed.reference_fingerprint(ref,'exposure',owner(changed),NOW) == baseline
    changed['issuers'][4]['entities'][1]['canonical_name'] += ' material correction'
    assert reviewed.reference_fingerprint(ref,'exposure',owner(changed),NOW) != baseline
