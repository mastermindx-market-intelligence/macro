"""app/account_actions.py — the four account-panel actions (MO-B F12-13, MO-PAID-078).

``templates/account.js`` has called ``/api/account/password``, ``/api/account/email``,
``/api/account/signout-everywhere`` and ``/api/account/delete`` since the account card
shipped, and NOTHING in ``app/`` answered them. Worse, the panel resolved its API base to
``window.MM_API`` (``https://app.mastermind-x.com``) on every macro page, so the calls left
this service entirely: the Terminal host has only
``terminal/app/api/account/{alert-prefs,deletion,export}/route.ts`` and sends no
Access-Control headers, so a signed-in reader on www.mastermind-x.com got a 404 (and a
failed CORS preflight) on every control. The whole panel was cross-origin-dead. This module
is the server half of the repair; ``templates/account.js`` now resolves its base same-origin
on ``mastermind-x.com`` hosts, the idiom ``templates/theme.js`` already uses for ``/api/me``.

What each route does, and the one law that shapes all four:

* **password / email / sign-out-everywhere** are Supabase Auth calls made with the CALLER'S
  OWN token (``PUT /auth/v1/user``, ``POST /auth/v1/logout?scope=global``). No admin
  endpoint is needed and none is used: ``/auth/v1/admin/*`` is never called, and the
  service-role key never appears on an ``Authorization`` header anywhere in this file.
* **delete is an INTAKE, not a deletion.** It files a row in the Terminal's
  ``public.account_lifecycle_requests`` (migration 0016, live in production 2026-09-09) over
  PostgREST with the caller's token, so RLS (``account_lifecycle_insert_own``) is the
  authority and the row can only be the caller's own. Nothing is deleted, updated or
  removed by this service, and there is no path here that could.

**A fabricated receipt is the one forbidden outcome.** ``/api/account/delete`` answers
``ok:true`` ONLY when the store confirmed the row — a 201 whose representation carries the
receipt code, or a 409 (the ``account_lifecycle_one_open_deletion`` partial unique index)
whose read-back of the caller's own open row does. Every other outcome — network, 5xx,
401/403, an unreadable body, a shed permit — is a 503 that says nothing was filed. The
code we mint is sent to the store first and reported only after the store echoes it back.

Copy contract (spec R4): every non-2xx answer from this module is a JSON body
``{"ok": false, "error": <one plain EN sentence>, "error_zh": <one plain ZH sentence>}``
built with ``fastapi.responses.JSONResponse``. ``account.js`` reads ``r.data.error`` /
``r.data.error_zh``; FastAPI's default ``{"detail": ...}`` is never read by it, so raising
``HTTPException`` here would put a machine string on a customer's screen. The one non-2xx
body this module does not own is a request whose bytes are not JSON at all — FastAPI rejects
that before the handler runs. ``account.js`` always sends ``JSON.stringify`` of an object
with ``Content-Type: application/json``, so that path is unreachable from the panel.

Bounded, and rate-limited on both identities. Each upstream call is one
``urllib.request`` with ``timeout=4`` inside a module ``BoundedSemaphore(8)`` acquired
non-blocking (the ``lib/team_membership.py`` idiom) — a slow vendor sheds instead of
pinning FastAPI's worker threadpool — and a per-action deque window keyed by BOTH user id
and client IP (the ``app/main.py::_brain_throttle`` idiom) so one account or one address
cannot hammer Supabase Auth through us. Logs carry status codes and a sha256 digest of the
user id only: never a token, never an email address.
"""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from lib.team_membership import extract_bearer

log = logging.getLogger("macro.account_actions")
router = APIRouter()

#: Seconds. Matches ``lib/team_membership._TIMEOUT`` and ``app/paywall.py``'s bounded auth
#: GET, both of which sit on the same shared worker threadpool this route runs on.
_TIMEOUT = 4

#: Caps concurrent upstream calls, mirroring ``lib/team_membership._UPSTREAM_SEM`` and
#: ``app/paywall._AUTH_UPSTREAM_SEM``. Acquired NON-BLOCKING: an excess caller sheds to a
#: plain-word 503 immediately rather than queueing on the pool (and ``/api/health`` with it).
_UPSTREAM_LIMIT = 8
_UPSTREAM_SEM = threading.BoundedSemaphore(_UPSTREAM_LIMIT)

