"""Offline transaction/race controls; inputs are explicitly non-economic fixtures."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts import render_intl_durable as durable


def test_file_path_help_resolves_own_lib_before_hostile_pythonpath(tmp_path):
    decoy = tmp_path / "decoy"
    foreign_lib = decoy / "lib"
    foreign_lib.mkdir(parents=True)
    (foreign_lib / "__init__.py").write_text(
        'raise RuntimeError("FOREIGN_LIB_IMPORTED")\n', encoding="utf-8"
    )
    result = subprocess.run(
        [sys.executable, str(Path(durable.__file__).resolve()), "--help"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(decoy), "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert "{build,finalize,verify,stage}" in result.stdout
    assert "FOREIGN_LIB_IMPORTED" not in result.stderr
    assert set(tmp_path.iterdir()) == {decoy}


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args]).decode().strip()


def put(root, path, body):
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)
    return p


@pytest.fixture
def transaction(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.name", "controlled test")
    git(root, "config", "user.email", "test@example.invalid")
    put(root, "scripts/source.py", "# synthetic non-economic fixture\n")
    put(root, "data/fred/FIXTURE.parquet", "fixture retained input")
    put(root, durable.RISK, '{"old":true}')
    put(root, "site/intl.html", "old synthetic page")
    put(root, "site/obsolete.css", "old synthetic asset")
    git(root, "add", ".")
    git(root, "commit", "-qm", "controlled initial source")
    source = git(root, "rev-parse", "HEAD")
    receipt = tmp_path / "receipt.json"
    from lib import config, store
    monkeypatch.setattr(config, "ROOT", root)
    monkeypatch.setattr(config, "load", lambda: {"storage": {"site_dir": "site"}})
    monkeypatch.setattr(config, "data_dir", lambda: root / "data")
    monkeypatch.setattr(store, "_path", lambda group, name: root / "data" / group / (name + ".parquet"))
    monkeypatch.setattr(store, "read", lambda group, name: (root / "data" / group / (name + ".parquet")).read_bytes())
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("INTL_DURABLE_MODE", "true")
    monkeypatch.setenv("INTL_RENDER_SCOPE", "intl")
    monkeypatch.setenv("RENDER_NO_DRIP", "1")
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    monkeypatch.delenv("US_LANE", raising=False)
    from lib.intl_generation_publication import publish_unavailable_generation
    from lib.intl_risk_publication import publish_risk_snapshot
    calls = []

    def builder(*, publication_result):
        calls.append("builder")
        store.read("fred", "FIXTURE")
        pub = publish_risk_snapshot(root / durable.RISK, {"fixture": "non-economic"})
        desc = publish_unavailable_generation(data_root=root / "data")
        pages = {p: sha256(put(root, p, "non-economic synthetic page").read_bytes()).hexdigest()
                 for p in ("site/intl.html", "site/intl_stocks.html")}
        publication_result.update(risk_publication=pub, descriptor=desc, pages=pages)
        return 0

    def feeds(*, render_only):
        assert render_only is True
        calls.append("full-feeds")
        desc = json.loads((root / durable.CURRENT).read_bytes())
        for p in durable._closure(root, desc):
            put(root, "site/feeds/" + Path(p).name, (root / p).read_text())
        put(root, "site/feeds/feeds_meta.json", '{"fixture":"full incumbent mock"}')
        return {}

    import scripts
    builder_module = SimpleNamespace(main=builder)
    feed_module = SimpleNamespace(build=feeds)
    monkeypatch.setitem(sys.modules, "scripts.build_intl", builder_module)
    monkeypatch.setitem(sys.modules, "scripts.build_feeds", feed_module)
    monkeypatch.setattr(scripts, "build_intl", builder_module, raising=False)
    monkeypatch.setattr(scripts, "build_feeds", feed_module, raising=False)
    return SimpleNamespace(root=root, source=source, receipt=receipt, calls=calls,
                           builder=builder_module, feeds=feed_module)


def build(t):
    durable.build(t.root, t.source, t.receipt)


def finish(t):
    build(t)
    # Canonical normalization is allowed between producer receipt and sealing.
    with (t.root / "site/intl.html").open("a") as out:
        out.write(" canonical asset transform")
    durable.finalize(t.root, t.receipt)


def test_same_invocation_partial_generation_bounded_stage_and_candidate(transaction):
    t = transaction
    finish(t)
    put(t.root, "data/run_status.json", "must not publish")
    put(t.root, "data/unrelated/private.json", "must not publish")
    durable.stage(t.root, t.receipt)
    paths = set(git(t.root, "diff", "--cached", "--name-only").splitlines())
    assert durable.RISK in paths
    assert durable.CURRENT in paths
    assert "site/intl.html" in paths
    assert not {"data/run_status.json", "data/unrelated/private.json"} & paths
    assert not any(p.endswith(".parquet") for p in paths)
    git(t.root, "commit", "-qm", "controlled produced closure")
    durable.verify(t.root, t.receipt, target_ref=t.source, candidate_ref="HEAD")
    assert t.calls == ["builder", "full-feeds"]


@pytest.mark.parametrize("key,value", [
    ("GITHUB_EVENT_NAME", "push"), ("INTL_DURABLE_MODE", "false"),
    ("INTL_RENDER_SCOPE", "all"), ("INTL_RENDER_SCOPE", "intl+macro"),
    ("COLLECT_LANE", "nightly"), ("US_LANE", "nightly"),
    ("RENDER_NO_DRIP", "0"),
])
def test_unadmitted_modes_refuse_before_builder(transaction, monkeypatch, key, value):
    t = transaction
    monkeypatch.setenv(key, value)
    with pytest.raises(durable.DurablePublicationError):
        build(t)
    assert t.calls == []


def test_resilient_exit_zero_and_identical_old_file_never_supply_success(transaction):
    t = transaction
    old = (t.root / durable.RISK).read_bytes()
    t.builder.main = lambda **kwargs: 0
    with pytest.raises(durable.DurablePublicationError, match="this invocation"):
        build(t)
    assert (t.root / durable.RISK).read_bytes() == old
    assert not t.receipt.exists()


def test_failed_identical_write_has_no_success_receipt(transaction, monkeypatch):
    t = transaction
    from lib.intl_risk_publication import publish_risk_snapshot
    payload = {"fixture": "non-economic"}
    publish_risk_snapshot(t.root / durable.RISK, payload)
    git(t.root, "add", durable.RISK)
    git(t.root, "commit", "-qm", "controlled identical previous payload")
    t.source = git(t.root, "rev-parse", "HEAD")
    original = Path.write_text

    def fail(path, *args, **kwargs):
        if path == t.root / durable.RISK:
            raise OSError("controlled failed write")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail)
    builder = t.builder.main

    def resilient(**kwargs):
        try:
            return builder(**kwargs)
        except OSError:
            return 0

    t.builder.main = resilient
    with pytest.raises(durable.DurablePublicationError, match="this invocation"):
        build(t)
    assert not t.receipt.exists()


@pytest.mark.parametrize("kind", ["risk", "input", "source", "selector", "page"])
def test_changed_inputs_outputs_or_source_refuse_before_staging(transaction, kind):
    t = transaction
    finish(t)
    path = {"risk": durable.RISK, "input": "data/fred/FIXTURE.parquet",
            "source": "scripts/source.py", "selector": durable.CURRENT,
            "page": "site/intl.html"}[kind]
    put(t.root, path, "changed bounded fixture")
    with pytest.raises(durable.DurablePublicationError):
        durable.stage(t.root, t.receipt)
    assert not git(t.root, "diff", "--cached", "--name-only")


@pytest.mark.parametrize("path", [durable.RISK, durable.CURRENT, "data/fred/FIXTURE.parquet", "scripts/source.py"])
def test_newer_upstream_result_input_or_source_refuses(transaction, path):
    t = transaction
    finish(t)
    # Build a distinct immutable upstream tree without altering our produced
    # worktree. A temporary index is only a controlled local test fixture.
    parent = git(t.root, "rev-parse", "HEAD")
    blob = subprocess.check_output(["git", "-C", str(t.root), "hash-object", "-w", "--stdin"], input=b"newer fixture").decode().strip()
    import os
    env = dict(os.environ, GIT_INDEX_FILE=str(t.receipt.parent / "upstream.index"))
    subprocess.run(["git", "-C", str(t.root), "read-tree", parent], env=env, check=True)
    subprocess.run(["git", "-C", str(t.root), "update-index", "--add", "--cacheinfo", "100644," + blob + "," + path], env=env, check=True)
    tree = subprocess.check_output(["git", "-C", str(t.root), "write-tree"], env=env).decode().strip()
    ref = git(t.root, "commit-tree", tree, "-p", parent, "-m", "newer fixture")
    with pytest.raises(durable.DurablePublicationError):
        durable.verify(t.root, t.receipt, target_ref=ref)


def test_removed_managed_asset_is_manifest_bound(transaction):
    t = transaction
    build(t)
    (t.root / "site/obsolete.css").unlink()
    durable.finalize(t.root, t.receipt)
    durable.stage(t.root, t.receipt)
    assert "site/obsolete.css" in git(t.root, "diff", "--cached", "--name-only")
    put(t.root, "site/obsolete.css", "reappeared")
    with pytest.raises(durable.DurablePublicationError):
        durable.verify(t.root, t.receipt)


@pytest.mark.parametrize("mode", ["120000", "100755"])
def test_same_blob_with_changed_git_file_mode_refuses(transaction, mode):
    t = transaction
    records = durable.capture_inputs(t.root, ["data/fred/FIXTURE.parquet"])
    import os
    env = dict(os.environ, GIT_INDEX_FILE=str(t.receipt.parent / "mode.index"))
    subprocess.run(["git", "-C", str(t.root), "read-tree", t.source], env=env, check=True)
    subprocess.run(["git", "-C", str(t.root), "update-index", "--cacheinfo",
                    mode + "," + records[0]["git_blob"] + ",data/fred/FIXTURE.parquet"], env=env, check=True)
    tree = subprocess.check_output(["git", "-C", str(t.root), "write-tree"], env=env).decode().strip()
    ref = git(t.root, "commit-tree", tree, "-p", t.source, "-m", "same bytes changed file mode")
    with pytest.raises(durable.DurablePublicationError, match="mode mismatch"):
        durable.validate_at_ref(t.root, ref, records)


@pytest.mark.parametrize("retained", [True, False])
def test_full_feed_render_mode_preserves_calendar_without_provider_calls(tmp_path, monkeypatch, retained):
    # Import the real incumbent feed composer, not the transaction's synthetic
    # feed stub. Only retained temporary inputs are present here.
    import importlib.util
    source = Path(__file__).resolve().parents[1] / "scripts/build_feeds.py"
    spec = importlib.util.spec_from_file_location("controlled_full_feed", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from lib import config
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "load", lambda: {"storage": {"site_dir": "site"}})
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path / "data")
    from engine import event_calendar, risk_radar_intl

    def prohibited(*args, **kwargs):
        pytest.fail("render-only feed must not acquire calendar inputs")

    monkeypatch.setattr(event_calendar, "us_macro_events", prohibited)
    monkeypatch.setattr(event_calendar, "high_impact_strip", prohibited)
    monkeypatch.setattr(event_calendar, "commodity_events", prohibited)
    monkeypatch.setattr(risk_radar_intl, "snapshot", lambda profile: None)
    import socket
    monkeypatch.setattr(socket.socket, "connect", prohibited)
    old = '{"asof":"2000-01-01","fixture":"non-economic retained calendar"}'
    if retained:
        put(tmp_path, "site/feeds/event_calendar.json", old)
    put(tmp_path, "data/neuralweb/world_state.json", '{"asof":"2000-01-02"}')
    result = module.build(render_only=True)
    if retained:
        assert (tmp_path / "site/feeds/event_calendar.json").read_text() == old
        assert result["event_calendar.json"] == "2000-01-01"
    else:
        assert not (tmp_path / "site/feeds/event_calendar.json").exists()
        assert "event_calendar.json" not in result
    assert result["world_state.json"] == "2000-01-02"
    manifest = json.loads((tmp_path / "site/feeds/feeds_meta.json").read_text())
    assert {"world_state.json", "intl_generation_current.json"} <= set(manifest["artifacts"])
    if retained:
        assert manifest["artifacts"]["event_calendar.json"]["source"] == "engine/event_calendar.py"
    # Default callers still execute all three incumbent calendar operations.
    calls = []
    for name in ("us_macro_events", "high_impact_strip", "commodity_events"):
        monkeypatch.setattr(event_calendar, name, lambda *args, _name=name: calls.append(_name) or [])
    module.build()
    assert calls == ["us_macro_events", "high_impact_strip", "commodity_events"]
    assert json.loads((tmp_path / "site/feeds/event_calendar.json").read_text())["asof"] != "2000-01-01"


def test_workflow_default_off_and_existing_guards_survive():
    import yaml
    path = Path(__file__).resolve().parents[1] / ".github/workflows/render.yml"
    text = path.read_text()
    workflow = yaml.safe_load(text)
    triggers = workflow.get("on", workflow.get(True))
    assert triggers["workflow_dispatch"]["inputs"]["durable_intl"]["default"] is False
    assert "github.event_name == 'workflow_dispatch' && inputs.durable_intl == true" in text
    assert 'if [ "$INTL_DURABLE_MODE" = true ]; then' in text
    assert '--target-ref origin/main --candidate-ref "$PUBLISH_COMMIT"' in text
    assert text.index("defer and recompute, never rebase stale evidence") < text.index("git rebase --autostash")
    for guard in ("check_site_asset_refs", "check_commodity_publication", "inject_shared_shell.py --check", "push_retry_init"):
        assert guard in text
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            if isinstance(step.get("run"), str):
                import re
                shell = re.sub(r"\$\{\{.*?\}\}", "controlled", step["run"])
                subprocess.run(["bash", "-n"], input=shell.encode(), check=True)
