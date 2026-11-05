"""engine.neuralweb.brain_market_intel — Mastermind retrieval: live events + research.

CLASSIFICATION: read-only retrieval helpers for the Mastermind brain gateway.
This module holds the FUNCTIONS and their Anthropic tool schemas only; the
gateway owns dispatch, the tool allowlist, and tier gating. Nothing here is
imported by the nightly or calls an LLM.

TIER: display/context — READ-ONLY. Never computes a signal, score, rank, size,
or gate. Every function is a pure read over artifacts other lanes publish.

TWO EXCEPTIONS, both belonging to mode="report" (W4) and to nothing else: it
reads the R2-backed corpus (so a cold process may pay ONE download through the
shared reader in research_vault.corpus) and it debits the hourly view ledger
(one small JSON file per user per hour, via research_vault.view_ratelimit). No
other path here touches a socket or writes a byte.

PUBLIC API
----------
get_market_events(root, window_h=12.0, limit=5, symbol=None) -> dict
    Fresh market events, merged from the intraday press wire (wires.v1) and
    topped up from the nightly news digests when the wire is thin. The wire pool
    is permuted by the desk's ranked-wire sidecar when a fresh one is published
    (W2 — see the _WIRE_RANK_BASENAME block); recency otherwise.

search_research(root, query, limit=5, mode="search", report_id="",
                user_ctx=None) -> dict
    mode="search"   — deterministic keyword search over the committed
                      research-vault catalog (third-party institutional
                      summaries — never the desk's own signals).
    mode="clusters" — street-convergence view of the SAME catalog: which themes
                      N>=3 fresh notes from >=2 institutions are all writing
                      about. A retrieval summary, never consensus-as-authority.
    mode="report"   — ONE report by id: catalog metadata + the PUBLIC excerpt +
                      a capped slice of the stored body. PRO-only (operator
                      ruling 2026-07-31) and metered — see the FUNCTION 2c block
                      for the rights reasoning and the caps.

EVENTS_TOOL_SCHEMA / RESEARCH_TOOL_SCHEMA
    Anthropic tool definitions, shaped like brain_gateway._brain_tool_schemas().

EPISTEMICS LAW (TI-R5) — WHY THE OUTPUT IS A WHITELIST
------------------------------------------------------
get_market_events returns FACTS ONLY: a timestamp, the headline the desk
composed, the source, the desk-computed salience where one exists, and the
corroboration chip. It must NEVER emit a predicted effect, a beneficiary or
casualty list, a "shelter" mapping, or an invented probability — the
shock→beneficiary map is a standing house KILL (TI-R5, research/DO_NOT_REBUILD.md
§1: "laundered directional escalation on nulled continuation claims"), and an
LLM may not originate a signal or escalation (A7).

The law is honored MECHANICALLY, not by good intentions: every output item is
built by ``_project_event`` from the literal key set ``EVENT_FIELDS``. There is
no ``{**item}`` spread anywhere on the output path, so a field an upstream lane
adds later — even one literally named ``beneficiaries`` — cannot reach the model
without someone editing ``EVENT_FIELDS`` and tripping
tests/test_brain_market_intel.py.

FAIL-SOFT is the whole contract: a missing artifact, corrupt JSON, an
unexpected container shape, or an unparseable timestamp degrades to fewer
events (or none) with an honest ``note``. Neither function raises.

CLOCK
-----
Both functions take a keyword-only ``now`` for tests. The house has twice shipped
a scheduled CI red by aging fixtures against the wall clock instead of the
caller's instant (see scripts/marketing_fastlane_daemon._merge_wires_window), so
the suite freezes ``now`` and derives every fixture timestamp from it. No clock
reading is hashed or persisted here — these functions write nothing.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlencode

# --------------------------------------------------------------------------- #
# Output contract (TI-R5 whitelist)
# --------------------------------------------------------------------------- #
# The EXACT key set an event item may carry. `headline_zh` is the one optional
# member (emitted only when the upstream actually carries a translation — never
# an English string passed off as translated, which is the same honest-disclosure
# rule the news.html wire rail follows with its 英文原文 marker).
EVENT_FIELDS: tuple[str, ...] = (
    "ts",
    "headline",
    "headline_zh",
    "source",
    "salience",
    "corroboration",
    "source_kind",
)
# Required members: everything except the optional translation.
EVENT_FIELDS_REQUIRED: tuple[str, ...] = tuple(f for f in EVENT_FIELDS if f != "headline_zh")

# Bounds, mirrored in the tool schemas' descriptions so the model and the code
# cannot drift apart.
_WINDOW_MIN_H, _WINDOW_MAX_H, _WINDOW_DEFAULT_H = 1.0, 48.0, 12.0
_EVENTS_LIMIT_MIN, _EVENTS_LIMIT_MAX, _EVENTS_LIMIT_DEFAULT = 1, 10, 5
_RESEARCH_LIMIT_MIN, _RESEARCH_LIMIT_MAX, _RESEARCH_LIMIT_DEFAULT = 1, 8, 5

# Salience sentinel for items that carry none. Real desk salience is 0..100, so a
# negative floor sorts unscored items AFTER scored ones without ever inventing a
# number for them — the emitted `salience` stays None.
_NO_SALIENCE = -1.0

# Research scoring weights (deterministic; no embeddings, no network).
_W_TITLE, _W_SUMMARY, _W_INSTITUTION, _W_TOP_PICK = 3.0, 1.5, 2.0, 1.0
_RECENCY_HALF_LIFE_DAYS = 45.0
_RECENCY_FLOOR = 0.35
_SUMMARY_POINTS_KEPT = 4
_SUMMARY_POINT_MAX_CHARS = 220


# --------------------------------------------------------------------------- #
# Small fail-soft helpers
# --------------------------------------------------------------------------- #
def _read_json(path: Path):
    """Parse `path` as JSON, or return None. Never raises.

    Missing file, unreadable file, and invalid JSON collapse to the same answer
    on purpose: every caller here treats "no usable artifact" identically, and a
    retrieval tool that raised would take the whole chat turn down with it.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001 — any read/parse failure degrades to None
        return None


def _parse_ts(raw) -> datetime | None:
    """Parse an ISO-8601-ish timestamp to an aware UTC datetime, else None.

    Handles the three forms the real artifacts use: "…Z" (wires.v1 updated_at
    and press published_at), "…+00:00" (site/news/*.json seendate), and a naive
    stamp (assumed UTC, matching every other reader in the repo). Anything else
    returns None and the caller SKIPS the item — an event with no trustworthy
    timestamp cannot be placed inside a freshness window, and guessing one would
    be inventing a fact.
    """
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _clamp_int(raw, low: int, high: int, default: int) -> int:
    """Coerce `raw` to an int inside [low, high]; unusable input → `default`."""
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, value))


def _clamp_float(raw, low: float, high: float, default: float) -> float:
    """Coerce `raw` to a float inside [low, high]; unusable input → `default`."""
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, value))


def _first_text(item: dict, *keys: str) -> str | None:
    """First non-blank string value among `keys`, else None (no empty strings).

    None rather than "" because the two are different claims to the model:
    None reads as "we do not know the source", "" reads as "the source is blank".
    """
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _float_or_none(raw) -> float | None:
    """Coerce to float, or None. Used for desk scores that may be absent/null."""
    if isinstance(raw, bool) or raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# FUNCTION 1 — live market events
# --------------------------------------------------------------------------- #
# Path ladder for the intraday wire, mirroring the precedents:
#   scripts/notify_turn_events.py:93          MACRO_LIVE_DIR overrides site/live
#   scripts/marketing_fastlane_daemon.py:555  VPS public live dir, dev-path fallback
# The daemon (a WRITER) picks the first candidate whose PARENT dir exists. A
# READER must not: on a dev box /var/lib/macro-live/public/live may exist and be
# empty while the dev sink under data/marketing/press/ holds the real window, so
# the first candidate whose FILE exists wins. A present-but-empty live dir
# therefore falls through instead of blanking the read.
_WIRES_BASENAME = "wires.json"
_VPS_LIVE_DIR = "/var/lib/macro-live/public/live"

# --- ranked-wire sidecar (W2) ---------------------------------------------- #
# The public rail carries NO salience, by the news desk's ruling: internal
# ranking numbers never ride a user-fetchable payload (their leak law, 2026-07-30,
# Intelligence Desk V2 lane). So the desk's ordering arrives out-of-band, on a
# NON-public STATE path, as a list of ids in best-first order:
#
#   {"schema": "wire_rank.v1", "updated_at": "<ISO>", "ids": ["<id>", ...]}
#
# Ordering by POSITION, with deliberately no numbers at all: there is no score to
# leak, nothing to quote back, and nothing an LLM could re-present as a desk
# probability. The effect here is a permutation of the wire pool and NOTHING else
# — EVENT_FIELDS is unchanged, so no sidecar value can reach the model's context.
# This module never writes the file.
_WIRE_RANK_BASENAME = "wire_rank.json"
_VPS_STATE_DIR = "/var/lib/macro-live/state"
# Older than this and the ranking is ignored: a wire window turns over in
# minutes, so a stale ordering is worse than honest recency (it would pin an hour-
# old lead story to the top of a fresh tape).
_WIRE_RANK_MAX_AGE_MIN = 45.0


def _wires_candidates(root: Path) -> list[Path]:
    """Ordered candidate paths for the wires.v1 payload (highest precedence first)."""
    candidates: list[Path] = []
    env_dir = os.environ.get("MACRO_LIVE_DIR")
    if env_dir:
        candidates.append(Path(env_dir) / _WIRES_BASENAME)
    vps = Path(_VPS_LIVE_DIR)
    try:
        if vps.is_dir():
            candidates.append(vps / _WIRES_BASENAME)
    except OSError:
        pass  # unreadable mount point — skip the rung, never raise
    candidates.append(root / "site" / "live" / _WIRES_BASENAME)
    # Final rung: the daemon's gitignored dev sink (data/marketing/press/wires.json).
    candidates.append(root / "data" / "marketing" / "press" / _WIRES_BASENAME)
    return candidates


def _resolve_wires_path(root: Path) -> Path | None:
    """First candidate on the ladder whose file exists, else None."""
    for cand in _wires_candidates(root):
        try:
            if cand.is_file():
                return cand
        except OSError:
            continue
    return None


def _wire_rank_candidates(root: Path) -> list[Path]:
    """Ordered candidate paths for the ranked-wire sidecar (highest first).

    Mirrors the wires ladder but on the STATE dir, not the PUBLIC live dir —
    that separation is the whole point of the sidecar (see the block comment
    above). MACRO_LIVE_STATE_DIR is the deployed override
    (app/deploy/live-setup.sh:80, scripts/vps_live_orchestrator.py:459).
    """
    candidates: list[Path] = []
    env_dir = os.environ.get("MACRO_LIVE_STATE_DIR")
    if env_dir:
        candidates.append(Path(env_dir) / _WIRE_RANK_BASENAME)
    state = Path(_VPS_STATE_DIR)
    try:
        if state.is_dir():
            candidates.append(state / _WIRE_RANK_BASENAME)
    except OSError:
        pass  # unreadable mount point — skip the rung, never raise
    # Dev sink: the same gitignored directory the fastlane daemon writes wires to.
    candidates.append(root / "data" / "marketing" / "press" / _WIRE_RANK_BASENAME)
    return candidates


def _resolve_wire_rank_path(root: Path) -> Path | None:
    """First sidecar candidate whose FILE exists, else None.

    File-exists (not dir-exists), same as _resolve_wires_path: on a dev box the
    state dir can exist and be empty while the dev sink holds the real file.
    """
    for cand in _wire_rank_candidates(root):
        try:
            if cand.is_file():
                return cand
        except OSError:
            continue
    return None


