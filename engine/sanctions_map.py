"""engine/sanctions_map.py — pure leaf view-model builder for the Sanctions
Map page (packet A-F02-1). Display-only, like engine.strategic_reserves: no
LLM originates any attribution, count, or rung. Every country<->programme
edge comes from the human-reviewed config/sanctions_ofac_programs.yml.

Never raises. Nulls are ``None``, never ``0``.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

STORE_DIR = Path("data/sanctions_ofac")
SDN_FILE = STORE_DIR / "sdn_snapshot.csv.gz"
META_FILE = STORE_DIR / "meta.json"
PROGRAMS_CONFIG = Path("config/sanctions_ofac_programs.yml")


def _rung(n: int) -> int:
    """Three-state ladder: 1 programme -> 1, 2-3 -> 2, 4+ -> 3."""
    if n >= 4:
        return 3
    if n >= 2:
        return 2
    return 1


UNKNOWN_RUNG = "x"
NOT_NAMED_RUNG = 0

# Frozen geo join for the public-news layer (W7-2 / MO-PAID-008).
# UK is the only jurisdiction that maps onto an existing ISO3 path.
# EU / EA / EFTA have no single ISO3 — they stay a dated list.
_NEWS_ISO3_BY_JURISDICTION = {"UK": "GBR"}
_PUBLISHER_ZH = {
    "European Commission": "欧盟委员会",
    "Bank of England": "英格兰银行",
    "European Central Bank": "欧洲中央银行",
}


def split_program_field(raw: str) -> list[str]:
    """OFAC's 'program' field packs multiple codes as ``[A] [B]`` — split on
    the ``] [`` join (any whitespace) and strip stray brackets/whitespace.
    Shared by collectors/ofac_sdn.py so both parsers agree on whitespace
    variants."""
    raw = (raw or "").strip()
    if not raw or raw == "-0-":
        return []
    parts = re.split(r"\]\s*\[", raw)
    return [p.strip().strip("[]").strip() for p in parts if p.strip().strip("[]").strip()]


# Back-compat alias used by older call sites / tests.
_split_program_field = split_program_field


def rungs_for(vm: dict, all_iso3=None) -> dict:
    """Per-country rung map for the world map SVG, honest about unknown
    coverage (acceptance 3: missing coverage prints as unknown, never as
    zero).

    - Positively resolved countries keep their 1/2/3 rung.
    - When any *country-scoped* OFAC programme failed to resolve
      (``coverage.unresolved > 0``), every other known country is painted
      unknown (hatch) — we cannot prove they are unsanctioned.
    - When country-scoped coverage is fully resolved, absent countries are
      an honest ``0`` ("not named"). Thematic programmes never trigger the
      hatch — they are not country attributions.
    """
    rungs: dict = {}
    coverage = vm.get("coverage")
    if coverage is None:
        for iso3 in (all_iso3 or ()):
            rungs[iso3] = UNKNOWN_RUNG
    else:
        unresolved = int(coverage.get("unresolved") or 0)
        if unresolved > 0:
            for iso3 in (all_iso3 or ()):
                rungs[iso3] = UNKNOWN_RUNG
        else:
            for iso3 in (all_iso3 or ()):
                rungs[iso3] = NOT_NAMED_RUNG
    for c in vm.get("countries") or []:
        rungs[c["iso3"]] = c["rung"]
    return rungs


def _load_programs_config(path: Path = PROGRAMS_CONFIG) -> tuple[list[dict], set[str]]:
    if not path.exists():
        return [], set()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return [], set()
    seen: set[str] = set()
    thematic: set[str] = set()
    for row in (raw.get("thematic") or []):
        if not isinstance(row, dict) or not row.get("code"):
            continue
        code = row["code"]
        if code in seen:
            print(f"::warning title=sanctions_map_duplicate_code::{code}", flush=True)
            continue
        seen.add(code)
        thematic.add(code)
    programs = []
    for row in (raw.get("programs") or []):
        if not isinstance(row, dict) or not row.get("code"):
            continue
        code = row["code"]
        if code in seen:
            print(f"::warning title=sanctions_map_duplicate_code::{code}", flush=True)
            continue
        seen.add(code)
        programs.append(row)
    return programs, thematic


def _load_program_code_counts(sdn_file: Path = SDN_FILE) -> dict[str, int]:
    """Count SDN entries per OFAC programme code from the raw snapshot.
    Column 3 (0-indexed) is OFAC's published 'program' field (verified
    against a live SDN.CSV fetch 2026-09-05 — column 7 was wrong)."""
    counts: dict[str, int] = {}
    if not sdn_file.exists():
        return counts
    try:
        raw_bytes = sdn_file.read_bytes()
        if sdn_file.suffix == ".gz":
            raw_bytes = gzip.decompress(raw_bytes)
        text = raw_bytes.decode("utf-8", errors="replace")
    except Exception:
        return counts
    try:
        reader = csv.reader(io.StringIO(text))
        for row in reader:
            if len(row) > 3 and row[3].strip():
                for code in split_program_field(row[3]):
                    counts[code] = counts.get(code, 0) + 1
    except Exception:
        return {}
    return counts


def _load_meta(meta_file: Path = META_FILE) -> dict:
    if not meta_file.exists():
        return {}
    try:
        return json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _cell(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "nat", "<na>"}:
        return ""
    return text


def _iso3_for_jurisdiction(jurisdiction: str) -> str | None:
    """UK → GBR on the existing worldmap path. No invented ISO3 for EU/EA/EFTA."""
    return _NEWS_ISO3_BY_JURISDICTION.get(str(jurisdiction or "").strip() or "")


def _publisher_labels() -> dict[str, tuple[str, str]]:
    """Map source key → (EN, ZH) publisher for keys whose rights_state is
    VERIFIED_PUBLIC_REUSE. Unknown keys (and UNVERIFIED_EXCLUDED) are absent
    so a display-time rights filter is a single `key in _allowed_publishers()`
    check. PURE."""
    out: dict[str, tuple[str, str]] = {}
    try:
        from engine.europe_news_intel import sources
        for spec in sources() or []:
            if str(spec.get("rights_state") or "") != "VERIFIED_PUBLIC_REUSE":
                continue
            key = _cell(spec.get("key"))
            en = _cell(spec.get("publisher"))
            if key and en:
                out[key] = (en, _PUBLISHER_ZH.get(en, en))
    except Exception:
        return out
    return out


def _allowed_publishers() -> set[str]:
    """Source keys whose rights_state == VERIFIED_PUBLIC_REUSE. PURE."""
    return set(_publisher_labels().keys())


def _today_utc() -> date:
    """UTC clock today. Kept off the hot path so tests can monkeypatch."""
    return datetime.now(timezone.utc).date()


def _news_is_recent(latest_asof: str, today: date) -> bool:
    """True iff latest_asof is today or yesterday (UTC). PURE.

    "Recent" means within the freshness bound — events older than
    today − 1 day are stale and the page should say so rather than print
    "Official press today" against days-old rows.
    """
    if not latest_asof:
        return False
    try:
        d = date.fromisoformat(str(latest_asof)[:10])
    except (ValueError, TypeError):
        return False
    return d >= (today - timedelta(days=1))


def _hoist_common(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Each key present ONLY when every row shares that value. PURE.

    Used to render the publisher / jurisdiction label once in the section
    header instead of repeating it on every row (Doctrine Law 4 — "no per-row
    repetition of a constant"). Returns an empty dict when nothing is shared.
    """
    if not rows:
        return {}
    out: dict[str, Any] = {}
    for k in ("source", "source_zh", "jurisdiction"):
        vals = {r.get(k) for r in rows}
        if len(vals) == 1:
            only = next(iter(vals))
            if only:
                out[k] = only
    return out


