"""lib/team_membership.py — caller-scoped team rows for GET /api/account.

Credentials are injected as ``(url, service_key)`` — no baked-in project default.
This is macro's first RLS-scoped PostgREST read: Authorization carries the CALLER'S
token, never the service-role key.

The one upstream call is bounded the same way the auth call beside it on /api/account
is bounded (see ``_UPSTREAM_SEM`` and ``_TIMEOUT``), and every failure — network,
schema, or a body in an unexpected shape — degrades to a fresh "unavailable" result
rather than raising.
"""
from __future__ import annotations

import json
import logging
import threading
import urllib.error
import urllib.parse
import urllib.request

_log = logging.getLogger(__name__)

#: Seconds. Matches the bounded auth call this read sits beside on the same route
#: (``app/paywall.py``'s GET /auth/v1/user uses ``timeout=4``). /api/account is a sync
#: route on FastAPI's shared worker threadpool and already makes one billing call, so a
#: slow vendor must not hold a worker thread longer than the auth path already tolerates.
_TIMEOUT = 4
_MAX_TEAMS = 20  # a one-line summary, not a management UI — Terminal's own MAX_TEAMS is 200

#: Caps concurrent team-membership reads, mirroring ``app/paywall.py``'s
#: ``_AUTH_UPSTREAM_SEM = threading.BoundedSemaphore(8)`` and its non-blocking
#: ``acquire(blocking=False)``. Excess callers SHED to "unavailable" instead of queueing
#: on the ~40-thread pool — the reason ``app.main.require_user``'s own docstring gives for
#: bounding the auth call: a slow vendor sheds instead of pinning the pool (and
#: /api/health with it). Shedding is safe here precisely because "unavailable" is a
#: distinct state from "no teams", so a shed read can never be misread as zero teams.
_UPSTREAM_LIMIT = 8
_UPSTREAM_SEM = threading.BoundedSemaphore(_UPSTREAM_LIMIT)


def _unavailable() -> dict:
    """A FRESH fail-closed result, built at each site that needs one.

    Deliberately a factory rather than a module-level constant copied with ``dict()``:
    ``dict()`` is shallow, so every returned result would share one ``items`` list for
    the life of the process and a single ``.append`` in any future consumer would poison
    every subsequent caller's payload.
    """
    return {"status": "unavailable", "items": [], "truncated": False}


def _team_name(embed: object) -> str:
    """The display name out of PostgREST's ``teams(name)`` embed, in whatever shape it arrives.

    PostgREST does not guarantee a single shape for an embed, so each is handled
    explicitly rather than left to a bare ``.get``:

    * ``{"name": "Acme"}`` — the to-one shape on current PostgREST. Used as-is.
    * ``[{"name": "Acme"}]`` — the to-many shape, and the to-one shape on older PostgREST
      versions. The first dict in the list wins; one ``team_members`` row is one
      membership, so there is never a second team to choose between.
    * ``null``, key absent, ``[]``, or a list holding no object — no embedded row came
      back. The name is "".
    * a bare scalar instead of an object, or a ``name`` that is not a string (``null``,
      a number) — the name is "".

    A name that cannot be read yields "" while the row is KEPT and the overall status
    stays "ok". That is the deliberate trade: the membership itself (``team_id`` +
    ``role``) is the fact /api/account is answering and it is fully readable in every
    shape above; the name is display sugar, and the renderer already shows an empty name
    as an unnamed team. Dropping the row instead would turn a cosmetic embed change into
    a caller silently losing a team they are in.
    """
    if isinstance(embed, list):
        embed = next((e for e in embed if isinstance(e, dict)), None)
    name = embed.get("name") if isinstance(embed, dict) else None
    return name if isinstance(name, str) else ""


