"""Controller races run in Node against the shipped browser module."""
from pathlib import Path
import hashlib
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_shipped_module_graph_is_content_versioned_and_public_safe():
    """A new parent script must not import a stale immutable dependency."""
    entry = (ROOT / "templates/ontology-company.js").read_text()
    for name in ("ontology-company-controller.js", "ontology-company-contract.js"):
        digest = hashlib.sha256((ROOT / "templates" / name).read_bytes()).hexdigest()[:8]
        assert f"./{name}?v={digest}" in entry
    for name in ("ontology-company.js", "ontology-company-controller.js", "ontology-company-contract.js", "ontology-company.css"):
        source = (ROOT / "templates" / name).read_bytes()
        assert source == (ROOT / "site" / name).read_bytes()
        for secret in (b"fixture-token", b"SYNTHETIC TEST PRODUCT", b"040b2f2e50e6611ce"):
            assert secret not in source
    shell = (ROOT / "site/ontology.html").read_text()
    assert 'id="ox-company"' in shell
    assert re.search(r'<script[^>]*type="module"[^>]*src="ontology-company.js', shell)


def test_controller_request_lifetimes_and_bounded_transport():
    node = shutil.which("node")
    if not node:
        pytest.fail("Node is required for the private company controller checks")
    result = subprocess.run([node, "--test", "tests/ontology_company_controller.test.mjs"],
                            cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
