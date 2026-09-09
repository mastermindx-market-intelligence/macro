"""lib/team_membership.py — caller-scoped team rows for GET /api/account.

Pure functions. Credentials are injected as ``(url, service_key)`` — no baked-in
project default. This is macro's first RLS-scoped PostgREST read: Authorization
carries the CALLER'S token, never the service-role key.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

_TIMEOUT = 6
_MAX_TEAMS = 20  # a one-line summary, not a management UI — Terminal's own MAX_TEAMS is 200

_UNAVAILABLE = {"status": "unavailable", "items": [], "truncated": False}


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
    ("RLS is the authority; every query here also carries an explicit filter").
    """
    url, service_key = supabase
    if not url or not service_key or not token or not user_id:
        return dict(_UNAVAILABLE)
    q = (
        f"team_members?select=team_id,role,teams(name)"
        f"&user_id=eq.{urllib.parse.quote(user_id)}"
        f"&order=created_at.asc&limit={_MAX_TEAMS + 1}"
    )
    req = urllib.request.Request(
        f"{url}/rest/v1/{q}", method="GET",
        headers={"apikey": service_key, "Authorization": f"Bearer {token}",
                 "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            raw = resp.read()
        rows = json.loads(raw) if raw else []
        if not isinstance(rows, list):
            return dict(_UNAVAILABLE)
    except Exception:  # noqa: BLE001 — any network/parse fault degrades, never crashes /api/account
        return dict(_UNAVAILABLE)
    truncated = len(rows) > _MAX_TEAMS
    items = []
    for row in rows[:_MAX_TEAMS]:
        if not isinstance(row, dict):
            continue
        team_id, role = row.get("team_id"), row.get("role")
        team = row.get("teams") or {}
        name = team.get("name") if isinstance(team, dict) else None
        # A malformed row (bad id, or a role outside the closed set) is dropped silently —
        # the same discipline lib/teams.ts::listTeams uses — and does not change `truncated`,
        # which only reflects whether the query itself hit the cap.
        if isinstance(team_id, str) and role in ("owner", "admin", "member"):
            items.append({"team_id": team_id, "team_name": name if isinstance(name, str) else "",
                          "role": role})
    return {"status": "ok", "items": items, "truncated": truncated}
