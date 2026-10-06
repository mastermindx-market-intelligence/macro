"""LEGACY publish shadow graph theme_state/v1 for cohort reads owner."""
from __future__ import annotations

import ast
import datetime as dt
import json
import sys
from datetime import timezone
from pathlib import Path

import pandas as pd
import pytest

from engine.neuralweb import theme_state_generation as g
from engine.theme_graph import selection_cohort_reads, theme_state
from scripts import build_thematic_state as builder
from tests.test_theme_state_generation import artifact, put
from tests.test_theme_state_production import EMITTED, KNOWN, production_world

PRIMARY = "data/neuralweb/theme_state.json"
MIRROR = "site/neuralwebdata/theme_state.json"
SHADOW = Path("data/theme_graph/shadow_theme_state.v1.json")


@pytest.fixture(autouse=True)
def nightly(monkeypatch):
    monkeypatch.setenv("COLLECT_LANE", "nightly")


def _legacy_build(root, monkeypatch, **kwargs):
    monkeypatch.setattr(builder, "compose", lambda **kw: artifact())
    return builder.build(root, mode="LEGACY", generated_at=EMITTED, **kwargs)


def test_t1_positive_shadow_and_reads(production_world, monkeypatch):
    rc = _legacy_build(production_world, monkeypatch)
    assert rc == 0
    shadow_path = production_world / SHADOW
    assert shadow_path.is_file()
    loaded = json.loads(shadow_path.read_bytes())
    theme_state.validate_state(loaded)
    assert loaded["schema"] == theme_state.SCHEMA
    assert loaded["generation_id"] == loaded["state_sha256"][:32]
    via_reads = selection_cohort_reads._load_state_artifact(production_world / "data")
    assert via_reads == loaded
    read = theme_state.read_theme_state(
        loaded,
        "theme:grid",
        effective_at=loaded["effective_at"],
        known_at=EMITTED,
        expected_generation_id=loaded["generation_id"],
    )
    assert "GENERATION_MISMATCH" not in read["reason_codes"]
    assert "EFFECTIVE_TIME_MISMATCH" not in read["reason_codes"]
    # theme:grid is NOT_QUALIFIED in the synthetic owner estate; read still binds generation.
    assert read["status"] == "UNAVAILABLE"
    assert read["reason_codes"] == sorted([
        "IDENTITY_UNAVAILABLE",
        "MEMBERSHIP_UNAVAILABLE",
        "RIGHTS_NOT_ADMITTED",
        "RIGHTS_UNAVAILABLE",
    ])


def test_t2_legacy_bytes_unchanged_when_shadow_skipped(production_world, monkeypatch):
    import shutil
    from lib import config

    root_full = production_world.parent / "t2-full"
    shutil.copytree(production_world, root_full)
    monkeypatch.setattr(builder, "_write_shadow_graph_state", lambda *a, **kw: False)
    monkeypatch.setattr(builder, "compose", lambda **kw: artifact())
    rc_skip = builder.build(production_world, mode="LEGACY", generated_at=EMITTED)
    primary_skip = (production_world / PRIMARY).read_bytes()
    mirror_skip = (production_world / MIRROR).read_bytes()
    monkeypatch.setattr(config, "data_dir", lambda: root_full / "data")
    rc_full = builder.build(root_full, mode="LEGACY", generated_at=EMITTED)
    assert rc_skip == rc_full == 0
    assert (root_full / PRIMARY).read_bytes() == primary_skip
    assert (root_full / MIRROR).read_bytes() == mirror_skip


