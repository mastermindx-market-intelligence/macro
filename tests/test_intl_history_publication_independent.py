"""AST-extracted History publication-boundary tests.

Layer label: exact `build_all`, `_history_publication_sources`, and
`_publication_workspace` function bodies from scripts/*.py via
ast.get_source_segment. Doubles replace owners that this capsule does not
ship (jinja templates, site_assets, intl_inputs, overviews). This is not a
whole-main run and does not claim parent pytest counts.
"""
from __future__ import annotations

import ast
import logging
import types
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest

from engine.international_macro_dashboard import REGIONS
from lib.intl_history_mount import attach_history


ROOT = Path(__file__).resolve().parents[1]


def _extract(path: Path, name: str) -> str:
    source = path.read_text()
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            segment = ast.get_source_segment(source, node)
            if segment is None:
                raise RuntimeError(f"missing source segment for {name}")
            return segment
    raise RuntimeError(f"{name} not found in {path}")


def _exec_function(path: Path, name: str, namespace: dict) -> object:
    code = _extract(path, name)
    exec(compile(code, str(path), "exec"), namespace)
    return namespace[name]


class _Log:
    def __init__(self):
        self.errors = []
        self.infos = []
        self.warnings = []

    def error(self, message, *args):
        self.errors.append(message % args if args else message)

    def info(self, message, *args):
        self.infos.append(message % args if args else message)

    def warning(self, message, *args):
        self.warnings.append(message % args if args else message)


def _build_all(tmp_path, load_history, load_history_result):
    class Config:
        ROOT = tmp_path

        @staticmethod
        def load():
            return {"storage": {"site_dir": str(tmp_path / "site")}}

        @staticmethod
        def data_dir():
            return tmp_path / "data"

    class Template:
        def render(self, **kwargs):
            return "page"

    class Env:
        def get_template(self, name):
            return Template()

    namespace = {
        "Path": Path,
        "config": Config,
        "REGIONS": REGIONS,
        "load_history": load_history,
        "load_history_result": load_history_result,
        "build_country_view": lambda record, history: {
            "schema": "ok",
            "cc": record["cc"],
            "history": history,
            "decision": {"score": 1},
        },
        "validate_view": lambda view: None,
        "json": __import__("json"),
        "date": __import__("datetime").date,
        "Environment": lambda **kwargs: Env(),
        "FileSystemLoader": lambda *args, **kwargs: None,
        "write_page": lambda *args, **kwargs: None,
        "site_assets": types.SimpleNamespace(copy_asset=lambda *args, **kwargs: None),
        "ASSETS": (),
        "_radar_display": lambda record: None,
        "_load_latest": lambda: pytest.fail("default latest loader must not run"),
        "log": _Log(),
    }
    return _exec_function(ROOT / "scripts/build_international_macro.py", "build_all", namespace)


def _history_sources(namespace=None):
    ns = {"logging": logging, "log": _Log()}
    if namespace:
        ns.update(namespace)
    return _exec_function(ROOT / "scripts/build_intl.py", "_history_publication_sources", ns), ns["log"]


def _workspace_fixture():
    # Same envelope shape as tests/test_intl_history_mount.py. Not a 7-market
    # overview; this capsule has no intl_workspace_overview owner.
    generation = "im-workspace-generation:12345678-1234-4123-8123-123456789012"
    markets = ["JP", "KR"]
    config = dict(
        markets=markets,
        horizons=["1m", "3m"],
        bases=["local", "usd_unhedged"],
        default_horizon="1m",
        default_basis="usd_unhedged",
        source_reference=generation,
        anchor_ids=[],
        library_group_ids=[],
    )
    panels = [
        dict(
            context_id="im-" + str(i),
            generation=generation,
            overview=dict(
                context=dict(
                    horizon=h,
                    currency_basis=b,
                    return_basis="price",
                    source_reference=None,
                    source_reference_reason="not_supplied",
                )
            ),
        )
        for i, (h, b) in enumerate((h, b) for h in config["horizons"] for b in config["bases"])
    ]
    workspace = dict(
        binding_version=2,
        config=config,
        panels=panels,
        existing_material={"kept": True},
    )
    return workspace, generation, markets


