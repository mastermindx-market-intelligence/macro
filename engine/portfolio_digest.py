"""Change-triggered portfolio digest — the COMPOSER only (PSI §19.5, W6).

    compose_digest(previous, current, *, user_id, asof, population) -> dict | None

**THE SEND PATH IS OFF. That statement is DATED, and it was checked on 2026-09-13
against ``origin/main``.** This module composes a digest and returns it as data. It does
not import ``app.mailer``, does not open a socket, and contains no call that could
deliver anything to a human. No digest has ever reached a reader. ``send_path_status()``
returns the same statement as data so a caller or an ops surface reports the truth
instead of inferring it; only its ``en``/``zh`` fields may ever be rendered.

Why "off" and not merely "unwired by choice" — the seat ruling for this packet (W9
RATIFICATION row ``w9b_f08_12``) is conditional: wire the digest into the existing drain
*if the drain has a configured transport*, otherwise ship the dated honesty line and name
the missing transport once. The digest has no transport of its own and the existing drain
is not its home, so this is the honesty line and ``NEEDS_SEAT`` below names what is
missing.

Four reads support that. Three are IN-TREE and re-checkable on ``origin/main`` — a test
pins them. The fourth is a DEPLOYED fact this tree can document but never prove. Keep the
two apart: only the first three can be re-verified by reading the repo, so a reader who
wants to age the claim knows which leg needs a host and which needs a checkout.

* IN-TREE, and the load-bearing leg: nothing calls the composer. ``git grep -n
  "compose_digest" -- ':!tests/'`` returns this file alone, so no endpoint, job or script
  under ``app/``, ``engine/`` or ``scripts/`` composes a digest in order to hand it to
  anything. A send path with no caller cannot send, whatever the credentials say.
* IN-TREE: the predicate a future send would have to satisfy is
  ``app/mailer.py:126-133`` ``is_configured()`` — ``MAIL_SMTP_HOST`` + ``MAIL_SMTP_USER``
  + ``MAIL_SMTP_PASS`` + ``MAIL_FROM`` — and ``app/mailer.py:408-411`` returns
  ``'skipped_no_smtp'`` rather than mailing when it is false.
* IN-TREE: the existing drain is not a drop-in home even once enabled.
  ``engine/alert_delivery_drain.py``, reached via ``scripts/drain_alert_outbox.py``, moves
  transactional ``alert_fire`` rows out of ``public.alert_outbox``, while a digest is
  ``marketing`` class (see ``CLS``) and needs the suppression / digest opt-in /
  one-click-unsub leg that drain does not have. Its own code files a marketing row that
  reaches it under "a marketing-only ledger race that should never reach this
  transactional class in practice". ``ALERT_DRAIN_ENABLE=1``
  (``scripts/drain_alert_outbox.py:43-46``; ``app/deploy/README.md:361-363``, "Ships
  DORMANT … forces ``--dry-run`` (decisions only, no sends, no writes)") is THAT lane's
  flag and is **not** a precondition for this path: a digest is not an ``alert_fire`` row,
  so no value of that flag can ever send one. The same is true of the opus privacy/risk
  review ``app/deploy/README.md:363-365`` requires before the alert drain's live sends —
  it is scoped to that lane, has not been performed, and is not a substitute for the
  review a marketing-class digest send would owe in its own right.
* DEPLOYED, documented here but not provable from this tree: whether relay credentials
  are actually set lives in ``/etc/macro-api.env``, written from repo secrets by
  ``.github/workflows/deploy-api-secrets.yml:163``. The in-repo statement of record is
  ``docs/ops/email-support-setup.md:3`` — the estate "works today in **mail-off mode**" —
  with §4 (``:126``) spelling out what mail-off looks like and ``:71`` restating that
  ``is_configured()`` requires host + user + pass + from, a partial config counting as
  mail-off on purpose. Re-checking THIS clause means reading the deployed environment, not
  this checkout. What the digest would additionally owe before a first send is PSI §19.5
  gate 12 (``research/PORTFOLIO_SUPERINTELLIGENCE_MASTERPLAN_BY_FABLE.md:673``): opt-in →
  change → ONE email → one-click unsub honored, with mail-off degrading clean.

Wiring the nightly job — recipient resolution, the ``email_prefs`` digest opt-in, the
quiet-day/weekly-heartbeat schedule, suppression, the one-click unsub URL — therefore
remains the named follow-up (PSI §19.5 gate 12, "opt-in → change → ONE email → one-click
unsub honored"). Shipping the composer and the send path together would have put an
untested nightly job one config flag away from mailing real users; shipping the composer
alone is the reviewable half, and the half the diff engine needs to be proven against.

Layering law (the one ``engine/alert_delivery_drain.py`` cites this module for):
``engine/`` may not import ``app/``, so a future send path injects its send function at
the ``scripts/`` seam exactly as the alert drain does — it is never imported from here.

The deliberate structural consequence: because there is no mailer import ANYWHERE in
this module, no test of it — and no build step that imports it — can send mail. That is
enforced by construction rather than by discipline, and pinned by a test.

**Return contract.** ``None`` on a quiet day (no changes) — PSI §19.5: "a quiet day sends
NOTHING". Otherwise a dict carrying exactly the arguments a future send path needs:

    {"template", "cls", "idem_key", "subject", "title_en", "title_zh", "preheader",
     "eyebrow", "why_en", "why_zh", "blocks", "change_count"}

``blocks`` is already in ``app.mailer.render_email``'s block format, so the wiring job is
``html, text = mailer.render_email(d["title_en"], d["title_zh"], d["blocks"], …)`` — no
content decisions left to make at send time.

**Privacy (PSI §19.5 + the two-organisms law).** The composer receives snapshots, which
carry tickers and desk state and nothing else — no shares, no cost basis, no weights (see
engine/portfolio_changes). The ``idem_key`` is ``psi_digest:<user_id>:<asof>`` — the user
id and the date, which is what makes it idempotent per user-day, and it is the ONLY place
a user identifier appears. The composed body names holdings, so neither it nor the
snapshots may ever be logged; the send ledger records metadata only.

Descriptive, never prescriptive; bilingual EN+ZH throughout; no falsifier/refutation
vocabulary. The lines are the change engine's own, passed through verbatim.
"""
from __future__ import annotations

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
# The date the two claims below were checked against origin/main. An undated "not
# wired" is what LEDGER_MOVES #10 kept re-filing: a reader cannot age it, so it reads
# as either fresh or abandoned and gets re-investigated either way. Re-checking means
# re-running the three reads named in the module docstring and moving this date.
SEND_PATH_ASOF = "2026-09-13"

