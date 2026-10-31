"""engine/marketing/persona_memory.py — per-persona memory stores (XG-W3).

Three stores per account, under `data/marketing/personas/<id>/`:

  promises.jsonl  open loops with due conditions — every promise closed or
                  explicitly released (constitution §11.6: "An open loop without
                  a follow-up trains distrust")
  phrases.jsonl   one record per EMITTED POST, which is what makes the XG-W1
                  per-quirk frequency caps enforceable across days
  relations.jsonl public interaction context per author handle — topics, stage,
                  last contact. NOTHING SENSITIVE INFERRED (constitution §10
                  relationship-memory law, charter §4).

`theses.jsonl` (the opinion ledger) already exists as a declared path in every
persona spec and is graded by the forward-ledger machinery; this module does not
touch it.

THE NIGHTLY-SOLE-ADVANCER LAW (charter §2 amendment 13).  Emission-time counters
accumulate in HOST state — zero tracked-repo writes intraday, the same posture as
the daemon's `items-host.jsonl` spool and the poller cursors. A nightly
consolidator is the ONLY writer of the tracked ledgers. Concretely:

    data/marketing/personas_host/<id>/*.jsonl   gitignored, appended intraday
    data/marketing/personas/<id>/*.jsonl        tracked, advanced by consolidate()

The split is not decorative. The VPS daemon runs inside a checkout that `git
pull`s every 3 minutes; an intraday writer touching a tracked file collides with
that pull and with the render lane's resets. `tests/test_marketing_desk_feeds.py`
carries an AST guard (modelled on XG-W2's hand-rolled-writer guard) asserting
that `consolidate()` is the only code path that opens a write handle under the
tracked directory — a RENAMED intraday writer has to fail it too.

WHY phrases.jsonl STORES POST TEXT.  `expression_dial.frequency_violations(text,
*, codex, as_of, recent)` re-runs each marker's own pattern over `recent`, where
recent is `[{"text": ..., "date": "YYYY-MM-DD"}, ...]`. It returns `[]` when
`recent` is empty — so before this module existed, `max_per_day` / `max_share_7d`
were declared-but-unenforced beyond a single batch (`copywriter.py` says so in
its own comment). Storing the emitted text is what arms them. Derived n-grams
ride along for topic-fatigue diagnostics; they are NOT the cap mechanism, because
re-deriving a marker from an n-gram would duplicate the codex's patterns and the
two copies would drift.

THE CROSS-HOST RECONCILIATION (closes the XG-W3 review's F11).  The split above
is correct but it was not complete: the spool is host-local, and publication is
not.  `scripts/marketing_publisher` writes two things on ONE `if receipt.ok:`
branch, forty lines apart, with opposite durability — the publication receipt to
`data/marketing/publications.jsonl`, which `marketing-publish.yml` commits back
to git so every host sees it, and the memory record to `personas_host/`, which
`.gitignore` excludes so no host but the writer ever sees it.  The publisher runs
on `macstudio-light`, this consolidator on `macstudio`, the reply desk on the
VPS; each has its own checkout.  A post shipped by one host was therefore
invisible to the ledger advanced by another, and SILENTLY so, because an absent
spool and an idle host leave identical evidence.  Measured on main 2026-09-18:
1,138 live publications over 46 days and 7 accounts, and `data/marketing/personas/`
did not exist at all — every per-quirk frequency cap was reading an empty store.

`reconcile_publications()` closes it by JOINING the two ledgers that already
cross hosts, adding no transport of its own: the publication receipt says what
shipped, the shared outbox says what its copy was, and `sha256(text)` must equal
the receipt's `effective_copy_hash` before a record is admitted.  Records are
minted through the same `_phrase_record` constructor the live path uses, so a
recovered post carries the same identity as a spooled one and folds to a single
record.  It is a lookback, not a watermark — nothing is consumed or deleted, a
missed night self-heals, and anything unresolvable is REPORTED rather than
quietly read as "no publication".  `phrases` is what a per-post receipt can
reach; `promises` and `relations` are named as unreconciled in the report.

Public API:
    recent_posts(account, *, now, days=7, root=None)   -> list[{text, date}]
    record_post(account, text, *, now, ...)            -> dict     (host write)
    open_promises(account, *, now=None, root=None)     -> list[dict]
    record_promise(account, text, *, due_condition, now, ...) -> dict (host)
    close_promise(account, promise_id, *, now, outcome, ...)  -> dict (host)
    relations(account, *, root=None)                   -> dict[handle, dict]
    record_relation(account, handle, *, now, topics=(), stage="") -> dict (host)
    ngram_fatigue(account, *, now, days=7, n=3, root=None) -> dict[str, int]
    reconcile_publications(*, now, root=None, ...)     -> (rows_by_account, report)
    consolidate(*, now, root=None, accounts=None)      -> dict  (THE ONLY tracked writer)
    host_dir(root, account) / repo_dir(root, account)
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

__all__ = [
    "STORES",
    "RELATION_STAGES",
    "host_dir",
    "repo_dir",
    "recent_posts",
    "record_post",
    "open_promises",
    "record_promise",
    "close_promise",
    "relations",
    "record_relation",
    "ngram_fatigue",
    "reconcile_publications",
    "publications_path",
    "consolidate",
]

#: The three stores this module owns. `theses.jsonl` is deliberately absent —
#: the opinion ledger is graded by the existing forward-ledger machinery and a
#: second writer would race it.
STORES: tuple[str, ...] = ("promises", "phrases", "relations")

#: Relationship stages (constitution §9.2 target tiers, reused). A closed
#: vocabulary because "stage" is the only judgment this store holds, and a
#: free-text stage would be an invitation to infer something about a person.
RELATION_STAGES: frozenset[str] = frozenset({"", "cold", "engaged", "reciprocal", "declined"})

#: How much history the tracked ledgers keep. The caps that consume this store
#: look back 7 days (expression_dial.SHARE_WINDOW_DAYS); 90 days leaves ample
#: room for the XG-W6 diagnostics without unbounded growth in a tracked file.
RETENTION_DAYS: int = 90

_DAY_FMT = "%Y-%m-%d"

#: The SHARED publication receipt ledger — the cross-host half of the pair this
#: module reconciles against (see THE CROSS-HOST RECONCILIATION in the module
#: docstring). Written by `scripts/marketing_publisher._append_publication` on
#: the same `if receipt.ok:` branch that calls `record_post`, and committed back
#: to git by `.github/workflows/marketing-publish.yml`
#: ("git add data/marketing/publications.jsonl").
#: `tests/test_marketing_persona_cross_host.py` pins this against the
#: publisher's own `_PUBLICATIONS_REL` so the two spellings cannot drift apart.
_PUBLICATIONS_REL: tuple[str, ...] = ("data", "marketing", "publications.jsonl")

#: Only a LIVE post shipped. A dry-run row records what WOULD have gone out, and
#: charging a frequency cap for copy nobody ever saw would be a fabricated
#: memory — strictly worse than the undercount this reconciliation repairs.
_LIVE_MODE = "live"


# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────
def _root_path(root: Path | str | None) -> Path:
    if root is None:
        return Path(__file__).resolve().parent.parent.parent
    return Path(root)


def repo_dir(root: Path | str | None, account: str) -> Path:
    """The TRACKED ledger dir. Only `consolidate()` may write here."""
    return _root_path(root) / "data" / "marketing" / "personas" / str(account)


def host_dir(root: Path | str | None, account: str) -> Path:
    """The GITIGNORED intraday spool dir (see `.gitignore`).

    Mirrors `outbox._host_items_path`'s posture: a gitignored sibling, not a
    filesystem-external path, so a developer can inspect it and the daemon can
    write it without dirtying the checkout.
    """
    return _root_path(root) / "data" / "marketing" / "personas_host" / str(account)


def _store_path(base: Path, store: str) -> Path:
    if store not in STORES:
        raise ValueError(f"unknown store {store!r}; allowed: {sorted(STORES)}")
    return base / f"{store}.jsonl"


def publications_path(root: Path | str | None = None) -> Path:
    """The SHARED publication receipt ledger (tracked, committed, cross-host)."""
    return _root_path(root).joinpath(*_PUBLICATIONS_REL)


# ─────────────────────────────────────────────────────────────────────────────
# JSONL I/O — fail-soft on read, atomic on write
# ─────────────────────────────────────────────────────────────────────────────
def _read_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file, skipping unparseable lines.

    Fail-soft: a half-written final line (the daemon killed mid-append) must not
    blind a guard to the 400 good records above it.
    """
    out: list[dict] = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if isinstance(rec, dict):
                    out.append(rec)
    except FileNotFoundError:
        return []
    except OSError:
        return []
    return out