def _wire_rank_order(root: Path, now: datetime) -> dict[str, int] | None:
    """{wire item id: position} from a FRESH sidecar, else None.

    None — meaning "fall back to the honest recency order" — for every degraded
    case: no file, corrupt JSON, no `ids` list, an unparseable `updated_at`, or a
    stamp older than _WIRE_RANK_MAX_AGE_MIN.

    An unparseable/absent stamp is treated as unusable rather than fresh: a
    ranking whose age cannot be established cannot be shown to be current, and
    assuming freshness is how a dead daemon's last ordering outlives it. A
    FUTURE stamp is clock skew, not staleness, so it passes (the same rule
    _recency_factor applies to research dates).

    The schema string is checked loosely, matching _wire_items: a reader that
    hard-failed on a rename would go dark on a schema bump, and every field
    access here is already defensive.
    """
    path = _resolve_wire_rank_path(root)
    if path is None:
        return None
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return None
    stamp = _parse_ts(payload.get("updated_at"))
    if stamp is None:
        return None
    age_min = (now - stamp).total_seconds() / 60.0
    if age_min > _WIRE_RANK_MAX_AGE_MIN:
        return None
    ids = payload.get("ids")
    if not isinstance(ids, list):
        return None
    order: dict[str, int] = {}
    for pos, raw in enumerate(ids):
        if not isinstance(raw, str):
            continue
        key = raw.strip()
        if key and key not in order:  # first position wins on a duplicated id
            order[key] = pos
    return order or None


def _apply_wire_rank(
    pool: list[tuple[float, datetime, dict, list, str | None]],
    order: dict[str, int] | None,
) -> list[tuple[float, datetime, dict, list, str | None]]:
    """Reorder the wire pool by sidecar position; unranked items keep their order.

    Stable-sorted on position with a +inf default, so items the sidecar does not
    name retain the salience/recency order `_rank` gave them and land AFTER every
    ranked one. Nothing about the events themselves changes — this is a
    permutation, which is why no output field had to be added.
    """
    if not order:
        return pool
    return sorted(pool, key=lambda row: order.get(row[4] or "", float("inf")))


def _wire_items(payload) -> list[dict]:
    """Extract the item list from a wires.v1 payload, defensively.

    Two shapes are accepted because both exist in the wild: the published
    payload is {"schema": "wires.v1", "updated_at": …, "items": [...]}, and an
    ad-hoc/dev file may be a bare top-level list. The schema string is NOT
    required to match — a reader that hard-failed on a schema bump would go dark
    on a rename, and every field access below is already defensive.
    """
    items = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        return []
    return [it for it in items if isinstance(it, dict)]


def _dedupe_key(headline: str | None) -> str:
    """Normalised headline key for cross-source dedupe.

    Both wire text tails are stripped first. press_lane composes rail text as
    "<headline> -- <attribution> · <tape_stamp>", so the wire copy of a story and
    its nightly-digest twin share no prefix-free substring unless those tails
    come off — without this the merge would show the same story twice.
    """
    text = (headline or "").split(" -- ")[0].split(" · ")[0]
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _project_event(
    *,
    ts: datetime,
    headline: str,
    headline_zh: str | None,
    source: str | None,
    salience: float | None,
    corroboration: str | None,
    source_kind: str,
) -> dict:
    """Build ONE output event from the whitelisted fields only (TI-R5).

    Keyword-only and fully literal by design: there is no dict spread and no
    passthrough of the upstream item, so a field added upstream can never leak
    into the model's context. See this module's EPISTEMICS LAW docstring.
    """
    event = {
        "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "headline": headline,
        "source": source,
        "salience": salience,
        "corroboration": corroboration,
        "source_kind": source_kind,
    }
    if headline_zh:
        event["headline_zh"] = headline_zh
    return event


def _collect_wire_events(root: Path, cutoff: datetime) -> list[tuple[float, datetime, dict, list, str | None]]:
    """Read the live wire and project its in-window items.

    Returns (salience_sort_value, ts, event, tickers, item_id) rows. The ticker
    list and the id ride ALONGSIDE the projected event rather than inside it:
    neither is an output field (EVENT_FIELDS), but symbol matching needs the
    tickers and the ranked sidecar needs the id, so both are carried out-of-band
    and dropped before the return.

    SHAPE NOTE: the published rail item carries id/ts/class/label_en/label_zh/
    register/en/attribution/corroboration (+ optional zh, tape_stamp) — it does
    NOT carry `salience`, `source_name`, or `tickers`; those live on the scored
    upstream item inside the daemon. Every one of them is therefore read
    optionally: a wire with no salience simply ranks by recency.
    """
    path = _resolve_wires_path(root)
    if path is None:
        return []
    items = _wire_items(_read_json(path))
    out: list[tuple[float, datetime, dict, list, str | None]] = []
    for item in items:
        ts = _parse_ts(item.get("ts") or item.get("published_at"))
        if ts is None or ts < cutoff:
            continue  # unparseable or out of window
        headline = _first_text(item, "en", "headline", "text", "title")
        if not headline:
            continue  # nothing to show; a bodiless item is not an event
        salience = _float_or_none(item.get("salience"))
        # `corroboration` is the honest display chip ("verified" / "3 sources" /
        # "reports"); `corroboration_class` is the machine slug on the scored
        # item. Prefer the chip, fall back to the slug, else None.
        corroboration = _first_text(item, "corroboration", "corroboration_class")
        out.append((
            salience if salience is not None else _NO_SALIENCE,
            ts,
            _project_event(
                ts=ts,
                headline=headline,
                headline_zh=_first_text(item, "zh", "headline_zh", "title_zh"),
                # label_en is a desk CLASS ("Washington", "Companies"), never a
                # source, so it is deliberately not a fallback here. attribution
                # is the corroboration decision's source claim, which is.
                source=_first_text(item, "source_name", "domain", "source", "attribution"),
                salience=salience,
                corroboration=corroboration,
                source_kind="live_wire",
            ),
            item.get("tickers") if isinstance(item.get("tickers"), list) else [],
            _first_text(item, "id"),
        ))
    return out


# Nightly digest containers. WHITELISTED rather than "every list-valued key":
# site/news/*.json also carry a `rejected` list (headlines the desk filtered
# OUT) that must never be presented as news.
_NIGHTLY_FILES = ("macro.json", "financial.json")
_NIGHTLY_LIST_KEYS = ("headlines", "market", "items")
_NIGHTLY_DICT_KEYS = ("by_ticker", "sectors", "mag7", "baskets")


def _nightly_candidate_items(payload) -> list[dict]:
    """Flatten a site/news/*.json payload into a flat list of headline dicts.

    macro.json keeps its items under `headlines`; financial.json keeps the broad
    tape under `market` plus dict-of-list buckets (`by_ticker`, `sectors`,
    `mag7`, `baskets`). Both are read; `rejected` never is.
    """
    if not isinstance(payload, dict):
        return [it for it in payload if isinstance(it, dict)] if isinstance(payload, list) else []
    items: list[dict] = []
    for key in _NIGHTLY_LIST_KEYS:
        value = payload.get(key)
        if isinstance(value, list):
            items.extend(it for it in value if isinstance(it, dict))
    for key in _NIGHTLY_DICT_KEYS:
        bucket = payload.get(key)
        if not isinstance(bucket, dict):
            continue
        for value in bucket.values():
            if isinstance(value, list):
                items.extend(it for it in value if isinstance(it, dict))
    return items


def _collect_nightly_events(root: Path, cutoff: datetime) -> list[tuple[float, datetime, dict, list, str | None]]:
    """Project in-window items from the nightly news digests.

    Same row shape as _collect_wire_events so one `_rank`/`_absorb` serves both.
    The trailing id is always None here: the ranked sidecar covers the WIRE pool
    only — the desk ranks the intraday tape, not last night's digest.

    SALIENCE NOTE: these are the NEWS desk's own scores (`importance_score`,
    `quality`, `rank_score` — all roughly 0..100), not press-lane salience. They
    are emitted because they are facts the desk computed, but nightly items are
    never sorted against wire items by them (see get_market_events).
    """
    out: list[tuple[float, datetime, dict, list, str | None]] = []
    for name in _NIGHTLY_FILES:
        payload = _read_json(root / "site" / "news" / name)
        if payload is None:
            continue
        for item in _nightly_candidate_items(payload):
            ts = _parse_ts(item.get("seendate") or item.get("published_at") or item.get("ts"))
            if ts is None or ts < cutoff:
                continue
            headline = _first_text(item, "title", "headline", "en")
            if not headline:
                continue
            salience = _float_or_none(
                item.get("importance_score")
                if item.get("importance_score") is not None
                else item.get("quality")
                if item.get("quality") is not None
                else item.get("rank_score")
            )
            out.append((
                salience if salience is not None else _NO_SALIENCE,
                ts,
                _project_event(
                    ts=ts,
                    headline=headline,
                    headline_zh=_first_text(item, "title_zh", "headline_zh", "zh"),
                    source=_first_text(item, "source_name", "domain", "source"),
                    salience=salience,
                    # The nightly digest carries no corroboration decision. None,
                    # never a manufactured "reports" chip.
                    corroboration=None,
                    source_kind="nightly",
                ),
                item.get("tickers") if isinstance(item.get("tickers"), list) else [],
                None,
            ))
    return out


def _rank(
    pool: list[tuple[float, datetime, dict, list, str | None]],
) -> list[tuple[float, datetime, dict, list, str | None]]:
    """Sort one source pool by salience desc, then timestamp desc."""
    return sorted(pool, key=lambda row: (-row[0], -row[1].timestamp()))


def _symbol_matcher(symbol: str):
    """Return a predicate: does this item's text or ticker list mention `symbol`?

    Word-boundary matching so "C" does not hit "CPI" and "BA" does not hit
    "BABA". re.escape keeps exchange-qualified forms (600036.SH, BRK.B) literal.
    """
    needle = symbol.strip()
    pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(needle) + r"(?![A-Za-z0-9])", re.IGNORECASE)

    def matches(item: dict, tickers) -> bool:
        if isinstance(tickers, (list, tuple)):
            for tick in tickers:
                if isinstance(tick, str) and tick.strip().upper() == needle.upper():
                    return True
        for key in ("headline", "headline_zh"):
            text = item.get(key)
            if isinstance(text, str) and pattern.search(text):
                return True
        return False

    return matches


def get_market_events(
    root: Path,
    window_h: float = _WINDOW_DEFAULT_H,
    limit: int = _EVENTS_LIMIT_DEFAULT,
    symbol: str | None = None,
    *,
    now: datetime | None = None,
) -> dict:
    """Fresh market events — FACTS ONLY (timestamps, headlines, source, salience).

    Sources, tried in order and merged (deduped by id-normalised headline):
      1. The intraday press wire (wires.v1) resolved off the MACRO_LIVE_DIR →
         VPS live dir → site/live → data/marketing/press ladder.
      2. The nightly news digests (site/news/macro.json, site/news/financial.json),
         used ONLY to top up when the wire yields fewer than `limit`.

    Ordering is SOURCE-MAJOR: wire events first (ranked among themselves by
    salience desc then ts desc, then permuted by the ranked-wire sidecar when a
    fresh one exists), then nightly top-ups (ranked the same way).
    The two pools are never sorted against each other, because their scores are
    not the same quantity — press salience and the news desk's importance/quality
    scores share a 0..100 range and nothing else, so a cross-pool comparison
    would be a fabricated ranking. Source-major ordering is also exactly what
    "nightly only tops up" means.

    `symbol` PREFERS matching items (ticker list or word-boundary text hit) and
    then backfills with general items to reach `limit` — a quiet ticker returns
    the broad tape rather than an empty answer.

    EPISTEMICS (TI-R5): the returned events carry only the keys in EVENT_FIELDS.
    No predicted effect, no beneficiary/casualty list, no invented probability —
    not even if an upstream lane starts publishing them. See the module docstring.

    Returns {"asof", "window_h", "events", "note"}. Never raises; a dead artifact
    degrades to fewer events and an honest note.
    """
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    reference = reference.astimezone(timezone.utc)

    window = _clamp_float(window_h, _WINDOW_MIN_H, _WINDOW_MAX_H, _WINDOW_DEFAULT_H)
    cap = _clamp_int(limit, _EVENTS_LIMIT_MIN, _EVENTS_LIMIT_MAX, _EVENTS_LIMIT_DEFAULT)
    cutoff = reference - timedelta(hours=window)

    try:
        wire_pool = _rank(_collect_wire_events(root, cutoff))
        # The desk's own ordering, when a fresh non-public sidecar publishes one;
        # otherwise the recency order above stands (see _wire_rank_order).
        wire_pool = _apply_wire_rank(wire_pool, _wire_rank_order(root, reference))
    except Exception:  # noqa: BLE001 — retrieval must not take the turn down
        wire_pool = []

    matches = _symbol_matcher(symbol) if isinstance(symbol, str) and symbol.strip() else None

    # Dedupe as we select, wire copy winning: it carries the desk's composed text,
    # its corroboration chip, and any zh twin we already paid for.
    seen: set[str] = set()
    selected: list[tuple[dict, bool]] = []  # (event, is_symbol_match)

    def _absorb(pool: list[tuple[float, datetime, dict, list, str | None]]) -> None:
        for _sal, _ts, event, tickers, _iid in pool:
            key = _dedupe_key(event.get("headline"))
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            selected.append((event, bool(matches(event, tickers)) if matches else False))

    _absorb(wire_pool)

    # Nightly is a TOP-UP only: read it when the wire could not fill the cap.
    # `symbol` widens what "fill" means — a ticker-specific ask wants the ticker's
    # own items, so top up whenever the wire's MATCHING set is short, even if the
    # wire filled the cap with general items.
    filled = sum(1 for _e, hit in selected if hit) if matches else len(selected)
    if filled < cap:
        try:
            _absorb(_rank(_collect_nightly_events(root, cutoff)))
        except Exception:  # noqa: BLE001
            pass

    if matches is not None:
        # Symbol-matching items keep their pool order and come first; general
        # items backfill to `cap`, so a quiet ticker returns the broad tape
        # instead of an empty answer.
        events = [e for e, hit in selected if hit] + [e for e, hit in selected if not hit]
    else:
        events = [e for e, _hit in selected]

    events = events[:cap]

    if not events:
        note = "no fresh events in window"
    elif any(e.get("source_kind") == "live_wire" for e in events):
        note = "live wire"
    else:
        note = "nightly digest only"

    return {
        "asof": reference.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_h": window,
        "events": events,
        "note": note,
    }