#: Crockford base32 — no I, L, O or U, so a receipt code read aloud or typed back from an
#: email cannot be mis-transcribed into a different valid code.
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_RECEIPT_TAIL_LEN = 8

#: Sliding-window request budget, per action, per identity kind. Password / email / delete
#: are 5 per 15 minutes because each one is a write to Supabase Auth or to the lifecycle
#: table; signing every device out is read-light and idempotent, so it gets 10.
_RATE_WINDOW_SECONDS = 900.0
_RATE_LIMITS = {"password": 5, "email": 5, "delete": 5, "signout-everywhere": 10}
_RATE_MAX_KEYS = 5_000
_rate_lock = threading.Lock()
_rate_buckets: dict[str, deque] = {}

#: Every user-facing sentence this module can put on a screen, EN and ZH together in one
#: table so a twin can never go missing. Values are (en, zh); the ZH side is real Chinese
#: with CJK punctuation, never a translation placeholder.
COPY: dict[str, tuple[str, str]] = {
    "busy": (
        "The account service is busy. Nothing was changed. Please try again in a moment.",
        "账户服务繁忙，未做任何改动。请稍后再试。",
    ),
    "no_answer": (
        "The account service did not answer. Nothing was changed. Please try again in a moment.",
        "账户服务没有响应，未做任何改动。请稍后再试。",
    ),
    "rate_limited": (
        "Too many attempts. Please wait a few minutes and try again.",
        "尝试次数过多，请几分钟后再试。",
    ),
    "no_identity": (
        "We could not confirm who is signed in. Please sign in again and try once more.",
        "我们无法确认当前登录的身份，请重新登录后再试一次。",
    ),
    "session_expired": (
        "Your session has expired. Please sign in again to do this.",
        "你的登录已过期，请重新登录后再操作。",
    ),
    "password_missing": (
        "Enter the new password you want to use.",
        "请输入你想使用的新密码。",
    ),
    "password_short": (
        "Use at least 8 characters for your new password.",
        "新密码至少需要 8 个字符。",
    ),
    "password_long": (
        "That password is too long to store. Please choose a shorter one.",
        "这个密码过长，无法保存，请选择一个更短的密码。",
    ),
    "password_weak": (
        "That password is too weak. Please choose a longer or less common one.",
        "这个密码强度不够，请换一个更长或不那么常见的密码。",
    ),
    "password_same": (
        "That is the password this account already uses. Please choose a different one.",
        "这与当前使用的密码相同，请换一个不同的密码。",
    ),
    "password_refused": (
        "We could not change your password. Please try again in a moment.",
        "我们无法修改你的密码，请稍后再试。",
    ),
    "email_missing": (
        "Enter the new email address you want to use.",
        "请输入你想使用的新邮箱地址。",
    ),
    "email_invalid": (
        "That does not look like an email address. Please check it and try again.",
        "这看起来不是一个邮箱地址，请检查后重试。",
    ),
    "email_same": (
        "That is already the email address on this account.",
        "这已经是此账户正在使用的邮箱地址。",
    ),
    "email_taken": (
        "That email address is already used by another account.",
        "该邮箱地址已被另一个账户使用。",
    ),
    "email_refused": (
        "We could not start that email change. Please check the address and try again.",
        "我们无法开始这次邮箱修改，请检查地址后重试。",
    ),
    "signout_refused": (
        "We could not sign out your other devices. Please try again in a moment.",
        "我们无法退出你的其他设备，请稍后再试。",
    ),
    "delete_confirm": (
        "Type the email on this account to confirm.",
        "请输入此账户的邮箱以确认。",
    ),
    "delete_no_email": (
        "This account has no email address on file, so we cannot check your confirmation. "
        "Please contact our support team and we will help you.",
        "此账户没有登记邮箱，因此我们无法核对你的确认信息。请联系我们的支持团队，我们会协助你。",
    ),
    "delete_not_recorded": (
        "We could not record your request, so nothing was filed and nothing was changed. "
        "Please try again later.",
        "我们无法记录你的请求，因此没有提交任何申请，你的账户也没有任何改动。请稍后再试。",
    ),
}