def _append_host(root: Path | str | None, account: str, store: str, rec: dict) -> dict:
    """Append one record to the HOST spool. The only write path used intraday."""
    d = host_dir(root, account)
    path = _store_path(d, store)
    d.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    return rec


def _write_tracked(path: Path, rows: Sequence[dict]) -> None:
    """Atomic replace of a TRACKED ledger. Called ONLY by `consolidate()`.

    Kept as a single private helper so the AST guard has exactly one symbol to
    allowlist, and so a second tracked writer cannot appear by accident.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".pm-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _read_union(root: Path | str | None, account: str, store: str) -> list[dict]:
    """Tracked ledger PLUS the host spool.

    Readers always see the union — exactly like `outbox.read_items_all`. This is
    load-bearing: a cap that ignored today's un-consolidated posts would let an
    account spend its whole daily quirk budget between two nightlies.
    """
    return _read_jsonl(_store_path(repo_dir(root, account), store)) + _read_jsonl(
        _store_path(host_dir(root, account), store)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Time helpers
# ─────────────────────────────────────────────────────────────────────────────
def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _day_of(rec: dict) -> str:
    """The record's calendar day, preferring an explicit `date`."""
    d = str(rec.get("date") or "").strip()
    if d:
        return d[:10]
    at = str(rec.get("at") or "").strip()
    return at[:10]


def _parse_day(s: str) -> datetime | None:
    try:
        return datetime.strptime(str(s)[:10], _DAY_FMT).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _record_key(store: str, rec: dict) -> str:
    """A stable identity for dedup at consolidation.

    Explicit `id` wins; otherwise a hash of the fields that make the record what
    it is. Without this, a consolidator re-run (a retried nightly) would double
    every counter and silently tighten every cap.
    """
    rid = str(rec.get("id") or "").strip()
    if rid:
        return rid
    if store == "phrases":
        # (DATE, text) — NOT (at, text) (review F9). The `at` timestamp is
        # wall-clock at write, so a plan-build re-run that re-emits the same
        # post a minute later produces a DIFFERENT key and the record survives
        # dedup twice. Two copies of one post inflate both the numerator and
        # the denominator of `max_share_7d` and double-count `max_per_day` —
        # i.e. a retried run would silently TIGHTEN the caps it is supposed to
        # measure. The business day plus the text is the post's real identity.
        basis = f"{_day_of(rec)}|{rec.get('text','')}"
    elif store == "relations":
        basis = f"{rec.get('handle','')}|{rec.get('at','')}"
    else:
        basis = f"{rec.get('at','')}|{rec.get('text','')}"
    return hashlib.sha1(basis.encode("utf-8", "replace")).hexdigest()[:16]