# --------------------------------------------------------------------------- #
# FUNCTION 2 — research-vault search
# --------------------------------------------------------------------------- #
_CATALOG_REL = ("data", "research_vault", "catalog.json")

# Plain ASCII word atoms, ≥2 chars. Qualified identifiers and Han spans use
# their own rules below so exact symbols never fall back to substring matching
# and Chinese queries are not erased before scoring.
_WORD_RE = re.compile(r"[a-z0-9]{2,}")
_HAN_RANGE = r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002fa1f"
_HAN_RE = re.compile("[" + _HAN_RANGE + "]+")
_RAW_SEARCH_ATOM_RE = re.compile(
    r"[A-Za-z0-9]+(?:[.\-][A-Za-z0-9]+)*|[" + _HAN_RANGE + "]+"
)


def _search_normalize(text: str) -> str:
    """NFKC + casefold for matching only; returned query text stays original.

    Most catalog fields are already ASCII. Preserve that hot path without a
    Unicode normalization pass while still normalizing full-width/mixed-script
    text whenever it is present.
    """
    value = str(text or "")
    if value.isascii():
        return value.casefold()
    return unicodedata.normalize("NFKC", value).casefold()


def _is_qualified_identifier(raw: str) -> bool:
    """Whether a punctuated ASCII atom should stay exact instead of splitting.

    Dotted exchange-qualified symbols are exact. Hyphenated atoms stay exact
    only for the ordinary one-letter share-class form (BRK-B, BF-A), including
    lowercase user input. Numeric ranges and research prose such as 10-yr,
    risk-off and AI-driven retain their previous word-search behaviour.
    """
    if "." in raw:
        return True
    parts = raw.split("-")
    return (
        len(parts) == 2
        and 1 <= len(parts[0]) <= 5
        and len(parts[1]) == 1
        and parts[0].isalnum()
        and parts[1].isalpha()
    )


def _tokenize(query: str) -> tuple[str, ...]:
    """Query → ordered, de-duplicated meaningful lexical atoms.

    The internal normalization is width/case only: it does not translate or
    equate Simplified and Traditional Chinese. Repeated atoms never buy extra
    weight because scoring counts distinct hits per field.
    """
    text = _search_normalize(query)
    tokens: list[str] = []

    def add(token: str) -> None:
        if len(token) >= 2 and token not in tokens:
            tokens.append(token)

    for raw in _RAW_SEARCH_ATOM_RE.findall(text):
        if _HAN_RE.fullmatch(raw):
            add(raw)
        elif _is_qualified_identifier(raw):
            add(raw)
        else:
            for word in _WORD_RE.findall(raw):
                add(word)
    return tuple(tokens)


def _hits(tokens: tuple[str, ...], haystack: str) -> int:
    """Count DISTINCT normalized atoms supported by `haystack`.

    Build only the index family the query needs. Plain catalog searches stay on
    the existing word-set hot path; exact-atom extraction is paid only for an
    exchange/share-class identifier, and a Han-only query needs neither set.
    """
    text = _search_normalize(haystack)
    if not text:
        return 0
    needs_words = any(
        not _HAN_RE.fullmatch(token) and "." not in token and "-" not in token
        for token in tokens
    )
    needs_atoms = any("." in token or "-" in token for token in tokens)
    words = set(_WORD_RE.findall(text)) if needs_words else set()
    atoms = set(_RAW_SEARCH_ATOM_RE.findall(text)) if needs_atoms else set()
    count = 0
    for token in tokens:
        if _HAN_RE.fullmatch(token):
            count += int(token in text)
        elif "." in token or "-" in token:
            count += int(token in atoms)
        else:
            count += int(token in words)
    return count


def _recency_factor(published_at, now: datetime) -> float:
    """max(0.35, 1 - age_days/45); an unparseable/absent date takes the floor.

    The floor, not 1.0: an item whose date we cannot read has not earned a
    freshness premium, and giving it one would let undated rows crowd out dated
    ones on every query.
    """
    ts = _parse_ts(published_at)
    if ts is None:
        return _RECENCY_FLOOR
    age_days = (now - ts).total_seconds() / 86400.0
    if age_days < 0:
        age_days = 0.0  # a future stamp is clock skew, not extra freshness
    return max(_RECENCY_FLOOR, 1.0 - age_days / _RECENCY_HALF_LIFE_DAYS)


def _truncate(text: str) -> str:
    """Clamp one summary point to _SUMMARY_POINT_MAX_CHARS, ellipsis included.

    The budget covers the ellipsis, so the returned string is never longer than
    the documented cap — a "220 + 1" result would break any caller sizing a
    context window off this number.
    """
    clean = " ".join(str(text or "").split())
    if len(clean) <= _SUMMARY_POINT_MAX_CHARS:
        return clean
    return clean[: _SUMMARY_POINT_MAX_CHARS - 1] + "…"


def _catalog_items(root: Path) -> list[dict] | None:
    """Read research_vault.catalog.v1 items, or None when unavailable.

    None (not []) distinguishes "vault missing/corrupt" — which the caller
    reports honestly — from "vault present, nothing matched".
    """
    payload = _read_json(root.joinpath(*_CATALOG_REL))
    if payload is None:
        return None
    items = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        return None
    return [it for it in items if isinstance(it, dict)]


# --------------------------------------------------------------------------- #
# FUNCTION 2b — street clusters (W2): what is the street all writing about?
# --------------------------------------------------------------------------- #
# WHAT THE CATALOG ACTUALLY GIVES US (recon, 2026-07-30, 374 items, ~7d window):
# `institution` is filled 374/374 across 28 distinct houses, and `side` splits
# sell 319 / independent 55. `desk`, `tags` and `tickers` are filled 0/374 —
# DEAD FIELDS. So convergence is read off text + institution, and nothing here
# touches tags/tickers: a theme keyed on an always-empty field would return zero
# clusters forever and read as "the street agrees on nothing". Deterministic and
# offline throughout — no embeddings, no LLM, no network.
#
# WHY THEMES ARE ANCHORED ON TERMS, AND ON THE TITLE (measured, not assumed)
# -------------------------------------------------------------------------
# The obvious build — bag-of-words over title+summary, greedy document
# clustering, join on Jaccard>=0.3 or >=2 shared tokens — was implemented first
# and MEASURED against the real catalog. It fabricates convergence:
#
#   * Top cluster: 51 reports / 14 houses labelled "hike fed rate", whose members
#     were "US EQUITIES COLOR PRESSER PRESSURE", "In Credit 27 07 2026" and
#     "Chile MPC Keeps Policy Rate at 4.5" — nothing in common.
#   * Second: 22 reports / 8 houses labelled "global policy data", members
#     "Qualcomm First Take", "CBRE 2Q26", "Pi gev 3q26".
#
# The cause is structural, not a tuning miss. Half this catalog is MULTI-TOPIC
# daily briefings ("GS MORNING 1 Oil Tracker, 2 USDJPY Topside, 3 Korea Update,
# 4 ..."), whose token bags span the whole macro universe. Each one is a hub that
# chains unrelated notes into one blob, and tightening the distinctiveness of the
# shared tokens (swept at 2/4/6/8% document frequency) never separates them.
# Reporting that as "14 houses are converging" would be a manufactured consensus
# claim — the exact laundered-escalation failure TI-R5 exists to stop.
#
# So a theme is a TERM plus the notes whose OWN TITLE names it. A title is the
# note's declaration of its subject; a mention buried in an omnibus briefing's
# bullets is not. That makes the emitted claim literally checkable — "11 notes
# from 6 houses have 'oil' in the title" — instead of an unfalsifiable grouping.
# Adding the summariser's bolded bullet headers as a second membership signal was
# tried too and rejected: recall rose but "geopolitical" then swept in "Ford
# Motor July 29", because an omnibus note's headers span everything its bullets
# do. Measured output of the shipped version: credit 10 reports/8 houses,
# europe 12/6, oil 11/6, iran 6/6, china 19/5, earnings 11/5 — every member's
# title genuinely names its theme.
#
# A term must start with a LETTER and run >=3 chars. That one rule drops the
# measurement noise this catalog is full of ("152bps", "2q26", "500") while
# keeping subject words that carry a digit ("mag7").
_CLUSTER_TOKEN_RE = re.compile(r"[a-z][a-z0-9]{2,}")

# Grammar words, report FURNITURE, and calendar words — the vocabulary of a
# note's packaging rather than its subject. Frozen and hand-checked against the
# real titles: "JPM GLOBAL MARKET INTELLIGENCE" and "DB Research Europe" are
# recurring PUBLICATION SERIES names, so market/global/research/intelligence must
# not become themes. "The street is focused on: market" is also exactly the vague
# glance-tier copy the design doctrine bans.
_CLUSTER_STOPWORDS: frozenset[str] = frozenset({
    # grammar / connective
    "and", "the", "for", "with", "from", "that", "this", "will", "has", "have",
    "are", "but", "not", "its", "was", "were", "been", "into", "over", "more",
    "less", "than", "per", "all", "any", "out", "our", "their", "they", "them",
    "what", "when", "where", "which", "while", "also", "may", "can", "could",
    "would", "should", "still", "after", "before", "amid", "amidst", "versus",
    "vs", "about", "above", "below", "between", "both", "each", "other",
    "others", "some", "such", "only", "own", "same", "too", "very", "just",
    "now", "one", "two", "three", "new", "near", "next", "last", "most",
    "much", "many", "due", "despite", "since", "until", "again", "off", "via",
    "without", "within", "across", "against", "along", "among", "around",
    "because", "being", "does", "doing", "done", "during", "further",
    "however", "itself", "made", "make", "making", "need", "needs", "once",
    "said", "says", "see", "seen", "set", "sets", "show", "shows", "thus",
    "toward", "towards", "use", "used", "using", "whether", "though",
    "although", "either", "neither", "yet", "already", "onto", "under", "upon",
    "here", "there", "then", "who", "whom", "how", "why",
    # report furniture / recurring publication-series words
    "report", "reports", "update", "updates", "note", "notes", "weekly",
    "monthly", "daily", "quarterly", "preview", "review", "first", "second",
    "third", "take", "takes", "group", "inc", "corp", "ltd", "plc", "llc",
    "research", "comment", "comments", "commentary", "color", "colour",
    "morning", "afternoon", "evening", "midday", "overnight", "summary",
    "brief", "briefing", "briefings", "desk", "recap", "wrap", "edition",
    "deck", "chart", "charts", "table", "exhibit", "appendix", "page", "pages",
    "key", "focus", "thoughts", "views", "view", "read", "reading", "insight",
    "insights", "idea", "ideas", "call", "calls", "week", "month", "year",
    "quarter", "today", "yesterday", "session", "meeting", "market", "markets",
    "global", "macro", "equity", "equities", "intelligence", "intell",
    "strategy", "strategies", "thematic", "think", "point", "talk", "tracker",
    "navigator", "kickstart", "analyst", "economics", "outlook",
    # calendar
    "january", "february", "march", "april", "june", "july", "august",
    "september", "october", "november", "december", "jan", "feb", "mar", "apr",
    "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec", "monday",
    "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
})

