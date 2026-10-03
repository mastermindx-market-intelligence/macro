import copy
import hashlib
import json
import unittest
from fixtures import baseline, plan, scenarios, absent, reference
from preview_contract import build_view, canonical_bytes, PreviewContractError, AUTHORITY


class ConsumerBoundaryTests(unittest.TestCase):
    def setUp(self): self.bundle=baseline()
    def reject(self, code, bundle=None, **kwargs):
        with self.assertRaisesRegex(PreviewContractError, code):
            build_view(self.bundle if bundle is None else bundle, **kwargs)
    def test_every_scenario_renders_both_audiences_without_authority(self):
        for scenario in scenarios():
            for audience in ('public','private'):
                with self.subTest(scenario=scenario['key'],audience=audience):
                    view=build_view(scenario['bundle'],audience=audience,viewer_id='fixture-viewer',private_plan=scenario['private_plan'])
                    self.assertIsNone(view['forecasts']);self.assertEqual(view['authority'],AUTHORITY)
    def test_deterministic_content_hash(self):
        a=build_view(self.bundle);b=build_view(self.bundle)
        self.assertEqual(canonical_bytes(a),canonical_bytes(b))
        digest=a.pop('content_sha256');self.assertEqual(digest,hashlib.sha256(canonical_bytes(a)).hexdigest())
    def test_does_not_mutate_inputs(self):
        before=copy.deepcopy(self.bundle);p=plan();old=copy.deepcopy(p)
        build_view(self.bundle,audience='private',viewer_id='fixture-viewer',private_plan=p)
        self.assertEqual(self.bundle,before);self.assertEqual(p,old)
    def test_output_does_not_alias_inputs(self):
        view=build_view(self.bundle);self.bundle['subject']['name']='changed'
        self.assertNotEqual(view['subject']['name'],'changed')
    def test_real_source_refused(self):
        self.bundle['synthetic']=False;self.reject('SYNTHETIC_ONLY')
    def test_integer_synthetic_marker_refused(self):
        self.bundle['synthetic']=1;self.reject('SYNTHETIC_ONLY')
    def test_unknown_profile_refused(self):
        self.bundle['profile']='live.v1';self.reject('SYNTHETIC_ONLY')
    def test_unknown_top_level_field_refused(self):
        self.bundle['confidence']=0.9;self.reject('UNKNOWN_FIELD')
    def test_missing_required_source_refused(self):
        del self.bundle['sources']['entry'];self.reject('REQUIRED_FIELD_MISSING')
    def test_source_role_cannot_be_laundered(self):
        self.bundle['sources']['entry']['ref']['owner']='prophet.board_admission';self.reject('OWNER_ROLE_MISMATCH')
    def test_issuer_or_ticker_is_not_security_join(self):
        self.bundle['sources']['phase']['ref']['security_id']='fixture:security:another';self.reject('SUBJECT_MISMATCH')
    def test_identity_epoch_must_match(self):
        self.bundle['sources']['phase']['ref']['identity_epoch']='other';self.reject('IDENTITY_EPOCH_MISMATCH')
    def test_unsupported_native_schema_refused(self):
        self.bundle['sources']['phase']['ref']['schema']='prophet.candidate_state/v1';self.reject('NATIVE_SCHEMA_NOT_ADMITTED')
    def test_no_fabricated_native_episode(self):
        self.bundle['sources']['phase']['ref']['native_id']='pe:DEMO:20261002';self.reject('NATIVE_ID_NOT_ADMITTED')
    def test_no_forecast_payload(self):
        self.bundle['forecasts']={'probability':0.9};self.reject('UNQUALIFIED_FORECAST')
    def test_no_rating_payload_in_entry(self):
        self.bundle['sources']['entry']['value']['confidence']=90;self.reject('UNKNOWN_FIELD')
    def test_fresh_quote_does_not_refresh_expired_entry(self):
        self.bundle['sources']['entry']['valid_until']=self.bundle['decision_at'];view=build_view(self.bundle)
        self.assertEqual(view['sources']['entry']['display_status'],'EXPIRED')
        self.assertIsNone(view['sources']['entry']['display_value'])
        self.assertEqual(view['sources']['quote']['display_status'],'AVAILABLE')
    def test_new_quote_generation_withholds_old_entry(self):
        self.bundle['sources']['quote']['ref']['generation']='new';view=build_view(self.bundle)
        self.assertEqual(view['sources']['entry']['display_status'],'GENERATION_MISMATCH')
    def test_schema_relation_is_load_bearing(self):
        self.bundle['sources']['entry']['value']['phase_ref']['schema']='fixture.other/v1';view=build_view(self.bundle)
        self.assertEqual(view['sources']['entry']['display_status'],'GENERATION_MISMATCH')
    def test_future_known_phase_is_absent_at_cut(self):
        self.bundle['sources']['phase']['known_at']='2026-10-02T15:01:00Z';view=build_view(self.bundle)
        self.assertEqual(view['sources']['phase']['display_status'],'NOT_YET_KNOWN')
        self.assertIsNone(view['sources']['phase']['display_value'])
        self.assertEqual(view['sources']['entry']['display_status'],'DEPENDENCY_UNAVAILABLE')
        self.assertNotIn('CONFIRMED',canonical_bytes(view).decode())
    def test_later_correction_cannot_change_earlier_cut_input(self):
        before=build_view(self.bundle)
        later=copy.deepcopy(self.bundle);r=later['sources']['contradiction'];r['correction_of']=copy.deepcopy(r['ref']);r['ref']['generation']='g2';r['known_at']='2026-10-02T15:01:00Z';r['value']['text']='later fact'
        self.assertNotIn('later fact',canonical_bytes(build_view(later)).decode())
        self.assertEqual(before,build_view(self.bundle))
    def test_invalid_clock_order_rejected(self):
        self.bundle['sources']['quote']['known_at']='2026-10-02T14:58:00Z';self.reject('SOURCE_CLOCK_ORDER')
    def test_naive_decision_time_rejected(self):
        self.bundle['decision_at']='2026-10-02T15:00:00';self.reject('NAIVE_CLOCK')
    def test_future_geometry_basis_cannot_pass_earlier_known_clock(self):
        self.bundle['sources']['geometry']['value']['basis_at']='2026-10-02T15:02:00Z';self.reject('GEOMETRY_BASIS_AFTER_OBSERVATION')
    def test_geometry_expiry_independent_of_source_expiry(self):
        self.bundle['sources']['geometry']['value']['opportunity_expires_at']=self.bundle['decision_at']
        self.assertEqual(build_view(self.bundle)['sources']['entry']['display_status'],'OPPORTUNITY_EXPIRED')
    def test_currency_mismatch_withholds_entry(self):
        self.bundle['sources']['quote']['value']['currency']='CAD'
        self.assertEqual(build_view(self.bundle)['sources']['entry']['display_status'],'BASIS_MISMATCH')
    def test_adjustment_mismatch_withholds_entry(self):
        self.bundle['sources']['quote']['value']['price_basis']='adjusted'
        self.assertEqual(build_view(self.bundle)['sources']['entry']['display_status'],'BASIS_MISMATCH')
    def test_nonfinite_zero_negative_and_boolean_prices_rejected(self):
        for bad in ('NaN','Infinity','0','-1',True,132.1):
            with self.subTest(value=bad):
                b=copy.deepcopy(self.bundle);b['sources']['quote']['value']['price']=bad
                with self.assertRaises(PreviewContractError):build_view(b)
    def test_optional_absence_is_not_a_neutral_vote(self):
        absent(self.bundle,'contradiction','NOT_COVERED');view=build_view(self.bundle)
        self.assertIsNone(view['sources']['contradiction']['display_value'])
        self.assertEqual(view['sources']['entry']['display_status'],'AVAILABLE')
        self.assertIn({'source':'contradiction','status':'NOT_COVERED'},view['degradations'])
    def test_absence_cannot_carry_zero_value(self):
        absent(self.bundle,'quote');self.bundle['sources']['quote']['value']=0;self.reject('ABSENT_SOURCE_HAS_VALUE')
    def test_transport_failure_is_not_no_opportunity(self):
        absent(self.bundle,'entry','TRANSPORT_UNAVAILABLE');view=build_view(self.bundle)
        self.assertEqual(view['sources']['entry']['display_status'],'TRANSPORT_UNAVAILABLE')
        self.assertIsNone(view['sources']['entry']['display_value'])
    def test_public_output_ignores_all_private_bytes(self):
        secret={'viewer_id':'SECRET_ACCOUNT','holdings':'SECRET_POSITION','quantity':999,'ref':'SECRET_PLAN'}
        public=build_view(self.bundle,private_plan=secret)
        self.assertNotIn('SECRET',canonical_bytes(public).decode());self.assertNotIn('quantity',canonical_bytes(public).decode())
    def test_saved_is_not_a_fill(self):
        view=build_view(self.bundle,audience='private',viewer_id='fixture-viewer',private_plan=plan())
        self.assertEqual(view['plan']['native_state'],'SAVED');self.assertIsNone(view['plan']['has_position'])
    def test_existing_position_does_not_change_entry_verdict(self):
        view=build_view(self.bundle,audience='private',viewer_id='fixture-viewer',private_plan=plan('ENTERED',True))
        self.assertTrue(view['plan']['has_position'])
        self.assertEqual(view['sources']['entry']['display_value']['native_verdict'],'WAIT_FOR_RESET')
    def test_private_user_mismatch_rejected(self):
        self.reject('PRIVATE_ACCOUNT_MISMATCH',audience='private',viewer_id='different',private_plan=plan())
    def test_private_subject_mismatch_rejected(self):
        p=plan();p['ref']['security_id']='fixture:security:other'
        self.reject('SUBJECT_MISMATCH',audience='private',viewer_id='fixture-viewer',private_plan=p)
    def test_missing_private_owner_does_not_mean_no_plan(self):
        view=build_view(self.bundle,audience='private',viewer_id='fixture-viewer')
        self.assertEqual(view['plan']['status'],'PRIVATE_OWNER_UNAVAILABLE');self.assertIsNone(view['plan']['has_position'])
    def test_expired_private_state_hidden(self):
        p=plan();p['valid_until']=self.bundle['decision_at']
        view=build_view(self.bundle,audience='private',viewer_id='fixture-viewer',private_plan=p)
        self.assertIsNone(view['plan']['native_state']);self.assertNotIn('ref',view['plan'])
    def test_correction_preserves_previous_ref(self):
        r=self.bundle['sources']['support'];old=copy.deepcopy(r['ref']);r['correction_of']=old;r['ref']['generation']='new'
        self.assertEqual(build_view(self.bundle)['sources']['support']['correction_of'],old)
    def test_self_correction_or_cross_native_id_rejected(self):
        r=self.bundle['sources']['support'];r['correction_of']=copy.deepcopy(r['ref']);self.reject('INVALID_CORRECTION_LINEAGE')
    def test_native_extended_not_remapped_or_sold(self):
        self.bundle['sources']['phase']['value']['native_state']='EXTENDED';view=build_view(self.bundle)
        self.assertEqual(view['sources']['phase']['display_value']['native_state'],'EXTENDED')
        self.assertFalse(view['authority']['can_execute']);self.assertNotIn('coarse_stage',view['sources']['phase'])
    def test_no_cross_owner_timestamp_claim_of_live(self):
        view=build_view(self.bundle)
        self.assertNotIn('live',view);self.assertNotIn('freshness',view)
        self.assertIn('known_at',view['sources']['quote']);self.assertIn('valid_until',view['sources']['entry'])