# Machine field. Never rendered — the sentences a person may be shown are the EN/ZH
# pair below, which carry no enum, no slug and no config name.
SEND_PATH_STATE = "off"

SEND_PATH_HONESTY_EN = (
    "Portfolio change digests are not being emailed yet. As of " + SEND_PATH_ASOF +
    ", nothing is emailed — the digest is written and then stops, and none has ever "
    "reached a reader. Two things are missing: the mail service it would be handed to "
    "has no delivery credentials set up, and switching delivery on still needs a privacy "
    "review that has not been done. Digests will reach readers once both are in place."
)

SEND_PATH_HONESTY_ZH = (
    "投资组合变化摘要目前还不会发送邮件。截至 " + SEND_PATH_ASOF +
    "，没有任何邮件会发出：摘要只会被写好，也从未有一封送到读者手中。还缺两件事："
    "接收摘要的邮件服务还没有配置发送凭据；开启投递还需要一次尚未完成的隐私审查。"
    "只有这两件事都办妥，摘要才会送到读者手中。"
)

# The ONE needs-seat line this packet owes (W9 RATIFICATION row w9b_f08_12): the digest's
# OWN missing transport, named concretely so the next reader does not redo the
# investigation. Engineer-facing — this string must never be rendered to a user. The alert
# lane's dormant flag is named only to be ruled off this path (review round 2 MAJOR-1):
# listing it as a precondition would hand a future lane a production enable this packet's
# OUT OF SCOPE forbids, for a flag that can never send a digest in any case.
NEEDS_SEAT = (
    "NEEDS_SEAT: the digest send path stays off until the digest has a transport of its "
    "own — MAIL_SMTP_HOST + MAIL_SMTP_USER + MAIL_SMTP_PASS + MAIL_FROM so "
    "app.mailer.is_configured() is true (today send() returns 'skipped_no_smtp'); a "
    "marketing-class leg the transactional drain does not have (suppression / email_prefs "
    "digest opt-in / one-click unsub — PSI §19.5 gate 12); and a privacy/risk review for "
    "mailing holdings-level content to real users. ALERT_DRAIN_ENABLE=1 is the alert "
    "lane's flag and is NOT a precondition here: scripts/drain_alert_outbox.py moves "
    "transactional alert_fire rows out of public.alert_outbox and a digest is not one, so "
    "this path needs its own scripts/ seam, exactly as that drain has its own."
)


def send_path_status() -> dict:
    """The send path's own answer to "does this digest actually go out?" — as data.

        {"state": "off", "asof": "2026-09-13", "en": <sentence>, "zh": <句子>}

    A caller that is about to hand a composed digest to something that mails people
    should read this first and surface ``en``/``zh`` rather than guess from the absence
    of an exception. ``state``/``asof`` are machine fields for branching and for aging
    the claim; only ``en``/``zh`` may be rendered, and they are the plain-language pair
    pinned by ``tests/test_portfolio_changes.py``.

    Pure and side-effect free: reading the status cannot deliver anything, which is the
    same construction guarantee the rest of this module relies on.
    """
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