# A term in more than a quarter of the window's notes is the week's WEATHER, not
# a theme worth naming: it has no discriminating power and its "N houses wrote
# about it" reads as convergence when it is just vocabulary.
_CLUSTER_DF_CEILING = 0.25
# Two terms whose supporting note sets overlap this much are one theme said two
# ways ("oil"/"crude"); merging on the DOCUMENT sets rather than on token
# similarity is what keeps an omnibus note from chaining themes together.
_CLUSTER_MERGE_JACCARD = 0.5
_CLUSTER_THEME_TERMS = 3         # words in the emitted theme label
_CLUSTER_REPORTS_SHOWN = 3       # newest N reports listed per theme
_CLUSTER_SCAN_CAP = 800          # bounds the walk on a runaway catalog

_CLUSTERS_SCHEMA = "brain.research_clusters.v1"
_CLUSTERS_NOTE = (
    "Convergence is a retrieval summary of what the street is writing about — "
    "not a view, not consensus-as-authority."
)

_MODE_SEARCH, _MODE_CLUSTERS, _MODE_REPORT = "search", "clusters", "report"


def _is_mode(mode, wanted: str) -> bool:
    """True only for an explicit request for `wanted`; anything else searches.

    Lenient on the way in (case, whitespace, a non-string the model invented) and
    strict about the DEFAULT: an unrecognised mode runs the search it always did
    rather than erroring, because the gateway hands model arguments straight
    through and a typo must not cost the user his answer.
    """
    return isinstance(mode, str) and mode.strip().lower() == wanted


def _is_clusters_mode(mode) -> bool:
    """True only for an explicit clusters request (see :func:`_is_mode`)."""
    return _is_mode(mode, _MODE_CLUSTERS)


def _is_report_mode(mode) -> bool:
    """True only for an explicit report request (see :func:`_is_mode`)."""
    return _is_mode(mode, _MODE_REPORT)


def _cluster_tokens(item: dict) -> frozenset[str]:
    """The note's OWN declared subject: filtered tokens of its title.

    Title only — see the block comment above for the measured reason. Markdown
    needs no stripping pass: a token regex anchored on a letter run drops
    asterisks, colons and dashes by itself.
    """
    text = str(item.get("title") or "").lower()
    return frozenset(
        t for t in _CLUSTER_TOKEN_RE.findall(text) if t not in _CLUSTER_STOPWORDS
    )


def _cluster_sort_key(item: dict) -> tuple:
    """Newest-first ordering key, total and stable.

    A note with no readable date sorts LAST rather than first, and `id` closes
    the order so a catalog rebuild cannot reshuffle the output.
    """
    ts = _parse_ts(item.get("published_at"))
    return (ts is None, -ts.timestamp() if ts is not None else 0.0,
            str(item.get("id") or ""))


def _research_clusters(
    items: list[dict],
    *,
    now: datetime,
    min_reports: int = 3,
    min_institutions: int = 2,
    max_clusters: int = 5,
) -> dict:
    """Themes several houses are writing about at once. Deterministic; never raises.

    A theme is a subject TERM plus every note whose title names it. Terms whose
    supporting note sets overlap by >=_CLUSTER_MERGE_JACCARD are folded together
    so one subject said two ways lands once, and the label keeps up to
    _CLUSTER_THEME_TERMS of them.

    A theme is only REPORTED when >=min_reports notes from >=min_institutions
    distinct houses carry it. One house publishing three notes on its own idea is
    not the street converging — it is one desk repeating itself, and the
    institution count is the only thing that separates the two.

    Empty is an honest answer: `clusters: []` means nothing cleared the bar, not
    that the read failed.
    """
    rows: list[tuple[tuple, dict, frozenset[str]]] = []
    for item in items:
        tokens = _cluster_tokens(item)
        if tokens:
            rows.append((_cluster_sort_key(item), item, tokens))
    # Sort BEFORE the cap: `items` arrives in whatever order the catalog builder
    # wrote it, which is not guaranteed to be chronological, so capping the raw
    # list could silently drop the NEWEST notes on a large vintage. Newest-first
    # then truncate keeps the cap a bound on cost, not a bias in what is read.
    rows.sort(key=lambda row: row[0])
    del rows[_CLUSTER_SCAN_CAP:]
    scanned = len(rows)

    # term -> the set of note indices whose title carries it
    support: dict[str, set[int]] = {}
    for index, (_key, _item, tokens) in enumerate(rows):
        for token in tokens:
            support.setdefault(token, set()).add(index)

    floor = max(1, int(min_reports))
    # The ambient ceiling can never fall BELOW the admission floor: on a small
    # catalog a quarter of the notes is fewer than min_reports, so a scaled-only
    # ceiling would classify every shared term as ambient and report nothing —
    # silently, and only on small inputs. max() keeps the floor always reachable
    # and needs no magic minimum-N cliff.
    ceiling = max(scanned * _CLUSTER_DF_CEILING, float(floor))
    candidates = sorted(
        ((len(docs), term) for term, docs in support.items()
         if floor <= len(docs) <= ceiling),
        # Commonest term first, alphabetical among equals: a total order, so the
        # same catalog always folds into the same themes.
        key=lambda row: (-row[0], row[1]),
    )

    themes: list[dict] = []
    for _count, term in candidates:
        docs = support[term]
        for theme in themes:
            union = len(docs | theme["docs"])
            if union and len(docs & theme["docs"]) / union >= _CLUSTER_MERGE_JACCARD:
                theme["terms"].append(term)
                theme["docs"] |= docs
                break
        else:
            themes.append({"terms": [term], "docs": set(docs)})

    reported: list[tuple[tuple, dict]] = []
    for theme in themes:
        members = [rows[i][1] for i in sorted(theme["docs"])]
        institutions = sorted({
            inst for inst in (_first_text(m, "institution") for m in members) if inst
        })
        if len(members) < min_reports or len(institutions) < min_institutions:
            continue
        reported.append(_cluster_projection(theme["terms"], members, institutions))

    # n_institutions desc, n_reports desc, newest first, theme — a total order.
    reported.sort(key=lambda row: row[0])
    return {
        "schema": _CLUSTERS_SCHEMA,
        "asof": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count_scanned": scanned,
        "clusters": [payload for _key, payload in reported[:max(1, int(max_clusters))]],
        "note": _CLUSTERS_NOTE,
    }


def _cluster_projection(terms: list[str], members: list[dict],
                        institutions: list[str]) -> tuple[tuple, dict]:
    """(sort_key, output theme). Literal fields only — no score, no confidence.

    `window_days` is the theme's OWN span, oldest to newest report: "6 houses
    inside 1.7 days" and "6 houses across a fortnight" are different facts about
    convergence, and the catalog's rolling window cannot express either.
    """
    theme = " ".join(terms[:_CLUSTER_THEME_TERMS])
    stamps = [s for s in (_parse_ts(m.get("published_at")) for m in members)
              if s is not None]
    window_days = (round((max(stamps) - min(stamps)).total_seconds() / 86400.0, 1)
                   if len(stamps) > 1 else 0.0)
    newest = max(str(m.get("published_at") or "") for m in members)
    shown = sorted(members, key=_cluster_sort_key)[:_CLUSTER_REPORTS_SHOWN]
    payload = {
        "theme": theme,
        "n_reports": len(members),
        "n_institutions": len(institutions),
        "institutions": institutions,
        "window_days": window_days,
        "top_pick_count": sum(1 for m in members if m.get("top_pick")),
        "reports": [{
            "id": m.get("id"),
            "title": m.get("title"),
            "institution": m.get("institution"),
            "published_at": m.get("published_at"),
        } for m in shown],
    }
    sort_key = (-len(institutions), -len(members), _neg_str_key(newest), theme)
    return sort_key, payload


# --------------------------------------------------------------------------- #
# FUNCTION 2c — full-report escalation (W4): ONE report, its fuller content
# --------------------------------------------------------------------------- #
# OPERATOR RULING (2026-07-31): the vault's full-report escalation is APPROVED
# for PRO members in chat. What that does and does not license:
#
#   * The material is a THIRD PARTY's copyrighted research. engine/research_vault/
#     excerpt.py frames its own caps as "the entire risk surface … an OPERATOR
#     decision, never a builder default"; the same rule governs here. The chat
#     exposure cap is _REPORT_BODY_MAX_CHARS (12,000 chars) — thesis plus core
#     argument, deliberately far under the 60,000 the corpus stores. Raising it is
#     an operator decision, not a tuning knob.
#   * The rights line rides in the payload `note` — the chat equivalent of the
#     watermark app/research.py stamps into a downloaded PDF. It is addressed to
#     the model because the model is what renders the answer: attribute, quote
#     sparingly, synthesize, never reproduce pages.
#   * TIER is the GATEWAY's job (Pro-only for this mode; insider keeps search and
#     clusters). This function still fails CLOSED on a missing `user_ctx`: a call
#     with no identity cannot be metered, and an unmeterable serve of third-party
#     research is exactly what the cap exists to prevent.
#
# The three content layers, cheapest first — a layer that is unavailable is
# DISCLOSED, never faked:
#   1. catalog metadata (committed, public);
#   2. the PUBLIC excerpt (data/research_vault/excerpts.json — already rendered
#      outside the paywall on site/research/<slug>.html, so it costs no new
#      exposure and is the honest fallback when the corpus is unreachable);
#   3. the stored body, via research_vault.corpus.get_document → R2. This is the
#      only paid layer, so it is the only one that debits the hourly view cap.
_EXCERPTS_REL = ("data", "research_vault", "excerpts.json")

_REPORT_SCHEMA = "brain.research_report.v1"
_EVIDENCE_SCHEMA = "brain.research_evidence.v1"
_RESEARCH_VAULT_URL = "https://mastermind-x.com/research_vault.html"
REPORT_BODY_MAX_CHARS = 12_000
_EVIDENCE_QUERY_MAX_CHARS = 512
_EVIDENCE_TERM_MAX_CHARS = 120
_EVIDENCE_TERM_LIMIT = 12
_REPORT_META_MAX_CHARS = 512
_REPORT_TEXT_LAYER_MAX_CHARS = 80
# Defense in depth only — the corpus owner already bounds a passage window
# independent of match length (EVIDENCE_WINDOW_CHARS). This is a second, cheap
# ceiling here so a corrupted/mocked upstream selector still cannot smuggle an
# unbounded string through the projector.
_EVIDENCE_PASSAGE_TEXT_MAX_CHARS = 1_200
# Bounds the link's PERCENT-ENCODED `q=` fragment, not the raw query — a CJK
# character can encode to 9 chars (%XX%XX%XX), so bounding only the raw text
# (_EVIDENCE_QUERY_MAX_CHARS) would let the encoded URL balloon regardless.
_EVIDENCE_LINK_Q_MAX_ENCODED_CHARS = 200
# Named so the model can tell the user where the rest of the report lives. The
# budget COVERS this marker (the _truncate idiom) — a "12,000 + marker" result
# would break any caller sizing a context window off the documented number.
_REPORT_TRUNCATION_MARKER = "…full report continues — available in the Research Vault"
# The catalog clamps summary_points at 8; all of them are kept for a single
# report (the point of the escalation is depth), each clamped to the same
# per-point budget the search results use so the payload stays bounded.
_REPORT_SUMMARY_POINTS_KEPT = 8

# The EXACT key set the `report` object may carry — the _project_event discipline
# (see the module's EPISTEMICS LAW). No score, no confidence, no desk read: this
# is somebody ELSE's note, and the tool's job is to hand it over attributed, not
# to grade it.
REPORT_FIELDS: tuple[str, ...] = (
    "id", "title", "institution", "side", "published_at",
    "summary_points", "excerpt_paragraphs", "body_text", "body_truncated",
)

