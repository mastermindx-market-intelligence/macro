"""Bounded three-way planner for Macro Caddy native-JSON host-route overlays.

``plan_routes(previous_source, candidate_source, active)`` reconciles two
consecutive public Caddy native-JSON source generations against the complete
active config and returns a DEEP COPY of the complete active config with ONLY
the supported source-derived changed-host route edits applied.  Inputs are
never mutated, and nothing here touches the network, filesystem, host state or
any Caddy process: it is a pure standard-library planner.

Supported edit envelope (everything else refuses, fail closed):

* source servers are identified by their exact unique ``listen`` tuple, never
  by name or ordinal, and source host routes by their exact sorted literal
  host set in the top-level match;
* a changed host route is replaced in place at its existing active position;
* adapter-generated ``group`` names matching ``group[0-9]+`` are compared
  modulo their numeric suffix and remapped onto the existing active group
  names at the same document-order occurrence, so opaque active IDs are
  preserved exactly (no renaming, no broad string replacement).

Intentionally unsupported (ReconcileRefusal, never guessed around):

* wildcard/non-literal host matchers, multi-set top-level matches, and any
  route in a compared source server lacking a simple host-only match;
* source changes to server/listen membership, host inventories, non-route
  server fields, TLS apps, global options or any other non-route config;
* changed group topology: added/removed group references, transitions between
  generated (``group[0-9]+``) and opaque group names, or inconsistent
  renumbering of generated names;
* unrelated same-host drift: an active host route whose normalized full
  content does not equal the FULL previous source host route;
* ambiguous active targets: zero or multiple active routes for one host set.
"""

from __future__ import annotations

import copy
import re

__all__ = ["ReconcileRefusal", "plan_routes"]

# Adapter-generated group names that may be renumbered between generations.
_GENERATED_GROUP_RE = re.compile(r"^group[0-9]+$")

# Marker used only inside normalized comparison structures.  A tuple cannot
# occur in JSON-decoded data, so it can never collide with real content.
_GENERATED_GROUP_MARKER = ("__macro_caddy_generated_group__",)


class ReconcileRefusal(ValueError):
    """Raised when a requested overlay is outside the supported envelope."""


# ---------------------------------------------------------------------------
# normalization / comparison helpers
# ---------------------------------------------------------------------------


def _require_mapping(value, what):
    if not isinstance(value, dict):
        raise ReconcileRefusal("%s must be a native JSON object" % what)
    return value


def _normalize(node, key=None):
    """Group-normalized view: generated ``group`` values become a marker."""
    if isinstance(node, dict):
        return {k: _normalize(v, k) for k, v in node.items()}
    if isinstance(node, list):
        return [_normalize(v, key) for v in node]
    if key == "group" and isinstance(node, str) and _GENERATED_GROUP_RE.match(node):
        return _GENERATED_GROUP_MARKER
    return node


def _canonical_route(route):
    """Group-normalized route with the top-level host list order-insensitive."""
    normalized = _normalize(route)
    match = normalized.get("match")
    if isinstance(match, list) and len(match) == 1 and isinstance(match[0], dict):
        hosts = match[0].get("host")
        if isinstance(hosts, list) and all(isinstance(h, str) for h in hosts):
            matcher = dict(match[0])
            matcher["host"] = sorted(hosts)
            canonical = dict(normalized)
            canonical["match"] = [matcher]
            return canonical
    return normalized


def _group_occurrences(node):
    """Document-order ``(path, raw_value)`` of every ``group`` string value."""
    occurrences = []

    def walk(value, key, path):
        if isinstance(value, dict):
            for child_key, child in value.items():
                walk(child, child_key, path + (child_key,))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, key, path + (index,))
        elif key == "group" and isinstance(value, str):
            occurrences.append((path, value))

    walk(node, None, ())
    return occurrences


def _set_at_path(node, path, value):
    cursor = node
    for part in path[:-1]:
        cursor = cursor[part]
    cursor[path[-1]] = value


def _subtree(node, path):
    for part in path:
        node = node[part]
    return node


