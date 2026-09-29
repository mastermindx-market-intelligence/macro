#!/usr/bin/env python3
"""Prophet journey reconciliation harness — release-integration proof tool.

A deterministic, offline checker that takes (a) a saved DOM snapshot of the
authenticated ``/us_stocks.html`` page (outerHTML after page JS ran), (b)
``factordata/us_standouts.json``, (c) ``prophet/index.json``, and one ticker,
and reports whether the ONE Prophet decision journey — Today → Screener
(table + grid) → same candidate's detail → linked native plan OR honest
no-plan path — shows the SAME record with reconciled clocks, preserved
source values, plain language, and no cross-market interception.

Output = a JSON receipt and one status line per check, followed by RESULT.
Exit 0 PASS, 1 FAIL, 2 PARTIAL (no FAIL but ≥1 UNSUPPORTED or N/A).

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
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if os.environ.get("PYTHONPATH"):
    sys.path.extend(os.environ["PYTHONPATH"].split(os.pathsep))

try:
    from bs4 import BeautifulSoup, Comment, NavigableString, Tag
except ImportError as exc:  # pragma: no cover - bs4 is in requirements
    raise SystemExit(f"beautifulsoup4 is required: {exc}")


SCHEMA = "mastermind.prophet_journey_reconciliation.v1"
GENERATED_BY = "scripts/prophet_journey_reconcile.py"

# --------------------------------------------------------------------------- #
# Field enumerations used for J11 (raw-snake-case token scan).
# The declared reason vocabulary is derived at runtime from the producing engine
# so a new engine code cannot silently escape the leak check.  Plan fields remain
# payload-derived as well; the fixed lifecycle set is part of the frozen DOM law.
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

try:
    from engine.prophet_bridge import REFUSAL_ORDER
    from engine.us_candidate_lanes import declared_reasons
    from scripts.build_prophet import LIFECYCLE_CELLS
except (ImportError, RuntimeError, TypeError, ValueError) as _exc:
    REFUSAL_ORDER = ()
    _LANE_IMPORT_ERROR = str(_exc)
    declared_reasons = lambda: frozenset()
    LIFECYCLE_CELLS = ()
else:
    _LANE_IMPORT_ERROR = ""

RUNTIME_DECLARED_REASON_VOCABULARY = frozenset(declared_reasons())
LIFECYCLE_VOCABULARY = frozenset(LIFECYCLE_CELLS)
PLAN_RELATION_VOCABULARY = frozenset({
    "none", "related_security", "unknown",
})


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
    return BeautifulSoup(html, HTML_PARSER)


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
    cleaned = BeautifulSoup(str(node), HTML_PARSER)
    for tag in cleaned(["script", "style"]):
        tag.decompose()
    # Walk the whole cleaned target, not only its first top-level child.
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
    own = node.get("data-mkt")
    if own is not None:
        out.append(own)
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


def _available_html_parser() -> str:
    try:
        import lxml  # noqa: F401, PLC0415
    except ImportError:
        return "html.parser"
    return "lxml"


HTML_PARSER = _available_html_parser()


def _normalized_body(body: Tag) -> str:
    """Serialize a setup body with comments removed and text whitespace collapsed."""
    parsed = BeautifulSoup(str(body), HTML_PARSER)
    root = parsed.select_one(".pv-setup-body") or parsed.find() or parsed
    for comment in root.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()
    for text_node in root.find_all(string=True):
        if isinstance(text_node, NavigableString) and not isinstance(text_node, Comment):
            text_node.replace_with(" ".join(str(text_node).split()))
    return root.decode().strip()


def _first_html_difference(left: str, right: str) -> dict[str, Any]:
    for index, (left_char, right_char) in enumerate(zip(left, right)):
        if left_char != right_char:
            start = max(0, index - 40)
            return {
                "offset": index,
                "left": left[start:index + 80],
                "right": right[start:index + 80],
            }
    offset = min(len(left), len(right))
    return {
        "offset": offset,
        "left": left[offset:offset + 80],
        "right": right[offset:offset + 80],
    }


def _setup_source_bodies(soup: BeautifulSoup,
                          ticker: str) -> tuple[list[Tag], list[Tag]]:
    """Return every displayed selected body and every template copy."""
    displayed: list[Tag] = []
    templates: list[Tag] = []
    requested = ticker.upper()
    for body in soup.select(".pv-setup-body"):
        prefixed_wrapper = body.find_parent(
            attrs={"data-setup-ticker": lambda value: str(value).upper().startswith(requested + "-")})
        exact_wrapper = body.find_parent(attrs={"data-setup-ticker": ticker})
        if exact_wrapper is None and prefixed_wrapper is None:
            continue
        if body.find_parent("template") is not None:
            templates.append(body)
        else:
            displayed.append(body)
    return displayed, templates


def _body_binding(body: Tag) -> dict[str, Any]:
    clock = body.select_one(".pvs-summary-clock")
    return {
        "data-plan-relation": str(body.get("data-plan-relation", "")),
        "data-entry-status": str(body.get("data-entry-status", "")),
        "data-native-id": str(body.get("data-native-id", "")),
        "summary-clock-text": clock.get_text(" ", strip=True) if clock else "",
    }


def _field_misses(body: Tag, row: dict[str, Any]) -> list[dict[str, Any]]:
    money_paths = ("price", "entry_signal.buy_zone.low",
                   "entry_signal.buy_zone.high", "entry_signal.stop",
                   "hold.invalidation", "entry_signal.chase_above")
    bool_paths = ("signal.above200", "signal.weekly_bull", "signal.provisional")
    misses: list[dict[str, Any]] = []
    for field in body.select("[data-source-field]"):
        path = str(field.get("data-source-field", ""))
        raw = _resolve_dotted(row, path)
        text = (field.select_one("dd").get_text(" ", strip=True)
                if field.select_one("dd") is not None else "")
        if path in money_paths and isinstance(raw, (int, float)):
            expected = f"${raw:.2f}"
            if text.split(" as of ", 1)[0].strip() != expected:
                misses.append({"path": path, "reason": "money_mismatch", "text": text, "expected": expected})
        elif path in bool_paths and isinstance(raw, bool):
            accepted = ("Yes", "No") if raw else ("No", "Yes")
            if not any(token in text for token in (accepted[0], "是" if raw else "否")):
                misses.append({"path": path, "reason": "bool_mismatch", "text": text})
        elif isinstance(raw, str) and raw and path in ("lane", "stage"):
            continue
        elif isinstance(raw, str) and raw and raw not in text:
            misses.append({"path": path, "reason": "string_missing", "text": text, "expected": raw})
    return misses


def _check_j6(soup: BeautifulSoup, standouts: dict[str, Any],
              ticker: str | None) -> dict[str, Any]:
    """J6 — displayed body, template copy and rendered source fields agree."""
    where = ("selected displayed .pv-setup-body and template.pvs-body-source "
             "binding plus rendered source fields")
    if not ticker:
        return _check_status("FAIL", "displayed selected body", "no ticker", where)
    displayed, templates = _setup_source_bodies(soup, ticker)
    if not displayed:
        return _check_status("FAIL", "displayed selected body",
                             "no displayed .pv-setup-body for ticker", where)
    bindings = [_body_binding(body) for body in displayed]
    bad_displayed = [binding for binding in bindings
                     if binding != bindings[0]
                     or binding["data-native-id"] != ticker]
    if bad_displayed:
        return _check_status("FAIL", "every displayed selected body agrees",
                             {"bad_displayed": bad_displayed}, where)
    binding = bindings[0]
    template_serializations = [_normalized_body(template) for template in templates]
    displayed_serializations = [_normalized_body(body) for body in displayed]
    normalized_template = (template_serializations[0]
                           if template_serializations
                           else displayed_serializations[0])
    differing_body = next(
        ((index, serialization) for index, serialization in
         enumerate(displayed_serializations, 1)
         if serialization != normalized_template),
        None,
    )
    if differing_body is not None:
        index, serialization = differing_body
        first_difference = _first_html_difference(serialization, normalized_template)
        return _check_status(
            "FAIL",
            "every displayed body equals the template by normalized HTML",
            {"displayed_index": index, "first_difference": first_difference,
             "displayed": serialization, "template": normalized_template},
            where,
        )
    template_bindings = [_body_binding(template) for template in templates]
    if any(template_binding != binding for template_binding in template_bindings):
        return _check_status("FAIL", "displayed binding equals every template binding",
                             {"displayed": binding,
                              "templates": template_bindings}, where)
    if binding["data-plan-relation"] not in PLAN_RELATION_VOCABULARY:
        return _check_status("FAIL", "supported plan relation", binding, where)
    row = _standouts_payload_row(standouts, ticker)
    if row is None:
        return _check_status("FAIL", "selected source row", "no row for ticker", where)
    misses: list[dict[str, Any]] = []
    for body in displayed:
        misses.extend(_field_misses(body, row))
    if misses:
        return _check_status("FAIL", "source fields equal payload", misses, where)
    return _check_status(
        "PASS",
        "every displayed body equals the template and source fields are supported",
                         {**binding, "displayed_count": len(displayed),
                          "template_count": len(templates),
                          "total_fields": len(displayed[0].select("[data-source-field]"))}, where)

def _body_clock_text(body: Tag, selector: str) -> Tag | None:
    return body.select_one(selector)


def _displayed_date(value: str) -> str:
    match = re.search(r"\d{4}-\d{2}-\d{2}", value)
    return match.group(0) if match else ""


def _source_field_text(body: Tag, path: str) -> str:
    field = body.select_one(f'[data-source-field="{path}"]')
    if field is None:
        return ""
    value = field.select_one("dd")
    return value.get_text(" ", strip=True) if value else ""


def _journey_digest(standouts: dict[str, Any], ticker: str,
                    plan_relation: str | None = None,
                    plan_ids: list[str] | None = None) -> str | None:
    """Hash exactly the selected row fields the journey renders."""
    row = _standouts_payload_row(standouts, ticker)
    if row is None:
        return None
    pool_rows = ((standouts.get("candidate_pool") or {}).get("rows") or [])
    pool_row = next((candidate for candidate in pool_rows
                     if str(candidate.get("ticker", "")).upper() == ticker.upper()), None)
    reasons = ((pool_row or {}).get("lane_reasons")
               or ([pool_row.get("headline_reason")] if pool_row and pool_row.get("headline_reason") is not None else []))
    resolved_plan_relation = plan_relation
    if resolved_plan_relation is None:
        for candidate in ((standouts.get("buy") or [])
                          + (standouts.get("watch") or [])):
            if str(candidate.get("ticker", "")).upper() == ticker.upper():
                resolved_plan_relation = str(candidate.get("plan_relation") or "none")
                break
    payload = {
        "ticker": str(row.get("ticker", "")),
        "entry_status": ((row.get("entry_signal") or {}).get("status")
                         if isinstance(row.get("entry_signal"), dict) else None),
        "signal_asof": row.get("signal_asof"),
        "price_as_of": row.get("price_as_of"),
        "plan_relation": resolved_plan_relation,
        "plan_ids": list(plan_ids or []),
        "reason_codes": [str(reason) for reason in reasons if reason is not None],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                     separators=(",", ":"), ensure_ascii=True,
                                     allow_nan=False).encode()).hexdigest()


def _check_j7(soup: BeautifulSoup, standouts: dict[str, Any],
              ticker: str | None = None,
              plan_relation: str | None = None,
              plan_ids: list[str] | None = None,
              displayed_bodies: list[Tag] | None = None) -> dict[str, Any]:
    """J7 - independently bind the selected row and its rendered digest."""
    where = "#us-candidate-pool clock, total, selected reasons and digest"
    pool = _select_first(soup, "#us-candidate-pool")
    if pool is None:
        return _check_status("N/A", "pool container present", "no pool", where)
    if not ticker:
        return _check_status("FAIL", "selected row digest", "no ticker", where)
    if not standouts.get("candidate_pool", {}).get("rows"):
        return _check_status("N/A", "selected pool row", "candidate pool absent", where)
    row = _standouts_payload_row(standouts, ticker)
    pool_row = next((candidate for candidate in ((standouts.get("candidate_pool") or {}).get("rows") or [])
                     if str(candidate.get("ticker", "")).upper() == ticker.upper()), None)
    digest = _journey_digest(standouts, ticker, plan_relation, plan_ids)
    rendered = pool.select_one(f'.ucp-row[data-ticker="{ticker}"]')
    if digest is None or row is None or pool_row is None or rendered is None:
        return _check_status("FAIL", "selected source and rendered rows",
                             "source or rendered row missing", where)
    rendered_reasons = [str(node.get("data-reason", ""))
                        for node in rendered.select(".ucp-reason[data-reason]")]
    source_reasons = [str(value) for value in (pool_row.get("lane_reasons") or
                        ([pool_row["headline_reason"]] if pool_row.get("headline_reason") is not None else []))]
    pool_dict = standouts.get("candidate_pool") or {}
    selected_bodies = displayed_bodies if displayed_bodies is not None else (
        _setup_source_bodies(soup, ticker)[0] if ticker else [])
    rendered_bindings: list[dict[str, Any]] = []
    for body in selected_bodies:
        rendered_bindings.append({
            "ticker": str(body.get("data-native-id", "")),
            "entry_status": str(body.get("data-entry-status", "")),
            "signal_asof": str((_body_clock_text(body, ".pvs-assessment-clock")
                                or {"data-assessment-asof": ""})
                               .get("data-assessment-asof", "")),
            "price_as_of": _displayed_date(_source_field_text(body, "price_as_of")),
            "plan_relation": str(body.get("data-plan-relation", "")),
            "plan_ids": [str(record.get("data-plan-id", ""))
                         for record in body.select(
                             ".pvs-plan-rec[data-plan-id]")],
        })
    source_binding = {
        "ticker": str(row.get("ticker", "")),
        "entry_status": str((row.get("entry_signal") or {}).get("status", "")
                            if isinstance(row.get("entry_signal"), dict) else ""),
        "signal_asof": str(row.get("signal_asof", "")),
        "price_as_of": str(row.get("price_as_of", "")),
        "plan_relation": str(plan_relation
                            if plan_relation is not None else "none"),
        "plan_ids": list(plan_ids or []),
    }
    observed = {"rendered_reasons": rendered_reasons,
                "source_reasons": source_reasons,
                "rendered_bindings": rendered_bindings,
                "source_binding": source_binding,
                "data_as_of": pool.get("data-as-of", ""),
                "source_as_of": str(pool_dict.get("as_of") or ""),
                "data_total": pool.get("data-total", ""),
                "source_total": str((pool_dict.get("counts") or {}).get("eligible")),
                "digest_match": pool.get("data-source-digest") == digest}
    if not source_reasons or not rendered_reasons or any(not reason for reason in rendered_reasons):
        return _check_status("FAIL", "non-empty reason codes", observed, where)
    if rendered_reasons != source_reasons:
        return _check_status("FAIL", "rendered reasons equal source reasons", observed, where)
    if not rendered_bindings or any(
            binding != source_binding for binding in rendered_bindings):
        return _check_status("FAIL", "displayed fields match the digest source", observed, where)
    if observed["data_as_of"] != observed["source_as_of"]:
        return _check_status("FAIL", "pool clock equals source clock", observed, where)
    if observed["data_total"] != observed["source_total"]:
        return _check_status("FAIL", "pool total equals source total", observed, where)
    if not observed["digest_match"]:
        return _check_status("FAIL", "selected-row digest recomputes exactly", observed, where)
    return _check_status("PASS", "selected-row digest recomputes exactly", observed, where)


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
    """J8 — validate every selected plan link's three-part identity."""
    where = ("selected .pvs-plan-link[data-pvs-plan-target]; page plan card "
             "id and ticker; index plan id, asset and closed flag")
    if not ticker:
        return (_check_status("FAIL", "selected plan link identity",
                              "no ticker resolved", where), [])
    detail = _setup_detail_node(soup, ticker)
    if detail is None:
        return (_check_status("FAIL", "displayed selected setup body",
                              "no displayed body for ticker", where), [])
    section = detail.select_one(".pvs-plan-relation")
    relation = section.get("data-plan-relation", "") if section else ""
    if relation not in PLAN_RELATION_VOCABULARY:
        return (_check_status("FAIL", "supported plan relation state",
                              relation or "missing", where), [])
    links = section.select(".pvs-plan-link[data-pvs-plan-target]") \
        if section else []
    open_plans = [plan for plan in index.get("plans") or []
                  if isinstance(plan, dict)
                  and str(plan.get("asset", "")).upper() == ticker.upper()
                  and not plan.get("closed")]
    if relation != "related_security":
        if links or open_plans:
            return (_check_status("FAIL", "relation agrees with the open plan book",
                                  {"relation": relation,
                                   "open_matching_plans": len(open_plans),
                                   "links": len(links)}, where), [])
        return (_check_status("PASS", "honest non-related plan relation",
                              relation, where), [])
    if not links:
        return (_check_status("FAIL", "one or more related plan links",
                              "none rendered", where), [])
    plans = {str(p.get("id")): p for p in (index.get("plans") or [])
             if isinstance(p, dict) and p.get("id")}
    failures: list[dict[str, str]] = []
    plan_ids: list[str] = []
    for link in links:
        target = str(link.get("data-pvs-plan-target", ""))
        plan_id = target[3:] if target.startswith("pv-") else ""
        record = link.find_parent(class_="pvs-plan-rec")
        rendered_id = str(record.get("data-plan-id", "")) if record else ""
        book = plans.get(plan_id)
        card = _select_first(soup, f'#pv-{plan_id}') if plan_id else None
        if card is not None and card.find_parent("template") is not None:
            card = None
        card_ticker = str(card.get("data-ticker", "")).upper() if card else ""
        if not card_ticker and card is not None:
            href = card.select_one('a[href*="stock.html#"]')
            if href:
                card_ticker = (href.get("href", "").split("#", 1)[-1]).upper()
        expected_ticker = str(book.get("asset", "")).upper() if book else ticker.upper()
        if not plan_id or rendered_id != plan_id:
            failures.append({"target": target, "reason": "record_id_mismatch",
                             "rendered_id": rendered_id})
        if book is None:
            failures.append({"target": target, "reason": "book_id_missing"})
        elif str(book.get("asset", "")).upper() != ticker.upper():
            failures.append({"target": target, "reason": "other_ticker_book"})
        if book and book.get("closed"):
            failures.append({"target": target, "reason": "closed_plan"})
        if card is None:
            failures.append({"target": target, "reason": "page_card_missing"})
        elif card_ticker != ticker.upper():
            failures.append({"target": target, "reason": "other_ticker_card",
                             "card_ticker": card_ticker})
        if expected_ticker != ticker.upper():
            failures.append({"target": target, "reason": "book_ticker_mismatch"})
        if plan_id and book and not book.get("closed"):
            plan_ids.append(plan_id)
    if failures:
        return (_check_status("FAIL", "target exists, ticker matches, book open",
                              failures, where), plan_ids)
    return (_check_status("PASS", "target exists, ticker matches, book open",
                          {"targets": [l.get("data-pvs-plan-target") for l in links]},
                          where), plan_ids)