def _public_news(today: date | None = None) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    """Today's official-press rows from europe_news_intel.read_events.

    Returns ``(state, rows, common)`` where ``state`` is one of:

    * ``"ok"`` — store read, latest day within today-1, every row passed the
      rights filter; ``rows`` is the filtered list (maybe empty after the
      rights filter, but never here).
    * ``"none_recent"`` — store read but the latest day is older than today-1
      (or the store had no rows at all), OR the rights filter dropped every
      row; ``rows`` is ``[]``.
    * ``"unavailable"`` — ``read_events`` raised (missing/unreadable store);
      ``rows`` is ``[]``.

    ``common`` carries shared publisher / jurisdiction labels for the
    per-row-constant hoist (D3). Never raises.
    """
    if today is None:
        today = _today_utc()
    allowed_keys = _allowed_publishers()
    try:
        from engine.europe_news_intel import read_events
        df = read_events()
    except Exception:
        return ("unavailable", [], {})
    if df is None or len(df) == 0 or "asof" not in df.columns:
        return ("none_recent", [], {})
    asofs = [_cell(v)[:10] for v in df["asof"].tolist()]
    asofs = [a for a in asofs if a]
    if not asofs:
        return ("none_recent", [], {})
    latest = max(asofs)
    if not _news_is_recent(latest, today):
        return ("none_recent", [], {})
    day = df[df["asof"].astype(str).str.slice(0, 10) == latest]
    labels = _publisher_labels()
    out: list[dict[str, Any]] = []
    for rec in day.to_dict(orient="records"):
        title = _cell(rec.get("title"))
        if not title:
            continue
        source_key = _cell(rec.get("source"))
        if source_key not in allowed_keys:
            continue
        en, zh = labels.get(source_key, ("", ""))
        juris = _cell(rec.get("jurisdiction"))
        asof = _cell(rec.get("asof"))[:10]
        seendate = _cell(rec.get("seendate"))[:10]
        out.append(
            {
                "title": title,
                "url": _cell(rec.get("url")),
                "source": en,
                "source_zh": zh,
                "jurisdiction": juris,
                "iso3": _iso3_for_jurisdiction(juris),
                "asof": asof,
                "seendate": seendate,
            }
        )
    if not out:
        return ("none_recent", [], {})
    out.sort(
        key=lambda row: (row.get("seendate") or row.get("asof") or "", row.get("title") or ""),
        reverse=True,
    )
    return ("ok", out, _hoist_common(out))


