"""Gate #8 graph shadow theme_state/v1 for the selection_cohort_reads owner.

Seat ruling G1-RC1 (2026-10-06): the shadow is produced by its OWN narrow mode,
``python -m scripts.build_thematic_state --mode GRAPH_SHADOW_STATE`` (daily.yml
oracle_offrender, off-render), as capture -> state-only compose -> validate ->
atomic write of data/theme_graph/shadow_theme_state.v1.json ONLY. LEGACY (the
engine TIL W0 step) behaves exactly like main and never captures or composes it.
"""
from __future__ import annotations

import ast
import datetime as dt
import json
import re
import shutil
import sys
from datetime import timezone
from pathlib import Path

import pandas as pd
import pytest

from engine.neuralweb import theme_state_generation as g
from engine.theme_graph import selection_cohort_reads, theme_state
from scripts import build_thematic_state as builder
from tests.test_theme_state_generation import artifact
from tests.test_theme_state_production import EFFECTIVE, EMITTED, KNOWN, production_world  # noqa: F401

PRIMARY = "data/neuralweb/theme_state.json"
MIRROR = "site/neuralwebdata/theme_state.json"
SHADOW = Path("data/theme_graph/shadow_theme_state.v1.json")
MODE = "GRAPH_SHADOW_STATE"
WARN = "::warning title=gmi-shadow-graph-state::"
TIMING = "[thematic_state] shadow_graph_state timing "
TIMING_RE = (r"\[thematic_state\] shadow_graph_state timing capture_s=\d+\.\d{3} "
             r"compose_s=\d+\.\d{3} serialize_s=\d+\.\d{3} bytes=\d+ peak_rss_mib=(\d+|na)")


@pytest.fixture(autouse=True)
def nightly(monkeypatch):
    monkeypatch.setenv("COLLECT_LANE", "nightly")


def _shadow_build(root, **kwargs):
    return builder.build(root, mode=MODE, generated_at=EMITTED, **kwargs)


def _legacy_build(root, monkeypatch):
    monkeypatch.setattr(builder, "compose", lambda **kw: artifact())
    return builder.build(root, mode="LEGACY", generated_at=EMITTED)


def _tree(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(Path(root).rglob("*")) if p.is_file()}


def _serialize(state):
    return json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n"


def _forbid(monkeypatch, calls, owner, *names):
    def make(name):
        def spy(*args, **kwargs):
            calls.append(name)
            raise AssertionError(f"{name} must not be called")
        return spy

    for name in names:
        monkeypatch.setattr(owner, name, make(name))


def _write_prior(root):
    prior = b'{"schema":"theme_state/v1","prior":"fixture"}\n'
    path = root / SHADOW
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(prior)
    return prior


# ---------------------------------------------------------------- (i) LEGACY spy


def test_i_legacy_never_captures_composes_or_writes_the_shadow(production_world, monkeypatch, capsys):
    from engine.neuralweb import theme_state_adapter as adapter

    calls: list[str] = []
    _forbid(monkeypatch, calls, adapter, "capture_owner_bundle", "compose_from_owner_bundle",
            "compose_state_only_from_owner_bundle")
    _forbid(monkeypatch, calls, builder, "_write_shadow_graph_state")
    stages: list[Path] = []
    monkeypatch.setattr(builder, "compose", lambda **kw: artifact())
    monkeypatch.setattr(builder, "run_optional_stages", lambda root: stages.append(root))
    monkeypatch.setattr(sys, "argv", ["build_thematic_state.py", "--root", str(production_world)])

    with pytest.raises(SystemExit) as caught:
        builder.main()
    out = capsys.readouterr().out
    lines = [line for line in out.splitlines() if line.startswith("[thematic_state]")]

    assert caught.value.code == 0
    assert calls == []
    assert stages == [production_world.resolve()]
    assert (production_world / PRIMARY).is_file() and (production_world / MIRROR).is_file()
    assert not (production_world / SHADOW).exists()
    assert "shadow_graph_state" not in out and WARN not in out
    assert lines and lines[-1].startswith("[thematic_state] legacy accepted; phase_history +")


def test_i_build_dispatches_the_shadow_writer_only_from_its_own_mode():
    tree = ast.parse(Path(builder.__file__).read_text(encoding="utf-8"))
    build_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build")

    def writer_calls(nodes):
        return [n for node in nodes for n in ast.walk(node)
                if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "_write_shadow_graph_state"]

    guarded = []
    for node in ast.walk(build_fn):
        if (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
                and getattr(node.test.left, "id", None) == "mode"
                and isinstance(node.test.ops[0], ast.Eq)
                and getattr(node.test.comparators[0], "id", None) == "_GRAPH_SHADOW_STATE_MODE"):
            guarded += writer_calls(node.body)
            assert isinstance(node.body[-1], ast.Return)
    assert len(guarded) == 1
    assert writer_calls([build_fn]) == guarded
    module_calls = writer_calls([n for n in tree.body if not (isinstance(n, ast.FunctionDef) and n.name == "build")])
    assert module_calls == []
    assert builder._GRAPH_SHADOW_STATE_MODE == MODE


