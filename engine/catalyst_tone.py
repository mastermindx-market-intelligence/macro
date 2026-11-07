"""Catalyst tone — market/regime narrative DIGEST layer (LLM Tier A).

LEAF · GATED · DEFAULT-OFF · CONTEXT-ONLY. This mirrors the engine/commodity_news.py
contract exactly: it imports nothing from the mechanical core (conditions/cycles/
dislocation/calibrate), and nothing in the scoring path imports it. Every public
function returns plain data or None and NEVER raises into the pipeline — all
network / parse / LLM failures degrade to "no digest".

Role (Tier A of the two-tier LLM design — see memory llm-layer-decision):
  DIGEST one PUBLIC catalyst document (an FOMC statement/minutes, a regulatory
  release, or the catalyst text around a detected dislocation shock) into a small
  typed record:
      tone_score        float [-1,1]  net risk-off impulse: -1 strongly
                                       supportive/dovish/de-escalating ... +1
                                       strongly risk-off/hawkish/escalating
      guidance_direction enum         tightening | easing | on_hold | mixed | unknown
      risk_delta        float [-1,1]  implied change in forward market risk
                                       (-1 risk falling ... +1 risk rising)
      shock_reversible  enum          reversible | persistent | unknown
                                       (the missing dislocation Gate-1 leg: is a
                                       shock a transient washout or a regime break)
      confidence        enum          low | medium | high
      evidence          [{field, quote_span}]  VERBATIM quotes justifying each call

Runs on DeepSeek V4 Flash via its Anthropic-compatible endpoint — the very same
`anthropic` SDK and `client.messages.create(...)` shape commodity_news.py uses,
with `base_url` + `DEEPSEEK_API_KEY` swapped in. Cheap, public-docs-only.

The digest is honest CONTEXT. Promotion of any field to a deterministic feature
(e.g. shock_reversible -> dislocation Gate-1, tone/risk_delta -> a conditions.py
additive lens) happens DOWNSTREAM and is itself gated; THIS module never writes a
score. Safety lives in CODE, never in the prompt:
  (1) tolerant JSON parse (handles ```json fences / surrounding prose),
  (2) schema validation — enums, types, numeric range-clamp,
  (3) CITATION VERIFICATION — every evidence quote_span must be a verbatim
      substring of the source document, else that field is dropped to its neutral
      "unknown" value and flagged,
  (4) code-side confidence floor — below the threshold every interpretive field
      collapses to unknown,
  (5) degrade-never-raise — any failure returns a degraded record or None.
Only PUBLIC source documents are ever sent to the (third-party) model.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import os
import secrets
import stat
from contextlib import contextmanager
from pathlib import Path
from datetime import date, datetime, timezone

from lib import config

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# schema (also used by the validator below)
# --------------------------------------------------------------------------- #
_GUIDANCE = {"tightening", "easing", "on_hold", "mixed", "unknown"}
_REVERSIBLE = {"reversible", "persistent", "unknown"}
_CONF_RANK = {"low": 0, "medium": 1, "high": 2}
# interpretive fields that must be earned by a verbatim citation; the value each
# collapses to when unverified / low-confidence / absent.
_NEUTRAL = {
    "tone_score": 0.0,
    "guidance_direction": "unknown",
    "risk_delta": 0.0,
    "shock_reversible": "unknown",
}

DISCLAIMER_TEXT = (
    "Context only — not a signal. This is a machine DIGEST of a public document, "
    "produced by an AI model after the fact. The tone / guidance / risk / "
    "reversibility readings are background context; they are NOT inputs to any "
    "score, signal or allocation unless a downstream, separately-gated step "
    "promotes a single field, and even then only as one bounded factor. "
    "“unknown” means the evidence was insufficient — the honest answer. Every "
    "non-unknown field is backed by a quote verified to appear verbatim in the "
    "source; unverifiable claims are dropped."
)

CATALYST_SYSTEM = (
    "You DIGEST one public financial/macro document into a small JSON record. This "
    "is annotation metadata only — it never feeds any score, signal or trading "
    "decision directly. Guessing is harmful; abstaining (\"unknown\") is correct.\n\n"
    "Return ONLY a JSON object with these keys:\n"
    "  tone_score: number in [-1,1]. Net risk-off impulse of the document: -1 = "
    "strongly supportive / dovish / de-escalating, 0 = neutral, +1 = strongly "
    "risk-off / hawkish / escalating.\n"
    "  guidance_direction: one of \"tightening\",\"easing\",\"on_hold\",\"mixed\","
    "\"unknown\" — the policy/forward-guidance lean if the document states one.\n"
    "  risk_delta: number in [-1,1]. Implied change to FORWARD market risk: -1 = "
    "risk clearly falling, +1 = risk clearly rising.\n"
    "  shock_reversible: one of \"reversible\",\"persistent\",\"unknown\". ONLY when "
    "the document explains a market shock: \"reversible\" = transient / liquidity / "
    "technical washout likely to retrace; \"persistent\" = a structural or regime "
    "break. Use \"unknown\" if the document is not about a specific shock.\n"
    "  confidence: one of \"low\",\"medium\",\"high\".\n"
    "  evidence: array of {\"field\": <one of the above field names>, \"quote_span\": "
    "<a SHORT EXACT verbatim quote copied character-for-character from the "
    "document>}. Provide one entry for each non-\"unknown\" field.\n\n"
    "Rules:\n"
    "- Output JSON only. No prose, no markdown fences.\n"
    "- For any field you cannot support with a verbatim quote from the document, "
    "use its \"unknown\"/0 value and OMIT it from evidence.\n"
    "- quote_span must be copied EXACTLY from the document (it is checked by code; "
    "a paraphrase will be discarded).\n"
    "- Prefer \"unknown\"/0 over a low-confidence guess."
)


def _cfg() -> dict:
    return config.load().get("catalyst_tone", {}) or {}


def enabled() -> bool:
    return bool(_cfg().get("enabled", False))


def _extraction_model(cfg: dict) -> str:
    """Return the version-pinned extraction model id (W5 — P5 R5).

    Resolution order:
    1. config['llm_models']['extraction']  (version-pinned, authoritative)
    2. cfg['llm_model']                    (catalyst_tone section override)
    3. hardcoded "deepseek-v4-flash"       (emergency fallback)

    Does NOT raise — catalyst_tone may run outside the W5 llm_models requirement.
    """
    llm_models = config.load().get("llm_models") or {}
    if llm_models.get("extraction"):
        return str(llm_models["extraction"])
    if cfg.get("llm_model"):
        return str(cfg["llm_model"])
    return "deepseek-v4-flash"


# --------------------------------------------------------------------------- #
# pure helpers (no network) — independently unit-tested
# --------------------------------------------------------------------------- #
def _repair_json_text(t: str) -> str:
    """Best-effort STRUCTURAL repair of almost-valid model JSON, used only as a
    last resort after strict parsing fails. Fixes the JSON slips models actually
    make: a stray/mismatched closing bracket (e.g. a spurious ``]`` after a scalar
    value — the real failure that left a BTC brief 'unparseable'), brackets left
    open by a truncated reply, and trailing commas. String contents are never
    touched — quote/escape state is tracked so a ``]`` or ``,`` inside a value is
    preserved verbatim."""
    out: list[str] = []
    stack: list[str] = []
    in_str = esc = False
    for ch in t:
        if in_str:
            out.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
        elif ch in "{[":
            stack.append(ch)
            out.append(ch)
        elif ch in "}]":
            if stack and ((ch == "}" and stack[-1] == "{") or (ch == "]" and stack[-1] == "[")):
                stack.pop()
                out.append(ch)
            # else: a closer with no matching opener -> drop the stray char
        else:
            out.append(ch)
    while stack:                                    # close whatever a truncation left open
        out.append("}" if stack.pop() == "{" else "]")
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))   # strip trailing commas


def _extract_json(text: str) -> dict | None:
    """Best-effort parse of a model reply into a dict. Tolerates ```json fences,
    leading/trailing prose, and — as a last resort — light structural repair of
    almost-valid JSON (stray brackets, truncation, trailing commas). Returns None
    on failure (never raises)."""
    if not text:
        return None
    t = text.strip()
    # strip a ```json ... ``` (or bare ```) fence if present
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.DOTALL)
    if m:
        t = m.group(1).strip()
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except (ValueError, TypeError):
        pass
    # fall back to the first {...} block, then to a repaired version of it. The
    # block runs to the last "}" when there is one, else to end-of-text so a
    # TRUNCATED reply (opened but never closed) can still be repaired.
    start = t.find("{")
    if start < 0:
        return None
    end = t.rfind("}")
    block = t[start:end + 1] if end > start else t[start:]
    for candidate in (block, _repair_json_text(block)):
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except (ValueError, TypeError):
            continue
    return None


