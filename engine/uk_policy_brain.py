"""UK policy desk — the latest HM Treasury announcement, read in plain words.

LEAF · GATED · DEFAULT-OFF-WITHOUT-KEY · CONTEXT-ONLY · DEGRADE-NEVER-RAISE.

Second jurisdiction under the engine.whitehouse_brain contract (that module's
docstring :1-27 is the reference; it is NOT imported and NOT refactored here).
Polls GOV.UK's keyless public Search/Content APIs for HM Treasury
announcements, keeps its own dedupe state, and asks the model to do exactly two
non-authoritative things over the fetched text: restate it in one plain
sentence, and classify its stance into a closed four-member set.

The MODEL NEVER ORIGINATES ANYTHING. Jurisdiction, issuing body, headline,
source URL, document type, published time, known-at time, staleness and the
panel state are all engine-derived facts. The model may not name a ticker, a
sector, a sanctions fact, a causal relation, a score, a size, a rank, or any
number that is not already in the quoted source text. Nothing in axes / regime
/ conditions / scoring imports this module; it writes a SEPARATE display
artifact (site/uk_policy.json) that only Fed & Policy Watch reads.

Source: GOV.UK, Crown copyright, reused under the Open Government Licence v3.0.
This is context, never advice and never a trade signal.
"""
from __future__ import annotations

import json
import hashlib
import logging
import math
import os
import re
import secrets
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from lib import config

log = logging.getLogger(__name__)

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
       "macro-dashboard/1.0 (+research; uk-policy-desk)")

SEARCH_URL = (
    "https://www.gov.uk/api/search.json?filter_organisations=hm-treasury"
    "&filter_content_purpose_supergroup=news_and_communications"
    "&order=-public_timestamp&count=20"
    "&fields=title,link,public_timestamp,description,content_store_document_type,organisations"
)
CONTENT_URL_BASE = "https://www.gov.uk/api/content"
FALLBACK_ATOM_URL = (
    "https://www.gov.uk/search/news-and-communications.atom"
    "?organisations%5B%5D=hm-treasury"
)

GATE_ENV = "UK_POLICY_DESK_ENABLED"

_STANCES = frozenset({"supportive", "restrictive", "mixed", "routine"})
_STATES = frozenset({"ok", "no_new", "source_outage", "stale", "gate_off", "model_unavailable"})

# GOV.UK content_store_document_type -> (EN label, ZH label). Explicit map — never a
# single hardcoded ZH constant across differing document types.
_DOC_TYPE_ZH = {
    "News Story": "新闻稿",
    "Press Release": "新闻发布",
    "Speech": "演讲",
    "Consultation Outcome": "咨询结果",
    "Policy Paper": "政策文件",
    "Guidance": "指导文件",
    "Statutory Guidance": "法定指导",
    "Independent Report": "独立报告",
    "Corporate Report": "机构报告",
    "Decision": "决定",
    "Notice": "通告",
    "Transparency Data": "透明度数据",
    "Impact Assessment": "影响评估",
    "Statistics": "统计数据",
    "National Statistics": "国家统计数据",
}


def _doc_type_zh(doc_type_en: str | None) -> str:
    """Explicit lookup, never inferred — unmapped types get a labelled fallback
    rather than a wrong translation."""
    if not doc_type_en:
        return "新闻稿"
    return _DOC_TYPE_ZH.get(doc_type_en, f"{doc_type_en}（原文）")


def _typed_state(name: str) -> str:
    """Load-bearing clamp: only a declared desk state may leave this function."""
    return name if name in _STATES else "gate_off"


_BANNED_TERMS = (
    "sanction", "sanctions", "score", "rank", "buy", "sell", "overweight",
    "underweight", "target", "causes", "because of", "will cause",
)
# 2–5 caps: 1-letter tokens ("I") are ordinary English, not tickers.
_TICKER_RE = re.compile(r"\b[A-Z]{2,5}\b")
# Policy acronyms that appear in HM Treasury prose; never treated as invented tickers.
_POLICY_ACRONYMS = frozenset({
    "UK", "GB", "EU", "US", "UN", "IMF", "OECD", "OBR", "HMRC", "GDP", "CPI",
    "RPI", "MPC", "BOE", "VAT", "ISA", "HMT", "FCA", "PRA", "NHS", "MOD",
    "G7", "G20", "FSCS", "DBT", "DWP",
})
_DIGIT_RUN_RE = re.compile(r"\d[\d,.]*")

_DEFAULTS = {
    "enabled": False,
    "max_age_days": 4.0,
    "stale_after_days": 3.0,
    "summary_max_en": 150,
    "summary_max_zh": 70,
    "excerpt_max": 400,
    "timeout": 15,
    "model": "claude-opus-4-8",
    # MO-PAID-023_FIX_R3 D1 — bound the SDK call: whitehouse-sentinel.yml gives
    # the job 10 minutes (`:28`), but the SDK default is 600s with 2 retries —
    # a single stalled rung eats the whole cycle. llm_auth._client_tuning_kwargs
    # consumes `client_timeout_s` (float) and `client_max_retries` (int); both
    # keys here keep the per-rung wall clock inside the 10-min budget.
    "client_timeout_s": 15,
    "client_max_retries": 0,
}

# MO-PAID-023_FIX_R3 D4 — cap repeated billing of a permanently-broken item.
# max_age_days × hourly cycles ≈ 96 calls over 4 days for one stuck item. The
# upstream model can't ever serve it (a 401 cascade never recovers on its own),
# so the desk would keep hammering `site/uk_policy.json` as `model_unavailable`
# forever. After MODEL_ATTEMPT_CAP failures we mark the item seen with
# `model_unavailable=True, model_attempts=N` so the next hourly cycle skips
# it (new_items filters out seen IDs) and the served chip stays the truthful
# "unavailable". A successful evaluate does NOT reset the counter — the item
# is now seen with its stance (R5) and stops cycling regardless.
MODEL_ATTEMPT_CAP = 3


