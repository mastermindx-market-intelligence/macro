"""同花顺 (Tonghuashun / 10jqka) concept-board (概念板块) membership fetcher.

THS curates ~370 thematic "concept boards" (concepts like 白酒/baijiu, 人形机器人/humanoid
robots, 固态电池/solid-state battery …) and the A-share members of each. This module pulls the
theme→members map straight from q.10jqka.com.cn so the China thematic-baskets desk can mirror
THS's themes and constituents (see scripts/seed_china_ths_baskets.py).

WHY THIS EXISTS (akshare can't do it any more): akshare exposes the THS concept *names*
(`stock_board_concept_name_ths`) but its members function (`stock_board_concept_cons_ths`) was
removed. The member table is still served on the plain detail page; this module pages through it.

ACCESS NOTES (verified from a non-China datacentre IP, 2026-06):
  • Theme list — akshare `stock_board_concept_name_ths()` (cached to disk here; ~370 names+codes).
  • Members  — page `https://q.10jqka.com.cn/gn/detail/order/desc/page/{N}/ajax/1/code/{code}/`
               (10 rows/page). The `/field/199112/` URL variant 403s from outside China; the
               clean variant above returns 200. An anti-scrape `v` cookie (generated from THS's
               own ths.js via py_mini_racer, exactly as akshare does) is required.
  • Fragile  — rapid sequential requests draw SSL drops / 403s, so every fetch retries with
               backoff and paces between pages; a failed theme is skipped (logged), never fatal.

Output: a dated raw snapshot data/baskets_china_ths/snapshots/<YYYY-MM-DD>.json
        ({theme_name: [{"ticker": "600519.SS", "name": "贵州茅台"}, …]}, full membership incl.
        names outside our price universe — the seed step filters). Re-runnable; the seed step
        accumulates point-in-time `added`/`removed` history by diffing snapshots over time.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd
import requests
from requests.adapters import HTTPAdapter

from lib import config

try:  # urllib3 ships with requests; Retry import path is stable
    from urllib3.util.retry import Retry
except Exception:  # noqa: BLE001 — extremely unlikely; degrade to no-retry adapter
    Retry = None  # type: ignore

log = logging.getLogger(__name__)


class ThsTruncated(RuntimeError):
    """A concept's member table could not be fully paged (throttle / SSL drop / partial page).

    Raised instead of returning a PARTIAL member list: a truncated fetch is indistinguishable from
    a genuinely-shorter board, and recording it as authoritative makes the seed step manufacture
    spurious `removed` events on the next diff (which silently breaks the THS baskets page). The
    caller (`snapshot`) treats this like a throttle — the theme is left unresolved and retried on a
    later resume run — so only COMPLETE member lists ever land in a snapshot.
    """


_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36")
_DATA = config.data_dir() / "baskets_china_ths"
_MAP_CACHE = _DATA / "concept_map.json"        # {"asof": iso-date, "map": {name: code}} (refreshed if asof older than _MAP_TTL_DAYS)
_MAP_TTL_DAYS = 7
_PAGE_PAUSE = 1.2                               # seconds between member pages (politeness / SSL stability)
_THEME_PAUSE = 4.0                              # seconds between themes (THS IP-throttles bursts hard)
_MAX_PAGES = 60                                 # hard ceiling (~600 members) — no real concept is bigger
_MAX_CONSEC_EMPTY = 4                           # consecutive empty themes ⇒ assume IP cool-down, stop & resume later


def _new_v() -> str:
    """Generate a FRESH THS anti-scrape `v` cookie from its own ths.js (same recipe akshare uses).

    Deliberately NOT cached: THS throttles bursts that reuse one cookie, so we mint a new one per
    theme. Generation is a sub-second py_mini_racer eval.
    """
    import py_mini_racer
    from akshare.datasets import get_ths_js

    js = py_mini_racer.MiniRacer()
    js.eval(open(get_ths_js("ths.js"), encoding="utf-8").read())
    return js.call("v")


def _session(v: str | None = None) -> requests.Session:
    """A fresh session bound to a (fresh) `v` cookie. New session per theme ⇒ new TCP, new cookie."""
    s = requests.Session()
    if Retry is not None:
        retry = Retry(total=3, backoff_factor=2.0, status_forcelist=[403, 429, 500, 502, 503, 504],
                      allowed_methods=["GET"])
        s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": _UA, "Referer": "https://q.10jqka.com.cn/",
                      "Cookie": f"v={v or _new_v()}"})
    return s


def to_suffixed(code6: str) -> str:
    """Bare 6-digit A-share code -> store ticker with exchange suffix (.SS/.SZ/.BJ).

    Shanghai (.SS): 6xxxxx main/STAR, 900xxx B-shares. Beijing Stock Exchange (.BJ): 8xxxxx,
    4xxxxx, 920xxx. Shenzhen (.SZ): everything else (000/002/003 main, 300 ChiNext, 200 B-shares).
    Beijing names are virtually never in our top-mktcap price cache, so they fall out at the seed
    step's universe filter anyway — but we still label them correctly.
    """
    code6 = str(code6).zfill(6)
    if code6[0] == "6" or code6.startswith("900"):
        return f"{code6}.SS"
    if code6[0] in ("8", "4") or code6.startswith("92"):
        return f"{code6}.BJ"
    return f"{code6}.SZ"


def _read_map_cache() -> tuple[dict[str, str] | None, int | None]:
    """(map, age_days) from the disk cache. Freshness is judged from the blob's
    embedded `asof` stamp, NEVER file mtime — on CI runners a checkout rewrites
    files with mtime = checkout time, so the committed cache always looked
    brand-new by mtime and the refetch short-circuited forever (the
    polygon-universe frozen-cache class, #2690; this map froze at its
    2026-06-27 fill the same way). Legacy stamp-less blobs ({name: code} flat
    dict) return age None — usable as a failure fallback but never fresh."""
    try:
        blob = json.loads(_MAP_CACHE.read_text())
    except Exception as e:  # noqa: BLE001
        log.warning("concept_map cache unreadable (%s)", e)
        return None, None
    if isinstance(blob, dict) and isinstance(blob.get("map"), dict):
        try:
            age = (date.today() - date.fromisoformat(str(blob.get("asof")))).days
        except Exception:  # noqa: BLE001
            age = None
        return {str(k): str(v) for k, v in blob["map"].items()}, age
    if isinstance(blob, dict):        # legacy flat {name: code} — stamp-less ⇒ stale
        return {str(k): str(v) for k, v in blob.items()}, None
    return None, None


def concept_code_map(force: bool = False) -> dict[str, str]:
    """{concept_name: ths_code} for every THS concept board (~370). Disk-cached for _MAP_TTL_DAYS.

    Uses akshare's working name endpoint; on failure falls back to a stale cache if present.
    """
    cached: dict[str, str] | None = None
    if _MAP_CACHE.exists():
        cached, age_days = _read_map_cache()
        if (not force and cached
                and age_days is not None and age_days < _MAP_TTL_DAYS):
            return cached
    try:
        import akshare as ak
        df = ak.stock_board_concept_name_ths()
        m = {str(r["name"]): str(r["code"]) for _, r in df.iterrows()}
        if m:
            _DATA.mkdir(parents=True, exist_ok=True)
            _MAP_CACHE.write_text(json.dumps(
                {"asof": date.today().isoformat(), "map": m}, ensure_ascii=False, indent=0))
            log.info("refreshed THS concept map: %d concepts", len(m))
            return m
    except Exception as e:  # noqa: BLE001
        log.error("THS concept-name fetch failed: %s", e)
    if cached:  # better stale than nothing
        log.warning("using STALE THS concept map")
        return cached
    return {}


COLLECTION_OBSERVATION_SCHEMA = "baskets_china_ths.collection_observation.v1"


def _collection_clock() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _member_url(code: str, page: int) -> str:
    return f"https://q.10jqka.com.cn/gn/detail/order/desc/page/{page}/ajax/1/code/{code}/"


def _member_table_closed(text: str) -> bool:
    """Require explicit source table boundaries, without pandas parser repair."""
    class TableBoundary(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.seen = False
            self.depth = 0
            self.closed = False

        def handle_starttag(self, tag: str, attrs: list) -> None:
            if tag == "table":
                self.seen = True
                self.closed = False
                self.depth += 1

        def handle_endtag(self, tag: str) -> None:
            if tag == "table" and self.depth:
                self.depth -= 1
                self.closed = self.depth == 0

    boundary = TableBoundary()
    boundary.feed(text)
    boundary.close()
    return boundary.seen and boundary.closed


def _member_response_has_error(text: str) -> bool:
    """Explicit error/challenge markup or throttle text cannot prove an end page."""
    class ErrorEvidence(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.marked = False
            self.ignored = 0
            self.text = []

        def handle_starttag(self, tag: str, attrs: list) -> None:
            if tag in {"script", "style"}:
                self.ignored += 1
            for key, value in attrs:
                if key in {"class", "id"} and value:
                    tokens = re.split(r"[\s_-]+", value.lower())
                    if set(tokens) & {"error", "throttle", "captcha", "interstitial"}:
                        self.marked = True

        def handle_endtag(self, tag: str) -> None:
            if tag in {"script", "style"} and self.ignored:
                self.ignored -= 1

        def handle_data(self, data: str) -> None:
            if not self.ignored:
                self.text.append(data)

    evidence = ErrorEvidence()
    evidence.feed(text)
    evidence.close()
    body = " ".join(evidence.text).lower()
    return evidence.marked or any(phrase in body for phrase in (
        "访问过于频繁", "访问频繁", "请稍后重试", "too many requests", "access denied",
    ))


def concept_members_observation(
    code: str, session: requests.Session | None = None,
) -> dict:
    """Collect one board with source-bound, JSON-serializable observation evidence.

    States are complete_nonempty, partial, failed and uncovered. Only
    complete_nonempty is currently qualified. The incumbent source exposes no
    verified zero-member count/publication-time field: a first empty table is
    uncovered, never an invented complete_empty marker, and source_asof is typed
    unknown. A valid empty terminal table AFTER member pages ends a nonempty
    pagination; missing/interstitial tables do not. Qualification also requires
    explicit source table end tags: parser recovery is partial evidence. Check all
    tables because pandas can skip hidden tables when selecting the member table.
    Parse hidden candidates too; multiple member-shaped tables or explicit source
    error/challenge evidence leave recovered facts unqualified. Even a short
    nonempty page cannot end pagination when every member was already seen.

    Counts describe parsed source rows, not price/measurement coverage. Partial
    facts are retained only in this return, with qualified=False. Response digests
    bind actual bodies and final board/page URLs; no cookies/headers are copied.
    observation_id excludes collection clocks and binds the exact observed
    responses/outcome. It is not first acceptance, a PIT append, or a rights grant.
    """
    board = str(code).strip() if code is not None else None
    result = {
        "schema": COLLECTION_OBSERVATION_SCHEMA,
        "source": "q.10jqka.com.cn",
        "board_id": board,
        "started_at": _collection_clock(),
        "finished_at": None,
        "source_asof": None,
        "source_asof_status": "unknown",
        "state": "uncovered",
        "qualified": False,
        "reason": None,
        "completion_basis": None,
        "members": [],
        "responses": [],
        "errors": [],
        "coverage": {"pages_parsed": 0, "rows_parsed": 0,
                     "unique_members": 0, "duplicate_members": 0,
                     "expected_members": None},
        "observation_id": None,
    }

    def finish(state: str, reason: str | None, basis: str | None = None) -> dict:
        result.update(state=state, reason=reason, completion_basis=basis,
                      qualified=state == "complete_nonempty",
                      finished_at=_collection_clock())
        result["coverage"]["unique_members"] = len(result["members"])
        if result["responses"]:
            identity = {field: result[field] for field in (
                "schema", "source", "board_id", "source_asof", "source_asof_status",
                "state", "reason", "completion_basis", "members",
            )}
            # A failed preliminary retry is audit evidence, not a different
            # successful source population. Keep its trace in the return only.
            identity["responses"] = [
                {field: value for field, value in receipt.items() if field != "attempt"}
                for receipt in result["responses"]
                if not result["qualified"] or receipt["status_code"] == 200
            ]
            payload = json.dumps(identity, ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":")).encode("utf-8")
            result["observation_id"] = "ths-collection:" + hashlib.sha256(payload).hexdigest()
        return result

    def refused(reason: str, *, uncovered: bool = False) -> dict:
        return finish("partial" if result["members"] else
                      ("uncovered" if uncovered else "failed"), reason)

    if board is None or re.fullmatch(r"[0-9]{6}", board) is None:
        return refused("invalid_board_id", uncovered=True)
    try:
        s = session if session is not None else _session()
    except Exception as exc:  # noqa: BLE001 — no source response was observed
        result["errors"].append({"kind": type(exc).__name__, "page": None})
        return refused("session_unavailable")

    seen: set[str] = set()
    for pg in range(1, _MAX_PAGES + 1):
        url = _member_url(board, pg)
        response = None
        for attempt in range(2):
            try:
                response = s.get(url, timeout=25)
            except Exception as exc:  # noqa: BLE001 — preserve source failure as failure
                result["errors"].append({"kind": type(exc).__name__, "page": pg,
                                         "attempt": attempt + 1})
                if attempt:
                    return refused("fetch_failed")
            else:
                # requests supplies exact response bytes. A text-only compatibility
                # response has a separately named UTF-8 digest basis, never raw-byte proof.
                raw = getattr(response, "content", None)
                if isinstance(raw, bytes):
                    digest_basis = "response.content"
                else:
                    raw = response.text.encode("utf-8")
                    digest_basis = "response.text:utf8"
                result["responses"].append({
                    "page": pg, "attempt": attempt + 1, "requested_url": url,
                    "response_url": getattr(response, "url", None),
                    "status_code": response.status_code,
                    "body_sha256": hashlib.sha256(raw).hexdigest(),
                    "body_bytes": len(raw), "digest_basis": digest_basis,
                    "member_table_closed": None, "member_table_count": None,
                    "source_error": None,
                })
                if response.status_code == 200:
                    break
                if attempt:
                    return refused("http_failure")
            try:
                # Preserve the existing one fresh-cookie/session retry, not another
                # retry scheduler. Tests supply an offline session for this seam.
                s = _session()
                time.sleep(1.5)
            except Exception as exc:  # noqa: BLE001
                result["errors"].append({"kind": type(exc).__name__, "page": pg})
                return refused("session_unavailable")

        final_url = getattr(response, "url", None)
        if not isinstance(final_url, str) or not final_url:
            return refused("response_identity_unknown", uncovered=True)
        try:
            actual, expected = urlsplit(final_url), urlsplit(url)
            matches = (actual.scheme == expected.scheme
                       and actual.netloc == expected.netloc and actual.path == expected.path
                       and actual.query == expected.query and actual.fragment == expected.fragment)
        except ValueError:
            matches = False
        if not matches:
            return refused("response_identity_mismatch", uncovered=True)
        table_closed = _member_table_closed(response.text)
        source_error = _member_response_has_error(response.text)
        result["responses"][-1].update(member_table_closed=table_closed,
                                       source_error=source_error)
        try:
            tables = pd.read_html(StringIO(response.text), displayed_only=False)
        except Exception as exc:  # noqa: BLE001 — no table is not an end-page proof
            result["errors"].append({"kind": type(exc).__name__, "page": pg})
            return refused("member_table_parse_failed")
        result["coverage"]["pages_parsed"] += 1
        result["coverage"]["rows_parsed"] += sum(len(table) for table in tables)
        candidates = [table for table in tables
                      if {"代码", "名称"}.issubset({str(c) for c in table.columns})]
        result["responses"][-1]["member_table_count"] = len(candidates)
        if not candidates:
            return refused("member_columns_invalid")
        # Retain valid positive facts from every candidate, but only a unique
        # member-shaped table can supply an authoritative pagination end.
        ambiguous = len(candidates) != 1
        tbl = pd.concat(candidates, ignore_index=True)
        if tbl.empty:
            if not table_closed:
                return refused("member_table_unclosed")
            if source_error:
                return refused("source_error_response")
            if ambiguous:
                return refused("member_tables_ambiguous")
            if not result["members"]:
                return refused("empty_membership_unconfirmed", uncovered=True)
            return finish("complete_nonempty", None, "terminal_empty_member_table")

        page_members: list[dict] = []
        for _, row in tbl.iterrows():
            value = str(row["代码"]).strip()
            if (pd.isna(row["代码"]) or pd.isna(row["名称"])
                    or re.fullmatch(r"[0-9]{1,6}(?:\.0)?", value) is None
                    or not str(row["名称"]).strip()):
                return refused("member_identity_invalid")
            page_members.append({"ticker": to_suffixed(value.split(".")[0]),
                                 "name": str(row["名称"]).strip()})
        if all(member["ticker"] in seen for member in page_members):
            result["coverage"]["duplicate_members"] += len(page_members)
            return refused("repeated_member_page")
        for member in page_members:
            if member["ticker"] in seen:
                result["coverage"]["duplicate_members"] += 1
                continue
            seen.add(member["ticker"])
            result["members"].append(member)
        if not table_closed:
            return refused("member_table_unclosed")
        if source_error:
            return refused("source_error_response")
        if ambiguous:
            return refused("member_tables_ambiguous")
        if len(tbl) < 10:
            return finish("complete_nonempty", None, "short_member_page")
        time.sleep(_PAGE_PAUSE)
    return refused("page_ceiling_without_end")


def concept_members(code: str, session: requests.Session | None = None) -> list[dict]:
    """Compatibility list API: complete positive members or an unresolved empty list.

    Unqualified empty membership remains [] for the existing snapshot caller,
    which already discards it. Partial/failed/unbound responses raise ThsTruncated;
    a missing later page can no longer silently qualify previously collected rows.
    """
    observation = concept_members_observation(code, session)
    if observation["qualified"] or observation["reason"] == "empty_membership_unconfirmed":
        return observation["members"]
    raise ThsTruncated(f"{code}: {observation['reason']}")


def snapshot(theme_names: list[str], as_of: str | None = None,
             resume: bool = True, snap_dir: "Path | str | None" = None) -> dict:
    """Fetch members for the given THS concept names and write a dated raw snapshot — RESUMABLE.

    THS IP-throttles bursts, so a single run rarely fetches every theme: this saves progress after
    each success and, on `_MAX_CONSEC_EMPTY` consecutive empty themes (the throttle signature),
    stops early so a later run can pick up where it left off. With `resume=True` (default) it loads
    today's existing snapshot and skips themes already resolved — so running it a few times across
    cool-downs accumulates full coverage. Each theme uses a fresh session + fresh `v` cookie.

    `snap_dir` overrides where the dated file is written (default: the canonical
    data/baskets_china_ths/snapshots/). It exists because progress is persisted after EVERY theme,
    so a run killed mid-scrape leaves a PARTIAL dated file wherever it was writing — and a partial
    dated file in the canonical directory is exactly what `ThsTruncated` exists to prevent one
    theme at a time: the seed step reads the newest dated file as the authoritative board list, so
    unfetched themes there read as mass exits (and, for the auto-imported taxonomy, as vanished
    baskets). `scripts/scrape_ths_weekly.py` therefore scrapes into a STAGING directory and
    promotes the file into the canonical one only once every theme resolved — complete-or-fail at
    the run level, mirroring this module's complete-or-fail at the theme level.

    Returns {theme_name: [{ticker,name}, …]} for every theme resolved so far (this run + prior).
    """
    code_map = concept_code_map()
    if not code_map:
        log.error("no THS concept map — cannot snapshot")
        return {}

    as_of = as_of or date.today().isoformat()
    snap_dir = Path(snap_dir) if snap_dir is not None else _DATA / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap_p = snap_dir / f"{as_of}.json"

    result: dict[str, list[dict]] = {}
    if resume and snap_p.exists():
        try:
            result = json.loads(snap_p.read_text())
            log.info("resuming today's snapshot — %d themes already resolved", len(result))
        except Exception as e:  # noqa: BLE001
            log.warning("existing snapshot unreadable (%s) — starting fresh", e)

    todo = [n for n in theme_names if n not in result or not result.get(n)]
    consec_empty = 0
    for name in todo:
        code = code_map.get(name)
        if not code:
            log.warning("THS concept name not found (renamed/retired?): %s", name)
            continue
        try:
            members = concept_members(code, _session())   # fresh cookie+session per theme
        except ThsTruncated as e:
            # partial/throttled fetch — do NOT record it (would fabricate `removed` events on the
            # next seed diff). Leave the theme unresolved so a later resume run retries it.
            consec_empty += 1
            log.warning("THS concept '%s' (%s) incomplete: %s (%d/%d consecutive)",
                        name, code, e, consec_empty, _MAX_CONSEC_EMPTY)
            if consec_empty >= _MAX_CONSEC_EMPTY:
                log.error("THS appears to be throttling this IP — stopping; re-run to resume "
                          "(%d/%d themes resolved so far)", len(result), len(theme_names))
                break
            time.sleep(_THEME_PAUSE * 2)              # back off harder after a truncated fetch
            continue
        if not members:
            consec_empty += 1
            log.warning("THS concept '%s' (%s) returned no members (%d/%d consecutive)",
                        name, code, consec_empty, _MAX_CONSEC_EMPTY)
            if consec_empty >= _MAX_CONSEC_EMPTY:
                log.error("THS appears to be throttling this IP — stopping; re-run to resume "
                          "(%d/%d themes resolved so far)", len(result), len(theme_names))
                break
            time.sleep(_THEME_PAUSE * 2)              # back off harder after an empty
            continue
        consec_empty = 0
        result[name] = members
        snap_p.write_text(json.dumps(result, ensure_ascii=False, indent=0))   # persist progress
        log.info("THS concept '%s' (%s): %d members  [%d/%d resolved]",
                 name, code, len(members), len(result), len(theme_names))
        time.sleep(_THEME_PAUSE)

    snap_p.write_text(json.dumps(result, ensure_ascii=False, indent=0))
    log.info("THS snapshot %s — %d/%d themes resolved", as_of, len(result), len(theme_names))
    return result


def main() -> int:
    """Resumably fetch today's snapshot for the curated THS themes (scripts.seed_china_ths_baskets).

    Safe to run repeatedly: each run skips themes already resolved today and stops early if THS
    starts throttling, so a handful of runs across cool-downs fill in full coverage.

    Usage: python -m collectors.china_ths_concepts
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from scripts.seed_china_ths_baskets import CURATED
    names = [row[1] for row in CURATED]
    res = snapshot(names, resume=True)
    return 0 if res else 1


if __name__ == "__main__":
    raise SystemExit(main())
