"""app/account_prefs.py — POST /api/account/prefs (SEE W3, masterplan R4).

``templates/account.js`` has been calling this route (debounced, on ``themechange`` and
``langchange``) since the account card shipped, and nothing implemented it server-side.
This is that implementation — the client is deployed, so the server matches the client:
a one-key body (``{"lang":"zh"}`` or ``{"theme":"dark"}``), fire-and-forget.

Two sinks, one request:

* **Supabase auth ``user_metadata``** — the durable home for a display preference, and
  what ``GET /api/account`` reads back so a signed-in visitor lands in their own theme and
  language on any device.
* **``email_prefs.lang``** — the mirror that makes single-language sends possible later
  without a migration (SEE-R4). Emails ship dual-language in v1; the column is the
  plumbing, filled now so it is populated when the switch is worth flipping.

Identity comes from the Bearer token ONLY (``app.main.require_user``, the same secretless
verification every authed route uses). Any ``user_id`` in the body is ignored — it is not
a field on the model and it is never read.

Analyst OS W3: the enum table and the GoTrue merge-write moved to ``lib/user_prefs.py``,
because the chat gateway now writes a preference too (``set_chat_preference`` — "answer
shorter from now on"). Two hand-rolled merge-writes is how one path clobbers the other's
key. This route keeps its own shape (400 with the offending field named, per-sink booleans,
the ``email_prefs`` mirror) and gains ``brain_depth`` on the body.
"""
from __future__ import annotations

import logging
import os
from uuid import UUID
from urllib.error import HTTPError
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr

from lib import user_prefs

log = logging.getLogger("macro.account_prefs")
router = APIRouter()

# Back-compat aliases: the value sets now live in lib/user_prefs.PREF_VALUES (one table,
# shared with the chat tool). Kept as names so nothing importing them breaks.
LANGS = user_prefs.PREF_VALUES["lang"]
THEMES = user_prefs.PREF_VALUES["theme"]
DEPTHS = user_prefs.PREF_VALUES["brain_depth"]


def _current_user(authorization: str | None = Header(default=None)) -> dict:
    """Lazy import mirrors app/billing.py::_current_user — no app.main import cycle."""
    from app.main import require_user  # noqa: PLC0415
    return require_user(authorization)


def _supabase() -> tuple[str, str]:
    from app import billing  # noqa: PLC0415 — one place owns these constants
    return billing.SUPABASE_URL, billing.SUPABASE_SERVICE_ROLE_KEY


def _write_user_metadata(user_id: str, patch: dict) -> bool:
    """Merge ``patch`` into the user's auth ``user_metadata``. False on any failure.

    Thin delegate to ``lib.user_prefs.write_user_prefs``. The cached identity
    record is never the merge base — the lib takes a fresh uncached admin GET
    immediately before the PUT and overlays only this writer's validated keys.
    ``app.billing``'s constants are injected so this process has one credential source.
    """
    if not user_id:
        return False
    return user_prefs.write_user_prefs(str(user_id), patch, supabase=_supabase())


def _mirror_email_lang(user_id: str, lang: str) -> bool:
    """Upsert ``email_prefs.lang``. False on any failure — the mirror is not load-bearing."""
    from app import billing  # noqa: PLC0415
    try:
        billing._pg(
            "POST", "email_prefs?on_conflict=user_id",
            body=[{"user_id": user_id, "lang": lang,
                   "updated_at": datetime.now(timezone.utc).isoformat()}],
            prefer="resolution=merge-duplicates,return=minimal",
        )
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("account_prefs: email_prefs mirror failed for %s (%s)",
                    user_id, type(exc).__name__)
        return False