class _Busy(Exception):
    """No upstream permit was available — the caller shed instead of queueing."""


class _NoAnswer(Exception):
    """The upstream never answered, or answered with bytes nobody could read."""


class PasswordRequest(BaseModel):
    password: str | None = None


class EmailRequest(BaseModel):
    email: str | None = None


class DeleteRequest(BaseModel):
    confirm: str | None = None


# --------------------------------------------------------------------------- #
# credentials and identity — one source each, all of them somebody else's
# --------------------------------------------------------------------------- #
def _current_user(authorization: str | None = Header(default=None)) -> dict:
    """Lazy import mirrors ``app/account_prefs.py::_current_user`` — no app.main cycle."""
    from app.main import require_user  # noqa: PLC0415
    return require_user(authorization)


def _supabase() -> tuple[str, str]:
    """``(url, service_role_key)`` — delegated to app.account_prefs, the one owner."""
    from app.account_prefs import _supabase as _prefs_supabase  # noqa: PLC0415
    return _prefs_supabase()


def _anon_key() -> str:
    """The publishable key Supabase's gateway wants on ``apikey`` for an auth call.

    Read at call time from ``app.main`` so this process has exactly one copy of it, and so
    the caller's own token stays the only credential that decides WHO is acting.
    """
    from app.main import SUPABASE_ANON_KEY  # noqa: PLC0415
    return SUPABASE_ANON_KEY or ""


def _client_ip(request: Request) -> str:
    """The real visitor IP, resolved by ``app.main._mm_client_ip`` (app/edge_client.py).

    Never derived here: that function's docstring records five forwarded-for style headers
    measured to arrive carrying whatever the caller forged, which would let one account mint
    a fresh rate-limit bucket per request. An unreadable IP degrades to a single shared
    bucket rather than to no IP leg at all.
    """
    try:
        from app.main import _mm_client_ip  # noqa: PLC0415
        return str(_mm_client_ip(request) or "")
    except Exception:  # noqa: BLE001 — a rate-limit leg must never 500 the action
        return ""


def _digest(value: str) -> str:
    """A log-safe stand-in for a user id. Tokens and emails are never logged, digested or not."""
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()[:12]


# --------------------------------------------------------------------------- #
# answers
# --------------------------------------------------------------------------- #
def _ok(payload: dict | None = None, status: int = 200) -> JSONResponse:
    body = {"ok": True}
    if payload:
        body.update(payload)
    return JSONResponse(status_code=status, content=body)


def _err(status: int, key: str) -> JSONResponse:
    """The copy contract: ``{ok:false, error:<EN>, error_zh:<ZH>}``, never ``{"detail":…}``."""
    en, zh = COPY[key]
    return JSONResponse(status_code=status, content={"ok": False, "error": en, "error_zh": zh})


# --------------------------------------------------------------------------- #
# rate limit (app/main.py::_brain_throttle idiom: per-key deque of monotonic
# timestamps, a capped dict with oldest-key eviction, one Lock)
# --------------------------------------------------------------------------- #
def _book(key: str, limit: int, now: float, cutoff: float) -> bool:
    """Prune, then take one slot. Caller holds ``_rate_lock``. False = over budget."""
    bucket = _rate_buckets.get(key)
    if bucket is None:
        if len(_rate_buckets) >= _RATE_MAX_KEYS:
            # Evict the oldest-INSERTED key (dict preserves insertion order). Bounded
            # global memory; this never relaxes a live caller's own limit, because the
            # key being dropped is by definition the one nobody has touched longest.
            try:
                _rate_buckets.pop(next(iter(_rate_buckets)))
            except StopIteration:
                pass
        bucket = deque()
        _rate_buckets[key] = bucket
    while bucket and bucket[0] <= cutoff:
        bucket.popleft()
    if len(bucket) >= limit:
        return False
    bucket.append(now)
    return True