# ─────────────────────────────────────────────────────────────────────────────
# phrases.jsonl — the store that arms the quirk caps
# ─────────────────────────────────────────────────────────────────────────────
_WORD_RE = re.compile(r"[a-z0-9']+")


def _ngrams(text: str, n: int = 3) -> list[str]:
    """Lowercased word n-grams, for topic/phrase fatigue diagnostics."""
    words = _WORD_RE.findall(str(text).lower())
    if len(words) < n:
        return []
    return [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)]


def record_post(
    account: str,
    text: str,
    *,
    now: datetime,
    as_of: str = "",
    franchise: str = "",
    kind: str = "",
    item_id: str = "",
    root: Path | str | None = None,
) -> dict:
    """Record an EMITTED post into the host spool (intraday).

    `text` should be the full emitted copy (`headline + " " + body`), because
    that is what `expression_dial.frequency_violations` re-scans for markers.

    DAY BASIS MUST MATCH THE EVALUATOR (review F18). The caps are evaluated by
    `frequency_violations(..., as_of=<business date>, recent=[{date: ...}])`,
    which compares each record's `date` against the item's `as_of` — the
    CONTENT PLAN's business date, not a wall clock. Storing a UTC-derived date
    here would put the two on different calendars: Cici's 08:00 Hong Kong post
    is still the previous UTC day, so her second signature opener of the HK
    morning would land on a different `date` than the plan's `as_of` and slip
    the ≤1/day cap entirely. When the caller knows the business date it wins;
    `now` is only the fallback.
    """
    rec = _phrase_record(
        account, text, at=_as_utc(now), as_of=as_of,
        franchise=franchise, kind=kind, item_id=item_id, source="emit",
    )
    return _append_host(root, account, "phrases", rec)


def _phrase_day(as_of: str, at: datetime) -> str:
    """The record's business day — the ONE definition, used by both writers.

    THIS IS THE EXACTLY-ONCE HINGE. `_record_key("phrases", ...)` hashes
    `date|text`, so a reconciled record that derives its day differently from
    the live one gets a DIFFERENT id and survives dedup as a second copy of a
    post that shipped once — inflating both sides of `max_share_7d` and doubling
    `max_per_day`, i.e. silently TIGHTENING the caps this store exists to
    measure. Measured on the real ledger (2026-09-18): 63 of 1,138 live
    publications carry an `as_of` business day that differs from their
    `published_at` wall-clock day, so a reconciler that reached for the
    publication timestamp would have double-counted every one of them.
    """
    return str(as_of or "").strip()[:10] or at.strftime(_DAY_FMT)


def _phrase_record(
    account: str,
    text: str,
    *,
    at: datetime,
    as_of: str = "",
    franchise: str = "",
    kind: str = "",
    item_id: str = "",
    source: str = "emit",
) -> dict:
    """Shape one phrases record. The SOLE constructor, for the reason above.

    `source` is provenance, never identity: it records HOW the post reached
    memory — "emit" (written by the publisher at posting success) or
    "reconciled" (recovered from the shared publication receipt ledger because
    the emitting host's spool never reached this consolidator). It is
    deliberately absent from `_record_key`, so the same post seen both ways
    folds to one record rather than two.
    """
    rec = {
        "account": str(account),
        "at": _as_utc(at).isoformat(),
        "date": _phrase_day(as_of, _as_utc(at)),
        "text": str(text),
        "franchise": str(franchise or ""),
        "kind": str(kind or ""),
        "item_id": str(item_id or ""),
        "ngrams": _ngrams(text),
        "source": str(source or "emit"),
    }
    rec["id"] = _record_key("phrases", rec)
    return rec


def recent_posts(
    account: str,
    *,
    now: datetime,
    days: int = 7,
    root: Path | str | None = None,
) -> list[dict]:
    """The `recent` argument `expression_dial.frequency_violations` wants.

    Returns `[{"text": str, "date": "YYYY-MM-DD"}, ...]` for the trailing
    `days` window, oldest-first. This is THE wiring that turns the XG-W1
    per-quirk caps (`max_per_day`, `max_per_7d`, `max_share_7d`) from declared
    numbers into enforced ones — `frequency_violations` returns `[]` on an empty
    `recent`, so an account with no store is simply uncapped, exactly as it was
    before this module.
    """
    cutoff = (_as_utc(now) - timedelta(days=days)).strftime(_DAY_FMT)
    rows = _read_union(root, account, "phrases")
    out: list[dict] = []
    seen: set[str] = set()
    for r in rows:
        day = _day_of(r)
        if not day or day < cutoff:
            continue
        key = _record_key("phrases", r)
        if key in seen:
            continue
        seen.add(key)
        out.append({"text": str(r.get("text") or ""), "date": day})
    out.sort(key=lambda x: x["date"])
    return out


def ngram_fatigue(
    account: str,
    *,
    now: datetime,
    days: int = 7,
    n: int = 3,
    root: Path | str | None = None,
    min_count: int = 2,
) -> dict[str, int]:
    """Rolling n-gram counts over the window — the anti-sameness diagnostic.

    Distinct from the quirk caps: those police WHITELISTED signatures against
    their declared budget; this surfaces UNDECLARED repetition (the same stock
    phrase three days running). Feeds the `topic_overused` abstention reason.
    """
    cutoff = (_as_utc(now) - timedelta(days=days)).strftime(_DAY_FMT)
    counts: dict[str, int] = {}
    seen: set[str] = set()
    for r in _read_union(root, account, "phrases"):
        day = _day_of(r)
        if not day or day < cutoff:
            continue
        key = _record_key("phrases", r)
        if key in seen:
            continue
        seen.add(key)
        grams = r.get("ngrams")
        if not isinstance(grams, list) or (n != 3):
            grams = _ngrams(r.get("text") or "", n)
        for g in grams:
            g = str(g)
            counts[g] = counts.get(g, 0) + 1
    return {g: c for g, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])) if c >= min_count}