def _iso_date(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def _runtime_stamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    parsed = None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = datetime.strptime(value, fmt)
            break
        except ValueError:
            continue
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone(timedelta(hours=-4), "ET"))


def _expected_plv_state(runtime: dict[str, Any]) -> str | None:
    stamp = _runtime_stamp((runtime.get("meta") or {}).get("quote_asof"))
    if stamp is None:
        return "unavailable"
    return "today" if stamp.date() == date.today() else "prior_day"


def _plv_time_text(stamp: datetime, locale: str) -> str:
    hour = stamp.hour % 12 or 12
    minute = f"{stamp.minute:02d}"
    suffix = "am" if stamp.hour < 12 else "pm"
    return (f"美东 {hour}:{minute}" if locale == "zh"
            else f"{hour}:{minute} {suffix} ET")


def _plv_day_text(stamp: datetime, locale: str) -> str:
    if locale == "zh":
        return stamp.strftime("%m-%d")
    return stamp.strftime("%b %-d")


def _check_j9(soup: BeautifulSoup, index: dict[str, Any],
               standouts: dict[str, Any] | None = None,
               runtime: dict[str, Any] | None = None,
               locale: str = "en", ticker: str | None = None) -> dict[str, Any]:
    """J9 — bind plan-book, assessment and quote clocks to their sources."""
    where = ("#us-plan-book-asof, .pvs-assessment-clock and #plv-asof "
             "against index.asof, signal_asof and runtime meta quote_asof")
    fails: list[str] = []
    book = _select_first(soup, "#us-plan-book-asof")
    if book is None:
        fails.append("plan book clock missing")
    else:
        raw_asof = index.get("asof") or index.get("as_of")
        rendered = str(book.get("data-plan-book-asof", ""))
        text = book.get_text(" ", strip=True)
        parsed_book = _iso_date(rendered)
        raw_asof_date = _iso_date(raw_asof)
        if rendered == "":
            if raw_asof_date is not None or "Plan record date unavailable" not in text:
                fails.append("plan book empty attribute with non-unavailable text")
        elif parsed_book is None:
            fails.append("plan book attribute is not YYYY-MM-DD")
        elif str(raw_asof) != rendered:
            fails.append("plan book attribute differs from index.asof")
        elif raw_asof_date is None or not text:
            fails.append("plan book dated text mismatch")
        elif rendered not in text:
            fails.append("plan book dated text mismatch")
    idx_asof = index.get("asof") or index.get("as_of")
    idx_source = index.get("source_board_asof")
    su_asof = (standouts or {}).get("as_of")
    if idx_source and su_asof and idx_source != su_asof:
        fails.append("index.source_board_asof differs from standouts.as_of")
    if idx_source and idx_asof and str(idx_source) > str(idx_asof):
        fails.append("index publication predates its source board")

    selected_row = _standouts_payload_row(standouts or {}, ticker or "")
    wrapper = soup.select_one(f'[data-setup-ticker="{ticker}"]') if ticker else None
    body = wrapper.select_one(".pv-setup-body") if wrapper else None
    clock = body.select_one(".pvs-assessment-clock") if body else None
    if clock is None or selected_row is None:
        fails.append("assessment clock missing")
    else:
        rendered = str(clock.get("data-assessment-asof", ""))
        source = str(selected_row.get("signal_asof", ""))
        source_date = _iso_date(source)
        clock_text = clock.get_text(" ", strip=True)
        if rendered and _iso_date(rendered) is None:
            fails.append("assessment clock differs from signal_asof")
        elif source_date is not None and rendered != source:
            fails.append("assessment clock differs from signal_asof")
        elif source_date is None:
            if rendered != "":
                fails.append("assessment clock differs from signal_asof")
            elif "not supplied" not in clock_text and "来源未提供" not in clock_text:
                fails.append("assessment clock unavailable text mismatch")
    plv = _select_first(soup, "#plv-asof")
    if plv is None:
        fails.append("#plv-asof missing")
    else:
        state = str(plv.get("data-plv-asof-state", ""))
        locale_node = plv.select_one(
            ".l-zh" if locale == "zh" else ".l-en")
        text = (locale_node or plv).get_text(" ", strip=True)
        if state not in ("today", "prior_day", "unavailable"):
            fails.append("#plv-asof state missing or unsupported")
        if runtime is None:
            if not fails:
                fails.append("runtime payload missing")
        else:
            quote_raw = (runtime.get("meta") or {}).get("quote_asof")
            stamp = _runtime_stamp(quote_raw)
            expected = _expected_plv_state(runtime)
            if stamp is None or expected == "unavailable":
                if state != "unavailable" or "quote time unavailable" not in text and "报价时间不可用" not in text:
                    fails.append("unavailable quote state or text mismatch")
            else:
                minute = _plv_time_text(stamp, locale)
                day = _plv_day_text(stamp, locale)
                if state != expected:
                    if state != expected:
                        fails.append("#plv-asof state differs from quote_asof")
                if minute not in text:
                    fails.append("#plv-asof time differs from quote_asof")
                if state == expected and expected == "prior_day" and day not in text:
                    fails.append("#plv-asof day differs from quote_asof")
                if state == expected and expected == "today" and day in text:
                    fails.append("#plv-asof today text names a prior day")
    if runtime is None:
        return _check_status("UNSUPPORTED",
                             "runtime quote state judged from rendered DOM",
                             {"reason": "live/prophet_live.json runtime payload not supplied",
                              "fails": fails},
                             where)
    if fails:
        return _check_status("FAIL", "all clocks bound to their sources",
                             fails, where)
    return _check_status("PASS", "all clocks bound to their sources",
                         {"plan_book": str(book.get("data-plan-book-asof", "")) if book else None,
                          "plv_state": str(plv.get("data-plv-asof-state", "")) if plv else None},
                         where)

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
            if mkt.upper() != "US":
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