_REPORT_NOTE = (
    "Third-party institutional research served under the vault's Pro access — "
    "attribute every claim to {institution}, quote sparingly, synthesize in your "
    "own words; never reproduce pages verbatim. Not for redistribution."
)
_REPORT_NOTE_FALLBACK_INSTITUTION = "the publishing institution"
_REPORT_EXCERPT_ONLY = (
    " The full text is not reachable right now, so this is the report's PUBLIC "
    "opening excerpt only — say plainly that you are reading the opening pages, "
    "not the whole note."
)
# The OTHER reason a body comes back empty, and the note above is a false promise
# for it: the corpus measured this PDF as image-only (text_layer 'none'), so there
# is no fuller text to become reachable later — no retry, no repair pass, nothing.
# 'unavailable' and '' keep the excerpt-only note, which is equally true of them:
# our extraction did not run (a HOST fault, healed by ingest._reextract_bodies).
_REPORT_SCAN_ONLY = (
    " This report is a scanned/image-only PDF — the vault holds no machine-readable "
    "text for it, so the public excerpt and summary above are all the text there "
    "is. Say that plainly; do not imply a temporary failure."
)
_REPORT_EVIDENCE_NOTE = (
    " The body_text above contains query-centered supporting passage(s), not the "
    "whole note. Ground the answer only in evidence.passages, preserve the "
    "publisher's meaning, and include evidence.open_url as an 'Open source' link."
)
_REPORT_NO_EVIDENCE = (
    " No matching passage for the exact question was found in the stored research "
    "text. No full-text view was served; it was not charged. Say that plainly; do "
    "not infer an answer from absence. Brain may re-call this same report with an "
    "empty query to read it generically, or offer the source-opening link for "
    "manual review."
)
_REPORT_NO_USABLE_PASSAGE = (
    " Matching terms were found, but no usable passage text was available. No "
    "full-text view was served or charged; do not describe this as a scan or "
    "extraction failure."
)
# Distinct from _REPORT_SCAN_ONLY: an image-only PDF has no text at all, but an
# identity-unverified row may well have readable text — it just cannot be bound
# to a canonical source-PDF fingerprint, so nothing sourced from it is served.
_REPORT_SOURCE_UNVERIFIED = (
    " This report's stored text carries no verified source-PDF fingerprint, so "
    "no full-text view was served or charged. This is a source-identity gap, "
    "not a scan or extraction failure — say that plainly; do not describe the "
    "document as unreadable or image-only."
)

# view_ratelimit.allow() keys a SECOND ledger on sha256(ip)[:16], and maps an
# empty/'unknown' ip to the literal bucket 'noip' — every chat user would then
# share one hourly counter and one Pro member's reading would deny everybody
# else's. So chat passes a per-user synthetic marker instead: the hash is
# hex-only and unique per user, which puts the ip ledger in lockstep with the
# user ledger (effective cap = the plain hourly limit, RESEARCH_VIEW_HOURLY).
# The gateway's `ip_hint` is deliberately NOT used as that key — an office NAT
# would collide unrelated Pro members into one bucket, which is the same bug.
_BRAIN_VIEW_IP_PREFIX = "brain:"

_REPORT_ERR_PRO = (
    "The full-report reader is a Pro capability and this call carried no "
    "signed-in Pro identity — explain the gate plainly and answer from the vault "
    "summaries instead. Never describe a report you have not read."
)
_REPORT_ERR_NOT_FOUND = (
    "No report with that id is in the vault catalog. Re-run search_research "
    "(mode='search' or mode='clusters') and use an id from those results — never "
    "guess an id, and never invent what a report says."
)
_REPORT_ERR_VAULT = (
    "The research vault catalog could not be read, so this report could not be "
    "looked up. Say so plainly rather than describing a note you have not read."
)
_REPORT_ERR_LIMIT = (
    "This account has reached its hourly full-report limit. Tell the user "
    "plainly, answer from the summaries already retrieved, and note that the cap "
    "resets at the top of the hour."
)


def _excerpt_paragraphs(root: Path, doc_id: str) -> list[str]:
    """The committed PUBLIC excerpt paragraphs for `doc_id` ([] when absent).

    Reads data/research_vault/excerpts.json ({"schema":1,"excerpts":{id:[…]}}),
    the same snapshot the SEO research pages render outside the paywall. Coverage
    is partial (a scanned PDF with no text layer has no excerpt), so [] is a
    normal answer, not a failure. Never raises.
    """
    payload = _read_json(root.joinpath(*_EXCERPTS_REL))
    if not isinstance(payload, dict):
        return []
    bucket = payload.get("excerpts")
    if not isinstance(bucket, dict):
        return []
    paras = bucket.get(doc_id)
    if not isinstance(paras, list):
        return []
    return [p.strip() for p in paras if isinstance(p, str) and p.strip()]


def _load_corpus_document(doc_id: str):
    """research_vault.corpus.get_document(doc_id), or None. Never raises.

    Imported lazily and called through the MODULE (not a from-import) so the
    attribute resolves at call time — the corpus reader is the seam tests replace,
    and an engine module that cannot be imported at all must degrade to the
    excerpt rather than take the chat turn down.
    """
    try:
        from engine.research_vault import corpus as corpus_mod  # noqa: PLC0415
        return corpus_mod.get_document(doc_id)
    except Exception:  # noqa: BLE001 — no corpus → excerpt-only, disclosed
        return None


def _load_evidence_document(doc_id: str):
    """The same corpus row plus source-binding metadata for R1B, or None."""
    try:
        from engine.research_vault import corpus as corpus_mod  # noqa: PLC0415
        return corpus_mod.get_evidence_document(doc_id)
    except Exception:  # noqa: BLE001 — no corpus → disclosed evidence shortfall
        return None


def _select_evidence(document, query: str) -> dict:
    """Run the corpus owner's deterministic selector; fail to body_unavailable."""
    try:
        from engine.research_vault import corpus as corpus_mod  # noqa: PLC0415
        return corpus_mod.find_evidence_passages(document or {}, query)
    except Exception:  # noqa: BLE001 — retrieval must not take the chat turn down
        return {
            "status": "body_unavailable", "query": str(query or ""),
            "passages": [], "source_binding": {},
        }


def _evidence_requested(query: str) -> bool:
    """Classify report intent, then use the corpus owner's one atom admission law."""
    try:
        from engine.research_vault import corpus as corpus_mod  # noqa: PLC0415
        if _is_generic_report_intent(query, corpus_mod):
            return False
        return corpus_mod.evidence_query_is_meaningful(query)
    except Exception:  # noqa: BLE001 — preserve the generic report path on failure
        return False


# Self-sufficient generic-summary triggers: a single occurrence classifies as
# generic INTENT on its own (no co-occurring document word required) — the real
# safety gate is the residual-emptiness check below, not this vocabulary. A
# genuine specific-topic question using one of these words (e.g. "Explain the
# Fed's rate decision") still leaves a non-empty residual and stays evidence.
_GENERIC_EN_INTENT_WORDS = frozenset({
    "argument", "arguments", "argue", "overview", "summarise", "summarize",
    "summary", "gist", "thesis", "takeaway", "takeaways", "explain", "tell",
    "walk", "break",
})
_GENERIC_EN_DOCUMENT_WORDS = frozenset({
    "document", "documents", "note", "notes", "paper", "papers", "report",
    "reports", "research", "study", "studies",
})
# Structural scaffolding: politeness, question form, pronouns, and output-format
# cues that carry no market/document content of their own. None of these is a
# real topic word, so stripping them cannot hide a genuine residual question.
_GENERIC_EN_SCAFFOLDING_WORDS = frozenset({
    "can", "could", "does", "give", "is", "it", "main", "please", "the",
    "this", "what", "you", "your", "provide", "down", "key", "bullet",
    "bullets", "point", "points", "format", "say", "says", "said", "me",
})
_TLDR_RE = re.compile(r"\btl\s*;?\s*dr\b")
# A 1-3 word Titlecase run immediately before a document word ("the Goldman
# report", "this Example Bank note") is a document-TARGET modifier, not a
# residual topic — this is a structural (position + capitalization) rule, never
# an institution allowlist: any capitalized word in that slot qualifies.
_EN_TARGET_MODIFIER_RE = re.compile(
    r"(?:\b[A-Z][A-Za-z]*\b\s+){1,3}(?=(?:"
    + "|".join(sorted(_GENERIC_EN_DOCUMENT_WORDS, reverse=True))
    + r")\b)"
)
_GENERIC_ZH_INTENT_PHRASES = (
    "总结", "概括", "摘要", "主要观点", "论点", "分析",
    "讲了什么", "说了什么", "说的是什么",
)
_GENERIC_ZH_DOCUMENT_PHRASES = ("报告", "研究", "论文", "文件", "文档", "笔记")
_GENERIC_ZH_SCAFFOLDING_PHRASES = ("请", "这份", "这篇", "一下", "帮我", "是什么")


def _is_generic_report_intent(query, corpus_mod) -> bool:
    """True when named summary/argument intent leaves no corpus content atom.

    This deliberately classifies chat CATEGORY/STRUCTURE in Brain, never a
    sentence table: an intent trigger (EN word, ZH phrase, or a TL;DR spelling)
    must be present, and — after removing that trigger plus document-target and
    politeness/question/format scaffolding — the corpus owner must find no
    meaningful content atom left in the residual. A real topic (a ticker, a
    theme, a Chinese key phrase) always survives this strip and keeps the query
    on the evidence path; the selector stays the sole atom/stopword owner.
    """
    nfkc = unicodedata.normalize("NFKC", str(query or ""))
    # Strip document-target modifiers (institution/proper-noun before a document
    # word) BEFORE casefolding — capitalization is what identifies the slot.
    nfkc = _EN_TARGET_MODIFIER_RE.sub(" ", nfkc)
    normalized = nfkc.casefold()

    en_words = re.findall(r"[a-z]+", normalized)
    has_en_intent = bool(set(en_words) & _GENERIC_EN_INTENT_WORDS)
    has_zh_intent = any(term in normalized for term in _GENERIC_ZH_INTENT_PHRASES)
    has_tldr = bool(_TLDR_RE.search(normalized))
    if not (has_en_intent or has_zh_intent or has_tldr):
        return False

    residual = _TLDR_RE.sub(" ", normalized)
    for word in (_GENERIC_EN_INTENT_WORDS | _GENERIC_EN_DOCUMENT_WORDS
                 | _GENERIC_EN_SCAFFOLDING_WORDS):
        residual = re.sub(rf"\b{re.escape(word)}\b", " ", residual)
    for phrase in (_GENERIC_ZH_INTENT_PHRASES + _GENERIC_ZH_DOCUMENT_PHRASES
                   + _GENERIC_ZH_SCAFFOLDING_PHRASES):
        residual = residual.replace(phrase, " ")
    return not corpus_mod.evidence_query_is_meaningful(residual)


def _peek_report_view(user_id: str, now: datetime) -> dict | None:
    """Read the canonical report-view limiter without debiting it; fail open."""
    try:
        from engine.research_vault import view_ratelimit  # noqa: PLC0415
        info = view_ratelimit.peek(
            user_id, _BRAIN_VIEW_IP_PREFIX + user_id, now=now)
        return info if isinstance(info, dict) else None
    except Exception:  # noqa: BLE001 — same availability rule as allow()
        return None


def _charge_report_view(user_id: str, now: datetime) -> tuple[bool, dict]:
    """Debit ONE hourly view for this user. Returns (allowed, {remaining, limit}).

    Called exactly once per served BODY and never for the excerpt-only fallback —
    the excerpt is already public, and metering a public read would deny a member
    material he can see on the website. The report-mode PREFLIGHT (peeked before
    this function ever runs) is a separate, uniform gate applied before either the
    generic or evidence reader — it may withhold even the public excerpt from an
    exhausted caller, because letting an exhausted request through to a cheaper
    fallback while a servable one is denied would itself be a paid-body-presence
    oracle. That preflight does not change the quota owner or its state; this
    function still debits only an actually-served paid body.

    Fails OPEN on an unusable limiter (import/IO error), mirroring
    view_ratelimit's own documented rule: a broken ledger must not lock a paying
    subscriber out of what he bought.
    """
    try:
        from engine.research_vault import view_ratelimit  # noqa: PLC0415
        return view_ratelimit.allow(
            user_id, _BRAIN_VIEW_IP_PREFIX + user_id, now=now)
    except Exception:  # noqa: BLE001 — fail-open, same as the ledger itself
        return True, {}