@pytest.mark.parametrize("case", ["injected", "both_null", "capture_unavailable"])
def test_t3_single_fail_open_harness(production_world, monkeypatch, capsys, case):
    from engine.neuralweb import theme_state_adapter as adapter
    from lib import config

    nodes_path = production_world / "data/theme_graph/nodes.parquet"
    if case == "both_null":
        nodes = pd.read_parquet(nodes_path)
        nodes.loc[nodes["node_id"] == "ltheme:finviz:power_grid", "name_en"] = float("nan")
        nodes.loc[nodes["node_id"] == "ltheme:finviz:power_grid", "name_zh"] = float("nan")
        nodes.to_parquet(nodes_path, index=False)

    primary_path = production_world / PRIMARY
    mirror_path = production_world / MIRROR
    real_capture = adapter.capture_owner_bundle
    capture_calls = []

    def capture_spy(root, **kwargs):
        assert primary_path.is_file()
        assert mirror_path.is_file()
        capture_calls.append((primary_path.read_bytes(), mirror_path.read_bytes()))
        if case == "injected":
            raise RuntimeError("injected\nsecond line")
        return real_capture(root, **kwargs)

    if case == "capture_unavailable":
        monkeypatch.setattr(config, "data_dir", lambda: production_world.parent / "else" / "data")
    monkeypatch.setattr(builder, "compose", lambda **kw: artifact())
    monkeypatch.setattr(builder, "run_optional_stages", lambda root: None)
    monkeypatch.setattr(adapter, "capture_owner_bundle", capture_spy)
    monkeypatch.setattr(sys, "argv", ["build_thematic_state.py", "--root", str(production_world)])

    with pytest.raises(SystemExit) as caught:
        builder.main()
    out = capsys.readouterr().out
    lines = out.splitlines()
    warnings = [line for line in lines if line.startswith("::warning title=gmi-shadow-graph-state::")]
    timing_lines = [line for line in lines if line.startswith("[thematic_state] shadow_graph_state timing ")]

    assert caught.value.code == 0
    assert len(capture_calls) == 1
    assert primary_path.read_bytes() == capture_calls[0][0]
    assert mirror_path.read_bytes() == capture_calls[0][1]
    assert not (production_world / SHADOW).exists()
    assert "shadow_graph_state=skipped" in out
    assert len(warnings) == 1
    assert all("second line" not in line for line in lines)
    assert len(timing_lines) == 1

    if case == "injected":
        assert warnings[0].startswith("::warning title=gmi-shadow-graph-state::RuntimeError: injected")
        assert timing_lines[0].endswith("capture_s=na compose_s=na serialize_s=na bytes=na")
    elif case == "both_null":
        assert warnings[0].startswith("::warning title=gmi-shadow-graph-state::ValueError:")
        assert "ltheme:finviz:power_grid" in warnings[0]
        assert "capture_s=" in timing_lines[0]
        assert "compose_s=na" in timing_lines[0]
    else:
        assert len(warnings) == 1

    if case == "capture_unavailable":
        assert "SOURCE_MISSING" in warnings[0] or "configured owner data root" in warnings[0]


def test_t14_timing_line_shape_and_order(production_world, monkeypatch, capsys):
    import re

    monkeypatch.setattr(builder, "compose", lambda **kw: artifact())
    rc = builder.build(production_world, mode="LEGACY", generated_at=EMITTED)
    out = capsys.readouterr().out
    lines = out.splitlines()
    timing_lines = [line for line in lines if line.startswith("[thematic_state] shadow_graph_state timing ")]
    legacy_lines = [line for line in lines if line.startswith("[thematic_state] legacy accepted;")]

    assert rc == 0
    assert len(timing_lines) == 1
    assert len(legacy_lines) == 1
    assert lines.index(legacy_lines[0]) < lines.index(timing_lines[0])
    assert re.fullmatch(
        r"\[thematic_state\] shadow_graph_state timing capture_s=\d+\.\d{3} "
        r"compose_s=\d+\.\d{3} serialize_s=\d+\.\d{3} bytes=\d+",
        timing_lines[0],
    )
    shadow_path = production_world / SHADOW
    assert int(timing_lines[0].rsplit("bytes=", 1)[1]) == shadow_path.stat().st_size
    assert not any(line.startswith("::warning title=gmi-shadow-graph-state::") for line in lines)


def test_t4_validation_failure_no_shadow(production_world, monkeypatch):
    from engine.neuralweb import theme_state_adapter as adapter

    real = adapter.compose_from_owner_bundle

    def bad(bundle, **kw):
        out = real(bundle, **kw)
        out["state"] = dict(out["state"])
        out["state"]["state_sha256"] = "0" * 64
        return out

    monkeypatch.setattr(adapter, "compose_from_owner_bundle", bad)
    rc = _legacy_build(production_world, monkeypatch)
    assert rc == 0
    assert not (production_world / SHADOW).exists()