class PrefsRequest(BaseModel):
    lang: str | None = Field(None, description="'en' | 'zh'")
    theme: str | None = Field(None, description="'light' | 'dark'")
    # Analyst OS W3: how many WORDS the chat answers with. Same evidence bar at every
    # setting — 'concise' buys a shorter answer, never a thinner-sourced one.
    brain_depth: str | None = Field(None, description="'concise' | 'standard' | 'deep'")
    # B-F08-1a: alert delivery preferences (MO-PAID-085, preferences half only).
    alert_email_optin: bool | str | None = Field(None, description="email alerts on/off")
    alert_categories: list[str] | None = Field(
        None, description="subset of user_prefs.ALERT_CATEGORIES")
    tz: str | None = Field(None, description="IANA zone, e.g. 'Asia/Hong_Kong'")
    quiet_hours: dict | str | None = Field(
        None,
        description="{'start':'HH:MM','end':'HH:MM'} or the literal string 'off' to clear "
                    "(quiet_hours is skipped-as-unchanged on a bare None like every other "
                    "field, so clearing needs its own sentinel — never {} )")


#: Plain-word 400 detail per rejected field (EN/ZH). Chairman plain-language law
#: 2026-09-06: never a machine string like "unknown tz 'Mars/Olympus'".
_FIELD_ERR: dict[str, tuple[str, str]] = {
    "tz": ("That time zone isn't one we know. Pick one from the list.",
           "无法识别该时区，请从列表中选择。"),
    "alert_categories": ("That isn't an alert type we send. Pick from the list.",
                          "这不是我们发送的提醒类型，请从列表中选择。"),
    "quiet_hours": ("Quiet hours need a start and an end time, like 22:00 and 07:00.",
                     "免打扰时段需要开始和结束时间，例如 22:00 与 07:00。"),
    "alert_email_optin": ("That setting is on or off — nothing else.",
                           "该设置只有开或关两种状态。"),
}
_DEFAULT_ERR = ("We don't recognise that choice.", "无法识别该选项。")
_EMPTY_BODY_ERR = (
    "Nothing to save. Send language, theme, answer length, or an alert setting.",
    "没有可保存的内容。请发送语言、主题、回答长度或一项提醒设置。",
)


def _field_error(key: str) -> dict:
    en, zh = _FIELD_ERR.get(key, _DEFAULT_ERR)
    return {"field": key, "en": en, "zh": zh}


@router.post("/api/account/prefs")
def save_prefs(body: PrefsRequest, user: dict = Depends(_current_user)) -> dict:
    """Store the caller's preferences. Body ``{lang?, theme?, brain_depth?}``; at least one.

    Returns ``{"ok", "prefs", "metadata", "email_prefs"}`` — the two booleans say which
    sinks actually took the write, so a partial failure is visible instead of silently
    reported as success. 400 on an unknown value; 502 only when NOTHING was stored.
    """
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(401, "no user id")

    # One validation loop over the lib's kind table — a value the lib would refuse is
    # rejected HERE, by name, so the client learns which field was wrong. quiet_hours'
    # wire sentinel for "clear" is the literal string "off" (see PrefsRequest docstring);
    # everything else skips a bare None as "don't change".
    patch: dict[str, Any] = {}
    response_prefs: dict[str, Any] = {}
    for key, raw in (("lang", body.lang), ("theme", body.theme),
                     ("brain_depth", body.brain_depth),
                     ("alert_email_optin", body.alert_email_optin),
                     ("alert_categories", body.alert_categories),
                     ("tz", body.tz),
                     ("quiet_hours", body.quiet_hours)):
        if raw is None:
            continue
        if key == "quiet_hours":
            if raw == "off":
                # Wire sentinel for "clear". Kept as the literal string through to the lib
                # writer (never bare None here) — the lib's own None-means-"don't touch"
                # convention would otherwise silently no-op this clear.
                patch[key] = "off"
                response_prefs[key] = None
                continue
            if not user_prefs.quiet_hours_shape_ok(raw):
                raise HTTPException(400, detail=_field_error(key))
            # Shape is valid; normalize_value may still legally collapse start==end to None
            # (a real clear, not a rejection) — route it through the same "off" sentinel.
            val = user_prefs.normalize_value(key, raw)
            patch[key] = val if val is not None else "off"
            response_prefs[key] = val
            continue
        val = user_prefs.normalize_value(key, raw)
        if val is None:
            raise HTTPException(400, detail=_field_error(key))
        patch[key] = val
        response_prefs[key] = val
    if not patch:
        en, zh = _EMPTY_BODY_ERR
        raise HTTPException(400, detail={"en": en, "zh": zh})

    # B-F08-1a freeze §8: alerts turned on with no IANA zone known -- neither sent on
    # this call nor already stored on a FRESH read -- get an explicit default. Main's
    # writer ignores the cached identity as merge base; #6907 wires apply_tz_default
    # onto that same fresh admin GET so a default cannot land over a zone we could not
    # see. The extra GET runs only when the gate could fire; a brain_depth-only save
    # still pays exactly one GET inside the writer (main seat R2).
    if patch.get("alert_email_optin") is True and "tz" not in patch:
        fresh_meta = user_prefs.fetch_user_metadata(str(user_id), supabase=_supabase())
        user_prefs.apply_tz_default(patch, fresh_meta)
        if "tz" in patch:
            response_prefs["tz"] = patch["tz"]

    stored = _write_user_metadata(str(user_id), patch)

    mirrored = False
    if "lang" in patch:
        mirrored = _mirror_email_lang(str(user_id), patch["lang"])

    if not stored and not mirrored:
        raise HTTPException(502, "could not save preferences, please try again")
    return {"ok": True, "prefs": response_prefs, "metadata": stored, "email_prefs": mirrored}


