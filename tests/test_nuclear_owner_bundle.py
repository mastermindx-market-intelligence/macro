"""Declared absence and import-closure laws for the Nuclear loader."""

from __future__ import annotations

import dataclasses
import subprocess
import sys
from pathlib import Path

from engine.market_ontology import nuclear_owner_bundle as loader
from engine.market_ontology import nuclear_theme_research as nuclear
from engine.market_ontology.semiconductor_owner_bundle import PRIVATE_ASSERTIONS_UNBOUND, wire_omission
from tests.nuclear_research_helpers import nuclear_query

SNAPSHOT = ("synthetic-rights-2026-09-25", {})
ROOT = Path(__file__).resolve().parents[1]


def bundle(**changes):
    query = nuclear_query(**changes)
    return loader.load_nuclear_owner_bundle(query, rights_snapshot=SNAPSHOT)


def test_bundle_declares_exactly_two_omissions():
    value = bundle()
    assert value.omissions == (
        PRIVATE_ASSERTIONS_UNBOUND, loader.PUBLIC_ASSERTIONS_UNCURATED)
    assert all(wire_omission(token) == token for token in value.omissions)
    assert all(getattr(value, field) == () for field in (
        "revision_tuple", "assertions", "identity_results", "event_workspaces",
        "financial_packets", "interpretation_blocks", "native_refs"))


def test_declared_absence_surfaces_in_composer_limitations():
    payload = nuclear.compose_nuclear_research(nuclear_query("fuel_cycle"), bundle())
    assert "omitted:private_assertions_unbound" in payload["limitations"]
    assert "omitted:public_assertions_uncurated" in payload["limitations"]


def test_rights_revision_is_the_snapshot_the_shell_enforced_with():
    assert bundle().rights_revision == SNAPSHOT[0]


def test_loader_reads_nothing_from_request():
    first = bundle()
    second = bundle(slice_key="nuclear_components", view="capacity", time_mode="system_replay")
    assert dataclasses.astuple(first) == dataclasses.astuple(second)


def test_import_closure_stays_light():
    code = (
        "import sys; import engine.market_ontology.nuclear_theme_research; "
        "import engine.market_ontology.nuclear_owner_bundle; "
        "print(sorted(m for m in ('requests', 'pandas', 'pyarrow', 'numpy', 'fastapi', "
        "'jinja2', 'engine.neuralweb.company_intelligence_reader') if m in sys.modules))"
    )
    result = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True,
                            text=True, cwd=str(ROOT), timeout=120)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]", result.stdout