def test_t5_prior_shadow_preserved_on_failure(production_world, monkeypatch, capsys):
    prior = b'{"schema":"theme_state/v1","prior":"fixture"}\n'
    shadow_path = production_world / SHADOW
    shadow_path.parent.mkdir(parents=True, exist_ok=True)
    shadow_path.write_bytes(prior)
    monkeypatch.setattr(builder, "_write_shadow_graph_state", lambda *a, **kw: False)
    monkeypatch.setattr(builder, "compose", lambda **kw: artifact())
    rc = builder.build(production_world, mode="LEGACY", generated_at=EMITTED)
    out = capsys.readouterr().out
    assert rc == 0
    assert shadow_path.read_bytes() == prior
    assert "shadow_graph_state=skipped" in out


def test_t6a_accepted_generation_refuses_shadow(production_world, monkeypatch):
    from tests.test_theme_state_production import compose
    from tests.test_theme_state_generation import AcceptedFixture

    bundle, _ = compose(production_world)
    entry = g.entry_preflight(production_world, legacy_api=True)
    plan = g.prepare_generation(
        bundle, root=production_world, generated_at=EMITTED,
        activation_at=EMITTED, entry=entry,
    )
    g.publish_generation(production_world, plan, controlled_verifier=AcceptedFixture())
    monkeypatch.setattr(builder, "compose", lambda **kw: artifact())
    assert builder.build(production_world, mode="LEGACY", generated_at=EMITTED) == 1
    assert not (production_world / SHADOW).exists()


def test_t6b_cas_entry_refuses_shadow(tmp_path, monkeypatch):
    monkeypatch.setattr(g, "cas_entry", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("cas")))
    monkeypatch.setattr(builder, "compose", lambda **kw: artifact())
    assert builder.build(tmp_path, mode="LEGACY", generated_at=EMITTED) == 1
    assert not (tmp_path / SHADOW).exists()


def test_t7_shadow_write_failure(production_world, monkeypatch, capsys):
    real_write = g.write_atomic

    def selective(root, rel, raw):
        if rel == builder._SHADOW_GRAPH_STATE_PATH:
            raise OSError("shadow write blocked")
        return real_write(root, rel, raw)

    monkeypatch.setattr(g, "write_atomic", selective)
    monkeypatch.setattr(builder, "compose", lambda **kw: artifact())
    rc = builder.build(production_world, mode="LEGACY", generated_at=EMITTED)
    assert rc == 0
    assert (production_world / PRIMARY).is_file()
    assert not (production_world / SHADOW).exists()
    warnings = [line for line in capsys.readouterr().out.splitlines()
                if line.startswith("::warning title=gmi-shadow-graph-state::")]
    assert len(warnings) == 1


def test_t8_shadow_and_successor_modes_skip_file(production_world, monkeypatch):
    from tests.test_theme_state_production import compose

    bundle, _ = compose(production_world)
    monkeypatch.setattr(builder, "compose", lambda **kw: artifact())
    assert builder.build(production_world, mode="SHADOW", bundle=bundle, generated_at=EMITTED) == 0
    assert not (production_world / SHADOW).exists()
    assert builder.build(production_world, mode="SUCCESSOR", bundle=bundle, generated_at=EMITTED) == 1
    assert not (production_world / SHADOW).exists()