def _allow(action: str, user_id: str, ip: str) -> bool:
    """Consume one slot for BOTH identities. Over budget on either leg → refuse.

    Both buckets are booked even once the first has refused, which is what stops a caller
    who rotates one identity from being let back in by the other leg staying empty.
    """
    limit = _RATE_LIMITS[action]
    now = time.monotonic()
    cutoff = now - _RATE_WINDOW_SECONDS
    with _rate_lock:
        ok_user = _book(f"{action}:user:{user_id}", limit, now, cutoff)
        ok_ip = _book(f"{action}:ip:{ip or 'unknown'}", limit, now, cutoff)
        return ok_user and ok_ip


def _reset_rate_limit_for_tests() -> None:
    """Reset process-local limiter state for isolated API tests."""
    with _rate_lock:
        _rate_buckets.clear()


# --------------------------------------------------------------------------- #
# one bounded upstream call
# --------------------------------------------------------------------------- #
def _json_body(raw: bytes | None) -> object:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:  # noqa: BLE001 — an HTML error page is "no readable body"
        return None


def _upstream(method: str, url: str, *, headers: dict, payload: object = None) -> tuple[int, object]:
    """One bounded call. Returns ``(status, parsed_body_or_None)``; raises ``_Busy``/``_NoAnswer``.

    An upstream 4xx/5xx is a RESULT, not an exception: ``urllib`` raises ``HTTPError`` for
    it, and this function turns it back into a status so each route can decide the
    plain-word sentence for that case. Only "nobody answered" leaves as an exception.
    """
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, method=method, data=data, headers=dict(headers))
    if not _UPSTREAM_SEM.acquire(blocking=False):
        log.warning("account action shed: %d upstream calls already in flight", _UPSTREAM_LIMIT)
        raise _Busy()
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            status = int(getattr(resp, "status", None) or resp.getcode())
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        # Upstream ANSWERED and refused. Only the status is logged: the URL carries the
        # project reference and the headers carry the caller's token.
        status = int(exc.code)
        try:
            raw = exc.read()
        except Exception:  # noqa: BLE001 — an unreadable error body is still an answer
            raw = b""
    except Exception as exc:  # noqa: BLE001 — timeout/DNS/TLS/reset: nobody answered
        log.warning("account action upstream failed: %s", type(exc).__name__)
        raise _NoAnswer() from None
    finally:
        _UPSTREAM_SEM.release()
    return status, _json_body(raw)


def _error_text(body: object) -> str:
    """Lower-cased classification text out of an upstream error body. NEVER shown to a user.

    Supabase Auth and PostgREST disagree on which key holds the reason (``msg``, ``error``,
    ``error_description``, ``message``, ``code``), so all of them are folded into one
    haystack that the classifiers below grep for keywords. The upstream wording itself never
    reaches a response body: it can carry an enum, an email address or a column name.
    """
    if not isinstance(body, dict):
        return ""
    parts = []
    for key in ("error_description", "error", "msg", "message", "code", "error_code"):
        value = body.get(key)
        if isinstance(value, str):
            parts.append(value)
    return " ".join(parts).lower()


def _auth_headers(token: str) -> dict:
    """The caller's own token on Authorization; the publishable key only names the project."""
    return {"Authorization": f"Bearer {token}", "apikey": _anon_key(),
            "Content-Type": "application/json"}


def _classify_password(text: str) -> str:
    if "rate limit" in text or "too many requests" in text:
        return "rate_limited"
    if "weak" in text or "min length" in text or "at least" in text or "password_min" in text:
        return "password_weak"
    if "same as" in text or "old password" in text or "different from the old" in text:
        return "password_same"
    return "password_refused"


def _classify_email(text: str) -> str:
    if "rate limit" in text or "too many requests" in text:
        return "rate_limited"
    if "same as" in text or "current email" in text or "already your email" in text:
        return "email_same"
    if "already registered" in text or "already exists" in text or "user already" in text:
        return "email_taken"
    return "email_refused"


