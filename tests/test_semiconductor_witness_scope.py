"""T08c-1 — declared witness roster + identity join through the owners.

Pinned against the COMMITTED ``data/`` artifacts (read-only): the two witness
slices resolve to TSMC and onsemi through
``engine.theme_graph.identity.company_node_id`` →
``engine.theme_graph.identity_resolution.resolve_graph_node_identity`` →
``lib.dataos.identity.IssuerMaster.cik_of_issuer``; every result carries
``slice_scope_unowned``; every failure path is a typed omission, never a
raise; nothing exposes ``mapping_learned_at``.
"""
from __future__ import annotations

import ast
import dataclasses
from pathlib import Path
from types import MappingProxyType

import pandas as pd
import pytest

from engine.company_intelligence.issuer_profiles import ON_CIK, TSM_CIK
from engine.market_ontology import semiconductor_witness_scope as scope_module
from engine.market_ontology.semiconductor_witness_scope import (
    SLICE_SCOPE_UNOWNED,
    WITNESS_ROSTER,
    WitnessIdentity,
    WitnessScope,
    resolve_witness_scope,
    verify_workspace_cik,
)
from lib.dataos.identity import IssuerMaster

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "engine" / "market_ontology" / "semiconductor_witness_scope.py"
MASTER_PATH = ROOT / "data" / "reference" / "security_master.parquet"

pytestmark = pytest.mark.skipif(
    not MASTER_PATH.is_file() or not (ROOT / "data" / "theme_graph" / "nodes.parquet").is_file(),
    reason="committed Data OS / Theme Graph artifacts absent (sparse checkout)",
)


# ─────────────────────────────────────────────────────────────────────────────
# (a)/(b) the two witnesses resolve through the owners to the real CIKs
# ─────────────────────────────────────────────────────────────────────────────


def test_hbm_packaging_resolves_to_tsmc_through_the_owners() -> None:
    scope = resolve_witness_scope("hbm_packaging")
    assert isinstance(scope, WitnessScope)
    assert scope.slice_key == "hbm_packaging"
    assert scope.identities == (
        WitnessIdentity(ticker="TSM", company_node_id="co:us:TSM",
                        issuer_id="ISS:US-XNYS-TSM", cik="0001046179"),
    )
    assert scope.identities[0].cik == TSM_CIK
    assert scope.omissions == (SLICE_SCOPE_UNOWNED,)


def test_sic_gan_specialty_resolves_to_onsemi_through_the_owners() -> None:
    scope = resolve_witness_scope("sic_gan_specialty")
    assert scope.identities == (
        WitnessIdentity(ticker="ON", company_node_id="co:us:ON",
                        issuer_id="ISS:US-XNAS-ON", cik="0001097864"),
    )
    assert scope.identities[0].cik == ON_CIK
    assert scope.omissions == (SLICE_SCOPE_UNOWNED,)


def test_resolved_ciks_cross_check_against_the_committed_security_master() -> None:
    master = pd.read_parquet(MASTER_PATH)
    by_issuer = {row["issuer_id"]: row["issuer_cik"] for row in master.to_dict("records")
                 if row.get("issuer_id") in {"ISS:US-XNYS-TSM", "ISS:US-XNAS-ON"}}
    assert by_issuer["ISS:US-XNYS-TSM"] == resolve_witness_scope("hbm_packaging").identities[0].cik
    assert by_issuer["ISS:US-XNAS-ON"] == resolve_witness_scope("sic_gan_specialty").identities[0].cik


# ─────────────────────────────────────────────────────────────────────────────
# (c)/(d) unknown slice; every result carries slice_scope_unowned
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("probe", [
    pytest.param("robotics_manipulation", id="foreign-slice"),
    pytest.param("HBM_PACKAGING", id="case-variant"),
    pytest.param(" hbm_packaging", id="whitespace"),
    pytest.param("hbm", id="prefix"),
    pytest.param("", id="empty"),
])
def test_unknown_slice_yields_no_identities_and_typed_omissions(probe) -> None:
    scope = resolve_witness_scope(probe)
    assert scope.identities == ()
    assert scope.omissions == (f"slice_unknown:{probe}", SLICE_SCOPE_UNOWNED)


@pytest.mark.parametrize("probe", [None, 7, b"hbm_packaging", ["hbm_packaging"], {"k": "v"}])
def test_non_string_slice_never_raises(probe) -> None:
    scope = resolve_witness_scope(probe)  # type: ignore[arg-type]
    assert scope.identities == ()
    assert SLICE_SCOPE_UNOWNED in scope.omissions
    assert scope.omissions[0].startswith("slice_unknown:")