# ─────────────────────────────────────────────────────────────────────────────
# promises.jsonl — open loops
# ─────────────────────────────────────────────────────────────────────────────
def record_promise(
    account: str,
    text: str,
    *,
    due_condition: str,
    now: datetime,
    due_by: str = "",
    franchise: str = "",
    item_id: str = "",
    root: Path | str | None = None,
) -> dict:
    """Open a loop. `due_condition` is mandatory and non-empty by design.

    Constitution §11.6: a promise without a condition cannot be closed, and an
    unclosable promise is precisely the thing that trains distrust. An empty
    condition raises rather than silently recording an unfollowable loop.
    """
    cond = str(due_condition or "").strip()
    if not cond:
        raise ValueError("due_condition is required — an open loop needs a closing condition")
    at = _as_utc(now)
    rec = {
        "account": str(account),
        "at": at.isoformat(),
        "date": at.strftime(_DAY_FMT),
        "text": str(text),
        "due_condition": cond,
        "due_by": str(due_by or ""),
        "franchise": str(franchise or ""),
        "item_id": str(item_id or ""),
        "status": "open",
    }
    rec["id"] = _record_key("promises", rec)
    return _append_host(root, account, "promises", rec)


def close_promise(
    account: str,
    promise_id: str,
    *,
    now: datetime,
    outcome: str = "",
    released: bool = False,
    root: Path | str | None = None,
) -> dict:
    """Close (or explicitly RELEASE) an open loop.

    A release is a first-class outcome, not a failure: the constitution asks for
    "every promise closed or explicitly released", and a condition that stopped
    being relevant deserves an honest release rather than a silent drop.
    Recorded as a new host record; `consolidate()` folds status onto the id.
    """
    at = _as_utc(now)
    rec = {
        "account": str(account),
        "at": at.isoformat(),
        "date": at.strftime(_DAY_FMT),
        "id": str(promise_id),
        "status": "released" if released else "closed",
        "closed_at": at.isoformat(),
        "outcome": str(outcome or ""),
    }
    return _append_host(root, account, "promises", rec)


def _fold_promises(rows: Iterable[dict]) -> dict[str, dict]:
    """Fold append-only promise records into current state, by id."""
    state: dict[str, dict] = {}
    for r in sorted(rows, key=lambda x: str(x.get("at") or "")):
        pid = str(r.get("id") or _record_key("promises", r))
        if pid in state:
            cur = dict(state[pid])
            cur.update({k: v for k, v in r.items() if v not in (None, "")})
            state[pid] = cur
        else:
            state[pid] = dict(r)
    return state


def open_promises(
    account: str,
    *,
    now: datetime | None = None,
    root: Path | str | None = None,
) -> list[dict]:
    """Every still-open loop, oldest-first, with `overdue` stamped when due_by passed."""
    state = _fold_promises(_read_union(root, account, "promises"))
    out = [r for r in state.values() if str(r.get("status") or "open") == "open"]
    if now is not None:
        today = _as_utc(now).strftime(_DAY_FMT)
        for r in out:
            due = str(r.get("due_by") or "")
            r["overdue"] = bool(due and due < today)
    out.sort(key=lambda r: str(r.get("at") or ""))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# relations.jsonl — public interaction context
# ─────────────────────────────────────────────────────────────────────────────
def record_relation(
    account: str,
    handle: str,
    *,
    now: datetime,
    topics: Sequence[str] = (),
    stage: str = "",
    root: Path | str | None = None,
) -> dict:
    """Record a PUBLIC interaction with an author handle.

    NOTHING SENSITIVE INFERRED (constitution §10, charter §4). The schema admits
    exactly three things — the handle, the public topics discussed, and a stage
    from a closed vocabulary. There is deliberately no field for demographics,
    affiliation, location, employer, or any inferred trait, so there is nowhere
    for one to be written even by a future careless caller. An out-of-vocabulary
    stage raises.
    """
    st = str(stage or "").strip().lower()
    if st not in RELATION_STAGES:
        raise ValueError(f"unknown relation stage {st!r}; allowed: {sorted(RELATION_STAGES)}")
    at = _as_utc(now)
    rec = {
        "account": str(account),
        "handle": str(handle).lstrip("@"),
        "at": at.isoformat(),
        "date": at.strftime(_DAY_FMT),
        "topics": [str(t) for t in topics],
        "stage": st,
    }
    rec["id"] = _record_key("relations", rec)
    return _append_host(root, account, "relations", rec)


def relations(account: str, *, root: Path | str | None = None) -> dict[str, dict]:
    """Fold interaction records into per-handle context: topics, stage, last contact."""
    out: dict[str, dict] = {}
    for r in sorted(_read_union(root, account, "relations"), key=lambda x: str(x.get("at") or "")):
        h = str(r.get("handle") or "").lstrip("@")
        if not h:
            continue
        cur = out.setdefault(h, {"handle": h, "topics": [], "stage": "", "last_contact": "", "touches": 0})
        for t in r.get("topics") or []:
            if t not in cur["topics"]:
                cur["topics"].append(str(t))
        if r.get("stage"):
            cur["stage"] = str(r["stage"])
        cur["last_contact"] = str(r.get("at") or cur["last_contact"])
        cur["touches"] += 1
    return out