# ---------------------------------------------------------------------------
# structure validation
# ---------------------------------------------------------------------------


def _http_servers(config, what):
    _require_mapping(config, what)
    apps = config.get("apps")
    if not isinstance(apps, dict):
        raise ReconcileRefusal("%s: missing 'apps' object" % what)
    http = apps.get("http")
    if not isinstance(http, dict):
        raise ReconcileRefusal("%s: missing 'apps.http' object" % what)
    servers = http.get("servers")
    if not isinstance(servers, dict) or not servers:
        raise ReconcileRefusal("%s: missing or empty 'apps.http.servers'" % what)
    return servers


def _listen_index(servers, what):
    """Map exact unique listen tuples to ``(server_name, server)``."""
    index = {}
    for name, server in servers.items():
        if not isinstance(server, dict):
            raise ReconcileRefusal("%s: server %r must be an object" % (what, name))
        listen = server.get("listen")
        if (
            not isinstance(listen, list)
            or not listen
            or not all(isinstance(addr, str) and addr for addr in listen)
        ):
            raise ReconcileRefusal(
                "%s: server %r has a missing/unsupported listen array" % (what, name)
            )
        key = tuple(listen)
        if key in index:
            raise ReconcileRefusal(
                "%s: servers %r and %r share listen array %s"
                % (what, index[key][0], name, list(key))
            )
        index[key] = (name, server)
    return index


def _without_routes(server):
    return {k: v for k, v in server.items() if k != "routes"}


def _non_route_projection(config):
    """Everything except route arrays: servers minus routes, TLS, globals."""
    projection = copy.deepcopy(config)
    for server in projection["apps"]["http"]["servers"].values():
        if isinstance(server, dict):
            server.pop("routes", None)
    return projection


# ---------------------------------------------------------------------------
# route location
# ---------------------------------------------------------------------------


def _simple_host_match(route):
    """Literal nonwildcard host list when the route match is host-only."""
    if not isinstance(route, dict):
        return None
    match = route.get("match")
    if not isinstance(match, list) or len(match) != 1 or not isinstance(match[0], dict):
        return None
    matcher = match[0]
    if set(matcher.keys()) != {"host"}:
        return None
    hosts = matcher["host"]
    if not isinstance(hosts, list) or not hosts:
        return None
    for host in hosts:
        if not isinstance(host, str) or not host or "*" in host or "?" in host:
            return None
    return list(hosts)


def _source_host_routes(listen_key, server):
    """Map each sorted host set to its route index; refuse other shapes."""
    routes = server.get("routes")
    if routes is None:
        routes = []
    if not isinstance(routes, list):
        raise ReconcileRefusal(
            "source server with listen %s: 'routes' must be an array" % (list(listen_key),)
        )
    located = {}
    for index, route in enumerate(routes):
        hosts = _simple_host_match(route)
        if hosts is None:
            if isinstance(route, dict) and "match" not in route and route.get("terminal") is True:
                continue  # Unmatched source tail is separately required byte-identical.
            raise ReconcileRefusal(
                "source server with listen %s: route %d lacks a simple host-only "
                "top-level match (unsupported source shape)" % (list(listen_key), index)
            )
        host_key = tuple(sorted(hosts))
        if host_key in located:
            raise ReconcileRefusal(
                "source server with listen %s: duplicate host route %s"
                % (list(listen_key), list(host_key))
            )
        located[host_key] = index
    return located


def _source_order_and_fallback(server):
    """Source precedence is fixed; unmatched terminal fallback is never adopted."""
    return [("hosts", tuple(sorted(hosts))) if (hosts := _simple_host_match(route)) is not None
            else ("unchanged-fallback", route) for route in server.get("routes", [])]


def _active_route_hosts(route):
    """Host list of an active route keyed by a single host matcher set."""
    if not isinstance(route, dict):
        return None
    match = route.get("match")
    if not isinstance(match, list) or len(match) != 1 or not isinstance(match[0], dict):
        return None
    hosts = match[0].get("host")
    if not isinstance(hosts, list) or not hosts:
        return None
    if not all(isinstance(host, str) and host for host in hosts):
        return None
    return list(hosts)


