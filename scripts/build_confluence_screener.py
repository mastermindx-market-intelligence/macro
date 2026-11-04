"""scripts.build_confluence_screener — render the signal-stack screener + paid payload + card.

Reads site/factordata/tech_confluence.json.
Writes:
  - site/confluence_screener.html (public preview shell)
  - site/premiumdata/confluence_screener.json (server-protected paid rows)
  - site/og/confluence_screener.png

Usage:
    python -m scripts.build_confluence_screener
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# CTA URL
# ─────────────────────────────────────────────────────────────────────────────

PAYLOAD_DIR = "premiumdata"
PAYLOAD_NAME = "confluence_screener.json"
PAYLOAD_URL = f"/{PAYLOAD_DIR}/{PAYLOAD_NAME}"


def _cta_url() -> str:
    # Tagged trial CTA via the D07 Funnel link builder (#3052); untagged fallback
    # keeps the page fail-soft if links.py is ever absent.
    try:
        from engine.marketing.links import canonical_link

        return canonical_link(
            "free_tools", "confluence_screener", "cta",
            base_url="https://app.mastermind-x.com/", utm_source="site",
        )
    except Exception:
        return "https://app.mastermind-x.com/"


# ─────────────────────────────────────────────────────────────────────────────
# build_context — pure function, testable
# ─────────────────────────────────────────────────────────────────────────────

_TICKER = re.compile(r"^[A-Za-z0-9._^=-]{1,20}$")


def _finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _source_receipt(raw: object) -> dict | None:
    """Qualify the reader's input and bind both projections to one artifact.

    The opaque digest is a consistency receipt, never an entitlement or a market
    observation clock. Reject malformed coverage instead of calling it zero.
    """
    if not isinstance(raw, dict):
        return None
    try:
        built = raw["generated_utc"]
        if not isinstance(built, str) or datetime.fromisoformat(built.replace("Z", "+00:00")).tzinfo is None:
            return None
        if type(raw["universe_n"]) is not int or raw["universe_n"] < 0:
            return None
        datetime.strptime(raw["split_date"], "%Y-%m-%d")
        legs = raw["legs"]
        longs = raw["combos"]["long"]
        if not isinstance(legs, list) or not isinstance(longs, list):
            return None
        if any(not isinstance(leg, dict) or leg.get("tf") not in ("D", "W") or
               not isinstance(leg.get("display_en"), str) or
               not isinstance(leg.get("display_zh"), str) for leg in legs):
            return None
        ids: set[str] = set()
        for combo in longs:
            if not isinstance(combo, dict):
                return None
            key, active, indices = combo.get("id"), combo.get("active_now"), combo.get("legs")
            if not isinstance(key, str) or not key or key in ids:
                return None
            ids.add(key)
            if not isinstance(active, list) or any(not isinstance(t, str) or not _TICKER.fullmatch(t) for t in active):
                return None
            if len(set(active)) != len(active):
                return None
            if not isinstance(indices, list) or any(type(i) is not int or not 0 <= i < len(legs) for i in indices):
                return None
            h21 = combo.get("h21")
            if h21 is None:
                h21 = {}
            if not isinstance(h21, dict) or not _finite_number(combo.get("rank_score", 0)):
                return None
            for half in ("test", "train"):
                rate = h21.get("wr_mc_" + half)
                if rate is not None and (not _finite_number(rate) or not 0 <= rate <= 1):
                    return None
            if active and all(h21.get("wr_mc_" + half) is not None for half in ("test", "train")):
                if not indices or not _finite_number(combo.get("rank_score")):
                    return None
                for key in ("n_test", "months_test", "n_train", "months_train"):
                    if type(h21.get(key)) is not int or h21[key] <= 0:
                        return None
        canonical = json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
    return {
        "schema": "confluence_source.v1",
        "generated_utc": built,
        "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }


def _baseline_pct(raw: dict, half: str) -> float | None:
    try:
        value = raw["base"]["long"]["h21"]["wr_mc_" + half]
    except (KeyError, TypeError):
        return None
    return value * 100 if _finite_number(value) and 0 <= value <= 1 else None


def _optional_date(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return value if datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d") == value else None
    except ValueError:
        return None


def _eligible_long_combos(raw: dict | None) -> list[dict]:
    """Return eligible long combos in rank order.

    Keeping this selection in one helper ensures the public shell and protected
    payload always agree about which rows are ranks 1–3.
    """
    if raw is None:
        return []

    longs = (raw.get("combos") or {}).get("long") or []
    eligible: list[dict] = []
    for combo in longs:
        if not combo.get("active_now"):
            continue
        h21 = combo.get("h21") or {}
        if h21.get("wr_mc_test") is None or h21.get("wr_mc_train") is None:
            continue
        eligible.append(combo)

    return sorted(
        eligible,
        key=lambda combo: combo.get("rank_score", 0),
        reverse=True,
    )


def build_context(raw: dict | None, name_map: dict) -> dict:
    """Build the Jinja context dict from the tech_confluence artifact.

    GATING LAW: gated combos (rank 2 and 3) MUST NOT expose tickers in the
    context. Only rank-1 (`is_free=True`) receives `active_tickers`. For gated
    combos only `len(c["active_now"])` is called — the ticker list is discarded.
    """
    generated_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    source_generation = _source_receipt(raw)
    if source_generation is None:
        raw = None

    if raw is None:
        return {
            "generated_utc": generated_utc,
            "asof": None,
            "source_status": "unavailable",
            "source_generation": None,
            "source_built": None,
            "universe_n": None,
            "split_date": "2018-01-01",
            "n_active_total": None,
            "combos": [],
            "cta_url": _cta_url(),
            "premium_payload_url": PAYLOAD_URL,
        }

    # Derive asof from generated_utc field in artifact
    artifact_utc = raw.get("generated_utc")
    asof: str | None = None
    if artifact_utc:
        try:
            asof = str(artifact_utc)[:10]
        except Exception:  # noqa: BLE001
            asof = None

    universe_n = raw.get("universe_n", 0) or 0
    split_date = raw.get("split_date") or "2018-01-01"

    legs_list = raw.get("legs") or []
    eligible = _eligible_long_combos(raw)

    n_active_total = len(eligible)

    # Take top 3 after the shared rank ordering.
    top3 = eligible[:3]

    combos: list[dict] = []
    for rank_idx, c in enumerate(top3):
        rank = rank_idx + 1
        is_free = (rank == 1)
        h21 = c.get("h21") or {}

        # Build legs from the legs_list using the combo's leg indices
        leg_indices = c.get("legs") or []
        legs_built = []
        for li in leg_indices:
            try:
                leg_data = legs_list[li]
                legs_built.append({
                    "en": leg_data.get("display_en", ""),
                    "zh": leg_data.get("display_zh", ""),
                    "tf": leg_data.get("tf", "D"),
                })
            except (IndexError, TypeError):
                continue

        # GATING LAW: only rank-1 exposes active_tickers
        active_now = c.get("active_now") or []
        if is_free:
            active_tickers = [
                {"ticker": t, "name": name_map.get(t, "")}
                for t in active_now
            ]
        else:
            # Gated: call len() only, never iterate tickers into the context
            active_tickers = []

        # Optional evidence stays unknown when absent or malformed. A useful
        # qualified rate must not turn a missing comparison into a zero result.
        n_fires = c.get("n_fires")
        if type(n_fires) is not int or n_fires < h21["n_test"] + h21["n_train"]:
            n_fires = None
        first_fire = _optional_date(c.get("first_fire"))
        last_fire = _optional_date(c.get("last_fire"))
        if first_fire and last_fire and first_fire > last_fire:
            first_fire = last_fire = None
        frequency = c.get("fires_per_year")
        if not _finite_number(frequency) or frequency < 0:
            frequency = None
        edge = c.get("edge_wr_test")
        edge_pp = edge * 100 if _finite_number(edge) and -1 <= edge <= 1 else None
        consistent = c.get("consistent")
        if type(consistent) is not bool or (consistent and (edge_pp is None or edge_pp <= 0)):
            consistent = None

        combo_entry = {
            "rank": rank,
            "combo_id": c.get("id", ""),
            "name_en": c.get("name_en", ""),
            "name_zh": c.get("name_zh", ""),
            "legs": legs_built,
            "wr_test_pct": (h21.get("wr_mc_test") or 0) * 100,
            "wr_train_pct": (h21.get("wr_mc_train") or 0) * 100,
            "n_test": h21.get("n_test") or 0,
            "months_test": h21.get("months_test") or 0,
            "n_train": h21.get("n_train") or 0,
            "months_train": h21.get("months_train") or 0,
            "n_fires": n_fires,
            "first_fire": first_fire,
            "last_fire": last_fire,
            "fires_per_year": frequency,
            "history_complete": all(v is not None for v in (n_fires, first_fire, last_fire, frequency)),
            "edge_test_pp": edge_pp,
            "consistent": consistent,
            "is_free": is_free,
            "active_count": len(active_now),
            "active_tickers": active_tickers,
        }
        combos.append(combo_entry)

    return {
        "generated_utc": generated_utc,
        "asof": asof,
        "source_status": "available",
        "source_generation": source_generation,
        "source_built": artifact_utc,
        "baseline_test_pct": _baseline_pct(raw, "test"),
        "baseline_train_pct": _baseline_pct(raw, "train"),
        "universe_n": universe_n,
        "split_date": split_date,
        "n_active_total": n_active_total,
        "combos": combos,
        "cta_url": _cta_url(),
        "premium_payload_url": PAYLOAD_URL,
    }


def build_premium_payload(raw: dict | None, name_map: dict) -> dict:
    """Build the server-protected rank-2/3 ticker payload.

    This data must never be embedded in the public page. Caddy protects the
    /premiumdata/ prefix with the authoritative registration + paywall checks.
    """
    source_generation = _source_receipt(raw)
    if source_generation is None:
        raw = None
    artifact_utc = raw.get("generated_utc") if raw else None
    combos: list[dict] = []
    for combo in _eligible_long_combos(raw)[1:3]:
        active_now = combo.get("active_now") or []
        combos.append({
            "combo_id": combo.get("id", ""),
            "active_count": len(active_now),
            "active_tickers": [
                {"ticker": ticker, "name": name_map.get(ticker, "")}
                for ticker in active_now
            ],
        })

    return {
        "schema": "tier_payload.v1",
        "page": "confluence_screener",
        "gated": True,
        "required_tier": "essential",
        "built": artifact_utc or "",
        "source_status": "available" if source_generation else "unavailable",
        "source_generation": source_generation,
        "combos": combos,
    }


# ─────────────────────────────────────────────────────────────────────────────
# render_html — pure Jinja render
# ─────────────────────────────────────────────────────────────────────────────

def render_html(root: Path, ctx: dict) -> str:
    """Render confluence_screener.html.j2 with the given context. Pure."""
    from jinja2 import Environment, FileSystemLoader
    from engine import i18n  # noqa: PLC0415

    env = Environment(
        loader=FileSystemLoader(str(root / "templates")),
        autoescape=True,
    )
    env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip)
    tpl = env.get_template("confluence_screener.html.j2")
    return re.sub(r"(?m)^[ \t]+$", "", tpl.render(**ctx))


# ─────────────────────────────────────────────────────────────────────────────
# render — I/O entrypoint
# ─────────────────────────────────────────────────────────────────────────────

def render(root: Path) -> None:
    """Load artifact, write the public shell, protected payload, and card."""
    t0 = time.perf_counter()

    # Load artifact (fail-soft)
    artifact_path = root / "site" / "factordata" / "tech_confluence.json"
    raw: dict | None = None
    if artifact_path.exists():
        try:
            raw = json.loads(artifact_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raw = None
        except Exception:  # noqa: BLE001
            raw = None

    # Load name_map from sp500_heatmap.json.
    # Actual structure: top-level "tiles" list with {t, name, ...} entries.
    # (The spec says "sectors[].tiles[]" but the file has a flat top-level "tiles" array.)
    name_map: dict[str, str] = {}
    heatmap_path = root / "site" / "marketdata" / "sp500_heatmap.json"
    if heatmap_path.exists():
        try:
            heatmap = json.loads(heatmap_path.read_text(encoding="utf-8"))
            if isinstance(heatmap, dict):
                tiles = heatmap.get("tiles") or []
                for tile in tiles:
                    t_sym = tile.get("t")
                    t_name = tile.get("name")
                    if t_sym and t_name:
                        name_map[t_sym] = t_name
        except Exception:  # noqa: BLE001
            pass

    ctx = build_context(raw, name_map)

    # Render HTML
    html = render_html(root, ctx)

    from lib.pages import write_page  # noqa: PLC0415
    write_page(root / "site" / "confluence_screener.html", html)

    # Paid ticker names live only in this protected asset. Always overwrite it,
    # including with an empty fail-soft payload, so a broken/missing source
    # artifact cannot leave yesterday's entitled rows stale on disk.
    premium_payload = build_premium_payload(raw, name_map)
    payload_out = root / "site" / PAYLOAD_DIR / PAYLOAD_NAME
    payload_out.parent.mkdir(parents=True, exist_ok=True)
    payload_out.write_text(
        json.dumps(premium_payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    # Share card (only when combos present)
    combos = ctx.get("combos") or []
    if combos:
        try:
            from engine.marketing.share_cards import render_screener_card, save_card  # noqa: PLC0415
            top = combos[0]
            asof = ctx.get("asof") or ""
            # wr_test_per10: convert win-rate-pct to "X.X" wins-per-10
            wr_test_pct = top.get("wr_test_pct", 0)
            wr_test_per10 = f"{wr_test_pct / 10:.1f}"
            img = render_screener_card(
                asof=asof,
                combo_headline=top.get("name_en", ""),
                wr_test_per10=wr_test_per10,
                n_fires=top.get("n_fires", 0),
                first_year=(top.get("first_fire") or "")[:4],
                active_count=top.get("active_count", 0),
            )
            card_out = root / "site" / "og" / "confluence_screener.png"
            save_card(img, card_out)
        except Exception:  # noqa: BLE001
            pass  # card failure is non-fatal; page was already written

    elapsed = time.perf_counter() - t0
    print(
        "[confluence_screener] page+premium-payload+card "
        f"in {elapsed:.1f}s (combos={len(combos)})"
    )


# ─────────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    try:
        render(_ROOT)
    except Exception as exc:  # noqa: BLE001
        print(f"::warning title=confluence_screener::{exc}")
        sys.exit(0)


if __name__ == "__main__":
    main()
