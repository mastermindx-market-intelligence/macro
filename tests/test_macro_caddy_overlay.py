"""Hermetic tests for the Macro Caddy three-way host-route overlay planner.

All fixtures are small synthetic native-JSON configs; no host, network or
filesystem effects and no real Macro/Caddy deployment is implied.
"""

from __future__ import annotations

import copy
import json

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app/deploy"))

from macro_caddy_overlay import ReconcileRefusal, plan_routes

MMX_NOT = {
    "header": {"Referer": ["https://beta.mastermind-x.com/*"]},
    "query": {"mmx_shell": ["1"]},
}
WWW_HOST = ["www.mastermind-x.com"]


# ---------------------------------------------------------------------------
# synthetic fixture builders
# ---------------------------------------------------------------------------


def _proxy_handle(dial="127.0.0.1:8096"):
    return [{"handler": "reverse_proxy", "upstreams": [{"dial": dial}]}]


def _cache_handle():
    return [{"handler": "headers", "response": {"set": {"Cache-Control": ["no-store"]}}}]


def _movers_inner(group_id, with_not=False, extra_handle=()):
    match = [{"path": ["/movers.html"]}]
    if with_not:
        match[0] = {**match[0], "not": [copy.deepcopy(MMX_NOT)]}
    return {
        "group": group_id,
        "match": match,
        "handle": list(_proxy_handle()) + copy.deepcopy(list(extra_handle)),
    }


def _root_inner(group_id):
    return {
        "group": group_id,
        "match": [{"path": ["/"]}],
        "handle": [{"handler": "subroute", "routes": []}],
    }


def _www_host_route(inner_routes):
    return {
        "match": [{"host": list(WWW_HOST)}],
        "handle": [{"handler": "subroute", "routes": inner_routes}],
        "terminal": True,
    }


def _source_config(inner_443, inner_80):
    return {
        "apps": {
            "http": {
                "servers": {
                    "srv0": {
                        "listen": [":443"],
                        "routes": [_www_host_route(inner_443)],
                    },
                    "srv1": {
                        "listen": [":80"],
                        "routes": [_www_host_route(inner_80)],
                    },
                }
            }
        }
    }


def _previous_source():
    inner = [_root_inner("group12"), _movers_inner("group8")]
    return _source_config(copy.deepcopy(inner), copy.deepcopy(inner))


def _candidate_source(with_cache=False):
    movers = _movers_inner("group8", with_not=True, extra_handle=_cache_handle() if with_cache else ())
    inner = [_root_inner("group12"), movers]
    return _source_config(copy.deepcopy(inner), copy.deepcopy(inner))


def _active_www_inner(root_group, movers_group, drifted=False):
    movers = _movers_inner(movers_group)
    if drifted:
        movers["handle"][0]["drift_sentinel"] = "unrelated-edit"
    return [_root_inner(root_group), movers]


def _active_config(drift_443=False, drift_80=False):
    srv0_routes = [
        {
            "match": [{"host": ["legacy.os.example"]}],
            "handle": [{"handler": "static_response", "content": "os"}],
        },
        _www_host_route(_active_www_inner("group9", "group11", drift_443)),
        {
            "match": [{"host": ["livingston.internal"]}],
            "handle": [{"handler": "file_server", "root": "/srv/livingston"}],
        },
    ]
    srv1_routes = [
        _www_host_route(_active_www_inner("group21", "group25", drift_80)),
        {
            "match": [{"host": ["os-status.internal"]}],
            "handle": [{"handler": "file_server", "root": "/srv/status", "sentinel": "keep-me"}],
        },
    ]
    return {
        "admin": {"disabled": True},
        "logging": {"logs": {"default": {"level": "INFO"}}},
        "apps": {
            "http": {
                "servers": {
                    "srv0": {
                        "listen": [":443"],
                        "routes": srv0_routes,
                        "logs": {"default_logger_name": "www"},
                    },
                    "srv1": {"listen": [":80"], "routes": srv1_routes},
                    "srv9": {
                        "listen": [":8443"],
                        "routes": [
                            {
                                "match": [{"host": ["active-only.example"]}],
                                "handle": [{"handler": "static_response", "content": "only"}],
                            }
                        ],
                    },
                }
            },
            "tls": {
                "certificates": {"automate": ["www.mastermind-x.com", "os-status.internal"]},
                "sentinel": {"cache": "keep"},
            },
        },
    }


