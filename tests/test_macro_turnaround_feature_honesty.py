from datetime import date, timedelta
import pytest
from engine.macro_turnaround import Observation, IndicatorSpec, MacroTurnaroundEngine, build_research_artifact

@pytest.mark.parametrize('shape',['flat','first_shock','steady_growth','steady_contraction'])
def test_unidentifiable_feature_scale_is_not_confident_neutral_evidence(shape):
    values=[100.0]*48
    if shape=='first_shock':values[-1]=150.0
    elif shape=='steady_growth':values=[100.0+i for i in range(48)]
    elif shape=='steady_contraction':values=[100.0-i for i in range(48)]
    series=[Observation(date(2018+i//12,i%12+1,1),v,date(2018+i//12,i%12+1,1)+timedelta(days=35)) for i,v in enumerate(values)]
    result=MacroTurnaroundEngine().assess({'x':series},[IndicatorSpec('x','activity')],series[-1].available_at)
    assert result.quality.excluded=={'x':'unidentifiable_feature_scale'}
    assert result.confidence==0.0
    assert not result.signals
    artifact=build_research_artifact(result)
    assert artifact['score_status']=='unavailable'
    assert artifact['numeric_interpretation']['standardized_slopes']=='historical_anomaly_not_economic_direction'

def test_horizon_metadata_does_not_claim_a_calibrated_forecast_horizon():
    import math
    from engine.macro_turnaround import TurnaroundConfig
    series=[Observation(date(2018+i//12,i%12+1,1),100+math.sin(i/3),date(2018+i//12,i%12+1,1)+timedelta(days=35)) for i in range(48)]
    artifacts=[]
    for h in (3,12):
        a=MacroTurnaroundEngine(TurnaroundConfig(horizon_months=h)).assess({'x':series},[IndicatorSpec('x','activity')],series[-1].available_at)
        artifacts.append(build_research_artifact(a))
    assert artifacts[0]['raw_scores']==artifacts[1]['raw_scores']
    assert artifacts[0]['numeric_interpretation']['horizon_months']=='research_label_not_validated_forecast_horizon'
    assert not artifacts[0]['authority']['calibrated_forecast']