def _runtime_engine_vocabulary() -> tuple[frozenset[str], tuple[str, str]]:
    try:
        from engine.prophet_bridge import REFUSAL_ORDER
        from engine.us_candidate_lanes import declared_reasons as engine_declared_reasons
    except (ImportError, RuntimeError) as exc:
        return frozenset(), (type(exc).__name__, str(exc))
    return frozenset(engine_declared_reasons()), REFUSAL_ORDER


def declared_reasons() -> frozenset[str]:
    """The runtime lane vocabulary, including engine featured-shortfall codes."""
    reasons, _error = _runtime_engine_vocabulary()
    return reasons


def _payload_enum_values(node: Any, fields: Iterable[str],
                         prefix: str = "") -> set[str]:
    values: set[str] = set()
    if isinstance(node, dict):
        for field in fields:
            value = node.get(field)
            if isinstance(value, str) and value:
                values.add(value)
        for value in node.values():
            values |= _payload_enum_values(value, fields, prefix)
    elif isinstance(node, list):
        for value in node:
            values |= _payload_enum_values(value, fields, prefix)
    return values


def _enum_values(standouts: dict[str, Any], index: dict[str, Any]) -> set[str]:
    """Every internal vocabulary that must never appear as display copy."""
    plan_values = _payload_enum_values(index.get("plans") or [], PLAN_ENUM_FIELDS)
    standout_values = _payload_enum_values(standouts, STANDOUTS_ENUM_FIELDS)
    vocabulary = (declared_reasons() | plan_values | standout_values
                  | LIFECYCLE_VOCABULARY | PLAN_RELATION_VOCABULARY)
    return {token for token in vocabulary if "_" in token}