# ─────────────────────────────────────────────────────────────────────────────
# CROSS-HOST RECONCILIATION — read-only; recovers publications whose host
# spool never reached this consolidator
# ─────────────────────────────────────────────────────────────────────────────
def _dial_governed(account: str) -> bool | None:
    """Does this account have a voice codex? None = could not determine.

    MIRRORS `marketing_publisher._record_persona_post`, which returns early when
    `expression_dial.codex_for(account) is None`. Reconciliation must apply the
    SAME filter or it stops recovering memory and starts inventing it: on the
    real ledger (2026-09-18) 944 of 1,138 live publications belong to accounts
    with no codex — `flagship` and `mastermind_news` — and the live path stores
    none of them, because there are no per-quirk caps for those counters to feed.
    """
    try:
        from engine.marketing import expression_dial as _ed  # noqa: PLC0415

        return _ed.codex_for(account) is not None
    except Exception:  # noqa: BLE001
        return None


def _outbox_items_by_id(root: Path | str | None) -> dict[str, dict] | None:
    """Index the SHARED outbox by item id. None when the corpus is unreadable.

    `outbox.read_items_all` is the canonical corpus reader (tracked
    `items.jsonl`, which the publish lane commits back, PLUS this host's spool).
    Last write wins, matching how the publisher resolves an item it re-reads.
    """
    try:
        from engine.marketing import outbox as _outbox  # noqa: PLC0415

        rows = _outbox.read_items_all(root)
    except Exception:  # noqa: BLE001
        return None
    out: dict[str, dict] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        iid = str(r.get("id") or "").strip()
        if iid:
            out[iid] = r
    return out


def reconcile_publications(
    *,
    now: datetime,
    root: Path | str | None = None,
    accounts: Sequence[str] | None = None,
    retention_days: int = RETENTION_DAYS,
) -> tuple[dict[str, list[dict]], dict[str, Any]]:
    """Recover phrase records for publications this host never spooled.

    THE DEFECT THIS CLOSES. `scripts/marketing_publisher` writes TWO things on
    one `if receipt.ok:` branch, forty lines apart, with opposite durability:
    the publication receipt goes to `data/marketing/publications.jsonl`, which
    `marketing-publish.yml` commits back to git and every host therefore sees;
    the memory record goes to `data/marketing/personas_host/`, which `.gitignore`
    excludes and which never leaves the machine that wrote it. The publisher runs
    on `macstudio-light`; this consolidator runs on `macstudio`; the reply desk
    runs on the VPS. Each has its own checkout, so a post shipped by one host
    was invisible to the ledger advanced by another — silently, because a missing
    spool and an idle host look identical. Measured on main at 2026-09-18:
    1,138 live publications across 46 days and 7 accounts, and
    `data/marketing/personas/` did not exist at all, so `recent_posts()` returned
    `[]` for every account and every per-quirk frequency cap was unarmed.

    THE REPAIR USES NO NEW TRANSPORT. Both inputs are existing tracked ledgers
    that already cross hosts by the same git commit-back the outbox uses; this
    function only READS them. No new ledger, queue, lifecycle plane or shadow
    authority is introduced — the publication receipt remains the sole authority
    on what published, and this store remains the sole authority on persona
    memory. Reconciliation is the join between them, and the join is verified:
    a recovered record is admitted only when `sha256(item.text)` equals the
    receipt's own `effective_copy_hash`, so memory can never be seeded with copy
    that differs from what actually shipped.

    IT IS A LOOKBACK, NOT A WATERMARK. Nothing is consumed, marked, or deleted,
    so a missed night self-heals on the next one, a re-run converges to the same
    set, and a duplicated receipt row folds to one record on the shared key. A
    publication that cannot be resolved is REPORTED, never silently dropped.

    Returns `(rows_by_account, report)`. The report is the observability
    surface — see `consolidate()`.
    """
    at_now = _as_utc(now)
    cutoff = (at_now - timedelta(days=max(0, int(retention_days)))).strftime(_DAY_FMT)
    want = {str(a) for a in accounts} if accounts is not None else None

    report: dict[str, Any] = {
        "publications_read": 0,
        "considered": 0,
        "recovered": 0,
        "aged_out": 0,
        "unresolved": [],
        "sources": {},
        # SAY WHAT IS NOT COVERED, in the artifact itself. `phrases` is the
        # publication store and the one the fatigue/cadence readers consume, and
        # the publication receipt ledger is a per-POST record — replies and
        # promises do not appear in it, so this join cannot reach them. The
        # reply desk's `relations` writes on the VPS therefore remain host-local.
        # Recorded here rather than left to be rediscovered.
        "stores_reconciled": ["phrases"],
        "stores_not_reconciled": ["promises", "relations"],
    }

    pubs_path = publications_path(root)
    pub_rows = _read_jsonl(pubs_path)
    report["sources"]["publications"] = {
        "path": str(pubs_path),
        "exists": pubs_path.exists(),
        "rows": len(pub_rows),
    }
    if not pub_rows:
        # A ledger we cannot read is NOT proof that nothing published — it is
        # proof that we cannot tell, and those two must never print the same.
        # An ABSENT ledger is a broken checkout or a missing restore; a PRESENT
        # but empty one is a host that genuinely has no receipts yet.
        report["unavailable"] = (
            "publication receipt ledger absent" if not pubs_path.exists()
            else "publication receipt ledger present but empty"
        )
        return {}, report
    report["publications_read"] = len(pub_rows)

    items = _outbox_items_by_id(root)
    report["sources"]["outbox_items"] = {
        "readable": items is not None,
        "rows": len(items or {}),
    }
    if items is None:
        report["unavailable"] = "outbox item corpus unreadable — copy text unrecoverable"
        return {}, report

    governed: dict[str, bool | None] = {}
    out: dict[str, list[dict]] = {}

    for pub in pub_rows:
        if not isinstance(pub, dict):
            continue
        if str(pub.get("mode") or "") != _LIVE_MODE:
            continue
        account = str(pub.get("account") or "").strip()
        asset_id = str(pub.get("asset_id") or "").strip()
        if not account or not asset_id:
            # A LIVE receipt we cannot even address. Something published and we
            # cannot say what or for whom — the one thing this repair exists to
            # stop being silent. Reported without an account, since that is
            # precisely the field that is missing.
            report["unresolved"].append(
                {"asset_id": asset_id, "account": account, "reason": "malformed_receipt"})
            continue
        if want is not None and account not in want:
            continue

        if account not in governed:
            governed[account] = _dial_governed(account)
        gov = governed[account]
        if gov is None:
            # Cannot tell whether this account has caps to feed. Fail CLOSED:
            # recovering nothing under-counts by one, inventing records for an
            # ungoverned account corrupts a ledger nothing would ever correct.
            report["unresolved"].append(
                {"asset_id": asset_id, "account": account, "reason": "dial_unavailable"})
            continue
        if not gov:
            continue  # no codex, no caps — the live path stores nothing either

        report["considered"] += 1

        item = items.get(asset_id)
        if item is None:
            report["unresolved"].append(
                {"asset_id": asset_id, "account": account, "reason": "no_outbox_item"})
            continue

        text = str(item.get("text") or "")
        if not text:
            report["unresolved"].append(
                {"asset_id": asset_id, "account": account, "reason": "empty_item_text"})
            continue

        want_hash = str(pub.get("effective_copy_hash") or "").strip()
        got_hash = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
        if not want_hash:
            report["unresolved"].append(
                {"asset_id": asset_id, "account": account, "reason": "receipt_has_no_copy_hash"})
            continue
        if want_hash != got_hash:
            # The item was edited after it shipped. Recording today's text
            # against yesterday's publication would put words in a persona's
            # mouth it never said, so this is a gap, not a record.
            report["unresolved"].append(
                {"asset_id": asset_id, "account": account, "reason": "copy_hash_mismatch"})
            continue

        as_of = str(item.get("as_of") or "").strip()
        if not as_of:
            # FAIL CLOSED ON A MISSING BUSINESS DATE, and say so.
            #
            # `_phrase_day` falls back to a wall clock when `as_of` is empty, and
            # the two writers hold DIFFERENT wall clocks: `record_post` gets the
            # publisher loop's `now`, this path gets the receipt's
            # `published_at`. They agree almost always and disagree exactly when
            # a post straddles midnight UTC — which would mint a second id for a
            # post that shipped once and double-count it on the emitting host.
            # Guessing is not worth it: the identity must be REPRODUCED, not
            # approximated, so an item with no business date is reported instead
            # of recovered. (0 of 1,138 live publications on main are in this
            # state; the branch exists so the guarantee is unconditional.)
            report["unresolved"].append(
                {"asset_id": asset_id, "account": account, "reason": "no_business_date"})
            continue

        # `source` is a free-form dict on the item; a malformed row must not
        # crash a nightly step whose whole contract is never-raise.
        src = item.get("source")
        franchise = str(src.get("franchise") or "") if isinstance(src, dict) else ""

        at = _parse_iso(str(pub.get("published_at") or "").strip()) or at_now
        rec = _phrase_record(
            account, text,
            at=at,
            as_of=as_of,
            franchise=franchise,
            kind=str(item.get("kind") or ""),
            item_id=asset_id,
            source="reconciled",
        )
        if rec["date"] < cutoff:
            # Outside the tracked ledger's own retention horizon — the
            # consolidator would drop it on the next line anyway. Counted, so
            # `considered` still equals recovered + unresolved + aged_out and a
            # reader is never left wondering where the difference went.
            report["aged_out"] = int(report.get("aged_out", 0)) + 1
            continue
        out.setdefault(account, []).append(rec)
        report["recovered"] += 1

    return out, report