def _www_inner(config, server_name):
    routes = config["apps"]["http"]["servers"][server_name]["routes"]
    for route in routes:
        hosts = route.get("match", [{}])[0].get("host")
        if hosts == WWW_HOST:
            return route["handle"][0]["routes"]
    raise AssertionError("no www host route in fixture for %s" % server_name)


# ---------------------------------------------------------------------------
# supported overlays
# ---------------------------------------------------------------------------


def test_first_movers_delta_applies_to_both_http_and_https():
    prev, cand, active = _previous_source(), _candidate_source(), _active_config()
    snapshots = (copy.deepcopy(prev), copy.deepcopy(cand), copy.deepcopy(active))

    result = plan_routes(prev, cand, active)

    assert (prev, cand, active) == snapshots  # inputs never mutated
    assert result is not active and result["apps"] is not active["apps"]
    s0 = result["apps"]["http"]["servers"]["srv0"]["routes"]
    s1 = result["apps"]["http"]["servers"]["srv1"]["routes"]

    # order preserved: active-only routes keep their positions, www stays put
    assert [r["match"][0]["host"] for r in s0] == [
        ["legacy.os.example"],
        WWW_HOST,
        ["livingston.internal"],
    ]
    assert s0[1]["terminal"] is True
    inner0 = _www_inner(result, "srv0")
    inner0_active = _www_inner(active, "srv0")
    assert inner0[0] == inner0_active[0]  # root route untouched, group9 kept raw
    movers0 = inner0[1]
    assert movers0["group"] == "group11"  # active raw group name preserved
    assert movers0["match"] == [{"path": ["/movers.html"], "not": [copy.deepcopy(MMX_NOT)]}]
    assert movers0["handle"] == _movers_inner("group11")["handle"]
    # exactly the two match.not fields were added; nothing else in the leaf
    assert set(movers0["match"][0].keys()) == {"path", "not"}

    inner1 = _www_inner(result, "srv1")
    assert inner1[0] == _www_inner(active, "srv1")[0]
    assert inner1[1]["group"] == "group25"
    assert inner1[1]["match"] == [{"path": ["/movers.html"], "not": [copy.deepcopy(MMX_NOT)]}]

    # no generated source group number leaked anywhere
    dumped = json.dumps(result)
    assert "group8" not in dumped and "group12" not in dumped


def test_active_only_hosts_tls_global_and_order_are_byte_identical():
    prev, cand, active = _previous_source(), _candidate_source(), _active_config()
    result = plan_routes(prev, cand, active)
    rservers = result["apps"]["http"]["servers"]
    aservers = active["apps"]["http"]["servers"]
    assert result["admin"] == {"disabled": True}
    assert result["logging"] == {"logs": {"default": {"level": "INFO"}}}
    assert result["apps"]["tls"] == active["apps"]["tls"]
    assert rservers["srv9"] == aservers["srv9"]  # active-only server preserved
    assert rservers["srv0"]["logs"] == aservers["srv0"]["logs"]
    assert rservers["srv0"]["routes"][0] == aservers["srv0"]["routes"][0]
    assert rservers["srv0"]["routes"][2] == aservers["srv0"]["routes"][2]
    assert rservers["srv1"]["routes"][1] == aservers["srv1"]["routes"][1]
    assert list(rservers) == list(aservers)  # server key order preserved