def test_t9_source_shape():
    text = Path(builder.__file__).read_text(encoding="utf-8")
    assert text.count('"data/theme_graph/shadow_theme_state.v1.json"') == 1
    assert text.count("write_atomic(root, _SHADOW_GRAPH_STATE_PATH") == 1
    expected_path = "data/theme_graph/" + selection_cohort_reads.STATE_ARTIFACT_NAME
    assert builder._SHADOW_GRAPH_STATE_PATH == expected_path
    tree = ast.parse(text)
    warning_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", None) == "print"
        and node.args
        and isinstance(node.args[0], ast.JoinedStr)
        and any(
            isinstance(value, ast.Constant)
            and "::warning title=gmi-shadow-graph-state::" in value.value
            for value in node.args[0].values
        )
        and any(keyword.arg == "flush" for keyword in node.keywords)
    ]
    assert len(warning_calls) == 1
    allowed = {
        "argparse", "json", "logging", "sys", "tempfile", "time", "pathlib",
        "datetime", "importlib",
        "engine.neuralweb.thematic_state", "engine.neuralweb.envelope",
        "engine.neuralweb.theme_state_generation", "engine.neuralweb.theme_state_adapter",
        "engine.theme_graph.theme_state",
    }
    stdlib = {"argparse", "json", "logging", "sys", "tempfile", "time", "pathlib", "datetime", "importlib"}
    seen = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name != "__future__":
                    seen.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level or (node.module or "") == "__future__":
                continue
            mod = node.module or ""
            for alias in node.names:
                if mod in stdlib:
                    seen.add(mod)
                elif mod.split(".", 1)[0] in stdlib:
                    seen.add(mod.split(".", 1)[0])
                elif mod in allowed:
                    seen.add(mod)
                else:
                    candidate = f"{mod}.{alias.name}"
                    seen.add(candidate if candidate in allowed else mod)
    assert seen <= allowed, f"unexpected imports: {seen - allowed}"


