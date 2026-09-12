"""RED-first tests for engine.market_ontology.exposure_map (A-F04-W2-1).

All fixtures are in-memory (list[dict]) — no test reads or writes data/, and no test
requires a materialized theme graph store. A fake StoreView is the whole harness.
"""
from __future__ import annotations

import ast
import datetime
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

from engine.market_ontology.exposure_map import ShockSpec, compose_exposure_map, to_json

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "contracts" / "market_ontology" / "exposure_map.v1.schema.json"
MODULE_PATH = REPO_ROOT / "engine" / "market_ontology" / "exposure_map.py"


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def edge(edge_id, type_, src, dst, *, valid_from="2026-01-01", valid_to=None,
         belief_time="2026-01-01", computed_at="2026-01-01T00:00:00Z",
         evidence_time="2026-01-01", era="observed", source_class="curated",
         date_provenance="curated_changelog", evidence_refs=None,
         confidence_basis="membership_doc.v1", engine_version="theme_graph.v1"):
    return {
        "edge_id": edge_id, "type": type_, "src": src, "dst": dst,
        "valid_from": valid_from, "valid_to": valid_to, "evidence_time": evidence_time,
        "belief_time": belief_time, "era": era, "source_class": source_class,
        "date_provenance": date_provenance, "evidence_refs": evidence_refs or [],
        "confidence_basis": confidence_basis, "computed_at": computed_at,
        "engine_version": engine_version,
    }


def identity_row(node_id, *, resolution_state="RESOLVED", security_id=None,
                  listing_key=None, issuer_id=None, resolution_asof="2026-01-01",
                  refusal_reason=None):
    return {
        "node_id": node_id, "resolution_state": resolution_state,
        "security_id": security_id, "listing_key": listing_key,
        "issuer_id": issuer_id, "resolution_asof": resolution_asof,
        "refusal_reason": refusal_reason,
    }


class FakeStore:
    def __init__(self, edges, identity=None, meta=None, raise_on_read=False):
        self._edges = edges
        self._identity = identity or []
        self._meta = meta if meta is not None else {"ok": True}
        self._raise = raise_on_read

    def read_edges(self):
        if self._raise:
            raise RuntimeError("store unavailable")
        return self._edges

    def read_identity_resolution(self):
        return self._identity

    def read_meta(self):
        return self._meta

    def read_nodes(self):
        return []


CHAINS = {
    "credit_spreads_refinancing": {
        "chain": "credit_spreads_refinancing",
        "title": {"en": "Credit spreads widen -> refinancing-dependent cohort de-rate",
                   "zh": "信用利差走阔 -> 依赖再融资的板块下修"},
        "tier": "hypothesis",
    }
}


def _chain_loader():
    return CHAINS


def _allow_all(_family):
    return None


def _refuse(family_to_refuse):
    def _assert(family):
        if family == family_to_refuse:
            raise RuntimeError("refused")
    return _assert


def _spec(theme_ids, shock_id="credit_spreads_refinancing"):
    return ShockSpec(shock_id=shock_id, theme_node_ids=tuple(theme_ids), declared_by="test")


def _compose(store, spec, asof="2026-06-01", **kw):
    kw.setdefault("chain_loader", _chain_loader)
    kw.setdefault("assert_allowed", _allow_all)
    return compose_exposure_map(store, spec, asof=asof, **kw)


def test_direct_membership_projection():
    edges = [
        edge("e1", "MEMBER_OF", "co:us:AAA", "ltheme:finviz:x"),
        edge("e2", "MEMBER_OF", "co:us:BBB", "ltheme:finviz:x"),
    ]
    m = _compose(FakeStore(edges), _spec(["ltheme:finviz:x"]))
    theme = m.themes[0]
    assert theme.state == "OK"
    assert [c["company_node_id"] for c in theme.companies] == ["co:us:AAA", "co:us:BBB"]
    for c in theme.companies:
        p = c["paths"][0]
        assert p["path_kind"] == "direct_membership" and p["hops"] == 1
        assert p["edges"][0]["edge_id"] in ("e1", "e2")


def test_basket_bridge_projection():
    edges = [
        edge("e1", "MEMBER_OF", "co:cn:X", "basket:baskets_china_ths:B"),
        edge("e2", "EXPRESSES", "basket:baskets_china_ths:B", "ltheme:ths:C"),
    ]
    m = _compose(FakeStore(edges), _spec(["ltheme:ths:C"]))
    theme = m.themes[0]
    assert theme.state == "OK"
    path = theme.companies[0]["paths"][0]
    assert path["path_kind"] == "basket_bridge"
    assert path["hops"] == 2
    assert path["via_node_id"] == "basket:baskets_china_ths:B"


def test_local_theme_bridge_for_canonical_theme():
    edges = [
        edge("e1", "EXPRESSES", "ltheme:finviz:L", "theme:t1"),
        edge("e2", "MEMBER_OF", "co:us:Z", "ltheme:finviz:L"),
    ]
    m = _compose(FakeStore(edges), _spec(["theme:t1"]))
    theme = m.themes[0]
    assert theme.state == "OK"
    path = theme.companies[0]["paths"][0]
    assert path["path_kind"] == "local_theme_bridge"
    assert path["via_node_id"] == "ltheme:finviz:L"
    # Path C never chains into Path B: no basket_bridge should appear here.
    assert all(p["path_kind"] != "basket_bridge" for c in theme.companies for p in c["paths"])


