"""Calibration never turns partial evidence into a clean or measured observation."""
from tests.test_pr_linkage_validator import MANIFEST, VALID, observation


def fixture(case_id='one', expected=None, judged=None, cohort='real'):
    return {'id': case_id, 'cohort': cohort, 'observation': observation(VALID),
            'labels': {'expected_rules': expected or [], 'judged_rules': judged or ['R001'],
                       'scope': 'header-only', 'unresolved': ['native-history']}}


def test_partial_real_observation_stays_out_of_complete_denominator():
    from scripts.pr_linkage_calibration import calibrate
    case = fixture()
    case['observation']['native_linkage'].update(state='PARTIAL', pagination_complete=False,
                                               diagnostics=['UNAVAILABLE'])
    from lib.pr_linkage_validator import finalize_receipt
    case['observation'] = finalize_receipt(case['observation'], MANIFEST)
    r = calibrate([case], MANIFEST)
    assert r['cohorts']['real']['complete'] == 0
    assert r['cohorts']['real']['incomplete'] == 1
    assert r['cohorts']['real']['rules']['R001']['incomplete'] == {'tp': 0, 'fp': 0, 'fn': 0, 'tn': 1}
    assert r['cases'][0]['unresolved'] == ['native-history']


def test_missing_expected_finding_is_false_negative_even_when_report_partial():
    from scripts.pr_linkage_calibration import calibrate
    r = calibrate([fixture(expected=['R001'])], MANIFEST)
    assert r['cohorts']['real']['rules']['R001']['incomplete']['fn'] == 1
    assert r['cases'][0]['false_negative_rules'] == ['R001']


def test_observed_finding_is_only_false_positive_in_independently_judged_scope():
    from scripts.pr_linkage_calibration import calibrate
    case = fixture(judged=['R001'])
    case['observation'] = observation(VALID + '\nFixes MAS-28')
    r = calibrate([case], MANIFEST)
    assert r['cases'][0]['false_positive_rules'] == []
    assert 'R052' in r['cases'][0]['unjudged_observed_rules']
    case['labels']['judged_rules'].append('R052')
    r = calibrate([case], MANIFEST)
    assert r['cases'][0]['false_positive_rules'] == ['R052']


def test_duplicate_ids_and_unjudged_positive_labels_are_rejected():
    import pytest
    from scripts.pr_linkage_calibration import calibrate
    with pytest.raises(ValueError, match='duplicate'):
        calibrate([fixture(), fixture()], MANIFEST)
    with pytest.raises(ValueError, match='judged'):
        calibrate([fixture(expected=['R052'])], MANIFEST)


def test_synthetic_and_real_denominators_are_separate_and_inputs_unchanged():
    from lib.pr_linkage_validator import canonical_json
    from scripts.pr_linkage_calibration import calibrate
    cases = [fixture('real'), fixture('synthetic', cohort='hostile')]
    before = canonical_json(cases)
    a = calibrate(cases, MANIFEST)
    b = calibrate(cases, MANIFEST)
    assert canonical_json(a) == canonical_json(b)
    assert canonical_json(cases) == before
    assert a['cohorts']['real']['observations'] == 1
    assert a['cohorts']['hostile']['observations'] == 1
    assert a['enforcement'] == 'REPORT_ONLY'


def test_refused_metadata_with_unavailable_observation_is_still_incomplete():
    from lib.pr_linkage_validator import finalize_receipt
    from scripts.pr_linkage_calibration import calibrate
    case = fixture()
    case['labels']['unresolved'] = []
    case['observation'] = observation('No authoring declaration')
    case['observation'] = finalize_receipt(case['observation'], MANIFEST)
    row = calibrate([case], MANIFEST)['cases'][0]
    assert row['verdict'] == 'REFUSE_METADATA'
    assert row['incomplete'] is True
    assert row['completeness'] == 'UNAVAILABLE'


def test_complete_and_incomplete_judgments_have_separate_counts():
    from scripts.pr_linkage_calibration import calibrate
    a, b = fixture('partial'), fixture('complete')
    b['labels']['unresolved'] = []
    counts = calibrate([a, b], MANIFEST)['cohorts']['real']['rules']['R001']
    assert counts['complete']['tn'] == 1
    assert counts['incomplete']['tn'] == 1


def test_label_ledger_binds_exact_ids_observations_and_labels():
    import pytest
    from lib.pr_linkage_validator import digest
    from scripts.pr_linkage_calibration import bind_labels
    case = fixture()
    ledger = [{'id': case['id'], 'observation_digest': digest(case['observation']),
               'labels': case['labels']}]
    assert bind_labels([case], ledger) == [case]
    with pytest.raises(ValueError, match='identity'):
        bind_labels([case], [])
    with pytest.raises(ValueError, match='digest'):
        bind_labels([case], [{**ledger[0], 'observation_digest': '0' * 64}])
    with pytest.raises(ValueError, match='labels'):
        bind_labels([case], [{**ledger[0], 'labels': {**case['labels'], 'scope': 'changed'}}])


def test_invalid_label_types_are_rejected_instead_of_becoming_rule_characters():
    import pytest
    from scripts.pr_linkage_calibration import calibrate
    case = fixture()
    case['labels']['judged_rules'] = 'R001'
    with pytest.raises(ValueError, match='list'):
        calibrate([case], MANIFEST)


def test_operationally_invalid_case_is_counted_and_does_not_hide_other_cases():
    from scripts.pr_linkage_calibration import calibrate
    invalid = fixture('oversized')
    invalid['observation'] = observation(VALID.replace('MAS28-W1', 'X' * 81))
    report = calibrate([invalid, fixture('valid')], MANIFEST)
    assert report['status'] == 'PARTIAL_EXECUTION'
    assert report['cohorts']['real']['execution_invalid'] == 1
    assert report['cohorts']['real']['observations'] == 2
    assert len(report['cases']) == 2
    row = next(c for c in report['cases'] if c['id'] == 'oversized')
    assert row['execution_error'] == 'RESOURCE_LIMIT:value_bytes'
    assert row['false_positive_rules'] is None
    assert row['false_negative_rules'] is None
