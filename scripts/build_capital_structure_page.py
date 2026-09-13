"""Render the Capital Structure observed-filing-state desk.

The browser receives its issuer rows and filing evidence only through the
authenticated Capital Structure API. This builder deliberately writes no data
projection of its own and still copies only `_ASSETS`. Two read-only
exceptions, both display-only (no score/rank/direction):

- B-F09-4: it reads the nightly-written `premium_featured.json` receipt so the
  desk can show one classified deal's dated premium. That receipt is
  server-rendered into the anonymously-fetchable HTML shell specifically
  because the page's live API is paid-gated (`site_full` —
  app/capital_structure.py:53), so an API-delivered premium could never be
  anonymously verified.
- B-F09-6 (MO-PAID-067): a read-only Policy watch chip that cites a single
  dated policy_calendar step.

Usage:
    python -m scripts.build_capital_structure_page
    python -m scripts.build_capital_structure_page --root /path/to/repo
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined


_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))
_ASSETS = ("capital_structure_boot.js", "capital_structure.css", "capital_structure.js")
_PREMIUM_RECEIPT = ("data", "special_situations", "premium_featured.json")


def _featured_premium(root: Path) -> dict | None:
    """Read the nightly premium receipt. Returns None when the receipt is absent,
    unreadable, or not the expected schema — the shell then prints its plain-word null."""
    path = root.joinpath(*_PREMIUM_RECEIPT)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict) or payload.get("schema") != "special_situations.premium.v1":
        return None
    return payload


# ── policy-watch:start (B-F09-6, MO-PAID-067) ──
# Round-2 review BLOCKER 1/2: the prior constant named two basket ids
# ("capital_markets", "capital_formation") that DO NOT EXIST anywhere in this
# pipeline's basket taxonomy — engine/federal_register* ingests documents into
# a frozen set of 17 industry-sector baskets (ai_semiconductors, solar, ...),
# none of them a capital-markets/financial-regulation theme, so the chip could
# never reach `present` and its `empty` copy asserted active watching that was
# never happening (an UNKNOWN shaped as an EMPTY).
#
# Measured against the live artifact this build reads
# (data/federal_register/documents.parquet, 2026-09-06, 33,696 rows / 17
# baskets / 74 agency_slug values): the one real basket that actually carries
# SEC / Treasury / FinCEN / OCC / FDIC filings is `fintech_payments` (349 rows;
# 246 treasury-department, 83 consumer-financial-protection-bureau, 3
# securities-and-exchange-commission, 2 financial-crimes-enforcement-network,
# 2 comptroller-of-the-currency, 1 federal-deposit-insurance-corporation).
# `federal-reserve-system` and any `commodity-futures-trading-commission`-like
# agency are NOT present under this basket (Fed appears once, under an
# unrelated basket; CFTC does not appear anywhere in the 74-agency taxonomy at
# all) — so "Fed" and "CFTC" were dropped from the chip's own copy below
# rather than left as an unbacked claim.
FINTECH_PAYMENTS_THEME = ("fintech_payments",)  # first (only) match wins


def _policy_watch(today=None) -> dict:
    """Cite ONE dated policy step for this desk. No score, no rank, no direction.

    Reuses engine.policy_calendar.compute_policy_calendar + format_policy_reg_chip
    (the one existing formatter) — never a second formatter, never a new signal.
    Three states, all rendered (nulls printed, UNKNOWN != EMPTY):
      unavailable — documents.parquet absent for this build
      empty       — calendar present, no dated step under the fintech_payments
                    basket (the real basket this pipeline files SEC/Treasury/
                    FinCEN/OCC/FDIC actions under)
      present     — a dated step, expressed only through typed chip fields
    """
    unavailable = {
        "state": "unavailable",
        "headline_en": "Policy calendar not in this build",
        "headline_zh": "本次构建未包含政策日历",
        "detail_en": "Nothing is hidden — the source record was not present when this page was built.",
        "detail_zh": "没有隐藏内容——本页构建时未取到来源记录。",
    }
    empty = {
        "state": "empty",
        "headline_en": "No dated policy step ahead",
        "headline_zh": "前方没有已定日期的政策节点",
        "detail_en": "We watch SEC, Treasury, FinCEN and bank-regulator rule dates. None is pending.",
        "detail_zh": "我们关注 SEC、财政部、FinCEN 与银行监管机构的规则日期，目前没有待办节点。",
    }
    try:
        from engine.policy_calendar import compute_policy_calendar, format_policy_reg_chip
    except Exception:  # noqa: BLE001 — a chip must never crash the desk build
        return unavailable

    try:
        cal = compute_policy_calendar(today=today)
    except Exception:  # noqa: BLE001
        return unavailable
    if cal is None:
        return unavailable

    themes = cal.get("themes") or {}
    theme_key = None
    row = None
    for key in FINTECH_PAYMENTS_THEME:
        if key in themes:
            theme_key = key
            row = themes[key]
            break

    if row is None:
        # No fintech_payments row in this build's data (e.g. a stub/fixture
        # parquet with no rows for that basket at all). Note (DEVIATION from
        # the frozen spec's agency_slug fallback): upcoming_events rows do not
        # carry agency_slug (only basket_id/reg_stage/title/date) — filtering by
        # agency there is not possible without fabricating a field, so the
        # fallback checks the same FINTECH_PAYMENTS_THEME basket id instead.
        upcoming = [e for e in (cal.get("upcoming_events") or [])
                    if e.get("basket_id") in FINTECH_PAYMENTS_THEME]
        if not upcoming:
            return empty
        theme_key = upcoming[0]["basket_id"]
        row = themes.get(theme_key) or {}

    try:
        chip = format_policy_reg_chip(row, theme_key)
    except Exception:  # noqa: BLE001
        return empty
    if chip is None:
        return empty

    dtcc = chip.get("days_to_comment_close")
    dtrf = chip.get("days_to_rule_effective")
    pr60 = chip.get("prorule_inflow_60d") or 0
    fr60 = chip.get("rule_finalization_60d") or 0

    if dtcc is not None:
        d = int(dtcc)
        if d <= 0:
            headline_en, headline_zh = "Comment window closes today", "征询意见期今天截止"
        elif d == 1:
            headline_en, headline_zh = "Comment window closes in 1 day", "征询意见期 1 天后截止"
        else:
            headline_en = f"Comment window closes in {d} days"
            headline_zh = f"征询意见期 {d} 天后截止"
    elif dtrf is not None:
        d = int(dtrf)
        headline_en = f"A final rule takes effect in {d} days"
        headline_zh = f"最终规则 {d} 天后生效"
    else:
        n = pr60 + fr60
        headline_en = f"{n} new rule steps in the last 60 days"
        headline_zh = f"过去 60 天有 {n} 项新规则动作"

    return {
        "state": "present",
        "headline_en": headline_en,
        "headline_zh": headline_zh,
        "detail_en": "Dated steps already on the public record. Not a rating and not a trade call.",
        "detail_zh": "均为已进入公开记录的既定日期节点。不是评级，也不是交易建议。",
    }
# ── policy-watch:end ──


# ── policy-projection:start (B-F09-6b, MO-PAID-067) ──
ARTIFACT_BUDGET_BYTES = 32_768


def _policy_projection(today=None) -> dict:
    """Dated-event ledger onto six frozen capital-markets windows. Context only.

    Strictly additive beside the merged Policy watch chip. `typed_unavailable`
    is resolved BEFORE the guarded import, so the fallback is reachable: a
    missing or raising `project` degrades to the typed unavailable shape
    instead of raising a second ImportError out of the handler. A leaf module
    that cannot be imported at all still fails the build loudly — that is a
    broken checkout, not a source that was unavailable for this build, and it
    must not be reported to a reader as the latter.
    """
    from engine.capital_policy_projection import typed_unavailable

    try:
        from engine.capital_policy_projection import project
        return project(today=today)
    except Exception:  # noqa: BLE001 — a section must never crash the desk
        return typed_unavailable(today=today)
# ── policy-projection:end ──


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


def _write_projection_artifact(root: Path, payload: dict) -> Path:
    """Serialize the projection atomically under site/data/."""
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    encoded = text.encode("utf-8")
    if len(encoded) > ARTIFACT_BUDGET_BYTES:
        raise RuntimeError(
            f"artifact over budget: {len(encoded)} > {ARTIFACT_BUDGET_BYTES}"
        )
    dest = root / "site" / "data" / "capital_policy_projection.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = _temp_sibling(dest)
    try:
        temp.write_bytes(encoded)
        os.replace(temp, dest)
    finally:
        temp.unlink(missing_ok=True)
    return dest


def _section_html(html: str) -> str:
    start = html.index('id="cs-policy-projection"')
    end = html.index("</section>", start)
    # The opening <section for THIS id is the one whose id attribute matches.
    # Earlier rindex("<section", 0, start) returns the `<section` opening the
    # PRECEDING section (e.g. policy-watch) when an intervening section is
    # inserted (B-F09-13 covenant headroom), which double-counts that section
    # and blows the budget. Walk forward from the previous </section> instead.
    prev_close = html.rfind("</section>", 0, start)
    section_open = html.index("<section", prev_close)
    return html[section_open:end + len("</section>")]


def _fence_section_budget(html: str) -> None:
    from engine.capital_policy_projection import SECTION_BUDGET_BYTES
    n = len(_section_html(html).encode("utf-8"))
    if n > SECTION_BUDGET_BYTES:
        raise RuntimeError(
            f"policy-projection section over budget: {n} > {SECTION_BUDGET_BYTES}"
        )


# ── covenant-headroom:start (B-F09-13, MO-PAID-062 slice 2) ──
# Display-only covenant headroom view-model for the one extracted issuer
# with at least one direct covenant-term observation. Pure engine, zero
# authority — see engine/covenant_headroom.py for the closed-set defenses.
# Builder reads:
#   data/capital_structure/covenant_term_observations.parquet  (the producer)
#   data/edgar/statements.parquet                              (the inputs)
#   data/edgar/ticker_cik_ledger.json                          (ticker→CIK)
#   data/capital_structure/health.json                         (outage flag)
#   data/capital_structure/source_manifest.jsonl               (cik-by-manifest)
# Any read failure fails closed to a typed no_terms_extracted payload —
# the page then renders the plain-word null copy.
def _covenant_headroom(root: Path) -> dict:
    """Materialize the headroom payload for the desk. Never raises."""
    from engine import covenant_headroom as headroom_engine  # noqa: PLC0415

    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    # 1) Observations parquet — empty list on any failure.
    try:
        import pandas as _pd  # noqa: PLC0415
        obs_df = _pd.read_parquet(
            root / "data" / "capital_structure" / "covenant_term_observations.parquet"
        )
        observations: list[dict] = []
        if len(obs_df):
            for _, row in obs_df.iterrows():
                try:
                    payload = json.loads(row["observation_json"])
                except (TypeError, ValueError):
                    continue
                if isinstance(payload, dict):
                    payload.setdefault("source_manifest_id", row.get("source_manifest_id"))
                    payload.setdefault("issuer_id", row.get("issuer_id"))
                    payload.setdefault("observation_id", row.get("observation_id"))
                    payload.setdefault("term_name", row.get("term_name"))
                    payload.setdefault("logical_observation_id", row.get("logical_observation_id"))
                    payload.setdefault("state", row.get("state"))
                    payload.setdefault("correction_version", row.get("correction_version", 1))
                    observations.append(payload)
    except Exception:  # noqa: BLE001 — a chip must never crash the desk build
        observations = []

    # 2) Statements parquet — empty map on any failure.
    fundamentals_by_cik: dict[str, dict] = {}
    try:
        import pandas as _pd  # noqa: PLC0415
        st_df = _pd.read_parquet(root / "data" / "edgar" / "statements.parquet")
        # Pull the ticker→CIK ledger to join statements.ticker → CIK.
        try:
            ledger = json.loads(
                (root / "data" / "edgar" / "ticker_cik_ledger.json").read_text(encoding="utf-8")
            )
            ticker_to_cik = dict(ledger.get("tickers") or {})
        except (OSError, ValueError):
            ticker_to_cik = {}
        for _, st_row in st_df.iterrows():
            ticker = st_row.get("ticker")
            if not isinstance(ticker, str) or not ticker:
                continue
            cik_int = ticker_to_cik.get(ticker)
            if cik_int is None:
                continue
            cik = f"{int(cik_int):010d}"
            fundamentals_by_cik.setdefault(cik, {
                "cik": cik,
                "operating_income": _maybe_float(st_row.get("op_income")),
                "depreciation": _maybe_float(st_row.get("depreciation")),
                "interest_expense": _maybe_float(st_row.get("interest_exp")),
                "cash_and_equivalents": _maybe_float(st_row.get("cash")),
                "debt_long_term": _maybe_float(st_row.get("debt_lt")),
                "debt_current": _maybe_float(st_row.get("debt_cur")),
                "period_end": _maybe_str(st_row.get("period_end")),
            })
    except Exception:  # noqa: BLE001
        fundamentals_by_cik = {}

    # 3) cik_to_ticker (reverse of the same ledger)
    cik_to_ticker: dict[str, str] = {}
    try:
        ledger = json.loads(
            (root / "data" / "edgar" / "ticker_cik_ledger.json").read_text(encoding="utf-8")
        )
        for ticker, cik_int in (ledger.get("tickers") or {}).items():
            cik_to_ticker[f"{int(cik_int):010d}"] = ticker
    except (OSError, ValueError):
        cik_to_ticker = {}

    # 4) source_manifest.jsonl — for the cik_by_source_manifest_id fallback.
    cik_by_source_manifest_id: dict[str, str] = {}
    try:
        with (root / "data" / "capital_structure" / "source_manifest.jsonl").open(
            encoding="utf-8"
        ) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                mid = rec.get("manifest_id")
                issuer = rec.get("issuer") or {}
                cik = issuer.get("cik")
                if isinstance(mid, str) and cik is not None:
                    cik_by_source_manifest_id[mid] = f"{int(cik):010d}"
    except OSError:
        cik_by_source_manifest_id = {}

    # 5) Health (optional)
    health = None
    try:
        h = json.loads(
            (root / "data" / "capital_structure" / "health.json").read_text(encoding="utf-8")
        )
        health = h if isinstance(h, dict) else None
    except (OSError, ValueError):
        health = None

    try:
        return headroom_engine.compute_headroom(
            observations,
            fundamentals_by_cik,
            cik_to_ticker,
            health=health,
            generated_at=now_iso,
            cik_by_source_manifest_id=cik_by_source_manifest_id,
        )
    except Exception:  # noqa: BLE001 — closed refusal, never raise from a builder
        return headroom_engine.compute_headroom(
            [], {}, {},
            generated_at=now_iso,
        )


def _maybe_float(v):
    if v is None:
        return None
    try:
        import math as _math
        f = float(v)
        if _math.isnan(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _maybe_str(v):
    if v is None:
        return None
    s = str(v).strip()
    return s or None


# ── covenant-headroom:end ──


def render(root: Path) -> Path:
    """Write a data-free desk shell plus exact CSS/JS companions."""
    root = root.resolve()
    site = root / "site"
    site.mkdir(parents=True, exist_ok=True)
    env = Environment(
        loader=FileSystemLoader(str(root / "templates")),
        autoescape=True,
        undefined=StrictUndefined,
    )
    import engine.policy_calendar as _pc
    _orig_cal = _pc.compute_policy_calendar
    _cal_once: dict = {"used": False, "value": None, "day": None}

    def _compute_once(df=None, today=None):
        """One policy-calendar result per build, for exactly one day.

        The stored value is keyed on nothing, so a later caller asking for a
        different day would have been handed the first call's answer without
        being told. It is now told, loudly. The day is resolved the way the
        callee resolves it (`None` means today), because the section leaf
        passes a concrete date where the chip passes `None` — both mean the
        same day, and only a genuinely different day is an error.
        """
        if df is not None:
            return _orig_cal(df=df, today=today)
        day = today if today is not None else date.today()
        if not _cal_once["used"]:
            _cal_once["used"] = True
            _cal_once["day"] = day
            _cal_once["value"] = _orig_cal(today=today)
        elif day != _cal_once["day"]:
            raise RuntimeError(
                "policy calendar: this build computes one day only; it was "
                f"computed for {_cal_once['day']} and cannot answer for {day}"
            )
        return _cal_once["value"]

    _pc.compute_policy_calendar = _compute_once
    # One wall-clock read for the whole page. `_cal_once["day"]` is not
    # relied on: it stays None when the parquet is absent or `_policy_watch`
    # is stubbed, and a clock that advances between the two callees would
    # otherwise split the chip and the section across midnight.
    day = date.today()
    try:
        watch = _policy_watch(today=day)
        payload = _policy_projection(today=day)
    finally:
        _pc.compute_policy_calendar = _orig_cal
    html = env.get_template("capital_structure.html.j2").render(
        active_section="research",
        active_page="capital_structure",
        premium=_featured_premium(root),
        policy_watch=watch,
        policy_projection=payload,
        covenant_headroom=_covenant_headroom(root),
    )
    # Shared navigation templates intentionally contain indentation around
    # conditional blocks. Normalize generated-only blank-line whitespace so the
    # committed shell remains diff-clean without modifying global nav output.
    html = "\n".join(line.rstrip() for line in html.splitlines()) + "\n"
    if payload and 'id="cs-policy-projection"' in html:
        _fence_section_budget(html)
    # The artifact is written only once the section is known to be within
    # budget, so an over-budget build cannot leave a refreshed JSON beside a
    # page that was withheld. A build with no payload leaves the last good
    # artifact in place rather than overwriting it with `null`.
    if payload is not None:
        _write_projection_artifact(root, payload)

    # write_page owns the depth-aware data-base shim. Use its result through a
    # temporary file so even a standalone builder cannot expose a partial page.
    from lib.pages import write_page  # noqa: PLC0415

    page = site / "capital_structure.html"
    temp = _temp_sibling(page)
    try:
        write_page(temp, html)
        os.replace(temp, page)
    finally:
        temp.unlink(missing_ok=True)
    for asset in _ASSETS:
        _atomic_copy(root / "templates" / asset, site / asset)
    return page


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=_REPO_ROOT)
    args = parser.parse_args(argv)
    try:
        page = render(args.root)
    except Exception as exc:  # noqa: BLE001 — precise non-zero helps shared render diagnose a missing desk asset
        print(f"::error title=capital_structure_page::build failed ({type(exc).__name__}: {exc})", flush=True)
        return 1
    print(f"wrote {page}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
