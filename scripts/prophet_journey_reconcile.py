#!/usr/bin/env python3
"""Prophet journey reconciliation harness — release-integration proof tool.

A deterministic, offline checker that takes (a) a saved DOM snapshot of the
authenticated ``/us_stocks.html`` page (outerHTML after page JS ran), (b)
``factordata/us_standouts.json``, (c) ``prophet/index.json``, and one ticker,
and reports whether the ONE Prophet decision journey — Today → Screener
(table + grid) → same candidate's detail → linked native plan OR honest
no-plan path — shows the SAME record with reconciled clocks, preserved
source values, plain language, and no cross-market interception.

Output = a JSON receipt. Exit 0 PASS, 1 FAIL, 2 PARTIAL (no FAIL but ≥1 N/A).

OWNED FILES (the only files this script is allowed to touch):
  - scripts/prophet_journey_reconcile.py     (this file)
  - tests/test_prophet_journey_reconcile.py  (the frozen test suite)

CITATION INDEX — every selector / expression is cited to the template or
builder line that defines it, on the base sha the script was built on.
All references are at base ``bb310311b7`` (HEAD of ``origin/main`` at
build time). The line numbers are the actual line numbers in those files
on that commit; if a referenced template or builder line moves, this
script's GAPS section should name the gap and rebase the citation.

Selectors / expressions and their owners:
  J1 — ``#us-standouts .pvcard[data-ticker=T]`` — board card node:
       the card's ``data-ticker`` attribute is emitted by the prophet
       card macro at templates/_prophet_card.html.j2:608. Nested price
       market attributes are optional at :635; the US board supplies
       lowercase ``mkt: 'us'`` at templates/_us_board_cards.html.j2:283-285.
       ``data-lane`` / ``data-stage`` heading sentinels emitted by the
       board at templates/_us_board_cards.html.j2:78 / :66
       (``<div class="nb-lane-hd" data-lane="...">`` and
       ``<div class="nb-stage-hd sg-..." data-stage="...">``).
  J2 — ``#us-candidate-pool [data-view="table"] [data-ticker=T]`` row —
       emitted by the pool rows partial at
       templates/_us_candidate_pool_rows.html.j2:27
       (``<div class="ucp-row" data-ticker="..." data-off-board="...">``).
  J3 — same row under ``#us-candidate-pool [data-view="grid"]`` —
       rendered by the same partial into the same DOM nodes; the view
       switch is a client-side attribute swap on the pool container
       (templates/_us_candidate_pool.html.j2:13 CSS, :67 JS).
  J4 — payload membership in ``us_standouts.buy ∪ watch ∪ candidate_pool.rows``:
       ``buy`` / ``watch`` keys consumed in templates/_us_board_cards.html.j2
       (the ``items`` param) and scripts/build_site.py:5284 / :5658; the
       ``candidate_pool`` dict key (NOT a list — it carries
       ``counts / status / rows / source_digest / as_of``) is constructed
       in engine/us_candidate_lanes.py:1007 (``result.update(...,
       source_digest=digest, ...)``).
  J5 — ``[data-setup-ticker=T]`` detail node — emitted by the table-only
       presenter at templates/_prophet_setup_detail.html.j2:91
       (``<details class="pv-setup-inline pv-setup-table"
       data-setup-ticker="..." data-setup-asof="...">``); ``data-native-id``
       and ``data-setup-kind`` at :27 (the ``body(...)`` macro's
       ``<div class="pv-setup-body" data-setup-kind="..."
       data-native-id="...">``); ``data-entry-status`` at :34
       (``<p class="pvs-read" data-entry-status="...">``) bound to
       ``es.get('status')`` where ``es = row.get('entry_signal')``.
  J6 — ``[data-source-field=<path>]`` fields — emitted by the field macro
       at templates/_prophet_setup_detail.html.j2:12
       (``<div class="pvs-field" data-source-field="..."><dt>...
       <dd>{{ value(v, money, boolean) }}</dd></div>``); ``<path>`` is
       the SAME dotted path passed to the field macro (e.g.
       ``entry_signal.buy_zone.low`` at :44).
  J7 — ``#us-candidate-pool[data-as-of] / [data-total] / [data-source-digest]`` —
       emitted by the pool container at templates/_us_candidate_pool.html.j2:17
       (``<details class="ucp" id="us-candidate-pool" data-status="..."
       data-total="{{ _pc.eligible ... }}" data-as-of="{{ _pool.as_of or
       '' }}" data-source-digest="{{ _pool.source_digest or '' }}">``);
       ``_pc.eligible`` is the engine's counts.eligible at
       engine/us_candidate_lanes.py:1008; ``_pool.source_digest`` is the
       digest computed at engine/us_candidate_lanes.py:1002-1006.
  J8 — ``plans = [p for p in index.plans if p.asset == T]`` — plans array
       written at scripts/build_prophet.py:2466 (the ``plans.append(...)
       inside the ``_emit_index_entries`` loop) and read at
       scripts/build_site.py:4858 / :5285; LIVE ``lifecycle_state`` values
       determined by ``build_prophet.lifecycle_state()`` at
       scripts/build_prophet.py:1383 / cells enumerated at :1331
       (``LIFECYCLE_CELLS = ("watch", "ready", "entered", "delivering",
       "overtime", "invalidated", "resolved")``); plan card id emitted by
       the prophet card macro at templates/_prophet_card.html.j2:608
       (``{% if cx.get('id') %} id="pv-{{ cx.id|e }}"{% endif %}``).
  J9 — ``index.source_board_asof`` and ``index.asof`` — written by the
       builder at scripts/build_prophet.py:2607 ("asof" — the
       publication stamp, with "as_of" accepted for synthetic / legacy
       payloads) and :2609 ("source_board_asof", which must equal
       standouts.as_of). The page's plan clock ``#plv-asof``
       (templates/dashboard.html.j2:16378) is filled by the page JS
       ``_plvAsOf`` at templates/dashboard.html.j2:18992, stacked at
       :19422 — the stamp is TIME-OF-DAY ("as of 3:41 pm ET" / "截至
       美东 15:41"), not an ISO date. PASS = (a) source_board_asof ==
       standouts.as_of and source_board_asof <= index.asof AND (b)
       ``#plv-asof`` is present AND non-empty (proves JS rendered the
       panel). FAIL when either reconciliation breaks OR the panel
       stamp is empty on a snapshot with populated index clocks.
       N/A only when ``#plv-asof`` is absent (e.g., dialog-only
       fixture) — the spec's "N/A with observed text" applies when the
       node is missing, not when the value is empty.
  J10 — journey node href / data-mkt filter — the journey nodes are
       ``#us-standouts``, ``#us-candidate-pool``, the per-ticker detail
       node (``[data-setup-ticker=T]``), and the linked plan node if any
       (``#pv-<id>`` at templates/_prophet_card.html.j2:608).
  J11 — raw snake_case token scan over the visible text of the journey
       nodes in the selected locale (the ``.l-en`` or ``.l-zh`` span
       children; templates/_prophet_card.html.j2:75, :586-588, the
       ``{% macro t(en, zh) %}`` wrappers throughout) — drops the other
       locale's spans, ``<script>``/``<style>``, and HTML attributes. Only
       raw values that contain ``_`` and match one of the enumerated
       enum field values across the page's standouts rows and index
       plans (lifecycle_state, entry_status, entry_zone_state,
       management_status, phase, admission_class, plus standouts row
       fields lane, state, entry_signal) count as hits.
  J12 — ``.mx-error[role=alert]`` — emitted by the lifecycle ladder
       error state at templates/_prophet_card.html.j2:120
       (``<div class="mx-error" role="alert">``); the alert text is the
       bilingual "Tracking unavailable" copy at :123-124.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

try:
    from bs4 import BeautifulSoup, NavigableString, Tag
except ImportError as exc:  # pragma: no cover - bs4 is in requirements
    raise SystemExit(f"beautifulsoup4 is required: {exc}")


SCHEMA = "mastermind.prophet_journey_reconciliation.v1"
GENERATED_BY = "scripts/prophet_journey_reconcile.py"

# --------------------------------------------------------------------------- #
# Field enumerations used for J11 (raw-snake-case token scan).
# These mirrors the live build's enum vocabulary; the harness reads the actual
# values off the standouts rows and index plans it was handed (no enumeration
# here is the source of truth — the JSON payloads are).
# --------------------------------------------------------------------------- #
PLAN_ENUM_FIELDS = (
    "lifecycle_state",
    "entry_status",
    "entry_zone_state",
    "management_status",
    "phase",
    "admission_class",
)
STANDOUTS_ENUM_FIELDS = ("lane", "state", "entry_signal")

# Cross-market href patterns (J10). Case-insensitive; the journey must not
# carry any HK / China / Canada / Intl market HTML inside its nodes.
_CROSSMARKET_HREF_RE = re.compile(
    r"^(hk|china|canada|intl)[_a-z]*\.html", re.IGNORECASE
)

# Tokens flagged as "raw internal enums" by J11: strings that contain ``_``
# AND match one of the enum values present in the supplied standouts/index
# payloads. Plain words (without underscores) are NEVER flagged — they are
# language copy, not enum leakage.
_SNAKE_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")

# Stale/empty sentinel strings the detail template prints when a field is
# missing — J6 records these as N/A-but-visible (not a hard FAIL on the
# preservation check) because the template's fail-soft surface is itself
# the honest answer.
EMPTY_SENTINELS = frozenset({"", "none", "nan", "undefined", "null",
                            "not supplied", "来源未提供"})

# Default scope: every journey node this harness considers. J10 / J11 walk
# exactly these — never their full-page siblings (the board's other markets
# are out of scope on purpose; we are checking the ONE US journey).
JOURNEY_SELECTORS = (
    "#us-standouts",
    "#us-candidate-pool",
    '[data-setup-ticker]',  # the per-ticker detail node(s)
    # The linked plan node if any — identified by ``#pv-<id>`` (the prophet
    # card's own id; ``templates/_prophet_card.html.j2:608``). Added by J8
    # AFTER the linked plans are known; the walk code unions it in.
)


# =========================================================================== #
# CLI plumbing
# =========================================================================== #
def _parse_argv(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog=GENERATED_BY, description=__doc__)
    p.add_argument("--page", required=True, help="Path to the saved page HTML")
    p.add_argument("--standouts", required=True,
                   help="Path to factordata/us_standouts.json")
    p.add_argument("--index", required=True,
                   help="Path to prophet/index.json")
    p.add_argument("--ticker", default=None,
                   help="Ticker to audit; default = first US board card")
    p.add_argument("--locale", choices=("en", "zh"), default="en",
                   help="Locale span treated as visible text "
                        "(default en). Mirrors the data-lang attribute.")
    p.add_argument("--out", required=True, help="Path to write the JSON report")
    return p.parse_args(argv)


def _sha256(path: Path) -> tuple[str, int]:
    raw = path.read_bytes()
    return hashlib.sha256(raw).hexdigest(), len(raw)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


# =========================================================================== #
# Page parsing — beautifulsoup over the saved outerHTML.
# =========================================================================== #
def _parse_page(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def _select_first(soup: BeautifulSoup, selector: str) -> Tag | None:
    node = soup.select_one(selector)
    return node if isinstance(node, Tag) else None


def _select_all(soup: BeautifulSoup, selector: str) -> list[Tag]:
    return [n for n in soup.select(selector) if isinstance(n, Tag)]


def _resolve_ticker(soup: BeautifulSoup, requested: str | None) -> str | None:
    """Pick the audit ticker.

    Default = the FIRST production card under ``#us-standouts`` with
    ``data-ticker`` (the card attribute at
    ``templates/_prophet_card.html.j2:608``).
    The script NEVER invents a ticker; absent a match it returns ``None``
    and the report records every check that depended on it as N/A.
    """
    if requested:
        return requested.strip().upper() or None
    container = _select_first(soup, "#us-standouts")
    if container is None:
        return None
    for card in container.select(".pvcard[data-ticker]"):
        sym = card.get("data-ticker", "").strip().upper()
        if sym:
            return sym
    return None


# =========================================================================== #
# Locale-aware visible text — J11 / J12 / J9.
# =========================================================================== #
def _strip_other_locale(node: Tag, locale: str) -> None:
    """Drop the spans in the OTHER locale so visible-text scans are clean.

    Templates wrap every bilingual string in
    ``<span class="l-en">…</span><span class="l-zh">…</span>``
    (``templates/_prophet_card.html.j2:75`` — the ``t(en, zh)`` macro).
    Removing the inactive span mirrors what the page actually renders.
    """
    other = "l-zh" if locale == "en" else "l-en"
    for span in node.find_all("span", class_=other):
        span.decompose()


def _visible_text(node: Tag, locale: str) -> str:
    """All visible text inside ``node`` in the selected locale.

    Drops ``<script>`` / ``<style>`` (always), drops attribute values
    (only TEXT nodes count), and drops the inactive locale's spans.
    """
    cleaned = BeautifulSoup(str(node), "lxml")
    for tag in cleaned(["script", "style"]):
        tag.decompose()
    target = cleaned.find() if False else (cleaned.contents[0]
                                          if cleaned.contents else cleaned)
    # Walk the cleaned tree, drop the OTHER locale's spans, then collect text.
    root = cleaned.find() or cleaned
    _strip_other_locale(root, locale)
    chunks: list[str] = []
    for elem in root.descendants:
        if isinstance(elem, NavigableString):
            parent = elem.parent
            if isinstance(parent, Tag) and parent.name in ("script", "style"):
                continue
            chunks.append(str(elem))
    return " ".join("".join(chunks).split())


def _hrefs(node: Tag) -> list[str]:
    return [a.get("href", "") for a in node.find_all("a")
            if isinstance(a, Tag) and a.get("href")]


def _data_mkts(node: Tag) -> list[str]:
    out: list[str] = []
    for el in node.find_all(True):
        v = el.get("data-mkt")
        if v is not None:
            out.append(v)
    return out


# =========================================================================== #
# Journey node set — the union J10 / J11 / J12 walk.
# =========================================================================== #
def _journey_nodes(
    soup: BeautifulSoup,
    ticker: str,
    plan_ids: Iterable[str],
) -> list[Tag]:
    """Every DOM node the audit considers part of the ONE journey."""
    nodes: list[Tag] = []
    for sel in ("#us-standouts", "#us-candidate-pool"):
        n = _select_first(soup, sel)
        if n is not None:
            nodes.append(n)
    # The per-ticker detail node(s) — there can be MORE than one (table +
    # dialog preview), so we walk every match.
    if ticker:
        nodes.extend(_select_all(
            soup, f'[data-setup-ticker="{ticker}"]'))
    # The linked plan nodes — J8's PLAN CARDS carry ``id="pv-<id>"``
    # (``templates/_prophet_card.html.j2:608``).
    for pid in plan_ids:
        n = _select_first(soup, f"#pv-{pid}")
        if n is not None:
            nodes.append(n)
    return nodes


# =========================================================================== #
# Individual checks — each returns a single check dict.
# =========================================================================== #
def _check_status(status: str, expected: Any, observed: Any,
                  where: str) -> dict[str, Any]:
    return {"id": "", "status": status, "expected": expected,
            "observed": observed, "where": where}


def _check_j1(soup: BeautifulSoup, ticker: str | None) -> dict[str, Any]:
    """J1 — the TODAY candidate is present on the US board."""
    where = ("#us-standouts .pvcard[data-ticker=T] "
             "(templates/_prophet_card.html.j2:608; nested market at :635; "
             "templates/_us_board_cards.html.j2:283-285; headings :78, :66)")
    if not ticker:
        return _check_status("N/A", "card present", "no ticker resolved",
                             where)
    card = _select_first(
        soup, f'#us-standouts .pvcard[data-ticker="{ticker}"]')
    nested_market: str | None = None
    if card is not None:
        market_node = card.select_one(".nb-px[data-mkt]")
        if market_node is not None:
            nested_market = str(market_node.get("data-mkt", "")).lower()
    if card is not None and nested_market not in (None, "us"):
        return _check_status(
            "FAIL",
            f"card present for {ticker} with nested market us when present",
            {"nested_data_mkt": nested_market},
            where,
        )
    if card is None:
        # Distinguish a missing container (N/A — the journey node was not
        # rendered into this snapshot, e.g. a dialog-only DOM dump) from a
        # container that exists but is missing the candidate card (FAIL —
        # the snapshot WAS rendered but the ticker is not on it).
        if _select_first(soup, "#us-standouts") is None:
            return _check_status(
                "N/A",
                f"card with data-ticker {ticker} in the US board",
                "#us-standouts container absent from snapshot",
                where)
        return _check_status("FAIL",
                             f"card with data-ticker {ticker} under #us-standouts",
                             "no matching production card",
                             where)
    lane = card.get("data-lane")
    stage = card.get("data-stage")
    return _check_status(
        "PASS",
        f"card present for {ticker} in the US board",
        {"data_lane": lane, "data_stage": stage,
         "nested_data_mkt": nested_market},
        where,
    )


def _pool_rows(soup: BeautifulSoup, view: str,
               ticker: str | None) -> list[Tag]:
    if not ticker:
        return []
    return _select_all(
        soup,
        f'#us-candidate-pool[data-view="{view}"] [data-ticker="{ticker}"]',
    )


def _check_j2(soup: BeautifulSoup, ticker: str | None,
              standouts: dict[str, Any]) -> dict[str, Any]:
    """J2 — screener TABLE row present; data-off-board mirrors in_buy_lane."""
    where = ("#us-candidate-pool[data-view=\"table\"] [data-ticker=T] "
             "(templates/_us_candidate_pool_rows.html.j2:27; "
             "templates/_us_candidate_pool.html.j2:17)")
    rows = _pool_rows(soup, "table", ticker)
    if not rows:
        return _check_status("N/A", "table row present",
                             "no row under #us-candidate-pool[data-view=table]",
                             where)
    row = rows[0]
    off_board = row.get("data-off-board", "")
    in_buy = ticker.upper() in {str(r.get("ticker", "")).upper()
                                for r in (standouts.get("buy") or [])
                                if isinstance(r, dict)}
    expected_off = "false" if in_buy else "true"
    href_ok = any(h.endswith(f"#{ticker}") for h in _hrefs(row))
    if off_board == expected_off and href_ok:
        return _check_status(
            "PASS",
            f"data-off-board={expected_off}; link stock.html#{ticker}",
            {"data_off_board": off_board, "href_to_stock": href_ok},
            where,
        )
    return _check_status(
        "FAIL",
        f"data-off-board={expected_off}; link stock.html#{ticker}",
        {"data_off_board": off_board, "href_to_stock": href_ok,
         "in_buy_lane": in_buy},
        where,
    )


def _check_j3(soup: BeautifulSoup, ticker: str | None,
              standouts: dict[str, Any]) -> dict[str, Any]:
    """J3 — screener GRID row present; same data-off-board contract."""
    where = ("#us-candidate-pool[data-view=\"grid\"] [data-ticker=T] "
             "(templates/_us_candidate_pool_rows.html.j2:27; "
             "templates/_us_candidate_pool.html.j2:13 CSS view switch)")
    # The view attribute is set CLIENT-SIDE by the pool's own JS
    # (templates/_us_candidate_pool.html.j2:67 — ``root.dataset.view=view``).
    # A STATIC snapshot may carry either value depending on capture timing;
    # accept BOTH ``table`` and ``grid`` views as evidence the row renders.
    rows = (_pool_rows(soup, "grid", ticker)
            + _pool_rows(soup, "table", ticker))
    if not rows:
        return _check_status("N/A", "grid row present",
                             "no row under #us-candidate-pool at any view",
                             where)
    row = rows[0]
    off_board = row.get("data-off-board", "")
    in_buy = ticker.upper() in {str(r.get("ticker", "")).upper()
                                for r in (standouts.get("buy") or [])
                                if isinstance(r, dict)}
    expected_off = "false" if in_buy else "true"
    href_ok = any(h.endswith(f"#{ticker}") for h in _hrefs(row))
    if off_board == expected_off and href_ok:
        return _check_status(
            "PASS",
            f"data-off-board={expected_off}; link stock.html#{ticker}",
            {"data_off_board": off_board, "href_to_stock": href_ok,
             "view_seen": row.find_parent(
                 attrs={"data-view": True}).get("data-view")
             if row.find_parent(attrs={"data-view": True}) else None},
            where,
        )
    return _check_status(
        "FAIL",
        f"data-off-board={expected_off}; link stock.html#{ticker}",
        {"data_off_board": off_board, "href_to_stock": href_ok,
         "in_buy_lane": in_buy},
        where,
    )


def _standouts_payload_row(standouts: dict[str, Any],
                           ticker: str) -> dict[str, Any] | None:
    """Find the row in any of the THREE standouts buckets the brief names.

    ``buy`` and ``watch`` carry FULL row dicts (with ``lane``, ``state``,
    ``entry_signal``, etc.). ``candidate_pool`` is itself a DICT
    (engine/us_candidate_lanes.py:1007) whose ``rows`` key holds the
    pool-row dicts (engine/us_candidate_lanes.py:599). The harness tries
    all three so the membership check (J4) survives any payload shape.
    """
    t = ticker.upper()
    for key in ("buy", "watch"):
        for row in (standouts.get(key) or []):
            if isinstance(row, dict) and str(row.get("ticker", "")).upper() == t:
                return row
    pool = standouts.get("candidate_pool") or {}
    for row in (pool.get("rows") or []):
        if isinstance(row, dict) and str(row.get("ticker", "")).upper() == t:
            return row
    return None


def _check_j4(standouts: dict[str, Any], ticker: str | None,
              j1_card_lane: str | None) -> dict[str, Any]:
    """J4 — T is in standouts.buy ∪ watch ∪ candidate_pool.rows."""
    where = ("us_standouts.buy / watch / candidate_pool.rows "
             "(engine/us_candidate_lanes.py:1007 candidate_pool shape; "
             "scripts/build_site.py:5284 / :5658 consumers)")
    if not ticker:
        return _check_status("N/A", "row in any bucket", "no ticker resolved",
                             where)
    found_in: list[str] = []
    row: dict[str, Any] | None = None
    for key in ("buy", "watch"):
        for r in (standouts.get(key) or []):
            if isinstance(r, dict) and str(r.get("ticker", "")).upper() == ticker.upper():
                found_in.append(key)
                row = r
                break
    pool = standouts.get("candidate_pool") or {}
    for r in (pool.get("rows") or []):
        if isinstance(r, dict) and str(r.get("ticker", "")).upper() == ticker.upper():
            found_in.append("candidate_pool")
            row = r
            break
    if not found_in:
        return _check_status(
            "FAIL",
            f"{ticker} in any of [buy, watch, candidate_pool.rows]",
            "no matching row",
            where,
        )
    # Lane reconciliation: board card data-lane (if present) must equal the
    # payload row's ``lane``. Cards on a PRIORITY board carry ``data-stage``
    # (the bucket key), not ``data-lane`` — see the citation above.
    payload_lane = row.get("lane") if isinstance(row, dict) else None
    card_attr = j1_card_lane
    if card_attr is not None and payload_lane is not None \
            and card_attr != payload_lane:
        return _check_status(
            "FAIL",
            f"board data-lane == payload lane ({payload_lane})",
            {"board_data_lane": card_attr, "payload_lane": payload_lane,
             "found_in": found_in},
            where,
        )
    return _check_status(
        "PASS",
        f"{ticker} present in {found_in}; lane reconciled",
        {"found_in": found_in,
         "board_data_lane": card_attr,
         "payload_lane": payload_lane},
        where,
    )


def _setup_detail_node(soup: BeautifulSoup,
                       ticker: str | None) -> Tag | None:
    """The detail body for ticker — J5 / J6 / J10 all walk through here.

    The table presenter emits ``[data-setup-ticker=T]`` (the ``<details>``
    wrapper, ``templates/_prophet_setup_detail.html.j2:91``); the body
    inside (``<div class="pv-setup-body" data-setup-kind="..."
    data-native-id="...">``) lives at :27. The harness reports the
    detail-INSIDE-the-wrapper — the wrapper itself has no
    ``data-native-id`` and no ``data-source-field`` nodes.
    """
    if not ticker:
        return None
    wrapper = _select_first(
        soup, f'[data-setup-ticker="{ticker}"]')
    if wrapper is None:
        return None
    body = wrapper.select_one('[data-native-id]')
    return body if isinstance(body, Tag) else wrapper


def _check_j5(soup: BeautifulSoup, standouts: dict[str, Any],
              ticker: str | None) -> dict[str, Any]:
    """J5 — detail binding: kind, native-id, asof, entry-status."""
    where = ("[data-setup-ticker=T] > [data-native-id=T] "
             "(templates/_prophet_setup_detail.html.j2:91 wrapper; "
             ":27 body; :34 entry-status)")
    detail = _setup_detail_node(soup, ticker)
    if detail is None:
        return _check_status("N/A", "detail body present",
                             "no [data-setup-ticker] wrapper for ticker",
                             where)
    native_id = detail.get("data-native-id", "")
    kind = detail.get("data-setup-kind", "")
    wrapper = detail.find_parent(attrs={"data-setup-ticker": True}) \
        or detail
    setup_asof = wrapper.get("data-setup-asof", "")
    entry_status_node = detail.select_one("[data-entry-status]")
    entry_status = (entry_status_node.get("data-entry-status", "")
                    if entry_status_node is not None else "")
    # Match setup-asof against standouts.as_of OR the payload row's signal_asof.
    standouts_asof = standouts.get("as_of")
    payload_row = _standouts_payload_row(standouts, ticker or "")
    payload_signal_asof = (payload_row or {}).get("signal_asof")
    payload_entry_status = None
    if payload_row is not None:
        entry_signal = payload_row.get("entry_signal")
        if isinstance(entry_signal, dict):
            payload_entry_status = entry_signal.get("status")
    asof_match = None
    if setup_asof and standouts_asof and setup_asof == standouts_asof:
        asof_match = "standouts.as_of"
    elif setup_asof and payload_signal_asof and setup_asof == payload_signal_asof:
        asof_match = "payload.signal_asof"
    if native_id != ticker:
        return _check_status(
            "FAIL",
            f"data-native-id == {ticker}",
            {"data_native_id": native_id, "data_setup_kind": kind,
             "data_setup_asof": setup_asof,
             "data_entry_status": entry_status,
             "asof_match": asof_match},
            where,
        )
    if kind not in ("board", "pool"):
        return _check_status(
            "FAIL",
            "data-setup-kind in {board, pool}",
            {"data_native_id": native_id, "data_setup_kind": kind,
             "data_setup_asof": setup_asof,
             "data_entry_status": entry_status,
             "asof_match": asof_match},
            where,
        )
    if asof_match is None:
        return _check_status(
            "FAIL",
            "data-setup-asof matches standouts.as_of OR payload.signal_asof",
            {"data_native_id": native_id, "data_setup_kind": kind,
             "data_setup_asof": setup_asof,
             "data_entry_status": entry_status,
             "payload_entry_status": payload_entry_status,
             "standouts_as_of": standouts_asof,
             "payload_signal_asof": payload_signal_asof},
            where,
        )
    if entry_status != payload_entry_status:
        return _check_status(
            "FAIL",
            "data-entry-status matches payload entry_signal.status",
            {"data_native_id": native_id, "data_setup_kind": kind,
             "data_setup_asof": setup_asof,
             "data_entry_status": entry_status,
             "payload_entry_status": payload_entry_status,
             "asof_match": asof_match},
            where,
        )
    return _check_status(
        "PASS",
        "native-id, kind, asof, entry-status bound",
        {"data_native_id": native_id, "data_setup_kind": kind,
         "data_setup_asof": setup_asof,
         "data_entry_status": entry_status,
         "payload_entry_status": payload_entry_status,
         "asof_match": asof_match},
        where,
    )


def _resolve_dotted(row: dict[str, Any], path: str) -> Any:
    """Resolve a dotted path on a dict; ``None`` on any miss.

    Mirrors the template's access pattern: ``entry_signal.buy_zone.low``
    walks three keys; ``signal.tier_observed_date`` walks two.
    """
    node: Any = row
    for piece in path.split("."):
        if isinstance(node, dict):
            node = node.get(piece)
        else:
            return None
        if node is None:
            return None
    return node


def _check_j6(soup: BeautifulSoup, standouts: dict[str, Any],
              ticker: str | None) -> dict[str, Any]:
    """J6 — every ``[data-source-field]`` inside the detail is preserved."""
    where = ("[data-source-field=...] <dd> inside the detail body "
             "(templates/_prophet_setup_detail.html.j2:12; "
             ":44-46 entry_signal paths; "
             ":58-60 signal paths; "
             ":65-67 / :74-77 audit paths)")
    detail = _setup_detail_node(soup, ticker)
    if detail is None:
        return _check_status("N/A", "source fields present",
                             "no detail body to inspect", where)
    payload_row = _standouts_payload_row(standouts, ticker or "")
    if payload_row is None:
        return _check_status("N/A", "source fields preserved",
                             "no payload row for ticker", where)
    fields = detail.select("[data-source-field]")
    if not fields:
        return _check_status("FAIL", "at least one [data-source-field]",
                             "detail body has zero source fields",
                             where)
    misses: list[dict[str, Any]] = []
    str_misses: list[dict[str, Any]] = []
    raw_pairs: list[dict[str, Any]] = []
    money_paths = ("price", "entry_signal.buy_zone.low",
                   "entry_signal.buy_zone.high", "entry_signal.stop",
                   "hold.invalidation", "entry_signal.chase_above")
    bool_paths = ("signal.above200", "signal.weekly_bull",
                  "signal.provisional")
    for fld in fields:
        path = fld.get("data-source-field", "")
        dd = fld.select_one("dd")
        dd_text = dd.get_text(" ", strip=True) if dd is not None else ""
        # Resolve the payload value for the same path.
        raw = _resolve_dotted(payload_row, path)
        raw_pairs.append({"path": path, "dd_text": dd_text,
                          "payload": raw})
        # Template "Not supplied 来源未提供" — the source field is unbound
        # by the live template (no data ever flows here). This is a
        # coverage gap, not a data-integrity defect — record the pair but
        # do not FAIL on it; the path is intentionally open. Combined
        # dd_text ``"Not supplied 来源未提供"`` is treated as the sentinel.
        sentinel_prefixes = ("not supplied", "来源未提供")
        dd_norm = dd_text.strip().lower()
        if any(dd_norm.startswith(p) for p in sentinel_prefixes):
            raw_pairs.append({"path": path, "dd_text": dd_text,
                              "payload": raw, "template_unbound": True})
            continue
        if raw is None:
            misses.append({"path": path, "reason": "payload_path_missing",
                           "dd_text": dd_text})
            continue
        # Empty / None / nan / undefined / null dd → FAIL on preservation.
        if dd_norm in EMPTY_SENTINELS:
            misses.append({"path": path, "reason": "dd_empty_or_sentinel",
                           "dd_text": dd_text, "payload": raw})
            continue
        # Booleans — the template renders "Yes" / "No" (EN) / "是" / "否"
        # (ZH) at :5-6. The two locale spans are siblings inside the dd
        # so ``dd.get_text(' ')`` produces the combined string (e.g.
        # ``"Yes 是"``); accept ANY of the four tokens as a substring.
        if path in bool_paths:
            if isinstance(raw, bool):
                yes_hits = sum(
                    1 for tok in ("Yes", "No", "是", "否")
                    if tok in dd_text)
                truthy_ok = (
                    ("Yes" in dd_text or "是" in dd_text) if raw
                    else ("No" in dd_text or "否" in dd_text))
                if yes_hits == 0 or not truthy_ok:
                    misses.append({
                        "path": path, "reason": "bool_render_mismatch",
                        "dd_text": dd_text, "payload": raw})
            continue
        # Numbers — the template formats money as ``$%.2f`` (:7). Mirror it.
        if path in money_paths:
            if isinstance(raw, (int, float)) and not isinstance(raw, bool):
                formatted = f"${raw:.2f}"
                if formatted != dd_text.strip():
                    misses.append(
                        {"path": path, "reason": "money_mismatch",
                         "dd_text": dd_text, "expected": formatted,
                         "payload": raw})
            continue
        # Strings — the dd text must CONTAIN the value verbatim (the
        # template wraps it in ``pvs-original-source`` when a verbatim
        # echo is wanted, but the dd itself prints the value at :8).
        if isinstance(raw, str):
            if raw and raw not in dd_text:
                str_misses.append({"path": path, "reason": "string_missing",
                                   "dd_text": dd_text, "payload": raw})
            continue
        # Other types (lists / dicts) — emit N/A but record the pair.
    if misses or str_misses:
        return _check_status(
            "FAIL",
            "every dd text reflects its payload value",
            {"misses": misses, "str_misses": str_misses,
             "raw_pairs_sample": raw_pairs[:5],
             "total_fields": len(fields)},
            where,
        )
    return _check_status(
        "PASS",
        "every [data-source-field] dd reflects its payload value",
        {"total_fields": len(fields),
         "raw_pairs_sample": raw_pairs[:5]},
        where,
    )


def _check_j7(soup: BeautifulSoup, standouts: dict[str, Any]) -> dict[str, Any]:
    """J7 — pool clocks: data-as-of, data-total, data-source-digest."""
    where = ("#us-candidate-pool[data-as-of / data-total / data-source-digest] "
             "(templates/_us_candidate_pool.html.j2:17; "
             "engine/us_candidate_lanes.py:1002-1006 / :1008)")
    pool = _select_first(soup, "#us-candidate-pool")
    if pool is None:
        return _check_status("N/A", "pool container present",
                             "no #us-candidate-pool", where)
    asof = pool.get("data-as-of", "")
    total = pool.get("data-total", "")
    digest = pool.get("data-source-digest", "")
    standouts_asof = standouts.get("as_of")
    pool_dict = standouts.get("candidate_pool") or {}
    payload_total = (pool_dict.get("counts") or {}).get("eligible")
    payload_digest = pool_dict.get("source_digest")
    observed = {"data_as_of": asof, "data_total": total,
                "data_source_digest": bool(digest)}
    fails: list[str] = []
    if standouts_asof and asof != standouts_asof:
        fails.append(f"data-as-of={standouts_asof!r} != pool {asof!r}")
    if isinstance(payload_total, int) and str(payload_total) != total:
        fails.append(
            f"data-total={payload_total} != pool {total!r}")
    # ``data-source-digest`` mirrors the engine's SHA-256; we do NOT
    # re-compute the hash here (that requires rebuilding the engine's
    # exact row serialization — GAPS in the spec). Instead we report
    # whether the page's digest equals the payload's and note N/A when
    # the digest field is empty (the engine may legitimately omit it).
    if digest and payload_digest and digest != payload_digest:
        fails.append("data-source-digest mismatch (page != payload)")
    if fails:
        return _check_status(
            "FAIL",
            "pool clocks reconcile",
            {**observed, "fails": fails,
             "payload_total": payload_total,
             "payload_digest_match": (
                 bool(payload_digest) and digest == payload_digest)},
            where,
        )
    notes: list[str] = []
    if not digest:
        notes.append("page data-source-digest empty; engine digest not mirrored")
    return _check_status(
        "PASS" if not notes else "N/A",
        "pool clocks reconcile",
        {**observed, "payload_total": payload_total,
         "payload_digest_match": (
             bool(payload_digest) and digest == payload_digest),
         "notes": notes},
        where,
    )


def _plan_lifecycle_states(plans: list[dict[str, Any]]) -> set[str]:
    """The LIVE set of lifecycle_state values (J8).

    Per the builder at scripts/build_prophet.py:1331 the canonical set is
    ``("watch", "ready", "entered", "delivering", "overtime",
    "invalidated", "resolved")`` — the harness reads whatever values the
    supplied plans ACTUALLY carry so a degraded payload doesn't make the
    check definition drift.
    """
    return {str(p.get("lifecycle_state")) for p in plans
            if p.get("lifecycle_state")}


def _check_j8(soup: BeautifulSoup, index: dict[str, Any],
              ticker: str | None) -> tuple[dict[str, Any], list[str]]:
    """J8 — plan relationship: native plan link OR honest no-plan path.

    Returns ``(check, linked_plan_ids)``; the linked ids are passed into
    the J10 / J11 / J12 walks so the linked plan node is part of the
    journey.

    A "fabricated plan" — any ``#pv-<id>`` link OR ``id="pv-<id>"`` anchor
    that is NOT in ``index.plans[*].id`` — is a FAIL regardless of
    whether the audited ticker itself has a live plan.
    """
    where = ("plans = [p for p in index.plans if p.asset == T]; "
             "plan card id=\"pv-<id>\" "
             "(templates/_prophet_card.html.j2:608; "
             "scripts/build_prophet.py:1383 lifecycle_state(); "
             ":1331 LIVE cells)")
    if not ticker:
        return (_check_status("N/A", "plan linkage", "no ticker resolved",
                              where), [])
    plans = [p for p in (index.get("plans") or [])
             if isinstance(p, dict)
             and str(p.get("asset", "")).upper() == ticker.upper()]
    live_states = _plan_lifecycle_states(plans)
    # Inventory EVERY ``#pv-<id>`` the page carries (anchor target via
    # ``id`` attribute, or link via ``href="#pv-..."``).
    page_plan_ids: set[str] = set()
    for el in soup.select("[id^='pv-']"):
        pid = (el.get("id") or "")[len("pv-"):]
        if pid:
            page_plan_ids.add(pid)
    for a in soup.select("a[href^='#pv-']"):
        pid = (a.get("href") or "")[len("#pv-"):]
        if pid:
            page_plan_ids.add(pid)
    # Index inventory — every plan id the index declares (any ticker).
    index_plan_ids: set[str] = {
        str(p.get("id")) for p in (index.get("plans") or [])
        if isinstance(p, dict) and p.get("id")
    }
    # A fabricated plan id: page carries it but the index doesn't.
    fabric_ids = sorted(page_plan_ids - index_plan_ids)
    # Tickerspecific plan ids (only this ticker's plans).
    plan_ids = [str(p.get("id")) for p in plans if p.get("id")]
    # ≥1 live plan for T: each must have a #pv-<id> anchor in the page.
    if plans:
        detail = _setup_detail_node(soup, ticker)
        detail_links: list[str] = []
        if detail is not None:
            wrapper = detail.find_parent(
                attrs={"data-setup-ticker": True}) or detail
            for a in wrapper.find_all("a"):
                href = a.get("href", "")
                if href.startswith("#pv-"):
                    detail_links.append(href)
        page_ids = [pid for pid in plan_ids
                    if _select_first(soup, f"#pv-{pid}") is not None]
        missing = [pid for pid in plan_ids
                   if _select_first(soup, f"#pv-{pid}") is None]
        if missing or fabric_ids:
            return (_check_status(
                "FAIL",
                "every plan id has a #pv-<id> anchor AND no fabrication",
                {"expected_ids": plan_ids,
                 "page_ids_present": page_ids,
                 "missing_in_page": missing,
                 "detail_links": detail_links,
                 "fabricated_in_page": fabric_ids},
                where,
            ), plan_ids)
        return (_check_status(
            "PASS",
            "every plan id has a #pv-<id> anchor and no fabrication",
            {"expected_ids": plan_ids,
             "page_ids_present": page_ids,
             "detail_links": detail_links,
             "fabricated_in_page": fabric_ids},
            where,
        ), plan_ids)
    # No live plan for T: any fabricated #pv-* link on the page is FAIL.
    if fabric_ids:
        return (_check_status(
            "FAIL",
            "no #pv-* link for a ticker with no live plan",
            {"fabricated_links": fabric_ids},
            where,
        ), [])
    return (_check_status(
        "PASS",
        "no #pv-* link for a ticker with no live plan",
        {"linked_plan_ids": [],
         "live_lifecycle_states_seen": sorted(live_states)},
        where,
    ), [])


def _check_j9(soup: BeautifulSoup, index: dict[str, Any],
               standouts: dict[str, Any] | None = None) -> dict[str, Any]:
    """J9 — index clocks reconcile with standouts; page plan clock rendered.

    Three falsifiable rules. Each can PASS independently — the overall
    status is PASS only when ALL three hold simultaneously, FAIL when
    any reconciliation rule breaks OR the panel stamp is empty on a
    snapshot with populated index clocks, and N/A when ``#plv-asof``
    is absent (e.g., dialog-only fixture — the spec's "N/A with
    observed text" applies to a MISSING node, not to an EMPTY stamp).

    Rules
    -----
    R1. ``index.source_board_asof == standouts.as_of`` — same vintage.
    R2. ``index.asof >= index.source_board_asof`` — publication stamp
        cannot predate the source board (R2 fails when the builder
        reran the index without refreshing the source snapshot).
    R3. ``#plv-asof`` is present AND its visible text is non-empty —
        the page JS ``_plvAsOf`` filled the panel stamp.

    Keys
    ----
    Builder emits the publication clock at ``index["asof"]``
    (scripts/build_prophet.py:2607) and the source board vintage at
    ``index["source_board_asof"]`` (:2609). Legacy / synthetic payloads
    carry ``as_of`` instead — the harness accepts both so a synthetic
    test fixture does not have to mirror the builder's key spelling.
    """
    where = (
        "R1 index.source_board_asof == standouts.as_of; "
        "R2 index.asof >= index.source_board_asof "
        "(scripts/build_prophet.py:2607 'asof' key, "
        ":2609 'source_board_asof' key — also accepts legacy 'as_of'); "
        "R3 #plv-asof visible text filled by _plvAsOf "
        "(templates/dashboard.html.j2:16378 static markup; "
        ":18992 _plvAsOf formatter; :19422 stack call). "
        "Mirror contract: TIME-OF-DAY stamp, not ISO date."
    )
    # Builder key is "asof" (scripts/build_prophet.py:2607). Accept
    # "as_of" too for synthetic / legacy fixtures (the test suite
    # uses "as_of"; the live builder uses "asof").
    idx_asof = index.get("asof") or index.get("as_of")
    idx_source = index.get("source_board_asof")
    su_asof = (standouts or {}).get("as_of") if standouts else None

    plv = _select_first(soup, "#plv-asof")
    observed_plv = plv.get_text(" ", strip=True) if plv is not None else ""

    fails: list[str] = []

    # R1 — same vintage across the two payloads.
    if idx_source and su_asof and idx_source != su_asof:
        fails.append(
            f"R1: index.source_board_asof={idx_source!r} "
            f"!= standouts.as_of={su_asof!r}"
        )
    # R2 — publication stamp >= source board.
    if idx_source and idx_asof and idx_source > idx_asof:
        fails.append(
            f"R2: index.source_board_asof={idx_source!r} "
            f"> index.asof={idx_asof!r} (publication predates source)"
        )
    # R3 — visible plan clock stamp.
    if plv is not None and not observed_plv and (idx_source or idx_asof):
        fails.append(
            "R3: #plv-asof visible text empty — JS did not fill "
            "the panel stamp before the snapshot"
        )

    observed = {
        "index_as_of": idx_asof,
        "index_source_board_asof": idx_source,
        "standouts_as_of": su_asof,
        "plv_asof_observed": observed_plv,
        "plv_asof_present": plv is not None,
    }

    if fails:
        return _check_status(
            "FAIL",
            "R1+R2+R3: index clocks reconcile AND plan clock stamp rendered",
            {**observed, "fails": fails},
            where,
        )

    # N/A: node absent — the spec's "N/A with observed text" applies.
    if plv is None:
        return _check_status(
            "N/A",
            "R1+R2+R3: index clocks reconcile AND plan clock stamp rendered",
            {**observed,
             "reason": "#plv-asof node absent (dialog-only snapshot)"},
            where,
        )

    # All three rules hold — clocks reconcile AND stamp rendered.
    return _check_status(
        "PASS",
        "R1+R2+R3: index clocks reconcile AND plan clock stamp rendered",
        observed,
        where,
    )


def _check_j10(soup: BeautifulSoup, ticker: str | None,
               plan_ids: list[str]) -> dict[str, Any]:
    """J10 — no cross-market interception inside the journey nodes."""
    where = ("journey nodes: #us-standouts, #us-candidate-pool, "
             "[data-setup-ticker=T], #pv-<id> "
             "(templates/_prophet_card.html.j2:608 for #pv-<id>)")
    if not ticker:
        return _check_status("N/A", "no cross-market href; data-mkt=US",
                             "no ticker resolved", where)
    nodes = _journey_nodes(soup, ticker, plan_ids)
    if not nodes:
        return _check_status("N/A", "no cross-market interception",
                             "no journey nodes", where)
    bad_hrefs: list[dict[str, str]] = []
    bad_mkts: list[dict[str, str]] = []
    for n in nodes:
        for href in _hrefs(n):
            if _CROSSMARKET_HREF_RE.match(href):
                bad_hrefs.append({"node": n.name or "?", "href": href})
        for mkt in _data_mkts(n):
            if mkt != "US":
                bad_mkts.append({"node": n.name or "?", "data_mkt": mkt})
    if bad_hrefs or bad_mkts:
        return _check_status(
            "FAIL",
            "every href is in-domain AND every data-mkt == US",
            {"bad_hrefs": bad_hrefs, "bad_mkts": bad_mkts},
            where,
        )
    return _check_status(
        "PASS",
        "no cross-market hrefs; every data-mkt == US",
        {"nodes_walked": len(nodes)},
        where,
    )


def _enum_values(standouts: dict[str, Any], index: dict[str, Any]) -> set[str]:
    """The set of enum-string values that J11 bans from visible text.

    Reads the values off the supplied payloads (NOT off a hard-coded enum
    list) so a degraded payload never widens or narrows the banned set
    incorrectly. Only ``_``-containing raw tokens count — plain words
    are language copy and never flagged (J11 spec).
    """
    banned: set[str] = set()
    for row in (standouts.get("buy") or []):
        if not isinstance(row, dict):
            continue
        for k in STANDOUTS_ENUM_FIELDS:
            v = row.get(k)
            if isinstance(v, str) and "_" in v:
                banned.add(v)
    pool = standouts.get("candidate_pool") or {}
    for row in (pool.get("rows") or []):
        if not isinstance(row, dict):
            continue
        for k in STANDOUTS_ENUM_FIELDS:
            v = row.get(k)
            if isinstance(v, str) and "_" in v:
                banned.add(v)
    for plan in (index.get("plans") or []):
        if not isinstance(plan, dict):
            continue
        for k in PLAN_ENUM_FIELDS:
            v = plan.get(k)
            if isinstance(v, str) and "_" in v:
                banned.add(v)
    # Also accept entries nested under ``plan.state`` (the nested shape
    # scripts/build_prophet.py:2425-2433 documents). Carry those over too.
    for plan in (index.get("plans") or []):
        state = plan.get("state")
        if isinstance(state, dict):
            for k in ("phase", "lifecycle_state", "management_status"):
                v = state.get(k)
                if isinstance(v, str) and "_" in v:
                    banned.add(v)
    return {b for b in banned if _SNAKE_RE.match(b)}


def _scan_tokens(text: str, banned: set[str]) -> list[dict[str, str]]:
    """Find banned enum tokens inside ``text`` and return snippets.

    A token must match a banned value WHOLE-WORD (so ``buy_now_v2`` is NOT
    a hit for ``buy_now``) and the snippet is ≤80 chars centered on the
    match (J11 spec).
    """
    hits: list[dict[str, str]] = []
    for tok in banned:
        for m in re.finditer(r"\b" + re.escape(tok) + r"\b", text):
            start = max(0, m.start() - 30)
            end = min(len(text), m.end() + 30)
            snippet = text[start:end].replace("\n", " ").strip()
            hits.append({"token": tok, "snippet": snippet[:80]})
    return hits


def _check_j11(soup: BeautifulSoup, locale: str,
               standouts: dict[str, Any], index: dict[str, Any],
               ticker: str | None,
               plan_ids: list[str]) -> dict[str, Any]:
    """J11 — no raw internal enum tokens in the visible journey text."""
    where = ("journey-node visible text in locale; "
             "banned enums read off the supplied payloads "
             "(PLAN_ENUM_FIELDS / STANDOUTS_ENUM_FIELDS in this script; "
             "templates/_prophet_card.html.j2:75 bilingual span wrapper)")
    if not ticker:
        return _check_status("N/A", "no enum leakage in visible text",
                             "no ticker resolved", where)
    nodes = _journey_nodes(soup, ticker, plan_ids)
    if not nodes:
        return _check_status("N/A", "no enum leakage in visible text",
                             "no journey nodes", where)
    banned = _enum_values(standouts, index)
    if not banned:
        return _check_status(
            "N/A",
            "no enum leakage in visible text",
            "payloads carry no _-containing enum values to ban",
            where,
        )
    hits: list[dict[str, Any]] = []
    for n in nodes:
        text = _visible_text(n, locale)
        for hit in _scan_tokens(text, banned):
            hit["node"] = n.name or "?"
            hits.append(hit)
    if hits:
        return _check_status(
            "FAIL",
            "no raw enum tokens in journey visible text",
            {"hits": hits[:20],
             "banned_tokens": sorted(banned),
             "nodes_walked": len(nodes),
             "locale": locale},
            where,
        )
    return _check_status(
        "PASS",
        "no raw enum tokens in journey visible text",
        {"banned_tokens": sorted(banned),
         "nodes_walked": len(nodes),
         "locale": locale},
        where,
    )


def _check_j12(soup: BeautifulSoup, index: dict[str, Any],
               standouts: dict[str, Any],
               ticker: str | None,
               plan_ids: list[str]) -> dict[str, Any]:
    """J12 — fail-soft: tracking-unavailable alert must not coexist with populated sources."""
    where = (".mx-error[role=alert] "
             "(templates/_prophet_card.html.j2:120; "
             ":123-124 bilingual 'Tracking unavailable' copy)")
    if not ticker:
        return _check_status("N/A", "alert absent or sources empty",
                             "no ticker resolved", where)
    nodes = _journey_nodes(soup, ticker, plan_ids)
    alerts: list[str] = []
    for n in nodes:
        for el in n.select(".mx-error[role=alert]"):
            alerts.append(el.get_text(" ", strip=True))
    plans_nonempty = bool(index.get("plans"))
    buy_nonempty = bool(standouts.get("buy"))
    if alerts and plans_nonempty and buy_nonempty:
        return _check_status(
            "FAIL",
            "tracking-unavailable alert absent when sources populated",
            {"alerts": alerts,
             "index_plans_nonempty": plans_nonempty,
             "standouts_buy_nonempty": buy_nonempty},
            where,
        )
    return _check_status(
        "PASS",
        "alert absent or sources genuinely empty",
        {"alerts": alerts,
         "index_plans_nonempty": plans_nonempty,
         "standouts_buy_nonempty": buy_nonempty},
        where,
    )


# =========================================================================== #
# Orchestration
# =========================================================================== #
def _verdict(checks: list[dict[str, Any]]) -> str:
    statuses = {c["status"] for c in checks}
    if "FAIL" in statuses:
        return "FAIL"
    if "N/A" in statuses:
        return "PARTIAL"
    return "PASS"


def _exit_code(verdict: str) -> int:
    return {"PASS": 0, "PARTIAL": 2, "FAIL": 1}[verdict]


def run(argv: list[str] | None = None) -> int:
    args = _parse_argv(argv)
    page_path = Path(args.page)
    standouts_path = Path(args.standouts)
    index_path = Path(args.index)
    out_path = Path(args.out)

    if not page_path.exists():
        print(f"--page not found: {page_path}", file=sys.stderr)
        return 1
    if not standouts_path.exists():
        print(f"--standouts not found: {standouts_path}", file=sys.stderr)
        return 1
    if not index_path.exists():
        print(f"--index not found: {index_path}", file=sys.stderr)
        return 1

    page_sha, page_bytes = _sha256(page_path)
    standouts_sha, standouts_bytes = _sha256(standouts_path)
    index_sha, index_bytes = _sha256(index_path)

    soup = _parse_page(page_path.read_text(encoding="utf-8"))
    ticker = _resolve_ticker(soup, args.ticker)
    standouts = _load_json(standouts_path)
    index = _load_json(index_path)

    j1 = _check_j1(soup, ticker)
    j2 = _check_j2(soup, ticker, standouts)
    j3 = _check_j3(soup, ticker, standouts)
    # J4 takes the card's data-lane (or data-stage) from J1's PASS dict —
    # we tolerate the N/A case (observed is a string there) by passing None.
    j1_observed = j1.get("observed") if isinstance(j1.get("observed"),
                                                    dict) else None
    j4 = _check_j4(standouts, ticker, j1_observed.get("data_lane")
                    if j1_observed else None)
    j5 = _check_j5(soup, standouts, ticker)
    j6 = _check_j6(soup, standouts, ticker)
    j7 = _check_j7(soup, standouts)
    j8, plan_ids = _check_j8(soup, index, ticker)
    j9 = _check_j9(soup, index, standouts)
    j10 = _check_j10(soup, ticker, plan_ids)
    j11 = _check_j11(soup, args.locale, standouts, index, ticker, plan_ids)
    j12 = _check_j12(soup, index, standouts, ticker, plan_ids)

    checks = [j1, j2, j3, j4, j5, j6, j7, j8, j9, j10, j11, j12]
    ids = ["J1", "J2", "J3", "J4", "J5", "J6", "J7", "J8", "J9",
           "J10", "J11", "J12"]
    for chk, cid in zip(checks, ids):
        chk["id"] = cid
    verdict = _verdict(checks)

    report = {
        "schema": SCHEMA,
        "generated_by": GENERATED_BY,
        "inputs": {
            "page": {"path": str(page_path), "sha256": page_sha,
                     "bytes": page_bytes},
            "standouts": {"path": str(standouts_path),
                          "sha256": standouts_sha,
                          "bytes": standouts_bytes},
            "index": {"path": str(index_path),
                      "sha256": index_sha, "bytes": index_bytes},
        },
        "ticker": ticker,
        "locale": args.locale,
        "linked_plan_ids": plan_ids,
        "checks": checks,
        "verdict": verdict,
    }
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2,
                   sort_keys=False, allow_nan=False),
        encoding="utf-8",
    )
    return _exit_code(verdict)


if __name__ == "__main__":
    raise SystemExit(run())