def _email_shape_ok(value: str) -> bool:
    """The syntactic check spec R2 names: one ``@``, a dot in the domain, at most 254 chars.

    Deliberately syntax, not deliverability — we do not resolve MX records and we do not
    guess a provider's rules. Supabase Auth is the authority on whether the address can
    receive the confirmation link, and its refusal comes back as a plain-word 400.
    """
    if not value or len(value) > 254 or value.count("@") != 1:
        return False
    if any(ch.isspace() for ch in value):
        return False
    local, _, domain = value.partition("@")
    if not local or not domain or "." not in domain:
        return False
    return not (domain.startswith(".") or domain.endswith(".") or ".." in domain)


def _user_id_or_none(user: dict) -> str:
    value = user.get("id")
    return value if isinstance(value, str) and value else ""


# --------------------------------------------------------------------------- #
# routes
# --------------------------------------------------------------------------- #
@router.post("/api/account/password")
def change_password(request: Request, body: PasswordRequest | None = None,
                    authorization: str | None = Header(default=None),
                    user: dict = Depends(_current_user)) -> JSONResponse:
    """Change the caller's own password via Supabase Auth with the caller's own token.

    Body ``{password}``; 8-72 characters or a plain-word 400. The 72 ceiling is bcrypt's
    input limit — a longer secret is silently truncated by the hash, so it is refused here
    instead of being stored as something other than what the user typed.
    """
    uid = _user_id_or_none(user)
    if not uid:
        return _err(401, "no_identity")
    password = (body.password if body else None) or ""
    if not password:
        return _err(400, "password_missing")
    if len(password) < 8:
        return _err(400, "password_short")
    if len(password) > 72:
        return _err(400, "password_long")
    token = extract_bearer(authorization)
    if not token:
        return _err(401, "no_identity")
    if not _allow("password", uid, _client_ip(request)):
        return _err(429, "rate_limited")

    url, _service_key = _supabase()
    if not url:
        return _err(502, "no_answer")
    try:
        status, upstream_body = _upstream(
            "PUT", f"{url}/auth/v1/user", headers=_auth_headers(token),
            payload={"password": password})
    except _Busy:
        return _err(503, "busy")
    except _NoAnswer:
        return _err(502, "no_answer")
    if status == 200:
        log.info("account password changed for %s", _digest(uid))
        return _ok()
    if status >= 500:
        log.warning("account password upstream HTTP %s for %s", status, _digest(uid))
        return _err(502, "no_answer")
    log.warning("account password refused upstream HTTP %s for %s", status, _digest(uid))
    if status in (401, 403):
        return _err(401, "session_expired")
    return _err(400, _classify_password(_error_text(upstream_body)))


@router.post("/api/account/email")
def change_email(request: Request, body: EmailRequest | None = None,
                 authorization: str | None = Header(default=None),
                 user: dict = Depends(_current_user)) -> JSONResponse:
    """START an email change: Supabase mails the confirmation link(s), nothing moves yet.

    Body ``{email}``. A successful answer is ``{ok:true, confirmation_required:true}``
    because the address on the account does not change until the reader clicks that link —
    ``templates/account.js`` prints its own "confirmation link sent" sentence for exactly
    this flag, so the panel never claims a change that has not happened.
    """
    uid = _user_id_or_none(user)
    if not uid:
        return _err(401, "no_identity")
    email = ((body.email if body else None) or "").strip()
    if not email:
        return _err(400, "email_missing")
    if not _email_shape_ok(email):
        return _err(400, "email_invalid")
    token = extract_bearer(authorization)
    if not token:
        return _err(401, "no_identity")
    if not _allow("email", uid, _client_ip(request)):
        return _err(429, "rate_limited")

    url, _service_key = _supabase()
    if not url:
        return _err(502, "no_answer")
    try:
        status, upstream_body = _upstream(
            "PUT", f"{url}/auth/v1/user", headers=_auth_headers(token),
            payload={"email": email})
    except _Busy:
        return _err(503, "busy")
    except _NoAnswer:
        return _err(502, "no_answer")
    if status == 200:
        log.info("account email change started for %s", _digest(uid))
        return _ok({"confirmation_required": True})
    if status >= 500:
        log.warning("account email upstream HTTP %s for %s", status, _digest(uid))
        return _err(502, "no_answer")
    log.warning("account email refused upstream HTTP %s for %s", status, _digest(uid))
    if status in (401, 403):
        return _err(401, "session_expired")
    return _err(400, _classify_email(_error_text(upstream_body)))