def _num_clamp(v, lo: float = -1.0, hi: float = 1.0):
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return None


def _validate(parsed: dict) -> dict:
    """Coerce a parsed reply into the canonical record, enums/ranges enforced.
    Unparseable fields fall back to their neutral value (no exception)."""
    out = dict(_NEUTRAL)
    ts = _num_clamp(parsed.get("tone_score"))
    if ts is not None:
        out["tone_score"] = ts
    rd = _num_clamp(parsed.get("risk_delta"))
    if rd is not None:
        out["risk_delta"] = rd
    g = str(parsed.get("guidance_direction", "")).strip().lower()
    out["guidance_direction"] = g if g in _GUIDANCE else "unknown"
    sr = str(parsed.get("shock_reversible", "")).strip().lower()
    out["shock_reversible"] = sr if sr in _REVERSIBLE else "unknown"
    conf = str(parsed.get("confidence", "")).strip().lower()
    out["confidence"] = conf if conf in _CONF_RANK else "low"
    ev = parsed.get("evidence")
    clean_ev = []
    if isinstance(ev, list):
        for e in ev:
            if isinstance(e, dict):
                f = str(e.get("field", "")).strip()
                q = e.get("quote_span")
                if f in _NEUTRAL and isinstance(q, str) and q.strip():
                    clean_ev.append({"field": f, "quote_span": q.strip()})
    out["evidence"] = clean_ev
    return out


def _norm(s: str) -> str:
    """Typography-agnostic normalization for matching a quote against the source:
    lowercase, then collapse every run of non-ASCII-alphanumeric characters
    (whitespace, punctuation, Unicode dashes/quotes/NBSP, and mojibake fragments —
    e.g. the Fed's non-breaking hyphen U+2011 that reaches the reply as 'â€‘') to a
    single space. The actual word/number SEQUENCE must still appear verbatim in the
    source, so the anti-hallucination guarantee holds — only typographic noise is
    normalized away. (Caveat: accented/non-Latin letters in a quote are also dropped;
    fine for the English macro/FOMC docs this is used on, and it's context-only.)"""
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _verify_citations(rec: dict, source_text: str) -> dict:
    """Every interpretive field must be backed by a verbatim quote present in the
    source. Fields without a verified quote collapse to their neutral value and
    are listed in `dropped_fields`. Mutates and returns `rec`."""
    src = _norm(source_text or "")
    verified: set[str] = set()
    kept_ev = []
    for e in rec.get("evidence", []):
        span = _norm(e.get("quote_span", ""))
        if span and len(span) >= 4 and span in src:
            verified.add(e["field"])
            kept_ev.append(e)
    dropped = []
    for field in _NEUTRAL:
        if rec.get(field) != _NEUTRAL[field] and field not in verified:
            rec[field] = _NEUTRAL[field]
            dropped.append(field)
    rec["evidence"] = kept_ev
    rec["dropped_fields"] = dropped
    return rec


def _apply_confidence_floor(rec: dict, threshold: str) -> dict:
    """Below the configured confidence floor, every interpretive field collapses
    to neutral (the call is logged via `confidence_gated`)."""
    if _CONF_RANK.get(rec.get("confidence"), 0) < _CONF_RANK.get(threshold, 2):
        for field in _NEUTRAL:
            rec[field] = _NEUTRAL[field]
        rec["evidence"] = []
        rec["confidence_gated"] = True
    else:
        rec["confidence_gated"] = False
    return rec


# --------------------------------------------------------------------------- #
# content-hash cache — determinism kit (W7 #33)
#
# Graded calls (shock_reversible → spvector veto, tone_score → ledger) MUST be
# reproducible: the SAME document on the SAME day must always yield the SAME
# record. We guarantee this by keying on a SHA-256 of (model, system_prompt,
# user_message) → the reply text is cached in data/catalyst/reply_cache/. A cache
# HIT returns the old bytes directly — no second model call, no sampling noise.
# The file is append-only-per-hash so two runs on the same day cannot diverge.
# --------------------------------------------------------------------------- #
def _prompt_hash(model: str, system: str, user: str) -> str:
    """SHA-256 hex of (model‖system‖user) — key for the reply cache."""
    h = hashlib.sha256()
    for part in (model, system, user):
        h.update(part.encode("utf-8"))
    return h.hexdigest()


def _reply_cache_path(prompt_hash: str, cfg: dict):
    from pathlib import Path
    cdir = config.ROOT / cfg.get("reply_cache_dir", "data/catalyst/reply_cache")
    Path(cdir).mkdir(parents=True, exist_ok=True)
    return Path(cdir) / f"{prompt_hash}.txt"


