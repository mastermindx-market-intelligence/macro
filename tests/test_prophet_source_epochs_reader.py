"""Exercise the existing stock reader, express refresh and hydration entry point.

All data is synthetic. The refresh test executes the production post-library
try body (without its fail-soft exception handler) against a temporary site.
It does not reimplement the refresh predicate, tier split or payload writer.
"""
from __future__ import annotations

import ast
import copy
import gzip
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from scripts import build_site as build
from engine.prophet_source_epochs import read_source_epochs
from tests.test_dashboard_template_render import _base_vm, _env

ROOT = Path(__file__).resolve().parents[1]
DAY = "2026-10-30"


def _bytes(value):
    return json.dumps(value, separators=(",", ":")).encode()


def epoch_fixture(root):
    site, data = root / "site", root / "data"
    (site / "factordata").mkdir(parents=True)
    (site / "prophet").mkdir()
    (data / "prophet" / "origination_sources").mkdir(parents=True)
    vm = _base_vm()
    a = copy.deepcopy(vm["us_standouts"])
    a["as_of"] = DAY
    raw_a = _bytes(a)
    digest = hashlib.sha256(raw_a).hexdigest()
    book = copy.deepcopy(vm["us_prophet_book"])
    book.update(
        asof="2026-11-01", source_asof=DAY, source_board_asof=DAY,
        source_board_sha256=digest,
        source_board_snapshot_path=f"data/prophet/origination_sources/{digest}.json.gz",
        source_board_snapshot_encoding="gzip",
    )
    index_path = site / "prophet" / "index.json"
    index_path.write_bytes(_bytes(book))
    snapshot = data / "prophet" / "origination_sources" / f"{digest}.json.gz"
    snapshot.write_bytes(gzip.compress(raw_a, mtime=0))
    (site / "factordata" / "us_standouts.json").write_bytes(raw_a)
    capture = {}
    admitted, error = build._read_us_prophet_book(index_path, source_capture=capture)
    assert admitted == book and not error
    epochs = read_source_epochs(
        board_bytes=raw_a, index_bytes=capture["raw"], data_dir=data)
    vm.update(us_standouts=a, us_prophet_book=admitted,
              us_prophet_book_error=False, us_prophet_source_epochs=epochs,
              us_today_source_binding=None, us_today_native_binding=None,
              generated_utc="2026-11-01 22:50")
    return dict(site=site, data=data, vm=vm, raw_a=raw_a,
                capture=capture, index_path=index_path, snapshot=snapshot)


def run_production_refresh(fixture, monkeypatch):
    """Run the exact post-build_library reader/render body with test directories."""
    from engine.us_candidate_lanes import (
        project_candidate_visibility, load_candidate_archive_status,
    )

    monkeypatch.setattr(build.config, "data_dir", lambda: fixture["data"])
    tree = ast.parse(Path(build.__file__).read_text())
    blocks = [
        node for node in ast.walk(tree) if isinstance(node, ast.Try)
        and any(isinstance(stmt, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "_fresh_source_bytes"
                        for t in stmt.targets)
                for stmt in node.body)
    ]
    assert len(blocks) == 1, "the actual express refresh reader must be exercised"
    namespace = dict(vars(build))
    namespace.update(
        site=fixture["site"], env=_env(), vm=fixture["vm"],
        us_standouts=copy.deepcopy(fixture["vm"]["us_standouts"]),
        us_prophet_book_error=False,
        _us_prophet_source_capture=fixture["capture"],
        _us_w3c_binding=hashlib.sha256(fixture["raw_a"]).hexdigest(),
        _us_gate_cfg=dict(preview_rows=1, today_preview_rows=3,
                          gated=True, panels=True, panel_preview_rows=3),
        _us_life_gate_cfg=lambda: True,
        project_candidate_visibility=project_candidate_visibility,
        load_candidate_archive_status=load_candidate_archive_status,
        generated="2026-11-01 22:50",
    )
    exec(compile(ast.Module(body=blocks[0].body, type_ignores=[]),
                 str(Path(build.__file__)), "exec"), namespace)
    return namespace