# --------------------------------------------------------------------------- #
# config + gate
# --------------------------------------------------------------------------- #
def _cfg() -> dict:
    try:
        return {**_DEFAULTS, **(config.load().get("uk_policy_desk") or {})}
    except Exception:  # noqa: BLE001
        return dict(_DEFAULTS)


def _provider(cfg: dict) -> tuple[str, str, str] | None:
    """(provider, credential, model) for the first available provider, or None.
    Mirrors engine.whitehouse_brain._provider's ladder exactly."""
    import os

    model = cfg.get("model", _DEFAULTS["model"])
    tok = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if tok:
        return ("oauth", tok, model)
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return ("anthropic", key, model)
    key = os.environ.get("DEEPSEEK_API_KEY")
    if key:
        return ("deepseek", key, "deepseek-v4-pro")
    return None


def enabled() -> bool:
    """Desk gate plus selected readiness, or the incumbent native credential."""
    import os

    cfg = _cfg()
    on = bool(cfg.get("enabled", False)) or os.environ.get(GATE_ENV) == "1"
    if not on:
        return False
    try:
        mode = _application_mode(cfg)
        if mode is not None:
            _selected_factory(cfg, mode)
            return True
    except Exception:
        return False
    return _provider(cfg) is not None


def provider_label(cfg: dict | None = None) -> str:
    cfg = cfg or _cfg()
    try:
        mode = _application_mode(cfg)
        if mode is not None:
            _selected_factory(cfg, mode)
            return "assistant"
    except Exception:
        return ""
    prov = _provider(cfg)
    if prov is None:
        return ""
    name, _cred, _model = prov
    # Customer surface never prints a model slug; truthiness only.
    labels = {"oauth": "assistant", "anthropic": "assistant", "deepseek": "assistant"}
    return labels.get(name, "assistant")


# --------------------------------------------------------------------------- #
# fetch + parse (mirrors engine.whitehouse_feed's shape; not imported/refactored)
# --------------------------------------------------------------------------- #
def _fetch(url: str, timeout: float = 15) -> bytes | None:
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:  # noqa: BLE001 — degrade, never raise
        log.debug("uk_policy fetch failed %s (%s)", url, e)
        return None


def _to_iso(ts: object) -> str:
    raw = str(ts or "").strip()
    if not raw:
        return ""
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:  # noqa: BLE001
        return ""


def _clean(text: object, limit: int = 4000) -> str:
    t = str(text or "")
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:limit]


def _slug_id(url: str, published: str) -> str:
    try:
        seg = [p for p in urlparse(url).path.split("/") if p]
        slug = seg[-1] if seg else "item"
    except Exception:  # noqa: BLE001
        slug = "item"
    slug = re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-")[:80] or "item"
    day = (published or "")[:10] or "undated"
    return f"uk-{day}-{slug}"


def _parse_search_results(raw: bytes) -> list[dict]:
    out: list[dict] = []
    try:
        data = json.loads(raw)
    except Exception as e:  # noqa: BLE001
        log.debug("uk_policy parse error (%s)", e)
        return out
    for it in (data.get("results") or []):
        title = _clean(it.get("title"))
        link = str(it.get("link") or "")
        if not title or not link:
            continue
        url = link if link.startswith("http") else f"https://www.gov.uk{link}"
        published = _to_iso(it.get("public_timestamp"))
        doc_type = _clean(it.get("content_store_document_type")).replace("_", " ").title()
        body_text = _clean(it.get("description"), limit=4000)
        out.append({
            "id": _slug_id(url, published),
            "title": title,
            "url": url,
            "published": published,
            "section": "news_and_communications",
            "doc_type": doc_type or "News story",
            "body_text": body_text,
        })
    return out


def _in_window(item: dict, cutoff: float) -> bool:
    """True when the item has no usable timestamp, or was published at/after cutoff."""
    try:
        ts = datetime.fromisoformat(item["published"]).timestamp() if item.get("published") else None
    except Exception:  # noqa: BLE001
        ts = None
    return ts is None or ts >= cutoff


def collect(max_age_days: float = 4.0, *, window: bool = True) -> list[dict]:
    """Current HM Treasury GOV.UK announcements, newest-first.

    When window is True, keep the historical age cut (undated items stay).
    When window is False, return every parsed item with no age cut. Never
    raises; returns [] on any failure.
    """
    try:
        raw = _fetch(SEARCH_URL, timeout=_cfg().get("timeout", 15))
        items = _parse_search_results(raw) if raw else []
        if not items:
            raw2 = _fetch(FALLBACK_ATOM_URL, timeout=_cfg().get("timeout", 15))
            items = _parse_atom(raw2) if raw2 else []
        if window:
            cutoff = datetime.now(timezone.utc).timestamp() - max_age_days * 86400
            items = [it for it in items if _in_window(it, cutoff)]
        items.sort(key=lambda x: x.get("published") or "", reverse=True)
        return items
    except Exception as e:  # noqa: BLE001 — degrade, never raise
        log.debug("uk_policy collect failed (%s)", e)
        return []