def test_rights_suppression_emits_typed_null_and_leaks_nothing():
    edges = [edge("e1", "MEMBER_OF", "co:us:SECRET", "ltheme:ths:C")]
    m = _compose(FakeStore(edges), _spec(["ltheme:ths:C"]),
                 assert_allowed=_refuse("ths_concepts"))
    theme = m.themes[0]
    assert theme.state == "RIGHTS_SUPPRESSED"
    assert theme.companies is None
    dumped = json.dumps(to_json(m))
    assert "co:us:SECRET" not in dumped


def test_rights_suppressed_basket_bridge_blocks_its_members():
    edges = [
        edge("e1", "MEMBER_OF", "co:cn:X", "basket:baskets_china_ths:B"),
        edge("e2", "EXPRESSES", "basket:baskets_china_ths:B", "ltheme:ths:C"),
    ]
    m = _compose(FakeStore(edges), _spec(["ltheme:ths:C"]),
                 assert_allowed=_refuse("ths_concepts"))
    theme = m.themes[0]
    # theme's own family (ths_concepts) is also refused here since ltheme:ths: is
    # the same family — so this exercises the theme-level suppression path too.
    assert theme.state == "RIGHTS_SUPPRESSED"
    assert theme.companies is None


def test_asof_belief_filtering():
    edges = [
        edge("e1", "MEMBER_OF", "co:us:A", "ltheme:finviz:x", valid_from="2026-05-01"),
        edge("e2", "MEMBER_OF", "co:us:B", "ltheme:finviz:x", valid_to="2026-01-01"),
        edge("e3", "MEMBER_OF", "co:us:C", "ltheme:finviz:x", valid_to="2026-12-01"),
        edge("e4", "MEMBER_OF", "co:us:D", "ltheme:finviz:x", valid_from="2026-07-01"),
    ]
    m = _compose(FakeStore(edges), _spec(["ltheme:finviz:x"]), asof="2026-06-01")
    companies = {c["company_node_id"] for c in m.themes[0].companies}
    assert companies == {"co:us:A", "co:us:C"}


def test_clock_mismatch_abstention():
    edges = [edge("e1", "MEMBER_OF", "co:us:A", "ltheme:finviz:x", belief_time="2026-09-01")]
    m = _compose(FakeStore(edges), _spec(["ltheme:finviz:x"]), asof="2026-06-01")
    theme = m.themes[0]
    codes = {a["code"] for a in theme.abstentions}
    assert "BELIEF_AFTER_ASOF" in codes
    assert theme.companies is None


def test_historical_belief_recollapse():
    edges = [
        edge("e1", "MEMBER_OF", "co:us:A", "ltheme:finviz:x",
             belief_time="2026-01-01", computed_at="2026-01-01T00:00:00Z", valid_to=None),
        edge("e1", "MEMBER_OF", "co:us:A", "ltheme:finviz:x",
             belief_time="2026-08-01", computed_at="2026-08-01T00:00:00Z", valid_to="2026-07-01"),
    ]
    m_early = _compose(FakeStore(edges), _spec(["ltheme:finviz:x"]), asof="2026-03-01")
    assert m_early.themes[0].state == "OK"
    assert m_early.themes[0].companies[0]["company_node_id"] == "co:us:A"

    m_late = _compose(FakeStore(edges), _spec(["ltheme:finviz:x"]), asof="2026-09-01")
    # The later belief closed the interval (valid_to=2026-07-01), so by 2026-09-01
    # there is truly no edge in view for this theme at all.
    assert m_late.themes[0].state == "NO_THEME_EDGES"


def test_no_membership_yet_null_pre_6809():
    edges = [edge("e1", "EXPRESSES", "ltheme:ths:C", "theme:t1")]
    m = _compose(FakeStore(edges), _spec(["ltheme:ths:C"]))
    theme = m.themes[0]
    assert theme.state == "NO_MEMBERSHIP_YET"
    assert theme.companies is None
    assert theme.unavailable["reason"]["en"] and theme.unavailable["reason"]["zh"]


def test_no_theme_edges_null():
    m = _compose(FakeStore([]), _spec(["ltheme:finviz:nothing"]))
    assert m.themes[0].state == "NO_THEME_EDGES"


def test_identity_unresolved_null():
    m = _compose(FakeStore([]), _spec(["garbage:1"]))
    theme = m.themes[0]
    assert theme.state == "IDENTITY_UNRESOLVED"
    assert theme.theme_node_id == "garbage:1"


def test_shock_unknown_null():
    m = _compose(FakeStore([]), _spec(["ltheme:finviz:x"], shock_id="not_a_real_chain"))
    assert m.unavailable["code"] == "SHOCK_UNKNOWN"
    assert m.themes == ()


def test_store_unavailable_null():
    m = _compose(FakeStore([], raise_on_read=True), _spec(["ltheme:finviz:x"]))
    assert m.unavailable["code"] == "STORE_UNAVAILABLE"
    assert m.themes == ()


