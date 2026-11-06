"""Pure domain resource boundaries; no actual task selection or private reads."""
import math

import pytest

from engine.research_factory import market_memory_contextual_registration as control


def node_object(total):
    # One dict, its string key, its list, then scalar elements.
    return {"nodes": [None] * (total - 3)}


def test_control_node_boundary_is_unchanged_and_domains_have_separate_finite_limit():
    assert control.MAX_NODES == 20000
    assert control.MAX_DOMAIN_NODES == 200000
    control._snapshot(node_object(control.MAX_NODES))
    with pytest.raises(control.E0ControlError, match="control_metadata_complexity_limit"):
        control._snapshot(node_object(control.MAX_NODES + 1))
    value = node_object(control.MAX_DOMAIN_NODES)
    detached, body = control._domain_snapshot(value)
    assert detached == value and control._domain_json(body) == value
    with pytest.raises(control.E0ControlError, match="domain_metadata_complexity_limit"):
        control._domain_snapshot(node_object(control.MAX_DOMAIN_NODES + 1))
    with pytest.raises(control.E0ControlError, match="invalid_domain_json"):
        control._domain_json(body[:-2] + b",null]}")


@pytest.mark.parametrize("domain,limit", [(False, 1024 * 1024), (True, 4 * 1024 * 1024)])
def test_exact_canonical_byte_boundary_without_changing_control_budget(domain, limit):
    snapshot = control._domain_snapshot if domain else control._snapshot
    value = {"x": "a" * (limit - len(b'{"x":""}'))}
    detached, body = snapshot(value)
    assert len(body) == limit and detached == value
    value["x"] += "a"
    with pytest.raises(control.E0ControlError, match=("domain" if domain else "control") + "_metadata_byte_limit"):
        snapshot(value)


def test_domain_parser_rejects_oversized_or_nonbyte_input_before_parsing():
    for body in (b" " * (control.MAX_DOMAIN_OBJECT_BYTES + 1), "{}", bytearray(b"{}"), b""):
        with pytest.raises(control.E0ControlError, match="bounded_domain_bytes_required"):
            control._domain_json(body)


def test_domain_and_control_depth_limits_remain_the_same():
    value = {"leaf": None}
    for _ in range(control.MAX_DEPTH - 1):
        value = {"x": value}
    for snapshot in (control._snapshot, control._domain_snapshot):
        snapshot(value)
        with pytest.raises(control.E0ControlError, match="metadata_complexity_limit"):
            snapshot({"one_too_deep": value})


@pytest.mark.parametrize("value", [{"x": math.nan}, {"x": math.inf}, {1: "bad-key"},
                                    {"x": (1, 2)}, {"x": "\ud800"}])
def test_domain_snapshot_keeps_strict_native_finite_unicode_rules(value):
    with pytest.raises(control.E0ControlError):
        control._domain_snapshot(value)


def test_domain_snapshot_rejects_cycles_subclasses_and_json_duplicate_keys():
    class Impostor(dict):
        pass
    cycle = {}
    cycle["x"] = cycle
    for value in (cycle, Impostor(x=1)):
        with pytest.raises(control.E0ControlError):
            control._domain_snapshot(value)
    with pytest.raises(control.E0ControlError, match="invalid_domain_json"):
        control._domain_json(b'{"x":1,"x":2}')


def test_domain_snapshot_is_detached_and_existing_owner_budgets_stay_fixed():
    source = {"nested": ["untouched"]}
    detached, _ = control._domain_snapshot(source)
    detached["nested"].clear()
    assert source == {"nested": ["untouched"]}
    assert control.MAX_CONTROL_BYTES == 1024 * 1024
    assert control.MAX_DOMAIN_OBJECT_BYTES == 4 * 1024 * 1024
    assert control.MAX_DOMAIN_TOTAL_BYTES == 32 * 1024 * 1024
    assert control.MAX_DOMAIN_OBJECTS == 64