def _active_route_indices_for_host(server, host_key):
    routes = server.get("routes")
    if routes is None:
        routes = []
    if not isinstance(routes, list):
        raise ReconcileRefusal(
            "active server with listen %s: 'routes' must be an array"
            % (list(host_key),)
        )
    indices = []
    for index, route in enumerate(routes):
        hosts = _active_route_hosts(route)
        if hosts is not None and tuple(sorted(hosts)) == host_key:
            indices.append(index)
    return indices


# ---------------------------------------------------------------------------
# group remapping
# ---------------------------------------------------------------------------


def _remap_candidate_groups(listen_key, host_key, prev_route, cand_route, active_route):
    """Candidate route with generated group tokens rewritten to active IDs."""
    prev_occs = _group_occurrences(prev_route)
    cand_occs = _group_occurrences(cand_route)
    active_occs = _group_occurrences(active_route)
    if not (len(prev_occs) == len(cand_occs) == len(active_occs)):
        raise ReconcileRefusal(
            "host route %s on listen %s: changed group topology (group reference "
            "count %d -> %d, active %d)"
            % (
                list(host_key),
                list(listen_key),
                len(prev_occs),
                len(cand_occs),
                len(active_occs),
            )
        )
    renumber = {}
    reverse = {}
    active_names = {}
    active_reverse = {}
    for position, (prev_occ, cand_occ, active_occ) in enumerate(
        zip(prev_occs, cand_occs, active_occs)
    ):
        prev_path, prev_value = prev_occ
        cand_path, cand_value = cand_occ
        active_path, active_value = active_occ
        if prev_path != active_path:
            raise ReconcileRefusal(
                "host route %s on listen %s: active group occurrence %d drifted to "
                "a different position (internal isolation guard)"
                % (list(host_key), list(listen_key), position)
            )
        if cand_path != prev_path:
            raise ReconcileRefusal(
                "host route %s on listen %s: changed group topology (group "
                "reference occurrence %d moved between generations)"
                % (list(host_key), list(listen_key), position)
            )
        prev_generated = bool(_GENERATED_GROUP_RE.match(prev_value))
        cand_generated = bool(_GENERATED_GROUP_RE.match(cand_value))
        if prev_generated != cand_generated:
            raise ReconcileRefusal(
                "host route %s on listen %s: unsupported group id change %r -> %r "
                "(only generated names matching group[0-9]+ may change)"
                % (list(host_key), list(listen_key), prev_value, cand_value)
            )
        if prev_generated != bool(_GENERATED_GROUP_RE.match(active_value)):
            raise ReconcileRefusal("active group topology changed between generated and opaque IDs")
        # Equality classes are semantic: normalization may rename IDs, never
        # split one shared group or merge two groups, including unchanged IDs.
        for names, reverse_names, value, label in (
            (renumber, reverse, cand_value, "candidate"),
            (active_names, active_reverse, active_value, "active"),
        ):
            if (names.setdefault(prev_value, value) != value
                    or reverse_names.setdefault(value, prev_value) != prev_value):
                raise ReconcileRefusal(
                    "inconsistent group renumbering: %s changed group topology" % label
                )
        if not cand_generated:
            if cand_value != prev_value or active_value != prev_value:
                raise ReconcileRefusal(
                    "host route %s on listen %s: opaque group id changed %r -> %r"
                    % (list(host_key), list(listen_key), prev_value, cand_value)
                )
            continue
        if cand_value == prev_value:
            continue
        if _normalize(_subtree(prev_route, cand_path[:-1])) != _normalize(
            _subtree(cand_route, cand_path[:-1])
        ):
            raise ReconcileRefusal(
                "host route %s on listen %s: changed group topology (renumbered "
                "group reference %r sits in different route content)"
                % (list(host_key), list(listen_key), prev_value)
            )
    desired = copy.deepcopy(cand_route)
    for (_prev_path, prev_value), (cand_path, cand_value), (_active_path, active_value) in zip(
        prev_occs, cand_occs, active_occs
    ):
        if cand_value != active_value and _GENERATED_GROUP_RE.match(cand_value):
            _set_at_path(desired, cand_path, active_value)
    if _canonical_route(desired) != _canonical_route(cand_route):
        raise ReconcileRefusal(
            "host route %s on listen %s: group remap altered non-group content"
            % (list(host_key), list(listen_key))
        )
    return desired


