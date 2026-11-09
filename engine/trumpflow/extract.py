"""TrumpFlow LLM extractor — GROWS the entity graph from unstructured news/filings.

The structured Quiver feeds cannot see private equity-for-partnership stakes, family
LLCs, or pre-IPO/SPAC vehicles — those live only in news/filings. This is the ONE place
an LLM touches raw text, and it is an EXTRACTOR, not an oracle:

  * reads recent Trump-entity items from BOTH the Quiver news feed (data/quiver/news.parquet)
    AND the SEC EDGAR filings (data/trumpflow/edgar_filings.parquet — the EX-99 press-release
    exhibits + 8-K/S-4/425 bodies, fetched as text; the genuinely-early source),
  * asks the model for candidate ownership/investment EDGES, each backed by a verbatim
    quote from the source,
  * REJECTS any edge whose citation is not a verbatim substring of the source text
    (reuses catalyst_tone._norm — the anti-hallucination gate), and
  * writes survivors to data/trumpflow/extracted_edges.jsonl as low-confidence,
    INFERRED-provenance CANDIDATES — NEVER auto-merged into the curated graph. A human
    promotes them into intel.json.

Gated (config trumpflow.extract, default off) + degrades to a no-op without an LLM key:
the graph still works from the curated seed; the LLM is an amplifier, not a dependency.
"""
from __future__ import annotations

import json
import logging
import os
import re
import secrets
import stat
from datetime import datetime, timezone
from pathlib import Path

import requests

from lib import config
from engine import catalyst_tone as _ct

log = logging.getLogger(__name__)

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
# www.sec.gov/Archives rejects the generic repo UA (403) but accepts a clean
# "name email" contact per SEC's fair-access policy. .example.com is a reserved
# placeholder (RFC 2606). The efts.sec.gov FTS endpoint is more lenient (collector uses
# the repo UA there).
_SEC_UA = "macro-dashboard admin@macro-dashboard.example.com"

_RELS = {"CONTROLS", "HOLDS_STAKE", "OPERATED_BY", "FORMED", "LINKED_TO", "MEMBER_OF",
         "ADVISES", "SPUN_OUT", "INVESTS_IN"}

# Trump-family / administration entity keywords used to filter the news feed.
_KEYWORDS = [
    "trump", "eric trump", "donald trump jr", "trump jr", "american bitcoin", "abtc",
    "hut 8", "world liberty", "wlfi", "usd1", "truth social", "trump media", "djt",
    "dominari", "american data centers", "affinity partners", "jared kushner",
]

_SYSTEM = (
    "You extract STRUCTURED ownership / investment relationships involving Donald Trump's "
    "family or the administration from a short news excerpt. Output ONLY JSON: "
    '{"edges":[{"src":"<person or entity>","rel":"<REL>","dst":"<entity>",'
    '"asset_hint":"<what the real asset is, if a brand differs from the underlying>",'
    '"citation":"<a VERBATIM quote from the text that supports this edge>"}]}. '
    f"REL must be one of {sorted(_RELS)}. Emit an edge ONLY if a verbatim quote in the "
    "text supports it; copy that quote exactly into `citation`. Never infer beyond the "
    "text. If nothing investment-relevant is stated, return {\"edges\":[]}."
)


def _cfg() -> dict:
    # reuse the catalyst_tone DeepSeek config (same key / base / model)
    base = dict(_ct._cfg())
    base.update(config.load().get("trumpflow", {}) or {})
    return base


def enabled() -> bool:
    return bool((config.load().get("trumpflow", {}) or {}).get("extract", False))