def _publication_workspace(monkeypatch, attach_history_fn=attach_history, overviews=None):
    workspace, generation, markets = _workspace_fixture()
    if overviews is None:
        def overviews(closes, *, workspace_generation=None, production_inputs=None):
            # This History-only fixture supplies no EOD permission or data.
            assert production_inputs is None
            return deepcopy(workspace)

    fake_inputs = types.ModuleType("engine.intl_inputs")
    fake_inputs.countries = lambda: {
        cc: {"name": cc, "name_zh": cc} for cc in markets
    }
    import sys

    import engine

    monkeypatch.setitem(sys.modules, "engine.intl_inputs", fake_inputs)
    monkeypatch.setattr(engine, "intl_inputs", fake_inputs, raising=False)

    log = _Log()
    namespace = {
        "Path": Path,
        "config": types.SimpleNamespace(load=lambda: {"intl": {}}),
        "uuid4": lambda: generation.split(":", 1)[1],
        "_workspace_overviews": overviews,
        "attach_macros": lambda ws, **kwargs: {**ws, "macros_attached": True},
        "attach_risks": lambda ws, **kwargs: {**ws, "risks_attached": True},
        "attach_history": attach_history_fn,
        "read_ecb_deposit_materialization": lambda **kwargs: {"status": "missing"},
        "_ecb_publication_measure": lambda *args, **kwargs: {},
        "log": log,
        "uuid4_imported": uuid4,
    }
    fn = _exec_function(ROOT / "scripts/build_intl.py", "_publication_workspace", namespace)
    return fn, log, workspace


def _receipt(cc, status="ready"):
    return {
        "status": status,
        "market_id": cc,
        "artifact_ref": f"intl_regime/{cc}_history.parquet",
        "read_at": "2026-10-09T01:00:00Z",
        "method_ref": None,
        "frame": object() if status in {"ready", "empty"} else None,
    }


def test_build_all_default_uses_compatibility_loader_not_result(tmp_path):
    calls = {"history": [], "result": []}

    def load_history(cc):
        calls["history"].append(cc)
        return f"compat-{cc}"

    def load_history_result(cc):
        calls["result"].append(cc)
        raise AssertionError("default path must not call load_history_result")

    build_all = _build_all(tmp_path, load_history, load_history_result)
    latest = {"records": [{"cc": cc} for cc in REGIONS]}
    outputs = build_all(latest)
    assert calls["history"] == list(REGIONS)
    assert calls["result"] == []
    assert len(outputs) == 5


def test_build_all_empty_sink_retains_each_owned_receipt_once(tmp_path):
    calls = []
    receipts = {}

    def load_history(cc):
        raise AssertionError("sink path must not call compatibility load_history")

    def load_history_result(cc):
        calls.append(cc)
        receipts[cc] = _receipt(cc, status=["ready", "empty", "missing", "failed", "invalid"][len(calls) - 1])
        return receipts[cc]

    build_all = _build_all(tmp_path, load_history, load_history_result)
    latest = {"records": [{"cc": cc} for cc in REGIONS]}
    sink = {}
    outputs = build_all(latest, history_receipts=sink)
    assert calls == list(REGIONS)
    assert len(outputs) == 5
    assert set(sink) == set(REGIONS)
    for cc in REGIONS:
        assert sink[cc] is receipts[cc]


@pytest.mark.parametrize("sink", [[], True, "", {"JP": "previous publication"}])
def test_build_all_rejects_invalid_sink_before_loader(tmp_path, sink):
    def boom(*args, **kwargs):
        raise AssertionError("invalid sink reached loaders")

    build_all = _build_all(tmp_path, boom, boom)
    with pytest.raises(ValueError, match="^invalid_history_receipts_sink$"):
        build_all({"records": [{"cc": "JP"}]}, history_receipts=sink)