@router.get("/api/account/prefs")
def read_prefs(user: dict = Depends(_current_user)) -> dict:
    """Readback for the alert-preferences surface (B-F08-1a). Zero network — rides the
    already-verified record, same as ``lib.user_prefs.read_user_prefs`` everywhere else.

    ``unset`` names every stored-preference key that has never been written, so the client
    can render an honest default (browser tz, "nothing chosen yet") instead of a fabricated
    saved value — null disclosure, not a hidden empty state.
    """
    stored = user_prefs.read_user_prefs(user)
    return {
        "ok": True,
        "prefs": stored,
        "unset": [k for k in user_prefs.PREF_KEYS if k not in stored],
        "categories_available": list(user_prefs.ALERT_CATEGORIES),
    }

# Explicit portfolio-digest consent belongs in email_prefs, apart from display
# settings and alert mail. The current schema may lack the specific field.
class PortfolioDigestChoice(BaseModel):
    enabled: StrictBool
    # Explicit null means the client observed no email_prefs row. Omission cannot
    # authorize an enable; a server-side refresh would rebase an older intent.
    expected_revision: StrictStr | None = None
    # Optional assertion for a displayed account, never a caller-selected target.
    # It also fences an account switch while the browser awaits its auth token.
    expected_user_id: StrictStr | None = None

    model_config = ConfigDict(extra="forbid")


def _digest_actor(user: dict) -> str:
    uid = user.get("id")
    try:
        if not isinstance(uid, str) or str(UUID(uid)) != uid:
            raise ValueError
    except ValueError:
        raise HTTPException(401, "Authenticated account required") from None
    return uid


def _digest_pref_store(*args, **kwargs):
    from app import billing
    return billing._pg(*args, **kwargs)


def _digest_revision(value: object) -> str:
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise ValueError("invalid digest revision")
    return value


def _digest_pref_state(uid: str, rows: object) -> dict:
    if rows == []:
        return {"enabled": False, "marketing_opt_out": None, "revision": None}
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise ValueError("invalid preference response")
    row = rows[0]
    if (row.get("user_id") != uid or type(row.get("portfolio_digest_opt_in")) is not bool
            or type(row.get("marketing_opt_out")) is not bool):
        raise ValueError("unqualified preference row")
    revision = _digest_revision(row.get("portfolio_digest_revision"))
    return {"enabled": row["portfolio_digest_opt_in"],
            "marketing_opt_out": row["marketing_opt_out"], "revision": revision}


_DIGEST_PREF_FIELDS = "user_id,portfolio_digest_opt_in,marketing_opt_out,portfolio_digest_revision"
_DIGEST_PRIVATE = {"Cache-Control": "private, no-store"}