# ------------------------------------------------- (ii) new mode writes ONLY the shadow


@pytest.mark.parametrize("prior", ["fresh_root", "after_legacy"])
def test_ii_new_mode_writes_only_the_shadow_path(production_world, monkeypatch, capsys, prior):
    if prior == "after_legacy":
        assert _legacy_build(production_world, monkeypatch) == 0
        capsys.readouterr()
    before = _tree(production_world)
    calls: list[str] = []
    _forbid(monkeypatch, calls, g, "entry_preflight", "cas_entry", "prepare_generation", "publish_generation",
            "append_legacy")
    _forbid(monkeypatch, calls, builder, "compose", "run_optional_stages")

    assert _shadow_build(production_world) == 0
    after = _tree(production_world)
    out = capsys.readouterr().out

    assert calls == []
    assert set(before) - set(after) == set()
    changed = {path for path in after if before.get(path) != after[path]}
    expected = {SHADOW.as_posix()} | ({g.LOCK} if g.LOCK not in before else set())
    assert changed == expected
    if g.LOCK in changed:
        assert after[g.LOCK] == b""
    for legacy_path in (PRIMARY, MIRROR, "data/neuralweb/theme_phase_history.jsonl"):
        assert before.get(legacy_path) == after.get(legacy_path)
    assert "shadow_graph_state=written" in out
    assert "legacy accepted" not in out


# --------------------------------------------- (iii) state-only == full compose, byte-equal


@pytest.mark.parametrize("world", ["native_labels", "label_fallback"])
def test_iii_state_only_compose_is_byte_equal_to_full_compose(production_world, world):
    from engine.neuralweb import theme_state_adapter as adapter

    if world == "label_fallback":
        nodes_path = production_world / "data/theme_graph/nodes.parquet"
        nodes = pd.read_parquet(nodes_path)
        nodes.loc[nodes["node_id"] == "ltheme:finviz:power_grid", "name_zh"] = float("nan")
        nodes.loc[nodes["node_id"] == "ltheme:ths:900001", "name_en"] = pd.NA
        nodes.to_parquet(nodes_path, index=False)

    bundle = adapter.capture_owner_bundle(production_world, effective_at=EFFECTIVE, known_at=KNOWN)
    full = adapter.compose_from_owner_bundle(bundle, generated_at=EMITTED)["state"]
    only = adapter.compose_state_only_from_owner_bundle(bundle, generated_at=EMITTED)
    theme_state.validate_state(only)
    assert _serialize(only) == _serialize(full)

    # The producer's file is exactly the full-compose state of the same capture.
    assert _shadow_build(production_world) == 0
    same_capture = adapter.capture_owner_bundle(production_world, effective_at=EMITTED[:10], known_at=EMITTED)
    expected = adapter.compose_from_owner_bundle(same_capture, generated_at=EMITTED)["state"]
    assert (production_world / SHADOW).read_bytes() == _serialize(expected)


def test_iii_state_only_keeps_the_emission_clock_guard(production_world):
    from engine.neuralweb import theme_state_adapter as adapter

    bundle = adapter.capture_owner_bundle(production_world, effective_at=EFFECTIVE, known_at=KNOWN)
    early = "2026-10-04T10:00:00Z"
    with pytest.raises(ValueError, match="generation emission precedes actual owner capture"):
        adapter.compose_from_owner_bundle(bundle, generated_at=early)
    with pytest.raises(ValueError, match="generation emission precedes actual owner capture"):
        adapter.compose_state_only_from_owner_bundle(bundle, generated_at=early)


# ------------------------------------------------------------- positive shadow + reads


def test_t1_positive_shadow_and_reads(production_world):
    assert _shadow_build(production_world) == 0
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


# ------------------------------------------------------------- single fail-open harness


