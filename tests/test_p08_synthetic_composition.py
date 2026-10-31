from __future__ import annotations

"""Synthetic composition falsifiers, not Q02 E2 or a forecast experiment."""

import ast
import dataclasses
import inspect
import math
from pathlib import Path

import pytest

from research.options_estate import p08_synthetic_composition as mod


def member(**changes):
    values = dict(strike=120.0, remaining_years=0.5, sigma=0.2, rate=0.03,
                  multiplier=100.0, open_interest=10, position_sign=-1,
                  continuous_yield=0.0, discrete_dividends=())
    return mod.SyntheticPut(**(values | changes))


def case(**changes):
    return mod.SyntheticCase(**(dict(members=(member(),), reference_spot=100.0,
                                    spots=(100.0,), elapsed_years=(0.0,)) | changes))


def refinement(value, status="CONVERGED"):
    return mod.reference.Refinement(status, value if status == "CONVERGED" else None,
                                    0.0, None, (1.0, 3.0) if status == "INTERVAL" else None,
                                    None if status == "CONVERGED" else "test_refusal", (value,) * 3)


def qualification(**changes):
    values = {name: refinement(value) for name, value in
              dict(price=21.0, delta=-0.6, gamma=0.02, vanna=0.03, charm=0.04).items()}
    return mod.reference.Qualification(values | changes, None, False, 0,
                                       mod.reference.GRID_LEVELS, mod.reference.VOL_BUMP)


@pytest.fixture
def solver(monkeypatch):
    calls = []

    def solve(*args, **kwargs):
        calls.append((args, kwargs))
        return qualification()

    monkeypatch.setattr(mod.reference, "qualify_fd", solve)
    return calls


def test_same_population_dollar_units_and_endpoint_sign(monkeypatch):
    def solve(spot, *_args, **_kwargs):
        return qualification(delta=refinement(-0.6 if spot == 100 else -0.5))
    monkeypatch.setattr(mod.reference, "qualify_fd", solve)
    surface = mod.compose_synthetic(case(spots=(101.0,)))
    cell = surface.cells[0]
    # Short puts: gamma/Vanna/Charm sign is explicit assumed inventory.
    assert cell.exposures["gamma"].value == pytest.approx(-10 * 100 * 0.02 * 101**2 * 0.01)
    assert cell.exposures["vanna"].value == pytest.approx(-10 * 100 * 0.03 * 101 * 0.01)
    assert cell.exposures["charm"].value == pytest.approx(-10 * 100 * 0.04 * 101 / 365)
    assert cell.hedge.anchor_shares.value == -600
    assert cell.hedge.endpoint_shares.value == -500
    assert cell.hedge.change_shares == 100
    assert cell.hedge.reference_notional_usd == 10000
    assert cell.hedge.reference_notional_usd != 101 * -500 - 100 * -600


def test_unchanged_delta_is_zero_rehedge_despite_spot_revaluation(solver):
    cell = mod.compose_synthetic(case(spots=(101.0,))).cells[0]
    assert cell.hedge.change_shares == cell.hedge.reference_notional_usd == 0


def test_opposite_positions_cancel_without_losing_members(solver):
    cell = mod.compose_synthetic(case(members=(member(), member(position_sign=1)))).cells[0]
    for total in cell.exposures.values():
        assert total.value == 0 and total.required_members == total.converged_members == 2
    assert cell.hedge.change_shares == 0


@pytest.mark.parametrize("quantity", ["gamma", "vanna", "charm", "delta"])
@pytest.mark.parametrize("status", ["INTERVAL", "UNAVAILABLE", "UNKNOWN"])
def test_one_nonconverged_member_withholds_only_corresponding_complete_quantity(monkeypatch, quantity, status):
    def solve(_spot, strike, *_args, **_kwargs):
        return qualification(**{quantity: refinement(2.0, status)}) if strike == 121 else qualification()
    monkeypatch.setattr(mod.reference, "qualify_fd", solve)
    cell = mod.compose_synthetic(case(members=(member(), member(strike=121.0)))).cells[0]
    ref = cell.members[1].qualification.quantities[quantity]
    assert ref.status == status and ref.value is None
    if quantity == "delta":
        assert cell.hedge.change_shares is None and cell.hedge.anchor_shares.value is None
        assert all(total.value is not None for total in cell.exposures.values())
    else:
        total = cell.exposures[quantity]
        assert total.value is None and total.required_members == 2 and total.converged_members == 1
        assert all(v.value is not None for k, v in cell.exposures.items() if k != quantity)
    if status == "INTERVAL":
        assert ref.interval == (1.0, 3.0)  # no midpoint or discarded interval


@pytest.mark.parametrize("bad", [None, math.nan, math.inf])
def test_forged_converged_nonfinite_value_is_not_a_contributor(monkeypatch, bad):
    monkeypatch.setattr(mod.reference, "qualify_fd", lambda *a, **k: qualification(gamma=refinement(bad)))
    assert mod.compose_synthetic(case()).cells[0].exposures["gamma"].value is None


def test_zero_oi_is_exact_zero_not_a_fabricated_greek(solver):
    cell = mod.compose_synthetic(case(members=(member(open_interest=0, sigma=0.01),))).cells[0]
    assert solver == []
    assert cell.members[0].zero_oi and cell.members[0].qualification is None
    for total in cell.exposures.values():
        assert total.value == 0 and total.required_members == 0 and total.zero_oi_members == 1


def test_zero_oi_retained_alongside_positive_member(solver):
    cell = mod.compose_synthetic(case(members=(member(), member(open_interest=0)))).cells[0]
    assert len(cell.members) == 2
    assert len(solver) == 1  # baseline and unchanged endpoint share a solve
    assert cell.exposures["gamma"].required_members == 1
    assert cell.exposures["gamma"].zero_oi_members == 1