def test_generated_group_number_mismatch_preserves_raw_active_names():
    prev, cand = _previous_source(), _candidate_source()
    active = _active_config()
    www0 = _www_inner(active, "srv0")
    www0[0]["group"] = "group77"
    www0[1]["group"] = "group9901"

    result = plan_routes(prev, cand, active)

    inner0 = _www_inner(result, "srv0")
    assert inner0[0]["group"] == "group77"
    assert inner0[1]["group"] == "group9901"
    assert inner0[1]["match"] == [{"path": ["/movers.html"], "not": [copy.deepcopy(MMX_NOT)]}]
    assert "group8" not in json.dumps(result) and "group12" not in json.dumps(result)


def test_second_ordinary_delta_from_first_candidate_as_baseline():
    out1 = plan_routes(_previous_source(), _candidate_source(), _active_config())
    cand2 = _candidate_source(with_cache=True)

    out2 = plan_routes(_candidate_source(), cand2, out1)

    assert out2 != out1
    for server_name, expected_group in (("srv0", "group11"), ("srv1", "group25")):
        inner = _www_inner(out2, server_name)
        movers = inner[1]
        assert movers["group"] == expected_group
        assert movers["match"] == [{"path": ["/movers.html"], "not": [copy.deepcopy(MMX_NOT)]}]
        assert movers["handle"][1] == {
            "handler": "headers",
            "response": {"set": {"Cache-Control": ["no-store"]}},
        }
        assert movers["handle"][0] == _www_inner(out1, server_name)[1]["handle"][0]
        assert inner[0] == _www_inner(out1, server_name)[0]  # root untouched
    aservers = out1["apps"]["http"]["servers"]
    bservers = out2["apps"]["http"]["servers"]
    assert bservers["srv0"]["routes"][0] == aservers["srv0"]["routes"][0]
    assert bservers["srv0"]["routes"][2] == aservers["srv0"]["routes"][2]
    assert bservers["srv1"]["routes"][1] == aservers["srv1"]["routes"][1]
    assert bservers["srv9"] == aservers["srv9"]
    assert out2["apps"]["tls"] == out1["apps"]["tls"]
    assert out2["admin"] == out1["admin"] and out2["logging"] == out1["logging"]


def test_idempotent_no_write_when_candidate_already_applied():
    out1 = plan_routes(_previous_source(), _candidate_source(), _active_config())
    baseline = copy.deepcopy(out1)

    out2 = plan_routes(_candidate_source(), _candidate_source(), out1)

    assert out2 == baseline
    assert out2 is not out1  # still a fresh deep copy


def test_planning_against_stale_baseline_refuses_as_drift():
    out1 = plan_routes(_previous_source(), _candidate_source(), _active_config())
    with pytest.raises(ReconcileRefusal, match="same-host drift"):
        # A later different C must not overwrite a B that matches neither the
        # supplied A preimage nor the full desired C. Exact current B itself is
        # a safe no-write result, covered separately.
        plan_routes(_previous_source(), _candidate_source(with_cache=True), out1)


# ---------------------------------------------------------------------------
# refusals: fail closed before any edit is produced
# ---------------------------------------------------------------------------


def test_refuses_unrelated_same_host_drift():
    prev, cand = _previous_source(), _candidate_source()
    active = _active_config(drift_443=True)
    snapshot = copy.deepcopy(active)
    with pytest.raises(ReconcileRefusal, match="same-host drift"):
        plan_routes(prev, cand, active)
    assert active == snapshot


def test_no_partial_edit_when_a_later_server_drifts():
    prev, cand = _previous_source(), _candidate_source()
    active = _active_config(drift_80=True)  # srv0 would edit cleanly, srv1 refuses
    snapshots = (copy.deepcopy(prev), copy.deepcopy(cand), copy.deepcopy(active))
    with pytest.raises(ReconcileRefusal, match="same-host drift"):
        plan_routes(prev, cand, active)
    assert (prev, cand, active) == snapshots


