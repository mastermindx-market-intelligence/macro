"""Actual destination binding and failure isolation for public Library copy."""
from copy import deepcopy
from html.parser import HTMLParser
import json
from pathlib import Path

import pytest

from lib.intl_library_mount import attach_public_library


CATALOGUE = json.loads((Path(__file__).resolve().parents[1] /
                        "config/intl_library_catalogue.json").read_text())
WORKSPACE = {"config": {"markets": ["JP", "GB"], "horizons": ["1m", "3m"],
                        "bases": ["usd_unhedged", "local"], "default_horizon": "1m",
                        "default_basis": "usd_unhedged", "source_reference": None,
                        "anchor_ids": ["intl-legacy-research"], "library_group_ids": []},
             "panels": [{"unrelated_owner_payload": [None, 1, 2]}]}


def mount(html="", stocks=True, catalogue=None):
    return attach_public_library(WORKSPACE, catalogue=CATALOGUE if catalogue is None else catalogue,
                                 macro_html=html, stocks_rendered=stocks)


def test_public_copy_mount_preserves_numeric_context_and_all_inputs():
    original, catalogue = deepcopy(WORKSPACE), deepcopy(CATALOGUE)
    result = mount('<h2 id="intl-cross-country">Existing comparison</h2>')
    assert WORKSPACE == original and CATALOGUE == catalogue
    assert result["panels"] == WORKSPACE["panels"]
    assert result["config"]["source_reference"] is None
    assert result["library"]["context"]["source_reference"] is None
    assert result["library"]["catalogue_generation"].startswith("public-copy:sha256:")
    assert len(result["library"]["tools"]) == 18
    assert len(result["config"]["library_group_ids"]) == 6
    assert all(tool["metrics"] == [] and tool["data_state"] == "unknown"
               for tool in result["library"]["tools"])
    result["panels"][0]["unrelated_owner_payload"].append(3)
    assert WORKSPACE == original


@pytest.mark.parametrize("html", [
    '<script>const text = \'id="intl-cross-country"\';</script>',
    '<!-- <h2 id="intl-cross-country">Fake</h2> -->',
    '<h2 id="intl-cross-country">A</h2><h2 id="intl-cross-country">B</h2>',
    '<h2 id="intl-cross-country" id="intl-cross-country">Duplicate attribute</h2>',
    '<h2 id="other">Cross-country comparison</h2>',
])
def test_missing_ambiguous_or_text_only_destination_is_not_advertised(html):
    result = mount(html, stocks=False)
    assert all(t["route_state"] == "unavailable" for t in result["library"]["tools"])
    assert result["config"]["anchor_ids"] == ["intl-legacy-research"]


def test_stock_destination_is_ordinary_route_and_requires_successful_render():
    tool = next(t for t in mount()["library"]["tools"] if t["presentation_key"] == "country_sectors_stocks")
    assert tool["target"] == {"page_id": "macro:intl_stocks", "route": "/intl_stocks.html", "region_id": None}
    assert next(t for t in mount(stocks=False)["library"]["tools"]
                if t["presentation_key"] == "country_sectors_stocks")["target"] is None


def test_changed_copy_needs_matching_public_copy_decision():
    changed = deepcopy(CATALOGUE)
    changed["bindings"]["tools"][0]["label_en"] = "Unapproved change"
    with pytest.raises(ValueError, match="digest"):
        mount(catalogue=changed)


def test_no_workspace_is_not_created_from_catalogue_alone():
    assert attach_public_library(None, catalogue=CATALOGUE, macro_html="", stocks_rendered=True) is None
