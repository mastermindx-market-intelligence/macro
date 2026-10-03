"""MarketDesk API client — the single place that knows how MarketDesk works.

Everything here is driven through a Playwright ``BrowserContext`` so requests carry the
authenticated session cookies from the persistent profile (see ``docs/MARKETDESK_API.md``).
We use ``context.request`` (Playwright's ``APIRequestContext``) rather than raw ``requests``
so no unauthenticated calls ever happen and redirects/cookies are handled by the browser
stack. The client is intentionally *deterministic* — no LLM, no heuristics.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Iterator

from tenacity import (
    retry, retry_if_exception_type, stop_after_attempt, wait_exponential,
)

from .config import Config
from .schemas import ArticleMeta
from .utils import chunked, get_logger, humanize_age, jitter_sleep, normalize_ws

log = get_logger("marketdesk")

PDF_TYPE = "application/pdf"
FOLDER_TYPE = "folder"
_PROVISION_CHUNK = 50


def _looks_like_app_shell(head: bytes) -> bool:
    """True if ``head`` is the start of an HTML document (an over-cap bounce OR
    the logged-out landing page — :meth:`MarketDeskClient.download_blob` probes
    the session to tell those two apart).

    Case-insensitive on the first non-whitespace bytes: ``<!doctype`` or ``<html``.
    """
    stripped = head.lstrip()[:16].lower()
    return stripped.startswith(b"<!doctype") or stripped.startswith(b"<html")


def _as_id_list(payload: Any, what: str) -> list[str]:
    """Coerce a feed payload to a list of ids, refusing a logged-out response.

    Feed endpoints return a JSON **array**. A logged-out MarketDesk answers 200
    with the object ``{"success": false}`` — and ``list()`` of a dict yields its
    KEYS, so a bare ``list(payload)`` silently turns a dead session into a
    plausible one-item feed. That is exactly how a lapsed login went unnoticed
    for four days (2026-08-07 → 08-11): the log read ``latest=1 picks=1 saved=1``
    where healthy is ``latest=25 picks=80``, and discovery reported an honest-
    looking ``scanned=0 new=0`` every quarter hour. Anything that is not a list
    is a dead session, not an empty feed.
    """
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise SessionExpired(
            f"{what}: expected a JSON array, got {type(payload).__name__} "
            f"({str(payload)[:60]}) — the MarketDesk session has lapsed"
        )
    return list(payload)


class MarketDeskError(RuntimeError):
    pass


class TransientHTTPError(MarketDeskError):
    """Raised on 5xx / network errors so tenacity retries."""


class DownloadCapExhausted(MarketDeskError):
    """Download refused because the account hit its rolling 24h PDF cap.

    Empirically, an over-limit ``/files/<id>/blob`` request returns the site's
    HTML app-shell (~146KB, starting ``<!DOCTYPE html>``) with a 200 instead of
    the PDF. We surface that specific bounce as its own exception (a subclass of
    ``MarketDeskError``, so existing generic handlers still treat it as a failed
    download) so the trickle allocator can catch it precisely and put the account
    into a self-calibrating cooldown rather than marking the paper permanently
    bad.

    NOT to be confused with :class:`SessionExpired`: both arrive as HTML with a
    200, and only a session probe separates them. See that class.
    """


class SessionExpired(MarketDeskError):
    """The persistent browser profile is no longer logged in to MarketDesk.

    MarketDesk never answers a logged-out client with 401/403 — it returns **200**
    for everything, which is what makes this failure mode invisible:

    * feed endpoints return the object ``{"success": false}`` instead of an array
      (see :func:`_as_id_list`);
    * ``/files/<id>/blob`` returns a ~2.2KB ``MarketDesk: Landing`` HTML page,
      whereas a genuine over-cap bounce returns the ~146KB app-shell. Both start
      ``<!doctype html>``, so byte-sniffing alone CANNOT tell them apart and the
      landing page was misread as :class:`DownloadCapExhausted` for four days
      while the account's own counter said ``used_24h=0``.

    The authoritative discriminator is therefore not the page but
    :meth:`MarketDeskClient.session_alive`. Recovery needs a human: stop the
    daemon (the profile is single-writer) and re-run ``marketdesk auth``.
    """


class MarketDeskClient:
    def __init__(self, context: Any, cfg: Config):
        self.ctx = context
        self.cfg = cfg
        self.req = context.request
        self._headers = {
            "Accept": "application/json, text/plain, */*",
            "Referer": f"{cfg.base_url}/library/browse",
            "X-Requested-With": "XMLHttpRequest",
        }

    # --- low level ---------------------------------------------------------
    @retry(
        retry=retry_if_exception_type(TransientHTTPError),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=0.6, max=8),
        reraise=True,
    )
    def _get(self, url: str) -> Any:
        resp = self.req.get(url, headers=self._headers, timeout=30_000)
        if resp.status >= 500:
            raise TransientHTTPError(f"GET {url} -> {resp.status}")
        if not resp.ok:
            raise MarketDeskError(f"GET {url} -> {resp.status}")
        return resp.json()

    @retry(
        retry=retry_if_exception_type(TransientHTTPError),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=0.6, max=8),
        reraise=True,
    )
    def _post(self, url: str, body: Any) -> Any:
        resp = self.req.post(url, data=body, headers=self._headers, timeout=30_000)
        if resp.status >= 500:
            raise TransientHTTPError(f"POST {url} -> {resp.status}")
        if not resp.ok:
            raise MarketDeskError(f"POST {url} -> {resp.status}")
        return resp.json()

    # --- session ------------------------------------------------------------
    def session_alive(self) -> bool:
        """True iff the profile's session still yields an authenticated response.

        The same probe as ``auth.BrowserSession.is_authenticated`` (POST the
        cheapest feed, require a JSON **array**), but reachable from the client
        so a download bounce can ask it mid-tick. That matters: the probe on
        BrowserSession runs only when a session is OPENED, and the production
        daemon holds one context alive for days — so it cannot see a session that
        lapses at hour 60. Never raises; a probe that cannot answer is treated as
        dead, which fails toward the loud path rather than the silent one.
        """
        try:
            resp = self.req.post(
                self.cfg.api("latest/latest"), data={},
                headers=self._headers, timeout=20_000,
            )
            if not resp.ok:
                return False
            return isinstance(resp.json(), list)
        except Exception as e:  # noqa: BLE001 - a probe that fails IS a dead session
            log.warning("session probe failed: %s", e)
            return False

    # --- feeds -------------------------------------------------------------
    def latest(self, institutions: list[str] | None = None) -> list[str]:
        body: dict[str, Any] = {}
        if institutions:
            body["institutions"] = institutions
        return _as_id_list(self._post(self.cfg.api("latest/latest"), body), "latest")

    def picks(self) -> list[str]:
        return _as_id_list(self._get(self.cfg.api("latest/picks")), "picks")

    def saved(self) -> list[str]:
        return _as_id_list(self._get(self.cfg.api("latest/saved")), "saved")

    def viewed(self) -> list[str]:
        return _as_id_list(self._get(self.cfg.api("latest/viewed")), "viewed")

    # --- tree --------------------------------------------------------------
    def browse_current(self) -> list[str]:
        return _as_id_list(
            self._get(self.cfg.api("library/browse/current")), "browse/current"
        )

    def browse(self, path_id: str) -> list[str]:
        return _as_id_list(
            self._get(self.cfg.api(f"library/browse/{path_id}")), f"browse/{path_id}"
        )

    # --- items -------------------------------------------------------------
    def provision(self, path_ids: list[str]) -> list[dict]:
        """Batch-hydrate item metadata. Chunked to be polite."""
        out: list[dict] = []
        for chunk in chunked(path_ids, _PROVISION_CHUNK):
            res = self._post(self.cfg.api("items/provision"), {"pathIds": chunk})
            if isinstance(res, list):
                out.extend(res)
            jitter_sleep()
        return out

    def item(self, item_id: str) -> dict:
        return self._get(self.cfg.api(f"items/{item_id}"))

    def item_extra(self, item_id: str) -> dict:
        try:
            return self._get(self.cfg.api(f"items/{item_id}/extra")) or {}
        except MarketDeskError:
            return {}

    def item_path(self, item_id: str) -> list[dict]:
        try:
            return list(self._get(self.cfg.api(f"items/{item_id}/path")) or [])
        except MarketDeskError:
            return []

    # --- tree walk ---------------------------------------------------------
    def walk_papers(
        self,
        *,
        since_unix: int | None = None,
        limit: int | None = None,
        max_days: int | None = 30,
    ) -> Iterator[dict]:
        """Yield paper items (``type == application/pdf``) newest-first.

        Walks current -> year -> month -> day -> broker -> paper. Days are processed
        newest-first; when ``since_unix`` is set we stop after the first fully-older day.
        Bounded by ``max_days`` and ``limit``.
        """
        yielded = 0
        days_seen = 0
        for year in self.browse_current():
            for month in self.browse(year):
                for day in self.browse(month):
                    if max_days is not None and days_seen >= max_days:
                        return
                    days_seen += 1
                    day_papers = self._papers_in_day(day)
                    if not day_papers:
                        continue
                    day_papers.sort(key=lambda x: x.get("t") or 0, reverse=True)
                    newest_t = day_papers[0].get("t") or 0
                    if since_unix is not None and newest_t < since_unix:
                        # this day (and every older one) is entirely before the cutoff
                        return
                    for p in day_papers:
                        if since_unix is not None and (p.get("t") or 0) < since_unix:
                            continue
                        yield p
                        yielded += 1
                        if limit is not None and yielded >= limit:
                            return

    def _papers_in_day(self, day_id: str) -> list[dict]:
        """All PDF papers under a day folder (across its broker sub-folders)."""
        child_ids = self.browse(day_id)
        if not child_ids:
            return []
        children = self.provision(child_ids)
        papers: list[dict] = []
        broker_ids: list[str] = []
        for c in children:
            if c.get("type") == PDF_TYPE:
                papers.append(c)
            elif c.get("type") == FOLDER_TYPE and c.get("pathId"):
                broker_ids.append(c["pathId"])
        for broker in broker_ids:
            paper_ids = self.browse(broker)
            if paper_ids:
                papers.extend(
                    p for p in self.provision(paper_ids) if p.get("type") == PDF_TYPE
                )
            jitter_sleep()
        return papers

    # --- download ----------------------------------------------------------
    def download_blob(self, blob_id: str) -> bytes:
        """GET the authenticated blob URL, follow redirects, return PDF bytes."""
        url = self.cfg.blob_url(blob_id)
        resp = self.req.get(url, headers={"Referer": self._headers["Referer"]},
                            timeout=120_000)
        if resp.status >= 500:
            raise TransientHTTPError(f"blob {blob_id} -> {resp.status}")
        if not resp.ok:
            raise MarketDeskError(f"blob {blob_id} -> {resp.status}")
        data = resp.body()
        if not data or data[:5] != b"%PDF-":
            head = (data or b"")[:64]
            if _looks_like_app_shell(head):
                # HTML where a PDF belongs means one of two very different things,
                # and the bytes cannot tell them apart (both are 200 + <!doctype).
                # Ask the session itself: a live session that bounced really is
                # over its cap; a dead one is a lapsed login wearing a cap's
                # clothes. Getting this backwards costs days of silent downtime.
                if not self.session_alive():
                    raise SessionExpired(
                        f"blob {blob_id}: got a {len(data or b'')}-byte HTML page "
                        "instead of a PDF and the session probe came back dead — "
                        "the MarketDesk login has LAPSED (stop the daemon and "
                        "re-run `marketdesk auth`). This is NOT a download cap."
                    )
                raise DownloadCapExhausted(
                    f"blob {blob_id}: got the HTML app-shell instead of a PDF "
                    f"({len(data or b'')} bytes) — account download cap reached"
                )
            raise MarketDeskError(
                f"blob {blob_id}: not a PDF (got {len(data or b'')} bytes, "
                f"head={data[:16]!r})"
            )
        return data


# ---------------------------------------------------------------------------
# item dict -> ArticleMeta (deterministic hydration)
# ---------------------------------------------------------------------------
_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}

_BREADCRUMB_YEAR = re.compile(r"\s*(20\d{2})\s*$")
_BREADCRUMB_MON_DAY = re.compile(r"\s*([A-Za-z]{3,9})\s+(\d{1,2})\s*$")


def _date_from_breadcrumb(breadcrumb: list[str] | None) -> datetime | None:
    """Recover a DAY-precision publish date from the MarketDesk browse breadcrumb.

    MarketDesk's library tree is organized by publish date, so a trail like
    ``["2026", "July", "Jul 7", "Goldman", "S&T"]`` carries the date even when the
    item dict omits its ``t`` unix timestamp. We pair the 4-digit YEAR crumb with a
    ``"Mon D"`` leaf crumb → midnight UTC of that day. Returns None when the trail
    has no parseable date, so the caller leaves ``published_at`` unset rather than
    inventing one — the vault then sorts an undated paper LAST (never as newest).

    Deterministic + pure; the first VALID month/day crumb wins, so a non-date crumb
    like ``"Top 5"`` is skipped in favour of the real ``"Jul 7"``.
    """
    if not breadcrumb:
        return None
    year = None
    for c in breadcrumb:
        m = _BREADCRUMB_YEAR.match(str(c))
        if m:
            year = int(m.group(1))
            break
    mon_day = None
    for c in breadcrumb:
        m = _BREADCRUMB_MON_DAY.match(str(c))
        if not m:
            continue
        mon = _MONTHS.get(m.group(1)[:3].title())
        day = int(m.group(2))
        if mon and 1 <= day <= 31:
            mon_day = (mon, day)
            break
    if not year or not mon_day:
        return None
    try:
        return datetime(year, mon_day[0], mon_day[1], tzinfo=timezone.utc)
    except ValueError:               # e.g. Feb 30 — refuse rather than guess
        return None


def build_meta(
    cfg: Config,
    item: dict,
    *,
    breadcrumb: list[str] | None = None,
    summary: str | None = None,
    is_latest: bool = False,
    is_top_pick: bool = False,
    is_saved: bool = False,
) -> ArticleMeta:
    blob_id = item["pathId"]
    t = item.get("t")
    published_at = ArticleMeta.unix_to_dt(t)
    published_unix = t
    if published_at is None:
        # No `t` from the API — recover the publish DATE from the browse tree
        # (organized by publish date) so we never emit a dateless sidecar. Day
        # precision; stays None when the trail carries no parseable date, in which
        # case the vault sorts the paper LAST rather than stamping it "today".
        recovered = _date_from_breadcrumb(breadcrumb)
        if recovered is not None:
            published_at = recovered
            published_unix = int(recovered.timestamp())
            log.info("build_meta: %s has no `t`; recovered publish date %s "
                     "from breadcrumb", blob_id, recovered.date().isoformat())
    return ArticleMeta(
        blob_id=blob_id,
        article_url=cfg.article_url(blob_id),
        blob_url=cfg.blob_url(blob_id),
        title=normalize_ws(item.get("name")),
        institution=item.get("institution") or None,
        published_at=published_at,
        published_unix=published_unix,
        size_bytes=item.get("size"),
        marketdesk_age_text=humanize_age(published_unix),
        marketdesk_summary=normalize_ws(summary) if summary else None,
        breadcrumb=breadcrumb or [],
        is_latest=is_latest,
        is_top_pick=is_top_pick,
        is_saved=is_saved,
    )