def test_refuses_changed_host_inventory():
    prev = _previous_source()
    cand = _candidate_source()
    extra = {
        "match": [{"host": ["new.example"]}],
        "handle": [{"handler": "static_response", "content": "x"}],
    }
    cand["apps"]["http"]["servers"]["srv0"]["routes"].append(extra)
    with pytest.raises(ReconcileRefusal, match="host inventory changed"):
        plan_routes(prev, cand, _active_config())


def test_refuses_changed_listen_membership():
    prev = _previous_source()
    cand = _candidate_source()
    cand["apps"]["http"]["servers"]["srv0"]["listen"] = [":443", "[::]:443"]
    with pytest.raises(ReconcileRefusal, match="server/listen membership changed"):
        plan_routes(prev, cand, _active_config())


def test_refuses_tls_and_global_source_changes():
    changed_tls = _candidate_source()
    changed_tls["apps"]["tls"] = {"certificates": {"automate": ["other.example"]}}
    with pytest.raises(ReconcileRefusal, match="non-route/TLS/global"):
        plan_routes(_previous_source(), changed_tls, _active_config())

    changed_global = _candidate_source()
    changed_global["admin"] = {"disabled": False}
    with pytest.raises(ReconcileRefusal, match="non-route/TLS/global"):
        plan_routes(_previous_source(), changed_global, _active_config())

    changed_server_field = _candidate_source()
    changed_server_field["apps"]["http"]["servers"]["srv1"]["logs"] = {"default_logger_name": "x"}
    with pytest.raises(ReconcileRefusal, match="non-route server fields"):
        plan_routes(_previous_source(), changed_server_field, _active_config())


def test_refuses_changed_group_topology():
    prev, cand, active = _previous_source(), _candidate_source(), _active_config()
    inner = _www_inner(cand, "srv0")
    inner.append(
        {
            "group": "group13",
            "match": [{"path": ["/extra.html"]}],
            "handle": [{"handler": "static_response", "content": "x"}],
        }
    )
    with pytest.raises(ReconcileRefusal, match="changed group topology"):
        plan_routes(prev, cand, active)


def test_refuses_unsupported_group_ids():
    prev, cand, active = _previous_source(), _candidate_source(), _active_config()
    _www_inner(cand, "srv0")[1]["group"] = "order-alpha"  # generated -> opaque
    with pytest.raises(ReconcileRefusal, match="unsupported group id change"):
        plan_routes(prev, cand, active)

    prev2, cand2, active2 = _previous_source(), _candidate_source(), _active_config()
    _www_inner(prev2, "srv0")[0]["group"] = "keep-a"
    _www_inner(cand2, "srv0")[0]["group"] = "keep-b"
    _www_inner(active2, "srv0")[0]["group"] = "keep-a"
    with pytest.raises(ReconcileRefusal, match="opaque group id changed"):
        plan_routes(prev2, cand2, active2)


def test_refuses_inconsistent_group_renumbering():
    prev, cand, active = _previous_source(), _candidate_source(), _active_config()
    # two identical root-shaped routes share the generated token "group8"
    _www_inner(prev, "srv0")[:] = [
        _root_inner("group8"),
        _root_inner("group8"),
        _movers_inner("group9"),
    ]
    _www_inner(active, "srv0")[:] = [
        _root_inner("group81"),
        _root_inner("group82"),
        _movers_inner("group93"),
    ]
    _www_inner(cand, "srv0")[:] = [
        _root_inner("group30"),  # group8 -> group30 ...
        _root_inner("group31"),  # ... and group8 -> group31: inconsistent
        _movers_inner("group9", with_not=True),
    ]
    with pytest.raises(ReconcileRefusal, match="inconsistent group renumbering"):
        plan_routes(prev, cand, active)