def test_continuous_time_and_fixed_solver_domain_no_floor_or_tuning(solver):
    remaining, elapsed = 0.5, 1.23456789 / (365 * 86400)
    mod.compose_synthetic(case(elapsed_years=(elapsed,)))
    assert len(solver) == 2
    assert solver[1][0][2] == remaining - elapsed
    assert solver[1][0][5] == 0
    assert solver[1][1] == dict(is_call=False, american=True, dividends=(), levels=(100, 200, 400))


@pytest.mark.parametrize("changes", [
    dict(multiplier=None), dict(multiplier=0), dict(multiplier=True), dict(strike=math.nan),
    dict(rate=-0.01), dict(rate=0.51), dict(continuous_yield=0.01), dict(continuous_yield=False),
    dict(discrete_dividends=((0.1, 2.0),)), dict(discrete_dividends=[]),
    dict(sigma=0), dict(remaining_years=0), dict(open_interest=None),
    dict(open_interest=-1), dict(open_interest=True), dict(position_sign=0),
])
def test_invalid_member_fails_before_any_solve(solver, changes):
    with pytest.raises(ValueError):
        mod.compose_synthetic(case(members=(member(), member(**changes))))
    assert solver == []


@pytest.mark.parametrize("elapsed", [0.5, 0.50001])
def test_no_expired_member_drop_even_zero_oi(solver, elapsed):
    with pytest.raises(ValueError, match="expiry"):
        mod.compose_synthetic(case(members=(member(open_interest=0),), elapsed_years=(elapsed,)))
    assert solver == []


@pytest.mark.parametrize("changes", [
    dict(members=()), dict(members=[member()]), dict(members=(member(),) * 5),
    dict(spots=(100.0,) * 2), dict(spots=tuple(range(100, 105))), dict(spots=(0,)),
    dict(elapsed_years=(-0.1,)), dict(reference_spot=math.inf),
    dict(members=(member(),) * 4, spots=(98., 99., 100., 101.), elapsed_years=(0.0,)),
])
def test_case_and_compute_bounds_fail_before_solver(solver, changes):
    with pytest.raises(ValueError):
        mod.compose_synthetic(case(**changes))
    assert solver == []


def test_source_payload_and_spoofed_synthetic_marker_have_no_parser(solver):
    payload = dict(synthetic=True, qualification="qualified", root="SPY", source_ref="retained",
                   expected_contracts=1, members=[dataclasses.asdict(member())])
    with pytest.raises(TypeError):
        mod.compose_synthetic(payload)
    with pytest.raises(TypeError):
        mod.compose_synthetic(case(members=(payload,)))
    class SourceCase(mod.SyntheticCase):
        pass
    with pytest.raises(TypeError):
        mod.compose_synthetic(SourceCase(**dataclasses.asdict(case())))
    with pytest.raises(TypeError):
        mod.SyntheticPut(**(dataclasses.asdict(member()) | {"source_ref": "retained"}))
    assert solver == []


def test_solver_error_cannot_return_a_partial_surface(monkeypatch):
    def fail(*a, **k):
        raise ArithmeticError("synthetic numerical failure")
    monkeypatch.setattr(mod.reference, "qualify_fd", fail)
    with pytest.raises(ArithmeticError):
        mod.compose_synthetic(case())


def test_actual_fixed_grid_put_preserves_reference_status_and_independent_price_control():
    surface = mod.compose_synthetic(case())  # one actual N/2N/4N solve, cached at zero shock
    q = surface.baseline[0].qualification
    assert q is surface.cells[0].members[0].qualification
    assert q.levels == (100, 200, 400)
    price = q.quantities["price"].levels[-1]
    crr = mod.reference.crr_price(100, 120, 0.5, 0.2, 0.03, 0.0, False, True, steps=2000)
    assert abs(price - crr) <= 0.02  # unchanged Q02 independent-price tolerance
    assert price >= 20 and crr - mod.reference.bs_price(100, 120, 0.5, 0.2, False, 0.03, 0) > 0.1
    for name in mod.METRICS:
        ref = q.quantities[name]
        total = surface.cells[0].exposures[name]
        assert (total.value is not None) == (ref.status == mod.reference.CONVERGED)
        if ref.status != mod.reference.CONVERGED:
            assert ref.value is None  # no attempt to tune into numeric availability


def test_actual_vol_boundary_keeps_vanna_unavailable():
    surface = mod.compose_synthetic(case(members=(member(strike=100, sigma=0.01),)))
    q = surface.baseline[0].qualification
    assert q.quantities["vanna"].status == mod.reference.UNAVAILABLE
    assert q.quantities["vanna"].reason == "vol_bump_out_of_bounds"
    assert surface.cells[0].exposures["vanna"].value is None


def test_research_only_imports_and_no_production_caller():
    source = inspect.getsource(mod)
    tree = ast.parse(source)
    imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    imports |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert imports == {"__future__", "math", "dataclasses", "types", "typing", "engine"}
    assert mod.RESEARCH_ONLY and mod.reference.RESEARCH_ONLY
    assert mod.reference.VERDICT == "INSUFFICIENT_DATA"
    assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                   and n.func.id in {"open", "exec", "eval", "__import__"} for n in ast.walk(tree))
    root = Path(__file__).resolve().parents[1]
    for directory in ("engine", "api", "lib", "scripts", "server", "app"):
        for path in (root / directory).rglob("*.py"):
            assert "p08_synthetic_composition" not in path.read_text(), path
