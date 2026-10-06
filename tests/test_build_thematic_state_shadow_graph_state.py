"""LEGACY publish shadow graph theme_state/v1 for cohort reads owner."""
from __future__ import annotations

import ast
import datetime as dt
import json
from datetime import timezone
from pathlib import Path

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
    monkeypatch.setattr(builder, "_compose_shadow_graph_state", lambda *a, **kw: None)
    monkeypatch.setattr(builder, "compose", lambda **kw: artifact())
    rc_skip = builder.build(production_world, mode="LEGACY", generated_at=EMITTED)
    primary_skip = (production_world / PRIMARY).read_bytes()
    mirror_skip = (production_world / MIRROR).read_bytes()
    monkeypatch.setattr(config, "data_dir", lambda: root_full / "data")
    rc_full = builder.build(root_full, mode="LEGACY", generated_at=EMITTED)
    assert rc_skip == rc_full == 0
    assert (root_full / PRIMARY).read_bytes() == primary_skip
    assert (root_full / MIRROR).read_bytes() == mirror_skip


def test_t3_capture_failure_no_shadow_warning(production_world, monkeypatch, capsys):
    from engine.neuralweb import theme_state_adapter as adapter
    from lib import config

    monkeypatch.setattr(config, "data_dir", lambda: production_world.parent / "else" / "data")
    monkeypatch.setattr(builder, "compose", lambda **kw: artifact())
    rc = builder.build(production_world, mode="LEGACY", generated_at=EMITTED)
    assert rc == 0
    assert not (production_world / SHADOW).exists()
    assert (production_world / PRIMARY).is_file()
    warnings = [line for line in capsys.readouterr().out.splitlines()
                if line.startswith("::warning title=gmi-shadow-graph-state::")]
    assert len(warnings) == 1


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


def test_t5_prior_shadow_preserved_on_failure(production_world, monkeypatch):
    prior = b'{"schema":"theme_state/v1","prior":"fixture"}\n'
    shadow_path = production_world / SHADOW
    shadow_path.parent.mkdir(parents=True, exist_ok=True)
    shadow_path.write_bytes(prior)
    monkeypatch.setattr(builder, "_compose_shadow_graph_state", lambda *a, **kw: None)
    rc = _legacy_build(production_world, monkeypatch)
    assert rc == 0
    assert shadow_path.read_bytes() == prior


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