def test_same_session_changed_membership_reaches_real_reader_and_payload(tmp_path, monkeypatch):
    fixture = epoch_fixture(tmp_path)
    index_before = fixture["index_path"].read_bytes()
    snapshot_before = fixture["snapshot"].read_bytes()
    b = copy.deepcopy(fixture["vm"]["us_standouts"])
    b["buy"][1]["ticker"] = "BETA"
    b["buy"][1]["name"] = "Synthetic replacement"
    raw_b = _bytes(b)
    assert b["as_of"] == DAY
    (fixture["site"] / "factordata" / "us_standouts.json").write_bytes(raw_b)

    run_production_refresh(fixture, monkeypatch)

    epochs = fixture["vm"]["us_prophet_source_epochs"]
    assert epochs["relation"] == "SEPARATE_EPOCHS"
    assert epochs["settlement_status"] == "PENDING"
    assert epochs["current_board"]["sha256"] == hashlib.sha256(raw_b).hexdigest()
    assert epochs["index"]["sha256"] == hashlib.sha256(index_before).hexdigest()
    assert epochs["origination_board"]["sha256"] == hashlib.sha256(fixture["raw_a"]).hexdigest()
    assert fixture["index_path"].read_bytes() == index_before
    assert fixture["snapshot"].read_bytes() == snapshot_before
    payload = json.loads((fixture["site"] / "premiumdata" / "us_stocks.json").read_text())
    assert payload["source_epochs"] == epochs
    assert "BETA" in payload["cards_html"]
    assert "ZEUS" in payload["plan_cards_html"]
    page = BeautifulSoup((fixture["site"] / "us_stocks.html").read_text(), "html.parser")
    disclosure = page.select_one("#us-prophet-source-epochs")
    assert disclosure["data-source-relation"] == "SEPARATE_EPOCHS"
    assert disclosure["data-settlement-status"] == "PENDING"
    assert "separate source snapshots" in disclosure.get_text()
    assert epochs["current_board"]["sha256"] in disclosure.get_text()
    assert epochs["origination_board"]["sha256"] in disclosure.get_text()
    assert "SETTLED" not in disclosure.get_text()
    assert "BETA" not in disclosure.get_text()
    assert "ZEUS" not in disclosure.get_text()


def test_same_board_lost_snapshot_refreshes_to_unavailable(tmp_path, monkeypatch):
    fixture = epoch_fixture(tmp_path)
    fixture["snapshot"].unlink()
    run_production_refresh(fixture, monkeypatch)
    assert fixture["vm"]["us_prophet_source_epochs"]["relation"] == "UNAVAILABLE"
    payload = json.loads((fixture["site"] / "premiumdata" / "us_stocks.json").read_text())
    assert payload["source_epochs"]["settlement_status"] == "PENDING"
    page = (fixture["site"] / "us_stocks.html").read_text()
    assert 'data-source-relation="UNAVAILABLE"' in page


def test_book_and_identity_use_one_read_even_if_path_advances(tmp_path, monkeypatch):
    fixture = epoch_fixture(tmp_path)
    path = fixture["index_path"]
    before = path.read_bytes()
    read = Path.read_bytes
    calls = []
    def advance_after_read(self):
        value = read(self)
        if self == path:
            calls.append(self)
            self.write_bytes(_bytes({"plans": [], "asof": "2026-11-02"}))
        return value
    monkeypatch.setattr(Path, "read_bytes", advance_after_read)
    capture = {"raw": b"stale"}
    book, error = build._read_us_prophet_book(path, source_capture=capture)
    assert not error and book == json.loads(before)
    assert calls == [path] and capture == {"raw": before}
    epochs = read_source_epochs(board_bytes=fixture["raw_a"],
                                index_bytes=capture["raw"], data_dir=fixture["data"])
    assert epochs["index"]["sha256"] == hashlib.sha256(before).hexdigest()
    assert epochs["relation"] == "SAME_SOURCE"


@pytest.mark.parametrize("content", [None, b"{broken", b'{"plans":[null]}'])
def test_missing_or_rejected_book_clears_previous_capture(tmp_path, content):
    path = tmp_path / "index.json"
    if content is not None:
        path.write_bytes(content)
    capture = {"raw": b"prior accepted bytes"}
    book, error = build._read_us_prophet_book(path, source_capture=capture)
    assert book is None and capture == {}
    assert error is (content is not None)