def _slice_report_body(body) -> tuple[str, bool]:
    """(body within the cap, was_truncated). Cut at a word boundary, marked.

    The marker is INSIDE the budget, so the returned text never exceeds
    :data:`REPORT_BODY_MAX_CHARS` — and the model is told where the rest lives
    instead of being handed a sentence that stops mid-word with no explanation.
    """
    text = str(body or "")
    if len(text) <= REPORT_BODY_MAX_CHARS:
        return text, False
    room = max(0, REPORT_BODY_MAX_CHARS - len(_REPORT_TRUNCATION_MARKER) - 2)
    cut = text[:room].rsplit(" ", 1)[0].rstrip() if room else ""
    return f"{cut}\n\n{_REPORT_TRUNCATION_MARKER}", True


def _meta_field(item: dict, document, key: str) -> str:
    """Catalog value for `key`, else the corpus row's, else ''.

    Catalog first because it is the PUBLIC, editorially-cleaned record (titles are
    repaired there — see research_vault.title); the corpus row is the fallback for
    a catalog field that happens to be blank.
    """
    return (_first_text(item, key)
            or (_first_text(document, key) if isinstance(document, dict) else None)
            or "")


def _positive_int(value) -> int | None:
    """A literal positive JSON/Python integer, never a coercible lookalike."""
    return value if type(value) is int and value > 0 else None


def _partial_evidence_search_note(evidence) -> str:
    """Distinguish complete, partial, and unverified search coverage."""
    binding = (evidence or {}).get("source_binding") if isinstance(evidence, dict) else None
    binding = binding if isinstance(binding, dict) else {}
    stored = _positive_int(binding.get("stored_char_count"))
    source = _positive_int(binding.get("source_char_count"))
    if binding.get("coverage") == "prefix_partial" and stored and source and source > stored:
        return (
            f" Only the stored prefix ({stored} of {source} source characters) was "
            "searched; absence does not prove the omitted tail lacks the topic."
        )
    if binding.get("coverage") == "unknown":
        return (
            " Coverage could not be verified; absence is not evidence that the "
            "source lacks the topic."
        )
    return ""


def _nonnegative_int(value) -> int | None:
    """A literal nonnegative JSON/Python integer, never a coercible lookalike."""
    return value if type(value) is int and value >= 0 else None


def _sha256_or_empty(value) -> str:
    """Return only an already-canonical lowercase SHA-256 fingerprint.

    Source identity is not a user convenience field: case-folding or trimming a
    malformed upstream value would silently manufacture a different canonical
    claim. Reject any non-string, padded, uppercase, or otherwise noncanonical
    representation instead.
    """
    return value if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) else ""


def _bounded_report_text(value, limit: int = _REPORT_META_MAX_CHARS) -> str:
    """Bound one display-only metadata string without coercing arbitrary objects."""
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[:max(0, limit - 1)] + ("…" if limit else "")


def _bounded_evidence_query(query) -> str:
    text = str(query or "")
    if len(text) <= _EVIDENCE_QUERY_MAX_CHARS:
        return text
    return text[:_EVIDENCE_QUERY_MAX_CHARS - 1] + "…"


def _evidence_link_query(query) -> str:
    """NFKC-normalized, bounded, user-authored text for the link's ``q`` — never
    publisher/passage text. Blank/whitespace-only input omits ``q`` entirely."""
    text = str(query or "").strip()
    if not text:
        return ""
    return _bounded_evidence_query(unicodedata.normalize("NFKC", text)).strip()


def _evidence_open_url(report_id: str, *, page=None, q: str = "") -> str:
    """Public, rights-safe Research Vault URL — never publisher/passage text or
    an internal path.

    ``doc`` is the only query-string param. An optional fragment carries a
    positive ``page`` and/or the bounded user-authored ``q`` — never publisher
    match text, source spans/hashes, or internal paths. Passage-level callers
    pass only ``page``; the top-level evidence link may add ``q`` once.
    """
    url = f"{_RESEARCH_VAULT_URL}?{urlencode([('doc', str(report_id or ''))])}"
    fragment: list[str] = []
    page_number = _positive_int(page)
    if page_number is not None:
        fragment.append(f"page={page_number}")
    q_text = _evidence_link_query(q)
    if q_text:
        # Percent-encoding inflates non-ASCII (a CJK char can become 9 chars,
        # %XX%XX%XX) — bound the ENCODED form, not just the raw text, so a long
        # Chinese query cannot balloon the response-string budget through the URL.
        encoded = quote(q_text, safe="")
        while encoded and len(encoded) > _EVIDENCE_LINK_Q_MAX_ENCODED_CHARS:
            q_text = q_text[:-1]
            encoded = quote(q_text, safe="")
        if encoded:
            fragment.append(f"q={encoded}")
    if fragment:
        url += "#" + "&".join(fragment)
    return url