def _reply_cache_get(prompt_hash: str, cfg: dict) -> str | None:
    """Return cached reply text, or None on miss/error."""
    p = _reply_cache_path(prompt_hash, cfg)
    try:
        return p.read_text() if p.exists() else None
    except Exception:  # noqa: BLE001
        return None


def _reply_cache_put(prompt_hash: str, text: str, cfg: dict) -> None:
    """Write reply text to cache. Idempotent (same hash → same file)."""
    try:
        _reply_cache_path(prompt_hash, cfg).write_text(text)
    except Exception:  # noqa: BLE001
        pass


# Selected results remain in each caller's incumbent cache. These helpers have
# no directory registry, background work, account state or retry authority.
def _cache_json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _cache_hash(value) -> str:
    return hashlib.sha256(_cache_json(value)).hexdigest()


def _cache_decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("fabric_cache_duplicate_key")
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError("fabric_cache_nonfinite")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def _cache_sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def _cache_lock(path, root):
    """Stable inode lock; every directory link is synced before an effect."""
    import fcntl
    root = Path(root).resolve(strict=True)
    path = Path(path).absolute()
    relative = path.parent.relative_to(root)
    if any(part in (".", "..") for part in relative.parts):
        raise ValueError("fabric_cache_directory_invalid")
    current = root
    for part in relative.parts:
        child = current / part
        child.mkdir(exist_ok=True)
        if child.is_symlink() or not child.is_dir():
            raise ValueError("fabric_cache_directory_invalid")
        _cache_sync_directory(current)
        current = child
    _cache_sync_directory(current)
    fd = os.open(str(path) + ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("fabric_cache_lock_invalid")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _cache_sync_directory(path.parent)
        yield
    finally:
        os.close(fd)


def _cache_read(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return None
    with os.fdopen(fd, "rb") as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 4 * 1024 * 1024:
            raise ValueError("fabric_cache_invalid")
        raw = source.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError("fabric_cache_invalid")
    value = _cache_decode(raw)
    if value is None:
        raise ValueError("fabric_cache_invalid")
    return value


def _cache_save(path, value):
    raw = _cache_json(value)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError("fabric_cache_bound")
    temporary = Path(path).with_name(Path(path).name + ".tmp-" + secrets.token_hex(12))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as target:
            target.write(raw)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
        _cache_sync_directory(Path(path).parent)
        if _cache_json(_cache_read(path)) != raw:
            raise ValueError("fabric_cache_readback_mismatch")
    finally:
        if temporary.exists():
            temporary.unlink()


def _fabric_cache_path(directory, logical_source):
    return Path(directory) / ("fabric-" + _cache_hash(logical_source) + ".json")


def _fabric_cache_state(path, logical_source):
    return _fabric_cache_value(_cache_read(path), logical_source)


_AUTO_CACHE_ENTRY = "macro.specialty_fabric_entry.v2"
_AUTO_CACHE_RECEIPT = "macro.specialty_fabric_receipt.v2"


def _cache_auto_request(operation_id, system, user, maximum):
    from engine import fabric_inference_client as transport
    request_id = operation_id + ":brain:0"
    _, raw = transport._request({"model": None, "request_id": request_id,
        "max_tokens": maximum, "system": system,
        "messages": [{"role": "user", "content": user}]}, None, False)
    original = transport._load_json(raw, unknown=False)
    return original, {"request_id": request_id, "digest": transport._auto_request_digest(original),
                      "max_tokens": maximum}


def _cache_auto_validate(row, original=None):
    """Pure validation inside the incumbent specialty cache owner."""
    from engine import fabric_inference_client as transport
    inspection = transport.validate_auto_inspection(row["inspection"])
    request = row["request"]
    if (row["schema"] != _AUTO_CACHE_ENTRY or type(request) is not dict
            or set(request) != {"request_id", "digest", "max_tokens"}
            or request["request_id"] != row["operation_id"] + ":brain:0"
            or type(request["digest"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", request["digest"]) is None
            or type(request["max_tokens"]) is not int or not 1 <= request["max_tokens"] <= 32768
            or original is not None and (original["max_tokens"] != request["max_tokens"]
                or transport._auto_request_digest(original) != request["digest"])):
        raise ValueError("fabric_cache_request_invalid")
    if row["state"] == "pending":
        return
    receipt = row["receipt"]
    if receipt["schema"] != _AUTO_CACHE_RECEIPT or receipt["requested_model"] is not None:
        raise ValueError("fabric_cache_receipt_invalid")
    document = receipt["application_observation"]
    if document is None:
        if (receipt["routed_request_digest"] is not None or receipt["route_identity"] is not None
                or receipt["provider"] != "unknown" or row["result"] is not None):
            raise ValueError("fabric_cache_observation_invalid")
    else:
        routed = (transport._auto_request_digest(dict(original, model=document["routing"]["selected_model"]))
                  if original is not None else receipt["routed_request_digest"])
        document = transport.validate_auto_observation(document, inspection,
            operation_id=row["operation_id"], request_id=request["request_id"],
            request_digest=request["digest"], routed_request_digest=routed,
            max_tokens=request["max_tokens"], expected_route=receipt["route_identity"],
            require_success=row["result"] is not None)
        if (document["effect_unknown"] and not receipt["effect_unknown"]
                or receipt["routed_request_digest"] != routed
                or receipt["route_identity"] != transport.auto_route_identity(document["routing"])
                or receipt["provider"] != document["routing"]["pool"]
                or receipt["served_model"] != document["serving_model"]
                or receipt["observed_usage"] != {"request_id": request["request_id"],
                    "serving_model": document["serving_model"], **document["usage"]}):
            raise ValueError("fabric_cache_observation_invalid")
    observed, usage = receipt["observed_usage"], receipt["usage"]
    if observed is not None:
        if any(observed[key] is not None and observed[key] > transport.MAX_NATIVE_TOKENS
               for key in ("input_tokens", "output_tokens")):
            raise ValueError("fabric_cache_usage_invalid")
        complete = all(type(observed[key]) is int for key in ("input_tokens", "output_tokens"))
        if usage is None or any(usage["completed_" + key] != (observed[key] if complete else 0)
                              for key in ("input_tokens", "output_tokens")):
            raise ValueError("fabric_cache_usage_invalid")
    elif usage is not None and any(usage["completed_" + key] != 0
                                  for key in ("input_tokens", "output_tokens")):
        raise ValueError("fabric_cache_usage_invalid")
    if (row["state"] == "terminal"
            and (document is not None or receipt["close"]["attempted"] or row["result"] is not None)
            and receipt["close"] != {"disposition": "closed", "closed": True,
                                    "effect_unknown": False, "attempted": True}):
        raise ValueError("fabric_cache_close_invalid")


def _fabric_cache_value(state, logical_source):
    if state is None:
        return {"schema": "macro.specialty_fabric_cache.v1", "source": logical_source, "entries": []}
    if (type(state) is not dict or set(state) != {"schema", "source", "entries"}
            or state["schema"] != "macro.specialty_fabric_cache.v1"
            or state["source"] != logical_source or type(state["entries"]) is not list
            or len(state["entries"]) > 64):
        raise ValueError("fabric_cache_invalid")
    seen, operations = set(), set()
    fields = {"operation_id", "input_digest", "mode_id", "inspection", "state",
              "text", "result", "result_digest", "receipt", "error"}
    for row in state["entries"]:
        automatic = type(row) is dict and row.get("schema") == _AUTO_CACHE_ENTRY
        expected_fields = fields | {"schema", "request"} if automatic else fields
        if (type(row) is not dict or set(row) != expected_fields
                or type(row["operation_id"]) is not str
                or re.fullmatch(r"[a-z][a-z0-9-]{0,31}:[0-9a-f]{32}", row["operation_id"]) is None
                or type(row["input_digest"]) is not str
                or re.fullmatch(r"[0-9a-f]{64}", row["input_digest"]) is None
                or row["input_digest"] in seen
                or row["operation_id"] in operations
                or row["state"] not in ("pending", "held", "terminal")
                or type(row["inspection"]) is not dict
                or type(row["mode_id"]) is not str
                or row["text"] is not None and (type(row["text"]) is not str or len(row["text"]) > 1048576)
                or row["result"] is not None and _cache_hash(row["result"]) != row["result_digest"]
                or row["result"] is None and row["result_digest"] is not None
                or row["state"] == "terminal" and type(row["receipt"]) is not dict):
            raise ValueError("fabric_cache_invalid")
        if (not automatic and row["inspection"].get("schema") ==
                "mastermind.fabric_application_inspection.v2"):
            raise ValueError("fabric_cache_invalid")
        if row["state"] == "pending":
            if any(row[key] is not None for key in ("text", "result", "result_digest", "receipt", "error")):
                raise ValueError("fabric_cache_invalid")
        else:
            receipt = row["receipt"]
            receipt_fields = {"operation_id", "provider", "requested_model", "served_model", "observed_usage", "usage",
                      "close", "effect_unknown", "completed_at"}
            if automatic:
                receipt_fields |= {"schema", "application_observation", "routed_request_digest", "route_identity"}
            if (type(receipt) is not dict or set(receipt) != receipt_fields
                    or receipt["operation_id"] != row["operation_id"]
                    or not automatic and receipt["provider"] != row["inspection"].get("provider")
                    or receipt["requested_model"] != row["inspection"].get("model")
                    or type(receipt["effect_unknown"]) is not bool
                    or type(receipt["completed_at"]) is not str
                    or receipt["served_model"] is not None and type(receipt["served_model"]) is not str):
                raise ValueError("fabric_cache_receipt_invalid")
            close = receipt["close"]
            if (type(close) is not dict or set(close) != {"disposition", "closed", "effect_unknown", "attempted"}
                    or close["disposition"] not in ("not_bound", "local_only", "refused", "pending", "effect_unknown", "closed")
                    or any(type(close[k]) is not bool for k in ("closed", "effect_unknown", "attempted"))
                    or close["closed"] != (close["disposition"] == "closed")
                    or row["state"] == "terminal" and (receipt["effect_unknown"] or close["effect_unknown"]
                        or close["disposition"] in ("pending", "effect_unknown"))
                    or row["state"] == "held" and receipt["effect_unknown"] is not True
                    or row["result"] is not None and (not isinstance(row["text"], str)
                        or not automatic and receipt["served_model"] != receipt["requested_model"])
                    or row["result"] is None and not isinstance(row["error"], str)):
                raise ValueError("fabric_cache_receipt_invalid")
            usage = receipt["usage"]
            observation = receipt["observed_usage"]
            if observation is not None and (type(observation) is not dict
                    or set(observation) != {"request_id", "serving_model", "input_tokens", "output_tokens"}
                    or observation["request_id"] != row["operation_id"] + ":brain:0"
                    or observation["serving_model"] is not None and type(observation["serving_model"]) is not str
                    or any(observation[k] is not None and (type(observation[k]) is not int or observation[k] < 0)
                        for k in ("input_tokens", "output_tokens"))):
                raise ValueError("fabric_cache_observation_invalid")
            if usage is None:
                if close["disposition"] != "not_bound":
                    raise ValueError("fabric_cache_usage_invalid")
            elif (type(usage) is not dict or set(usage) != {"input_tokens", "output_tokens", "usage_state",
                    "completed_input_tokens", "completed_output_tokens"}
                    or usage["usage_state"] not in ("known", "unknown")
                    or any(type(usage[k]) is not int or usage[k] < 0
                        for k in ("completed_input_tokens", "completed_output_tokens"))
                    or any(usage[k] is not None and (type(usage[k]) is not int or usage[k] < 0)
                        for k in ("input_tokens", "output_tokens"))):
                raise ValueError("fabric_cache_usage_invalid")
            if usage is not None and (usage["usage_state"] == "known" and any(
                    usage[k] != usage["completed_" + k] for k in ("input_tokens", "output_tokens"))
                    or usage["usage_state"] == "unknown" and any(
                    usage[k] is not None for k in ("input_tokens", "output_tokens"))):
                raise ValueError("fabric_cache_usage_invalid")
        if automatic:
            _cache_auto_validate(row)
        seen.add(row["input_digest"])
        operations.add(row["operation_id"])
    if sum(row["state"] != "terminal" for row in state["entries"]) > 1:
        raise ValueError("fabric_cache_invalid")
    return state


def _fabric_cached_document(*, path, root, logical_source, cfg, lane,
                            system, user, input_context, validate,
                            load_cache=None, store_cache=None, cache_root=None,
                            allow_truncated=False, local_mutex=None,
                            startup_workload="site_batch"):
    """One caller-owned document operation in its existing cache envelope.

    The caller supplies the source key, cache path, task, prompt and validator.
    Original pending custody is consulted before mutable selection. A stored
    answer is local delivery only; this path never restores a network request.
    """
    from engine import llm_auth
    provider = operation = None
    # Presence must not become native fallback even if the cache is corrupt.
    try:
        if startup_workload not in ("site_batch", "portfolio_analysis"):
            raise ValueError("fabric_startup_workload_invalid")
        if type(allow_truncated) is not bool:
            raise ValueError("fabric_output_policy_invalid")
        if ((load_cache is None) != (store_cache is None)
                or load_cache is not None and (not callable(load_cache) or not callable(store_cache))):
            raise ValueError("fabric_cache_owner_invalid")
        lock_root = root if cache_root is None else cache_root
        @contextmanager
        def locked_cache():
            from contextlib import nullcontext
            with (local_mutex if local_mutex is not None else nullcontext()):
                with _cache_lock(path, lock_root):
                    yield
        def read_state():
            return (_fabric_cache_state(path, logical_source) if load_cache is None
                    else _fabric_cache_value(load_cache(), logical_source))
        def save_state(state):
            _fabric_cache_value(state, logical_source)
            if store_cache is None:
                _cache_save(path, state)
            else:
                store_cache(state)
        exists = os.path.lexists(path)
        if not exists and llm_auth.application_mode_id(cfg) is None:
            return None
        with locked_cache():
            state = read_state()
            held = next((r for r in state["entries"] if r["state"] != "terminal"), None)
            if held is not None:
                return {"result": None, "receipt": held["receipt"], "error": "fabric_original_held"}
        mode_id = llm_auth.application_mode_id(cfg)
        if mode_id is None:
            return None
        selected_cfg = {**cfg, "provider_order": ["fabric"], "usage_lane": lane}
        selected_cfg.setdefault("workload_profile", startup_workload)
        bound = cfg.get("max_tokens", 1500)
        if type(bound) is not int or not 1 <= bound <= 32768:
            raise ValueError("fabric_token_bound_invalid")
        if not isinstance(user, str) or not user.strip() or len(user.encode()) > 1048576:
            raise ValueError("fabric_input_invalid")
        from engine.provider_production_modes import make_application_fabric_factory
        factory = make_application_fabric_factory(mode_id=mode_id, lane=lane,
            workload_cfg={**selected_cfg, "workload_profile": startup_workload}, root=Path(root))
        identity = factory.inspect(selected_cfg)
        automatic = identity.get("schema") == "mastermind.fabric_application_inspection.v2"
        commitment = {"system": system, "user": user, "max_tokens": bound, "context": input_context}
        if automatic:
            commitment["application_inspection"] = identity
            commitment["application_mode"] = mode_id
        if allow_truncated:
            commitment["output_policy"] = "preserve_valid_truncation"
        digest = _cache_hash(commitment)
        with locked_cache():
            state = read_state()
            if any(r["state"] != "terminal" for r in state["entries"]):
                return {"result": None, "receipt": None, "error": "fabric_original_held"}
            prior = next((r for r in state["entries"] if r["input_digest"] == digest), None)
            if prior is not None:
                if prior["mode_id"] != mode_id or prior["inspection"] != identity:
                    raise ValueError("fabric_cache_identity_changed")
                if automatic:
                    original, request = _cache_auto_request(prior["operation_id"], system, user, bound)
                    if prior.get("request") != request:
                        raise ValueError("fabric_cache_request_changed")
                    _cache_auto_validate(prior, original)
                if prior["result"] is not None:
                    if validate(prior["text"]) != prior["result"]:
                        raise ValueError("fabric_cache_result_invalid")
                return {"result": prior["result"], "receipt": prior["receipt"], "error": prior["error"]}
            if len(state["entries"]) >= 64:
                raise ValueError("fabric_cache_bound")
            row = {"operation_id": lane[:32] + ":" + secrets.token_hex(16), "input_digest": digest,
                   "mode_id": mode_id, "inspection": identity, "state": "pending",
                   "text": None, "result": None, "result_digest": None, "receipt": None, "error": None}
            original = None
            if automatic:
                original, request = _cache_auto_request(row["operation_id"], system, user, bound)
                row.update(schema=_AUTO_CACHE_ENTRY, request=request)
            state["entries"].append(row)
            save_state(state)
        # No lock is held across credentials, bind, provider bytes or close.
        text = result = observed_model = None
        error = None
        truncated = False
        try:
            provider = llm_auth.build_fabric_provider(factory.with_inspection(identity),
                request_id=row["operation_id"], workload_cfg=selected_cfg)
            provider["usage_lane"] = lane
            operation = llm_auth.begin_operation([provider], operation_id=row["operation_id"], context=lane)
            def call(client, model):
                nonlocal observed_model, truncated
                response = client.messages.create(model=model, max_tokens=bound, system=system,
                    messages=[{"role": "user", "content": user}])
                observed_model = getattr(response, "model", None)
                stop = getattr(response, "stop_reason", None)
                truncated = stop == "max_tokens" and allow_truncated
                if stop not in ("end_turn", "stop_sequence") and not truncated:
                    raise llm_auth.FabricProviderError("fabric_response_not_complete")
                content = "".join(b.text for b in response.content if getattr(b, "type", "") == "text")
                if not content.strip() or len(content.encode()) > 1048576:
                    raise llm_auth.FabricProviderError("fabric_response_invalid")
                return content, None, response
            text, _, _ = llm_auth.make_call(operation.providers, call, context=lane)
            result = validate(text)
            if result is None or type(result) not in (dict, list):
                raise ValueError("fabric_result_invalid")
            _cache_json(result)
            if truncated:
                error = "truncated"
        except Exception as exc:
            error = getattr(exc, "code", "fabric_result_invalid")
            result = None
        finally:
            if operation is not None:
                operation.close()
            elif provider is not None:
                llm_auth.close_fabric_provider(provider)
        close = (provider.get("_fabric_close") if provider is not None else
                 {"disposition": "not_bound", "closed": False, "effect_unknown": False, "attempted": False})
        unknown = (not isinstance(close, dict) or close.get("effect_unknown") is not False
                   or close.get("disposition") in ("pending", "effect_unknown")
                   or bool(provider and (provider.get("_fabric_pending")
                       or getattr(provider.get("_fabric_failure"), "effect_unknown", False))))
        observation = provider.get("_fabric_last_observation") if provider is not None else None
        if observed_model is None and isinstance(observation, dict):
            observed_model = observation.get("serving_model")
        application_observation = routed_digest = route_identity = None
        actual_provider = identity.get("provider")
        if automatic:
            from engine import fabric_inference_client as transport
            value = llm_auth._fabric_routed_observation(provider,
                llm_auth.fabric_observation(provider), row["request"]["request_id"]) if provider is not None else None
            actual_provider = "unknown"
            if value is not None:
                document = value.document
                routed_digest = transport._auto_request_digest(
                    dict(original, model=document["routing"]["selected_model"]))
                application_observation = transport.validate_auto_observation(document, identity,
                    operation_id=row["operation_id"], request_id=row["request"]["request_id"],
                    request_digest=row["request"]["digest"], routed_request_digest=routed_digest,
                    max_tokens=bound, require_success=result is not None)
                route_identity = transport.auto_route_identity(application_observation["routing"])
                actual_provider = application_observation["routing"]["pool"]
            if (result is not None and application_observation is None
                    or (application_observation is not None or result is not None
                        or isinstance(close, dict) and close.get("attempted") is True)
                    and close != {"disposition": "closed", "closed": True,
                                  "effect_unknown": False, "attempted": True}):
                unknown = True
            if not isinstance(close, dict):
                close = {"disposition": "effect_unknown", "closed": False,
                         "effect_unknown": True, "attempted": True}
        receipt = {"operation_id": row["operation_id"], "provider": actual_provider,
                   "requested_model": identity.get("model"), "served_model": observed_model,
                   "observed_usage": observation,
                   "usage": llm_auth.fabric_usage(provider) if provider is not None else None,
                   "close": close, "effect_unknown": unknown,
                   "completed_at": datetime.now(timezone.utc).isoformat()}
        if automatic:
            receipt.update(schema=_AUTO_CACHE_RECEIPT, application_observation=application_observation,
                           routed_request_digest=routed_digest, route_identity=route_identity)
        row.update(state="held" if unknown else "terminal", text=text, result=result,
                   result_digest=_cache_hash(result) if result is not None else None,
                   receipt=receipt, error=error or ("fabric_close_unknown" if unknown else None))
        with locked_cache():
            state = read_state()
            original = next(r for r in state["entries"] if r["operation_id"] == row["operation_id"])
            if original["state"] != "pending" or original["input_digest"] != digest:
                raise ValueError("fabric_cache_original_changed")
            original.update(row)
            save_state(state)
        return {"result": None if automatic and unknown else result, "receipt": receipt, "error": row["error"]}
    except Exception:
        # Any visible pending claim stays a barrier after lost save/ACK. A
        # cache or selected-mode error must never fall through to an SDK.
        return {"result": None, "receipt": None, "error": "fabric_cache_refused"}


# --------------------------------------------------------------------------- #
# GDELT headline snapshot — determinism kit (W7 #33)
#
# Live GDELT headlines shift intraday, so the same dislocation day can feed a
# DIFFERENT prompt on a second run → non-reproducible shock_reversible. Fix:
# snapshot the fetched headlines to a dated artifact BEFORE scoring; on a cache
# hit for the same date, reuse the snapshot instead of re-fetching.
# --------------------------------------------------------------------------- #
def _gdelt_snapshot_path(today: date, cfg: dict):
    from pathlib import Path
    cdir = config.ROOT / cfg.get("gdelt_snapshot_dir", "data/catalyst/gdelt_snapshots")
    Path(cdir).mkdir(parents=True, exist_ok=True)
    return Path(cdir) / f"gdelt_{today.isoformat()}.json"


def _gdelt_snapshot_get(today: date, cfg: dict) -> list[str] | None:
    """Return cached headlines for `today`, or None on miss."""
    p = _gdelt_snapshot_path(today, cfg)
    try:
        return json.loads(p.read_text()) if p.exists() else None
    except Exception:  # noqa: BLE001
        return None


def _gdelt_snapshot_put(today: date, headlines: list[str], cfg: dict) -> None:
    """Write the headline list for `today`."""
    try:
        _gdelt_snapshot_path(today, cfg).write_text(json.dumps(headlines))
    except Exception:  # noqa: BLE001
        pass


# --------------------------------------------------------------------------- #
# the model call (DeepSeek V4 Flash via the Anthropic-compatible endpoint)
# --------------------------------------------------------------------------- #
def _client(cfg: dict):
    """Build an Anthropic-SDK client pointed at the configured provider. Returns
    None if the SDK or the API key is unavailable (caller degrades)."""
    try:
        import anthropic
    except ImportError:
        return None
    key = config.secret(cfg.get("api_key_env", "DEEPSEEK_API_KEY"))
    if not key:
        return None
    base = cfg.get("llm_base_url", "https://api.deepseek.com/anthropic")
    try:
        return anthropic.Anthropic(base_url=base, api_key=key)
    except Exception:  # noqa: BLE001
        return None


def _call_model(source_text: str, context: str, cfg: dict) -> tuple[str | None, str | None]:
    """Return (reply_text, degraded_reason). Never raises.

    Determinism kit (W7 #33): temperature=0 + seed=0 so the provider samples as
    deterministically as it can. Content-hash cache: the SHA-256 of (model, system,
    user) is checked FIRST — before any client/key check — so a cache hit never
    requires an API key and the same document always yields the SAME graded record.
    """
    from engine import llm_auth
    try:
        if llm_auth.application_mode_id(cfg) is not None:
            return None, "fabric_document_owner_required"
    except Exception:
        return None, "fabric_selection_refused"
    model = _extraction_model(cfg)
    user = (f"Document context: {context}\n\n"
            f"Document text follows between <doc> tags.\n<doc>\n{source_text}\n</doc>")
    # content-hash cache check — BEFORE the client/key check (no key needed on hit)
    phash = _prompt_hash(model, CATALYST_SYSTEM, user)
    cached = _reply_cache_get(phash, cfg)
    if cached is not None:
        log.debug("catalyst_tone: reply cache HIT (%s)", phash[:12])
        return cached, None
    client = _client(cfg)
    if client is None:
        return None, "no_client_or_key"
    from engine import llm_auth

    env_var = cfg.get("api_key_env", "DEEPSEEK_API_KEY")
    providers = [{"name": "deepseek", "env_var": env_var, "cred": "present",
                  "client": client, "model": model, "usage_lane": "catalyst-tone"}]

    def _do_call(_client, _model: str):
        kw: dict = {
            "model": _model,
            "max_tokens": int(cfg.get("max_tokens", 1500)),
            "system": CATALYST_SYSTEM,
            "messages": [{"role": "user", "content": user}],
            "temperature": 0,
        }
        try:
            kw["seed"] = 0
            resp = _client.messages.create(**kw)
        except TypeError:
            del kw["seed"]
            resp = _client.messages.create(**kw)
        if getattr(resp, "stop_reason", None) in ("refusal", "max_tokens"):
            return None, f"stop_{resp.stop_reason}", resp
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        return (text or None), (None if text else "empty_reply"), resp

    try:
        text, reason, _ = llm_auth.make_call(providers, _do_call, context="catalyst_tone")
    except Exception as e:  # noqa: BLE001 — degrade, never raise
        log.warning("catalyst_tone model call failed (%s)", e)
        return None, "llm_error"

    if text:
        _reply_cache_put(phash, text, cfg)
    return text, reason


# --------------------------------------------------------------------------- #
# public: digest one document
# --------------------------------------------------------------------------- #
def digest_document(source_text: str, kind: str = "macro", doc_id: str | None = None,
                    context: str = "", asof: date | str | None = None, *,
                    root=None, fabric_cfg=None) -> dict | None:
    """Digest one PUBLIC catalyst document into the typed record. Returns None
    when the master switch is off; otherwise always returns a record (degraded
    fields flagged). NEVER raises into the pipeline.

    kind: free-form tag (e.g. "fomc_statement", "dislocation", "reg_release").
    context: a one-line hint passed to the model (e.g. "FOMC March 2026 statement"
             or "gold -4.1σ residual shock on 2026-06-12").
    """
    cfg = dict(_cfg())
    if not cfg.get("enabled", False):
        return None
    if fabric_cfg is not None:
        # Trusted composition from another repository caller; feature and
        # validation gates stay Tone's. This cannot provide transport authority.
        if type(fabric_cfg) is not dict or set(fabric_cfg) - {"application_fabric_mode", "workload_profile", "usage_sink"}:
            return None
        cfg.update(fabric_cfg)

    rec = {
        "schema": "catalyst_tone.v1",
        "is_context_only": True,
        "kind": kind,
        "doc_id": doc_id,
        "context": context,
        "asof": (asof.isoformat() if isinstance(asof, date) else asof),
        "digested_at": datetime.now(timezone.utc).isoformat(),
        "model": _extraction_model(cfg),
        "tone_score": 0.0, "guidance_direction": "unknown",
        "risk_delta": 0.0, "shock_reversible": "unknown",
        "confidence": "low", "evidence": [],
        "dropped_fields": [], "confidence_gated": False,
        "degraded_reason": None,
        "disclaimer": DISCLAIMER_TEXT,
    }
    if not source_text or not source_text.strip():
        rec["degraded_reason"] = "empty_source"
        return rec

    actual_root = Path(root) if root is not None else config.ROOT
    logical = {"task": "catalyst-tone", "kind": kind,
               "source_id": doc_id if doc_id is not None else hashlib.sha256(source_text.encode()).hexdigest()}
    cache = _fabric_cache_path(actual_root / cfg.get("reply_cache_dir", "data/catalyst/reply_cache"), logical)
    def validate(text):
        parsed = _extract_json(text)
        if not isinstance(parsed, dict):
            raise ValueError("unparseable_reply")
        result = _validate(parsed)
        _verify_citations(result, source_text)
        _apply_confidence_floor(result, cfg.get("llm_min_confidence", "high"))
        return result
    selected = _fabric_cached_document(path=cache, root=actual_root, logical_source=logical,
        cfg=cfg, lane="catalyst-tone", system=CATALYST_SYSTEM,
        user=f"Document context: {context}\n\nDocument text follows between <doc> tags.\n<doc>\n{source_text}\n</doc>",
        input_context={"source_sha256": hashlib.sha256(source_text.encode()).hexdigest(),
                       "confidence_floor": cfg.get("llm_min_confidence", "high")}, validate=validate)
    if selected is not None:
        receipt = selected["receipt"] or {}
        requested = (receipt.get("requested_model") if receipt.get("schema") == _AUTO_CACHE_RECEIPT
                     else rec["model"])
        rec.update(requested_model=requested, model=receipt.get("served_model"),
                   fabric=receipt, degraded_reason=selected["error"])
        if selected["result"] is not None:
            rec.update(selected["result"])
        if receipt.get("completed_at"):
            rec["digested_at"] = receipt["completed_at"]
        return rec

    reply, reason = _call_model(source_text, context, cfg)
    if reply is None:
        rec["degraded_reason"] = reason
        return rec

    parsed = _extract_json(reply)
    if parsed is None:
        rec["degraded_reason"] = "unparseable_reply"
        return rec

    validated = _validate(parsed)
    rec.update(validated)
    _verify_citations(rec, source_text)                       # drops unverifiable fields
    _apply_confidence_floor(rec, cfg.get("llm_min_confidence", "high"))
    return rec


# --------------------------------------------------------------------------- #
# source fetch + daily snapshot — the most recent FOMC statement, digested once
# per meeting (cached) and surfaced as honest CONTEXT in latest.json.
# --------------------------------------------------------------------------- #
# FOMC decision dates (the statement is released that afternoon). Refresh yearly.
_FOMC_MEETINGS = [
    "2025-09-17", "2025-10-29", "2025-12-10",
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
]
_FOMC_URL = "https://www.federalreserve.gov/newsevents/pressreleases/monetary{ymd}a.htm"


def _as_date(x: date | str | None) -> date | None:
    if x is None:
        return None
    if isinstance(x, datetime):          # datetime / pd.Timestamp -> pure date
        return x.date()                  # (Timestamp subclasses date, so this MUST precede the date check)
    if isinstance(x, date):
        return x
    try:
        return date.fromisoformat(str(x)[:10])
    except ValueError:
        return None


def _recent_fomc(today: date, max_age_days: int) -> date | None:
    """Most recent FOMC decision on/before `today`, if within max_age_days."""
    past = [date.fromisoformat(d) for d in _FOMC_MEETINGS
            if date.fromisoformat(d) <= today]
    if not past:
        return None
    meeting = max(past)
    return meeting if (today - meeting).days <= max_age_days else None


def _html_to_statement(html: str, cap: int) -> str:
    """Crude tag-strip + best-effort trim to the FOMC statement body."""
    t = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.DOTALL | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    starts = ("Recent indicators", "Information received", "The Committee")
    ends = ("Voting for the monetary policy action", "Implementation Note",
            "Last Update", "Board of Governors")
    lo = min((i for i in (t.find(s) for s in starts) if i != -1), default=-1)
    if lo > 0:
        t = t[lo:]
    hi = min((i for i in (t.find(e) for e in ends) if i != -1), default=-1)
    if hi > 0:
        t = t[:hi]
    return t[:cap].strip()


def fetch_fomc_statement(meeting_date: date,
                         cfg: dict | None = None) -> tuple[str | None, str | None]:
    """Fetch + plain-text the FOMC statement for a decision date (public, keyless).
    Returns (text, degraded_reason); never raises."""
    cfg = cfg or _cfg()
    url = _FOMC_URL.format(ymd=meeting_date.strftime("%Y%m%d"))
    try:
        import requests
        r = requests.get(url, timeout=30,
                         headers={"User-Agent": "macro-dashboard/1.0 (research)"})
        if r.status_code != 200 or "html" not in r.headers.get("Content-Type", "").lower():
            return None, f"fetch_status_{getattr(r, 'status_code', '?')}"
        text = _html_to_statement(r.text, int(cfg.get("max_doc_chars", 20000)))
        return (text, None) if text else (None, "empty_after_strip")
    except Exception as e:  # noqa: BLE001 — degrade, never raise
        log.warning("fomc fetch failed (%s)", e)
        return None, "fetch_error"


def _cache_path(doc_id: str, cfg: dict):
    from pathlib import Path
    cdir = config.ROOT / cfg.get("cache_dir", "data/catalyst/digest_cache")
    Path(cdir).mkdir(parents=True, exist_ok=True)
    return Path(cdir) / f"{doc_id}.json"


def _cached_or_digest_fomc(meeting: date, cfg: dict) -> dict | None:
    """Return the digest for one FOMC meeting, from cache if present (the
    statement never changes) else fetch+digest. Only a SUCCESSFUL digest is
    cached, so a transient failure retries next run."""
    doc_id = f"fomc_{meeting.isoformat()}"
    cache = _cache_path(doc_id, cfg)
    from engine import llm_auth
    original = _fabric_cache_path(config.ROOT / cfg.get("reply_cache_dir", "data/catalyst/reply_cache"),
        {"task": "catalyst-tone", "kind": "fomc_statement", "source_id": doc_id})
    if cache.exists() and not os.path.lexists(original) and llm_auth.application_mode_id(cfg) is None:
        try:
            return json.loads(cache.read_text())
        except Exception:  # noqa: BLE001
            pass
    text, reason = fetch_fomc_statement(meeting, cfg)
    if not text:
        return {"schema": "catalyst_tone.v1", "is_context_only": True,
                "kind": "fomc_statement", "doc_id": doc_id, "asof": meeting.isoformat(),
                **_NEUTRAL, "confidence": "low", "confidence_gated": False,
                "evidence": [], "dropped_fields": [], "degraded_reason": reason,
                "disclaimer": DISCLAIMER_TEXT}
    rec = digest_document(text, kind="fomc_statement", doc_id=doc_id,
                          context=f"FOMC monetary-policy statement, {meeting.isoformat()}",
                          asof=meeting)
    if rec is None:                       # disabled mid-call; don't cache
        return None
    if rec.get("degraded_reason") is None:
        try:
            cache.write_text(json.dumps(rec))
        except Exception:  # noqa: BLE001
            pass
    return rec


_SNAP_KEYS = ("schema", "is_context_only", "kind", "doc_id", "asof",
              "tone_score", "guidance_direction", "risk_delta", "shock_reversible",
              "confidence", "confidence_gated", "dropped_fields", "evidence",
              "degraded_reason", "disclaimer")


def daily_snapshot(asof: date | str | None = None) -> dict | None:
    """Daily Action-step entry: digest the most recent FOMC statement (cached per
    meeting) as honest CONTEXT for latest.json. Returns None when disabled or
    when nothing is recent enough. NEVER raises into the pipeline."""
    cfg = _cfg()
    if not cfg.get("enabled", False):
        return None
    try:
        today = _as_date(asof) or date.today()
        meeting = _recent_fomc(today, int(cfg.get("max_age_days", 120)))
        if meeting is None:
            return None
        rec = _cached_or_digest_fomc(meeting, cfg)
        if rec is None:
            return None
        return {k: rec.get(k) for k in _SNAP_KEYS}
    except Exception as e:  # noqa: BLE001 — additive, never fatal
        log.error("catalyst daily_snapshot failed (%s)", e)
        return None


# --------------------------------------------------------------------------- #
# event trigger — on a dislocation day, digest that day's market news (Stage 3b)
# --------------------------------------------------------------------------- #
_GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
_EVENT_QUERY = ('(stock market OR "S&P 500" OR selloff OR "Federal Reserve" OR Treasury '
                'OR "risk-off" OR volatility OR crash OR rally)')


def _fetch_event_headlines(today: date, cfg: dict) -> list[str]:
    """GDELT macro/market headlines around `today` (free, keyless). [] on any error.

    Delegates HTTP, throttling, and retry handling to engine.gdelt_client so
    all GDELT callers share a single cross-process pacing lock (GDELT 5s/IP rule;
    nine callers without shared throttle caused a penalty-box incident 2026-06-20)."""
    from datetime import timedelta
    from engine import gdelt_client as _gc
    win = int(cfg.get("event_window_days", 2))
    start = datetime(today.year, today.month, today.day) - timedelta(days=win)
    end = datetime(today.year, today.month, today.day, 23, 59, 59)
    n = int(cfg.get("event_max_records", 8))
    params = {"query": cfg.get("event_query", _EVENT_QUERY) + " sourcelang:eng",
              "mode": "artlist", "format": "json", "maxrecords": str(n), "sort": "datedesc",
              "startdatetime": start.strftime("%Y%m%d%H%M%S"),
              "enddatetime": end.strftime("%Y%m%d%H%M%S")}
    try:
        arts, _ = _gc.get_articles(params, timeout=30)
        if not arts:
            return []
        return [a.get("title", "").strip() for a in arts[:n] if a.get("title")]
    except Exception as e:  # noqa: BLE001 — degrade, never raise
        log.warning("event headline fetch failed (%s)", e)
        return []


def event_snapshot(asof: date | str | None = None, context: str = "") -> dict | None:
    """Digest the current dislocation day's market news into a shock_reversible read.
    None when disabled, event-digest off, or no headlines. NEVER raises.
    The digest text is PUBLIC headlines only (same firewall as the FOMC path).

    Determinism kit (W7 #33): GDELT headlines are snapshotted to a dated artifact
    BEFORE scoring. On a second run for the same date the snapshot is reused instead
    of re-fetching, so the input text feeding the graded shock_reversible call is
    identical and the content-hash cache can serve the same reply. This makes the
    veto reproducible even though GDELT headlines shift intraday.
    """
    cfg = _cfg()
    if not cfg.get("enabled", False) or not cfg.get("event_enabled", True):
        return None
    try:
        today = _as_date(asof) or date.today()
        # snapshot-before-score: reuse the dated snapshot if it exists, else fetch+persist
        headlines = _gdelt_snapshot_get(today, cfg)
        if headlines is None:
            headlines = _fetch_event_headlines(today, cfg)
            if headlines:
                _gdelt_snapshot_put(today, headlines, cfg)
        if not headlines:
            return None
        text = "Market headlines around the dislocation:\n" + "\n".join(f"- {h}" for h in headlines)
        rec = digest_document(text, kind="dislocation", doc_id=f"event_{today.isoformat()}",
                              context=context or "market dislocation day", asof=today)
        return {k: rec.get(k) for k in _SNAP_KEYS} if rec else None
    except Exception as e:  # noqa: BLE001 — additive, never fatal
        log.error("catalyst event_snapshot failed (%s)", e)
        return None
