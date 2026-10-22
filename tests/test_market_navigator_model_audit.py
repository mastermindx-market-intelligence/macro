from scripts.research.market_navigator_model_audit import audit


def test_audit_is_bounded_reproducible_and_reuses_kernel():
    a = audit()
    assert a == audit()
    assert a['n_pre_expiry_cases'] == 224
    assert a['n_one_day_cases'] == 56
    assert a['finite_changes_within_unit_bound']
    assert a['max_relative_finite_difference_charm_error'] < 1e-5
    assert a['n_one_day_extrapolations_violating_delta_bound'] > 0
    assert a['max_hedge_error_units_per_contract'] > 1
    assert not any(a['authority'].values())
    assert len(a['source_sha256']) == 64