def test_refuses_ambiguous_duplicate_host_routes():
    cand = _candidate_source()
    cand["apps"]["http"]["servers"]["srv0"]["routes"].append(
        _www_host_route([_root_inner("group14"), _movers_inner("group8", with_not=True)])
    )
    with pytest.raises(ReconcileRefusal, match="duplicate host route"):
        plan_routes(_previous_source(), cand, _active_config())

    active = _active_config()
    active["apps"]["http"]["servers"]["srv1"]["routes"].append(
        _www_host_route([_root_inner("group21"), _movers_inner("group25")])
    )
    with pytest.raises(ReconcileRefusal, match="ambiguous host routes"):
        plan_routes(_previous_source(), _candidate_source(), active)


def test_refuses_wildcard_and_non_simple_source_matches():
    cand = _candidate_source()
    srv0 = cand["apps"]["http"]["servers"]["srv0"]
    srv0["routes"][0]["match"][0]["host"] = ["*.mastermind-x.com"]
    with pytest.raises(ReconcileRefusal, match="simple host-only"):
        plan_routes(_previous_source(), cand, _active_config())

    cand2 = _candidate_source()
    cand2["apps"]["http"]["servers"]["srv1"]["routes"][0]["match"][0]["path"] = ["/"]
    with pytest.raises(ReconcileRefusal, match="simple host-only"):
        plan_routes(_previous_source(), cand2, _active_config())

    prev3 = _previous_source()
    prev3["apps"]["http"]["servers"]["srv0"]["routes"].append(
        {"match": [{"path": ["/health"]}], "handle": [{"handler": "static_response"}]}
    )
    with pytest.raises(ReconcileRefusal, match="simple host-only"):
        plan_routes(prev3, _candidate_source(), _active_config())


def test_refuses_changed_group_reference_position_and_missing_active():
    prev, cand, active = _previous_source(), _candidate_source(), _active_config()
    inner = _www_inner(cand, "srv0")
    inner.reverse()  # group occurrence positions no longer line up
    with pytest.raises(ReconcileRefusal):
        plan_routes(prev, cand, active)

    trimmed = _active_config()
    del trimmed["apps"]["http"]["servers"]["srv1"]
    with pytest.raises(ReconcileRefusal, match="no active server with listen"):
        plan_routes(_previous_source(), _candidate_source(), trimmed)


def test_refuses_non_object_inputs():
    active = _active_config()
    for broken in (None, [], "config", 7):
        with pytest.raises(ReconcileRefusal, match="must be a native JSON object"):
            plan_routes(broken, _candidate_source(), active)
        with pytest.raises(ReconcileRefusal, match="must be a native JSON object"):
            plan_routes(_previous_source(), broken, active)
        with pytest.raises(ReconcileRefusal, match="must be a native JSON object"):
            plan_routes(_previous_source(), _candidate_source(), broken)


def test_refusal_is_value_error_and_inputs_survive_any_failure_mix():
    assert issubclass(ReconcileRefusal, ValueError)
    prev, cand, active = _previous_source(), _candidate_source(), _active_config()
    snapshots = (copy.deepcopy(prev), copy.deepcopy(cand), copy.deepcopy(active))
    for args in (
        (prev, _candidate_source(with_cache=True), active),  # unsupported delta
        (prev, prev, active),  # no change at all -> valid but no edits
    ):
        try:
            plan_routes(*args)
        except ReconcileRefusal:
            pass
    assert (prev, cand, active) == snapshots


def test_unchanged_unmatched_http_421_tail_is_preserved_without_adoption():
    previous, candidate, active = _previous_source(), _candidate_source(), _active_config()
    fallback = {'handle': [{'handler': 'static_response', 'status_code': 421}], 'terminal': True}
    for config in (previous, candidate):
        config['apps']['http']['servers']['srv1']['routes'].append(copy.deepcopy(fallback))
    active_tail = {'handle': [{'handler': 'static_response', 'body': 'unrelated-owner'}], 'terminal': True}
    active['apps']['http']['servers']['srv1']['routes'].append(copy.deepcopy(active_tail))
    result = plan_routes(previous, candidate, active)
    assert result['apps']['http']['servers']['srv1']['routes'][-1] == active_tail
    assert active['apps']['http']['servers']['srv1']['routes'][-1] == active_tail


