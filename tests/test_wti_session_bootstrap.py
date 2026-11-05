"""Production constructor/bootstrap composition; all evidence is synthetic and isolated."""
import ast
import base64
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import pytest

from lib import config, store
from lib import wti_session_bootstrap as wiring
from engine.ontology_scenario_runtime import WTISessionSubject
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_ontology_explorer_transport import (  # noqa: F401
    published_wti, x2_inputs, _client, _scenario_payload, SCENARIO_ROUTE,
)
from test_yahoo_availability_capture import modules  # noqa: F401


def publish(root, value):
    raw = store._availability_json(value)
    digest = hashlib.sha256(raw).hexdigest()
    directory = root / "yahoo/.availability_capture/objects"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / (digest + ".json")).write_bytes(raw)
    return digest


def facts():
    return dict(schema="yahoo.wti_native_sessions.v1", ticker="CL=F", purpose="ontology_scenario_display",
        vendor_receipt_ref="sha256:" + "a" * 64, rights_ref="sha256:" + "b" * 64,
        provider_sha256="1" * 64, merged_sha256="2" * 64, context_sha256="3" * 64,
        known_by="2026-11-02T22:00:00Z", last_session_completed_at="2026-11-02T21:00:00Z",
        calendar_id="synthetic-only", calendar_version="v1", label_convention="fixture",
        historical_labels=[["2026-11-02", "2026-11-02"]], future_sessions=["2026-11-03"])


def test_actual_collector_constructor_supplies_reader_only_to_yahoo(monkeypatch, tmp_path, modules):
    from scripts import collect
    _, _, yahoo = modules
    from collectors.base import FetchResult
    from engine import pit_lag_recorder
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    monkeypatch.setenv(wiring.FACTS_PIN, publish(tmp_path, facts()))
    monkeypatch.setattr(pit_lag_recorder, "record_fetch_result", lambda *a, **k: None)
    seen = []
    observed = datetime(2026, 11, 2, 22, tzinfo=timezone.utc)
    def runner(adapter, **kw):
        # This is the real Yahoo constructor. Never invoke fetch or capture.
        seen.append((adapter, kw))
        if adapter.name == "yahoo":
            assert adapter.native_wti_session_reader("1"*64, "2"*64, "3"*64, observed) == facts()
        return FetchResult(adapter.name, "ok")
    monkeypatch.setattr(collect, "run_adapter", runner)
    assert collect._run_one("yahoo", yahoo.YahooAdapter, False)[0].status == "ok"
    class Other:
        name = "other"
        def __init__(self):
            pass  # Unexpected Yahoo-specific kwargs would fail construction.
    assert collect._run_one("other", Other, False)[0].status == "ok"
    assert seen[0][1]["capture_wti_receipts"] is True
    assert "capture_wti_receipts" not in seen[1][1]


@pytest.mark.parametrize("bad", ["absent", "missing", "provider", "merged", "context", "late", "preclose", "shape"])
def test_reader_refuses_unqualified_facts(tmp_path, bad):
    supplied = facts()
    env = {}
    if bad != "absent":
        if bad in ("provider", "merged", "context"):
            supplied[bad + "_sha256"] = "0" * 64
        if bad == "late":
            supplied["known_by"] = "2099-01-01T00:00:00Z"
        if bad == "preclose":
            supplied["last_session_completed_at"] = "2026-11-03T21:00:00Z"
        if bad == "shape":
            supplied["historical_labels"] = [None]
        env[wiring.FACTS_PIN] = "f"*64 if bad == "missing" else publish(tmp_path, supplied)
    read = wiring.native_session_reader(data_dir=tmp_path, environ=env)
    assert read("1"*64, "2"*64, "3"*64, datetime(2026, 11, 2, 22, tzinfo=timezone.utc)) is None


def subject():
    return WTISessionSubject("1"*64, "2"*64, "sha256:"+"3"*64, "sha256:"+"4"*64, "2026-11-03T00:00:00Z")


def admission(selected):
    return dict(schema="ontology.wti_session_admission.v1", subject=asdict(selected),
        native_facts_sha256="5"*64, known_by=selected.knowledge_cutoff)


@pytest.mark.parametrize("field", list(asdict(subject())))
def test_selector_never_carries_admission_to_another_subject(tmp_path, field):
    expected = subject()
    pin = publish(tmp_path, admission(expected))
    select = wiring.session_selector(data_dir=tmp_path, environ={wiring.ADMISSION_PIN: pin})
    assert select(expected).subject == expected
    assert select(replace(expected, **{field: "different"})) is None