# --------------------------------------------------------------------------- pure core
def _extract_edges(source_text: str, reply_text: str | None) -> list[dict]:
    """Parse a model reply into verified candidate edges. PURE — no network.
    Any edge whose citation is not a verbatim (normalized) substring of the source is
    dropped (the anti-hallucination gate)."""
    parsed = _ct._extract_json(reply_text or "")
    if not parsed or not isinstance(parsed.get("edges"), list):
        return []
    src_norm = _ct._norm(source_text or "")
    out = []
    for e in parsed["edges"]:
        if not isinstance(e, dict):
            continue
        rel = str(e.get("rel", "")).strip().upper()
        src, dst = str(e.get("src", "")).strip(), str(e.get("dst", "")).strip()
        cite = _ct._norm(e.get("citation", ""))
        if rel not in _RELS or not src or not dst:
            continue
        if len(cite) < 8 or cite not in src_norm:        # citation must be verbatim in source
            continue
        out.append({
            "src": src, "rel": rel, "dst": dst,
            "asset_hint": str(e.get("asset_hint", "")).strip() or None,
            "citation": str(e.get("citation", "")).strip(),
            "provenance": "INFERRED", "confidence": 0.5, "status": "candidate",
        })
    return out


def _key(e: dict) -> str:
    return f"{e['src'].lower()}|{e['rel']}|{e['dst'].lower()}"


# --------------------------------------------------------------------------- io
def _path(root=None):
    return _data_root(root) / "trumpflow" / "extracted_edges.jsonl"


def _data_root(root=None):
    configured = Path(config.ROOT if root is None else root).absolute()
    actual = configured.resolve(strict=True)
    data = Path(config.data_dir()).absolute() if root is None else configured / "data"
    if data.is_relative_to(configured):
        relative = data.relative_to(configured)
    elif data.is_relative_to(actual):
        relative = data.relative_to(actual)
    else:
        # An explicitly configured external store is its own existing owner.
        return data.resolve(strict=True)
    current = actual
    for part in relative.parts:
        if part in (".", ".."):
            raise ValueError("extract_directory_invalid")
        current = current / part
        if current.is_symlink():
            raise ValueError("extract_directory_invalid")
    return current


def _lock_root(root=None):
    actual = Path(config.ROOT if root is None else root).resolve(strict=True)
    data = _data_root(root)
    return actual if data.is_relative_to(actual) else data.resolve(strict=True)


def load_candidates(root=None) -> list[dict]:
    p = _path(root)
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _s(v):
    s = str(v).strip() if v is not None else ""
    return s if s and s.lower() not in ("nan", "none") else None


def _news_items(root=None, limit: int = 40) -> list[dict]:
    try:
        import pandas as pd
        p = (config.data_dir() if root is None else (root / "data")) / "quiver" / "news.parquet"
        if not p.exists():
            return []
        df = pd.read_parquet(p)
    except Exception:  # noqa: BLE001
        return []
    items = []
    for _, r in df.iterrows():
        text = " ".join(str(r.get(k, "")) for k in ("headline", "summary") if r.get(k))
        if any(k in text.lower() for k in _KEYWORDS):
            items.append({"text": text[:2000], "url": _s(r.get("url")), "time": _s(r.get("time")),
                          "source_id": "news:" + (_s(r.get("url")) or text[:60]), "source_type": "news"})
        if len(items) >= limit:
            break
    return items


def _strip_html(html: str, cap: int = 4000) -> str:
    txt = _TAG.sub(" ", html or "")
    for a, b in (("&nbsp;", " "), ("&#160;", " "), ("&amp;", "&"), ("&#39;", "'"), ("&quot;", '"')):
        txt = txt.replace(a, b)
    return _WS.sub(" ", txt).strip()[:cap]


def _fetch_text(url: str | None, cap: int = 4000) -> str | None:
    if not url:
        return None
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": _SEC_UA})
        return _strip_html(r.text, cap) if r.status_code == 200 else None
    except Exception:  # noqa: BLE001
        return None


