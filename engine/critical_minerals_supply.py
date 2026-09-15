"""engine/critical_minerals_supply.py — Critical-minerals supply-concentration context.

DISPLAY / CONFLUENCE CONTEXT ONLY.
Authority: may_rank=false, may_gate=false, may_size=false, may_escalate=false,
           is_context_only=true.

Framing:
  USGS Mineral Commodity Summaries raw production, reserves, net-import
  reliance and import-source shares for rare earths, lithium, cobalt and
  gallium. Display-only context. No score, rank, composite or concentration
  index. The only derived numbers are shares already implied by the source,
  each naming its inputs.

CRITICAL FENCE:
  Never fold into fused_obs_z — separate display leg only.
  Never imported by scripts/build_site*.py or any render-path builder.

Input (reads from parquet, never network):
  data/usgs_mcs/mcs_rows.parquet  (override: USGS_MCS_STORE)

Outputs:
  data/neuralweb/critical_minerals_supply.json
  site/basketdata/critical_minerals_supply.json
  (overrides: USGS_MCS_NW_OUT, USGS_MCS_SITE_OUT)

When the parquet is absent: honest null with a fresh as_of, every commodity
nulls ['no_edition_ingested'], exit 0.

Usage:
  python -m engine.critical_minerals_supply
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import yaml

log = logging.getLogger(__name__)

_REPO = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _REPO / "config" / "usgs_mcs_sources.yml"
_DEFAULT_STORE = _REPO / "data" / "usgs_mcs"
_NW_OUT = _REPO / "data" / "neuralweb" / "critical_minerals_supply.json"
_SITE_OUT = _REPO / "site" / "basketdata" / "critical_minerals_supply.json"

AUTHORITY = {
    "may_rank": False,
    "may_gate": False,
    "may_size": False,
    "may_escalate": False,
    "is_context_only": True,
    "framing": "critical_minerals_supply_context",
    "rotation_calls": False,
    "short_calls": False,
    "fused_obs_z_fence": "SEPARATE_DISPLAY_LEG — never fold into fused_obs_z",
}

_PCT = float("100")
_TOP_N = int("3")


def _store_dir(store: Optional[Path] = None) -> Path:
    if store is not None:
        return Path(store)
    env = os.environ.get("USGS_MCS_STORE")
    if env:
        return Path(env)
    return _DEFAULT_STORE


def _load_config() -> dict:
    with open(_CONFIG_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _as_pct(part: Optional[float], whole: Optional[float]) -> Optional[float]:
    if part is None or whole is None:
        return None
    try:
        if float(whole) == 0.0:
            return None
        return (float(part) / float(whole)) * _PCT
    except (TypeError, ValueError):
        return None


def _latest_revision(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "release_revision" not in df.columns:
        return df
    newest = str(df["release_revision"].astype(str).max())
    return df[df["release_revision"].astype(str) == newest].copy()


def _first_num(series: pd.Series) -> Optional[float]:
    for val in series.tolist():
        if val is None or (isinstance(val, float) and pd.isna(val)):
            continue
        try:
            return float(val)
        except (TypeError, ValueError):
            continue
    return None


def _nir_text(value: Optional[float], qualifier: str, lang: str) -> str:
    if qualifier == "E":
        return (
            "The United States was a net exporter of this mineral."
            if lang == "en"
            else "美国是该矿产的净出口国。"
        )
    if value is None:
        return (
            "US net import reliance is not given as a number in this edition."
            if lang == "en"
            else "这一版未给出美国净进口依赖的数字。"
        )
    shown = f"{qualifier}{int(value)}" if qualifier in {">", "<"} else f"{int(value)}"
    if lang == "en":
        return f"The United States imported about {shown}% of what it used."
    return f"美国进口了其用量的约{shown}%。"


def _read_sentences(payload: dict) -> tuple[str, str]:
    label_en = payload["label_en"]
    label_zh = payload["label_zh"]
    bits_en: list[str] = []
    bits_zh: list[str] = []
    lead = payload.get("leading_producer") or {}
    china_share = payload.get("china_share_world_production_pct")
    period = (lead.get("period") or "").replace("_estimated", "")
    share = lead.get("share_pct")
    country = lead.get("country")
    if china_share is not None and period:
        bits_en.append(
            f"China mined about {china_share:.0f}% of the world's {label_en.lower()} in {period}"
        )
        bits_zh.append(f"中国在{period}年开采了全球约{china_share:.0f}%的{label_zh}")
    elif country and share is not None and period:
        bits_en.append(
            f"{country} mined about {share:.0f}% of the world's {label_en.lower()} in {period}"
        )
        bits_zh.append(f"{country}在{period}年开采了全球约{share:.0f}%的{label_zh}")
    nir = payload.get("us_net_import_reliance") or {}
    if nir.get("text_en"):
        bits_en.append(nir["text_en"].replace("The United States imported ", "and the US imported ").replace("The United States was ", "and the US was "))
        # Keep the first clause capitalised; stitch later.
    if nir.get("text_zh"):
        bits_zh.append(nir["text_zh"])
    if not bits_en:
        return (
            f"{label_en} supply figures from this edition are incomplete.",
            f"这一版的{label_zh}供给数字不完整。",
        )
    if len(bits_en) == 1:
        en = bits_en[0]
        if not en.endswith("."):
            en = en + "."
        zh = bits_zh[0] if bits_zh else ""
        if zh and not zh.endswith("。"):
            zh = zh + "。"
        return en[0].upper() + en[1:], zh
    # Two clauses: production + US reliance.
    first = bits_en[0]
    second = bits_en[1]
    if second.startswith("and "):
        en = first + ", " + second
    else:
        en = first + ", and " + second[0].lower() + second[1:]
    if not en.endswith("."):
        en = en + "."
    zh = "，".join(bits_zh) if bits_zh else ""
    if zh and not zh.endswith("。"):
        zh = zh + "。"
    return en[0].upper() + en[1:], zh


def _commodity_block(cfg_entry: dict, df: Optional[pd.DataFrame]) -> dict:
    key = cfg_entry["key"]
    block: dict[str, Any] = {
        "label_en": cfg_entry["label_en"],
        "label_zh": cfg_entry["label_zh"],
        "theme_id": cfg_entry["theme_id"],
        "us_net_import_reliance": None,
        "leading_producer": None,
        "import_sources_2021_24": [],
        "top3_import_share_pct": None,
        "china_share_world_production_pct": None,
        "world_production": None,
        "reserves_top": None,
        "read_en": "",
        "read_zh": "",
        "nulls": [],
    }
    if df is None or df.empty:
        block["nulls"] = ["no_edition_ingested"]
        block["read_en"] = f"{cfg_entry['label_en']} has not been ingested yet."
        block["read_zh"] = f"尚未收录{cfg_entry['label_zh']}的供给数字。"
        return block

    sub = df[df["commodity_key"] == key]
    if sub.empty:
        block["nulls"].append("commodity_absent_in_edition")
        block["read_en"] = f"{cfg_entry['label_en']} is not in the ingested edition."
        block["read_zh"] = f"已收录的这一版没有{cfg_entry['label_zh']}。"
        return block

    t7 = sub[sub["table"] == "t7"]
    nir_rows = t7[t7["metric"] == "net_import_reliance"]
    if not nir_rows.empty:
        row = nir_rows.iloc[0]
        q = row.get("qualifier") or ""
        val = None if pd.isna(row.get("value_num")) else float(row["value_num"])
        block["us_net_import_reliance"] = {
            "value": val,
            "qualifier": q,
            "text_en": _nir_text(val, q, "en"),
            "text_zh": _nir_text(val, q, "zh"),
            "inputs": ["T7.Net_Import_Reliance"],
        }
    lead_rows = t7[t7["metric"] == "leading_producer_share"]
    world_t7 = t7[t7["metric"] == "world_total_prod"]
    if not lead_rows.empty:
        row = lead_rows.iloc[0]
        share = None if pd.isna(row.get("value_num")) else float(row["value_num"])
        world_total = _first_num(world_t7["value_num"]) if not world_t7.empty else None
        period = str(row.get("period") or "")
        block["leading_producer"] = {
            "country": row.get("country"),
            "share_pct": share,
            "world_total": world_total,
            "unit": row.get("unit"),
            "period": period.replace("_estimated", "") if period.endswith("_estimated") else period,
            "inputs": [
                "T7.Leading_source_country",
                "T7.Leading_source_precent_world",
                "T7.World_total_prod",
            ],
        }

    fig = sub[sub["table"] == "fig3_import_sources"]
    sources = []
    for _, row in fig.iterrows():
        pct = None if pd.isna(row.get("value_num")) else float(row["value_num"])
        sources.append({"country": row.get("country"), "pct": pct})
    block["import_sources_2021_24"] = sources
    if sources:
        top = sources[:_TOP_N]
        nums = [s["pct"] for s in top if s["pct"] is not None]
        block["top3_import_share_pct"] = sum(nums) if nums else None
        # Name the input: sum of the first three Fig3 Percent rows.

    world = sub[sub["table"] == "world_production"]
    metric_want = (cfg_entry.get("world_metric") or "Mine production").lower()
    prod = world[
        world["metric"].astype(str).str.lower().str.contains("production")
        & ~world["metric"].astype(str).str.lower().str.contains("capacity")
        & ~world["metric"].astype(str).str.lower().str.contains("reserves")
    ]
    # Prefer the configured metric name when present.
    named = prod[prod["metric"].astype(str).str.lower().str.contains(metric_want.lower())]
    if not named.empty:
        prod = named
    if not prod.empty:
        # Latest period present.
        periods = sorted(prod["period"].astype(str).unique())
        period = periods[-1]
        slice_ = prod[prod["period"].astype(str) == period]
        by_country = []
        china_val = None
        world_val = None
        unit = None
        for _, row in slice_.iterrows():
            country = str(row.get("country") or "")
            val = None if pd.isna(row.get("value_num")) else float(row["value_num"])
            q = row.get("qualifier") or ""
            by_country.append({"country": country, "value": val, "qualifier": q})
            if country.lower() == "china":
                china_val = val
            if country.lower().startswith("world"):
                world_val = val
                unit = row.get("unit")
        block["world_production"] = {
            "period": period,
            "unit": unit or (slice_["unit"].dropna().iloc[0] if slice_["unit"].notna().any() else None),
            "total": world_val,
            "by_country": by_country,
            "inputs": ["Commodities_Data.China", "Commodities_Data.World total"],
        }
        block["china_share_world_production_pct"] = _as_pct(china_val, world_val)

    reserves = world[world["metric"].astype(str).str.lower().str.contains("reserves")]
    if not reserves.empty:
        ranked = []
        for _, row in reserves.iterrows():
            country = str(row.get("country") or "")
            if country.lower().startswith("world"):
                continue
            val = None if pd.isna(row.get("value_num")) else float(row["value_num"])
            if val is None:
                continue
            ranked.append({"country": country, "value": val})
        ranked.sort(key=lambda r: r["value"], reverse=True)
        block["reserves_top"] = ranked[:_TOP_N] if ranked else None
    else:
        block["reserves_top"] = None

    if block["us_net_import_reliance"] is None:
        block["nulls"].append("nir_absent")
    if block["leading_producer"] is None:
        block["nulls"].append("leading_producer_absent")
    if not block["import_sources_2021_24"]:
        block["nulls"].append("import_sources_absent")
    if block["china_share_world_production_pct"] is None:
        block["nulls"].append("china_share_absent")

    en, zh = _read_sentences(block)
    block["read_en"] = en
    block["read_zh"] = zh
    return block


def _honesty() -> dict:
    return {
        "en": (
            "These figures come from the USGS Mineral Commodity Summaries, "
            "an annual public report. They are context only. They do not rank, "
            "size, or gate any position."
        ),
        "zh": (
            "这些数字来自美国地质调查局《矿产商品摘要》年度公开报告。"
            "仅作背景披露，不用于排名、仓位或门槛。"
        ),
    }


def compute_critical_minerals_supply(
    store: Optional[Path] = None,
    nw_out: Optional[Path] = None,
    site_out: Optional[Path] = None,
    write: bool = True,
) -> dict:
    now = datetime.now(timezone.utc)
    as_of = now.strftime("%Y-%m-%d")
    generated_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    cfg = _load_config()
    commodities_cfg = cfg.get("commodities") or []
    store_path = _store_dir(store)
    parquet = store_path / "mcs_rows.parquet"
    df: Optional[pd.DataFrame] = None
    if parquet.exists():
        try:
            df = _latest_revision(pd.read_parquet(parquet))
        except Exception as exc:  # noqa: BLE001
            log.warning("critical_minerals_supply: parquet unreadable: %s", exc)
            df = None

    edition = {"year": None, "item_id": None, "published": None}
    if df is not None and not df.empty:
        edition["year"] = int(df["edition_year"].dropna().iloc[0]) if df["edition_year"].notna().any() else None
        edition["item_id"] = (
            str(df["source_item_id"].dropna().iloc[0]) if df["source_item_id"].notna().any() else None
        )
        known = (cfg.get("known_editions") or {}).get(edition["year"]) or (cfg.get("known_editions") or {}).get(
            str(edition["year"])
        )
        if known:
            edition["published"] = known.get("published")

    out_commodities = {
        entry["key"]: _commodity_block(entry, df) for entry in commodities_cfg
    }
    with_data = sum(1 for c in out_commodities.values() if "no_edition_ingested" not in c.get("nulls", []))
    artifact = {
        "schema": "critical_minerals_supply.v1",
        "as_of": as_of,
        "generated_at": generated_at,
        "authority": AUTHORITY,
        "honesty_header": _honesty(),
        "edition": edition,
        "commodities": out_commodities,
        "coverage_stats": {
            "commodities_configured": len(commodities_cfg),
            "commodities_with_rows": with_data,
            "parquet_absent": df is None,
        },
        "source_note": (
            "USGS Mineral Commodity Summaries via ScienceBase NMIC. "
            "Public-domain US Government work. Display-only context. "
            "Leading-producer share uses T7 Leading_source_precent_world; "
            "top-3 import share sums the first three Fig3 Percent rows; "
            "China share of world production is China divided by World total "
            "from Commodities_Data for the same period."
        ),
    }

    nw_path = Path(os.environ["USGS_MCS_NW_OUT"]) if os.environ.get("USGS_MCS_NW_OUT") else (nw_out or _NW_OUT)
    site_path = Path(os.environ["USGS_MCS_SITE_OUT"]) if os.environ.get("USGS_MCS_SITE_OUT") else (site_out or _SITE_OUT)
    if write:
        try:
            nw_path.parent.mkdir(parents=True, exist_ok=True)
            nw_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            log.error("critical_minerals_supply: NW write failed: %s", exc)
        try:
            site_path.parent.mkdir(parents=True, exist_ok=True)
            site_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            log.error("critical_minerals_supply: site write failed: %s", exc)
    return artifact


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    try:
        art = compute_critical_minerals_supply()
        stats = art.get("coverage_stats") or {}
        log.info(
            "critical_minerals_supply: %s/%s commodities with rows (parquet_absent=%s)",
            stats.get("commodities_with_rows"),
            stats.get("commodities_configured"),
            stats.get("parquet_absent"),
        )
    except Exception as exc:  # noqa: BLE001
        log.error("critical_minerals_supply: unexpected failure (non-fatal): %s", exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