def test_t10_production_clock_path_writes_shadow(production_world, monkeypatch, capsys):
    """Production LEGACY call shape: no pinned generated_at; emission after capture."""
    from engine.neuralweb import theme_state_adapter as adapter
    import types

    # Capture ends after the pre-capture wall instant (production ordering).
    capture_observed = dt.datetime.fromisoformat("2026-10-04T12:00:00.150000+00:00")

    class CaptureEndClock(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is not None:
                return capture_observed.astimezone(tz)
            return capture_observed.replace(tzinfo=None)

    namespace = {name: getattr(dt, name) for name in dir(dt) if not name.startswith("__")}
    namespace["datetime"] = CaptureEndClock
    monkeypatch.setattr(adapter, "dt", types.SimpleNamespace(**namespace))

    emission_times = [
        dt.datetime(2026, 10, 4, 12, 0, 0, tzinfo=timezone.utc),
        dt.datetime(2026, 10, 4, 12, 0, 0, 100000, tzinfo=timezone.utc),
        dt.datetime(2026, 10, 4, 12, 0, 0, 200000, tzinfo=timezone.utc),
    ]
    call_idx = {"n": 0}

    class ProductionWallClock(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            instant = emission_times[min(call_idx["n"], len(emission_times) - 1)]
            call_idx["n"] += 1
            if tz is not None:
                return instant.astimezone(tz)
            return instant.replace(tzinfo=None)

    real_datetime = dt.datetime
    monkeypatch.setattr(dt, "datetime", ProductionWallClock)

    monkeypatch.setattr(builder, "compose", lambda **kw: artifact())
    rc = builder.build(production_world, mode="LEGACY")
    out = capsys.readouterr().out
    assert rc == 0
    shadow_path = production_world / SHADOW
    assert shadow_path.is_file()
    loaded = json.loads(shadow_path.read_bytes())
    theme_state.validate_state(loaded)

    def _parse_instant(value: str) -> dt.datetime:
        return real_datetime.fromisoformat(value.replace("Z", "+00:00"))

    assert _parse_instant(loaded["generated_at"]) >= _parse_instant(loaded["known_at"])
    assert "shadow_graph_state=written" in out


def test_t11_bilingual_label_fallback_writes_shadow(production_world, monkeypatch, capsys):
    both_node_id = "theme:grid"
    nodes_path = production_world / "data/theme_graph/nodes.parquet"
    nodes = pd.read_parquet(nodes_path)
    native_pair = ("Grid", "电网")
    nodes.loc[nodes["node_id"] == "ltheme:finviz:power_grid", "name_zh"] = float("nan")
    nodes.loc[nodes["node_id"] == "ltheme:ths:900001", "name_en"] = pd.NA
    nodes.loc[nodes["node_id"] == "ltheme:finviz:power_grid", "name_en"] = "Power Grid"
    nodes.to_parquet(nodes_path, index=False)

    monkeypatch.setattr(builder, "compose", lambda **kw: artifact())
    rc = builder.build(production_world, mode="LEGACY", generated_at=EMITTED)
    out = capsys.readouterr().out

    assert rc == 0
    shadow_path = production_world / SHADOW
    assert shadow_path.is_file()
    loaded = json.loads(shadow_path.read_bytes())
    theme_state.validate_state(loaded)
    assert "shadow_graph_state=written" in out
    assert len(loaded["subjects"]) == len(nodes)

    subjects = {subject["node_id"]: subject for subject in loaded["subjects"]}
    assert subjects["ltheme:finviz:power_grid"]["name_en"] == "Power Grid"
    assert subjects["ltheme:finviz:power_grid"]["name_zh"] == "Power Grid"
    assert subjects["ltheme:ths:900001"]["name_en"] == "测试"
    assert subjects["ltheme:ths:900001"]["name_zh"] == "测试"
    assert (subjects[both_node_id]["name_en"], subjects[both_node_id]["name_zh"]) == native_pair


def test_t12_assembled_labels_contract():
    from engine.neuralweb.theme_state_adapter import _assembled_labels

    assert _assembled_labels("node", "x", "y") == ("x", "y")
    assert _assembled_labels("node", "  x ", "y") == ("  x ", "y")
    assert _assembled_labels("node", None, "y") == ("y", "y")
    assert _assembled_labels("node", "x", None) == ("x", "x")
    assert _assembled_labels("node", {"native_null": "NaN"}, "y") == ("y", "y")
    assert _assembled_labels("node", {"native_null": "NaTType"}, "y") == ("y", "y")
    assert _assembled_labels("node", "", "y") == ("y", "y")
    assert _assembled_labels("node", "x", "   ") == ("x", "x")
    for raw_en, raw_zh in ((None, None), ("", {"native_null": "NaN"}), ("  ", "\t")):
        with pytest.raises(ValueError, match="theme subject node:"):
            _assembled_labels("node", raw_en, raw_zh)
    for raw_en, raw_zh in ((1.5, "y"), ({"native_null": "NaN", "x": 1}, "y"), (["a"], "y")):
        with pytest.raises(ValueError, match="invalid captured subject label"):
            _assembled_labels("node", raw_en, raw_zh)


def _wall_clock_masked(payload_json):
    import re

    payload_json = re.sub(r'"observed_at":"[^"]*"', '"observed_at":""', payload_json)
    return re.sub(r'"computed_at":"[0-9T:Z-]*"', '"computed_at":""', payload_json)


def test_t15_capture_memo_reads_each_owner_frame_once_bundle_unchanged(production_world, monkeypatch):
    """RULING_G1_render_cost r4: one owner read per frame per capture; bundle bytes unchanged."""
    from engine.neuralweb import theme_state_adapter as adapter
    from engine.theme_graph import ontology
    from tests.test_theme_state_production import EFFECTIVE

    calls = []
    incumbent = ontology.RepositoryStore

    class Counting(incumbent):
        def read_nodes(self):
            calls.append("read_nodes")
            return super().read_nodes()

        def read_node_lifecycle(self):
            calls.append("read_node_lifecycle")
            return super().read_node_lifecycle()

        def read_edges(self):
            calls.append("read_edges")
            return super().read_edges()

        def read_proposals(self):
            calls.append("read_proposals")
            return super().read_proposals()

    monkeypatch.setattr(ontology, "RepositoryStore", Counting)
    memo = adapter.capture_owner_bundle(production_world, effective_at=EFFECTIVE, known_at=KNOWN)
    memo_calls, calls[:] = list(calls), []
    monkeypatch.setattr(adapter, "_CaptureStoreView", lambda inner: inner)
    direct = adapter.capture_owner_bundle(production_world, effective_at=EFFECTIVE, known_at=KNOWN)

    subjects = json.loads(direct.payload_json)["subjects"]
    assert len(subjects) >= 2
    assert all(s["native_reads"]["ontology"]["availability"] == "AVAILABLE" for s in subjects.values())
    # The adapter's own node census read stays; compose's four frames are read once.
    assert {name: memo_calls.count(name) for name in set(memo_calls)} == {
        "read_nodes": 2, "read_node_lifecycle": 1, "read_edges": 1, "read_proposals": 1}
    assert calls.count("read_edges") == len(subjects)
    assert _wall_clock_masked(memo.payload_json) == _wall_clock_masked(direct.payload_json)