def test_hydration_refuses_every_mixed_identity_before_rows_or_panels(tmp_path):
    fixture = epoch_fixture(tmp_path)
    expected = fixture["vm"]["us_prophet_source_epochs"]
    separate = copy.deepcopy(expected)
    separate["current_board"]["sha256"] = "a" * 64
    separate["relation"] = "SEPARATE_EPOCHS"
    cases = [None, {}, {"schema": "prophet_source_epochs.v1"}]
    for parent, key, value in [
        ("current_board", "sha256", "b" * 64),
        ("current_board", "source_asof", "2026-10-29"),
        ("index", "sha256", "c" * 64),
        ("index", "asof", "2026-11-02"),
        ("index", "source_asof", "2026-10-29"),
        ("origination_board", "sha256", "d" * 64),
        ("origination_board", "source_asof", "2026-10-29"),
        ("origination_board", "snapshot_verified", False),
    ]:
        bad = copy.deepcopy(expected)
        bad[parent][key] = value
        cases.append(bad)
    for key, value in [("relation", "UNAVAILABLE"), ("settlement_status", "SETTLED"),
                       ("schema", "other")]:
        bad = copy.deepcopy(expected)
        bad[key] = value
        cases.append(bad)
    template = (ROOT / "templates" / "dashboard.html.j2").read_text()
    start = template.index("  function hydrate(payload){")
    end = template.index("  /* The chips were baked", start)
    hydrate = template[start:end]
    guard = (ROOT / "templates" / "_prophet_source_epochs.js.j2").read_text()
    node = shutil.which("node")
    assert node, "Node is required to execute the production hydration guard"
    script = guard + "\n" + hydrate + """
let mutations=0, refused=0, panels=0;
const document={getElementById(id){
  if(id==='us-prophet-source-epochs') return {setAttribute(){refused++;}};
  if(id==='us-prophet-epoch-refusal') return {set hidden(v){if(!v) refused++;}};
  return null;
},createElement(){mutations++; throw new Error('unexpected row mutation');}};
const window={}, GATE=null, LIFE_GATE=null;
function hydratePanels(){panels++; return null;}
let SOURCE_EPOCHS=INPUT.expected;
function payload(epochs){return {schema:'tier_payload.v1',page:'us_stocks',
  source_epochs:epochs,plan_cards_html:'WITHHELD_PLAN',cards_html:'WITHHELD_BOARD',rows:[]};}
for(const value of INPUT.bad){
  let threw=false; try{hydrate(payload(value));}catch(e){threw=true;}
  if(!threw || panels || mutations) throw new Error('mixed epochs reached hydration');
}
hydrate(payload(INPUT.expected));
SOURCE_EPOCHS=INPUT.separate;
hydrate(payload(INPUT.separate));
if(panels!==2 || mutations!==0) throw new Error('valid dual epochs were not admitted');
process.stdout.write(JSON.stringify({refusals:INPUT.bad.length,panels,mutations,refused}));
"""
    script = "const INPUT=" + json.dumps(dict(expected=expected, separate=separate, bad=cases)) + ";\n" + script
    result = subprocess.run([node], input=script, text=True, capture_output=True, check=True)
    receipt = json.loads(result.stdout)
    assert receipt["refusals"] == len(cases)
    assert receipt["panels"] == 2 and receipt["mutations"] == 0
    assert receipt["refused"] >= len(cases)


def test_fresh_render_keeps_displayed_index_when_nightly_path_advances(tmp_path, monkeypatch):
    fixture = epoch_fixture(tmp_path)
    captured = fixture["capture"]["raw"]
    replacement = copy.deepcopy(fixture["vm"]["us_standouts"])
    replacement["buy"][1]["ticker"] = "BETA"
    (fixture["site"] / "factordata" / "us_standouts.json").write_bytes(_bytes(replacement))
    fixture["index_path"].write_bytes(_bytes({"plans": [], "asof": "2026-11-02"}))
    run_production_refresh(fixture, monkeypatch)
    epochs = fixture["vm"]["us_prophet_source_epochs"]
    assert epochs["index"]["sha256"] == hashlib.sha256(captured).hexdigest()
    assert fixture["vm"]["us_prophet_book"]["plans"] == json.loads(captured)["plans"]
    page = BeautifulSoup((fixture["site"] / "us_stocks.html").read_text(), "html.parser")
    text = page.select_one("#us-prophet-source-epochs").get_text()
    assert epochs["index"]["sha256"] in text
    assert "Page rendered 2026-11-01 22:50 UTC" in text


@pytest.mark.parametrize("encoding", ["utf-16", "utf-32", "utf-8-sig"])
def test_book_keeps_existing_utf8_admission_rule(tmp_path, encoding):
    path = tmp_path / "index.json"
    path.write_bytes('{"plans":[]}'.encode(encoding))
    capture = {}
    assert build._read_us_prophet_book(path, source_capture=capture) == (None, True)
    assert capture == {}


def test_absent_book_keeps_existing_loading_surface():
    vm = _base_vm()
    vm.update(us_prophet_book=None, us_prophet_book_error=False)
    page = BeautifulSoup(_env().get_template("dashboard.html.j2").render(**vm, mode="stocks"),
                         "html.parser")
    assert page.select_one("#us-plan-block [aria-busy=true]")
    assert page.select_one("#us-prophet-source-epochs") is None