def test_identity_collision_abstention():
    edges = [
        edge("e1", "MEMBER_OF", "co:us:A", "ltheme:finviz:x"),
        edge("e2", "MEMBER_OF", "co:us:B", "ltheme:finviz:x"),
    ]
    identity = [
        identity_row("co:us:A", security_id="SEC:1"),
        identity_row("co:us:B", security_id="SEC:1"),
    ]
    m = _compose(FakeStore(edges, identity), _spec(["ltheme:finviz:x"]))
    theme = m.themes[0]
    assert theme.company_count == 2
    assert theme.distinct_security_count == 1
    assert any(a["code"] == "IDENTITY_COLLISION" for a in theme.abstentions)
    for c in theme.companies:
        assert c["identity"]["collision_group"] == "SEC:1"


def test_double_count_abstention():
    edges = [
        edge("e1", "MEMBER_OF", "co:cn:X", "ltheme:ths:C"),
        edge("e2", "MEMBER_OF", "co:cn:X", "basket:baskets_china_ths:B"),
        edge("e3", "EXPRESSES", "basket:baskets_china_ths:B", "ltheme:ths:C"),
    ]
    m = _compose(FakeStore(edges), _spec(["ltheme:ths:C"]))
    theme = m.themes[0]
    assert theme.company_count == 1
    assert len(theme.companies) == 1
    assert len(theme.companies[0]["paths"]) == 2
    kinds = {p["path_kind"] for p in theme.companies[0]["paths"]}
    assert kinds == {"direct_membership", "basket_bridge"}


def test_identity_never_joined_on_symbol():
    edges = [edge("e1", "MEMBER_OF", "co:us:A", "ltheme:finviz:x")]
    identity = [{"node_id": "co:us:OTHER", "resolution_state": "RESOLVED",
                 "security_id": "SEC:9", "listing_key": None, "issuer_id": None,
                 "resolution_asof": "2026-01-01", "refusal_reason": None,
                 "source_native_symbol": "A"}]
    m = _compose(FakeStore(edges, identity), _spec(["ltheme:finviz:x"]))
    company = m.themes[0].companies[0]
    assert company["identity"]["state"] == "NO_RESOLUTION_ROW"
    assert company["identity"]["security_id"] is None


@pytest.mark.parametrize("case", [
    "direct", "basket_bridge", "rights_suppressed", "no_membership", "no_theme_edges",
    "identity_unresolved", "shock_unknown", "store_unavailable", "collision",
])
def test_schema_validation_every_case(case):
    schema = _schema()
    assert schema["$id"] == "https://mastermind-x.com/contracts/market_ontology/exposure_map.v1.schema.json"

    if case == "direct":
        edges = [edge("e1", "MEMBER_OF", "co:us:A", "ltheme:finviz:x")]
        m = _compose(FakeStore(edges), _spec(["ltheme:finviz:x"]))
    elif case == "basket_bridge":
        edges = [
            edge("e1", "MEMBER_OF", "co:cn:X", "basket:baskets_china_ths:B"),
            edge("e2", "EXPRESSES", "basket:baskets_china_ths:B", "ltheme:ths:C"),
            edge("e3", "TRACKS", "etf:KWEB", "basket:baskets_china_ths:B"),
        ]
        m = _compose(FakeStore(edges), _spec(["ltheme:ths:C"]))
    elif case == "rights_suppressed":
        edges = [edge("e1", "MEMBER_OF", "co:us:A", "ltheme:ths:C")]
        m = _compose(FakeStore(edges), _spec(["ltheme:ths:C"]), assert_allowed=_refuse("ths_concepts"))
    elif case == "no_membership":
        edges = [edge("e1", "EXPRESSES", "ltheme:ths:C", "theme:t1")]
        m = _compose(FakeStore(edges), _spec(["ltheme:ths:C"]))
    elif case == "no_theme_edges":
        m = _compose(FakeStore([]), _spec(["ltheme:finviz:nothing"]))
    elif case == "identity_unresolved":
        m = _compose(FakeStore([]), _spec(["garbage:1"]))
    elif case == "shock_unknown":
        m = _compose(FakeStore([]), _spec(["ltheme:finviz:x"], shock_id="nope"))
    elif case == "store_unavailable":
        m = _compose(FakeStore([], raise_on_read=True), _spec(["ltheme:finviz:x"]))
    else:  # collision
        edges = [
            edge("e1", "MEMBER_OF", "co:us:A", "ltheme:finviz:x"),
            edge("e2", "MEMBER_OF", "co:us:B", "ltheme:finviz:x"),
        ]
        identity = [identity_row("co:us:A", security_id="SEC:1"),
                    identity_row("co:us:B", security_id="SEC:1")]
        m = _compose(FakeStore(edges, identity), _spec(["ltheme:finviz:x"]))

    jsonschema.validate(to_json(m), schema)