def test_changed_unmatched_fallback_refuses():
    previous, candidate, active = _previous_source(), _candidate_source(), _active_config()
    for config, code in ((previous, 421), (candidate, 200)):
        config['apps']['http']['servers']['srv1']['routes'].append({
            'terminal': True, 'handle': [{'handler': 'static_response', 'status_code': code}]})
    with pytest.raises(ReconcileRefusal, match='precedence|fallback'):
        plan_routes(previous, candidate, active)


def test_source_host_precedence_change_refuses_even_when_each_host_is_unchanged():
    previous, candidate, active = _previous_source(), _previous_source(), _active_config()
    extra = {'match': [{'host': ['extra.example']}], 'handle': [{'handler': 'static_response', 'body': 'x'}]}
    for config in (previous, candidate):
        config['apps']['http']['servers']['srv0']['routes'].append(copy.deepcopy(extra))
    candidate['apps']['http']['servers']['srv0']['routes'].reverse()
    with pytest.raises(ReconcileRefusal, match='precedence|fallback'):
        plan_routes(previous, candidate, active)


def _with_error_groups(previous, candidate, active):
    for server_name in ('srv0', 'srv1'):
        old = _www_host_route([{'group': 'group27', 'match': [{'path': ['/old.css']}],
                               'handle': _cache_handle()}])
        new = copy.deepcopy(old)
        new['handle'][0]['routes'][0]['match'][0]['path'].append('/intl_workspace_surveillance.css')
        previous['apps']['http']['servers'][server_name]['errors'] = {'routes': [old]}
        candidate['apps']['http']['servers'][server_name]['errors'] = {'routes': [new]}
        actual = copy.deepcopy(old)
        actual['handle'][0]['routes'][0]['group'] = 'group902'
        active['apps']['http']['servers'][server_name]['errors'] = {
            'retained_error_metadata': 'active-owner',
            'routes': [{'match': [{'host': ['os.example']}], 'handle': _proxy_handle()}, actual]}
    return previous, candidate, active


def test_same_strict_overlay_applies_host_scoped_error_routes_and_preserves_other_owners():
    previous, candidate, active = _with_error_groups(_previous_source(), _candidate_source(), _active_config())
    original = copy.deepcopy(active)
    result = plan_routes(previous, candidate, active)
    for name in ('srv0', 'srv1'):
        error = result['apps']['http']['servers'][name]['errors']
        assert error['retained_error_metadata'] == 'active-owner'
        assert error['routes'][0] == original['apps']['http']['servers'][name]['errors']['routes'][0]
        body = error['routes'][1]['handle'][0]['routes'][0]
        assert body['group'] == 'group902'
        assert body['match'][0]['path'] == ['/old.css', '/intl_workspace_surveillance.css']
    assert active == original
    assert result.get('admin') == original.get('admin')
    assert result['apps'].get('tls') == original['apps'].get('tls')


def test_error_group_same_host_drift_refuses_without_partial_main_route_adoption():
    previous, candidate, active = _with_error_groups(_previous_source(), _candidate_source(), _active_config())
    active['apps']['http']['servers']['srv0']['errors']['routes'][1]['terminal'] = False
    original = copy.deepcopy(active)
    with pytest.raises(ReconcileRefusal, match='FULL previous'):
        plan_routes(previous, candidate, active)
    assert active == original


def test_error_handler_nonroute_metadata_change_remains_unsupported():
    previous, candidate, active = _with_error_groups(_previous_source(), _candidate_source(), _active_config())
    candidate['apps']['http']['servers']['srv0']['errors']['new_global_behavior'] = True
    with pytest.raises(ReconcileRefusal, match='non-route'):
        plan_routes(previous, candidate, active)