def _parse_atom(raw: bytes) -> list[dict]:
    out: list[dict] = []
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(raw)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("a:entry", ns):
            title_el = entry.find("a:title", ns)
            link_el = entry.find("a:link", ns)
            updated_el = entry.find("a:updated", ns)
            summary_el = entry.find("a:summary", ns)
            title = _clean(title_el.text if title_el is not None else "")
            url = link_el.get("href") if link_el is not None else ""
            if not title or not url:
                continue
            published = _to_iso(updated_el.text if updated_el is not None else "")
            out.append({
                "id": _slug_id(url, published),
                "title": title,
                "url": url,
                "published": published,
                "section": "news_and_communications",
                "doc_type": "News story",
                "body_text": _clean(summary_el.text if summary_el is not None else "", limit=4000),
            })
    except Exception as e:  # noqa: BLE001
        log.debug("uk_policy atom parse failed (%s)", e)
    return out


def fetch_body(url: str) -> str:
    """Fetch the fuller body via the GOV.UK Content API. Degrades to '' on failure."""
    try:
        path = urlparse(url).path
        raw = _fetch(f"{CONTENT_URL_BASE}{path}", timeout=_cfg().get("timeout", 15))
        if not raw:
            return ""
        data = json.loads(raw)
        details = data.get("details") or {}
        body = details.get("body") or ""
        return _clean(body, limit=8000)
    except Exception as e:  # noqa: BLE001
        log.debug("uk_policy fetch_body failed (%s)", e)
        return ""


def fetch_version(url: str) -> str | None:
    """Document version marker via the GOV.UK Content API: content_id@public_updated_at.
    Degrades to None on any failure — never fabricated."""
    try:
        path = urlparse(url).path
        raw = _fetch(f"{CONTENT_URL_BASE}{path}", timeout=_cfg().get("timeout", 15))
        if not raw:
            return None
        data = json.loads(raw)
        content_id = data.get("content_id")
        updated_at = data.get("public_updated_at") or data.get("updated_at")
        if not content_id and not updated_at:
            return None
        return f"{content_id or 'unknown'}@{updated_at or 'unknown'}"
    except Exception as e:  # noqa: BLE001
        log.debug("uk_policy fetch_version failed (%s)", e)
        return None


# --------------------------------------------------------------------------- #
# dedupe state
# --------------------------------------------------------------------------- #
def _state_path(root: Path) -> Path:
    return Path(root) / "data" / "uk_policy" / "processed.json"


def load_processed(root: Path) -> dict:
    p = _state_path(root)
    try:
        d = json.loads(p.read_text())
        if isinstance(d, dict) and isinstance(d.get("seen"), dict):
            return d
    except Exception:  # noqa: BLE001
        pass
    return {"seen": {}}


def save_processed(root: Path, state: dict) -> None:
    try:
        with _processed_lock(root):
            current = _read_processed_strict(root)
            # Native scheduler snapshots must never erase a selected original
            # claimed or settled by another process since that snapshot.
            merged = {**current, **state,
                "seen": {**current.get("seen", {}), **state.get("seen", {})}}
            if "fabric_operations" in current:
                merged["fabric_operations"] = current["fabric_operations"]
            _write_processed_strict(root, merged)
    except Exception as e:  # noqa: BLE001
        log.warning("uk_policy: processed.json write failed (%s)", e)


_FABRIC_OPERATION_SCHEMA = "mastermind.uk_policy_fabric_operation.v1"


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("uk_policy_state_duplicate_key")
        value[key] = item
    return value