def _digest_client_state(uid: str, state: dict) -> dict:
    return {**state, "user_id": uid,
            "enrollment_available": os.environ.get("PORTFOLIO_DIGEST_ENROLLMENT_ENABLED") == "1"}


@router.get("/api/account/prefs/portfolio-digest")
def get_portfolio_digest_choice(response: Response, user: dict = Depends(_current_user)) -> dict:
    response.headers["Cache-Control"] = "private, no-store"
    uid = _digest_actor(user)
    try:
        rows = _digest_pref_store("GET", f"email_prefs?user_id=eq.{uid}&select={_DIGEST_PREF_FIELDS}")
        return _digest_client_state(uid, _digest_pref_state(uid, rows))
    except Exception:
        raise HTTPException(503, "Digest preference unavailable", headers=_DIGEST_PRIVATE) from None


@router.put("/api/account/prefs/portfolio-digest")
def set_portfolio_digest_choice(body: PortfolioDigestChoice, response: Response,
                                user: dict = Depends(_current_user)) -> dict:
    response.headers["Cache-Control"] = "private, no-store"
    uid = _digest_actor(user)
    if "expected_user_id" in body.model_fields_set:
        try:
            observed_uid = _digest_revision(body.expected_user_id)
        except (ValueError, TypeError, AttributeError):
            raise HTTPException(422, "Invalid observed account", headers=_DIGEST_PRIVATE) from None
        if observed_uid != uid:
            raise HTTPException(409, {"code": "digest_account_changed",
                                      "message": "Your signed-in account changed. Reload account settings."},
                                headers=_DIGEST_PRIVATE)
    expected = None
    if body.enabled:
        if os.environ.get("PORTFOLIO_DIGEST_ENROLLMENT_ENABLED") != "1":
            raise HTTPException(503, "Portfolio digest enrollment is off", headers=_DIGEST_PRIVATE)
        if "expected_revision" not in body.model_fields_set:
            raise HTTPException(409, "Refresh digest preference before enabling",
                                headers=_DIGEST_PRIVATE)
        if body.expected_revision is not None:
            try:
                expected = _digest_revision(body.expected_revision)
            except (ValueError, TypeError, AttributeError):
                raise HTTPException(422, "Invalid digest preference revision",
                                    headers=_DIGEST_PRIVATE) from None

    # One existing-owner atomic operation, without a fresh GET or any automatic
    # replay. Every negative request writes a new fence, even if already disabled.
    try:
        result = _digest_pref_store(
            "POST", "rpc/portfolio_digest_consent_set_v1",
            body={"p_user_id": uid, "p_enabled": body.enabled, "p_expected_revision": expected})
    except HTTPError as exc:
        detail = ("Digest preference change not applied" if exc.code in (401, 403)
                  else "Digest preference change unconfirmed")
        raise HTTPException(503, detail, headers=_DIGEST_PRIVATE) from None
    except Exception:
        # The mutation may have committed. A new GET cannot identify this attempt.
        raise HTTPException(503, "Digest preference change unconfirmed",
                            headers=_DIGEST_PRIVATE) from None

    try:
        if not isinstance(result, dict) or result.get("status") not in {"applied", "stale_revision"}:
            raise ValueError("unqualified mutation response")
        row = result.get("state")
        rows = [] if row is None and result["status"] == "stale_revision" else [row]
        state = _digest_pref_state(uid, rows)
        if result["status"] == "applied" and (
                state["enabled"] is not body.enabled or state["revision"] is None
                or (body.enabled and state["revision"] == expected)):
            raise ValueError("unconfirmed digest preference write")
    except Exception:
        raise HTTPException(503, "Digest preference change unconfirmed",
                            headers=_DIGEST_PRIVATE) from None

    state = _digest_client_state(uid, state)
    if result["status"] == "stale_revision":
        raise HTTPException(409, {"message": "Digest preference changed. Refresh before enabling.",
                                  "state": state}, headers=_DIGEST_PRIVATE)
    return state