def test_error_group_source_precedence_change_refuses():
    previous, candidate, active = _with_error_groups(_previous_source(), _candidate_source(), _active_config())
    extra = {'match': [{'host': ['another.example']}], 'handle': _proxy_handle()}
    for config in (previous, candidate):
        config['apps']['http']['servers']['srv0']['errors']['routes'].append(copy.deepcopy(extra))
    candidate['apps']['http']['servers']['srv0']['errors']['routes'].reverse()
    with pytest.raises(ReconcileRefusal, match='precedence'):
        plan_routes(previous, candidate, active)


def test_already_current_candidate_is_verified_without_renaming_ids_or_noop_edit():
    previous, candidate, active = _with_error_groups(_previous_source(), _candidate_source(), _active_config())
    current = plan_routes(previous, candidate, active)
    repeated = plan_routes(previous, candidate, current)
    assert repeated == current and repeated is not current


@pytest.mark.parametrize("channel", ["ordinary", "errors"])
@pytest.mark.parametrize("changed", ["active", "candidate"])
@pytest.mark.parametrize("topology", ["split", "merge"])
def test_group_equality_classes_cannot_split_or_merge(channel, changed, topology):
    previous, candidate, active = _previous_source(), _candidate_source(), _active_config()
    old_names = ["group8", "group8", "group10"] if topology == "split" else ["group8", "group9", "group10"]
    candidate_names = list(old_names)
    active_names = ["group81", "group81", "group93"] if topology == "split" else ["group81", "group82", "group93"]
    if changed == "candidate":
        # The merge includes an unchanged name; skipping unchanged references
        # would silently erase this unsupported source transition.
        candidate_names[1] = "group9" if topology == "split" else "group8"
    else:
        active_names[1] = "group82" if topology == "split" else "group81"
    for config, names, opt_in in ((previous, old_names, False),
                                  (candidate, candidate_names, True),
                                  (active, active_names, False)):
        inner = [_root_inner(names[0]), _root_inner(names[1]),
                 _movers_inner(names[2], with_not=opt_in)]
        if channel == "errors":
            config["apps"]["http"]["servers"]["srv0"]["errors"] = {
                "routes": [_www_host_route(inner)]}
        else:
            _www_inner(config, "srv0")[:] = inner
    snapshots = copy.deepcopy((previous, candidate, active))
    with pytest.raises(ReconcileRefusal, match="group topology|group renumbering"):
        plan_routes(previous, candidate, active)
    assert (previous, candidate, active) == snapshots


@pytest.mark.parametrize("channel", ["ordinary", "errors"])
def test_shared_group_can_be_consistently_renumbered_without_losing_active_ids(channel):
    previous, candidate, active = _previous_source(), _candidate_source(), _active_config()
    for config, names, opt_in in ((previous, ['group8', 'group8', 'group10'], False),
                                  (candidate, ['group30', 'group30', 'group10'], True),
                                  (active, ['group81', 'group81', 'group93'], False)):
        inner = [_root_inner(names[0]), _root_inner(names[1]),
                 _movers_inner(names[2], with_not=opt_in)]
        if channel == 'errors':
            config['apps']['http']['servers']['srv0']['errors'] = {
                'routes': [_www_host_route(inner)]}
        else:
            _www_inner(config, 'srv0')[:] = inner
    result = plan_routes(previous, candidate, active)
    server = result['apps']['http']['servers']['srv0']
    routes = server['errors']['routes'] if channel == 'errors' else server['routes']
    body = next(route for route in routes if route.get('match') == [{'host': WWW_HOST}])
    inner = body['handle'][0]['routes']
    assert [route['group'] for route in inner] == ['group81', 'group81', 'group93']
    assert inner[-1]['match'][0]['not'] == [MMX_NOT]
