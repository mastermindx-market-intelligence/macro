"""
collectors/usgs_mcs.py — USGS Mineral Commodity Summaries (ScienceBase NMIC) collector.

Acquisition source:
  USGS National Minerals Information Center Mineral Commodity Summaries
  data releases on ScienceBase (US Government work, public domain, keyless).

SOURCE VERIFIED LIVE 2026-09-13:
  - Parent collection: https://www.sciencebase.gov/catalog/items?parentId=5c8c03e4e4b0938824529f7d
  - Newest T7-shaped edition: 2026 item 696a75d5d4be0228872d3bf8
    title 'Mineral Commodity Summaries 2026 Data Release', published 2026-02-06
  - 2025 item 677eaf95d34e760b392c4970 and 2024 item 65a6e45fd34e5af967a46749
    use ZIP-per-commodity layouts — out of this collector (backfill child).
  - Files by name regex from the item files[] list (never a guessed URL):
      MCS<year>_T7_Critical_Minerals_Salient.csv
      MCS<year>_Fig3_Major_Import_Sources.csv
      MCS<year>_Commodities_Data.csv (cp1252)
  - Keyless HTTP 200. At most five requests per run. Never parse PDFs.

Env:
  USGS_MCS_STORE       — Optional override for data/usgs_mcs/ (tests).
  USGS_MCS_PARENT_URL  — Optional override for the parent listing URL (tests).
  USGS_MCS_TIMEOUT     — Per-request timeout seconds as a string (default "30").

PIT LAW:
  Rows keyed by (edition_year, table, commodity_key, country, metric, period).
  Same sha256 of every ingested file → no-op (status no_change).
  New sha256 → rows written under a new release_revision; older rows stay.

OUTPUT (nightly-advanced, never committed from a session tree):
  data/usgs_mcs/mcs_rows.parquet
  data/usgs_mcs/state.json
  data/usgs_mcs/receipts.json

RENDER BUDGET LAW:
  This collector NEVER runs on the render critical path. It is a collect-lane
  step only (dag.yml collect_tail). Steady-state no-op when file hashes match.

FAILURE ISOLATION:
  Per-file failures are caught and logged. One bad CSV never voids the other
  tables. Parent/item HTTP failure is a typed outage; existing parquet is left
  untouched. Always exits 0.

PACING:
  Polite User-Agent, 30-second timeouts, at most five HTTP requests per run.
  No inter-file sleep is required at three files; do not retry a non-200.

Usage:
  python -m collectors.usgs_mcs
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import pandas as pd
import requests
import yaml

log = logging.getLogger(__name__)

_REPO = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _REPO / "config" / "usgs_mcs_sources.yml"
_DEFAULT_STORE = _REPO / "data" / "usgs_mcs"
_SCIENCEBASE = "https://www.sciencebase.gov/catalog"
_UA = (
    "macro-dashboard-usgs-mcs/1.0 "
    "(+https://github.com/mastermindx-market-intelligence/macro; polite annual ingest)"
)

STORE_COLS = [
    "edition_year",
    "table",
    "commodity_key",
    "commodity_label_src",
    "country",
    "metric",
    "period",
    "value_num",
    "value_raw",
    "qualifier",
    "unit",
    "notes",
    "source_item_id",
    "source_file",
    "source_sha256",
    "release_revision",
    "ingested_at",
]

_TITLE_RE = re.compile(
    r"^(U\.S\. Geological Survey )?Mineral Commodity Summaries (\d{4}) Data Release"
)
_FOOTNOTE_RE = re.compile(r"^(.*?)(\d+)$")
_QUAL_PREFIX = re.compile(r"^([><])\s*(.*)$")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")

_WORLD_SECTIONS = {
    "World Mine Production and Reserves",
    "World Low-Purity Production and Production Capacity",
}


def _timeout() -> float:
    return float(os.environ.get("USGS_MCS_TIMEOUT", "30"))


def _max_requests() -> int:
    return int(os.environ.get("USGS_MCS_MAX_REQUESTS", "5"))


def _store_dir(store: Optional[Path] = None) -> Path:
    if store is not None:
        return Path(store)
    env = os.environ.get("USGS_MCS_STORE")
    if env:
        return Path(env)
    return _DEFAULT_STORE


def load_config() -> dict:
    with open(_CONFIG_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def strip_glued_footnote(label: str) -> tuple[str, str]:
    """Strip a footnote digit glued to a T7 label and record it."""
    text = (label or "").strip()
    m = _FOOTNOTE_RE.match(text)
    if m and m.group(1) and m.group(1)[-1].isalpha() or (
        m and m.group(1) and m.group(1)[-1] in ")."
    ):
        return m.group(1), m.group(2)
    return text, ""


def parse_qualifier(raw: Any) -> tuple[Optional[float], str]:
    """Parse USGS qualifier grammar; keep the qualifier when the raw is non-numeric."""
    if raw is None:
        return None, ""
    text = str(raw).strip()
    if text == "":
        return None, ""
    if text in {"E", "W", "NA"}:
        return None, text
    if text in {"—", "-", "–", "―"}:
        return None, "dash"
    qual = ""
    body = text
    m = _QUAL_PREFIX.match(text)
    if m:
        qual = m.group(1)
        body = m.group(2).strip()
    body = body.replace(",", "").replace(" ", "")
    if body == "":
        return None, qual or ""
    try:
        return float(body), qual
    except ValueError:
        if body in {"E", "W", "NA"}:
            return None, body
        if body in {"—", "-", "–"}:
            return None, "dash"
        return None, qual or ""


def _slug(label: str) -> str:
    cleaned, _ = strip_glued_footnote(label)
    slug = _NON_ALNUM.sub("_", cleaned.lower()).strip("_")
    return slug or "unknown"


def _norm(label: str) -> str:
    cleaned, _ = strip_glued_footnote(label)
    return _NON_ALNUM.sub(" ", cleaned.lower()).strip()


def _commodity_key(label: str, commodities: list[dict]) -> str:
    norm = _norm(label)
    for entry in commodities:
        for candidate in (
            entry.get("t7_label") or "",
            entry.get("commodities_data_commodity") or "",
            entry.get("label_en") or "",
        ):
            cand = _norm(candidate)
            if not cand:
                continue
            if norm == cand or cand in norm or norm in cand:
                return entry["key"]
    return _slug(label)


def discover_editions(parent: dict) -> list[dict]:
    """Return MCS data-release editions from a ScienceBase parent listing."""
    cfg = load_config()
    pattern = re.compile(cfg["sciencebase"]["title_regex"])
    found: list[dict] = []
    for item in parent.get("items") or []:
        title = item.get("title") or ""
        m = pattern.search(title)
        if not m:
            continue
        year = int(m.group(2))
        found.append(
            {
                "year": year,
                "item_id": item.get("id"),
                "title": title,
            }
        )
    found.sort(key=lambda e: e["year"])
    return found


def select_ingest_edition(editions: list[dict], known_editions: dict) -> dict:
    """Pick the newest edition whose known layout is the 2026 T7 CSV shape."""
    known = {int(k): v for k, v in (known_editions or {}).items()}
    t7_years = [
        e for e in editions if known.get(int(e["year"]), {}).get("layout") == "t7_csv"
    ]
    if t7_years:
        chosen = max(t7_years, key=lambda e: e["year"])
        extra = known[int(chosen["year"])]
        return {
            **chosen,
            "layout": extra.get("layout"),
            "published": extra.get("published"),
        }
    if editions:
        newest = max(editions, key=lambda e: e["year"])
        extra = known.get(int(newest["year"]), {})
        return {**newest, "layout": extra.get("layout"), "published": extra.get("published")}
    raise ValueError("no Mineral Commodity Summaries editions in parent listing")


def _decode_csv(content: bytes) -> str:
    if content.startswith(b"\xef\xbb\xbf"):
        return content.decode("utf-8-sig")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("cp1252")


def _empty_row(**kwargs) -> dict:
    row = {k: None for k in STORE_COLS}
    row["qualifier"] = ""
    row.update(kwargs)
    return row


def parse_t7_csv(
    content: bytes,
    edition_year: int,
    source_item_id: str = "",
    source_file: str = "",
    source_sha256: str = "",
    release_revision: str = "",
    ingested_at: str = "",
) -> list[dict]:
    cfg = load_config()
    commodities = cfg.get("commodities") or []
    text = _decode_csv(content)
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict] = []
    common = {
        "edition_year": edition_year,
        "table": "t7",
        "source_item_id": source_item_id,
        "source_file": source_file,
        "source_sha256": source_sha256,
        "release_revision": release_revision,
        "ingested_at": ingested_at,
        "unit": None,
    }
    for rec in reader:
        label_src = (rec.get("Critical_mineral") or "").strip()
        if not label_src:
            continue
        _, footnote = strip_glued_footnote(label_src)
        key = _commodity_key(label_src, commodities)
        period = (rec.get("Year") or "").strip()
        unit = (rec.get("Units") or "").strip()
        notes_bits = [rec.get("Prod_notes") or "", rec.get("Consumption_Notes") or "", rec.get("Import_source_notes") or "", rec.get("World_prod_notes") or ""]
        if footnote:
            notes_bits.append(f"footnote {footnote}")
        notes = " | ".join(p for p in notes_bits if p)
        common_row = {
            **common,
            "commodity_key": key,
            "commodity_label_src": label_src,
            "period": period,
            "unit": unit,
            "notes": notes,
        }
        nir_raw = rec.get("Net_Import_Reliance")
        nir_num, nir_q = parse_qualifier(nir_raw)
        rows.append(
            _empty_row(
                **common_row,
                country="United States",
                metric="net_import_reliance",
                value_num=nir_num,
                value_raw="" if nir_raw is None else str(nir_raw).strip(),
                qualifier=nir_q,
            )
        )
        lead_country = (rec.get("Leading_source_country") or "").strip()
        share_raw = rec.get("Leading_source_precent_world")
        share_num, share_q = parse_qualifier(share_raw)
        rows.append(
            _empty_row(
                **common_row,
                country=lead_country,
                metric="leading_producer_share",
                value_num=share_num,
                value_raw="" if share_raw is None else str(share_raw).strip(),
                qualifier=share_q,
            )
        )
        world_raw = rec.get("World_total_prod")
        world_num, world_q = parse_qualifier(world_raw)
        rows.append(
            _empty_row(
                **common_row,
                country="World",
                metric="world_total_prod",
                value_num=world_num,
                value_raw="" if world_raw is None else str(world_raw).strip(),
                qualifier=world_q,
            )
        )
    return rows


def parse_fig3_csv(
    content: bytes,
    edition_year: int,
    source_item_id: str = "",
    source_file: str = "",
    source_sha256: str = "",
    release_revision: str = "",
    ingested_at: str = "",
) -> list[dict]:
    cfg = load_config()
    commodities = cfg.get("commodities") or []
    text = _decode_csv(content)
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict] = []
    for rec in reader:
        label_src = (rec.get("Commodity") or "").strip()
        if not label_src:
            continue
        pct_raw = rec.get("Percent")
        pct_num, pct_q = parse_qualifier(pct_raw)
        rows.append(
            _empty_row(
                edition_year=edition_year,
                table="fig3_import_sources",
                commodity_key=_commodity_key(label_src, commodities),
                commodity_label_src=label_src,
                country=(rec.get("Import_Source_2021_24") or "").strip(),
                metric="import_share",
                period="2021-24",
                value_num=pct_num,
                value_raw="" if pct_raw is None else str(pct_raw).strip(),
                qualifier=pct_q,
                unit="percent",
                notes=(rec.get("NIR") or ""),
                source_item_id=source_item_id,
                source_file=source_file,
                source_sha256=source_sha256,
                release_revision=release_revision,
                ingested_at=ingested_at,
            )
        )
    return rows


def parse_commodities_csv(
    content: bytes,
    edition_year: int,
    source_item_id: str = "",
    source_file: str = "",
    source_sha256: str = "",
    release_revision: str = "",
    ingested_at: str = "",
) -> tuple[list[dict], int]:
    cfg = load_config()
    commodities = cfg.get("commodities") or []
    text = _decode_csv(content)
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict] = []
    unparsed = 0
    for rec in reader:
        section = (rec.get("Section") or "").strip()
        if section not in _WORLD_SECTIONS:
            continue
        label_src = (rec.get("Commodity") or "").strip()
        if not label_src:
            unparsed += 1
            continue
        raw = rec.get("Value")
        num, qual = parse_qualifier(raw)
        detail = (rec.get("Statistics_detail") or rec.get("Statistics") or "").strip()
        rows.append(
            _empty_row(
                edition_year=edition_year,
                table="world_production",
                commodity_key=_commodity_key(label_src, commodities),
                commodity_label_src=label_src,
                country=(rec.get("Country") or "").strip(),
                metric=detail or (rec.get("Statistics") or "").strip(),
                period=(rec.get("Year") or "").strip(),
                value_num=num,
                value_raw="" if raw is None else str(raw).strip(),
                qualifier=qual,
                unit=(rec.get("Unit") or "").strip(),
                notes=(rec.get("Notes") or ""),
                source_item_id=source_item_id,
                source_file=source_file,
                source_sha256=source_sha256,
                release_revision=release_revision,
                ingested_at=ingested_at,
            )
        )
    return rows, unparsed


def _public_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def _match_files(files: list[dict], year: int, regexes: dict) -> dict[str, dict]:
    matched: dict[str, dict] = {}
    for role, pattern in regexes.items():
        cre = re.compile(pattern)
        for fh in files:
            name = fh.get("name") or ""
            if cre.search(name):
                # Prefer the file whose captured year matches, else first hit.
                m = cre.search(name)
                if m and m.lastindex and str(year) not in name:
                    continue
                matched[role] = fh
                break
        if role not in matched:
            for fh in files:
                name = fh.get("name") or ""
                if cre.search(name):
                    matched[role] = fh
                    break
    return matched


def _get(session: requests.Session, url: str, receipts: dict) -> Optional[requests.Response]:
    if receipts["_n_http"] >= _max_requests():
        log.warning("usgs_mcs: request cap reached before %s", _public_url(url))
        return None
    receipts["_n_http"] += 1
    rec = {"url": _public_url(url), "status": None, "bytes": 0}
    try:
        resp = session.get(url, timeout=_timeout())
        rec["status"] = resp.status_code
        rec["bytes"] = len(resp.content or b"")
        receipts["requests"].append(rec)
        return resp
    except requests.Timeout:
        rec["status"] = "timeout"
        receipts["requests"].append(rec)
        return None
    except requests.RequestException as exc:
        rec["status"] = f"error:{exc.__class__.__name__}"
        receipts["requests"].append(rec)
        log.warning("usgs_mcs: request failed %s: %s", _public_url(url), exc)
        return None


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _append_parquet(store: Path, new_rows: list[dict]) -> None:
    path = store / "mcs_rows.parquet"
    incoming = pd.DataFrame(new_rows)
    for col in STORE_COLS:
        if col not in incoming.columns:
            incoming[col] = None
    incoming = incoming[STORE_COLS]
    if path.exists():
        existing = pd.read_parquet(path)
        out = pd.concat([existing, incoming], ignore_index=True)
    else:
        out = incoming
    store.mkdir(parents=True, exist_ok=True)
    out.to_parquet(path, index=False)


def collect(store: Optional[Path] = None, session: Optional[requests.Session] = None) -> dict:
    """Ingest the newest T7-shaped MCS edition. Always returns a receipts dict."""
    store_path = _store_dir(store)
    receipts: dict[str, Any] = {
        "status": "ok",
        "requests": [],
        "rows_parsed": {"t7": 0, "fig3_import_sources": 0, "world_production": 0},
        "unparsed_rows": 0,
        "_n_http": 0,
    }
    cfg = load_config()
    parent_id = cfg["sciencebase"]["parent_id"]
    parent_url = os.environ.get(
        "USGS_MCS_PARENT_URL",
        f"{_SCIENCEBASE}/items?parentId={parent_id}&format=json&fields=title,id&max=50",
    )
    own_session = session is None
    sess = session or requests.Session()
    sess.headers["User-Agent"] = _UA
    try:
        parent_resp = _get(sess, parent_url, receipts)
        if parent_resp is None or parent_resp.status_code != 200:
            receipts["status"] = "outage"
            _write_json(store_path / "receipts.json", {k: v for k, v in receipts.items() if k != "_n_http"})
            return receipts
        try:
            parent = parent_resp.json()
        except ValueError:
            receipts["status"] = "outage"
            _write_json(store_path / "receipts.json", {k: v for k, v in receipts.items() if k != "_n_http"})
            return receipts
        editions = discover_editions(parent)
        if not editions:
            receipts["status"] = "outage"
            _write_json(store_path / "receipts.json", {k: v for k, v in receipts.items() if k != "_n_http"})
            return receipts
        chosen = select_ingest_edition(editions, cfg.get("known_editions") or {})
        item_id = chosen["item_id"]
        item_url = f"{_SCIENCEBASE}/item/{item_id}?format=json"
        item_resp = _get(sess, item_url, receipts)
        if item_resp is None or item_resp.status_code != 200:
            receipts["status"] = "outage"
            _write_json(store_path / "receipts.json", {k: v for k, v in receipts.items() if k != "_n_http"})
            return receipts
        item = item_resp.json()
        files = item.get("files") or []
        matched = _match_files(files, int(chosen["year"]), cfg["file_regexes"])
        if "t7" not in matched:
            receipts["status"] = "layout_changed"
            receipts["files"] = [fh.get("name") for fh in files]
            receipts["file_list"] = receipts["files"]
            _write_json(store_path / "receipts.json", {k: v for k, v in receipts.items() if k != "_n_http"})
            return receipts

        bodies: dict[str, bytes] = {}
        shas: dict[str, str] = {}
        names: dict[str, str] = {}
        for role in ("t7", "fig3", "commodities"):
            fh = matched.get(role)
            if not fh:
                continue
            url = fh.get("url") or fh.get("downloadUri")
            if not url:
                continue
            resp = _get(sess, url, receipts)
            if resp is None or resp.status_code != 200:
                log.warning("usgs_mcs: isolated failure downloading %s", role)
                continue
            bodies[role] = resp.content
            shas[role] = hashlib.sha256(resp.content).hexdigest()
            names[role] = fh.get("name") or role

        state_path = store_path / "state.json"
        prior = {}
        if state_path.exists():
            try:
                prior = json.loads(state_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                prior = {}
        prior_shas = (prior.get("files") or {})
        if bodies and all(prior_shas.get(role) == shas.get(role) for role in shas):
            receipts["status"] = "no_change"
            receipts["edition_year"] = chosen["year"]
            _write_json(store_path / "receipts.json", {k: v for k, v in receipts.items() if k != "_n_http"})
            return receipts

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        revision = now
        meta = {
            "source_item_id": item_id,
            "release_revision": revision,
            "ingested_at": now,
        }
        new_rows: list[dict] = []
        if "t7" in bodies:
            t7_rows = parse_t7_csv(
                bodies["t7"],
                edition_year=int(chosen["year"]),
                source_file=names["t7"],
                source_sha256=shas["t7"],
                **meta,
            )
            receipts["rows_parsed"]["t7"] = len(t7_rows)
            new_rows.extend(t7_rows)
        if "fig3" in bodies:
            fig_rows = parse_fig3_csv(
                bodies["fig3"],
                edition_year=int(chosen["year"]),
                source_file=names["fig3"],
                source_sha256=shas["fig3"],
                **meta,
            )
            receipts["rows_parsed"]["fig3_import_sources"] = len(fig_rows)
            new_rows.extend(fig_rows)
        if "commodities" in bodies:
            world_rows, unparsed = parse_commodities_csv(
                bodies["commodities"],
                edition_year=int(chosen["year"]),
                source_file=names["commodities"],
                source_sha256=shas["commodities"],
                **meta,
            )
            receipts["rows_parsed"]["world_production"] = len(world_rows)
            receipts["unparsed_rows"] = unparsed
            new_rows.extend(world_rows)

        if new_rows:
            _append_parquet(store_path, new_rows)
        _write_json(
            state_path,
            {
                "item_id": item_id,
                "edition_year": chosen["year"],
                "files": shas,
                "last_run": now,
            },
        )
        receipts["status"] = "ok"
        receipts["edition_year"] = chosen["year"]
        slim = {k: v for k, v in receipts.items() if k != "_n_http"}
        _write_json(store_path / "receipts.json", slim)
        return receipts
    finally:
        if own_session:
            sess.close()


def main(store: Optional[Path] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    try:
        receipts = collect(store=store)
        log.info("usgs_mcs: status=%s rows=%s", receipts.get("status"), receipts.get("rows_parsed"))
    except Exception as exc:  # noqa: BLE001 — house law: always exit 0
        log.error("usgs_mcs: unexpected failure (non-fatal): %s", exc)
    return 0


def main_exit(store: Optional[Path] = None) -> int:
    return main(store=store)


if __name__ == "__main__":
    sys.exit(main())