def _filing_items(root=None, limit: int = 15, max_age_days: int = 45) -> list[dict]:
    """Recent Trump-entity EDGAR filings — fetch the document text (EX-99 press releases +
    8-K/S-4/425 bodies), the genuinely-early source."""
    try:
        import pandas as pd
        p = (config.data_dir() if root is None else (root / "data")) / "trumpflow" / "edgar_filings.parquet"
        if not p.exists():
            return []
        df = pd.read_parquet(p)
    except Exception:  # noqa: BLE001
        return []
    df = df.assign(_d=pd.to_datetime(df["file_date"], errors="coerce")).sort_values("_d", ascending=False)
    cutoff = pd.Timestamp(datetime.now(timezone.utc).date()) - pd.Timedelta(days=max_age_days)
    df = df[df["_d"] >= cutoff]
    ft = df["file_type"].fillna("")
    df = df[ft.str.startswith("EX-99") | df["form"].isin(["8-K", "S-4", "425"])]
    items = []
    for _, r in df.head(limit).iterrows():
        txt = _fetch_text(_s(r.get("url")))
        if txt and len(txt) > 120:
            items.append({"text": txt[:2400], "url": _s(r.get("url")), "time": _s(r.get("file_date")),
                          "source_id": "filing:" + str(r.get("_id")), "source_type": "filing"})
    return items


def _seen_path(root=None):
    directory = _data_root(root) / "trumpflow"
    if directory.is_symlink():
        raise ValueError("extract_directory_invalid")
    return directory / "extract_seen.json"


def _logical_source(source_id):
    return {"task": "trumpflow-extract", "source_id": source_id}


def _seen_document(root=None):
    return _seen_value(_ct._cache_read(_seen_path(root)))


def _seen_value(raw):
    if raw is None:
        return {"schema": "trumpflow.extract_seen.v2", "seen": [], "selected": {}}
    if type(raw) is list:
        if any(type(value) is not str or not value for value in raw):
            raise ValueError("extract_seen_invalid")
        return {"schema": "trumpflow.extract_seen.v2", "seen": sorted(set(raw))[-5000:], "selected": {}}
    if (type(raw) is not dict or set(raw) != {"schema", "seen", "selected"}
            or raw["schema"] != "trumpflow.extract_seen.v2"
            or type(raw["seen"]) is not list or len(raw["seen"]) > 5000
            or any(type(value) is not str or not value for value in raw["seen"])
            or raw["seen"] != sorted(set(raw["seen"])) or type(raw["selected"]) is not dict):
        raise ValueError("extract_seen_invalid")
    operations = set()
    for source_id, record in raw["selected"].items():
        if (type(source_id) is not str or not source_id or len(source_id) > 4096
                or type(record) is not dict or set(record) != {"source", "source_digest", "cache", "delivered"}
                or type(record["delivered"]) is not bool):
            raise ValueError("extract_seen_selected_invalid")
        source = record["source"]
        if (type(source) is not dict or set(source) != {"text", "url", "time", "source_id", "source_type"}
                or source["source_id"] != source_id or source["source_type"] not in {"news", "filing"}
                or type(source["text"]) is not str or not source["text"].strip()
                or len(source["text"].encode()) > 1048576
                or any(source[key] is not None and type(source[key]) is not str for key in ("url", "time"))
                or _ct._cache_hash(source) != record["source_digest"]):
            raise ValueError("extract_seen_source_invalid")
        cache = _ct._fabric_cache_value(record["cache"], _logical_source(source_id))
        if len(cache["entries"]) != 1:
            raise ValueError("extract_seen_operation_invalid")
        row = cache["entries"][0]
        if (row["operation_id"] in operations
                or record["delivered"] and row["state"] != "terminal"):
            raise ValueError("extract_seen_operation_invalid")
        operations.add(row["operation_id"])
    return raw


def _write_seen(document, root=None):
    # A native-only watermark retains its incumbent list representation.
    document["seen"] = sorted(set(document["seen"]))[-5000:]
    _seen_value(document)
    _ct._cache_save(_seen_path(root), document if document["selected"] else document["seen"])


def _load_seen(root=None) -> set:
    document = _seen_document(root)
    return set(document["seen"]) | set(document["selected"])


def _save_seen(seen: set, root=None) -> None:
    with _ct._cache_lock(_seen_path(root), _lock_root(root)):
        document = _seen_document(root)
        document["seen"] = sorted(set(document["seen"]) | set(seen))[-5000:]
        _write_seen(document, root)


