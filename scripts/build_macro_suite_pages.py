"""Render the Macro & Monetary workspace pages (F01 suite, R1B).

One builder for the whole twelve-workspace suite. For each REGISTERED page it:

1. reads the suite manifest and the workspace snapshot published by R1A
   (``site/macrodata/workspaces/manifest.json`` and
   ``site/macrodata/workspaces/<workspace>/<region>/latest.json``);
2. validates FAIL-CLOSED through the shared contract
   (``engine.market_os.macro_workspaces.contract``): closed schema, exact
   contract id and version, and a recomputed ``content_sha256``; then
   cross-checks the manifest's declared hash and byte size against the body it
   actually read, so a manifest can never describe a generation the page is not
   showing;
3. builds the pre-labelled view model (``lib.macro_suite_view``) and renders the
   shared shell to a flat page under ``site/``.

A validation failure does NOT produce an empty page and does NOT fall back to a
previous build. It renders the honest refusal page: workspace identity, the
typed reason, the exact artifact receipt, and no state whatsoever.

Adding workspace 2..12 is one :class:`SuitePage` entry plus a thin template.

Usage:
    python -m scripts.build_macro_suite_pages
    python -m scripts.build_macro_suite_pages --root /path/to/repo
    python -m scripts.build_macro_suite_pages --data-root /tmp/tampered/macrodata
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from jinja2 import Environment, FileSystemLoader, StrictUndefined

_REPO_ROOT = Path(__file__).resolve().parents[1]
# Unconditional insert at position 0 — the conditional shape is not a pin: a repo
# root already present LATER in sys.path leaves a decoy tree ahead of it, which is
# exactly what the import-pin guard's hostile-tree proof rejects.
sys.path.insert(0, str(_REPO_ROOT))

from engine.market_os.macro_workspaces import contract, registry  # noqa: E402
from lib import macro_suite_labels as L  # noqa: E402
from lib import macro_suite_view  # noqa: E402

# Shared across every workspace page: copied once per build, never per page.
# macro_command.css / macro_command.js are Macro Command's page-level assets —
# non-.j2 plain-copy files, so they are paired here (F01 Macro Command P1,
# frozen spec §9 standing notes) and re-synced with
# `python -m scripts.check_template_site_sync --fix`.
SHARED_ASSETS = ("macro_suite_boot.js", "macro_suite.css", "macro_suite.js",
                  "macro_command.css", "macro_command.js")

MIN_CLIENT_CONTRACT = f"{contract.CONTRACT_ID}@{contract.CONTRACT_VERSION}"


@dataclass(frozen=True)
class SuitePage:
    """One published workspace page. This is the whole per-page contract."""

    workspace_id: str
    region: str
    template: str
    output: str
    seo_title: str
    seo_desc: str


# The suite registry. A workspace appears here only when its producer is BUILT
# in engine.market_os.macro_workspaces.registry — a page is never advertised
# ahead of its data (production navigation law, architecture section 6.2).
# R1B shipped liquidity_regime; the R2 pages wave (2026-09-04) added the six
# MCS/cycle workspaces the R2 producer wave made BUILT.
SUITE_PAGES: tuple[SuitePage, ...] = (
    SuitePage(
        workspace_id="liquidity_regime",
        region="US",
        template="macro_liquidity_regime.html.j2",
        output="macro_liquidity_regime.html",
        seo_title="US Liquidity Regime Monitor — Macro & Monetary | MastermindX",
        seo_desc=(
            "Funding pressure against balance-sheet support for the United States, "
            "with every source clock, method receipt and typed gap shown."
        ),
    ),
    SuitePage(
        workspace_id="growth_real_economy",
        region="US",
        template="macro_growth_real_economy.html.j2",
        output="macro_growth_real_economy.html",
        seo_title="US Growth & Real Economy — Macro & Monetary | MastermindX",
        seo_desc=(
            "Growth momentum against level and breadth for the United States, with "
            "nowcast-versus-hard-data disagreement, source clocks and typed gaps shown."
        ),
    ),
    SuitePage(
        workspace_id="business_activity",
        region="US",
        template="macro_business_activity.html.j2",
        output="macro_business_activity.html",
        seo_title="US Business Activity — Macro & Monetary | MastermindX",
        seo_desc=(
            "Leading, coincident and lagging cycle tiers for the United States — "
            "composites refuse honestly when their legs fall below floor, with every "
            "source clock shown."
        ),
    ),
    SuitePage(
        workspace_id="labor_markets",
        region="US",
        template="macro_labor_markets.html.j2",
        output="macro_labor_markets.html",
        seo_title="US Labor Markets — Macro & Monetary | MastermindX",
        seo_desc=(
            "Labor demand against supply tightness for the United States, with "
            "source clocks, method receipts and typed coverage gaps shown."
        ),
    ),
    SuitePage(
        workspace_id="inflation_system",
        region="US",
        template="macro_inflation_system.html.j2",
        output="macro_inflation_system.html",
        seo_title="US Inflation System — Macro & Monetary | MastermindX",
        seo_desc=(
            "Inflation impulse against persistence and breadth for the United "
            "States, with sticky-versus-headline contradictions surfaced and "
            "release-lag clocks shown."
        ),
    ),
    SuitePage(
        workspace_id="monetary_policy",
        region="US",
        template="macro_monetary_policy.html.j2",
        output="macro_monetary_policy.html",
        seo_title="US Monetary Policy — Macro & Monetary | MastermindX",
        seo_desc=(
            "Policy stance against the market-implied path for the United States, "
            "with two-sided splits surfaced and every source clock and typed gap shown."
        ),
    ),
    SuitePage(
        workspace_id="financial_conditions",
        region="US",
        template="macro_financial_conditions.html.j2",
        output="macro_financial_conditions.html",
        seo_title="US Financial Conditions — Macro & Monetary | MastermindX",
        seo_desc=(
            "Financial-conditions level against impulse for the United States, with "
            "uncovered legs typed honestly and every source clock shown."
        ),
    ),
    SuitePage(
        workspace_id="liquidity_central_banks",
        region="US",
        template="macro_liquidity_central_banks.html.j2",
        output="macro_liquidity_central_banks.html",
        seo_title="Liquidity & Central Banks — Macro & Monetary | MastermindX",
        seo_desc=(
            "Global monetary impulse against Fed, ECB and BoJ balance-sheet stance, "
            "with the weekly grid clock, warmup windows and typed gaps shown."
        ),
    ),
    SuitePage(
        workspace_id="capital_structure",
        region="US",
        template="macro_capital_structure.html.j2",
        output="macro_capital_structure.html",
        seo_title="US Capital Structure — Macro & Monetary | MastermindX",
        seo_desc=(
            "A read-only census of the US corporate capital-structure event "
            "projection — coverage, classification and review backlog, with "
            "everything the owner does not publish typed honestly."
        ),
    ),
    SuitePage(
        workspace_id="housing_real_estate",
        region="US",
        template="macro_housing_real_estate.html.j2",
        output="macro_housing_real_estate.html",
        seo_title="US Housing & Real Estate — Macro & Monetary | MastermindX",
        seo_desc=(
            "Mortgage rates, starts, permits and home prices for the United States, "
            "with rights-blocked and uncovered legs typed honestly and every "
            "release clock shown."
        ),
    ),
    SuitePage(
        workspace_id="consumer_payments",
        region="US",
        template="macro_consumer_payments.html.j2",
        output="macro_consumer_payments.html",
        seo_title="US Consumer & Payments — Macro & Monetary | MastermindX",
        seo_desc=(
            "Retail sales, consumer sentiment, household credit, saving and "
            "delinquencies for the United States — payments panels and sources "
            "still being collected are typed honestly, never imputed."
        ),
    ),
    SuitePage(
        workspace_id="national_debt_liabilities",
        region="US",
        template="macro_national_debt_liabilities.html.j2",
        output="macro_national_debt_liabilities.html",
        seo_title="US National Debt & Liabilities — Macro & Monetary | MastermindX",
        seo_desc=(
            "Treasury cash balance, net issuance, auction demand and BIS debt-service "
            "reads for the United States, with the missing debt-stock lanes disclosed "
            "rather than fabricated."
        ),
    ),
    SuitePage(
        workspace_id="rates_curves",
        region="US",
        template="macro_rates_curves.html.j2",
        output="macro_rates_curves.html",
        seo_title="US Rates & Curves — Macro & Monetary | MastermindX",
        seo_desc=(
            "The Treasury curve node by node — slopes, inversions, real yields, "
            "breakevens, term premium and the policy corridor — every read dated "
            "and same-day-disciplined."
        ),
    ),
    SuitePage(
        workspace_id="trade_flows",
        region="US",
        template="macro_trade_flows.html.j2",
        output="macro_trade_flows.html",
        seo_title="US Trade Flows — Macro & Monetary | MastermindX",
        seo_desc=(
            "The US trade balance, exports, imports and trade prices on a "
            "balance-of-payments basis — collection state shown honestly while "
            "the source lanes come online."
        ),
    ),
)


@dataclass(frozen=True)
class HubPage:
    """The one suite entry point. It owns no producer and publishes no state of
    its own — it composes what the fourteen workspace owners already published."""

    template: str
    output: str
    seo_title: str
    seo_desc: str


HUB_PAGE = HubPage(
    template="macro_monetary.html.j2",
    output="macro_monetary.html",
    seo_title="Macro & Monetary — the current read across fourteen workspaces | MastermindX",
    seo_desc=(
        "One entry point to the Macro & Monetary research suite: the current state of "
        "each of the fourteen workspaces, what changed, and which inputs need attention "
        "— every read dated and every gap typed."
    ),
)

#: Workspaces whose body renders decision-first rather than in the frozen §6.3
#: order. R1 sets the pattern on ONE page (Sol ruling 2026-09-05); extending it is
#: one entry here, and the amendment record
#: research/market_intelligence_productization/MARKET_ONTOLOGY_F01_R1_DECISION_FIRST_AMENDMENT_2026-09-05.md
#: is what authorizes the supersession.
DECISION_FIRST_WORKSPACES = frozenset({"liquidity_regime"})


@dataclass(frozen=True)
class SubTab:
    """One sub-tab inside a Macro Command section that covers two workspaces
    (frozen spec §1.1). `id` is a bare token — the template writes the
    `#<section>/<subtab>` hash and DOM ids, never this dataclass (R10)."""

    id: str
    label_en: str
    label_zh: str
    workspace_id: str
    deep_href: str


@dataclass(frozen=True)
class Section:
    """One Macro Command left-rail section (frozen spec §1.1 / §1.3).

    Named for the CUSTOMER's question, not the producer's workspace title —
    `label_en`/`label_zh` are the question, and `subtabs` (when present) are
    named for the answer. Either `workspace_id`+`deep_href` (single-workspace
    section) or `subtabs` (two-workspace section) is set, never both."""

    id: str
    label_en: str
    label_zh: str
    workspace_id: str | None = None
    deep_href: str | None = None
    subtabs: tuple[SubTab, ...] = ()
    question_en: str | None = None
    question_zh: str | None = None


# Macro Command left-rail sections — twelve, in the FIXED reading order a
# first-time customer asks them (frozen spec §1.1), never the producer
# registry order above (SUITE_PAGES) and never re-sorted with the data (G3,
# DNR:KILL-REGIME-SCORECARD). The template adds the leading "#" to `id` for
# hrefs/DOM ids (R10) — this constant carries bare tokens only.
SECTIONS: tuple[Section, ...] = (
    Section(id="overview", label_en="Overview", label_zh="总览",
            question_en="What is macro saying today, and what moved?",
            question_zh="今天宏观在说什么？有什么变化？"),
    Section(id="money", label_en="Money & liquidity", label_zh="资金与流动性",
            question_en="Is money getting easier or harder to come by?",
            question_zh="资金是变得更容易还是更难获得？", subtabs=(
        SubTab(id="liquidity", label_en="How much money is around", label_zh="市场资金",
               workspace_id="liquidity_regime", deep_href="macro_liquidity_regime.html"),
        SubTab(id="central_banks", label_en="What central banks are holding", label_zh="央行资产负债表",
               workspace_id="liquidity_central_banks", deep_href="macro_liquidity_central_banks.html"),
    )),
    Section(id="policy", label_en="Policy rates", label_zh="政策利率",
            workspace_id="monetary_policy", deep_href="macro_monetary_policy.html",
            question_en="Where is the policy rate, and where do markets think it goes?",
            question_zh="政策利率在哪里？市场认为它会去哪里？"),
    Section(id="rates", label_en="Rates & the curve", label_zh="利率与收益率曲线",
            workspace_id="rates_curves", deep_href="macro_rates_curves.html",
            question_en="What do government borrowing costs look like across time?",
            question_zh="不同期限的政府借贷成本是什么样？"),
    Section(id="inflation", label_en="Inflation", label_zh="通胀",
            workspace_id="inflation_system", deep_href="macro_inflation_system.html",
            question_en="Are prices still rising, and is it spreading?",
            question_zh="物价还在上涨吗？涨势是否在扩散？"),
    Section(id="growth", label_en="Growth", label_zh="经济增长", subtabs=(
        SubTab(id="economy", label_en="The whole economy", label_zh="整体经济",
               workspace_id="growth_real_economy", deep_href="macro_growth_real_economy.html"),
        SubTab(id="business", label_en="What companies are doing", label_zh="企业活动",
               workspace_id="business_activity", deep_href="macro_business_activity.html"),
    )),
    Section(id="jobs", label_en="Jobs", label_zh="就业",
            workspace_id="labor_markets", deep_href="macro_labor_markets.html"),
    Section(id="housing", label_en="Housing", label_zh="房地产",
            workspace_id="housing_real_estate", deep_href="macro_housing_real_estate.html"),
    Section(id="consumer", label_en="Consumers", label_zh="消费者",
            workspace_id="consumer_payments", deep_href="macro_consumer_payments.html"),
    Section(id="credit", label_en="Borrowing costs", label_zh="融资环境", subtabs=(
        SubTab(id="borrowing", label_en="How hard it is to borrow", label_zh="融资难易",
               workspace_id="financial_conditions", deep_href="macro_financial_conditions.html"),
        SubTab(id="funding", label_en="How companies fund themselves", label_zh="企业融资结构",
               workspace_id="capital_structure", deep_href="macro_capital_structure.html"),
    )),
    Section(id="debt", label_en="Government debt", label_zh="政府债务",
            workspace_id="national_debt_liabilities", deep_href="macro_national_debt_liabilities.html"),
    Section(id="trade", label_en="Trade", label_zh="贸易往来",
            workspace_id="trade_flows", deep_href="macro_trade_flows.html"),
)


def _layout_for(workspace_id: str) -> str:
    return (macro_suite_view.LAYOUT_DECISION_FIRST
            if workspace_id in DECISION_FIRST_WORKSPACES
            else macro_suite_view.LAYOUT_GRAMMAR)


def suite_nav(current_output: str | None) -> dict[str, Any]:
    """The in-suite navigation context shared by the hub and all fourteen pages.

    Built from the closed registry in SUITE_PAGES order, so the switcher can
    never advertise a workspace the producer registry does not carry, and can
    never present a different order from the hub.
    """
    # `entries`, never `items`: `nav.items` in Jinja resolves to the dict method.
    entries = []
    for page in SUITE_PAGES:
        identity = _identity(page)
        entries.append({
            "workspace_id": page.workspace_id,
            "href": page.output,
            "title": identity["title"],
            "current": page.output == current_output,
        })
    return {
        "hub": {"href": HUB_PAGE.output, "current": HUB_PAGE.output == current_output},
        "entries": entries,
    }



class SnapshotRefused(Exception):
    """The published artifact did not clear the closed contract.

    ``kind`` is a token from the contract's closed null vocabulary (section
    7.7), so the refusal the reader sees is typed rather than free text.
    """

    def __init__(self, kind: str, detail: str) -> None:
        super().__init__(detail)
        self.kind = kind
        self.detail = detail


def _temp_sibling(path: Path) -> Path:
    return path.with_name(f".{path.name}.{os.getpid()}.tmp")


def _atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = _temp_sibling(destination)
    try:
        shutil.copyfile(source, temp)
        os.replace(temp, destination)
    finally:
        temp.unlink(missing_ok=True)


def _read_json(path: Path) -> Any:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise SnapshotRefused("SOURCE_FAILED", f"cannot read {path.name}: {exc.strerror or exc}") from exc
    try:
        return json.loads(raw.decode("utf-8")), len(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SnapshotRefused("SOURCE_FAILED", f"{path.name} is not valid JSON: {exc}") from exc


def read_workspace(data_root: Path, page: SuitePage) -> tuple[dict, dict]:
    """Load + validate one workspace artifact. Raises :class:`SnapshotRefused`.

    Order matters: the manifest is read FIRST (it is written LAST by the
    producer, so its presence implies the body is already on disk), then the
    body, then the body is checked against what the manifest declared. A reader
    that trusted either half alone could render one generation under another
    generation's header.
    """
    manifest_path = data_root / "workspaces" / "manifest.json"
    manifest, _ = _read_json(manifest_path)
    if not isinstance(manifest, Mapping):
        raise SnapshotRefused("SOURCE_FAILED", "manifest.json is not a JSON object")

    declared_contract = manifest.get("min_client_contract")
    if declared_contract != MIN_CLIENT_CONTRACT:
        raise SnapshotRefused(
            "COMPUTATION_REFUSED",
            f"manifest requires client contract {declared_contract!r}; this page implements "
            f"{MIN_CLIENT_CONTRACT!r}",
        )

    key = f"{page.workspace_id}/{page.region}"
    entry = (manifest.get("workspaces") or {}).get(key)
    if not isinstance(entry, Mapping):
        raise SnapshotRefused("NOT_COVERED", f"the suite manifest publishes no entry for {key!r}")

    relative = str(entry.get("path") or "")
    if not relative or relative.startswith("/") or ".." in Path(relative).parts:
        raise SnapshotRefused("SOURCE_FAILED", f"manifest path for {key!r} is not a safe relative path")

    body_path = data_root / relative
    snapshot, byte_size = _read_json(body_path)

    try:
        contract.validate(snapshot)
    except contract.ContractError as exc:
        raise SnapshotRefused("COMPUTATION_REFUSED", str(exc)) from exc

    published = (snapshot.get("generation") or {}).get("content_sha256")
    if entry.get("content_sha256") != published:
        raise SnapshotRefused(
            "DISAGREEMENT",
            f"manifest declares content_sha256 {entry.get('content_sha256')!r} but the body carries "
            f"{published!r}",
        )
    if isinstance(entry.get("bytes"), int) and entry["bytes"] != byte_size:
        raise SnapshotRefused(
            "DISAGREEMENT",
            f"manifest declares {entry['bytes']} bytes but the body on disk is {byte_size}",
        )
    if snapshot.get("workspace", {}).get("id") != page.workspace_id or \
            snapshot.get("region", {}).get("code") != page.region:
        raise SnapshotRefused(
            "DISAGREEMENT",
            "the artifact's own workspace/region identity does not match the manifest entry",
        )

    artifact = {
        "path": f"macrodata/{relative}",
        "manifest_path": "macrodata/workspaces/manifest.json",
        "sha256": published,
        "bytes": byte_size,
        "min_client_contract": MIN_CLIENT_CONTRACT,
    }
    return dict(snapshot), artifact


def _identity(page: SuitePage) -> dict[str, Any]:
    """Workspace identity for the refusal page, taken from the closed registry —
    never from the artifact we just refused to trust."""
    entry = registry.entry(page.workspace_id)
    return {
        "title": {"en": entry.get("title_en") or page.workspace_id,
                  "zh": entry.get("title_zh") or entry.get("title_en") or page.workspace_id},
        "subtitle": {"en": entry.get("subtitle_en") or "",
                     "zh": entry.get("subtitle_zh") or entry.get("subtitle_en") or ""},
    }


_REGION_NAMES = {"US": "United States"}


def _environment(root: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(root / "templates")),
        autoescape=True,
        undefined=StrictUndefined,
    )


def render_page(env: Environment, page: SuitePage, view: Mapping[str, Any]) -> str:
    html = env.get_template(page.template).render(
        view=view,
        workspace_id=page.workspace_id,
        region_code=page.region,
        page_title=view["workspace"]["title"]["en"],
        page_seo_title=page.seo_title,
        page_seo_desc=page.seo_desc,
        page_seo_path=page.output,
        active_section="research",
        active_page=Path(page.output).stem,
        suite_nav=suite_nav(page.output),
    )
    # The shared navigation partials indent around conditional blocks; normalise
    # generated-only trailing whitespace so the committed page stays diff-clean.
    return "\n".join(line.rstrip() for line in html.splitlines()) + "\n"


def build_page(root: Path, page: SuitePage, *, data_root: Path, out_dir: Path,
               env: Environment, page_built_at: str) -> tuple[Path, bool]:
    """Render one workspace page. Returns ``(path, ok)`` — ``ok`` is False when
    the page rendered the honest refusal instead of a state."""
    identity = _identity(page)
    fallback_artifact = {
        "path": f"macrodata/workspaces/{page.workspace_id}/{page.region}/latest.json",
        "manifest_path": "macrodata/workspaces/manifest.json",
        "sha256": None,
        "bytes": None,
        "min_client_contract": MIN_CLIENT_CONTRACT,
    }
    try:
        snapshot, artifact = read_workspace(data_root, page)
        view = macro_suite_view.build_view(snapshot, page_built_at=page_built_at,
                                           artifact=artifact, layout=_layout_for(page.workspace_id))
        ok = True
        hub_entry: dict[str, Any] = {"snapshot": snapshot, "failure": None}
    except SnapshotRefused as refusal:
        print(
            f"::warning title=macro_suite_page::{page.workspace_id}/{page.region} refused "
            f"({refusal.kind}: {refusal.detail}) — rendering the degraded page",
            flush=True,
        )
        view = macro_suite_view.degraded_view(
            workspace_id=page.workspace_id,
            title=identity["title"],
            subtitle=identity["subtitle"],
            region_code=page.region,
            region_display_name=_REGION_NAMES.get(page.region, page.region),
            page_built_at=page_built_at,
            artifact=fallback_artifact,
            failure_kind=refusal.kind,
            failure_detail=refusal.detail,
        )
        ok = False
        hub_entry = {"snapshot": None,
                     "failure": {"kind": refusal.kind, "detail": refusal.detail}}

    html = render_page(env, page, view)

    # write_page owns the depth-aware data-base shim. Route through a temporary
    # file so even an interrupted builder cannot leave a partial page served.
    from lib.pages import write_page  # noqa: PLC0415

    out_dir.mkdir(parents=True, exist_ok=True)
    destination = out_dir / page.output
    temp = _temp_sibling(destination)
    try:
        write_page(temp, html)
        os.replace(temp, destination)
    finally:
        temp.unlink(missing_ok=True)

    hub_entry.update({
        "workspace_id": page.workspace_id,
        "region": page.region,
        "output": page.output,
        "title": identity["title"],
        "subtitle": identity["subtitle"],
    })
    return destination, ok, hub_entry


P3_COPY_IDS = frozenset({"overview", "money", "policy", "rates", "inflation"})
P3_PRIMER_OPEN = frozenset({"overview", "money", "policy"})
_SOURCE_NOTE_TITLES = frozenset({
    "Required source not current",
    "Optional legs degraded",
    "Contradictory signals",
})
_E2_STATES = frozenset({"SOURCE_FAILED", "STALE_SOURCE"})


class MacroCommandBuildError(RuntimeError):
    """Fail-closed: an unmapped stance key or metric id writes no page."""


def rail_workspace_ids() -> tuple[str, ...]:
    """The fourteen workspaces in rail reading order (addendum DELTA 13).

    Sub-tabbed sections contribute first sub-tab then second. Data-independent,
    so DNR:KILL-REGIME-SCORECARD is not engaged.
    """
    order: list[str] = []
    for section in SECTIONS:
        if section.subtabs:
            order.extend(tab.workspace_id for tab in section.subtabs)
        elif section.workspace_id:
            order.append(section.workspace_id)
    return tuple(order)


def _detail_link(title_by_workspace: Mapping[str, Mapping[str, str]], workspace_id: str,
                  deep_href: str) -> dict[str, Any]:
    title = title_by_workspace.get(workspace_id)
    return {"title": title or {"en": workspace_id, "zh": workspace_id}, "href": deep_href}


def _empty_state(state_id: str, *, cta_href: str | None = None,
                 plan: str | None = None) -> dict[str, Any]:
    spec = L.EMPTY_STATES[state_id]
    state: dict[str, Any] = {
        "id": spec["id"],
        "title": dict(spec["title"]),
        "why": dict(spec["why"]),
        "unlock": dict(spec["unlock"]) if spec.get("unlock") else None,
        "next": dict(spec["next"]) if spec.get("next") else None,
        "cta": None,
    }
    if state_id == "e5":
        state["cta"] = {"href": cta_href or "#overview", "label": dict(spec["cta_label"])}
        state["unlock"] = None
        state["next"] = None
    elif state_id == "e6":
        why = spec["why"]
        filled = plan or "a higher plan"
        state["why"] = {"en": why["en"].format(plan=filled),
                        "zh": why["zh"].format(plan=filled)}
        state["cta"] = {"href": spec["cta_href"], "label": dict(spec["cta_label"])}
        state["next"] = None
    elif state_id == "e2":
        state["next"] = None
    elif state_id == "e3":
        state["unlock"] = None
    elif state_id == "e4":
        state["next"] = None
    return state


def _require_metric(metric_id: str) -> None:
    if metric_id not in L.METRIC:
        raise MacroCommandBuildError(
            f"unmapped metric_id {metric_id!r} on the hub — extend METRIC, never deslug")


def _move_rows_from_deltas(deltas: Sequence[Mapping[str, Any]], *,
                           href: str | None, show_source: Mapping[str, str] | None,
                           prior_is_earlier: bool = True,
                           as_of_month: Mapping[str, str] | None = None,
                           ) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for delta in deltas:
        metric_id = str(delta.get("metric_id") or "")
        _require_metric(metric_id)
        is_movement = bool(
            prior_is_earlier
            and (delta.get("is_movement") if "is_movement" in delta
                 else (delta.get("prior_present") and delta.get("current_present")
                       and delta.get("delta_present")))
        )
        if is_movement:
            sign = delta.get("sign") if delta.get("delta_present") else "unavailable"
            rows.append({
                "kind": "movement",
                "name": dict(delta["label"]) if delta.get("label") else dict(L.METRIC[metric_id]),
                "source": dict(show_source) if show_source else None,
                "href": href,
                "prior": delta.get("prior") if delta.get("prior_present") else L.EM_DASH,
                "current": delta.get("current") if delta.get("current_present") else L.EM_DASH,
                "delta": delta.get("delta") if delta.get("delta_present") else L.EM_DASH,
                "sign": sign or "unavailable",
                "as_of_month": None,
                "metric_id": metric_id,
            })
            continue
        if not delta.get("current_present"):
            continue
        rows.append({
            "kind": "current",
            "name": dict(delta["label"]) if delta.get("label") else dict(L.METRIC[metric_id]),
            "source": dict(show_source) if show_source else None,
            "href": href,
            "prior": None,
            "current": delta.get("current"),
            "delta": None,
            "sign": None,
            "as_of_month": dict(as_of_month) if as_of_month else None,
            "metric_id": metric_id,
        })
    return rows


def _figure_mode(rows: Sequence[Mapping[str, Any]]) -> str:
    """Overview deck voice from the rows that are actually on the figure.

    R6-M2: "movement" when any row has a genuine earlier prior; "current"
    only when no row does; "mixed" when both kinds sit in one figure.
    """
    has_movement = any(row.get("kind") == "movement" for row in rows)
    has_current = any(row.get("kind") == "current" for row in rows)
    if has_movement and has_current:
        return "mixed"
    if has_movement:
        return "movement"
    return "current"


def _panel_is_populated(section: Mapping[str, Any]) -> bool:
    """R6-m2: populated means a typed figure or empty, never stance-only."""
    if section.get("figure") or section.get("empty"):
        return True
    for tab in section.get("subtabs") or []:
        if tab.get("figure") or tab.get("empty"):
            return True
    return False


def _section_coverage_workspace(section_id: str) -> str | None:
    """Primary workspace for a rail section — first sub-tab when split."""
    for section in SECTIONS:
        if section.id != section_id:
            continue
        if section.workspace_id:
            return section.workspace_id
        if section.subtabs:
            return section.subtabs[0].workspace_id
        return None
    return None


def populated_section_coverage_tally(
        entries: Sequence[Mapping[str, Any]],
        panel_ids: set[str]) -> tuple[int, int]:
    """DATA COVERAGE for the panels this page actually renders (R6-M1)."""
    by_workspace = {entry["workspace_id"]: entry for entry in entries}
    available = 0
    total = 0
    for section in SECTIONS:
        if section.id not in panel_ids:
            continue
        total += 1
        if section.id == "overview":
            available += 1
            continue
        workspace_id = _section_coverage_workspace(section.id)
        entry = by_workspace.get(workspace_id) if workspace_id else None
        snap = entry.get("snapshot") if entry else None
        if snap and macro_suite_view._freshness_state(snap) == "CURRENT":
            available += 1
    return available, total


def _apply_overview_deck(section: dict[str, Any], *,
                         available: int, total: int) -> None:
    """One Overview voice from figure mode + the populated coverage tally."""
    rows = list((section.get("figure") or {}).get("rows") or [])
    mode = _figure_mode(rows)
    key = "all_read" if available == total else "some_unread"
    if mode == "current":
        key = f"{key}_current"
        section["question"] = dict(L.OVERVIEW_QUESTIONS["current"])
        if section.get("figure"):
            # One null voice: the stance already says there is no earlier
            # reading. Mixed must NOT take this branch (R6-M2).
            section["figure"]["state_line"] = None
    elif mode == "mixed":
        key = f"{key}_mixed"
        section["question"] = dict(L.OVERVIEW_QUESTIONS["movement"])
        if section.get("figure"):
            # R7-M1: the Overview `_mixed` deck already carries the mixed
            # pair. Printing it again on the figure is the same sentence
            # twice. Section figures keep the pair (they have no deck).
            section["figure"]["state_line"] = None
    else:
        section["question"] = dict(L.OVERVIEW_QUESTIONS["movement"])
    table = L.STANCES.get("overview") or {}
    if key not in table:
        raise MacroCommandBuildError(f"unknown stance key overview/{key}")
    section["stance"] = {
        "text": dict(table[key]),
        "tone": "ok" if key.startswith("all_read") else "warn",
    }


def _restrict_header_to_populated(
        header: dict[str, Any],
        entries: Sequence[Mapping[str, Any]],
        panel_ids: set[str]) -> None:
    """R6-M3: chips and Read clauses only for rendered panels. No redirect."""
    chips = [
        chip for chip in (header.get("strip") or [])
        if chip.get("id") == "coverage" or chip.get("section") in panel_ids
    ]
    clauses = [
        clause for clause in ((header.get("read") or {}).get("clauses") or [])
        if clause.get("section") in panel_ids
    ]
    n = len(clauses)
    for index, clause in enumerate(clauses):
        if index == n - 1:
            punct_key = "last"
        elif index == n - 2:
            punct_key = "penultimate"
        else:
            punct_key = "mid"
        clause["punct"] = dict(L.READ_PUNCT[punct_key])
        clause["href_section"] = clause.get("section")
    for chip in chips:
        chip["href_section"] = chip.get("section")
    available, total = populated_section_coverage_tally(entries, panel_ids)
    coverage = macro_suite_view._coverage_chip(available, total)
    coverage["note"] = {
        "en": f"{available} of {total} sections have today's data",
        "zh": f"{total}个板块中有{available}个有今日数据",
    }
    coverage["href_section"] = coverage.get("section") or "overview"
    chips = [
        coverage if chip.get("id") == "coverage" else chip
        for chip in chips
    ]
    dated = [chip["as_of"] for chip in chips if chip.get("as_of")]
    read = header.setdefault("read", {})
    read["clauses"] = clauses
    read["omitted"] = len(clauses) < len(
        [chip for chip in chips if chip.get("id") != "coverage"])
    if dated:
        read["as_of"] = min(dated)
        read["as_of_display"] = L.date_display_pair(read["as_of"])
        read["as_of_meaning"] = macro_suite_view._as_of_meaning(
            len(dated), all_same=min(dated) == max(dated))
    header["strip"] = chips
    header["coverage"] = {"available": available, "total": total}


def _figure_block(rows: Sequence[Mapping[str, Any]], *, overview: bool,
                  shown: int, total: int) -> dict[str, Any]:
    """Mode-driven figure chrome (R7-M1). Not `any_current`-driven.

    movement → count_text, no state line.
    current  → same_publication state line, no count.
    mixed    → overview_mixed state line, no count. Overview then drops
    the state line in `_apply_overview_deck` so the mixed pair is spoken
    once (the deck already carries it).
    """
    mode = _figure_mode(rows)
    count = None
    state_line = None
    if mode == "movement":
        if overview:
            count = {
                "en": L.COUNT["overview"]["en"].format(shown=shown, total=total),
                "zh": L.COUNT["overview"]["zh"].format(shown=shown, total=total),
            }
        else:
            count = {
                "en": L.COUNT["section"]["en"].format(n=len(rows)),
                "zh": L.COUNT["section"]["zh"].format(n=len(rows)),
            }
    elif mode == "current":
        state_line = dict(L.COUNT["same_publication"])
    elif mode == "mixed":
        state_line = dict(L.COUNT["overview_mixed"])
    return {"rows": list(rows), "count_text": count, "state_line": state_line}


def _state_key(snapshot: Mapping[str, Any] | None) -> str:
    if not snapshot:
        return "unavailable"
    headline = snapshot.get("headline") or {}
    if headline.get("status") == "PRESENT" and headline.get("state_id"):
        return str(headline["state_id"])
    if headline.get("null_reason") == "NOT_APPLICABLE":
        return "unstated"
    return "unavailable"


def _stance_snapshot(section: Section,
                     by_id: Mapping[str, Mapping[str, Any]],
                     ) -> tuple[str | None, Mapping[str, Any] | None]:
    """D5: first sub-tab whose workspace publishes a state; else first tab."""
    if section.subtabs:
        for tab in section.subtabs:
            entry = by_id.get(tab.workspace_id) or {}
            snap = entry.get("snapshot")
            if snap and (snap.get("headline") or {}).get("status") == "PRESENT":
                return tab.workspace_id, snap
        first = section.subtabs[0]
        entry = by_id.get(first.workspace_id) or {}
        return first.workspace_id, entry.get("snapshot")
    if section.workspace_id:
        entry = by_id.get(section.workspace_id) or {}
        return section.workspace_id, entry.get("snapshot")
    return None, None


def _workspace_view(snapshot: Mapping[str, Any], *, workspace_id: str,
                    page_built_at: str) -> dict[str, Any]:
    artifact = {
        "path": f"macrodata/workspaces/{workspace_id}/US/latest.json",
        "manifest_path": "macrodata/workspaces/manifest.json",
        "sha256": None,
        "bytes": None,
        "min_client_contract": MIN_CLIENT_CONTRACT,
    }
    return macro_suite_view.build_view(
        snapshot, page_built_at=page_built_at, artifact=artifact,
        layout=_layout_for(workspace_id),
    )


def _input_note_from_view(view: Mapping[str, Any]) -> bool:
    for item in view.get("diagnostics") or []:
        title = item.get("title") or {}
        title_en = title.get("en") if isinstance(title, Mapping) else None
        if item.get("tone") in ("warn", "bad") and title_en in _SOURCE_NOTE_TITLES:
            return True
    return False


def _entitlement_plan(snapshot: Mapping[str, Any] | None, *,
                      allow_fixture_keys: bool = False) -> str | None:
    """Fixture-only plan name. Production snapshots never carry this key
    (contract additionalProperties:false). The production path ignores it
    unless ``--empty-state-fixture`` (or ``allow_fixture_keys``) is set."""
    if not allow_fixture_keys or not snapshot:
        return None
    raw = snapshot.get("entitlement")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    if isinstance(raw, Mapping) and raw.get("plan"):
        return str(raw["plan"]).strip() or None
    return None


def _command_tab_withheld(snapshot: Mapping[str, Any] | None,
                          view: Mapping[str, Any] | None,
                          tab_id: str, *,
                          allow_fixture_keys: bool = False) -> bool:
    """E4: a Command sub-tab whose withheld list names it.

    Production ``view.withheld_tabs`` uses workspace-page ids (scenario /
    alerts). Those ids are unioned with the Command tab id so a future
    workspace that withholds a Command tab by the same token still fires
    E4 (disclosed: today's withheld ids do not collide). The
    contract-forbidden ``withheld_command_tabs`` snapshot key is read
    only when ``--empty-state-fixture`` / ``allow_fixture_keys`` is set.
    """
    named = {str(item.get("tab_id") or "")
             for item in ((view or {}).get("withheld_tabs") or [])}
    extra: set[str] = set()
    if allow_fixture_keys:
        extra = {str(item) for item in ((snapshot or {}).get("withheld_command_tabs") or [])}
    return bool(tab_id) and tab_id in (named | extra)


def _apply_empty_voice(empty: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """One null voice: the empty state's own title is the section stance."""
    if not empty:
        return None
    spec = L.EMPTY_STATES.get(str(empty.get("id") or ""))
    if not spec:
        return None
    return {"text": dict(spec["title"]), "tone": "neutral"}


def _figure_or_empty_for_workspace(snapshot: Mapping[str, Any] | None, *,
                                   view: Mapping[str, Any] | None,
                                   href: str | None,
                                   entitlement: str | None = None,
                                   ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if entitlement:
        return None, _empty_state("e6", plan=entitlement)
    if view and (view.get("context") or {}).get("state") in _E2_STATES:
        return None, _empty_state("e2")
    headline = (view or {}).get("headline") or {}
    changes = (view or {}).get("changes") or {}
    deltas = list(changes.get("deltas") or [])
    has_date = bool(headline.get("effective_date"))
    raw = (snapshot or {}).get("headline") or {}
    not_applicable = raw.get("null_reason") == "NOT_APPLICABLE"
    try:
        if "prior_is_earlier" in changes:
            prior_is_earlier = bool(changes.get("prior_is_earlier"))
        else:
            prior_is_earlier = macro_suite_view.prior_publication_is_earlier(
                changes.get("prior_effective_date"),
                headline.get("effective_date") or raw.get("effective_date"),
            )
    except Exception:
        prior_is_earlier = False
    as_of = headline.get("effective_date") or raw.get("effective_date")
    as_of_month = L.month_display_pair(str(as_of)) if as_of else None
    rows = _move_rows_from_deltas(
        deltas, href=href, show_source=None,
        prior_is_earlier=prior_is_earlier, as_of_month=as_of_month)
    if not has_date and not rows and not not_applicable:
        return None, _empty_state("e1")
    if not rows:
        return None, _empty_state("e3")
    return _figure_block(rows, overview=False,
                         shown=len(rows), total=len(rows)), None


def _boundary_watching(section_id: str, snapshot: Mapping[str, Any] | None,
                       view: Mapping[str, Any] | None) -> list[dict[str, str]]:
    reviewed = [dict(item) for item in L.WATCHING[section_id]]
    if not view or not snapshot:
        return reviewed
    boundary = (view.get("headline") or {}).get("nearest_boundary") or {}
    if not boundary.get("distance_present"):
        return reviewed
    axis_id = ((snapshot.get("headline") or {}).get("nearest_boundary") or {}).get("axis")
    if axis_id:
        _require_metric(str(axis_id))
        axis_label = L.METRIC[str(axis_id)]
    else:
        axis_label = boundary.get("axis_label") or {"en": "", "zh": ""}
    distance = boundary.get("distance")
    line = {
        "en": L.BOUNDARY_LINE["en"].format(axis=axis_label["en"], distance=distance),
        "zh": L.BOUNDARY_LINE["zh"].format(axis=axis_label["zh"], distance=distance),
    }
    return [line, *reviewed]


def _macro_command_sections(entries: Sequence[Mapping[str, Any]], *,
                            page_built_at: str,
                            allow_empty_state_fixture: bool = False,
                            ) -> list[dict[str, Any]]:
    """Build the `sections` template context from the static SECTIONS constant.

    P3 populates question / stance / primer / caption / watching for the first
    five sections only; the seven P4 sections degrade to head + figure.
    Every optional field is an explicit falsy so StrictUndefined stays silent.
    """
    by_id = {entry["workspace_id"]: entry for entry in entries}
    title_by_workspace = {entry["workspace_id"]: entry["title"] for entry in entries}
    rail_ids = rail_workspace_ids()
    overview_links = [
        _detail_link(title_by_workspace, workspace_id,
                     (by_id.get(workspace_id) or {}).get("output")
                     or f"macro_{workspace_id}.html")
        for workspace_id in rail_ids
    ]

    hub = macro_suite_view.build_hub_view(entries, page_built_at=page_built_at)
    rail_index = {workspace_id: index for index, workspace_id in enumerate(rail_ids)}
    shown = list(hub["changes"]["entries"])
    shown.sort(key=lambda row: rail_index.get(row.get("workspace_id"), 999))
    overview_rows = []
    for row in shown:
        kind = row.get("kind") or "movement"
        overview_rows.append({
            "kind": kind,
            "name": dict(row["label"]) if row.get("label") else {"en": "", "zh": ""},
            "source": dict(row["workspace_title"]) if row.get("workspace_title") else None,
            "href": row.get("href"),
            "prior": (row.get("prior") or L.EM_DASH) if kind == "movement" else None,
            "current": row.get("current") or L.EM_DASH,
            "delta": (row.get("delta") or L.EM_DASH) if kind == "movement" else None,
            "sign": (row.get("sign") or "unavailable") if kind == "movement" else None,
            "as_of_month": dict(row["as_of_month"]) if row.get("as_of_month") else None,
            "metric_id": row.get("metric_id"),
        })

    sections: list[dict[str, Any]] = []
    for section in SECTIONS:
        is_overview = section.id == "overview"
        has_copy = section.id in P3_COPY_IDS
        subtabs: list[dict[str, Any]] | None = None
        detail_links: list[dict[str, Any]]
        if section.subtabs:
            detail_links = [_detail_link(title_by_workspace, tab.workspace_id, tab.deep_href)
                            for tab in section.subtabs]
        elif is_overview:
            detail_links = overview_links
        else:
            detail_links = [_detail_link(title_by_workspace, section.workspace_id, section.deep_href)]

        snap = None
        stance = None
        primer = None
        caption = None
        watching = None
        input_note = False
        state_label = None
        as_of = None
        as_of_display = None
        figure = None
        empty = None
        tone = None
        question = ({"en": section.question_en, "zh": section.question_zh}
                    if section.question_en else None)

        if is_overview:
            if overview_rows:
                figure = _figure_block(
                    overview_rows, overview=True,
                    shown=hub["changes"]["shown"],
                    total=hub["changes"]["total"],
                )
            else:
                empty = _empty_state("e3")
            # Stance / question are applied after the populated filter so
            # the coverage tally and the figure mode share one count
            # (R6-M1 / R6-M2). Placeholder copy keeps has_copy slots live.
            table = L.STANCES.get("overview") or {}
            if has_copy:
                stance = {
                    "text": dict(table["some_unread"]),
                    "tone": "warn",
                }
                primer = dict(hub["deck"])
                caption = dict(L.CAPTIONS["overview"])
                watching = _boundary_watching("overview", None, None)
        else:
            workspace_id, snap = _stance_snapshot(section, by_id)
            view = (_workspace_view(snap, workspace_id=workspace_id,
                                    page_built_at=page_built_at)
                    if snap and workspace_id else None)
            if has_copy:
                key = _state_key(snap)
                table = L.STANCES.get(section.id) or {}
                if key not in table:
                    raise MacroCommandBuildError(
                        f"unknown stance key {section.id}/{key}")
                if key in ("unstated", "unavailable"):
                    tone = "neutral"
                elif workspace_id and key in (L.STATE_TONE.get(workspace_id) or {}):
                    tone = L.STATE_TONE[workspace_id][key]
                else:
                    tone = "neutral"
                stance = {"text": dict(table[key]), "tone": tone}
                primer = dict(L.PRIMERS[section.id])
                caption = dict(L.CAPTIONS[section.id])
                watching = _boundary_watching(section.id, snap, view)
            if view and has_copy:
                input_note = _input_note_from_view(view)
                headline = view.get("headline") or {}
                state_label = headline.get("state_label")
                as_of = headline.get("effective_date")
                as_of_display = L.date_display_pair(as_of) if as_of else None

            if section.subtabs:
                subtabs = []
                notes = [input_note]
                for index, tab in enumerate(section.subtabs):
                    tab_entry = by_id.get(tab.workspace_id) or {}
                    tab_snap = tab_entry.get("snapshot")
                    tab_view = (_workspace_view(tab_snap, workspace_id=tab.workspace_id,
                                                page_built_at=page_built_at)
                                if tab_snap else None)
                    tab_figure = tab_empty = None
                    if has_copy:
                        if _command_tab_withheld(
                                tab_snap, tab_view, tab.id,
                                allow_fixture_keys=allow_empty_state_fixture):
                            tab_figure, tab_empty = None, _empty_state("e4")
                        else:
                            tab_figure, tab_empty = _figure_or_empty_for_workspace(
                                tab_snap, view=tab_view, href=tab.deep_href,
                                entitlement=_entitlement_plan(
                                    tab_snap,
                                    allow_fixture_keys=allow_empty_state_fixture))
                    if tab_view:
                        notes.append(_input_note_from_view(tab_view))
                    subtabs.append({
                        "id": tab.id,
                        "label": {"en": tab.label_en, "zh": tab.label_zh},
                        "first": index == 0,
                        "deep_href": tab.deep_href,
                        "figure": tab_figure,
                        "empty": tab_empty,
                    })
                input_note = any(notes) if has_copy else False
            elif has_copy:
                figure, empty = _figure_or_empty_for_workspace(
                    snap, view=view, href=section.deep_href,
                    entitlement=_entitlement_plan(
                        snap, allow_fixture_keys=allow_empty_state_fixture))

        # M2: one null voice for every empty slot, not only E2. A figure
        # with no rows drops the "each row shows…" caption; a section-level
        # empty replaces the stance with that state's own title.
        slot_empty = empty
        if subtabs:
            slot_empty = empty or next(
                (tab.get("empty") for tab in subtabs if tab.get("empty")), None)
        if has_copy and slot_empty:
            caption = None
        # I4: current-only rows already carry the typed state line. The
        # "before and after / last two readings" caption would be a lie.
        figure_rows = list((figure or {}).get("rows") or [])
        if subtabs:
            for tab in subtabs:
                figure_rows.extend((tab.get("figure") or {}).get("rows") or [])
        if has_copy and any(row.get("kind") == "current" for row in figure_rows):
            caption = None
        if has_copy and empty:
            voiced = _apply_empty_voice(empty)
            if voiced:
                stance = voiced

        empty_e5 = None if is_overview else _empty_state(
            "e5", cta_href=section.deep_href or (
                section.subtabs[0].deep_href if section.subtabs else "#overview"))

        sections.append({
            "id": section.id,
            "label": {"en": section.label_en, "zh": section.label_zh},
            "first": is_overview,
            "tone": (stance or {}).get("tone") if stance else None,
            "question": question,
            "stance": stance,
            "primer": primer,
            "primer_open": section.id in P3_PRIMER_OPEN,
            "caption": caption,
            "watching": watching,
            "input_note": input_note,
            "state_label": state_label,
            "as_of": as_of,
            "as_of_display": as_of_display,
            "figure": figure,
            "empty": empty,
            "empty_e5": empty_e5,
            "entitlement": (
                _entitlement_plan(snap, allow_fixture_keys=allow_empty_state_fixture)
                if not is_overview else None
            ),
            "dests_title": (
                {
                    "en": f"Where to go next — {len(overview_links)} destination pages",
                    "zh": f"接下来去哪里——{len(overview_links)} 个目标页面",
                } if is_overview else None
            ),
            "deep_href": section.deep_href,
            "subtabs": subtabs,
            "detail_links": detail_links,
        })
    # N5-M2: P3 ships only populated panels. The P4 seven stay in SECTIONS
    # (rail-order / dests / coverage) but do not render as empty shells.
    populated = [section for section in sections if _panel_is_populated(section)]
    count = len(populated)
    panel_ids = {section["id"] for section in populated}
    available, total = populated_section_coverage_tally(entries, panel_ids)
    for section in populated:
        if section.get("first"):
            section["primer"] = macro_suite_view._deck_copy(count)
            _apply_overview_deck(section, available=available, total=total)
    return populated


def write_fragments(env: Environment, sections: Sequence[Mapping[str, Any]],
                    out_dir: Path) -> list[Path]:
    """Emit `site/macro/fragments/<id>.html` — the inner HTML of `[data-mc-figure]`."""
    dest = Path(out_dir) / "macro" / "fragments"
    dest.mkdir(parents=True, exist_ok=True)
    tmpl = env.get_template("_macro_command_fragment.html.j2")
    written: list[Path] = []
    keep: set[str] = set()
    for section in sections:
        if section.get("first"):
            continue
        html = tmpl.render(s=section)
        html = "\n".join(line.rstrip() for line in html.splitlines()) + "\n"
        path = dest / f"{section['id']}.html"
        temp = _temp_sibling(path)
        try:
            temp.write_text(html, encoding="utf-8")
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)
        written.append(path)
        keep.add(path.name)
    for stale in dest.glob("*.html"):
        if stale.name not in keep:
            stale.unlink()
    return written


def _macro_command_analyst(root: Path) -> dict[str, Any]:
    """`analyst.mountable` (§8, R8): true when the sitewide brain widget's
    launcher stub is baked into theme.js at build time. Degraded fallback
    (bare `<a href="chat.html">`, §8) only when it is genuinely absent."""
    try:
        theme_js = (root / "templates" / "theme.js").read_text(encoding="utf-8")
    except OSError:
        return {"mountable": False}
    return {"mountable": "mmb-boot" in theme_js}



_MONTH_ABBR_EN = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


def _plain_as_of_display(iso_date: str) -> dict[str, str] | None:
    """Human dates for the hub eyebrow — never a raw ISO string (Front-End
    Clarity Law / Opus review PR #6930 M1). EN is ``1 Jul 2026``; ZH is
    ``2026年7月1日``. Returns None when the string is not a YYYY-MM-DD."""
    try:
        parsed = datetime.strptime(iso_date[:10], "%Y-%m-%d")
    except (TypeError, ValueError):
        return None
    return {
        "en": f"{parsed.day} {_MONTH_ABBR_EN[parsed.month - 1]} {parsed.year}",
        "zh": f"{parsed.year}年{parsed.month}月{parsed.day}日",
    }


def build_hub(entries: Sequence[Mapping[str, Any]], *, out_dir: Path,
              env: Environment, root: Path, page_built_at: str,
              allow_empty_state_fixture: bool = False) -> Path:
    """Render the suite hub from what the fourteen pages just read.

    The hub reads NO artifact of its own. Every row is the snapshot (or the typed
    refusal) that the workspace page beside it was built from, so the hub and the
    page it links to cannot disagree about state, date or coverage. A workspace
    the builder could not read arrives here as a refusal, and the hub says so.

    Macro Command (F01 Macro Command P1) supersedes the hub's prior markup
    entirely (frozen spec §2.7): `sections`, `analyst`, `read` and `strip` are
    the new page's context. P2 wires `read` and `strip` to the real
    seven-workspace pass-through from `macro_suite_view.build_command_header`
    — every clause and chip is a verbatim single-workspace reading, never a
    fused or scored composite (G3). The hub does not reprint `page_built_at`
    (Opus review PR #6930 m2); the stamp is only an input to the coverage
    tally's "today" cut.
    """
    header = macro_suite_view.build_command_header(entries, page_built_at=page_built_at)
    sections = _macro_command_sections(
        entries, page_built_at=page_built_at,
        allow_empty_state_fixture=allow_empty_state_fixture)
    _restrict_header_to_populated(
        header, entries, {section["id"] for section in sections})
    fragment_paths = write_fragments(env, sections, out_dir)
    html = env.get_template(HUB_PAGE.template).render(
        page_title="Macro & Monetary",
        page_seo_title=HUB_PAGE.seo_title,
        page_seo_desc=HUB_PAGE.seo_desc,
        page_seo_path=HUB_PAGE.output,
        active_section="research",
        active_page=Path(HUB_PAGE.output).stem,
        suite_nav=suite_nav(HUB_PAGE.output),
        sections=sections,
        analyst=_macro_command_analyst(root),
        read=header["read"],
        strip=header["strip"],
        fragments_ready=bool(fragment_paths),
    )
    html = "\n".join(line.rstrip() for line in html.splitlines()) + "\n"

    from lib.pages import write_page  # noqa: PLC0415

    out_dir.mkdir(parents=True, exist_ok=True)
    destination = out_dir / HUB_PAGE.output
    temp = _temp_sibling(destination)
    try:
        write_page(temp, html)
        os.replace(temp, destination)
    finally:
        temp.unlink(missing_ok=True)
    return destination


def _apply_empty_state_fixture(entries: list[Mapping[str, Any]],
                               fixture: Mapping[str, Any]) -> None:
    """Mutate in-memory entries from a capture-only sidecar. Never a snapshot."""
    workspace_id = fixture.get("workspace_id")
    if not workspace_id:
        return
    for entry in entries:
        if entry.get("workspace_id") != workspace_id:
            continue
        snap = entry.get("snapshot")
        if not isinstance(snap, dict):
            continue
        empty_id = str(fixture.get("empty_id") or "")
        if empty_id == "e4" or fixture.get("withheld_command_tabs"):
            tabs = fixture.get("withheld_command_tabs") or [fixture.get("subtab")]
            snap["withheld_command_tabs"] = [str(tab) for tab in tabs if tab]
        if empty_id == "e6" or fixture.get("entitlement"):
            plan = fixture.get("entitlement") or "Research"
            snap["entitlement"] = str(plan)


def render(root: Path | str = _REPO_ROOT, *, data_root: Path | str | None = None,
           out_dir: Path | str | None = None, page_built_at: str | None = None,
           empty_state_fixture: Path | str | None = None) -> list[Path]:
    """Render every registered suite page plus the shared assets."""
    root = Path(root).resolve()
    site = Path(out_dir) if out_dir else root / "site"
    site.mkdir(parents=True, exist_ok=True)
    data = Path(data_root) if data_root else root / "site" / "macrodata"
    stamp = page_built_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    env = _environment(root)
    fixture_doc: Mapping[str, Any] | None = None
    if empty_state_fixture:
        fixture_path = Path(empty_state_fixture)
        fixture_doc = json.loads(fixture_path.read_text(encoding="utf-8"))

    written: list[Path] = []
    entries: list[Mapping[str, Any]] = []
    for page in SUITE_PAGES:
        path, _ok, entry = build_page(root, page, data_root=data, out_dir=site, env=env,
                                      page_built_at=stamp)
        written.append(path)
        entries.append(entry)
    if fixture_doc:
        _apply_empty_state_fixture(entries, fixture_doc)
    written.append(build_hub(entries, out_dir=site, env=env, root=root,
                            page_built_at=stamp,
                            allow_empty_state_fixture=bool(fixture_doc)))
    for asset in SHARED_ASSETS:
        _atomic_copy(root / "templates" / asset, site / asset)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=_REPO_ROOT)
    parser.add_argument("--data-root", type=Path, default=None,
                        help="macrodata root holding workspaces/ (default: <root>/site/macrodata)")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="output directory (default: <root>/site)")
    parser.add_argument(
        "--empty-state-fixture", type=Path, default=None,
        help="Capture-only sidecar JSON. Production builds omit this flag and "
             "ignore contract-forbidden snapshot keys (entitlement, "
             "withheld_command_tabs).")
    args = parser.parse_args(argv)
    try:
        pages = render(args.root, data_root=args.data_root, out_dir=args.out_dir,
                       empty_state_fixture=args.empty_state_fixture)
    except Exception as exc:  # noqa: BLE001 — a precise non-zero helps the shared render lane
        print(f"::error title=macro_suite_pages::build failed ({type(exc).__name__}: {exc})", flush=True)
        return 1
    for page in pages:
        print(f"wrote {page}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
