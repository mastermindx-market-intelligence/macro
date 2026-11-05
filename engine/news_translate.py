"""Cached build-time translation for sourced news headlines.

Static pages cannot call a translation API in the browser without exposing a key.
This helper is therefore build-time only: translate the small filtered headline
set, cache by text hash, and degrade to the original English when disabled,
unkeyed, rate-limited, or malformed.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from pathlib import Path

from lib import config

log = logging.getLogger(__name__)

# The Codex tier that carries this lane (operator directive 2026-07-31). Kept as a
# literal rather than an import of engine.codex_provider.TERRA_MODEL: that module
# pulls in the codex_lane runner, and a deepseek host must not pay that import just
# to name a default. tests/test_news_translate_render_gate.py pins the two equal.
CODEX_TERRA_MODEL = "gpt-5.6-terra"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"

# --------------------------------------------------------------------------- #
# The incumbent Fabric application binding.
#
# When the trusted host (or the trusted caller config) selects the shared
# Fabric application transport, the incumbent owner composes the ONLY
# transport this lane may use: no native credential read, no direct client,
# no provider fallback, no resend. An owner refusal degrades to this lane's
# existing unavailable contract (the caller keeps the source text).
#
# ABSENT selection keeps the legacy provider path exactly as it was. A PRESENT
# but invalid selection stays SELECTED with no factory, so the lane refuses
# instead of quietly reverting to a native credential. The selection is read
# through llm_auth's own semantics, so this module keeps NO shadow selector
# of its own: the host environment wins over the caller config, and a present
# invalid/null/empty value refuses. Request content, browser input and cached
# text can never choose a factory, an endpoint or a credential.
# --------------------------------------------------------------------------- #
FABRIC_LANE = "news-translate"
FABRIC_WORKLOAD_PROFILE = "site_batch"

SYSTEM_ZH = (
    "You are a professional financial-news translator. Translate each English "
    "headline or short summary into concise, natural Simplified Chinese. Preserve "
    "ticker symbols, company names when commonly used in English, numbers, and "
    "market terms such as ETF names. Do not add analysis. Return ONLY a JSON array "
    "of strings, exactly one output per input, in the same order."
)

SYSTEM_EN = (
    "You are a professional financial-news translator. Translate each Simplified "
    "Chinese headline or short summary into concise, natural English. Use the "
    "common English names for Chinese companies, institutions and policy terms "
    "(PBOC, CSRC, RRR, A-shares); preserve ticker symbols and numbers. Do not add "
    "analysis. Return ONLY a JSON array of strings, exactly one output per input, "
    "in the same order."
)


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text or "")


def _cjk_ratio(text: str) -> float:
    if not text:
        return 0.0
    return sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff") / len(text)


def _looks_english(text: str) -> bool:
    """A plausible English translation: nonempty, mostly non-CJK (proper nouns may
    keep a few CJK glyphs), and carries at least some latin letters."""
    s = (text or "").strip()
    return bool(s) and _cjk_ratio(s) <= 0.3 and any(c.isascii() and c.isalpha() for c in s)


def _cfg() -> dict:
    cfg = config.load().get("news_translation", {}) or {}
    if not cfg:
        cfg = {
            "enabled": False,
            "provider": "deepseek",
            "api_key_env": "DEEPSEEK_API_KEY",
            "base_url": "https://api.deepseek.com/anthropic",
            "model": DEFAULT_DEEPSEEK_MODEL,
            "cache_dir": "data/news_translation/cache",
        }
    return cfg


def _provider(cfg: dict) -> str:
    """Which transport this config selects: "codex" or "deepseek" (the default).

    One provider at a time, chosen by config — deliberately NOT a failover chain.
    An unreachable provider degrades this lane to cache-only, which is the same
    honest fallback an unkeyed host has always had.
    """
    return str(cfg.get("provider") or "deepseek").strip().lower()


def _model(cfg: dict) -> str:
    """The model id sent on the wire, defaulted per provider.

    Without the per-provider default a codex config that omits `model` would send
    "deepseek-chat"; ``codex_provider.translate_model`` maps that to Terra anyway,
    so the call would work while the usage ledger recorded a model that never ran.
    """
    return str(cfg.get("model") or (
        CODEX_TERRA_MODEL if _provider(cfg) == "codex" else DEFAULT_DEEPSEEK_MODEL))


def translator_ready(cfg: dict | None = None) -> tuple[bool, str]:
    """Whether the CONFIGURED translator can actually run here -> (ready, reason).

    Callers used to preflight with a bare ``config.secret("DEEPSEEK_API_KEY")``.
    That reads as a correct check and is wrong under any other provider: on a
    codex host it warns about a key nothing needs while the lane works fine, and
    it would stay silent in the one case that matters — codex selected and not
    attached. Asking the translator keeps the check from drifting away from the
    client it is checking.

    ``reason`` is an operator sentence in both directions; the ready form names
    the provider and model actually in force, so a log line proves WHICH
    translator ran rather than which one the config hoped for.
    """
    cfg = cfg if cfg is not None else _cfg()
    selected, mode_id = _fabric_selection(cfg)
    if selected:
        # A SELECTED transport owns readiness: the incumbent owner composes the
        # binding, and no native credential is discovered on this path. The
        # readiness allocation is closed before returning — a local close never
        # claims the upstream settled.
        if not _api_fill_allowed(cfg):
            return (False, "the selected Fabric fill is disabled on this host "
                           "(this lane is cache-only)")
        factory = _fabric_factory(cfg, mode_id)
        request_id = _operation_id()
        provider = _fabric_provider(factory, cfg, request_id)
        if provider is None:
            return (False, "the selected Fabric binding is not eligible on this host")
        from engine import llm_auth

        operation = llm_auth.begin_operation(
            [provider], operation_id=request_id, context="news-translate")
        try:
            return (True, f"fabric/{provider.get('model') or ''}")
        finally:
            operation.close()
    provider = _provider(cfg)
    if provider == "codex":
        try:
            from engine import codex_provider as _codex  # noqa: PLC0415
        except Exception as e:  # noqa: BLE001
            return (False, f"codex provider import failed ({type(e).__name__}: {e})")
        if not _codex.is_available():
            return (False, "no attached Codex account on this host (codex CLI "
                           "missing, no login under CODEX_HOME, or "
                           "CODEX_PROVIDER_ENABLED is off)")
        return (True, f"codex/{_model(cfg)}")
    env = str(cfg.get("api_key_env") or "DEEPSEEK_API_KEY")
    if not config.secret(env):
        return (False, f"{env} is not set on this host")
    return (True, f"{provider}/{_model(cfg)}")


def _api_fill_allowed(cfg: dict) -> bool:
    """Cache reads always happen; this gates only the network fill.

    Render-family lanes (render / engine-render / closing-bell, identified by the
    RENDER_NO_DRIP=1 sentinel they already set) are secret-free by design, so the
    API fill there is opt-in via news_translation.render_lanes (default off) —
    per-build LLM spend stays an operator decision. Nightly daily.yml and
    asia-close leave the sentinel unset and are unaffected.
    """
    if not cfg.get("enabled"):
        return False
    if os.environ.get("RENDER_NO_DRIP") == "1" and not cfg.get("render_lanes"):
        return False
    return True


def _cache_dir(cfg: dict) -> Path:
    """The translation cache directory.

    A relative ``cache_dir`` resolves under the repo root (the nightly/render
    lanes, whose cache IS committed). An ABSOLUTE one is taken verbatim, which is
    how a long-running poller keeps its cache off the deployed checkout — that
    tree is hard-reset every few minutes and its ``data/news_translation/cache``
    is git-tracked, so a poller writing there both loses its cache and dirties
    the work-tree (D05 W0 zero-repo-writes law).
    """
    raw = str(cfg.get("cache_dir") or "data/news_translation/cache")
    cdir = Path(raw) if Path(raw).is_absolute() else config.ROOT / raw
    cdir.mkdir(parents=True, exist_ok=True)
    return cdir


def _payload_text(text: str, cfg: dict) -> str:
    """The EXACT string sent to the model for ``text``.

    The batch call truncates to ``max_chars``; the cache must be keyed on THIS,
    not on the caller's original. Keying on the original stored a translation of
    the first N characters under the full text, so every later consumer of the
    SHARED cache — macro_news, china_news — read back a silently truncated
    Chinese string as if it were the whole item. One definition, used by the
    reader, the writer and the sender so they cannot drift apart.
    """
    try:
        max_chars = int(cfg.get("max_chars", 360))
    except (TypeError, ValueError):
        max_chars = 360
    return text[:max_chars] if max_chars > 0 else text


def _create_kwargs(cfg: dict, system: str, user: str) -> dict:
    """Arguments for one messages.create call.

    ``timeout``/``max_retries`` are opt-in per lane: the SDK default is minutes
    plus retries, which is fine inside a nightly build and fatal inside a
    75-second poller tick whose heartbeat only touches after the tick returns —
    one hung endpoint reads to the monitor as a dead daemon.
    """
    kwargs: dict = {
        "model": _model(cfg),
        "max_tokens": int(cfg.get("max_tokens", 3000)),
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    if cfg.get("timeout_s"):
        kwargs["timeout"] = float(cfg["timeout_s"])
    return kwargs


def _record_usage(cfg: dict, resp) -> None:
    """Record spend, unless the caller owns a sink outside the repo.

    ``usage_sink`` set to "none" suppresses the lib.ai_costs write entirely. That
    ledger lives at data/ai_costs/usage.jsonl, which the nightly is the sole
    advancer of; an intraday poller appending to it both violates that law and
    writes inside a checkout that gets hard-reset. Such a caller reports its own
    spend through its own gitignored host state.
    """
    if str(cfg.get("usage_sink", "")).lower() == "none":
        return
    try:
        from lib import ai_costs as _ac  # noqa: PLC0415
        if _provider(cfg) == "codex":
            # infer_provider only knows base_url shapes, and the codex path has no
            # base_url — it would file an attached-subscription turn as metered
            # claude_api. Same vocabulary llm_auth._capture_usage uses for codex.
            _prov, _basis = "codex", "subscription"
        else:
            _prov, _basis = _ac.infer_provider(cfg.get("base_url"))
        _ac.record_response_usage(lane=str(cfg.get("usage_lane", "news-translate")),
                                  response=resp,
                                  model=_model(cfg),
                                  provider=_prov, cost_basis=_basis)
    except Exception:  # noqa: BLE001
        pass


def _key(text: str, target: str = "zh", identity: str = "") -> str:
    """The cache key for one translated item.

    The legacy key is preserved byte-for-byte when no identity is supplied. A
    SELECTED transport adds its own identity, so an entry produced by one
    provider/model/capability is never served to another and can never collide
    with a legacy model label.
    """
    if identity:
        return hashlib.sha1(f"{target}\0{identity}\0{text}".encode("utf-8")).hexdigest()
    return hashlib.sha1(f"{target}\0{text}".encode("utf-8")).hexdigest()


def _read_cache(texts: list[str], cfg: dict, identity: str = "") -> tuple[list[str | None], list[int]]:
    cdir = _cache_dir(cfg)
    out: list[str | None] = []
    missing: list[int] = []
    for i, text in enumerate(texts):
        if not text or _has_cjk(text):
            out.append(text if text else None)
            continue
        path = cdir / f"{_key(_payload_text(text, cfg), 'zh', identity)}.json"
        try:
            if path.exists():
                val = json.loads(path.read_text()).get("text_zh")
                out.append(val if val and _has_cjk(val) else None)
                if out[-1]:
                    continue
        except Exception:  # noqa: BLE001
            pass
        out.append(None)
        missing.append(i)
    return out, missing


def _write_cache(pairs: list[tuple[str, str | None]], cfg: dict, identity: str = "") -> None:
    cdir = _cache_dir(cfg)
    for src, zh in pairs:
        if not src or not zh or not _has_cjk(zh):
            continue
        try:
            sent = _payload_text(src, cfg)
            (cdir / f"{_key(sent, 'zh', identity)}.json").write_text(json.dumps(
                {"text": sent, "text_zh": zh}, ensure_ascii=False))
        except Exception:  # noqa: BLE001
            pass


def _codex_client(cfg: dict):
    """The attached Codex subscription, wearing the Anthropic client shape.

    Operator directive 2026-07-31: the zh wire-headline pass runs on the embedded
    codex subscription instead of DEEPSEEK_API_KEY, which was never provisioned on
    the press host — the lane looked armed in config and shipped English forever.
    ``CodexClient`` exposes the same ``messages.create(model=, max_tokens=, system=,
    messages=)`` surface, so the batch JSON-array protocol above is untouched: only
    the transport moves. Tier is Terra, which already carries the hot-tape wire.

    The import is lazy because ``engine.codex_provider`` drags in the codex_lane
    runner; a deepseek host must neither pay that import nor fail on it.

    Unavailable is a NORMAL outcome, not an error: a runner with no codex login
    returns None here and the lane degrades to cache-only, exactly as an unkeyed
    host always has.
    """
    try:
        from engine import codex_provider as _codex  # noqa: PLC0415
    except Exception as e:  # noqa: BLE001
        log.warning("news translation codex provider unavailable: %s", e)
        return None
    if not _codex.is_available():
        log.warning("news translation: provider is codex but no attached account "
                    "on this host — translation degrades to cache-only")
        return None
    try:
        kw: dict = {"timeout_s": max(1, int(float(cfg.get("timeout_s") or 60)))}
        # Optional: headline translation is mechanical, so a lane on a short tick
        # budget can spend less thinking time per turn.
        effort = str(cfg.get("codex_reasoning_effort") or "").strip()
        if effort:
            kw["reasoning_effort"] = effort
        return _codex.CodexClient(**kw)
    except Exception as e:  # noqa: BLE001
        log.warning("news translation codex client init failed: %s", e)
        return None


def _client(cfg: dict):
    """The legacy direct client — REFUSED once a transport is selected.

    A selected transport owns every model construction in this module: this
    path would read a native credential and build a direct client. Reaching
    this function directly still refuses, so no selected host can discover a
    native credential behind the selection.
    """
    selected, _mode_id = _fabric_selection(cfg)
    if selected:
        return None
    if _provider(cfg) == "codex":
        return _codex_client(cfg)
    key = config.secret(cfg.get("api_key_env", "DEEPSEEK_API_KEY"))
    if not key:
        return None
    try:
        import anthropic
    except ImportError:
        log.warning("anthropic SDK not installed; news translation skipped")
        return None
    try:
        kw: dict = {"api_key": key}
        if cfg.get("base_url"):
            kw["base_url"] = cfg["base_url"]
        # A poller lane sets max_retries=0: the SDK's default retry ladder turns
        # one slow endpoint into several multiples of the timeout, inside a tick
        # that has a heartbeat waiting on it.
        if cfg.get("max_retries") is not None:
            kw["max_retries"] = int(cfg["max_retries"])
        return anthropic.Anthropic(**kw)
    except Exception as e:  # noqa: BLE001
        log.warning("news translation client init failed: %s", e)
        return None


def _extract_array(text: str) -> list | None:
    if not text:
        return None
    s = text.strip()
    if s.startswith("```"):
        parts = s.split("```")
        s = parts[1] if len(parts) > 1 else s.strip("`")
        if s.lstrip().startswith("json"):
            s = s.lstrip()[4:]
    i, j = s.find("["), s.rfind("]")
    if i < 0 or j < i:
        return None
    try:
        arr = json.loads(s[i:j + 1])
    except Exception:  # noqa: BLE001
        return None
    return arr if isinstance(arr, list) else None


def _translate_batch(client, texts: list[str], cfg: dict) -> list[str | None]:
    none = [None] * len(texts)
    payload = [_payload_text(t, cfg) for t in texts]
    user = "Translate this JSON array to Simplified Chinese:\n" + json.dumps(payload, ensure_ascii=False)
    try:
        resp = client.messages.create(**_create_kwargs(cfg, SYSTEM_ZH, user))
        _record_usage(cfg, resp)
        text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")
    except Exception as e:  # noqa: BLE001
        log.warning("news translation batch failed: %s", e)
        return none
    arr = _extract_array(text)
    if arr is None or len(arr) != len(texts):
        log.warning("news translation malformed: got %s for %d inputs",
                    None if arr is None else len(arr), len(texts))
        return none
    out: list[str | None] = []
    for val in arr:
        s = str(val).strip() if val is not None else ""
        out.append(s if _has_cjk(s) else None)
    return out


def translate_to_zh(texts: list[str], cfg: dict | None = None) -> list[str | None]:
    """Translate English news strings to Simplified Chinese, cache-aligned.

    Native Chinese strings pass through. English strings return a cached/API
    translation or None, so callers can fall back to the original text.
    """
    cfg = cfg if cfg is not None else _cfg()
    if not texts:
        return []
    selected, mode_id = _fabric_selection(cfg)
    if selected:
        return _fabric_translate(texts, cfg, mode_id, "zh")
    cached, missing = _read_cache(texts, cfg)
    if not missing or not _api_fill_allowed(cfg):
        return cached
    client = _client(cfg)
    if client is None:
        return cached
    batch_size = max(1, int(cfg.get("batch_size", 16)))
    for start in range(0, len(missing), batch_size):
        idxs = missing[start:start + batch_size]
        src = [texts[i] for i in idxs]
        zh = _translate_batch(client, src, cfg)
        _write_cache(list(zip(src, zh)), cfg)
        for i, val in zip(idxs, zh, strict=False):
            if val:
                cached[i] = val
    return cached


# --------------------------------------------------------------------------- #
# ZH -> EN direction (the china_news page's EN language toggle). Mirrors the
# EN -> ZH path: same cache dir (keys carry target="en"), same client, same
# batch protocol — only the system prompt, cache field and output validator
# differ (a plausible English string instead of a CJK one).
# --------------------------------------------------------------------------- #
def _read_cache_en(texts: list[str], cfg: dict, identity: str = "") -> tuple[list[str | None], list[int]]:
    cdir = _cache_dir(cfg)
    out: list[str | None] = []
    missing: list[int] = []
    for i, text in enumerate(texts):
        if not text or not _has_cjk(text):
            out.append(text if text else None)     # already English -> passthrough
            continue
        path = cdir / f"{_key(_payload_text(text, cfg), 'en', identity)}.json"
        try:
            if path.exists():
                val = json.loads(path.read_text()).get("text_en")
                out.append(val if val and _looks_english(val) else None)
                if out[-1]:
                    continue
        except Exception:  # noqa: BLE001
            pass
        out.append(None)
        missing.append(i)
    return out, missing


def _write_cache_en(pairs: list[tuple[str, str | None]], cfg: dict, identity: str = "") -> None:
    cdir = _cache_dir(cfg)
    for src, en in pairs:
        if not src or not en or not _looks_english(en):
            continue
        try:
            sent = _payload_text(src, cfg)
            (cdir / f"{_key(sent, 'en', identity)}.json").write_text(json.dumps(
                {"text": sent, "text_en": en}, ensure_ascii=False))
        except Exception:  # noqa: BLE001
            pass


def _translate_batch_en(client, texts: list[str], cfg: dict) -> list[str | None]:
    none = [None] * len(texts)
    payload = [_payload_text(t, cfg) for t in texts]
    user = "Translate this JSON array to English:\n" + json.dumps(payload, ensure_ascii=False)
    try:
        resp = client.messages.create(**_create_kwargs(cfg, SYSTEM_EN, user))
        _record_usage(cfg, resp)
        text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")
    except Exception as e:  # noqa: BLE001
        log.warning("news EN-translation batch failed: %s", e)
        return none
    arr = _extract_array(text)
    if arr is None or len(arr) != len(texts):
        log.warning("news EN-translation malformed: got %s for %d inputs",
                    None if arr is None else len(arr), len(texts))
        return none
    out: list[str | None] = []
    for val in arr:
        s = str(val).strip() if val is not None else ""
        out.append(s if _looks_english(s) else None)
    return out


def translate_to_en(texts: list[str], cfg: dict | None = None) -> list[str | None]:
    """Translate Simplified-Chinese news strings to English, cache-aligned.

    English strings pass through unchanged. Chinese strings return a cached/API
    translation or None, so callers can fall back to the original text.
    """
    cfg = cfg if cfg is not None else _cfg()
    if not texts:
        return []
    selected, mode_id = _fabric_selection(cfg)
    if selected:
        return _fabric_translate(texts, cfg, mode_id, "en")
    cached, missing = _read_cache_en(texts, cfg)
    if not missing or not _api_fill_allowed(cfg):
        return cached
    client = _client(cfg)
    if client is None:
        return cached
    batch_size = max(1, int(cfg.get("batch_size", 16)))
    for start in range(0, len(missing), batch_size):
        idxs = missing[start:start + batch_size]
        src = [texts[i] for i in idxs]
        en = _translate_batch_en(client, src, cfg)
        _write_cache_en(list(zip(src, en)), cfg)
        for i, val in zip(idxs, en, strict=False):
            if val:
                cached[i] = val
    return cached


# --------------------------------------------------------------------------- #
# The incumbent Fabric application binding — the only transport a SELECTED
# host may use. See the FABRIC_LANE note at the top of this module.
#
# THE SPEND SINK. Under a selected transport the spend is recorded by the
# incumbent llm_auth writer (make_call), NOT by this lane's own
# ``_record_usage`` — one writer, one row, never two. A caller that declared
# ``usage_sink: "none"`` keeps that declaration: the owner carries it into the
# bound operation and suppresses only its own repository ledger row. This lane
# never adds a second writer to work around it.
# --------------------------------------------------------------------------- #
def _fabric_selection(cfg: dict) -> tuple[bool, str | None]:
    """The trusted selection in force -> (selected, mode_id).

    This lane keeps NO shadow selector of its own: the incumbent owner's own
    semantics decide. The host environment wins over the caller config; a
    PRESENT but invalid/null/empty value stays SELECTED with no mode id, so
    the lane refuses instead of reverting to a native credential; an ABSENT
    selection leaves the legacy path untouched.
    """
    from engine import llm_auth

    try:
        mode_id = llm_auth.application_mode_id(cfg if isinstance(cfg, dict) else {})
    except llm_auth.FabricProviderError:
        return True, None
    if mode_id is None:
        return False, None
    return True, mode_id


def _fabric_factory(cfg: dict, mode_id: str | None):
    """The incumbent owner's factory for the selected mode, or None.

    The owner root is this lane's explicit ``config.ROOT`` — never the owner's
    internal repository root: a recipe conversion must not silently retarget
    the root the caller configured.
    """
    if not mode_id:
        return None
    try:
        from engine.provider_production_modes import make_application_fabric_factory
    except Exception as e:  # noqa: BLE001 — degrade, never raise
        log.warning("news translation: Fabric owner unavailable (%s)", e)
        return None
    try:
        return make_application_fabric_factory(
            mode_id=mode_id, lane=FABRIC_LANE, root=config.ROOT,
            workload_cfg={"workload_profile": FABRIC_WORKLOAD_PROFILE,
                          "provider_order": ["fabric"]},
        )
    except Exception as e:  # noqa: BLE001 — degrade, never raise
        log.warning("news translation: Fabric selection failed (%s)", e)
        return None


def _operation_id() -> str:
    """ONE operation identity for ONE logical batch.

    Allocated once, BEFORE the batch's intentional inference steps and outside
    every retry branch: the incumbent client stamps each intentional step with
    it. A later batch allocates its own.
    """
    return f"{FABRIC_LANE}:{uuid.uuid4().hex[:24]}"


def _fabric_provider(factory, cfg: dict, request_id: str) -> dict | None:
    """Compose ONE turn-scoped Fabric provider through the incumbent owner.

    None when the owner refuses: the lane degrades to its existing unavailable
    contract instead of reaching for a native credential or a direct client.
    The caller's own cfg travels with the binding, so its declared workload
    profile (presence AND value) and its declared spend sink are preserved.
    """
    from engine import llm_auth

    if factory is None:
        return None
    try:
        provider = llm_auth.build_fabric_provider(
            factory, request_id=request_id,
            workload_cfg=cfg if isinstance(cfg, dict) else None)
    except llm_auth.FabricProviderError as exc:
        log.warning("news translation: Fabric binding unavailable (%s)", exc.code)
        return None
    except Exception as e:  # noqa: BLE001 — degrade, never raise
        log.warning("news translation: Fabric binding failed (%s)", e)
        return None
    provider["usage_lane"] = str(cfg.get("usage_lane") or "news-translate")
    return provider


def _fabric_cache_identity(inspected: dict, mode_id: str, cfg: dict, target: str) -> str:
    """The cache identity of the transport that ACTUALLY produced the entry.

    It names the selected mode, the provider, the model, the capability, the
    cost basis, the workload in force and the output contract, so one
    transport's translation is never served to another and can never collide
    with a legacy model label. The transport half of the identity comes from
    the owner's own credential-free inspection, never from the caller.
    """
    policy = inspected.get("workload_policy") or {}
    profiles = policy.get("profiles") or []
    try:
        max_tokens = int(cfg.get("max_tokens", 3000) or 0)
    except (TypeError, ValueError):
        max_tokens = 0
    return "|".join([
        "fabric-v2",
        str(mode_id or ""),
        str(target),
        str(inspected.get("provider") or ""),
        str(inspected.get("model") or ""),
        str(inspected.get("cap_id") or ""),
        str(inspected.get("capability_id") or ""),
        str(inspected.get("cost_basis") or ""),
        str(inspected.get("transport_identity") or ""),
        ",".join(str(p) for p in profiles),
        str(policy.get("policy_revision") or ""),
        str(policy.get("policy_hash") or ""),
        str(max_tokens),
    ])


def _fabric_response_text(resp) -> str:
    """The response's text. Text translation never accepts tools: a tool_use
    block in a translation reply is unsolicited, so the batch is refused
    rather than half-parsed. A truncated reply is refused for the same
    reason — a cut-off answer cannot satisfy the JSON-array contract.
    """
    if getattr(resp, "stop_reason", None) == "max_tokens":
        raise ValueError("fabric_response_truncated")
    blocks = getattr(resp, "content", None)
    if not isinstance(blocks, list):
        raise ValueError("fabric_content_invalid")
    for block in blocks:
        if getattr(block, "type", "") == "tool_use":
            raise ValueError("fabric_tools_unsolicited")
    return "".join(getattr(b, "text", "") for b in blocks
                   if getattr(b, "type", "") == "text")


def _fabric_call_text(provider: dict, cfg: dict, system: str, user: str) -> str | None:
    """ONE Anthropic-shaped batch through the incumbent llm_auth path.

    Returns the reply's text, or None when the operation STOPPED. The
    incumbent wrapper owns the response/model/usage validation, the request
    identity and the uncertainty: an unknown execution, an empty reply, a
    truncated reply or an unsolicited tool ends the operation. This lane never
    retries, falls back to another provider or resends.
    """
    from engine import llm_auth

    def _call(client, model):
        resp = client.messages.create(
            model=model,
            max_tokens=int(cfg.get("max_tokens", 3000)),
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return _fabric_response_text(resp), None, resp

    try:
        text, _reason, _used = llm_auth.make_call(
            [provider], _call, context="news-translate")
    except Exception as e:  # noqa: BLE001 — degrade, never raise
        log.warning("news translation Fabric batch failed (%s)", e)
        return None
    return text


def _fabric_fill_zh(provider: dict, cfg: dict, src: list[str]) -> list[str | None] | None:
    """One EN->ZH batch; None means the operation stopped (no retry/resend)."""
    payload = [_payload_text(t, cfg) for t in src]
    user = ("Translate this JSON array to Simplified Chinese:\n"
            + json.dumps(payload, ensure_ascii=False))
    text = _fabric_call_text(provider, cfg, SYSTEM_ZH, user)
    if text is None:
        return None
    arr = _extract_array(text)
    if arr is None or len(arr) != len(src):
        log.warning("news translation Fabric malformed: got %s for %d inputs",
                    None if arr is None else len(arr), len(src))
        return None
    out: list[str | None] = []
    for val in arr:
        s = str(val).strip() if val is not None else ""
        out.append(s if _has_cjk(s) else None)
    return out


def _fabric_fill_en(provider: dict, cfg: dict, src: list[str]) -> list[str | None] | None:
    """One ZH->EN batch; None means the operation stopped (no retry/resend)."""
    payload = [_payload_text(t, cfg) for t in src]
    user = ("Translate this JSON array to English:\n"
            + json.dumps(payload, ensure_ascii=False))
    text = _fabric_call_text(provider, cfg, SYSTEM_EN, user)
    if text is None:
        return None
    arr = _extract_array(text)
    if arr is None or len(arr) != len(src):
        log.warning("news translation Fabric EN malformed: got %s for %d inputs",
                    None if arr is None else len(arr), len(src))
        return None
    out: list[str | None] = []
    for val in arr:
        s = str(val).strip() if val is not None else ""
        out.append(s if _looks_english(s) else None)
    return out


def _untranslated(texts: list[str], target: str) -> list[str | None]:
    """This lane's existing unavailable contract: no translation, source kept.

    An item already written in the target language is returned unchanged; the
    rest is None, so the caller keeps the source text. No cached output is
    presented as a healthy selection.
    """
    out: list[str | None] = []
    for text in texts:
        native = _has_cjk(text) if target == "zh" else not _has_cjk(text)
        out.append(text if (text and native) else None)
    return out


def _fabric_translate(texts: list[str], cfg: dict, mode_id: str | None,
                      target: str) -> list[str | None]:
    """Translate one logical batch through the incumbent Fabric binding.

    The lane's existing contract is preserved: a list aligned to ``texts``
    where a missing translation is None. Batch order, batch count,
    target-language semantics and the cache are the legacy ones — only the
    transport and the cache identity change.

    The order of the steps is the security order. The owner's credential-free
    inspection names the selected transport FIRST, so a revoked or
    reconfigured owner cannot serve a cached entry; the cache is then read
    under that identity; and only a fill that is actually allowed resolves a
    credential and constructs a client.
    """
    if mode_id is None:
        # SELECTED with no eligible binding: the honest unavailable contract.
        return _untranslated(texts, target)
    factory = _fabric_factory(cfg, mode_id)
    if factory is None:
        return _untranslated(texts, target)
    try:
        inspected = factory.inspect(cfg if isinstance(cfg, dict) else None)
        factory = factory.with_inspection(inspected)
    except Exception as e:  # noqa: BLE001 — the owner refuses; degrade honestly
        log.warning("news translation: Fabric owner refused (%s)", e)
        return _untranslated(texts, target)
    identity = _fabric_cache_identity(inspected, mode_id, cfg, target)
    if target == "zh":
        cached, missing = _read_cache(texts, cfg, identity)
    else:
        cached, missing = _read_cache_en(texts, cfg, identity)
    if not missing or not _api_fill_allowed(cfg):
        return cached

    from engine import llm_auth

    request_id = _operation_id()
    provider = None
    operation = None
    try:
        provider = _fabric_provider(factory, cfg, request_id)
        if provider is None:
            return cached
        operation = llm_auth.begin_operation(
            [provider], operation_id=request_id, context="news-translate")
        batch_size = max(1, int(cfg.get("batch_size", 16)))
        for start in range(0, len(missing), batch_size):
            idxs = missing[start:start + batch_size]
            src = [texts[i] for i in idxs]
            if target == "zh":
                filled = _fabric_fill_zh(provider, cfg, src)
            else:
                filled = _fabric_fill_en(provider, cfg, src)
            if filled is None:
                # The operation stopped: no retry, no fallback, no invented result.
                break
            if target == "zh":
                _write_cache(list(zip(src, filled)), cfg, identity)
            else:
                _write_cache_en(list(zip(src, filled)), cfg, identity)
            for i, val in zip(idxs, filled, strict=False):
                if val:
                    cached[i] = val
        return cached
    finally:
        # EVERY exit closes the bound provider: success, cache-only,
        # unavailable and exception alike. A local close invalidates the
        # retained reference; it never claims the upstream lease released.
        if operation is not None:
            operation.close()
        elif provider is not None:
            llm_auth.close_fabric_provider(provider)
