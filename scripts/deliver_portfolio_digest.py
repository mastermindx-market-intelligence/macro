"""One account's change digest (Portfolio §19.5). No scheduler or enrolment.

The native nightly capture uses the brief's account-scoped holdings and current
context. A trusted cursor reader must supply a capture from an earlier night.
Without that reader the delivery job refuses to infer a prior book. Never accept an address or a portfolio from a public request.
The script returns only a disposition. It does not log or persist the book.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from email.headerregistry import Address
import json
from urllib.parse import urlsplit
from urllib.request import HTTPSHandler, OpenerDirector, Request
from uuid import UUID

from app import email_segments, mailer, marketing_emails
from engine.portfolio_changes import MAX_PREVIOUS_NAMES, SNAPSHOT_SCHEMA, is_snapshot, snapshot_state
from engine.portfolio_digest import compose_digest


def _load_pref(user_id):
    # Read the existing table. In a schema without the affirmative digest
    # preference the returned row cannot grant consent.
    rows = marketing_emails._pg("GET", f"email_prefs?user_id=eq.{user_id}&select=*")
    return rows[0] if isinstance(rows, list) and len(rows) == 1 else None


def _consents(user_id):
    row = _load_pref(user_id)
    return (isinstance(row, dict) and row.get("user_id") == user_id
            and row.get("portfolio_digest_opt_in") is True
            and row.get("marketing_opt_out") is False)


def _recipient(user_id):
    # Single GoTrue record on the existing marketing account service. Holdings
    # content requires the current confirmed address for exactly this account.
    key = marketing_emails._key()
    if not key:
        return None
    url = f"{marketing_emails.SUPABASE_URL}/auth/v1/admin/users/{user_id}"
    if urlsplit(url).scheme != "https":
        return None
    req = Request(url, headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"})
    # A service-role header belongs only on the configured auth host.
    # Installing only the HTTPS handler prevents automatic redirect following.
    opener = OpenerDirector()
    opener.add_handler(HTTPSHandler())
    with opener.open(req, timeout=8) as response:
        if response.status != 200:
            return None
        user = json.load(response)
    if (isinstance(user, dict) and user.get("id") == user_id and user.get("email_confirmed_at")
            and email_segments.base_match(user)):
        address = user["email"].strip()
        mailbox = Address(addr_spec=address)
        if mailbox.domain and mailbox.username:
            return mailbox.addr_spec
    return None


@dataclass(frozen=True)
class NightlyCapture:
    """Internal result of a consented night's read. Never accept it from an HTTP client."""
    user_id: str
    asof: str
    population: str
    snapshot: dict


def _nightly_context():
    # Use the brief's configured repository and the same nightly artifact.
    from app.main import REPO, _PORTFOLIO_CTX_PATH

    with (REPO / _PORTFOLIO_CTX_PATH).open(encoding="utf-8") as stream:
        return json.load(stream)


def _account_holdings(user_id):
    from app.main import _portfolio_load_holdings
    return _portfolio_load_holdings(user_id)


def _capture_day():
    # build_portfolio_ctx.main stamps the host's local calendar date by default.
    return date.today().isoformat()


def capture_digest_night(user_id: str, asof: str, *, enabled=False) -> NightlyCapture:
    """Capture only the current bake with the account's current book on that night."""
    if (enabled is not True or not marketing_emails.marketing_enabled()
            or str(UUID(user_id)) != user_id or date.fromisoformat(asof).isoformat() != asof
            or asof != _capture_day() or not _consents(user_id)):
        raise ValueError("capture unavailable")
    ctx = _nightly_context()
    if (not isinstance(ctx, dict) or ctx.get("asof") != asof
            or ctx.get("schema") not in ("portfolio_ctx.v1", "portfolio_ctx.v2")
            or not isinstance(ctx.get("tickers"), dict)):
        raise ValueError("nightly context unavailable")
    holdings, population = _account_holdings(user_id)
    if population not in ("positions", "watchlist_union") or not isinstance(holdings, list):
        raise ValueError("account holdings unavailable")
    tickers = []
    for holding in holdings:
        if not isinstance(holding, dict) or not isinstance(holding.get("ticker"), str) or not holding["ticker"].strip():
            raise ValueError("incomplete account holdings")
        tickers.append(holding["ticker"])
    return NightlyCapture(user_id, asof, population, snapshot_state(ctx, tickers))