@pytest.mark.parametrize("bad", ["late", "naive", "extra", "facts_as_grant", "duplicate", "nonfinite", "corrupt", "symlink", "directory_symlink", "oversized"])
def test_selected_evidence_fails_closed(tmp_path, bad):
    doc = admission(subject())
    if bad == "late": doc["known_by"] = "2099-01-01T00:00:00Z"
    if bad == "naive": doc["known_by"] = "2026-11-02T00:00:00"
    if bad == "extra": doc["issuer_verified"] = True
    if bad == "facts_as_grant": doc = facts()
    digest = publish(tmp_path, doc)
    path = tmp_path / "yahoo/.availability_capture/objects" / (digest + ".json")
    if bad in ("duplicate", "nonfinite", "oversized"):
        raw = {"duplicate": b'{"a":1,"a":2}', "nonfinite": b'{"a":NaN}', "oversized": b' ' * 500001}[bad]
        digest = hashlib.sha256(raw).hexdigest()
        path = path.with_name(digest + ".json")
        path.write_bytes(raw)
    if bad == "corrupt": path.write_bytes(b'{}')
    if bad == "symlink":
        other = tmp_path / "other.json"
        path.rename(other)
        path.symlink_to(other)
    if bad == "directory_symlink":
        directory = path.parent
        other = tmp_path / "other"
        directory.rename(other)
        directory.symlink_to(other, target_is_directory=True)
    assert wiring.session_selector(data_dir=tmp_path, environ={wiring.ADMISSION_PIN: digest})(subject()) is None


def install_actual_bootstrap(app):
    # Execute the actual production import + installation statements without
    # importing unrelated DB/email/background services in app.main.
    source = Path(__file__).resolve().parents[1] / "app/main.py"
    tree = ast.parse(source.read_text())
    nodes = [n for n in tree.body if (
        isinstance(n, ast.ImportFrom) and n.module == "lib.wti_session_bootstrap") or (
        isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
        and isinstance(n.value.func, ast.Name) and n.value.func.id == "configure_wti_sessions")]
    assert len(nodes) == 2
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), {"app": app})


@pytest.mark.parametrize("published_wti", ["v2"], indirect=True)
def test_production_bootstrap_reaches_real_authenticated_route(monkeypatch, published_wti):
    root, _, snapshot, sessions = published_wti
    monkeypatch.setattr(config, "data_dir", lambda: root / "data")
    monkeypatch.delenv(wiring.ADMISSION_PIN, raising=False)
    raw = (root / "data/yahoo/CL_F.observation.json").read_bytes()
    export = json.loads(raw)
    native = json.loads(base64.b64decode(export["capture_receipt"]["content_base64"]))["native_sessions"]
    selected = WTISessionSubject(hashlib.sha256(raw).hexdigest(), export["canonical_parquet"]["sha256"],
        sessions.txi_generation, sessions.manifest_hash, sessions.knowledge_cutoff)
    grant = admission(selected)
    grant["native_facts_sha256"] = hashlib.sha256(store._availability_json(native)).hexdigest()
    with _client(monkeypatch, root, root=root, chain=snapshot["source"]["chain"]) as client:
        install_actual_bootstrap(client.app)
        payload = _scenario_payload(snapshot)
        response = client.post(SCENARIO_ROUTE, json=payload)
        assert response.status_code == 200
        assert response.json()["root_evaluation"]["status"] == "UNAVAILABLE"
        monkeypatch.setenv(wiring.ADMISSION_PIN, publish(root / "data", grant))
        install_actual_bootstrap(client.app)
        accepted = client.post(SCENARIO_ROUTE, json=payload)
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["root_evaluation"]["status"] == "ROOT_THRESHOLD_MET"
        # Client bodies cannot install or override the server selection.
        assert client.post(SCENARIO_ROUTE, json={**payload, "wti_session_selector": grant}).status_code == 400
        grant["known_by"] = export["exported_known_by_utc"]
        monkeypatch.setenv(wiring.ADMISSION_PIN, publish(root / "data", grant))
        install_actual_bootstrap(client.app)
        assert client.post(SCENARIO_ROUTE, json=payload).json()["root_evaluation"]["status"] == "UNAVAILABLE"
        (root / "data/yahoo/CL_F.parquet").write_bytes(b"changed publication")
        changed = client.post(SCENARIO_ROUTE, json=payload)
        assert changed.status_code != 200 or changed.json()["root_evaluation"]["status"] == "UNAVAILABLE"