def _parse_iso(s: str) -> datetime | None:
    """Parse a receipt timestamp. `Z` is the publisher's spelling of +00:00."""
    raw = str(s or "").strip()
    if not raw:
        return None
    try:
        return _as_utc(datetime.fromisoformat(raw.replace("Z", "+00:00")))
    except Exception:  # noqa: BLE001
        return None


def _report_reconciliation(recon: dict[str, Any]) -> None:
    """Make the reconciliation's OWN failures visible in the nightly log.

    The defect this module repairs was silent: a spool that never arrived and a
    host that published nothing produce the same evidence — nothing. So a
    reconciliation that cannot see its inputs must never be allowed to look like
    a reconciliation that found nothing to do. Anything unreadable or
    unresolvable is stated, with its reason and its count.

    Bare `print` at line start, flushed — a logger would prefix the annotation
    and GitHub would silently drop it (house law).
    """
    unavailable = recon.get("unavailable")
    if unavailable:
        print(
            "::warning title=persona_memory::publication reconciliation UNAVAILABLE "
            f"({unavailable}) — persona memory may undercount posts shipped by "
            "another host; frequency caps read as 'at least this many'",
            flush=True,
        )
        return

    unresolved = recon.get("unresolved") or []
    if unresolved:
        by_reason: dict[str, int] = {}
        for u in unresolved:
            r = str((u or {}).get("reason") or "unknown")
            by_reason[r] = by_reason.get(r, 0) + 1
        detail = ", ".join(f"{k}={v}" for k, v in sorted(by_reason.items()))
        print(
            f"::warning title=persona_memory::{len(unresolved)} live publication(s) "
            f"could not be reconciled into persona memory ({detail}) — these posts "
            "shipped but are NOT counted by the frequency caps",
            flush=True,
        )

    recovered = int(recon.get("recovered") or 0)
    if recovered:
        print(
            f"::notice title=persona_memory::reconciled {recovered} publication(s) "
            f"from the shared receipt ledger (considered {recon.get('considered')})",
            flush=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# THE CONSOLIDATOR — the only writer of data/marketing/personas/
# ─────────────────────────────────────────────────────────────────────────────
@contextlib.contextmanager
def _spool_lock(root: Path | str | None, timeout_s: float = 2.0):
    """Advisory flock over the host spool, mirroring `outbox._outbox_lock`.

    THE READ→TRUNCATE WINDOW IS THE RACE (review F10). `consolidate()` reads a
    spool, writes the tracked ledger, then unlinks the spool. A daemon
    appending a post between the read and the unlink loses that post outright —
    it was never folded in and its file is gone. On the VPS the fastlane daemon
    appends at press-tick cadence while the nightly runs, so the window is real,
    not theoretical.

    Yields True when held, False when proceeding unlocked (flock unsupported or
    busy) — same fail-soft contract as the outbox lock, because a lock failure
    must not stop the nightly from advancing ledgers.
    """
    lock_fh = None
    acquired = False
    try:
        try:
            import fcntl  # noqa: PLC0415  (POSIX only; fail-soft elsewhere)

            d = _root_path(root) / "data" / "marketing" / "personas_host"
            d.mkdir(parents=True, exist_ok=True)
            lock_fh = open(d / ".lock", "a", encoding="utf-8")  # noqa: SIM115
            deadline = time.monotonic() + timeout_s
            while True:
                try:
                    fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        print(
                            "::warning title=persona_memory::host spool lock busy after "
                            f"{timeout_s:.1f}s — consolidating unlocked; a concurrent "
                            "append may be lost",
                            flush=True,
                        )
                        break
                    time.sleep(0.05)
        except Exception as exc:  # noqa: BLE001
            print(
                f"::warning title=persona_memory::advisory lock unavailable ({exc}) — "
                "consolidating unlocked",
                flush=True,
            )
        yield acquired
    finally:
        if lock_fh is not None:
            try:
                if acquired:
                    import fcntl  # noqa: PLC0415

                    fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
            except Exception:  # noqa: BLE001
                pass
            try:
                lock_fh.close()
            except Exception:  # noqa: BLE001
                pass


def _accounts_with_host_state(root: Path | str | None) -> list[str]:
    base = _root_path(root) / "data" / "marketing" / "personas_host"
    try:
        return sorted(p.name for p in base.iterdir() if p.is_dir())
    except (FileNotFoundError, NotADirectoryError, OSError):
        return []


def consolidate(
    *,
    now: datetime,
    root: Path | str | None = None,
    accounts: Sequence[str] | None = None,
    retention_days: int = RETENTION_DAYS,
    clear_host: bool = True,
) -> dict[str, Any]:
    """Advance the TRACKED persona ledgers from the host spools. Nightly only.

    This is the sole writer of `data/marketing/personas/` (charter §2 amendment
    13; the nightly-sole-advancer law). It is idempotent: records dedup on their
    stable key, so a retried nightly cannot double a counter — which matters
    because those counters bound how often a persona may use its own signature.

    `clear_host=True` truncates each consolidated host spool AFTER the tracked
    write lands, so an interrupted run loses nothing (the records are still in
    the spool and the next run re-folds them).

    CROSS-HOST SPOOL STRANDING IS CLOSED (was the XG-W3 review's F11). This
    consolidator still only READS the spool on the machine it runs on — that
    part is unchanged and is fine — but it no longer treats that spool as the
    whole truth. Before folding anything it calls `reconcile_publications()`,
    which recovers every live publication in the SHARED receipt ledger that this
    host's spool does not already account for, and the account set it iterates
    is the UNION of spool-bearing accounts and publication-bearing ones. A post
    shipped from `macstudio-light` or the VPS therefore reaches this ledger even
    though its spool never left that machine.

    The old note said the honest reading of a cap was "at least this many". It
    now converges on "exactly this many" for `phrases`, with two stated
    exceptions that the returned report NAMES rather than hides: publications
    the join cannot resolve (`reconciliation.unresolved`), and the two stores a
    per-post receipt cannot speak for (`promises`, `relations`).

    Returns a per-account, per-store summary of counts for the nightly log, plus
    a `reconciliation` block carrying the cross-host result and its gaps.
    """
    # THE KNOB MUST BE REAL (review F12). daily.yml sets
    # MARKETING_PERSONA_MEMORY_ENABLED on this step; a step that ignores its own
    # env gate is a fake knob — an operator who sets it to 0 to stop ledger
    # growth would see the ledgers advance anyway. Default ON: absent means
    # "nobody expressed an opinion", which for a nightly consolidation is
    # correct, and only an explicit off-value disables it.
    flag = os.environ.get("MARKETING_PERSONA_MEMORY_ENABLED")
    if flag is not None and flag.strip().lower() in ("0", "false", "no", "off"):
        print(
            "::notice title=persona_memory::MARKETING_PERSONA_MEMORY_ENABLED="
            f"{flag!r} — skipping consolidation; tracked ledgers not advanced",
            flush=True,
        )
        return {"as_of": _as_utc(now).isoformat(), "accounts": {}, "skipped": "disabled"}

    # HOLD THE SPOOL LOCK ACROSS THE WHOLE read→write→truncate SEQUENCE
    # (review F10) — see `_spool_lock`. Taking it per-store would reopen the
    # same window between stores.
    with _spool_lock(root):
        return _consolidate_locked(
            now=now, root=root, accounts=accounts,
            retention_days=retention_days, clear_host=clear_host,
        )


def _consolidate_locked(
    *,
    now: datetime,
    root: Path | str | None,
    accounts: Sequence[str] | None,
    retention_days: int,
    clear_host: bool,
) -> dict[str, Any]:
    """The body of `consolidate()`, run under the host-spool lock."""
    cutoff_dt = _as_utc(now) - timedelta(days=max(0, int(retention_days)))
    cutoff = cutoff_dt.strftime(_DAY_FMT)
    summary: dict[str, Any] = {"as_of": _as_utc(now).isoformat(), "accounts": {}}

    # CROSS-HOST RECONCILIATION FIRST — it decides which accounts exist.
    #
    # NEVER-RAISE, and never at the expense of the local fold. Reconciliation
    # reads two ledgers this module does not own; if one of them is malformed in
    # a way `_read_jsonl` cannot absorb, the correct outcome is a degraded run
    # that still advances the host's own spool and SAYS it was degraded — not a
    # nightly step that dies and leaves every ledger where it was.
    try:
        recovered, recon = reconcile_publications(
            now=now, root=root, accounts=accounts, retention_days=retention_days,
        )
    except Exception as exc:  # noqa: BLE001
        recovered, recon = {}, {
            "recovered": 0, "considered": 0, "unresolved": [], "sources": {},
            "unavailable": f"reconciliation raised: {exc!r}",
        }
    summary["reconciliation"] = recon
    _report_reconciliation(recon)

    # THE ACCOUNT SET IS A UNION, AND THAT IS THE WHOLE FIX. Deriving it from
    # `_accounts_with_host_state` alone made this consolidator blind by
    # construction: a host that published nothing has no spool, so it produced
    # ZERO accounts and skipped straight past every publication another host had
    # shipped. On main at 2026-09-18 the consolidating runner had no
    # `personas_host/` directory at all while 1,138 live publications sat in the
    # shared receipt ledger — the loop below never ran once.
    ids = (
        list(accounts) if accounts is not None
        else sorted(set(_accounts_with_host_state(root)) | set(recovered))
    )

    for account in ids:
        acct_summary: dict[str, Any] = {}
        for store in STORES:
            host_path = _store_path(host_dir(root, account), store)
            tracked_path = _store_path(repo_dir(root, account), store)
            host_rows = _read_jsonl(host_path)
            tracked_rows = _read_jsonl(tracked_path)
            # Reconciled rows come LAST everywhere, so a record the emitting
            # host actually spooled always wins the dedup over its recovered
            # twin and keeps its `source: "emit"` provenance.
            recovered_rows = list(recovered.get(account, ())) if store == "phrases" else []
            if not host_rows and not tracked_rows and not recovered_rows:
                continue

            if store == "promises":
                # Fold status updates onto their promise id, then keep every
                # still-open loop REGARDLESS of age — an old open promise is
                # exactly the one most in need of closing, so retention must
                # never quietly retire it.
                folded = _fold_promises(tracked_rows + host_rows)
                merged = []
                for r in folded.values():
                    day = _day_of(r)
                    if str(r.get("status") or "open") == "open" or not day or day >= cutoff:
                        merged.append(r)
                merged.sort(key=lambda r: str(r.get("at") or ""))
            else:
                seen: set[str] = set()
                merged = []
                for r in tracked_rows + host_rows + recovered_rows:
                    day = _day_of(r)
                    if day and day < cutoff:
                        continue
                    key = _record_key(store, r)
                    if key in seen:
                        continue
                    seen.add(key)
                    merged.append(r)
                merged.sort(key=lambda r: str(r.get("at") or ""))

            _write_tracked(tracked_path, merged)
            acct_summary[store] = {
                "host": len(host_rows),
                "tracked_before": len(tracked_rows),
                "tracked_after": len(merged),
            }
            if recovered_rows:
                # How many of the recovered rows were genuinely ABSENT here, as
                # opposed to folding onto a record this host had already spooled.
                # The difference is the cross-host loss this run actually
                # repaired, and it is the number worth reading in the log.
                acct_summary[store]["reconciled_offered"] = len(recovered_rows)
                acct_summary[store]["reconciled_admitted"] = sum(
                    1 for r in merged if str(r.get("source") or "") == "reconciled")
            if clear_host and host_rows:
                try:
                    host_path.unlink()
                except OSError:
                    pass
        if acct_summary:
            summary["accounts"][account] = acct_summary
    return summary


def _main(argv: Sequence[str] | None = None) -> int:
    """CLI entry for the nightly step: `python -m engine.marketing.persona_memory`."""
    import argparse

    ap = argparse.ArgumentParser(description="Consolidate persona memory host spools into the tracked ledgers.")
    ap.add_argument("--root", default=None)
    ap.add_argument("--retention-days", type=int, default=RETENTION_DAYS)
    ap.add_argument("--keep-host", action="store_true", help="do not truncate host spools")
    args = ap.parse_args(list(argv) if argv is not None else None)

    out = consolidate(
        now=datetime.now(timezone.utc),
        root=args.root,
        retention_days=args.retention_days,
        clear_host=not args.keep_host,
    )
    n = len(out.get("accounts") or {})
    recon = out.get("reconciliation") or {}
    # Bare print at line start — a logger would prefix the annotation and
    # GitHub would silently drop it (house law).
    print(
        f"persona_memory: consolidated {n} account(s); "
        f"reconciled {recon.get('recovered', 0)} publication(s) from the shared "
        f"receipt ledger, {len(recon.get('unresolved') or [])} unresolved",
        flush=True,
    )
    if not n:
        # NOT "no host spools" any more — that phrasing is exactly the silence
        # this module was repaired to stop. An empty result now means both the
        # local spool AND the shared receipt ledger had nothing to add, and the
        # reconciliation block above says which of those two it was.
        print(
            "::notice title=persona_memory::nothing to consolidate — no host spool "
            "and no unreconciled publication in the shared receipt ledger",
            flush=True,
        )
    print(json.dumps(out, ensure_ascii=False, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