class AdditionalBoundaryTests(unittest.TestCase):
    def test_nonhashable_status_returns_typed_error(self):
        b=baseline();b['sources']['quote']['status']=[]
        with self.assertRaises(PreviewContractError):build_view(b)
    def test_unbounded_price_rejected(self):
        b=baseline();b['sources']['quote']['value']['price']='1'*1000
        with self.assertRaises(PreviewContractError):build_view(b)
    def test_future_value_shape_is_not_examined_at_earlier_cut(self):
        b=baseline();b['sources']['phase']['known_at']='2026-10-02T15:01:00Z'
        b['sources']['phase']['value']={'a_future_schema':'not admitted yet'}
        view=build_view(b)
        self.assertEqual(view['sources']['phase']['display_status'],'NOT_YET_KNOWN')
        self.assertNotIn('a_future_schema',canonical_bytes(view).decode())
    def test_output_authority_is_not_shared_mutable_state(self):
        v=build_view(baseline());v['authority']['can_execute']=True
        self.assertFalse(build_view(baseline())['authority']['can_execute'])

class RendererBoundaryTests(unittest.TestCase):
    def test_both_artifacts_reproduce_deterministically(self):
        from render_preview import render
        h1,v1=render();h2,v2=render();self.assertEqual(h1,h2);self.assertEqual(v1,v2)
        self.assertEqual(len(v1),10)
    def test_all_embedded_views_are_explicitly_synthetic(self):
        from render_preview import render
        _,views=render()
        for pair in views.values():
            for v in pair.values():self.assertIs(v['synthetic'],True)
    def test_script_breakout_is_escaped_but_value_is_preserved(self):
        import re
        from unittest.mock import patch
        from render_preview import render
        b=baseline();payload='</script><script>window.pwned=1</script>&<tag>'
        b['sources']['support']['value']['text']=payload
        with patch('render_preview.scenarios',return_value=[{'key':'attack','bundle':b,'private_plan':plan()}]):
            html,views=render()
        self.assertNotIn(payload,html)
        data=re.search(r'<script id="fixture-data" type="application/json">(.*?)</script>',html,re.S).group(1)
        decoded=json.loads(data)
        self.assertEqual(decoded['attack']['public']['sources']['support']['display_value']['text'],payload)
        self.assertEqual(decoded,views)

if __name__=='__main__':unittest.main(verbosity=2)