def _read_processed_strict(root: Path) -> dict:
    """The existing processed state is authoritative for selected originals."""
    try:
        raw = _state_path(root).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"seen": {}}
    state = json.loads(raw, object_pairs_hook=_unique_object,
        parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("uk_policy_state_nonfinite")))
    if (not isinstance(state, dict) or not isinstance(state.get("seen"), dict)
            or not isinstance(state.get("attempts", {}), dict)
            or not isinstance(state.get("fabric_operations", {}), dict)):
        raise ValueError("uk_policy_state_invalid")
    for key, entry in state.get("fabric_operations", {}).items():
        if (not isinstance(key, str) or not key or not isinstance(entry, dict)
                or entry.get("schema") != _FABRIC_OPERATION_SCHEMA
                or not isinstance(entry.get("operation_id"), str)
                or re.fullmatch(r"app:[0-9a-f]{32}", entry["operation_id"]) is None
                or not isinstance(entry.get("input_sha256"), str)
                or re.fullmatch(r"[0-9a-f]{64}", entry["input_sha256"]) is None
                or entry.get("state") not in {"pending", "terminal", "held"}
                or entry.get("outcome") not in {"pending", "usable", "invalid", "unavailable"}
                or not isinstance(entry.get("selection"), dict)
                or not isinstance(entry.get("source_identity"), dict)
                or entry["source_identity"].get("id") != key
                or not isinstance(entry.get("record"), dict)
                or entry.get("receipt") is not None and not isinstance(entry["receipt"], dict)):
            raise ValueError("uk_policy_operation_invalid")
    return state


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def _processed_lock(root: Path):
    """Short filesystem transaction only; never held during model I/O."""
    import fcntl

    root = Path(root)
    if not root.is_dir():
        raise ValueError("uk_policy_existing_state_root_required")
    parent = _state_path(root).parent
    parent.mkdir(parents=True, exist_ok=True)
    # An earlier mkdir may be visible even though its parent fsync failed.
    # Re-establish every owned link on every entry, including that recovery
    # case. The caller owns the already-existing repository root itself.
    for directory in (root, root / "data", parent):
        _fsync_directory(directory)
    with (parent / "processed.json.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _write_processed_strict(root: Path, state: dict) -> None:
    """Atomic existing-owner publication, fsync and exact readback, or fail."""
    path = _state_path(root)
    payload = (json.dumps(state, sort_keys=True, indent=2, ensure_ascii=False,
                          allow_nan=False) + "\n").encode("utf-8")
    descriptor, name = tempfile.mkstemp(prefix="processed.json.", suffix=".stage", dir=path.parent)
    stage = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(stage, path)
        _fsync_directory(path.parent)
        if path.read_bytes() != payload or _read_processed_strict(root) != state:
            raise ValueError("uk_policy_state_readback_failed")
    finally:
        stage.unlink(missing_ok=True)


def mark_seen(state: dict, item: dict, **kw) -> None:
    state.setdefault("seen", {})[item["id"]] = {
        "at": datetime.now(timezone.utc).isoformat(),
        **kw,
    }


def new_items(items: list[dict], state: dict) -> list[dict]:
    seen = (state or {}).get("seen", {})
    return [it for it in items if it.get("id") not in seen]


# --------------------------------------------------------------------------- #
# model boundary — clamps enforced in CODE, never trusted from the prompt
# --------------------------------------------------------------------------- #
def _norm_stance(raw: object) -> str:
    s = str(raw or "").strip().lower()
    return s if s in _STANCES else "routine"


def _no_new_numbers(text: object, excerpt: str) -> bool:
    """True if `text` is safe: every digit run in it also appears in `excerpt`."""
    t = str(text or "")
    for m in _DIGIT_RUN_RE.findall(t):
        if m not in excerpt:
            return False
    return True


def _ban_terms(text: object, excerpt: str) -> bool:
    """True if `text` is safe: no banned term or ticker-shaped token the excerpt lacks.

    Terms already in the quoted excerpt are allowed — the model may restate
    'inflation target' when the source said it. It may not introduce one.
    """
    t = str(text or "")
    low = t.lower()
    excerpt_low = excerpt.lower()
    for term in _BANNED_TERMS:
        if term in low and term not in excerpt_low:
            return False
    for tok in _TICKER_RE.findall(t):
        if tok in _POLICY_ACRONYMS:
            continue
        if tok not in excerpt:
            return False
    return True


def _sanitize_field(text: object, excerpt: str) -> str | None:
    if text is None:
        return None
    t = str(text).strip()
    if not t:
        return None
    if not _no_new_numbers(t, excerpt):
        return None
    if not _ban_terms(t, excerpt):
        return None
    return t


_PROMPT_TEMPLATE = """You are reading one UK government announcement. Use only the
text provided. Do not add facts, numbers, companies, tickers, sectors, sanctions or
causes. If the text does not support a stance, answer 'routine'.

Title: {title}
Text: {excerpt}

Reply with strict JSON only:
{{"summary_en": "<one plain sentence restating the text, <= {sum_en} chars>",
  "summary_zh": "<translation of summary_en, <= {sum_zh} chars>",
  "stance": "<one of supportive, restrictive, mixed, routine>",
  "watch_en": "<one context/what-to-watch sentence drawn from the text>",
  "watch_zh": "<translation of watch_en>"}}
"""


def _call_model(item: dict, excerpt: str, cfg: dict, call=None) -> dict:
    """Runs the model call (or the injected `call` stub) and returns a raw dict.
    Never raises — any failure returns an empty dict, which evaluate() treats as
    model_unavailable (stance stays None; no fabricated routine).

    MO-PAID-023_FIX_R1: the real model path now goes through engine.llm_auth
    (build_providers + make_call) — the SAME waterfall engine.whitehouse_brain
    uses — so a 401 on the first provider is marked cold and the call falls
    through to the next rung (e.g. DEEPSEEK_API_KEY after ANTHROPIC_API_KEY).
    The bespoke urllib call to one Anthropic-compatible endpoint is gone; the
    only bespoke urllib calls left in this module are the GOV.UK fetch helpers
    (SEARCH_URL / CONTENT_URL_BASE / FALLBACK_ATOM_URL) which are unrelated.
    llm_auth is imported LAZILY here so the minimal-deps `A-F02-W2-4` CI job
    (which installs only pytest/pyyaml/jinja2) can still import this module
    and run the gate-off test without anthropic on disk.

    MO-PAID-023_FIX_R3 D3: a missing-provider build (no SDK on the runner, no
    credentials, or both) and a reply that lacks the JSON block BOTH used to
    fall through silently — `{}` from this function then hit `not raw` in
    evaluate() and surfaced as `model_unavailable` with no breadcrumb. We now
    emit a WARNING naming the cause BEFORE returning {} so the sentinel log
    tells an operator why the desk is dark instead of looking like a silent
    state. Plain `log.warning` (NOT `::warning` annotation — the GitHub
    annotation hook at tests/test_gh_annotation_line_start.py requires a bare
    print, and a logger prefixes with `WARNING ` which GitHub silently drops).
    """
    # Even a direct/private native call cannot bypass selected durability.
    try:
        if _application_mode(cfg) is not None:
            return {}
    except Exception:
        return {}
    prompt = _PROMPT_TEMPLATE.format(
        title=item.get("title", ""), excerpt=excerpt,
        sum_en=cfg.get("summary_max_en", 150), sum_zh=cfg.get("summary_max_zh", 70),
    )
    try:
        if call is not None:
            raw = call(prompt)
            if isinstance(raw, dict):
                return raw
            text = str(raw or "")
            m = re.search(r"\{.*\}", text, re.S)
            return json.loads(m.group(0)) if m else {}
        # Real waterfall path. Lazy import keeps anthropic out of the minimal-deps
        # import surface (see R2 in MO-PAID-023_FIX_R1).
        from engine import llm_auth

        providers = llm_auth.build_providers(
            cfg,
            opus_model=cfg.get("model", _DEFAULTS["model"]),
            deepseek_model="deepseek-v4-pro",
        )
        if not providers:
            # MO-PAID-023_FIX_R3 D3 — name the likely cause before returning {}.
            # build_providers() returns [] when no credential env-var is set,
            # the anthropic SDK is missing, or no oauth pool key is authorized
            # for this lane. The operator needs at least the category.
            try:
                import anthropic as _an_sdk  # noqa: F401, PLC0415
                _sdk_state = "installed"
            except Exception:
                _sdk_state = "missing"
            creds_present = sum(
                bool(__import__("os").environ.get(v))
                for v in ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY")
            )
            log.warning(
                "uk_policy: build_providers() returned [] "
                "(sdk=%s, credentials_present=%d/3) — skipping model call",
                _sdk_state, creds_present,
            )
            return {}

        max_tokens = int(cfg.get("max_tokens", 600))

        def _do_call(client, model):
            # MUST NOT catch exceptions — make_call catches them and routes
            # 401/rate_limit to the next rung.
            #
            # MO-PAID-023_FIX_R3 D5 — return the 3-tuple (text, reason, resp)
            # the way engine/whitehouse_brain._do_call does, so make_call can
            # capture `resp.usage` into the AI cost ledger (a paid call that
            # never lands a ledger row understates the desk's spend).
            # stop_reason="refusal" returns None with a typed reason (don't
            # bill the empty text as a success); stop_reason="max_tokens"
            # returns the partial text and labels the reason "truncated" so
            # downstream readers can see the cap was hit.
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            sr = getattr(resp, "stop_reason", None)
            if sr == "refusal":
                return None, "stop_refusal", resp
            text = "".join(
                b.text for b in resp.content if getattr(b, "type", "") == "text"
            )
            if not text:
                return None, "empty_reply", resp
            return text, ("truncated" if sr == "max_tokens" else None), resp

        text, reason, used = llm_auth.make_call(
            providers, _do_call, context="uk_policy_brain"
        )
        if not text:
            log.warning("uk_policy model call failed (%s)", reason or "no_text")
            return {}
        if used and used != providers[0]["name"]:
            log.info("uk_policy served_by:%s", used)
        # Parse the text exactly as before: re.search r"\{.*\}" then json.loads.
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            # MO-PAID-023_FIX_R3 D3 — a non-empty reply with no JSON block
            # used to fall through silently. Log the provider label and the
            # first 80 chars so an operator can see whether the model went
            # off-contract (preamble / markdown wrapper / wrong schema).
            log.warning(
                "uk_policy: model reply from '%s' carried no JSON block; "
                "first 80 chars: %.80s",
                used or "?", text,
            )
            return {}
        return json.loads(m.group(0))
    except Exception as e:  # noqa: BLE001
        log.warning("uk_policy model call failed (%s)", e)
        return {}


def _base_record(item: dict, cfg: dict | None = None) -> dict:
    """Engine-derived facts only — no model call, stance stays None."""
    cfg = cfg or _cfg()
    excerpt = _clean(item.get("body_text") or item.get("title") or "", limit=cfg.get("excerpt_max", 400))
    now = datetime.now(timezone.utc)
    try:
        pub_dt = datetime.fromisoformat(item["published"]) if item.get("published") else now
    except Exception:  # noqa: BLE001
        pub_dt = now
    age_days = max(0.0, (now - pub_dt).total_seconds() / 86400.0)
    doc_type_en = item.get("doc_type") or "News story"
    return {
        "schema": "uk_policy/1",
        "jurisdiction_en": "United Kingdom", "jurisdiction_zh": "英国",
        "body_en": "HM Treasury", "body_zh": "英国财政部",
        "source_label": "GOV.UK",
        "headline": item.get("title"),
        "doc_type_en": doc_type_en, "doc_type_zh": _doc_type_zh(doc_type_en),
        "source_url": item.get("url"),
        "doc_version": item.get("doc_version"),
        "published_iso": item.get("published"),
        "known_at_iso": now.isoformat(),
        "age_days": round(age_days, 2),
        "stance": None,
        "model_unavailable": False,
        # MO-PAID-023_FIX_R3 D4 — number of model calls already attempted on
        # this item. Persisted on the record so run() can decide whether to
        # STOP re-calling after MODEL_ATTEMPT_CAP failures (the saved JSON
        # keeps the honest count — only the seen-side `model_attempts` kwarg
        # is what freezes the item in `new_items()`).
        "model_attempts": 0,
        "summary_en": None, "summary_zh": None,
        "watch_en": None, "watch_zh": None,
        "excerpt": excerpt,
        "provider_label": "",
        "generated_utc": now.strftime("%Y-%m-%d %H:%M UTC"),
    }


def _application_mode(cfg: dict) -> str | None:
    from engine import llm_auth
    return llm_auth.application_mode_id(cfg)


def _selected_factory(cfg: dict, mode: str):
    from engine import llm_auth, provider_production_modes as owner

    maximum = cfg.get("max_tokens", 600)
    timeout = cfg.get("client_timeout_s", 15)
    if (type(maximum) is not int or maximum <= 0
            or type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError("uk_policy_request_invalid")
    selected = {**cfg, "provider_order": ["fabric"],
                "client_timeout_s": min(float(timeout), 15.0), "client_max_retries": 0}
    selected.setdefault("workload_profile", "site_batch")
    factory = owner.make_application_fabric_factory(mode_id=mode,
        lane=str(cfg.get("oauth_pool_lane") or cfg.get("usage_lane") or "application"),
        workload_cfg=selected, root=llm_auth._repo_root())
    identity = factory.inspect(selected)
    return factory.with_inspection(identity), selected, identity, maximum


def _selected_input(item: dict, cfg: dict, record: dict):
    prompt = _PROMPT_TEMPLATE.format(title=item.get("title", ""), excerpt=record["excerpt"],
        sum_en=cfg.get("summary_max_en", 150), sum_zh=cfg.get("summary_max_zh", 70))
    source = {"id": item.get("id"), "url": item.get("url"), "doc_version": item.get("doc_version")}
    digest = hashlib.sha256(json.dumps({"source": source, "prompt": prompt,
        "max_tokens": cfg.get("max_tokens", 600)}, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
    return prompt, source, digest


def _unavailable_record(record: dict, reason: str) -> dict:
    return {**record, "model_unavailable": True, "state": "model_unavailable",
            "fabric_selected": True, "fabric_reason": reason}


def _retained_record(entry: dict, digest: str | None = None) -> dict:
    record = dict(entry["record"])
    record["fabric_selected"] = True
    record["fabric_operation"] = {key: entry[key] for key in
        ("schema", "operation_id", "input_sha256", "source_identity", "selection", "state", "outcome", "receipt")}
    if digest is not None and digest != entry["input_sha256"]:
        record["fabric_reason"] = "fabric_original_input_conflict"
    elif entry["state"] in {"pending", "held"}:
        record["fabric_reason"] = "fabric_original_unsettled"
    if record.get("stance") is None:
        record.update(model_unavailable=True, state="model_unavailable")
    return record


def _selected_completion(cfg, mode, route, operation_id, prompt, record):
    """No state owner here: evaluate has already durably claimed this turn."""
    from engine import llm_auth

    factory, selected_cfg, _identity, maximum = route
    provider, error = None, None
    observed = {}
    raw = None

    def complete(client, model):
        response = client.messages.create(model=model, max_tokens=maximum,
            messages=[{"role": "user", "content": prompt}])
        observed["model"] = response.model
        observed["response"] = True
        if (response.stop_reason != "end_turn" or not response.content
                or any(getattr(block, "type", None) != "text" for block in response.content)):
            raise llm_auth.FabricProviderError("fabric_text_completion_required")
        text = "".join(block.text for block in response.content).strip()
        if not text:
            raise llm_auth.FabricProviderError("fabric_text_completion_required")
        return text, None, response

    try:
        if _application_mode(cfg) != mode:
            raise llm_auth.FabricProviderError("fabric_selection_changed")
        provider = llm_auth.build_fabric_provider(factory, request_id=operation_id,
                                                workload_cfg=selected_cfg)
        for key in ("usage_lane", "usage_stage"):
            if selected_cfg.get(key):
                provider[key] = str(selected_cfg[key])
        provider["usage_cycle_id"] = operation_id
        with llm_auth.begin_operation([provider], operation_id=operation_id,
                                     context="uk_policy_brain") as operation:
            text, _reason, _used = llm_auth.make_call(operation.providers, complete,
                                                    context="uk_policy_brain")
            raw = json.loads(text)
    except Exception as exc:  # a selected error never enters the native waterfall
        error = exc
    finally:
        if provider is not None:
            llm_auth.close_fabric_provider(provider)

    failure = provider.get("_fabric_failure") if provider else None
    close = dict(provider.get("_fabric_close") or {}) if provider else {}
    disposition = provider.get("_fabric_native_disposition") if provider else None
    observation = (dict(provider["_fabric_last_observation"])
        if provider and isinstance(provider.get("_fabric_last_observation"), dict) else None)
    unknown = (bool(getattr(error, "effect_unknown", False))
        or bool(getattr(failure, "effect_unknown", False))
        or bool(provider and provider.get("_fabric_pending"))
        or disposition in {"pending", "effect_unknown"}
        or close.get("effect_unknown") is True
        or close.get("disposition") in {"pending", "effect_unknown"})
    receipt = {"operation_id": operation_id,
        "provider": provider.get("provider") if provider else None,
        "model": observed.get("model") or (observation or {}).get("serving_model"),
        "usage": llm_auth.fabric_usage(provider) if provider else None,
        "observed_usage": observation, "effect_unknown": unknown,
        "native_disposition": disposition or ("completed" if observed.get("response")
            else "unavailable" if provider else "not_started"), "close": close}
    result = _unavailable_record(record, "fabric_completion_unavailable")
    outcome = "invalid" if observed.get("response") else "unavailable"
    if (isinstance(raw, dict) and isinstance(raw.get("stance"), str)
            and raw["stance"] in _STANCES):
        summary = _sanitize_field(raw.get("summary_en"), record["excerpt"])
        if summary is not None:
            result = {**record, "stance": raw["stance"], "summary_en": summary,
                "summary_zh": _sanitize_field(raw.get("summary_zh"), record["excerpt"]),
                "watch_en": _sanitize_field(raw.get("watch_en"), record["excerpt"]),
                "watch_zh": _sanitize_field(raw.get("watch_zh"), record["excerpt"]),
                "provider_label": "assistant", "fabric_selected": True,
                "state": "stale" if record.get("age_days", 0) > cfg.get("stale_after_days", 3.0) else "ok"}
            outcome = "usable"
    result["serving_model"] = receipt["model"]
    return result, receipt, "held" if unknown else "terminal", outcome


def _evaluate_selected(item, cfg, root, record, mode, persist):
    if not persist:
        return _unavailable_record(record, "fabric_durable_state_required")
    try:
        route = _selected_factory(cfg, mode)
        prompt, source, digest = _selected_input(item, cfg, record)
        if not isinstance(item.get("id"), str) or not item["id"]:
            raise ValueError("uk_policy_item_identity_required")
        with _processed_lock(root):
            state = _read_processed_strict(root)
            operations = state.setdefault("fabric_operations", {})
            if item["id"] in operations:
                return _retained_record(operations[item["id"]], digest)
            entry = {"schema": _FABRIC_OPERATION_SCHEMA,
                "operation_id": "app:" + secrets.token_hex(16),
                "input_sha256": digest, "source_identity": source,
                "selection": {"mode_id": mode, "identity": route[2]},
                "state": "pending", "outcome": "pending", "receipt": None,
                "record": _unavailable_record(record, "fabric_original_unsettled")}
            operations[item["id"]] = entry
            _write_processed_strict(root, state)
    except Exception:
        return _unavailable_record(record, "fabric_claim_unavailable")

    # Only a confirmed durable claim reaches credential binding or inference.
    result, receipt, final_state, outcome = _selected_completion(
        cfg, mode, route, entry["operation_id"], prompt, record)
    settled = {**entry, "record": result, "receipt": receipt,
               "state": final_state, "outcome": outcome}
    try:
        with _processed_lock(root):
            current = _read_processed_strict(root)
            original = current.get("fabric_operations", {}).get(item["id"])
            if (not isinstance(original, dict) or original["operation_id"] != entry["operation_id"]
                    or original["input_sha256"] != digest or original["state"] != "pending"):
                raise ValueError("uk_policy_original_state_changed")
            current["fabric_operations"][item["id"]] = settled
            if final_state == "terminal":
                mark_seen(current, item, model_unavailable=outcome != "usable",
                          fabric_operation_id=entry["operation_id"])
            _write_processed_strict(root, current)
    except Exception:
        # Keep a useful observed answer, while exposing unconfirmed publication.
        # The original pending disk entry remains the replay barrier.
        settled["state"] = "held"
        settled["receipt"] = {**receipt, "state_publication": "unconfirmed"}
    return _retained_record(settled)


def evaluate(item: dict, cfg: dict | None = None, root=None, call=None,
             previous_attempts: int = 0, *, persist: bool = False) -> dict:
    """Engine facts + model restate/classify, clamped in code. Never raises.

    MO-PAID-023_FIX_R3 D4: `previous_attempts` is the count already persisted
    in state["seen"][item["id"]].model_attempts for this item. On a failed
    call we record `previous_attempts + 1`; on success the count stays at 0
    (R5 — success resets nothing because the item is then seen with its
    stance, so new_items() will skip it regardless).
    """
    cfg = cfg or _cfg()
    record = _base_record(item, cfg)
    root = Path(root) if root else config.ROOT
    try:
        # Lookup precedes selector resolution, including a removed or invalid
        # selector. Neither a forced cycle nor native credentials release it.
        state = _read_processed_strict(root)
        entry = state.get("fabric_operations", {}).get(item.get("id"))
        if entry is not None:
            return _retained_record(entry, _selected_input(item, cfg, record)[2])
        mode = _application_mode(cfg)
    except Exception:
        return _unavailable_record(record, "fabric_state_or_selection_unavailable")
    if mode is not None:
        return _evaluate_selected(item, cfg, root, record, mode, persist)
    excerpt = record["excerpt"]
    raw = _call_model(item, excerpt, cfg, call=call)
    if not raw:
        record["model_unavailable"] = True
        record["model_attempts"] = int(previous_attempts) + 1
        record["provider_label"] = provider_label(cfg)
        return record
    record["stance"] = _norm_stance(raw.get("stance"))
    record["summary_en"] = _sanitize_field(raw.get("summary_en"), excerpt)
    record["summary_zh"] = _sanitize_field(raw.get("summary_zh"), excerpt)
    record["watch_en"] = _sanitize_field(raw.get("watch_en"), excerpt)
    record["watch_zh"] = _sanitize_field(raw.get("watch_zh"), excerpt)
    record["provider_label"] = provider_label(cfg)
    # successful evaluate: counter stays at previous_attempts on the record
    # (the cycle is data-side irrelevant once stance is set; mark_seen does
    # not persist model_attempts on a success path).
    record["model_attempts"] = int(previous_attempts)
    return record


# --------------------------------------------------------------------------- #
# artifact + state derivation
# --------------------------------------------------------------------------- #
def _artifact_path(root: Path) -> Path:
    return Path(root) / "site" / "uk_policy.json"


def latest(root=None) -> dict | None:
    root = Path(root) if root else config.ROOT
    try:
        d = json.loads(_artifact_path(root).read_text())
        return d if isinstance(d, dict) else None
    except Exception:  # noqa: BLE001
        return None


def _persist(record: dict, root: Path) -> None:
    try:
        p = _artifact_path(root)
        p.parent.mkdir(parents=True, exist_ok=True)
        clean = {k: v for k, v in record.items() if k != "raw_text"}
        p.write_text(json.dumps(clean, indent=2, default=str))
    except Exception as e:  # noqa: BLE001
        log.warning("uk_policy persist failed: %s", e)


def _log_verdict(record: dict) -> None:
    """One INFO line per verdict so a sentinel log always shows the desk's state."""
    log.info("uk_policy: state=%s headline=%r", record.get("state"), record.get("headline"))


def run(persist: bool = True, root=None, force: bool = False, call=None) -> dict | None:
    """Gather -> evaluate -> persist. Returns None when the gate is off (unless
    force). NEVER raises into the caller — every failure degrades to a typed
    'source_outage' record when a prior record exists, else None.

    A reachable feed whose items are all older than the window is not an
    outage. That quiet cycle persists state no_new (from the prior record, or
    from the newest parsed item when there is no prior) and does not call the
    model.
    """
    root = Path(root) if root else config.ROOT
    cfg = _cfg()
    if not force and not enabled():
        return None
    try:
        state = load_processed(root)
        max_age = cfg.get("max_age_days", 4.0)
        cutoff = datetime.now(timezone.utc).timestamp() - max_age * 86400
        all_items = collect(max_age, window=False)
        items = [it for it in all_items if _in_window(it, cutoff)]
        prior = latest(root)
        if not all_items:
            log.warning(
                "uk_policy: feed empty — search and atom returned nothing; %s",
                "prior kept as source_outage" if prior else "no prior, nothing written",
            )
            record = dict(prior) if prior else None
            if record is not None:
                record["state"] = _typed_state("source_outage")
                if persist:
                    _persist(record, root)
                _log_verdict(record)
            return record
        if not items:
            # Reachable feed, nothing inside the window. Do not spend a model call.
            record = dict(prior) if prior else _base_record(all_items[0], cfg)
            record["state"] = _typed_state("no_new")
            if persist:
                _persist(record, root)
            log.info(
                "uk_policy: state=no_new (quiet window %.1fd) headline=%r",
                max_age, record.get("headline"),
            )
            return record
        fresh = new_items(items, state)
        if not fresh:
            # Do not spend a model call to label "no new announcement".
            original = state.get("fabric_operations", {}).get(items[0].get("id"))
            record = (_retained_record(original) if original is not None
                      else dict(prior) if prior else _base_record(items[0], cfg))
            record["state"] = _typed_state("model_unavailable" if original is not None
                and record.get("stance") is None else "no_new")
            if persist:
                _persist(record, root)
            _log_verdict(record)
            return record
        item = fresh[0]
        item = dict(item)
        if not item.get("body_text"):
            item["body_text"] = fetch_body(item["url"]) or item.get("title", "")
        if not item.get("doc_version"):
            item["doc_version"] = fetch_version(item["url"])
        # MO-PAID-023_FIX_R3 D4 — read the running attempt count for this item
        # from a separate `state["attempts"]` dict (NOT from state["seen"] —
        # seen is reserved for the mark_seen contract, and writing a partial
        # seen entry would filter the item out of new_items() before the cap
        # is reached). The attempts dict is monotonic across cycles; only the
        # cap-hit cycle writes the count into state["seen"] via mark_seen.
        attempts_map = state.setdefault("attempts", {})
        try:
            previous_attempts = int(attempts_map.get(item["id"], 0) or 0)
        except Exception:  # noqa: BLE001
            previous_attempts = 0
        record = evaluate(item, cfg, root, call=call, previous_attempts=previous_attempts, persist=persist)
        stale_after = cfg.get("stale_after_days", 3.0)
        if record.get("stance") is None:
            record["state"] = _typed_state("model_unavailable")
        else:
            record["state"] = _typed_state(
                "stale" if record.get("age_days", 0.0) > stale_after else "ok"
            )
        if record.get("fabric_selected"):
            # evaluate owns selected claim/settlement. This pre-I/O native
            # scheduler snapshot must never overwrite that transaction.
            if persist:
                _persist(record, root)
            _log_verdict(record)
            return record
        # MO-PAID-023_FIX_R1 S4 — only mark the item SEEN when evaluate produced a
        # stance (i.e. the model call succeeded). A model_unavailable item stays
        # UNSEEN so the next cycle retries it instead of relabelling the cached
        # failure. The model_unavailable record is still persisted (R5) so the
        # page continues to show the honest state.
        #
        # MO-PAID-023_FIX_R3 D4 — but a permanently-broken item would loop
        # forever under S4 (4 days × 24 cycles ≈ 96 paid calls on the same
        # 401 cascade). Once the persisted model_attempts reaches
        # MODEL_ATTEMPT_CAP we mark the item seen with model_unavailable=True
        # so new_items() skips it from then on and the served chip stays the
        # truthful "unavailable" until the operator rotates credentials. A
        # successful evaluate does NOT reset the counter (R5 — the item is
        # then seen with its stance and stops cycling regardless).
        attempts_now = int(record.get("model_attempts", 0) or 0)
        if record.get("stance") is not None:
            mark_seen(state, item)
            # Mirror the running counter into seen for the success path too,
            # so an operator inspecting state["seen"][id]["model_attempts"]
            # can still see how many failures preceded the recovery (R5:
            # "the counter is not reset" — the value is preserved verbatim).
            if attempts_now > 0:
                state["seen"][item["id"]]["model_attempts"] = attempts_now
            if persist:
                save_processed(root, state)
        elif attempts_now >= MODEL_ATTEMPT_CAP:
            mark_seen(
                state, item,
                model_unavailable=True,
                model_attempts=attempts_now,
            )
            if persist:
                save_processed(root, state)
            log.warning(
                "uk_policy: item %s reached model_attempts=%d (>= %d); "
                "stopping re-calls until credentials are rotated",
                item["id"], attempts_now, MODEL_ATTEMPT_CAP,
            )
        else:
            # Pre-cap failed cycle — persist the running counter so the next
            # cycle can resume from the right value. The item itself stays
            # UNSEEN so new_items() keeps including it.
            attempts_map[item["id"]] = attempts_now
            if persist:
                save_processed(root, state)
        if persist:
            _persist(record, root)
        _log_verdict(record)
        return record
    except Exception as e:  # noqa: BLE001 — degrade-never-raise
        log.warning("uk_policy run failed: %s", e)
        try:
            prior = latest(root)
            if prior is not None:
                prior = dict(prior)
                prior["state"] = _typed_state("source_outage")
                if persist:
                    _persist(prior, root)
                _log_verdict(prior)
                return prior
        except Exception:  # noqa: BLE001
            pass
        return None