@pytest.mark.parametrize("slice_key", [*WITNESS_ROSTER, "unknown_slice"])
def test_every_result_carries_slice_scope_unowned_exactly_once(slice_key) -> None:
    scope = resolve_witness_scope(slice_key)
    assert scope.omissions.count(SLICE_SCOPE_UNOWNED) == 1
    assert scope.omissions[-1] == SLICE_SCOPE_UNOWNED


# ─────────────────────────────────────────────────────────────────────────────
# (e) verify_workspace_cik — exact ten-digit string equality
# ─────────────────────────────────────────────────────────────────────────────

_TSM = WitnessIdentity(ticker="TSM", company_node_id="co:us:TSM",
                       issuer_id="ISS:US-XNYS-TSM", cik="0001046179")


@pytest.mark.parametrize("workspace_cik, expected", [
    pytest.param("0001046179", True, id="exact"),
    pytest.param("1046179", False, id="unpadded"),
    pytest.param(" 0001046179", False, id="leading-space"),
    pytest.param("0001046179 ", False, id="trailing-space"),
    pytest.param(1046179, False, id="int"),
    pytest.param(None, False, id="none"),
    pytest.param("0001097864", False, id="other-witness"),
    pytest.param(b"0001046179", False, id="bytes"),
])
def test_verify_workspace_cik_is_exact_string_equality(workspace_cik, expected) -> None:
    assert verify_workspace_cik(_TSM, workspace_cik) is expected


# ─────────────────────────────────────────────────────────────────────────────
# (f) owner refusals → no identity + identity_unverified:<ticker>, never a raise
# ─────────────────────────────────────────────────────────────────────────────


def test_unresolved_graph_identity_yields_identity_unverified(monkeypatch) -> None:
    def unresolved(node_id, asof=None):
        return {"node_id": node_id, "resolution_state": "UNRESOLVED", "issuer_id": None}

    monkeypatch.setattr(scope_module.identity_resolution, "resolve_graph_node_identity", unresolved)
    scope = resolve_witness_scope("hbm_packaging")
    assert scope.identities == ()
    assert scope.omissions == ("identity_unverified:TSM", SLICE_SCOPE_UNOWNED)


def test_resolved_row_without_issuer_id_yields_identity_unverified(monkeypatch) -> None:
    monkeypatch.setattr(
        scope_module.identity_resolution, "resolve_graph_node_identity",
        lambda node_id, asof=None: {"node_id": node_id, "resolution_state": "RESOLVED", "issuer_id": ""},
    )
    assert resolve_witness_scope("sic_gan_specialty").omissions == ("identity_unverified:ON", SLICE_SCOPE_UNOWNED)


def test_owner_exception_yields_identity_unverified_not_a_raise(monkeypatch) -> None:
    def boom(node_id, asof=None):
        raise scope_module.identity_resolution.UnknownGraphNodeError(node_id)

    monkeypatch.setattr(scope_module.identity_resolution, "resolve_graph_node_identity", boom)
    scope = resolve_witness_scope("hbm_packaging")
    assert scope.identities == () and scope.omissions == ("identity_unverified:TSM", SLICE_SCOPE_UNOWNED)


def test_missing_security_master_yields_identity_unverified(monkeypatch) -> None:
    monkeypatch.setattr(scope_module, "_load_issuer_master", lambda root=None: None)
    scope = resolve_witness_scope("hbm_packaging")
    assert scope.identities == () and scope.omissions == ("identity_unverified:TSM", SLICE_SCOPE_UNOWNED)


def test_unreadable_security_master_returns_none_not_a_raise(tmp_path) -> None:
    ref = tmp_path / "reference"
    ref.mkdir()
    (ref / "security_master.parquet").write_bytes(b"not a parquet file")
    assert scope_module._load_issuer_master(tmp_path) is None
    assert scope_module._load_issuer_master(tmp_path / "absent") is None