@pytest.mark.parametrize("case", ["injected", "both_null", "capture_unavailable"])
def test_t3_single_fail_open_harness(production_world, monkeypatch, capsys, case):
    from engine.neuralweb import theme_state_adapter as adapter
    from lib import config

    assert _legacy_build(production_world, monkeypatch) == 0
    legacy_before = {path: (production_world / path).read_bytes() for path in (PRIMARY, MIRROR)}
    capsys.readouterr()

    if case == "both_null":
        nodes_path = production_world / "data/theme_graph/nodes.parquet"
        nodes = pd.read_parquet(nodes_path)
        nodes.loc[nodes["node_id"] == "ltheme:finviz:power_grid", "name_en"] = float("nan")
        nodes.loc[nodes["node_id"] == "ltheme:finviz:power_grid", "name_zh"] = float("nan")
        nodes.to_parquet(nodes_path, index=False)

    real_capture = adapter.capture_owner_bundle
    capture_calls = []

    def capture_spy(root, **kwargs):
        capture_calls.append(kwargs)
        if case == "injected":
            raise RuntimeError("injected\nsecond line")
        return real_capture(root, **kwargs)

    stages: list[Path] = []
    if case == "capture_unavailable":
        monkeypatch.setattr(config, "data_dir", lambda: production_world.parent / "else" / "data")
    monkeypatch.setattr(builder, "run_optional_stages", lambda root: stages.append(root))
    monkeypatch.setattr(adapter, "capture_owner_bundle", capture_spy)
    monkeypatch.setattr(sys, "argv", ["build_thematic_state.py", "--root", str(production_world), "--mode", MODE])

    with pytest.raises(SystemExit) as caught:
        builder.main()
    out = capsys.readouterr().out
    lines = out.splitlines()
    warnings = [line for line in lines if line.startswith(WARN)]
    timing_lines = [line for line in lines if line.startswith(TIMING)]

    assert caught.value.code == 0
    assert stages == []
    assert len(capture_calls) == 1
    for path, raw in legacy_before.items():
        assert (production_world / path).read_bytes() == raw
    assert not (production_world / SHADOW).exists()
    assert "shadow_graph_state=skipped" in out
    assert len(warnings) == 1
    assert all("second line" not in line for line in lines)
    assert len(timing_lines) == 1

    if case == "injected":
        assert warnings[0].startswith(WARN + "RuntimeError: injected")
        assert re.search(r"capture_s=na compose_s=na serialize_s=na bytes=na peak_rss_mib=(\d+|na)$",
                         timing_lines[0])
    elif case == "both_null":
        assert warnings[0].startswith(WARN + "ValueError:")
        assert "ltheme:finviz:power_grid" in warnings[0]
        assert "capture_s=" in timing_lines[0] and "capture_s=na" not in timing_lines[0]
        assert "compose_s=na" in timing_lines[0]
    else:
        assert "SOURCE_MISSING" in warnings[0] or "configured owner data root" in warnings[0]


def test_t14_timing_line_shape_and_order(production_world, capsys):
    assert _shadow_build(production_world) == 0
    lines = capsys.readouterr().out.splitlines()
    timing_lines = [line for line in lines if line.startswith(TIMING)]
    assert len(timing_lines) == 1
    assert re.fullmatch(TIMING_RE, timing_lines[0])
    assert lines.index(timing_lines[0]) < lines.index("[thematic_state] shadow_graph_state=written")
    assert not any(line.startswith("[thematic_state] legacy accepted;") for line in lines)
    size = int(re.search(r" bytes=(\d+) ", timing_lines[0]).group(1))
    assert size == (production_world / SHADOW).stat().st_size
    assert not any(line.startswith(WARN) for line in lines)


# ------------------------------------------------ failures leave the prior shadow untouched