def _nightly_book(user_id, asof, read_previous):
    """Join the original trusted cursor's capture to this night's native read.

    There is no server cursor in the current schema. A missing cursor or a hash
    without its source snapshot cannot be used as an empty prior portfolio.
    """
    if read_previous is None:
        raise ValueError("no account cursor source")
    prior = read_previous(user_id, asof)
    if (not isinstance(prior, NightlyCapture) or prior.user_id != user_id
            or date.fromisoformat(prior.asof) >= date.fromisoformat(asof)
            or prior.population not in ("positions", "watchlist_union")
            or not is_snapshot(prior.snapshot) or prior.snapshot.get("schema") != SNAPSHOT_SCHEMA
            or prior.snapshot.get("asof") != prior.asof):
        raise ValueError("unqualified account cursor")
    current = capture_digest_night(user_id, asof, enabled=True)
    if current.population != prior.population:
        raise ValueError("incomparable portfolio populations")
    return {"user_id": user_id, "asof": asof, "population": current.population,
            "previous": prior.snapshot, "current": current.snapshot}


def deliver_digest(user_id: str, asof: str, *, load_book=None, read_previous=None, enabled=False, send_fn=None) -> str:
    """Deliver at most one changed-book email per account/day through the marketing ledger.

    Both the explicit job switch and the existing marketing master must be on.
    send_fn may replace the mailer for offline tests. Return its original status,
    including duplicate, suppressed, skipped_no_smtp, queued or EFFECT_UNKNOWN.
    """
    if enabled is not True or not marketing_emails.marketing_enabled():
        return "disabled"
    try:
        if str(UUID(user_id)) != user_id or date.fromisoformat(asof).isoformat() != asof:
            return "invalid_request"
    except (TypeError, ValueError, AttributeError):
        return "invalid_request"

    try:
        if not _consents(user_id):
            return "not_opted_in"
        if load_book is not None and read_previous is not None:
            return "source_unavailable"
        book = (_nightly_book(user_id, asof, read_previous) if load_book is None
                else load_book(user_id, asof))
    except Exception:
        return "source_unavailable"
    if not isinstance(book, dict) or book.get("user_id") != user_id or book.get("asof") != asof:
        return "source_unavailable"
    current = book.get("current")
    if not is_snapshot(current) or current.get("asof") != asof:
        return "source_unavailable"
    if "previous" not in book:
        return "source_unavailable"
    previous = book["previous"]
    if previous is not None and previous != {}:
        if not is_snapshot(previous) or len(previous["names"]) > MAX_PREVIOUS_NAMES:
            return "source_unavailable"
        try:
            if date.fromisoformat(previous["asof"]) >= date.fromisoformat(asof):
                return "source_unavailable"
        except (KeyError, ValueError, TypeError):
            return "source_unavailable"
    digest = compose_digest(previous or {}, current, user_id=user_id, asof=asof,
                            population=book.get("population", "unspecified"))
    if digest is None:
        return "quiet"
    if not mailer.is_configured():
        return "skipped_no_smtp"
    footer = marketing_emails.unsub_page_url(user_id)
    one_click = marketing_emails.unsub_api_url(user_id)
    if not all(urlsplit(link).scheme == "https" and urlsplit(link).hostname for link in (footer, one_click)):
        return "unsubscribe_unavailable"
    try:
        recipient = _recipient(user_id)
        if not recipient:
            return "recipient_unavailable"
        if not _consents(user_id):
            return "not_opted_in"
    except Exception:
        return "source_unavailable"

    html, text = mailer.render_email(digest["title_en"], digest["title_zh"], digest["blocks"],
                                     preheader=digest["preheader"], eyebrow=digest["eyebrow"],
                                     why_en=digest["why_en"], why_zh=digest["why_zh"],
                                     unsubscribe_url=footer)
    send = mailer.send if send_fn is None else send_fn
    return send(template=digest["template"], cls=digest["cls"], user_id=user_id,
                to_email=recipient, idem_key=digest["idem_key"], subject=digest["subject"],
                html=html, text=text, strict_ledger=True, headers={"unsubscribe_url": one_click})