def extract_bearer(authorization: str | None) -> str | None:
    """The same 'Bearer <token>' contract app.main.require_user already enforces upstream,
    factored out so this module never re-derives it differently."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization.split(" ", 1)[1] or None


def fetch_caller_teams(token: str | None, user_id: str, supabase: tuple[str, str]) -> dict:
    """{"status": "ok", "items": [...], "truncated": bool} | {"status": "unavailable", ...}.

    SECURITY-CRITICAL: `Authorization` carries the CALLER'S OWN token, never
    SUPABASE_SERVICE_ROLE_KEY. `apikey` stays the service-role key only because Supabase's
    gateway requires SOME valid project key on that header; it does not elevate the Postgres
    role PostgREST assumes — that role is set from the JWT on `Authorization`, which is the
    caller's own ('authenticated', auth.uid() = user_id). This is what makes the read RLS-
    scoped rather than a service-role bypass — the exact distinction the census's "same RLS
    path the teams routes already use" instruction draws. A missing/empty token — however
    that happens — returns "unavailable" and NEVER falls back to a service-role Authorization
    header; there is no path in this function that can silently escalate.

    An explicit `user_id=eq.<uid>` filter is kept even though `tm_select_member` already scopes
    by `is_team_member` — belt-and-braces, matching `lib/teams.ts`'s own stated convention
    ("RLS is the authority; every query here also carries an explicit filter"). The filter
    value is escaped with `safe=""` so no character in a user id — `/` included — can leave
    the filter value it belongs to.

    The call is BOUNDED, not merely timed out: `_UPSTREAM_SEM` is acquired without blocking
    and a caller that cannot get a permit sheds to "unavailable" immediately, so a stalled
    PostgREST cannot pin more than `_UPSTREAM_LIMIT` of FastAPI's worker threads on a route
    that also serves plan display. This is the same shape as the auth call on the same
    request path.
    """
    url, service_key = supabase
    if not url or not service_key or not token or not user_id:
        return _unavailable()
    q = (
        f"team_members?select=team_id,role,teams(name)"
        f"&user_id=eq.{urllib.parse.quote(user_id, safe='')}"
        f"&order=created_at.asc&limit={_MAX_TEAMS + 1}"
    )
    req = urllib.request.Request(
        f"{url}/rest/v1/{q}", method="GET",
        headers={"apikey": service_key, "Authorization": f"Bearer {token}",
                 "Accept": "application/json"},
    )
    if not _UPSTREAM_SEM.acquire(blocking=False):
        _log.warning("team membership read shed: %d concurrent reads already in flight",
                     _UPSTREAM_LIMIT)
        return _unavailable()
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            raw = resp.read()
        rows = json.loads(raw) if raw else []
    except urllib.error.HTTPError as exc:
        # PostgREST ANSWERED and refused. A 4xx here is the one fault an offline suite
        # cannot reach — a renamed `created_at`, or a `teams` relationship that is not
        # exposed — and without a log it is indistinguishable from a network outage. Only
        # the status code is logged: the URL carries the project reference and the headers
        # carry the caller's token, and neither belongs in a log line.
        _log.warning("team membership read failed: HTTP %s", exc.code)
        return _unavailable()
    except Exception as exc:  # noqa: BLE001 — timeout/DNS/TLS/reset/bad body: degrade, never crash
        _log.warning("team membership read failed: %s", type(exc).__name__)
        return _unavailable()
    finally:
        _UPSTREAM_SEM.release()
    if not isinstance(rows, list):
        _log.warning("team membership read failed: body was %s, not a list", type(rows).__name__)
        return _unavailable()
    truncated = len(rows) > _MAX_TEAMS
    items = []
    for row in rows[:_MAX_TEAMS]:
        if not isinstance(row, dict):
            continue
        team_id, role = row.get("team_id"), row.get("role")
        # A malformed row (bad id, or a role outside the closed set) is dropped silently —
        # the same discipline lib/teams.ts::listTeams uses — and does not change `truncated`,
        # which only reflects whether the query itself hit the cap. An unreadable team NAME
        # is not a malformed row: see _team_name for every embed shape and why the row stays.
        if isinstance(team_id, str) and role in ("owner", "admin", "member"):
            items.append({"team_id": team_id, "team_name": _team_name(row.get("teams")),
                          "role": role})
    return {"status": "ok", "items": items, "truncated": truncated}