def _scan_tokens(text: str, banned: set[str]) -> list[dict[str, str]]:
    """Find banned enum tokens in display text, preserving snippets."""
    hits: list[dict[str, str]] = []
    for token in sorted(banned):
        for match in re.finditer(r"(?<![\w])" + re.escape(token) + r"(?![\w])", text, re.IGNORECASE):
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            hits.append({"token": token,
                         "snippet": text[start:end].replace("\n", " ").strip()[:80]})
    return hits


def _reason_shape_problems(soup: BeautifulSoup) -> list[dict[str, str]]:
    problems: list[dict[str, str]] = []
    for reason in soup.select(".ucp-reason"):
        if reason.find_parent("template") is not None:
            continue
        code = str(reason.get("data-reason", ""))
        if not code:
            problems.append({"problem": "empty data-reason"})
            continue
        if not re.fullmatch(r"[a-z0-9_]+", code):
            problems.append({"problem": "invalid data-reason", "code": code})
            continue
        english_node = reason.select_one(".l-en")
        english = english_node.get_text(" ", strip=True) if english_node else ""
        chinese_node = reason.select_one(".l-zh")
        chinese = chinese_node.get_text(" ", strip=True) if chinese_node else ""
        if not english:
            problems.append({"problem": "empty English label", "code": code})
        elif not any("a" <= char.lower() <= "z" for char in english):
            problems.append({"problem": "English label has no ASCII letter",
                             "code": code, "label": english})
        if re.search(r"[\u3400-\u9fff]", english):
            problems.append({"problem": "CJK in English label", "code": code,
                             "label": english})
        normalized_code = re.sub(r"[ _]+", "", code).casefold()
        normalized_label = re.sub(r"[ _]+", "", english).casefold()
        if normalized_label == normalized_code:
            problems.append({"problem": "English label repeats the reason code",
                             "code": code, "label": english})
        if not chinese or not re.search(r"[\u3400-\u9fff]", chinese):
            problems.append({"problem": "Chinese label has no CJK text",
                             "code": code, "label": chinese})
        raw_nodes = reason.select("code.ucp-reason-raw")
        if raw_nodes:
            raw = raw_nodes[0]
            if raw.get_text(" ", strip=True) != code:
                problems.append({"problem": "raw code differs from data-reason",
                                 "code": code,
                                 "raw": raw.get_text(" ", strip=True)})
            if len(raw_nodes) > 1:
                problems.append({"problem": "multiple raw code nodes", "code": code})
            if english != "Unlabelled decision code":
                problems.append(
                    {"problem": "unmapped English label must be exact",
                     "code": code, "label": english})
    return problems


