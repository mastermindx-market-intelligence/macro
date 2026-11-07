"""Real Node boundary tests for the opt-in Sector Dossier Cycle presentation.

The component consumes existing producer stamps; it never computes a signal,
fetches data, owns authorization or creates another navigation/persistence plane.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "templates" / "sector_dossier_cycle.js"
NODE = shutil.which("node")

PRELUDE = r"""
const assert = require('node:assert/strict');
const api = require(process.argv[1]);
function fixture() {
  return {
    meta: {asOf: '2026-10-30', region: 'us', benchmark: 'SPY',
      live_hazard_parity: {verdict: 'PARITY_FAILS'}},
    sectors: [{id: 'xle', kind: 'sector', ticker: 'XLE', name: 'Energy', name_zh: '能源',
      basis: 'price',
      now: {phase: 'Expansion', pos: 91, phase_v2: 'Downturn', pos_v2: 71.4,
        phase_v2_source: 'ontology', phase_v2_position_input: 'pos_v2',
        phase_v2_age_sessions: 23, phase_v2_age_status: 'measured',
        phase_v2_age: {sessions: 23, status: 'measured'},
        above200d: true, rs_63d: 6.1, thin_history: false},
      osc: [{x: 2026.1, v: 90}, {x: 2026.2, v: 91}],
      price: [{x: 2026.1, v: 100}, {x: 2026.2, v: 110}],
      estimate_kinds: {model_cell_current_claim: 'parity_failed',
        live_feature_parity: {verdict: 'PARITY_FAILS'},
        hazard: {'1m': 'qualified_model_cell', '3m': 'baseline_prior', '6m': 'baseline_prior'}},
      series_provenance: {schema: 'sector_cycles.series_provenance.v1',
        rs_basis: 'tr', structure_basis: 'price', benchmark: 'SPY',
        membership: 'single_instrument', point_in_time: true,
        history_mode: 'reconstructed_price_history'}}], baskets: [], nasdaq: [], russell: []
  };
}
function opts(extra) {
  return Object.assign({accessState:'allowed', dataState:'ready', family:'sectors',
    id:'xle', locale:'en', expectedAsOf:'2026-10-30'}, extra || {});
}
function view(p, o) { return api.buildView(p || fixture(), opts(o)); }
"""

NATIVE_PRELUDE = r"""
function evidence(extra={}) {
 return Object.assign({schema:'sector_cycles.evidence.v1',status:'verified',
  publicationId:'cycp1-'+ 'a'.repeat(64),asOf:'2026-10-30',region:'us',
  spine:{schema:'sector_cycles.sector_spine.v1',scope:'us_sectors_11',sha256:'b'.repeat(64)},
  parts:{core:'verified',series:'verified',narr:'source_unavailable',dna:'verified'},
  sources:{narr:{status:'source_unavailable'},dna:{status:'available'}}},extra);
}
function nativeOpts(extra={}) {return Object.assign({requirePublication:true,
 evidence:evidence(),expectedPublicationId:'cycp1-'+'a'.repeat(64)},extra);}