# ---------------------------------------------------------------------------
# planner
# ---------------------------------------------------------------------------


def _plan_route_array_views(previous_source, candidate_source, active):
    """Plan the source-derived changed-host route overlay onto ``active``.

    Returns a deep copy of the complete ``active`` config in which ONLY the
    supported changed source host routes have been replaced, each at its
    existing active position, with candidate group references remapped onto
    the existing active group names.  Raises :class:`ReconcileRefusal` for
    anything outside the supported envelope, before any edit is produced;
    the three inputs are never mutated.
    """
    _require_mapping(previous_source, "previous_source")
    _require_mapping(candidate_source, "candidate_source")
    _require_mapping(active, "active")

    prev_servers = _http_servers(previous_source, "previous_source")
    cand_servers = _http_servers(candidate_source, "candidate_source")
    active_servers = _http_servers(active, "active")

    prev_index = _listen_index(prev_servers, "previous_source")
    cand_index = _listen_index(cand_servers, "candidate_source")
    active_index = _listen_index(active_servers, "active")

    if set(prev_index) != set(cand_index):
        raise ReconcileRefusal(
            "source server/listen membership changed: previous %s vs candidate %s"
            % (
                sorted(list(k) for k in prev_index),
                sorted(list(k) for k in cand_index),
            )
        )

    for listen_key in sorted(prev_index):
        prev_server = prev_index[listen_key][1]
        cand_server = cand_index[listen_key][1]
        if _without_routes(prev_server) != _without_routes(cand_server):
            raise ReconcileRefusal(
                "server with listen %s: non-route server fields changed between "
                "source generations" % (list(listen_key),)
            )

    if _non_route_projection(previous_source) != _non_route_projection(candidate_source):
        raise ReconcileRefusal(
            "non-route/TLS/global source configuration changed between generations"
        )

    edits = []
    for listen_key in sorted(prev_index):
        _prev_name, prev_server = prev_index[listen_key]
        _cand_name, cand_server = cand_index[listen_key]
        prev_hosts = _source_host_routes(listen_key, prev_server)
        cand_hosts = _source_host_routes(listen_key, cand_server)
        if set(prev_hosts) != set(cand_hosts):
            raise ReconcileRefusal(
                "host inventory changed for listen %s: previous %s vs candidate %s"
                % (
                    list(listen_key),
                    sorted(list(k) for k in prev_hosts),
                    sorted(list(k) for k in cand_hosts),
                )
            )
        if _source_order_and_fallback(prev_server) != _source_order_and_fallback(cand_server):
            raise ReconcileRefusal("source host precedence or unmatched terminal fallback changed")
        for host_key in sorted(prev_hosts):
            prev_route = prev_server["routes"][prev_hosts[host_key]]
            cand_route = cand_server["routes"][cand_hosts[host_key]]
            if _canonical_route(prev_route) == _canonical_route(cand_route):
                continue
            edit = _plan_changed_host(
                    listen_key,
                    host_key,
                    prev_route,
                    cand_route,
                    active_index,
                )
            if edit is not None:
                edits.append(edit)

    result = copy.deepcopy(active)
    result_servers = result["apps"]["http"]["servers"]
    for server_name, route_index, desired_route in edits:
        result_servers[server_name]["routes"][route_index] = desired_route
    _assert_only_planned_edits(active, result, edits)
    return result