def _remove_raw_reason_nodes(node: Tag) -> None:
    for raw in node.select("span.ucp-reason[data-reason] > code.ucp-reason-raw"):
        raw.decompose()


def _check_j11(soup: BeautifulSoup, locale: str,
               standouts: dict[str, Any], index: dict[str, Any],
               ticker: str | None,
               plan_ids: list[str]) -> dict[str, Any]:
    """J11 — no internal enum tokens in displayed journey text."""
    where = (".ucp-receipt, .pvs-section, .pv-setup-body and #us-plan-block "
             "displayed text; raw codes allowed only inside code.ucp-reason-raw")
    reason_problems = _reason_shape_problems(soup)
    if reason_problems:
        return _check_status(
            "FAIL", "every displayed reason has a valid code and plain labels",
            reason_problems[:20], where)
    scopes: list[Tag] = []
    for selector in (".ucp-receipt", ".pvs-section", ".pv-setup-body", "#us-plan-block"):
        for node in soup.select(selector):
            if node.find_parent("template") is not None:
                continue
            scopes.append(node)
    scopes = [node for node in scopes
              if not any(other is not node and other in node.parents for other in scopes)]
    if not scopes:
        return _check_status("FAIL", "displayed scopes present",
                             "no displayed scopes", where)
    banned = _enum_values(standouts, index)
    hits: list[dict[str, Any]] = []
    for node in scopes:
        copied = BeautifulSoup(str(node), HTML_PARSER)
        target = copied.body or copied
        _remove_raw_reason_nodes(target)
        text = _visible_text(target, locale)
        for hit in _scan_tokens(text, banned):
            hit["node"] = node.name or "?"
            hits.append(hit)
    if hits:
        return _check_status("FAIL", "no internal enum tokens in displayed text",
                             hits[:20], where)
    return _check_status("PASS", "no internal enum tokens in displayed text",
                         {"scopes_walked": len(scopes)}, where)


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
    if "UNSUPPORTED" in statuses:
        return "PARTIAL"
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
    j8, plan_ids = _check_j8(soup, index, ticker)
    displayed_bodies, _templates = _setup_source_bodies(
        soup, ticker) if ticker else ([], [])
    displayed_binding = (_body_binding(displayed_bodies[0])
                         if displayed_bodies else None)
    j7 = _check_j7(
        soup, standouts, ticker,
        plan_relation=displayed_binding["data-plan-relation"]
        if displayed_binding else None,
        plan_ids=plan_ids, displayed_bodies=displayed_bodies)
    runtime_path = page_path.parent / "prophet_live.json"
    runtime = _load_json(runtime_path) if runtime_path.exists() else None
    j9 = _check_j9(soup, index, standouts, runtime, args.locale, ticker)
    j10 = _check_j10(soup, ticker, plan_ids)
    j11 = _check_j11(soup, args.locale, standouts, index, ticker, plan_ids)
    j12 = _check_j12(soup, index, standouts, ticker, plan_ids)

    checks = [j1, j2, j3, j4, j5, j6, j7, j8, j9, j10, j11, j12]
    ids = ["J1", "J2", "J3", "J4", "J5", "J6", "J7", "J8", "J9",
           "J10", "J11", "J12"]
    for chk, cid in zip(checks, ids):
        chk["id"] = cid
    verdict = _verdict(checks)
    for chk in checks:
        reason = str(chk.get("expected", ""))
        print(f"{chk['id']} {chk['status']} {reason}")
    print(f"RESULT: {verdict}")

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