@pytest.mark.parametrize("failure", ["validation", "compose_raises", "write_blocked", "owner_busy"])
def test_t5_prior_shadow_preserved_on_failure(production_world, monkeypatch, capsys, failure):
    from engine.neuralweb import theme_state_adapter as adapter

    prior = _write_prior(production_world)
    real_compose = adapter.compose_state_only_from_owner_bundle
    if failure == "validation":
        def bad(bundle, **kw):
            state = dict(real_compose(bundle, **kw))
            state["state_sha256"] = "0" * 64
            return state
        monkeypatch.setattr(adapter, "compose_state_only_from_owner_bundle", bad)
    elif failure == "compose_raises":
        monkeypatch.setattr(adapter, "compose_state_only_from_owner_bundle",
                            lambda bundle, **kw: (_ for _ in ()).throw(RuntimeError("compose blew up")))
    elif failure == "write_blocked":
        real_write = g.write_atomic

        def selective(root, rel, raw):
            if rel == builder._SHADOW_GRAPH_STATE_PATH:
                raise OSError("shadow write blocked")
            return real_write(root, rel, raw)
        monkeypatch.setattr(g, "write_atomic", selective)

    before = _tree(production_world)
    if failure == "owner_busy":
        with g.family_lock(production_world):
            rc = _shadow_build(production_world)
    else:
        rc = _shadow_build(production_world)
    out = capsys.readouterr().out
    warnings = [line for line in out.splitlines() if line.startswith(WARN)]

    assert rc == 0
    assert (production_world / SHADOW).read_bytes() == prior
    assert {k: v for k, v in _tree(production_world).items() if k != g.LOCK} == \
        {k: v for k, v in before.items() if k != g.LOCK}
    assert "shadow_graph_state=skipped" in out
    assert len(warnings) == 1
    if failure == "owner_busy":
        assert "OWNER_BUSY" in warnings[0]


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
    assert text.count("compose_state_only_from_owner_bundle(") == 1
    assert "compose_from_owner_bundle(" not in text
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
    stdlib = {"argparse", "json", "logging", "sys", "tempfile", "time", "pathlib", "datetime", "importlib",
              "resource"}
    allowed = stdlib | {
        "engine.neuralweb.thematic_state", "engine.neuralweb.envelope",
        "engine.neuralweb.theme_state_generation", "engine.neuralweb.theme_state_adapter",
        "engine.theme_graph.theme_state",
    }
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
    """Production call shape: no pinned generated_at; emission is stamped after capture."""
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

    # First wall read = known_at (before capture); every later read = after capture.
    emission_times = [
        dt.datetime(2026, 10, 4, 12, 0, 0, tzinfo=timezone.utc),
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

    rc = builder.build(production_world, mode=MODE)
    out = capsys.readouterr().out
    assert rc == 0
    shadow_path = production_world / SHADOW
    assert shadow_path.is_file()
    loaded = json.loads(shadow_path.read_bytes())
    theme_state.validate_state(loaded)

    def _parse_instant(value: str) -> dt.datetime:
        return real_datetime.fromisoformat(value.replace("Z", "+00:00"))

    assert _parse_instant(loaded["generated_at"]) >= _parse_instant(loaded["known_at"])
    observed = theme_state.read_theme_state(
        loaded, "theme:grid", effective_at=loaded["effective_at"],
        known_at=loaded["generated_at"], expected_generation_id=loaded["generation_id"],
    )
    assert "SOURCE_AFTER_CUTOFF" not in observed["reason_codes"], observed["reason_codes"]
    assert observed["status"] == "UNAVAILABLE"
    assert {"IDENTITY_UNAVAILABLE", "MEMBERSHIP_UNAVAILABLE", "RIGHTS_NOT_ADMITTED",
            "RIGHTS_UNAVAILABLE"} <= set(observed["reason_codes"])
    assert "shadow_graph_state=written" in out


def test_t11_bilingual_label_fallback_writes_shadow(production_world, capsys):
    both_node_id = "theme:grid"
    nodes_path = production_world / "data/theme_graph/nodes.parquet"
    nodes = pd.read_parquet(nodes_path)
    native_pair = ("Grid", "电网")
    nodes.loc[nodes["node_id"] == "ltheme:finviz:power_grid", "name_zh"] = float("nan")
    nodes.loc[nodes["node_id"] == "ltheme:ths:900001", "name_en"] = pd.NA
    nodes.loc[nodes["node_id"] == "ltheme:finviz:power_grid", "name_en"] = "Power Grid"
    nodes.to_parquet(nodes_path, index=False)

    rc = _shadow_build(production_world)
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


@pytest.mark.parametrize("failure", ["midnight", "native_mutation", "qualification_mutation"])
def test_live_capture_refusal_preserves_previous_shadow(production_world, monkeypatch, capsys, failure):
    from engine.neuralweb import theme_state_adapter as adapter
    from engine.neuralweb import thematic_state as legacy
    from tests.test_theme_state_owner_adapter import _live_capture_clock

    prior = _write_prior(production_world)
    instants = ("2026-10-04T23:59:59Z", "2026-10-05T00:00:01Z") if failure == "midnight" else (
        "2026-10-04T12:00:00Z", "2026-10-04T12:00:03Z")
    _live_capture_clock(monkeypatch, *instants)

    def mutate():
        (production_world / legacy._NARRATIVE_PATH).write_text('{"as_of":"2026-10-03","narratives":[]}')

    if failure == "native_mutation":
        original = adapter.ontology.compose_neighborhood

        def during_native(*args, **kwargs):
            result = original(*args, **kwargs)
            mutate()
            return result
        monkeypatch.setattr(adapter.ontology, "compose_neighborhood", during_native)
    elif failure == "qualification_mutation":
        class Reader:
            def read_state_qualification(self, **kwargs):
                mutate()
                return None
        original = adapter.capture_owner_bundle
        monkeypatch.setattr(adapter, "capture_owner_bundle",
                            lambda *args, **kwargs: original(*args, owner_readers=Reader(), **kwargs))

    assert builder.build(production_world, mode=MODE) == 0
    assert (production_world / SHADOW).read_bytes() == prior
    out = capsys.readouterr().out
    assert "shadow_graph_state=skipped" in out
    assert "day changed" in out if failure == "midnight" else "source changed" in out
