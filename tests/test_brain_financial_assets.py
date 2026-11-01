"""Exact generated-source custody and existing delivery/gate ownership."""
import hashlib
import json
from pathlib import Path
import yaml
import pytest

ROOT=Path(__file__).resolve().parents[1]
def sha(body):return hashlib.sha256(body).hexdigest()

def test_canonical_bundle_sources_and_output_bytes_are_reproducibly_bound():
    build=ROOT/"tools/brain-output"
    sources=json.loads((build/"terminal-sources.json").read_text())
    for name,receipt in sources["sources"].items():
        assert sha((build/"vendor/terminal"/name).read_bytes())==receipt["sha256"]
    manifest=json.loads((build/"build-manifest.json").read_text())
    assert manifest["normalizer_version"]=="terminal-statements-38723cef-v1"
    assert manifest["terminal_revision"]==sources["revision"]
    for name,receipt in manifest["assets"].items():
        body=(ROOT/"templates"/name).read_bytes()
        assert sha(body)==receipt["sha256"]
        assert len(body)==receipt["bytes"]
        assert body==(ROOT/"site"/name).read_bytes()
    pure=(ROOT/"templates/mm_brain_finance_math_v1.js").read_text()
    assert all(token not in pure for token in ("fetch(","indexedDB","localStorage","sessionStorage","Reader excluded"))
    assert len(pure)<15000
    widget=(ROOT/"templates/mm_brain.js").read_text()
    source=widget[widget.index("  var MD_INLINE ="):widget.index("  /* ── MdStream:")]
    assert sha(source.encode())==manifest["markdown_source_sha256"]

@pytest.mark.parametrize("suite",[
    "tests/test_brain_output_fast_presentation.py","tests/test_brain_financial_views.py",
    "tests/test_brain_financial_assets.py","tests/test_brain_financial_browser.py",
    "tests/test_brain_financial_standalone.py","tests/test_brain_financial_widget.py",
])
def test_new_suites_keep_one_existing_gate_owner(suite):
    jobs=yaml.safe_load((ROOT/".github/ci/legacy-jobs.yml").read_text())["jobs"]
    owners=[(name,j.get("gate")) for name,j in jobs.items()
            for step in j.get("steps",[]) if suite in str(step.get("run",""))]
    assert owners==[("unrun-brain-gateway","code")]

def test_backend_deploy_restart_closure_includes_new_modules():
    source=(ROOT/"app/deploy/update.sh").read_text()
    trigger=source.split("# BEGIN MACRO_API_RESTART_TRIGGER",1)[1].split("# END MACRO_API_RESTART_TRIGGER",1)[0]
    assert "brain_financial_views|brain_financial_reader" in trigger

def test_lazy_asset_hashes_match_controlled_presentation_registry():
    source=(ROOT/"templates/mm_brain_presentation.js").read_text()
    for key,name in [("financeJS","mm_brain_finance.js"),("financeCSS","mm_brain_finance.css"),
                     ("visualJS","mm_brain_visuals.js"),("visualCSS","mm_brain_visuals.css"),("math","mm_brain_math.js")]:
        assert key+":'"+sha((ROOT/"templates"/name).read_bytes())[:8]+"'" in source
