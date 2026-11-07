"""Synthetic forward-scorecard falsifiers; no empirical performance claim."""
from copy import deepcopy
import json
import math

import pytest

from engine.event_hedging_evaluation import score_event_hedging_forecasts
from engine.k3e_eval1_forward import brier_score, mean_log_loss


@pytest.fixture
def inputs():
    protocol = dict(registration_ref='fixture:registration', registered_at='2026-10-01T12:00:00Z',
        target_ref='fixture:first-touch-60-v1', horizon_minutes=60, security_id='fixture:SPX',
        baseline_model_ref='fixture:baseline-v1', challenger_model_ref='fixture:hedge-v1',
        training_episode_ids=['fixture:training-event'], evaluation_start='2026-10-08T13:30:00Z',
        evaluation_end='2026-10-08T20:00:00Z', expected_origins=[dict(origin_id='o1',episode_id='event1')],
        cohort_source_ref='fixture:eligible-cohort')
    def forecast(model, probabilities):
        return dict(model_ref=model,receipt_ref=model+':issued-o1', issued_at='2026-10-08T14:00:00Z',
            features_known_at='2026-10-08T13:59:59Z',training_labels_known_at='2026-10-01T12:00:00Z',
            probabilities=probabilities)
    row = dict(origin_id='o1',episode_id='event1',target_ref=protocol['target_ref'],horizon_minutes=60,
        security_id=protocol['security_id'],decision_at='2026-10-08T14:00:00Z',
        target_end_at='2026-10-08T15:00:00Z',target_window_ref='fixture:window-o1',
        baseline=forecast(protocol['baseline_model_ref'],[.4,.3,.3]),
        challenger=forecast(protocol['challenger_model_ref'],[.6,.2,.2]),
        outcome=dict(status='available',label='UPPER_FIRST',known_at='2026-10-08T15:01:00Z',
                     receipt_ref='fixture:outcome-o1',reason=None))
    return dict(protocol=protocol,records=[row],evaluated_at='2026-10-08T21:00:00Z')


def test_exact_incumbent_metric_parity_and_zero_promotion(inputs):
    original=deepcopy(inputs)
    out=score_event_hedging_forecasts(**inputs)
    assert out['status']=='scored'
    for name in ('baseline','challenger'):
        probs=[inputs['records'][0][name]['probabilities']]
        assert out['row_weighted_scores'][name]['multiclass_brier']==pytest.approx(brier_score(probs,['UP']))
        assert out['row_weighted_scores'][name]['mean_log_loss']==pytest.approx(mean_log_loss(probs,['UP']))
    assert out['baseline_minus_challenger_brier']>0
    assert out['promotion_eligible'] is False
    assert not any(out['authority'].values())
    assert inputs==original
    assert score_event_hedging_forecasts(**inputs)==out
    json.dumps(out,allow_nan=False)


def test_missing_records_and_abstentions_remain_in_denominator(inputs):
    inputs['protocol']['expected_origins'] += [dict(origin_id='o2',episode_id='event2'),dict(origin_id='o3',episode_id='event3')]
    row=deepcopy(inputs['records'][0]);row.update(origin_id='o2',episode_id='event2',challenger=None)
    inputs['records'].append(row)
    out=score_event_hedging_forecasts(**inputs)
    assert out['coverage']==dict(expected_origins=3,received_origins=2,scored_origins=1,excluded_origins=2,
        expected_episodes=3,scored_episodes=1,scored_fraction=1/3)
    assert out['exclusion_counts']==dict(missing_challenger=1,missing_record=1)


@pytest.mark.parametrize('state',['pending','unavailable'])
def test_censored_outcome_is_never_neither(inputs,state):
    inputs['records'][0]['outcome'].update(status=state,label=None,reason='same_bar_ambiguous',known_at=None)
    out=score_event_hedging_forecasts(**inputs)
    assert out['status']=='non_evaluable'
    assert out['row_weighted_scores'] is None
    assert out['equal_episode_weighted_scores'] is None
    assert out['coverage']['scored_origins']==0


def test_same_event_rows_do_not_become_independent_episodes(inputs):
    original=inputs['records'][0]
    inputs['protocol']['expected_origins'] += [dict(origin_id='o2',episode_id='event1'),dict(origin_id='o3',episode_id='event2')]
    row2=deepcopy(original);row2.update(origin_id='o2')
    row3=deepcopy(original);row3.update(origin_id='o3',episode_id='event2')
    row3['outcome']['label']='LOWER_FIRST'
    inputs['records'] += [row2,row3]
    out=score_event_hedging_forecasts(**inputs)
    assert out['coverage']['scored_origins']==3
    assert out['coverage']['scored_episodes']==2
    assert out['equal_episode_weighted_scores']['challenger'] != out['row_weighted_scores']['challenger']
    assert len(out['by_episode'])==2
    assert out['by_episode'][0]['scored_origins']==2