@router.post("/api/account/signout-everywhere")
def signout_everywhere(request: Request,
                       authorization: str | None = Header(default=None),
                       user: dict = Depends(_current_user)) -> JSONResponse:
    """End EVERY session of this user: ``POST /auth/v1/logout?scope=global``, caller's token.

    No body. Upstream 204 (its normal answer) and 200 both mean the sessions are gone. The
    panel then clears its own local session — this route does not sign anybody out of this
    request, and it cannot: it never sees a refresh token.
    """
    uid = _user_id_or_none(user)
    if not uid:
        return _err(401, "no_identity")
    token = extract_bearer(authorization)
    if not token:
        return _err(401, "no_identity")
    if not _allow("signout-everywhere", uid, _client_ip(request)):
        return _err(429, "rate_limited")

    url, _service_key = _supabase()
    if not url:
        return _err(502, "no_answer")
    try:
        status, _logout_body = _upstream(
            "POST", f"{url}/auth/v1/logout?scope=global", headers=_auth_headers(token))
    except _Busy:
        return _err(503, "busy")
    except _NoAnswer:
        return _err(502, "no_answer")
    if status in (200, 204):
        log.info("account signed out everywhere for %s", _digest(uid))
        return _ok()
    if status >= 500:
        log.warning("account logout upstream HTTP %s for %s", status, _digest(uid))
        return _err(502, "no_answer")
    log.warning("account logout refused upstream HTTP %s for %s", status, _digest(uid))
    if status in (401, 403):
        # require_user can serve a cached identity for up to its TTL, so a token that was
        # valid on the way in can already be dead upstream. Say so plainly.
        return _err(401, "session_expired")
    return _err(400, "signout_refused")


# --------------------------------------------------------------------------- #
# deletion intake (Terminal migration 0016: public.account_lifecycle_requests)
# --------------------------------------------------------------------------- #
def _receipt_code(now: datetime | None = None) -> str:
    """``MMX-DEL-YYYYMMDD-XXXXXXXX`` — the Terminal intake's shape, 8 Crockford base32 chars.

    ``secrets``, not ``random``: a receipt code is a lookup key a support agent will be
    given over email, so it must not be guessable from the ones already issued.
    """
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%d")
    tail = "".join(secrets.choice(_CROCKFORD) for _ in range(_RECEIPT_TAIL_LEN))
    return f"MMX-DEL-{stamp}-{tail}"


def _receipt_view(row: object) -> dict | None:
    """The three fields the panel shows, read from what the STORE echoed back — never local.

    Returns None when the row is not a dict or carries no usable receipt code: an
    unreadable confirmation is a failed intake (503), not a licence to report the code we
    happened to mint. That is the whole "no fabricated receipt" rule in one place.
    """
    if not isinstance(row, dict):
        return None
    code = row.get("receipt_code")
    if not isinstance(code, str) or not code:
        return None
    return {"receipt_code": code,
            "requested_at": row.get("requested_at"),
            "status": row.get("status")}