def test_bridge_reuses_projected_receipt_with_unknown_capabilities(monkeypatch):
    from engine import international_macro_dashboard as owner

    projected = {
        "status": "ready",
        "market_id": "JP",
        "artifact_ref": "intl_regime/JP_history.parquet",
        "read_at": "2026-10-09T01:00:00Z",
        "method_ref": None,
        "identity": None,
        "points": [{"observation_at": "2026-01-01T00:00:00+00:00", "growth_score": 1, "inflation_score": 0}],
    }
    supplied = _receipt("JP")
    seen = []

    def fake_project(value):
        seen.append(value)
        return deepcopy(projected)

    monkeypatch.setattr(owner, "project_history_read", fake_project)
    fn, log = _history_sources()
    sources = fn({"JP": supplied})
    assert seen == [supplied]
    assert sources["JP"]["history_read"] == projected
    for key in ("history_source", "events", "track_record"):
        assert sources["JP"]["capabilities"][key] == dict(metadata="unknown", value="unknown")
    assert sources["JP"]["turn_events"] == []
    assert sources["JP"]["track_record"] is None
    assert sources["JP"]["destinations"] == {}
    assert log.errors == []


def test_bridge_skips_unknown_market_without_projector(monkeypatch):
    from engine import international_macro_dashboard as owner

    monkeypatch.setattr(
        owner,
        "project_history_read",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unknown market reached projector")),
    )
    fn, _ = _history_sources()
    assert fn({"UNKNOWN": object()}) == {}


def test_bridge_isolates_one_bad_market_and_sanitizes_log(monkeypatch, caplog):
    from engine import international_macro_dashboard as owner

    projected = {
        "status": "ready",
        "market_id": "JP",
        "artifact_ref": "intl_regime/JP_history.parquet",
        "read_at": "2026-10-09T01:00:00Z",
        "method_ref": None,
        "identity": None,
        "points": [],
    }
    bad, good = object(), object()

    def fake_project(value):
        if value is bad:
            raise ValueError("private secret cannot appear in log")
        out = deepcopy(projected)
        if value is good:
            out["market_id"] = "JP"
        return out

    monkeypatch.setattr(owner, "project_history_read", fake_project)
    fn, log = _history_sources()
    with caplog.at_level(logging.ERROR):
        sources = fn({"GB": bad, "JP": good, "KR": good})
    assert set(sources) == {"JP"}
    assert all("private secret" not in message for message in log.errors)
    assert all("private secret" not in rec.getMessage() for rec in caplog.records)


def test_bridge_rejects_non_dict_or_non_str_keys():
    fn, _ = _history_sources()
    for invalid in ([], None, {"JP": object(), 7: object()}):
        with pytest.raises(ValueError, match="^invalid_history_receipts$"):
            fn(invalid)
    assert fn({}) == {}


def test_history_attach_failure_keeps_macro_and_risk(monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("private History error")

    fn, log, original = _publication_workspace(monkeypatch, attach_history_fn=fail)
    result = fn(None, data_root="unused", evaluated_at="2026-10-09T01:30:00Z")
    assert result["macros_attached"] is True
    assert result["risks_attached"] is True
    assert "histories" not in result
    assert result["existing_material"] == original["existing_material"]
    assert any("History panel unavailable" in message for message in log.errors)
    assert all("private History error" not in message for message in log.errors)


def test_unknown_sources_mount_without_inventing_grants(monkeypatch):
    fn, log, _ = _publication_workspace(monkeypatch)
    result = fn(None, data_root="unused", evaluated_at="2026-10-09T01:30:00Z", history_sources={})
    assert "histories" in result
    sections = result["histories"][0]["sections"]
    assert [s["selected_market"] for s in sections] == ["JP", "KR"]
    assert all(s["source_read_status"] == "unknown" and s["points"] == [] for s in sections)
    assert all(s["events"]["status"] == "unknown" for s in sections)
    assert all(s["track_record"]["status"] == "unknown" for s in sections)
    assert log.errors == []
