"""Pure change-triggered portfolio digest composer (PSI §19.5).

The composer returns bilingual content or None on a quiet day. It imports no
mailer and performs no I/O. The explicit, default-off job boundary lives in
scripts/deliver_portfolio_digest.py. Only that caller checks a specific user's
digest preference, resolves the recipient and passes a marketing message to
the existing ledger-first mailer. The shared transactional alert drain is a
separate path. The nightly snapshot cursor and authenticated opt-in are
runtime prerequisites. The presence of the caller does not establish either.

Snapshot inputs contain desk state, never money values. Do not log the digest
or snapshots. The mailer's metadata-only daily key is psi_digest:<user_id>:<asof>.
"""
from __future__ import annotations

import re

from engine.portfolio_changes import diff_snapshots

TEMPLATE = "psi_digest"
# Digests are recurring bulk mail, never transactional (PSI §19.5 consent rule): they
# consult suppression + opt-out, and they carry an unsubscribe slot.
CLS = "marketing"

# How many change lines the email itself renders. The rest are counted, not dropped —
# an email that silently truncates teaches the reader it is not complete.
MAX_LINES = 10

# --------------------------------------------------------------------------- #
# Send-path state (packet W9B_F08_12, MO-PAID-085 residual — the honesty fork)
# --------------------------------------------------------------------------- #
# Source observation only. Activation and delivery require separate evidence.
SEND_PATH_ASOF = "2026-11-02"

SEND_PATH_STATE = "off"

_REFUSAL_MONTHS_EN = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _plain_date(iso):
    """``"2026-09-13"`` → ``("13 Sep 2026", "2026年9月13日")``; unparseable → ``("", "")``.

    Local twin of ``engine.prophet_bridge._plain_date`` (prophet_bridge.py:1386) — the
    same plain-word date form the rest of the reader-facing copy uses, for the same
    doctrine reason (Law 2/Law 3: a date a reader reads at full precision, not an
    identifier). FAIL-SOFT by design — every caller drops its date clause on ``("", "")``
    rather than printing a wrong day, so a bad input cannot reach a reader.
    """
    match = re.match(r"\s*(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    if not match:
        return ("", "")
    year, month, day = (int(g) for g in match.groups())
    if not 1 <= month <= 12 or not 1 <= day <= 31:
        return ("", "")
    return (f"{day} {_REFUSAL_MONTHS_EN[month - 1]} {year}",
            f"{year}年{month}月{day}日")


_SEND_PATH_DATE_EN, _SEND_PATH_DATE_ZH = _plain_date(SEND_PATH_ASOF)

SEND_PATH_HONESTY_EN = (
    "As of " + _SEND_PATH_DATE_EN + ", portfolio change emails are off by default."
)
SEND_PATH_HONESTY_ZH = (
    "截至" + _SEND_PATH_DATE_ZH + "，投资组合变化邮件默认关闭。"
)

NEEDS_SEAT = (
    "NEEDS_SEAT: a real digest needs authenticated digest opt-in in email_prefs, "
    "a user-scoped snapshot cursor, configured marketing mail and privacy/risk review "
    "before activation. Real opt-in, one delivery and one-click opt-out require runtime evidence."
)


def send_path_status() -> dict:
    """Report the default source posture without inspecting a host or sending."""
    return {
        "state": SEND_PATH_STATE,
        "asof": SEND_PATH_ASOF,
        "en": SEND_PATH_HONESTY_EN,
        "zh": SEND_PATH_HONESTY_ZH,
    }


def idem_key(user_id: str, asof: str) -> str:
    """``psi_digest:<user_id>:<asof>`` — the per-user-day idempotency key (PSI §19.5).

    The mailer's ``email_log.idem_key`` is UNIQUE, so a re-run of the nightly job on the
    same asof returns 'duplicate' instead of mailing a second time. The frequency cap of
    1 digest/day is therefore enforced by the key's shape, not by the job remembering.
    """
    return f"{TEMPLATE}:{user_id}:{asof}"


def compose_digest(previous: dict, current: dict, *, user_id: str, asof: str,
                   population: str = "unspecified") -> dict | None:
    """Compose the digest for one user, or None when nothing changed.

    `previous` / `current` are state digests from engine.portfolio_changes.snapshot_state.
    A first visit (empty `previous`) produces no changes and therefore no email — a new
    reader is not mailed a wall of "new" on day one.
    """
    changes = diff_snapshots(previous, current)
    if not changes:
        return None

    n = len(changes)
    unit_en = "change" if n == 1 else "changes"
    # The population is named in the subject and the lede — the same A8 discipline the
    # brief carries. An email that says "your book" about a watchlist is the defect
    # arriving in the reader's inbox instead of on a page.
    if population == "positions":
        what_en, what_zh = "your book", "你的持仓"
    elif population == "watchlist_union":
        what_en, what_zh = "your watchlist", "你的观察列表"
    else:
        what_en, what_zh = "the names you follow", "你关注的标的"

    subject = f"{n} {unit_en} in {what_en} · {what_zh}有 {n} 项变化"

    blocks: list[dict] = [{
        "en": (f"Since the last digest, the desk's read changed on {n} {unit_en} in "
               f"{what_en}. Each line below is the desk's own wording, applied to the "
               f"names you follow."),
        "zh": (f"自上一封摘要以来，桌面对{what_zh}的判读出现 {n} 项变化。"
               f"以下每一行均为桌面自身的表述。"),
    }]

    shown = changes[:MAX_LINES]
    blocks.append({
        "kind": "kv",
        "en": [(c.get("ticker") or c.get("sector") or "Market", c["en"]) for c in shown],
        "zh": [(c.get("ticker") or c.get("sector") or "市场", c["zh"]) for c in shown],
    })

    extra = n - len(shown)
    if extra > 0:
        blocks.append({
            "kind": "fine",
            "en": (f"{extra} further {'change' if extra == 1 else 'changes'} are not "
                   f"listed here."),
            "zh": f"另有 {extra} 项变化未在此列出。",
        })

    blocks.append({
        "kind": "fine",
        "en": ("These are changes in what the desk reads, not instructions. Nothing here "
               "is a recommendation to trade."),
        "zh": "以上为桌面判读的变化，并非操作指示，也不构成任何交易建议。",
    })

    return {
        "template": TEMPLATE,
        "cls": CLS,
        "idem_key": idem_key(user_id, asof),
        "subject": subject,
        "title_en": f"{n} {unit_en} in {what_en}",
        "title_zh": f"{what_zh}有 {n} 项变化",
        "preheader": "What the desk changed its read on since the last digest.",
        "eyebrow": "DIGEST",
        "why_en": ("You received this because you turned on change digests for the names "
                   "you follow."),
        "why_zh": "你收到这封邮件，是因为你为关注的标的开启了变化摘要。",
        "blocks": blocks,
        "change_count": n,
    }
