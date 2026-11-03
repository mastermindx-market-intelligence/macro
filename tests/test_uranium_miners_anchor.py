"""``uranium_miners`` is a fuel-cycle anchor. The uranium page stays dark."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from engine.market_ontology import nuclear_theme_research as nuclear
from engine.market_ontology.theme_research_binding import ResearchRefusal
from engine.market_ontology.theme_research_mounts import (
    mount_context,
    registered_anchor_for_basket,
)
from engine.market_ontology.theme_research_registry import registration_for
from tests.nuclear_research_helpers import N07, nuclear_bundle, nuclear_query, variant

ROOT = Path(__file__).resolve().parents[1]


def test_uranium_registration_serves_fuel_cycle_only():
    fuel = N07
    reactor = variant(
        "N07", "U-REACTOR", scope={"technology_facet": "reactor_technology"},
    )
    payload = nuclear.compose_nuclear_research(
        nuclear_query(
            "fuel_cycle", "capacity", anchor_theme_id="uranium_miners",
        ),
        nuclear_bundle(fuel, reactor),
    )
    blob = json.dumps(payload)
    assert fuel["curation_revision"] in blob
    assert reactor["curation_revision"] not in blob
    entry = registration_for("uranium_miners")
    assert entry is not None
    assert entry.slice_keys == ("fuel_cycle",)
    context = mount_context("uranium_miners")
    assert context is not None
    labels = json.loads(context["slice_labels_json"])
    assert labels == {"fuel_cycle": ["Fuel cycle", "核燃料循环"]}
    assert context["title_en"] == "Uranium miners research"
    assert context["title_zh"] == "铀矿研究"
    with pytest.raises(ResearchRefusal) as caught:
        nuclear.compose_nuclear_research(
            nuclear_query(
                "reactor_technology", "capacity",
                anchor_theme_id="uranium_miners",
            ),
            nuclear_bundle(fuel),
        )
    assert caught.value.code == "slice_not_supported"


def test_uranium_page_does_not_borrow_the_nuclear_mount():
    assert registered_anchor_for_basket("uranium_miners") is None
    assert registered_anchor_for_basket("nuclear_power") == "nuclear_power"
    context = mount_context("uranium_miners")
    assert context is not None
    assert context["title_en"] != "Nuclear power industry research"


def test_registry_import_does_not_load_the_uranium_module():
    code = (
        "import sys\n"
        "import engine.market_ontology.theme_research_registry as registry\n"
        "ura = 'engine.market_ontology.uranium_miners_anchor'\n"
        "nuc = 'engine.market_ontology.nuclear_theme_research'\n"
        "assert ura not in sys.modules, 'uranium module loaded at registry import'\n"
        "assert nuc not in sys.modules, 'nuclear composer loaded at registry import'\n"
        "entry = registry.registration_for('uranium_miners')\n"
        "assert entry is not None, 'uranium_miners is unregistered'\n"
        "try:\n"
        "    entry.load_bundle(None)\n"
        "except Exception:\n"
        "    pass\n"
        "assert ura in sys.modules, 'load_bundle did not load uranium_miners_anchor'\n"
        "print('URANIUM_LAZY_OK')\n"
    )
    run = subprocess.run(
        [sys.executable, "-B", "-c", code],
        capture_output=True, text=True, cwd=str(ROOT), timeout=120,
    )
    assert run.returncode == 0, run.stderr
    assert "URANIUM_LAZY_OK" in run.stdout