def _as_of_from_meta(meta: dict) -> str | None:
    """Prefer OFAC list_published_date; fall back to the fetch date so the
    page never claims 'unknown' when we have a verified snapshot timestamp."""
    published = meta.get("list_published_date")
    if published:
        return str(published)[:10]
    fetched = meta.get("fetched_at")
    if fetched:
        return str(fetched)[:10]
    return None


def build(
    sdn_file: Path = SDN_FILE,
    meta_file: Path = META_FILE,
    programs_config: Path = PROGRAMS_CONFIG,
) -> dict[str, Any]:
    """Build the Sanctions Map view model. Never raises."""
    try:
        code_counts = _load_program_code_counts(sdn_file)
        meta = _load_meta(meta_file)
        config_rows, thematic_codes = _load_programs_config(programs_config)
    except Exception:
        code_counts, meta, config_rows, thematic_codes = {}, {}, [], set()

    news_state, news, news_common = _public_news()

    if not code_counts:
        return {
            "as_of": _as_of_from_meta(meta),
            "source_url": meta.get("source_url"),
            "fetched_at": meta.get("fetched_at"),
            "n_programs_total": 0,
            "n_countries": 0,
            "countries": [],
            "unresolved": [],
            "thematic": [],
            "coverage": None,
            "public_news": news,
            "public_news_state": news_state,
            "public_news_common": news_common,
        }

    by_code = {row["code"]: row for row in config_rows if row.get("code")}

    by_iso3: dict[str, dict] = {}
    unresolved: list[dict] = []
    thematic: list[dict] = []
    n_programs_total = 0
    resolved_count = 0
    unresolved_count = 0
    thematic_count = 0

    for code, n_entries in code_counts.items():
        n_programs_total += 1
        if code in thematic_codes:
            thematic.append({"code": code, "n_entries": n_entries})
            thematic_count += 1
            continue
        row = by_code.get(code)
        if row is None or not row.get("iso3"):
            unresolved.append({"code": code, "n_entries": n_entries})
            unresolved_count += 1
            continue
        resolved_count += 1
        iso3 = row["iso3"]
        entry = by_iso3.setdefault(
            iso3,
            {
                "iso3": iso3,
                "name_en": row.get("country_name_en") or row.get("name_en", iso3),
                "name_zh": row.get("country_name_zh") or row.get("name_zh", iso3),
                "n_programs": 0,
                "programs": [],
            },
        )
        # Prefer explicit country_* once set; don't overwrite with a later program title.
        if row.get("country_name_en"):
            entry["name_en"] = row["country_name_en"]
        if row.get("country_name_zh"):
            entry["name_zh"] = row["country_name_zh"]
        entry["n_programs"] += 1
        entry["programs"].append(
            {
                "code": code,
                "name_en": row.get("name_en"),
                "name_zh": row.get("name_zh"),
                "url": row.get("ofac_program_url"),
            }
        )

    countries = []
    for iso3, entry in by_iso3.items():
        entry["rung"] = _rung(entry["n_programs"])
        countries.append(entry)
    countries.sort(key=lambda c: c["n_programs"], reverse=True)

    return {
        "as_of": _as_of_from_meta(meta),
        "source_url": meta.get("source_url"),
        "fetched_at": meta.get("fetched_at"),
        "n_programs_total": n_programs_total,
        "n_countries": len(countries),
        "countries": countries,
        "unresolved": unresolved,
        "thematic": thematic,
        "coverage": {
            "resolved": resolved_count,
            "unresolved": unresolved_count,
            "thematic": thematic_count,
        },
        "public_news": news,
        "public_news_state": news_state,
        "public_news_common": news_common,
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, default=str))