def _candidate_bytes(root=None):
    try:
        fd = os.open(_path(root), os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return b""
    with os.fdopen(fd, "rb") as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 64 * 1024 * 1024:
            raise ValueError("extract_candidates_invalid")
        raw = source.read(64 * 1024 * 1024 + 1)
    if len(raw) > 64 * 1024 * 1024 or raw and not raw.endswith(b"\n"):
        raise ValueError("extract_candidates_invalid")
    return raw


def _merge_candidates(new, root=None):
    """Called under the same seen-owner lock for native and selected delivery."""
    current = []
    for line in _candidate_bytes(root).splitlines():
        if not line.strip():
            continue
        row = _ct._cache_decode(line)
        if type(row) is not dict or any(type(row.get(k)) is not str or not row[k] for k in ("src", "rel", "dst")):
            raise ValueError("extract_candidates_invalid")
        current.append(row)
    keys = {_key(row) for row in current}
    added = 0
    for row in new:
        if _key(row) not in keys:
            current.append(row)
            keys.add(_key(row))
            added += 1
    if not added:
        return 0
    raw = b"".join(_ct._cache_json(row) + b"\n" for row in current)
    if len(raw) > 64 * 1024 * 1024:
        raise ValueError("extract_candidates_bound")
    path = _path(root)
    temporary = path.with_name(path.name + ".tmp-" + secrets.token_hex(12))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as target:
            target.write(raw)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
        _ct._cache_sync_directory(path.parent)
        if _candidate_bytes(root) != raw:
            raise ValueError("extract_candidates_readback_mismatch")
    finally:
        if temporary.exists():
            temporary.unlink()
    return added


def _selected_edges(source, text):
    parsed = _ct._extract_json(text)
    if type(parsed) is not dict or set(parsed) != {"edges"} or type(parsed["edges"]) is not list or len(parsed["edges"]) > 256:
        raise ValueError("extract_reply_invalid")
    return _extract_edges(source["text"], text)


def _deliver_selected(source_id, root=None):
    with _ct._cache_lock(_seen_path(root), _lock_root(root)):
        document = _seen_document(root)
        record = document["selected"][source_id]
        row = record["cache"]["entries"][0]
        if record["delivered"]:
            return 0
        if row["state"] != "terminal":
            raise ValueError("fabric_original_held")
        result = row["result"]
        if result is not None and _selected_edges(record["source"], row["text"]) != result:
            raise ValueError("extract_saved_result_invalid")
        source, receipt = record["source"], row["receipt"]
        candidates = [{**edge, "url": source["url"], "source_type": source["source_type"],
            "source_time": source["time"], "extracted_at": receipt["completed_at"],
            "fabric_operation_id": row["operation_id"], "llm_model": receipt["served_model"]}
            for edge in result or []]
        added = _merge_candidates(candidates, root)
        record["delivered"] = True
        document["seen"].append(source_id)
        _write_seen(document, root)
        return added


def _selected_call(item, cfg, root=None):
    source_id = item["source_id"]
    logical = _logical_source(source_id)
    def load_cache():
        record = _seen_document(root)["selected"].get(source_id)
        if record is not None and record["source"] != item:
            raise ValueError("extract_original_input_changed")
        return record["cache"] if record is not None else None
    def store_cache(cache):
        if len(cache["entries"]) != 1:
            raise ValueError("extract_source_already_claimed")
        document = _seen_document(root)
        record = document["selected"].get(source_id)
        if record is not None and record["source"] != item:
            raise ValueError("extract_original_input_changed")
        if record is not None and any(cache["entries"][0][key] != record["cache"]["entries"][0][key]
                for key in ("operation_id", "input_digest")):
            raise ValueError("extract_source_already_claimed")
        document["selected"][source_id] = {"source": item, "source_digest": _ct._cache_hash(item),
            "cache": cache, "delivered": record["delivered"] if record else False}
        _write_seen(document, root)
    return _ct._fabric_cached_document(path=_seen_path(root),
        root=Path(config.ROOT if root is None else root), cache_root=_lock_root(root),
        logical_source=logical, cfg={"max_tokens": 1200, **cfg}, lane="trumpflow-extract",
        system=_SYSTEM, user=f"<doc>\n{item['text']}\n</doc>",
        input_context={"source": item, "relations": sorted(_RELS)},
        validate=lambda text: _selected_edges(item, text), load_cache=load_cache, store_cache=store_cache)


def _call(source_text: str, cfg: dict) -> str | None:
    from engine import llm_auth
    try:
        if llm_auth.application_mode_id(cfg) is not None:
            return None
    except Exception:
        return None
    client = _ct._client(cfg)
    if client is None:
        return None
    try:
        resp = client.messages.create(
            model=cfg.get("llm_model", "deepseek-v4-flash"),
            max_tokens=int(cfg.get("max_tokens", 1200)),
            system=_SYSTEM,
            messages=[{"role": "user", "content": f"<doc>\n{source_text}\n</doc>"}],
        )
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text") or None
    except Exception as e:  # noqa: BLE001
        log.warning("trumpflow extract model call failed (%s)", e)
        return None


def run(root=None, news_limit: int = 40, filing_limit: int = 15) -> dict:
    """Extract candidate edges from recent Trump-entity NEWS + SEC FILINGS. Each candidate
    needs a verbatim citation (anti-hallucination). Gated + degrade-never-raise; watermarked
    so each source is processed once."""
    if not enabled():
        return {"extracted": 0, "reason": "disabled"}
    from engine import llm_auth
    recovered = 0
    try:
        document = _seen_document(root)
        for source_id, record in document["selected"].items():
            if record["cache"]["entries"][0]["state"] != "terminal":
                return {"extracted": 0, "processed": 0, "reason": "fabric_original_held"}
        with _ct._cache_lock(_seen_path(root), _lock_root(root)):
            _merge_candidates([], root)
        for source_id, record in document["selected"].items():
            if not record["delivered"]:
                recovered += _deliver_selected(source_id, root)
        cfg = _cfg()
        selected = llm_auth.application_mode_id(cfg) is not None
        seen = _load_seen(root)
    except Exception:
        return {"extracted": recovered, "processed": 0, "reason": "fabric_state_refused"}
    items = [it for it in (_news_items(root, news_limit) + _filing_items(root, filing_limit))
             if it["source_id"] not in seen]
    if items and not selected and _ct._client(cfg) is None:
        return {"extracted": recovered, "reason": "no_key"}
    new, processed = [], []
    for item in items:
        if selected:
            try:
                result = _selected_call(item, cfg, root)
                if result is None:
                    return {"extracted": recovered, "processed": len(processed), "reason": "fabric_selection_changed"}
                document = _seen_document(root)
                record = document["selected"].get(item["source_id"])
                if record is None or record["cache"]["entries"][0]["state"] != "terminal":
                    return {"extracted": recovered, "processed": len(processed), "reason": result["error"] or "fabric_original_held"}
                recovered += _deliver_selected(item["source_id"], root)
                processed.append(item["source_id"])
                if result["error"]:
                    return {"extracted": recovered, "processed": len(processed), "reason": result["error"]}
            except Exception:
                return {"extracted": recovered, "processed": len(processed), "reason": "fabric_delivery_refused"}
            continue
        processed.append(item["source_id"])
        for e in _extract_edges(item["text"], _call(item["text"], cfg)):
            e.update({"url": item.get("url"), "source_type": item.get("source_type"),
                      "source_time": item.get("time"),
                      "extracted_at": datetime.now(timezone.utc).isoformat()})
            new.append(e)
    if processed and not selected:
        try:
            with _ct._cache_lock(_seen_path(root), _lock_root(root)):
                document = _seen_document(root)
                recovered += _merge_candidates(new, root)
                document["seen"] = sorted(set(document["seen"]) | set(processed))[-5000:]
                _write_seen(document, root)
        except Exception:
            return {"extracted": recovered, "processed": len(processed), "reason": "delivery_refused"}
    log.info("trumpflow extract: %d candidate edge(s) from %d source(s)", recovered, len(processed))
    return {"extracted": recovered, "processed": len(processed), "reason": "ok"}