def _rest_headers(token: str, service_key: str, *, prefer: str | None = None) -> dict:
    """PostgREST headers, ``lib/team_membership.py``'s shape.

    SECURITY-CRITICAL: ``Authorization`` carries the CALLER'S OWN token so the database role
    PostgREST assumes is the caller's (``authenticated``, ``auth.uid() = user_id``) and the
    row-level policies ``account_lifecycle_select_own`` / ``account_lifecycle_insert_own``
    are what authorise the write. The service-role key rides on ``apikey`` only because
    Supabase's gateway requires SOME valid project key there; it does not elevate the role.
    Putting it on ``Authorization`` instead would bypass RLS entirely and is never done.
    """
    headers = {"apikey": service_key, "Authorization": f"Bearer {token}",
               "Accept": "application/json", "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _read_open_deletion(token: str, url: str, service_key: str, user_id: str) -> dict | None:
    """The caller's own open deletion row, or None. RLS-scoped by the caller's token."""
    query = (
        "account_lifecycle_requests?select=receipt_code,requested_at,status"
        f"&user_id=eq.{urllib.parse.quote(user_id, safe='')}"
        "&kind=eq.deletion&status=in.(received,in_progress)"
        "&order=requested_at.desc&limit=1"
    )
    status, body = _upstream("GET", f"{url}/rest/v1/{query}",
                             headers=_rest_headers(token, service_key))
    if status != 200 or not isinstance(body, list) or not body:
        return None
    return _receipt_view(body[0])


@router.post("/api/account/delete")
def request_deletion(request: Request, body: DeleteRequest | None = None,
                     authorization: str | None = Header(default=None),
                     user: dict = Depends(_current_user)) -> JSONResponse:
    """FILE a deletion request. Deletes nothing, updates nothing, removes nothing.

    Body ``{confirm}`` must equal the email on the caller's own identity record, compared
    case-insensitively — the same typed-confirmation the Terminal's own intake asks for, and
    the reason a stray click cannot file anything. The email is read from the verified
    identity, never from the request.

    ``{ok:true, already_open:false, receipt:{…}}`` on a 201 whose representation carries the
    code; ``{ok:true, already_open:true, receipt:{…}}`` when the partial unique index
    ``account_lifecycle_one_open_deletion`` refuses a second open request (PostgREST 409 /
    Postgres 23505) and the caller's own open row is read back to name the code they already
    hold. Everything else is a 503 that says nothing was filed.
    """
    uid = _user_id_or_none(user)
    if not uid:
        return _err(401, "no_identity")
    on_file = user.get("email")
    if not isinstance(on_file, str) or not on_file.strip():
        log.warning("account deletion refused: identity record carries no email for %s",
                    _digest(uid))
        return _err(400, "delete_no_email")
    confirm = ((body.confirm if body else None) or "").strip()
    if confirm.lower() != on_file.strip().lower():
        # Logged as a digest only. The attempted value is an email address, and an address
        # is never written to a log whether it belongs to this user or to somebody else.
        log.info("account deletion confirmation mismatch for %s", _digest(uid))
        return _err(400, "delete_confirm")
    token = extract_bearer(authorization)
    if not token:
        return _err(401, "no_identity")
    if not _allow("delete", uid, _client_ip(request)):
        return _err(429, "rate_limited")

    url, service_key = _supabase()
    if not url or not service_key:
        return _err(503, "delete_not_recorded")
    try:
        status, upstream_body = _upstream(
            "POST", f"{url}/rest/v1/account_lifecycle_requests",
            headers=_rest_headers(token, service_key, prefer="return=representation"),
            payload={"user_id": uid, "kind": "deletion", "status": "received",
                     "receipt_code": _receipt_code()})
    except _Busy:
        log.warning("account deletion shed for %s", _digest(uid))
        return _err(503, "delete_not_recorded")
    except _NoAnswer:
        log.warning("account deletion intake did not answer for %s", _digest(uid))
        return _err(503, "delete_not_recorded")

    if status == 201:
        row = upstream_body[0] if isinstance(upstream_body, list) and upstream_body else upstream_body
        receipt = _receipt_view(row)
        if receipt is None:
            # The store said 201 but did not echo a usable row. We will not report a code we
            # cannot confirm was stored, so this is an unrecorded intake, not a success.
            log.warning("account deletion 201 with unreadable representation for %s", _digest(uid))
            return _err(503, "delete_not_recorded")
        log.info("account deletion filed for %s (HTTP 201)", _digest(uid))
        return _ok({"already_open": False, "receipt": receipt})

    if status == 409:
        # account_lifecycle_one_open_deletion: this user already has one open request.
        try:
            receipt = _read_open_deletion(token, url, service_key, uid)
        except (_Busy, _NoAnswer):
            receipt = None
        if receipt is None:
            log.warning("account deletion 409 but no open row readable for %s", _digest(uid))
            return _err(503, "delete_not_recorded")
        log.info("account deletion already open for %s (HTTP 409)", _digest(uid))
        return _ok({"already_open": True, "receipt": receipt})

    log.warning("account deletion intake failed: HTTP %s for %s", status, _digest(uid))
    return _err(503, "delete_not_recorded")
