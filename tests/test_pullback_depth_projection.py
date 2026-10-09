"""Synthetic arithmetic contracts; not evidence of forecasting skill."""
import importlib
from math import inf, nan

import pytest


def project(*args):
    try:
        module = importlib.import_module("lib.pullback_depth_projection")
    except ModuleNotFoundError as exc:
        pytest.fail(f"depth projection implementation is absent: {exc}")
    return module.project_total_drawdown(*args)


def test_paper_example_compounds_from_current_price():
    result = project(100, 93.2, 92.6, [1 - 91 / 93.2, 1 - 88 / 93.2])
    assert result == pytest.approx((0.09, 0.12))


def test_rebound_does_not_erase_the_prior_worst_drawdown():
    assert project(100, 96, 90, [0, 0.02, 0.12]) == pytest.approx((0.10, 0.10, 0.1552))


def test_losses_compound_and_total_loss_is_supported():
    assert project(100, 80, 80, [0.1, 1]) == pytest.approx((0.28, 1))


def test_zero_additional_loss_at_the_current_low():
    assert project(100, 93, 93, [0]) == pytest.approx((0.07,))


def test_reclaimed_peak_retains_past_damage_without_granting_authority():
    assert project(100, 100, 90, [0, 0.05, 0.2]) == pytest.approx((0.1, 0.1, 0.2))


def test_repeated_quantiles_are_valid_and_input_is_not_mutated():
    losses = [0.02, 0.02, 0.05]
    result = project(100, 95, 90, losses)
    assert result == pytest.approx((0.1, 0.1, 0.1))
    assert losses == [0.02, 0.02, 0.05]
    assert isinstance(result, tuple)


@pytest.mark.parametrize("scale", [0.001, 1, 1000, 1e8])
def test_price_scale_does_not_change_loss(scale):
    assert project(100 * scale, 93.2 * scale, 92.6 * scale, [0, 0.1]) == pytest.approx((0.074, 0.1612))


@pytest.mark.parametrize("prices", [
    (0, 90, 80), (-1, 90, 80), (100, 0, 0), (100, 90, -1),
    (100, 101, 90), (100, 90, 95), (True, 1, 1),
    (100, True, 1), (100, 90, False), ("100", 90, 80),
    (nan, 90, 80), (100, inf, 80), (100, 90, nan),
])
def test_rejects_invalid_or_incoherent_prices(prices):
    with pytest.raises(ValueError):
        project(*prices, [0.05])


@pytest.mark.parametrize("losses", [
    [], None, "0.05", b"0.05", {0.05}, [False], [nan], [inf],
    [-0.01], [1.01], ["0.05"], [0.2, 0.1],
])
def test_rejects_invalid_or_unordered_quantiles(losses):
    with pytest.raises(ValueError):
        project(100, 90, 85, losses)


@pytest.mark.parametrize("current", [55, 80, 97, 100])
def test_projection_is_bounded_ordered_and_preserves_worst(current):
    trough = current * 0.95
    result = project(100, current, trough, [0, 0.02, 0.25, 1])
    assert result == tuple(sorted(result))
    assert all(1 - trough / 100 <= loss <= 1 for loss in result)
    assert result[-1] == 1