def _plan_changed_host(listen_key, host_key, prev_route, cand_route, active_index):
    """Validate and build the single replacement for one changed host route."""
    if listen_key not in active_index:
        raise ReconcileRefusal(
            "no active server with listen %s for changed host route %s"
            % (list(listen_key), list(host_key))
        )
    active_name, active_server = active_index[listen_key]
    indices = _active_route_indices_for_host(active_server, host_key)
    if not indices:
        raise ReconcileRefusal(
            "active server with listen %s has no host route for %s"
            % (list(listen_key), list(host_key))
        )
    if len(indices) > 1:
        raise ReconcileRefusal(
            "active server with listen %s has %d ambiguous host routes for %s"
            % (list(listen_key), len(indices), list(host_key))
        )
    route_index = indices[0]
    active_route = active_server["routes"][route_index]
    if _canonical_route(active_route) not in (_canonical_route(prev_route), _canonical_route(cand_route)):
        raise ReconcileRefusal(
            "active host route %s on listen %s does not equal the FULL previous "
            "source route (unrelated same-host drift is not overwritten)"
            % (list(host_key), list(listen_key))
        )
    desired_route = _remap_candidate_groups(
        listen_key, host_key, prev_route, cand_route, active_route
    )
    if desired_route == active_route:
        return None  # idempotent no-write: active already matches the candidate
    return (active_name, route_index, desired_route)


def _channel_view(config, errors):
    """Present one existing route array to the same strict host-group planner."""
    view = copy.deepcopy(config)
    for server in _http_servers(view, "route channel").values():
        error_handler = server.get("errors")
        if error_handler is not None and not isinstance(error_handler, dict):
            raise ReconcileRefusal("unsupported server error-handler shape")
        error_routes = error_handler.pop("routes", []) if error_handler is not None else []
        if not isinstance(error_routes, list):
            raise ReconcileRefusal("error routes must be an array")
        if errors:
            server["routes"] = error_routes
    return view


def plan_routes(previous_source, candidate_source, active):
    """Overlay qualified ordinary and host-scoped error groups, preserving all else.

    The same listen/host identity, whole-host preimage, source order, opaque ID
    mapping and immutable-tail rules apply independently to both route arrays.
    Error-handler metadata, globals and TLS remain outside the adopted envelope.
    """
    result = copy.deepcopy(active)
    result_servers = _http_servers(result, "active")
    for errors in (False, True):
        previous_view = _channel_view(previous_source, errors)
        candidate_view = _channel_view(candidate_source, errors)
        active_view = _channel_view(active, errors)
        planned = _plan_route_array_views(previous_view, candidate_view, active_view)
        original_servers = _http_servers(active_view, "active")
        for name, planned_server in _http_servers(planned, "planned").items():
            if planned_server.get("routes") == original_servers[name].get("routes"):
                continue
            if errors:
                # A changed source group must already exist in the active
                # array; the inner planner refuses missing/ambiguous matches.
                if not isinstance(result_servers[name].get("errors"), dict):
                    raise ReconcileRefusal("active error group container missing")
                result_servers[name]["errors"]["routes"] = planned_server["routes"]
            else:
                result_servers[name]["routes"] = planned_server["routes"]
    return result


def _assert_only_planned_edits(original, result, edits):
    """Fail closed unless the result differs from active exactly as planned."""
    allowed = {
        ("apps", "http", "servers", server_name, "routes", route_index)
        for server_name, route_index, _desired in edits
        if _desired is not None
    }

    def walk(expected, actual, path):
        if len(path) >= 6 and tuple(path[:6]) in allowed:
            return
        if isinstance(expected, dict) and isinstance(actual, dict):
            if set(expected.keys()) != set(actual.keys()):
                raise ReconcileRefusal(
                    "internal isolation violation: key set changed at %s" % (list(path),)
                )
            for key in expected:
                walk(expected[key], actual[key], path + (key,))
        elif isinstance(expected, list) and isinstance(actual, list):
            if len(expected) != len(actual):
                raise ReconcileRefusal(
                    "internal isolation violation: length changed at %s" % (list(path),)
                )
            for index, (exp_item, act_item) in enumerate(zip(expected, actual)):
                walk(exp_item, act_item, path + (index,))
        elif expected != actual:
            raise ReconcileRefusal(
                "internal isolation violation: unexpected change at %s" % (list(path),)
            )

    walk(original, result, ())