def test_zero_probability_of_realized_label_is_infinite_loss_not_clipped(inputs):
    inputs['records'][0]['challenger']['probabilities']=[0.,.5,.5]
    out=score_event_hedging_forecasts(**inputs)
    loss=out['row_weighted_scores']['challenger']
    assert loss['mean_log_loss'] is None
    assert loss['log_loss_state']=='infinite'
    assert loss['multiclass_brier']==pytest.approx(1.5)
    assert out['equal_episode_weighted_scores']['challenger']['log_loss_state']=='infinite'
    json.dumps(out,allow_nan=False)


@pytest.mark.parametrize('field,value',[
    ('issued_at','2026-10-08T14:00:01Z'),('features_known_at','2026-10-08T14:00:01Z'),
    ('training_labels_known_at','2026-10-08T14:00:01Z'),('issued_at','2026-10-08T14:00:00'),
    ('model_ref','wrong-model'),('receipt_ref',''),('probabilities',[True,0,0]),
    ('probabilities',[.3,.3,.3]),('probabilities',[-.1,.5,.6]),('probabilities',[math.nan,.5,.5]),
    ('probabilities',[math.inf,0,0]),('probabilities',[.5,.5]),
])
def test_bad_or_leaked_forecast_is_refused(inputs,field,value):
    inputs['records'][0]['challenger'][field]=value
    with pytest.raises(ValueError):score_event_hedging_forecasts(**inputs)


@pytest.mark.parametrize('field,value',[
    ('target_ref','other'),('horizon_minutes',30),('security_id','other'),
    ('episode_id','other'),('origin_id','foreign'),('target_window_ref',''),
    ('decision_at','2026-10-08T13:00:00Z'),('target_end_at','2026-10-08T15:01:00Z'),
    ('target_end_at','2026-10-08T14:00:00Z'),
])
def test_incomparable_or_misstated_target_refused(inputs,field,value):
    inputs['records'][0][field]=value
    with pytest.raises(ValueError):score_event_hedging_forecasts(**inputs)


def test_evaluation_episode_cannot_be_a_training_episode(inputs):
    inputs['protocol']['training_episode_ids'].append('event1')
    with pytest.raises(ValueError,match='overlaps'):score_event_hedging_forecasts(**inputs)


def test_duplicate_record_cannot_inflate_sample(inputs):
    inputs['protocol']['expected_origins'].append(dict(origin_id='o2',episode_id='event1'))
    inputs['records'].append(deepcopy(inputs['records'][0]))
    with pytest.raises(ValueError,match='duplicate'):score_event_hedging_forecasts(**inputs)


def test_immature_or_future_outcome_receipts(inputs):
    inputs['records'][0]['outcome']['known_at']='2026-10-08T14:59:00Z'
    with pytest.raises(ValueError,match='mature'):score_event_hedging_forecasts(**inputs)
    inputs['records'][0]['outcome']['known_at']='2026-10-09T14:59:00Z'
    out=score_event_hedging_forecasts(**inputs)
    assert out['status']=='non_evaluable'
    assert out['exclusion_counts']=={'outcome_not_yet_available':1}


def test_neither_is_a_real_mature_label_not_missing(inputs):
    inputs['records'][0]['outcome']['label']='NEITHER'
    out=score_event_hedging_forecasts(**inputs)
    assert out['coverage']['scored_origins']==1
    assert out['row_weighted_scores']['challenger']['mean_log_loss']==pytest.approx(-math.log(.2))


def test_protocol_must_predate_test_window_and_evaluation_after_window(inputs):
    inputs['protocol']['registered_at']='2026-10-08T13:31:00Z'
    with pytest.raises(ValueError):score_event_hedging_forecasts(**inputs)
    inputs['protocol']['registered_at']='2026-10-01T12:00:00Z'
    inputs['evaluated_at']='2026-10-08T19:00:00Z'
    with pytest.raises(ValueError):score_event_hedging_forecasts(**inputs)


def test_receipt_change_invalidates_calculation_identity(inputs):
    before=score_event_hedging_forecasts(**inputs)
    inputs['records'][0]['outcome']['receipt_ref']='fixture:corrected-v2'
    after=score_event_hedging_forecasts(**inputs)
    assert before['input_digest']!=after['input_digest']
    assert before['content_id']!=after['content_id']