def test_deterministic_ordering():
    edges = [
        edge("e3", "MEMBER_OF", "co:us:CCC", "ltheme:finviz:x"),
        edge("e1", "MEMBER_OF", "co:us:AAA", "ltheme:finviz:x"),
        edge("e2", "MEMBER_OF", "co:us:BBB", "ltheme:finviz:x"),
    ]
    m1 = _compose(FakeStore(list(edges)), _spec(["ltheme:finviz:x"]))
    m2 = _compose(FakeStore(list(reversed(edges))), _spec(["ltheme:finviz:x"]))
    assert json.dumps(to_json(m1), sort_keys=False) == json.dumps(to_json(m2), sort_keys=False)


_FORBIDDEN_IMPORTS = (
    "engine.prophet", "engine.regime", "engine.axes", "engine.conditions",
    "engine.alerts", "engine.run", "lib.store", "requests", "urllib", "httpx",
    "openai", "anthropic",
)


def test_module_is_a_pure_leaf():
    tree = ast.parse(MODULE_PATH.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(alias.name.startswith(f) for f in _FORBIDDEN_IMPORTS), alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not any(node.module.startswith(f) for f in _FORBIDDEN_IMPORTS), node.module
        elif isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
            assert name not in ("now", "today"), "no clock call allowed"
            if isinstance(fn, ast.Name) and fn.id == "open":
                pytest.fail("no filesystem write allowed")

    # B1 fix: the five package-shaped paths named in the original spec prose do not
    # exist in this checkout (engine/axes.py and engine/alerts.py are files, not
    # packages; engine/prophet, engine/regime, engine/conditions do not exist at
    # all) -- grep exits rc=2 (no such file/dir) with empty stdout on those, which
    # made the old `out.stdout.strip() == ""` assertion vacuously true even for an
    # actual import. Resolve to the scoring-path targets that really exist, assert
    # grep's own returncode (1 == "ran clean, matched nothing"; 0 == a real hit;
    # 2 == a path resolution error we must not silently swallow), never just stdout.
    candidate_paths = [
        "engine/prophet", "engine/regime", "engine/axes.py", "engine/axes",
        "engine/conditions", "engine/alerts.py", "engine/alerts", "engine/run.py",
    ]
    scoring_paths = [pth for pth in candidate_paths if (REPO_ROOT / pth).exists()]
    assert scoring_paths, "no scoring-path targets resolved to real files/dirs"
    out = subprocess.run(
        ["grep", "-rl", "engine.market_ontology", *scoring_paths],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert out.returncode == 1, (
        f"scoring-path guard did not run clean: rc={out.returncode} "
        f"stdout={out.stdout!r} stderr={out.stderr!r}"
    )
    assert out.stdout.strip() == ""


_FORBIDDEN_KEY_RE = __import__("re").compile(
    r"(score|rank|weight|alpha|signal|conviction|size|target|priced|probability|confidence_pct)",
    __import__("re").IGNORECASE,
)


def _walk_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_keys(item)


def test_authority_ceiling_keys():
    edges = [
        edge("e1", "MEMBER_OF", "co:us:A", "ltheme:finviz:x"),
        edge("e2", "MEMBER_OF", "co:cn:X", "basket:baskets_china_ths:B"),
        edge("e3", "EXPRESSES", "basket:baskets_china_ths:B", "ltheme:ths:C"),
    ]
    m = _compose(FakeStore(edges), _spec(["ltheme:finviz:x", "ltheme:ths:C"]))
    payload = to_json(m)
    for key in _walk_keys(payload):
        if key == "confidence_basis":
            continue
        assert not _FORBIDDEN_KEY_RE.search(key), key
    assert payload["authority_ceiling"] == "research_display_only"
    assert payload["display_only"] is True


def test_post_6809_fixture_needs_no_code_change():
    # Simulates the state AFTER #6809 lands: a direct co:*->ltheme:ths:* MEMBER_OF
    # edge exists (today only Finviz has this; THS gets it via #6809). No code
    # change to this module should be required for this to work.
    edges = [edge("e1", "MEMBER_OF", "co:cn:300123", "ltheme:ths:C")]
    m = _compose(FakeStore(edges), _spec(["ltheme:ths:C"]))
    theme = m.themes[0]
    assert theme.state == "OK"
    assert theme.companies[0]["paths"][0]["path_kind"] == "direct_membership"


def test_production_edge_reader_is_honest_about_history_read():
    import inspect

    from engine.market_ontology.exposure_map import _DefaultStoreView, _EDGE_READER

    src = inspect.getsource(_DefaultStoreView.read_edges)
    assert "read_edges(latest_belief=False)" in src
    assert "latest_belief=True" not in src
    assert _EDGE_READER == "engine.theme_graph.store.read_edges(latest_belief=False)"

    m = _compose(
        FakeStore([edge("e1", "MEMBER_OF", "co:us:A", "ltheme:finviz:x")]),
        _spec(["ltheme:finviz:x"]),
    )
    assert m.provenance["edge_reader"] == _EDGE_READER
    const = _schema()["properties"]["provenance"]["properties"]["edge_reader"]["const"]
    assert const == _EDGE_READER
    jsonschema.validate(to_json(m), _schema())


def test_rights_blocked_companies_are_not_ok_empty_list():
    def family(node_id):
        nid = str(node_id or "")
        if nid.startswith("co:"):
            return "vendor_co"
        from engine.theme_graph import rights

        return rights.family_for_node_id(node_id)

    edges = [
        edge("e1", "MEMBER_OF", "co:us:A", "theme:gold"),
        edge("e2", "MEMBER_OF", "co:us:B", "theme:gold"),
    ]
    m = _compose(
        FakeStore(edges), _spec(["theme:gold"]),
        family_resolver=family, assert_allowed=_refuse("vendor_co"),
    )
    theme = m.themes[0]
    assert theme.state == "RIGHTS_SUPPRESSED"
    assert theme.companies is None
    assert theme.company_count is None
    assert theme.unavailable["code"] == "RIGHTS_SUPPRESSED"
    assert "cannot be shown" in theme.unavailable["reason"]["en"]
    assert theme.unavailable["reason"]["zh"]
    payload = to_json(m)
    assert payload["themes"][0]["companies"] is None
    assert payload["themes"][0]["company_count"] is None
    subjects = {a["subject_id"] for a in theme.abstentions}
    assert subjects == {"co:us:A", "co:us:B"}
    jsonschema.validate(payload, _schema())


def test_partial_company_rights_keeps_allowed_rows():
    def family(node_id):
        return "vendor_co" if str(node_id) == "co:us:SECRET" else None

    edges = [
        edge("e1", "MEMBER_OF", "co:us:A", "theme:gold"),
        edge("e2", "MEMBER_OF", "co:us:SECRET", "theme:gold"),
    ]
    m = _compose(
        FakeStore(edges), _spec(["theme:gold"]),
        family_resolver=family, assert_allowed=_refuse("vendor_co"),
    )
    theme = m.themes[0]
    assert theme.state == "OK"
    assert [c["company_node_id"] for c in theme.companies] == ["co:us:A"]
    assert theme.company_count == 1
    assert any(
        a["code"] == "RIGHTS_SUPPRESSED" and a["subject_id"] == "co:us:SECRET"
        for a in theme.abstentions
    )
    assert "co:us:SECRET" not in json.dumps(theme.companies)


def test_company_rights_family_string_validates():
    def family(node_id):
        return "finviz_themes" if str(node_id).startswith("co:") else None

    edges = [edge("e1", "MEMBER_OF", "co:us:A", "theme:gold")]
    m = _compose(FakeStore(edges), _spec(["theme:gold"]), family_resolver=family)
    company = m.themes[0].companies[0]
    assert company["rights_family"] == "finviz_themes"
    jsonschema.validate(to_json(m), _schema())


def test_owner_rights_gate_refuses_unresolved_vendor_families():
    from engine.theme_graph.rights import RightsRefusal, assert_public_emission_allowed

    with pytest.raises(RightsRefusal, match="finviz_themes"):
        assert_public_emission_allowed("finviz_themes")
    with pytest.raises(RightsRefusal, match="ths_concepts"):
        assert_public_emission_allowed("ths_concepts")

    edges = [edge("e1", "MEMBER_OF", "co:us:A", "ltheme:finviz:x")]
    m = compose_exposure_map(
        FakeStore(edges), _spec(["ltheme:finviz:x"]), asof="2026-06-01",
        chain_loader=_chain_loader,
    )
    theme = m.themes[0]
    assert theme.state == "RIGHTS_SUPPRESSED"
    assert theme.companies is None
    assert theme.rights_family == "finviz_themes"
    assert theme.unavailable["code"] == "RIGHTS_SUPPRESSED"
    assert "co:us:A" not in json.dumps(to_json(m))


def test_owner_rights_gate_allows_house_curated_basket():
    edges = [
        edge("e1", "MEMBER_OF", "co:us:A", "basket:baskets:gold"),
        edge("e2", "EXPRESSES", "basket:baskets:gold", "theme:gold"),
    ]
    m = compose_exposure_map(
        FakeStore(edges), _spec(["theme:gold"]), asof="2026-06-01",
        chain_loader=_chain_loader,
    )
    theme = m.themes[0]
    assert theme.state == "OK"
    assert [c["company_node_id"] for c in theme.companies] == ["co:us:A"]
    assert theme.companies[0]["paths"][0]["path_kind"] == "basket_bridge"


def test_rights_refused_bridge_is_not_no_membership_yet():
    edges = [
        edge("e1", "EXPRESSES", "ltheme:finviz:L", "theme:t1"),
        edge("e2", "MEMBER_OF", "co:us:Z", "ltheme:finviz:L"),
    ]
    m = _compose(
        FakeStore(edges), _spec(["theme:t1"]),
        assert_allowed=_refuse("finviz_themes"),
    )
    theme = m.themes[0]
    assert theme.state == "RIGHTS_SUPPRESSED"
    assert theme.companies is None
    assert theme.unavailable["code"] == "RIGHTS_SUPPRESSED"
    assert "cannot be shown" in theme.unavailable["reason"]["en"]
    assert "has not been recorded" not in theme.unavailable["reason"]["en"]
    assert "尚未被记录" not in theme.unavailable["reason"]["zh"]

    real = compose_exposure_map(
        FakeStore(edges), _spec(["theme:t1"]), asof="2026-06-01",
        chain_loader=_chain_loader,
    )
    assert real.themes[0].state == "RIGHTS_SUPPRESSED"
    assert "has not been recorded" not in real.themes[0].unavailable["reason"]["en"]


def test_null_src_member_of_is_typed_null_not_raise():
    edges = [edge("e1", "MEMBER_OF", None, "ltheme:finviz:x")]
    m = _compose(FakeStore(edges), _spec(["ltheme:finviz:x"]))
    theme = m.themes[0]
    assert theme.state == "NO_MEMBERSHIP_YET"
    assert theme.companies is None
    assert theme.unavailable["code"] == "NO_MEMBERSHIP_YET"


def test_null_src_expresses_is_typed_null_not_raise():
    edges = [edge("e1", "EXPRESSES", None, "theme:t1")]
    m = _compose(FakeStore(edges), _spec(["theme:t1"]))
    theme = m.themes[0]
    assert theme.state == "NO_MEMBERSHIP_YET"
    assert theme.companies is None
    assert theme.unavailable["code"] == "NO_MEMBERSHIP_YET"


def test_collapse_tie_on_same_belief_and_computed_at_is_deterministic():
    a = edge(
        "e1", "MEMBER_OF", "co:us:B", "ltheme:finviz:x",
        belief_time="2026-01-01", computed_at="2026-01-01T00:00:00Z",
    )
    b = edge(
        "e1", "MEMBER_OF", "co:us:A", "ltheme:finviz:x",
        belief_time="2026-01-01", computed_at="2026-01-01T00:00:00Z",
    )
    m1 = _compose(FakeStore([a, b]), _spec(["ltheme:finviz:x"]))
    m2 = _compose(FakeStore([b, a]), _spec(["ltheme:finviz:x"]))
    assert json.dumps(to_json(m1)) == json.dumps(to_json(m2))
    assert [c["company_node_id"] for c in m1.themes[0].companies] == ["co:us:B"]
    law = (
        "max belief_time <= asof per edge_id (null belief_time never eligible); "
        "ties on computed_at then src then dst"
    )
    assert m1.provenance["belief_collapse"] == law
    const = _schema()["properties"]["provenance"]["properties"]["belief_collapse"]["const"]
    assert const == law


def test_later_belief_coexisting_with_eligible_row_is_not_silent():
    edges = [
        edge(
            "e1", "MEMBER_OF", "co:us:A", "ltheme:finviz:x",
            belief_time="2026-01-01", computed_at="2026-01-01T00:00:00Z",
        ),
        edge(
            "e1", "MEMBER_OF", "co:us:A", "ltheme:finviz:x",
            belief_time="2026-09-01", computed_at="2026-09-01T00:00:00Z",
        ),
    ]
    m = _compose(FakeStore(edges), _spec(["ltheme:finviz:x"]), asof="2026-06-01")
    theme = m.themes[0]
    assert theme.state == "OK"
    assert [c["company_node_id"] for c in theme.companies] == ["co:us:A"]
    after = [a for a in theme.abstentions if a["code"] == "BELIEF_AFTER_ASOF"]
    assert len(after) == 1
    assert after[0]["subject_id"] == "e1"
    assert "later update" in after[0]["reason"]["en"]


def test_copied_helpers_match_theme_adapter_on_shared_inputs():
    from engine.intelligence_workspace.adapters import theme as theme_ad
    from engine.market_ontology import exposure_map as em

    rows = [{"a": 1}, {"a": 2}]
    assert em._records(rows) == theme_ad._records(rows)

    class _Frame:
        def to_dict(self, orient):
            assert orient == "records"
            return rows

    assert em._records(_Frame()) == theme_ad._records(_Frame())

    for bad in (None, "not-tabular", 12):
        with pytest.raises(TypeError):
            em._records(bad)
        with pytest.raises(TypeError):
            theme_ad._records(bad)

    for value in (None, "", 0, "x", datetime.date(2026, 1, 1)):
        assert em._is_null(value) is theme_ad._is_null(value)

    for value in (
        None,
        datetime.date(2026, 1, 1),
        datetime.datetime(2026, 1, 2, 15, 0),
        "2026-03-04",
    ):
        assert em._date(value) == theme_ad._date(value)

    # Totality law: a malformed date is data-availability, never a raise here.
    # The theme adapter still raises — that divergence is pinned, not silent.
    assert em._date("not-a-date") is None
    with pytest.raises(ValueError):
        theme_ad._date("not-a-date")


def test_belief_after_asof_attribution_is_order_independent_across_themes():
    """NM1: one edge_id with future rows on two themes must attribute both,
    and the serialized payload must be byte-identical under input reversal."""
    future_a = edge(
        "e9", "MEMBER_OF", "co:us:NEW", "theme:a",
        belief_time="2026-12-01", computed_at="2026-12-01T00:00:00Z",
    )
    future_b = edge(
        "e9", "MEMBER_OF", "co:us:NEWER", "theme:b",
        belief_time="2026-12-02", computed_at="2026-12-02T00:00:00Z",
    )
    eligible_a = edge(
        "ea", "MEMBER_OF", "co:us:OLD", "theme:a",
        belief_time="2026-01-01", computed_at="2026-01-01T00:00:00Z",
    )
    eligible_b = edge(
        "eb", "MEMBER_OF", "co:us:OLD2", "theme:b",
        belief_time="2026-01-01", computed_at="2026-01-01T00:00:00Z",
    )
    fwd = [future_a, future_b, eligible_a, eligible_b]
    rev = list(reversed(fwd))
    spec = _spec(["theme:a", "theme:b"])
    m_fwd = _compose(FakeStore(fwd), spec, asof="2026-06-01")
    m_rev = _compose(FakeStore(rev), spec, asof="2026-06-01")
    payload_fwd = json.dumps(to_json(m_fwd), sort_keys=False)
    payload_rev = json.dumps(to_json(m_rev), sort_keys=False)
    assert payload_fwd == payload_rev

    def attribution(payload_theme):
        return {(a["code"], a["subject_id"]) for a in payload_theme.abstentions}

    by_id_fwd = {t.theme_node_id: t for t in m_fwd.themes}
    by_id_rev = {t.theme_node_id: t for t in m_rev.themes}
    assert attribution(by_id_fwd["theme:a"]) == attribution(by_id_rev["theme:a"])
    assert attribution(by_id_fwd["theme:b"]) == attribution(by_id_rev["theme:b"])
    assert ("BELIEF_AFTER_ASOF", "e9") in attribution(by_id_fwd["theme:a"])
    assert ("BELIEF_AFTER_ASOF", "e9") in attribution(by_id_fwd["theme:b"])
    jsonschema.validate(to_json(m_fwd), _schema())


def test_unknown_basket_prefix_fails_closed_on_real_gate():
    """NM2: an unregistered basket: prefix must not emit through the production gate."""
    edges = [
        edge("e1", "EXPRESSES", "basket:newvendor:x", "theme:g"),
        edge("e2", "MEMBER_OF", "co:us:LEAK", "basket:newvendor:x"),
    ]
    m = compose_exposure_map(
        FakeStore(edges), _spec(["theme:g"]), asof="2026-06-01",
        chain_loader=_chain_loader,
    )
    theme = m.themes[0]
    assert theme.state == "RIGHTS_SUPPRESSED"
    assert theme.companies is None
    assert theme.company_count is None
    assert theme.unavailable["code"] == "UNKNOWN_RIGHTS_FAMILY"
    dumped = json.dumps(to_json(m))
    assert "co:us:LEAK" not in dumped
    src = MODULE_PATH.read_text()
    assert "UNKNOWN_RIGHTS_FAMILY" in src
    assert "never assumed safe because today's table maps no such prefix" in src
    jsonschema.validate(to_json(m), _schema())


def test_production_compose_has_no_allow_all_default():
    """NM2: _allow_all is fixture-only; compose_exposure_map cannot reach it."""
    import inspect

    from engine.market_ontology import exposure_map as em

    src = inspect.getsource(em.compose_exposure_map)
    assert "_allow_all" not in src
    assert "assert_allowed = assert_allowed or _default_assert_allowed" in src
    sig = inspect.signature(em.compose_exposure_map)
    assert sig.parameters["assert_allowed"].default is None
    fallback = inspect.getsource(em._default_assert_allowed)
    assert "assert_public_emission_allowed" in fallback
    assert "_allow_all" not in fallback
    assert "_allow_all" not in MODULE_PATH.read_text()


def test_unknown_ltheme_prefix_fails_closed_on_real_gate():
    """NM4: an unregistered ltheme: prefix is RIGHTS_SUPPRESSED /
    UNKNOWN_RIGHTS_FAMILY, not NO_MEMBERSHIP_YET. Twin of the basket-plane gate."""
    edges = [
        edge("e1", "EXPRESSES", "ltheme:newvendor:y", "theme:g"),
        edge("e2", "MEMBER_OF", "co:us:LEAK2", "ltheme:newvendor:y"),
    ]
    m = compose_exposure_map(
        FakeStore(edges), _spec(["theme:g"]), asof="2026-06-01",
        chain_loader=_chain_loader,
    )
    theme = m.themes[0]
    assert theme.state == "RIGHTS_SUPPRESSED"
    assert theme.companies is None
    assert theme.company_count is None
    assert theme.unavailable["code"] == "UNKNOWN_RIGHTS_FAMILY"
    dumped = json.dumps(to_json(m))
    assert "co:us:LEAK2" not in dumped
    assert "has not been recorded" not in theme.unavailable["reason"]["en"]
    jsonschema.validate(to_json(m), _schema())


def test_null_belief_time_is_never_eligible():
    """m1: a row whose belief date is unknown is not knowable at any as-of."""
    from engine.market_ontology.exposure_map import _REASONS

    enum = set(_schema()["$defs"]["unavailable"]["properties"]["code"]["enum"])
    assert set(_REASONS) == enum
    assert "BELIEF_TIME_UNKNOWN" in enum

    edges = [
        edge("e1", "MEMBER_OF", "co:us:NB", "theme:g",
             belief_time=None, valid_from="1800-01-01"),
    ]
    for asof in ("1900-01-01", "2027-01-01"):
        m = _compose(FakeStore(edges), _spec(["theme:g"]), asof=asof)
        theme = m.themes[0]
        dumped = json.dumps(to_json(m))
        assert "co:us:NB" not in dumped
        assert theme.companies is None
        codes = {a["code"] for a in theme.abstentions}
        if theme.unavailable is not None:
            codes.add(theme.unavailable["code"])
        assert "BELIEF_TIME_UNKNOWN" in codes
        jsonschema.validate(to_json(m), _schema())


def test_null_edge_id_is_typed_abstention():
    """m2: a missing edge_id is EDGE_ID_MISSING, counted, not a silent drop."""
    edges = [
        edge(None, "MEMBER_OF", "co:us:NAN", "theme:g"),
        edge("e2", "MEMBER_OF", "co:us:OK", "theme:g"),
    ]
    m = _compose(FakeStore(edges), _spec(["theme:g"]))
    theme = m.themes[0]
    assert theme.state == "OK"
    assert [c["company_node_id"] for c in theme.companies] == ["co:us:OK"]
    assert any(a["code"] == "EDGE_ID_MISSING" for a in theme.abstentions)
    dumped = json.dumps(to_json(m))
    assert dumped.count("EDGE_ID_MISSING") >= 1
    jsonschema.validate(to_json(m), _schema())


def test_collapse_matches_store_latest_belief_on_single_belief_and_differs_on_two(
    monkeypatch,
):
    """m3: composer collapse equals store latest_belief on one belief per
    edge_id; a two-belief edge recollapses at the caller as-of and differs."""
    import pandas as pd

    from engine.market_ontology.exposure_map import _collapse_and_filter_edges
    from engine.theme_graph import store as tg_store

    def _pairs(frame_or_map):
        if isinstance(frame_or_map, dict):
            return {
                eid: (row["src"], row["dst"], row["belief_time"])
                for eid, row in frame_or_map.items()
            }
        out = {}
        for _, row in frame_or_map.iterrows():
            bt = row["belief_time"]
            if hasattr(bt, "isoformat"):
                bt = bt.isoformat()
            else:
                bt = None if bt is None else str(bt)[:10]
            out[str(row["edge_id"])] = (row["src"], row["dst"], bt)
        return out

    single = [
        edge("e1", "MEMBER_OF", "co:us:A", "theme:g",
             belief_time="2026-01-01", computed_at="2026-01-01T00:00:00Z"),
    ]

    def _read_single(_path, _columns):
        return pd.DataFrame(single)

    monkeypatch.setattr(tg_store, "_read", _read_single)
    store_single = tg_store.read_edges(latest_belief=True)
    collapsed_single, _ = _collapse_and_filter_edges(
        single, datetime.date(2026, 6, 1),
    )
    assert _pairs(collapsed_single) == _pairs(store_single)

    two = [
        edge("e1", "MEMBER_OF", "co:us:OLD", "theme:g",
             belief_time="2026-01-01", computed_at="2026-01-01T00:00:00Z"),
        edge("e1", "MEMBER_OF", "co:us:NEW", "theme:g",
             belief_time="2026-08-01", computed_at="2026-08-01T00:00:00Z"),
    ]

    def _read_two(_path, _columns):
        return pd.DataFrame(two)

    monkeypatch.setattr(tg_store, "_read", _read_two)
    store_two = tg_store.read_edges(latest_belief=True)
    early, _ = _collapse_and_filter_edges(two, datetime.date(2026, 3, 1))
    late, _ = _collapse_and_filter_edges(two, datetime.date(2026, 9, 1))

    store_pairs = _pairs(store_two)
    assert store_pairs == {"e1": ("co:us:NEW", "theme:g", "2026-08-01")}
    assert _pairs(early) == {"e1": ("co:us:OLD", "theme:g", "2026-01-01")}
    assert _pairs(late) == store_pairs
    assert _pairs(early) != store_pairs


def test_theme_level_rights_refusal_omits_clock_abstentions():
    """m4: a rights-refused theme omits BELIEF_AFTER_ASOF so a later-belief
    edge cannot leak through the abstention list of a family we may not show."""
    edges = [
        edge("e1", "MEMBER_OF", "co:us:A", "ltheme:finviz:z",
             belief_time="2026-01-01", computed_at="2026-01-01T00:00:00Z"),
        edge("e1", "MEMBER_OF", "co:us:A", "ltheme:finviz:z",
             belief_time="2026-12-01", computed_at="2026-12-01T00:00:00Z"),
    ]
    m = compose_exposure_map(
        FakeStore(edges), _spec(["ltheme:finviz:z"]), asof="2026-06-01",
        chain_loader=_chain_loader,
    )
    theme = m.themes[0]
    assert theme.state == "RIGHTS_SUPPRESSED"
    assert theme.companies is None
    assert theme.unavailable["code"] == "RIGHTS_SUPPRESSED"
    assert not any(a["code"] == "BELIEF_AFTER_ASOF" for a in theme.abstentions)
    dumped = json.dumps(to_json(m))
    assert "co:us:A" not in dumped
    jsonschema.validate(to_json(m), _schema())