"""
PRELUDE += NATIVE_PRELUDE

CASES = {
    "verified_status_requires_verified_core_part_before_payload_read": r"""
      for(const parts of [null,{}, {core:'pending'}, {core:'integrity_failed'}]) {
        const p=new Proxy({}, {get(){throw Error('unverified core accessed');}});
        assert.equal(view(p,nativeOpts({evidence:evidence({parts})})).state,'unavailable');
      }
    """,
    "native_mount_adapter_is_available_without_automatic_boot": r"""
      assert.equal(typeof api.mountFromNative,'function');
      assert.equal(globalThis.document,undefined);
    """,
    "publication_pending_never_evaluates_payload": r"""
      const p=new Proxy({}, {get(){throw Error('unverified payload accessed');}});
      assert.equal(view(p,nativeOpts({evidence:evidence({status:'pending'})})).state,'loading');
    """,
    "native_publication_is_bound_in_successful_view": r"""
      const v=view(fixture(),nativeOpts());assert.equal(v.state,'ready');
      assert.equal(v.publication.id,'cycp1-'+'a'.repeat(64));
      assert.equal(v.publication.status,'verified');assert.equal(v.history.state,'ready');
    """,
    "same_day_different_publication_is_not_same_snapshot": r"""
      const p=new Proxy({}, {get(){throw Error('mismatched payload accessed');}});
      assert.equal(view(p,nativeOpts({expectedPublicationId:'cycp1-'+'c'.repeat(64)})).state,'incompatible_generation');
    """,
    "unverified_or_invalid_receipt_never_exposes_data": r"""
      for(const status of ['legacy_unverified','integrity_failed','invalid_payload','verification_unavailable','mystery']) {
        const p=new Proxy({}, {get(){throw Error('unverified payload accessed');}});
        assert.equal(view(p,nativeOpts({evidence:evidence({status})})).state,'unavailable',status);
      }
    """,
    "superseded_source_clears_snapshot_claim": r"""
      const v=view(fixture(),nativeOpts({evidence:evidence({status:'superseded'})}));
      assert.equal(v.state,'incompatible_generation');assert.equal(v.relative,undefined);
    """,
    "missing_or_malformed_publication_binding_is_not_optional": r"""
      for(const expectedPublicationId of [undefined,null,'','cycp1-bad']) {
        assert.equal(view(fixture(),nativeOpts({expectedPublicationId})).state,'unavailable');
      }
      for(const e of [null,{},evidence({schema:'other'}),evidence({publicationId:'bad'})]) {
        assert.equal(view(fixture(),nativeOpts({evidence:e})).state,'unavailable');
      }
    """,
    "native_receipt_region_and_session_must_match_payload": r"""
      for(const e of [evidence({region:'china'}),evidence({asOf:'2026-10-29'})]) {
        const v=view(fixture(),nativeOpts({evidence:e}));
        assert.equal(v.state,'incompatible_generation');assert.equal(v.relative,undefined);
      }
    """,
    "expected_sector_spine_is_exact_not_a_date_only_join": r"""
      const expected={schema:'sector_cycles.sector_spine.v1',scope:'us_sectors_11',sha256:'b'.repeat(64)};
      assert.equal(view(fixture(),nativeOpts({expectedSpine:expected})).state,'ready');
      for(const change of [{sha256:'c'.repeat(64)},{scope:'china:sectors'},{schema:'other'}]) {
        assert.equal(view(fixture(),nativeOpts({expectedSpine:{...expected,...change}})).state,'incompatible_generation');
      }
    """,
    "unverified_nonsector_series_does_not_draw_even_if_arrays_exist": r"""
      for(const family of ['baskets','nasdaq','russell']) for(const status of ['pending','invalid_payload','incompatible_publication','integrity_failed','unavailable','legacy_unverified']) {
        const p=fixture();const rec=p.sectors.pop();rec.kind=family==='baskets'?'basket':family;p[family]=[rec];
        const v=view(p,nativeOpts({family,evidence:evidence({parts:{core:'verified',series:status}})}));
        assert.equal(v.state,'ready');assert.equal(v.relative.value,6.1);
        assert.equal(v.chart.hasHistory,false);assert.equal(v.history.rows.length,0);
      }
    """,
    "verified_sector_core_history_survives_optional_series_failure": r"""
      for(const status of ['pending','invalid_payload','incompatible_publication','unavailable']) {
        const v=view(fixture(),nativeOpts({evidence:evidence({parts:{core:'verified',series:status}})}));
        assert.equal(v.chart.hasHistory,true);assert.equal(v.history.sourcePart,'core');
        assert.equal(v.history.rows.length,2);
      }
    """,
    "optional_annotation_failure_does_not_erase_verified_core": r"""
      const v=view(fixture(),nativeOpts({evidence:evidence({parts:{core:'verified',series:'verified',narr:'quarantined',dna:'unavailable'}})}));
      assert.equal(v.state,'ready');assert.equal(v.history.state,'ready');
      assert.equal(v.publication.parts.narr,'quarantined');
    """,
    "exact_values_preserve_observations_and_zero": r"""
      const p=fixture();p.sectors[0].osc=[{x:2026.1,v:0},{x:2026.2,v:100}];
      const v=view(p);assert.deepEqual(v.history.rows,[{x:2026.1,value:0},{x:2026.2,value:100}]);
      v.history.rows[0].value=91;assert.equal(p.sectors[0].osc[0].v,0);
    """,
    "malformed_history_is_withheld_not_silently_filtered": r"""
      for(const bad of [{x:2026.2,v:null},{x:2026.2,v:'71'},{x:NaN,v:50},{x:2026.2,v:101}]) {
        const p=fixture();p.sectors[0].osc.push(bad);const v=view(p);
        assert.equal(v.history.state,'invalid');assert.equal(v.chart.hasHistory,false);
        assert.equal(v.history.rows.length,0);assert.equal(v.relative.value,6.1);
      }
    """,
    "out_of_order_or_repeated_coordinates_are_not_a_valid_series": r"""
      for(const x of [2026.1,2026.05]) {
        const p=fixture();p.sectors[0].osc[1].x=x;assert.equal(view(p).history.state,'invalid');
      }
    """,
    "legacy_classifier_is_never_labelled_ontology": r"""
      for(const source of ['legacy_fallback',undefined,'unknown']) {
        const p=fixture();p.sectors[0].now.phase_v2_source=source;
        const v=view(p);assert.equal(v.phase.key,null);
        assert.equal(v.phase.semanticFamily,'unavailable');
        assert.equal(v.age.value,null);
      }
    """,
    "phase_fallback_provenance_remains_inspectable": r"""
      const p=fixture();p.sectors[0].now.phase_v2_source='legacy_fallback';
      assert.equal(view(p).phase.source,'legacy_fallback');
      assert.equal(view(p).position.value,71.4);
    """,
    "reads_producer_v2_without_legacy_substitution": r"""
      const v=view(); assert.equal(v.state,'ready'); assert.equal(v.subject.id,'xle');
      assert.equal(v.phase.key,'Downturn'); assert.equal(v.position.value,71.4);
      assert.equal(v.position.semanticFamily,'ontology');
      assert.equal(v.chart.semanticFamily,'legacy');
      assert.equal(v.relative.value,6.1); assert.equal(v.relative.horizonSessions,63);
      assert.equal(v.relative.benchmark,'SPY'); assert.equal(v.asOf,'2026-10-30');
    """,
    "denied_never_reads_sensitive_payload": r"""
      const forbidden=new Proxy({}, {get(){throw Error('sensitive payload read');}});
      for(const accessState of ['forbidden','unauthenticated']) {
        const v=api.buildView(forbidden,opts({accessState}));
        assert.equal(v.state,'denied'); assert.equal(v.subject,undefined);
        assert.equal(v.relative,undefined);
      }
    """,
    "pending_access_never_reads_payload": r"""
      const p=new Proxy({}, {get(){throw Error('payload read before access settled');}});
      assert.equal(api.buildView(p,opts({accessState:'pending'})).state,'loading');
      assert.notEqual(api.buildView(p,{}).state,'ready');
    """,
    "unknown_access_fails_closed": r"""
      assert.equal(view(fixture(),{accessState:'admin'}).state,'denied');
    """,
    "source_failure_is_not_an_empty_success": r"""
      for(const dataState of ['unavailable','error','offline']) {
        const v=view(null,{dataState}); assert.equal(v.state,'unavailable');
        assert.equal(v.relative,undefined);
      }
      assert.equal(view(null,{dataState:'loading'}).state,'loading');
    """,
    "unknown_data_state_fails_closed": r"""
      assert.equal(view(fixture(),{dataState:'mystery'}).state,'unavailable');
    """,
    "stale_is_preserved_without_a_new_freshness_policy": r"""
      const v=view(fixture(),{dataState:'stale'}); assert.equal(v.state,'stale');
      assert.equal(v.asOf,'2026-10-30'); assert.equal(v.relative.value,6.1);
    """,
    "different_snapshot_never_shows_newer_values_under_old_context": r"""
      const v=view(fixture(),{expectedAsOf:'2026-10-29'});
      assert.equal(v.state,'incompatible_generation'); assert.equal(v.relative,undefined);
    """,
    "malformed_expected_date_is_not_a_wildcard": r"""
      assert.equal(view(fixture(),{expectedAsOf:'not-a-date'}).state,'unavailable');
    """,
    "real_calendar_date_validation": r"""
      for(const date of ['2026-02-30','2026-13-01','2026-00-01','26-10-30','2026-1-01',null]) {
        const p=fixture(); p.meta.asOf=date;
        assert.equal(view(p,{expectedAsOf:null}).state,'unavailable',String(date));
      }
      const p=fixture();p.meta.asOf='2024-02-29';
      assert.equal(view(p,{expectedAsOf:'2024-02-29'}).state,'ready');
    """,
    "exact_identity_only_no_first_row_fallback": r"""
      for(const id of ['XLE','missing','',null]) assert.equal(view(fixture(),{id}).state,'unavailable');
    """,
    "duplicate_identity_is_ambiguous": r"""
      const p=fixture();p.sectors.push({...p.sectors[0]});
      assert.equal(view(p).state,'unavailable');
    """,
    "family_and_kind_must_agree": r"""
      const p=fixture();p.sectors[0].kind='basket';assert.equal(view(p).state,'unavailable');
      assert.equal(view(fixture(),{family:'baskets'}).state,'unavailable');
      assert.equal(view(fixture(),{family:'__proto__'}).state,'unavailable');
    """,
    "regional_records_are_not_silently_called_us": r"""
      const p=fixture();p.meta.region='china';assert.equal(view(p).state,'unavailable');
    """,
    "null_and_numeric_strings_are_not_zero": r"""
      for(const val of [null,undefined,'0','6.1',NaN,Infinity,false]) {
        const p=fixture();p.sectors[0].now.rs_63d=val;
        assert.equal(view(p).relative.value,null,String(val));
      }
      const p=fixture();p.sectors[0].now.rs_63d=0;assert.equal(view(p).relative.value,0);
    """,
    "thin_history_withholds_inconsistent_return": r"""
      const p=fixture();p.sectors[0].now.thin_history=true;
      assert.equal(view(p).relative.value,null);
    """,
    "unknown_rs_basis_or_benchmark_withholds_labelled_return": r"""
      for(const key of ['rs_basis','benchmark']) {
        const p=fixture();delete p.sectors[0].series_provenance[key];
        assert.equal(view(p).relative.value,null);
      }
    """,
    "position_is_v2_only_and_bounded": r"""
      for(const val of [null,undefined,-1,101,'71.4']) {
        const p=fixture();p.sectors[0].now.pos_v2=val;
        assert.equal(view(p).position.value,null);
      }
      const p=fixture();p.sectors[0].now.pos_v2=0;assert.equal(view(p).position.value,0);
    """,
    "legacy_fallback_cannot_masquerade_as_v2": r"""
      const p=fixture();p.sectors[0].now.phase_v2_position_input='legacy_pos_fallback';
      assert.equal(view(p).position.value,null);
    """,
    "age_lower_bound_is_not_exact": r"""
      const p=fixture(),n=p.sectors[0].now;n.phase_v2_age_status='lower_bound';
      n.phase_v2_age={status:'lower_bound',sessions:23};
      const a=view(p).age;assert.equal(a.status,'lower_bound');assert.equal(a.value,23);
    """,
    "age_missing_or_contradictory_is_unavailable": r"""
      for(const status of ['not_logged','insufficient_history','source_unavailable']) {
        const p=fixture();p.sectors[0].now.phase_v2_age={status,sessions:23};
        assert.equal(view(p).age.value,null);
      }
      const p=fixture();p.sectors[0].now.phase_v2_age.sessions=24;
      assert.equal(view(p).age.value,null);
    """,
    "monthly_age_not_labelled_trading_sessions": r"""
      const p=fixture();p.sectors[0].now.freq='M';assert.equal(view(p).age.value,null);
    """,
    "missing_boolean_not_a_negative_trend": r"""
      for(const val of [null,undefined,0,'false']) {
        const p=fixture();p.sectors[0].now.above200d=val;
        assert.equal(view(p).trend.above200,null);
      }
      const p=fixture();p.sectors[0].now.above200d=false;
      assert.equal(view(p).trend.above200,false);
    """,
    "parity_failure_is_retained_not_current_probability": r"""
      const v=view();assert.equal(v.qualification,'parity_failed');
      assert.equal(v.hazard,undefined);assert.equal(v.probability,undefined);
    """,
    "missing_and_conflicting_parity_fail_closed": r"""
      const p=fixture(),r=p.sectors[0];r.estimate_kinds.model_cell_current_claim='parity_holds';
      r.estimate_kinds.live_feature_parity.verdict='PARITY_HOLDS';
      assert.equal(view(p).qualification,'parity_failed');
      delete p.meta.live_hazard_parity;delete r.estimate_kinds.live_feature_parity;
      assert.equal(view(p).qualification,'parity_not_established');
    """,
    "zh_changes_labels_not_numbers": r"""
      const a=view(),b=view(fixture(),{locale:'zh'});assert.equal(b.subject.name,'能源');
      assert.equal(a.relative.value,b.relative.value);assert.equal(a.phase.key,b.phase.key);
      assert.equal(b.locale,'zh');
    """,
    "unknown_locale_is_not_silently_accepted": r"""
      assert.equal(view(fixture(),{locale:'fr'}).state,'unavailable');
    """,
    "legacy_phase_fallback_is_not_ontology": r"""
      const p=fixture();p.sectors[0].now.phase_v2_source='legacy_fallback';
      assert.equal(view(p).phase.key,null);assert.equal(view(p).age.value,null);
    """,
    "unknown_phase_cannot_keep_a_measured_phase_age": r"""
      const p=fixture();p.sectors[0].now.phase_v2='Undocumented';
      assert.equal(view(p).phase.key,null);assert.equal(view(p).age.value,null);
    """,
    "no_mutation_of_engine_objects": r"""
      const p=fixture(),before=JSON.stringify(p);view(p);assert.equal(JSON.stringify(p),before);
    """,
    "loading_module_has_no_global_browser_side_effect": r"""
      assert.equal(typeof api.mount,'function');assert.equal(typeof api.buildView,'function');
      assert.equal(globalThis.SECTOR_CYCLES,undefined);assert.equal(globalThis.document,undefined);
    """,
}


@pytest.mark.parametrize("case", CASES, ids=CASES.keys())
def test_cycle_dossier_boundary(case: str) -> None:
    assert MODULE.is_file(), "Dossier Cycle source component is not implemented"
    if not NODE:
        pytest.skip("Node is required for the real JavaScript boundary test")
    result = subprocess.run(
        [NODE, "-e", PRELUDE + CASES[case], str(MODULE)],
        text=True, capture_output=True, timeout=15, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
