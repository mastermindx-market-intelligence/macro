"""Recurring briefs producer (F11 packet B-F11-7b, MO-PAID-032).

ONE scheduler: a subscription over the existing nightly/weekly owners, never a
new cron and never an app-side timer. Each active subscription is written
exactly one `brief_deliveries` row per cadence slot, or an honest miss.

Slot (R4):
  daily_after_us_close  → site/intelligence/briefing.json field `as_of`
                          (also accepts `asof` if a future producer renames it)
  weekly_saturday       → site/master_brief.json field `state_asof`
                          (the brief weekly.yml's `build_aibrief` step surfaces;
                          also accepts `as_of` / `asof`)

A missing or older-than-run-date artifact still writes TODAY's slot as
`degraded` with the contract's plain line in body.market_read[0]. An
unreadable/deleted target writes degraded 'target unavailable'. Never
back-fills earlier slots.

Body is deterministic: sentences copied verbatim from the published artifact
(sections relevant to the target's tickers) plus the target's current monitor
states from the existing thesis-monitor projection. No LLM call, no new
number, no score. Authority ceiling: workflow_only.

Data access mirrors engine/thesis_condition_monitor.py: the same Supabase
service client, the same env variable names, the same never-print-secrets
discipline. Writes brief_deliveries ONLY (insert on conflict do nothing).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://fsldfzlxyavsuwqbceod.supabase.co"
).rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

CADENCE_DAILY = "daily_after_us_close"
CADENCE_WEEKLY = "weekly_saturday"
CADENCES = (CADENCE_DAILY, CADENCE_WEEKLY)

DAILY_ARTIFACT_REL = "site/intelligence/briefing.json"
DAILY_ASOF_FIELDS = ("as_of", "asof")
WEEKLY_ARTIFACT_REL = "site/master_brief.json"
WEEKLY_ASOF_FIELDS = ("state_asof", "as_of", "asof")

CONTRACT_MISS_EN = (
    "Tonight's brief didn't run — the market read it uses wasn't rebuilt. "
    "Nothing has been recalculated."
)
CONTRACT_MISS_ZH = (
    "今晚的简报没有生成——它所依据的市场阅读尚未重建。没有重新计算任何内容。"
)
TARGET_UNAVAILABLE_REASON = "target unavailable"
TARGET_UNAVAILABLE_EN = (
    "This brief could not be written because the thesis or watchlist it "
    "follows is no longer available."
)
TARGET_UNAVAILABLE_ZH = (
    "这份简报无法写成，因为它所跟踪的论点或观察列表已不可用。"
)
NO_COVERAGE_REASON = "no target coverage"
NO_COVERAGE_EN = (
    "No tracked names for this thesis yet — we can't write a brief until it "
    "carries one."
)
NO_COVERAGE_ZH = (
    "此论点暂未关联任何个股名称——在它对应到具体股票之前，我们无法撰写简报。"
)
TRANSLATION_PENDING_ZH = "（翻译待补）"


@dataclass(frozen=True)
class RunResult:
    subscription_n: int
    ready_n: int
    degraded_n: int
    slot: date | None
    duplicate_n: int = 0
    planned_n: int = 0
    error_n: int = 0
    read_missing: int = 0
    read_unavailable: int = 0
    planned_rows: tuple = ()


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------

def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        try:
            return datetime.fromisoformat(text).date()
        except ValueError:
            return None


def artifact_asof_value(artifact: dict | None) -> Any:
    if not isinstance(artifact, dict):
        return None
    schema = artifact.get("schema") or ""
    fields = WEEKLY_ASOF_FIELDS if "master_brief" in str(schema) else DAILY_ASOF_FIELDS
    # Prefer the cadence-native field, then the union, so a briefing.json
    # weekly fallback and a master_brief daily fallback both still parse.
    for key in fields + DAILY_ASOF_FIELDS + WEEKLY_ASOF_FIELDS:
        if artifact.get(key):
            return artifact.get(key)
    return None


def _artifact_generated_at(artifact: dict | None) -> Any:
    """The artifact's generation timestamp as a parseable string.

    The slot-clock fix needs this: a weekly artifact built this Saturday run
    carries Friday market state but was generated on the run_date. The run's
    own ``generated_at`` is the binding clock; ``state_asof`` is the brief's
    content. Used ONLY for slot eligibility — not for the row's slot value.
    """
    if not isinstance(artifact, dict):
        return None
    for key in ("generated_at", "generated_utc", "asof", "as_of"):
        val = artifact.get(key)
        if isinstance(val, str) and "T" in val:
            return val
    return None


def compute_slot(
    cadence: str,
    artifact_asof: Any,
    run_date: date,
    *,
    artifact_generated_at: Any = None,
) -> date | None:
    """Return the slot date if the artifact is usable for this cadence, else None.

    Slot eligibility (binding clock): the artifact is fresh for this run
    when its asof is on or after run_date (state carried into today), OR
    when it was GENERATED within the 24-hour window around the run — the
    brief was rebuilt this run with state from the previous session. This
    covers the two measured production shapes:

      * ``weekly_saturday`` — ``generated_at`` falls on the run_date itself
        (Saturday 10:10 UTC run with Friday state).
      * ``daily_after_us_close`` — the nightly crosses UTC midnight, so the
        briefing captured mid-job has ``generated_utc`` 30 min before UTC
        midnight and ``run_date`` (captured at the end of the same job) is
        the next day.

    The 3-arg form preserves the strict pre-fix behaviour for callers that
    don't have the generated_at clock (e.g. existing tests).
    """
    if cadence not in CADENCES:
        return None
    asof_date = _as_date(artifact_asof)
    if asof_date is not None:
        if asof_date >= run_date:
            return run_date
        if artifact_generated_at is None:
            return None
    gen_date = _as_date(artifact_generated_at)
    if gen_date is None:
        return None
    # An artifact rebuilt this run — on the run_date itself OR within the
    # prior 24h — is fresh. A truly stale artifact (gen_date several days
    # older than run_date) still degrades with the contract's plain line.
    delta_days = (run_date - gen_date).days
    if 0 <= delta_days <= 1:
        return run_date
    return None


def classify(
    subscription: dict, artifact: dict | None, target: dict | None
) -> tuple[str, str | None]:
    """Return ('ready'|'degraded', reason). reason is None when ready."""
    if not target or (isinstance(target, dict) and target.get("unavailable")):
        return ("degraded", TARGET_UNAVAILABLE_REASON)
    run_date = _as_date(subscription.get("run_date")) or date.today()
    cadence = subscription.get("cadence") or CADENCE_DAILY
    if isinstance(artifact, dict):
        slot = compute_slot(
            cadence,
            artifact_asof_value(artifact),
            run_date,
            artifact_generated_at=_artifact_generated_at(artifact),
        )
    else:
        slot = compute_slot(cadence, None, run_date)
    if slot is None:
        return ("degraded", CONTRACT_MISS_EN)
    # H6 (MAJOR 2): a target with no ticker coverage cannot compose a
    # ticker-filtered brief. Returning ready would publish only the global
    # backdrop as if it were a real brief for the target. The two measured
    # production shapes:
    #   * a theme thesis whose ``_thesis_tickers`` returns ``[]``;
    #   * a thesis / watchlist whose tickers miss every item in the
    #     artifact's priority_queue / divergences / watch_items.
    # Both must degrade with the typed honest-miss line bound to
    # ``degraded_reason``.
    if isinstance(target, dict):
        kind = target.get("kind")
        tickers = target.get("tickers") or []
        if kind in ("thesis", "watchlist"):
            wanted = _ticker_set(tickers)
            if not wanted:
                return ("degraded", NO_COVERAGE_REASON)
            if not _target_has_artifact_coverage(target, wanted, artifact):
                return ("degraded", NO_COVERAGE_REASON)
    return ("ready", None)


def _sentence_row(section: str, en: str, zh: str | None, asof: str | None) -> dict | None:
    en = (en or "").strip() if isinstance(en, str) else ""
    if not en:
        return None
    zh_text = (zh or "").strip() if isinstance(zh, str) else ""
    if not zh_text:
        zh_text = f"{en}{TRANSLATION_PENDING_ZH}"
    return {
        "section": section,
        "sentence_en": en,
        "sentence_zh": zh_text,
        "asof": asof,
    }


def _ticker_set(tickers: Any) -> set[str]:
    out = set()
    for raw in tickers or []:
        if isinstance(raw, str) and raw.strip():
            out.add(raw.strip().upper())
    return out


def _item_tickers(item: dict) -> set[str]:
    found = set()
    for key in ("ticker", "symbol", "root"):
        val = item.get(key)
        if isinstance(val, str) and val.strip():
            found.add(val.strip().upper())
    for key in ("tickers", "symbols"):
        for val in item.get(key) or []:
            if isinstance(val, str) and val.strip():
                found.add(val.strip().upper())
    return found


def _matches_target(item: dict, tickers: set[str]) -> bool:
    if not tickers:
        return False
    return bool(_item_tickers(item) & tickers)


def _target_has_artifact_coverage(
    target: dict, tickers: set[str], artifact: dict | None
) -> bool:
    """True if any item in the artifact's covered sections names one of the
    target's tickers. The H6 fix — pre-compute whether the target's ticker
    set intersects priority_queue / divergences / watch_items. A thesis
    whose tickers exist but yield zero rows in the published artifact must
    NOT classify ready while emitting only the global backdrop.
    """
    if not tickers or not isinstance(artifact, dict):
        return False
    for item in artifact.get("priority_queue") or []:
        if isinstance(item, dict) and _matches_target(item, tickers):
            return True
    for item in artifact.get("divergences") or []:
        if isinstance(item, dict) and _matches_target(item, tickers):
            return True
    for item in artifact.get("watch_items") or []:
        if not isinstance(item, dict):
            continue
        if not _item_tickers(item):
            continue
        if _matches_target(item, tickers):
            return True
    return False


def extract_market_read(artifact: dict | None, tickers: set[str]) -> list[dict]:
    """Verbatim sentences from the published artifact, ticker-filtered.

    Never copies numeric judgement fields (priority/confidence/strength/…).
    Never copies raw engine ``evidence`` slugs into a user-facing string — the
    H4 review measured ``radar CONF edge7 · alt92 ACCUMULATE · news neutral n1``
    on every row of the daily briefing; that prose is for Engine output, not
    for what a user reads.
    """
    if not isinstance(artifact, dict):
        return []
    asof = None
    asof_date = _as_date(artifact_asof_value(artifact))
    if asof_date is not None:
        asof = asof_date.isoformat()
    rows: list[dict] = []
    seen: set[str] = set()

    def add(section: str, en: Any, zh: Any = None) -> None:
        if not isinstance(en, str):
            return
        row = _sentence_row(section, en, zh if isinstance(zh, str) else None, asof)
        if row is None or row["sentence_en"] in seen:
            return
        seen.add(row["sentence_en"])
        rows.append(row)

    macro = artifact.get("macro_context") or {}
    if isinstance(macro, dict):
        add("backdrop", macro.get("posture") or macro.get("headline"))

    for item in artifact.get("priority_queue") or []:
        if not isinstance(item, dict):
            continue
        if tickers and not _matches_target(item, tickers):
            continue
        if not tickers:
            continue
        # Situation is prose; evidence is engine-slug code — H4 forbids copying
        # raw ``evidence`` into user-facing strings.
        add("tape", item.get("situation"), item.get("situation_zh"))

    for item in artifact.get("divergences") or []:
        if not isinstance(item, dict):
            continue
        if tickers and not _matches_target(item, tickers):
            continue
        if not tickers:
            continue
        add("tape", item.get("situation"), item.get("situation_zh"))

    # Weekly artifacts publish a paired ``zh`` block whose strings are real
    # Chinese; pair ``tldr``/``watch_items`` by index to the ``zh.tldr`` /
    # ``zh.watch_items`` arrays — the H3 measured triple fed an English
    # sentence paired with a ``（翻译待补）`` fallback for 11/11 weekly rows.
    zh_block = artifact.get("zh") if isinstance(artifact.get("zh"), dict) else {}
    zh_tldr = list(zh_block.get("tldr") or []) if isinstance(zh_block, dict) else []
    zh_watch = list(zh_block.get("watch_items") or []) if isinstance(zh_block, dict) else []

    tldr_items = artifact.get("tldr") or []
    for index, item in enumerate(tldr_items):
        zh_pair = zh_tldr[index] if index < len(zh_tldr) else None
        if isinstance(item, str):
            add("week", item, zh_pair)
        elif isinstance(item, dict):
            add(
                "week",
                item.get("sentence") or item.get("text") or item.get("note"),
                zh_pair,
            )

    # Top-level ``summary`` / ``regime_read``: paired with the zh block
    # when one exists; fall back to ``summary_zh`` / ``regime_read_zh`` only
    # when there is no zh-block on the artifact (older producers).
    if isinstance(zh_block, dict) and zh_block:
        add("week", artifact.get("summary"), zh_block.get("summary"))
        add("week", artifact.get("regime_read"), zh_block.get("regime_read"))
    else:
        add("week", artifact.get("summary"), artifact.get("summary_zh"))
        add(
            "week",
            artifact.get("regime_read"),
            artifact.get("regime_read_zh"),
        )

    for index, item in enumerate(artifact.get("watch_items") or []):
        zh_pair = zh_watch[index] if index < len(zh_watch) else None
        if isinstance(item, str):
            add("week", item, zh_pair)
            continue
        if not isinstance(item, dict):
            continue
        if tickers and _item_tickers(item) and not _matches_target(item, tickers):
            continue
        add(
            "week",
            item.get("note") or item.get("sentence") or item.get("text"),
            zh_pair,
        )
    return rows


def _artifact_display_name(artifact: dict | None) -> str:
    if not isinstance(artifact, dict):
        return "Published market read"
    schema = str(artifact.get("schema") or "")
    if "briefing" in schema:
        return "Daily market briefing"
    if "master_brief" in schema:
        return "Weekly market brief"
    return "Published market read"


def _target_view(target: dict | None) -> dict:
    target = target or {}
    return {
        "kind": target.get("kind") or "thesis",
        "id": target.get("id") or "",
        "name": target.get("name")
        or "This thesis or watchlist is no longer available",
        "version_or_asof": target.get("version_or_asof"),
    }


def compose_body(
    target: dict | None,
    artifact: dict | None,
    monitors: list | None,
    *,
    degraded_reason: str | None = None,
) -> dict:
    """Deterministic body dict. No LLM, no new number, no score."""
    asof = None
    asof_date = _as_date(artifact_asof_value(artifact)) if artifact else None
    if asof_date is not None:
        asof = asof_date.isoformat()
    tickers = _ticker_set((target or {}).get("tickers"))
    if degraded_reason == TARGET_UNAVAILABLE_REASON:
        market_read = [
            _sentence_row("status", TARGET_UNAVAILABLE_EN, TARGET_UNAVAILABLE_ZH, asof)
        ]
    elif degraded_reason == NO_COVERAGE_REASON:
        market_read = [
            _sentence_row("status", NO_COVERAGE_EN, NO_COVERAGE_ZH, asof)
        ]
    elif degraded_reason:
        market_read = [
            _sentence_row("status", CONTRACT_MISS_EN, CONTRACT_MISS_ZH, asof)
        ]
    else:
        market_read = extract_market_read(artifact, tickers)
    market_read = [row for row in market_read if row]
    return {
        "target": _target_view(target),
        "market_read": market_read,
        "monitors": list(monitors or []),
        "artifact": {
            "name": _artifact_display_name(artifact),
            "asof": asof,
        },
    }


def project_monitors(tickers: list[str] | set[str], windows: list[dict] | None) -> list[dict]:
    """Plain-language monitor states. Never names a tripwire or a condition slug."""
    quiet = {
        "name": "Conditions we watch",
        "state_en": "No change in the conditions we watch.",
        "state_zh": "我们关注的条件没有变化。",
    }
    wanted = _ticker_set(tickers)
    fired = False
    for window in windows or []:
        if not isinstance(window, dict):
            continue
        w_tickers = _ticker_set(window.get("tickers"))
        if wanted and w_tickers and not (wanted & w_tickers):
            continue
        state = str(window.get("state") or "").upper()
        if state == "FIRED" or window.get("latched") or window.get("fired_on"):
            fired = True
            break
    if not fired:
        return [quiet]
    return [
        {
            "name": "Conditions we watch",
            "state_en": "A market condition we watch has changed.",
            "state_zh": "你关注的一项市场条件已发生变化。",
        }
    ]


# ---------------------------------------------------------------------------
# IO — same service client as engine/thesis_condition_monitor.py
# ---------------------------------------------------------------------------

def _pg(method: str, path: str, body: Any = None, prefer: str | None = None, timeout: int = 6):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def load_published_artifact(cadence: str, root: Path | None = None) -> dict | None:
    base = Path(root) if root is not None else ROOT
    rel = DAILY_ARTIFACT_REL if cadence == CADENCE_DAILY else WEEKLY_ARTIFACT_REL
    path = base / rel
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def read_subscriptions(cadence: str) -> list[dict]:
    if not SUPABASE_SERVICE_ROLE_KEY:
        return []
    path = (
        "brief_subscriptions?state=eq.active"
        f"&cadence=eq.{cadence}"
        "&select=subscription_id,user_id,target_kind,target_id,cadence,delivery,state,created_at"
    )
    try:
        rows = _pg("GET", path)
    except urllib.error.HTTPError:
        return []
    except Exception:
        return []
    return rows if isinstance(rows, list) else []


def _thesis_tickers(subject_ref: dict | None, content: dict | None) -> list[str]:
    tickers: list[str] = []
    seen: set[str] = set()

    def add(raw: Any) -> None:
        if not isinstance(raw, str) or not raw.strip():
            return
        sym = raw.strip().upper()
        if sym not in seen:
            seen.add(sym)
            tickers.append(sym)

    if isinstance(subject_ref, dict):
        listing = subject_ref.get("listing") or {}
        if isinstance(listing, dict):
            add(listing.get("symbol"))
        if subject_ref.get("kind") == "issuer":
            add(subject_ref.get("key"))
    if isinstance(content, dict):
        for raw in content.get("symbols") or content.get("tickers") or []:
            add(raw)
    return tickers


def read_target(subscription: dict) -> dict | None:
    if not SUPABASE_SERVICE_ROLE_KEY:
        return None
    kind = subscription.get("target_kind")
    target_id = subscription.get("target_id")
    sub_user_id = subscription.get("user_id")
    if not kind or not target_id:
        return None
    # H5: owner-scope the target read. brief_subscriptions is RLS owner-only
    # on ``user_id default auth.uid()``; without the equivalent filter on this
    # read, any authenticated user could subscribe to a target UUID and have
    # the nightly write that target's title/symbols/monitor state into a
    # ``brief_deliveries`` row the subscriber may select. Mirror the watchdog
    # sentinel at scripts/run_watchlist_sentinel.py:101-103.
    try:
        if kind == "thesis":
            path = (
                f"theses?id=eq.{target_id}"
                f"&user_id=eq.{sub_user_id}" if sub_user_id else
                f"theses?id=eq.{target_id}"
            )
            # H10 minor (b): mirror ``engine/thesis_condition_monitor.py:601``
            # and only return active theses. Archived/closed theses get the
            # R4 "target unavailable" verdict upstream.
            path += "&lifecycle_state=eq.active"
            path += "&select=id,user_id,current_version,subject_ref,lifecycle_state"
            rows = _pg("GET", path)
            if not rows:
                return None
            head = rows[0]
            # Belt-and-braces: even after the URL filter, ignore rows whose
            # ``user_id`` does not match the subscription — defence in depth
            # against any future RLS / PostgREST reorganisation.
            if sub_user_id and head.get("user_id") != sub_user_id:
                return None
            version = head.get("current_version")
            content = {}
            if version is not None:
                vrows = _pg(
                    "GET",
                    f"thesis_versions?thesis_id=eq.{target_id}&version=eq.{version}&select=content,version",
                )
                if vrows:
                    content = (vrows[0] or {}).get("content") or {}
            title = content.get("title") if isinstance(content, dict) else None
            return {
                "kind": "thesis",
                "id": head.get("id") or target_id,
                "name": title or "Untitled thesis",
                "version_or_asof": str(version) if version is not None else None,
                "tickers": _thesis_tickers(head.get("subject_ref"), content),
                "unavailable": False,
            }
        if kind == "watchlist":
            wl_path = (
                f"watchlists?id=eq.{target_id}"
                f"&user_id=eq.{sub_user_id}" if sub_user_id else
                f"watchlists?id=eq.{target_id}"
            )
            wl_path += "&select=id,user_id,name,watchlist_symbols(symbol)"
            rows = _pg("GET", wl_path)
            if not rows:
                return None
            row = rows[0]
            if sub_user_id and row.get("user_id") != sub_user_id:
                return None
            members = []
            seen: set[str] = set()
            for entry in row.get("watchlist_symbols") or []:
                if not isinstance(entry, dict):
                    continue
                sym = (entry.get("symbol") or "").strip().upper()
                if sym and sym not in seen:
                    seen.add(sym)
                    members.append(sym)
            return {
                "kind": "watchlist",
                "id": row.get("id") or target_id,
                "name": row.get("name") or "Untitled watchlist",
                "version_or_asof": None,
                "tickers": members,
                "unavailable": False,
            }
    except urllib.error.HTTPError:
        return None
    except Exception:
        return None
    return None


def write_delivery(row: dict, *, dry_run: bool = False) -> str:
    """Insert one brief_deliveries row. Idempotent on (subscription_id, slot_asof)."""
    if dry_run:
        return "dry"
    if not SUPABASE_SERVICE_ROLE_KEY:
        return "error"
    try:
        _pg(
            "POST",
            "brief_deliveries?on_conflict=subscription_id,slot_asof",
            body=row,
            prefer="resolution=ignore-duplicates,return=minimal",
        )
        return "inserted"
    except urllib.error.HTTPError as exc:
        code = getattr(exc, "code", None)
        raw = b""
        try:
            raw = exc.read()
        except Exception:
            pass
        text = raw.decode("utf-8", "ignore")
        if code == 409 or "23505" in text:
            return "conflict"
        return "error"
    except Exception:
        return "error"


def load_monitors_for_target(target: dict | None) -> list[dict]:
    """Current monitor states from the existing thesis-monitor projection."""
    tickers = list((target or {}).get("tickers") or [])
    windows: list[dict] = []
    try:
        from engine import thesis_condition_monitor as tcm

        entries, latch_state, error_class = tcm.load_tripwire_view()
        if error_class is None:
            for window in tcm.fired_windows(entries, latch_state):
                windows.append(window)
    except Exception:
        windows = []
    return project_monitors(tickers, windows)


def _artifact_asof_timestamptz(artifact: dict | None) -> str | None:
    if not isinstance(artifact, dict):
        return None
    for key in ("generated_utc", "generated_at"):
        val = artifact.get(key)
        if isinstance(val, str) and "T" in val:
            return val
    asof_date = _as_date(artifact_asof_value(artifact))
    if asof_date is None:
        return None
    return datetime(asof_date.year, asof_date.month, asof_date.day, tzinfo=timezone.utc).isoformat()


def run(
    *,
    cadence: str,
    dry_run: bool = True,
    run_date: date | None = None,
    root: Path | None = None,
) -> RunResult:
    if run_date is None:
        run_date = datetime.now(timezone.utc).date()
    artifact = load_published_artifact(cadence, root=root)
    if isinstance(artifact, dict):
        slot = (
            compute_slot(
                cadence,
                artifact_asof_value(artifact),
                run_date,
                artifact_generated_at=_artifact_generated_at(artifact),
            )
            or run_date
        )
    else:
        slot = (
            compute_slot(cadence, artifact_asof_value(artifact), run_date)
            or run_date
        )

    subscriptions = read_subscriptions(cadence)
    ready_n = 0
    degraded_n = 0
    duplicate_n = 0
    planned_n = 0
    error_n = 0
    read_missing = 0
    read_unavailable = 0
    planned_rows: list[dict] = []
    considered = 0

    for sub in subscriptions:
        if sub.get("cadence") not in (None, cadence):
            continue
        if sub.get("state") not in (None, "active"):
            continue
        considered += 1
        work = dict(sub)
        work["run_date"] = run_date.isoformat()
        target = read_target(work)
        state, reason = classify(work, artifact, target)
        if state == "degraded":
            degraded_n += 1
            if reason == TARGET_UNAVAILABLE_REASON:
                read_unavailable += 1
            elif reason == CONTRACT_MISS_EN:
                read_missing += 1
            body = compose_body(
                target
                or {
                    "kind": work.get("target_kind"),
                    "id": work.get("target_id"),
                    "name": "This thesis or watchlist is no longer available",
                    "version_or_asof": None,
                    "tickers": [],
                    "unavailable": True,
                },
                artifact,
                [],
                degraded_reason=reason,
            )
        else:
            ready_n += 1
            body = compose_body(target, artifact, load_monitors_for_target(target))
        row = {
            "subscription_id": work.get("subscription_id"),
            "slot_asof": slot.isoformat(),
            "state": state,
            "degraded_reason": reason,
            "artifact_asof": _artifact_asof_timestamptz(artifact),
            "body": body,
        }
        planned_n += 1
        if dry_run:
            planned_rows.append(row)
            outcome = write_delivery(row, dry_run=True)
        else:
            outcome = write_delivery(row, dry_run=False)
        if outcome == "conflict":
            duplicate_n += 1
        elif outcome == "error":
            # H8: persistent 500/RLS/network failures must be visible. The
            # mirrored precedent (scripts/run_thesis_condition_monitor.py:50)
            # surfaces this with a ::warning line; we keep that shape here.
            error_n += 1

    return RunResult(
        subscription_n=considered,
        ready_n=ready_n,
        degraded_n=degraded_n,
        slot=slot,
        duplicate_n=duplicate_n,
        planned_n=planned_n,
        error_n=error_n,
        read_missing=read_missing,
        read_unavailable=read_unavailable,
        planned_rows=tuple(planned_rows),
    )
