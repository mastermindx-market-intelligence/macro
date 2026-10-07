"""Bind approved Library copy to destinations in the rendered incumbent page.

This composition adapter does no data I/O and qualifies no numerical values.
The caller supplies the existing workspace, approved copy and rendered pages.
"""
from collections import Counter
from copy import deepcopy
from html.parser import HTMLParser
import logging

from lib.intl_library_view import build_public_intl_library_view


_SECTIONS = {
    "performance_currency": "lb-board",
    "leadership_rotation": "intl-leadership-rotation",
    "cross_country": "intl-cross-country",
    "market_turns": "intl-market-turns",
    "rates_curves_carry": "intl-rates-curves",
    "central_banks_liquidity": "intl-central-banks",
    "credit_bonds": "intl-credit-bonds",
    "euro_fragmentation": "intl-euro-fragmentation",
    "growth_inflation": "intl-growth-inflation",
    "dollar_conditions": "intl-dollar-conditions",
    "structural_fragility": "intl-structural-fragility",
    "contagion": "intl-contagion",
    "cross_market_correlation": "intl-cross-market-correlation",
}


class _RenderedIds(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = Counter()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key == "id" and value:
                self.ids[value] += 1

    handle_startendtag = handle_starttag


def attach_public_library(workspace, *, catalogue, macro_html, stocks_rendered):
    """Return a copy with one metadata panel and only unique existing targets.

    ``stocks_rendered`` is the caller's successful render of the ordinary stocks
    page. Its route deliberately carries no invented research-market filter.
    """
    if workspace is None:
        return None
    if not isinstance(macro_html, str) or type(stocks_rendered) is not bool:
        raise ValueError("invalid rendered destination evidence")
    parser = _RenderedIds()
    parser.feed(macro_html)
    result = deepcopy(workspace)
    config = result["config"]
    context = {
        "market_ids": list(config["markets"]),
        "horizons": list(config["horizons"]),
        "research_market": None,
        "horizon": config["default_horizon"],
        "currency_basis": config["default_basis"],
        "return_basis": "price",
        "source_reference": config["source_reference"],
    }
    targets = {
        key: {"page_id": "macro:intl", "route": "/intl.html",
              "region_id": region, "verified": True}
        for key, region in _SECTIONS.items() if parser.ids[region] == 1
    }
    if stocks_rendered:
        targets["country_sectors_stocks"] = {
            "page_id": "macro:intl_stocks", "route": "/intl_stocks.html",
            "region_id": None, "verified": True,
        }
    view = build_public_intl_library_view(
        context,
        route_bindings={"bindings": catalogue["bindings"], "targets": targets},
        public_copy_decision=catalogue["public_copy_decision"],
    )
    result["library"] = view
    config["library_group_ids"] = [g["id"] for g in view["groups"] if "id" in g]
    config["anchor_ids"] = list(dict.fromkeys([
        *config["anchor_ids"],
        *(tool["target"]["region_id"] for tool in view["tools"]
          if tool["route_state"] == "available" and tool["target"]["region_id"]),
    ]))
    return result


def render_international_pages(template, vm, *, catalogue=None):
    """Render the incumbent destinations before advertising any Library link."""
    stocks = template.render(**vm, mode="stocks")
    macro = template.render(**vm, mode="macro")
    if catalogue is not None and vm.get("intl_workspace") is not None:
        try:
            workspace = attach_public_library(
                vm["intl_workspace"], catalogue=catalogue,
                macro_html=macro, stocks_rendered=True,
            )
            macro = template.render(**{**vm, "intl_workspace": workspace}, mode="macro")
        except (ValueError, KeyError, TypeError) as exc:
            # Keep the complete existing page if approved copy cannot be bound.
            logging.getLogger(__name__).error("International Library unavailable (%s)", type(exc).__name__)
    return macro, stocks