def _project_evidence_passage(raw, report_id: str) -> dict | None:
    """Literal R1B passage projection; no upstream dict passthrough.

    Fails CLOSED (omits the whole passage) rather than raising or coercing on
    a malformed upstream shape: non-integer/negative/bool locator offsets, an
    incoherent span (not start <= match_start < match_end <= end), or non-string
    text/match_text. A non-string field is never rendered as a Python repr.
    """
    if not isinstance(raw, dict):
        return None
    locator_raw = raw.get("locator") if isinstance(raw.get("locator"), dict) else {}
    kind = str(locator_raw.get("kind") or "text_span")
    if kind not in {"text_span", "page_text_span"}:
        kind = "text_span"
    start_char = _nonnegative_int(locator_raw.get("start_char"))
    end_char = _nonnegative_int(locator_raw.get("end_char"))
    match_start_char = _nonnegative_int(locator_raw.get("match_start_char"))
    match_end_char = _nonnegative_int(locator_raw.get("match_end_char"))
    if None in (start_char, end_char, match_start_char, match_end_char):
        return None
    if not (start_char <= match_start_char < match_end_char <= end_char):
        return None
    text = raw.get("text")
    match_text = raw.get("match_text")
    if not isinstance(text, str) or not isinstance(match_text, str):
        return None

    # A source locator is a claim about the emitted literal slice, not decorative
    # metadata. Reject mismatched upstream text before any defensive clipping.
    span_chars = end_char - start_char
    relative_match_start = match_start_char - start_char
    relative_match_end = match_end_char - start_char
    if len(text) != span_chars:
        return None
    if text[relative_match_start:relative_match_end] != match_text:
        return None

    # Keep a bounded source window around the match and rewrite every absolute
    # offset to the exact emitted slice. If the match itself exceeds the cap, the
    # bounded prefix remains a truthful literal subspan with coherent locators.
    clip_start = 0
    clip_end = len(text)
    if len(text) > _EVIDENCE_PASSAGE_TEXT_MAX_CHARS:
        cap = _EVIDENCE_PASSAGE_TEXT_MAX_CHARS
        match_chars = relative_match_end - relative_match_start
        if match_chars >= cap:
            clip_start = relative_match_start
            clip_end = min(len(text), clip_start + cap)
        else:
            room = cap - match_chars
            clip_start = max(0, relative_match_start - (room // 2))
            clip_end = min(len(text), clip_start + cap)
            if clip_end - clip_start < cap:
                clip_start = max(0, clip_end - cap)

    clipped_match_start = max(relative_match_start, clip_start)
    clipped_match_end = min(relative_match_end, clip_end)
    if clipped_match_start >= clipped_match_end:
        return None
    source_text = text
    text = source_text[clip_start:clip_end]
    match_text = source_text[clipped_match_start:clipped_match_end]
    start_char += clip_start
    end_char = start_char + len(text)
    match_start_char = start_char + (clipped_match_start - clip_start)
    match_end_char = start_char + (clipped_match_end - clip_start)

    page = _positive_int(locator_raw.get("page")) if kind == "page_text_span" else None
    if kind == "page_text_span" and page is None:
        return None
    locator = {
        "kind": kind,
        "start_char": start_char,
        "end_char": end_char,
        "match_start_char": match_start_char,
        "match_end_char": match_end_char,
    }
    if page is not None:
        locator["page"] = page
    terms = raw.get("matched_terms")
    terms = [term[:_EVIDENCE_TERM_MAX_CHARS] for term in terms if isinstance(term, str)] \
        if isinstance(terms, list) else []
    terms = terms[:_EVIDENCE_TERM_LIMIT]
    return {
        "text": text,
        "match_text": match_text,
        "matched_terms": terms,
        "locator": locator,
        "open_url": _evidence_open_url(report_id, page=page),
    }


def _project_evidence(raw, *, report_id: str, published_at: str,
                      query: str, allowed: bool) -> dict:
    """Whitelisted evidence envelope bound to one report and one access decision."""
    payload = raw if isinstance(raw, dict) else {}
    status = str(payload.get("status") or "body_unavailable")
    if status not in {"matched", "no_matching_passage", "body_unavailable"}:
        status = "body_unavailable"
    binding_raw = payload.get("source_binding") \
        if isinstance(payload.get("source_binding"), dict) else {}
    coverage = str(binding_raw.get("coverage") or "unknown")
    coverage = coverage if coverage in {"complete", "prefix_partial", "unknown"} else "unknown"
    stored = _nonnegative_int(binding_raw.get("stored_char_count"))
    source = _nonnegative_int(binding_raw.get("source_char_count"))
    tail_raw = binding_raw.get("tail_omitted")
    tail_is_valid = tail_raw is None or isinstance(tail_raw, bool)
    tail = tail_raw if isinstance(tail_raw, bool) else None
    if not tail_is_valid:
        coverage = "unknown"
    elif coverage == "complete" and (stored is None or source != stored):
        coverage = "unknown"
    elif coverage == "prefix_partial" and (stored is None or source is None or source <= stored):
        coverage = "unknown"
    if coverage == "unknown":
        source, tail = None, None
    elif coverage == "complete":
        tail = False
    else:
        tail = True
    binding = {
        "report_id": report_id,
        "published_at": _bounded_report_text(published_at),
        "content_sha256": _sha256_or_empty(binding_raw.get("content_sha256")),
        "stored_body_sha256": _sha256_or_empty(binding_raw.get("stored_body_sha256")),
        "coverage": coverage,
        "source_char_count": source,
        "stored_char_count": stored,
        "tail_omitted": tail,
        "text_layer": _bounded_report_text(
            binding_raw.get("text_layer"), _REPORT_TEXT_LAYER_MAX_CHARS),
        "page_count": _positive_int(binding_raw.get("page_count")),
    }
    passages_raw = payload.get("passages") if status == "matched" else []
    passages_raw = passages_raw if isinstance(passages_raw, list) else []
    projected = []
    for passage in passages_raw:
        item = _project_evidence_passage(passage, report_id)
        if item is not None:
            projected.append(item)
    # Top-level open_url may carry the bounded user query once (fragment `q=`)
    # to avoid repeated inflation across passages; passage-level open_url stays
    # doc+page only (see _project_evidence_passage).
    top_page = None
    if projected:
        first_locator = projected[0].get("locator") or {}
        if first_locator.get("kind") == "page_text_span":
            top_page = first_locator.get("page")
    open_url = _evidence_open_url(report_id, page=top_page, q=query)
    return {
        "schema": _EVIDENCE_SCHEMA,
        "status": status,
        "query": _bounded_evidence_query(query),
        "report_id": report_id,
        "published_at": _bounded_report_text(published_at),
        "passages": projected,
        "source_binding": binding,
        "access": {"decision": "allowed" if allowed else "not_served",
                   "metered": bool(allowed)},
        "open_url": open_url,
    }


def _project_report(
    *,
    report_id: str,
    title: str,
    institution: str,
    side: str,
    published_at: str,
    summary_points: list[str],
    excerpt_paragraphs: list[str],
    body_text: str,
    body_truncated: bool,
) -> dict:
    """Build the report object from the whitelisted fields only (REPORT_FIELDS).

    Keyword-only and fully literal, exactly like :func:`_project_event`: no dict
    spread, no passthrough of the catalog item or the corpus row, so nothing an
    upstream lane adds later can reach the model's context by accident.
    """
    return {
        "id": report_id,
        "title": _bounded_report_text(title),
        "institution": _bounded_report_text(institution),
        "side": _bounded_report_text(side),
        "published_at": _bounded_report_text(published_at),
        "summary_points": summary_points,
        "excerpt_paragraphs": excerpt_paragraphs,
        "body_text": body_text,
        "body_truncated": body_truncated,
    }


def _response_string_total(value) -> int:
    """Recursive character count for every string value in one tool response."""
    if isinstance(value, str):
        return len(value)
    if isinstance(value, dict):
        return sum(_response_string_total(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_response_string_total(item) for item in value)
    return 0


def _trim_string_list(values, overflow: int) -> int:
    """Remove/truncate list tail strings until ``overflow`` characters are gone."""
    if not isinstance(values, list):
        return overflow
    while values and overflow > 0:
        last = values[-1]
        if not isinstance(last, str):
            values.pop()
            continue
        if len(last) <= overflow:
            overflow -= len(last)
            values.pop()
            continue
        values[-1] = last[:len(last) - overflow].rstrip()
        overflow = 0
        if not values[-1]:
            values.pop()
    return overflow


def _fit_evidence_response_budget(response: dict) -> bool:
    """Fit an evidence response under the shared 12k string ceiling in place.

    Public excerpts and summaries yield first. The legacy ``body_text`` duplicate
    may collapse to the first literal match while the authoritative evidence
    passage remains intact. Only then are optional matched-term labels and extra
    passages removed. Identity, hashes, rights note, and one usable passage are
    never silently truncated.
    """
    report = response.get("report") if isinstance(response, dict) else None
    evidence = response.get("evidence") if isinstance(response, dict) else None
    if not isinstance(report, dict) or not isinstance(evidence, dict):
        return False

    def overflow() -> int:
        return max(0, _response_string_total(response) - REPORT_BODY_MAX_CHARS)

    over = overflow()
    over = _trim_string_list(report.get("excerpt_paragraphs"), over)
    if over:
        over = _trim_string_list(report.get("summary_points"), overflow())

    passages = evidence.get("passages")
    passages = passages if isinstance(passages, list) else []
    matched = evidence.get("status") == "matched"
    if overflow() and matched and passages:
        first = passages[0] if isinstance(passages[0], dict) else {}
        support = first.get("match_text") or first.get("text") or ""
        if isinstance(support, str) and support:
            report["body_text"] = support
            report["body_truncated"] = True

    for passage in reversed(passages):
        if not overflow():
            break
        if isinstance(passage, dict):
            _trim_string_list(passage.get("matched_terms"), overflow())

    while overflow() and len(passages) > 1:
        passages.pop()
        if matched:
            first = passages[0] if isinstance(passages[0], dict) else {}
            support = first.get("match_text") or first.get("text") or ""
            if isinstance(support, str) and support:
                report["body_text"] = support
                report["body_truncated"] = True

    # The bounded query is useful but not source identity; yield its tail only if
    # all public/redundant fields above were insufficient.
    over = overflow()
    query = evidence.get("query")
    if over and isinstance(query, str):
        evidence["query"] = query[:max(0, len(query) - over)]

    return _response_string_total(response) <= REPORT_BODY_MAX_CHARS


def _report_error(code: str, note: str, **extra) -> dict:
    """One bounded honest error envelope; caller text never escapes the ceiling."""
    projected = dict(extra)
    if "report_id" in projected:
        projected["report_id"] = _bounded_report_text(projected.get("report_id"))
    for key in ("remaining", "limit"):
        if key in projected:
            projected[key] = _nonnegative_int(projected.get(key))
    return {"schema": _REPORT_SCHEMA, "error": code, "note": note, **projected}


def _evidence_body(selection) -> tuple[str, bool]:
    """Project selected passages and disclose whether source text was omitted.

    The corpus selector owns the exact source slices. This helper only joins
    those slices for the frozen ``report.body_text`` consumer and derives its
    legacy ``body_truncated`` fact from the bound source spans. The evidence
    envelope remains authoritative for exact text and locators.
    """
    payload = selection if isinstance(selection, dict) else {}
    passages = payload.get("passages")
    passages = passages if isinstance(passages, list) else []

    texts: list[str] = []
    ranges: list[tuple[int, int]] = []
    for passage in passages:
        if not isinstance(passage, dict):
            continue
        text = str(passage.get("text") or "")
        if text.strip():
            texts.append(text)
        locator = passage.get("locator")
        if not isinstance(locator, dict):
            continue
        try:
            start = int(locator.get("start_char"))
            end = int(locator.get("end_char"))
        except (TypeError, ValueError):
            continue
        if 0 <= start < end:
            ranges.append((start, end))

    body_text = "\n\n".join(texts)
    if not body_text:
        return "", False
    body_text, cap_truncated = _slice_report_body(body_text)

    binding = payload.get("source_binding")
    binding = binding if isinstance(binding, dict) else {}
    stored_chars = _positive_int(binding.get("stored_char_count"))
    fully_covered = False
    if binding.get("coverage") == "complete" and stored_chars is not None and ranges:
        cursor = 0
        for start, end in sorted(ranges):
            if start > cursor:
                break
            cursor = max(cursor, end)
            if cursor >= stored_chars:
                fully_covered = True
                break
    return body_text, cap_truncated or not fully_covered


def _research_report(root: Path, report_id, *, query="", user_ctx,
                     now: datetime) -> dict:
    """One report's generic body or exact-question evidence for a PRO member.

    Order is deliberate and each step is its own gate:
      1. identity — no `user_ctx`/user_id → pro_required (fail CLOSED; an
         unmeterable serve of third-party research is the thing being prevented);
      2. EXISTENCE in the committed catalog — an id the catalog does not carry
         never reaches the corpus, so a hallucinated id cannot probe the store;
      3. public layers — catalog metadata + the committed excerpt;
      4. the corpus selector's admission rule chooses deterministic, source-bound
         passages or the existing generic note path;
      5. an exhausted evidence request is denied before selection; ONLY text that
         will actually be served debits one hourly view;
      6. the whitelisted report/evidence projections + the rights note.
    """
    uid = str((user_ctx or {}).get("user_id") or "").strip()
    if not uid:
        return _report_error("pro_required", _REPORT_ERR_PRO)

    rid = str(report_id or "").strip()

    try:
        items = _catalog_items(root)
    except Exception:  # noqa: BLE001
        items = None
    if items is None:
        return _report_error("vault_unavailable", _REPORT_ERR_VAULT, report_id=rid)

    item = None
    if rid:
        for candidate in items:
            if str(candidate.get("id") or "") == rid:
                item = candidate
                break
    if item is None:
        return _report_error("report_not_found", _REPORT_ERR_NOT_FOUND, report_id=rid)

    points = item.get("summary_points")
    points = [p for p in points if isinstance(p, str)] if isinstance(points, list) else []
    paragraphs = _excerpt_paragraphs(root, rid)

    evidence_query = str(query or "")
    evidence_requested = _evidence_requested(evidence_query)
    preflight = _peek_report_view(uid, now)
    if (isinstance(preflight, dict)
            and preflight.get("remaining") == 0):
        return _report_error(
            "view_limit_reached", _REPORT_ERR_LIMIT,
            report_id=rid, remaining=0, limit=preflight.get("limit"))
    document = (
        _load_evidence_document(rid)
        if evidence_requested
        else _load_corpus_document(rid)
    )
    # Independent re-check (defense in depth alongside the corpus owner's own
    # fail-closed gate) so the note can distinguish an identity gap from a scan.
    identity_ok = bool(_sha256_or_empty((document or {}).get("content_sha256"))) \
        if isinstance(document, dict) else False

    quota: dict | None = None
    evidence: dict | None = None
    pending_evidence_charge = False
    matched_without_usable_text = False
    if evidence_requested:
        selection = _select_evidence(document, evidence_query)
        # Projection is the final trust boundary. Validate/clip every passage and
        # canonical binding before body assembly or quota mutation; a raw selector
        # status is never sufficient debit authority.
        evidence = _project_evidence(
            selection,
            report_id=rid,
            published_at=_meta_field(item, document, "published_at"),
            query=evidence_query,
            allowed=False,
        )
        status = str(evidence.get("status") or "body_unavailable")
        binding = evidence.get("source_binding") or {}
        binding_ok = bool(
            binding.get("content_sha256") and binding.get("stored_body_sha256"))
        candidate_body, candidate_truncated = _evidence_body(evidence)
        if status == "matched" and (not binding_ok or not candidate_body):
            evidence["status"] = "body_unavailable"
            evidence["passages"] = []
            status = "body_unavailable"
            candidate_body, candidate_truncated = "", False
            raw_passages = selection.get("passages") if isinstance(selection, dict) else None
            matched_without_usable_text = binding_ok or not raw_passages

        if status == "matched":
            # A matched projection is only a draft until the COMPLETE response
            # fits the shared context ceiling. Quota mutation happens after that
            # final invariant, never on selector status or a partial envelope.
            pending_evidence_charge = True
            body_text, truncated = candidate_body, candidate_truncated
        else:
            body_text, truncated = "", False
    else:
        body_raw = str((document or {}).get("body") or "")
        if body_raw.strip():
            allowed, info = _charge_report_view(uid, now)
            if not allowed:
                return _report_error(
                    "view_limit_reached", _REPORT_ERR_LIMIT,
                    report_id=rid, remaining=0, limit=(info or {}).get("limit"))
            quota = {"remaining": (info or {}).get("remaining"),
                     "limit": (info or {}).get("limit")}
            body_text, truncated = _slice_report_body(body_raw)
        else:
            body_text, truncated = "", False

    institution = _bounded_report_text(_meta_field(item, document, "institution"))
    rights_note = _REPORT_NOTE.format(
        institution=institution or _REPORT_NOTE_FALLBACK_INSTITUTION)
    note = rights_note
    if evidence_requested:
        status = str((evidence or {}).get("status") or "body_unavailable")
        if status == "matched":
            note += _REPORT_EVIDENCE_NOTE
        elif status == "no_matching_passage":
            note += _REPORT_NO_EVIDENCE + _partial_evidence_search_note(evidence)
        elif matched_without_usable_text:
            note += _REPORT_NO_USABLE_PASSAGE
        elif not identity_ok:
            note += _REPORT_SOURCE_UNVERIFIED
        else:
            layer = str((document or {}).get("text_layer") or "") \
                if isinstance(document, dict) else ""
            note += _REPORT_SCAN_ONLY if layer == "none" else _REPORT_EXCERPT_ONLY
    elif quota is None:
        # No body was served. WHY there is none decides which sentence is honest:
        # a measured 'none' is a scan (nothing more will ever exist), everything
        # else — no corpus row at all, an unmeasured row, a host-fault
        # 'unavailable' — is a shortfall that a later run may close.
        layer = str((document or {}).get("text_layer") or "") \
            if isinstance(document, dict) else ""
        note += _REPORT_SCAN_ONLY if layer == "none" else _REPORT_EXCERPT_ONLY

    response = {
        "schema": _REPORT_SCHEMA,
        "asof": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "report": _project_report(
            report_id=rid,
            title=_meta_field(item, document, "title"),
            institution=institution,
            side=_meta_field(item, document, "side"),
            published_at=_meta_field(item, document, "published_at"),
            summary_points=[_truncate(p) for p in points[:_REPORT_SUMMARY_POINTS_KEPT]],
            excerpt_paragraphs=paragraphs,
            body_text=body_text,
            body_truncated=truncated,
        ),
        "quota": quota,
        "evidence": evidence,
        "note": note,
    }

    if evidence_requested:
        # This is the last pure transformation before a paid-view mutation. It
        # counts EVERY response string—including public excerpts, metadata, URLs,
        # duplicated passage text, terms, and notes—not merely report.body_text.
        budget_ok = _fit_evidence_response_budget(response)
        projected = response.get("evidence")
        projected = projected if isinstance(projected, dict) else {}
        final_passages = projected.get("passages")
        final_passages = final_passages if isinstance(final_passages, list) else []
        final_body = response["report"].get("body_text")
        final_match_is_servable = bool(
            budget_ok
            and projected.get("status") == "matched"
            and final_passages
            and isinstance(final_body, str)
            and final_body.strip()
        )

        if not budget_ok and not pending_evidence_charge:
            # Even an unmetered no-match/body-unavailable envelope must honor the
            # same caller context ceiling. Public/contextual fields yield first;
            # the honest retrieval status and source identity remain intact.
            response["report"]["summary_points"] = []
            response["report"]["excerpt_paragraphs"] = []
            projected["query"] = ""
            if not _fit_evidence_response_budget(response):
                return _report_error(
                    "body_unavailable",
                    "This report could not be represented within the response "
                    "safety ceiling. No full-text view was served or charged.",
                    report_id=rid,
                )

        if pending_evidence_charge and not final_match_is_servable:
            # Fail closed before touching quota. Keep public identity only and
            # state the shortfall honestly; never charge a projection that could
            # not survive validation or the complete response budget.
            pending_evidence_charge = False
            projected["status"] = "body_unavailable"
            projected["passages"] = []
            projected["query"] = ""
            projected["access"] = {"decision": "not_served", "metered": False}
            response["report"]["summary_points"] = []
            response["report"]["excerpt_paragraphs"] = []
            response["report"]["body_text"] = ""
            response["report"]["body_truncated"] = False
            response["quota"] = None
            response["note"] = rights_note + _REPORT_NO_USABLE_PASSAGE
            if not _fit_evidence_response_budget(response):
                return _report_error(
                    "body_unavailable",
                    "This report could not be served within the response safety "
                    "ceiling. No full-text view was served or charged.",
                    report_id=rid,
                )

        if pending_evidence_charge:
            allowed, info = _charge_report_view(uid, now)
            if not allowed:
                return _report_error(
                    "view_limit_reached", _REPORT_ERR_LIMIT,
                    report_id=rid, remaining=0, limit=(info or {}).get("limit"))
            response["quota"] = {
                "remaining": _nonnegative_int((info or {}).get("remaining")),
                "limit": _nonnegative_int((info or {}).get("limit")),
            }
            projected["access"] = {"decision": "allowed", "metered": True}

    return response


def search_research(
    root: Path,
    query: str = "",
    limit: int = _RESEARCH_LIMIT_DEFAULT,
    *,
    mode: str | None = None,
    report_id: str = "",
    user_ctx: dict | None = None,
    now: datetime | None = None,
) -> dict:
    """Keyword-search the research vault — THIRD-PARTY views, not the desk's own.

    Deterministic and offline: no embeddings, no network, no LLM. Per item,
        score = (3.0 × distinct title hits)
              + (1.5 × distinct summary hits)
              + (2.0 × distinct institution word hits)
              + (1.0 if top_pick)
        score × max(0.35, 1 - age_days/45)

    The top_pick bonus only applies to an item that already matched something —
    it is a tiebreak among relevant research, not a free pass into every result
    set. `tags`/`tickers` are empty across the committed catalog today, so they
    are deliberately not scored; title, summary_points, and institution are.

    A meaningful single atom is searchable, including an English topic, ticker,
    qualified identifier, or Chinese phrase. Input with no meaningful atom
    (empty/noise or a one-character atom) returns "query too short". A missing
    or corrupt catalog returns "research vault unavailable". Never raises.

    mode="clusters" answers a different question over the same catalog — which
    themes several houses are all writing about right now — and returns the
    brain.research_clusters.v1 envelope instead of `results`. `query` and `limit`
    are not read in that mode (see the clusters block above).

    mode="report" reads ONE report named by `report_id` and returns the
    brain.research_report.v1 envelope. A meaningful `query` asks for deterministic
    source-bound passages supporting that exact question; a blank/noise query
    preserves the generic capped-body reader. It is PRO-only and METERED —
    `user_ctx` ({"user_id": …}) must be present or the call fails closed with
    pro_required (the gateway owns the tier decision; this is the fail-safe under
    it). `limit` is not read in that mode.

    Any other mode value, including a typo, searches.
    """
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    reference = reference.astimezone(timezone.utc)

    # --- report mode (W4 + R1B evidence) ----------------------------------- #
    # First because it does not use the catalog search ranking. `query` is passed
    # only to the deterministic corpus passage selector; `limit` remains ignored.
    # The whole path is wrapped so a corpus or ledger surprise degrades to an
    # honest error instead of killing the turn.
    if _is_report_mode(mode):
        try:
            return _research_report(root, report_id, query=query, user_ctx=user_ctx,
                                    now=reference)
        except Exception:  # noqa: BLE001 — retrieval must not take the turn down
            return _report_error("vault_unavailable", _REPORT_ERR_VAULT,
                                 report_id=str(report_id or ""))

    cap = _clamp_int(limit, _RESEARCH_LIMIT_MIN, _RESEARCH_LIMIT_MAX, _RESEARCH_LIMIT_DEFAULT)
    note = (
        "institutional research summaries — third-party views, "
        "not the desk's own signals"
    )

    # --- clusters mode ----------------------------------------------------- #
    # Same tool, same catalog, same tier gate (the gateway gates by NAME, so this
    # mode inherits the Insider/Pro fence without touching it). The query is not
    # read here: convergence is a property of the whole window, and filtering it
    # by search terms would answer "who agrees with my premise" instead.
    if _is_clusters_mode(mode):
        try:
            items = _catalog_items(root)
        except Exception:  # noqa: BLE001
            items = None
        if items is None:
            return {"schema": "brain.research_clusters.v1",
                    "asof": reference.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "count_scanned": 0, "clusters": [],
                    "note": "research vault unavailable"}
        try:
            return _research_clusters(items, now=reference)
        except Exception:  # noqa: BLE001 — retrieval must not take the turn down
            return {"schema": "brain.research_clusters.v1",
                    "asof": reference.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "count_scanned": 0, "clusters": [],
                    "note": "street clusters unavailable"}

    tokens = _tokenize(query)
    if not tokens:
        return {"query": str(query or ""), "results": [], "count_scanned": 0,
                "note": "query too short"}

    try:
        items = _catalog_items(root)
    except Exception:  # noqa: BLE001
        items = None
    if items is None:
        return {"query": str(query or ""), "results": [], "count_scanned": 0,
                "note": "research vault unavailable"}

    scored: list[tuple[float, str, str, dict]] = []
    for item in items:
        title = str(item.get("title") or "")
        points = item.get("summary_points")
        points = [str(p) for p in points if isinstance(p, str)] if isinstance(points, list) else []
        institution = str(item.get("institution") or "")

        title_hits = _hits(tokens, title)
        summary_hits = _hits(tokens, " ".join(points))
        institution_hits = _hits(tokens, institution)
        if not (title_hits or summary_hits or institution_hits):
            continue  # no textual relevance — top_pick alone never admits an item

        raw = (
            _W_TITLE * title_hits
            + _W_SUMMARY * summary_hits
            + _W_INSTITUTION * institution_hits
            + (_W_TOP_PICK if item.get("top_pick") else 0.0)
        )
        published_at = item.get("published_at")
        score = raw * _recency_factor(published_at, reference)
        if score <= 0:
            continue
        # Tie-break on published_at then id so the ordering is stable across runs
        # (a catalog rebuild reorders `items`, and an unstable top-5 would make
        # the tool look like it changed its mind).
        scored.append((score, str(published_at or ""), str(item.get("id") or ""), item))

    # Score descending; among ties the NEWEST note first, then id for a total
    # order. `_neg_str_key` inverts the ISO date because Python cannot negate a
    # str — a plain ascending sort would surface the oldest tied note.
    scored.sort(key=lambda row: (-row[0], _neg_str_key(row[1]), row[2]))

    results = []
    for _score, _pub, _iid, item in scored[:cap]:
        points = item.get("summary_points")
        points = [p for p in points if isinstance(p, str)] if isinstance(points, list) else []
        results.append({
            "id": item.get("id"),
            "title": item.get("title"),
            "institution": item.get("institution"),
            "side": item.get("side"),
            "published_at": item.get("published_at"),
            "summary_points": [_truncate(p) for p in points[:_SUMMARY_POINTS_KEPT]],
            "top_pick": bool(item.get("top_pick")),
        })

    return {
        "query": str(query or ""),
        "results": results,
        "count_scanned": len(items),
        "note": note,
    }


def _neg_str_key(text: str) -> tuple:
    """Descending sort key for an ISO date string used as a tie-break.

    Python cannot negate a str, so invert each codepoint. Only ever applied to
    ISO-8601 stamps, where lexical order IS chronological order.
    """
    return tuple(-ord(ch) for ch in text)


# --------------------------------------------------------------------------- #
# Anthropic tool schemas (shape mirrors brain_gateway._brain_tool_schemas)
# --------------------------------------------------------------------------- #
EVENTS_TOOL_SCHEMA: dict = {
    "name": "get_market_events",
    "description": (
        "Read the desk's fresh market-events feed: the intraday press wire, "
        "topped up from the nightly news digests when the wire is thin. Call for "
        "any question about today's or current news, catalysts, 'why is the "
        "market moving', 'what happened', breaking developments, or what is "
        "driving a ticker right now. Returns FACTS ONLY — timestamp, headline "
        "(EN and ZH where translated), source, desk-computed salience, and a "
        "corroboration chip ('verified', 'N sources', 'reports'). It returns no "
        "predicted effects and no beneficiary or casualty lists; draw any market "
        "read yourself from the engine's own signal tools, and never present a "
        "single-source 'reports' item as confirmed."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "window_h": {
                "type": "number",
                "description": "Look-back window in hours (1..48, default 12)",
            },
            "limit": {
                "type": "integer",
                "description": "Max events to return (1..10, default 5)",
            },
            "symbol": {
                "type": "string",
                "description": (
                    "Prefer events mentioning this ticker (e.g. 'NVDA'); general "
                    "events backfill to the limit. Optional."
                ),
            },
        },
        "required": [],
    },
}

RESEARCH_TOOL_SCHEMA: dict = {
    "name": "search_research",
    "description": (
        "Search the research vault of institutional sell-side and buy-side notes "
        "by keyword. Call when the user asks what analysts, institutions, banks, "
        "or the street think, wants research on a theme or ticker, or asks for a "
        "second opinion beside the desk's own signals. Returns third-party "
        "institutional research summaries — attribute every view to its "
        "institution ('Goldman Sachs writes…'), never present one as the desk's "
        "own read, and say plainly when a note disagrees with the engine. "
        "Set mode='clusters' instead of searching when the user asks what the "
        "street is FOCUSED on, where the desks are converging or crowding, or "
        "what everyone is writing about this week: that returns the themes "
        "several houses hit at once, with the report counts and house names. "
        "Convergence is what was WRITTEN, not evidence the view is right — many "
        "desks agreeing is a crowding fact, so name the houses and say so. "
        "Set mode='report' with report_id to open ONE note in depth once a "
        "search or clusters result has named it — when the user asks what a "
        "specific report actually argues, or you need its reasoning rather than "
        "its headline. For generic requests such as 'summarize this report' or "
        "'what does this note argue?', pass an empty query to open the note "
        "generically. Pass the exact question only for a specific factual "
        "request, to return a query-centered supporting passage with a source "
        "fingerprint and an 'Open source' link. "
        "Text actually served is metered hourly for PRO members, so call it for "
        "the one report that matters, not for every hit; no matching passage or "
        "unavailable body is not charged. Attribute it to its institution, quote "
        "sparingly, and synthesize in your own words rather than reproducing pages."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Search terms — a theme, ticker, institution, or Chinese "
                    "phrase. One meaningful term is accepted (e.g. "
                    "'semiconductors', 'AAPL', '中国流动性'); add focused terms "
                    "when the first result set is broad. With mode='report', pass "
                    "an empty query for generic requests such as 'summarize this "
                    "report' or 'what does this note argue?'; pass the user's exact "
                    "question only for a specific factual request in English so "
                    "Brain can return source-bound supporting passages. For "
                    "Chinese, matching is literal (no sentence segmentation), so "
                    "pass 1-3 literal key terms or phrases (e.g. '通胀预期', "
                    "'美联储 利率') rather than a full unsegmented sentence. Not "
                    "read when mode='clusters'."
                ),
            },
            "limit": {
                "type": "integer",
                "description": "Max results to return (1..8, default 5)",
            },
            "mode": {
                "type": "string",
                "enum": [_MODE_SEARCH, _MODE_CLUSTERS, _MODE_REPORT],
                "description": (
                    "'search' (default) ranks individual notes against the "
                    "query; 'clusters' ignores the query and returns the themes "
                    "3+ notes from 2+ institutions share right now; 'report' "
                    "opens the single note named by report_id and uses query for "
                    "query-centered, source-bound evidence."
                ),
            },
            "report_id": {
                "type": "string",
                "description": (
                    "The id of ONE report to open in depth, used with "
                    "mode='report'. Ids come from search or clusters results — "
                    "never invent or guess one. A Pro capability: on a "
                    "non-Pro account the call returns the gate, which you "
                    "explain instead of describing a report you have not read."
                ),
            },
        },
        "required": ["query"],
    },
}