def test_conflicting_or_missing_data_os_cik_yields_identity_unverified(monkeypatch) -> None:
    conflicting = IssuerMaster.from_records([
        {"security_id": "SEC:US-XNYS-TSM", "issuer_id": "ISS:US-XNYS-TSM",
         "issuer_state": "RESOLVED", "issuer_cik": "0001046179", "listing_key": "US-XNYS-TSM"},
        {"security_id": "SEC:US-XNYS-TSM2", "issuer_id": "ISS:US-XNYS-TSM",
         "issuer_state": "RESOLVED", "issuer_cik": "0009999999", "listing_key": "US-XNYS-TSM2"},
    ])
    monkeypatch.setattr(scope_module, "_load_issuer_master", lambda root=None: conflicting)
    assert resolve_witness_scope("hbm_packaging").omissions == ("identity_unverified:TSM", SLICE_SCOPE_UNOWNED)

    without_cik = IssuerMaster.from_records([
        {"security_id": "SEC:US-XNYS-TSM", "issuer_id": "ISS:US-XNYS-TSM",
         "issuer_state": "RESOLVED", "issuer_cik": None, "listing_key": "US-XNYS-TSM"},
    ])
    monkeypatch.setattr(scope_module, "_load_issuer_master", lambda root=None: without_cik)
    assert resolve_witness_scope("hbm_packaging").identities == ()


def test_no_ticker_equality_fallback_when_the_graph_node_is_unknown(monkeypatch) -> None:
    """A ticker never becomes an identity by name alone: refusing the graph
    node refuses the witness even though the Data OS master knows the CIK."""
    def unknown(node_id, asof=None):
        raise scope_module.identity_resolution.UnknownGraphNodeError(node_id)

    monkeypatch.setattr(scope_module.identity_resolution, "resolve_graph_node_identity", unknown)
    scope = resolve_witness_scope("sic_gan_specialty")
    assert scope.identities == () and "identity_unverified:ON" in scope.omissions


# ─────────────────────────────────────────────────────────────────────────────
# (g) no mapping_learned_at anywhere; closure of the roster and dataclasses
# ─────────────────────────────────────────────────────────────────────────────


def test_no_result_exposes_mapping_learned_at() -> None:
    for cls in (WitnessIdentity, WitnessScope):
        assert "mapping_learned_at" not in {f.name for f in dataclasses.fields(cls)}
    scope = resolve_witness_scope("hbm_packaging")
    assert not hasattr(scope, "mapping_learned_at")
    assert all(not hasattr(identity, "mapping_learned_at") for identity in scope.identities)
    source = MODULE_PATH.read_text(encoding="utf-8")
    code_only = "\n".join(
        line for line in source.splitlines() if not line.lstrip().startswith("#")
    )
    # The name appears only in the docstring that forbids it, never as a field or key.
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert node.value != "mapping_learned_at"
        if isinstance(node, (ast.Attribute, ast.Name)):
            assert getattr(node, "attr", getattr(node, "id", "")) != "mapping_learned_at"
    assert "mapping_learned_at" in code_only  # the docstring states the law


def test_roster_is_closed_read_only_and_frozen() -> None:
    assert isinstance(WITNESS_ROSTER, MappingProxyType)
    assert dict(WITNESS_ROSTER) == {"hbm_packaging": ("TSM",), "sic_gan_specialty": ("ON",)}
    with pytest.raises(TypeError):
        WITNESS_ROSTER["robotics_manipulation"] = ("ABB",)  # type: ignore[index]
    scope = resolve_witness_scope("hbm_packaging")
    with pytest.raises(dataclasses.FrozenInstanceError):
        scope.identities = ()  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        scope.identities[0].cik = "0000000000"  # type: ignore[misc]


def test_identities_follow_roster_order_and_are_tuples() -> None:
    for slice_key, tickers in WITNESS_ROSTER.items():
        scope = resolve_witness_scope(slice_key)
        assert isinstance(scope.identities, tuple) and isinstance(scope.omissions, tuple)
        assert tuple(identity.ticker for identity in scope.identities) == tickers


_FORBIDDEN_IMPORT_ROOTS = frozenset({"fastapi", "starlette", "app", "yaml", "requests", "httpx",
                                     "urllib", "socket", "subprocess", "re", "fnmatch", "glob"})


def test_module_imports_only_the_named_owners_and_writes_nothing() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
        if isinstance(node, ast.Call):
            name = getattr(node.func, "attr", getattr(node.func, "id", ""))
            assert name not in {"open", "write_bytes", "write_text", "to_parquet", "to_csv",
                                "write_evidence", "mkdir", "unlink", "rename"}, name
    assert not (roots & _FORBIDDEN_IMPORT_ROOTS), sorted(roots & _FORBIDDEN_IMPORT_ROOTS)
    assert roots <= {"__future__", "collections", "dataclasses", "io", "pathlib", "types",
                     "lib", "engine", "pandas"}, sorted(roots)
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "identity_resolution.REFERENCE_SUBDIR" in source and "identity_resolution.MASTER_FILE" in source
    assert "config.data_dir()" in source
    for forbidden in ("can_rank", "can_gate", "can_size", "can_originate", "can_open_entry"):
        assert forbidden not in source
